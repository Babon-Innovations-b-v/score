"""A place's scene package: what any engine loads, written from a finished route run (JoeyKardolus/2099#129). Every
object is its own glTF model as baked (objects/<name>.gltf, its .bin and its pictures), and scene.json says where
each copy of an object stands in the place's frame. No engine's format is in it: the game 2099 reads it through its
Unity reader (Farm.Places), Blender or a benchmark through theirs. This docstring is the format for both writers, this
file's and score/stages/place_build/scene_package.py's (`package`, from a laid place's USD).

    .venv/bin/python tools/props/library/package.py <place> <work> <out>        # write the package, then check it
    .venv/bin/python tools/props/library/package.py --check <out>               # check a package that is there

An outdoor place's run is place_route.py's (plan-route.json: each copy a spot, a facing, a tilt and an even scale). A
kit room's package (route.py's run, `--kit`) went with the old kits on 2026-10-21; `kit_matrix` stands a kit piece's
model as the game's HubKit stood it (its box fitted to the laid size on the middle of its foot, in the piece's own
frame), which the export and the settle read.

scene.json (a field marked [place_build] is written only by scene_package.py):
    format, version      "score.scene", 1
    place, frame         the place and its frame in words (from its inventory): metres, y up
    units, up            "metre", "+y"
    ground               how a copy's height is meant: a lift off the ground under its spot, so an engine with terrain
                         stands each copy on its own ground (a flat place frame has its ground at y = 0)
    on_seat              where the place's middle sits on its seat, (across, along)
    objects              {name: {file, kind, route, size (x, y, z as laid, metres), triangles, check {pass, ...}}};
                         [place_build] a character's (kind "character", route "skinned from the laid USD") glTF is
                         skinned (score/stages/place_build/skinned.py: skin 0, its joints under node 1, morph targets
                         named in each mesh's extras.targetNames), its `clips` {animation: seconds} each a glTF
                         animation, and its check's `skinned_error` (metres from UsdSkel's own skin)
    instances            [{object, row, at, facing, tilt, scale, matrix}]: `facing` a bearing in degrees (0 looks
                         along -z, 90 along +x), `tilt` degrees about the copy's own across, `matrix` the whole
                         transform as 16 numbers, column by column, as glTF writes a node's matrix; a kit piece also
                         `stretch` [x, y, z]; [place_build] instead of `row`, `name` and `kind`, and when the physics
                         check ran `role` and `collider` {shape ("convex hull" or "mesh"), dynamic, mass_kg (a dynamic
                         one's, or null)}; a door's copy `door` {leaf (the node that moves: the copy itself, the whole
                         piece), frame (the still part, or null), move ("hinge"), axis and pivot (the hinge line, place
                         frame), limits [low, high] and open (degrees, right-handed about the axis), opens (its
                         score:opens mark: the walkers swing it open), opening {in (the shell or connector it is set
                         in, or null), end_wall (a tunnel's end wall's doorway), middle, size [across, up], through (a
                         unit way)}, between [the enclosure past its face along `through`, the one against it] (null:
                         outside), and in a chamber lock, side ("inner" or "outer") and leads (where it opens to)};
                         a character's copy `plays` {animation, starts (the place's second its first key falls at: a
                         crowd copy's phase starts before 0), loops (a clip that runs round)} or null (its rest pose)
    chambers             [place_build] [{name, inner [doors], outer [doors], air_volume (m³: the convex hull of the
                         enclosure over its deck's top)}]: an airlock, a shell or connector that a door from another
                         enclosure and a door from outside open into
    children             [{object, on}]: an object standing on another object, laid by its parent
    lamps                [{name, kind, intensity, colour [r, g, b]}]: kind "point" with `at` [x, y, z], `watts` and
                         `radius` (metres), or "sun" with `shines`, a unit way [x, y, z]; [place_build] each with its
                         `strength` in Blender's units as the final render lights with it (watts, a sun's W/m²)
    counts               {kind: copies}: a kit room's layout or [place_build] the laid place's own, checked against
                         its instances
    physics              [place_build] the physics check's file ("ready.json"), or null when it has not run
    left_out             [place_build] [{name, why}]: each prim not converted (an animated effect, a prim that draws
                         no face, the sky's dome, a character that cannot be carried as drawn, saying why)
    environment          [place_build] the sky and light as the final render draws them: `sky` {file (under the
                         package), projection, turn (degrees about up), strength, library} or null, `ambient` [r, g, b]
                         (linear), `background` [r, g, b] or null, `exposure` (a multiplier), `view_transform` and
                         `look` (the grade the engine's tone mapping takes), `sun` {name, elevation, heading (degrees
                         round from +x towards +z), strength (Blender's W/m²), colour, angle} or null, `night` {moon
                         (as the sun), glow {threshold, intensity} or null} or null, `ground_albedo` [r, g, b] (linear: the laid ground's
                         baked tile's mean base colour, the light it throws back up) or null, `grade` {file (a
                         16-bit PNG under the package), size, low, high, middle, display, layout}: the view transform
                         and look as Blender draws them, each scene linear channel at middle * 2 ** (low + c * (high -
                         low)) for c from 0 to 1 in its lattice
    textures             [place_build] the caps its pictures were written under: {use ("game", or "film" for an
                         Unreal film render, `package --film`), held_texels (the longest side a picture is written
                         at), largest (the longest side of a baked map)}
    draft                [place_build] present only on a preview that never ships (`package --draft`): {baked: false,
                         why}; its palette recipes are their plain colour, metal and roughness, never baked, and
                         score-lib take-in refuses a place whose package carries it
An object's .gltf may use KHR_materials_transmission, _ior and _emissive_strength (listed in its extensionsUsed) and
carry its baked pictures in its own buffer; a version 1 reader that skips them still loads every object.

Version 2, the piece list (score/stages/place_build/pieces.py, `package --pieces`; 2099 #245), written beside a
version 1 package from the laid USD with no Blender and no bake. Every block above that is not geometry is as in
version 1 (place, frame, units, up, ground, on_seat, lamps, counts, physics, left_out, chambers, environment, and
per copy role, collider, door, plays), except `environment.sky.file`, the sky's picture as its library reference
(`kind/id@version/file`), and `environment.grade` and `ground_albedo`, null (Blender draws them). Instead of objects
and instances:
    pieces               {name: a library piece {library (its entry's address), digest (the entry's content digest,
                         as the library's index has it), parts, size, triangles, and where an engine reads its
                         geometry: gltf (a file of the entry: its web3d/full.glb, else the glTF its laid USD was
                         converted from), or for an entry with no glTF mesh (meshes/<name>.glb under the package: its
                         geometry as laid, a made piece's GLB) and sha256}, or a made piece {made (made/<name>.glb
                         under the package), sha256 (its bytes'), from (the algorithm or entry it was made by, or null),
                         parts, size, triangles; a character's also skinned true, clips and check}}: `parts` the
                         piece's part names (a GeomSubset's name, a laid layer's, else its mesh's), `size` its box
                         sides in its own frame. A made piece's GLB holds one mesh a part, named by it: positions and
                         normals, no material and no texture coordinates (an engine tiles its look in the piece's own
                         frame); a character's is version 1's skinned glTF in its own texture, its pictures apart, each once at
                         made/pictures/<sha256>.<ending> (images[].uri)
    looks                {id: a palette recipe's {library (its surface's address), spec (its score:recipe:spec word
                         for word: recipe, token, colour, second, bare, dirt_colour, wear, dirt, seed, roughness...)},
                         or another library surface's {library, colour, roughness, metal, opacity, glow, maps {input:
                         {file (a library reference), read, scale}}, tile_metres}, or {own: piece} (the piece's own
                         texture)}
    copies               [{piece, name, kind, matrix (the whole transform, glTF's column order: a stretch kept in it),
                         looks {part: look id; EVERY_PART for every part}}], with version 1's per-copy blocks

The version 2 check refuses a piece list with a library piece the library does not hold, has withdrawn or holds at
another digest, names a gltf its entry does not hold, or whose mesh is missing, hashes otherwise or does not hold its
parts as named meshes, a made piece whose file is missing, hashes otherwise or does not hold its parts as named meshes, a
piece no copy uses, a copy of no piece, a matrix that is no transform, a part of a copy's piece with no look, a look
id the list does not hold, an own look of no piece, or a count of copies that differs from `counts`.

The check refuses a package with a missing or unreadable model file, buffer or picture, a model that failed its model
check, an object no copy uses, a transform that is not a turn and an even scale (a kit room's: a turn and its
`stretch`, no part of it past STRETCH_LIMIT), or a count of copies that differs from the record's: an inventory row's
for an outdoor place, a kind's in the layout (`counts`) for a kit room.
"""
import argparse
import json
import math
import pathlib
import shutil

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
INVENTORIES = REPO / "data/inventory"
FORMAT = "score.scene"
VERSION = 1
PIECES = 2  # the piece list's version (above)
EVERY_PART = "*"  # a copy's look on every part of its piece
# How far a kit room's copy may stretch its model on any side before the package is refused: a model is made at the
# size it is laid at, so a stretch past this is a layout that no longer matches its bake.
STRETCH_LIMIT = 0.05
GROUND = ("each copy's y is its lift off the ground under its own spot; on a flat place frame the ground is y = 0, "
          "an engine with terrain stands each copy on the ground there")


