"""Command-line entry point.

The generator is a deterministic compiler: it reads a .pattern arrangement
and writes a Standard MIDI File. It makes no musical decisions of its own.

Examples:
    python generate.py arrangements/song_01.pattern   -> output/song_01.mid
    python generate.py arrangements/example.pattern   -> output/example.mid
    python generate.py -o foo.mid arrangements/song_01.pattern
    python generate.py --pattern example              -> output/example.mid (built-in)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from midi_generator.midi_builder_logic import MidiBuilder, Tempo
from midi_generator.parser import parse_pattern_file
from midi_generator.midi_builder_logic import TimeSignature, ProgramChange
from midi_generator.parser import PatternError
from midi_generator.patterns import (
    four_bar_example,
    logic_test_pattern,
    LOGIC_TEST_TRACK_NAME,
)

_PATTERNS = {
    "example": (four_bar_example, "output/example.mid", "MIDI 1"),
    "logic-test": (logic_test_pattern, "output/logic_test.mid", LOGIC_TEST_TRACK_NAME),
}


def _write_arrangement(source: str, output: str | None, ticks_per_beat: int) -> Path:
    """Compile one .pattern arrangement file to a .mid file.

    The output filename derives from the input filename (DEFAULT: output/<stem>.mid).
    """
    src = Path(source)
    if not src.is_file():
        raise OSError(f"Arrangement file not found: {src}")
    parsed = parse_pattern_file(src)

    out = Path(output) if output else Path("output") / f"{src.stem}.mid"
    out.parent.mkdir(parents=True, exist_ok=True)

    builder = MidiBuilder(
        tempo=parsed.tempo,
        time_signature=parsed.time_signature,
    )
    notes = parsed.track_notes()
    if len(notes) == 1:
        (track_name, track_notes), = notes.items()
        builder.build(
            track_notes,
            ticks_per_beat=ticks_per_beat,
            output_path=out,
            track_name=track_name,
        )
    else:
        builder.build_multi_track(
            notes,
            ticks_per_beat=ticks_per_beat,
            output_path=out,
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile a .pattern arrangement into a Standard MIDI file.",
    )
    parser.add_argument(
        "arrangement", nargs="?", type=str, default=None,
        help="Path to a .pattern arrangement file (see arrangements/). "
             "Output is written to output/<arrangement-name>.mid.",
    )
    parser.add_argument(
        "-p", "--pattern", choices=sorted(_PATTERNS), default="example",
        help="Built-in pattern to generate (default: example). "
             "Ignored when an arrangement file is given.",
    )
    parser.add_argument(
        "--pattern-file", type=str, default=None,
        help="Deprecated alias for the positional ARRANGEMENT argument.",
    )
    parser.add_argument(
        "-o", "--output", type=str, default=None,
        help="Output path for the .mid file (overrides the derived default)",
    )
    parser.add_argument(
        "--bpm", type=int, default=120,
        help="Tempo in BPM for built-in patterns only (default: 120)",
    )
    parser.add_argument(
        "--ticks-per-beat", type=int, default=480,
        help="PPQ resolution (default: 480)",
    )
    args = parser.parse_args(argv)

    if args.arrangement and args.pattern_file:
        parser.error("Give either the positional ARRANGEMENT path or --pattern-file, not both")
    source = args.arrangement or args.pattern_file
    if source:
        try:
            out = _write_arrangement(source, args.output, args.ticks_per_beat)
        except (OSError, PatternError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"Wrote {out}")
        return 0

    notes_fn, default_output, track_name = _PATTERNS[args.pattern]
    output = Path(args.output) if args.output else Path(default_output)
    builder = MidiBuilder(
        tempo=Tempo(bpm=args.bpm),
        time_signature=TimeSignature(4, 4),
        program_changes=(ProgramChange(program=0),),
    )
    builder.build(
        notes_fn(),
        ticks_per_beat=args.ticks_per_beat,
        output_path=output,
        track_name=track_name,
    )
    print(f"Wrote {output} ({args.bpm} BPM)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())