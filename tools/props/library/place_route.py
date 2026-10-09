"""The robust route for an outdoor place (job place, 2026-10-07: the old station and the wreck in the game 2099; moved
here as a tool, JoeyKardolus/2099#129): an outdoor place has no kit layout, so every piece is a row of the place's
inventory (data/inventory/<place>.json) with its spots on the place's seat. The pieces are the route's own:
make_chunky for generated pieces (library surfaces only) and make_kit for the sorter's PLAIN kinds (pipe_straight for
walkway tubes, cable_bundle for cables, pit_floor_plate for a dust apron), its gates (gates/model.py, straight.py)
and its scene package (package.py) as the output any engine loads.

    python=.venv/bin/python
    $python tools/props/library/place_route.py split <labelled> <out a> <out b>    # a take too long for one piece
    $python tools/props/library/place_route.py plan <place> <work> [--take r1]     # models, cloud bake jobs
    $python tools/props/library/place_route.py check <place> <work>                # model gate, straightness
    $python tools/props/library/package.py <place> <work> <out>                    # the scene package, checked

<work> holds the place's labelled takes (parts/<row>-<take>/, labels.py), and gets plan-route.json, the bake jobs
(job-*.json, for cloud/library_bake.py), the baked models (made/) and the checks (checks.json). A generated kind's
turn (how its model is turned into the kit frame: x across, y up, z depth) and whether it is square are its
data/library/details.json entry, written when the place was planned.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import library  # noqa: E402

DETAILS = REPO / "data/library/details.json"
INVENTORIES = REPO / "data/inventory"
# Texels a metre a generated piece is baked at (the normal map's): near the walker's hands, and the cap a big one is
# held to by the bake (one 4096 picture a piece).
DENSITY = 1024
LARGEST = 4096
# Triangle budgets by what a piece is (the first world's asset budgets), and the fewest a piece is cut to.
LANDMARK = ("hab_lander", "first_module", "lab_module", "solar_mast", "solar_mast_dead", "comms_mast",
            "aft_section", "forward_section")
VEHICLE = ("rover",)
STRUCTURE = ("radiator", "power_unit", "parts_rack", "bag_pile", "bag_stack")
FACES = {"landmark": 60000, "vehicle": 60000, "structure": 19000, "furniture": 19000}
SMALLEST_FACES = 5000
# A generated piece's solid wall as a share of its largest side (two of make_chunky's voxels): at its 5 mm the big
# outdoor pieces' skins came back as slivers under the model check's 3 mm after the cut to their triangle budget.
WALL_SHARE = 150
# Pieces that passed at make_chunky's own 5 mm and whose sheets would read as slabs thicker (a solar blanket on a mast).
THIN_WALLED = ("solar_mast", "solar_mast_dead", "comms_mast")
# The builders the code rows are built as, and how each lies: tilt 90 lays a piece's front up (a cable or a plate
# on the ground). The camp grounds' mast and cable lengths are their own code builders, standing as built.
CODE_KINDS = {"walkway_tube": ("pipe_straight", 0.0), "cable_run": ("cable_bundle", 90.0),
              "apron": ("pit_floor_plate", 90.0), "mast": ("mast", 0.0), "ground_cable": ("ground_cable", 0.0)}
# Generated pieces are baked over this many machines' jobs, largest first, round robin.
CHUNKY_SETS = 2
MEMORY_CAP = ["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=16G"]


def budget_of(row_id):
    """Which triangle budget a row's piece is held to."""
    if row_id in LANDMARK:
        return "landmark"
    if row_id in VEHICLE:
        return "vehicle"
    return "structure" if row_id in STRUCTURE else "furniture"


def kit_size(size):
    """An inventory size (wide, deep, tall) as the kit frame's (wide, tall, deep)."""
    wide, deep, tall = size
    return [float(wide), float(tall), float(deep)]


def faces_for(row_id, size):
    """The triangles a generated piece is cut to: its budget, less for a small piece."""
    found = FACES[budget_of(row_id)]
    return int(max(SMALLEST_FACES, min(found, found * max(size) ** 2)))


def yaw_of(turn):
    """The yaw about up (degrees) of a details.json turn (rows of the rotation, glTF frame to the kit's)."""
    return round(float(np.degrees(np.arctan2(turn[2], turn[0]))), 3) % 360


def made_size(labelled, planned, yaw):
    """A generated piece's size in the kit frame: its labelled model's own proportions (turned by `yaw` about up),
    scaled as one so its largest planned side is as planned (a model is scaled uniformly; the plan's other two sides
    are what the picture gave, never stretched to). Read off its labelled parts, which stand in the finished model's
    frame, so a take split into two pieces (a torn leg) is sized as each piece."""
    import trimesh
    corners = np.vstack([trimesh.load(path, force="mesh", process=False).bounds
                         for path in sorted(labelled.glob("*.ply"))])
    found = corners.max(0) - corners.min(0)
    wide, tall, deep = (found[2], found[1], found[0]) if round(yaw / 90) % 2 == 1 else (found[0], found[1], found[2])
    scale = max(planned) / max(wide, tall, deep)
    return [round(float(side * scale), 3) for side in (wide, tall, deep)]


