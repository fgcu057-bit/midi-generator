"""MIDI Reader engine for converting MIDI files to structured data and .pattern files.
This module implements the reverse of the MIDI builder: it reads Standard MIDI Files
and translates them into a structured representation compatible with the project's
pattern syntax.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any
import mido
from .note import midi_to_note
from .midi_builder_logic import NoteEvent, Tempo, TimeSignature

@dataclass
class MidiFileInfo:
    """General metadata about a MIDI file."""
    file_path: str
    type: int
    ticks_per_beat: int
    tempo: Tempo
    time_signature: TimeSignature
    tracks: list[MidiTrackData] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

@dataclass
class MidiTrackData:
    """Data for a single MIDI track."""
    name: str
    channel: int = 0
    program: int = 0
    notes: list[NoteEvent] = field(default_factory=list)
    note_count: int = 0

class MidiReader:
    """Reads MIDI files and converts them to project-specific musical structures."""

def read_vlq(data: bytes, ptr: int) -> tuple[int, int]:
    """Reads a Variable Length Quantity from data starting at ptr."""
    value = 0
    while ptr < len(data):
        b = data[ptr]
        value = (value << 7) | (b & 0x7F)
        ptr += 1
        if b < 0x80:
            return value, ptr
    raise EOFError("Unexpected end of data while reading VLQ")

class MidiReader:
    """Reads MIDI files and converts them to project-specific musical structures."""

    def __init__(self, file_path: str | Path):
        self.file_path = str(file_path)
        self.info = None
        
        try:
            # Try standard mido first for speed and correctness on valid files
            self.midi = mido.MidiFile(self.file_path)
            self._analyze_file()
        except OSError as e:
            if "data byte must be in range 0..127" in str(e):
                self._robust_analyze_file()
            else:
                raise RuntimeError(f"Unable to open MIDI file {self.file_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Unable to open MIDI file {self.file_path}: {e}")

    def _robust_analyze_file(self) -> None:
        """
        Read-only state-machine parser that handles malformed MIDI files.
        Excludes malformed events and reports them as warnings without modifying source bytes.
        """
        with open(self.file_path, "rb") as f:
            header = f.read(14)
            if len(header) < 14 or header[:4] != b'MThd':
                raise RuntimeError("Invalid MIDI file: Missing or truncated MThd header")
            
            # header[4:8] is header length (should be 6)
            header_len = int.from_bytes(header[4:8], 'big')
            format_type = int.from_bytes(header[8:10], 'big')
            tpb = int.from_bytes(header[10:14], 'big')
            
            class MockMidi:
                def __init__(self, t, p):
                    self.type = t
                    self.ticks_per_beat = p
                    self.tracks = []
            
            self.midi = MockMidi(format_type, tpb)
            tempo = Tempo()
            time_sig = TimeSignature()
            warnings: list[str] = []
            tracks_data: list[MidiTrackData] = []
            
            f.seek(0)
            f.read(14) # Skip header
            
            smf_track_idx = 0
            while True:
                chunk_id = f.read(4)
                if not chunk_id: break
                if chunk_id == b'MTrk':
                    smf_track_idx += 1
                    chunk_size_bytes = f.read(4)
                    if len(chunk_size_bytes) < 4:
                        warnings.append(f"MIDI READ WARNING: Truncated MTrk header for SMF track {smf_track_idx}")
                        break
                    chunk_size = int.from_bytes(chunk_size_bytes, 'big')
                    start_offset = f.tell()
                    track_data = f.read(chunk_size)
                    
                    if len(track_data) < chunk_size:
                        warnings.append(f"MIDI READ WARNING: SMF track {smf_track_idx} is truncated. Expected {chunk_size} bytes, got {len(track_data)}.")

                    track_name = f"Track {smf_track_idx}"
                    channel = 0
                    program = 0
                    active_notes: dict[int, tuple[int, int]] = {}
                    track_notes: list[NoteEvent] = []
                    absolute_tick = 0
                    running_status = None
                    
                    ptr = 0
                    while ptr < len(track_data):
                        abs_offset = start_offset + ptr
                        
                        # 1. Parse Delta Time (VLQ)
                        delta = 0
                        vlq_start_ptr = ptr
                        try:
                            delta, ptr = read_vlq(track_data, ptr)
                        except EOFError:
                            warnings.append(f"MIDI READ WARNING\nSMF Track Index: {smf_track_idx}\nAbsolute offset: {ptr}\nError: Truncated delta-time VLQ. Stopping track parsing.")
                            ptr = len(track_data)
                            break
                        
                        absolute_tick += delta
                        if ptr >= len(track_data): break
                        
                        # 2. Determine Status Byte
                        status = track_data[ptr]
                        if status < 0x80:
                            if running_status is None:
                                warnings.append(
                                    f"MIDI READ WARNING\nSMF Track Index: {smf_track_idx}\n"
                                    f"Track Name: {track_name}\n"
                                    f"Absolute offset: {abs_offset}\n"
                                    f"Tick: {absolute_tick}\n"
                                    f"Error: Data byte {hex(status)} found without status byte. "
                                    "Stopping track parsing due to ambiguous state."
                                )
                                ptr = len(track_data)
                                break
                            current_status = running_status
                        else:
                            current_status = status
                            ptr += 1
                            running_status = current_status
                        
                        event_start_ptr = ptr - (1 if status >= 0x80 else 0)
                        
                        # 3. Parse Event by Status
                        try:
                            if 0x80 <= current_status <= 0xBF:
                                # Channel Message
                                channel_num = current_status & 0x0F
                                status_type = current_status & 0xF0
                                
                                if status_type == 0xC0 or status_type == 0xD0:
                                    d_len = 1
                                else:
                                    d_len = 2
                                
                                data_bytes = []
                                malformed = False
                                for i in range(d_len):
                                    if ptr >= len(track_data):
                                        warnings.append(f"MIDI READ WARNING: Truncated channel event at offset {start_offset + ptr}")
                                        malformed = True
                                        break
                                    b = track_data[ptr]
                                    if b >= 0x80:
                                        event_type_name = {
                                            0x80: "Note Off", 0x90: "Note On", 0xA0: "Poly Pressure",
                                            0xB0: "Control Change", 0xC0: "Program Change", 
                                            0xD0: "Channel Pressure", 0xE0: "Pitch Bend"
                                        }.get(status_type, "Unknown")
                                        
                                        warnings.append(
                                            f"MIDI READ WARNING\nSMF Track Index: {smf_track_idx}\n"
                                            f"Track Name: {track_name}\n"
                                            f"Absolute offset: {start_offset + ptr}\n"
                                            f"Track-relative offset: {ptr - vlq_start_ptr}\n"
                                            f"Tick: {absolute_tick}\n"
                                            f"Delta-time: {delta}\n"
                                            f"Status: {hex(current_status)}\n"
                                            f"Event: {event_type_name}\n"
                                            f"Channel: {channel_num}\n"
                                            f"Data bytes already decoded: {' '.join(hex(x) for x in data_bytes)}\n"
                                            f"Invalid byte: {hex(b)} ({b})\n"
                                            f"Expected range: 0x00-0x7F\n"
                                            f"Raw event bytes: {' '.join(hex(x) for x in track_data[event_start_ptr:ptr+1])}\n"
                                            f"Action: malformed event excluded from musical data. "
                                            "Stopping track parsing due to ambiguous state.\n"
                                            f"Source bytes modified: NO"
                                        )
                                        malformed = True
                                        break
                                    data_bytes.append(b)
                                    ptr += 1
                                
                                if not malformed:
                                    if status_type == 0x90 and data_bytes[1] > 0:
                                        channel = channel_num
                                        active_notes[data_bytes[0]] = (absolute_tick, data_bytes[1])
                                    elif status_type == 0x80 or (status_type == 0x90 and data_bytes[1] == 0):
                                        if data_bytes[0] in active_notes:
                                            start_tick, vel = active_notes.pop(data_bytes[0])
                                            track_notes.append(NoteEvent(
                                                pitch=midi_to_note(data_bytes[0]),
                                                start_beats=absolute_tick_to_beats(start_tick, tpb),
                                                duration_beats=ticks_to_beats(absolute_tick - start_tick, tpb),
                                                velocity=vel
                                            ))
                                    elif status_type == 0xC0:
                                        program = data_bytes[0]
                                elif malformed:
                                    ptr = len(track_data)
                                    break
                                
                            elif current_status == 0xFF:
                                # Meta Event
                                try:
                                    meta_len, ptr = read_vlq(track_data, ptr)
                                    meta_data = track_data[ptr : ptr + meta_len]
                                    ptr += meta_len
                                    
                                    if not meta_data:
                                        continue
                                    
                                    meta_type = meta_data[0]
                                    if meta_type == 0x03: # Track Name
                                        track_name = meta_data[1:].decode('utf-8', errors='replace')
                                    elif meta_type == 0x51: # Tempo
                                        if len(meta_data) >= 4:
                                            us_per_qn = int.from_bytes(meta_data[1:4], 'big')
                                            bpm = 60000000 / us_per_qn
                                            tempo = Tempo(bpm=int(round(bpm)))
                                    elif meta_type == 0x58: # Time Signature
                                        if len(meta_data) >= 4:
                                            num = meta_data[1]
                                            den = meta_data[2]
                                            time_sig = TimeSignature(numerator=num, denominator=den)
                                    elif meta_type == 0x2F: # End of Track
                                        ptr = len(track_data)
                                except EOFError:
                                    warnings.append(f"MIDI READ WARNING: Truncated meta event at offset {start_offset + ptr}")
                                    ptr = len(track_data)

                            elif current_status == 0xF0:
                                # SysEx
                                while ptr < len(track_data) and track_data[ptr] != 0xF7:
                                    ptr += 1
                                ptr += 1
                                
                            else:
                                if current_status == 0xF1: # Tune Request
                                    ptr += 1
                                elif current_status == 0xF2: # System Common Event
                                    ptr += 2
                                elif current_status == 0xF3: # Song Position Pointer
                                    try:
                                        _, ptr = read_vlq(track_data, ptr)
                                    except EOFError: ptr = len(track_data)
                                elif current_status == 0xF6: # System Reset
                                    ptr += 1
                                else:
                                    warnings.append(f"MIDI READ WARNING: Unknown system status {hex(current_status)} at offset {start_offset + ptr}. Stopping track parsing.")
                                    ptr = len(track_data)
                                    break
                        except Exception as e:
                            warnings.append(f"Unexpected error parsing event at offset {start_offset + ptr}: {e}. Stopping track parsing.")
                            ptr = len(track_data)
                            break

                    # Finalize hanging notes
                    for pitch, (start_tick, vel) in active_notes.items():
                        track_notes.append(NoteEvent(
                            pitch=midi_to_note(pitch),
                            start_beats=absolute_tick_to_beats(start_tick, tpb),
                            duration_beats=ticks_to_beats(absolute_tick - start_tick, tpb),
                            velocity=vel
                        ))

                    tracks_data.append(MidiTrackData(
                        name=track_name,
                        channel=channel,
                        program=program,
                        notes=track_notes,
                        note_count=len(track_notes)
                    ))
                    running_status = None

        self.info = MidiFileInfo(
            file_path=self.file_path,
            type=format_type,
            ticks_per_beat=tpb,
            tempo=tempo,
            time_signature=time_sig,
            tracks=tracks_data,
            warnings=warnings
        )



    def _analyze_file(self) -> None:
        tempo = Tempo()
        time_sig = TimeSignature()
        warnings: list[str] = []
        
        # Pass 1: Global Timing/Metadata
        for track in self.midi.tracks:
            for msg in track:
                if msg.type == "set_tempo":
                    bpm = int(round(mido.tempo2bpm(msg.tempo)))
                    tempo = Tempo(bpm=bpm)
                elif msg.type == "time_signature":
                    time_sig = TimeSignature(
                        numerator=msg.numerator, 
                        denominator=msg.denominator
                    )
        
        # Pass 2: Track Processing
        tracks_data: list[MidiTrackData] = []
        for i, track in enumerate(self.midi.tracks):
            track_name = f"Track {i + 1}"
            channel = 0
            program = 0
            active_notes: dict[int, tuple[int, int]] = {}
            track_notes: list[NoteEvent] = []
            absolute_tick = 0
            
            for j, msg in enumerate(track):
                absolute_tick += msg.time
                
                try:
                    if msg.type == "track_name":
                        track_name = msg.name
                    elif msg.type == "program_change":
                        program = msg.program
                    elif msg.type == "note_on" and msg.velocity > 0:
                        channel = msg.channel
                        active_notes[msg.note] = (absolute_tick, msg.velocity)
                    elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                        if msg.note in active_notes:
                            start_tick, velocity = active_notes.pop(msg.note)
                            duration_ticks = absolute_tick - start_tick
                            
                            start_beats = absolute_tick_to_beats(start_tick, self.midi.ticks_per_beat)
                            duration_beats = ticks_to_beats(duration_ticks, self.midi.ticks_per_beat)
                            pitch_label = midi_to_note(msg.note)
                            
                            track_notes.append(NoteEvent(
                                pitch=pitch_label,
                                start_beats=start_beats,
                                duration_beats=duration_beats,
                                velocity=velocity
                            ))
                        else:
                            warnings.append(f"Track {i}, Event {j}: Note-off without Note-on for pitch {msg.note} at tick {absolute_tick}")
                except Exception as e:
                    warnings.append(f"Track {i}, Event {j}: Error processing message {msg} - {e}")

            # Cleanup hanging notes
            for pitch, (start_tick, velocity) in active_notes.items():
                start_beats = absolute_tick_to_beats(start_tick, self.midi.ticks_per_beat)
                duration_beats = ticks_to_beats(absolute_tick - start_tick, self.midi.ticks_per_beat)
                track_notes.append(NoteEvent(
                    pitch=midi_to_note(pitch),
                    start_beats=start_beats,
                    duration_beats=duration_beats,
                    velocity=velocity
                ))

            tracks_data.append(MidiTrackData(
                name=track_name,
                channel=channel,
                program=program,
                notes=track_notes,
                note_count=len(track_notes)
            ))

        self.info = MidiFileInfo(
            file_path=self.file_path,
            type=self.midi.type,
            ticks_per_beat=self.midi.ticks_per_beat,
            tempo=tempo,
            time_signature=time_sig,
            tracks=tracks_data,
            warnings=warnings
        )

    def get_info(self) -> MidiFileInfo:
        return self.info

def absolute_tick_to_beats(tick: int, tpb: int) -> float:
    return tick / tpb

def ticks_to_beats(ticks: int, tpb: int) -> float:
    return ticks / tpb
