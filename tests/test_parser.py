"""Tests for the human-readable pattern language parser."""

from __future__ import annotations

from pathlib import Path

import pytest
from mido import MidiFile

from midi_generator import (
    MidiBuilder,
    PatternError,
    parse_pattern,
    parse_pattern_file,
)
from midi_generator.midi_builder import NoteEvent
from midi_generator.note import note_to_midi
from midi_generator.patterns import logic_test_pattern

PIANO_PATTERN = """\
TEMPO 120
TIME 4/4

TRACK Piano

BAR 1
1.1: F1 + A3
1.2: C4
1.3: D4
1.4: A3

BAR 2
2.1: F1 + C4
2.2: A3
2.3: D4
2.4: C4
"""


def _parse_error(text: str) -> PatternError:
    try:
        parse_pattern(text)
    except PatternError as exc:
        return exc
    raise AssertionError(f"Expected PatternError for:\n{text}")


# --- headers -------------------------------------------------------------

def test_tempo_and_time_signature() -> None:
    parsed = parse_pattern("TEMPO 90\nTIME 3/4\n")
    assert parsed.tempo.bpm == 90
    assert parsed.time_signature.numerator == 3
    assert parsed.time_signature.denominator == 4


def test_defaults_when_no_headers() -> None:
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: C4\n")
    assert parsed.tempo.bpm == 120
    assert parsed.time_signature.numerator == 4
    assert parsed.time_signature.denominator == 4


# --- notes, chords, modifiers --------------------------------------------

def test_single_note_position_and_defaults() -> None:
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: C4\n")
    (note,) = parsed.tracks[0].notes
    assert note.pitch == "C4"
    assert note.start_beats == 0.0
    assert note.duration_beats == 1.0  # default 1/4 = one beat
    assert note.velocity == 100


def test_chord_is_simultaneous_same_start() -> None:
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: F1 + A3 + C4\n")
    notes = parsed.tracks[0].notes
    assert [n.pitch for n in notes] == ["F1", "A3", "C4"]
    assert len({n.start_beats for n in notes}) == 1


def test_velocity_modifier() -> None:
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: F1 velocity=100\n1.2: F1 velocity=12\n")
    assert [n.velocity for n in parsed.tracks[0].notes] == [100, 12]


def test_duration_modifier() -> None:
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: F1 duration=1/16\n")
    (note,) = parsed.tracks[0].notes
    assert note.duration_beats == 0.25  # 1/16 of a whole note in 4/4


def test_dotted_duration() -> None:
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: C4 duration=1/4.\n")
    (note,) = parsed.tracks[0].notes
    assert note.duration_beats == 1.5  # dotted quarter


def test_velocity_and_duration_together() -> None:
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: F1 velocity=100 duration=1/16\n")
    (note,) = parsed.tracks[0].notes
    assert note.velocity == 100
    assert note.duration_beats == 0.25


def test_duration_applies_to_whole_chord() -> None:
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: C4 + E4 + G4 duration=1/8 velocity=90\n")
    for note in parsed.tracks[0].notes:
        assert note.duration_beats == 0.5
        assert note.velocity == 90


def test_modifiers_can_precede_note() -> None:
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: duration=1/4 velocity=80 C4\n")
    (note,) = parsed.tracks[0].notes
    assert note.pitch == "C4"
    assert note.duration_beats == 1.0
    assert note.velocity == 80


def test_position_across_bars() -> None:
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: C4\n1.4: C4\nBAR 2\n2.1: C4\n2.2: C4\n")
    starts = [n.start_beats for n in parsed.tracks[0].notes]
    assert starts == [0.0, 3.0, 4.0, 5.0]


# --- octave convention pass-through --------------------------------------

def test_logic_octave_passthrough() -> None:
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: F1 + A3\n1.2: C4\n1.3: D4\n")
    pitches = {n.pitch: note_to_midi(n.pitch) for n in parsed.tracks[0].notes}
    assert pitches == {"F1": 41, "A3": 69, "C4": 72, "D4": 74}


def test_sharps_and_flats() -> None:
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: C#4 + Db5\n")
    notes = parsed.tracks[0].notes
    assert [note_to_midi(n.pitch) for n in notes] == [73, 85]


# --- tracks --------------------------------------------------------------

def test_multiple_tracks_in_definition_order() -> None:
    text = "TRACK Bass\nBAR 1\n1.1: F1\nTRACK Chords\nBAR 1\n1.1: A3\n"
    parsed = parse_pattern(text)
    assert [t.name for t in parsed.tracks] == ["Bass", "Chords"]
    assert note_to_midi(parsed.tracks[0].notes[0].pitch) == 41
    assert note_to_midi(parsed.tracks[1].notes[0].pitch) == 69


def test_track_notes_dict() -> None:
    parsed = parse_pattern("TRACK Bass\nBAR 1\n1.1: F1\nTRACK Melody\nBAR 1\n1.1: D4\n")
    notes = parsed.track_notes()
    assert list(notes) == ["Bass", "Melody"]
    assert note_to_midi(notes["Bass"][0].pitch) == 41
    assert note_to_midi(notes["Melody"][0].pitch) == 74


# --- errors --------------------------------------------------------------

def test_error_note_line_before_track() -> None:
    err = _parse_error("1.1: C4\n")
    assert err.line == 1


def test_error_note_line_before_bar() -> None:
    err = _parse_error("TRACK T\n1.1: C4\n")
    assert err.line == 2


def test_error_bar_before_track() -> None:
    err = _parse_error("BAR 1\n")
    assert err.line == 1


