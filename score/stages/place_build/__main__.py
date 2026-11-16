"""The placing agent's commands, one step each; each prints one JSON line (a refused step: {"refused": why}, exit 2).

    python -m score.stages.place_build start <folder> <place> <concept.png> [--objects objects.json] [--split]
    python -m score.stages.place_build camera <folder> --eye x,y,z --aim x,y,z --fov degrees
    python -m score.stages.place_build put <folder> <name> <kind/id[@version]> [--at x,y,z] [--turn rx,ry,rz]
                                       [--scale s|sx,sy,sz] [--ground] [--wear group,group] [--clip name]
                                       [--second s] [--rest] [--on-ground]
    python -m score.stages.place_build dome <folder> <name> --radius m [--at x,y,z] [--turn rx,ry,rz]
                                       [--meridians n] [--rings n] [--rib m] [--opening around,radius,centre ...]
    python -m score.stages.place_build tube <folder> <name> --radius m --length m [--at x,y,z] [--turn rx,ry,rz]
                                       [--hoops n] [--rib m] [--cap width,height]
    python -m score.stages.place_build stairs <folder> <name> [--storeys n] [--at x,y,z] [--turn rx,ry,rz] [--mirror]
    python -m score.stages.place_build ground <folder> <name> --radius m [--at x,y,z]
    python -m score.stages.place_build terrain <folder> <name> <kind/id[@version]> [--at x,y,z] [--turn rx,ry,rz]
                                       [--pad x,z,radius ...]
    python -m score.stages.place_build sky <folder> <light/id> --elevation deg --heading deg [--strength s]
                                       [--colour #rrggbb] [--turn degrees] [--background #rrggbb]
    python -m score.stages.place_build view <folder> <name> --eye x,y,z --aim x,y,z --fov degrees
    python -m score.stages.place_build batch <folder> <steps.json>
    python -m score.stages.place_build snap <folder> <name> [--grid metres]
    python -m score.stages.place_build palette <folder> <materials.json> --wear w --dirt d
    python -m score.stages.place_build surface <folder> <name> <surface/id[@version]|palette/variant>
                                       [--colour #rrggbb] [--part name]
    python -m score.stages.place_build light <folder> <name> --at x,y,z --watts W [--radius m] [--colour #rrggbb]
    python -m score.stages.place_build remove <folder> <name>
    python -m score.stages.place_build list <folder>
    python -m score.stages.place_build render <folder> [--width pixels] [--views name,name] [--final]
    python -m score.stages.place_build compare <folder>
    python -m score.stages.place_build review <folder> [--box x0,z0,x1,z1 | --prefix name] [--width pixels] [--out dir]
    python -m score.stages.place_build viewer <folder> [--glb path] [--box x0,z0,x1,z1 | --prefix name] [--megabytes m]
    python -m score.stages.place_build on <folder> <name> <floor|object|wall:object> [--level n] [--height m]
    python -m score.stages.place_build check <folder> [--no-settle]
    python -m score.stages.place_build film <folder> [--through 'stop;stop'] [--seconds s] [--eye m] [--seed n]
    python -m score.stages.place_build film-render <folder> [--every n] [--final] [--out dir]
    python -m score.stages.place_build make <folder> <name> <take/<take>|concept/<n>|like|picture.png> --material class
                                       (--like model/<id> | --height m)
    python -m score.stages.place_build route <folder> --through x,y,z --through x,y,z [--through x,y,z ...]

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
`palette` takes in the place's one surface library (a scene's surface-library output: its ProcFunc recipe variants
and palette tokens, the ones its props were painted from) with the place's wear and dirt; `surface ... palette/<variant>`
then lays that variant, which the render draws as its recipe (edge wear, dirt, relief), so props, shells and floors
share one palette. `render --final` renders at the films' samples (denoised) instead of the review's, 1920x1080.
`stairs` lays the stair core algorithm (stair_core.py): a walkable switchback stairwell of real size, its flats'
blocks and glazed front, parts `slab`, `steps`, `wall`, `dado`, `block`, `glass`, `frame`, `balusters`, `handrail`;
it answers its doorways for the doors laid in them (`--mirror`: the other hand).
`review` renders a region's plan (grid, names), corners, door and middle eye-height views and compartment close-ups in
one fast Blender call onto one contact sheet, a physics check's faults boxed in red (review.py); `viewer` writes the
scene as one compressed GLB for a browser viewer.
`batch` runs a JSON list of steps ([{"step": "put", "name", "address", "at", ...}], each its function's arguments by
name) in one process, the scene composed once; it prints each step's answer.
`on` lays an object at rest in contact on its support: `floor`, an object's top (or its `--level` n-th surface that
looks up, a shelf), or `wall:<object>` at `--height` over the floor (ready/). `check` tells, per object, everything that
keeps the place from being physics ready (floating, penetration, no support, tipping, a door in no opening, a walkway
under 0.9 m, a connector joined to nothing or with no floor, no collision geometry, unstable when let go in MuJoCo):
one JSON line of counts, the full list in <folder>/ready.json.
`film` plans the place's film (film.py): still on the concept's view, a clear glide down, then through the stops at
eye height (or in free air), clear of every solid the check reads, written to <folder>/film/path.json with its
measures; `film-render` renders every `--every`th frame through the card queue (half size at the review's samples, or
`--final` at the films' 1920x1080), with the seconds a frame.
`make` makes a prop's model with TRELLIS.2 on this PC's card (maker/): from a take's close-up, the concept cut by a
SAM 3 mask, or the picture the `--like` model was made from; set over the `--like` model it replaces (or `--height`
metres tall), its paint graded to the place's palette, CoACD hulls and mass from its `--material` class, taken into
score_lib as a draft model entry; `put` then lays its address.
`route` answers a walker's way through the `--through` spots, in order, on the check's walkers' floor (doors open,
0.9 m wide): the shortest one, its corners rounded, for a walker's cast `path` (scene clips, sim body).
"""
import argparse
import json
import sys

