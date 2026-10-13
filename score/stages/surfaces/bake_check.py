"""The framework's check of a place's baked models (row surfaces-check@<place>, after place_line.py's paint and bake):
every part's baked base colour lies on its library surface (CIE76 under BAKE_DELTA_E) and near its colour in the
close-up (under CLOSE_UP_DELTA_E), a model's surfaces do not collapse into one look its close-up does not have, no
near-black blotch, every map there, triangles within the bake job's budget. A module of its own, so a change to the check moves the check
row's key alone, never the paint's or the paid bake's.
"""
import json
import math
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
# A model's surfaces collapse into one look when every two of them bake within ONE_LOOK_DELTA_E (CIE76) and every one
# is near neutral (chroma under NEUTRAL_CHROMA), while its close-up shows them over DISTINCT_DELTA_E apart (twice
# ONE_LOOK) or its main surface's close-up colour is not neutral. The greenhouse's water tank (2026-10-12): cream paint,
# bare steel and water, 28.5 apart in the close-up, baked as three greys 10.2 apart at most, which the owner saw as one
# white block. On world 1's 39 split models with two surfaces or more (measured 2026-10-12) the next widest after the
# tank's and the greenhouse crop crate's (9.3: off-white paint over wood in the grey deck token) is 15.1 (the
# campgrounds' cargo pallet).
ONE_LOOK_DELTA_E, NEUTRAL_CHROMA, DISTINCT_DELTA_E = 12.0, 10.0, 24.0
# A part's baked colour must lie within this of its finish's colour in the close-up (finish_parts.COLOUR_DELTA_E, kept
# at 32, measured 2026-10-12 on world 1's 145 measured finishes): the close-up's light lifts a right surface's L* by
# 15 to 30 (stainless 66 seen at 85, black rubber 9 seen at 30 to 40), so right surfaces lie up to dE 31.7 from it
# while the water tank's grey for cream lies 22.5 off; at 22.5 the check would fail 51 of 145 finishes, most of them
# right blacks. A wrong light paint among right parts is caught by the one look above, which compares a model's
# surfaces with each other, so the close-up's light cancels.
CLOSE_UP_DELTA_E = 32.0
# The close-up's light moves every surface's L*, but keeps their order: of two opaque surfaces of a model, the one its
# close-up shows over ORDER_L lighter must not bake over ORDER_BAKED darker. The water tank's cream paint, 13 L* over
# its bare steel in the close-up, baked 4.7 under it as painted_panel. Measured 2026-10-12 on world 1's split models
# (library colours): 5 pairs on 4 models reverse so, the tank, the airlock's dust vacuum (its paint 10 L* over its
# steel, baked 4.7 under), the campgrounds' open cargo case (tan cardboard as carbon_fibre) and the greenhouse's seed
# tray (its dark plastic as black rubber, under its soil).
# See-through and glowing surfaces (SEEN_THROUGH families) are left out: their close-up lightness is what they show.
ORDER_L, ORDER_BAKED = 10.0, 3.0
SEEN_THROUGH = ("glass", "screen", "light", "water")
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


def check_model(name, entry, labelled, made, materials, dirt=0.0):
    """One baked model measured: per surface its parts' baked base colour (area-weighted median over its triangles'
    texture at their middles' coordinates; glTF's v runs down the picture) against the surface's colour dirtied as the
    place's dirt dirties it (on_surface), its blotch share, its maps and its triangles against the job's budget."""
    import numpy as np
    from PIL import Image
    import labels
    geometry, maps = gltf_model(made / f"{name}.gltf")
    record = {"triangles": int(len(geometry["triangles"])), "budget": int(entry["faces"]),
              "maps": sorted(maps), "surfaces": {}, "close_up": close_up_colours(labelled)}
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
    dirty = [labels.lab(labels.srgb(np.array(materials[each]["dirt_colour"]))[None])[0]
             if each in materials and "dirt_colour" in materials[each] else None for each in names]
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
            "delta_e": None if token is None else round(on_surface(middle, token, dirty[index], dirt), 1),
            "dirt_lab": None if dirty[index] is None else [round(float(value), 1) for value in dirty[index]],
            "near_black": round(blotch_share(colour, areas, chosen, reach, tokens), 4),
            "family": materials.get(names[index], {}).get("family")}
    return record


def on_surface(baked, clean, dirt_colour, dirt):
    """How far (CIE76) a part's baked colour lies from its library colour dirtied toward the place's dirt colour, as
    far as the place's dirt amount: the nearest point of that stretch (the bake dirties a surface up to its place's
    dirt; wreck and old_station are dirt 0.6 in regolith: a white at L* 89.6 bakes to 69). A clean place, or a surface
    with no dirt colour, is measured against its library colour alone."""
    import numpy as np
    if dirt_colour is None or dirt <= 0:
        return float(np.linalg.norm(baked - clean))
    toward = dirt_colour - clean
    share = float(np.clip(np.dot(baked - clean, toward) / max(float(np.dot(toward, toward)), 1e-9), 0.0, dirt))
    return float(np.linalg.norm(baked - (clean + share * toward)))


