import sys
import os
from pathlib import Path

# Set up imports to work from the project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from midi_generator.midi_reader import MidiReader
from midi_generator.parser import _format_position

def format_duration(beats: float, beats_per_bar: int) -> str:
    """Convert beat duration to the project's duration=1/X syntax."""
    ratio = beats / beats_per_bar
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
    return f"{beats:.3f} beats"

def main():
    # ==============================================================================
    # CONFIGURATION: CHANGE THIS PATH TO YOUR MIDI FILE
    # ==============================================================================
    MIDI_PATH = "/Users/karenina/Desktop/Love is in the Air, Pt. 1.mid"
    # ==============================================================================

    midi_path = Path(MIDI_PATH)
    if not midi_path.exists():
        print(f"Error: MIDI file not found at {MIDI_PATH}")
        sys.exit(1)
        
    try:
        reader = MidiReader(midi_path)
        info = reader.get_info()
    except Exception as e:
        print(f"Error reading MIDI file: {e}")
        sys.exit(1)

    # Derive output filename from script name
    script_name = Path(__file__).stem
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{script_name}.txt"

    output_lines = []
    
    # 1. MIDI Verification Header
    output_lines.append("=== MIDI VERIFICATION ===")
    output_lines.append(f"File: {midi_path.name}")
    output_lines.append(f"Type: {info.type}")
    output_lines.append(f"PPQ: {info.ticks_per_beat}")
    output_lines.append(f"Initial Tempo: {info.tempo.bpm} BPM")
    output_lines.append(f"Time Signature: {info.time_signature.numerator}/{info.time_signature.denominator}")
    
    # Calculate total bars (approximate based on last note)
    total_bars = 0
    for track in info.tracks:
        if track.notes:
            last_note = track.notes[-1]
            bar = int(last_note.start_beats // info.time_signature.numerator) + 1
            total_bars = max(total_bars, bar)
    output_lines.append(f"Total Bars: {total_bars}")
    output_lines.append(f"Track Count: {len(info.tracks)}")
    output_lines.append("")

    # 2. Timing Information
    output_lines.append("=== TIMING MAP ===")
    output_lines.append(f"Base Tempo: {info.tempo.bpm} BPM")
    output_lines.append(f"Base Time Signature: {info.time_signature.numerator}/{info.time_signature.denominator}")
    # Note: In the current implementation, only initial tempo/sig are extracted.
    # I will add a placeholder for changes to be expanded later.
    output_lines.append("No mid-song tempo/sig changes detected.")
    output_lines.append("")

    # 3. Track-by-Track Information
    beats_per_bar = info.time_signature.numerator
    
    for i, track in enumerate(info.tracks):
        if track.note_count == 0 and track.name.startswith("Track"):
            continue
            
        output_lines.append(f"TRACK: {track.name}")
        output_lines.append(f"Channel: {track.channel}")
        output, program = track.channel, track.program
        output_lines.append(f"Program: {track.program}")
        output_lines.append(f"Note Count: {track.note_count}")
        output_lines.append("")
        
        # Bar-by-bar representation
        sorted_notes = sorted(track.notes, key=lambda n: n.start_beats)
        current_bar = -1
        for note in sorted_notes:
            bar = int(note.start_beats // beats_per_bar) + 1
            if bar != current_bar:
                output_lines.append(f"BAR {bar}:")
                current_bar = bar
            
            pos = _format_position(note.start_beats, beats_per_bar)
            dur_val = format_duration(note.duration_beats, beats_per_bar)
            dur_str = f"duration={dur_val}"
            vel_str = f"velocity={note.velocity}"
            output_lines.append(f"{pos}: {note.pitch} {dur_str} {vel_str}")
        
        output_lines.append("")

    # 4. Continuous Chronological Representation
    output_lines.append("=== CONTINUOUS NOTE SEQUENCE ===")
    all_notes = []
    for track in info.tracks:
        for note in track.notes:
            all_notes.append(note)
    
    all_notes.sort(key=lambda n: n.start_beats)
    
    # Group simultaneous notes
    if all_notes:
        current_tick = all_notes[0].start_beats
        group = []
        for note in all_notes:
            if abs(note.start_beats - current_tick) < 0.001:
                group.append(note.pitch)
            else:
                # Flush group
                group_str = " + ".join(group)
                output_lines.append(f"{group_str}")
                output_lines.append(" → ")
                group = [note.pitch]
                current_tick = note.start_beats
        # Final group
        group_str = " + ".join(group)
        output_lines.append(f"{group_str}")
    else:
        output_lines.append("No notes found.")
    
    output_lines.append("\n")

    # 5. Warnings/Errors
    if info.warnings:
        output_lines.append("=== MIDI READ WARNINGS ===")
        for warn in info.warnings:
            output_lines.append(warn)
    else:
        output_lines.append("No MIDI read warnings. Reconstruction is exact.")

    final_output = "\n".join(output_lines)
    
    # Write to TXT file
    with open(output_file, "w") as f:
        f.write(final_output)
        
    # Print to terminal
    print(final_output)
    print("\n" + "="*40)
    print("MIDI successfully analyzed.")
    print(f"ChatGPT output: {output_file}")
    print("="*40)

if __name__ == "__main__":
    main()
