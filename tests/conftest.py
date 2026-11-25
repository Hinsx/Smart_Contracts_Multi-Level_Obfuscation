"""Shared pytest fixtures for the Solidity obfuscation test suite.

The suite is deliberately contract-directory agnostic: ``--contract-dir DIR`` (or the
``OBF_CONTRACT_DIR`` environment variable) selects the folder of ``<Name>.sol`` files
under test, so the exact same tests can later run against the original contracts and
against the Level 1 / 2 / 3 outputs.

Every test gets a fresh in-process py-evm chain (``web3[tester]``), no network and no
external node.  Deployment gas, call gas and runtime bytecode sizes are collected into
``tests/artifacts/gas_report.json`` at session end for the Phase 5 evaluation.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import pytest
from eth_tester.exceptions import TransactionFailed
from web3 import Web3
from web3.exceptions import ContractLogicError
from web3.logs import DISCARD
from web3.providers.eth_tester import EthereumTesterProvider

from obf.compiler import CompilationResult, compile_source, read_source

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"

#: Exceptions eth-tester/web3 raise for a reverted call or transaction.
REVERT_ERRORS = (TransactionFailed, ContractLogicError)

_GAS_ENTRIES: list[dict[str, Any]] = []
_RUN_META: dict[str, Any] = {}


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("obfuscator", "multi-level obfuscator options")
    group.addoption(
        "--contract-dir",
        action="store",
        default=None,
        metavar="DIR",
        help="directory holding the <Name>.sol contracts under test (default: contracts)",
    )
    group.addoption(
        "--optimize",
        action="store_true",
        default=False,
        help="compile the contracts under test with the solc optimizer enabled",
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not _GAS_ENTRIES:
        return
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"run": _RUN_META, "entries": _GAS_ENTRIES}, indent=2, sort_keys=True) + "\n"
    (ARTIFACT_DIR / "gas_report.json").write_text(payload, encoding="utf-8")


@lru_cache(maxsize=None)
def _compile_cached(path_str: str, mtime_ns: int, optimize: bool, source_name: str) -> CompilationResult:
    """Compile once per (file, mtime, optimizer) and reuse across tests.

    ``mtime_ns`` is part of the cache key only so that editing a contract during a
    session invalidates the entry; the suite never patches sources in place.
    """
    del mtime_ns
    text, _ = read_source(path_str)
    return compile_source(text, optimize=optimize, source_name=source_name)


@pytest.fixture(scope="session")
def contract_dir(pytestconfig: pytest.Config) -> Path:
    """Directory containing the contracts under test."""
    raw = pytestconfig.getoption("--contract-dir") or os.environ.get("OBF_CONTRACT_DIR") or "contracts"
    path = Path(raw)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.is_dir():
        pytest.fail(f"contract directory not found: {path}")
    return path


@pytest.fixture(scope="session")
def optimize_flag(pytestconfig: pytest.Config) -> bool:
    return bool(pytestconfig.getoption("--optimize"))


@pytest.fixture()
def w3() -> Web3:
    """A fresh in-process py-evm chain for every test (no network, no external node)."""
    return Web3(EthereumTesterProvider())


@dataclass
class Deployed:
    """A deployed contract plus the gas bookkeeping for that deployment."""

    name: str
    w3: Web3
    contract: Any
    receipt: Any
    compilation: CompilationResult
    default_account: str
    calls: dict[str, list[int]] = field(default_factory=dict)

    @property
    def address(self) -> str:
        return self.receipt.contractAddress

    def transact(self, fn_name: str, *args: Any, from_: str | None = None, value: int = 0) -> Any:
        """Send a transaction to ``fn_name``, return its receipt and record the gas used."""
        account = from_ or self.default_account
        fn = getattr(self.contract.functions, fn_name)(*args)
        tx_hash = fn.transact({"from": account, "value": value})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.calls.setdefault(fn_name, []).append(receipt.gasUsed)
        return receipt

    def view(self, fn_name: str, *args: Any, from_: str | None = None) -> Any:
        """Call a view/pure function (or public getter) without mining a block."""
        fn = getattr(self.contract.functions, fn_name)(*args)
        return fn.call({"from": from_ or self.default_account})

    def events(self, event_name: str, receipt: Any) -> list[Any]:
        """Decode only the logs of ``event_name``; ABI mismatches from sibling events are dropped."""
        event = getattr(self.contract.events, event_name)()
        return list(event.process_receipt(receipt, errors=DISCARD))


@pytest.fixture()
def deploy(w3: Web3, contract_dir: Path, optimize_flag: bool) -> Callable[..., Deployed]:
    """Compile and deploy ``<contract_dir>/<name>.sol`` on the fresh chain."""

    def _deploy(
        name: str,
        *args: Any,
        from_: str | None = None,
        value: int = 0,
        optimize: bool | None = None,
    ) -> Deployed:
        path = contract_dir / f"{name}.sol"
        if not path.is_file():
            pytest.fail(f"contract source not found: {path}")

        use_optimizer = optimize_flag if optimize is None else optimize
        result = _compile_cached(
            str(path), path.stat().st_mtime_ns, use_optimizer, f"{name}.sol"
        )

        account = from_ or w3.eth.accounts[0]
        factory = w3.eth.contract(abi=result.abi, bytecode=result.bytecode)
        tx_hash = factory.constructor(*args).transact({"from": account, "value": value})
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            pytest.fail(f"deployment of {name} failed (status={receipt.status})")

        deployed = Deployed(
            name=name,
            w3=w3,
            contract=w3.eth.contract(address=receipt.contractAddress, abi=result.abi),
            receipt=receipt,
            compilation=result,
            default_account=account,
        )
        if not _RUN_META:
            _RUN_META.update(
                {
                    "contract_dir": str(contract_dir),
                    "optimize": bool(optimize_flag),
                    "pytest": pytest.__version__,
                }
            )
        _GAS_ENTRIES.append(
            {
                "contract": name,
                "source_dir": str(path.parent),
                "optimize": bool(use_optimizer),
                "deployment_gas": receipt.gasUsed,
                "runtime_size_bytes": result.deployed_bytecode_size,
                "runtime_size_kb": round(result.deployed_bytecode_size / 1024.0, 3),
                "calls": deployed.calls,
            }
        )
        return deployed

    return _deploy


@pytest.fixture()
def expect_revert() -> Callable[[Callable[[], Any], str], None]:
    """Assert that a call reverts with a specific reason string."""

    def _check(action: Callable[[], Any], reason: str) -> None:
        with pytest.raises(REVERT_ERRORS) as excinfo:
            action()
        message = str(excinfo.value)
        assert reason in message, f"expected revert reason {reason!r}, got {message!r}"

    return _check


@pytest.fixture()
def travel(w3: Web3) -> Callable[[int], int]:
    """Advance chain time by N seconds (eth-tester takes an absolute timestamp)."""

    def _travel(seconds: int) -> int:
        tester = w3.provider.ethereum_tester
        current = tester.get_block_by_number("pending")["timestamp"]
        target = current + int(seconds)
        tester.time_travel(target)
        return target

    return _travel
