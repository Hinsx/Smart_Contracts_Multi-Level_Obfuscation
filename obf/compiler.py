"""Compilation layer built on :mod:`py_solc_x` (solc 0.8.20).

Two invariants from the engineering spec drive this module:

* **LF normalisation** - every source string is rewritten to ``\\n`` before it is
  compiled or patched.  solc reports AST offsets as UTF-8 *byte* offsets, so a
  CRLF source would shift every single offset handed to the patch engine.
* **Explicit solc path** - the compiler binary is resolved through py-solc-x and
  returned by :func:`get_solc_executable`, never through ``PATH``.  The same path
  is passed to Slither later so both tools agree on 0.8.20.

The compiled artifact is exposed as :class:`CompilationResult`, which carries the
ABI, creation/runtime bytecode, the runtime opcode listing and the full AST that
later passes address by byte range.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import solcx
from solcx import compile_standard
from solcx.install import get_executable

SOLC_VERSION = "0.8.20"
DEFAULT_OPTIMIZER_RUNS = 200

#: Outputs requested from solc for every compilation.
OUTPUT_SELECTION = {
    "*": {
        "": ["ast"],
        "*": [
            "abi",
            "evm.bytecode.object",
            "evm.deployedBytecode.object",
            "evm.deployedBytecode.opcodes",
        ],
    },
}


class CompilationError(RuntimeError):
    """Raised when solc rejects a source file."""


@dataclass(frozen=True)
class CompilationResult:
    """Everything downstream phases need from a single solc invocation."""

    source_name: str
    contract_name: str
    abi: list[dict]
    bytecode: str
    deployed_bytecode: str
    opcodes: str
    ast: dict
    solc_version: str = SOLC_VERSION

    @property
    def bytecode_bytes(self) -> bytes:
        """Creation bytecode as raw bytes (empty string means nothing to deploy)."""
        return bytes.fromhex(self.bytecode)

    @property
    def deployed_bytecode_bytes(self) -> bytes:
        """Runtime bytecode as raw bytes."""
        return bytes.fromhex(self.deployed_bytecode)

    @property
    def deployed_bytecode_size(self) -> int:
        """Runtime size in bytes (EIP-170 limit check uses this)."""
        return len(self.deployed_bytecode) // 2

    @property
    def opcode_list(self) -> list[str]:
        return self.opcodes.split()


def normalize_source(source_str: str) -> tuple[str, bytes]:
    """Return ``(lf_text, utf8_bytes)`` for one source file.

    The two values are derived from the same string, so byte offsets reported by
    solc for ``lf_text`` are valid indices into ``utf8_bytes``.  Any ``\\r\\n`` or
    lone ``\\r`` becomes ``\\n``; UTF-8 multi-byte characters are preserved.
    """
    if not isinstance(source_str, str):
        raise TypeError(f"source_str must be str, got {type(source_str).__name__}")

    text = source_str.replace("\r\n", "\n").replace("\r", "\n")
    return text, text.encode("utf-8")


def read_source(path: str | Path) -> tuple[str, bytes]:
    """Read a ``.sol`` file as UTF-8, return its LF-normalised text and bytes."""
    raw = Path(path).read_bytes()
    return normalize_source(raw.decode("utf-8"))


def get_solc_executable(version: str = SOLC_VERSION) -> str:
    """Return the absolute path of the pinned solc binary, installing it if needed.

    Slither must be given ``solc=...`` explicitly; using this helper keeps the
    analyser on the same compiler build as the obfuscator.
    """
    installed = {str(item) for item in solcx.get_installed_solc_versions()}
    if version not in installed:
        solcx.install_solc(version)
    return str(get_executable(version))


def compile_source(
    source_str: str,
    optimize: bool = False,
    source_name: str = "Main.sol",
    contract_name: str | None = None,
) -> CompilationResult:
    """Compile one Solidity source string with solc 0.8.20.

    Args:
        source_str: Solidity source; CRLF input is normalised to LF first.
        optimize: enable solc's optimizer (200 runs) when true.
        source_name: logical file name used inside standard-JSON output.
        contract_name: contract to extract; defaults to the only contract found.

    Raises:
        CompilationError: solc reported a syntax or type error.
    """
    lf_source, _ = normalize_source(source_str)

    standard_input = {
        "language": "Solidity",
        "sources": {source_name: {"content": lf_source}},
        "settings": {
            "optimizer": {"enabled": bool(optimize), "runs": DEFAULT_OPTIMIZER_RUNS},
            "outputSelection": OUTPUT_SELECTION,
        },
    }

    try:
        output = compile_standard(standard_input, solc_version=SOLC_VERSION)
    except solcx.exceptions.SolcError as exc:
        raise CompilationError(
            f"solc {SOLC_VERSION} failed to compile {source_name} (optimize={optimize}):\n{exc}"
        ) from exc

    ast = output.get("sources", {}).get(source_name, {}).get("ast")
    if ast is None:
        raise CompilationError(f"solc produced no AST for {source_name}")

    contracts = output.get("contracts", {}).get(source_name, {})
    if not contracts:
        raise CompilationError(f"solc produced no contract for {source_name}")

    if contract_name is None:
        if len(contracts) != 1:
            raise CompilationError(
                f"{source_name} defines several contracts ({sorted(contracts)}); pass contract_name"
            )
        contract_name = next(iter(contracts))
    if contract_name not in contracts:
        raise CompilationError(f"{source_name} does not define contract {contract_name!r}")

    compiled = contracts[contract_name]
    evm = compiled["evm"]
    return CompilationResult(
        source_name=source_name,
        contract_name=contract_name,
        abi=compiled["abi"],
        bytecode=evm["bytecode"]["object"],
        deployed_bytecode=evm["deployedBytecode"]["object"],
        opcodes=evm["deployedBytecode"]["opcodes"],
        ast=ast,
    )