def turned(facing, tilt, scale):
    """A copy's 3 x 3: turned about up by -facing (a bearing), tipped about its own across by tilt, scaled evenly."""
    yaw, tip = math.radians(-facing), math.radians(tilt)
    about_up = np.array([[math.cos(yaw), 0.0, math.sin(yaw)], [0.0, 1.0, 0.0], [-math.sin(yaw), 0.0, math.cos(yaw)]])
    about_across = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(tip), -math.sin(tip)], [0.0, math.sin(tip), math.cos(tip)]])
    return about_up @ about_across * scale


def standing_at(entry, spot):
    """Where a copy's origin stands: its spot; a piece laid front up (tilted: a cable, a plate on the ground) is lifted
    by half its depth and moved back by half its tall side, which the tilt lays along the ground, so its middle lands
    on its spot."""
    at = np.array([float(spot["x"]), float(spot.get("y", 0.0)), float(spot["z"])])
    if entry.get("tilt"):
        _, tall, deep = entry["size"]
        facing = math.radians(float(spot.get("facing", 0.0)))
        along = np.array([-math.sin(facing), 0.0, math.cos(facing)])  # the copy's own +z, turned
        at = at - along * tall / 2 + np.array([0.0, deep / 2, 0.0])
    return at


def instance(planned, piece):
    """One copy as scene.json has it."""
    entry = planned["models"][piece["model"]]
    spot = piece["spot"]
    facing, tilt, scale = float(spot.get("facing", 0.0)), float(entry.get("tilt", 0.0)), float(spot.get("scale", 1.0))
    matrix = np.eye(4)
    matrix[:3, :3] = turned(facing, tilt, scale)
    if "rotation" in spot:  # a settled piece's turn on its own seat, a quaternion [x, y, z, w] (tools/usd/settle.py)
        from scipy.spatial.transform import Rotation
        matrix[:3, :3] = Rotation.from_quat(spot["rotation"]).as_matrix() * scale
    matrix[:3, 3] = standing_at(entry, spot)
    return {"object": piece["model"], "row": piece["row"], "at": [round(float(value), 4) for value in matrix[:3, 3]],
            "facing": facing, "tilt": tilt, "scale": scale,
            "matrix": [round(float(value), 6) + 0.0 for value in matrix.T.reshape(-1)]}


