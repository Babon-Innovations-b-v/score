"""The dress's bake (dress.py): a dressed body's library surfaces baked onto the body itself, as the finish route
bakes a model. Every triangle of the body's meshes is sent with the library surface its material names
(`extras.library`) to one job on the bake's rented card (surfaces/place_line.CLASSES, through blender_cloud.py:
inside/bake_body.py, tools/props/library/inside/bake.py `Atlas.bake_self` with the people palette's wear and dirt at
the route's near density, surfaces/bake_job.job_head), never on this PC. The maps come back as one picture set; here
each vertex list is split where its corners' bake coordinates part (every attribute and morph target carried over,
in the accessors it had), the maps go into the file as its pictures (the build's own picture, the face print, is
replaced, never kept) and every material of the body reads them, its factors 1. Then the bake is checked as the
surface stage checks a bake (surfaces/bake_check.py): each surface's baked base colour on its library surface worn
and dirtied as the people place wears and dirties it, near its colour in the close-up (the take's labels.json, each
finish under the name its settings bake as), no near-black blotch, not one grey look, no lightness order reversed.
"""
import json
import pathlib
import subprocess
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
for folder in (REPO / "score/stages/surfaces", REPO / "tools/props", REPO / "tools/props/library"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))

import bake_check  # noqa: E402
import glb_file  # noqa: E402
import route_settings  # noqa: E402

PROPS_PYTHON = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
SCRIPT = "score/stages/people/inside/bake_body.py"
# What of the repository the card reads besides the script: the bake (tools/props/library: inside/bake.py,
# recipes.py), ProcFunc and infinigen2's shaders (route_bake.BAKE_REPO's).
SENT = ("tools/props/library", "vendor/procfunc/src", "vendor/infinigen2")
# The card's minutes: one body (about 25,000 triangles) unwrapped and baked at 4096, with Blender's start.
MINUTES = 15
MAPS = ("base_color", "metal_roughness", "normal")
UV_STEPS = 2 ** 20  # bake coordinates this close are one corner


def triangles_of(document, views):
    """Every triangle of the file's meshes: (the vertex lists, each a list of its primitives; points, normals,
    triangles over the lists joined, each triangle's primitive as (mesh, primitive))."""
    lists = {}
    for mesh_number, mesh in enumerate(document["meshes"]):
        for number, primitive in enumerate(mesh["primitives"]):
            key = json.dumps([primitive["attributes"], primitive.get("targets", [])], sort_keys=True)
            lists.setdefault(key, []).append((mesh_number, number))
    points, normals, triangles, owners, offset = [], [], [], [], 0
    for members in lists.values():
        attributes = document["meshes"][members[0][0]]["primitives"][members[0][1]]["attributes"]
        found = glb_file.accessor_array(document, views, attributes["POSITION"]).astype(np.float64)
        points.append(found)
        normals.append(glb_file.accessor_array(document, views, attributes["NORMAL"]).astype(np.float64))
        for owner in members:
            primitive = document["meshes"][owner[0]]["primitives"][owner[1]]
            faces = glb_file.accessor_array(document, views, primitive["indices"]).reshape(-1, 3).astype(np.int64)
            triangles.append(faces + offset)
            owners += [owner] * len(faces)
        offset += len(found)
    return list(lists.values()), np.concatenate(points), np.concatenate(normals), np.concatenate(triangles), owners


def slots_of(document, owners):
    """(the library surfaces in slot order, each triangle's slot) from its primitive's material's `extras.library`;
    a material naming none stops the bake."""
    named = [document["materials"][document["meshes"][mesh]["primitives"][number]["material"]].get("extras", {})
             .get("library") for mesh, number in owners]
    if None in named:
        raise RuntimeError("a material of the body names no library surface: nothing is baked")
    names = sorted(set(named))
    return names, np.array([names.index(name) for name in named])


