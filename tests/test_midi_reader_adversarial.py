import pytest
from pathlib import Path
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo
from midi_generator.midi_reader import MidiReader
from midi_generator.midi_builder import MidiBuilder, Tempo, TimeSignature, NoteEvent
from midi_generator.parser import parse_pattern_file, parse_pattern

def create_complex_midi(path, tracks_config, tempo=120, time_sig=(4,4), tpb=480):
    """
    Helper to create a MIDI file with multiple tracks and various events.
    tracks_config: list of (name, notes) where notes = [(pitch, start, dur, vel), ...]
    """
    mid = MidiFile(ticks_per_beat=tpb)
    
    # Global metadata track (Track 0)
    meta_track = MidiTrack()
    mid.tracks.append(meta_track)
    meta_track.append(MetaMessage("set_tempo", tempo=bpm2tempo(tempo), time=0))
    meta_track.append(MetaMessage("time_signature", numerator=time_sig[0], denominator=time_sig[1], time=0))
    
    for track_name, notes in tracks_config:
        track = MidiTrack()
        mid.tracks.append(track)
        track.append(MetaMessage("track_name", name=track_name, time=0))
        
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

def test_midi_reader_adversarial_cases(tmp_path):
    # 1. Multiple tracks, different PPQ, mixed durations, and off-grid timing
    midi_path = tmp_path / "adversarial.mid"
    tpb = 960 
    tracks_config = [
        ("Piano", [
            (60, 0.0, 1.0, 100),      # Exact grid
            (64, 0.1, 0.5, 80),      # Off-grid start
            (67, 0.0, 0.123, 90),    # Off-grid duration
        ]),
        ("Bass", [
            (36, 0.0, 4.0, 110),     # Spans bar boundary (Bar 1 -> 2)
        ]),
        ("Empty", [])                # Empty track
    ]
    create_complex_midi(midi_path, tracks_config, tpb=tpb)
    
    reader = MidiReader(midi_path)
    info = reader.get_info()
    
    assert info.ticks_per_beat == tpb
    # We expect 4 tracks because create_complex_midi adds a metadata track at index 0
    assert len(info.tracks) == 4
    assert info.tracks[1].name == "Piano"
    assert info.tracks[2].name == "Bass"
    assert info.tracks[3].name == "Empty"
    assert info.tracks[1].notes[1].start_beats == 0.1
    assert info.tracks[2].notes[0].duration_beats == 4.0

def test_midi_reader_velocity_zero_as_off(tmp_path):
    # Test that note_on with velocity 0 is treated as note_off
    midi_path = tmp_path / "vel0.mid"
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)
    
    # Note on, then Note on with velocity 0
    track.append(Message("note_on", note=60, velocity=100, time=0))
    track.append(Message("note_on", note=60, velocity=0, time=480))
    mid.save(str(midi_path))
    
    reader = MidiReader(midi_path)
    info = reader.get_info()
    assert info.tracks[0].note_count == 1
    assert info.tracks[0].notes[0].duration_beats == 1.0

def test_midi_reader_overlapping_same_pitch(tmp_path):
    # Test overlapping notes of same pitch (should be handled by state machine)
    midi_path = tmp_path / "overlap.mid"
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)
    
    track.append(Message("note_on", note=60, velocity=100, time=0))
    track.append(Message("note_on", note=60, velocity=100, time=240)) # Overlap
    track.append(Message("note_off", note=60, velocity=0, time=240))
    track.append(Message("note_off", note=60, velocity=0, time=240))
    mid.save(str(midi_path))
    
    reader = MidiReader(midi_path)
    info = reader.get_info()
    assert len(info.tracks[0].notes) > 0

def test_midi_reader_program_changes(tmp_path):
    midi_path = tmp_path / "prog.mid"
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(Message("program_change", program=12, time=0))
    mid.save(str(midi_path))
    
    reader = MidiReader(midi_path)
    info = reader.get_info()
    assert info.tracks[0].program == 12

def test_midi_reader_type0_file(tmp_path):
    # Type 0: All events in one track
    midi_path = tmp_path / "type0.mid"
    mid = MidiFile(ticks_per_beat=480, type=0)
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(Message("note_on", note=60, velocity=100, time=0))
    track.append(Message("note_off", note=60, velocity=0, time=480))
    mid.save(str(midi_path))
    
    reader = MidiReader(midi_path)
    info = reader.get_info()
    assert info.type == 0
    assert info.tracks[0].note_count == 1

def test_midi_reader_unnamed_tracks(tmp_path):
    midi_path = tmp_path / "unnamed.mid"
    mid = MidiFile(ticks_per_beat=480)
    mid.tracks.append(MidiTrack()) # Track 1 (unnamed)
    mid.tracks.append(MidiTrack()) # Track 2 (unnamed)
    mid.save(str(midi_path))
    
    reader = MidiReader(midi_path)
    info = reader.get_info()
    assert info.tracks[0].name == "Track 1"
    assert info.tracks[1].name == "Track 2"
