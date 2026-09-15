
import os
from pathlib import Path
from midi_generator.midi_reader import MidiReader
from midi_generator.parser import _format_position
from fractions import Fraction

def midi_to_pattern(midi_path, output_dir):
    print(f"Processing {midi_path}...")
    reader = MidiReader(midi_path)
    info = reader.get_info()
    
    pattern_lines = []
    pattern_lines.append(f"TEMPO {info.tempo.bpm}")
    pattern_lines.append(f"TIME {info.time_signature.numerator}/{info.time_signature.denominator}")
    
    for track in info.tracks:
        if not track.notes:
            continue
            
        pattern_lines.append(f"\nTRACK {track.name}")
        
        notes_by_bar = {}
        beats_per_bar = info.time_signature.numerator
        
        for note in track.notes:
            bar = int(note.start_beats // beats_per_bar) + 1
            notes_by_bar.setdefault(bar, []).append(note)
            
        for bar in sorted(notes_by_bar.keys()):
            pattern_lines.append(f"BAR {bar}")
            for note in notes_by_bar[bar]:
                pos = _format_position(note.start_beats, beats_per_bar)
                duration = note.duration_beats / beats_per_bar
                dur_frac = Fraction(duration).limit_denominator()
                dur_str = f"{dur_frac.numerator}/{dur_frac.denominator}"
                
                line = f"{pos}: {note.pitch} velocity={note.velocity} duration={dur_str}"
                pattern_lines.append(line)
                
    output_path = Path(output_dir) / (Path(midi_path).stem + ".pattern")
    output_path.write_text("\n".join(pattern_lines))
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    midi_files = [
        "/Users/karenina/Desktop/Random1.mid",
        "/Users/karenina/Desktop/LORNDropRough.mid"
    ]
    output_folder = "arrangements"
    os.makedirs(output_folder, exist_ok=True)
    
    for f in midi_files:
        try:
            midi_to_pattern(f, output_folder)
        except Exception as e:
            print(f"Error processing {f}: {e}")
