"""python -m score.stages.place_build.hardware build <kind> <entry> --size W,D,T --out <folder> --words W --material M
[--option key=json ...] [--picture close-up.png] [--take-in]: one product built (hardware.made) and, with
--take-in, committed to score_lib as the draft `model/<entry>`; one summary line, the record in <out>/<entry>.json.
python -m score.stages.place_build.hardware take-in <work> <out folder>=<title> ...: products built before (each
folder named for its entry) committed to score_lib in one take-in; one line of their addresses."""
import argparse
import json
import pathlib
import sys

from score.stages.place_build import hardware


def options_of(pairs):
    """{key: value} of `key=json` pairs (a bare word kept as text)."""
    found = {}
    for pair in pairs or []:
        key, _, value = pair.partition("=")
        try:
            found[key] = json.loads(value)
        except json.JSONDecodeError:
            found[key] = value
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m score.stages.place_build.hardware")
    steps = parser.add_subparsers(dest="step", required=True)
    build = steps.add_parser("build")
    build.add_argument("kind", choices=sorted(hardware.KINDS))
    build.add_argument("entry")
    build.add_argument("--size", required=True)
    build.add_argument("--out", required=True)
    build.add_argument("--words", required=True)
    build.add_argument("--material", required=True)
    build.add_argument("--option", action="append")
    build.add_argument("--picture")
    build.add_argument("--title")
    build.add_argument("--take-in", action="store_true")
    taking = steps.add_parser("take-in")
    taking.add_argument("work")
    taking.add_argument("made", nargs="+")
    args = parser.parse_args(argv)
    if args.step == "take-in":
        items = []
        for pair in args.made:
            folder, _, title = pair.partition("=")
            folder = pathlib.Path(folder)
            items.append((folder.name, json.loads((folder / f"{folder.name}.json").read_text()), title, folder))
        print(json.dumps({"addresses": hardware.taken_in(items, args.work)}))
        return 0
    size = [float(side) for side in args.size.split(",")]
    record = hardware.made(args.kind, size, args.out, args.entry, args.words, args.material, args.picture,
                           options_of(args.option))
    address = None
    if args.take_in:
        title = args.title or f"{args.words[:1].upper()}{args.words[1:]} (built, {args.entry.split('.')[-1]})"
        address = hardware.taken_in([(args.entry, record, title, args.out)], args.out)[0]
    print(json.dumps({"entry": args.entry, "address": address, "size_m": record["size_m"], "parts": record["parts"],
                      "mass_kg": record["physics"]["mass_kg"], "faces": record["faces"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
