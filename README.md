# MIDI Generator

A deliberately simple, deterministic Python tool that compiles handwritten
**arrangement files** into real **Standard MIDI Files (.mid)**. Import the `.mid`
into Logic Pro (or any DAW): it appears as normal, fully editable MIDI regions.

This tool has no musical intelligence. It never interprets, invents, or rewrites
your notes. You write the arrangement; it writes the file. The same input
always produces the same output.

- No GUI, no AI, no network access, no extra services.
- Only two Python dependencies: `mido` (MIDI I/O) and `pytest` (tests).
- Nothing else is needed for normal operation.

## Installation

Requires **Python 3.10+**. One-time setup:

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# 2. Install the two dependencies
pip install -r requirements.txt
```

That is the entire installation.

## How to run the generator

Compile an arrangement file into a MIDI file:

```bash
python generate.py arrangements/song_01.pattern
# writes output/song_01.mid
```

Turn one of the bundled samples into MIDI (the only operating mode that needs
no arguments):

```bash
python generate.py
# writes output/example.mid
```

### How output filenames are determined

The output filename is **derived from the input filename**: the directory part
of the input is stripped and its stem is used, so

```
python generate.py arrangements/piano_intro.pattern   -> output/piano_intro.mid
python generate.py arrangements/song_01.pattern       -> output/song_01.mid
python generate.py any/where/else/my_song.pattern     -> output/my_song.mid
```

Override it explicitly with `-o`:

```bash
python generate.py arrangements/song_01.pattern -o output/custom.mid
```

`output/` is created automatically if it does not exist.

### Full option list

```
usage: generate.py [-h] [-p {example,logic-test}] [--pattern-file PATTERN_FILE]
                   [-o OUTPUT] [--bpm BPM] [--ticks-per-beat TPB]
                   [arrangement]

positional arguments:
  arrangement           Path to a .pattern arrangement file (see arrangements/).

optional arguments:
  -h, --help            show this help message and exit
  -p, --pattern         built-in demo pattern (example | logic-test)
  --pattern-file        deprecated alias for the positional arrangement path
  -o, --output          output .mid path (overrides the derived default)
  --bpm                 tempo for built-in patterns only (default: 120)
  --ticks-per-beat      PPQ resolution (default: 480)
```

`--bpm` only affects the built-in demo patterns. An arrangement file carries its
own tempo; the file always wins.

## The `.pattern` arrangement syntax

An arrangement is a plain text file. It must contain everything needed to
reproduce the MIDI: tempo, time signature, tracks, bars, notes, positions,
velocities, and durations. Whitespace and blank lines are ignored.

### Grammar

```
TEMPO 120                          # beats per minute (default 120)
TIME 4/4                           # time signature (default 4/4)

TRACK Bass                         # start a track (name required)

BAR 1                              # bar number (must increase per track)
1.1: F1                            # beat 1
1.3: A1 duration=1/2               # beat 3, half note

BAR 2
2.1: C4 + E4 + G4 velocity=95      # chord on beat 1
2.2.3: B4 duration=1/16            # beat 2, subdivision 3 = a sixteenth

