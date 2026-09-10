"""Tests for the user-provided 2-bar pattern: arrangements/song_02.pattern.

Right hand: eight sixteenth-note melody notes per bar, one every two
sixteenths (positions 1.1.1, 1.1.3, 1.2.1, ...). Left hand: two-octave
punchy hits on the beat subdivisions 1 only.
"""

from __future__ import annotations

from pathlib import Path

from mido import MidiFile

from midi_generator import MidiBuilder, note_to_midi, parse_pattern_file

PATTERN = Path(__file__).resolve().parent.parent / "arrangements" / "song_02.pattern"


def _pitch_starts(track) -> dict[str, list[float]]:
    starts: dict[str, list[float]] = {}
    for n in track.notes:
        starts.setdefault(n.pitch, []).append(n.start_beats)
    return {p: sorted(s) for p, s in starts.items()}


def test_user_pattern_rh_melody_positions() -> None:
    parsed = parse_pattern_file(PATTERN)
    (track,) = parsed.tracks
    assert track.name == "Piano"

    starts = _pitch_starts(track)
    # Bar 1 should be 0.25-beat-spaced sixteenths across the whole bar.
    assert starts["C5"] == [0.0, 1.0, 2.5, 4.0, 6.0, 7.5]
    assert starts["A4"] == [0.5, 3.0, 6.5]
    assert starts["F5"] == [1.5]
    assert starts["E5"] == [2.0, 4.5, 5.5]
    assert starts["D5"] == [3.5, 7.0]
    assert starts["G5"] == [5.0]

    melody = [n for n in track.notes if (n.pitch, n.velocity) in
              (("C5", 100), ("A4", 100), ("F5", 100), ("E5", 100),
               ("D5", 100), ("G5", 100))]
    assert sorted(n.start_beats for n in melody) == [0.0, 0.5, 1.0, 1.5, 2.0, 2.5,
                                                     3.0, 3.5, 4.0, 4.5, 5.0, 5.5,
                                                     6.0, 6.5, 7.0, 7.5]


def test_user_pattern_lh_two_octave_hits() -> None:
    parsed = parse_pattern_file(PATTERN)
    (track,) = parsed.tracks

    lh = [n for n in track.notes if n.velocity == 90]
    assert len(lh) == 16  # 8 hits per bar x 2 octaves
    assert all(n.duration_beats == 0.25 for n in lh)

    starts = _pitch_starts(track)
    # F1 and F2 always start together (chord).
    assert starts["F1"] == [0.0, 1.0, 3.0]
    assert starts["F2"] == [0.0, 1.0, 3.0]
    assert starts["D1"] == [2.0]
    assert starts["D2"] == [2.0]
    assert starts["A1"] == [4.0, 5.0]
    assert starts["A2"] == [4.0, 5.0]
    assert starts["E1"] == [6.0, 7.0]
    assert starts["E2"] == [6.0, 7.0]

    # All left-hand hits land on beat subdivision 1 (int .0 beat positions).
    assert all(n.start_beats == int(n.start_beats) for n in lh)


def test_user_pattern_generates_expected_midi(tmp_path: Path) -> None:
    parsed = parse_pattern_file(PATTERN)
    builder = MidiBuilder(tempo=parsed.tempo, time_signature=parsed.time_signature)
    out = tmp_path / "user_test.mid"
    builder.build(parsed.track_notes()["Piano"], output_path=out, track_name="Piano")

    midi = MidiFile(out)
    assert midi.type == 1
    assert midi.ticks_per_beat == 480
    (track,) = midi.tracks

    assert next(x.tempo for x in track if x.type == "set_tempo") == 500_000  # 120 BPM
    sig = next(x for x in track if x.type == "time_signature")
    assert (sig.numerator, sig.denominator) == (4, 4)

    ons = [m for m in track if m.type == "note_on" and m.velocity > 0]
    offs = [m for m in track if m.type == "note_off"]
    assert len(ons) == 32  # 16 melody + 16 bass
    assert len(offs) == 32

    assert {m.note for m in ons} == {note_to_midi(p) for p in
                                     ["C5", "A4", "F5", "E5", "D5", "G5",
                                      "F1", "F2", "D1", "D2", "A1", "A2", "E1", "E2"]}
    assert len({m.velocity for m in ons}) == 2  # 100 RH, 90 LH