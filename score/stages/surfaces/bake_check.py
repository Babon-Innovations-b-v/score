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
# BLOTCH_L (the black blotches of round six) whose colour lies over BLOTCH_DELTA_E from every colour of every surface
# within its reach: a surface's colour and the second its recipe draws (the flat's quilt_cotton draws ink-line seams,
# 6% of its bake near black, 2026-10-13; measured against its colour alone they failed it as blotches). Inside a part
# that is its own surface, so every near-black triangle off its colours counts; on a border it may bake its
# neighbour's colour and count only when it is off that one too (the seed tray's paper label on black plastic, bake of
# 2026-10-12: its 19 near-black triangles bake the plastic, nine in ten within 3.3 of its colour; black lies 9.5 off
# it). A smudge within BLOTCH_DELTA_E of a dark neighbour's colour cannot be told from that neighbour and passes.
# The cost of counting a drawn second: 4 of the library's 369 variants (perforated_steel, perforated_blue_board,
# quilt_cotton, composite_grey; not dark, a second at L* 2.5) can now hide a black smudge under L* 8.5 on themselves.
# Parts under PART_LEAST of the model are not judged.
BAKE_DELTA_E = 20.0
# A standing model's footprint quadrants (of its lowest STANCE_BAND of height) end within STANCE_GAP of its lowest
# point (the resting check's 3 cm).
STANCE_BAND, STANCE_GAP = 0.25, 0.03
# Not paint (owner, #8): judged by their own colour, never against the close-up's lit colour.
OWN_COLOUR = ("glass", "screen", "light", "print")
DARK_SURFACE, BLOTCH_L, BLOTCH_SHARE, BLOTCH_DELTA_E = 35.0, 12.0, 0.05, 6.0
PART_LEAST = 0.01
# A model's surfaces collapse into one look when no two of them bake far enough apart for a viewer to tell at the
# place's view distance, every one is near neutral (chroma under NEUTRAL_CHROMA), while its close-up shows them over
# DISTINCT_DELTA_E apart or its main surface's close-up colour is not neutral (the greenhouse's water tank, 2026-10-12:
# cream paint, bare steel and water, 28.5 apart in the close-up, baked as three greys). What a viewer tells apart is
# measured, not set: Stone, Szafir and Setlur (2014, "An Engineering Model for Color Difference as a Function of
# Size", IS&T Color and Imaging Conference 22, Table 3) measured the CIELAB difference half of their viewers see
# between two colours s degrees of visual angle wide, per axis ND(50, s) = C + K / s (NOTICED: C, K for L*, a*, b*),
# on sizes 1/3 to 6 degrees (SEEN_DEGREES; a size outside is taken at the nearer end). Two surfaces are told apart
# when their difference, each axis over its ND, is 1 or more. A surface's size is its model's middle size times the
# root of its share, seen from the place's nearest view (its scene record's eyes, its inventory's spots). It replaced
# a fixed CIE76 12 (owner, 2026-10-13: the wreck's access cover, its steel 9.3 L* under its scorched white, failed
# on a difference he sees; at 6 degrees half of viewers see 5.2 L*).
NOTICED = ((5.079, 0.751), (5.339, 1.541), (5.349, 2.871))
SEEN_DEGREES = (1 / 3, 6.0)
NEUTRAL_CHROMA, DISTINCT_DELTA_E = 10.0, 24.0
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
# The bake names a baked triangle's colour by a ray (make_chunky's bake_from: Blender's selected-to-active, its cage
# BAKE_REACH_VOXELS of its solid copy's voxels out (BAKE_VOXEL_SHARE of the piece's largest side, no finer than
# BAKE_VOXEL_FINEST), at least BAKE_REACH_LEAST, as make_chunky's bake_reach), so the check names its surface the same way: from its middle that far out along its normal, inward,
# the first labelled face hit. The nearest labelled point named the wrong part: the bake's cut-down copy stands a wall
# proud of the model (0.6 m on far_city's 140 m pencil tower, 2026-10-13), and from there a thin post's side lies
# nearer than the facade the bake's ray meets, so half of what the check called post_dark baked the facade and its
# median failed at dE 45 while every triangle the bake's ray gave the post baked its library colour exactly.
BAKE_REACH_VOXELS, BAKE_REACH_LEAST = 4, 0.01
BAKE_VOXEL_SHARE, BAKE_VOXEL_FINEST = 1 / 300, 0.0012
# The wear stretch (on_surface) is tried at this many shares from clean to the place's wear, each dirtied exactly.
WEAR_STEPS = 41


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


