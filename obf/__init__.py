"""Pure-Python Solidity multi-level obfuscator.

Modules:

* :mod:`obf.compiler` - solc 0.8.20 wrapper (LF normalisation, AST, bytecode, opcodes)
* :mod:`obf.engine` - byte-precise patch engine and per-pass recompilation pipeline
* :mod:`obf.passes` - Level 1 layout, Level 2 data and Level 3 control-flow passes
* :mod:`obf.cli` - command line entry point for single files and batch directories
"""

__all__ = ["cli", "compiler", "engine", "passes"]
