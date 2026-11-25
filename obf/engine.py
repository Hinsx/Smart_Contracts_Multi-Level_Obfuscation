"""Byte-precise patch engine for the Solidity obfuscator.

The engine never rewrites the AST back into source code.  Instead every obfuscation
pass reports *byte ranges* into the LF-normalised UTF-8 source, and the engine applies
those ranges in one descending sweep so earlier offsets stay valid.  After each pass
the patched source is recompiled, which both proves the pass kept the contract valid
and refreshes the AST byte coordinates for the next pass.

Contract of this module:

* :func:`normalize_source` / :func:`read_source` (re-exported from ``obf.compiler``)
  are the only supported ways to obtain the bytes that offsets refer to.
* :func:`parse_src` turns solc's ``"start:length:file_id"`` into an absolute range.
* :func:`walk_ast` walks the solc AST and hands every node its ancestor chain.
* :func:`apply_patches` validates ranges, rejects overlaps and applies patches from
  the end of the file backwards.
* :func:`run_pipeline` chains passes per level with per-pass recompilation.
"""

from __future__ import annotations

import importlib
import logging
import random
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

from obf.compiler import (
    CompilationError,
    CompilationResult,
    compile_source,
    normalize_source,
    read_source,
)

logger = logging.getLogger(__name__)

__all__ = [
    "LEVEL_PASSES",
    "PassSpec",
    "PassStat",
    "Patch",
    "PatchConflictError",
    "PatchError",
    "PatchRangeError",
    "PipelineCompileError",
    "PipelineError",
    "PipelineResult",
    "apply_patches",
    "normalize_source",
    "parse_src",
    "read_source",
    "resolve_passes",
    "run_pipeline",
    "walk_ast",
]

#: ``(start_byte, end_byte, replacement_bytes)`` in normalised UTF-8 byte space.
Patch = tuple[int, int, bytes]

#: A pass reports patches for the *current* source and AST.
PassFunc = Callable[..., list[Patch]]

#: Which passes each obfuscation level enables.  0 is the unmodified baseline.
LEVEL_PASSES: dict[int, tuple[str, ...]] = {
    0: (),
    1: ("layout",),
    2: ("layout", "data"),
    3: ("layout", "data", "control"),
}


class PatchError(ValueError):
    """Base class for invalid or conflicting patch ranges."""


class PatchRangeError(PatchError):
    """A patch points outside the source or has an invalid range."""


class PatchConflictError(PatchError):
    """Two patches overlap, or two zero-length inserts share one position."""


class PipelineError(RuntimeError):
    """A pass produced unusable output or the pipeline configuration is invalid."""


class PipelineCompileError(PipelineError):
    """The source produced by a pass no longer compiles."""

    def __init__(self, pass_name: str, source_name: str, error: Exception) -> None:
        self.pass_name = pass_name
        self.source_name = source_name
        self.error = error
        super().__init__(
            f"pass {pass_name!r} broke compilation of {source_name}: {error}"
        )


@dataclass(frozen=True)
class PassSpec:
    """A named pass: ``get_patches(source_bytes, ast, rng, **kwargs)``."""

    name: str
    get_patches: PassFunc


@dataclass(frozen=True)
class PassStat:
    """What one pass changed, for the structured pipeline log."""

    name: str
    requested: int
    applied: int
    skipped: int
    size_before: int
    size_after: int


@dataclass(frozen=True)
class PipelineResult:
    """Final source plus per-pass statistics for one pipeline run."""

    level: int
    seed: int
    source: str
    source_bytes: bytes
    stats: tuple[PassStat, ...]
    compilation: CompilationResult

    @property
    def total_applied(self) -> int:
        return sum(stat.applied for stat in self.stats)

    @property
    def size(self) -> int:
        return len(self.source_bytes)