def made_reports(work):
    """What the bake said of each model it made (triangles, bounds), by model: only the reports of the work folder's
    current jobs (`job-*.json` names each one's report), when it has any. A report an earlier plan's job left in
    made/ names models by the same names at their old sizes, and read with the rest it overrode the newer bounds (the
    camp's foot rings, laid 7% narrower than their models, 2026-10-09)."""
    jobs = sorted(pathlib.Path(work).glob("job-*.json"))
    current = {json.loads(path.read_text()).get("report") for path in jobs}
    found = {}
    for path in sorted((pathlib.Path(work) / "made").glob("report*.json")):
        if jobs and path.name not in current:
            continue
        data = json.loads(path.read_text())
        found.update(data.get("pieces", data))
    return found


def model_files(gltf):
    """Every file a .gltf names (its buffers and pictures), relative to its folder."""
    found = json.loads(gltf.read_text())
    return [item["uri"] for item in found.get("buffers", []) + found.get("images", []) if "uri" in item]


def copy_object(source, target, name):
    """A made model and everything it names, into the package's objects folder."""
    gltf = source / f"{name}.gltf"
    shutil.copy(gltf, target / gltf.name)
    for uri in model_files(gltf):
        (target / uri).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source / uri, target / uri)


def passed_checks(work, planned):
    """The model gate's verdict for every planned model; refuses a package while any failed or is unchecked."""
    checks = json.loads((work / "checks.json").read_text())
    held = sorted(name for name in planned["models"] if not checks.get(name, {}).get("pass"))
    if held:
        raise SystemExit(f"models that failed or missed their check: {', '.join(held)}")
    return checks


