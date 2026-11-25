"""Pure-Python Solidity multi-level obfuscator.

Phase 1 ships the compilation layer (:mod:`obf.compiler`); Phase 2 adds the patch
engine (:mod:`obf.engine`).  The three obfuscation passes and the CLI arrive in
later phases.
"""

__all__ = ["compiler", "engine"]
