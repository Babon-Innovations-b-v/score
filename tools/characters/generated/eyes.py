"""A generated person's eyes made real (#223): TRELLIS.2 paints its eyes into sunken holes with no eyeball (an iris and
pupil painted on the hole's floor, thick painted lids round it), and one wrong feature, the eyes most, makes a face
read fake. Each painted eye is replaced by the face module's own eye (`../face/`: ICT-FaceKit's eyeball with its UV
rings, the cornea's clear dome and the tear film over the white, the score_lib eye finishes).

    python -m tools.characters.generated.eyes <model.glb> <close-up photo> <out folder> --height <m>

The model is read as the head route draws it: scaled so it is `--height` tall, its front looking along +z, y up. Each
eye is found on the model seen from the front (its painted pupil, the darkest small blob a nose's height over the nose
tip, `pupils`), its lid margins along rays out from the pupil (the first steep forward rise, `rims`, joined round the
pupil into the opening's edge, `opening`); the eyeball, EYE_DIAMETER_M across scaled by the eyes' distance apart over
the adult mean, is set behind the pupil, its cornea just behind the margins and the ball RIM_GAP_M under every margin
(`eye_depth`), then EYE_FORWARD_M forward (the generated lid corners stand 6 to 8 mm in front of a ball sat so deep;
`lids.py` lays the lids over it), gazing at a point GAZE_M straight ahead (the close-up photos look into the camera;
both eyes the same point). The painted floor is pushed straight back (`pushed`) and removed where it lies inside the
ball (`buried`); the lids' inner rim gets a tear film over it (the wet line, `wet_strip`). The iris is the library's
iris toned to the colour read off the photo's iris (`photo_iris`); `iris_picture` unrolls the photo's own iris onto the
eyeball's UV for the whole head's run (`head.py`): its fibres, its pupil's size and its limbal ring, the catchlights and
the lid's shade taken off. The lids keep the model's geometry.

Writes <out>/eyes.npz (in the model's own frame and units: the pieces `blender_eyes.py` draws, the points it pushes
back and the triangles it removes) and <out>/stats.json; prints one line.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
import trimesh
from PIL import Image
from scipy import ndimage

FACE = pathlib.Path(__file__).resolve().parents[1] / "face"
EYE_DIAMETER_M = 0.024  # an adult eyeball's axial length
PUPIL_DISTANCE_M = 0.063  # the adult mean distance between the pupils
EYE_SCALE_LIMITS = (0.9, 1.1)  # the eye's size follows the face's within these
RIM_GAP_M = 0.0003  # each lid margin this far in front of the eyeball's surface
EYE_FORWARD_M = 0.002  # and the ball then moved this far forward (round 1, 2026-11-26: 6 to 8 mm behind the corners)
LID_EDGE_M = 0.0015  # a lid's inside rim: this deep behind its margin; deeper inside the opening is the painted floor
WET_FROM_M = 0.0002  # the wet line runs on the rim's inside from this behind the margin to LID_EDGE_M
SKIN_RING_M = (0.014, 0.02)  # the cheek's paint read this far out from each pupil, below it
SKIN_CHROMA = 0.05  # paint this far off the cheek's chroma is the eye's, not skin
OPENING_CORE = 0.85  # inside this share of the way to the opening's edge, paint in front of the eyeball is floor
OPENING_RAYS = 6  # an opening's edge needs margins on at least this many rays round its pupil
TEAR_FILM_LIFT_M = 0.00008  # the wet line's film over the skin
BURIED_M = 0.0004  # a painted triangle this far inside the eyeball is removed
CORNEA_RISE = 0.2  # the cornea's apex stands this share of the eyeball's radius over its sphere (the focus point)
GAZE_M = 1.5  # both eyes look at a point this far straight ahead (the photos' camera)
STEP_M = 0.00025  # the front view's pixel
WINDOW_M = {"over_top": 0.05, "under_top": 0.22, "half_width": 0.07}  # the front view round the face
NOSE = {"half_width": 0.012, "low_share": 0.6}  # the nose tip: the front-most point near the middle, low in the view
PUPIL_SEARCH_M = {"over_nose": (0.02, 0.06), "out": (0.02, 0.045)}  # where a pupil is looked for round the nose tip
BLOB_M = (0.0015, 0.005)  # a pupil's darkness: the paint smoothed over the first less over the second
RAY = {"from": 0.002, "to": 0.016, "degrees": np.arange(0, 360, 10)}  # the lid margin looked for along these rays
RIM_RISE_M = 0.001  # a lid margin stands at least this far forward of the floor before it
RIM_RUN_M = 0.0025  # within this run along the ray
RIM_OVER_FLOOR_M = 0.0015  # and stands at least this far over the painted pupil
RIM_NEIGHBOUR_SHARE = 0.75  # a margin this much closer in than both its neighbours is a floor bump
RIM_FLAT = 0.15  # and is where the rise flattens to this slope (depth over distance)
RIM_FROM_VERTICAL_DEGREES = 50.0  # margins on rays within this of straight up or down hold the eye
RIM_WITHIN = 0.9  # and within this share of the eyeball's radius out from the pupil
PHOTO = {"rows": (0.30, 0.46), "halves": ((0.35, 0.5), (0.5, 0.65)), "blob": (0.006, 0.02)}  # photo share of width
IRIS_RING = (0.45, 0.85)  # the photo's iris read on this ring of its radius (out of the pupil, in from the limbus)
IRIS_DIAMETER_M = 0.0117
IRIS_SURROUND = 1.6  # an iris is found as a dark disc against the ring out to this share of its radius
IRIS_CLIP = 0.9  # the window's highlights clipped at this quantile of its brightness
IRIS_LID_DEGREES = 100.0  # the ring's top this many degrees across lies in the upper lid's shade and lashes
IRIS_KEEP = (0.2, 0.85)  # of the ring's pixels, by brightness: drop the darkest (lashes, pupil) and the highlights
# The photo's iris unrolled onto the eyeball's UV (`iris_picture`): `size` texels square, read on `rings` x `rays` of
# the iris; a pixel within `lid` of a lid margin (its share of the radius) is the lid's shade or a lash, a pixel
# `catchlight` times brighter than the iris's body a reflection, both filled from the iris turned; the
# pupil's edge where the ring's brightness has risen `pupil_rise` of the way to the iris's; the limbal ring darkened
# to `limbus` of its brightness from `limbus_from` of the radius out.
IRIS_PICTURE = {"size": 1024, "rings": 96, "rays": 360, "lid": 0.15, "catchlight": 1.6, "pupil_rise": 0.5,
                "limbus": 0.6, "limbus_from": 0.82, "pupil_linear": 0.004,
                "radius": 0.87, "pupil_guess": 0.35,
                "turns": (180, 90, -90, 45, -45, 135, -135), "detail": (0.75, 1.3), "grow": 3}


def face_modules():
    """The face module's own `face` and `ict` (it imports its siblings by their plain names)."""
    if str(FACE) not in sys.path:
        sys.path.insert(0, str(FACE))
    import face
    import ict
    return face, ict


