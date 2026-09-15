import struct
import sys

def analyze_midi(file_path):
    print(f"Raw MIDI Analysis: {file_path}")
    try:
        with open(file_path, "rb") as f:
            data = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print(f"File Size: {len(data)} bytes")
    
    if len(data) < 14:
        print("File too small to be a MIDI file.")
        return

    # Header
    header = data[:14]
    if header[:4] != b"MThd":
        print(f"Invalid header: {header[:4]}")
        return
    
    # Header length is at [4:8]
    header_len = struct.unpack(">I", data[4:8])[0]
    print(f"Header Length: {header_len}")
    
    # The laaaaaaaa... wait.
    # Mido's failure "data byte must be in range 0..127"
    # usually means it thinks it is in a MIDI message where it expects a data byte,
    # but it's actually at a position where the byte is >= 128.
    # This happens if the parser loses sync.
    
    # Let's just dump the first 100 bytes in hex to see what's happening
    print("\nFirst 100 bytes (hex):")
    print(data[:100].hex(' '))
    
    # Let's try to find all MTrk markers
    print("\nScanning for MTrk markers...")
    offset = 0
    track_count = 0
    while offset < len(data):
        if data[offset:offset+4] == b"MTrk":
            track_count += 1
            print(f"Track {track_count} found at offset {offset}")
            # Try to read length
            if offset + 8 <= len(data):
                length = struct.unpack(">I", data[offset+4:offset+8])[0]
                print(f"  Declared length: {length}")
        offset += 1
    print(f"Total MTrk markers found: {track_count}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_midi(sys.argv[1])
