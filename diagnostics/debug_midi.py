import mido
import sys

def debug_midi(file_path):
    print(f"Debugging: {file_path}")
    try:
        # Using mido.MidiFile normally
        mid = mido.MidiFile(file_path)
        print("Successfully opened with mido.MidiFile")
        for i, track in enumerate(mid.tracks):
            print(f"Track {i} length: {len(track)}")
    except Exception as e:
        print(f"Mido error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        debug_midi(sys.argv[1])
