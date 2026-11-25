"""Tests for the command line interface (Phase 4)."""

from __future__ import annotations

import pytest

from obf.cli import main


def _cli(input_path, output_path, *args: str) -> int:
    return main(["-i", str(input_path), "-o", str(output_path), *args])


def test_all_levels_generates_twelve_ascii_reported_files(tmp_path, contract_dir, capsys):
    output = tmp_path / "out"

    code = _cli(contract_dir, output, "--all-levels", "--seed", "42", "--max-injections", "2")
    assert code == 0

    files = sorted(path.relative_to(output).as_posix() for path in output.glob("L*/*.sol"))
    assert len(files) == 12
    assert files == sorted(f"L{level}/{name}.sol" for level in (1, 2, 3) for name in
                           ("Counter", "SimpleERC20", "SimpleAuction", "EscrowVault"))

    captured = capsys.readouterr()
    table_lines = [line for line in captured.out.splitlines() if line.startswith(("+", "|"))]
    assert table_lines
    assert all(line.isascii() for line in table_lines)
    assert "| Contract" in table_lines[1]
    assert "Result: OK" in captured.out


def test_level_three_is_deterministic_across_runs(tmp_path, contract_dir):
    first = tmp_path / "first"
    second = tmp_path / "second"

    assert _cli(contract_dir, first, "-l", "3", "--seed", "42", "--max-injections", "2") == 0
    assert _cli(contract_dir, second, "-l", "3", "--seed", "42", "--max-injections", "2") == 0

    for name in ("Counter", "SimpleERC20", "SimpleAuction", "EscrowVault"):
        assert (first / "L3" / f"{name}.sol").read_bytes() == (second / "L3" / f"{name}.sol").read_bytes()


def test_single_file_mode_writes_lf_utf8(tmp_path, contract_dir):
    destination = tmp_path / "Counter_L3.sol"
    assert _cli(contract_dir / "Counter.sol", destination, "-l", "3") == 0

    data = destination.read_bytes()
    assert b"\r" not in data
    text = data.decode("utf-8")
    assert "pragma solidity ^0.8.20;" in text
    assert "if (" in text  # control-flow injection happened


def test_output_directory_layout_for_a_directory_input(tmp_path, contract_dir):
    output = tmp_path / "out"
    assert _cli(contract_dir, output, "-l", "2", "--seed", "1") == 0
    assert sorted(path.name for path in (output / "L2").glob("*.sol")) == [
        "Counter.sol",
        "EscrowVault.sol",
        "SimpleAuction.sol",
        "SimpleERC20.sol",
    ]
    assert not (output / "L1").exists()


def test_level_and_all_levels_conflict_exits(tmp_path, contract_dir):
    with pytest.raises(SystemExit):
        _cli(contract_dir, tmp_path / "out", "-l", "1", "--all-levels")


def test_missing_level_exits(tmp_path, contract_dir):
    with pytest.raises(SystemExit):
        _cli(contract_dir, tmp_path / "out")


def test_missing_input_reports_error(tmp_path, capsys):
    code = _cli(tmp_path / "does-not-exist", tmp_path / "out", "-l", "1")
    assert code == 2
    assert "ERROR" in capsys.readouterr().err