def loaded(path):
    """The glb's one mesh: its points, triangles, UVs and base colour texture (rows top down, 0 to 1)."""
    scene = trimesh.load(path)
    geometry = list(scene.geometry.values())
    if len(geometry) != 1:
        raise ValueError(f"{path} holds {len(geometry)} meshes; a generated head is one")
    mesh = geometry[0]
    texture = np.asarray(mesh.visual.material.baseColorTexture.convert("RGB"), np.float64) / 255.0
    return np.asarray(mesh.vertices, np.float64), np.asarray(mesh.faces), np.asarray(mesh.visual.uv), texture


def barycentric(trio, grid_x, grid_y):
    """Each grid point's barycentric weights (... x 3) in the 2D triangle `trio` (3 x 2); all -1 for a flat one."""
    (ax, ay), (bx, by), (cx, cy) = trio
    area = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(area) < 1e-18:
        return np.full(grid_x.shape + (3,), -1.0)
    first = ((by - cy) * (grid_x - cx) + (cx - bx) * (grid_y - cy)) / area
    second = ((cy - ay) * (grid_x - cx) + (ax - cx) * (grid_y - cy)) / area
    return np.stack([first, second, 1.0 - first - second], axis=-1)


def raster(points, triangles, uv, box, step):
    """The model seen from the front (along -z) in the box (x0, x1, y0, y1) at `step` a pixel, rows going up: per
    pixel the front-most depth (z, -inf where nothing) and its UV."""
    x0, x1, y0, y1 = box
    width, height = int(np.ceil((x1 - x0) / step)), int(np.ceil((y1 - y0) / step))
    depth = np.full((height, width), -np.inf)
    texel = np.zeros((height, width, 2))
    corners = points[triangles]
    inside = ((corners[:, :, 0].max(1) >= x0) & (corners[:, :, 0].min(1) <= x1) & (corners[:, :, 1].max(1) >= y0)
              & (corners[:, :, 1].min(1) <= y1))
    for row in np.flatnonzero(inside):
        trio = corners[row]
        cols = np.arange(max(0, int(np.floor((trio[:, 0].min() - x0) / step))),
                         min(width, int(np.ceil((trio[:, 0].max() - x0) / step)) + 1))
        rows = np.arange(max(0, int(np.floor((trio[:, 1].min() - y0) / step))),
                         min(height, int(np.ceil((trio[:, 1].max() - y0) / step)) + 1))
        if not len(cols) or not len(rows):
            continue
        grid_x, grid_y = np.meshgrid(x0 + (cols + 0.5) * step, y0 + (rows + 0.5) * step)
        weights = barycentric(trio[:, :2], grid_x, grid_y)
        hit = (weights >= -1e-9).all(axis=-1)
        if not hit.any():
            continue
        z = weights[hit] @ trio[:, 2]
        pick_rows, pick_cols = np.nonzero(hit)
        image_rows, image_cols = rows[pick_rows], cols[pick_cols]
        closer = z > depth[image_rows, image_cols]
        depth[image_rows[closer], image_cols[closer]] = z[closer]
        texel[image_rows[closer], image_cols[closer]] = weights[hit][closer] @ uv[triangles[row]]
    return depth, texel


def painted(texture, texel):
    """The texture's colour at each pixel's UV (glTF's UV: v up from the picture's bottom)."""
    height, width = texture.shape[:2]
    cols = np.clip(np.round(texel[..., 0] * (width - 1)).astype(int), 0, width - 1)
    rows = np.clip(np.round((1.0 - texel[..., 1]) * (height - 1)).astype(int), 0, height - 1)
    return texture[rows, cols]