def write(place, work, out):
    """The package of a finished route run in <work>, into <out>; returns scene.json's content."""
    planned = json.loads((work / "plan-route.json").read_text())
    checks = passed_checks(work, planned)
    reports = made_reports(work)
    children = {child["model"] for child in planned["children"]}
    if out.exists():
        shutil.rmtree(out)
    (out / "objects").mkdir(parents=True)
    objects = {}
    for name, entry in planned["models"].items():
        copy_object(work / "made", out / "objects", name)
        objects[name] = {"file": f"objects/{name}.gltf", "kind": entry["kind"], "route": entry["route"],
                         "size": entry["size"], "triangles": reports.get(name, {}).get("triangles"),
                         "check": checks[name]}
    scene = {"format": FORMAT, "version": VERSION, "place": place, "frame": planned.get("frame", ""),
             "units": "metre", "up": "+y", "ground": GROUND, "on_seat": planned["on_seat"], "objects": objects,
             "instances": [instance(planned, piece) for piece in planned["pieces"] if piece["model"] not in children],
             "children": [{"object": child["model"], "on": child["parent"]} for child in planned["children"]],
             "lamps": json.loads((work / "lamps.json").read_text()) if (work / "lamps.json").exists() else []}
    (out / "scene.json").write_text(json.dumps(scene, indent=1) + "\n")
    return scene


# --- a kit piece's stand -----------------------------------------------------------------------------------------

def model_box(gltf):
    """A made model's box in its own file (low, high corners), from its one primitive's position bounds."""
    document = json.loads(gltf.read_text())
    lows, highs = [], []
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            accessor = document["accessors"][primitive["attributes"]["POSITION"]]
            lows.append(accessor["min"])
            highs.append(accessor["max"])
    return np.min(lows, axis=0), np.max(highs, axis=0)


