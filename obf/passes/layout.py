"""Level 1 - layout obfuscation.

Two transformations, both emitted as byte patches so the engine can apply them in one
descending sweep:

1. **Comment and whitespace stripping** - a small byte scanner that understands string
   literals (including escapes), so ``//`` inside a string is never mistaken for a
   comment.  The SPDX licence line is preserved.  Runs of three or more newlines
   collapse to one blank line and indentation collapses to a single space.
2. **ABI-safe renaming** - only symbols that cannot appear in the external ABI:
   ``private``/``internal`` functions, local variables, and parameters of
   ``private``/``internal`` functions.  Declarations are addressed through solc's
   ``nameLocation`` (the identifier itself, never the whole statement), references
   through ``Identifier`` nodes whose ``referencedDeclaration`` points at the renamed
   node.  Public/external functions, state variables, events, modifiers, struct and
   enum members, constructors, ``receive``/``fallback`` and the parameters of
   public/external functions are never touched, so the ABI JSON stays byte-identical.
"""

from __future__ import annotations

import random
from typing import Any

from obf.engine import Patch, parse_src, walk_ast

_SPDX_PREFIX = b"// SPDX-License-Identifier:"
_WHITESPACE = b" \t\r\n"
_QUOTES = (0x22, 0x27)  # " and '

_RENAMEABLE_VISIBILITY = frozenset({"private", "internal"})


def _scan_comments_and_whitespace(source: bytes) -> list[Patch]:
    """Return disjoint patches for comments and redundant whitespace.

    Comments and the whitespace around them are treated as one "gap" so a block of
    removed comment lines collapses into a single separator instead of leaving several
    blank lines behind.  Gaps never touch string literals or code tokens.
    """
    patches: list[Patch] = []
    size = len(source)
    gap_start: int | None = None

    def close_gap(end: int) -> None:
        nonlocal gap_start
        if gap_start is None:
            return
        run = source[gap_start:end]
        newlines = run.count(b"\n")
        replacement = b" " if newlines == 0 else b"\n" * min(newlines, 2)
        if replacement != run:
            patches.append((gap_start, end, replacement))
        gap_start = None

    i = 0
    while i < size:
        char = source[i]

        if char in _WHITESPACE:
            if gap_start is None:
                gap_start = i
            i += 1
            continue

        if char == 0x2F and i + 1 < size and source[i + 1] == 0x2F:  # //
            if i == 0 and source.startswith(_SPDX_PREFIX):
                close_gap(i)
                while i < size and source[i] != 0x0A:
                    i += 1
                continue
            if gap_start is None:
                gap_start = i
            i += 2
            while i < size and source[i] != 0x0A:
                i += 1
            continue

        if char == 0x2F and i + 1 < size and source[i + 1] == 0x2A:  # /*
            if gap_start is None:
                gap_start = i
            i += 2
            while i + 1 < size and not (source[i] == 0x2A and source[i + 1] == 0x2F):
                i += 1
            i = min(i + 2, size)
            continue

        if char in _QUOTES:
            close_gap(i)
            quote = char
            i += 1
            while i < size:
                if source[i] == 0x5C:  # backslash escape
                    i += 2
                    continue
                if source[i] == quote:
                    i += 1
                    break
                i += 1
            continue

        close_gap(i)
        i += 1

    close_gap(size)
    return patches


def strip_comments(source_bytes: bytes) -> list[Patch]:
    """Comment removal plus blank-line/indentation compaction."""
    return _scan_comments_and_whitespace(source_bytes)


def _collect_targets(ast: dict) -> dict[int, dict]:
    """Collect declarations that may be renamed without touching the ABI."""
    targets: dict[int, dict] = {}

    def visit(node: dict, ancestors: tuple[dict, ...]) -> None:
        node_type = node.get("nodeType")

        if node_type == "FunctionDefinition":
            name = node.get("name")
            if name and node.get("visibility") in _RENAMEABLE_VISIBILITY:
                targets[node["id"]] = node
            return

        if node_type != "VariableDeclaration" or not node.get("name"):
            return

        parent = ancestors[-1] if ancestors else None
        if parent is None or parent.get("nodeType") in ("ContractDefinition", "SourceUnit"):
            return  # state variable or file-level constant

        if parent.get("nodeType") == "VariableDeclarationStatement":
            targets[node["id"]] = node
            return

        if parent.get("nodeType") == "ParameterList":
            owner = ancestors[-2] if len(ancestors) >= 2 else None
            if (
                owner is not None
                and owner.get("nodeType") == "FunctionDefinition"
                and owner.get("parameters") is parent
                and owner.get("visibility") in _RENAMEABLE_VISIBILITY
            ):
                targets[node["id"]] = node

    walk_ast(ast, visit)
    return targets


def _collect_names(ast: dict) -> set[str]:
    names: set[str] = set()

    def visit(node: dict, _ancestors: tuple[dict, ...]) -> None:
        for key in ("name", "value"):
            value = node.get(key)
            if isinstance(value, str):
                names.add(value)

    walk_ast(ast, visit)
    return names


def _fresh_name(rng: random.Random, used: set[str]) -> str:
    while True:
        candidate = f"_0x{rng.getrandbits(24):06x}"
        if candidate not in used:
            used.add(candidate)
            return candidate


def rename_identifiers(source_bytes: bytes, ast: dict, rng: random.Random) -> list[Patch]:
    """Rename private/internal functions, their parameters and all local variables."""
    targets = _collect_targets(ast)
    if not targets:
        return []

    used = _collect_names(ast)
    mapping: dict[int, str] = {}
    patches: list[Patch] = []

    ordered = sorted(targets, key=lambda decl_id: parse_src(targets[decl_id]["nameLocation"])[0])
    for decl_id in ordered:
        new_name = _fresh_name(rng, used)
        mapping[decl_id] = new_name
        start, end = parse_src(targets[decl_id]["nameLocation"])
        patches.append((start, end, new_name.encode("ascii")))

    def visit(node: dict, _ancestors: tuple[dict, ...]) -> None:
        if node.get("nodeType") != "Identifier":
            return
        decl_id = node.get("referencedDeclaration")
        if decl_id in mapping:
            start, end = parse_src(node["src"])
            patches.append((start, end, mapping[decl_id].encode("ascii")))

    walk_ast(ast, visit)
    return patches


def get_patches(
    source_bytes: bytes,
    ast: dict,
    rng: random.Random,
    **kwargs: Any,
) -> list[Patch]:
    """Level 1 entry point: strip layout noise, then rename private symbols."""
    patches = strip_comments(source_bytes)
    patches.extend(rename_identifiers(source_bytes, ast, rng))
    return patches
