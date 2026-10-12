"""The framework's check of a place's baked models (row surfaces-check@<place>, after place_line.py's paint and bake):
every part's baked base colour lies on its library surface (CIE76 under BAKE_DELTA_E), no near-black blotch, every
map there, triangles within the bake job's budget. A module of its own, so a change to the check moves the check
row's key alone, never the paint's or the paid bake's.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROPS = REPO / "tools/props"
for folder in (HERE, PROPS, PROPS / "library", PROPS / "cloud"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the method modules must not shadow the framework's
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import surface_gates as gates  # noqa: E402
import prop_env  # noqa: E402

# A baked part lies on its surface when its median base colour is within BAKE_DELTA_E (CIE76) of the surface's
# colour: the bake's wear and dirt (0.4 each) move a surface's colour, a wrong surface moves it far more. A part
# whose surface is not dark (L* over DARK_SURFACE) fails with over BLOTCH_SHARE of its area a blotch: a triangle under
# BLOTCH_L (the black blotches of round six) whose colour lies over BLOTCH_DELTA_E from every surface within its
# reach. Inside a part that is its own surface, so every near-black triangle counts; on a border it may bake its
# neighbour's colour and count only when it is off that one too (the seed tray's paper label on black plastic, bake of
# 2026-10-12: its 19 near-black triangles bake the plastic, nine in ten within 3.3 of its colour; black lies 9.5 off
# it). A smudge within BLOTCH_DELTA_E of a dark neighbour's colour cannot be told from that neighbour and passes.
# Parts under PART_LEAST of the model are not judged.
BAKE_DELTA_E = 20.0
DARK_SURFACE, BLOTCH_L, BLOTCH_SHARE, BLOTCH_DELTA_E = 35.0, 12.0, 0.05, 6.0
PART_LEAST = 0.01
PART_POINTS = 60000  # labelled points kept per model to name each baked triangle (export.PART_POINTS)


def data_of(inputs):
    return json.loads(inputs["surfaces"].read_text())


def gltf_model(gltf):
    """A baked .gltf's one primitive (positions, texture coordinates in glTF's own convention, triangles) and its
    maps by role, read as tools/usd/export.py reads them but without OpenUSD (the prop environment has none)."""
    import glb_file
    document = json.loads(gltf.read_text())
    blob = (gltf.parent / document["buffers"][0]["uri"]).read_bytes()
    views = [blob[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]]
             for view in document["bufferViews"]]
    primitive = document["meshes"][0]["primitives"][0]
    geometry = {"positions": glb_file.accessor_array(document, views, primitive["attributes"]["POSITION"]),
                "uvs": glb_file.accessor_array(document, views, primitive["attributes"]["TEXCOORD_0"]),
                "triangles": glb_file.accessor_array(document, views, primitive["indices"]).reshape(-1, 3)}
    material = document["materials"][primitive["material"]]
    references = {"base_color": material["pbrMetallicRoughness"].get("baseColorTexture"),
                  "metal_roughness": material["pbrMetallicRoughness"].get("metallicRoughnessTexture"),
                  "normal": material.get("normalTexture")}
    maps = {role: gltf.parent / document["images"][document["textures"][reference["index"]]["source"]]["uri"]
            for role, reference in references.items() if reference is not None}
    return geometry, maps


def baked_surfaces(geometry, labelled, entry):
    """Each baked triangle's surface and the surfaces within its reach, the labelled parts (one .ply per surface)
    laid into the kit frame as make_chunky lays them (stored_parts.kit_frame): (surface names, each triangle's surface
    index (the part whose nearest point lies under its middle), reach (triangles x surfaces: its own, its corners'
    and every part with a point within its furthest corner from its middle))."""
    import numpy as np
    import trimesh
    from scipy.spatial import cKDTree
    import stored_parts
    paths = sorted(labelled.glob("*.ply"))
    points, codes = [], []
    for code, path in enumerate(paths):
        vertices = np.asarray(trimesh.load(path, process=False).vertices)
        vertices = vertices[::max(1, len(vertices) // PART_POINTS)]
        points.append(vertices)
        codes += [code] * len(vertices)
    laid = stored_parts.kit_frame(np.vstack(points), np.array(entry["base"]).reshape(3, 3), entry["size"])
    tree, codes = cKDTree(laid), np.array(codes)
    corners = geometry["positions"][geometry["triangles"]]
    middles = corners.mean(axis=1)
    surface = codes[tree.query(middles)[1]]
    reach = np.zeros((len(middles), len(paths)), dtype=bool)
    reach[np.arange(len(middles)), surface] = True
    for corner in codes[tree.query(geometry["positions"])[1]][geometry["triangles"]].T:
        reach[np.arange(len(middles)), corner] = True
    radius = np.linalg.norm(corners - middles[:, None], axis=2).max(axis=1)
    for triangle, found in enumerate(tree.query_ball_point(middles, radius)):
        reach[triangle, np.unique(codes[found])] = True
    return [path.stem for path in paths], surface, reach


def blotch_share(colour, areas, chosen, reach, tokens):
    """The share of the chosen triangles' area that is a blotch: under BLOTCH_L and over BLOTCH_DELTA_E (CIE76) from
    the colour of every surface within its reach (`reach`: triangles x surfaces; `tokens`: each surface's L*a*b*, None
    for one not in the library, which explains nothing)."""
    import numpy as np
    far = np.full(len(colour), np.inf)
    for index, token in enumerate(tokens):
        if token is not None:
            near = np.linalg.norm(colour - np.asarray(token), axis=1)
            far = np.where(reach[:, index], np.minimum(far, near), far)
    blotch = chosen & (colour[:, 0] < BLOTCH_L) & (far > BLOTCH_DELTA_E)
    return float(areas[blotch].sum() / max(areas[chosen].sum(), 1e-12))


def check_model(name, entry, labelled, made, materials):
    """One baked model measured: per surface its parts' baked base colour (area-weighted median over its triangles'
    texture at their middles' coordinates; glTF's v runs down the picture) against the surface's colour, its
    blotch share, its maps and its triangles against the job's budget."""
    import numpy as np
    from PIL import Image
    import labels
    geometry, maps = gltf_model(made / f"{name}.gltf")
    record = {"triangles": int(len(geometry["triangles"])), "budget": int(entry["faces"]),
              "maps": sorted(maps), "surfaces": {}}
    record["missing_maps"] = [role for role in ("base_color", "metal_roughness", "normal") if role not in maps]
    if "base_color" in record["missing_maps"]:
        return record
    picture = np.asarray(Image.open(maps["base_color"]).convert("RGB"), dtype=np.float64) / 255
    height, width = picture.shape[:2]
    uv = geometry["uvs"][geometry["triangles"]].mean(axis=1) % 1.0
    columns = np.clip((uv[:, 0] * width).astype(int), 0, width - 1)
    rows = np.clip((uv[:, 1] * height).astype(int), 0, height - 1)
    colour = labels.lab(picture[rows, columns])
    corners = geometry["positions"][geometry["triangles"]]
    areas = 0.5 * np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
    names, surface, reach = baked_surfaces(geometry, labelled, entry)
    tokens = [labels.lab(labels.srgb(np.array(materials[each]["colour"]))[None])[0] if each in materials else None
              for each in names]
    for index in sorted(set(surface.tolist())):
        chosen = surface == index
        order = np.argsort(colour[chosen, 0])
        weights = np.cumsum(areas[chosen][order])
        middle = colour[chosen][order][np.searchsorted(weights, weights[-1] / 2)]
        token = tokens[index]
        record["surfaces"][names[index]] = {
            "share": round(float(areas[chosen].sum() / areas.sum()), 4),
            "baked_lab": [round(float(value), 1) for value in middle],
            "surface_lab": None if token is None else [round(float(value), 1) for value in token],
            "delta_e": None if token is None else round(float(np.linalg.norm(middle - token)), 1),
            "near_black": round(blotch_share(colour, areas, chosen, reach, tokens), 4)}
    return record


