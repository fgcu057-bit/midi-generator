import pytest
from pathlib import Path
from midi_generator.midi_reader import MidiReader
from midi_generator.midi_builder import MidiBuilder, Tempo, TimeSignature, NoteEvent
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo

def create_complex_midi(path, tracks_config, tempo=120, time_sig=(4,4), tpb=480):
    mid = MidiFile(ticks_per_beat=tpb)
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

def test_chatgpt_output_fidelity(tmp_path):
    # We test if the template-style logic would produce the correct data
    midi_path = tmp_path / "fidelity.mid"
    tpb = 480
    tracks_config = [
        ("Piano", [
            (60, 0.0, 1.0, 100),    # 1.1: C3 duration=1/4 velocity=100
            (64, 0.25, 0.25, 80),   # 1.1.2: E3 duration=1/16 velocity=80
        ]),
    ]
    create_complex_midi(midi_path, tracks_config, tpb=tpb)
    
    reader = MidiReader(midi_path)
    info = reader.get_info()
    
    # Verify the reader engine (which the template uses) is accurate
    notes = sorted(info.tracks[1].notes, key=lambda n: n.start_beats)
    assert notes[0].pitch == "C3"
    assert notes[0].start_beats == 0.0
    assert notes[1].pitch == "E3"
    assert notes[1].start_beats == 0.25

def test_chatgpt_offgrid_reporting(tmp_path):
    midi_path = tmp_path / "offgrid_rep.mid"
    create_complex_midi(midi_path, [("T1", [(60, 0.123, 1.0, 100)])])
    
    reader = MidiReader(midi_path)
    info = reader.get_info()
    
    # The reader should store the exact float
    assert abs(info.tracks[1].notes[0].start_beats - 0.123) < 0.001
