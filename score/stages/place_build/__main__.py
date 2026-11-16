"""The placing agent's commands, one step each; each prints one JSON line (a refused step: {"refused": why}, exit 2).

    python -m score.stages.place_build start <folder> <place> <concept.png> [--objects objects.json] [--split]
    python -m score.stages.place_build camera <folder> --eye x,y,z --aim x,y,z --fov degrees
    python -m score.stages.place_build put <folder> <name> <kind/id[@version]> [--at x,y,z] [--turn rx,ry,rz]
                                       [--scale s|sx,sy,sz] [--ground] [--wear group,group] [--clip name]
                                       [--second s]
    python -m score.stages.place_build dome <folder> <name> --radius m [--at x,y,z] [--turn rx,ry,rz]
                                       [--meridians n] [--rings n] [--rib m]
    python -m score.stages.place_build batch <folder> <steps.json>
    python -m score.stages.place_build snap <folder> <name> [--grid metres]
    python -m score.stages.place_build surface <folder> <name> <surface/id[@version]> [--colour #rrggbb]
                                       [--part name]
    python -m score.stages.place_build light <folder> <name> --at x,y,z --watts W [--radius m] [--colour #rrggbb]
    python -m score.stages.place_build remove <folder> <name>
    python -m score.stages.place_build list <folder>
    python -m score.stages.place_build render <folder> [--width pixels]
    python -m score.stages.place_build compare <folder>

`--split` runs SAM 3 over the concept (score/review/concept_objects.py) on this PC's card (SCORE_CLOUD=local, free).
`put --ground` marks the piece as the place's ground, so the render lays no grey plane of its own; a character is
dressed in its body group (`--wear`, its made body by default) and held still in a clip (`--clip`, `--second`).
`dome` lays the dome shell algorithm (dome_shell.py): its parts `shell` and `ribs` take a surface each (`surface --part`).
`batch` runs a JSON list of steps ([{"step": "put", "name", "address", "at", ...}], each its function's arguments by
name) in one process, the scene composed once; it prints each step's answer.
"""
import argparse
import json
import sys

from score.stages import place_build


POINTS = ("--at", "--turn", "--eye", "--aim", "--scale")


def with_negatives(given):
    """The command line with a point that starts with a minus joined to its option (`--at=-1,0,2`), so argparse does
    not read it as an option."""
    joined = []
    for word in given:
        if joined and joined[-1] in POINTS and word.startswith("-"):
            joined[-1] = f"{joined[-1]}={word}"
        else:
            joined.append(word)
    return joined


def numbers(text):
    return [float(value) for value in text.split(",")]


def scale_of(text):
    values = numbers(text)
    return values * 3 if len(values) == 1 else values


# The free route for SAM 3: this PC's card as the runners' one machine (tools/cloud/this_pc.py's own settings).
THIS_PC = {"SCORE_CLOUD": "local", "SCORE_FREE_ONLY": "1"}


def split(args):
    """The concept split into objects by SAM 3 on this PC's card (free), its answer written as
    <folder>/split/objects.json."""
    import os
    os.environ.update(THIS_PC)  # before the cloud tools load: provider.py reads the backend once, when imported
    from score.review import concept_objects
    found = concept_objects.objects(args.concept, f"{args.folder}/split")
    path = f"{args.folder}/split/objects.json"
    with open(path, "w") as out:
        json.dump(found, out, indent=1)
    return path


def run(args):
    if args.step == "start":
        record = place_build.start(args.folder, args.place, args.concept, args.objects)
        if args.split:
            record = place_build.start_objects(args.folder, split(args))
        return record
    if args.step == "camera":
        return place_build.camera(args.folder, numbers(args.eye), numbers(args.aim), args.fov)
    if args.step == "put":
        return place_build.put(args.folder, args.name, args.address, numbers(args.at), numbers(args.turn),
                               scale_of(args.scale), args.ground, args.wear.split(",") if args.wear else None,
                               args.clip, args.second)
    if args.step == "dome":
        return place_build.dome(args.folder, args.name, args.radius, numbers(args.at), numbers(args.turn),
                                args.meridians, args.rings, args.rib)
    if args.step == "batch":
        with open(args.steps) as given:
            return place_build.batch(args.folder, json.load(given))
    if args.step == "snap":
        return place_build.snap(args.folder, args.name, args.grid)
    if args.step == "surface":
        return place_build.surface(args.folder, args.name, args.address, args.colour, args.part)
    if args.step == "light":
        return place_build.light(args.folder, args.name, numbers(args.at), args.watts, args.radius, args.colour)
    if args.step == "remove":
        return place_build.remove(args.folder, args.name)
    if args.step == "list":
        return place_build.listing(args.folder)
    if args.step == "render":
        from score.stages.place_build import render
        return render.render(args.folder, args.width)
    from score.stages.place_build import measure
    return measure.compare(args.folder)


def parser():
    made = argparse.ArgumentParser(prog="python -m score.stages.place_build", description=__doc__,
                                   formatter_class=argparse.RawDescriptionHelpFormatter)
    steps = made.add_subparsers(dest="step", required=True)
    step = steps.add_parser("start")
    step.add_argument("folder")
    step.add_argument("place")
    step.add_argument("concept")
    step.add_argument("--objects")
    step.add_argument("--split", action="store_true")
    step = steps.add_parser("camera")
    step.add_argument("folder")
    step.add_argument("--eye", required=True)
    step.add_argument("--aim", required=True)
    step.add_argument("--fov", type=float, required=True)
    step = steps.add_parser("put")
    for name in ("folder", "name", "address"):
        step.add_argument(name)
    step.add_argument("--at", default="0,0,0")
    step.add_argument("--turn", default="0,0,0")
    step.add_argument("--scale", default="1")
    step.add_argument("--ground", action="store_true")
    step.add_argument("--wear")
    step.add_argument("--clip")
    step.add_argument("--second", type=float, default=0.0)
    step = steps.add_parser("dome")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--radius", type=float, required=True)
    step.add_argument("--at", default="0,0,0")
    step.add_argument("--turn", default="0,0,0")
    step.add_argument("--meridians", type=int)
    step.add_argument("--rings", type=int)
    step.add_argument("--rib", type=float)
    step = steps.add_parser("batch")
    step.add_argument("folder")
    step.add_argument("steps")
    step = steps.add_parser("snap")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--grid", type=float, default=0.5)
    step = steps.add_parser("surface")
    for name in ("folder", "name", "address"):
        step.add_argument(name)
    step.add_argument("--colour")
    step.add_argument("--part")
    step = steps.add_parser("light")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--at", required=True)
    step.add_argument("--watts", type=float, required=True)
    step.add_argument("--radius", type=float, default=0.05)
    step.add_argument("--colour", default="#ffffff")
    for name in ("remove",):
        step = steps.add_parser(name)
        step.add_argument("folder")
        step.add_argument("name")
    for name in ("list", "compare"):
        steps.add_parser(name).add_argument("folder")
    step = steps.add_parser("render")
    step.add_argument("folder")
    step.add_argument("--width", type=int, default=768)
    return made


def main():
    args = parser().parse_args(with_negatives(sys.argv[1:]))
    try:
        print(json.dumps(run(args)))
    except place_build.Refused as why:
        print(json.dumps({"refused": str(why)}))
        sys.exit(2)
    except RuntimeError as why:  # a render that wrote no picture (render.RenderFailed)
        print(json.dumps({"failed": str(why)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