def kit_matrix(laid, low, high):
    """A kit piece's transform as HubKit stands it: its model's box fitted to the laid size on the middle of its foot,
    in the piece's frame at its origin; the transform and the stretch on each side."""
    axes = np.column_stack([np.asarray(laid[axis], dtype=np.float64) for axis in ("x", "y", "z")])
    stretch = np.asarray(laid["size"], dtype=np.float64) / np.maximum(high - low, 1e-9)
    foot = np.array([(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2])
    matrix = np.eye(4)
    matrix[:3, :3] = axes * stretch
    matrix[:3, 3] = np.asarray(laid["at"], dtype=np.float64) - matrix[:3, :3] @ foot
    return matrix, stretch


def object_problems(out, name, about):
    """What is wrong with one object of a package: its files, its mesh, its check."""
    import trimesh
    gltf = out / about["file"]
    if not gltf.is_file():
        return [f"{name}: no model at {about['file']}"]
    found = [f"{name}: {uri} is missing" for uri in model_files(gltf) if not (gltf.parent / uri).is_file()]
    if found:
        return found
    mesh = trimesh.load(gltf, force="mesh", skip_materials=True)
    if len(mesh.faces) == 0:
        found.append(f"{name}: its model has no faces")
    if not about.get("check", {}).get("pass"):
        found.append(f"{name}: failed its model check")
    return found


def transform_problems(index, copy):
    """What is wrong with one copy's transform: not finite, or not a turn with an even scale (a kit piece's: a turn
    with its stretch, none past STRETCH_LIMIT)."""
    matrix = np.array(copy["matrix"], dtype=float).reshape(4, 4).T
    if not np.all(np.isfinite(matrix)) or not np.allclose(matrix[3], [0.0, 0.0, 0.0, 1.0]):
        return [f"copy {index} ({copy['object']}): its matrix is not a transform"]
    if "stretch" in copy:
        stretch = np.linalg.norm(matrix[:3, :3], axis=0)
        if np.any(np.abs(stretch - 1.0) > STRETCH_LIMIT):
            return [f"copy {index} ({copy['object']}): stretched {stretch.round(3).tolist()} past its model"]
        basis = matrix[:3, :3] / stretch
        square = 1e-3  # a kit layout writes its axes to five places: a tapered plate's frame is square to that
    else:
        basis = matrix[:3, :3] / copy["scale"]
        square = 1e-5
    if not np.allclose(basis.T @ basis, np.eye(3), atol=square) or np.linalg.det(basis) < 0:
        return [f"copy {index} ({copy['object']}): its matrix is not a turn with an even scale"]
    return []


def count_problems(scene, inventory):
    """Every inventory row's count of copies against the package's (a child row stands in its parent's); a kit room's
    every kind's count in its layout against the package's whole pieces (a glowing part is not a piece)."""
    if "counts" in scene:
        laid = {}
        for copy in scene["instances"]:
            if "part" not in copy:
                laid[copy["kind"]] = laid.get(copy["kind"], 0) + 1
        return [f"kind {kind}: the layout has {count} pieces, the package {laid.get(kind, 0)}"
                for kind, count in sorted(scene["counts"].items()) if laid.get(kind, 0) != count]
    copies = {}
    for copy in scene["instances"]:
        copies[copy["row"]] = copies.get(copy["row"], 0) + 1
    standing_on = {child["object"] for child in scene["children"]}
    return [f"row {row['id']}: the inventory has {row['count']} copies, the package {copies.get(row['id'], 0)}"
            for row in inventory["rows"] if row["id"] not in standing_on and copies.get(row["id"], 0) != row["count"]]


def held_entries(addresses):
    """{address: {digest, state}} of each entry address as the library's own index holds it (score/library, the one
    reader of the library's files; SCORE_LIB_ROOT or the checkout beside score's)."""
    import sys
    for path in (REPO, REPO / "tools/library"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    import library_files
    from score import library
    root = library.root_from_environment() or library_files.default_root()
    indexed = {}
    for kind in sorted({address.split("/", 1)[0] for address in addresses}):
        indexed.update({row["address"]: {"digest": row["digest"], "state": row["state"]}
                        for row in library.index(root, kind)["entries"]})
    return {address: {**indexed[address], "files": entry_files(library, root, address)} for address in addresses
            if address in indexed}


def entry_files(library, root, address):
    """The file names of the entry at `address` (score/library's record), [] when its record is not there."""
    kind, rest = address.split("/", 1)
    entry_id, version = rest.rsplit("@", 1)
    try:
        return sorted(library.entry(root, kind, entry_id, int(version))["files"])
    except (OSError, ValueError):
        return []


def piece_problems(out, name, piece, held):
    """What is wrong with one piece of a piece list: a library piece the library (`held`) lacks, withdrew or holds at
    another digest; a made piece missing, hashing otherwise or without its parts as named meshes."""
    import hashlib
    if "library" in piece:
        entry = held.get(piece["library"])
        if entry is None:
            return [f"piece {name}: the library holds no {piece['library']}"]
        if entry["state"] == "withdrawn":
            return [f"piece {name}: {piece['library']} is withdrawn"]
        if entry["digest"] != piece.get("digest"):
            return [f"piece {name}: its digest is not {piece['library']}'s ({entry['digest'][:12]})"]
        if "gltf" in piece:
            return [] if piece["gltf"] in entry.get("files", ()) else [
                f"piece {name}: {piece['library']} holds no {piece['gltf']}"]
        if "mesh" not in piece:
            return [f"piece {name}: no gltf of its entry and no mesh"]
    held_file = piece["made"] if "made" in piece else piece["mesh"]
    path = out / held_file
    if not path.is_file():
        return [f"piece {name}: no made file at {held_file}"]
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != piece["sha256"]:
        return [f"piece {name}: {held_file} does not hash to its sha256"]
    if piece.get("skinned"):
        document = json.loads(data[20:20 + int.from_bytes(data[12:16], "little")])
        return [f"piece {name}: no picture at {image['uri']} beside {held_file}" for image in document.get("images", [])
                if "uri" in image and not (path.parent / image["uri"]).is_file()]
    length = int.from_bytes(data[12:16], "little")
    meshes = {mesh.get("name") for mesh in json.loads(data[20:20 + length])["meshes"]}
    return [f"piece {name}: its part {part} is no mesh of {held_file}" for part in piece["parts"]
            if part not in meshes]


def copy_problems(index, copy, scene):
    """What is wrong with one copy of a piece list: no piece, a matrix that is no transform, a part with no look, a
    look the list lacks."""
    piece = scene["pieces"].get(copy["piece"])
    if piece is None:
        return [f"copy {index} ({copy['name']}): no piece {copy['piece']}"]
    matrix = np.array(copy["matrix"], dtype=float).reshape(4, 4).T
    found = []
    if not np.all(np.isfinite(matrix)) or not np.allclose(matrix[3], [0.0, 0.0, 0.0, 1.0]) \
            or abs(np.linalg.det(matrix[:3, :3])) < 1e-12:
        found.append(f"copy {index} ({copy['name']}): its matrix is not a transform")
    if EVERY_PART not in copy["looks"]:
        found += [f"copy {index} ({copy['name']}): its part {part} has no look" for part in piece["parts"]
                  if part not in copy["looks"]]
    return found + [f"copy {index} ({copy['name']}): no look {look}" for look in copy["looks"].values()
                    if look not in scene["looks"]]


def pieces_problems(out, scene, held=None):
    """Everything wrong with a piece list (version 2) at <out>, its library pieces against the library's index
    (`held`, held_entries by default); [] when it is sound."""
    addresses = sorted({piece["library"] for piece in scene["pieces"].values() if "library" in piece})
    held = held_entries(addresses) if held is None else held
    found = []
    for name, piece in scene["pieces"].items():
        found += piece_problems(out, name, piece, held)
    used = {copy["piece"] for copy in scene["copies"]}
    found += [f"piece {name}: no copy uses it" for name in sorted(set(scene["pieces"]) - used)]
    for index, copy in enumerate(scene["copies"]):
        found += copy_problems(index, copy, scene)
    found += [f"look {key}: own look of no piece {look['own']}" for key, look in scene["looks"].items()
              if "own" in look and look["own"] not in scene["pieces"]]
    laid = {}
    for copy in scene["copies"]:
        laid[copy["kind"]] = laid.get(copy["kind"], 0) + 1
    return found + [f"kind {kind}: counts has {count} copies, the list {laid.get(kind, 0)}"
                    for kind, count in sorted(scene["counts"].items()) if laid.get(kind, 0) != count]


def problems(out, inventory=None, held=None):
    """Everything wrong with the package at <out>, against its place's inventory (a piece list's library pieces
    against the library, `held`: pieces_problems); [] when it is sound."""
    scene = json.loads((out / "scene.json").read_text())
    if scene.get("format") == FORMAT and scene.get("version") == PIECES:
        return pieces_problems(out, scene, held)
    if scene.get("format") != FORMAT or scene.get("version") != VERSION:
        return [f"scene.json is not {FORMAT} version {VERSION}"]
    if inventory is None and "counts" not in scene:
        inventory = json.loads((INVENTORIES / f"{scene['place']}.json").read_text())
    found = []
    for name, about in scene["objects"].items():
        found += object_problems(out, name, about)
    used = {copy["object"] for copy in scene["instances"]} | {child["object"] for child in scene["children"]}
    found += [f"{name}: no copy uses it" for name in sorted(set(scene["objects"]) - used)]
    found += [f"copy {index}: no object {copy['object']}" for index, copy in enumerate(scene["instances"])
              if copy["object"] not in scene["objects"]]
    for index, copy in enumerate(scene["instances"]):
        found += transform_problems(index, copy)
    return found + count_problems(scene, inventory)


def summary(out):
    """One line: objects (a piece list's pieces), copies, triangles placed, size on disk."""
    scene = json.loads((out / "scene.json").read_text())
    if scene.get("version") == PIECES:
        placed = sum(scene["pieces"][copy["piece"]]["triangles"] for copy in scene["copies"]
                     if copy["piece"] in scene["pieces"])
        size = sum(path.stat().st_size for path in out.rglob("*") if path.is_file())
        return (f"{scene['place']}: {len(scene['pieces'])} pieces, {len(scene['copies'])} copies, "
                f"{placed:,} triangles placed, {size / 1e6:.2f} MB")
    placed = sum(scene["objects"][copy["object"]].get("triangles") or 0 for copy in scene["instances"]
                 if copy["object"] in scene["objects"])
    size = sum(path.stat().st_size for path in out.rglob("*") if path.is_file())
    return (f"{scene['place']}: {len(scene['objects'])} objects, {len(scene['instances'])} copies, "
            f"{placed:,} triangles placed, {size / 1e6:.1f} MB")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="+", type=str, help="<place> <work> <out>, or with --check <out>")
    parser.add_argument("--check", action="store_true", help="only check the package at <out>")
    options = parser.parse_args()
    if options.check:
        out = pathlib.Path(options.names[0])
    else:
        place, work, out = options.names[0], pathlib.Path(options.names[1]), pathlib.Path(options.names[2])
        write(place, work, out)
    found = problems(out)
    for line in found:
        print("PROBLEM", line)
    print(summary(out), "| check:", "sound" if not found else f"{len(found)} problems")
    if found:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