def close_up_colours(labelled):
    """Each surface's colour in the close-up (L*a*b*, the mean of its finishes' measured colours) from the paint's
    report of the take (labels.json `finishes`); {} when the method measured none."""
    measured = {}
    for finish in json.loads((labelled / "labels.json").read_text()).get("finishes", []):
        if finish.get("measured_lab") is not None:
            measured.setdefault(finish["surface"], []).append(finish["measured_lab"])
    return {surface: [round(sum(colour[axis] for colour in colours) / len(colours), 1) for axis in range(3)]
            for surface, colours in measured.items()}


def make_check(inputs, out, seed, params):
    prop_env.handover(__file__, "check", inputs, out)


def check_step(inputs, out):
    """The prop environment's side: every baked model measured (checks.json)."""
    import library
    name = data_of(inputs)["library"]
    materials = {**library.by_library(name), **library.resolved(name)}
    dirt = library.wear_of(name)[1]
    found = {model: check_model(model, entry, inputs["paint"] / "labelled" / entry["parts"], inputs["bake"] / "made",
                                materials, dirt)
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
    return faults + close_up_faults(name, record) + one_look_faults(name, record) + order_faults(name, record)


def order_faults(name, record):
    """Each pair of a model's judged opaque surfaces whose lightness order the bake reverses from the close-up's: the
    one seen over ORDER_L lighter baked over ORDER_BAKED darker."""
    close_up = record.get("close_up", {})
    judged = {surface: entry for surface, entry in judged_surfaces(record).items()
              if surface in close_up and entry.get("family") not in SEEN_THROUGH}
    faults = []
    for lighter, entry in sorted(judged.items()):
        for darker, other in sorted(judged.items()):
            seen = close_up[lighter][0] - close_up[darker][0]
            baked = entry["baked_lab"][0] - other["baked_lab"][0]
            if seen > ORDER_L and baked < -ORDER_BAKED:
                faults.append(f"{name}: {lighter} is {seen:.1f} L* lighter than {darker} in its close-up but bakes "
                              f"{-baked:.1f} darker")
    return faults


def judged_surfaces(record):
    """A baked model's surfaces the check judges (PART_LEAST of it or more): {surface: its entry}."""
    return {surface: entry for surface, entry in record["surfaces"].items() if entry["share"] >= PART_LEAST}


def close_up_faults(name, record):
    """Each judged surface whose baked colour lies over CLOSE_UP_DELTA_E from its colour in the close-up."""
    close_up = record.get("close_up", {})
    faults = []
    for surface, entry in judged_surfaces(record).items():
        apart = math.dist(entry["baked_lab"], close_up[surface]) if surface in close_up else 0.0
        if apart > CLOSE_UP_DELTA_E:
            faults.append(f"{name}: {surface} baked {entry['baked_lab']}, its close-up {close_up[surface]} "
                          f"(dE {apart:.1f}, over {CLOSE_UP_DELTA_E:.0f})")
    return faults


def widest(colours):
    """The largest CIE76 distance between two of the colours, 0 for fewer than two."""
    colours = list(colours)
    return max((math.dist(first, second) for index, first in enumerate(colours) for second in colours[index + 1:]),
               default=0.0)


def chroma(colour):
    return math.hypot(colour[1], colour[2])


def one_look_faults(name, record):
    """A model whose judged surfaces bake to one near-neutral look (every two within ONE_LOOK_DELTA_E, each under
    NEUTRAL_CHROMA) while its close-up shows them over DISTINCT_DELTA_E apart, or its main surface not neutral."""
    judged = judged_surfaces(record)
    baked = [entry["baked_lab"] for entry in judged.values()]
    if len(judged) < 2 or widest(baked) >= ONE_LOOK_DELTA_E or max(map(chroma, baked)) >= NEUTRAL_CHROMA:
        return []
    close_up = {surface: colour for surface, colour in record.get("close_up", {}).items() if surface in judged}
    main = max(judged, key=lambda surface: judged[surface]["share"])
    seen = widest(close_up.values())
    if seen <= DISTINCT_DELTA_E and (main not in close_up or chroma(close_up[main]) < NEUTRAL_CHROMA):
        return []
    return [f"{name}: its {len(judged)} surfaces ({', '.join(sorted(judged))}) bake to one grey look, "
            f"{widest(baked):.1f} apart at most (under {ONE_LOOK_DELTA_E:.0f}), while its close-up shows them "
            f"{seen:.1f} apart (its main surface {main} seen at {close_up.get(main)})"]


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