TRACK Chords                       # a second track (type-1 MIDI file)
BAR 1
1.1: C3 duration=1/1 velocity=70
```

Simple rule list:

- `TEMPO <bpm>` — whole number, optional, default **120**. Must appear before
  any notes that need it (put it at the top of the file).
- `TIME <num>/<den>` — optional, default **4/4**. One bar has `num` beats.
- `TRACK <name>` — starts a (new) MIDI track. Track names must be unique. All
  lines that follow belong to this track until the next `TRACK`. Multiple
  tracks produce a type-1 MIDI file, one track each.
- `BAR <n>` — opens bar `n` for the current track. Bar numbers must be positive
  and strictly increasing within a track.
- `<bar>.<beat>: <notes>` — place notes at `bar`/`beat`.
- `<bar>.<beat>.<sub>: <notes>` — place notes at sixteenth subdivision `sub`
  (a fraction within the beat), see *Positions* below.
- `<notes>` — one note name, or a chord joined by `+`: `C4 + E4 + G4`. The `+`
  sign is only allowed in note lines.

### Positions: bar, beat, and sixteenth subdivision

- `1.1` = bar 1, beat 1.
- `1.4` = bar 1, beat 4.
- For notes that fall between principal beats you can add a third number:
  `1.2.3` = bar 1, beat 2, **subdivision 3**. Each beat is split into four
  subdivisions (sub 1 through 4), one subdivision = 1/4 beat = one sixteenth
  note. The position of a note is measured from the bar's downbeat:

  ```
  1.1.1  =  beat 1            (subdivision 1)
  1.1.2  =  beat 1 + 1/4 beat (second sixteenth)
  1.1.3  =  beat 1 + 1/2 beat (third sixteenth)
  1.1.4  =  beat 1 + 3/4 beat (fourth sixteenth)
  1.2.1  =  beat 2
  ...and so on.
  ```

  `beat` must be between 1 and the bar length; `sub` between 1 and 4. A note
  whose bar is `n` must be written inside a `BAR n` block.

### Chords

Join simultaneous notes with `+`:

```
1.1: C4 + E4 + G4
LH:
2.1: F1 + F2
```

All members of a chord start at exactly the same position. Modifiers after the
chord apply to every member.

### Velocity

```
1.1: C4 velocity=100
```

Range **0..127** (MIDI standard; 0 = no sound). Default is **100**.

### Duration

```
1.1: C4 duration=1/4
1.2: C4 duration=1/8
1.3: C4 duration=1/16
```

Durations are fractions of a whole note. Supported values:

| Token   | Length                       |
| ------- | ---------------------------- |
| `1/1`   | whole note (4 beats in 4/4)  |
| `1/2`   | half note (2 beats)          |
| `1/4`   | quarter note (1 beat)        |
| `1/8`   | eighth note (1/2 beat)       |
| `1/16`  | sixteenth (1/4 beat)         |
| `1/32`  | thirty-second (1/8 beat)     |

Dotted versions are supported by appending a dot: `1/4.` = 1.5 beats,
`1/8.` = 3/4 beat, and so on. Default duration is **1/4** (one beat).

Both modifiers can be combined on any order:

```
1.1: C4 duration=1/8 velocity=90
```

### Multiple tracks

Use one `TRACK <name>` line per track:

```
TRACK Bass
BAR 1
1.1: F1 duration=1/1

TRACK Chords
BAR 1
1.1: C4 + E4 + G4 duration=1/2
1.3: A3 + C4 + E4 duration=1/2
```

The output is a type-1 MIDI file with one named track per `TRACK` declaration
(see `arrangements/two_instruments.pattern` for a complete example).

### Logic Pro octave numbering

Note names follow **Logic Pro's octave convention**, where middle C is C3:

| Note name | MIDI number |
| --------- | ----------- |
| C-2       | 0           |
| C0        | 24          |
| C1        | 36          |
| C2        | 48          |
| C3        | 60          |
| C4        | 72          |
| G8        | 127 (max)   |

The formula is `MIDI = 12 * (octave + 2) + offset`. Sharps and flats are
supported: `C#4`, `Db4`. **What you write is what Logic's Piano Roll shows** —
there is no octave offset hiding anywhere.

The valid range is C-2 (MIDI 0) through G8 (MIDI 127). Out-of-range or unknown
names are rejected at compile time.

### Validation and error reporting

The parser rejects malformed files before anything is written. Errors name the
**source file and line number** of the offending line, for example:

```
Error: arrangements/song_01.pattern: Line 14: Invalid note name 'H4'
Error: arrangements/song_01.pattern: Line 9: Beat 5 is outside the 1..4 range of time signature 4/4
Error: arrangements/song_01.pattern: Line 6: Conflicting note C4 at position 1.1 (already present on line 5)
```

Checked on every run:

- invalid note names (`H4`) and out-of-range octaves (`C-3`)
- invalid positions (beat beyond the time signature, subdivision < 1 or > 4,
  bar/beat numbers that are not integers)
- invalid durations (unknown fraction like `1/7`, numerator other than 1)
- invalid velocities (outside 0..127)
- malformed chords (empty members, e.g. `C4 +`; unknown modifier placement)
- duplicate or conflicting events (the same pitch at the same position on the
  same track, including in the same chord)
- invalid bar values (0/negative, non-increasing within a track)
- malformed track declarations (missing name, duplicate track names)

Validation is deterministic: a given file either compiles to one stable result
or fails with a precise message. Nothing is guessed.

