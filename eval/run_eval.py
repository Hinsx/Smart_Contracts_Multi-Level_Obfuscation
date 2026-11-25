"""Four-dimension evaluation for the multi-level obfuscator (Phase 5).

Produces ``eval/output/metrics_summary.csv`` with one row per
``contract x level x solc-optimizer setting`` (4 x 4 x 2 = 32 rows) covering:

* **Potency** - ``ast_nodes`` (AST node count) and ``cfg_basic_blocks`` / ``cfg_edges``
  from Slither, which is always given the explicit solc 0.8.20 binary path.
* **Stealth** - ``opcode_cosine_sim``: cosine similarity between the runtime opcode
  frequency vector of a variant and its own L0 baseline (closer to 1.0 is stealthier).
* **Resilience** - ``bytecode_diff_sim`` (difflib ratio of runtime hex, lower is better)
  and ``optimizer_retention_rate``: how much of the added control-flow complexity
  survives ``solc --optimize``.  Slither's CFG is derived from the Solidity AST and is
  identical for both optimizer settings, so retention is measured on runtime-bytecode
  basic blocks, counted as ``JUMPDEST`` tokens in solc's disassembled opcode list (push
  payloads are separate tokens, so a ``5b`` byte inside push data can never be
  miscounted); that is exactly where the optimizer can delete injected code.
* **Cost** - ``bytecode_size_kb``, ``deploy_gas``, ``avg_exec_gas`` and their growth
  percentages relative to the L0 baseline of the same optimizer setting.

The script also exports the L0 and L3 runtime bytecode of ``SimpleERC20`` as plain hex
text files for the Dedaub decompilation comparison.

Run from the repository root::

    python eval/run_eval.py
"""

from __future__ import annotations

import csv
import logging
import math
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web3 import Web3  # noqa: E402
from web3.providers.eth_tester import EthereumTesterProvider  # noqa: E402

from obf.compiler import (  # noqa: E402
    CompilationResult,
    compile_source,
    get_solc_executable,
    read_source,
)

OUTPUT_DIR = ROOT / "eval" / "output"
CSV_PATH = OUTPUT_DIR / "metrics_summary.csv"

CONTRACTS = ("Counter", "SimpleERC20", "SimpleAuction", "EscrowVault")
LEVELS = {
    "L0": ROOT / "contracts",
    "L1": OUTPUT_DIR / "obfuscated" / "L1",
    "L2": OUTPUT_DIR / "obfuscated" / "L2",
    "L3": OUTPUT_DIR / "obfuscated" / "L3",
}
OPTIMIZER_SETTINGS = (("off", False), ("on", True))
ETHER = 10**18

FIELDS = (
    "contract",
    "level",
    "optimize",
    "ast_nodes",
    "cfg_basic_blocks",
    "cfg_edges",
    "runtime_basic_blocks",
    "opcode_cosine_sim",
    "bytecode_diff_sim",
    "optimizer_retention_rate",
    "bytecode_size_kb",
    "deploy_gas",
    "avg_exec_gas",
    "deploy_gas_delta_pct",
    "avg_exec_gas_delta_pct",
)

# Slither and crytic-compile are chatty on stderr; the CSV is the product here.
for logger_name in ("Slither", "CryticCompile", "crytic_compile"):
    logging.getLogger(logger_name).setLevel(logging.ERROR)


def count_ast_nodes(ast: dict) -> int:
    """Iterative AST node count (every dict carrying a nodeType)."""
    total = 0
    stack: list[dict] = [ast]
    while stack:
        node = stack.pop()
        total += 1
        for value in node.values():
            if isinstance(value, dict) and "nodeType" in value:
                stack.append(value)
            elif isinstance(value, list):
                stack.extend(item for item in value if isinstance(item, dict) and "nodeType" in item)
    return total


def slither_cfg(path: Path) -> tuple[int, int]:
    """(basic blocks, edges) summed over every non-constructor function via Slither."""
    from slither.slither import Slither

    analysis = Slither(str(path), solc=str(get_solc_executable()))
    blocks = 0
    edges = 0
    for contract in analysis.contracts:
        for function in contract.functions:
            if function.is_constructor:
                continue
            blocks += len(function.nodes)
            edges += sum(len(node.sons) for node in function.nodes)
    return blocks, edges