def laid_parts(labelled, entry, laid_folder=None):
    """A labelled take's parts (one .ply per surface) as one mesh laid into the kit frame as make_chunky lays them
    (stored_parts.kit_frame): (surface names, the mesh, each vertex's surface index, each face's surface index). A model
    the bake built over a body (make_chunky.make_bodied) is laid as the bake made it: its `laid_folder` (`<model>.parts`
    beside the made model) holds its surfaces' faces already in the kit frame, the body's and the details it kept."""
    import numpy as np
    import trimesh
    import stored_parts
    bodied = laid_folder is not None and laid_folder.is_dir()
    paths = sorted((laid_folder if bodied else labelled).glob("*.ply"))
    meshes = [trimesh.load(path, process=False) for path in paths]
    joined = trimesh.util.concatenate(meshes)
    laid = np.asarray(joined.vertices) if bodied else stored_parts.kit_frame(
        np.asarray(joined.vertices), np.array(entry["base"]).reshape(3, 3), entry["size"])
    vertex_codes = np.concatenate([np.full(len(mesh.vertices), code) for code, mesh in enumerate(meshes)])
    codes = np.concatenate([np.full(len(mesh.faces), code) for code, mesh in enumerate(meshes)])
    return [path.stem for path in paths], trimesh.Trimesh(laid, joined.faces, process=False), vertex_codes, codes


def ray_surfaces(geometry, laid, codes, size, sampled=None):
    """Each baked triangle's surface index as the bake's ray finds it (BAKE_REACH_VOXELS): the first laid face hit from
    its sampled point (`sampled`: (points, triangles they lie on), else each triangle's middle) that far out along its
    triangle's normal, inward; -1 where the ray meets nothing."""
    import numpy as np
    corners = geometry["positions"][geometry["triangles"]]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    points, owners = sampled if sampled is not None else (corners.mean(axis=1), np.arange(len(corners)))
    reach = max(BAKE_REACH_VOXELS * max(BAKE_VOXEL_FINEST, max(size) * BAKE_VOXEL_SHARE), BAKE_REACH_LEAST)
    hit = laid.ray.intersects_first(points + normals[owners] * reach, -normals[owners])
    return np.where(hit >= 0, codes[np.maximum(hit, 0)], -1)


def sampled_points(geometry, rows, columns, width, height):
    """Where on the baked mesh each triangle's sampled texel (rows, columns) was baked: the bake writes a texel by its
    centre's point, which lies on whichever triangle covers it in the texture layout, often not the triangle sampled
    (the flat's bowl stack, bake of 2026-10-13: 1,543 of its 4,995 triangles, its glass rims under a texel each); a
    centre on no triangle (the bake's padding round each island) keeps the sampled triangle's middle. Returns (points,
    the triangle each lies on)."""
    import numpy as np
    corners = geometry["positions"][geometry["triangles"]]
    pixel = (geometry["uvs"][geometry["triangles"]] % 1.0) * [width, height]
    owner = np.full((height, width), -1)
    weights = np.zeros((height, width, 3))
    for triangle, (first, second, third) in enumerate(pixel):
        low = np.floor(np.minimum(np.minimum(first, second), third) - 0.5).astype(int)
        high = np.ceil(np.maximum(np.maximum(first, second), third) - 0.5).astype(int)
        columns_here, rows_here = np.meshgrid(np.arange(max(low[0], 0), min(high[0], width - 1) + 1),
                                              np.arange(max(low[1], 0), min(high[1], height - 1) + 1))
        columns_here, rows_here = columns_here.ravel(), rows_here.ravel()
        frame = np.array([second - first, third - first]).T
        if len(columns_here) == 0 or abs(np.linalg.det(frame)) < 1e-12:
            continue
        local = np.linalg.solve(frame, (np.stack([columns_here + 0.5, rows_here + 0.5], axis=1) - first).T).T
        inside = (local[:, 0] >= 0) & (local[:, 1] >= 0) & (local.sum(axis=1) <= 1)
        owner[rows_here[inside], columns_here[inside]] = triangle
        weights[rows_here[inside], columns_here[inside]] = np.stack(
            [1 - local[inside].sum(axis=1), local[inside, 0], local[inside, 1]], axis=1)
    found = owner[rows, columns]
    owners = np.where(found >= 0, found, np.arange(len(corners)))
    bary = np.where((found >= 0)[:, None], weights[rows, columns], 1 / 3)
    return np.einsum("ij,ijk->ik", bary, corners[owners]), owners


