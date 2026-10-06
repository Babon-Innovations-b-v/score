"""The robust route for a whole kit room, step by step (job robust-exp round three, 2026-10-06: the hub built the new
way end to end, as the route would run for a new room).

    python=~/.farm-factory-props/env/bin/python
    $python tools/props/library/route.py plan <kit layout> <work>       # models to make, and the cloud jobs
    $python tools/props/library/route.py layout <kit layout> <work>     # the game's layout over the made models
    $python tools/props/library/route.py install <work> <room>          # the made models into the game

`plan` sorts every kind of the room's kit layout (tools/props/scene/hub_kit.py writes it: where every piece stands,
as its kind) by sorter.py and makes one model per kind and size (and per what a piece of it shows: a door's label,
a ring plate's taper): code-built kinds in a few shared picture sets by where they are in the room (walls, wall gear
and doors, roof, floor and pit; inside/make_kit.py), generated kinds from their labelled parts (labels.py) with
their details (data/library/details.json) and closed into solids (inside/make_chunky.py). It writes <work>/plan.json
and the jobs <work>/job-*.json for ../cloud/library_bake.py.

`layout` writes <work>/layout.json, the game's layout (HubKit): every piece names its made model and is laid at the
model's own box (a model made at the laid size, so nothing is stretched), the glowing parts a code-built piece was
split into (make_kit.py: a screen's content, a lamp's lens) and a generated piece's screens as `part` pieces of their
own, and the room's lamps and floors as before. A generated model that fails the model check (gates/model.py) is
not placed: its pieces are left out and listed.

`install` copies the made models and their shared pictures into game/base/models/<room>_kit/ with the pictures'
import settings (BC7, high quality: an import left lossless took 3.7 GB of video memory in round two), points each
kind's own scene at its first model, and puts the layout in place (data/kit/<room>.json).
"""
import json
import pathlib
import re
import shutil
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "gates"))
import library  # noqa: E402
import sorter  # noqa: E402

REPO = library.REPO
DETAILS = REPO / "data/library/details.json"
# Texels a metre for code-built pieces (a shared picture set is capped at 4096 a side) and for generated pieces.
DENSITY = 1024
CHUNKY_DENSITY = 768
CHUNKY_FACES = 20000
SIZE_STEP = 0.005  # two pieces of a kind within this of each other's size share a model
# Code-built kinds by the picture set they share, by the start of their name; the rest are wall gear and doors.
ATLASES = (("roof", ("roof_", "lattice_", "ceiling_")),
           ("floor", ("ring_floor", "floor_", "tread_", "pit_", "machine_bay", "stair_")),
           ("walls", ("wall_lower", "wall_upper", "wall_skirting", "wall_cornice", "wall_corner", "hatch_wall",
                      "porthole")))
# A door's label by the way it leads on the base: the hub stands turned half round on its seat, so its own north
# (bearing 0) is the base's south.
DOOR_LABELS = {0: "label_south_hatch", 90: "label_west_hatch", 180: "label_north_hatch", 270: "label_east_hatch",
               330: "label_airlock"}


def own_name(kind):
    """A kind's name without its room's prefix (`hub_wall_lower_plain` -> `wall_lower_plain`)."""
    return kind.split("_", 1)[1]


def bearing_of(laid):
    """The bearing (degrees clockwise from north, -z) a piece's back looks toward: its wall's."""
    back = np.asarray(laid["z"])
    return round(float(np.degrees(np.arctan2(back[0], -back[2]))) % 360)


def shows(kind, laid):
    """What a piece shows that its model is made with, beyond its size."""
    found = {key: laid[key] for key in ("taper", "treads") if key in laid}
    if own_name(kind) == "hatch_wall_surround":
        found["label"] = DOOR_LABELS[bearing_of(laid) % 360]
    return found


def atlas_of(name):
    for atlas, starts in ATLASES:
        if name.startswith(starts):
            return atlas
    return "gear"


def made_size(size):
    return tuple(round(round(value / SIZE_STEP) * SIZE_STEP, 4) for value in size)


