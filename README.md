# Smart Contracts Multi-Level Obfuscation (SolObfuscator)

A pure-Python, source-level multi-level obfuscator for Solidity smart contracts, shipped with an
automated test harness and a four-dimension quantitative evaluation pipeline
(**Potency**, **Stealth**, **Resilience**, **Cost**).

Course project for **HKUST CSIT5730 - Principles of Cybersecurity**.

> **Status: repository scaffold only.**
> The directory layout, dependency manifest and implementation plan are committed.
> The obfuscation passes, CLI and evaluation scripts are implemented phase by phase,
> see [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md).

## 1. Motivation

Once deployed, a smart contract's EVM bytecode is public to the whole network, so a decompiler
such as Dedaub can recover most of the business logic. At the same time the EVM is extremely
sensitive to **gas consumption** and to the **24 KB runtime bytecode limit (EIP-170)**, so heavy
traditional obfuscation cannot be applied as-is. This project explores a *source-level*,
multi-level, low-overhead alternative with a strict equivalence guarantee.

## 2. Obfuscation levels

| Level | Pass (module) | Technique | Hard constraint |
| ----- | ------------- | --------- | --------------- |
| L1 | `obf/passes/layout.py` | Comment stripping, whitespace compaction, ABI-safe renaming of `private`/`internal` functions, parameters and locals | Public ABI must not change |
| L2 | `obf/passes/data.py` | Integer literals split with XOR: `(uint256(N ^ R) ^ uint256(R))`; boolean literals replaced by equivalent expressions | Type-safe under Solidity 0.8 checked arithmetic |
| L3 | `obf/passes/control.py` | Opaque predicates derived from runtime on-chain state (`block.timestamp`, `tx.gasprice`, `msg.sender`), side-effect-free dead branches | Must survive `solc --optimize`; no state mutation |

The obfuscated contract must keep **the same external ABI** and **100% identical business logic
and `revert` behaviour** as the original.

## 3. Environment

| Item | Requirement |
| ---- | ----------- |
| OS | Linux (Ubuntu VM) preferred; Windows / WSL2 supported with the cross-platform rules below |
| Python | **3.10 or 3.11** - do not use 3.12 / 3.13 (prebuilt wheels for `web3[tester]` crypto extensions) |
| Solidity compiler | `solc 0.8.20`, installed through `py-solc-x` and always passed explicitly to Slither |
| Chain sandbox | `web3[tester]` `EthereumTesterProvider` (py-evm), no external node, no network RPC |
| Not allowed | Node.js / Hardhat anywhere in the pipeline |

Cross-platform rules that are enforced by the code base:

* Every `.sol` file is normalised to **LF** before compiling or patching; solc AST offsets are UTF-8
  **byte** offsets, so string and bytes views must come from the same normalised source.
* All path handling uses `pathlib.Path`; no hardcoded separators.
* CLI logs, tables and matplotlib labels are **plain ASCII English** (Windows PowerShell defaults to
  GBK and would otherwise raise `UnicodeEncodeError`).

## 4. Repository layout

```text
.
├── requirements.txt
├── README.md
├── contracts/                  # 4 self-contained benchmark contracts (solc 0.8.20, LF)
│   ├── Counter.sol
│   ├── SimpleERC20.sol
│   ├── SimpleAuction.sol
│   └── EscrowVault.sol
├── obf/
│   ├── __init__.py
│   ├── compiler.py             # py-solc-x wrapper: compile, AST, bytecode / opcodes
│   ├── engine.py               # AST walkers, UTF-8 reverse byte patching, pass scheduler
│   ├── cli.py                  # command line entry point (single file and directory modes)
│   └── passes/
│       ├── __init__.py
│       ├── layout.py           # Level 1: strip comments + ABI-safe renaming
│       ├── data.py             # Level 2: XOR integer split + boolean replacement
│       └── control.py          # Level 3: opaque predicates + dead code injection
├── tests/
│   ├── conftest.py             # py-evm fixtures, gas collection hooks, parameterised loader
│   └── test_equivalence.py     # functional equivalence for 4 contracts, happy path + revert
├── eval/
│   ├── run_eval.py             # 4 contracts x 4 levels x 2 optimizer settings -> CSV
│   ├── plot_charts.py          # 4 x 300 DPI PNG charts
│   └── output/                 # generated CSV, obfuscated artifacts, PNG charts
└── docs/
    └── IMPLEMENTATION_PLAN.md  # phase plan, acceptance criteria, engineering guardrails
```

## 5. Planned CLI

```bash
python -m obf.cli -i contracts -o eval/output/obfuscated -l 3 --seed 42 --max-injections 2
python -m obf.cli -i contracts -o eval/output/obfuscated --all-levels --seed 42
```

* `--all-levels` emits `L1/`, `L2/` and `L3/` variants for every contract in one run.
* Output is written as UTF-8 with LF newlines.
* A pure-ASCII summary table is printed: `Contract | Level | Patches Applied | Compile Status`.

## 6. Evaluation

`eval/run_eval.py` produces `eval/output/metrics_summary.csv` covering the four dimensions:

* **Potency** - AST node count, CFG basic blocks and edges (via Slither with an explicit solc path).
* **Stealth** - cosine similarity of EVM opcode frequency vectors against the L0 baseline.
* **Resilience** - runtime bytecode diff similarity, plus retained CFG growth under `--optimize`.
* **Cost** - runtime bytecode size in KB (< 24 KB), deployment gas and average call gas overhead.

`eval/plot_charts.py` renders four 300 DPI English-labelled PNG charts for the final presentation.
The pipeline also dumps the L0 and L3 runtime bytecode of `SimpleERC20` as text for a Dedaub
decompilation comparison.

## 7. Roadmap

| Phase | Scope | Exit criterion |
| ----- | ----- | -------------- |
| 1 | Baseline contracts, compiler wrapper, pytest harness | 4 originals compile; `pytest tests/ -v` fully green |
| 2 | Patch engine and AST utilities | CRLF / non-ASCII smoke test passes; overlapping patches rejected |
| 3 | L1 / L2 / L3 passes | After each level: 4 contracts compile, pytest 100% pass |
| 4 | CLI and batch generation | 12 obfuscated contracts generated, all 16 variants pass regression |
| 5 | Four-dimension evaluation and charts | CSV + 4 charts produced without errors |

## 8. Acceptance criteria (Definition of Done)

* 16 contract variants (4 contracts x 4 levels) compile with `solc 0.8.20`, with and without
  `--optimize`.
* All 16 variants pass the same parameterised pytest suite; external ABI signatures identical.
* Same `--seed` yields byte-identical output across runs and across Windows / Linux.
* L3 opaque predicates and dead branches survive `solc --optimize` (CFG complexity retained).
* Every runtime bytecode stays below 24,576 bytes.
* One command produces the CSV summary plus four PNG charts in `eval/output/`.
