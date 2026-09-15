
import sys
from pathlib import Path
from midi_generator.midi_reader import MidiReader
from midi_generator.midi_builder import MidiBuilder, Tempo, TimeSignature, NoteEvent

def get_midi_pitch(note_name):
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    import re
    match = re.match(r"([A-G]#?)(\d)", note_name)
    if not match: return None
    name, octave = match.groups()
    return notes.index(name) + (int(octave) + 1) * 12

def get_note_name(pitch):
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (pitch // 12) - 1
    name = notes[pitch % 12]
    return f"{name}{octave}"

def transpose_notes(notes, chord_map):
    # chord_map is a list of (start_beat, end_beat, shift)
    new_notes = []
    for note in notes:
        shift = 0
        for start, end, s in chord_map:
            if start <= note.start_beats < end:
                shift = s
                break
        
        # pitch is a string like "F#3" in NoteEvent from MidiReader
        p = get_midi_pitch(note.pitch)
        if p is not None:
            new_pitch = get_note_name(p + shift)
            new_notes.append(NoteEvent(new_pitch, note.start_beats, note.duration_beats, note.velocity))
        else:
            new_notes.append(note)
    return new_notes

def main():
    input_path = Path('/Users/karenina/Downloads/M83 - Outro (Piano).mid')
    reader = MidiReader(input_path)
    info = reader.get_info()
    
    # Original chords: D Bm G Em G5 E
    # Roots: D (62), B (59), G (67), E (64), G (67), E (64)
    # Note: we use MIDI numbers for roots to calculate shifts
    # MIDI D4 = 62, B3 = 59, G3 = 67, E3 = 64
    roots_orig = [62, 59, 67, 64, 67, 64]
    
    mappings = [
        # F Bb Dm Fm C (5 items) - User provided 5, original has 6. 
        # Assuming the 6th is a repeat of the 5th or the 5th repeats.
        # We'll map: F (65), Bb (70), D (62), F (65), C (60), C (60)
        [65, 70, 62, 65, 60, 60],
        # A D F#m Am E (5 items)
        # A (69), D (62), F# (66), A (69), E (64), E (64)
        [69, 62, 66, 69, 64, 64],
        # A F#m D Bm E (5 items)
        # A (69), F# (66), D (62), B (59), E (64), E (64)
        [69, 66, 62, 59, 64, 64]
    ]

    # In the original MIDI, let's determine chord durations.
    # Looking at the .pattern file:
    # Bar 1: D (0-4s)
    # Bar 2: D (4-6s), G (6-8s)
    # Bar 3: Bm (8-12s)
    # Bar 4: G (12-16s)
    # ... (repeats every 12 bars or so?)
    # Let's use the sequence of chords provided by the user: D, Bm, G, Em, G5, E
    # We'll assume each chord lasts for 4 beats (one bar)
    
    total_beats = info.tracks[0].notes[-1].start_beats + info.tracks[0].notes[-1].duration_beats
    
    for i, mapping_roots in enumerate(mappings):
        # Create chord_map for this mapping
        chord_map = []
        beat = 0
        while beat < total_beats:
            for root_orig, root_new in zip(roots_orig, mapping_roots):
                shift = root_new - root_orig
                chord_map.append((beat, beat + 4, shift))
                beat += 4
        
        # Process track
        original_notes = info.tracks[0].notes
        new_notes = transpose_notes(original_notes, chord_map)
        
        # Build MIDI
        builder = MidiBuilder(
            tempo=Tempo(bpm=info.tempo.bpm),
            time_signature=TimeSignature(numerator=info.time_signature.numerator, denominator=info.time_signature.denominator)
        )
        output_path = Path(f'/Users/karenina/midi-generator/output/outro_v{i+1}.mid')
        builder.build(
            notes=new_notes,
            ticks_per_beat=info.ticks_per_beat,
            output_path=output_path,
            track_name=info.tracks[0].name
        )
        print(f"Created {output_path}")

if __name__ == "__main__":
    main()
