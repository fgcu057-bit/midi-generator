"""Tests for the MIDI generator.

Requires ``pytest`` and ``mido``.
"""

from __future__ import annotations

from pathlib import Path

from mido import MidiFile

from midi_generator import MidiBuilder, Tempo, midi_to_note, note_to_midi
from midi_generator.midi_builder import TimeSignature, NoteEvent
from midi_generator.patterns import four_bar_example


def _note_on_ticks(midi: MidiFile, pitch: int) -> list[int]:
    ticks: list[int] = []
    running = 0
    for msg in midi.tracks[0]:
        running += msg.time
        if msg.type == "note_on" and msg.velocity > 0 and msg.note == pitch:
            ticks.append(running)
    return ticks


def test_note_to_midi_conversion() -> None:
    assert note_to_midi("C4") == 72
    assert note_to_midi("C-2") == 0
    assert note_to_midi("G8") == 127
    assert note_to_midi("F1") == 41
    assert note_to_midi("A3") == 69
    assert note_to_midi("C3") == 60  # middle C, Logic convention
    assert note_to_midi("C#4") == 73
    assert note_to_midi("Db4") == 73


def test_midi_to_note_roundtrip() -> None:
    for pitch in range(0, 128):
        assert note_to_midi(midi_to_note(pitch)) == pitch


def test_invalid_note_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        note_to_midi("H4")
    with pytest.raises(ValueError):
        note_to_midi("C-3")  # below MIDI range (C-2 is MIDI 0, Logic convention)


def test_builds_valid_type_1_file(tmp_path: Path) -> None:
    out = tmp_path / "test.mid"
    builder = MidiBuilder(tempo=Tempo(bpm=120), time_signature=TimeSignature(4, 4))
    builder.build(four_bar_example(), output_path=out)

    assert out.exists()
    assert out.stat().st_size > 10

    midi = MidiFile(out)
    assert midi.type == 1
    assert len(midi.tracks) == 1


def test_four_bar_pattern_has_note_events() -> None:
    builder = MidiBuilder(tempo=Tempo(bpm=120))
    midi = builder.build(four_bar_example(), ticks_per_beat=480)

    note_ons = [m for m in midi.tracks[0] if m.type == "note_on" and m.velocity > 0]
    note_offs = [m for m in midi.tracks[0] if m.type == "note_off"]

    assert len(note_ons) >= 1
    assert len(note_offs) == len(note_ons)


def test_tempo_and_time_signature_markers() -> None:
    builder = MidiBuilder(tempo=Tempo(bpm=100), time_signature=TimeSignature(3, 4))
    midi = builder.build([NoteEvent("C4", 0, 1)])

    tempos = [m for m in midi.tracks[0] if m.type == "set_tempo"]
    signatures = [m for m in midi.tracks[0] if m.type == "time_signature"]

    assert tempos[0].tempo == round(60_000_000 / 100)
    assert signatures[0].numerator == 3
    assert signatures[0].denominator == 4


def test_chord_notes_start_at_same_position() -> None:
    builder = MidiBuilder()
    midi = builder.build([
        NoteEvent("C4", 0, 2, 100),
        NoteEvent("E4", 0, 2, 100),
        NoteEvent("G4", 0, 2, 100),
    ])
    # The three note_ons all occur at tick 0.
    running = 0
    starts = []
    for msg in midi.tracks[0]:
        running += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            starts.append(running)
    assert starts == [0, 0, 0]


def test_generation_end_to_end(tmp_path: Path) -> None:
    src = Path(__file__).resolve().parent.parent / "generate.py"
    out = tmp_path / "example.mid"
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(src), "--output", str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    MidiFile(str(out))  # reloadable without error