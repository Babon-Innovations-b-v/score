"""A baked model's texture layout measured (#92): per map, the triangles whose texture coordinates lie outside the
picture, are mirrored, share texels with another triangle (overlap), are stretched one way, get far less texture
detail than the model's own (a face given a fraction of the density), and the charts too thin to hold a colour.
route_check.py records it on each baked model (layout_of), judge_layout fails a model by name: here, not in
bake_check.py, which the people's dress (people/baked_body.py) and other lines read, so the gate moves the check
row's key alone.

The method follows marso-skills' Apache-2.0 texture scripts (github.com/mxr-software/marso-skills, commit dc632e34,
skills/blender/marso-blender-texture/scripts/audit_uv.py and measure_uv_quality.py: the winding test, the per-triangle
Jacobian's anisotropy, density as resolution * sqrt(UV area / surface area), charts joined by exact position and UV
across the exported normal splits, chart width as 2 * area / perimeter), rewritten here in numpy over the baked
.gltf (baked_gltf.geometry) rather than inside Blender. Overlap is counted where the bake writes, texel centres of
the map's base colour picture lying on two triangles or more, not as polygon intersections."""
import json
import pathlib

import numpy as np

# A triangle under a ten-thousandth of a texel, or with no surface, measures nothing.
DEGENERATE_TEXELS = 1e-4
DEGENERATE_M2 = 1e-14


def layout_of(gltf):
    """A baked .gltf's texture layout (layout_record), each map measured against its base colour picture's size."""
    from PIL import Image
    import bake_check
    geometry, maps = bake_check.gltf_model(gltf)
    sizes = []
    for roles in maps:
        with Image.open(roles["base_color"]) as picture:
            sizes.append(tuple(int(value) for value in picture.size))
    return layout_record(measure(geometry, sizes))


def judge_layout(output, inputs, evidence):
    """Every baked model's texture layout sound (#92): no surface outside its picture, mirrored, sharing texels,
    stretched, given a fraction of its model's texture detail or in charts too thin to hold a colour, past each
    measure's limit (LIMITS), named by model and measure."""
    import surface_gates as gates
    found = json.loads((pathlib.Path(output) / "checks.json").read_text())
    measured = {model: record["layout"] for model, record in found.items() if "layout" in record}
    if not measured:
        return gates.unknown("texture layout sound", "no baked model's texture layout was measured")
    failing = [f"{model}: {fault}" for model, layout in measured.items() for fault in faults(layout)]
    return gates.verdict("texture layout sound", failing, len(measured), "layout faults over the models")


def measure(geometry, sizes):
    """The layout's measures over every map (`sizes`: each map's base colour picture as (width, height)): each
    triangle's 3D area and map, and per triangle its winding, out-of-picture, overlap, anisotropy, density and chart
    width; see layout_record for what is kept."""
    corners = geometry["positions"][geometry["triangles"]]
    areas = 0.5 * np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
    flat = geometry["uvs"][geometry["triangles"]]
    pixels = flat * np.asarray(sizes, dtype=np.float64)[geometry["maps"]][:, None, :]
    signed = winding(pixels)
    found = {"areas": areas, "maps": geometry["maps"], "signed": signed,
             "outside": ((flat < -1e-6) | (flat > 1 + 1e-6)).any(axis=(1, 2)),
             "valid": (np.abs(signed) > DEGENERATE_TEXELS) & (areas > DEGENERATE_M2),
             "overlapped": np.zeros(len(areas), dtype=bool), "width": np.zeros(len(areas)), "texels": [0, 0]}
    found["anisotropy"] = anisotropy(corners, pixels)
    found["density"] = np.sqrt(np.abs(signed) / np.maximum(areas, DEGENERATE_M2))
    for number in np.unique(geometry["maps"]):
        chosen = np.flatnonzero(geometry["maps"] == number)
        width, height = sizes[number]
        found["overlapped"][chosen], shared, covered = overlapped(pixels[chosen], width, height)
        found["texels"] = [found["texels"][0] + shared, found["texels"][1] + covered]
        found["width"][chosen] = chart_widths(geometry, chosen, pixels[chosen])
    return found


def winding(pixels):
    """Each triangle's signed area in texels, in glTF's texture convention (v down the picture): positive for a face
    laid as the bake lays it (Blender's v up, counter-clockwise), negative for one laid mirrored."""
    first, second, third = pixels[:, 0], pixels[:, 1], pixels[:, 2]
    return -0.5 * ((second[:, 0] - first[:, 0]) * (third[:, 1] - first[:, 1])
                   - (second[:, 1] - first[:, 1]) * (third[:, 0] - first[:, 0]))


