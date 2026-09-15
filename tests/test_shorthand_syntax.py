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

def test_shorthand_bar_mismatch_precise_error():
    text = (
        "TEMPO 120\n"
        "TIME 4/4\n"
        "TRACK T\n"
        "BAR 1\n"
        "G4 2.1 1/4\n"
    )
    with pytest.raises(PatternError) as exc:
        parse_pattern(text)
    assert "Position bar 2 does not match the active BAR 1" in str(exc.value)
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