from score.stages import place_build


POINTS = ("--at", "--turn", "--eye", "--aim", "--scale", "--pad", "--box", "--through")


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
                                args.meridians, args.rings, args.rib, openings=[numbers(hole) for hole in args.opening])
    if args.step == "tube":
        return place_build.tube(args.folder, args.name, args.radius, args.length, numbers(args.at), numbers(args.turn),
                                args.hoops, args.rib, cap=numbers(args.cap) if args.cap else None,
                                cap_door=args.cap_door)
    if args.step == "stairs":
        return place_build.stairs(args.folder, args.name, args.storeys, numbers(args.at), numbers(args.turn),
                                  args.mirror)
    if args.step == "ground":
        return place_build.ground(args.folder, args.name, args.radius, numbers(args.at))
    if args.step == "terrain":
        return place_build.terrain(args.folder, args.name, args.address, numbers(args.at), numbers(args.turn),
                                   [numbers(pad) for pad in args.pad])
    if args.step == "sky":
        return place_build.sky(args.folder, args.address, args.elevation, args.heading, args.strength, args.colour,
                               args.turn, args.background, args.exposure)
    if args.step == "view":
        return place_build.view(args.folder, args.name, numbers(args.eye), numbers(args.aim), args.fov)
    if args.step == "batch":
        with open(args.steps) as given:
            return place_build.batch(args.folder, json.load(given))
    if args.step == "snap":
        return place_build.snap(args.folder, args.name, args.grid)
    if args.step == "palette":
        return place_build.palette(args.folder, args.library, args.wear, args.dirt)
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
        return render.render(args.folder, args.width, [name for name in (args.views or "").split(",") if name],
                             args.final)
    if args.step in ("film", "film-render"):
        from score.stages.place_build import film
        if args.step == "film":
            return film.path(args.folder, args.through.split(";") if args.through else None, args.seconds, args.eye,
                             args.seed)
        return film.render(args.folder, args.every, args.final, args.out)
    if args.step in ("review", "viewer"):
        from score.stages.place_build import review
        box = numbers(args.box) if args.box else None
        if args.step == "review":
            return review.review(args.folder, box, args.prefix, args.width, args.out)
        return review.viewer(args.folder, args.glb, box, args.prefix, args.megabytes)
    if args.step == "on":
        from score.stages.place_build import ready
        return ready.on(args.folder, args.name, args.support, args.level, args.height)
    if args.step == "check":
        from score.stages.place_build import ready
        return ready.check(args.folder, not args.no_settle)
    if args.step == "make":
        from score.stages.place_build import maker
        return maker.make(args.folder, args.name, args.source, args.material, args.like, args.height)
    if args.step == "route":
        from score.stages.place_build import ready
        points, length = ready.route(args.folder, [numbers(spot) for spot in args.through])
        return {"route": points, "metres": length}
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
    step.add_argument("--opening", action="append", default=[])
    step = steps.add_parser("tube")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--radius", type=float, required=True)
    step.add_argument("--length", type=float, required=True)
    step.add_argument("--at", default="0,0,0")
    step.add_argument("--turn", default="0,0,0")
    step.add_argument("--hoops", type=int)
    step.add_argument("--rib", type=float)
    step.add_argument("--cap")
    step.add_argument("--cap-door", help="a laid door whose own outline the end wall's doorway is cut to")
    step = steps.add_parser("stairs")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--storeys", type=int)
    step.add_argument("--at", default="0,0,0")
    step.add_argument("--turn", default="0,0,0")
    step.add_argument("--mirror", action="store_true")
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
    step.add_argument("--turn", type=float, default=0.0)
    step.add_argument("--background")
    step.add_argument("--exposure", type=float)
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
    step = steps.add_parser("palette")
    for name in ("folder", "library"):
        step.add_argument(name)
    step.add_argument("--wear", type=float, required=True)
    step.add_argument("--dirt", type=float, required=True)
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
    step = steps.add_parser("on")
    for name in ("folder", "name", "support"):
        step.add_argument(name)
    step.add_argument("--level", type=int)
    step.add_argument("--height", type=float)
    step = steps.add_parser("check")
    step.add_argument("folder")
    step.add_argument("--no-settle", action="store_true")
    step = steps.add_parser("make")
    for name in ("folder", "name", "source"):
        step.add_argument(name)
    step.add_argument("--material", required=True)
    step.add_argument("--like")
    step.add_argument("--height", type=float)
    step = steps.add_parser("route")
    step.add_argument("folder")
    step.add_argument("--through", action="append", required=True)
    step = steps.add_parser("render")
    step.add_argument("folder")
    step.add_argument("--width", type=int, default=768)
    step.add_argument("--views")
    step.add_argument("--final", action="store_true")
    for name in ("review", "viewer"):
        step = steps.add_parser(name)
        step.add_argument("folder")
        step.add_argument("--box")
        step.add_argument("--prefix")
    filmed = steps.add_parser("film")
    filmed.add_argument("folder")
    filmed.add_argument("--through", help="stops by ';': a named view, x,z (eye height over the floor) or x,y,z, "
                                          "either ending >ax,ay,az to look there")
    filmed.add_argument("--seconds", type=float, default=25.0)
    filmed.add_argument("--eye", type=float, default=1.6)
    filmed.add_argument("--seed", type=int, default=0)
    rendered = steps.add_parser("film-render")
    rendered.add_argument("folder")
    rendered.add_argument("--every", type=int, default=1)
    rendered.add_argument("--final", action="store_true")
    rendered.add_argument("--out")
    steps.choices["review"].add_argument("--width", type=int, default=960)
    steps.choices["review"].add_argument("--out")
    steps.choices["viewer"].add_argument("--glb")
    steps.choices["viewer"].add_argument("--megabytes", type=float, default=15.0)
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
