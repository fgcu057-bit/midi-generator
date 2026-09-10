import pytest
from pathlib import Path
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo
from midi_generator.midi_reader import MidiReader
from midi_generator.midi_builder import MidiBuilder, Tempo, TimeSignature, NoteEvent
from midi_generator.parser import parse_pattern_file

def create_simple_midi(path, notes, tempo=120, time_sig=(4,4), tpb=480):
    """Helper to create a MIDI file for testing."""
    mid = MidiFile(ticks_per_beat=tpb)
    track = MidiTrack()
    mid.tracks.append(track)
    
    track.append(MetaMessage("set_tempo", tempo=bpm2tempo(tempo), time=0))
    track.append(MetaMessage("time_signature", numerator=time_sig[0], denominator=time_sig[1], time=0))
    
    # Correct way to build a test MIDI
    events = []
    for note in notes:
        events.append((int(round(note[1] * tpb)), "on", note[0], note[3]))
        events.append((int(round((note[1] + note[2]) * tpb)), "off", note[0], 0))
    
    events.sort()
    
    curr_tick = 0
    for tick, type, pitch, vel in events:
        delta = tick - curr_tick
        curr_tick = tick
        track.append(Message("note_on" if type == "on" else "note_off", note=pitch, velocity=vel, time=delta))
        
    mid.save(str(path))
    return mid

def test_midi_reader_single_note(tmp_path):
    # C4 (60), start 0.0, duration 1.0, vel 100
    midi_path = tmp_path / "test.mid"
    create_simple_midi(midi_path, [(60, 0.0, 1.0, 100)])
    
    reader = MidiReader(midi_path)
    info = reader.get_info()
    
    assert info.tracks[0].note_count == 1
    note = info.tracks[0].notes[0]
    assert note.pitch == "C3" # Logic convention: MIDI 60 = C3
    assert note.start_beats == 0.0
    assert note.duration_beats == 1.0
    assert note.velocity == 100

def test_midi_reader_chord(tmp_path):
    midi_path = tmp_path / "test.mid"
    # C4 (60) and E4 (64) at 0.0, duration 1.0
    create_simple_midi(midi_path, [(60, 0.0, 1.0, 100), (64, 0.0, 1.0, 100)])
    
    reader = MidiReader(midi_path)
    info = reader.get_info()
    
    assert info.tracks[0].note_count == 2
    pitches = {n.pitch for n in info.tracks[0].notes}
    assert pitches == {"C3", "E3"}

def test_midi_reader_roundtrip_exact(tmp_path):
    # This is the "gold standard" test: MIDI -> Pattern -> MIDI
    # We'll use notes that land exactly on the grid to ensure identity
    original_notes = [
        ("C3", 0.0, 1.0, 100),   # Bar 1.1
        ("E3", 1.0, 0.5, 80),    # Bar 1.2
        ("G3", 1.5, 0.25, 90),   # Bar 1.2.3
    ]
    
    # 1. Build original MIDI
    builder = MidiBuilder(Tempo(120), TimeSignature(4, 4))
    note_events = [NoteEvent(p, s, d, v) for p, s, d, v in original_notes]
    midi_out_1 = tmp_path / "original.mid"
    builder.build(note_events, output_path=str(midi_out_1))
    
    # 2. Read MIDI -> Pattern
    reader = MidiReader(midi_out_1)
    info = reader.get_info()
    
    # Simulate the .pattern file generation
    pattern_lines = []
    pattern_lines.append(f"TEMPO {info.tempo.bpm}")
    pattern_lines.append(f"TIME {info.time_signature.numerator}/{info.time_signature.denominator}")
    pattern_lines.append("")
    pattern_lines.append("TRACK Piano")
    pattern_lines.append("")
    pattern_lines.append("BAR 1")
    
    for note in info.tracks[0].notes:
        from midi_generator.parser import _format_position
        pos = _format_position(note.start_beats, 4)
        # simplistic duration for test
        dur = "duration=1/4" if note.duration_beats == 1.0 else "duration=1/8" if note.duration_beats == 0.5 else "duration=1/16"
        pattern_lines.append(f"{pos}: {note.pitch} {dur} velocity={note.velocity}")
        
    pattern_text = "\n".join(pattern_lines)
    
    # 3. Pattern -> MIDI
    from midi_generator.parser import parse_pattern
    parsed = parse_pattern(pattern_text)
    
    builder_2 = MidiBuilder(parsed.tempo, parsed.time_signature)
    midi_out_2 = tmp_path / "roundtrip.mid"
    builder_2.build(parsed.tracks[0].notes, output_path=str(midi_out_2), track_name="Piano")
    
    # 4. Compare MIDI files (by reading them back)
    reader_2 = MidiReader(midi_out_2)
    info_2 = reader_2.get_info()
    
    # Compare note events
    notes_1 = sorted(info.tracks[0].notes, key=lambda n: (n.start_beats, n.pitch))
    notes_2 = sorted(info_2.tracks[0].notes, key=lambda n: (n.start_beats, n.pitch))
    
    assert len(notes_1) == len(notes_2)
    for n1, n2 in zip(notes_1, notes_2):
        assert n1.pitch == n2.pitch
        assert n1.start_beats == n2.start_beats
        assert n1.duration_beats == n2.duration_beats
        assert n1.velocity == n2.velocity

def test_midi_reader_off_grid(tmp_path):
    # Note at 0.1 beats (not on 0.25 grid)
    midi_path = tmp_path / "offgrid.mid"
    create_simple_midi(midi_path, [(60, 0.1, 1.0, 100)])
    
    reader = MidiReader(midi_path)
    info = reader.get_info()
    
    # The reader should preserve the exact 0.1
    assert info.tracks[0].notes[0].start_beats == 0.1
