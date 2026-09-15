import pytest
from pathlib import Path
from midi_generator.parser import parse_pattern, PatternError
from midi_generator.midi_builder import MidiBuilder
from mido import MidiFile

def test_canonical_vs_shorthand_equivalence():
    """Prove that canonical and shorthand syntaxes produce byte-equivalent MIDI."""
    canonical_text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK Test\n"
        "BAR 1\n"
        "1.1: A#4 duration=1/4\n"
        "1.3: G#4 duration=1/4\n"
        "BAR 2\n"
        "2.1: F4 duration=1/4\n"
        "2.3: G4 duration=1/4\n"
    )
    shorthand_text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK Test\n"
        "BAR 1\n"
        "A#4 1.1 1/4\n"
        "G#4 1.3 1/4\n"
        "BAR 2\n"
        "F4 2.1 1/4\n"
        "G4 2.3 1/4\n"
    )

    p_can = parse_pattern(canonical_text)
    p_sh = parse_pattern(shorthand_text)
    
    # Check internal representation
    assert p_can.tracks[0].notes == p_sh.tracks[0].notes
    
    builder_can = MidiBuilder(p_can.tempo, p_can.time_signature)
    builder_sh = MidiBuilder(p_sh.tempo, p_sh.time_signature)
    
    midi_can = builder_can.build(p_can.track_notes()["Test"])
    midi_sh = builder_sh.build(p_sh.track_notes()["Test"])
    
    # Compare track contents
    assert list(midi_can.tracks[0]) == list(midi_sh.tracks[0])

def test_shorthand_positions():
    """Test bar.beat and bar.beat.subdivision positions in shorthand."""
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK Test\n"
        "BAR 1\n"
        "C4 1.1 1/4\n"
        "D4 1.1.2 1/16\n"
        "E4 1.2 1/8\n"
    )
    p = parse_pattern(text)
    notes = p.tracks[0].notes
    
    # 1.1 -> 0.0
    assert notes[0].start_beats == 0.0
    # 1.1.2 -> 0.25
    assert notes[1].start_beats == 0.25
    # 1.2 -> 1.0
    assert notes[2].start_beats == 1.0

def test_shorthand_duration_preservation():
    """Ensure durations are preserved exactly."""
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK Test\n"
        "BAR 1\n"
        "C4 1.1 1/1\n"
        "D4 1.2 1/2\n"
        "E4 1.3 1/4\n"
        "F4 1.4 1/8\n"
    )
    p = parse_pattern(text)
    notes = p.tracks[0].notes
    
    # duration_beats = duration * beats_per_bar (4)
    assert notes[0].duration_beats == 4.0
    assert notes[1].duration_beats == 2.0
    assert notes[2].duration_beats == 1.0
    assert notes[3].duration_beats == 0.5

def test_invalid_position_error():
    """Verify that invalid positions generate errors instead of truncation."""
    # Beat 5 in 4/4
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK Test\n"
        "BAR 1\n"
        "C4 1.5 1/4\n"
    )
    with pytest.raises(PatternError) as exc:
        parse_pattern(text)
    assert "Beat 5 is outside the 1..4 range" in str(exc.value)

def test_large_scale_pattern():
    """Test 100+ bars work correctly."""
    lines = ["TEMPO 120", "TIME 4/4", "TRACK Test"]
    for b in range(1, 102):
        lines.append(f"BAR {b}")
        lines.append(f"C4 {b}.1 1/4")
    
    p = parse_pattern("\n".join(lines))
    assert len(p.tracks[0].notes) == 101
    assert p.tracks[0].notes[-1].start_beats == 400.0 # Bar 101, beat 1

def test_notes_spanning_bars():
    """Verify notes spanning multiple bars work (long duration)."""
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK Test\n"
        "BAR 1\n"
        "C4 1.1 1/1\n" # 4 beats
        "BAR 2\n"
        "D4 2.1 1/4\n"
    )
    p = parse_pattern(text)
    notes = p.tracks[0].notes
    assert notes[0].duration_beats == 4.0
    assert notes[1].start_beats == 4.0

