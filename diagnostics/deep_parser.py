import struct
import sys

def read_vlq(data, pos):
    delta = 0
    shift = 0
    while True:
        if pos >= len(data):
            return None, pos
        byte = data[pos]
        delta |= (byte & 0x7f) << shift
        pos += 1
        if not (byte & 0x80):
            break
        shift += 7
        if shift > 28:
            return None, pos
    return delta, pos

def deep_parse_midi(file_path):
    print(f"Deep Analysis: {file_path}")
    try:
        with open(file_path, "rb") as f:
            data = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    if len(data) < 14 or data[:4] != b"MThd":
        print("Invalid MIDI header")
        return

    header_len = struct.unpack(">I", data[4:8])[0]
    fmt = struct.unpack(">H", data[8:10])[0]
    num_tracks = struct.unpack(">H", data[10:12])[0]
    division = struct.unpack(">I", data[12:16])[0]
    print(f"Header: Type {fmt}, Tracks {num_tracks}, PPQ {division}")

    offset = 14
    for t_idx in range(num_tracks):
        if offset >= len(data): break
        if data[offset:offset+4] != b"MTrk":
            print(f"Unexpected byte at {offset}, expected MTrk")
            break
        
        chunk_len = struct.unpack(">I", data[offset+4:offset+8])[0]
        track_start = offset + 8
        track_end = track_start + chunk_len
        
        print(f"\n--- Track {t_idx} (Offset: {offset}, Len: {chunk_len}) ---")
        
        pos = track_start
        absolute_tick = 0
        event_idx = 0
        running_status = None
        
        while pos < track_end and pos < len(data):
            start_pos = pos
            
            # 1. Delta Time
            delta, pos = read_vlq(data, pos)
            if delta is None:
                print(f"CRITICAL FAILURE: Invalid VLQ delta at pos {start_pos}")
                print(f"Bytes around failure: {data[max(0, pos-10):pos+10].hex(' ')}")
                return
            
            absolute_tick += delta
            
            # 2. Status Byte
            if pos >= len(data): break
            status = data[pos]
            
            # Handle Running Status
            current_status = status
            if status < 0x80:
                if running_status is None:
                    print(f"CRITICAL FAILURE: Running status used before any status byte at pos {pos}")
                    print(f"Bytes around failure: {data[max(0, pos-10):pos+10].hex(' ')}")
                    return
                current_status = running_status
                # status byte was actually a data byte, do not increment pos
                pos -= 1 
            else:
                running_status = status
                pos += 1
            
            # 3. Event Processing
            event_type = ""
            try:
                if current_status == 0xFF: # Meta
                    if pos >= len(data): raise ValueError("Truncated meta type")
                    meta_type = data[pos]
                    pos += 1
                    m_len, pos = read_vlq(data, pos)
                    if m_len is None: raise ValueError("Truncated meta length")
                    pos += m_len
                    event_type = f"META(type={meta_type})"
                elif current_status == 0xFA: # SysEx Start
                    # Find end 0xFF
                    found = False
                    while pos < len(data):
                        if data[pos] == 0xFF:
                            pos += 1
                            found = True
                            break
                        pos += 1
                    if not found: raise ValueError("Truncated SysEx")
                    event_type = "SYSEX"
                elif (current_status & 0xF0) == 0x90: # Note On
                    if pos + 1 >= len(data): raise ValueError("Truncated NoteOn")
                    p, v = data[pos], data[pos+1]
                    if p >= 128 or v >= 128:
                        print(f"CRITICAL FAILURE: Invalid data byte in NoteOn at pos {pos}")
                        print(f"Note: {p}, Vel: {v}")
                        print(f"Bytes around: {data[max(0, pos-10):pos+10].hex(' ')}")
                        return
                    pos += 2
                    event_type = f"NoteOn(p={p}, v={v})"
                elif (current_status & 0xF0) == 0x80: # Note Off
                    if pos + 1 >= len(data): raise ValueError("Truncated NoteOff")
                    p, v = data[pos], data[pos+1]
                    if p >= 128 or v >= 128:
                        print(f"CRITICAL FAILURE: Invalid data byte in NoteOff at pos {pos}")
                        print(f"Note: {p}, Vel: {v}")
                        print(f"Bytes around: {data[max(0, pos-10):pos+10].hex(' ')}")
                        return
                    pos += 2
                    event_type = f"NoteOff(p={p}, v={v})"
                elif (current_status & 0xF0) == 0xB0: # CC
                    if pos + 1 >= len(data): raise ValueError("Truncated CC")
                    c, v = data[pos], data[pos+1]
                    if c >= 128 or v >= 128:
                        print(f"CRITICAL FAILURE: Invalid data byte in CC at pos {pos}")
                        print(f"Ctrl: {c}, Val: {v}")
                        print(f"Bytes around: {data[max(0, pos-10):pos+10].hex(' ')}")
                        return
                    pos += 2
                    event_type = f"CC(c={c}, v={v})"
                elif (current_status & 0xF0) == 0xC0: # Prog Change
                    if pos >= len(data): raise ValueError("Truncated ProgChange")
                    p = data[pos]
                    if p >= 128:
                        print(f"CRITICAL FAILURE: Invalid data byte in ProgChange at pos {pos}")
                        print(f"Prog: {p}")
                        print(f"Bytes around: {data[max(0, pos-10):pos+10].hex(' ')}")
                        return
                    pos += 1
                    event_type = f"ProgChange(p={p})"
                elif (current_status & 0xF0) == 0xD0: # Channel Aftertouch
                    if pos >= len(data): raise ValueError("Truncated Aftertouch")
                    v = data[pos]
                    if v >= 128:
                        print(f"CRITICAL FAILURE: Invalid data byte in Aftertouch at pos {pos}")
                        print(f"Val: {v}")
                        print(f"Bytes around: {data[max(0, pos-10):pos+10].hex(' ')}")
                        return
                    pos += 1
                    event_type = "ChannelAftertouch"
                elif (current_status & 0xF0) == 0xE0: # Pitch Bend
                    if pos + 1 >= len(data): raise ValueError("Truncated PitchBend")
                    v1, v2 = data[pos], data[pos+1]
                    if v1 >= 128 or v2 >= 128:
                        print(f"CRITICAL FAILURE: Invalid data byte in PitchBend at pos {pos}")
                        print(f"V1: {v1}, V2: {v2}")
                        print(f"Bytes around: {data[max(0, pos-10):pos+10].hex(' ')}")
                        return
                    pos += 2
                    event_type = "PitchBend"
                elif current_status == 0xF0: # System Common / Realtime
                    # Simplified: just skip one byte or handle specifically
                    pos += 1
                    event_type = "SystemCommon"
                else:
                    print(f"Unknown status byte 0x{current_status:02x} at pos {pos}")
                    return
            except Exception as e:
                print(f"Unexpected parsing error at pos {pos}: {e}")
                return

            print(f"Ev {event_idx} | Tick {absolute_tick} | Delta {delta} | {event_type}")
            event_idx += 1
        
        offset = track_end

if __name__ == "__main__":
    if len(sys.argv) > 1:
        deep_parse_midi(sys.argv[1])
