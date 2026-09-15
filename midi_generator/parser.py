"""Human-readable pattern language parser.

Parses a text pattern like::

    TEMPO 120
    TIME 4/4

    TRACK Piano

    BAR 1
    1.1: F1 + A3
    1.2: C4 velocity=100 duration=1/16

into a :class:`ParsedPattern` of structured musical events, which can be fed
straight into the existing :class:`MidiBuilder`.

Note names pass through :func:`midi_generator.note.note_to_midi` unchanged,
so they use Logic Pro's octave numbering convention exactly as the rest of
the project (C3 = MIDI 60, C4 = MIDI 72).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from .midi_builder import NoteEvent, Tempo, TimeSignature
from .note import note_to_midi

DEFAULT_VELOCITY = 100
DEFAULT_DURATION = Fraction(1, 4)  # one quarter note (one beat)

# Duration values supported: base note lengths plus their dotted versions.
_DURATION_BASES = (Fraction(1, 1), Fraction(1, 2), Fraction(1, 4), Fraction(1, 8), Fraction(1, 16), Fraction(1, 32))

# bar.beat position: "1.1", "2.4"; optional sixteenth sub-position: "1.1.2".
_POSITION_RE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?\s*:\s*(.+)$")
_SHORTHAND_RE = re.compile(r"^([A-Ga-g](?:##|bb|#|b)?-?\d+)\s+(\d+)\.(\d+)(?:\.(\d+))?\s+([\d./]+)$")
_NOTE_MEMBER_RE = re.compile(r"^[A-Ga-g](?:##|bb|#|b)?-?\d+$")
_DURATION_RE = re.compile(r"\bduration=([\d.]+/[\d.]+)")
_VELOCITY_RE = re.compile(r"\bvelocity=(\d+)\b")


class PatternError(Exception):
    """Pattern parse error carrying the source file and offending line number."""

    def __init__(self, line: int, message: str, source: str | None = None) -> None:
        self.line = line
        self.message = message
        self.source = source
        super().__init__(line, message)

    def __str__(self) -> str:
        where = f"{self.source}: " if self.source else ""
        return f"{where}Line {self.line}: {self.message}"


@dataclass(frozen=True)
class TrackPattern:
    """A single named track with its note events."""

    name: str
    notes: list[NoteEvent] = field(default_factory=list)


@dataclass
class ParsedPattern:
    """The structured result of parsing a pattern file."""

    tempo: Tempo = Tempo()
    time_signature: TimeSignature = TimeSignature()
    tracks: list[TrackPattern] = field(default_factory=list)

    def track_notes(self) -> dict[str, list[NoteEvent]]:
        """Return ``{track_name: [NoteEvent, ...]}`` in definition order."""
        return {track.name: list(track.notes) for track in self.tracks}


def parse_pattern(text: str) -> ParsedPattern:
    """Parse pattern source text into structured musical events."""
    tempo = Tempo()
    time_signature = TimeSignature()
    header_lines: list[tuple[int, str, list[str]]] = []  # (line, keyword, args)

    # First pass: split lines into headers and note-line groups per track.
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue

        upper = line.upper()
        if upper.startswith("TEMPO"):
            header_lines.append((line_no, "TEMPO", line.split()[1:]))
            continue
        if upper.startswith("TIME"):
            header_lines.append((line_no, "TIME", line.split()[1:]))
            continue
        if upper.startswith("BAR"):
            header_lines.append((line_no, "BAR", line.split()[1:]))
            continue
        if upper.startswith("TRACK"):
            header_lines.append((line_no, "TRACK", [line.split(None, 1)[1].strip()] if line.split(None, 1) else []))
            continue
        header_lines.append((line_no, "NOTE", [line]))

    # Apply tempo/time signature and track definitions in order.
    parsed = ParsedPattern()
    current_track: TrackPattern | None = None
    last_bar_in_track: dict[str, int] = {}
    # Track duplicate (same pitch, same absolute position) events per track:
    # key (start_beats, midi_pitch) -> (line_no).
    seen_notes: dict[str, dict[tuple[float, int], int]] = {}

    for line_no, keyword, args in header_lines:
        if keyword == "TEMPO":
            if len(args) != 1 or not args[0].isdigit():
                raise PatternError(line_no, "Expected format: TEMPO <beats-per-minute>, e.g. TEMPO 120")
            parsed.tempo = Tempo(bpm=int(args[0]))
        elif keyword == "TIME":
            if len(args) != 1 or "/" not in args[0]:
                raise PatternError(line_no, "Expected format: TIME <numerator>/<denominator>, e.g. TIME 4/4")
            numerator, denominator = args[0].split("/", 1)
            if not numerator.isdigit() or not denominator.isdigit():
                raise PatternError(line_no, "Expected format: TIME <numerator>/<denominator>, e.g. TIME 4/4")
            parsed.time_signature = TimeSignature(numerator=int(numerator), denominator=int(denominator))
        elif keyword == "TRACK":
            if not args or not args[0]:
                raise PatternError(line_no, "Expected a track name after TRACK, e.g. TRACK Piano")
            if args[0] in {t.name for t in parsed.tracks}:
                raise PatternError(line_no, f"Duplicate track name {args[0]!r}")
            current_track = TrackPattern(name=args[0])
            parsed.tracks.append(current_track)
        elif keyword == "BAR":
            if current_track is None:
                raise PatternError(line_no, "BAR line appears before any TRACK line")
            if len(args) != 1 or not args[0].isdigit():
                raise PatternError(line_no, "Expected format: BAR <number>, e.g. BAR 1")
            bar = int(args[0])
            if bar < 1:
                raise PatternError(line_no, f"Bar number must be >= 1, got {bar}")
            last = last_bar_in_track.get(current_track.name, 0)
            if bar <= last:
                raise PatternError(line_no, f"Bar {bar} is not after bar {last} in track {current_track.name!r}")
            last_bar_in_track[current_track.name] = bar
        elif keyword == "NOTE":
            if current_track is None:
                raise PatternError(line_no, "Note line appears before any TRACK line")
            bar_number = last_bar_in_track.get(current_track.name, 0)
            if bar_number == 0:
                raise PatternError(line_no, "Note line appears before any BAR line in this track")
            
            new_events = _parse_note_line(
                line_no, args[0], parsed.time_signature, bar_number, current_track.name
            )
            seen = seen_notes.setdefault(current_track.name, {})
            for event in new_events:
                key = (event.start_beats, note_to_midi(event.pitch))
                if key in seen:
                    first_line = seen[key]
                    position = _format_position(event.start_beats, parsed.time_signature.numerator)
                    if first_line == line_no:
                        raise PatternError(
                            line_no,
                            f"Duplicate note {event.pitch} at position {position} in the same chord",
                        )
                    raise PatternError(
                        line_no,
                        f"Conflicting note {event.pitch} at position {position} "
                        f"(already present on line {first_line})",
                    )
                seen[key] = line_no
            current_track.notes.extend(new_events)



    return parsed


def _parse_note_line(
    line_no: int,
    line: str,
    time_signature: TimeSignature,
    current_bar: int,
    track_name: str,
) -> list[NoteEvent]:
    """Parse a note line into NoteEvents for the given track.
    Supports both canonical "bar.beat: note-list" and shorthand "NOTE POSITION DURATION".
    """
    # Try canonical syntax first
    match = _POSITION_RE.match(line)
    if match:
        bar = int(match.group(1))
        beat = int(match.group(2))
        sub = int(match.group(3)) if match.group(3) is not None else 1
        rest = match.group(4)
        
        if bar != current_bar:
            raise PatternError(
                line_no, f"Position bar {bar} does not match the active BAR {current_bar} in track {track_name!r}"
            )
        
        velocity, duration, note_text = _extract_modifiers(line_no, rest)
        
        beats_per_bar = time_signature.numerator
        position_str = _position_token(bar, beat, sub)
        if not 1 <= beat <= beats_per_bar:
            raise PatternError(
                line_no,
                f"Position {position_str}: Beat {beat} is outside the 1..{beats_per_bar} range of "
                f"time signature {time_signature.numerator}/{time_signature.denominator}",
            )
        if not 1 <= sub <= 4:
            raise PatternError(
                line_no,
                f"Position {position_str}: Sixteenth sub-position {sub} is outside the 1..4 range "
                f"(a beat is 4 sixteenths)",
            )
        
        start_beats = float((bar - 1) * beats_per_bar + (beat - 1) + (sub - 1) * 0.25)
        duration_beats = float(duration * beats_per_bar)
        
        events: list[NoteEvent] = []
        for raw_name in note_text.split("+"):
            name = raw_name.strip()
            if not name:
                raise PatternError(line_no, "Empty note name before/after '+'")
            if not _NOTE_MEMBER_RE.match(name):
                raise PatternError(line_no, f"Invalid note name {name!r}")
            events.append(NoteEvent(pitch=name, start_beats=start_beats, duration_beats=duration_beats, velocity=velocity))
        return events

    # Try shorthand syntax: NOTE POSITION DURATION
    sh_match = _SHORTHAND_RE.match(line)
    if sh_match:
        pitch = sh_match.group(1)
        bar = int(sh_match.group(2))
        beat = int(sh_match.group(3))
        sub = int(sh_match.group(4)) if sh_match.group(4) is not None else 1
        duration_str = sh_match.group(5)
        
        if bar != current_bar:
            raise PatternError(
                line_no, f"Position bar {bar} does not match the active BAR {current_bar} in track {track_name!r}"
            )
            
        beats_per_bar = time_signature.numerator
        position_str = _position_token(bar, beat, sub)
        if not 1 <= beat <= beats_per_bar:
            raise PatternError(
                line_no,
                f"Position {position_str}: Beat {beat} is outside the 1..{beats_per_bar} range of "
                f"time signature {time_signature.numerator}/{time_signature.denominator}",
            )
        if not 1 <= sub <= 4:
            raise PatternError(
                line_no,
                f"Position {position_str}: Sixteenth sub-position {sub} is outside the 1..4 range "
                f"(a beat is 4 sixteenths)",
            )

        duration = _parse_duration(line_no, duration_str)
        start_beats = float((bar - 1) * beats_per_bar + (beat - 1) + (sub - 1) * 0.25)
        duration_beats = float(duration * beats_per_bar)
        
        return [NoteEvent(pitch=pitch, start_beats=start_beats, duration_beats=duration_beats, velocity=DEFAULT_VELOCITY)]

    raise PatternError(
        line_no,
        "Expected \"<bar>.<beat>: <notes>\", e.g. 1.2: C4 + E4, or shorthand \"NOTE POSITION DURATION\", e.g. A#4 1.1 1/4. "
        "Note lines must belong to a BAR section.",
    )


def _extract_modifiers(line_no: int, rest: str) -> tuple[int, Fraction, str]:
    """Extract ``velocity=NN`` / ``duration=FRAC`` and the remaining notes."""
    velocity = DEFAULT_VELOCITY
    duration: Fraction = DEFAULT_DURATION

    velocity_matches = _VELOCITY_RE.findall(rest)
    duration_matches = _DURATION_RE.findall(rest)

    if len(velocity_matches) > 1:
        raise PatternError(line_no, "Only one velocity= modifier allowed per line")
    if len(duration_matches) > 1:
        raise PatternError(line_no, "Only one duration= modifier allowed per line")

    note_text = rest

    if velocity_matches:
        velocity = int(velocity_matches[0])
        if not 0 <= velocity <= 127:
            raise PatternError(line_no, f"Velocity must be 0..127, got {velocity}")
        note_text = _VELOCITY_RE.sub("", note_text, count=1)

    if duration_matches:
        duration = _parse_duration(line_no, duration_matches[0])
        note_text = _DURATION_RE.sub("", note_text, count=1)

    return velocity, duration, note_text


def _parse_duration(line_no: int, token: str) -> Fraction:
    """Parse a duration token like 1/4 or 1/4. into a fraction of a whole note."""
    dotted = token.endswith(".")
    bare = token[:-1] if dotted else token
    if "/" not in bare:
        raise PatternError(line_no, f"Invalid duration {token!r}")
    numerator, denominator = bare.split("/", 1)
    try:
        base = Fraction(int(numerator), int(denominator))
    except ValueError:
        raise PatternError(line_no, f"Invalid duration {token!r}") from None
    if base not in _DURATION_BASES:
        raise PatternError(
            line_no, f"Unsupported duration {token!r}; use 1/1, 1/2, 1/4, 1/8, 1/16, 1/32 or dotted versions"
        )
    if base.numerator != 1:
        raise PatternError(line_no, f"Unsupported duration {token!r}; numerator must be 1")
    if dotted:
        base = base * Fraction(3, 2)
    return base


def _format_position(beats: float, beats_per_bar: int) -> str:
    """Format an absolute beat position as bar.beat (.sub when relevant)."""
    bar = int(beats // beats_per_bar) + 1
    rem = beats - (bar - 1) * beats_per_bar
    beat = int(rem) + 1
    sub = round((rem - int(rem)) * 4) + 1
    return _position_token(bar, beat, sub)


def _position_token(bar: int, beat: int, sub: int) -> str:
    """Format a bar/beat/sub tuple back into bar.beat (bar.beat.sub when relevant)."""
    if sub == 1:
        return f"{bar}.{beat}"
    return f"{bar}.{beat}.{sub}"


def parse_pattern_file(path: str | Path) -> ParsedPattern:
    """Parse a pattern file from disk.

    Errors carry the file path so they can identify the offending source line.
    """
    path = Path(path)
    try:
        return parse_pattern(path.read_text())
    except PatternError as exc:
        exc.source = str(path)
        raise