def test_exact_example_shorthand():
    """Test the specific example requested by the user."""
    text = (
        "TEMPO 109\n"
        "TIME 4/4\n"
        "TRACK BUILD HIGH PIANO\n"
        "BAR 1\n"
        "A#4 1.1 1/4\n"
        "G#4 1.3 1/4\n"
        "BAR 2\n"
        "F4 2.1 1/4\n"
        "G4 2.3 1/4\n"
        "BAR 3\n"
        "A#4 3.1 1/4\n"
        "G#4 3.3 1/4\n"
        "BAR 4\n"
        "F4 4.1 1/4\n"
    )
    p = parse_pattern(text)
    notes = p.tracks[0].notes
    
    assert len(notes) == 7
    expected_starts = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0] 
    
    actual_starts = [n.start_beats for n in notes]
    assert actual_starts == expected_starts
    for n in notes:
        assert n.duration_beats == 1.0

def test_exact_example_midi_contains_exactly_seven_notes(tmp_path):
    """The exact 7-note example must compile to a MIDI with exactly those notes."""
    shorthand = (
        "TEMPO 109\n"
        "TIME 4/4\n"
        "TRACK BUILD HIGH PIANO\n"
        "BAR 1\n"
        "A#4 1.1 1/4\n"
        "G#4 1.3 1/4\n"
        "BAR 2\n"
        "F4 2.1 1/4\n"
        "G4 2.3 1/4\n"
        "BAR 3\n"
        "A#4 3.1 1/4\n"
        "G#4 3.3 1/4\n"
        "BAR 4\n"
        "F4 4.1 1/4\n"
    )
    p = parse_pattern(shorthand)
    notes = p.tracks[0].notes

    expected_pitches = ["A#4", "G#4", "F4", "G4", "A#4", "G#4", "F4"]
    expected_starts = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0]
    assert [n.pitch for n in notes] == expected_pitches
    assert [n.start_beats for n in notes] == expected_starts
    assert all(n.duration_beats == 1.0 for n in notes)

    builder = MidiBuilder(p.tempo, p.time_signature)
    out = tmp_path / "exact.mid"
    midi = builder.build(p.track_notes()["BUILD HIGH PIANO"], output_path=out, track_name="BUILD HIGH PIANO")

    (track,) = midi.tracks
    ons = [m for m in track if m.type == "note_on" and m.velocity > 0]
    offs = [m for m in track if m.type == "note_off"]
    assert len(ons) == 7
    assert len(offs) == 7
    MidiFile(str(out))  # reloadable

def test_beat_vs_subdivision_disambiguation():
    """bar.beat (1.3 = beat 3) must never be read as sixteenth bar.beat.subdivision."""
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK T\n"
        "BAR 1\n"
        "C4 1.1 1/4\n"
        "D4 1.2 1/4\n"
        "E4 1.3 1/4\n"
        "F4 1.4 1/4\n"
        "BAR 2\n"
        "G4 2.1.1 1/16\n"
        "A4 2.1.2 1/16\n"
        "B4 2.1.3 1/16\n"
        "C5 2.1.4 1/16\n"
    )
    notes = parse_pattern(text).tracks[0].notes
    # 1.1..1.4 -> beats 1..4 of bar 1: starts 0,1,2,3 (NOT subdivision 0.0,0.25,...)
    assert [(n.pitch, n.start_beats) for n in notes[:4]] == [
        ("C4", 0.0), ("D4", 1.0), ("E4", 2.0), ("F4", 3.0),
    ]
    # 2.1.1..2.1.4 -> bar 2, beat 1, sixteenths 1..4: starts 4.0, 4.25, 4.5, 4.75
    assert [(n.pitch, n.start_beats) for n in notes[4:]] == [
        ("G4", 4.0), ("A4", 4.25), ("B4", 4.5), ("C5", 4.75),
    ]
    assert all(n.duration_beats == 1.0 for n in notes[:4])
    assert all(n.duration_beats == 0.25 for n in notes[4:])

def test_shorthand_error_includes_position():
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK T\n"
        "BAR 1\n"
        "C4 1.5 1/4\n"
    )
    with pytest.raises(PatternError) as exc:
        parse_pattern(text)
    assert "Position 1.5" in str(exc.value)
    assert "Beat 5 is outside the 1..4 range" in str(exc.value)
    assert exc.value.line == 5

def test_shorthand_subdivision_out_of_range_error():
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK T\n"
        "BAR 1\n"
        "C4 1.1.5 1/16\n"
    )
    with pytest.raises(PatternError) as exc:
        parse_pattern(text)
    assert "Position 1.1.5" in str(exc.value)
    assert "outside the 1..4 range" in str(exc.value)
    assert exc.value.line == 5

