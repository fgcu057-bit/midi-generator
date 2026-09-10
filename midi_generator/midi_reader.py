"""MIDI Reader engine for converting MIDI files to structured data and .pattern files.

This module implements the reverse of the MIDI builder: it reads Standard MIDI Files
and translates them into a structured representation compatible with the project's
pattern syntax.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import mido
from .note import midi_to_note
from .midi_builder import NoteEvent, Tempo, TimeSignature


@dataclass
class MidiFileInfo:
    """General metadata about a MIDI file."""
    file_path: str
    type: int
    ticks_per_beat: int
    tempo: Tempo
    time_signature: TimeSignature
    tracks: list[MidiTrackData] = field(default_factory=list)


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

    def __init__(self, file_path: str | Path):
        self.file_path = str(file_path)
        self.midi = mido.MidiFile(self.file_path)
        self._analyze_file()

    def _analyze_file(self) -> None:
        """Extract metadata and note events from the MIDI file."""
        # Defaults
        tempo = Tempo()
        time_sig = TimeSignature()
        
        # First pass: Find global tempo and time signature (usually in track 0)
        for track in self.midi.tracks:
            for msg in track:
                if msg.type == "set_tempo":
                    # mido.bpm2tempo(bpm) = 60000000 / bpm
                    # bpm = 60000000 / tempo
                    bpm = int(round(mido.tempo2bpm(msg.tempo)))
                    tempo = Tempo(bpm=bpm)
                elif msg.type == "time_signature":
                    time_sig = TimeSignature(
                        numerator=msg.numerator, 
                        denominator=msg.denominator
                    )
        
        # Second pass: Process tracks
        tracks_data: list[MidiTrackData] = []
        
        for i, track in enumerate(self.midi.tracks):
            track_name = f"Track {i + 1}"
            channel = 0
            program = 0
            
            # State for note pairing: pitch -> (start_tick, velocity)
            active_notes: dict[int, tuple[int, int]] = {}
            track_notes: list[NoteEvent] = []
            absolute_tick = 0
            
            for msg in track:
                absolute_tick += msg.time
                
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
                        
                        # Convert ticks to beats
                        start_beats = absolute_tick_to_beats(start_tick, self.midi.ticks_per_beat)
                        duration_beats = ticks_to_beats(duration_ticks, self.midi.ticks_per_beat)
                        
                        # Use the project's note labeling (Logic Pro convention)
                        pitch_label = midi_to_note(msg.note)
                        
                        track_notes.append(NoteEvent(
                            pitch=pitch_label,
                            start_beats=start_beats,
                            duration_beats=duration_beats,
                            velocity=velocity
                        ))
            
            # Clean up any hanging notes at the end of the track
            # (Not ideal, but better than ignoring them)
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
            tracks=tracks_data
        )

    def get_info(self) -> MidiFileInfo:
        """Return the analyzed MIDI file information."""
        return self.info


def absolute_tick_to_beats(tick: int, tpb: int) -> float:
    """Convert absolute ticks to beat position."""
    return tick / tpb


def ticks_to_beats(ticks: int, tpb: int) -> float:
    """Convert a duration in ticks to beat length."""
    return ticks / tpb