def plan(layout, takes):
    """Every piece's made model: {"models": {name: {kind, route, size, laid, atlas}}, "pieces": [name per piece]}."""
    models, by_key, pieces = {}, {}, []
    # A kind takes one route, its largest piece's: a lattice ring's short top beams are still beams.
    largest = {}
    for laid in layout["pieces"]:
        if max(laid["size"]) > max(largest.get(laid["kind"], [0.0])):
            largest[laid["kind"]] = laid["size"]
    routes = {kind: sorter.route(kind, size) for kind, size in largest.items()}
    for laid in layout["pieces"]:
        kind = laid["kind"]
        route = routes[kind]
        route = "code" if route == "decal" else route  # labels and notices are printed parts on code-built plates
        if route == "model" and own_name(kind) not in takes:
            raise SystemExit(f"{kind} is a generated kind with no labelled parts (labels.py)")
        extra = shows(kind, laid) if route == "code" else {}
        key = (kind, made_size(laid["size"]), json.dumps(extra, sort_keys=True))
        if key not in by_key:
            count = sum(1 for other in by_key if other[0] == kind) + 1
            name = f"{own_name(kind)}_{count}"
            by_key[key] = name
            models[name] = {"kind": kind, "route": route, "size": [float(value) for value in laid["size"]],
                            "laid": extra, "atlas": atlas_of(own_name(kind)) if route == "code" else name}
        pieces.append(by_key[key])
    return {"models": models, "pieces": pieces}


def jobs(planned, takes, work, place):
    """The cloud jobs: a make_kit job per shared picture set, one make_chunky job for every generated model."""
    wear, dirt = library.wear_of(place)
    specs = library.by_library(place)
    details = json.loads(DETAILS.read_text())
    found = {}
    for atlas in sorted({entry["atlas"] for entry in planned["models"].values() if entry["route"] == "code"}):
        found[f"kit-{atlas}"] = {
            "script": "make_kit.py", "out": str(work / "made"), "report": f"report-{atlas}.json",
            "atlas": f"{place}_{atlas}", "density": DENSITY,
            "wear": wear, "dirt": dirt, "seed": 3, "specs": specs,
            "pieces": [{"name": name, "kind": own_name(entry["kind"]), "size": entry["size"], "laid": entry["laid"]}
                       for name, entry in planned["models"].items()
                       if entry["route"] == "code" and entry["atlas"] == atlas]}
    chunky = []
    for name, entry in planned["models"].items():
        if entry["route"] != "model":
            continue
        own = details.get(entry["kind"], {})
        chunky.append({"name": name, "parts": str(takes[own_name(entry["kind"])]),
                       "base": own["turn"], "size": entry["size"],
                       "details": own.get("details", []), "screens": own.get("screens", [])})
    if chunky:
        found["chunky"] = {"script": "make_chunky.py", "out": str(work / "made"), "report": "report-chunky.json",
                           "density": CHUNKY_DENSITY,
                           "wear": wear, "dirt": dirt, "seed": 3, "faces": CHUNKY_FACES, "specs": specs,
                           "chunky": chunky}
    return found


def labelled_takes(folders):
    """Generated kinds -> their folder of labelled parts (a .ply per material, labels.py), each folder named for its
    Pixal3D take (`wall_cage_lamp-b`) or the take and a way (`conduit_box-4`)."""
    return {re.sub(r"(-b)?(-\d+)?$", "", pathlib.Path(folder).name): pathlib.Path(folder) for folder in folders}


