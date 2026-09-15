import pytest
from pathlib import Path
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo
from midi_generator.midi_reader import MidiReader

def create_large_midi(path, num_tracks=5, bars=100, tpb=480):
    mid = MidiFile(ticks_per_beat=tpb)
    meta = MidiTrack()
    mid.tracks.append(meta)
    meta.append(MetaMessage("set_tempo", tempo=bpm2tempo(120), time=0))
    meta.append(MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    
    for t in range(num_tracks):
        track = MidiTrack()
        mid.tracks.append(track)
        track.append(MetaMessage("track_name", name=f"Inst {t}", time=0))
        
        for b in range(bars):
            # Note On: start at beat b*4
            # We must account for the previous note's duration in the delta time
            # For the first note, delta is 0. For subsequent, delta is (4-1)*tpb = 3*tpb
            delta_on = 0 if b == 0 else 3 * tpb
            track.append(Message("note_on", note=60 + t, velocity=100, time=delta_on))
            # Note Off: 1 beat duration
            track.append(Message("note_off", note=60 + t, velocity=0, time=tpb))
            
    mid.save(str(path))
    return mid

def test_large_midi_processing(tmp_path):
    midi_path = tmp_path / "large.mid"
    bars = 100
    create_large_midi(midi_path, num_tracks=10, bars=bars)
    
    reader = MidiReader(midi_path)
    info = reader.get_info()
    
    assert len(info.tracks) == 11 # 1 meta + 10 inst
    assert info.tracks[1].note_count == bars
    # Last note start beat: (bars-1) * 4
    assert info.tracks[1].notes[-1].start_beats == (bars - 1) * 4

def test_melody1_failure_resolved(tmp_path):
    midi_path = tmp_path / "trigger.mid"
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(Message("note_on", note=60, velocity=100, time=0))
    track.append(MetaMessage("text", text="Logic Pro Metadata", time=0))
    track.append(Message("note_off", note=60, velocity=0, time=120))
    mid.save(str(midi_path))
    
    reader = MidiReader(midi_path)
    info = reader.get_info()
    assert info.tracks[0].note_count == 1