def luminance(colour):
    """Rec. 709 luminance of colours (... x 3)."""
    return colour @ np.array([0.2126, 0.7152, 0.0722])


def front_view(points, triangles, uv, texture):
    """The face seen from the front round its top (WINDOW_M): {depth, colour, xs, ys} (rows going up)."""
    top = points[:, 1].max()
    box = (-WINDOW_M["half_width"], WINDOW_M["half_width"], top - WINDOW_M["under_top"], top - WINDOW_M["over_top"])
    depth, texel = raster(points, triangles, uv, box, STEP_M)
    colour = painted(texture, texel)
    colour[~np.isfinite(depth)] = 0.0
    xs = box[0] + (np.arange(depth.shape[1]) + 0.5) * STEP_M
    ys = box[2] + (np.arange(depth.shape[0]) + 0.5) * STEP_M
    return {"depth": depth, "colour": colour, "xs": xs, "ys": ys}


def nose_tip(view):
    """The nose tip's (x, y, z): the front-most point within NOSE's half width of the middle, in the view's low part."""
    across, up = np.meshgrid(view["xs"], view["ys"])
    low = up < view["ys"][0] + NOSE["low_share"] * (view["ys"][-1] - view["ys"][0])
    held = np.where(np.isfinite(view["depth"]) & (np.abs(across) < NOSE["half_width"]) & low, view["depth"], -np.inf)
    row, col = np.unravel_index(held.argmax(), held.shape)
    return np.array([view["xs"][col], view["ys"][row], held[row, col]])


def dark_blobs(lightness, small, large):
    """How much darker each pixel is smoothed over `small` (pixels) than over `large`: a pupil's dark blob."""
    return ndimage.gaussian_filter(lightness, small) - ndimage.gaussian_filter(lightness, large)


def pupils(view, tip):
    """The painted pupils' (x, y) on the model, the subject's right (-x) first: on each side the darkest blob
    (BLOB_M) within PUPIL_SEARCH_M of the nose tip."""
    across, up = np.meshgrid(view["xs"], view["ys"])
    blobs = dark_blobs(luminance(view["colour"]), BLOB_M[0] / STEP_M, BLOB_M[1] / STEP_M)
    found = []
    for side in (-1.0, 1.0):
        held = (np.isfinite(view["depth"]) & (up > tip[1] + PUPIL_SEARCH_M["over_nose"][0])
                & (up < tip[1] + PUPIL_SEARCH_M["over_nose"][1]) & (side * across > PUPIL_SEARCH_M["out"][0])
                & (side * across < PUPIL_SEARCH_M["out"][1]))
        row, col = np.unravel_index(np.where(held, blobs, np.inf).argmin(), blobs.shape)
        found.append([view["xs"][col], view["ys"][row]])
    return np.array(found)


def depth_at(view, x, y):
    """The view's depth at points (x, y), bilinear (nan off the model)."""
    cols = (np.asarray(x) - view["xs"][0]) / STEP_M
    rows = (np.asarray(y) - view["ys"][0]) / STEP_M
    depth = np.where(np.isfinite(view["depth"]), view["depth"], np.nan)
    return ndimage.map_coordinates(depth, [rows, cols], order=1, cval=np.nan)


