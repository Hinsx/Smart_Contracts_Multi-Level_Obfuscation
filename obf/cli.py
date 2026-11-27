"""Command line interface for the Solidity multi-level obfuscator.

Usage::

    python -m obf.cli -i contracts -o eval/output/obfuscated -l 3 --seed 42 --max-injections 2
    python -m obf.cli -i contracts -o eval/output/obfuscated --all-levels --seed 42
    python -m obf.cli -i contracts/Counter.sol -o out/Counter_L3.sol -l 3

Directory input writes ``<output>/L<level>/<Name>.sol``; ``--all-levels`` writes the
L1, L2 and L3 trees in one run.  Every file is written as UTF-8 with LF newlines, and
the console summary is plain ASCII so Windows PowerShell and Linux terminals agree.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from obf.compiler import CompilationError, read_source
from obf.engine import PipelineError, run_pipeline

PROG = "python -m obf.cli"
ALL_LEVELS = (1, 2, 3)


@dataclass(frozen=True)
class Job:
    """One contract to obfuscate at one level."""

    source: Path
    level: int
    destination: Path


@dataclass
class Outcome:
    contract: str
    level: int
    patches: int | str
    size: int | str
    status: str
    message: str = ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Obfuscate Solidity sources at level 1 (layout), 2 (data) or 3 (control flow).",
        epilog="Output is written as UTF-8 with LF newlines; the same --seed reproduces identical bytes.",
    )
    parser.add_argument("-i", "--input", required=True, metavar="PATH", help="a .sol file or a directory of .sol files")
    parser.add_argument("-o", "--output", required=True, metavar="PATH", help="output directory, or a .sol path for single-file mode")
    parser.add_argument("-l", "--level", type=int, choices=(0, 1, 2, 3), default=None, help="obfuscation level to produce (0 copies the source)")
    parser.add_argument("--all-levels", action="store_true", help="produce levels 1, 2 and 3 in one run")
    parser.add_argument("--seed", type=int, default=42, help="deterministic RNG seed (default: 42)")
    parser.add_argument("--max-injections", type=int, default=3, dest="max_injections", help="maximum control-flow injections per function (default: 3)")
    return parser


def collect_jobs(input_path: Path, output_path: Path, levels: Sequence[int]) -> list[Job]:
    """Resolve the input/output pair into concrete write jobs."""
    if input_path.is_dir():
        sources = sorted(path for path in input_path.glob("*.sol") if path.is_file())
        if not sources:
            raise ValueError(f"no .sol files found in {input_path}")
        return [Job(source, level, output_path / f"L{level}" / source.name) for level in levels for source in sources]

    if input_path.is_file():
        if len(levels) > 1:
            base = output_path
            return [Job(input_path, level, base / f"L{level}" / input_path.name) for level in levels]
        if output_path.suffix.lower() == ".sol":
            return [Job(input_path, levels[0], output_path)]
        return [Job(input_path, levels[0], output_path / f"L{levels[0]}" / input_path.name)]

    raise ValueError(f"input not found: {input_path}")


def _print_table(rows: list[Outcome]) -> None:
    headers = ("Contract", "Level", "Patches", "Bytes", "Status")
    cells = [(row.contract, str(row.level), str(row.patches), str(row.size), row.status) for row in rows]
    widths = [max(len(headers[i]), *(len(row[i]) for row in cells)) for i in range(len(headers))]

    separator = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def line(values: Sequence[str]) -> str:
        return "|" + "|".join(f" {value:<{width}} " for value, width in zip(values, widths)) + "|"

    print(separator)
    print(line(headers))
    print(separator)
    for row in cells:
        print(line(row))
    print(separator)


def run_job(job: Job, seed: int, max_injections: int) -> Outcome:
    try:
        source_text, _ = read_source(job.source)
        result = run_pipeline(
            source_text,
            level=job.level,
            seed=seed,
            max_injections=max_injections,
            source_name=job.source.name,
        )
        job.destination.parent.mkdir(parents=True, exist_ok=True)
        job.destination.write_bytes(result.source_bytes)
    except (CompilationError, PipelineError, OSError, ValueError) as exc:
        message = " ".join(str(exc).split())
        print(f"ERROR {job.source.name} (level {job.level}): {message}", file=sys.stderr)
        return Outcome(job.source.stem, job.level, "-", "-", "FAILED")

    return Outcome(job.source.stem, job.level, result.total_applied, len(result.source_bytes), "OK")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.all_levels and args.level is not None:
        parser.error("use either --level or --all-levels, not both")
    if not args.all_levels and args.level is None:
        parser.error("pass --level N or --all-levels")
    if args.max_injections < 0:
        parser.error("--max-injections must be >= 0")

    levels = ALL_LEVELS if args.all_levels else (args.level,)

    try:
        jobs = collect_jobs(Path(args.input), Path(args.output), levels)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        f"SolObfuscator: {len(jobs)} file(s), levels {','.join(str(level) for level in levels)}, "
        f"seed {args.seed}, max_injections {args.max_injections}"
    )

    outcomes = [run_job(job, args.seed, args.max_injections) for job in jobs]
    _print_table(outcomes)

    failed = [outcome for outcome in outcomes if outcome.status != "OK"]
    total_patches = sum(outcome.patches for outcome in outcomes if isinstance(outcome.patches, int))
    print(
        f"Summary: {len(outcomes) - len(failed)}/{len(outcomes)} file(s) written, "
        f"{total_patches} patch(es) applied, output {Path(args.output)}"
    )
    if failed:
        print(f"Result: FAILED ({len(failed)} file(s))", file=sys.stderr)
        return 1

    print("Result: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