def baked_surfaces(geometry, labelled, entry, sampled=None, laid_folder=None):
    """Each baked triangle's surface and the surfaces within its reach, the labelled parts laid in the kit frame
    (laid_parts): (surface names, each triangle's surface index (the bake's ray from its sampled point, ray_surfaces
    and sampled_points; the part whose nearest point lies under its middle where the ray meets nothing), reach (triangles x surfaces: its own, its corners' and
    every part with a point within its furthest corner from its middle))."""
    import numpy as np
    from scipy.spatial import cKDTree
    names, laid, vertex_codes, codes = laid_parts(labelled, entry, laid_folder)
    kept = np.concatenate([np.flatnonzero(vertex_codes == code)[::max(1, (vertex_codes == code).sum() // PART_POINTS)]
                           for code in range(len(names))])
    tree, point_codes = cKDTree(laid.vertices[kept]), vertex_codes[kept]
    corners = geometry["positions"][geometry["triangles"]]
    middles = corners.mean(axis=1)
    surface = ray_surfaces(geometry, laid, codes, entry["size"], sampled)
    surface = np.where(surface >= 0, surface, point_codes[tree.query(middles)[1]])
    reach = np.zeros((len(middles), len(names)), dtype=bool)
    reach[np.arange(len(middles)), surface] = True
    for corner in point_codes[tree.query(geometry["positions"])[1]][geometry["triangles"]].T:
        reach[np.arange(len(middles)), corner] = True
    radius = np.linalg.norm(corners - middles[:, None], axis=2).max(axis=1)
    for triangle, found in enumerate(tree.query_ball_point(middles, radius)):
        reach[triangle, np.unique(point_codes[found])] = True
    return names, surface, reach


def blotch_share(colour, areas, chosen, reach, shades):
    """The share of the chosen triangles' area that is a blotch: under BLOTCH_L and over BLOTCH_DELTA_E (CIE76) from
    every colour of every surface within its reach (`reach`: triangles x surfaces; `shades`: each surface's L*a*b*
    colours (library_shades), none for one not in the library, which explains nothing)."""
    import numpy as np
    far = np.full(len(colour), np.inf)
    for index, colours in enumerate(shades):
        for shade in colours:
            near = np.linalg.norm(colour - np.asarray(shade), axis=1)
            far = np.where(reach[:, index], np.minimum(far, near), far)
    blotch = chosen & (colour[:, 0] < BLOTCH_L) & (far > BLOTCH_DELTA_E)
    return float(areas[blotch].sum() / max(areas[chosen].sum(), 1e-12))


def library_shades(spec):
    """A library surface's L*a*b* colours as its recipe draws them: its colour, then its `second` when it has one (the
    quilt's ink-line seams, a perforated sheet's holes, tile grout: drawn on purpose, not a blotch)."""
    import numpy as np
    import labels
    return [labels.lab(labels.srgb(np.array(spec[key]))[None])[0] for key in ("colour", "second") if key in spec]


def area_median(colour, areas):
    """Colours' area-weighted median, each of L*, a*, b* on its own: a triangle picked by its L* alone brought its own
    a* and b* along, so a part whose colours share one L* took whichever lay in the middle (lab's junction_box_1,
    bake of 2026-10-14: 56% of its crane_yellow_paint's area baked yellow, 29% the grey panel round it at the same L*
    64, and the grey one picked failed it at dE 37)."""
    import numpy as np
    order = np.argsort(colour, axis=0)
    weights = np.cumsum(areas[order], axis=0)
    middles = (weights < weights[-1] / 2).sum(axis=0)
    return colour[order[middles, range(colour.shape[1])], range(colour.shape[1])]


def check_model(name, entry, labelled, made, materials, dirt=0.0, wear=0.0):
    """One baked model measured: per surface its parts' baked base colour (area_median over its triangles' texture
    at their middles' coordinates; glTF's v runs down the picture) against the surface's colour worn and dirtied as
    the place's wear and dirt wear and dirty it (on_surface), its blotch share, its maps and its triangles against
    the job's budget."""
    import numpy as np
    from PIL import Image
    import labels
    geometry, maps = gltf_model(made / f"{name}.gltf")
    record = {"triangles": int(len(geometry["triangles"])), "budget": int(entry["faces"]),
              "maps": sorted(maps), "surfaces": {}, "close_up": close_up_colours(labelled)}
    record["stance_lows"] = stance_lows(geometry["positions"])
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
    names, surface, reach = baked_surfaces(geometry, labelled, entry,
                                           sampled_points(geometry, rows, columns, width, height),
                                           made / f"{name}.parts")
    shades = [library_shades(materials[each]) if each in materials else [] for each in names]
    tokens = [colours[0] if colours else None for colours in shades]
    dirty = [labels.lab(labels.srgb(np.array(materials[each]["dirt_colour"]))[None])[0]
             if each in materials and "dirt_colour" in materials[each] else None for each in names]
    bare = [labels.lab(labels.srgb(np.array(materials[each]["bare"]))[None])[0]
            if each in materials and "bare" in materials[each] else None for each in names]
    for index in sorted(set(surface.tolist())):
        chosen = surface == index
        middle = area_median(colour[chosen], areas[chosen])
        token = tokens[index]
        record["surfaces"][names[index]] = {
            "share": round(float(areas[chosen].sum() / areas.sum()), 4),
            "baked_lab": [round(float(value), 1) for value in middle],
            "surface_lab": None if token is None else [round(float(value), 1) for value in token],
            "delta_e": None if token is None else round(on_surface(middle, token, dirty[index], dirt, bare[index],
                                                                     wear), 1),
            "dirt_lab": None if dirty[index] is None else [round(float(value), 1) for value in dirty[index]],
            "near_black": round(blotch_share(colour, areas, chosen, reach, shades), 4),
            "family": materials.get(names[index], {}).get("family")}
    return record


def on_surface(baked, clean, dirt_colour, dirt, bare=None, wear=0.0):
    """How far (CIE76) a part's baked colour lies from its library colour worn toward its recipe's `bare` (what its
    edge wear lays open, as far as the place's wear) and then dirtied toward the place's dirt colour (as far as the
    place's dirt): the nearest such colour (the bake wears and dirties a surface up to its place's settings; wreck and
    old_station are dirt 0.6 in regolith: a white at L* 89.6 bakes to 69; the engine room is worn 0.8, and its power
    core's thin hazard trim, 2026-10-15, baked 30% of its area bare steel and 32% part worn, its median dE 20.1 off
    the clean yellow and 2.3 off the worn one). A new, clean place, or a surface with neither, is measured against its
    library colour alone."""
    import numpy as np
    wears = np.linspace(0.0, wear, WEAR_STEPS) if bare is not None and wear > 0 else np.zeros(1)
    nearest = np.inf
    for share_worn in wears:
        worn = clean + share_worn * (bare - clean) if bare is not None else clean
        if dirt_colour is None or dirt <= 0:
            nearest = min(nearest, float(np.linalg.norm(baked - worn)))
            continue
        toward = dirt_colour - worn
        share = float(np.clip(np.dot(baked - worn, toward) / max(float(np.dot(toward, toward)), 1e-9), 0.0, dirt))
        nearest = min(nearest, float(np.linalg.norm(baked - (worn + share * toward))))
    return nearest


def stance_lows(points):
    """How far (metres) the lowest point of each footprint quadrant of a model's lowest quarter (what it stands on,
    +y up) lies over its lowest point: a standing model's are all near 0."""
    import numpy as np
    low, high = points.min(0), points.max(0)
    points = points[points[:, 1] <= low[1] + STANCE_BAND * (high[1] - low[1])]
    middle = (points.min(0) + points.max(0)) / 2
    found = []
    for x_side in (points[:, 0] < middle[0], points[:, 0] >= middle[0]):
        for z_side in (points[:, 2] < middle[2], points[:, 2] >= middle[2]):
            chosen = points[x_side & z_side]
            if len(chosen):
                found.append(round(float(chosen[:, 1].min() - low[1]), 3))
    return found


def stands(name, labelled, inventory_rows, lying_words):
    """Whether a baked model stands on its feet: its paint levelled its feet (not 'skipped': no floor or held row of
    its place lays it) and its inventory row's words name no lying class (data/checks/stance.json: torn wreckage on
    its side lies, it does not stand)."""
    report = json.loads((labelled / "labels.json").read_text())
    if "skipped" in report.get("feet", {}):
        return False
    row = next((row for row in inventory_rows if row.get("id") == name), {})
    words = f"{row.get('id', '')} {row.get('name', '')}".lower()
    return not any(word in words for word in lying_words)


def close_up_colours(labelled):
    """Each surface's colour in the close-up (L*a*b*, the mean of its finishes' measured colours) from the paint's
    report of the take (labels.json `finishes`); {} when the method measured none. A coloured see-through cover
    (`cover`, finish_parts.coloured_cover: the garage beacon's red_plastic dome, whose pixels are its highlights and
    what lies behind it) is left out, as glass is (owner, #8); any other finish judged by its own colour (an OWN_COLOUR
    family's, print off its listed colour) stays in, so the order and one-look checks still see it."""
    measured = {}
    for finish in json.loads((labelled / "labels.json").read_text()).get("finishes", []):
        if finish.get("measured_lab") is not None and not finish.get("cover"):
            measured.setdefault(finish["surface"], []).append(finish["measured_lab"])
    return {surface: [round(sum(colour[axis] for colour in colours) / len(colours), 1) for axis in range(3)]
            for surface, colours in measured.items()}


def seen_degrees(inputs, baked_sizes=None):
    """Each kit model's middle size in degrees of visual angle from the place's nearest view (its scene record's
    eyes) to its nearest spot (the kit's pieces, the scene record's objects and the machines record's machines, in
    the record's frame): {model: degrees}; {} with no kit or view. `baked_sizes`: {model: its bake entry's size}."""
    kit, scene = inputs.get("kit"), inputs.get("scene record")
    if kit is None or scene is None or not kit.exists() or not scene.exists():
        return {}
    record = json.loads(scene.read_text())
    eyes = [view["eye"] for view in record.get("views", [])]
    found = json.loads(kit.read_text())
    spots = [(piece["model"], piece["at"], piece["size"]) for piece in found.get("pieces", [])]
    spots += list(object_spots(record.get("objects", []), found.get("models", {})))
    machines = inputs.get("machines")
    if machines is not None and machines.exists():
        spots += list(machine_spots(json.loads(machines.read_text())["machines"], found.get("pieces", []),
                                    baked_sizes or {}))
    nearest = {}
    for model, spot, size in spots if eyes else []:
        near = min(math.dist(spot, eye) for eye in eyes)
        nearest[model] = max(nearest.get(model, 0.0),
                             math.degrees(2 * math.atan2(sorted(size)[1] / 2, max(near, 1e-3))))
    return {model: round(value, 2) for model, value in nearest.items()}


def object_spots(objects, sizes, origin=(0.0, 0.0, 0.0), yaw=0.0):
    """(model, spot, size) of each scene-record object the kit sizes, and of the models laid on it (`children`, their
    spots turned by the parent's yaw about +y: the hub's headset on its comms desk)."""
    turn = math.radians(yaw)
    for entry in objects:
        offset = entry.get("at")
        if not isinstance(offset, list) or len(offset) != 3:
            continue
        spot = [origin[0] + offset[0] * math.cos(turn) + offset[2] * math.sin(turn), origin[1] + offset[1],
                origin[2] - offset[0] * math.sin(turn) + offset[2] * math.cos(turn)]
        model = pathlib.Path(entry.get("model", "")).stem
        if "size" in sizes.get(model, {}):
            yield model, spot, sizes[model]["size"]
        yield from object_spots(entry.get("children", []), sizes, spot, yaw + entry.get("yaw", 0.0))


def machine_spots(machines, pieces, sizes):
    """(model, spot, size) of each machine of the place's machines record (data/machines: the hangar's ship and its
    thrusters) the bake sizes: one standing on a kit piece at that piece's spot (the machines stage centres it on its
    support), one mounted on another at its host's spot.
    shortcut: a mounted piece is seen at its host's middle, not its mount point (that needs the host's `nose`, which
    the record may not have yet), so a long host's far-end piece reads nearer than it is; upgrade with
    machines.mount_point once every host names its nose."""
    at = {piece["model"]: piece["at"] for piece in pieces}

    def spot_of(name):
        entry = machines[name]
        return spot_of(entry["mounted"]["on"]) if "mounted" in entry else at.get(entry["on"])

    for name, entry in machines.items():
        model, spot = entry.get("model", name), spot_of(name)
        if spot is not None and model in sizes:
            yield model, spot, sizes[model]


def make_check(inputs, out, seed, params):
    prop_env.handover(__file__, "check", inputs, out)


def check_step(inputs, out):
    """The prop environment's side: every baked model measured (checks.json)."""
    import library
    name = data_of(inputs)["library"]
    materials = {**library.by_library(name), **library.resolved(name)}
    wear, dirt = library.wear_of(name)
    rows = [row for key, path in inputs.items() if key.startswith("inventory ") and path.exists()
            for row in json.loads(path.read_text()).get("rows", [])]
    lying = [word for kind in json.loads(inputs["stance rules"].read_text())["lies"] for word in kind["words"]]
    baked = json.loads((inputs["bake"] / "baked.json").read_text())
    degrees = seen_degrees(inputs, {model: entry["size"] for model, entry in baked.items()})
    found = {}
    for model, entry in baked.items():
        labelled = inputs["paint"] / "labelled" / entry["parts"]
        found[model] = check_model(model, entry, labelled, inputs["bake"] / "made", materials, dirt, wear)
        found[model]["stands"] = stands(model, labelled, rows, lying)
        found[model]["seen_degrees"] = degrees.get(model)
    (out / "checks.json").write_text(json.dumps(found, indent=1))


def judge_stance(output, inputs, evidence):
    """Every baked model that stands on its feet stands level: each footprint quadrant's lowest point within
    STANCE_GAP of its lowest (the hangar's parts rack stood on a middle part, its legs 22 cm up; the paint's feet
    check, in shares of the model's size, let 7% pass). Lying wreckage and wall or held models are left out (stands)."""
    found = json.loads((output / "checks.json").read_text())
    standing = {model: record for model, record in found.items() if record.get("stands")}
    failing = [f"{model}: a foot {max(record['stance_lows']) * 100:.1f} cm off the floor while another touches "
               f"(quadrant lows {[round(low * 100, 1) for low in record['stance_lows']]} cm)"
               for model, record in standing.items() if max(record["stance_lows"]) > STANCE_GAP]
    return gates.verdict("stands level", failing, len(standing), "standing models with a foot off the floor")


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
    """Each judged surface whose baked colour lies over CLOSE_UP_DELTA_E from its colour in the close-up. Glass, screen
    glow, lamp light, print and a coloured see-through cover (close_up_colours) are judged by their own colour, not
    the close-up's lit one (owner, #8)."""
    close_up = record.get("close_up", {})
    faults = []
    for surface, entry in judged_surfaces(record).items():
        if entry.get("family") in OWN_COLOUR:
            continue
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


def noticed(first, second, degrees):
    """How many noticeable differences (Stone et al.'s ND(50), NOTICED) two L*a*b* colours lie apart, each `degrees`
    wide in the view: under 1, half of viewers or more cannot tell them apart."""
    degrees = min(max(degrees, SEEN_DEGREES[0]), SEEN_DEGREES[1])
    return math.sqrt(sum(((one - other) / (least + fall / degrees)) ** 2
                         for one, other, (least, fall) in zip(first, second, NOTICED)))


def told_apart(judged, degrees):
    """The most noticeable differences between two of a model's judged surfaces, each pair seen at the smaller one's
    size (the model's `degrees` times the root of its share)."""
    names = list(judged)
    return max(noticed(judged[first]["baked_lab"], judged[second]["baked_lab"],
                       degrees * math.sqrt(min(judged[first]["share"], judged[second]["share"])))
               for index, first in enumerate(names) for second in names[index + 1:])


def one_look_faults(name, record):
    """A model whose judged surfaces bake to one near-neutral look (no two told apart at the place's view distance,
    each under NEUTRAL_CHROMA) while its close-up shows them over DISTINCT_DELTA_E apart, or its main surface not
    neutral. A model with no view distance is named: whether a viewer tells its surfaces apart is unknown."""
    judged = judged_surfaces(record)
    baked = [entry["baked_lab"] for entry in judged.values()]
    if len(judged) < 2 or max(map(chroma, baked)) >= NEUTRAL_CHROMA:
        return []
    close_up = {surface: colour for surface, colour in record.get("close_up", {}).items() if surface in judged}
    main = max(judged, key=lambda surface: judged[surface]["share"])
    seen = widest(close_up.values())
    if seen <= DISTINCT_DELTA_E and (main not in close_up or chroma(close_up[main]) < NEUTRAL_CHROMA):
        return []
    degrees = record.get("seen_degrees")
    if degrees is None:
        return [f"{name}: no view distance (no spot in its place's kit or no view in its scene record), so "
                f"whether a viewer tells its {len(judged)} near-neutral surfaces apart is unknown"]
    apart = told_apart(judged, degrees)
    if apart >= 1:
        return []
    return [f"{name}: its {len(judged)} surfaces ({', '.join(sorted(judged))}) bake to one grey look, "
            f"{widest(baked):.1f} apart at most, {apart:.2f} noticeable differences at its view ({degrees:.1f} "
            f"degrees, under 1), while its close-up shows them {seen:.1f} apart (its main surface {main} seen at "
            f"{close_up.get(main)})"]


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
