import mido
import sys

def trace_midi(file_path):
    print(f"Tracing: {file_path}")
    try:
        mid = mido.MidiFile(file_path)
        for i, track in enumerate(mid.tracks):
            print(f"\n--- Track {i} ---")
            for j, msg in enumerate(track):
                try:
                    print(f"Event {j}: {msg}")
                except Exception as e:
                    print(f"Event {j}: ERROR reading message - {e}")
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        trace_midi(sys.argv[1])