def parse_src(src: str) -> tuple[int, int]:
    """Convert solc's ``"start:length:file_id"`` into ``(start, end)`` byte offsets."""
    if not isinstance(src, str):
        raise TypeError(f"src must be str, got {type(src).__name__}")

    parts = src.split(":")
    if len(parts) != 3:
        raise ValueError(f"malformed solc src {src!r}: expected 'start:length:file_id'")

    try:
        start, length, file_id = (int(part) for part in parts)
    except ValueError:
        raise ValueError(f"malformed solc src {src!r}: non-integer component") from None

    if start < 0 or length < 0 or file_id < 0:
        raise ValueError(f"malformed solc src {src!r}: negative component")
    return start, start + length


def walk_ast(
    node: Any,
    callback: Callable[[dict[str, Any], tuple[dict[str, Any], ...]], None],
    ancestors: tuple[dict[str, Any], ...] = (),
) -> int:
    """Recursively visit every AST node, passing the chain of enclosing nodes.

    ``callback(node, ancestors)`` is called depth-first in source order; ``ancestors``
    is root-first and *excludes* ``node`` itself.  Only dictionaries carrying a
    ``nodeType`` are treated as nodes, so ``src``/``nameLocation`` strings and other
    metadata are never visited.  Returns the number of visited nodes.
    """
    if not isinstance(node, dict) or "nodeType" not in node:
        return 0

    callback(node, ancestors)
    visited = 1
    child_ancestors = ancestors + (node,)

    for value in node.values():
        if isinstance(value, dict) and "nodeType" in value:
            visited += walk_ast(value, callback, child_ancestors)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and "nodeType" in item:
                    visited += walk_ast(item, callback, child_ancestors)
    return visited


def _validate_patch(patch: Patch, size: int) -> None:
    if not (isinstance(patch, tuple) and len(patch) == 3):
        raise PatchRangeError(f"patch must be (start, end, bytes), got {patch!r}")
    start, end, replacement = patch
    if not isinstance(start, int) or not isinstance(end, int):
        raise PatchRangeError(f"patch offsets must be int, got {patch!r}")
    if not isinstance(replacement, bytes):
        raise PatchRangeError(f"patch replacement must be bytes, got {type(replacement).__name__}")
    if start < 0 or end < start:
        raise PatchRangeError(f"invalid patch range ({start}, {end})")
    if end > size:
        raise PatchRangeError(f"patch range ({start}, {end}) exceeds source size {size}")


def _apply_patches(
    source_bytes: bytes,
    patches: Iterable[Patch],
    on_conflict: str,
) -> tuple[bytes, int, int]:
    """Apply patches and return ``(result, applied, skipped)``."""
    if not isinstance(source_bytes, (bytes, bytearray)):
        raise TypeError(f"source_bytes must be bytes, got {type(source_bytes).__name__}")
    source = bytes(source_bytes)

    prepared: list[Patch] = []
    for patch in patches:
        _validate_patch(patch, len(source))
        prepared.append(patch)

    # Stable sort by start; equal starts keep their input order so that the
    # descending sweep is deterministic.
    prepared.sort(key=lambda item: (item[0], item[1]))

    accepted: list[Patch] = []
    skipped = 0
    for patch in prepared:
        if not accepted:
            accepted.append(patch)
            continue

        previous = accepted[-1]
        prev_start, prev_end = previous[0], previous[1]
        start, end = patch[0], patch[1]
        overlaps = start < prev_end or (start == prev_start and (start == end or prev_start == prev_end))
        if not overlaps:
            accepted.append(patch)
            continue

        if on_conflict == "skip":
            logger.warning("skipping conflicting patch %r (conflicts with %r)", patch, previous)
            skipped += 1
            continue
        if on_conflict != "error":
            raise ValueError(f"on_conflict must be 'error' or 'skip', got {on_conflict!r}")
        raise PatchConflictError(f"patch {patch!r} overlaps patch {previous!r}")

    result = bytearray(source)
    for start, end, replacement in sorted(accepted, key=lambda item: (item[0], item[1]), reverse=True):
        result[start:end] = replacement
    return bytes(result), len(accepted), skipped


