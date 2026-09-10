import argparse
import sys
from pathlib import Path
from fractions import Fraction

from midi_generator.midi_reader import MidiReader, MidiFileInfo
from midi_generator.parser import _format_position

def format_duration(beats: float, beats_per_bar: int) -> str:
    """Convert beat duration to the project's duration=1/X syntax."""
    # A whole note is beats_per_bar
    whole_note_beats = beats_per_bar
    ratio = beats / whole_note_beats
    
    # Find the closest power-of-two denominator
    # 1/1, 1/2, 1/4, 1/8, 1/16, 1/32
    denominators = [1, 2, 4, 8, 16, 32]
    best_denom = 4 # default
    min_diff = float('inf')
    
    for d in denominators:
        diff = abs(ratio - (1 / d))
        if diff < min_diff:
            min_diff = diff
            best_denom = d
            
    # Check for dotted notes (roughly 1.5 * base)
    # E.g. 1/4. is 1.5 * 1/4 = 0.375
    for d in denominators:
        dotted_val = (1 / d) * 1.5
        diff = abs(ratio - dotted_val)
        if diff < min_diff:
            min_diff = diff
            best_denom = d
            # We'll handle the dot in the final string
            
    # This is a simplified heuristic. For exact conversion, 
    # we would need to check if it's exactly 1/d or 1.5/d.
    
    # Since the goal is round-trip, let's be more precise:
    if abs(ratio - 1.0) < 0.001: return "1/1"
    if abs(ratio - 0.5) < 0.001: return "1/2"
    if abs(ratio - 0.25) < 0.001: return "1/4"
    if abs(ratio - 0.125) < 0.001: return "1/8"
    if abs(ratio - 0.0625) < 0.001: return "1/16"
    if abs(ratio - 0.03125) < 0.001: return "1/32"
    
    if abs(ratio - 1.5) < 0.001: return "1/1."
    if abs(ratio - 0.75) < 0.001: return "1/2."
    if abs(ratio - 0.375) < 0.001: return "1/4."
    if abs(ratio - 0.1875) < 0.001: return "1/8."
    if abs(ratio - 0.09375) < 0.001: return "1/16."
    if abs(ratio - 0.046875) < 0.001: return "1/32."
    
    return f"duration={beats:.3f} beats" # Fallback

def main():
    parser = argparse.ArgumentParser(description="Inspect MIDI files or convert to .pattern")
    parser.add_argument("midi_file", help="Path to the MIDI file to read")
    parser.add_argument("--to-pattern", action="store_true", help="Convert MIDI to a .pattern file")
    parser.add_argument("--output", help="Explicit output path for .pattern file")
    
    args = parser.parse_args()
    
    midi_path = Path(args.midi_file)
    if not midi_path.exists():
        print(f"Error: File {midi_path} not found.")
        sys.exit(1)
        
    reader = MidiReader(midi_path)
    info = reader.get_info()
    
    if args.to_pattern:
        # Conversion mode
        stem = midi_path.stem
        output_path = Path(args.output) if args.output else midi_path.with_suffix(".pattern")
        
        if output_path.exists() and not args.output: # only warn if derived
             # To prevent silent overwrite, we can check exists. 
             # The prompt asked for explicit overwrite or error.
             pass 

        # We'll implement the collision check properly
        if output_path.exists():
             print(f"Error: Output file {output_path} already exists.")
             sys.exit(1)

        lines = []
        lines.append(f"TEMPO {info.tempo.bpm}")
        lines.append(f"TIME {info.time_signature.numerator}/{info.time_signature.denominator}")
        lines.append("")
        
        beats_per_bar = info.time_signature.numerator
        
        for track in info.tracks:
            lines.append(f"TRACK {track.name}")
            lines.append("")
            
            # Group notes by bar
            # Notes might not be perfectly sorted by bar in MIDI
            sorted_notes = sorted(track.notes, key=lambda n: n.start_beats)
            
            current_bar = -1
            for note in sorted_notes:
                bar = int(note.start_beats // beats_per_bar) + 1
                if bar != current_bar:
                    lines.append(f"BAR {bar}")
                    current_bar = bar
                
                pos = _format_position(note.start_beats, beats_per_bar)
                
                # Determine duration string
                dur_str = format_duration(note.duration_beats, beats_per_bar)
                if not dur_str.startswith("duration="):
                    dur_str = f"duration={dur_str}"
                
                vel_str = f"velocity={note.velocity}"
                
                lines.append(f"{pos}: {note.pitch} {dur_str} {vel_str}")
                lines.append("")
                
        with open(output_path, "w") as f:
            f.write("\n".join(lines))
            
        print(f"Converted {midi_path.name} -> {output_path}")
        
    else:
        # Inspection mode
        print(f"File: {info.file_path}")
        print(f"Type: {info.type}")
        print(f"PPQ: {info.ticks_per_beat}")
        print(f"Tempo: {info.tempo.bpm} BPM")
        print(f"Time: {info.time_signature.numerator}/{info.time_signature.denominator}")
        print("")
        
        for track in info.tracks:
            print(f"Track: {track.name}")
            print(f"Channel: {track.channel}")
            print(f"Program: {track.program}")
            print(f"Notes: {track.note_count}")
            print("")
            
            beats_per_bar = info.time_signature.numerator
            for note in track.notes:
                pos = _format_position(note.start_beats, beats_per_bar)
                # a simple duration in beats
                dur_beats = note.duration_beats
                
                print(f"{pos}  {note.pitch}  velocity={note.velocity}  duration={dur_beats:.3f} beats")
            print("")

if __name__ == "__main__":
    main()
