# Smart Contracts Multi-Level Obfuscation (SolObfuscator)

A pure-Python, source-level multi-level obfuscator for Solidity smart contracts, shipped with an
automated test harness and a four-dimension quantitative evaluation pipeline
(**Potency**, **Stealth**, **Resilience**, **Cost**).

Course project for **HKUST CSIT5730 - Principles of Cybersecurity**.

> **Status: all five phases complete.**
> Environment, four benchmark contracts, the solc wrapper, the byte-patch engine, the three
> obfuscation levels, the batch CLI and the four-dimension evaluation with charts are implemented.
> All 16 contract variants pass the equivalence suite, and `eval/output/` holds the CSV, the four
> 300 DPI charts and the Dedaub bytecode dumps.

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

### Quick start (uv-managed Python 3.11, no sudo required)

```bash
wget -qO- https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.11

cd Smart_Contracts_Multi-Level_Obfuscation
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

`.python-version` pins the interpreter to 3.11, `solc 0.8.20` is downloaded on first use into
`~/.solcx`, and `.venv` is git-ignored. Exact resolved versions, the verified chain
(solc -> AST -> bytecode/opcodes -> py-evm deploy/gas -> Slither CFG) and the known pitfalls are
documented in [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md).

## 4. Repository layout

```text
.
├── requirements.txt
├── pytest.ini                  # testpaths=tests, pythonpath=. so `obf` imports work
├── README.md
├── contracts/                  # 4 self-contained benchmark contracts (solc 0.8.20, LF)
│   ├── Counter.sol
│   ├── SimpleERC20.sol
│   ├── SimpleAuction.sol
│   └── EscrowVault.sol
├── obf/
│   ├── __init__.py
│   ├── compiler.py             # py-solc-x wrapper: LF normalisation, AST, bytecode / opcodes
│   ├── engine.py               # AST walkers, UTF-8 reverse byte patching, pass scheduler
│   ├── cli.py                  # command line entry point (single file and directory modes)
│   └── passes/
│       ├── __init__.py
│       ├── layout.py           # Level 1: strip comments + ABI-safe renaming
│       ├── data.py             # Level 2: XOR integer split + boolean replacement
│       └── control.py          # Level 3: opaque predicates + dead code injection
├── tests/
│   ├── conftest.py             # py-evm fixtures, gas collection hooks, contract-dir switch
│   ├── test_equivalence.py     # functional equivalence for 4 contracts, happy path + revert
│   └── artifacts/              # generated gas_report.json (git-ignored)
├── eval/
│   ├── run_eval.py             # 4 contracts x 4 levels x 2 optimizer settings -> CSV
│   ├── plot_charts.py          # 4 x 300 DPI PNG charts
│   └── output/                 # generated CSV, obfuscated artifacts, PNG charts
└── docs/
    ├── IMPLEMENTATION_PLAN.md  # phase plan, acceptance criteria, engineering guardrails
    └── ENVIRONMENT.md          # toolchain versions, verification record, known pitfalls
```

## 5. Testing

```bash
# baseline: the four original contracts, default solc settings
.venv/bin/python -m pytest tests/ -v

# same suite with solc --optimize (DoD requires both compiler settings)
.venv/bin/python -m pytest tests/ -v --optimize

# run the identical suite against an obfuscated variant directory
.venv/bin/python -m pytest tests/ -v --contract-dir eval/output/obfuscated/L3
# equivalent: OBF_CONTRACT_DIR=eval/output/obfuscated/L3 .venv/bin/python -m pytest tests/ -v
```

* `tests/test_equivalence.py` (41 tests) covers all four contracts: state changes, emitted
  events and revert boundaries (unauthorised callers, wrong state, insufficient
  allowance/balance, time checks), plus the optimizer matrix, CRLF/LF equality and
  compilation determinism.
* `tests/test_engine.py` (30 tests) covers the patch engine: LF normalisation of `\r\n`
  and lone `\r`, `src` parsing, AST walking with ancestor chains, UTF-8 byte-offset
  robustness against non-ASCII comments, insertion/deletion patches, overlap and
  range rejection, deterministic seeds, per-pass recompilation and error attribution.
* `tests/test_passes.py` (22 tests) covers the three levels: comment stripping keeps
  SPDX and string literals, only non-ABI symbols are renamed, uint256 literals are XOR
  split while narrow integers are left alone, booleans become byte comparisons, `pure`
  functions and declaration statements are never wrapped, the injection budget is
  respected, every level keeps the ABI JSON identical, and an obfuscated ERC20 still
  charges the right fee when deployed on py-evm.
* `tests/test_cli.py` (7 tests) covers `python -m obf.cli`: `--all-levels` writes 12 files,
  the report stays ASCII, the same seed reproduces identical bytes, single-file mode
  writes LF-only UTF-8, and invalid usage or a missing input exits with the documented code.
* `tests/test_eval.py` (12 tests) covers the evaluation maths (cosine similarity, runtime
  block counting, retention ratio, AST counting), checks that every gas scenario still
  targets a real ABI function, and verifies the committed CSV shape and chart/bytecode
  artefacts.
* `--contract-dir` / `OBF_CONTRACT_DIR` switch the source directory, so Phase 3/4 can point the
  same suite at L1/L2/L3 outputs without touching test code.
* Every pytest run writes `tests/artifacts/gas_report.json` with deployment gas, per-function
  call gas and runtime bytecode size for each deployment; `eval/run_eval.py` performs its own
  fixed-scenario gas measurement so the CSV does not depend on a previous test run.

## 6. Command-line interface

```bash
# one level for the whole contracts/ directory -> <out>/L3/*.sol
python -m obf.cli -i contracts -o eval/output/obfuscated -l 3 --seed 42 --max-injections 2