def refuse_patchy(labelled):
    """Stops the plan on a labelled take whose paint failed the patchiness check (patchy.py, written by labels.py)."""
    score = json.loads((labelled / "labels.json").read_text()).get("patchy")
    if score is not None and not score.get("pass"):
        raise SystemExit(f"{labelled.name}: its paint is patchy ({', '.join(score.get('faults', []))}); label it again")


def code_models(row, place):
    """A code row's models (one per length) and its pieces."""
    builder, tilt = CODE_KINDS[row["id"]]
    models, pieces = {}, []
    for spot in row["at"]:
        # A piece laid front up (tilt) shows its tall side along the ground and its depth as its height.
        size = [float(side) for side in row["size"]] if tilt else kit_size(row["size"])
        size[0] = round(spot.get("length", size[0]), 2)
        name = f"{row['id']}_{size[0]:g}".replace(".", "p")
        models.setdefault(name, {"kind": f"{place}_{row['id']}", "route": "code", "builder": builder, "size": size,
                                 "budget": "furniture", "tilt": tilt})
        pieces.append({"model": name, "spot": spot, "row": row["id"]})
    return models, pieces


def plan(place, work, take):
    """Every model the place needs: {name: {kind, route, size (kit), ...}}, and every piece: a model at a spot. Code
    rows make one model per length; generated rows one model per row (its pieces are scaled copies)."""
    inventory = json.loads((INVENTORIES / f"{place}.json").read_text())
    details = json.loads(DETAILS.read_text())
    models, pieces, children = {}, [], []
    for row in inventory["rows"]:
        if row["kind"] == "code":
            found, laid = code_models(row, place)
            models.update(found)
            pieces += laid
            continue
        kind = f"{place}_{row['id']}"
        labelled = work / "parts" / f"{row['id']}-{take}"
        refuse_patchy(labelled)
        yaw = yaw_of(details[kind]["turn"])
        size = made_size(labelled, kit_size(row["size"]), yaw)
        models[row["id"]] = {"kind": kind, "route": "model", "size": size, "budget": budget_of(row["id"]),
                             "faces": faces_for(row["id"], row["size"]), "yaw": yaw}
        if row.get("parent"):
            children.append({"model": row["id"], "parent": row["parent"]})
        pieces += [{"model": row["id"], "spot": spot, "row": row["id"]} for spot in row["at"]]
    found = {"scene": place, "take": take, "models": models, "pieces": pieces, "children": children,
             "frame": inventory["room"]["layout"].get("frame", ""),
             "on_seat": inventory["room"]["layout"].get("on_seat") or [0.0, 0.0]}
    (work / "plan-route.json").write_text(json.dumps(found, indent=1))
    return found


def code_jobs(planned, made, place, wear, dirt, specs):
    """make_kit jobs: a walkway tube's seen area (about 21 m2) takes a 4096 picture set of its own at 512 texels a
    metre; the cables and the apron share one (one shared set of 75.8 m2 was past the cap)."""
    sets = {}
    for name, entry in planned["models"].items():
        if entry["route"] != "code":
            continue
        piece = {"name": name, "kind": entry["builder"], "size": entry["size"], "laid": {}, "foot": 0.0}
        sets.setdefault(name if entry["builder"] == "pipe_straight" else "code", []).append(piece)
    return {f"kit-{name}": {"script": "make_kit.py", "out": str(made), "report": f"report-kit-{name}.json",
                            "atlas": f"{place}_{name}", "density": 512, "wear": wear, "dirt": dirt, "seed": 3,
                            "specs": specs, "pieces": pieces}
            for name, pieces in sets.items()}


