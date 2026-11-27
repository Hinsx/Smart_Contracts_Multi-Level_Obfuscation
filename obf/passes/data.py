"""Level 2 - data obfuscation.

* **Integer literals** are split with a random mask: ``N`` becomes
  ``(uint256(N ^ R) ^ uint256(R))``.  The conversion is only emitted where the
  surrounding expression is a ``uint256`` context, because Solidity 0.8 rejects
  implicit narrowing: a literal feeding a ``uint8``/``uint16``/``address`` or an array
  length is left alone.
* **Boolean literals** become constant-foldable comparisons of random byte pairs:
  ``true`` -> ``((0x1a ^ 0x2b) == 0x31)`` and ``false`` -> ``((0x1a ^ 0x2b) == 0x00)``.
  These are pure arithmetic, so they are also valid inside ``pure`` functions.

Every replacement is byte-precise: literals are addressed through their own ``src``
range, so no other token can be disturbed.
"""

from __future__ import annotations

import random
from typing import Any

from obf.engine import Patch, parse_src, walk_ast

#: Types whose literals must not be rewritten with a uint256 expression.
_NON_UINT256_TYPES = frozenset(
    {"int256", "address", "bool", "string", "bytes", "byte"}
    | {f"uint{bits}" for bits in range(8, 256, 8)}
    | {f"int{bits}" for bits in range(8, 256, 8)}
    | {f"bytes{size}" for size in range(1, 33)}
)

#: Contexts in which solc demands a compile-time constant integer.
_CONSTANT_CONTEXTS = frozenset({"PragmaDirective", "ArrayTypeName"})

#: Node types that clamp the expected type: the literal is consumed by a call or an
#: index expression, so the surrounding statement type says nothing about it.
_TYPE_BOUNDARIES = frozenset({"FunctionCall", "IndexAccess"})

_MAX_LITERAL = 2**64


def _type_string(node: dict) -> str:
    return (node.get("typeDescriptions") or {}).get("typeString", "")


def _base_type(node: dict) -> str:
    return _type_string(node).split(" ")[0]


def _is_uint256_context(node: dict, ancestors: tuple[dict, ...]) -> bool:
    """True when replacing ``node`` with a uint256 expression keeps the file valid."""
    for ancestor in reversed(ancestors):
        node_type = ancestor.get("nodeType")
        if node_type in _CONSTANT_CONTEXTS or node_type in _TYPE_BOUNDARIES:
            return False

        base = _base_type(ancestor)
        if base in _NON_UINT256_TYPES:
            return False
        if base == "uint256":
            return True

        if node_type == "BinaryOperation":
            left = ancestor.get("leftExpression")
            right = ancestor.get("rightExpression")
            other = right if left is node else left
            if isinstance(other, dict) and _base_type(other) == "uint256":
                return True
        elif node_type == "Assignment":
            left = ancestor.get("leftHandSide")
            if isinstance(left, dict) and _base_type(left) == "uint256":
                return True

    return False


def obfuscate_numbers(source_bytes: bytes, ast: dict, rng: random.Random) -> list[Patch]:
    patches: list[Patch] = []

    def visit(node: dict, ancestors: tuple[dict, ...]) -> None:
        if node.get("nodeType") != "Literal" or node.get("kind") != "number":
            return
        if node.get("subdenomination"):
            return

        raw = node.get("value")
        if not isinstance(raw, str):
            return
        digits = raw.replace("_", "")
        if not digits.isdigit():
            return
        value = int(digits, 10)
        if value > _MAX_LITERAL:
            return
        if not _is_uint256_context(node, ancestors):
            return

        mask = rng.randrange(1, 100_001)
        expression = f"(uint256({value ^ mask}) ^ uint256({mask}))"
        start, end = parse_src(node["src"])
        patches.append((start, end, expression.encode("ascii")))

    walk_ast(ast, visit)
    return patches


def obfuscate_booleans(source_bytes: bytes, ast: dict, rng: random.Random) -> list[Patch]:
    patches: list[Patch] = []

    def visit(node: dict, _ancestors: tuple[dict, ...]) -> None:
        if node.get("nodeType") != "Literal" or node.get("kind") != "bool":
            return
        literal = node.get("value")
        if literal not in ("true", "false"):
            return

        left = rng.randrange(1, 255)
        right = rng.randrange(1, 255)
        while right == left:
            right = rng.randrange(1, 255)

        if literal == "true":
            expression = f"((0x{left:02x} ^ 0x{right:02x}) == 0x{left ^ right:02x})"
        else:
            expression = f"((0x{left:02x} ^ 0x{right:02x}) == 0x00)"

        start, end = parse_src(node["src"])
        patches.append((start, end, expression.encode("ascii")))

    walk_ast(ast, visit)
    return patches


def get_patches(
    source_bytes: bytes,
    ast: dict,
    rng: random.Random,
    **kwargs: Any,
) -> list[Patch]:
    """Level 2 entry point: obfuscate integer and boolean literals."""
    patches = obfuscate_numbers(source_bytes, ast, rng)
    patches.extend(obfuscate_booleans(source_bytes, ast, rng))
    return patches
