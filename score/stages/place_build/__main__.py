"""The placing agent's commands, one step each; each prints one JSON line (a refused step: {"refused": why}, exit 2).

    python -m score.stages.place_build start <folder> <place> <concept.png> [--objects objects.json] [--split]
    python -m score.stages.place_build camera <folder> --eye x,y,z --aim x,y,z --fov degrees
    python -m score.stages.place_build put <folder> <name> <kind/id[@version]> [--at x,y,z] [--turn rx,ry,rz]
                                       [--scale s|sx,sy,sz] [--ground] [--wear group,group] [--clip name]
                                       [--second s] [--rest] [--on-ground]
    python -m score.stages.place_build dome <folder> <name> --radius m [--at x,y,z] [--turn rx,ry,rz]
                                       [--meridians n] [--rings n] [--rib m]
    python -m score.stages.place_build tube <folder> <name> --radius m --length m [--at x,y,z] [--turn rx,ry,rz]
                                       [--hoops n] [--rib m]
    python -m score.stages.place_build ground <folder> <name> --radius m [--at x,y,z]
    python -m score.stages.place_build terrain <folder> <name> <kind/id[@version]> [--at x,y,z] [--turn rx,ry,rz]
                                       [--pad x,z,radius ...]
    python -m score.stages.place_build sky <folder> <light/id> --elevation deg --heading deg [--strength s]
                                       [--colour #rrggbb]
    python -m score.stages.place_build view <folder> <name> --eye x,y,z --aim x,y,z --fov degrees
    python -m score.stages.place_build batch <folder> <steps.json>
    python -m score.stages.place_build snap <folder> <name> [--grid metres]
    python -m score.stages.place_build surface <folder> <name> <surface/id[@version]> [--colour #rrggbb]
                                       [--part name]
    python -m score.stages.place_build light <folder> <name> --at x,y,z --watts W [--radius m] [--colour #rrggbb]
    python -m score.stages.place_build remove <folder> <name>
    python -m score.stages.place_build list <folder>
    python -m score.stages.place_build render <folder> [--width pixels] [--views name,name]
    python -m score.stages.place_build compare <folder>

`--split` runs SAM 3 over the concept (score/review/concept_objects.py) on this PC's card (SCORE_CLOUD=local, free).
`put --rest` stands the piece's lowest point at its `--at` height (on a floor or table); `--on-ground` reads that
height as above the laid ground there (a rock on a terrain's relief). `put --ground` marks the piece as the place's ground, so the render lays no grey plane of its own; a character is
dressed in its body group (`--wear`, its made body by default) and held still in a clip (`--clip`, `--second`).
`dome` lays the dome shell algorithm (dome_shell.py): its parts `shell`, `ribs` and `deck` (its floor) take a surface
each (`surface --part`). `ground` lays a flat disc as the place's ground (its part `ground`), for a library surface
such as surface/ambientcg_ground054; an image surface's maps tile at their real size in the render.
`terrain` lays a heightfield terrain entry (relief.py, a real DTM's relief) as the ground, each `--pad` (a building's
site) levelled to its laid height. `sky` lays a light entry's sky dome as the place's own sky and a sun from
`--elevation` and `--heading` (degrees round from +x towards +z). `view` names a camera besides the concept's;
`render --views` draws those too, as <folder>/view-<name>.png.
A glTF-only model or take (our picture-made props) is laid in its own bake and paint.
`batch` runs a JSON list of steps ([{"step": "put", "name", "address", "at", ...}], each its function's arguments by
name) in one process, the scene composed once; it prints each step's answer.
"""
import argparse
import json
import sys

from score.stages import place_build


POINTS = ("--at", "--turn", "--eye", "--aim", "--scale", "--pad")


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


def this_pc_environment():
    """The free route for SAM 3, tools/cloud/this_pc.py's own: this PC's card as the runners' one machine, free only,
    in this PC's run home (its runner key and books; the pilot's split was refused for the PC's home having no key)."""
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools" / "cloud"))
    import this_pc
    return this_pc.run_environment(this_pc.prepared(this_pc.HOME))


# The split's own process: the cloud tools read PROPS_HOME and the backend once, when imported, so they load in a
# process started in this PC's run environment, never in this one (where this_pc.py has loaded them already).
SPLIT = ("import json, sys\nfrom score.review import concept_objects\n"
         "json.dump(concept_objects.objects(sys.argv[1], sys.argv[2]), open(sys.argv[3], 'w'), indent=1)")


def split(args):
    """The concept split into objects by SAM 3 on this PC's card (free), its answer written as
    <folder>/split/objects.json."""
    import pathlib
    import subprocess
    path = f"{args.folder}/split/objects.json"
    done = subprocess.run([sys.executable, "-c", SPLIT, str(args.concept), f"{args.folder}/split", path],
                          env=this_pc_environment(), cwd=pathlib.Path(__file__).resolve().parents[3])
    if done.returncode != 0:
        raise place_build.Refused(f"the concept split on this PC's card failed (exit {done.returncode})")
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
                               args.clip, args.second, args.rest, args.on_ground)
    if args.step == "dome":
        return place_build.dome(args.folder, args.name, args.radius, numbers(args.at), numbers(args.turn),
                                args.meridians, args.rings, args.rib)
    if args.step == "tube":
        return place_build.tube(args.folder, args.name, args.radius, args.length, numbers(args.at), numbers(args.turn),
                                args.hoops, args.rib)
    if args.step == "ground":
        return place_build.ground(args.folder, args.name, args.radius, numbers(args.at))
    if args.step == "terrain":
        return place_build.terrain(args.folder, args.name, args.address, numbers(args.at), numbers(args.turn),
                                   [numbers(pad) for pad in args.pad])
    if args.step == "sky":
        return place_build.sky(args.folder, args.address, args.elevation, args.heading, args.strength, args.colour)
    if args.step == "view":
        return place_build.view(args.folder, args.name, numbers(args.eye), numbers(args.aim), args.fov)
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
        return render.render(args.folder, args.width, [name for name in (args.views or "").split(",") if name])
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
    step.add_argument("--rest", action="store_true")
    step.add_argument("--on-ground", action="store_true")
    step = steps.add_parser("dome")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--radius", type=float, required=True)
    step.add_argument("--at", default="0,0,0")
    step.add_argument("--turn", default="0,0,0")
    step.add_argument("--meridians", type=int)
    step.add_argument("--rings", type=int)
    step.add_argument("--rib", type=float)
    step = steps.add_parser("tube")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--radius", type=float, required=True)
    step.add_argument("--length", type=float, required=True)
    step.add_argument("--at", default="0,0,0")
    step.add_argument("--turn", default="0,0,0")
    step.add_argument("--hoops", type=int)
    step.add_argument("--rib", type=float)
    step = steps.add_parser("ground")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--radius", type=float, required=True)
    step.add_argument("--at", default="0,0,0")
    step = steps.add_parser("terrain")
    for name in ("folder", "name", "address"):
        step.add_argument(name)
    step.add_argument("--at", default="0,0,0")
    step.add_argument("--turn", default="0,0,0")
    step.add_argument("--pad", action="append", default=[])
    step = steps.add_parser("sky")
    step.add_argument("folder")
    step.add_argument("address")
    step.add_argument("--elevation", type=float, required=True)
    step.add_argument("--heading", type=float, required=True)
    step.add_argument("--strength", type=float, default=1.0)
    step.add_argument("--colour", default="#ffffff")
    step = steps.add_parser("view")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--eye", required=True)
    step.add_argument("--aim", required=True)
    step.add_argument("--fov", type=float, required=True)
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
    step.add_argument("--views")
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