# all three levels in one run -> <out>/L1/, <out>/L2/, <out>/L3/
python -m obf.cli -i contracts -o eval/output/obfuscated --all-levels --seed 42

# a single contract straight to a file
python -m obf.cli -i contracts/Counter.sol -o /tmp/Counter_L3.sol -l 3
```

The console report is plain ASCII so Windows PowerShell and Linux terminals agree:

```text
+---------------+-------+---------+-------+--------+
| Contract      | Level | Patches | Bytes | Status |
+---------------+-------+---------+-------+--------+
| Counter       | 3     | 73      | 7695  | OK     |
| EscrowVault   | 3     | 70      | 5619  | OK     |
| SimpleAuction | 3     | 73      | 5841  | OK     |
| SimpleERC20   | 3     | 105     | 7021  | OK     |
+---------------+-------+---------+-------+--------+
Summary: 4/4 file(s) written, 321 patch(es) applied, output /tmp/inj3
Result: OK
```

* Directory input writes `<output>/L<level>/<Name>.sol`; `--all-levels` writes `L1`, `L2` and `L3`.
* Output is UTF-8 with LF newlines; `--seed` makes the run byte-for-byte reproducible.
* Exit code `0` on success, `1` if any file failed, `2` for invalid usage or a missing input.
* `--max-injections N` caps Level 3 injections per function (default 3, use 2 for tighter gas).
* `eval/output/obfuscated/` in this repository contains the current L1/L2/L3 output for
  `--seed 42`, so the 16-variant regression can be re-run without regenerating first.

## 7. Evaluation

```bash
.venv/bin/python eval/run_eval.py     # CSV + Dedaub bytecode dumps
.venv/bin/python eval/plot_charts.py  # four 300 DPI PNG charts
```

`run_eval.py` evaluates 4 contracts x 4 levels x 2 solc optimizer settings (32 rows) and writes
`eval/output/metrics_summary.csv`:

| Dimension | Columns | Measurement |
| --- | --- | --- |
| Potency | `ast_nodes`, `cfg_basic_blocks`, `cfg_edges` | AST recursion; Slither with the explicit solc 0.8.20 path, summed over non-constructor functions |
| Stealth | `opcode_cosine_sim` | cosine similarity of runtime opcode frequency vectors against the contract's own L0 |
| Resilience | `bytecode_diff_sim`, `optimizer_retention_rate` | difflib ratio of runtime bytecode hex; share of added runtime basic blocks (JUMPDEST markers) surviving `--optimize` |
| Cost | `bytecode_size_kb`, `deploy_gas`, `avg_exec_gas`, `*_delta_pct` | py-evm deployment plus a fixed core-call scenario per contract, relative to L0 |

`optimizer_retention_rate` is measured on deployed bytecode rather than Slither's CFG: the CFG is
rebuilt from the Solidity AST, so it is identical with and without `--optimize`, while the optimizer
can only delete code at the bytecode level. Levels 1 and 2 add no runtime blocks, so their retention
is undefined (empty cell) and the chart shows Level 3 only.

Charts (English labels, 300 DPI):

* `fig1_gas_overhead.png` - deployment and core-call gas growth per level, 4 contracts.
* `fig2_potency_complexity.png` - AST nodes and CFG blocks/edges vs level.
* `fig3_security_gas_tradeoff.png` - CFG growth (potency) vs call-gas growth (cost).
* `fig4_stealth_resilience_opt.png` - opcode cosine / bytecode diff similarity and Level 3 retention.

`SimpleERC20_L0_runtime_bytecode.txt` and `SimpleERC20_L3_runtime_bytecode.txt` contain plain hex
runtime bytecode for the Dedaub decompilation screenshots.

## 8. Roadmap

| Phase | Scope | Exit criterion | Status |
| ----- | ----- | -------------- | ------ |
| 1 | Baseline contracts, compiler wrapper, pytest harness | 4 originals compile; `pytest tests/ -v` fully green | **done (41 tests, both optimizer modes)** |
| 2 | Patch engine and AST utilities | CRLF / non-ASCII smoke test passes; overlapping patches rejected | **done (30 tests)** |
| 3 | L1 / L2 / L3 passes | After each level: 4 contracts compile, pytest 100% pass | **done (22 pass tests, 71 -> 93 total)** |
| 4 | CLI and batch generation | 12 obfuscated contracts generated, all 16 variants pass regression | **done (12 files, 16/16 variants green)** |
| 5 | Four-dimension evaluation and charts | CSV + 4 charts produced without errors | **done (32-row CSV, 4 PNG, bytecode dumps)** |

## 9. Acceptance criteria (Definition of Done)

* 16 contract variants (4 contracts x 4 levels) compile with `solc 0.8.20`, with and without
  `--optimize`.
* All 16 variants pass the same parameterised pytest suite; external ABI signatures identical.
* Same `--seed` yields byte-identical output across runs and across Windows / Linux.
* L3 opaque predicates and dead branches survive `solc --optimize` (CFG complexity retained).
* Every runtime bytecode stays below 24,576 bytes.
* One command produces the CSV summary plus four PNG charts in `eval/output/`.