def test_shorthand_two_part_mismatched_bar_is_bar_relative():
    """A two-part token whose bar number != active BAR is beat(.sixteenth):
    BAR 1 + 'G4 2.1 1/4' -> bar 1, beat 2, subdivision 1 (start 1.0)."""
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK T\n"
        "BAR 1\n"
        "G4 2.1 1/4\n"
    )
    (note,) = parse_pattern(text).tracks[0].notes
    assert note.pitch == "G4"
    assert note.start_beats == 1.0
    assert note.duration_beats == 1.0

def test_three_part_shorthand_bar_mismatch_still_errors():
    """Three-part tokens are absolute-only: a bar mismatch must still error."""
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK T\n"
        "BAR 9\n"
        "C4 3.1.2 1/16\n"
    )
    with pytest.raises(PatternError) as exc:
        parse_pattern(text)
    assert "Position bar 3 does not match the active BAR 9" in str(exc.value)
    assert exc.value.line == 5

def test_no_notes_silently_omitted():
    """Every note in a large shorthand pattern must reach the MIDI (nothing dropped)."""
    lines = ["TEMPO 120", "TIME 4/4", "TRACK T"]
    pitches = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]
    count = 0
    for b in range(1, 26):
        lines.append(f"BAR {b}")
        for beat in (1, 2, 3, 4):
            pitch = pitches[count % len(pitches)]
            lines.append(f"{pitch} {b}.{beat} 1/8")
            count += 1
    p = parse_pattern("\n".join(lines))
    assert len(p.tracks[0].notes) == count

    builder = MidiBuilder(p.tempo, p.time_signature)
    midi = builder.build(p.track_notes()["T"])
    (track,) = midi.tracks
    ons = [m for m in track if m.type == "note_on" and m.velocity > 0]
    assert len(ons) == count

# --------------------------------------------------------------------------
# BAR-relative shorthand: NOTE BEAT(.SIXTEENTH) DURATION under an active BAR
# --------------------------------------------------------------------------

BAR_RELATIVE_SIX_NOTE = """\
TEMPO 109
TIME 4/4

TRACK BUILD HIGH PIANO

BAR 9
F4 3.1 1/4
G4 3.3 1/4
F4 4.1 1/4

BAR 10
G4 1.1 1/4
F4 1.3 1/4
G4 2.1 1/4
"""

BAR_RELATIVE_SIX_NOTE_CANONICAL = """\
TEMPO 109
TIME 4/4

TRACK BUILD HIGH PIANO

BAR 9
9.3: F4 duration=1/4
9.3.3: G4 duration=1/4
9.4: F4 duration=1/4

BAR 10
10.1: G4 duration=1/4
10.1.3: F4 duration=1/4
10.2: G4 duration=1/4
"""

def test_bar_relative_beat_position():
    """BAR 9 + 'F4 3.1 1/4' -> absolute BAR 9, beat 3 (start 34.0)."""
    (note,) = parse_pattern("TEMPO 120\nTIME 4/4\nTRACK T\nBAR 9\nF4 3.1 1/4\n").tracks[0].notes
    assert note.pitch == "F4"
    assert note.start_beats == 34.0
    assert note.duration_beats == 1.0
    assert note.velocity == 100

def test_bar_relative_subdivision_position():
    """BAR 9 + 'G4 3.3 1/4' -> absolute BAR 9, beat 3, subdivision 3 (start 34.5)."""
    (note,) = parse_pattern("TEMPO 120\nTIME 4/4\nTRACK T\nBAR 9\nG4 3.3 1/4\n").tracks[0].notes
    assert note.start_beats == 34.5

def test_bar_relative_multiple_bars():
    """Positions under BAR 9/10/11 resolve to 9.x/10.x/11.x."""
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK T\n"
        "BAR 9\n"
        "C4 3.1 1/4\n"
        "BAR 10\n"
        "D4 1.1 1/4\n"
        "BAR 11\n"
        "E4 2.1 1/4\n"
    )
    notes = parse_pattern(text).tracks[0].notes
    assert [(n.pitch, n.start_beats) for n in notes] == [
        ("C4", 34.0),   # 9.3
        ("D4", 36.0),   # 10.1
        ("E4", 41.0),   # 11.2
    ]