def chunky_entry(name, entry, own, work, take):
    """One generated piece as make_chunky takes it."""
    wall = 0.005 if name in THIN_WALLED else round(max(0.005, max(entry["size"]) / WALL_SHARE), 4)
    return {"name": name, "parts": str(work / "parts" / f"{name}-{take}"), "base": own["turn"], "size": entry["size"],
            "screens": own.get("screens", []), "cuts": own.get("cuts", []),
            "density": min(DENSITY, LARGEST // max(1, int(np.ceil(max(entry["size"]))))),
            "decals": own.get("decals", []), "foot": 0.0, "faces": entry["faces"], "wall": wall}


def chunky_jobs(planned, made, work, wear, dirt, specs):
    """make_chunky jobs: the generated pieces over CHUNKY_SETS machines, largest first, round robin."""
    details = json.loads(DETAILS.read_text())
    chunky = [chunky_entry(name, entry, details[entry["kind"]], work, planned["take"])
              for name, entry in planned["models"].items() if entry["route"] == "model"]
    chunky.sort(key=lambda entry: -entry["faces"] * max(entry["size"]))
    found = {}
    for index in range(CHUNKY_SETS):
        share = chunky[index::CHUNKY_SETS]
        if share:
            found[f"chunky{index + 1}"] = {"script": "make_chunky.py", "out": str(made),
                                           "report": f"report-chunky{index + 1}.json", "density": DENSITY,
                                           "wear": wear, "dirt": dirt, "seed": 3, "faces": 19000, "specs": specs,
                                           "chunky": share}
    return found


def styled_as(place):
    """The place whose style, wear and library surfaces a place's pieces take: its inventory's `place` (the camp
    grounds are painted as the expedition camp), else its own name."""
    return json.loads((INVENTORIES / f"{place}.json").read_text()).get("place") or place


def jobs(planned, work, place):
    """The cloud bake jobs, each written to <work>/job-<name>.json."""
    wear, dirt = library.wear_of(styled_as(place))
    # A code-built part names a library variant; a generated piece's labelled parts are the place's own materials
    # (labels.py), which in the camp are not named as their variants (stainless is stainless_lander): both, as route.py.
    specs = dict(library.by_library(styled_as(place)), **library.resolved(styled_as(place)))
    made = work / "made"
    found = code_jobs(planned, made, place, wear, dirt, specs)
    found.update(chunky_jobs(planned, made, work, wear, dirt, specs))
    for name, job in found.items():
        (work / f"job-{name}.json").write_text(json.dumps(job, indent=1))
    return found


def check_layout(planned):
    """The model gate's layout: each model once, at its kit size, under its kind."""
    return {"pieces": [{"kind": entry["kind"], "model": name, "size": entry["size"]}
                       for name, entry in planned["models"].items()],
            "models": {name: {} for name in planned["models"]}}


def square_models(planned):
    """The generated models whose kind should come out square (details.json `square`)."""
    details = json.loads(DETAILS.read_text())
    return [name for name, entry in planned["models"].items()
            if entry["route"] == "model" and details.get(entry["kind"], {}).get("square")]


def check(work):
    """The model gate on every made model into <work>/checks.json, and straightness on the square ones; the names
    that failed."""
    planned = json.loads((work / "plan-route.json").read_text())
    (work / "check-layout.json").write_text(json.dumps(check_layout(planned), indent=1))
    subprocess.run(MEMORY_CAP + [sys.executable, str(HERE.parent / "gates/model.py"), str(work / "check-layout.json"),
                                 "--models", str(work / "made"), "--report", str(work / "checks.json")],
                   check=True, stdout=subprocess.DEVNULL)
    checks = json.loads((work / "checks.json").read_text())
    for name in square_models(planned):
        done = subprocess.run(MEMORY_CAP + [sys.executable, str(HERE / "straight.py"),
                                            str(work / "made" / f"{name}.gltf")], capture_output=True, text=True)
        checks[name]["straight"] = done.returncode == 0
        checks[name]["pass"] = checks[name]["pass"] and done.returncode == 0
    (work / "checks.json").write_text(json.dumps(checks, indent=1))
    return sorted(name for name, found in checks.items() if not found.get("pass"))


def split(source, first, second):
    """A labelled take cut in two across its longest side (a take longer than one piece may be, the torn leg): every
    material's .ply cut by its faces' middles at the middle of that side, into two labelled folders."""
    import trimesh
    if source.resolve() in (first.resolve(), second.resolve()):
        raise SystemExit("split writes two new folders; neither may be the labelled take it reads")
    meshes = {path.stem: trimesh.load(path, force="mesh", process=False) for path in sorted(source.glob("*.ply"))}
    every = np.vstack([mesh.vertices for mesh in meshes.values()])
    axis = int(np.argmax(every.max(0) - every.min(0)))
    middle = (every.max(0)[axis] + every.min(0)[axis]) / 2
    for out, below in ((first, True), (second, False)):
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        for name, mesh in meshes.items():
            faces = mesh.triangles_center[:, axis] < middle if below else mesh.triangles_center[:, axis] >= middle
            if faces.sum() >= 50:
                mesh.submesh([np.nonzero(faces)[0]], append=True).export(out / f"{name}.ply")
        shutil.copy(source / "labels.json", out / "labels.json")
    return axis, float(middle)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=("split", "plan", "check"))
    parser.add_argument("names", nargs="+", help="split: <labelled> <out a> <out b>; plan, check: <place> <work>")
    parser.add_argument("--take", default="r1", help="the takes' label (parts/<row>-<take>)")
    options = parser.parse_args()
    if options.step == "split":
        print(json.dumps(dict(zip(("axis", "middle"), split(*(pathlib.Path(name) for name in options.names))))))
        return
    place, work = options.names[0], pathlib.Path(options.names[1])
    if options.step == "plan":
        planned = plan(place, work, options.take)
        for name, job in jobs(planned, work, place).items():
            print(name, len(job.get("pieces", job.get("chunky", []))))
        routes = [entry["route"] for entry in planned["models"].values()]
        print(len(planned["models"]), "models:", {route: routes.count(route) for route in sorted(set(routes))},
              len(planned["pieces"]), "pieces")
        return
    failed = check(work)
    print("checks failed:", ", ".join(failed) if failed else "none")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
