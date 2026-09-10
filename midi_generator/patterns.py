"""A ready-made 4-bar musical pattern used by the CLI and tests.

Currently a plain list of NoteEvents. This is the data format that a future
higher-level pattern language will compile down to.
"""

from __future__ import annotations

from .midi_builder import NoteEvent


def four_bar_example() -> list[NoteEvent]:
    """A simple 4-bar 4/4 pattern: bass plus repeating chords."""
    return [
        # Bar 1: F1 bass with A3 + C4 chord
        NoteEvent("F1", start_beats=0.0, duration_beats=4.0, velocity=90),
        NoteEvent("A3", start_beats=0.0, duration_beats=4.0, velocity=100),
        NoteEvent("C4", start_beats=0.0, duration_beats=4.0, velocity=100),
        # Bar 2: A3 held, then C4 added (a "suspension-like" move)
        NoteEvent("A3", start_beats=4.0, duration_beats=2.0, velocity=100),
        NoteEvent("C4", start_beats=6.0, duration_beats=2.0, velocity=100),
        NoteEvent("F1", start_beats=6.0, duration_beats=1.0, velocity=85),
        NoteEvent("F1", start_beats=7.0, duration_beats=1.0, velocity=85),
        # Bar 3: D4 melody note with a low D2
        NoteEvent("D4", start_beats=8.0, duration_beats=1.5, velocity=110),
        NoteEvent("D2", start_beats=8.0, duration_beats=3.5, velocity=90),
        NoteEvent("D4", start_beats=10.0, duration_beats=0.5, velocity=95),
        # Bar 4: full chord on F
        NoteEvent("F2", start_beats=12.0, duration_beats=2.0, velocity=90),
        NoteEvent("F3", start_beats=12.0, duration_beats=2.0, velocity=95),
        NoteEvent("A3", start_beats=12.0, duration_beats=2.0, velocity=95),
        NoteEvent("C4", start_beats=12.0, duration_beats=2.0, velocity=95),
        NoteEvent("C5", start_beats=14.0, duration_beats=2.0, velocity=100),
    ]


LOGIC_TEST_TRACK_NAME = "Logic Test"


def logic_test_pattern() -> list[NoteEvent]:
    """A deliberately simple, visually readable 4-bar 4/4 pattern.

    Designed to be easy to verify by eye in Logic's Piano Roll:

    * Bar 1 -- whole-bar C1 sustained note + C major chord on beats 1 and 3
    * Bar 2 -- F major chord on beats 1 and 3
    * Bar 3 -- ascending quarter-note melody: D E F G
    * Bar 4 -- whole-bar A1 sustained note + A minor chord on beats 1 and 3
    """
    return [
        # Bar 1: sustained C1 (whole note) plus C major chord on beats 1 and 3
        NoteEvent("C1", start_beats=0.0, duration_beats=4.0, velocity=90),
        NoteEvent("C4", start_beats=0.0, duration_beats=1.0, velocity=100),
        NoteEvent("E4", start_beats=0.0, duration_beats=1.0, velocity=100),
        NoteEvent("G4", start_beats=0.0, duration_beats=1.0, velocity=100),
        NoteEvent("C4", start_beats=2.0, duration_beats=1.0, velocity=95),
        NoteEvent("E4", start_beats=2.0, duration_beats=1.0, velocity=95),
        NoteEvent("G4", start_beats=2.0, duration_beats=1.0, velocity=95),
        # Bar 2: F major chord on beats 1 and 3
        NoteEvent("F3", start_beats=4.0, duration_beats=1.0, velocity=100),
        NoteEvent("A3", start_beats=4.0, duration_beats=1.0, velocity=100),
        NoteEvent("C4", start_beats=4.0, duration_beats=1.0, velocity=100),
        NoteEvent("F3", start_beats=6.0, duration_beats=1.0, velocity=95),
        NoteEvent("A3", start_beats=6.0, duration_beats=1.0, velocity=95),
        NoteEvent("C4", start_beats=6.0, duration_beats=1.0, velocity=95),
        # Bar 3: ascending quarter-note melody
        NoteEvent("D4", start_beats=8.0, duration_beats=1.0, velocity=110),
        NoteEvent("E4", start_beats=9.0, duration_beats=1.0, velocity=100),
        NoteEvent("F4", start_beats=10.0, duration_beats=1.0, velocity=100),
        NoteEvent("G4", start_beats=11.0, duration_beats=1.0, velocity=110),
        # Bar 4: sustained A1 (whole note) plus A minor chord on beats 1 and 3
        NoteEvent("A1", start_beats=12.0, duration_beats=4.0, velocity=85),
        NoteEvent("A3", start_beats=12.0, duration_beats=2.0, velocity=95),
        NoteEvent("C4", start_beats=12.0, duration_beats=2.0, velocity=95),
        NoteEvent("E4", start_beats=12.0, duration_beats=2.0, velocity=95),
        NoteEvent("A3", start_beats=14.0, duration_beats=2.0, velocity=95),
        NoteEvent("C4", start_beats=14.0, duration_beats=2.0, velocity=95),
        NoteEvent("E4", start_beats=14.0, duration_beats=2.0, velocity=95),
    ]