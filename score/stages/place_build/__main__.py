"""The placing agent's commands, one step each; each prints one JSON line (a refused step: {"refused": why}, exit 2).

    python -m score.stages.place_build start <folder> <place> <concept.png> [--objects objects.json] [--split]
                                       [--nouns word,word]
    python -m score.stages.place_build split <folder> [--nouns word,word] [--box word=x0,y0,x1,y1 ...]
    python -m score.stages.place_build camera <folder> --eye x,y,z --aim x,y,z --fov degrees
    python -m score.stages.place_build put <folder> <name> <kind/id[@version]> [--at x,y,z] [--turn rx,ry,rz]
                                       [--scale s|sx,sy,sz] [--ground] [--wear group,group] [--clip name]
                                       [--second s] [--rest] [--on-ground]
    python -m score.stages.place_build dome <folder> <name> --radius m [--at x,y,z] [--turn rx,ry,rz]
                                       [--meridians n] [--rings n] [--rib m] [--opening around,radius,centre ...]
    python -m score.stages.place_build tube <folder> <name> --radius m --length m [--at x,y,z] [--turn rx,ry,rz]
                                       [--hoops n] [--rib m] [--cap width,height]
    python -m score.stages.place_build stairs <folder> <name> [--storeys n] [--at x,y,z] [--turn rx,ry,rz] [--mirror]
                                       [--curtain] [--cut] [--one-block]
    python -m score.stages.place_build ground <folder> <name> --radius m [--at x,y,z]
    python -m score.stages.place_build terrain <folder> <name> <kind/id[@version]> [--at x,y,z] [--turn rx,ry,rz]
                                       [--pad x,z,radius ...]
    python -m score.stages.place_build sky <folder> <light/id> --elevation deg --heading deg [--strength s]
                                       [--colour #rrggbb] [--turn degrees] [--background #rrggbb]
    python -m score.stages.place_build sky-at <folder> (--scene <kept sky> | --on body --latitude deg --longitude deg
                                       --time iso) [--height m] [--turn degrees] [--exposure x]
    python -m score.stages.place_build view <folder> <name> --eye x,y,z --aim x,y,z --fov degrees
    python -m score.stages.place_build batch <folder> <steps.json>
    python -m score.stages.place_build snap <folder> <name> [--grid metres]
    python -m score.stages.place_build palette <folder> <materials.json> --wear w --dirt d
    python -m score.stages.place_build surface <folder> <name> <surface/id[@version]|palette/variant>
                                       [--colour #rrggbb] [--part name]
    python -m score.stages.place_build light <folder> <name> --at x,y,z --watts W [--radius m] [--colour #rrggbb]
    python -m score.stages.place_build remove <folder> <name>
    python -m score.stages.place_build cut <folder> <name>
    python -m score.stages.place_build backdrop <folder> <name>
    python -m score.stages.place_build hollow <folder> <name> --region x0,y0,z0,x1,y1,z1 [--region ...]
    python -m score.stages.place_build door <folder> <name> [--opens] [--slide] [--lock chamber --side inner|outer]
    python -m score.stages.place_build refinish <folder> <name>
    python -m score.stages.place_build plan <folder> <plan.json>
    python -m score.stages.place_build dress <folder> <name> <address> <row> <N|S|E|W|floor> [--support wall]
                                       [--height m] [--every m] [--front +x|-x|+z|-z]
    python -m score.stages.place_build list <folder>
    python -m score.stages.place_build render <folder> [--width pixels] [--views name,name] [--final]
    python -m score.stages.place_build compare <folder>
    python -m score.stages.place_build review <folder> [--box x0,z0,x1,z1 | --prefix name] [--width pixels] [--out dir]
    python -m score.stages.place_build viewer <folder> [--glb path] [--box x0,z0,x1,z1 | --prefix name] [--megabytes m]
    python -m score.stages.place_build on <folder> <name> <floor|object|wall:object> [--level n] [--height m]
    python -m score.stages.place_build check <folder> [--no-settle] [--among <place>=<folder> ...]
    python -m score.stages.place_build film <folder> [--through 'stop;stop'] [--seconds s] [--eye m] [--seed n]
    python -m score.stages.place_build film-render <folder> [--every n] [--final] [--out dir]
    python -m score.stages.place_build make <folder> <name> <take/<take>|concept/<n>|like|picture.png> --material class
                                       (--like model/<id> | --height m | --size wide,deep,tall) [--no-take-in]
    python -m score.stages.place_build route <folder> --through x,y,z --through x,y,z [--through x,y,z ...]
    python -m score.stages.place_build package <folder> <out>

`--split` runs SAM 3 over the concept (score/review/concept_objects.py) on this PC's card (SCORE_CLOUD=local, free),
asking `--nouns` when given, else its generic probes; `split` asks a laid place's concept for more nouns, their objects
added after the ones objects.json holds (their numbers, `make concept/<n>`'s, unchanged); its `--box` asks SAM 3 for
the one thing in a pixel box of the concept (its point-and-box model), named by the word, where a noun over the whole
picture finds specks or two panels as one.
`put --rest` stands the piece's lowest point at its `--at` height (on a floor or table); `--on-ground` reads that
height as above the laid ground there (a rock on a terrain's relief). `put --ground` marks the piece as the place's ground, so the render lays no grey plane of its own; a character is
dressed in its body group (`--wear`, its made body by default) and held still in a clip (`--clip`, `--second`).
`dome` lays the dome shell algorithm (dome_shell.py): its parts `shell`, `ribs` and `deck` (its floor) take a surface
each (`surface --part`). `ground` lays a flat disc as the place's ground (its part `ground`), for a library surface
such as surface/ambientcg_ground054; an image surface's maps tile at their real size in the render.
`terrain` lays a heightfield terrain entry (relief.py, a real DTM's relief) as the ground, each `--pad` (a building's
site) levelled to its laid height. `sky` lays a light entry's sky dome as the place's own sky and a sun from
`--elevation` and `--heading` (degrees round from +x towards +z). `view` names a camera besides the concept's;
`render --views` draws those too, as <folder>/view-<name>.png. `plan` takes the place's plan in (scene_record's
place-plan): its views (an eye-height view from each person spot and each doorway) are named views `render` draws
with the concept's when no --views is given, at 1920 wide, and `check` tells every way the place strays from it
(ready.json `plan`). `dress` lays copies of a library piece (a wall panel, a pipe run, a floor grate) along a plan
wall, mounted on the laid wall `--support`, or tiled over the floor, as the row of the plan's walls it dresses.
A glTF-only model or take (our picture-made props) is laid in its own bake and paint.
`palette` takes in the place's one surface library (a scene's surface-library output: its ProcFunc recipe variants
and palette tokens, the ones its props were painted from) with the place's wear and dirt; `surface ... palette/<variant>`
then lays that variant, which the render draws as its recipe (edge wear, dirt, relief), so props, shells and floors
share one palette. `render --final` renders at the films' samples (denoised) instead of the review's, 1920x1080.
`stairs` lays the stair core algorithm (stair_core.py): a walkable switchback stairwell of real size, its flats'
blocks and glazed front, parts `slab`, `steps`, `wall`, `dado`, `block`, `glass`, `frame`, `balusters`, `handrail`;
it answers its doorways for the doors laid in them (`--mirror`: the other hand; `--curtain`: its front a storey-high
curtain wall, the slab edges and corner piers left, so the look in reads as a cut-away's; `--cut`: its front wall laid
as its own object <name>_front, which the camera alone cuts, at render; `--one-block`: only the flats' block the
entrance opens into, the shaft's far wall standing free).
`cut` lists an object the camera sees through (place.json `cut`; the concept's cut-away, at render only): every
inside place is built closed, the cut is the camera's, never the building's; the walkers, the physics check and a game
engine get the building whole.
`door` marks a laid object a door: `--opens` the walkers open it (else it stays shut), `--slide` it slides aside
along its face (a sliding balcony door, a lock's plug door) instead of swinging on a hinge, `--lock` and `--side` it is
the inner (to the base) or outer (to the outside) pressure door of an airlock chamber, any laid object closing the
chamber's air (a blocks-built shell too): the package lists the chamber, and a pressure door opens to its high-pressure
side (the outer one into the chamber, the inner one out of it).
`review` renders a region's plan (grid, names), corners, door and middle eye-height views and compartment close-ups in
one fast Blender call onto one contact sheet, a physics check's faults boxed in red (review.py); `viewer` writes the
scene as one compressed GLB for a browser viewer.
`hold` sets a laid character's joints to a library pose (a character entry's pose.json: the smoker's right arm) and,
with `--prop`, lays that object (the cigarette) at the pose's hold frame of the posed hand. A `put` effect entry (the
cigarette's wisp) is laid under Effects, no solid.
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
metres tall, or `--size` its longest side the size's, turned as its close-up shows it), its paint graded to the
place's palette, CoACD hulls, its `--material` class's friction (data/physics/surface_classes.json) and a real-world
mass Claude gives (EUR 0), taken into score_lib as a draft model entry
(`--no-take-in`: kept in the place's made/ folder only, the prop benchmark's mode, #163); `put` then lays its address.
`route` answers a walker's way through the `--through` spots, in order, on the check's walkers' floor (doors open,
0.9 m wide): the shortest one, its corners rounded, for a walker's cast `path` (scene clips, sim body).
`package` writes the place as a scene package any engine loads (scene_package.py; the game 2099's Unity through
glTFast): <out>/scene.json in score.scene version 1 (tools/props/library/package.py's format, checked by its check)
and an <out>/objects/<name>.gltf a distinct object, converted from the laid USD in its bound looks (a palette recipe
baked into its own pictures by headless Blender on this PC's card), each copy's collider from the physics check's
roles when ready.json is there, and the place's sky, sun, exposure and grade. `package --draft` is a preview that
never ships, in minutes: nothing baked (each palette recipe its plain colour, metal and roughness), scene.json marked
`draft`, which score-lib take-in refuses. `package --film` is a film's (an Unreal render, tools/unreal/scene):
its baked maps kept whole at scene_package.FILM_CAPS, not the game's texture caps. `package --pieces` writes the piece list instead (pieces.py, score.scene
version 2, 2099 #245) in seconds with no Blender: library pieces by address and digest, the place's made geometry as
small untextured GLBs, each copy's parts' looks.
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


def lines_of(given):
    """Polylines from 'x,z;x,z;...' texts."""
    return [[numbers(spot) for spot in line.split(";")] for line in given]


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
         "boxes = json.loads(sys.argv[5])\n"
         "words = [word for word in sys.argv[4].split(',') if word] or ([] if boxes else concept_objects.PROBES)\n"
         "json.dump(concept_objects.objects(sys.argv[1], sys.argv[2], words, boxes=boxes), open(sys.argv[3], 'w'),"
         " indent=1)")


def boxes_of(given):
    """{word: [x0, y0, x1, y1]} from 'word=x0,y0,x1,y1' texts."""
    named = [text.rpartition("=") for text in given or ()]
    return {word: numbers(box) for word, _, box in named}


def split(concept, folder, nouns=None, under="split", boxes=None):
    """The concept split into objects by SAM 3 on this PC's card (free), asked `nouns` (a comma list; the generic
    probes when neither nouns nor boxes are given) and the one thing in each of `boxes` ({word: pixel box}), its
    answer written as <folder>/<under>/objects.json."""
    import pathlib
    import subprocess
    path = f"{folder}/{under}/objects.json"
    done = subprocess.run([sys.executable, "-c", SPLIT, str(concept), f"{folder}/{under}", path, nouns or "",
                           json.dumps(boxes or {})],
                          env=this_pc_environment(), cwd=pathlib.Path(__file__).resolve().parents[3])
    if done.returncode != 0:
        raise place_build.Refused(f"the concept split on this PC's card failed (exit {done.returncode})")
    return path


def run(args):
    if args.step == "start":
        record = place_build.start(args.folder, args.place, args.concept, args.objects)
        if args.split:
            record = place_build.start_objects(args.folder, split(args.concept, args.folder, args.nouns))
        return record
    if args.step == "split":
        import pathlib
        under = f"split-{len(list(pathlib.Path(args.folder).glob('split*')))}"
        if not args.nouns and not args.box:
            raise place_build.Refused("split asks SAM 3 something: give --nouns or --box")
        found = split(pathlib.Path(args.folder) / "concept.png", args.folder, args.nouns, under, boxes_of(args.box))
        return place_build.more_objects(args.folder, found)
    if args.step == "from":
        return place_build.from_library(args.address, args.folder)
    if args.step == "camera":
        return place_build.camera(args.folder, numbers(args.eye), numbers(args.aim), args.fov)
    if args.step == "put":
        return place_build.put(args.folder, args.name, args.address, numbers(args.at), numbers(args.turn),
                               scale_of(args.scale), args.ground, args.wear.split(",") if args.wear else None,
                               args.clip, args.second, args.rest, args.on_ground)
    if args.step == "hold":
        return place_build.hold(args.folder, args.name, args.address, args.prop)
    if args.step == "dome":
        return place_build.dome(args.folder, args.name, args.radius, numbers(args.at), numbers(args.turn),
                                args.meridians, args.rings, args.rib, openings=[numbers(hole) for hole in args.opening])
    if args.step == "tube":
        return place_build.tube(args.folder, args.name, args.radius, args.length, numbers(args.at), numbers(args.turn),
                                args.hoops, args.rib, cap=numbers(args.cap) if args.cap else None,
                                cap_door=args.cap_door)
    if args.step == "stairs":
        return place_build.stairs(args.folder, args.name, args.storeys, numbers(args.at), numbers(args.turn),
                                  args.mirror, curtain=args.curtain, cut=args.cut,
                                  one_block=args.one_block, joined=args.joined or (), street=args.street_door)
    if args.step == "tracks":
        return place_build.tracks(args.folder, args.name, lines_of(args.rover), lines_of(args.boots), args.seed)
    if args.step == "rain":
        return place_build.rain(args.folder, args.name, numbers(args.low), numbers(args.high), args.height,
                                args.density, args.seed)
    if args.step == "ground":
        return place_build.ground(args.folder, args.name, args.radius, numbers(args.at))
    if args.step == "terrain":
        return place_build.terrain(args.folder, args.name, args.address, numbers(args.at), numbers(args.turn),
                                   [numbers(pad) for pad in args.pad])
    if args.step == "sky":
        return place_build.sky(args.folder, args.address, args.elevation, args.heading, args.strength, args.colour,
                               args.turn, args.background, args.exposure)
    if args.step == "sky-at":
        return place_build.sky_at(args.folder, args.scene, args.on, args.latitude, args.longitude, args.height,
                                  args.time, args.turn, args.exposure)
    if args.step == "view":
        return place_build.view(args.folder, args.name, numbers(args.eye), numbers(args.aim), args.fov, args.cut)
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
    if args.step == "cut":
        return place_build.camera_cut(args.folder, args.name)
    if args.step == "backdrop":
        return place_build.backdrop(args.folder, args.name)
    if args.step == "hollow":
        return place_build.hollow(args.folder, args.name, [numbers(region) for region in args.region])
    if args.step == "kind":
        return place_build.kind(args.folder, args.kind)
    if args.step == "door":
        return place_build.door(args.folder, args.name, args.opens, "slide" if args.slide else "hinge", args.lock,
                                args.side, args.crouch)
    if args.step == "refinish":
        return place_build.refinish(args.folder, args.name)
    if args.step == "plan":
        return place_build.plan(args.folder, args.source)
    if args.step == "dress":
        return place_build.dress(args.folder, args.name, args.address, args.row, args.side, args.support,
                                 args.height, args.every, args.front)
    if args.step == "list":
        return place_build.listing(args.folder)
    if args.step == "render":
        from score.stages.place_build import render
        return render.render(args.folder, args.width or render.WIDTH,
                             [name for name in (args.views or "").split(",") if name],
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
        return ready.check(args.folder, not args.no_settle, dict(given.split("=", 1) for given in args.among or []))
    if args.step == "make":
        from score.stages.place_build import maker
        return maker.make(args.folder, args.name, args.source, args.material, args.like, args.height,
                          numbers(args.size) if args.size else None, not args.no_take_in)
    if args.step == "route":
        from score.stages.place_build import ready
        points, length = ready.route(args.folder, [numbers(spot) for spot in args.through])
        return {"route": points, "metres": length}
    if args.step == "join":
        from score.stages.place_build import area
        return area.join(args.folder, args.doorway, args.to, numbers(args.inward) if args.inward else None)
    if args.step == "area":
        from score.stages.place_build import area
        folders = dict(given.split("=", 1) for given in args.place)
        record = area.area(args.plans, args.outside, folders, args.out, args.seat, args.stands)
        return {"seats": {name: seat["from"] for name, seat in record["seats"].items()},
                "joins": len(record["joins"]), "failed": len(record["faults"]), "faults": record["faults"][:6],
                "out": args.out}
    if args.step == "package":
        from score.stages.place_build import scene_package
        if args.pieces:
            from score.stages.place_build import pieces
            return pieces.packaged(args.folder, args.out)
        return scene_package.packaged(args.folder, args.out, draft=args.draft, film=args.film)
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
    step.add_argument("--nouns", help="word,word: what SAM 3 is asked (its generic probes when not given)")
    step = steps.add_parser("split", help="a laid place's concept asked for more nouns, their objects added")
    step.add_argument("folder")
    step.add_argument("--nouns")
    step.add_argument("--box", action="append", help="word=x0,y0,x1,y1: the one thing in that pixel box of the concept")
    step = steps.add_parser("from", help="a place entry of the library laid out as a place_build folder")
    step.add_argument("address")
    step.add_argument("folder")
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
    step = steps.add_parser("hold")
    for name in ("folder", "name", "address"):
        step.add_argument(name)
    step.add_argument("--prop")
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
    step.add_argument("--curtain", action="store_true")
    step.add_argument("--cut", action="store_true")
    step.add_argument("--one-block", action="store_true")
    step.add_argument("--joined", type=int, action="append", help="a storey whose flat door opens onto a place of "
                      "its own (no hall stub behind it); again for more")
    step.add_argument("--street-door", action="store_true", help="a street door in the entrance block's facade, its "
                      "ground floor the lobby the entrance opens off")
    step = steps.add_parser("rain")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--low", required=True, help="x,z of the box's near corner")
    step.add_argument("--high", required=True, help="x,z of the box's far corner")
    step.add_argument("--height", type=float, required=True)
    step.add_argument("--density", type=float, required=True, help="streaks a cubic metre")
    step.add_argument("--seed", type=int, default=0)
    step = steps.add_parser("tracks")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--rover", action="append", default=[], help="a rover's line: x,z;x,z;...")
    step.add_argument("--boots", action="append", default=[], help="a walker's line: x,z;x,z;...")
    step.add_argument("--seed", type=int, default=0)
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
    step = steps.add_parser("sky-at")
    step.add_argument("folder")
    step.add_argument("--scene")
    step.add_argument("--on")
    step.add_argument("--latitude", type=float)
    step.add_argument("--longitude", type=float)
    step.add_argument("--height", type=float, default=0.0)
    step.add_argument("--time")
    step.add_argument("--turn", type=float, default=0.0)
    step.add_argument("--exposure", type=float)
    step = steps.add_parser("plan")
    step.add_argument("folder")
    step.add_argument("source")
    step = steps.add_parser("dress")
    for name in ("folder", "name", "address", "row", "side"):
        step.add_argument(name)
    step.add_argument("--support")
    step.add_argument("--height", type=float, default=0.0)
    step.add_argument("--every", type=float)
    step.add_argument("--front", default="+z")
    step = steps.add_parser("view")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--eye", required=True)
    step.add_argument("--aim", required=True)
    step.add_argument("--fov", type=float, required=True)
    step.add_argument("--cut", action="store_true", help="it sees through place.json `cut` as the concept's view does")
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
    for name in ("remove", "refinish", "cut", "backdrop"):
        step = steps.add_parser(name)
        step.add_argument("folder")
        step.add_argument("name")
    step = steps.add_parser("hollow")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--region", action="append", required=True, help="x0,y0,z0,x1,y1,z1 in the scene's frame")
    for name in ("list", "compare"):
        steps.add_parser(name).add_argument("folder")
    step = steps.add_parser("door")
    step.add_argument("folder")
    step.add_argument("name")
    step.add_argument("--opens", action="store_true")
    step.add_argument("--slide", action="store_true")
    step.add_argument("--lock")
    step.add_argument("--side", choices=place_build.SIDES)
    step.add_argument("--crouch", action="store_true", help="a hatch the walkers cross crouching")
    step = steps.add_parser("kind")
    step.add_argument("folder")
    step.add_argument("kind", choices=place_build.KINDS)
    step = steps.add_parser("on")
    for name in ("folder", "name", "support"):
        step.add_argument(name)
    step.add_argument("--level", type=int)
    step.add_argument("--height", type=float)
    step = steps.add_parser("check")
    step.add_argument("folder")
    step.add_argument("--no-settle", action="store_true")
    step.add_argument("--among", action="append", help="place=folder: a neighbour the area seats it beside (both "
                      "`area --seat`ed), read in as the game lays it; again for each")
    step = steps.add_parser("make")
    for name in ("folder", "name", "source"):
        step.add_argument(name)
    step.add_argument("--material", required=True)
    step.add_argument("--like")
    step.add_argument("--height", type=float)
    step.add_argument("--size", help="wide,deep,tall metres: its longest side the model's, turned as its close-up "
                      "picture shows it (the prop benchmark)")
    step.add_argument("--no-take-in", action="store_true", help="keep the made files here, take nothing into score_lib")
    step = steps.add_parser("route")
    step.add_argument("folder")
    step.add_argument("--through", action="append", required=True)
    step = steps.add_parser("join")
    for name in ("folder", "doorway", "to"):
        step.add_argument(name)
    step.add_argument("--inward", help="x,z: the way into this place through the doorway (a leaf set in no shell)")
    step = steps.add_parser("area")
    step.add_argument("plans", help="the kept plans' folder ({home}/design/plans)")
    step.add_argument("outside", help="the area's outside place, whose plan holds the rest")
    step.add_argument("--place", action="append", required=True, help="place=folder; again for each place")
    step.add_argument("--out", help="seats.json: the seats and the joins check")
    step.add_argument("--seat", action="store_true", help="write each place's seat into its place.json, so its "
                      "package is laid in the area's frame")
    step.add_argument("--stands", help="the place laid in the area's frame, standing as laid; the rest seated onto it")
    step = steps.add_parser("package")
    step.add_argument("folder")
    step.add_argument("out")
    step.add_argument("--draft", action="store_true", help="a preview that never ships: no bake, each palette "
                      "recipe its plain colour, metal and roughness, scene.json marked draft (take-in refuses it)")
    step.add_argument("--film", action="store_true", help="for an Unreal film render (#221): every baked map kept "
                      "whole on maps up to scene_package.FILM_CAPS a side, not held at the game's texture caps")
    step.add_argument("--pieces", action="store_true", help="the piece list (score.scene version 2, pieces.py): "
                      "library pieces by address and digest, made pieces as small untextured GLBs, each part's look; "
                      "no Blender, no bake")
    step = steps.add_parser("render")
    step.add_argument("folder")
    step.add_argument("--width", type=int)
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