def test_error_invalid_tempo() -> None:
    err = _parse_error("TEMPO abc\n")
    assert err.line == 1


def test_error_invalid_time_signature() -> None:
    err = _parse_error("TIME 4x4\n")
    assert err.line == 1


def test_error_beat_out_of_range() -> None:
    err = _parse_error("TRACK T\nBAR 1\n1.5: C4\n")
    assert err.line == 3
    assert "outside the 1..4 range" in err.message


def test_error_bar_mismatch() -> None:
    err = _parse_error("TRACK T\nBAR 1\n2.1: C4\n")
    assert err.line == 3


def test_error_invalid_note_name() -> None:
    err = _parse_error("TRACK T\nBAR 1\n1.1: H4\n")
    assert err.line == 3


def test_error_empty_chord_member() -> None:
    err = _parse_error("TRACK T\nBAR 1\n1.1: C4 +\n")
    assert err.line == 3


def test_error_velocity_out_of_range() -> None:
    err = _parse_error("TRACK T\nBAR 1\n1.1: C4 velocity=200\n")
    assert err.line == 3


def test_error_duplicate_velocity() -> None:
    err = _parse_error("TRACK T\nBAR 1\n1.1: C4 velocity=1 velocity=2\n")
    assert err.line == 3


def test_error_invalid_duration() -> None:
    err = _parse_error("TRACK T\nBAR 1\n1.1: C4 duration=1/3\n")
    assert err.line == 3
    assert "Unsupported duration" in err.message


def test_error_non_decreasing_bar() -> None:
    err = _parse_error("TRACK T\nBAR 2\n2.1: C4\nBAR 1\n1.1: C4\n")
    assert err.line == 4


def test_error_duplicate_track() -> None:
    err = _parse_error("TRACK T\nTRACK T\n")
    assert err.line == 2


# --- end-to-end ----------------------------------------------------------

def test_error_conflicting_note_same_position_same_pitch() -> None:
    err = _parse_error("TRACK T\nBAR 1\n1.1: C4\n1.1: C4\n")
    assert err.line == 4
    assert "Conflicting note C4 at position 1.1" in err.message
    assert "line 3" in err.message


def test_error_duplicate_pitch_in_same_chord() -> None:
    err = _parse_error("TRACK T\nBAR 1\n1.1: C4 + C4\n")
    assert err.line == 3
    assert "Duplicate note C4" in err.message


def test_same_pitch_at_different_positions_is_allowed() -> None:
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: C4\n1.2: C4\n")
    (track,) = parsed.tracks
    assert len(track.notes) == 2


def test_file_error_includes_source_path(tmp_path: Path) -> None:
    path = tmp_path / "arr.pattern"
    path.write_text("TRACK T\nBAR 1\n1.1: H4\n")
    with pytest.raises(PatternError) as exc_info:
        parse_pattern_file(path)
    assert str(exc_info.value) == f"{path}: Line 3: Invalid note name 'H4'"
    assert exc_info.value.source == str(path)


def test_piano_pattern_builds_midi(tmp_path: Path) -> None:
    parsed = parse_pattern(PIANO_PATTERN)
    builder = MidiBuilder(tempo=parsed.tempo, time_signature=parsed.time_signature)
    out = tmp_path / "piano.mid"
    builder.build(parsed.track_notes()["Piano"], output_path=out, track_name="Piano")

    midi = MidiFile(out)
    (track,) = midi.tracks
    ons = [m for m in track if m.type == "note_on" and m.velocity > 0]
    pitches = sorted({m.note for m in ons})
    assert pitches == [41, 69, 72, 74]  # F1 A3 C4 D4 under Logic convention


def test_logic_test_pattern_recreates_python_pattern() -> None:
    parsed = parse_pattern_file(Path(__file__).resolve().parent.parent / "arrangements" / "logic_test.pattern")
    (track,) = parsed.tracks
    assert track.name == "Logic Test"
    assert [n.pitch for n in track.notes] == [n.pitch for n in logic_test_pattern()]
    assert [n.start_beats for n in track.notes] == [n.start_beats for n in logic_test_pattern()]
    assert [n.duration_beats for n in track.notes] == [n.duration_beats for n in logic_test_pattern()]
    assert [n.velocity for n in track.notes] == [n.velocity for n in logic_test_pattern()]


def test_multi_track_pattern_builds_type1_with_two_tracks(tmp_path: Path) -> None:
    path = Path(__file__).resolve().parent.parent / "arrangements" / "two_instruments.pattern"
    parsed = parse_pattern_file(path)
    builder = MidiBuilder(tempo=parsed.tempo, time_signature=parsed.time_signature)
    out = tmp_path / "two.mid"
    midi = builder.build_multi_track(parsed.track_notes(), output_path=out)

    assert midi.type == 1
    assert [t.name for t in parsed.tracks] == ["Bass", "Chords"]
    names = [m for t in midi.tracks for m in t if m.type == "track_name"]
    assert [m.name for m in names] == ["Bass", "Chords"]
    for track, (name, notes) in zip(midi.tracks, parsed.track_notes().items()):
        ons = [m for m in track if m.type == "note_on" and m.velocity > 0]
        assert len(ons) == len(notes)
    MidiFile(str(out))  # reloadable


def test_parser_uses_existing_note_to_midi() -> None:
    assert note_to_midi("C4") == 72
    parsed = parse_pattern("TRACK T\nBAR 1\n1.1: C4\n")
    assert parsed.tracks[0].notes[0].pitch == "C4"
    # A raw int pitch is convertible, confirming the converter is the same one.
    assert note_to_midi(parsed.tracks[0].notes[0].pitch) == 72