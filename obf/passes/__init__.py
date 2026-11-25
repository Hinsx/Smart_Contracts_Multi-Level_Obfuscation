"""Package for the three obfuscation levels.

Each pass module exposes ``get_patches(source_bytes, ast, rng, **kwargs)`` and returns
``(start_byte, end_byte, replacement_bytes)`` tuples in the LF-normalised UTF-8 byte
space, as required by :mod:`obf.engine`.
"""
