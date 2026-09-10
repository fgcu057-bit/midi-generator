"""Note name conversion helpers.

Supports note names such as C4, F1, A3, including sharps (C#4) and flats
(Db4, Eb2, Bb1).

Note names use Logic Pro's octave numbering convention: C3 is middle C
(MIDI 60).
"""

from __future__ import annotations

import re

from dataclasses import dataclass

_NOTE_OFFSETS = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

_ACCIDENTAL_OFFSETS = {
    "b": -1,
    "#": 1,
}

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

_NOTE_RE = re.compile(
    r"^(?P<note>[A-Ga-g])(?P<accidental>bb|b|#|##)?(?P<octave>-?\d+)?$"
)


@dataclass(frozen=True)
class Note:
    """A musical note using Logic Pro's octave numbering convention."""

    name: str
    octave: int

    def __post_init__(self) -> None:
        if not _NOTE_RE.match(f"{self.name}{self.octave}"):
            raise ValueError(f"Invalid note name: {self.name}{self.octave}")

    @property
    def midi_pitch(self) -> int:
        return note_to_midi(f"{self.name}{self.octave}")

    @property
    def label(self) -> str:
        return f"{self.name}{self.octave}"

    def __str__(self) -> str:
        return self.label


def note_to_midi(note_name: str) -> int:
    """Convert a note name like ``C4`` to a MIDI pitch number.

    Uses Logic Pro's octave numbering: ``C3`` is middle C (MIDI 60),
    ``C4`` is MIDI 72, ``C-2`` is MIDI 0.
    """
    match = _NOTE_RE.match(note_name.strip())
    if not match:
        raise ValueError(f"Invalid note name: {note_name!r}. Expected e.g. C4, F#3, Db2.")

    letter = match.group("note").upper()
    accidental = match.group("accidental") or ""
    octave = int(match.group("octave") or "4")

    pitch = 12 * (octave + 2) + _NOTE_OFFSETS[letter]
    for symbol in accidental:
        pitch += _ACCIDENTAL_OFFSETS[symbol]

    if pitch < 0 or pitch > 127:
        raise ValueError(
            f"Note {note_name!r} is outside the MIDI range (0-127)."
        )
    return pitch


def midi_to_note(pitch: int) -> str:
    """Convert a MIDI pitch number to a note name like ``C4`` (Logic convention)."""
    if not isinstance(pitch, int) or pitch < 0 or pitch > 127:
        raise ValueError(f"MIDI pitch must be in range 0-127, got {pitch!r}.")

    name = _NOTE_NAMES[pitch % 12]
    octave = pitch // 12 - 2
    return f"{name}{octave}"