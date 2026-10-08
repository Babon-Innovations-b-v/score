"""The robust route for a whole kit room, step by step (job robust-exp round three, 2026-10-06: the hub built the new
way end to end, as the route would run for a new room).

    python=~/.farm-factory-props/env/bin/python
    $python tools/props/library/route.py plan <kit layout> <work>       # models to make, and the cloud jobs
    $python tools/props/library/route.py layout <kit layout> <work>     # the game's layout over the made models
    $python tools/props/library/route.py install <work> <room>          # the made models into the game
    $python tools/props/library/route.py fittings <work>                # method B's check: the fittings' parts seen
    $python tools/props/library/route.py precheck <work>                # the model check on the code models, pre-bake

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

`install` copies the made models and their shared pictures into game/base/models/<room>_kit/, stores the pictures
compressed and stops a room past its budget (stored.py), with the pictures'
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
import stored  # noqa: E402

REPO = library.REPO
DETAILS = REPO / "data/library/details.json"
# Composites split into one model per real-world object (round six): a parent kind's children, each its own kind
# standing where the parent leaves room for it, in the parent's kit frame.
COMPOSITES = REPO / "data/library/composites.json"
# Texels a metre (the normal map's; colour gets half), by how near the player's hands a piece comes (the coordinator,
# hub round four): NEAR within arm's reach of the walkway or the pit floor, FAR for the roof and the high walls. A
# shared picture set takes its set's (SET_DENSITY); a generated piece is near when its middle stands under REACH_HIGH
# above the walkway.
NEAR = 1024
FAR = 512
# Scenery seen only from afar (the prologue build, 2026-10-07: the square, the launch pad and the city round them are
# 10 to 300 m from the balcony): a kind whose own name starts with DISTANT_PREFIX takes DISTANT texels a metre.
DISTANT = 128
DISTANT_PREFIX = "far_"
# The expedition camp's soft goods (mars-build, 2026-10-07): the domes' fabric shell seen from outside and their
# ceiling over 3.4 m are large curved pieces whose quilting reads at 256 texels a metre; their lining walls and deck
# take FAR. At NEAR one wall panel alone overflowed a 4096 set.
CAMP_SOFT = 256
REACH_HIGH = 1.8
PIT_DEEP = 0.9  # hub_kit.PIT_DEEP: the pit's floor under the walkway
SET_DENSITY = {"roof": FAR, "floor": NEAR, "walls_low": NEAR, "walls_high": FAR, "gear": NEAR, "furniture": NEAR,
               "fittings": NEAR, "distant": DISTANT, "camp_shell": CAMP_SOFT, "camp_high": CAMP_SOFT, "camp_floor": FAR,
               "camp_walls": FAR, "plaster": FAR}
# The bake's largest picture side and the share of it packed UV islands fill (inside/bake.py), and how much of that a
# shared set is planned to fill, leaving room for packing, print drawn sharp and the faces a box's estimate misses (both
# sides of an open box's thin walls: planned at 0.7, a floor set came out 1% past the cap, 2026-10-07).
LARGEST = 4096
UV_FILL = 0.6
SET_SLACK = 0.5
# A set left this small a share of a set's room joins another set of its density with room for it (`absorbed`).
SLIVER = 0.1
MEASURED_SLACK = 0.85
CHUNKY_FACES = 19000  # triangles: a prop's furniture budget is 20,000 (asset_check), its detail parts take the rest
# A smaller object gets fewer (round six: 26 tools of 19,000 each put half a million triangles on one tool board): the
# budget by the square of its largest side against a metre, never under SMALLEST_FACES (the owner's check on the tools
# up close: at 800 to 1,700 the pliers' outline went angular; at 5,000 they match the 19,000 model, baked alike).
SMALLEST_FACES = 5000
SIZE_STEP = 0.005  # two pieces of a kind within this of each other's size share a model
# Code-built kinds by the picture set they share, by the start of their name; the rest are wall gear and doors.
ATLASES = (("distant", (DISTANT_PREFIX,)),
           # Earth's big plain plaster, board and stair surfaces (the prologue build): broad and flat, half the density.
           ("plaster", ("plaster_", "render_wall", "floorboards", "landing", "stair_flight")),
           ("fittings", ("hatch_", "porthole_panel", "wall_lower_vent", "notice_board")),  # method B's room fittings
           ("roof", ("roof_", "lattice_", "ceiling_")),
           ("floor", ("ring_floor", "floor_", "tread_", "pit_", "machine_bay", "stair_", "under_floor")),
           ("walls_low", ("wall_lower", "wall_skirting", "wall_corner")),
           ("walls_high", ("wall_upper", "wall_cornice", "backer", "status_display")),  # the display hangs high
           # the expedition camp's domes (mars-build, 2026-10-07): their shell and ceiling at CAMP_SOFT, the lining's
           # walls and deck at FAR
           ("camp_shell", ("shell_gore", "foot_ring", "passage_hull")),
           ("camp_high", ("dome_ceiling_gore", "dome_roof_cap", "rod_lamp")),
           ("camp_floor", ("dome_deck_wedge", "passage_lining")),
           ("camp_walls", ("dome_wall_panel", "dome_window_panel", "dome_rib", "dome_opening_frame", "partition")))
# The room's furniture: the inventory's rows the route makes that are not kit pieces (the console, the lab bench, the
# chair, the lockers, the comms desk, the toolboard), each placed by the game as its prop. They go through the sorter
# like every kit kind (round four, 2026-10-07: round three sent them to code by a fixed table, with no check, and the
# room lost their detail).
FURNITURE_MADE = "made by the route"
# The console's live screens (the Workstation's feed and side screens) are glass plates written at install, dark until
# the Workstation paints its content on them: centred and facing +z, as the quads they replace were.
LIVE_SCREEN = {"name": "console_screen_1", "size": [0.44, 0.26, 0.004]}
# What the console's two side screens show from habitat level 2: printed pictures, written beside the live screen on
# its dark glass as <name>_<side>.png for the Workstation to paint on.
LIVE_SCREEN_SHOWS = {"left": "screen_status", "right": "console_systems"}
# A desk's status lamp (StatusLamp): a lens the route writes, which the game lights red or green.
STATUS_LAMP = {"name": "status_lamp_1", "radius": 0.03}
# The colour of a screen switched off, where no picture is given (8-bit sRGB).
DARK_GLASS = (14, 16, 19)
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


# What a laid piece shows that its code-built model is made with (a print's picture and frame, a plaster wall's dado
# band, a rail's rise: the prologue build).
SHOWN = ("taper", "treads", "openings", "arc", "material", "print", "frame", "dado", "rises_to", "label")


def shows(kind, laid):
    """What a piece shows that its model is made with, beyond its size."""
    found = {key: laid[key] for key in SHOWN if key in laid}
    found.update(laid.get("shows", {}))  # a kit room's composite parent or child: what its build shows (room_kit.py)
    if kind == "hub_hatch_wall_surround":
        found["label"] = DOOR_LABELS[bearing_of(laid) % 360]
    return found


def atlas_of(name):
    for atlas, starts in ATLASES:
        if name.startswith(starts):
            return atlas
    return "gear"


def made_size(size):
    return tuple(round(round(value / SIZE_STEP) * SIZE_STEP, 4) for value in size)


def furniture(inventory):
    """The room's furniture models: {name: {kind, route, size, laid, atlas, prop}}, one per furniture row
    (FURNITURE_MADE) and per row a game node draws as its prop (`made_as` "prop": the airlock's moving door leaves),
    routed by the sorter, its size (wide, tall, deep) from the row's (wide, deep, tall)."""
    found = {}
    composites = json.loads(COMPOSITES.read_text()) if COMPOSITES.exists() else {}
    for row in inventory["rows"]:
        if (row.get("made") != FURNITURE_MADE and row.get("made_as") != "prop") or row.get("parent"):
            continue
        wide, deep, tall = row["size"]
        kind = f"{inventory.get('scene', 'hub')}_{row['id']}"
        route = sorter.planned_route(kind)
        laid = composites.get(kind, {}).get("laid", {})  # what a parent's own build shows (a toolboard's tool layout)
        found[f"{row['id']}_1"] = {"kind": kind, "route": route, "size": [wide, tall, deep], "laid": laid,
                                   "atlas": "furniture" if route == "code" else f"{row['id']}_1",
                                   "prop": row.get("prop") or row["thing"].split(":", 1)[1], "near": True,
                                   "foot": min((foot_of(spot["y"]) for spot in row.get("at", [])), default=0.0)}
    found.update(children(found, composites))
    return found


def children(parents, composites):
    """The parents' children (data/library/composites.json): one model per child kind, size and what it shows, routed
    by the sorter like any kind; each parent lists where its children stand (`children`: model, at, turn), which its
    prop scene places them by."""
    found, by_key = {}, {}
    for parent_name, parent in parents.items():
        for child in composites.get(parent["kind"], {}).get("children", []):
            kind, laid = child["kind"], child.get("laid", {})
            key = (kind, made_size(child["size"]), json.dumps(laid, sort_keys=True))
            if key not in by_key:
                name = f"{own_name(kind)}_{sum(1 for other in by_key if other[0] == kind) + 1}"
                by_key[key] = name
                route = sorter.planned_route(kind)
                found[name] = {"kind": kind, "route": route, "size": list(child["size"]), "laid": laid,
                               "atlas": "furniture" if route == "code" else name, "near": True,
                               "foot": round(parent["foot"] + child["at"][1], 3), "child_of": parent_name}
            parent.setdefault("children", []).append({"model": by_key[key], "at": child["at"],
                                                      "turn": child.get("turn", 0.0)})
    return found


def plan(layout, takes, inventory=None):
    """Every piece's made model: {"models": {name: {kind, route, size, laid, atlas}}, "pieces": [name per piece]}, and
    the room's furniture as models placed by the game rather than the kit; stops on a generated kind with no labelled
    parts."""
    models, by_key, pieces = {}, {}, []
    for laid in layout["pieces"]:
        kind = laid["kind"]
        route = sorter.planned_route(kind)
        extra = shows(kind, laid) if route == "code" else {}
        key = (kind, made_size(laid["size"]), json.dumps(extra, sort_keys=True))
        if key not in by_key:
            count = sum(1 for other in by_key if other[0] == kind) + 1
            name = f"{own_name(kind)}_{count}"
            by_key[key] = name
            models[name] = {"kind": kind, "route": route, "size": [float(value) for value in laid["size"]],
                            "laid": extra, "atlas": atlas_of(own_name(kind)) if route == "code" else name,
                            "near": False}
        # A layout may say a piece is near or not and where its foot stands, where its height over the room's one
        # walkway cannot (the prologue build: a stairwell's landings, a street's facades).
        models[by_key[key]]["near"] |= laid.get("near", middle_high(laid) < REACH_HIGH)
        models[by_key[key]]["foot"] = min(models[by_key[key]].get("foot", 99.0),
                                          laid.get("foot", foot_of(laid["at"][1])))
        pieces.append(by_key[key])
    models.update(furniture(inventory) if inventory is not None else {})
    missing = sorted({entry["kind"] for entry in models.values()
                      if entry["route"] == "model" and own_name(entry["kind"]) not in takes})
    if missing:
        raise SystemExit(f"generated kinds with no labelled parts (labels.py): {', '.join(missing)}")
    return {"models": models, "pieces": pieces}


def jobs(planned, takes, work, place):
    """The cloud jobs: a make_kit job per shared picture set, one make_chunky job for every generated model."""
    wear, dirt = library.wear_of(place)
    # A code-built part names a library variant; a generated piece's labelled parts are the place's own materials
    # (labels.py), which in the habitat are not named as their variants (brushed_steel takes bare_steel): both.
    specs = dict(library.by_library(place), **library.resolved(place))
    details = json.loads(DETAILS.read_text())
    found = {}
    for atlas, names in shared_sets(planned, measured_areas(work)).items():
        found[f"kit-{atlas}"] = {
            "script": "make_kit.py", "out": str(work / "made"), "report": f"report-{atlas}.json",
            "atlas": f"{place}_{atlas}", "density": SET_DENSITY[set_of(atlas)],
            "wear": wear, "dirt": dirt, "seed": 3, "specs": specs,
            "pieces": [{"name": name, "kind": own_name(planned["models"][name]["kind"]),
                        "size": planned["models"][name]["size"], "laid": planned["models"][name]["laid"],
                        "foot": planned["models"][name].get("foot")}
                       for name in names]}
    chunky = []
    for name, entry in planned["models"].items():
        if entry["route"] != "model":
            continue
        own = details.get(entry["kind"], {})
        # Method B (hub round five): the pipeline gives shape only; surfaces are the library's alone, never the
        # picture's colours (round four's picture layer brought each piece its own rust and stains), and print comes
        # as the kind's few decals, placed on purpose (details.json `decals`).
        chunky.append({"name": name, "parts": str(takes[own_name(entry["kind"])]),
                       "base": own["turn"], "size": entry["size"], "screens": own.get("screens", []),
                       "cuts": own.get("cuts", []), "density": density_of(entry),
                       "decals": own.get("decals", []), "foot": entry.get("foot"), "faces": faces_for(entry["size"]),
                       "regions": own.get("regions", [])})
        if "wall" in own:  # a piece of thin rails and hooks closed thicker, so its solid copy keeps a 3 mm wall
            chunky[-1]["wall"] = own["wall"]
    if chunky:
        found["chunky"] = {"script": "make_chunky.py", "out": str(work / "made"), "report": "report-chunky.json",
                           "density": NEAR,
                           "wear": wear, "dirt": dirt, "seed": 3, "faces": CHUNKY_FACES, "specs": specs,
                           "chunky": chunky}
    return found


def density_of(entry):
    """A generated piece's texels a metre: DISTANT for scenery seen only from afar, else NEAR or FAR by its reach."""
    if own_name(entry["kind"]).startswith(DISTANT_PREFIX):
        return DISTANT
    return NEAR if entry.get("near", True) else FAR


def foot_of(high):
    """How high a foot at `high` (over the walkway) stands over the floor it stands on: the walkway's, or the pit's
    PIT_DEEP below it (the kick wear, method B)."""
    return round(max(0.0, high + PIT_DEEP if high < -0.05 else high), 3)


def faces_for(size):
    """A generated piece's triangle budget by its size: CHUNKY_FACES for a metre or more, by the square of its largest
    side below that, never under SMALLEST_FACES."""
    return int(max(SMALLEST_FACES, min(CHUNKY_FACES, CHUNKY_FACES * max(size) ** 2)))


def middle_high(laid):
    """How high a laid piece's middle stands above the walkway."""
    return float(laid["at"][1] + laid["y"][1] * laid["size"][1] / 2)


def set_of(chunk):
    """The named picture set (ATLASES) a set of shared_sets belongs to: `walls_low_2` -> `walls_low`."""
    return chunk if chunk in SET_DENSITY else chunk.rsplit("_", 1)[0]


def seen_area(size):
    """A code-built piece's area the room sees, from its box (wide, tall, deep): all but its back."""
    wide, tall, deep = size
    return wide * tall + 2 * deep * (wide + tall)


def shared_sets(planned, measured=None):
    """The code-built models by the picture set they share: each named set (ATLASES) split into as few sets as keep
    their seen area within one LARGEST-sided picture at the set's density, named `<set>` or `<set>_<n>`: largest
    first, each into the first set it still fits (round six: in layout order a wall vent took a 4096 set of its own
    between two door walls). A model's area is its measured one when the work folder has it (`measured`, from its
    own build: measure_areas), with MEASURED_SLACK spare for packing; else its box's estimate with SET_SLACK spare (the
    estimate missed bolts, cables and louvres by up to four and a half times, round six). The bake stops a set that
    still does not fit (bake.Atlas)."""
    measured = measured or {}
    found = {}
    for atlas in sorted({entry["atlas"] for entry in planned["models"].values() if entry["route"] == "code"}):
        members = [name for name, entry in planned["models"].items()
                   if entry["route"] == "code" and entry["atlas"] == atlas]

        def area_of(name):
            if name not in measured:
                return seen_area(planned["models"][name]["size"])
            return measured[name]["near" if SET_DENSITY[atlas] >= NEAR else "far"]  # bake.SHARP_FROM

        slack = MEASURED_SLACK if all(name in measured for name in members) else SET_SLACK
        room = slack * UV_FILL * (LARGEST / SET_DENSITY[atlas]) ** 2
        chunks, areas = [], []
        for name in sorted(members, key=lambda name: -area_of(name)):
            place = next((index for index, used in enumerate(areas) if used + area_of(name) <= room), None)
            if place is None:
                chunks.append([])
                areas.append(0.0)
                place = len(chunks) - 1
            chunks[place].append(name)
            areas[place] += area_of(name)
        for index, names in enumerate(chunks):
            found[atlas if len(chunks) == 1 else f"{atlas}_{index + 1}"] = names
    return absorbed(found, planned, measured)


def absorbed(found, planned, measured):
    """The sets with every one left as a sliver (under SLIVER of a set's room: two pipe lengths spilt over from a full
    set, step 0 of the modules round, which put a 4096 picture set on the card for 0.13 m2) taken into another set of
    the same density that still has room for it."""
    def area_of(chunk):
        density = SET_DENSITY[set_of(chunk)]
        return sum(measured[name]["near" if density >= NEAR else "far"] if name in measured
                   else seen_area(planned["models"][name]["size"]) for name in found[chunk])

    def room_of(chunk):
        return MEASURED_SLACK * UV_FILL * (LARGEST / SET_DENSITY[set_of(chunk)]) ** 2

    for chunk in sorted(found, key=area_of):
        if chunk not in found or area_of(chunk) >= SLIVER * room_of(chunk):
            continue
        host = next((other for other in sorted(found, key=area_of) if other != chunk
                     and SET_DENSITY[set_of(other)] == SET_DENSITY[set_of(chunk)]
                     and area_of(other) + area_of(chunk) <= room_of(other)), None)
        if host is not None:
            found[host] = found[host] + found.pop(chunk)
    return found


def measured_areas(work):
    """The code-built models' measured seen areas (<work>/areas.json, measure_areas), or none."""
    path = pathlib.Path(work) / "areas.json"
    return json.loads(path.read_text()) if path.exists() else {}


def labelled_takes(folders):
    """Generated kinds -> their folder of labelled parts (a .ply per material, labels.py), each folder named for its
    Pixal3D take (`wall_cage_lamp-b`, a round's `comms-r4` or `talllocker-r4f`) or the take and a way
    (`conduit_box-4`)."""
    return {re.sub(r"(-r\d+[a-z]?)?(-b)?(-\d+)?$", "", pathlib.Path(folder).name): pathlib.Path(folder)
            for folder in folders}


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
    if screen.get("facing") == "down":  # a hanging lamp's lens: under the piece, `at` its (x, z), `size` wide by long
        low = [screen["at"][0] - wide / 2, screen["surface"] - deep, screen["at"][1] - tall / 2]
        high = [screen["at"][0] + wide / 2, screen["surface"], screen["at"][1] + tall / 2]
    else:
        low = [screen["at"][0] - wide / 2, screen["at"][1] - tall / 2, screen["surface"] - deep]
        high = [screen["at"][0] + wide / 2, screen["at"][1] + tall / 2, screen["surface"]]
    found = placed_at(host, low, high)
    found.update(model=model, part="screen")
    found.pop("scored", None)
    return found


def screen_picture(variant):
    """The printed picture a screen variant shows (data/library/pictures/<name>.png)."""
    return library.variants(library.theme_library())[variant]["picture"]


def screen_model(name, picture, folder, size, live=False):
    """A screen as a model of its own, written here rather than baked: a thin plate at `size` showing the printed
    `picture` whole on its front, its edges and back the picture's corner (no picture: dark glass). A generated
    piece's screen stands in the kit's frame, its front -z; a live screen (`live`) is centred, its front +z, as the
    quad it replaces was, for the game to paint its content on."""
    import trimesh
    from PIL import Image
    wide, tall, deep = size
    box = trimesh.creation.box(extents=(wide, tall, deep))
    if not live:
        box.apply_translation((0.0, tall / 2, 0.0))
    # Every face its own corners, so the front's picture does not run onto the edges.
    plate = trimesh.Trimesh(vertices=box.vertices[box.faces].reshape(-1, 3),
                            faces=np.arange(3 * len(box.faces)).reshape(-1, 3), process=False)
    front = np.repeat(box.face_normals[:, 2] > 0.5 if live else box.face_normals[:, 2] < -0.5, 3)
    uv = np.zeros((len(plate.vertices), 2))
    # Seen from in front, the kit's +x is the viewer's left; a live screen is seen from +z, its +x on the right.
    uv[front, 0] = 0.5 + plate.vertices[front, 0] / wide if live else 0.5 - plate.vertices[front, 0] / wide
    uv[front, 1] = plate.vertices[front, 1] / tall + (0.5 if live else 0.0)
    shown = Image.new("RGB", (64, 64), DARK_GLASS) if picture is None else \
        Image.open(library.PICTURES / f"{picture}.png").convert("RGB")
    plate.visual = trimesh.visual.TextureVisuals(uv=uv, image=shown)
    write_gltf(name, plate, folder, shown)


def on_dark_glass(picture):
    """A printed picture (content on a clear ground) laid over a screen's dark glass, as one opaque picture."""
    from PIL import Image
    shown = Image.open(library.PICTURES / f"{picture}.png").convert("RGBA")
    glass = Image.new("RGBA", shown.size, DARK_GLASS + (255,))
    return Image.alpha_composite(glass, shown).convert("RGB")


def lamp_model(name, lamp, folder):
    """A status lamp's lens: a bead, round from every side, in a pale picture the game lights red or green."""
    import trimesh
    from PIL import Image
    lens = trimesh.creation.uv_sphere(radius=lamp["radius"], count=[12, 12])
    pale = Image.new("RGB", (8, 8), (235, 235, 230))
    lens.visual = trimesh.visual.TextureVisuals(uv=np.full((len(lens.vertices), 2), 0.5), image=pale)
    write_gltf(name, lens, folder, pale)


def write_gltf(name, mesh, folder, picture):
    """A trimesh mesh as <name>.gltf with one <name>.bin and its picture as <name>.png beside it (trimesh names its
    buffers alike in every file, and an image inside the glTF is pulled out by Godot into a loose file the next install
    would not bring back)."""
    import trimesh.exchange.gltf
    written = trimesh.exchange.gltf.export_gltf(mesh, include_normals=True)
    found = json.loads(written["model.gltf"])
    joined, starts = b"", []
    for buffer in found["buffers"]:
        starts.append(len(joined))
        joined += written[buffer["uri"]] + b"\0" * (-len(written[buffer["uri"]]) % 4)
    for view in found["bufferViews"]:
        view["byteOffset"] = view.get("byteOffset", 0) + starts[view["buffer"]]
        view["buffer"] = 0
    found["buffers"] = [{"uri": f"{name}.bin", "byteLength": len(joined)}]
    found["images"] = [{"uri": f"{name}.png"} for _ in found["images"]]
    (folder / f"{name}.bin").write_bytes(joined)
    picture.save(folder / f"{name}.png")
    import hashlib
    found.setdefault("asset", {}).setdefault("extras", {})["bin_md5"] = hashlib.md5(joined).hexdigest()
    (folder / f"{name}.gltf").write_text(json.dumps(found))


def game_layout(layout, planned, reports, checks):
    """The game's layout over the made models; the generated models that failed their check and were left out."""
    made = {}
    for report in reports:
        made.update(report.get("pieces", report))
    failed = sorted({entry["kind"] for entry in planned["models"].values()
                     if entry["route"] == "code" and sorter.route(entry["kind"]) != "code"})
    if failed:
        raise SystemExit(f"code builds that do not show every part their close-up has, or lay a print over a part "
                         f"(`route.py fittings` records them; send them to the pipeline): {', '.join(failed)}")
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
        models.setdefault(name, {"glows": False, "route": planned["models"][name]["route"]})
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
    for name, entry in planned["models"].items():
        if "prop" not in entry and "child_of" not in entry:
            continue
        if "prop" in entry:
            models[name] = {"glows": False, "route": entry["route"], "prop": entry["prop"], "size": entry["size"],
                            "children": entry.get("children", [])}
        else:
            models[name] = {"glows": False, "route": entry["route"], "child_of": entry["child_of"],
                            "size": entry["size"]}
        if f"{name}_glow" in made:
            models[f"{name}_glow"] = {"glows": True, "part_of": name}
    if layout.get("room", "hub") == "hub":  # the Workstation's live screens and the desks' status lamp
        models[LIVE_SCREEN["name"]] = {"glows": True, "picture": None, "live": True, "size": LIVE_SCREEN["size"],
                                       "shows": LIVE_SCREEN_SHOWS}
        models[STATUS_LAMP["name"]] = {"glows": True, "lamp": STATUS_LAMP}
    counts = {}
    for found in pieces:
        if "part" not in found:
            counts[found["kind"]] = counts.get(found["kind"], 0) + 1
    kinds = {kind: {key: value for key, value in about.items() if key in ("group", "light", "solid", "outside")}
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
            size = about.get("size") or next(found for found in layout["pieces"] if found["model"] == name)["size"]
            screen_model(name, about["picture"], folder, size, about.get("live", False))
            for side, picture in about.get("shows", {}).items():
                on_dark_glass(picture).save(folder / f"{name}_{side}.png")
            continue
        if "lamp" in about:
            lamp_model(name, about["lamp"], folder)
            continue
        shutil.copy(made / f"{name}.bin", folder / f"{name}.bin")
        stamped(made / f"{name}.gltf", folder / f"{name}.gltf")
    first, sizes = {}, {}
    for laid in layout["pieces"]:
        if "part" not in laid:
            first.setdefault(laid["kind"], laid["model"])
            sizes.setdefault(laid["model"], laid["size"])
    for kind, model in first.items():
        scene = REPO / f"game/base/models/{kind}"
        if scene.exists():
            for old in scene.iterdir():
                old.unlink()
        scene.mkdir(exist_ok=True)
        wide, tall, deep = sizes[model]
        (scene / f"{kind}.tscn").write_text(KIND_SCENE.format(room=room, model=model, node=node_name(kind),
                                                              size=f"{wide:g}, {tall:g}, {deep:g}", middle=f"{tall / 2:g}"))
    for name, about in layout["models"].items():
        if "prop" in about:
            prop_scene(room, name, about, layout["models"])
    for path, text in imports.items():
        if (folder / path.with_suffix("")).exists():
            (folder / path).write_text(text)
    stored.store(folder)
    for path, text in imports.items():
        if path.name.endswith(".webp.import") and (folder / path.with_suffix("")).exists():
            (folder / path).write_text(text)
    past = stored.over_budget(stored.cost(folder))
    if past:
        raise SystemExit(f"{room}'s models are over the room budget (stored.BUDGET): {'; '.join(past)}")
    (REPO / f"data/kit/{room}.json").write_text(json.dumps(layout, indent="\t") + "\n")
    return len(layout["models"]), len(first)


# A kind's own scene (the prop catalogue's, the asset gate's): its first model, and a box round it that collides, as
# every prop's scene has (HubKit draws the room from the models alone; the shell keeps the room's collision).
KIND_SCENE = """[gd_scene format=3]

[ext_resource type="PackedScene" path="res://game/base/models/{room}_kit/{model}.gltf" id="1_mesh"]

[sub_resource type="BoxShape3D" id="prop_shape"]
size = Vector3({size})

[node name="{node}" type="StaticBody3D"]

[node name="Mesh" parent="." instance=ExtResource("1_mesh")]

[node name="Collision" type="CollisionShape3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, {middle}, 0)
shape = SubResource("prop_shape")
"""


def stamped(source, target):
    """A model's .gltf copied with its .bin's hash written into it (asset.extras.bin_md5): Godot re-imports a glTF only
    when its own text changes, so a model whose new .bin came with the same .gltf kept its old mesh in the game, its old
    UVs over the new pictures (2026-10-06: a hatch leaf showed a status screen's content)."""
    import hashlib
    found = json.loads(source.read_text())
    binary = source.with_suffix(".bin")
    found.setdefault("asset", {}).setdefault("extras", {})["bin_md5"] = hashlib.md5(binary.read_bytes()).hexdigest()
    target.write_text(json.dumps(found, indent=1))


def prop_scene(room, name, about, models):
    """A furniture model's prop scene (game/base/models/<prop>/<prop>.tscn): the model, its children standing where
    the composite places them (each its own model, round six), the glowing parts of both under `Glow`, and a box round
    it that collides."""
    prop = about["prop"]
    scene = REPO / f"game/base/models/{prop}"
    if scene.exists():
        for old in scene.iterdir():
            old.unlink()
    scene.mkdir(exist_ok=True)
    wide, tall, deep = about["size"]
    text = KIND_SCENE.format(room=room, model=name, node=node_name(prop), size=f"{wide:g}, {tall:g}, {deep:g}",
                             middle=f"{tall / 2:g}")
    resources, nodes, glows = [], [], []
    if f"{name}_glow" in models:
        glows.append((f"{name}_glow", IDENTITY))
    for index, child in enumerate(about.get("children", [])):
        placed = child_transform(child)
        resources.append((child["model"], f"c{index}"))
        nodes.append(f'\n[node name="{node_name(child["model"])}_{index}" parent="." groups=["child_object"] '
                     f'instance=ExtResource("c{index}")]\ntransform = {placed}\n')
        if f"{child['model']}_glow" in models:
            glows.append((f"{child['model']}_glow", placed))
    if glows:
        nodes.append('\n[node name="Glow" type="Node3D" parent="."]\n')
        for index, (glow, placed) in enumerate(glows):
            resources.append((glow, f"g{index}"))
            nodes.append(f'\n[node name="{node_name(glow)}_{index}" parent="Glow" instance=ExtResource("g{index}")]\n'
                         f'transform = {placed}\n')
    lines = "".join(f'[ext_resource type="PackedScene" path="res://game/base/models/{room}_kit/{model}.gltf" '
                    f'id="{ident}"]\n' for model, ident in resources)
    text = text.replace('id="1_mesh"]\n', 'id="1_mesh"]\n' + lines, 1) + "".join(nodes)
    (scene / f"{prop}.tscn").write_text(text)


IDENTITY = "Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0)"


def child_transform(child):
    """A child's place on its parent as a scene's Transform3D: turned `turn` degrees about up, its foot at `at` (the
    parent's kit frame). Godot writes a basis row by row."""
    angle = np.radians(child.get("turn", 0.0))
    cos, sin = np.cos(angle), np.sin(angle)
    x, y, z = child["at"]
    numbers = (cos, 0.0, sin, 0.0, 1.0, 0.0, -sin, 0.0, cos, x, y, z)
    return "Transform3D(" + ", ".join(f"{value:.6g}" for value in numbers) + ")"


def node_name(kind):
    return "".join(part.capitalize() for part in kind.split("_"))


def picture_imports(folder):
    """After Godot first imports the shared pictures: their .import files set to BC7, high quality (normal maps
    keep their normal-map setting)."""
    changed = 0
    for found in sorted(pathlib.Path(folder).glob("textures/*.png.import")) + \
            sorted(pathlib.Path(folder).glob("textures/*.webp.import")):
        text = found.read_text()
        for key, value in IMPORT_SETTINGS.items():
            text = re.sub(rf"^{re.escape(key)}=.*$", f"{key}={value}", text, flags=re.MULTILINE)
        if "_normal" in found.name:
            text = re.sub(r"^compress/normal_map=.*$", "compress/normal_map=1", text, flags=re.MULTILINE)
        found.write_text(text)
        changed += 1
    return changed


def record_fittings(reports, path=sorter.FITTINGS):
    """Method B's check, written back: for every room fitting a code build made, how much of each named part the room
    can see (make_kit's parts_seen; the least over the kind's models), into data/library/fittings.json's `built`."""
    data = json.loads(pathlib.Path(path).read_text())
    built = {}
    for report in reports:
        for name, piece in report.get("pieces", {}).items():
            kind = name.rsplit("_", 1)[0]
            if kind not in data["fittings"] or not piece.get("parts_seen"):
                continue
            found = built.setdefault(kind, {"seen": dict(piece["parts_seen"]), "prints_off": []})
            for part, share in piece["parts_seen"].items():
                found["seen"][part] = min(found["seen"].get(part, share), share)
            found["prints_off"] += [f"{name}: {off}" for off in piece.get("prints_off", [])]
    for kind, seen in built.items():
        data["fittings"][kind]["built"] = seen["seen"]
        data["fittings"][kind]["prints_off"] = seen["prints_off"]
    pathlib.Path(path).write_text(json.dumps(data, indent="\t") + "\n")
    return {kind: sorter.missing_parts(data["fittings"][kind]) for kind in built}


def precheck(work):
    """The model check (gates/model.py: thinnest wall, proportions) on every code model of a plan, built here as
    geometry alone (inside/build_only.py, headless Blender, no bake), before anything is paid for (modules round,
    2026-10-07: five builds failed on walls under 3 mm only after their bake, a band laid 2 mm proud of what it wraps
    or a stripe sunk into its plate). {model: its thinnest wall} for each under the limit."""
    import subprocess
    import tempfile

    import trimesh
    import model as model_check
    with tempfile.TemporaryDirectory() as folder:
        subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=16G", "python3",
                        str(REPO / "tools/blender/session.py"), "batch", str(HERE / "inside/build_only.py"), "--",
                        str(REPO), str(work / "plan.json"), folder], check=True, capture_output=True)
        planned = json.loads((work / "plan.json").read_text())["models"]
        failed = {}
        for path in sorted(pathlib.Path(folder).glob("*.glb")):
            mesh = trimesh.load(path, force="mesh")
            # Judged at its own built size: the layout lays a code model at its own box (a bracket's clamp past its
            # plate), so only the walls are in question here, never its proportions.
            thinnest = model_check.thinnest(mesh, mesh.extents)
            if thinnest < model_check.THINNEST_LIMIT:
                failed[path.stem] = round(thinnest, 4)
    return failed


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    step = sys.argv[1]
    if step == "plan":
        layout = json.loads(pathlib.Path(sys.argv[2]).read_text())
        work = pathlib.Path(sys.argv[3])
        work.mkdir(parents=True, exist_ok=True)
        takes = labelled_takes(sys.argv[4:])
        inventory = json.loads((REPO / f"data/inventory/{layout.get('room', 'hub')}.json").read_text())
        planned = plan(layout, takes, inventory)
        (work / "plan.json").write_text(json.dumps(planned, indent=1))
        # A room's place (its wear and library surfaces, data/definitions/place.json) is its own name unless the layout
        # names another (the prologue's rooms: `flat` in the place `prologue_flat`).
        for name, job in jobs(planned, takes, work, layout.get("place", layout.get("room", "hub"))).items():
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
    elif step == "fittings":
        reports = [json.loads(path.read_text()) for path in sorted((pathlib.Path(sys.argv[2]) / "made").glob("report*.json"))]
        for kind, missing in sorted(record_fittings(reports).items()):
            print(kind, "code" if not missing else f"pipeline: missing {', '.join(missing)}")
    elif step == "precheck":
        failed = precheck(pathlib.Path(sys.argv[2]))
        print("code models failing the model check before the bake:", failed or "none")
        if failed:
            raise SystemExit(1)
    elif step == "imports":
        print(picture_imports(sys.argv[2]), "picture imports set to BC7")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
