"""Unit and integration tests for the three obfuscation passes (Phase 3).

The heavy functional equivalence proof is the contract suite pointed at each generated
directory (``pytest --contract-dir .../L1``).  These tests pin down the pass-level
guarantees that make those runs meaningful: comments never eat string literals, only
non-ABI symbols are renamed, literals keep their types, ``pure`` functions and
declarations are left alone, and every level keeps the ABI byte-identical.
"""

from __future__ import annotations

import json
import random

import pytest

from obf.compiler import compile_source, normalize_source, read_source
from obf.engine import apply_patches, parse_src, run_pipeline, walk_ast
from obf.passes import control, layout

CONTRACTS = ("Counter", "SimpleERC20", "SimpleAuction", "EscrowVault")

SYNTH = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Synth {
    uint256 public counter;
    uint8 public small = 5;
    bool public enabled = true;
    bool public disabled = false;
    string public note = "http://example.com//path";

    event Incremented(uint256 value);

    function increment() public returns (uint256) {
        uint256 next = counter + 1;
        counter = next;
        emit Incremented(next);
        return counter;
    }

    function _double(uint256 x) internal pure returns (uint256) {
        return x * 2;
    }

    function _secret(uint256 x) private returns (uint256) {
        uint256 doubled = x * 2;
        return doubled;
    }
}
"""


def _nodes(ast: dict, node_type: str) -> list[dict]:
    found: list[dict] = []

    def visit(node: dict, _ancestors: tuple[dict, ...]) -> None:
        if node.get("nodeType") == node_type:
            found.append(node)

    walk_ast(ast, visit)
    return found


def _spans(ast: dict, node_type: str) -> list[tuple[int, int]]:
    return [parse_src(node["src"]) for node in _nodes(ast, node_type)]


# --------------------------------------------------------------------------- #
# Level 1: layout
# --------------------------------------------------------------------------- #


def test_strip_comments_keeps_string_literals_and_spdx():
    source = '// SPDX-License-Identifier: MIT\n// gone\ncontract A { string s = "http://x//y"; }'
    data = normalize_source(source)[1]

    stripped = apply_patches(data, layout.strip_comments(data))
    text = stripped.decode("utf-8")

    assert "SPDX-License-Identifier" in text
    assert "gone" not in text
    assert '"http://x//y"' in text


def test_strip_comments_removes_block_comments_and_blank_runs():
    source = "a;\n\n\n\n/* block\n   comment */\nb;\n"
    out = apply_patches(source.encode(), layout.strip_comments(source.encode())).decode()
    assert "block" not in out
    assert "\n\n\n" not in out
    assert out.strip().startswith("a;")
    assert out.strip().endswith("b;")


def test_rename_only_touches_non_abi_symbols():
    result = run_pipeline(SYNTH, level=1, seed=42, source_name="Synth.sol")
    text = result.source

    assert "function increment" in text  # public
    assert "counter" in text  # public state variable
    assert "note" in text  # public state variable
    assert "_double" not in text  # internal function renamed
    assert "_secret" not in text  # private function renamed
    assert '"http://example.com//path"' in text


@pytest.mark.parametrize("name", CONTRACTS)
def test_level1_keeps_abi(name, contract_dir):
    text, _ = read_source(contract_dir / f"{name}.sol")
    original = compile_source(text, source_name=f"{name}.sol")
    variant = run_pipeline(text, level=1, seed=42, source_name=f"{name}.sol")

    assert json.dumps(variant.compilation.abi, sort_keys=True) == json.dumps(original.abi, sort_keys=True)
    assert variant.stats[0].name == "layout"
    assert variant.stats[0].applied > 0


# --------------------------------------------------------------------------- #
# Level 2: data
# --------------------------------------------------------------------------- #


def test_data_rewrites_uint256_literals_and_booleans():
    result = run_pipeline(SYNTH, level=2, seed=42, source_name="Synth.sol")
    text = result.source

    assert "uint256(" in text  # XOR split
    assert "0x" in text  # boolean comparison
    assert "== 0x00" in text  # false branch of the boolean template


def test_data_leaves_narrow_integer_literals_alone():
    source = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Narrow {
    function f() external pure returns (uint8) { uint8 value = 7; return value; }
}
"""
    result = run_pipeline(source, level=2, seed=42, source_name="Narrow.sol")
    # The local identifier may be renamed by Level 1, but the uint8 literal stays a literal.
    assert "= 7;" in result.source
    assert "uint256(" not in result.source


