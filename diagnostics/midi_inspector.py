import mido
import sys

def inspect_midi(file_path):
    print(f"--- Inspecting: {file_path} ---")
    try:
        mid = mido.MidiFile(file_path)
        print(f"Type: {mid.type}, PPQ: {mid.ticks_per_beat}")
        
        for i, track in enumerate(mid.tracks):
            print(f"\nTrack {i}:")
            absolute_tick = 0
            for msg in track:
                absolute_tick += msg.time
                if msg.is_meta:
                    print(f"Tick {absolute_tick:<6} META: {msg}")
                else:
                    print(f"Tick {absolute_tick:<6} {msg}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inspect_midi(sys.argv[1])
    else:
        print("Usage: python midi_inspector.py <file.mid>")
