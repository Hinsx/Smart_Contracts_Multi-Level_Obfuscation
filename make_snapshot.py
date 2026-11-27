"""Merge the project sources into one UTF-8 snapshot file.

Collects every ``.py`` / ``.sol`` file under ``obf/``, ``eval/``, ``tests/`` and
``contracts/``, plus the repository ``README.md`` and
``eval/output/metrics_summary.csv``, and concatenates them into
``project_snapshot.txt`` with a ``=== FILE: <path> ===`` header per file.

Excluded: ``.venv``, ``.git``, ``__pycache__`` and image files.

Run from the repository root::

    .venv/bin/python make_snapshot.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "project_snapshot.txt"

TARGET_DIRS = ("obf", "eval", "tests", "contracts")
SUFFIXES = {".py", ".sol"}
EXTRA_FILES = (
    ROOT / "README.md",
    ROOT / "eval" / "output" / "metrics_summary.csv",
)
EXCLUDED_PARTS = {".venv", ".git", "__pycache__", ".pytest_cache"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".ico", ".tiff"}


def is_excluded(path: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return True
    return path.suffix.lower() in IMAGE_SUFFIXES


def collect_files() -> list[Path]:
    found: dict[Path, Path] = {}

    for directory in TARGET_DIRS:
        base = ROOT / directory
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or is_excluded(path):
                continue
            if path.suffix.lower() in SUFFIXES:
                found[path.resolve()] = path

    for path in EXTRA_FILES:
        if path.is_file() and not is_excluded(path):
            found[path.resolve()] = path

    return sorted(found.values(), key=lambda item: item.relative_to(ROOT).as_posix())


def main() -> int:
    files = collect_files()
    source_bytes = 0

    with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8")
            handle.write(f"=== FILE: {relative} ===\n")
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
            handle.write("\n")
            source_bytes += len(text.encode("utf-8"))

    snapshot_bytes = OUTPUT.stat().st_size
    headers = sum(
        1 for line in OUTPUT.read_text(encoding="utf-8").splitlines() if line.startswith("=== FILE: ")
    )

    print(f"output: {OUTPUT.name}")
    for path in files:
        print(f"  + {path.relative_to(ROOT).as_posix()}")
    print(f"files: {len(files)} (headers found: {headers})")
    print(f"source bytes: {source_bytes} ({source_bytes / 1024:.1f} KB)")
    print(f"snapshot size: {snapshot_bytes} bytes ({snapshot_bytes / 1024:.1f} KB)")
    return 0 if headers == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())
