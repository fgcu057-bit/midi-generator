import mido
from midi_generator.midi_builder import MidiBuilder, NoteEvent, Tempo, TimeSignature

def create_test_midi(path, note_durations, name="test"):
    builder = MidiBuilder(Tempo(120), TimeSignature(4, 4))
    notes = []
    start = 0.0
    for dur in note_durations:
        notes.append(NoteEvent("C3", start, dur, 100))
        start += dur
    builder.build(notes, output_path=path, track_name=name)

# Experiment 1: Exactly 1/16 notes (like melody1)
create_test_midi("output/exp_16th.mid", [0.25] * 32, "16ths")
# Experiment 2: Slightly longer notes (1/16 + 0.01)
create_test_midi("output/exp_long.mid", [0.26] * 32, "slightly_longer")
# Experiment 3: Slightly shorter notes (1/16 - 0.01)
create_test_midi("output/exp_short.mid", [0.24] * 32, "slightly_shorter")