def placed_at(laid, low, high):
    """A piece laid at its model's own box: low and high corners in the piece's frame at its laid size."""
    origin = np.asarray(laid["at"], dtype=np.float64)
    axes = [np.asarray(laid[axis], dtype=np.float64) for axis in ("x", "y", "z")]
    middle = [(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2]
    moved = dict(laid)
    moved["at"] = [round(float(value), 4) for value in origin + sum(axis * shift for axis, shift in zip(axes, middle))]
    moved["size"] = [round(float(high[axis] - low[axis]), 4) for axis in range(3)]
    return moved


def screen_piece(host, screen, model):
    """A generated piece's screen as a glowing part of its own on the host's front, at the depth the bake found."""
    wide, tall = screen["size"]
    deep = 0.012
    low = [screen["at"][0] - wide / 2, screen["at"][1] - tall / 2, screen["surface"] - deep]
    high = [screen["at"][0] + wide / 2, screen["at"][1] + tall / 2, screen["surface"]]
    found = placed_at(host, low, high)
    found.update(model=model, part="screen")
    found.pop("scored", None)
    return found


def screen_picture(variant):
    """The printed picture a screen variant shows (data/library/pictures/<name>.png)."""
    return library.variants(library.theme_library())[variant]["picture"]


def screen_model(name, picture, folder, size):
    """A generated piece's screen as a model of its own, written here rather than baked: a thin plate in the kit's
    frame at its laid `size` whose front (-z) shows the printed picture whole, its edges and back the picture's corner."""
    import trimesh
    from PIL import Image
    wide, tall, deep = size
    box = trimesh.creation.box(extents=(wide, tall, deep))
    box.apply_translation((0.0, tall / 2, 0.0))
    # Every face its own corners, so the front's picture does not run onto the edges.
    plate = trimesh.Trimesh(vertices=box.vertices[box.faces].reshape(-1, 3),
                            faces=np.arange(3 * len(box.faces)).reshape(-1, 3), process=False)
    front = np.repeat(box.face_normals[:, 2] < -0.5, 3)
    uv = np.zeros((len(plate.vertices), 2))
    uv[front, 0] = 0.5 - plate.vertices[front, 0] / wide  # seen from in front, the kit's +x is the viewer's left
    uv[front, 1] = plate.vertices[front, 1] / tall
    shown = Image.open(library.PICTURES / f"{picture}.png").convert("RGB")
    plate.visual = trimesh.visual.TextureVisuals(uv=uv, image=shown)
    plate.export(folder / f"{name}.gltf", embed_buffers=True, include_normals=True)  # one file: trimesh names loose buffers alike


def game_layout(layout, planned, reports, checks):
    """The game's layout over the made models; the generated models that failed their check and were left out."""
    made = {}
    for report in reports:
        made.update(report.get("pieces", report))
    pieces, held_back, models = [], {}, {}
    for laid, name in zip(layout["pieces"], planned["pieces"]):
        if checks.get(name, {}).get("pass") is False:
            held_back[name] = held_back.get(name, 0) + 1
            continue
        low, high = made[name]["bounds"]
        stretch = np.asarray(laid["size"]) / np.asarray(planned["models"][name]["size"])
        low, high = np.asarray(low) * stretch, np.asarray(high) * stretch
        own = placed_at(laid, low, high)
        own["model"] = name
        own.pop("scored", None)
        pieces.append(own)
        models.setdefault(name, {"glows": False})
        glow = f"{name}_glow"
        if glow in made:
            part = placed_at(laid, *(np.asarray(corner) * stretch for corner in made[glow]["bounds"]))
            part.update(model=glow, part="glow")
            part.pop("scored", None)
            pieces.append(part)
            models[glow] = {"glows": True}
        for index, screen in enumerate(made[name].get("screens", [])):
            screen_name = f"{name}_screen_{index + 1}"
            pieces.append(screen_piece(laid, screen, screen_name))
            models[screen_name] = {"glows": True, "picture": screen_picture(screen["variant"])}
    counts = {}
    for found in pieces:
        if "part" not in found:
            counts[found["kind"]] = counts.get(found["kind"], 0) + 1
    kinds = {kind: {key: value for key, value in about.items() if key in ("group", "light")}
             for kind, about in layout["kinds"].items() if kind in counts}
    room = {key: value for key, value in layout.items() if key not in ("pieces", "counts", "kinds")}
    return dict(room, counts=counts, kinds=kinds, models=models, pieces=pieces), held_back


IMPORT_SETTINGS = {"compress/mode": "2", "compress/high_quality": "true"}


def install(work, room):
    """The made models and their pictures into the game, every kind's scene pointed at its first model, the layout
    into data/kit/<room>.json."""
    layout = json.loads((work / "layout.json").read_text())
    folder = REPO / f"game/base/models/{room}_kit"
    # Godot's import files are kept, so a model installed again keeps its id and its import settings.
    imports = {found.relative_to(folder): found.read_text() for found in folder.rglob("*.import")} \
        if folder.exists() else {}
    if folder.exists():
        shutil.rmtree(folder)
    (folder / "textures").mkdir(parents=True)
    made = work / "made"
    for picture in (made / "textures").glob("*.png"):
        shutil.copy(picture, folder / "textures" / picture.name)
    for name, about in layout["models"].items():
        if "picture" in about:
            laid = next(found for found in layout["pieces"] if found["model"] == name)
            screen_model(name, about["picture"], folder, laid["size"])
            continue
        for suffix in (".gltf", ".bin"):
            shutil.copy(made / f"{name}{suffix}", folder / f"{name}{suffix}")
    first = {}
    for laid in layout["pieces"]:
        if "part" not in laid:
            first.setdefault(laid["kind"], laid["model"])
    for kind, model in first.items():
        scene = REPO / f"game/base/models/{kind}"
        if scene.exists():
            for old in scene.iterdir():
                old.unlink()
        scene.mkdir(exist_ok=True)
        (scene / f"{kind}.tscn").write_text(KIND_SCENE.format(room=room, model=model, node=node_name(kind)))
    for path, text in imports.items():
        if (folder / path.with_suffix("")).exists():
            (folder / path).write_text(text)
    (REPO / f"data/kit/{room}.json").write_text(json.dumps(layout, indent="\t") + "\n")
    return len(layout["models"]), len(first)


KIND_SCENE = """[gd_scene format=3]

[ext_resource type="PackedScene" path="res://game/base/models/{room}_kit/{model}.gltf" id="1_mesh"]

[node name="{node}" type="Node3D"]

[node name="Mesh" parent="." instance=ExtResource("1_mesh")]
"""


def node_name(kind):
    return "".join(part.capitalize() for part in kind.split("_"))


def picture_imports(folder):
    """After Godot first imports the shared pictures: their .import files set to BC7, high quality (normal maps
    keep their normal-map setting)."""
    changed = 0
    for found in pathlib.Path(folder).glob("textures/*.png.import"):
        text = found.read_text()
        for key, value in IMPORT_SETTINGS.items():
            text = re.sub(rf"^{re.escape(key)}=.*$", f"{key}={value}", text, flags=re.MULTILINE)
        if "_normal" in found.name:
            text = re.sub(r"^compress/normal_map=.*$", "compress/normal_map=1", text, flags=re.MULTILINE)
        found.write_text(text)
        changed += 1
    return changed


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    step = sys.argv[1]
    if step == "plan":
        layout = json.loads(pathlib.Path(sys.argv[2]).read_text())
        work = pathlib.Path(sys.argv[3])
        work.mkdir(parents=True, exist_ok=True)
        takes = labelled_takes(sys.argv[4:])
        planned = plan(layout, takes)
        (work / "plan.json").write_text(json.dumps(planned, indent=1))
        for name, job in jobs(planned, takes, work, layout.get("room", "hub")).items():
            (work / f"job-{name}.json").write_text(json.dumps(job, indent=1))
            print(name, len(job.get("pieces", job.get("chunky", []))))
        routes = [entry["route"] for entry in planned["models"].values()]
        print(len(planned["models"]), "models:", {route: routes.count(route) for route in set(routes)})
    elif step == "layout":
        layout = json.loads(pathlib.Path(sys.argv[2]).read_text())
        work = pathlib.Path(sys.argv[3])
        planned = json.loads((work / "plan.json").read_text())
        reports = [json.loads(path.read_text()) for path in sorted((work / "made").glob("report*.json"))]
        checks_path = work / "checks.json"
        checks = json.loads(checks_path.read_text()) if checks_path.exists() else {}
        found, held_back = game_layout(layout, planned, reports, checks)
        (work / "layout.json").write_text(json.dumps(found, indent="\t") + "\n")
        print(len(found["pieces"]), "pieces;", len(found["models"]), "models; held back:", held_back)
    elif step == "install":
        work = pathlib.Path(sys.argv[2])
        models, kinds = install(work, sys.argv[3])
        print(models, "models installed;", kinds, "kinds' scenes pointed at them")
    elif step == "imports":
        print(picture_imports(sys.argv[2]), "picture imports set to BC7")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