def opcode_histogram(opcodes: str) -> Counter[str]:
    return Counter(opcodes.split())


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    shared = set(left) | set(right)
    dot = sum(left[key] * right[key] for key in shared)
    norm_left = math.sqrt(sum(value * value for value in left.values()))
    norm_right = math.sqrt(sum(value * value for value in right.values()))
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return dot / (norm_left * norm_right)


def runtime_basic_blocks(opcodes: str) -> int:
    """Basic-block proxy on deployed code: one JUMPDEST per entry point plus the entry."""
    return opcodes.split().count("JUMPDEST") + 1


def gas_scenario(name: str, accounts: list[str]) -> tuple[tuple[Any, ...], list[tuple[str, tuple, int, int]]]:
    """Deployment arguments and the core call sequence used for gas measurement."""
    if name == "Counter":
        return (5,), [
            ("increment", (), 0, 0),
            ("setCount", (41,), 0, 0),
            ("reset", (), 0, 0),
        ]
    if name == "SimpleERC20":
        return ("Demo", "DEMO", 10**24, accounts[9]), [
            ("transfer", (accounts[1], 1000), 0, 0),
            ("approve", (accounts[1], 500), 0, 0),
            ("transferFrom", (accounts[0], accounts[2], 200), 0, 1),
        ]
    if name == "SimpleAuction":
        return (accounts[5], 3600), [
            ("bid", (), ETHER, 1),
            ("bid", (), 2 * ETHER, 2),
            ("withdraw", (), 0, 1),
        ]
    if name == "EscrowVault":
        return (accounts[1], accounts[2]), [
            ("deposit", (), ETHER, 0),
            ("confirmDelivery", (), 0, 0),
        ]
    raise ValueError(f"no gas scenario for {name}")


def measure_gas(compilation: CompilationResult, name: str) -> tuple[int, float]:
    """Deploy on a fresh py-evm chain and average the core-call gas."""
    w3 = Web3(EthereumTesterProvider())
    accounts = list(w3.eth.accounts)
    deploy_args, calls = gas_scenario(name, accounts)

    factory = w3.eth.contract(abi=compilation.abi, bytecode=compilation.bytecode)
    deploy_receipt = w3.eth.wait_for_transaction_receipt(
        factory.constructor(*deploy_args).transact({"from": accounts[0]})
    )
    if deploy_receipt.status != 1:
        raise RuntimeError(f"deployment failed for {name}")

    contract = w3.eth.contract(address=deploy_receipt.contractAddress, abi=compilation.abi)
    gas_used: list[int] = []
    for function_name, args, value, sender_index in calls:
        receipt = w3.eth.wait_for_transaction_receipt(
            getattr(contract.functions, function_name)(*args).transact(
                {"from": accounts[sender_index], "value": value}
            )
        )
        if receipt.status != 1:
            raise RuntimeError(f"{name}.{function_name} failed during gas measurement")
        gas_used.append(receipt.gasUsed)

    return deploy_receipt.gasUsed, mean(gas_used)


def collect_rows() -> tuple[list[dict[str, Any]], dict[tuple[str, str, str], CompilationResult]]:
    cfg_cache: dict[Path, tuple[int, int]] = {}
    compiled: dict[tuple[str, str, str], CompilationResult] = {}
    rows: list[dict[str, Any]] = []

    for level, directory in LEVELS.items():
        if not directory.is_dir():
            raise FileNotFoundError(
                f"missing {directory}; generate the variants first with "
                "python -m obf.cli -i contracts -o eval/output/obfuscated --all-levels --seed 42"
            )
        for name in CONTRACTS:
            path = directory / f"{name}.sol"
            if not path.is_file():
                raise FileNotFoundError(f"missing contract source: {path}")
            if path not in cfg_cache:
                cfg_cache[path] = slither_cfg(path)

            for label, optimize in OPTIMIZER_SETTINGS:
                text, _ = read_source(path)
                compilation = compile_source(text, optimize=optimize, source_name=path.name)
                compiled[(name, level, label)] = compilation
                deploy_gas, avg_exec_gas = measure_gas(compilation, name)

                rows.append(
                    {
                        "contract": name,
                        "level": level,
                        "optimize": label,
                        "ast_nodes": count_ast_nodes(compilation.ast),
                        "cfg_basic_blocks": cfg_cache[path][0],
                        "cfg_edges": cfg_cache[path][1],
                        "runtime_basic_blocks": runtime_basic_blocks(compilation.opcodes),
                        "opcode_cosine_sim": None,
                        "bytecode_diff_sim": None,
                        "optimizer_retention_rate": None,
                        "bytecode_size_kb": compilation.deployed_bytecode_size / 1024.0,
                        "deploy_gas": deploy_gas,
                        "avg_exec_gas": avg_exec_gas,
                        "deploy_gas_delta_pct": None,
                        "avg_exec_gas_delta_pct": None,
                    }
                )
    return rows, compiled