def make_check(inputs, out, seed, params):
    prop_env.handover(__file__, "check", inputs, out)


def check_step(inputs, out):
    """The prop environment's side: every baked model measured (checks.json)."""
    import library
    name = data_of(inputs)["library"]
    materials = {**library.by_library(name), **library.resolved(name)}
    found = {model: check_model(model, entry, inputs["paint"] / "labelled" / entry["parts"], inputs["bake"] / "made",
                                materials)
             for model, entry in json.loads((inputs["bake"] / "baked.json").read_text()).items()}
    (out / "checks.json").write_text(json.dumps(found, indent=1))


def check_faults(folder):
    return [] if (folder / "checks.json").exists() else ["no checks.json"]


def surface_faults(name, record):
    """A baked model's faults against its surfaces: parts off their surface's colour, near-black blotches, a
    surface not in the place's library."""
    faults = []
    for surface, entry in record["surfaces"].items():
        if entry["share"] < PART_LEAST:
            continue
        if entry["delta_e"] is None:
            faults.append(f"{name}: {surface} is not in the place's library")
        elif entry["delta_e"] > BAKE_DELTA_E:
            faults.append(f"{name}: {surface} baked {entry['baked_lab']} against {entry['surface_lab']} "
                          f"(dE {entry['delta_e']})")
        if entry["surface_lab"] and entry["surface_lab"][0] > DARK_SURFACE and entry["near_black"] > BLOTCH_SHARE:
            faults.append(f"{name}: {surface} {entry['near_black']:.1%} near black")
    return faults


def judge_lit(output, inputs, evidence):
    """The baked model matches its surfaces: every part's baked colour on its surface, no blotch, every map."""
    found = json.loads((output / "checks.json").read_text())
    failing = []
    for name, record in found.items():
        failing += [f"{name}: no {role} map" for role in record["missing_maps"]] + surface_faults(name, record)
    return gates.verdict("baked matches its surfaces", failing, len(found), "faults over the models")


def judge_triangles(output, inputs, evidence):
    """Triangles within the bake job's budget per model."""
    found = json.loads((output / "checks.json").read_text())
    failing = [f"{name}: {record['triangles']} triangles over {record['budget']}" for name, record in found.items()
               if record["triangles"] > record["budget"]]
    return gates.verdict("triangles within budget", failing, len(found), "models",
                         {"triangles": sum(record["triangles"] for record in found.values())})


STEPS = {"check": check_step}

if __name__ == "__main__":
    prop_env.main(STEPS)