def baked_on_card(job, mesh, folder):
    """The bake job run once on the bake's card class (blender_cloud.py); its maps and coordinates in `folder`."""
    import place_line
    listing = folder / "job.json"
    listing.write_text(json.dumps(job))
    cloud = folder / "cloud.json"
    cloud.write_text(json.dumps({"script": SCRIPT, "args": [str(listing)], "minutes": MINUTES,
                                 "inputs": [str(listing), str(mesh), *(str(REPO / path) for path in SENT)],
                                 "outputs": [str(folder / "maps")]}))
    done = subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/props/cloud/blender_cloud.py"), str(cloud), "--who",
                           "people-dress", "--classes", place_line.CLASSES], cwd=REPO, capture_output=True, text=True)
    (folder / "bake.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    missing = [name for name in ("uvs.npy", *(f"{role}.png" for role in MAPS)) if not (folder / "maps" / name).exists()]
    if done.returncode or missing:
        raise RuntimeError(f"the body's bake brought back no {', '.join(missing) or 'result'}: {done.stderr[-3000:]}")
    return folder / "maps"


def split_corners(corners, uvs):
    """(the old vertex of each new one, each corner's new vertex): a vertex whose corners lie at more than one bake
    coordinate becomes one vertex a coordinate."""
    keys = np.column_stack([corners, np.round(uvs * UV_STEPS).astype(np.int64)])
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    return corners[first], first, inverse.ravel()


def laid_coordinates(document, views, lists, uvs):
    """Each vertex list split where its corners' bake coordinates part (split_corners), every attribute and morph
    target in its own accessor again, TEXCOORD_0 the bake's, each primitive's triangles over the new vertices."""
    start, seen = 0, set()
    for members in lists:
        primitives = [document["meshes"][mesh]["primitives"][number] for mesh, number in members]
        faces = [glb_file.accessor_array(document, views, primitive["indices"]).reshape(-1, 3) for primitive in
                 primitives]
        count = sum(map(len, faces))
        corners = np.concatenate(faces).ravel().astype(np.int64)
        coordinates = uvs[start:start + count].reshape(-1, 2)
        start += count
        old, first, inverse = split_corners(corners, coordinates)
        held = primitives[0]
        carried = {*held["attributes"].values(), *(index for target in held.get("targets", []) for index in
                                                   target.values())} - {held["attributes"].get("TEXCOORD_0")}
        if carried & seen:
            raise RuntimeError("two vertex lists share an accessor: neither can be split on its own")
        seen |= carried
        for number in carried:
            glb_file.replace_accessor(document, views, number, glb_file.accessor_array(document, views, number)[old])
        coordinate = new_accessor(document, views, coordinates[first].astype(np.float32), "VEC2")
        at = 0
        for primitive, face in zip(primitives, faces):
            primitive["attributes"]["TEXCOORD_0"] = coordinate
            mine = inverse[at * 3:(at + len(face)) * 3]
            primitive["indices"] = new_accessor(document, views, mine.astype(np.uint32), "SCALAR", 34963)
            at += len(face)


def new_accessor(document, views, values, kind, target=None):
    """`values` (float32 or uint32) as an accessor of a buffer view of its own: its number."""
    document["bufferViews"].append({"buffer": 0, "byteLength": values.nbytes, **({"target": target} if target else {})})
    views.append(np.ascontiguousarray(values).tobytes())
    rows = values.reshape(len(values), -1)
    document["accessors"].append({"bufferView": len(views) - 1, "componentType": 5126 if values.dtype == np.float32
                                  else 5125, "count": len(values), "type": kind, "min": rows.min(0).tolist(),
                                  "max": rows.max(0).tolist()})
    return len(document["accessors"]) - 1


def laid_maps(document, views, maps):
    """The baked pictures as the file's only pictures, every material reading them with its factors 1 (the maps
    carry the library's colour, roughness and metal)."""
    # the build's own pictures (a face print) are replaced in their buffer views, never kept
    free = [image["bufferView"] for image in document.get("images", [])]
    if len(free) > len(MAPS):
        raise RuntimeError(f"the body carries {len(free)} pictures of its own, more than the bake's {len(MAPS)} maps")
    document["images"], document["textures"] = [], []
    document["samplers"] = [{"magFilter": 9729, "minFilter": 9987}]
    for role in MAPS:
        if not free:
            document["bufferViews"].append({"buffer": 0, "byteLength": 0})
            views.append(b"")
        view = free.pop(0) if free else len(views) - 1
        document["bufferViews"][view].pop("target", None)
        views[view] = (maps / f"{role}.png").read_bytes()
        document["images"].append({"bufferView": view, "mimeType": "image/png", "name": role})
        document["textures"].append({"source": len(document["images"]) - 1, "sampler": 0})
    for material in document["materials"]:
        material["pbrMetallicRoughness"] = {"baseColorFactor": [1.0, 1.0, 1.0, 1.0], "metallicFactor": 1.0,
                                            "roughnessFactor": 1.0, "baseColorTexture": {"index": 0},
                                            "metallicRoughnessTexture": {"index": 1}}
        material["normalTexture"] = {"index": 2}


def close_up(labelled):
    """Each surface's colour in the close-up (L*a*b*), as bake_check.close_up_colours measures it, under the name
    the surface bakes as (a finish with the list's settings as route_settings.settings_name names it)."""
    measured = {}
    for finish in json.loads((labelled / "labels.json").read_text()).get("finishes", []):
        if finish.get("measured_lab") is not None and not finish.get("cover"):
            name = route_settings.settings_name(finish["surface"], finish["settings"]) if finish.get("settings") \
                else finish["surface"]
            measured.setdefault(name, []).append(finish["measured_lab"])
    return {name: [round(float(np.mean([colour[axis] for colour in colours])), 1) for axis in range(3)]
            for name, colours in measured.items()}


def checked(points, triangles, slots, names, uvs, base_colour, specs, close, wear_dirt):
    """The bake measured as bake_check.check_model measures a baked model, each triangle's surface its own slot:
    {"surfaces": {surface: share, baked and library L*a*b*, dE worn and dirtied, near-black share, family},
    "close_up", "faults" (bake_check.surface_faults)}."""
    import baked_gltf
    import labels
    wear, dirt = wear_dirt
    corners = np.arange(len(triangles) * 3).reshape(-1, 3)
    colours = baked_gltf.base_colours({"uvs": uvs.reshape(-1, 2), "triangles": corners,
                                       "maps": np.zeros(len(triangles), dtype=np.int64)}, [{"base_color": base_colour}])[0]
    colour = labels.lab(colours)
    laid = points[triangles]
    areas = 0.5 * np.linalg.norm(np.cross(laid[:, 1] - laid[:, 0], laid[:, 2] - laid[:, 0]), axis=1)
    shades = [bake_check.library_shades(specs[name]) for name in names]
    reach = np.zeros((len(triangles), len(names)), dtype=bool)
    reach[np.arange(len(triangles)), slots] = True
    record = {"surfaces": {}, "close_up": close}
    for index, name in enumerate(names):
        chosen = slots == index
        spec = specs[name]
        middle = bake_check.area_median(colour[chosen], areas[chosen])
        dirty = labels.lab(labels.srgb(np.array(spec["dirt_colour"]))[None])[0] if "dirt_colour" in spec else None
        bare = labels.lab(labels.srgb(np.array(spec["bare"]))[None])[0] if "bare" in spec else None
        record["surfaces"][name] = {
            "share": round(float(areas[chosen].sum() / areas.sum()), 4),
            "baked_lab": [round(float(value), 1) for value in middle],
            "surface_lab": [round(float(value), 1) for value in shades[index][0]],
            "delta_e": round(bake_check.on_surface(middle, shades[index][0], dirty, dirt, bare,
                                                   spec.get("wear", wear)), 1),
            "near_black": round(bake_check.blotch_share(colour, areas, chosen, reach, shades), 4),
            "family": spec.get("family")}
    record["faults"] = bake_check.surface_faults("body", record)
    return record


def bake(glb, specs, head, labelled, folder):
    """The dressed body at `glb` baked with its library surfaces and written again with its maps; the bake's check
    (checked) and what the card made (side, slots). `head`: bake_job.job_head's (density, wear, dirt, seed)."""
    document, views = glb_file.read(glb)
    lists, points, normals, triangles, owners = triangles_of(document, views)
    names, slots = slots_of(document, owners)
    folder.mkdir(parents=True, exist_ok=True)
    mesh = folder / "body.npz"
    np.savez(mesh, points=points, normals=normals, triangles=triangles, slots=slots)
    maps = baked_on_card({"repo": str(REPO), "mesh": str(mesh), "slots": names, "out": str(folder / "maps"),
                          "specs": {name: specs[name] for name in names},
                          **{key: head[key] for key in ("density", "wear", "dirt", "seed")}}, mesh, folder)
    uvs = np.load(maps / "uvs.npy")
    laid_coordinates(document, views, lists, uvs)
    laid_maps(document, views, maps)
    glb_file.write(document, views, glb)
    return checked(points, triangles, slots, names, uvs, maps / "base_color.png", specs, close_up(labelled),
                   (head["wear"], head["dirt"]))