def derive_metrics(
    rows: list[dict[str, Any]],
    compiled: dict[tuple[str, str, str], CompilationResult],
) -> None:
    """Fill similarity, growth and retention columns once the L0 baseline is known."""
    index = {(row["contract"], row["level"], row["optimize"]): row for row in rows}

    for row in rows:
        key = (row["contract"], row["level"], row["optimize"])
        baseline_key = (row["contract"], "L0", row["optimize"])
        current = compiled[key]
        baseline = compiled[baseline_key]
        baseline_row = index[baseline_key]

        row["opcode_cosine_sim"] = cosine_similarity(
            opcode_histogram(baseline.opcodes), opcode_histogram(current.opcodes)
        )
        row["bytecode_diff_sim"] = SequenceMatcher(
            None, baseline.deployed_bytecode, current.deployed_bytecode
        ).ratio()
        row["deploy_gas_delta_pct"] = (
            (row["deploy_gas"] - baseline_row["deploy_gas"]) / baseline_row["deploy_gas"] * 100.0
        )
        row["avg_exec_gas_delta_pct"] = (
            (row["avg_exec_gas"] - baseline_row["avg_exec_gas"])
            / baseline_row["avg_exec_gas"]
            * 100.0
        )

    for row in rows:
        row["optimizer_retention_rate"] = _retention(index, row["contract"], row["level"])


def _retention(
    index: dict[tuple[str, str, str], dict[str, Any]],
    contract: str,
    level: str,
) -> float | None:
    if level == "L0":
        return None
    base_off = index[(contract, "L0", "off")]["runtime_basic_blocks"]
    base_on = index[(contract, "L0", "on")]["runtime_basic_blocks"]
    added_off = index[(contract, level, "off")]["runtime_basic_blocks"] - base_off
    added_on = index[(contract, level, "on")]["runtime_basic_blocks"] - base_on
    if added_off <= 0:
        return None
    return added_on / added_off


def _format(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return value


def write_csv(rows: list[dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _format(row[key]) for key in FIELDS})


def export_bytecode() -> list[Path]:
    """Dump SimpleERC20 L0/L3 runtime bytecode for the Dedaub comparison."""
    written: list[Path] = []
    for level in ("L0", "L3"):
        text, _ = read_source(LEVELS[level] / "SimpleERC20.sol")
        compilation = compile_source(text, source_name="SimpleERC20.sol")
        target = OUTPUT_DIR / f"SimpleERC20_{level}_runtime_bytecode.txt"
        target.write_text(compilation.deployed_bytecode + "\n", encoding="ascii")
        written.append(target)
    return written


def print_summary(rows: list[dict[str, Any]]) -> None:
    headers = ("Contract", "Lvl", "Opt", "AST", "CFG", "Sim", "Diff", "Retain", "KB", "DeployGas", "CallGas")
    cells = [
        (
            row["contract"],
            row["level"],
            row["optimize"],
            str(row["ast_nodes"]),
            f'{row["cfg_basic_blocks"]}/{row["cfg_edges"]}',
            _format(row["opcode_cosine_sim"]) or "-",
            _format(row["bytecode_diff_sim"]) or "-",
            _format(row["optimizer_retention_rate"]) or "-",
            f'{row["bytecode_size_kb"]:.2f}',
            str(row["deploy_gas"]),
            str(int(row["avg_exec_gas"])),
        )
        for row in rows
    ]
    widths = [max(len(headers[i]), *(len(cell[i]) for cell in cells)) for i in range(len(headers))]
    separator = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def line(values: tuple[str, ...]) -> str:
        return "|" + "|".join(f" {value:<{width}} " for value, width in zip(values, widths)) + "|"

    print(separator)
    print(line(headers))
    print(separator)
    for cell in cells:
        print(line(cell))
    print(separator)


def main() -> int:
    rows, compiled = collect_rows()
    derive_metrics(rows, compiled)
    write_csv(rows)
    exported = export_bytecode()
    print_summary(rows)
    print(f"CSV: {CSV_PATH.relative_to(ROOT)} ({len(rows)} rows)")
    for path in exported:
        print(f"bytecode: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
