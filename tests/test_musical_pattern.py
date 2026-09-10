"""Tests for the real-music example: arrangements/song_01.pattern.

Covers only the behavior the musical pattern actually exercises:
sub-beat sixteenth positions, sustained bass, simultaneous chords,
varied velocities/durations, and clean generation.
"""

from __future__ import annotations

from pathlib import Path

from mido import MidiFile

from midi_generator import MidiBuilder, note_to_midi, parse_pattern_file

PATTERN = Path(__file__).resolve().parent.parent / "arrangements" / "song_01.pattern"


def _starts(track) -> dict[str, list[float]]:
    starts: dict[str, list[float]] = {}
    for n in track.notes:
        starts.setdefault(n.pitch, []).append(n.start_beats)
    return {p: sorted(s) for p, s in starts.items()}


def test_event_count_in_musical_order() -> None:
    parsed = parse_pattern_file(PATTERN)
    (track,) = parsed.tracks
    assert track.name == "Piano"
    assert len(track.notes) == 58
    assert min(n.start_beats for n in track.notes) == 0.0
    assert max(n.start_beats for n in track.notes) == 15.0


def test_sixteenth_sub_positions_quarter_beat_apart() -> None:
    parsed = parse_pattern_file(PATTERN)
    starts = _starts(parsed.tracks[0])

    # Melody runs at bar.beat.sub granularity (0.25 beat = one sixteenth).
    # Bar 1: E5 at 1.1, D5 at 1.1.2, C5 at 1.1.3 -> 0, 0.25, 0.5.
    assert starts["D5"] == [0.25, 10.5, 11.25, 12.0, 15.0]
    assert starts["C5"] == [0.5, 3.0, 4.0, 11.0]
    # Bar 4: D5 4.1, B4 4.1.3, A4 4.2, G4 4.2.3 -> 12.0, 12.5, 13.0, 13.5.
    assert starts["B4"] == [1.0, 4.25, 12.5, 14.0]
    assert starts["G4"] == [0.0, 13.5, 14.0]


def test_sustained_bass_and_lower_register_movement() -> None:
    parsed = parse_pattern_file(PATTERN)
    by_pitch = {n.pitch: n for n in parsed.tracks[0].notes}

    assert by_pitch["C2"].start_beats == 0.0  # bar 1.1
    assert by_pitch["C2"].duration_beats == 4.0  # 1/1 whole note
    assert by_pitch["A1"].start_beats == 4.0  # bar 2.1
    assert by_pitch["A1"].duration_beats == 4.0
    assert by_pitch["F2"].start_beats == 8.0  # bar 3.1
    assert by_pitch["F2"].duration_beats == 4.0
    # Bar 4 bass moves twice within the bar.
    assert by_pitch["G1"].start_beats == 12.0
    assert by_pitch["G1"].duration_beats == 2.0
    assert by_pitch["G2"].start_beats == 14.0


def test_chords_are_simultaneous_and_use_varied_velocities() -> None:
    parsed = parse_pattern_file(PATTERN)
    (track,) = parsed.tracks

    at_zero = {n.pitch for n in track.notes if n.start_beats == 0.0}
    assert {"C4", "E4", "G4"}.issubset(at_zero)  # C major, bar 1 beat 1

    at_4 = {n.pitch for n in track.notes if n.start_beats == 4.0}
    assert {"A1", "A3", "C4", "E4", "C5"}.issubset(at_4)  # Am bar 2, beat 1

    chord_hits = [n for n in track.notes if n.pitch == "F3"]  # bar 3 comping
    assert len(chord_hits) == 4
    assert [c.start_beats for c in chord_hits] == [8.0, 9.0, 10.0, 11.0]
    assert [c.duration_beats for c in chord_hits] == [1.0, 0.5, 1.0, 0.5]  # 1/4, 1/8, 1/4, 1/8


def test_velocities_and_durations_varied() -> None:
    parsed = parse_pattern_file(PATTERN)
    (track,) = parsed.tracks
    velocities = {n.velocity for n in track.notes}
    durations = {n.duration_beats for n in track.notes}
    assert len(velocities) >= 7
    assert {78, 84, 92, 100, 108}.issubset(velocities)
    assert durations == {0.25, 0.5, 1.0, 2.0, 4.0}  # 1/16, 1/8, 1/4, 1/2, 1/1


def test_generates_valid_midi_with_expected_pitches(tmp_path: Path) -> None:
    parsed = parse_pattern_file(PATTERN)
    builder = MidiBuilder(tempo=parsed.tempo, time_signature=parsed.time_signature)
    out = tmp_path / "musical_test.mid"
    builder.build(parsed.track_notes()["Piano"], output_path=out, track_name="Piano")

    midi = MidiFile(out)
    assert midi.type == 1
    (track,) = midi.tracks
    tempos = [m for m in track if m.type == "set_tempo"]
    sigs = [m for m in track if m.type == "time_signature"]
    assert tempos[0].tempo == 500_000  # 120 BPM
    assert sigs[0].numerator == 4 and sigs[0].denominator == 4

    ons = [m for m in track if m.type == "note_on" and m.velocity > 0]
    offs = [m for m in track if m.type == "note_off"]
    assert len(ons) == 58
    assert len(offs) == 58

    names = ["C2", "C4", "E4", "G4", "G3", "E5", "D5", "C5", "B4", "A1",
             "A3", "E3", "A4", "F2", "F3", "F5", "G1", "G2", "B3", "D4"]
    assert {m.note for m in ons} == {note_to_midi(n) for n in names}

    # Sub-beat sixteenth lands on tick 120 (0.25 beat * 480 PPQ).
    running = 0
    sixteenth_tick: int | None = None
    for msg in track:
        running += msg.time
        if msg.type == "note_on" and msg.velocity > 0 and msg.note == note_to_midi("D5") and running == 120:
            sixteenth_tick = running
    assert sixteenth_tick == 120