@pytest.mark.parametrize("name", CONTRACTS)
def test_level2_keeps_abi(name, contract_dir):
    text, _ = read_source(contract_dir / f"{name}.sol")
    original = compile_source(text, source_name=f"{name}.sol")
    variant = run_pipeline(text, level=2, seed=42, source_name=f"{name}.sol")

    assert json.dumps(variant.compilation.abi, sort_keys=True) == json.dumps(original.abi, sort_keys=True)
    assert [stat.name for stat in variant.stats] == ["layout", "data"]
    assert variant.stats[1].applied > 0


# --------------------------------------------------------------------------- #
# Level 3: control flow
# --------------------------------------------------------------------------- #


def test_control_skips_pure_functions():
    compiled = compile_source(SYNTH, source_name="Synth.sol")
    data = normalize_source(SYNTH)[1]
    patches = control.get_patches(data, compiled.ast, random.Random(42), max_injections=3)

    pure_bodies = set()
    for function in _nodes(compiled.ast, "FunctionDefinition"):
        if function.get("stateMutability") == "pure" and function.get("body"):
            pure_bodies.add(parse_src(function["body"]["src"]))

    for start, end, _replacement in patches:
        for body_start, body_end in pure_bodies:
            assert not (body_start <= start < body_end)


def test_control_never_wraps_variable_declaration_statements():
    compiled = compile_source(SYNTH, source_name="Synth.sol")
    data = normalize_source(SYNTH)[1]
    patches = control.get_patches(data, compiled.ast, random.Random(7), max_injections=3)

    declarations = _spans(compiled.ast, "VariableDeclarationStatement")
    assert declarations
    for start, _end, _replacement in patches:
        assert start not in {decl_start for decl_start, _ in declarations}


def test_control_respects_the_injection_budget(contract_dir):
    text, _ = read_source(contract_dir / "SimpleERC20.sol")
    compiled = compile_source(text, source_name="SimpleERC20.sol")
    data = normalize_source(text)[1]

    functions = len(_nodes(compiled.ast, "FunctionDefinition"))
    patches = control.get_patches(data, compiled.ast, random.Random(1), max_injections=1)
    assert 0 < len(patches) <= functions

    none = control.get_patches(data, compiled.ast, random.Random(1), max_injections=0)
    assert none == []


@pytest.mark.parametrize("name", CONTRACTS)
def test_level3_keeps_abi_and_size(name, contract_dir):
    text, _ = read_source(contract_dir / f"{name}.sol")
    original = compile_source(text, source_name=f"{name}.sol")
    variant = run_pipeline(text, level=3, seed=42, max_injections=2, source_name=f"{name}.sol")

    assert json.dumps(variant.compilation.abi, sort_keys=True) == json.dumps(original.abi, sort_keys=True)
    assert [stat.name for stat in variant.stats] == ["layout", "data", "control"]
    assert variant.compilation.deployed_bytecode_size < 24_576
    assert b"block.timestamp" in variant.source_bytes or b"tx.gasprice" in variant.source_bytes


def test_engine_pipeline_is_deterministic_per_seed(contract_dir):
    text, _ = read_source(contract_dir / "EscrowVault.sol")
    first = run_pipeline(text, level=3, seed=42, max_injections=2, source_name="EscrowVault.sol")
    second = run_pipeline(text, level=3, seed=42, max_injections=2, source_name="EscrowVault.sol")
    other = run_pipeline(text, level=3, seed=7, max_injections=2, source_name="EscrowVault.sol")

    assert first.source_bytes == second.source_bytes
    assert first.source_bytes != other.source_bytes


def test_level3_erc20_still_behaves(w3, contract_dir):
    text, _ = read_source(contract_dir / "SimpleERC20.sol")
    result = run_pipeline(text, level=3, seed=42, max_injections=2, source_name="SimpleERC20.sol")

    accounts = w3.eth.accounts
    factory = w3.eth.contract(abi=result.compilation.abi, bytecode=result.compilation.bytecode)
    deploy_receipt = w3.eth.wait_for_transaction_receipt(
        factory.constructor("Demo", "DEMO", 10**24, accounts[9]).transact({"from": accounts[0]})
    )
    token = w3.eth.contract(address=deploy_receipt.contractAddress, abi=result.compilation.abi)

    w3.eth.wait_for_transaction_receipt(
        token.functions.transfer(accounts[1], 1000).transact({"from": accounts[0]})
    )
    assert token.functions.balanceOf(accounts[1]).call() == 990
    assert token.functions.balanceOf(accounts[9]).call() == 10
