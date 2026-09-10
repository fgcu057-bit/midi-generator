"""Mathematical verification of the Logic-import test MIDI file.

Rebuilds the *exact* expected event stream (absolute tick, type, note,
velocity) from the pattern data using straightforward beat arithmetic, then
asserts the real file matches it event-for-event.
"""

from __future__ import annotations

from pathlib import Path

from mido import MidiFile

from midi_generator import MidiBuilder, Tempo
from midi_generator.midi_builder import TimeSignature, NoteEvent
from midi_generator.patterns import LOGIC_TEST_TRACK_NAME, logic_test_pattern

RESOLUTION = 480  # ticks per beat
BEATS_PER_BAR = 4
BARS = 4


def _beats_to_ticks(beats: float) -> int:
    return round(beats * RESOLUTION)


def _expected_note_events() -> list[tuple[int, str, int, int]]:
    """The mathematically expected note_on/note_off stream from the pattern."""
    events: list[tuple[int, str, int, int]] = []
    for n in logic_test_pattern():
        midi_pitch = n.pitch if isinstance(n.pitch, int) else _pitch(n.pitch)
        on = _beats_to_ticks(n.start_beats)
        off = _beats_to_ticks(n.start_beats + n.duration_beats)
        events.append((on, "note_on", midi_pitch, n.velocity))
        events.append((off, "note_off", midi_pitch, 0))
    # note_off orders before note_on at the same tick (matches the builder).
    return sorted(events, key=lambda e: (e[0], 0 if e[1] == "note_off" else 1))


def _pitch(name: str) -> int:
    from midi_generator import note_to_midi

    return note_to_midi(name)


def _actual_note_events(midi: MidiFile) -> list[tuple[int, str, int, int]]:
    result: list[tuple[int, str, int, int]] = []
    tick = 0
    for msg in midi.tracks[0]:
        tick += msg.time
        if msg.type in ("note_on", "note_off"):
            result.append((tick, msg.type, msg.note, msg.velocity))
    return result


def test_logic_test_file_structure(tmp_path: Path) -> None:
    out = tmp_path / "logic_test.mid"
    midi = MidiBuilder(
        tempo=Tempo(bpm=120),
        time_signature=TimeSignature(4, 4),
    ).build(logic_test_pattern(), ticks_per_beat=RESOLUTION, output_path=out,
            track_name=LOGIC_TEST_TRACK_NAME)

    assert midi.type == 1
    assert midi.ticks_per_beat == RESOLUTION
    assert len(midi.tracks) == 1

    track = midi.tracks[0]
    names = [m for m in track if m.type == "track_name"]
    tempos = [m for m in track if m.type == "set_tempo"]
    sigs = [m for m in track if m.type == "time_signature"]

    assert names[0].name == "Logic Test"
    assert tempos[0].tempo == 500_000  # 120 BPM
    assert sigs[0].numerator == 4
    assert sigs[0].denominator == 4

    total_ticks = sum(m.time for m in track)
    assert total_ticks == _beats_to_ticks(BEATS_PER_BAR * BARS) + RESOLUTION


def test_logic_test_track_runs_exactly_4_bars(tmp_path: Path) -> None:
    midi = MidiBuilder(tempo=Tempo(bpm=120)).build(
        logic_test_pattern(), ticks_per_beat=RESOLUTION
    )
    total_ticks = sum(m.time for m in midi.tracks[0])
    assert total_ticks == (BEATS_PER_BAR * BARS * RESOLUTION) + RESOLUTION


def test_logic_test_exact_event_stream(tmp_path: Path) -> None:
    midi = MidiBuilder(
        tempo=Tempo(bpm=120),
        time_signature=TimeSignature(4, 4),
    ).build(logic_test_pattern(), ticks_per_beat=RESOLUTION)

    expected = _expected_note_events()
    actual = _actual_note_events(midi)

    assert len(actual) == len(expected)
    for i, (exp, act) in enumerate(zip(expected, actual)):
        assert act == exp, f"Event {i} mismatch.\nExpected: {exp}\nActual:   {act}"


def test_logic_test_bar1_literal_events(tmp_path: Path) -> None:
    """Hard-coded bar 1 to make the chord/sustain layout unambiguous."""
    midi = MidiBuilder().build(logic_test_pattern(), ticks_per_beat=RESOLUTION)
    actual = _actual_note_events(midi)

    expected_bar1 = [
        # Beat 1 (tick 0): sustained C1 (36), plus C major chord, vel 100
        (0, "note_on", 36, 90),
        (0, "note_on", 72, 100),
        (0, "note_on", 76, 100),
        (0, "note_on", 79, 100),
        # Beat 2 (tick 480): chord releases
        (480, "note_off", 72, 0),
        (480, "note_off", 76, 0),
        (480, "note_off", 79, 0),
        # Beat 3 (tick 960): same chord, but velocity 95
        (960, "note_on", 72, 95),
        (960, "note_on", 76, 95),
        (960, "note_on", 79, 95),
        # Beat 4 (tick 1440): chord releases again
        (1440, "note_off", 72, 0),
        (1440, "note_off", 76, 0),
        (1440, "note_off", 79, 0),
        # Bar 2 downbeat (tick 1920): the sustained C1 finally releases
        (1920, "note_off", 36, 0),
    ]
    assert actual[: len(expected_bar1)] == expected_bar1


def test_logic_test_has_required_features(tmp_path: Path) -> None:
    """The file must contain chords, a sustained note, and varied velocities."""
    midi = MidiBuilder().build(logic_test_pattern(), ticks_per_beat=RESOLUTION)
    actual = _actual_note_events(midi)
    ons = [(t, n, v) for t, kind, n, v in actual if kind == "note_on"]

    # Sustained note: C1 (36) 4 beats and A1 (45) 4 beats.
    c1 = [e for e in actual if e[2] == 36]
    a1 = [e for e in actual if e[2] == 45]
    assert (c1[0][0], c1[1][0] - c1[0][0]) == (0, 1920)  # 4 beats long
    assert (a1[0][0], a1[1][0] - a1[0][0]) == (5760, 1920)

    # Chord: three different pitches all starting at tick 0.
    at_zero = {(n, v) for t, kind, n, v in actual if kind == "note_on" and t == 0}
    assert len(at_zero) == 4  # C1 + C/E/G
    zero_pitches = {n for t, n, v in ons if t == 0}
    assert {72, 76, 79}.issubset(zero_pitches)  # C4 E4 G4

    # Different velocities present.
    velocities = {v for t, n, v in ons}
    assert {85, 90, 95, 100, 110}.issubset(velocities)

    # Notes on every downbeat of each bar (ticks 0, 1920, 3840, 5760).
    downbeat_ticks = {t for t, n, v in ons if t % (RESOLUTION * BEATS_PER_BAR) == 0}
    assert downbeat_ticks == {0, 1920, 3840, 5760}

    # Bar 3 melody is four quarter notes on beats 1-4 (ticks 3840..5280).
    melody = {t for t, n, v in ons if t in {3840, 4320, 4800, 5280}}
    assert melody == {3840, 4320, 4800, 5280}