def anisotropy(corners, pixels):
    """Each triangle's stretch: the ratio of the largest to the smallest scale its 3D-to-texture map has (1 lays it
    alike both ways; marso's measure_uv_quality, the Jacobian in the triangle's own orthonormal frame); infinite for a
    triangle that measures nothing."""
    along = corners[:, 1] - corners[:, 0]
    across = corners[:, 2] - corners[:, 0]
    length = np.linalg.norm(along, axis=1)
    height = np.linalg.norm(np.cross(along, across), axis=1) / np.maximum(length, 1e-15)
    offset = np.einsum("ij,ij->i", along, across) / np.maximum(length, 1e-15)
    first = pixels[:, 1] - pixels[:, 0]
    second = pixels[:, 2] - pixels[:, 0]
    scale_u = first / np.maximum(length, 1e-15)[:, None]
    scale_v = (second - scale_u * offset[:, None]) / np.maximum(height, 1e-15)[:, None]
    trace = (scale_u ** 2).sum(axis=1) + (scale_v ** 2).sum(axis=1)
    determinant = np.abs(scale_u[:, 0] * scale_v[:, 1] - scale_u[:, 1] * scale_v[:, 0])
    largest = 0.5 * (trace + np.sqrt(np.maximum(0.0, trace ** 2 - 4 * determinant ** 2)))
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(determinant > 0, largest / determinant, np.inf)
    return np.where((length > 1e-15) & (height > 1e-15), ratio, np.inf)


def overlapped(pixels, width, height):
    """Each of a map's triangles (`pixels`: its corners in texels) that shares a texel with another triangle (a texel
    centre strictly inside two triangles or more, so the bake writes one colour for both), with the map's shared and
    covered texel counts."""
    counts = np.zeros((height, width), dtype=np.int32)
    covered = []
    for triangle in pixels:
        rows, columns = texels_inside(triangle, width, height)
        covered.append((rows, columns))
        np.add.at(counts, (rows, columns), 1)
    shares = np.array([bool((counts[rows, columns] > 1).any()) for rows, columns in covered], dtype=bool)
    return shares, int((counts > 1).sum()), int((counts > 0).sum())


def texels_inside(triangle, width, height):
    """The texels (rows, columns) of a `width` by `height` picture whose centres lie strictly inside the triangle
    (its corners in texels, wrapped onto the picture as the bake samples: bake_check.texel_owners's `% 1.0`)."""
    triangle = triangle - np.floor(triangle.min(axis=0) / [width, height]) * [width, height]
    low = np.floor(triangle.min(axis=0) - 0.5).astype(int)
    high = np.ceil(triangle.max(axis=0) - 0.5).astype(int)
    columns, rows = np.meshgrid(np.arange(max(low[0], 0), min(high[0], width - 1) + 1),
                                np.arange(max(low[1], 0), min(high[1], height - 1) + 1))
    columns, rows = columns.ravel(), rows.ravel()
    frame = np.array([triangle[1] - triangle[0], triangle[2] - triangle[0]]).T
    if len(columns) == 0 or abs(np.linalg.det(frame)) < 1e-12:
        return rows[:0], columns[:0]
    local = np.linalg.solve(frame, (np.stack([columns + 0.5, rows + 0.5], axis=1) - triangle[0]).T).T
    edge = 1e-9
    inside = (local[:, 0] > edge) & (local[:, 1] > edge) & (local.sum(axis=1) < 1 - edge)
    return rows[inside], columns[inside]


def chart_widths(geometry, chosen, pixels):
    """Each of a map's triangles' chart width in texels, 2 * chart area / chart perimeter (marso's
    area_perimeter_width_proxy_px): its chart the triangles joined by an edge whose ends share position and texture
    coordinate, so the .gltf's split corners at a hard normal edge join again."""
    triangles = geometry["triangles"][chosen]
    keys = np.concatenate([geometry["positions"], geometry["uvs"]], axis=1)
    _, corner_ids = np.unique(np.round(keys, 9), axis=0, return_inverse=True)
    corners = corner_ids.reshape(-1)[triangles]
    edges = np.concatenate([corners[:, [0, 1]], corners[:, [1, 2]], corners[:, [2, 0]]])
    owners = np.tile(np.arange(len(triangles)), 3)
    ordered = np.sort(edges, axis=1)
    _, edge_ids, uses = np.unique(ordered, axis=0, return_inverse=True, return_counts=True)
    edge_ids = edge_ids.reshape(-1)
    charts = joined(len(triangles), edge_ids, owners)
    texel_area = np.abs(winding(pixels))
    edge_pixels = np.concatenate([pixels[:, [0, 1]], pixels[:, [1, 2]], pixels[:, [2, 0]]])
    lengths = np.linalg.norm(edge_pixels[:, 1] - edge_pixels[:, 0], axis=1)
    border = uses[edge_ids] == 1
    area = np.bincount(charts, weights=texel_area)
    perimeter = np.bincount(charts[owners[border]], weights=lengths[border], minlength=len(area))
    with np.errstate(divide="ignore", invalid="ignore"):
        width = np.where(perimeter > 0, 2 * area / perimeter, np.inf)
    return width[charts]