def apply_patches(
    source_bytes: bytes,
    patches: Iterable[Patch],
    on_conflict: str = "error",
) -> bytes:
    """Apply byte patches to ``source_bytes`` and return the new bytes.

    Patches are applied from the highest offset downwards, so a patch never shifts the
    coordinates of the patches that follow it.  Ranges are validated against the
    source size, and overlaps are rejected before anything is applied.

    Args:
        source_bytes: LF-normalised UTF-8 source bytes.
        patches: iterable of ``(start, end, replacement_bytes)``.
        on_conflict: ``"error"`` (default) raises :class:`PatchConflictError`;
            ``"skip"`` drops the conflicting patch, logs a warning and keeps going.

    Raises:
        PatchRangeError: a patch is malformed or outside the source.
        PatchConflictError: two patches overlap and ``on_conflict="error"``.
    """
    result, _, _ = _apply_patches(source_bytes, patches, on_conflict)
    return result


def resolve_passes(level: int) -> list[PassSpec]:
    """Load the pass modules for ``level`` in pipeline order.

    Phase 3 adds ``obf.passes.layout`` / ``data`` / ``control``; until then levels
    above 0 fail with a clear error instead of silently doing nothing.
    """
    if level not in LEVEL_PASSES:
        raise ValueError(f"unknown obfuscation level {level}; expected 0..{max(LEVEL_PASSES)}")

    specs: list[PassSpec] = []
    for name in LEVEL_PASSES[level]:
        try:
            module = importlib.import_module(f"obf.passes.{name}")
        except ImportError as exc:
            raise PipelineError(
                f"level {level} needs pass {name!r} but obf.passes.{name} is not implemented yet"
            ) from exc
        get_patches = getattr(module, "get_patches", None)
        if not callable(get_patches):
            raise PipelineError(f"obf.passes.{name} must expose get_patches(source_bytes, ast, rng, **kwargs)")
        specs.append(PassSpec(name=name, get_patches=get_patches))
    return specs


def run_pipeline(
    source_str: str,
    level: int = 0,
    seed: int = 0,
    max_injections: int = 3,
    passes: Sequence[PassSpec] | None = None,
    source_name: str = "Main.sol",
    optimize: bool = False,
    on_conflict: str = "error",
) -> PipelineResult:
    """Run all passes for ``level`` with per-pass recompilation.

    The source is LF-normalised once; every pass receives the same byte space that
    solc reports offsets in.  After each pass the patched text is recompiled:

    * a compile failure raises :class:`PipelineCompileError` naming the pass, so a
      broken obfuscation step is blamed on the right module instead of a later one;
    * the refreshed AST becomes the coordinate system for the next pass, which
      removes all offset drift.

    ``passes`` overrides the level registry (used by the engine smoke tests); the
    random generator is seeded once per run, so an identical ``seed`` reproduces an
    identical output byte for byte.
    """
    lf_text, source_bytes = normalize_source(source_str)
    rng = random.Random(seed)
    compilation = compile_source(lf_text, optimize=optimize, source_name=source_name)

    specs = list(passes) if passes is not None else resolve_passes(level)
    stats: list[PassStat] = []

    for spec in specs:
        requested = list(
            spec.get_patches(source_bytes, compilation.ast, rng, max_injections=max_injections)
        )
        try:
            patched, applied, skipped = _apply_patches(source_bytes, requested, on_conflict)
        except PatchError as exc:
            raise PipelineError(f"pass {spec.name!r} produced invalid patches: {exc}") from exc

        try:
            patched_text = patched.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PipelineError(f"pass {spec.name!r} produced invalid UTF-8: {exc}") from exc

        try:
            compilation = compile_source(patched_text, optimize=optimize, source_name=source_name)
        except CompilationError as exc:
            raise PipelineCompileError(spec.name, source_name, exc) from exc

        stat = PassStat(
            name=spec.name,
            requested=len(requested),
            applied=applied,
            skipped=skipped,
            size_before=len(source_bytes),
            size_after=len(patched),
        )
        stats.append(stat)
        logger.info(
            "pass %s: %d patches applied, %d -> %d bytes",
            spec.name,
            applied,
            stat.size_before,
            stat.size_after,
        )
        source_bytes = patched

    return PipelineResult(
        level=level,
        seed=seed,
        source=source_bytes.decode("utf-8"),
        source_bytes=source_bytes,
        stats=tuple(stats),
        compilation=compilation,
    )