## How to create a new arrangement

1. Copy a sample to a new name in `arrangements/`:
   ```bash
   cp arrangements/example.pattern arrangements/my_song.pattern
   ```
2. Edit `arrangements/my_song.pattern` with any text editor.
3. Compile it:
   ```bash
   python generate.py arrangements/my_song.pattern
   # writes output/my_song.mid
   ```
4. Close and reopen the file, or import into Logic Pro: File > Import > MIDI
   File.

Repeat. No Python code is ever edited to make a new arrangement. The `.pattern`
file is the musical source; `generate.py` is the fixed compiler.

## Examples of complete arrangement files

`arrangements/example.pattern` — two bars of piano, chords, varied beats:

```
TEMPO 120
TIME 4/4

TRACK Piano

BAR 1
1.1: F1 + A3
1.2: C4
1.3: D4
1.4: A3

BAR 2
2.1: F1 + C4
2.2: A3
2.3: D4
2.4: C4
```

`arrangements/song_02.pattern` — melody + bass with sixteenth subdivisions,
chords, and per-part velocities:

```
TEMPO 120
TIME 4/4

TRACK Piano

BAR 1
1.1.1: C5 duration=1/16 velocity=100
1.1.1: F1 + F2 duration=1/16 velocity=90
1.1.3: A4 duration=1/16 velocity=100
1.2.1: C5 duration=1/16 velocity=100
1.2.1: F1 + F2 duration=1/16 velocity=90
...

BAR 2
2.1.1: C5 duration=1/16 velocity=100
2.1.1: A1 + A2 duration=1/16 velocity=90
...
```

`arrangements/two_instruments.pattern` — two tracks (bass and chords) in the
same file.

`arrangements/piano_intro.pattern` — a gentle two-bar intro with sustained
whole notes and dotted-style placement across beats.

## Programmatic use (advanced)

The core engine is a small, portable API:

```python
from midi_generator import MidiBuilder, Tempo
from midi_generator.midi_builder import NoteEvent, TimeSignature

builder = MidiBuilder(
    tempo=Tempo(bpm=120),
    time_signature=TimeSignature(4, 4),
)
builder.build(
    [
        NoteEvent("C4", start_beats=0.0, duration_beats=1.0, velocity=100),
        NoteEvent("E4", start_beats=0.0, duration_beats=1.0, velocity=100),
        NoteEvent("G4", start_beats=0.0, duration_beats=1.0, velocity=100),
    ],
    output_path="output/chord.mid",
)

parsed = parse_pattern_file("arrangements/song_01.pattern")
builder.build(parsed.track_notes()["Piano"], output_path="output/song_01.mid", track_name="Piano")
```

Normal use does not require the API; the `.pattern` files are the interface.

## Testing and validation

Run the full test suite:

```bash
python -m pytest tests/ -v
```

The suite covers note conversion, the pattern parser, the MIDI builder, the
CLI workflow (`python generate.py arrangements/example.pattern ->
output/example.mid`), validation error reporting, and several complete sample
arrangements.

To verify a generated file yourself without any tooling beyond Python:

```bash
python - <<'EOF'
import mido
m = mido.MidiFile("output/song_01.mid")
print(m.type, len(m.tracks), m.ticks_per_beat)
EOF
```

## Project layout

```
arrangements/        your editable musical source files (*.pattern)
  example.pattern        two-bar piano
  song_01.pattern        four-bar C–Am–F–G piano with sixteenths
  song_02.pattern        two-bar 16th-note melody + two-octave bass
  piano_intro.pattern    two-bar chordal intro, whole/half/quarter notes
  two_instruments.pattern  two tracks (Bass + Chords)
  logic_test.pattern     Logic-import regression reference
midi_generator/
  __init__.py       public API
  note.py           note name <-> MIDI pitch conversion
  midi_builder.py   MidiBuilder: events -> .mid file (NOTE: do not edit)
  parser.py         the .pattern language compiler
  patterns.py       bundled note-data for the two built-in demos
generate.py         command-line compiler entry point
tests/              pytest suite
output/             generated .mid files land here
requirements.txt    pinned dependencies
```

The rule of thumb: **edit files in `arrangements/`, run `generate.py`, import
the result into Logic.** Nothing else is involved.