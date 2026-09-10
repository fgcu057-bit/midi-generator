"""Tests for the stable command-line authoring workflow.

The canonical workflow is:

    python generate.py arrangements/<name>.pattern   -> output/<name>.mid

These tests drive generate.py as a subprocess so they exercise the real CLI.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run_cli(*args: str, cwd: Path = PROJECT_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "generate.py", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def test_arrangement_file_produces_stem_named_output(tmp_path: Path) -> None:
    out = PROJECT_ROOT / "output" / "example.mid"
    result = _run_cli("arrangements/example.pattern")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Wrote output/example.mid"
    assert out.is_file()

    from mido import MidiFile

    midi = MidiFile(out)
    assert midi.type == 1
    (track,) = midi.tracks
    ons = [m for m in track if m.type == "note_on" and m.velocity > 0]
    assert len(ons) == 10  # two-bar piano: 10 notes (both bars, incl. F1+A3 chord)


def test_arrangement_output_name_derives_from_input(tmp_path: Path) -> None:
    out = PROJECT_ROOT / "output" / "piano_intro.mid"
    result = _run_cli("arrangements/piano_intro.pattern")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Wrote output/piano_intro.mid"
    assert out.is_file()


def test_output_override_flag(tmp_path: Path) -> None:
    out = tmp_path / "custom_name.mid"
    derived = PROJECT_ROOT / "output" / "song_01.mid"
    derived.unlink(missing_ok=True)
    result = _run_cli(
        "arrangements/song_01.pattern",
        "-o",
        str(out),
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert out.is_file()
    assert not derived.exists()


def test_missing_arrangement_is_a_clean_error() -> None:
    result = _run_cli("arrangements/does_not_exist.pattern")
    assert result.returncode == 1
    assert "Arrangement file not found" in result.stderr


def test_invalid_arrangement_reports_file_and_line(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pattern"
    bad.write_text(
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK Piano\n"
        "BAR 1\n"
        "1.1: C4\n"
        "BAR 2\n"
        "2.1: H4\n"
    )
    result = _run_cli(str(bad), cwd=PROJECT_ROOT)
    assert result.returncode == 1
    assert f"{bad}: Line 7" in result.stderr
    assert "Invalid note name" in result.stderr


def test_invalid_duration_reports_file_and_line(tmp_path: Path) -> None:
    bad = tmp_path / "bad_duration.pattern"
    bad.write_text(
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK Piano\n"
        "BAR 1\n"
        "1.1: C4 duration=1/7\n"
    )
    result = _run_cli(str(bad), cwd=PROJECT_ROOT)
    assert result.returncode == 1
    assert f"{bad}: Line 5" in result.stderr
    assert "duration" in result.stderr.lower()


def test_invalid_velocity_reports_file_and_line(tmp_path: Path) -> None:
    bad = tmp_path / "bad_velocity.pattern"
    bad.write_text(
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK Piano\n"
        "BAR 1\n"
        "1.1: C4 velocity=300\n"
    )
    result = _run_cli(str(bad), cwd=PROJECT_ROOT)
    assert result.returncode == 1
    assert f"{bad}: Line 5" in result.stderr
    assert "Velocity" in result.stderr


def test_invalid_position_reports_file_and_line(tmp_path: Path) -> None:
    bad = tmp_path / "bad_position.pattern"
    bad.write_text(
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK Piano\n"
        "BAR 1\n"
        "1.5: C4\n"
    )
    result = _run_cli(str(bad), cwd=PROJECT_ROOT)
    assert result.returncode == 1
    assert f"{bad}: Line 5" in result.stderr


def test_conflicting_note_reports_file_and_line(tmp_path: Path) -> None:
    bad = tmp_path / "bad_conflict.pattern"
    bad.write_text(
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK Piano\n"
        "BAR 1\n"
        "1.1: C4\n"
        "1.1: C4\n"
    )
    result = _run_cli(str(bad), cwd=PROJECT_ROOT)
    assert result.returncode == 1
    assert f"{bad}: Line 6" in result.stderr
    assert "Conflicting note" in result.stderr


def test_multi_track_arrangement_builds_type1(tmp_path: Path) -> None:
    out = PROJECT_ROOT / "output" / "two_instruments.mid"
    result = _run_cli("arrangements/two_instruments.pattern")
    assert result.returncode == 0, result.stderr
    assert out.is_file()

    from mido import MidiFile

    midi = MidiFile(out)
    assert midi.type == 1
    names = [m.name for t in midi.tracks for m in t if m.type == "track_name"]
    assert names == ["Bass", "Chords"]