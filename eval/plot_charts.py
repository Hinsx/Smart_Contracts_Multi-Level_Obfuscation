"""Render the four evaluation charts from ``eval/output/metrics_summary.csv``.

All labels are English and every figure is written at 300 DPI, ready to drop into the
presentation.  Run ``python eval/run_eval.py`` first, then::

    python eval/plot_charts.py
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUTPUT_DIR = ROOT / "eval" / "output"
CSV_PATH = OUTPUT_DIR / "metrics_summary.csv"

CONTRACTS = ("Counter", "SimpleERC20", "SimpleAuction", "EscrowVault")
LEVELS = ("L0", "L1", "L2", "L3")
DPI = 300

NUMERIC_FIELDS = (
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

COLORS = {
    "Counter": "#1f77b4",
    "SimpleERC20": "#ff7f0e",
    "SimpleAuction": "#2ca02c",
    "EscrowVault": "#d62728",
}


def load_rows(path: Path | None = None) -> dict[tuple[str, str, str], dict[str, float | str]]:
    source = path or CSV_PATH
    if not source.is_file():
        raise SystemExit(f"missing {source}; run python eval/run_eval.py first")

    data: dict[tuple[str, str, str], dict[str, float | str]] = {}
    with source.open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            row: dict[str, float | str] = {"contract": raw["contract"], "level": raw["level"], "optimize": raw["optimize"]}
            for field in NUMERIC_FIELDS:
                text = raw[field]
                row[field] = float(text) if text not in ("", None) else math.nan
            data[(raw["contract"], raw["level"], raw["optimize"])] = row
    return data


def _save(figure, name: str) -> Path:
    target = OUTPUT_DIR / name
    figure.savefig(target, dpi=DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"wrote {target.relative_to(ROOT)}")
    return target


def chart_gas_overhead(data) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(11, 7.5), constrained_layout=True)
    width = 0.38
    positions = list(range(len(LEVELS)))

    for axis, contract in zip(axes.flat, CONTRACTS):
        deploy = [data[(contract, level, "off")]["deploy_gas_delta_pct"] for level in LEVELS]
        calls = [data[(contract, level, "off")]["avg_exec_gas_delta_pct"] for level in LEVELS]
        axis.bar([p - width / 2 for p in positions], deploy, width, color="#4c72b0", label="Deployment gas")
        axis.bar([p + width / 2 for p in positions], calls, width, color="#dd8452", label="Core-call gas")
        axis.axhline(0.0, color="black", linewidth=0.8)
        axis.set_xticks(positions)
        axis.set_xticklabels(LEVELS)
        axis.set_title(contract)
        axis.set_ylabel("Change vs L0 (%)")
        axis.grid(axis="y", alpha=0.3)

    axes[0, 0].legend(loc="upper left", fontsize=8, frameon=False)
    figure.suptitle("Gas overhead by obfuscation level (solc optimizer off)", fontsize=13)
    _save(figure, "fig1_gas_overhead.png")


def chart_potency(data) -> None:
    figure, (left, right) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)

    for contract in CONTRACTS:
        nodes = [data[(contract, level, "off")]["ast_nodes"] for level in LEVELS]
        left.plot(LEVELS, nodes, marker="o", color=COLORS[contract], label=contract)
    left.set_title("AST node count by level")
    left.set_ylabel("AST nodes")
    left.set_xlabel("Obfuscation level")
    left.grid(alpha=0.3)
    left.legend(fontsize=8, frameon=False)

    mean_blocks = [
        sum(data[(contract, level, "off")]["cfg_basic_blocks"] for contract in CONTRACTS) / len(CONTRACTS)
        for level in LEVELS
    ]
    mean_edges = [
        sum(data[(contract, level, "off")]["cfg_edges"] for contract in CONTRACTS) / len(CONTRACTS)
        for level in LEVELS
    ]
    width = 0.38
    positions = list(range(len(LEVELS)))
    right.bar([p - width / 2 for p in positions], mean_blocks, width, color="#55a868", label="CFG basic blocks")
    right.bar([p + width / 2 for p in positions], mean_edges, width, color="#c44e52", label="CFG edges")
    right.set_xticks(positions)
    right.set_xticklabels(LEVELS)
    right.set_title("CFG size by level (mean across contracts)")
    right.set_ylabel("Count")
    right.set_xlabel("Obfuscation level")
    right.grid(axis="y", alpha=0.3)
    right.legend(fontsize=8, frameon=False)

    figure.suptitle("Potency: structural complexity growth", fontsize=13)
    _save(figure, "fig2_potency_complexity.png")


def chart_tradeoff(data) -> None:
    figure, axis = plt.subplots(figsize=(9, 6), constrained_layout=True)

    for contract in CONTRACTS:
        base_blocks = data[(contract, "L0", "off")]["cfg_basic_blocks"]
        costs = [data[(contract, level, "off")]["avg_exec_gas_delta_pct"] for level in LEVELS]
        potency = [
            (data[(contract, level, "off")]["cfg_basic_blocks"] - base_blocks) / base_blocks * 100.0
            for level in LEVELS
        ]
        axis.plot(costs, potency, marker="o", color=COLORS[contract], label=contract)
        # Only Level 3 carries a visible cost; L0/L1/L2 sit on the origin and would
        # overlap their annotations there.
        axis.annotate("L3", (costs[-1], potency[-1]), textcoords="offset points", xytext=(4, 4), fontsize=8)

    axis.axhline(0.0, color="black", linewidth=0.8)
    axis.axvline(0.0, color="black", linewidth=0.8)
    axis.set_xlabel("Core-call gas change vs L0 (%)")
    axis.set_ylabel("CFG basic-block growth vs L0 (%)")
    axis.set_title("Potency vs cost trade-off (solc optimizer off)")
    axis.grid(alpha=0.3)
    axis.legend(fontsize=8, frameon=False)
    _save(figure, "fig3_security_gas_tradeoff.png")


def chart_stealth_resilience(data) -> None:
    figure, (left, right) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)

    for field, label, marker, color in (
        ("opcode_cosine_sim", "Opcode cosine similarity", "o", "#4c72b0"),
        ("bytecode_diff_sim", "Runtime bytecode diff similarity", "s", "#dd8452"),
    ):
        averages = [
            sum(data[(contract, level, "off")][field] for contract in CONTRACTS) / len(CONTRACTS)
            for level in LEVELS
        ]
        left.plot(LEVELS, averages, marker=marker, color=color, label=label)
    left.set_ylim(0.0, 1.05)
    left.set_title("Stealth and resilience by level (optimizer off)")
    left.set_xlabel("Obfuscation level")
    left.set_ylabel("Similarity to L0")
    left.grid(alpha=0.3)
    left.legend(fontsize=8, frameon=False)

    # Only Level 3 adds runtime basic blocks, so only L3 has a defined retention rate.
    positions = list(range(len(CONTRACTS)))
    retention_l3 = [
        0.0 if math.isnan(data[(contract, "L3", "on")]["optimizer_retention_rate"])
        else data[(contract, "L3", "on")]["optimizer_retention_rate"]
        for contract in CONTRACTS
    ]
    right.bar(positions, retention_l3, 0.5, color="#4c72b0", label="Level 3")
    right.set_xticks(positions)
    right.set_xticklabels(CONTRACTS, fontsize=8)
    right.set_ylim(0.0, 1.05)
    right.set_title("Level 3 retention under solc --optimize")
    right.set_ylabel("Share of added blocks surviving")
    right.grid(axis="y", alpha=0.3)
    right.legend(fontsize=8, frameon=False)

    figure.suptitle("Stealth, bytecode similarity and optimizer retention", fontsize=13)
    _save(figure, "fig4_stealth_resilience_opt.png")


def main() -> int:
    data = load_rows()
    chart_gas_overhead(data)
    chart_potency(data)
    chart_tradeoff(data)
    chart_stealth_resilience(data)
    print("Charts: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