def joined(count, edge_ids, owners):
    """Each of `count` triangles' chart number: triangles sharing an edge id (`edge_ids`, each owned by `owners`)
    joined, by union-find."""
    parent = np.arange(count)

    def root(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index
    first_owner = {}
    for edge, owner in zip(edge_ids.tolist(), owners.tolist()):
        if edge in first_owner:
            parent[root(owner)] = root(first_owner[edge])
        else:
            first_owner[edge] = owner
    roots = np.array([root(index) for index in range(count)])
    return np.unique(roots, return_inverse=True)[1].reshape(-1)


def layout_record(found):
    """What the check keeps of a model's layout, each a share of its surface area (3D): outside the picture, mirrored,
    stretched past STRETCH, under DENSITY_FALL of the model's median density (area-weighted), in charts under
    THIN_TEXELS wide; the overlap as a share of its covered texels; and the median density and p95 stretch."""
    areas, valid = found["areas"], found["valid"]
    total = float(areas.sum()) or 1.0
    density = found["density"][valid]
    median = weighted_quantile(density, areas[valid], 0.5)
    stretch = found["anisotropy"][valid]

    def share(mask):
        return round(float(areas[mask].sum() / total), 4)
    return {"outside": share(found["outside"]), "mirrored": share(valid & (found["signed"] < 0)),
            "overlap": round(found["texels"][0] / max(found["texels"][1], 1), 4),
            "stretched": share(valid & (found["anisotropy"] > STRETCH)),
            "sparse": share(valid & (found["density"] < median * DENSITY_FALL)),
            "thin": share(valid & (found["width"] < THIN_TEXELS)),
            "degenerate": share(~valid),
            "median_texels_per_m": round(float(median), 1),
            "stretch_p95": round(float(weighted_quantile(stretch, areas[valid], 0.95)), 2)}


def weighted_quantile(values, weights, fraction):
    """The value at `fraction` of the weight, values in order (marso's _percentile); 0 when nothing is weighed."""
    if len(values) == 0 or weights.sum() <= 0:
        return 0.0
    order = np.argsort(values)
    reached = np.cumsum(weights[order])
    return float(values[order][min(np.searchsorted(reached, fraction * reached[-1]), len(values) - 1)])


def faults(layout):
    """A model's layout faults, one a measure past its limit (LIMITS), in words (WORDS) with its share."""
    return [f"{WORDS[measure]} {layout[measure]:.1%} of its surface, over {limit:.1%}"
            if measure != "overlap" else f"{WORDS[measure]} {layout[measure]:.1%} of its texels, over {limit:.1%}"
            for measure, limit in LIMITS.items() if layout[measure] > limit]


WORDS = {"outside": "texture coordinates outside the picture on", "mirrored": "texture laid mirrored on",
         "overlap": "texture shared by two faces on", "stretched": "texture stretched one way on",
         "sparse": "a fraction of the model's texture detail on", "thin": "charts too thin for a colour on"}
# The limits. marso sets no universal stretch or chart threshold, so each is the point a texel stops holding its own
# face's colour: a face mapped over STRETCH times longer one way than the other, given under DENSITY_FALL of its
# model's median texels a metre (the bake's old hidden share gave the back a twentieth), or in a chart under
# THIN_TEXELS of the base colour picture wide (its colour bleeds into its neighbours'). A model fails on a share of
# its surface over LEAST, the share bake_check judges a part at (PART_LEAST); outside the picture on any share, since
# the bake wraps it onto another chart. Measured on env1's 439 baked models on this PC's store (2026-11-05): stretch
# p95 at most 1.77, nothing outside, no sparse or mirrored share over 0.02%; 15 models over 1% of their texels
# shared (galley's stove top 12.4%, the faces sharing a texel 7% of its size apart), 17 over 1% in charts under a
# texel (quarters' sticky note on its 128 px picture 3.2%).
STRETCH = 4.0
DENSITY_FALL = 0.25
THIN_TEXELS = 1.0
LEAST = 0.01
LIMITS = {"outside": 0.0, "mirrored": LEAST, "overlap": LEAST, "stretched": LEAST, "sparse": LEAST, "thin": LEAST}
