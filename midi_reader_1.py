import sys
from pathlib import Path

# Set up imports to work from the project root
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from midi_generator.midi_reader import MidiReader
from midi_generator.parser import _format_position

# ==============================================================================
# CONFIGURATION: CHANGE THIS PATH TO YOUR MIDI FILE
# ==============================================================================
MIDI_PATH = "/Users/karenina/Desktop/Main Melody.mid"
# ==============================================================================

def format_duration(beats: float, beats_per_bar: int) -> str:
    """Convert beat duration to the project's duration=1/X syntax."""
    ratio = beats / beats_per_bar
    
    # Exact match for common durations
    if abs(ratio - 1.0) < 0.001: return "1/1"
    if abs(ratio - 0.5) < 0.001: return "1/2"
    if abs(ratio - 0.25) < 0.001: return "1/4"
    if abs(ratio - 0.125) < 0.001: return "1/8"
    if abs(ratio - 0.0625) < 0.001: return "1/16"
    if abs(ratio - 0.03125) < 0.001: return "1/32"
    
    # Exact match for dotted durations
    if abs(ratio - 1.5) < 0.001: return "1/1."
    if abs(ratio - 0.75) < 0.001: return "1/2."
    if abs(ratio - 0.375) < 0.001: return "1/4."
    if abs(ratio - 0.1875) < 0.001: return "1/8."
    if abs(ratio - 0.09375) < 0.001: return "1/16."
    if abs(ratio - 0.046875) < 0.001: return "1/32."
    
    return f"{beats:.3f} beats"

def main():
    midi_path = Path(MIDI_PATH)
    if not midi_path.exists():
        print(f"Error: MIDI file not found at {MIDI_PATH}")
        print("Please edit the MIDI_PATH variable in this script.")
        sys.exit(1)
        
    try:
        reader = MidiReader(midi_path)
        info = reader.get_info()
    except Exception as e:
        print(f"Error reading MIDI file: {e}")
        sys.exit(1)

    # --- START OF CHATGPT-PASTEABLE OUTPUT ---
    print(f"MIDI File: {midi_path.name}")
    print(f"Type: {info.type} | PPQ: {info.ticks_per_beat}")
    print(f"TEMPO {info.tempo.bpm}")
    print(f"TIME {info.time_signature.numerator}/{info.time_signature.denominator}")
    print("")
    
    beats_per_bar = info.time_signature.numerator
    
    for track in info.tracks:
        # Skip empty tracks for a cleaner ChatGPT paste, but keep named ones
        if track.note_count == 0 and track.name.startswith("Track"):
            continue
            
        print(f"TRACK {track.name}")
        print(f"Program: {track.program} | Channel: {track.channel}")
        print("")
        
        # Sort notes by start time
        sorted_notes = sorted(track.notes, key=lambda n: n.start_beats)
        
        current_bar = -1
        for note in sorted_notes:
            bar = int(note.start_beats // beats_per_bar) + 1
            if bar != current_bar:
                print(f"BAR {bar}")
                current_bar = bar
            
            pos = _format_position(note.start_beats, beats_per_bar)
            dur_val = format_duration(note.duration_beats, beats_per_bar)
            
            # If duration is a fraction, format as duration=1/X
            if "/" in dur_val:
                dur_str = f"duration={dur_val}"
            else:
                dur_str = f"duration={dur_val}"
                
            vel_str = f"velocity={note.velocity}"
            
            print(f"{pos}: {note.pitch} {dur_str} {vel_str}")
            
        print("") # Gap between tracks

if __name__ == "__main__":
    main()
