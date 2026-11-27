"""Tests for the Phase 5 evaluation pipeline (fast, artefact-based)."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import pytest

from eval import plot_charts
from eval.run_eval import (
    CONTRACTS,
    FIELDS,
    _retention,
    cosine_similarity,
    count_ast_nodes,
    gas_scenario,
    opcode_histogram,
    runtime_basic_blocks,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "eval" / "output"


def test_cosine_similarity_identical_and_orthogonal():
    histogram = Counter({"PUSH1": 3, "ADD": 1})
    assert cosine_similarity(histogram, histogram) == pytest.approx(1.0)
    assert cosine_similarity(Counter({"PUSH1": 1}), Counter({"ADD": 1})) == 0.0
    assert cosine_similarity(Counter({"PUSH1": 2}), Counter({"PUSH1": 2})) == pytest.approx(1.0)


def test_runtime_basic_blocks_counts_jumpdest_markers():
    assert runtime_basic_blocks("PUSH1 JUMPDEST ADD JUMPDEST") == 3
    assert runtime_basic_blocks("PUSH1 ADD") == 1


def test_opcode_histogram_ignores_push_immediates():
    histogram = opcode_histogram("PUSH1 0x80 DUP1 PUSH2 0x1234 ADD")
    assert histogram["PUSH1"] == 1
    assert histogram["PUSH2"] == 1
    assert histogram["ADD"] == 1
    assert "0x80" not in histogram
    assert "0x1234" not in histogram
    assert sum(histogram.values()) == 4


def test_count_ast_nodes_visits_nested_nodes_only():
    ast = {
        "nodeType": "SourceUnit",
        "src": "0:10:0",
        "nodes": [
            {"nodeType": "ContractDefinition", "nodes": [{"nodeType": "FunctionDefinition"}]},
            "not a node",
        ],
    }
    assert count_ast_nodes(ast) == 3


@pytest.mark.parametrize("contract", CONTRACTS)
def test_gas_scenario_calls_exist_in_the_abi(contract, contract_dir):
    from obf.compiler import compile_source, read_source

    text, _ = read_source(contract_dir / f"{contract}.sol")
    abi = compile_source(text, source_name=f"{contract}.sol").abi
    functions = {entry["name"] for entry in abi if entry.get("type") == "function"}

    accounts = ["0x" + "00" * 20] * 10
    _args, calls = gas_scenario(contract, accounts)
    assert calls
    for function_name, *_rest in calls:
        assert function_name in functions


def test_retention_ratio_uses_runtime_block_growth():
    def row(blocks: int) -> dict:
        return {"runtime_basic_blocks": blocks}

    index = {
        ("C", "L0", "off"): row(100),
        ("C", "L0", "on"): row(50),
        ("C", "L3", "off"): row(140),
        ("C", "L3", "on"): row(60),
    }
    assert _retention(index, "C", "L3") == pytest.approx(10 / 40)
    assert _retention(index, "C", "L0") is None


def test_retention_is_undefined_without_added_blocks():
    def row(blocks: int) -> dict:
        return {"runtime_basic_blocks": blocks}

    index = {
        ("C", "L0", "off"): row(100),
        ("C", "L0", "on"): row(50),
        ("C", "L1", "off"): row(100),
        ("C", "L1", "on"): row(50),
    }
    assert _retention(index, "C", "L1") is None


@pytest.mark.skipif(not (OUTPUT / "metrics_summary.csv").is_file(), reason="evaluation not generated yet")
def test_committed_metrics_csv_has_32_rows():
    with (OUTPUT / "metrics_summary.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 32
    assert tuple(rows[0].keys()) == FIELDS
    assert {row["level"] for row in rows} == {"L0", "L1", "L2", "L3"}
    assert {row["optimize"] for row in rows} == {"off", "on"}
    assert {row["contract"] for row in rows} == set(CONTRACTS)


@pytest.mark.skipif(not (OUTPUT / "metrics_summary.csv").is_file(), reason="evaluation not generated yet")
def test_plot_charts_dataset_loads_every_row():
    data = plot_charts.load_rows()
    assert len(data) == 32
    assert data[("SimpleERC20", "L3", "off")]["cfg_basic_blocks"] > 0
    assert data[("SimpleERC20", "L0", "off")]["opcode_cosine_sim"] == pytest.approx(1.0)


@pytest.mark.skipif(not (OUTPUT / "metrics_summary.csv").is_file(), reason="evaluation not generated yet")
def test_four_charts_and_bytecode_exports_exist():
    for name in (
        "fig1_gas_overhead.png",
        "fig2_potency_complexity.png",
        "fig3_security_gas_tradeoff.png",
        "fig4_stealth_resilience_opt.png",
    ):
        path = OUTPUT / name
        assert path.is_file(), name
        assert path.stat().st_size > 10_000, name

    for level in ("L0", "L3"):
        payload = (OUTPUT / f"SimpleERC20_{level}_runtime_bytecode.txt").read_text(encoding="ascii").strip()
        assert payload
        assert all(character in "0123456789abcdef" for character in payload)
