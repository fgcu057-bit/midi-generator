"""Build Standard MIDI Files using Mido.

Takes a list of note events (pitch, start beat, duration in beats, velocity)
plus tempo and time signature and writes a valid ``.mid`` file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping, NamedTuple, Optional

from mido import MidiFile, MidiTrack, MetaMessage, Message, bpm2tempo

from .note import note_to_midi


class NoteEvent(NamedTuple):
    """One MIDI note. ``pitch`` may be an int MIDI number or a note name like "C4"."""

    pitch: int | str
    start_beats: float
    duration_beats: float
    velocity: int = 100


class Tempo(NamedTuple):
    """Tempo marker. ``bpm`` is the default value (120)."""

    bpm: int = 120
    position_beats: float = 0.0


class TimeSignature(NamedTuple):
    """Time signature. Defaults to 4/4 at beat 0."""

    numerator: int = 4
    denominator: int = 4
    position_beats: float = 0.0


class ProgramChange(NamedTuple):
    """Optional program (instrument) change event."""

    program: int = 0
    position_beats: float = 0.0


class MidiBuilder:
    """Builds a type-1 MIDI file with one track holding all note events."""

    def __init__(
        self,
        tempo: Tempo = Tempo(),
        time_signature: TimeSignature = TimeSignature(),
        program_changes: Iterable[ProgramChange] = (),
    ) -> None:
        self.tempo = tempo
        self.time_signature = time_signature
        self.program_changes = tuple(program_changes)

    def build(
        self,
        notes: Iterable[NoteEvent],
        ticks_per_beat: int = 480,
        output_path: Optional[str | Path] = None,
        track_name: str = "MIDI 1",
    ) -> MidiFile:
        """Create and return a MidiFile from note events.

        If ``output_path`` is given, the file is also saved there.
        """
        resolution = int(ticks_per_beat)

        midi = MidiFile(ticks_per_beat=resolution, type=1)
        track = MidiTrack()
        midi.tracks.append(track)

        track.append(MetaMessage("track_name", name=track_name, time=0))
        track.append(
            MetaMessage(
                "time_signature",
                numerator=self.time_signature.numerator,
                denominator=self.time_signature.denominator,
                time=0,
            )
        )
        track.append(MetaMessage("set_tempo", tempo=bpm2tempo(self.tempo.bpm), time=0))

        self._append_note_events(track, notes, resolution)

        if output_path is not None:
            midi.save(str(output_path))
        return midi

    def build_multi_track(
        self,
        tracks: Mapping[str, Iterable[NoteEvent]],
        ticks_per_beat: int = 480,
        output_path: Optional[str | Path] = None,
    ) -> MidiFile:
        """Create a type-1 MidiFile with one track per entry in ``tracks``.
        
        ``tracks`` maps a track name to its note events (insertion order is
        preserved). Global tempo/time-signature markers are written on the
        first track, which is what DAWs expect.
        """
        resolution = int(ticks_per_beat)

        midi = MidiFile(ticks_per_beat=resolution, type=1)
        for index, (track_name, notes) in enumerate(tracks.items()):
            track = MidiTrack()
            midi.tracks.append(track)

            track.append(MetaMessage("track_name", name=track_name, time=0))
            if index == 0:
                track.append(
                    MetaMessage(
                        "time_signature",
                        numerator=self.time_signature.numerator,
                        denominator=self.time_signature.denominator,
                        time=0,
                    )
                )
                track.append(MetaMessage("set_tempo", tempo=bpm2tempo(self.tempo.bpm), time=0))

            self._append_note_events(track, notes, resolution, channel=index % 16)

        if output_path is not None:
            midi.save(str(output_path))
        return midi

    def _append_note_events(
        self,
        track: MidiTrack,
        notes: Iterable[NoteEvent],
        resolution: int,
        channel: int = 0,
    ) -> None:
        notes = [self._coerce_note(n) for n in notes]

        # Build one absolute-tick event list, sort it, and emit with delta times.
        events: list[tuple[int, str, dict]] = []
        for change in self.program_changes:
            tick = self._beats_to_ticks(change.position_beats, resolution)
            events.append((tick, "program", {"program": change.program}))

        for note in notes:
            on_tick = self._beats_to_ticks(note.start_beats, resolution)
            off_tick = self._beats_to_ticks(note.start_beats + note.duration_beats, resolution)
            events.append(
                (on_tick, "note", {"type": "note_on", "note": note.pitch, "velocity": note.velocity})
            )
            events.append(
                (off_tick, "note", {"type": "note_off", "note": note.pitch, "velocity": 0})
            )

        events.sort(key=lambda e: (e[0], self._event_order(e)))

        prev_tick = 0
        for tick, kind, data in events:
            delta = max(0, tick - prev_tick)
            prev_tick = tick
            if kind == "program":
                track.append(Message("program_change", channel=channel, time=delta, **data))
            else:
                track.append(Message(data["type"], channel=channel, time=delta, **{k: v for k, v in data.items() if k != "type"}))

        # End of track with a small tail so the last note-off is always included.
        end_tick = max(events, key=lambda e: e[0])[0] + resolution if events else 4 * resolution
        track.append(MetaMessage("end_of_track", time=max(0, end_tick - prev_tick)))

    @staticmethod
    def _coerce_note(note: NoteEvent) -> NoteEvent:
        if isinstance(note.pitch, int):
            return note
        return NoteEvent(note_to_midi(note.pitch), note.start_beats, note.duration_beats, note.velocity)

    @staticmethod
    def _beats_to_ticks(beats: float, resolution: int) -> int:
        return max(0, round(beats * resolution))

    @staticmethod
    def _event_order(event: tuple[int, str, dict]) -> int:
        # Note-offs sort before note-ons at the same tick so a new note on the
        # same pitch does not get instantly cut off by the previous note's tail.
        if event[1] == "note" and event[2].get("type") == "note_off":
            return 0
        if event[1] == "note" and event[2].get("type") == "note_on":
            return 10
        return 5