"""Occurrence octave diagnostic.

Generates a tiny MIDI file with exactly five single notes whose raw MIDI
pitch numbers are 24, 36, 48, 60 and 72, at clearly separated positions,
all with the same velocity and duration.

It then prints each pitch alongside the note name produced by the current
note-naming code (midi_to_note). We intentionally make NO assumption about
which octave convention is "correct" -- Logic Pro's displayed names are the
reference to be compared against.

Run from the project root:
    python diagnostics/octave_diag.py
(or) python -m diagnostics.octave_diag
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mido import MidiFile

from midi_generator import MidiBuilder, Tempo, midi_to_note
from midi_generator.midi_builder import NoteEvent, TimeSignature

DIAG_NOTES = [24, 36, 48, 60, 72]
VELOCITY = 100
DURATION_BEATS = 1.0
SEPARATION_BEATS = 2.0  # one note every two beats

OUTPUT_PATH = Path("output/octave_diag.mid")


def main() -> int:
    notes: list[NoteEvent] = []
    for index, pitch in enumerate(DIAG_NOTES):
        notes.append(
            NoteEvent(
                pitch=pitch,
                start_beats=index * SEPARATION_BEATS,
                duration_beats=DURATION_BEATS,
                velocity=VELOCITY,
            )
        )

    builder = MidiBuilder(tempo=Tempo(bpm=120), time_signature=TimeSignature(4, 4))
    builder.build(notes, ticks_per_beat=480, output_path=OUTPUT_PATH, track_name="Octave Diagnostic")

    # Report the exact content of the generated file.
    print("Octave diagnostic written to:", OUTPUT_PATH)
    print("Tempo: 120 BPM | 4/4 | 480 PPQ | velocity: 100 | duration: 1 beat")
    print()
    print(" Raw MIDI   current Python note name  (midi_to_note)")
    print(" pitch")
    print("-" * 52)
    for _index, pitch in enumerate(DIAG_NOTES):
        name = midi_to_note(pitch)
        print(f"   {pitch:3d}         {name:>12}")

    print()
    print("Verification -- actual events in file:")
    midi = MidiFile(OUTPUT_PATH)
    running = 0
    for msg in midi.tracks[0]:
        running += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            print(f"  tick {running:5d}  pitch {msg.note:3d}  velocity {msg.velocity:3d}  "
                  f"note name {midi_to_note(msg.note)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())