def test_bar_relative_six_note_structure():
    """The exact musical structure must resolve to 9.3/9.3.3/9.4/10.1/10.1.3/10.2,
    and never to bars 1-4."""
    notes = parse_pattern(BAR_RELATIVE_SIX_NOTE).tracks[0].notes
    assert [n.start_beats for n in notes] == [34.0, 34.5, 35.0, 36.0, 36.5, 37.0]
    assert [n.pitch for n in notes] == ["F4", "G4", "F4", "G4", "F4", "G4"]
    assert all(n.start_beats >= 34.0 for n in notes)  # bars 1-4 would be < 16.0
    assert all(n.duration_beats == 1.0 for n in notes)

def test_bar_relative_byte_identical_to_canonical():
    """BAR-relative shorthand must be byte-identical to its expanded canonical form."""
    def build(text):
        p = parse_pattern(text)
        return MidiBuilder(p.tempo, p.time_signature).build(p.track_notes()["BUILD HIGH PIANO"])

    midi_sh = build(BAR_RELATIVE_SIX_NOTE)
    midi_ca = build(BAR_RELATIVE_SIX_NOTE_CANONICAL)
    assert list(midi_sh.tracks[0]) == list(midi_ca.tracks[0])

    import io
    buf_sh, buf_ca = io.BytesIO(), io.BytesIO()
    midi_sh.save(file=buf_sh)
    midi_ca.save(file=buf_ca)
    assert buf_sh.getvalue() == buf_ca.getvalue()

def test_bar_relative_invalid_beat_rejected():
    """BAR 9 + 'F4 5.1 1/4' must fail: beat 5 is outside 1..4 in 4/4."""
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK T\n"
        "BAR 9\n"
        "F4 5.1 1/4\n"
    )
    with pytest.raises(PatternError) as exc:
        parse_pattern(text)
    assert "Position 9.5" in str(exc.value)
    assert "Beat 5 is outside the 1..4 range" in str(exc.value)
    assert exc.value.line == 5

def test_bar_relative_invalid_subdivision_rejected():
    """BAR 9 + 'G4 3.5 1/4' must fail: subdivision 5 is outside 1..4."""
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK T\n"
        "BAR 9\n"
        "G4 3.5 1/4\n"
    )
    with pytest.raises(PatternError) as exc:
        parse_pattern(text)
    assert "Position 9.3.5" in str(exc.value)
    assert "outside the 1..4 range" in str(exc.value)
    assert exc.value.line == 5

def test_bar_relative_duration_preserved():
    """Durations from the BAR-relative form are preserved exactly."""
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK T\n"
        "BAR 9\n"
        "C4 3.1 1/2\n"
        "D4 4.1 1/8\n"
        "E4 3.3 1/16\n"
    )
    notes = parse_pattern(text).tracks[0].notes
    assert [n.duration_beats for n in notes] == [2.0, 0.5, 0.25]

def test_bar_relative_duration_spans_bars():
    """A long BAR-relative note spans into following bars per existing rules."""
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK T\n"
        "BAR 9\n"
        "F4 4.1 1/1\n"
    )
    (note,) = parse_pattern(text).tracks[0].notes
    assert note.start_beats == 35.0   # bar 9, beat 4
    assert note.duration_beats == 4.0  # whole note spans bar 10

    # Must equal the canonical absolute spelling.
    (canon,) = parse_pattern("TEMPO 120\nTIME 4/4\nTRACK T\nBAR 9\n9.4: F4 duration=1/1\n").tracks[0].notes
    assert (note.start_beats, note.duration_beats, note.pitch) == (
        canon.start_beats, canon.duration_beats, canon.pitch,
    )
    assert note.duration_beats + note.start_beats > 36.0  # spills into bar 10

def test_bar_relative_100_notes_no_omission():
    """100+ BAR-relative notes must all reach the MIDI (nothing dropped)."""
    lines = ["TEMPO 120", "TIME 4/4", "TRACK T"]
    count = 0
    for b in range(9, 34):  # 25 bars, active BAR numbers never equal the beat tokens
        lines.append(f"BAR {b}")
        for beat in (1, 2, 3, 4):
            lines.append(f"C4 {beat}.1 1/8")
            count += 1
    p = parse_pattern("\n".join(lines))
    assert len(p.tracks[0].notes) == count

    builder = MidiBuilder(p.tempo, p.time_signature)
    midi = builder.build(p.track_notes()["T"])
    (track,) = midi.tracks
    ons = [m for m in track if m.type == "note_on" and m.velocity > 0]
    assert len(ons) == count

