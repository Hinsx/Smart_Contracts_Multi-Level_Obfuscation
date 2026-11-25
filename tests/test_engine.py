"""Phase 2 smoke tests for the byte-patch engine.

They exercise LF normalisation, solc ``src`` parsing, AST walking with ancestors,
overlap detection, the UTF-8 byte offset guarantee (a non-ASCII comment must not shift
anything), and the per-pass recompilation pipeline.
"""

from __future__ import annotations

import pytest

from obf.compiler import compile_source, normalize_source, read_source
from obf.engine import (
    PassSpec,
    PatchConflictError,
    PatchRangeError,
    PipelineCompileError,
    PipelineError,
    apply_patches,
    parse_src,
    resolve_passes,
    run_pipeline,
    walk_ast,
)

SOURCE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// 非 ASCII 注释：用于验证 UTF-8 字节偏移，而不是字符偏移
contract Smoke {
    uint256 public value;

    function setValue(uint256 newValue) external {
        value = newValue;
    }
}
"""


def _find(ast: dict, node_type: str, predicate=None) -> list[tuple[dict, tuple[dict, ...]]]:
    """Return ``(node, ancestors)`` pairs for every matching AST node."""
    matches: list[tuple[dict, tuple[dict, ...]]] = []

    def visit(node: dict, ancestors: tuple[dict, ...]) -> None:
        if node.get("nodeType") == node_type and (predicate is None or predicate(node)):
            matches.append((node, ancestors))

    walk_ast(ast, visit)
    return matches


# --------------------------------------------------------------------------- #
# LF normalisation and solc src parsing
# --------------------------------------------------------------------------- #


def test_normalize_converts_crlf_and_lone_cr_to_lf():
    text, data = normalize_source("a\r\nb\rc\nd")
    assert text == "a\nb\nc\nd"
    assert data == b"a\nb\nc\nd"
    assert b"\r" not in data


def test_parse_src_returns_absolute_range():
    assert parse_src("10:20:0") == (10, 30)
    assert parse_src("0:0:0") == (0, 0)


@pytest.mark.parametrize("bad", ["10:20", "a:b:c", "10:20:0:1", "-1:2:0", "1:-2:0", "1:2:-3"])
def test_parse_src_rejects_malformed_input(bad):
    with pytest.raises(ValueError):
        parse_src(bad)


# --------------------------------------------------------------------------- #
# AST walking
# --------------------------------------------------------------------------- #


def test_walk_ast_tracks_ancestor_chain():
    text, _ = normalize_source(SOURCE)
    compiled = compile_source(text, source_name="Smoke.sol")

    found = _find(compiled.ast, "FunctionDefinition", lambda node: node["name"] == "setValue")
    assert len(found) == 1
    node, ancestors = found[0]
    assert [item["nodeType"] for item in ancestors] == ["SourceUnit", "ContractDefinition"]
    assert ancestors[-1]["name"] == "Smoke"

    visited = walk_ast(compiled.ast, lambda *_: None)
    assert visited > 10


def test_walk_ast_ignores_non_node_strings():
    text, _ = normalize_source(SOURCE)
    compiled = compile_source(text, source_name="Smoke.sol")
    types = []
    walk_ast(compiled.ast, lambda node, _ancestors: types.append(node["nodeType"]))
    assert "SourceUnit" in types
    assert "ContractDefinition" in types
    assert all(isinstance(item, str) for item in types)


# --------------------------------------------------------------------------- #
# Patch application
# --------------------------------------------------------------------------- #


def test_apply_patches_replaces_name_location():
    text, data = normalize_source(SOURCE)
    compiled = compile_source(text, source_name="Smoke.sol")
    node, _ = _find(compiled.ast, "ContractDefinition")[0]
    start, end = parse_src(node["nameLocation"])
    assert data[start:end] == b"Smoke"

    patched = apply_patches(data, [(start, end, b"Renamed")])
    assert b"contract Renamed" in patched
    recompiled = compile_source(patched.decode("utf-8"), source_name="Smoke.sol")
    assert recompiled.contract_name == "Renamed"


def test_apply_patches_is_order_independent_for_disjoint_ranges():
    _text, data = normalize_source(SOURCE)
    name_at = data.index(b"Smoke")
    fn_at = data.index(b"setValue")

    first = (name_at, name_at + 5, b"Alpha")
    second = (fn_at, fn_at + 8, b"beta")

    assert apply_patches(data, [first, second]) == apply_patches(data, [second, first])


def test_apply_patches_inserts_and_deletes():
    assert apply_patches(b"hello world", [(0, 0, b"[x]"), (6, 11, b"")]) == b"[x]hello "


def test_apply_patches_rejects_overlap():
    with pytest.raises(PatchConflictError):
        apply_patches(b"abcdefghij", [(1, 5, b"x"), (4, 8, b"y")])


def test_apply_patches_rejects_duplicate_insertion_point():
    with pytest.raises(PatchConflictError):
        apply_patches(b"abc", [(1, 1, b"x"), (1, 1, b"y")])


def test_apply_patches_can_skip_conflicts():
    result = apply_patches(b"abcdefghij", [(1, 5, b"X"), (4, 8, b"Y")], on_conflict="skip")
    assert result == b"aXfghij"


@pytest.mark.parametrize(
    "patch",
    [
        (0, 4, b"x"),  # beyond the source
        (-1, 2, b"x"),  # negative start
        (2, 1, b"x"),  # end before start
        (0, 1, "x"),  # str instead of bytes
    ],
)
def test_apply_patches_rejects_invalid_ranges(patch):
    with pytest.raises(PatchRangeError):
        apply_patches(b"abc", [patch])


# --------------------------------------------------------------------------- #
# UTF-8 byte offsets
# --------------------------------------------------------------------------- #


def test_non_ascii_comment_does_not_shift_byte_offsets():
    text, data = normalize_source(SOURCE)
    compiled = compile_source(text, source_name="Smoke.sol")
    node, _ = _find(compiled.ast, "FunctionDefinition", lambda item: item["name"] == "setValue")[0]

    start, end = parse_src(node["nameLocation"])
    assert data[start:end] == b"setValue"  # byte offsets, not character offsets

    patched = apply_patches(data, [(start, end, b"writeValue")])
    recompiled = compile_source(patched.decode("utf-8"), source_name="Smoke.sol")
    names = [item["name"] for item, _ in _find(recompiled.ast, "FunctionDefinition")]
    assert names == ["writeValue"]


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #


def test_pipeline_level_zero_is_identity():
    _text, data = normalize_source(SOURCE)
    result = run_pipeline(SOURCE, level=0, seed=1, source_name="Smoke.sol")
    assert result.source_bytes == data
    assert result.stats == ()
    assert result.compilation.contract_name == "Smoke"


def test_pipeline_normalizes_crlf_input():
    crlf = SOURCE.replace("\n", "\r\n")
    result = run_pipeline(crlf, level=0, source_name="Smoke.sol")
    assert b"\r" not in result.source_bytes
    assert result.source == SOURCE


def test_pipeline_applies_a_custom_pass():
    def inject_comment(source_bytes, ast, rng, **kwargs):
        return [(0, 0, b"// injected by smoke pass\n")]

    result = run_pipeline(SOURCE, passes=[PassSpec("inject", inject_comment)], source_name="Smoke.sol")
    assert result.source.startswith("// injected by smoke pass\n")
    assert result.stats[0].name == "inject"
    assert result.stats[0].applied == 1
    assert result.stats[0].skipped == 0
    assert result.compilation.contract_name == "Smoke"


def test_pipeline_recompiles_after_each_pass_and_uses_fresh_ast():
    seen_offsets: list[int] = []

    def first_pass(source_bytes, ast, rng, **kwargs):
        # Grow the source *before* the contract so every later offset shifts.
        return [(0, 0, b"// padding comment\n")]

    def second_pass(source_bytes, ast, rng, **kwargs):
        node, _ = _find(ast, "ContractDefinition")[0]
        start, end = parse_src(node["nameLocation"])
        seen_offsets.append(start)
        return [(start, end, b"Shifted")]

    result = run_pipeline(
        SOURCE,
        passes=[PassSpec("pad", first_pass), PassSpec("rename", second_pass)],
        source_name="Smoke.sol",
    )
    assert result.compilation.contract_name == "Shifted"
    assert seen_offsets and seen_offsets[0] == result.source_bytes.index(b"Shifted")


def test_pipeline_names_the_pass_that_broke_compilation():
    def break_pragma(source_bytes, ast, rng, **kwargs):
        marker = b"pragma solidity ^0.8.20;"
        start = source_bytes.index(marker) + len(marker) - 1
        return [(start, start + 1, b"")]

    with pytest.raises(PipelineCompileError) as excinfo:
        run_pipeline(SOURCE, passes=[PassSpec("breaker", break_pragma)], source_name="Smoke.sol")
    assert excinfo.value.pass_name == "breaker"


def test_pipeline_rejects_overlapping_patches_from_a_pass():
    def overlap(source_bytes, ast, rng, **kwargs):
        return [(1, 5, b"x"), (4, 8, b"y")]

    with pytest.raises(PipelineError):
        run_pipeline(SOURCE, passes=[PassSpec("overlap", overlap)], source_name="Smoke.sol")


def test_pipeline_is_deterministic_for_a_seed():
    def random_comment(source_bytes, ast, rng, **kwargs):
        return [(0, 0, f"// nonce={rng.randrange(10**6)}\n".encode("ascii"))]

    first = run_pipeline(SOURCE, seed=7, passes=[PassSpec("rand", random_comment)])
    second = run_pipeline(SOURCE, seed=7, passes=[PassSpec("rand", random_comment)])
    other = run_pipeline(SOURCE, seed=8, passes=[PassSpec("rand", random_comment)])
    assert first.source == second.source
    assert first.source != other.source


def test_counter_with_crlf_and_non_ascii_comment(contract_dir):
    text, _ = read_source(contract_dir / "Counter.sol")
    commented = text.replace("pragma solidity ^0.8.20;", "// 中文注释：偏移鲁棒性\npragma solidity ^0.8.20;")
    crlf = commented.replace("\n", "\r\n")

    identity = run_pipeline(crlf, level=0, source_name="Counter.sol")
    assert identity.compilation.contract_name == "Counter"
    assert b"\r" not in identity.source_bytes

    def insert_marker(source_bytes, ast, rng, **kwargs):
        pragma, _ = _find(ast, "PragmaDirective")[0]
        _start, end = parse_src(pragma["src"])
        return [(end, end, b"\n// obfuscated marker")]

    replaced = run_pipeline(
        crlf, passes=[PassSpec("marker", insert_marker)], source_name="Counter.sol"
    )
    assert b"// obfuscated marker" in replaced.source_bytes
    assert b"\r" not in replaced.source_bytes
    assert replaced.compilation.deployed_bytecode_size > 0


def test_resolve_passes_knows_level_zero_and_rejects_unknown_levels():
    assert resolve_passes(0) == []
    with pytest.raises(ValueError):
        resolve_passes(9)
    with pytest.raises(ValueError):
        run_pipeline(SOURCE, level=4)
