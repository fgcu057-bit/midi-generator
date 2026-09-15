import mido
import sys

def precision_trace(file_path):
    print(f"Precision Trace: {file_path}")
    try:
        mid = mido.MidiFile(file_path)
        for i, track in enumerate(mid.tracks):
            print(f"\n--- Track {i} ---")
            absolute_tick = 0
            for j, msg in enumerate(track):
                absolute_tick += msg.time
                try:
                    # Force access to all attributes to trigger potential errors
                    _ = msg.type
                    if hasattr(msg, 'note'): _ = msg.note
                    if hasattr(msg, 'velocity'): _ = msg.velocity
                    if hasattr(msg, 'time'): _ = msg.time
                    print(f"Event {j} | Tick {absolute_tick} | {msg}")
                except Exception as e:
                    print(f"Event {j} | Tick {absolute_tick} | ERROR: {e}")
                    # Try to see raw data if possible
                    if hasattr(msg, 'data'):
                        print(f"  Raw data: {msg.data}")
    except Exception as e:
        print(f"Critical File Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        precision_trace(sys.argv[1])