def test_bar_relative_canonical_unchanged():
    """Canonical '3.1: F4' still means absolute BAR 3, beat 1 (start 8.0)."""
    (canon,) = parse_pattern("TEMPO 120\nTIME 4/4\nTRACK T\nBAR 3\n3.1: F4\n").tracks[0].notes
    (rel,) = parse_pattern("TEMPO 120\nTIME 4/4\nTRACK T\nBAR 3\nF4 3.1 1/4\n").tracks[0].notes
    # When the token bar equals the active BAR, absolute shorthand wins (bar 3, beat 1).
    assert canon.start_beats == 8.0
    assert (rel.pitch, rel.start_beats, rel.duration_beats) == (
        canon.pitch, canon.start_beats, canon.duration_beats,
    )

FULL_BAR_9_25_PATTERN = """\
TEMPO 109
TIME 4/4

TRACK BUILD HIGH PIANO

BAR 9
F4 3.1 1/4
G4 3.3 1/4
F4 4.1 1/4

BAR 10
G4 1.1 1/4
F4 1.3 1/4
G4 2.1 1/4

BAR 11
G#4 3.1 1/4
G4 3.3 1/4
G#4 4.1 1/4

BAR 12
F4 1.1 1/4
G4 1.3 1/4
F4 2.1 1/4

BAR 13
F4 3.1 1/4
G#4 3.3 1/4
F4 4.1 1/4

BAR 14
F4 1.1 1/4
G#4 1.3 1/4
A#4 2.1 1/4

BAR 15
A#4 3.1 1/4
G#4 3.3 1/4
F4 4.1 1/4

BAR 16
G4 1.1 1/4
F4 1.3 1/4
G4 2.1 1/4

BAR 17
F4 3.1 1/4
G#4 3.3 1/4
F4 4.1 1/4

BAR 18
G#4 1.1 1/4
A#4 1.3 1/4
G#4 2.1 1/4

BAR 19
A#4 3.1 1/4
G#4 3.3 1/4
F4 4.1 1/4

BAR 20
G4 1.1 1/4
F4 1.3 1/4
G4 2.1 1/4

BAR 21
F4 3.1 1/4
G#4 3.3 1/4
A#4 4.1 1/4

BAR 22
A#4 1.1 1/4
G#4 1.3 1/4
F4 2.1 1/4

BAR 23
F4 3.1 1/4
G4 3.3 1/4
A#4 4.1 1/4

BAR 24
A#4 1.1 1/4
G#4 1.3 1/4
G4 2.1 1/4
F4 2.3 1/4
G4 3.1 1/4
A#4 3.3 1/4
G4 4.1 1/4
F4 4.3 1/4

BAR 25
A#4 1.1 1/4
G#4 1.3 1/4
F4 2.1 1/4
G4 2.3 1/4
A#4 3.1 1/4
G#4 3.3 1/4
F4 4.1 1/4
"""

def test_full_bar_9_25_pattern():
    """The complete BAR 9-25 pattern compiles with all notes in bars 9-25."""
    p = parse_pattern(FULL_BAR_9_25_PATTERN)
    notes = p.tracks[0].notes
    expected_count = 15 * 3 + 8 + 7  # bars 9-23 three each, bar 24 eight, bar 25 seven
    assert expected_count == 60
    assert len(notes) == expected_count
    assert all(n.start_beats >= 32.0 for n in notes)   # bar 9 starts at beat 32
    assert all(n.start_beats < 100.0 for n in notes)   # bar 25 ends at beat 99
    assert all(n.duration_beats == 1.0 for n in notes)  # all 1/4

    builder = MidiBuilder(p.tempo, p.time_signature)
    midi = builder.build(p.track_notes()["BUILD HIGH PIANO"])
    (track,) = midi.tracks
    ons = [m for m in track if m.type == "note_on" and m.velocity > 0]
    offs = [m for m in track if m.type == "note_off"]
    assert len(ons) == expected_count
    assert len(offs) == expected_count