def margin_along(depth, scale, floor):
    """The index of the lid margin along one ray's depths (from the pupil out), or None: the top (where the slope falls
    under RIM_FLAT) of the first rise of RIM_RISE_M within RIM_RUN_M (a curved floor rises too, but slowly) that stands
    RIM_OVER_FLOOR_M over the pupil's `floor` (a bump in the painted floor does not)."""
    run = max(1, int(round(RIM_RUN_M * scale / STEP_M)))
    lowest = ndimage.minimum_filter1d(np.nan_to_num(depth, nan=np.inf), run + 1, origin=run // 2, mode="nearest")
    risen = np.flatnonzero(depth - lowest >= RIM_RISE_M * scale)
    slope = np.gradient(depth, STEP_M)
    for start in risen[np.r_[True, np.diff(risen) > 1]] if len(risen) else []:
        flat = np.flatnonzero((slope < RIM_FLAT) & (np.arange(len(slope)) > start))
        top = flat[0] if len(flat) else len(slope) - 1
        if depth[top] - floor >= RIM_OVER_FLOOR_M * scale:
            return int(top)
    return None


def rims(view, pupil, scale):
    """The lid margins round one pupil as (x, y, z, degrees) rows, one for each ray (RAY, scaled by the face's
    `scale`) along which `margin_along` finds one. (A steepness threshold missed an older woman's gentle lower lid,
    and the floor's push took the lid in with it; a bump on a painted floor was taken for a lid, and the floor beyond
    it covered the iris, 2026-11-26.)"""
    found = []
    reach = np.arange(RAY["from"] * scale, RAY["to"] * scale, STEP_M)
    floor = float(depth_at(view, [pupil[0]], [pupil[1]])[0])
    for degrees in RAY["degrees"]:
        way = np.array([np.cos(np.radians(degrees)), np.sin(np.radians(degrees))])
        x, y = pupil[0] + reach * way[0], pupil[1] + reach * way[1]
        depth = depth_at(view, x, y)
        top = margin_along(depth, scale, floor)
        if top is not None:
            found.append([x[top], y[top], depth[top], degrees])
    return consistent(np.array(found).reshape(-1, 4), pupil)


def consistent(margins, pupil):
    """The margins without those standing in far closer to the pupil than both rays beside them (under
    RIM_NEIGHBOUR_SHARE of the nearer's distance): a bump on the floor, not the lid."""
    if len(margins) < 3:
        return margins
    across = np.linalg.norm(margins[:, :2] - pupil, axis=1)
    beside = np.minimum(np.roll(across, 1), np.roll(across, -1))
    return margins[across >= RIM_NEIGHBOUR_SHARE * beside]


def eye_scale(pupil_points):
    """The eye's size over the adult's: the pupils' distance apart over PUPIL_DISTANCE_M, held in EYE_SCALE_LIMITS."""
    return float(np.clip(np.linalg.norm(pupil_points[1] - pupil_points[0]) / PUPIL_DISTANCE_M, *EYE_SCALE_LIMITS))


def eye_depth(pupil, margins, radius):
    """The eyeball's centre depth behind `pupil`: as far forward as its lid margins allow, each RIM_GAP_M in front of
    the ball (a sphere of `radius`), and its cornea's apex (CORNEA_RISE over the sphere) RIM_GAP_M behind the margins'
    mean depth, so the eye sits inside the lids and never bulges past them (sat on its margins alone, the white stood
    out past the generated lids' outer corner, which falls back, 2026-11-26); the margins are those within
    RIM_FROM_VERTICAL_DEGREES of straight up or down and within RIM_WITHIN of the radius out (past it a ray has met the
    brow or the cheek, not a lid)."""
    from_vertical = np.abs(((margins[:, 3] - 90.0 + 90.0) % 180.0) - 90.0)
    across = np.linalg.norm(margins[:, :2] - pupil, axis=1)
    kept = (from_vertical <= RIM_FROM_VERTICAL_DEGREES) & (across < RIM_WITHIN * radius)
    if kept.sum() < 2:
        raise ValueError(f"the eye at {pupil} shows {kept.sum()} lid margins over or under it; at least 2 are needed")
    held, across = margins[kept], across[kept]
    resting = (held[:, 2] - RIM_GAP_M - np.sqrt(radius ** 2 - across ** 2)).min()
    behind_rim = held[:, 2].mean() - RIM_GAP_M - radius * (1.0 + CORNEA_RISE)
    return float(min(resting, behind_rim))


def rotation_onto(start, end):
    """The rotation matrix turning unit vector `start` onto unit vector `end` (Rodrigues)."""
    axis = np.cross(start, end)
    sine, cosine = np.linalg.norm(axis), float(start @ end)
    if sine < 1e-12:
        return np.eye(3) if cosine > 0 else -np.eye(3)
    axis /= sine
    cross = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + sine * cross + (1 - cosine) * cross @ cross


def ict_eye(model, side):
    """One of ICT-FaceKit's eyeballs ("left" or "right", the subject's) with its finishes: {points (cm, ICT's frame),
    triangles, uv, finish, centre, axis, radius}; the centre, gaze axis and radius as the face's cornea reads them."""
    face, ict = face_modules()
    triangles, rows = face.model_triangles(model, [f"eyeball_{side}"])
    uv = model["uvs"][model["corners"][rows]]
    points, triangles, _ = face.compact(model["neutral"], triangles, np.zeros((0, len(model["neutral"]), 3)))
    out = np.linalg.norm(face.corner_values(triangles, uv, len(points)) - 0.5, axis=1)
    centre = points.mean(axis=0)
    offset = points - centre
    axis = offset[out < face.PUPIL_UV / 2].mean(axis=0)
    radius = float(np.median(np.linalg.norm(offset[(out > face.IRIS_UV * 1.3) & (out < 0.25)], axis=1)))
    return {"points": points, "triangles": triangles, "uv": uv, "finish": face.eye_finish(uv), "centre": centre,
            "axis": axis / np.linalg.norm(axis), "radius": radius}


def placed(eye, centre, gaze, radius):
    """The ICT eye moved so its centre is `centre`, its axis along unit `gaze` and its radius `radius` (metres)."""
    turn = rotation_onto(eye["axis"], gaze)
    points = (eye["points"] - eye["centre"]) * (radius / eye["radius"]) @ turn.T + centre
    return {"points": points, "triangles": eye["triangles"], "uv": eye["uv"], "finish": eye["finish"]}


def joined(pieces):
    """Pieces of the same fields joined into one (their triangles renumbered)."""
    offsets = np.cumsum([0] + [len(piece["points"]) for piece in pieces[:-1]])
    return {"points": np.vstack([piece["points"] for piece in pieces]),
            "triangles": np.vstack([piece["triangles"] + offset for piece, offset in zip(pieces, offsets)]),
            "uv": np.vstack([piece["uv"] for piece in pieces]),
            "finish": np.concatenate([piece["finish"] for piece in pieces])}


def opening(margins, pupil):
    """One lid opening's edge as a function of the angle round the pupil: (radius, depth) arrays for `degrees`,
    interpolated round the circle between the rays that found a margin (OPENING_RAYS at least)."""
    if len(margins) < OPENING_RAYS:
        raise ValueError(f"the eye at {pupil} shows {len(margins)} lid margins round it; {OPENING_RAYS} are needed")
    order = np.argsort(margins[:, 3])
    angles = margins[order, 3]
    across = np.linalg.norm(margins[order, :2] - pupil, axis=1)
    depths = margins[order, 2]

    def edge(degrees):
        wrapped = np.asarray(degrees) % 360.0
        return (np.interp(wrapped, angles, across, period=360.0), np.interp(wrapped, angles, depths, period=360.0))

    return edge


def in_opening(points, pupil, edge):
    """For each point: its distance out from the pupil over the lid opening's edge on its side (under 1 inside the
    opening, seen from the front) and that edge's depth (its margin's)."""
    offset = points[:, :2] - pupil
    radius, depth = edge(np.degrees(np.arctan2(offset[:, 1], offset[:, 0])))
    return np.linalg.norm(offset, axis=1) / radius, depth


def chroma(colour):
    """Colours (... x 3) by their share of each channel: their hue and saturation without their brightness (the paint's
    baked shade)."""
    return colour / np.maximum(colour.sum(axis=-1, keepdims=True), 1e-6)


def skin_tone(points, paint, pupils_at):
    """The face's skin chroma: the median of the paint on the cheeks under the eyes (SKIN_RING_M out from each pupil,
    below it)."""
    held = np.zeros(len(points), bool)
    for pupil in pupils_at:
        offset = points[:, :2] - pupil
        out = np.linalg.norm(offset, axis=1)
        held |= (out > SKIN_RING_M[0]) & (out < SKIN_RING_M[1]) & (offset[:, 1] < -0.7 * out)
    return np.median(chroma(paint[held]), axis=0)


def pushed(points, paint, pupils_at, edges, centres, radius):
    """The model's points with the painted eye's floor pushed back. The floor is what lies inside a lid opening more
    than LID_EDGE_M behind its margin, or, painted as an eye and not as skin (its chroma more than SKIN_CHROMA off the
    cheeks'), inside the opening's core (OPENING_CORE of the way to its edge) in front of the eyeball (a shallow
    socket's paint covered the iris, 2026-11-26); it moves straight back to just inside the eyeball's front (hidden
    behind it), or beside the ball to its middle's depth (the socket's shade). The lids' skin and the lid edge stay."""
    moved = points.copy()
    eye_paint = np.linalg.norm(chroma(paint) - skin_tone(points, paint, pupils_at), axis=1) > SKIN_CHROMA
    for pupil, edge, centre in zip(pupils_at, edges, centres):
        out, rim_depth = in_opening(points, pupil, edge)
        across = np.linalg.norm(points[:, :2] - centre[:2], axis=1)
        ball_front = centre[2] + np.sqrt(np.clip(radius ** 2 - across ** 2, 0.0, None))
        covering = (out < OPENING_CORE) & eye_paint & (points[:, 2] > ball_front - BURIED_M)
        floor = (out < 1.0) & ((points[:, 2] < rim_depth - LID_EDGE_M) | covering)
        target = np.where(across < radius, ball_front - 2.0 * BURIED_M, centre[2])
        moved[floor, 2] = np.minimum(points[floor, 2], target[floor])
    return moved


def ball_gap(points, centres, radius):
    """Each point's distance off the nearer eyeball's sphere (negative inside it)."""
    return np.min([np.linalg.norm(points - centre, axis=1) - radius for centre in centres], axis=0)


def buried(points, triangles, centres, radius):
    """The model's triangles inside an eyeball (every corner BURIED_M inside its sphere): the painted eye's floor."""
    inside = ball_gap(points, centres, radius) < -BURIED_M
    return np.flatnonzero(inside[triangles].all(axis=1))


def wet_strip(points, triangles, pupils_at, edges):
    """The lid's wet line: the model's triangles on the inside of each lid's rim (their centres inside the opening, from
    WET_FROM_M to LID_EDGE_M behind its margin), copied TEAR_FILM_LIFT_M out along their corners' normals, as a
    piece."""
    centroids = points[triangles].mean(axis=1)
    band = np.zeros(len(triangles), bool)
    for pupil, edge in zip(pupils_at, edges):
        out, rim_depth = in_opening(centroids, pupil, edge)
        band |= (out < 1.0) & (centroids[:, 2] <= rim_depth - WET_FROM_M) & (centroids[:, 2] >= rim_depth - LID_EDGE_M)
    held = triangles[band]
    if not len(held):
        return {"points": np.zeros((0, 3)), "triangles": np.zeros((0, 3), np.int64)}
    normals = trimesh.Trimesh(points, held, process=False).vertex_normals
    used, renumbered = np.unique(held, return_inverse=True)
    return {"points": points[used] + normals[used] * TEAR_FILM_LIFT_M, "triangles": renumbered.reshape(held.shape)}


def photo_pupils(photo):
    """The photo's pupils as (column, row) pixels, the picture's left first: on each half the darkest blob in the
    eyes' band (PHOTO)."""
    lightness = luminance(photo)
    height, width = lightness.shape
    blobs = dark_blobs(lightness, PHOTO["blob"][0] * width, PHOTO["blob"][1] * width)
    top, bottom = int(PHOTO["rows"][0] * height), int(PHOTO["rows"][1] * height)
    found = []
    for left, right in PHOTO["halves"]:
        band = blobs[top:bottom, int(left * width):int(right * width)]
        row, col = np.unravel_index(band.argmin(), band.shape)
        found.append((col + int(left * width), row + top))
    return np.array(found, np.float64)


def srgb_to_linear(colour):
    """sRGB colours (0 to 1) as linear ones."""
    colour = np.asarray(colour, np.float64)
    return np.where(colour <= 0.04045, colour / 12.92, ((colour + 0.055) / 1.055) ** 2.4)


def iris_centre(lightness, guess, radius):
    """The iris's centre near `guess` (column, row): where a disc of `radius` is darkest against the ring round it
    (out to IRIS_SURROUND of the radius), highlights clipped at the window's IRIS_CLIP quantile."""
    column, row = np.round(guess).astype(int)
    reach = int(np.ceil(radius * (IRIS_SURROUND + 1.0)))
    window = lightness[row - reach:row + reach + 1, column - reach:column + reach + 1]
    window = np.minimum(window, np.quantile(window, IRIS_CLIP))
    offsets = np.arange(-reach, reach + 1)
    distance = np.hypot(*np.meshgrid(offsets, offsets))
    disc = (distance <= radius).astype(np.float64)
    surround = ((distance > radius) & (distance <= IRIS_SURROUND * radius)).astype(np.float64)
    contrast = (ndimage.correlate(window, surround / surround.sum(), mode="nearest")
                - ndimage.correlate(window, disc / disc.sum(), mode="nearest"))
    middle = distance <= radius  # the centre is looked for within one radius of the guess
    found_row, found_col = np.unravel_index(np.where(middle, contrast, -np.inf).argmax(), contrast.shape)
    return np.array([column + offsets[found_col], row + offsets[found_row]], np.float64)


def photo_iris(photo):
    """The iris's linear colour read off the photo: each iris found round its pupil (`iris_centre`, its radius from
    the pupils' distance apart in pixels over PUPIL_DISTANCE_M), then the median of both irises' ring (IRIS_RING of
    the radius) under the upper lid's shade (the ring's top IRIS_LID_DEGREES dropped), its darkest and brightest
    pixels (lashes, the pupil's edge, the window's highlight) dropped by IRIS_KEEP."""
    guesses = photo_pupils(photo)
    radius = np.linalg.norm(guesses[1] - guesses[0]) * IRIS_DIAMETER_M / 2.0 / PUPIL_DISTANCE_M
    lightness = luminance(photo)
    centres = np.array([iris_centre(lightness, guess, radius) for guess in guesses])
    rows, cols = np.mgrid[:photo.shape[0], :photo.shape[1]]
    ring = np.zeros(photo.shape[:2], bool)
    for col, row in centres:
        out = np.hypot(cols - col, rows - row) / radius
        upward = np.degrees(np.arctan2(row - rows, cols - col))
        under_lid = np.abs(upward - 90.0) < IRIS_LID_DEGREES / 2.0
        ring |= (out > IRIS_RING[0]) & (out < IRIS_RING[1]) & ~under_lid
    pixels = photo[ring]
    order = np.argsort(luminance(pixels))
    kept = pixels[order[int(IRIS_KEEP[0] * len(order)):int(IRIS_KEEP[1] * len(order))]]
    return srgb_to_linear(np.median(kept, axis=0)), centres, radius


def unrolled(photo_linear, centre, radius):
    """The photo's iris round `centre` (column, row) out to `radius` pixels on a polar grid (IRIS_PICTURE's rings out
    by rays anticlockwise from the picture's right, up being up): (colours rings x rays x 3, columns, rows)."""
    out = (np.arange(IRIS_PICTURE["rings"]) + 0.5) / IRIS_PICTURE["rings"]
    angle = np.radians(np.arange(IRIS_PICTURE["rays"]) * 360.0 / IRIS_PICTURE["rays"])
    out, angle = np.meshgrid(out, angle, indexing="ij")
    columns = centre[0] + out * radius * np.cos(angle)
    rows = centre[1] - out * radius * np.sin(angle)
    colours = np.stack([ndimage.map_coordinates(photo_linear[..., channel], [rows, columns], order=1, mode="nearest")
                        for channel in range(3)], axis=-1)
    return colours, columns, rows


def iris_found(lightness, eye):
    """The photo's iris (centre (column, row), radius pixels) from marks.py's: MediaPipe's circle runs wide (laid on
    the photos, 2026-11-26, about IRIS_PICTURE's `radius` of it is the iris) and its centre off by a few pixels, so
    the centre is the pupil's, where a disc of IRIS_PICTURE's `pupil_guess` of the radius is darkest against its ring
    (`iris_centre`)."""
    radius = IRIS_PICTURE["radius"] * float(eye["iris_radius"])
    centre = iris_centre(lightness, np.asarray(eye["iris_centre"], np.float64), IRIS_PICTURE["pupil_guess"] * radius)
    return centre, radius


def lid_covered(eye, columns, rows, radius):
    """Which polar samples (at photo `columns`, `rows`) lie over the eye's upper margin or under its lower one, or
    within IRIS_PICTURE's `lid` of the radius of them (the lid's shade, its lashes)."""
    reach = IRIS_PICTURE["lid"] * radius
    covered = np.zeros(columns.shape, bool)
    for key, sign in (("upper", 1.0), ("lower", -1.0)):
        line = np.asarray(eye[key], np.float64)
        line = line[np.argsort(line[:, 0])]
        margin = np.interp(columns, line[:, 0], line[:, 1])
        covered |= sign * (margin + sign * reach - rows) > 0.0
    return covered


def catchlights(colours, kept):
    """Which polar samples are reflections: brighter than the iris's body (the median of its `kept` samples 0.55 to
    0.8 of its radius out) by IRIS_PICTURE's `catchlight`, grown by its `grow` samples (the reflection's soft rim). (A
    ring's own median, dark by the pupil, took the iris round the pupil's edge for a reflection and the pupil read
    large.)"""
    lightness = luminance(colours)
    rings = len(lightness)
    body = kept[int(0.55 * rings):int(0.8 * rings)]
    bright = lightness > IRIS_PICTURE["catchlight"] * np.median(lightness[int(0.55 * rings):int(0.8 * rings)][body])
    grown = bright.copy()
    for _ in range(IRIS_PICTURE["grow"]):
        grown = ndimage.binary_dilation(grown, border_value=0) | np.roll(grown, 1, 1) | np.roll(grown, -1, 1)
    return grown


def ring_medians(colours, kept):
    """Each polar ring's median colour over its `kept` samples (the whole iris's where a ring keeps three or fewer)."""
    whole = np.median(colours[kept], axis=0)
    return np.array([np.median(ring[held], axis=0) if held.sum() > 3 else whole for ring, held in zip(colours, kept)])


def filled_iris(eye):
    """One eye's polar iris ({colours, kept}) made whole: each ring its median colour (`ring_medians`, so the iris's
    own rings, the collarette and the limbus, stay) times the samples' own brightness over it (the fibres and crypts),
    a lost sample's brightness taken from the ring turned by the first of IRIS_PICTURE's `turns` that keeps it (a
    brightness ratio, so a turned piece shows no seam), clipped to its `detail` range."""
    colours, kept = eye["colours"], eye["kept"]
    base = ring_medians(colours, kept)
    ratio = luminance(colours) / np.maximum(luminance(base), 1e-6)[:, None]
    filled, held = ratio.copy(), kept.copy()
    rays = colours.shape[1]
    for turn in IRIS_PICTURE["turns"]:
        shift = int(round(turn * rays / 360.0))
        taken = ~held & np.roll(kept, shift, axis=1)
        filled[taken] = np.roll(ratio, shift, axis=1)[taken]
        held |= taken
    filled[~held] = 1.0
    return base[:, None, :] * np.clip(filled, *IRIS_PICTURE["detail"])[..., None]


def pupil_share(colours, kept):
    """The pupil's radius over the iris's: where the rings' median brightness (over their `kept` samples) has risen
    IRIS_PICTURE's `pupil_rise` of the way from the darkest inner ring to the iris's (its rings 0.55 to 0.8 out)."""
    lightness = luminance(colours)
    profile = np.array([np.median(ring[held]) if held.any() else np.nan for ring, held in zip(lightness, kept)])
    profile = np.interp(np.arange(len(profile)), np.flatnonzero(np.isfinite(profile)), profile[np.isfinite(profile)])
    rings = len(profile)
    inner = profile[:rings // 4].min()
    iris = np.median(profile[int(0.55 * rings):int(0.8 * rings)])
    risen = np.flatnonzero((profile > inner + IRIS_PICTURE["pupil_rise"] * (iris - inner))
                           & (np.arange(rings) > np.argmin(profile[:rings // 4])))
    return float(np.clip((risen[0] + 0.5) / rings if len(risen) else 0.4, 0.15, 0.6))


def iris_picture(photo, marks, sclera, iris_uv):
    """The photo's iris unrolled onto the eyeball's UV (linear, IRIS_PICTURE's `size` square, rows top down; the iris
    the disc `iris_uv` round the UV's middle, `sclera` outside it): each of the photo's irises (marks.py's centre and
    radius refined, `iris_found`) unrolled, its lid-covered samples and catchlights lost, the one keeping more made
    whole (`filled_iris`); the pupil set dark at the photo's own share (`pupil_share`) and the limbal ring darkened.
    With {pupil_share, kept_share}."""
    photo_linear = srgb_to_linear(photo)
    lightness = luminance(photo)
    found = []
    for eye in marks["eyes"]:
        centre, radius = iris_found(lightness, eye)
        colours, columns, rows = unrolled(photo_linear, centre, radius)
        kept = ~lid_covered(eye, columns, rows, radius)
        kept &= ~catchlights(colours, kept)
        found.append({"colours": colours, "kept": kept})
    found.sort(key=lambda eye: -eye["kept"].mean())
    polar = filled_iris(found[0])
    share = pupil_share(found[0]["colours"], found[0]["kept"])
    size = IRIS_PICTURE["size"]
    texel = (np.arange(size) + 0.5) / size
    across, up = np.meshgrid(texel - 0.5, 0.5 - texel)
    out = np.hypot(across, up) / iris_uv
    ray = (np.degrees(np.arctan2(up, across)) % 360.0) * IRIS_PICTURE["rays"] / 360.0
    ring = np.clip(out * IRIS_PICTURE["rings"] - 0.5, 0.0, IRIS_PICTURE["rings"] - 1.0)
    wrapped = np.concatenate([polar, polar[:, :1]], axis=1)
    colour = np.stack([ndimage.map_coordinates(wrapped[..., channel], [ring, ray], order=1, mode="nearest")
                       for channel in range(3)], axis=-1)
    edge = 1.0 - IRIS_PICTURE["limbus"]
    colour *= (1.0 - edge * np.clip((out - IRIS_PICTURE["limbus_from"]) / (1.0 - IRIS_PICTURE["limbus_from"]), 0, 1)
               ** 2)[..., None]
    dark = np.clip((share + 0.03 - out) / 0.06, 0.0, 1.0)[..., None]
    colour = colour * (1.0 - dark) + IRIS_PICTURE["pupil_linear"] * dark
    white = np.clip((out - 1.0) / 0.04, 0.0, 1.0)[..., None]
    colour = colour * (1.0 - white) + np.asarray(sclera, np.float64) * white
    return colour, {"pupil_share": round(share, 3), "kept_share": round(float(found[0]["kept"].mean()), 3)}


def cornea_of(eyes):
    """The face module's cornea and tear film shell over the joined eyes (finish 0 the cornea, 1 the film)."""
    face, _ = face_modules()
    shell = face.cornea({**eyes, "shapes": np.zeros((0, len(eyes["points"]), 3))})
    return {"points": shell["points"], "triangles": shell["triangles"], "finish": shell["finish"]}


def made(points, triangles, uv, texture, photo, sources):
    """The eyes made for one model (in metres, the model's frame) from the source eyes (`ict_eye`'s, {"right", "left"},
    the subject's): {eyes, cornea, wet, moved_from and moved_to (the floor's pushed points), removed (the removed
    triangles' centres, as pushed), painted_pupils, iris, cornea_apex, stats}."""
    view = front_view(points, triangles, uv, texture)
    tip = nose_tip(view)
    pupil_points = pupils(view, tip)
    scale = eye_scale(pupil_points)
    radius = EYE_DIAMETER_M / 2.0 * scale
    margins = [rims(view, pupil, scale) for pupil in pupil_points]
    centres = np.array([[*pupil, eye_depth(pupil, rim, radius) + EYE_FORWARD_M]
                        for pupil, rim in zip(pupil_points, margins)])
    target = np.array([centres[:, 0].mean(), centres[:, 1].mean(), centres[:, 2].max() + GAZE_M])
    gazes = [(target - centre) / np.linalg.norm(target - centre) for centre in centres]
    eyes = joined([placed(sources[side], centre, gaze, radius)
                   for side, centre, gaze in zip(("right", "left"), centres, gazes)])
    colour, photo_centres, _ = photo_iris(photo)
    edges = [opening(rim, pupil) for rim, pupil in zip(margins, pupil_points)]
    moved = pushed(points, painted(texture, uv), pupil_points, edges, centres, radius)
    removed = buried(moved, triangles, centres, radius)
    shifted = np.flatnonzero(np.any(moved != points, axis=1))
    stats = {"pupils_m": pupil_points.round(5).tolist(), "nose_tip_m": tip.round(5).tolist(),
             "eye_diameter_mm": round(2000 * radius, 2), "eye_centres_m": centres.round(5).tolist(),
             "lid_margins": [len(rim) for rim in margins], "pushed_points": int(len(shifted)),
             "removed_triangles": int(len(removed)), "iris_linear": colour.round(4).tolist(),
             "photo_pupils_px": photo_centres.round(1).tolist()}
    painted_pupils = np.column_stack([pupil_points, depth_at(view, pupil_points[:, 0], pupil_points[:, 1])])
    return {"eyes": eyes, "cornea": cornea_of(eyes), "moved_from": points[shifted], "moved_to": moved[shifted],
            "removed": moved[triangles[removed]].mean(axis=1), "painted_pupils": painted_pupils,
            "wet": wet_strip(moved, np.delete(triangles, removed, axis=0), pupil_points, edges),
            "iris": colour, "cornea_apex": centres + np.array(gazes) * radius * (1.0 + CORNEA_RISE), "stats": stats}


def written(result, scale, out):
    """The made eyes written in the model's own units (metres over `scale`) to <out>/eyes.npz and stats.json."""
    arrays = {"removed": result["removed"] / scale, "moved_from": result["moved_from"] / scale,
              "moved_to": result["moved_to"] / scale, "iris": result["iris"], "scale": np.array(scale),
              "cornea_apex": result["cornea_apex"] / scale, "painted_pupils": result["painted_pupils"] / scale}
    for name in ("eyes", "cornea", "wet"):
        for field, values in result[name].items():
            arrays[f"{name}.{field}"] = values / scale if field == "points" else values
    np.savez_compressed(out / "eyes.npz", **arrays)
    (out / "stats.json").write_text(json.dumps(result["stats"], indent=1))
    return out / "eyes.npz"


def arguments():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("model", type=pathlib.Path)
    parser.add_argument("photo", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--height", type=float, required=True, help="the model's height in metres as drawn")
    return parser.parse_args()


def main():
    options = arguments()
    points, triangles, uv, texture = loaded(options.model)
    scale = options.height / float(np.ptp(points[:, 1]))
    photo = np.asarray(Image.open(options.photo).convert("RGB"), np.float64) / 255.0
    _, ict = face_modules()
    model = ict.load()
    sources = {side: ict_eye(model, side) for side in ("right", "left")}
    result = made(points * scale, triangles, uv, texture, photo, sources)
    options.out.mkdir(parents=True, exist_ok=True)
    path = written(result, scale, options.out)
    stats = result["stats"]
    print(f"eyes: {path}, {stats['eye_diameter_mm']} mm balls, {stats['removed_triangles']} painted triangles "
          f"removed, {len(result['wet']['triangles'])} wet-line triangles, iris {stats['iris_linear']}")


if __name__ == "__main__":
    main()
