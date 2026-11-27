"""Level 3 - control-flow obfuscation.

For every non-``pure`` function, up to ``max_injections`` statements are rewritten as

.. code-block:: solidity

    if (<always-false predicate>) { <side-effect-free local arithmetic> }
    if (<always-true predicate>) { <original statement> } else { <side-effect-free arithmetic> }

The predicates read runtime chain state (``block.timestamp``, ``block.number``,
``tx.gasprice``, ``msg.sender``), so solc cannot fold them away; ``always-false``
variants are provably false but not constant-foldable (e.g. ``x % 2 == 3``).

Red lines enforced here:

* ``VariableDeclarationStatement`` is never selected, so a local declared before the
  branch can never leak into a new block scope and trigger "Undeclared identifier".
* ``pure`` functions are skipped entirely: their bodies may not read chain state, and
  a runtime predicate would not compile there.
* at most ``max_injections`` rewrites per function (default 3), limiting stack growth
  and keeping the risk of "Stack too deep" at bay.

Injected dead code only declares and recomputes a local ``uint256``: it never writes
state, never emits events, and its ``revert()`` guard is strictly unreachable at runtime.
"""

from __future__ import annotations

import random
from typing import Any

from obf.engine import Patch, parse_src, walk_ast

#: Always-true predicates that depend on runtime chain state.
TRUE_PREDICATES: tuple[bytes, ...] = (
    b"((block.timestamp & 1) <= 1)",
    b"((uint256(uint160(msg.sender)) % 2) < 2)",
    b"((tx.gasprice | 1) != 0)",
    b"((block.number | 1) != 0)",
    b"((block.timestamp | 1) != 0)",
)

#: Provably false predicates that solc still cannot constant-fold.
FALSE_PREDICATES: tuple[bytes, ...] = (
    b"((block.timestamp % 2) == 2)",
    b"((block.number & 1) == 2)",
    b"((tx.gasprice % 2) == 3)",
    b"((uint256(uint160(msg.sender)) % 2) == 2)",
    b"((block.number % 2) == 3)",
)

#: Statements that must never be wrapped (scope-sensitive declarations).
_SKIPPED_STATEMENTS = frozenset({"VariableDeclarationStatement"})


def _collect_names(ast: dict) -> set[str]:
    names: set[str] = set()

    def visit(node: dict, _ancestors: tuple[dict, ...]) -> None:
        name = node.get("name")
        if isinstance(name, str):
            names.add(name)

    walk_ast(ast, visit)
    return names


def _fresh_local(rng: random.Random, used: set[str]) -> str:
    while True:
        candidate = f"_0xd{rng.getrandbits(20):05x}"
        if candidate not in used:
            used.add(candidate)
            return candidate


def _dead_code(rng: random.Random, used: set[str]) -> bytes:
    """Dead-branch code that survives ``solc --optimize``.

    A plain constant computation is removed by dead-store elimination, which also
    removes the JUMPDEST/JUMPI pair the injection exists to add.  The value is mixed
    with ``block.timestamp`` so it cannot be constant-folded, and the guard
    ``if (name == 0) revert()`` consumes it, making the computation observable and
    therefore inerasable.  The branch is unreachable at runtime, so behaviour is
    unchanged.
    """
    name = _fresh_local(rng, used)
    first = rng.randrange(1, 2**32)
    second = rng.randrange(1, 2**32)
    mask = rng.randrange(1, 2**32)
    return (
        f"uint256 {name} = (uint256({first}) ^ uint256({second})) ^ (block.timestamp & 1); "
        f"if ({name} == 0) {{ revert(); }} "
        f"{name} = (({name} << 1) | uint256({mask}));"
    ).encode("ascii")


def _collect_immutables(ast: dict) -> set[int]:
    """Ids of ``immutable`` state variables.

    Solidity only allows an immutable to be assigned at construction time and *not*
    inside a conditional, so statements that mention one must never be wrapped.
    """
    ids: set[int] = set()

    def visit(node: dict, _ancestors: tuple[dict, ...]) -> None:
        if node.get("nodeType") == "VariableDeclaration" and node.get("mutability") == "immutable":
            ids.add(node["id"])

    walk_ast(ast, visit)
    return ids


def _mentions(node: dict, declaration_ids: set[int]) -> bool:
    found = False

    def visit(child: dict, _ancestors: tuple[dict, ...]) -> None:
        nonlocal found
        if child.get("nodeType") == "Identifier" and child.get("referencedDeclaration") in declaration_ids:
            found = True

    walk_ast(node, visit)
    return found


def _candidate_functions(ast: dict, immutable_ids: set[int]) -> list[tuple[dict, list[dict]]]:
    """Functions that may be injected, with their eligible top-level statements."""
    functions: list[tuple[dict, list[dict]]] = []

    def visit(node: dict, _ancestors: tuple[dict, ...]) -> None:
        if node.get("nodeType") != "FunctionDefinition":
            return
        if node.get("stateMutability") == "pure":
            return
        body = node.get("body")
        if not isinstance(body, dict) or body.get("nodeType") != "Block":
            return
        statements = [item for item in body.get("statements", []) if isinstance(item, dict)]
        candidates = [
            item
            for item in statements
            if item.get("nodeType") not in _SKIPPED_STATEMENTS
            and not _mentions(item, immutable_ids)
        ]
        if candidates:
            functions.append((node, candidates))

    walk_ast(ast, visit)
    return functions


def _inject(statement: bytes, rng: random.Random, used: set[str]) -> bytes:
    true_predicate = TRUE_PREDICATES[rng.randrange(len(TRUE_PREDICATES))]
    false_predicate = FALSE_PREDICATES[rng.randrange(len(FALSE_PREDICATES))]
    first_dead = _dead_code(rng, used)
    second_dead = _dead_code(rng, used)
    return (
        b"if ("
        + false_predicate
        + b") { "
        + first_dead
        + b" } if ("
        + true_predicate
        + b") { "
        + statement
        + b" } else { "
        + second_dead
        + b" }"
    )


def _statement_span(source: bytes, node: dict) -> tuple[int, int]:
    """Byte span of a statement, including its trailing semicolon.

    solc's ``src`` for an ``ExpressionStatement`` stops before the ``;``, so wrapping
    the raw range would drop the semicolon and produce a parser error.  Extend the
    span over optional whitespace when the next non-space byte is ``;``.
    """
    start, end = parse_src(node["src"])
    cursor = end
    while cursor < len(source) and source[cursor] in b" \t\r\n":
        cursor += 1
    if cursor < len(source) and source[cursor] == 0x3B:  # ';'
        return start, cursor + 1
    return start, end


def get_patches(
    source_bytes: bytes,
    ast: dict,
    rng: random.Random,
    max_injections: int = 3,
    **kwargs: Any,
) -> list[Patch]:
    """Level 3 entry point: wrap statements in opaque predicates and dead branches."""
    budget = int(max_injections)
    if budget <= 0:
        return []

    patches: list[Patch] = []
    used = _collect_names(ast)
    immutable_ids = _collect_immutables(ast)

    for _function, candidates in _candidate_functions(ast, immutable_ids):
        count = min(budget, len(candidates))
        if count <= 0:
            continue
        for index in sorted(rng.sample(range(len(candidates)), count)):
            statement = candidates[index]
            start, end = _statement_span(source_bytes, statement)
            replacement = _inject(source_bytes[start:end], rng, used)
            patches.append((start, end, replacement))

    return patches
