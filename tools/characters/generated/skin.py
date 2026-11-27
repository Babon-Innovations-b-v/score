"""A generated head's face re-painted from its close-up photo (#223): TRELLIS.2's 2K paint is a blurred copy of the
photo spread over the whole head, the face a small part of it, so the skin reads waxy and smooth. The face gets its own
4K texture, the photo seen from the front, laid on the head by a planar UV over the face's box.

    python -m tools.characters.generated.skin <model.glb> <close-up photo> <eyes.npz> <out folder> --height <m>

Steps:
1. `front_grid`: the model seen from the front (along -z, the model's own frame scaled to `--height` metres) over the
   face's box (`face_box`, round the nose tip): per pixel its front-most depth, its paint and its slope.
2. `registered`: where each front pixel lies in the photo. Started from the pupils (the model's painted pupils,
   `eyes.pupils`, onto the photo's irises, `eyes.photo_iris`: a similarity), then refined in ROUNDS by matching the
   paint's detail (each smoothed to the paint's own blur, its broad tone taken off, `detail`) to the photo's, a PATCH_M
   patch round each node of a CONTROL x CONTROL grid (`node_shifts`): an affine plus a smooth displacement.
3. `face_texture`: the photo resampled onto the box at TEXTURE pixels, its light taken off as far as reasonable: the
   broad shading fitted per channel to the front's slope and the model's own `occlusion` (`shading`, first-order in
   the normal and the occlusion over the skin: the render makes a hollow's shade and its warm bounce again) divided
   out, and the
   highlights pressed down (`gloss_free`: brightness over the matte skin round them, `matte_skin`, past a pore's own
   scaled down, their colour moved to the matte skin's); then toned towards the model's own paint over BLEND_SIGMA_M
   where it fades into it, so the two meet with no step. Its alpha is the photo's share (`grid_share`): the photo's
   face (`face_mask`: its skin in one piece, its holes, brows, eyes and lips, filled, its head `hair` and lid openings,
   `eye_openings`, left out), never the model's painted head hair (`model_hair_free`), how squarely the point faces
   the camera (FACING) and how far from the eye's opening (EYE_CLEAR_M of the painted eye's floor `eyes.py` pushes
   back), rising over EDGE_FEATHER_M from its outer edge and smoothed so the edge is soft.
4. `point_shares` / `visible`: which model points are the front the photo saw (VISIBLE_M); `skin_triangles`: which
   triangles are painted skin (the rest keeps the model's own material); `tzone`: the oily T-zone (the forehead's
   middle, the nose, the chin), for the skin's `sheen` region.

5. `paint_toned`: the model's own paint on the skin's triangles given the photo skin's colour statistics (PAINT_TONE),
   so where the photo fades or does not reach the paint is the photo's skin, not TRELLIS.2's warm dark paint.

Writes <out>/face.png (TEXTURE square, sRGB, its alpha the photo's share), <out>/paint.png (the toned paint, sRGB),
<out>/skin.npz (the box in the model's own units, every model point with whether it is the front the photo saw and
its T-zone, the middles of the painted skin's triangles) and <out>/stats.json; prints one line. `blender_skin.py`
lays it.
"""
import argparse
import json
import pathlib

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage.color import lab2rgb, rgb2lab

from tools.characters.generated import eyes, labels

STEP_M = 0.0005  # the front grid's pixel for registering and the shading
TEXTURE = 4096  # the face texture's side
BOX_M = {"half_width": 0.105, "under_tip": 0.11, "over_tip": 0.12}  # the face's box round the nose tip
PAINT_BLUR_M = 0.0012  # the model's paint is the photo blurred about this much: the photo is blurred so before matching
DETAIL_SIGMA_M = 0.006  # the broad tone over this taken off both before matching
CONTROL = 9  # the displacement's control grid over the box
PATCH_M = 0.03  # each control node's patch matched this wide
PATCH_HELD = 0.4  # a patch is matched when at least this share of it is face looking forward
PATCH_SURE = 0.3  # and kept when its best correlation is at least this
ROUNDS = (0.006, 0.003, 0.0015, 0.0015)  # each round's search reach (m)
SMOOTH_NODES = 0.7  # the displacement smoothed over this many nodes
REGISTER_FACING = 0.5  # registered only where the face looks at least this squarely forward
# a point's share rises from the first to the second (the normal's forward part; round 2, 2026-11-26: from 0.25 to 0.6
# it left the nose's sides, the lids' creases and the temples to the paint, orange under the skin light)
FACING = (0.1, 0.35)
VISIBLE_M = 0.0015  # a point wears the photo when it is within this of the front-most surface over it, more on a slope:
VISIBLE_SLOPE = 1.5  # this many front pixels times the slope (a steep brow's points missed it, half of them paint)
VISIBLE_MAX_M = 0.004
EYE_CLEAR_M = (0.0008, 0.0025)  # the photo fades in from the first to the second away from the painted eye's floor
SHARE_SIGMA_M = 0.001  # the share smoothed over this, so its edge is soft
MASK_ERODE_M = 0.002  # the photo's face mask pulled this far in from hair and background
SHADING_SIGMA_M = 0.004  # the shading fitted to the photo's brightness smoothed over this
# a fitted shading outside this is clipped (a crease's shade is the skin's own; down to 0.4 since the model's own
# occlusion is fitted: the photo's dark sockets are the render's to make, round 3, 2026-11-27)
SHADING_RANGE = (0.4, 1.25)
# the model's own occlusion of the sky (`occlusion`): over `directions`, the highest rise within `reach_m` in `samples`
OCCLUSION = {"reach_m": 0.015, "directions": 12, "samples": 10}
HAIR_GROW_M = 0.002  # the photo's hair (not skin, reaching the picture's edge) grown this far out of the face mask
HAIR_SIDE_M = 0.04  # head hair is over the pupils' line or this far beside their middle (a beard's middle is not)
EYE_GROW_M = 0.0015  # the photo's lid openings (marks.json's margins) grown this far out of the face mask
EDGE_FEATHER_M = 0.006  # the photo's share rises over this from its outer edge (its holes keep their own edges)
# the highlights: brighter than the matte skin (the brightness's lower `percentile` within `matte_m`) by more than
# `kept`, the rest of the excess pressed to `left` of it and its colour moved to the matte skin's over `recolour`
GLOSS = {"matte_m": 0.006, "percentile": 35, "kept": 0.05, "left": 0.25, "recolour": 0.1}
# the matte skin is read over plain skin only: a pixel darker than `dark` of the skin's brightness over `matte_m` (a
# brow, the lashes, a lid's crease) is filled from the plain skin round it (the whole person's round 3, 2026-11-27: read over the brows,
# lashes and eye openings too, the matte in the socket fell under the skin there, the socket band counted as a 31%
# highlight and was pressed 19% darker and recoloured, the brown band round the eyes)
MATTE_DARK = 0.7
# The photo's broad shade left in the model's own hollows after the fit (the fit is one line over the whole face, a
# socket's shade is deeper than it): where the model's smoothed `occlusion` rises from the first to the second of
# `shut`, the plain skin's brightness over SHADING_SIGMA_M against its brightness over `broad_m` is divided out too
# (down to SHADING_RANGE's floor): the render makes the hollow's shade again (the whole person's round 3, 2026-11-27: the socket band
# rendered L 44 against the photo's 52, its cheek 74 against 80).
HOLLOW = {"shut": (0.15, 0.35), "broad_m": 0.012}
CLOSE_AIM_M = (0.022, 0.012)  # the cheek and nose close-up aimed this far beside and over the nose tip
BLEND_SIGMA_M = 0.012  # the photo is toned to the paint's broad colour where it fades into the paint
CHECK_SQUARE = 40  # check.png's board of paint and registered photo, squares this many front pixels
# The model's own paint where the photo does not reach: its dark baked shading (a socket's, the nose's sides) lifted
# to its skin's broad tone (over `broad_m`, the paint over `local_m` against it, skin-coloured paint only), by up to
# `gain` times, where it is darker than the broad tone by `dark` (from the first to the second); there the light under
# the surface reaches `under` of the library's (round 1, 2026-11-26: TRELLIS.2's dark socket and nose paint turned
# orange under the random-walk skin light).
PAINT_SHADE = {"local_m": 0.0015, "broad_m": 0.01, "gain": 2.0, "chroma": (0.7, 1.4), "dark": (0.05, 0.3),
               "under": 0.3}
# The model's own paint on the skin the photo does not cover (its sides, ears and neck, a fold's hidden side) given the
# photo's skin colour (round 2, 2026-11-26: TRELLIS.2's warm, dark paint read as rust and orange blotches round the
# eyes, the nose and the temples): in CIELAB, the paint's broad colour (over `broad_m`) moved to the photo skin's mean
# and its spread scaled to the photo's, its detail too (`detail`: never sharper, its baked creases are no pores); the
# photo skin is the flattened photo where its share is over `share` and it is skin-coloured (`labels.skin_like`).
PAINT_TONE = {"broad_m": 0.01, "detail": (0.5, 1.0), "share": 0.8, "grow_px": 3}
TZONE = [  # (centre over the nose tip (x, y) m, radii (x, y) m): the forehead's middle, the nose, the chin
    ((0.0, 0.075), (0.03, 0.022)), ((0.0, 0.022), (0.009, 0.03)), ((0.0, 0.0), (0.012, 0.01)),
    ((0.0, -0.062), (0.018, 0.012))]


def face_box(tip):
    """The face's box (x0, x1, y0, y1) round the nose tip, metres."""
    return (tip[0] - BOX_M["half_width"], tip[0] + BOX_M["half_width"], tip[1] - BOX_M["under_tip"],
            tip[1] + BOX_M["over_tip"])


def front_grid(points, triangles, uv, texture, box, step):
    """The model from the front over `box` at `step`: {depth, colour, xs, ys, facing} (rows going up); facing is the
    surface normal's forward part read off the depth's slope (the model's triangles are wound either way)."""
    depth, texel = eyes.raster(points, triangles, uv, box, step)
    colour = eyes.painted(texture, texel)
    seen = np.isfinite(depth)
    filled = np.where(seen, depth, np.nan)
    slope_y, slope_x = np.gradient(filled, step)
    facing = 1.0 / np.sqrt(1.0 + slope_x ** 2 + slope_y ** 2)
    facing = np.where(np.isfinite(facing), facing, 0.0)
    xs = box[0] + (np.arange(depth.shape[1]) + 0.5) * step
    ys = box[2] + (np.arange(depth.shape[0]) + 0.5) * step
    return {"depth": depth, "colour": colour, "texel": texel, "xs": xs, "ys": ys, "facing": facing, "seen": seen,
            "normal_x": np.nan_to_num(-slope_x * facing), "normal_y": np.nan_to_num(-slope_y * facing)}


def similarity(model_points, photo_points):
    """The 2 x 3 matrix taking model (x, y) to photo (column, row) that carries two model points onto two photo points
    (the photo's rows run down)."""
    model = model_points[:, 0] + 1j * model_points[:, 1]
    photo = photo_points[:, 0] - 1j * photo_points[:, 1]
    turn = (photo[1] - photo[0]) / (model[1] - model[0])
    shift = photo[0] - turn * model[0]
    return np.array([[turn.real, -turn.imag, shift.real], [-turn.imag, -turn.real, -shift.imag]])


def control_field(displacement, extent, grid_x, grid_y):
    """The control grid's displacements (CONTROL x CONTROL x 2, its nodes spread evenly over `extent`, (x0, x1, y0,
    y1)) spread smoothly (cubic) to the model points (grid_x, grid_y)."""
    rows = (grid_y - extent[2]) / (extent[3] - extent[2]) * (CONTROL - 1)
    cols = (grid_x - extent[0]) / (extent[1] - extent[0]) * (CONTROL - 1)
    return np.stack([ndimage.map_coordinates(displacement[..., axis], [rows, cols], order=3, mode="nearest")
                     for axis in range(2)], axis=-1)


def extent_of(grid):
    """The front grid's extent (its first and last pixels' x, then y): where the control nodes stand."""
    return grid["xs"][0], grid["xs"][-1], grid["ys"][0], grid["ys"][-1]


def mapped(warp, xs, ys):
    """Photo (column, row) of every grid point (rows of `ys`, columns of `xs`) under `warp` ({matrix, displacement,
    extent}): the affine plus the field."""
    matrix = warp["matrix"]
    grid_x, grid_y = np.meshgrid(xs, ys)
    field = control_field(warp["displacement"], warp["extent"], grid_x, grid_y)
    column = matrix[0, 0] * grid_x + matrix[0, 1] * grid_y + matrix[0, 2] + field[..., 0]
    row = matrix[1, 0] * grid_x + matrix[1, 1] * grid_y + matrix[1, 2] + field[..., 1]
    return column, row


def sampled(picture, column, row, order=1):
    """A picture's channels (H x W x C) at fractional (column, row)."""
    return np.stack([ndimage.map_coordinates(picture[..., channel], [row, column], order=order, mode="nearest")
                     for channel in range(picture.shape[-1])], axis=-1)


def detail(lab, sigma_pixels):
    """A CIELAB picture's detail for matching: its broad tone (over DETAIL_SIGMA_M) taken off, scaled per channel."""
    fine = lab - np.stack([ndimage.gaussian_filter(lab[..., channel], sigma_pixels) for channel in range(3)], axis=-1)
    return fine / np.array([10.0, 4.0, 4.0])


def photo_detail(photo, pixels_per_m):
    """The photo's matching detail: blurred to the paint's blur, then `detail`."""
    blur = PAINT_BLUR_M * pixels_per_m
    smooth = np.stack([ndimage.gaussian_filter(photo[..., channel], blur) for channel in range(3)], axis=-1)
    return detail(rgb2lab(smooth), DETAIL_SIGMA_M * pixels_per_m)


def peak(scores):
    """The best of a square of scores (its middle no shift) as a shift (rows, columns), refined to a part of a pixel by
    a parabola through the best and its neighbours."""
    reach = scores.shape[0] // 2
    best_row, best_col = np.unravel_index(scores.argmax(), scores.shape)
    shift = np.array([best_row, best_col], np.float64) - reach
    for axis, best in ((0, best_row), (1, best_col)):
        if 0 < best < 2 * reach:
            line = scores[:, best_col] if axis == 0 else scores[best_row, :]
            low, middle, high = line[best - 1], line[best], line[best + 1]
            bend = low - 2.0 * middle + high
            if bend < 0:
                shift[axis] += 0.5 * (low - high) / bend
    return shift


def node_shifts(model_fine, warped_fine, used, reach):
    """Each control node's shift (CONTROL x CONTROL x 2, grid pixels, rows then columns) and whether it was found: the
    PATCH_M patch round the node (where it is face looking forward) correlated with the warped photo's moved by every
    whole shift within `reach`, the best kept (`peak`) where enough of the patch is face (PATCH_HELD) and the match is
    sure (PATCH_SURE). Both details are taken as zero-mean (their broad tone is off)."""
    shape = used.shape
    size = int(PATCH_M / STEP_M)
    weight = used.astype(np.float64)
    node_rows = np.round(np.linspace(0, shape[0] - 1, CONTROL)).astype(int)
    node_cols = np.round(np.linspace(0, shape[1] - 1, CONTROL)).astype(int)
    at = np.ix_(node_rows, node_cols)

    def patch_sum(values):
        return ndimage.uniform_filter(values, size, mode="constant")[at]

    model_power = patch_sum(weight * (model_fine ** 2).sum(-1))
    padded = np.pad(warped_fine, ((reach, reach), (reach, reach), (0, 0)), mode="edge")
    scores = np.zeros((CONTROL, CONTROL, 2 * reach + 1, 2 * reach + 1))
    for row in range(2 * reach + 1):
        for col in range(2 * reach + 1):
            moved = padded[row:row + shape[0], col:col + shape[1]]
            together = patch_sum(weight * (moved * model_fine).sum(-1))
            power = patch_sum(weight * (moved ** 2).sum(-1))
            scores[:, :, row, col] = together / np.sqrt(np.maximum(model_power * power, 1e-18))
    held = patch_sum(weight) >= PATCH_HELD
    shifts = np.zeros((CONTROL, CONTROL, 2))
    found = np.zeros((CONTROL, CONTROL), bool)
    for node_row in range(CONTROL):
        for node_col in range(CONTROL):
            square = scores[node_row, node_col]
            if held[node_row, node_col] and square.max() >= PATCH_SURE:
                shifts[node_row, node_col], found[node_row, node_col] = peak(square), True
    return shifts, found


def filled(shifts, found):
    """Shifts where none was found filled from the found ones (averaged over their neighbours, wider until all are)."""
    result = shifts.copy()
    weight = found.astype(np.float64)
    sigma = 1.0
    while True:
        total = ndimage.gaussian_filter(weight, sigma, mode="nearest")
        spread = np.stack([ndimage.gaussian_filter(shifts[..., axis] * weight, sigma, mode="nearest")
                           for axis in range(2)], -1) / np.maximum(total, 1e-12)[..., None]
        if (total > 1e-6).all():
            result[~found] = spread[~found]
            return result
        sigma *= 2.0


def affine_at(matrix, grid_x, grid_y):
    """The affine's photo (column, row) at model points, stacked on the last axis."""
    return np.stack([matrix[0, 0] * grid_x + matrix[0, 1] * grid_y + matrix[0, 2],
                     matrix[1, 0] * grid_x + matrix[1, 1] * grid_y + matrix[1, 2]], -1)


def registered(view, photo, start):
    """The warp ({matrix: an affine 2 x 3, displacement: CONTROL x CONTROL x 2 photo pixels, extent}) taking the front
    grid onto the
    photo, refined from `start` in ROUNDS: the photo's detail laid on the grid through the current map, each control
    node's patch matched to the paint's detail (`node_shifts`), the nodes' new photo places fitted by an affine and
    the rest, smoothed over the nodes, kept as the displacement. Matched only on the photo's face (`face_mask`): the
    paint's hair is not the photo's."""
    pixels_per_m = float(np.sqrt(abs(np.linalg.det(start[:, :2]))))
    photo_fine = photo_detail(photo, pixels_per_m)
    model_fine = detail(rgb2lab(view["colour"]), DETAIL_SIGMA_M / STEP_M)
    first = {"matrix": start, "displacement": np.zeros((CONTROL, CONTROL, 2)), "extent": extent_of(view)}
    column, row = mapped(first, view["xs"], view["ys"])
    face = ndimage.map_coordinates(face_mask(photo, pixels_per_m), [row, column], order=1, mode="constant") > 0.5
    used = view["seen"] & (view["facing"] > REGISTER_FACING) & face
    used = ndimage.binary_erosion(used, iterations=int(DETAIL_SIGMA_M / STEP_M))
    matrix, displacement = start.copy(), np.zeros((CONTROL, CONTROL, 2))
    grid_x, grid_y = np.meshgrid(np.linspace(view["xs"][0], view["xs"][-1], CONTROL),
                                 np.linspace(view["ys"][0], view["ys"][-1], CONTROL))
    moves = []
    for reach_m in ROUNDS:
        column, row = mapped({"matrix": matrix, "displacement": displacement, "extent": first["extent"]}, view["xs"],
                             view["ys"])
        warped = sampled(photo_fine, column, row)
        shifts, found = node_shifts(model_fine, warped, used, max(1, int(round(reach_m / STEP_M))))
        if not found.any():
            raise ValueError("no patch of the face matched the photo")
        # the warped photo's match `shift` pixels on (rows up, columns): the model point shows the photo of the point
        # that far on
        move = filled(shifts, found)[..., ::-1] * STEP_M
        new = affine_at(matrix, grid_x + move[..., 0], grid_y + move[..., 1]) + displacement
        if found.sum() >= 6:
            design = np.column_stack([grid_x[found], grid_y[found], np.ones(found.sum())])
            fitted, *_ = np.linalg.lstsq(design, new[found], rcond=None)
            matrix = fitted.T
        displacement = ndimage.gaussian_filter(new - affine_at(matrix, grid_x, grid_y), (SMOOTH_NODES, SMOOTH_NODES, 0),
                                               mode="nearest")
        moves.append(round(float(np.median(np.abs(move[found])) * 1000.0), 2))
    used_values = model_fine[used].ravel()

    def agreement(warp):
        column, row = mapped(warp, view["xs"], view["ys"])
        return round(float(np.corrcoef(sampled(photo_fine, column, row)[used].ravel(), used_values)[0, 1]), 3)

    warp = {"matrix": matrix, "displacement": displacement, "extent": first["extent"]}
    return warp, {"detail_correlation_before": agreement(first), "detail_correlation_after": agreement(warp),
                                  "patches_found": int(found.sum()), "median_move_mm": moves,
                                  "displacement_px_max": round(float(np.abs(displacement).max()), 2)}


def linear(picture):
    """sRGB values 0 to 1 as linear."""
    return np.where(picture <= 0.04045, picture / 12.92, ((picture + 0.055) / 1.055) ** 2.4)


def encoded(values):
    """Linear values as sRGB 0 to 1."""
    values = np.clip(values, 0.0, 1.0)
    return np.where(values <= 0.0031308, values * 12.92, 1.055 * values ** (1.0 / 2.4) - 0.055)


def hair_zone(across, up, side):
    """Where head hair can be: over the pupils' line (`up` above it) or farther than `side` beside their middle
    (`across`); a beard's middle and a moustache are not (round 3, 2026-11-27: taken as hair, a bearded man's
    moustache took the skin beside his nose with it)."""
    return (up > 0) | (np.abs(across) > side)


def hair(skin, zone, grow):
    """The hair round a skin piece (`skin`) in `zone`: what is not skin and reaches the picture's edge without crossing
    it, grown `grow` pixels (a fringe's strands with skin between them; round 2, 2026-11-26: closing the skin piece
    took an older woman's grey fringe and bob into the face, and the photo smeared over the model's hair). The holes
    the skin closes round (brows, eyes, lips, nostrils) are not hair."""
    outside, _ = ndimage.label(~skin)
    edge = np.unique(np.concatenate([outside[0], outside[-1], outside[:, 0], outside[:, -1]]))
    reaching = np.isin(outside, edge[edge > 0]) & zone
    return ndimage.binary_dilation(reaching, iterations=max(1, int(grow)))


def eye_openings(shape, marks, pixels_per_m):
    """The photo's lid openings (marks.json's upper and lower margins, MediaPipe's), grown EYE_GROW_M: the photo's
    iris and white, never laid on the model's lids (round 2, 2026-11-26: an older woman wore a second iris under each
    lower lid)."""
    picture = Image.new("L", (shape[1], shape[0]), 0)
    for eye in marks["eyes"]:
        ImageDraw.Draw(picture).polygon([tuple(point) for point in eye["upper"] + eye["lower"][::-1]], fill=255)
    return ndimage.binary_dilation(np.asarray(picture) > 0, iterations=max(1, int(EYE_GROW_M * pixels_per_m)))


def model_hair_free(grid, pupils):
    """Where the model's front is not its painted head hair (0 or 1): the `hair` round its skin-coloured paint's
    largest piece (`labels.skin_like`) in the `hair_zone` of its painted `pupils` (x, y); the photo is never laid on
    the model's hair (round 2, 2026-11-26: an older woman's fringe and bob, wider on the model than in the photo, wore
    the photo's forehead and cheeks)."""
    skin = grid["seen"] & labels.skin_like(rgb2lab(grid["colour"]).reshape(-1, 3)).reshape(grid["seen"].shape)
    pieces, count = ndimage.label(skin)
    if not count:
        raise ValueError("the model's front shows no skin-coloured paint")
    largest = np.bincount(pieces.ravel())[1:].argmax() + 1
    pupils = np.asarray(pupils)
    across, up = np.meshgrid(grid["xs"] - pupils[:, 0].mean(), grid["ys"] - pupils[:, 1].mean())
    return (~hair(pieces == largest, hair_zone(across, up, HAIR_SIDE_M), HAIR_GROW_M / STEP_M)).astype(np.float64)


def face_mask(photo, pixels_per_m, pupils=None):
    """The photo's face (0 to 1): its skin-coloured pixels (`labels.SKIN_HUE`) in one piece, the holes in it (brows,
    eyes, lips, nostrils) filled and, given its `pupils` (columns, rows), its `hair` in their `hair_zone` taken out
    (registering matches on the face with it), pulled MASK_ERODE_M in from the hair and the background and softened."""
    lab = rgb2lab(np.stack([ndimage.gaussian_filter(photo[..., channel], 2.0) for channel in range(3)], axis=-1))
    skin = labels.skin_like(lab.reshape(-1, 3)).reshape(lab.shape[:2])
    pieces, count = ndimage.label(skin)
    if not count:
        raise ValueError("the photo shows no skin-coloured piece")
    largest = np.bincount(pieces.ravel())[1:].argmax() + 1
    face = ndimage.binary_fill_holes(ndimage.binary_closing(pieces == largest, iterations=int(0.003 * pixels_per_m)))
    face = ndimage.binary_fill_holes(face)
    if pupils is not None:
        rows, columns = np.indices(skin.shape)
        pupils = np.asarray(pupils)
        zone = hair_zone(columns - pupils[:, 0].mean(), pupils[:, 1].mean() - rows, HAIR_SIDE_M * pixels_per_m)
        face = face & ~hair(pieces == largest, zone, HAIR_GROW_M * pixels_per_m)
    face = ndimage.binary_erosion(face, iterations=max(1, int(MASK_ERODE_M * pixels_per_m)))
    return ndimage.gaussian_filter(face.astype(np.float64), MASK_ERODE_M * pixels_per_m / 2.0)


def smoothed_over(values, weight, sigma):
    """`values` (H x W x C or H x W) averaged over `sigma` pixels where `weight` holds (normalised convolution)."""
    total = ndimage.gaussian_filter(weight, sigma) + 1e-9
    if values.ndim == 2:
        return ndimage.gaussian_filter(values * weight, sigma) / total
    return np.stack([ndimage.gaussian_filter(values[..., channel] * weight, sigma) / total
                     for channel in range(values.shape[-1])], axis=-1)


def occlusion(grid):
    """How much of the sky over each front pixel the model's own front hides (0 open to 1 shut): over OCCLUSION's
    `directions` across the front, the highest rise within `reach_m` (the depth `samples` steps out over the distance),
    as the sine of its angle, averaged. Where the photo is dark by this, the render darkens it again."""
    depth = np.where(grid["seen"], grid["depth"], -np.inf)
    reach = OCCLUSION["reach_m"] / STEP_M
    shut = np.zeros(depth.shape)
    for angle in np.linspace(0.0, 2.0 * np.pi, OCCLUSION["directions"], endpoint=False):
        rise = np.zeros(depth.shape)
        for distance in np.linspace(reach / OCCLUSION["samples"], reach, OCCLUSION["samples"]):
            moved = ndimage.shift(depth, (-distance * np.sin(angle), -distance * np.cos(angle)), order=0,
                                  mode="constant", cval=-np.inf)
            rise = np.maximum(rise, (moved - depth) / (distance * STEP_M))
        shut += rise / np.sqrt(1.0 + rise ** 2)
    return np.where(grid["seen"], shut / OCCLUSION["directions"], 0.0)


def shading(grid, photo_linear, skin):
    """The photo's broad light over the front grid, per channel (a shut hollow's light is the skin's own colour
    bounced, so it is warmer as well as darker): each linear channel over SHADING_SIGMA_M fitted as first order in the
    surface normal and in the model's own `occlusion` (smoothed alike) over the skin, over its mean there; clipped to
    SHADING_RANGE."""
    colour = smoothed_over(photo_linear, skin, SHADING_SIGMA_M / STEP_M)
    shut = smoothed_over(occlusion(grid), skin, SHADING_SIGMA_M / STEP_M)  # smoothed as the photo is, so fitted whole
    terms = np.stack([np.ones_like(grid["facing"]), grid["normal_x"], grid["normal_y"], grid["facing"], shut], axis=-1)
    held = skin > 0.5
    fitted, *_ = np.linalg.lstsq(terms[held], colour[held], rcond=None)
    light = terms @ fitted
    return np.clip(light / light[held].mean(axis=0), *SHADING_RANGE), fitted


def hollows(grid, flat, skin):
    """The photo's broad shade left in the model's hollows (HOLLOW): per front pixel 1 on open skin, in a hollow the
    plain skin's (`plain_skin`) brightness over SHADING_SIGMA_M against its brightness over `broad_m`, as far as the
    model's own smoothed `occlusion` shuts it, clipped to SHADING_RANGE's floor and 1. `flat`: the photo with the
    fitted shading divided out."""
    brightness = eyes.luminance(flat)
    plain = plain_skin(brightness, skin, int(GLOSS["matte_m"] / STEP_M))
    local = smoothed_over(brightness, plain, SHADING_SIGMA_M / STEP_M)
    broad = smoothed_over(brightness, plain, HOLLOW["broad_m"] / STEP_M)
    shut = smoothed_over(occlusion(grid), skin, SHADING_SIGMA_M / STEP_M)
    return np.clip(local / np.maximum(broad, 1e-4), SHADING_RANGE[0], 1.0) ** ramp(shut, *HOLLOW["shut"])


def gloss_free(colour, matte, chroma):
    """Linear colours with the photo's highlights pressed down: brightness over the matte skin round it (`matte`) past
    GLOSS's `kept` excess (a pore's or a freckle's own) scaled by its `left` share, and the colour of such a highlight
    moved to the matte skin's chromaticity round it (`chroma`, each channel over red) over GLOSS's `recolour` range;
    the pixel's own detail is scaled, never replaced. With the excess before."""
    excess = eyes.luminance(colour) / np.maximum(matte, 1e-4) - 1.0
    kept = np.where(excess > GLOSS["kept"], GLOSS["kept"] + (excess - GLOSS["kept"]) * GLOSS["left"], excess)
    pressed = colour * ((1.0 + kept) / np.maximum(1.0 + excess, 1e-4))[..., None]
    moved = ramp(excess, GLOSS["kept"], GLOSS["kept"] + GLOSS["recolour"])[..., None]
    recoloured = eyes.luminance(pressed)[..., None] / np.maximum(eyes.luminance(chroma)[..., None], 1e-4) * chroma
    return pressed * (1.0 - moved) + recoloured * moved, excess


def plain_skin(brightness, skin, reach):
    """The skin's weight (`skin`, 0 to 1) where it is no darker than MATTE_DARK of its brightness over `reach` pixels:
    a brow, the lashes and a crease left out."""
    return skin * (brightness > MATTE_DARK * smoothed_over(brightness, skin, reach))


def matte_skin(flat, skin):
    """The matte skin's brightness and chromaticity (each channel over red) over the front grid: the brightness's
    lower GLOSS `percentile` within `matte_m` (a highlight is smaller than that) over the plain skin (`plain_skin`,
    the rest filled from it), smoothed; the chromaticity averaged over it where the skin is no brighter than that."""
    brightness = eyes.luminance(flat)
    reach = int(GLOSS["matte_m"] / STEP_M)
    plain = plain_skin(brightness, skin, reach)
    filled = np.where(plain > 0, brightness, smoothed_over(brightness, plain, reach / 2.0))
    matte = ndimage.gaussian_filter(ndimage.percentile_filter(filled, GLOSS["percentile"], size=reach), reach / 4.0)
    weight = skin * (brightness < matte * (1.0 + GLOSS["kept"]))
    chroma = smoothed_over(flat / np.maximum(flat[..., :1], 1e-4), weight, reach / 2.0)
    return matte, chroma


def ramp(values, low, high):
    """0 under `low`, 1 over `high`, smooth between."""
    share = np.clip((values - low) / (high - low), 0.0, 1.0)
    return share * share * (3.0 - 2.0 * share)


def eye_floor_distance(grid, floor_points):
    """Each front pixel's distance (m) from the painted eye's floor (points the eyes step pushes back or removes);
    infinite with no floor (the whole head's run, `head.py`: its lids are laid on the photo's, so the photo reaches
    their margins)."""
    near = np.zeros(grid["depth"].shape, bool)
    if not len(floor_points):
        return np.full(near.shape, np.inf)
    cols = np.round((floor_points[:, 0] - grid["xs"][0]) / STEP_M).astype(int)
    rows = np.round((floor_points[:, 1] - grid["ys"][0]) / STEP_M).astype(int)
    inside = (rows >= 0) & (rows < near.shape[0]) & (cols >= 0) & (cols < near.shape[1])
    near[rows[inside], cols[inside]] = True
    return ndimage.distance_transform_edt(~near) * STEP_M


def grid_share(grid, mask_on_grid, floor_distance):
    """How much of the photo each front pixel wears: the photo's face, how squarely it faces forward (FACING) and how
    far from the eye's floor (EYE_CLEAR_M), rising over EDGE_FEATHER_M from its outer edge (round 2: a hard paint edge
    at the temples and forehead), softened over SHARE_SIGMA_M."""
    share = mask_on_grid * ramp(grid["facing"], *FACING) * ramp(floor_distance, *EYE_CLEAR_M) * grid["seen"]
    inside = ndimage.distance_transform_edt(ndimage.binary_fill_holes(share > 0.5)) * STEP_M
    return ndimage.gaussian_filter(share * ramp(inside, 0.0, EDGE_FEATHER_M), SHARE_SIGMA_M / STEP_M)


def at_points(grid, values, points):
    """A front grid's values at model points (x, y), bilinear."""
    cols = (points[:, 0] - grid["xs"][0]) / STEP_M
    rows = (points[:, 1] - grid["ys"][0]) / STEP_M
    return ndimage.map_coordinates(values, [rows, cols], order=1, mode="constant", cval=0.0)


def visible(grid, points):
    """Which model points lie on the front-most surface over them: within VISIBLE_M, more on a slope (VISIBLE_SLOPE
    front pixels times the steepest slope round it, up to VISIBLE_MAX_M)."""
    depth = np.where(grid["seen"], grid["depth"], -1e3)
    facing = np.clip(ndimage.minimum_filter(grid["facing"], size=3), 1e-3, 1.0)
    slope = np.sqrt(1.0 / facing ** 2 - 1.0)
    reach = np.minimum(VISIBLE_M + VISIBLE_SLOPE * STEP_M * at_points(grid, slope, points), VISIBLE_MAX_M)
    return np.abs(points[:, 2] - at_points(grid, depth, points)) < reach


def tzone(points, tip):
    """Each point's share of the oily T-zone (TZONE's ellipses round the nose tip), 0 to 1."""
    total = np.zeros(len(points))
    for (centre_x, centre_y), (radius_x, radius_y) in TZONE:
        reach = (((points[:, 0] - tip[0] - centre_x) / radius_x) ** 2
                 + ((points[:, 1] - tip[1] - centre_y) / radius_y) ** 2)
        total += np.exp(-reach)
    return np.clip(total, 0.0, 1.0)


def texture_rows(grid, warp, photo_linear, coarse, rows):
    """The face texture's rows `rows` (TEXTURE wide, the box's rows from the bottom), linear: the photo resampled, the
    shading divided out, the gloss taken off and the broad tone moved to the paint's where the photo fades out."""
    box = grid["box"]
    step_x = (box[1] - box[0]) / TEXTURE
    step_y = (box[3] - box[2]) / TEXTURE
    xs = box[0] + (np.arange(TEXTURE) + 0.5) * step_x
    ys = box[2] + (rows + 0.5) * step_y
    column, row = mapped(warp, xs, ys)
    colour = np.clip(sampled(photo_linear, column, row, order=3), 0.0, None)
    grid_x, grid_y = np.meshgrid((xs - grid["xs"][0]) / STEP_M, (ys - grid["ys"][0]) / STEP_M)
    at = [grid_y, grid_x]

    def coarse_at(values):
        if values.ndim == 2:
            return ndimage.map_coordinates(values, at, order=1, mode="nearest")
        return np.stack([ndimage.map_coordinates(values[..., channel], at, order=1, mode="nearest")
                         for channel in range(values.shape[-1])], axis=-1)

    colour = colour / coarse_at(coarse["shading"])
    colour, _ = gloss_free(colour, coarse_at(coarse["matte"]), coarse_at(coarse["chroma"]))
    toning = coarse_at(coarse["toning"])
    colour = colour * coarse_at(coarse["tone_ratio"]) ** toning[..., None]
    return colour, np.clip(coarse_at(coarse["share"]), 0.0, 1.0)


def coarse_maps(grid, warp, photo, pupils, marks=None):
    """The front grid's photo (linear), its face mask, shading, the matte skin and the tone moved towards the
    paint where the photo fades out; with the grid's photo share. `pupils`: the model's painted pupils (x, y) and the
    photo's (columns, rows), for where head hair can be; `marks` (marks.json's), the photo's lid openings."""
    pixels_per_m = float(np.sqrt(abs(np.linalg.det(warp["matrix"][:, :2]))))
    column, row = mapped(warp, grid["xs"], grid["ys"])
    photo_linear = linear(photo)
    seen = sampled(photo_linear, column, row)
    model_pupils, photo_pupils = pupils
    face = face_mask(photo, pixels_per_m, photo_pupils)
    if marks is not None:
        face = face * ~eye_openings(face.shape, marks, pixels_per_m)
    mask = (ndimage.map_coordinates(face, [row, column], order=1, mode="constant")
            * model_hair_free(grid, model_pupils))
    skin = mask * grid["seen"] * (grid["facing"] > 0.3)
    light, fitted = shading(grid, seen, skin)
    light = light * hollows(grid, seen / light, skin)[..., None]
    flat = seen / light
    matte, chroma = matte_skin(flat, skin)
    cleaned, _ = gloss_free(flat, matte, chroma)
    share = grid_share(grid, mask, grid["floor_distance"])
    coarse = {"shading": light, "matte": matte, "chroma": chroma, "share": share, "light_fit": fitted, "photo": seen,
              "cleaned": cleaned}
    coarse.update(fade_toning(grid, coarse))
    return coarse


def fade_toning(grid, coarse):
    """Where the photo fades into the model's paint, how far its broad tone moves to the paint's (`toning`, 1 at the
    edge) and by what ratio (`tone_ratio`): the grid's paint over the flattened photo, both over BLEND_SIGMA_M."""
    share = coarse["share"]
    sigma = BLEND_SIGMA_M / STEP_M
    held = (share > 0.05).astype(np.float64)
    tone_ratio = np.clip(smoothed_over(linear(grid["colour"]), held, sigma)
                         / np.maximum(smoothed_over(coarse["cleaned"], held, sigma), 1e-4), 0.5, 2.0)
    whole = ndimage.binary_fill_holes(share > 0.3).astype(np.float64)  # the eyes, nostrils and lips' edges are inside
    toning = 1.0 - ndimage.gaussian_filter(np.clip(ndimage.gaussian_filter(whole, sigma / 2.0) - 0.5, 0.0, 0.5) * 2.0,
                                           sigma / 4.0)
    return {"tone_ratio": tone_ratio, "toning": toning}


def photo_skin(coarse):
    """The flattened photo's skin on the front grid as CIELAB (sRGB) and where it is (its share over PAINT_TONE's
    `share`, skin-coloured)."""
    lab = rgb2lab(encoded(coarse["cleaned"]))
    held = (coarse["share"] > PAINT_TONE["share"]) & labels.skin_like(lab.reshape(-1, 3)).reshape(lab.shape[:2])
    if held.sum() < 100:
        raise ValueError("the photo's face shows too little skin to tone the paint by")
    return lab, held


def broad_and_spread(lab, held, sigma):
    """A CIELAB picture's skin (`held`) statistics: its broad colour (over `sigma` pixels, normalised over `held`) and
    the broad mean, the broad spread and the detail's spread over `held`, per channel."""
    broad = smoothed_over(lab, held.astype(np.float64), sigma)
    return broad, broad[held].mean(axis=0), broad[held].std(axis=0), (lab - broad)[held].std(axis=0)


def texture_mask(corner_uv, chosen, shape):
    """The texels (rows top down) of `chosen` triangles' UVs (glTF's: v up)."""
    picture = Image.new("L", (shape[1], shape[0]), 0)
    draw = ImageDraw.Draw(picture)
    corners = corner_uv[chosen] * [shape[1] - 1, -(shape[0] - 1)] + [0.0, shape[0] - 1]
    for trio in corners:
        draw.polygon([tuple(point) for point in trio], fill=255)
    return np.asarray(picture) > 0


def texels_per_m(points, triangles, corner_uv, chosen, shape):
    """The texture's texels a metre on `chosen` triangles (their UV area over their area)."""
    corners = points[triangles[chosen]]
    area = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1).sum()
    flat = corner_uv[chosen] * [shape[1], shape[0]]
    first, second = flat[:, 1] - flat[:, 0], flat[:, 2] - flat[:, 0]
    uv_area = np.abs(first[:, 0] * second[:, 1] - first[:, 1] * second[:, 0]).sum()
    return float(np.sqrt(uv_area / max(area, 1e-12)))


def paint_toned(texture, mask, per_m, photo_lab, photo_held):
    """The model's texture (sRGB 0 to 1) with its skin texels (`mask`) given the photo skin's colour statistics
    (PAINT_TONE): broad colour and spread, then detail, per CIELAB channel, read on the mask and laid on it grown by
    `grow_px` (the texture's filtering reads past a UV island's edge); with the per channel scales used."""
    lab = rgb2lab(texture)
    broad, mean, spread, fine = broad_and_spread(lab, mask, PAINT_TONE["broad_m"] * per_m)
    _, photo_mean, photo_spread, photo_fine = broad_and_spread(photo_lab, photo_held, PAINT_TONE["broad_m"] / STEP_M)
    broad_scale = np.clip(photo_spread / np.maximum(spread, 1e-6), 0.0, 1.0)
    detail_scale = np.clip(photo_fine / np.maximum(fine, 1e-6), *PAINT_TONE["detail"])
    toned = photo_mean + (broad - mean) * broad_scale + (lab - broad) * detail_scale
    grown = ndimage.binary_dilation(mask, iterations=PAINT_TONE["grow_px"])
    result = texture.copy()
    result[grown] = np.clip(lab2rgb(toned[grown]), 0.0, 1.0)
    return result, {"paint_lab": mean.round(1).tolist(), "photo_lab": photo_mean.round(1).tolist(),
                    "broad_scale": broad_scale.round(3).tolist(), "detail_scale": detail_scale.round(3).tolist()}


def face_texture(grid, warp, photo, coarse, out):
    """The TEXTURE-square face texture written to `out` (sRGB png), made a band of rows at a time."""
    photo_linear = linear(photo)
    texture = np.zeros((TEXTURE, TEXTURE, 4), np.uint8)
    for first in range(0, TEXTURE, 512):
        rows = np.arange(first, min(TEXTURE, first + 512))
        band, share = texture_rows(grid, warp, photo_linear, coarse, rows)
        texture[TEXTURE - 1 - rows, :, :3] = np.round(encoded(band) * 255.0).astype(np.uint8)
        texture[TEXTURE - 1 - rows, :, 3] = np.round(share * 255.0).astype(np.uint8)
    Image.fromarray(texture).save(out)
    return out


def paint_shade(grid):
    """The model's own paint's dark baked shading over the front grid (PAINT_SHADE): (the gain lifting it to its skin's
    broad tone, H x W x 3; how dark it was, 0 to 1)."""
    paint = linear(grid["colour"])
    skin = (grid["seen"] & labels.skin_like(rgb2lab(grid["colour"]).reshape(-1, 3)).reshape(grid["seen"].shape))
    weight = skin.astype(np.float64)
    local = smoothed_over(paint, weight, PAINT_SHADE["local_m"] / STEP_M)
    broad = smoothed_over(paint, weight, PAINT_SHADE["broad_m"] / STEP_M)
    local_light, broad_light = eyes.luminance(local), eyes.luminance(broad)
    lift = np.clip(broad_light / np.maximum(local_light, 1e-4), 1.0, PAINT_SHADE["gain"])
    tint = np.clip((broad / np.maximum(broad_light, 1e-4)[..., None]) / np.maximum(
        local / np.maximum(local_light, 1e-4)[..., None], 1e-4), *PAINT_SHADE["chroma"])
    dark = ramp(1.0 - local_light / np.maximum(broad_light, 1e-4), *PAINT_SHADE["dark"]) * (weight > 0)
    return 1.0 + (lift[..., None] * tint - 1.0) * dark[..., None], dark


def point_shares(grid, coarse, points):
    """Each model point's photo share: the grid's share where it lies on the front-most surface, else none (the
    texture's alpha carries the share finely; a point's says only whether it is the front the photo saw)."""
    return np.where(visible(grid, points), at_points(grid, coarse["share"], points), 0.0)


def close_point(grid, tip):
    """The cheek and nose close-up's aim: the front surface CLOSE_AIM_M beside (the subject's left) and over the nose
    tip."""
    point = np.array([[tip[0] + CLOSE_AIM_M[0], tip[1] + CLOSE_AIM_M[1], 0.0]])
    point[0, 2] = at_points(grid, np.where(grid["seen"], grid["depth"], tip[2]), point)[0]
    return point[0]


def skin_triangles(points, triangles, likeness, shares):
    """Which model triangles are skin: painted skin (`likeness`, 1 where `labels.skin_like` holds on their paint,
    settled by their neighbours, `labels.settled`, so the hairline follows the paint's edge, not single triangles), or
    wearing the photo (their corners' `shares` over a half: the photo's brows lie on the model's painted ones, round
    1, 2026-11-26). The hair and clothes the model paints keep the model's own material."""
    painted = labels.settled(likeness, labels.adjacency(points, triangles)) > 0.5
    return painted | (shares[triangles].mean(axis=1) > 0.5)


def written(out, scale, grid, coarse, points, triangles, tip, stats, skin):
    """skin.npz (the model's own units; each point's paint gain and how dark its paint was where the photo does not
    reach, `paint_shade`), stats.json and the check pictures under `out`."""
    shares = point_shares(grid, coarse, points)
    front = visible(grid, points)
    zone = tzone(points, tip) * visible(grid, points)
    gain, dark = paint_shade(grid)
    point_gain = np.where(front[:, None], np.stack([at_points(grid, gain[..., channel] - 1.0, points)
                                                    for channel in range(3)], axis=-1) + 1.0, 1.0)
    thin_dark = np.where(front, at_points(grid, dark, points), 0.0) * (1.0 - np.clip(shares, 0.0, 1.0))
    stats["paint_lifted_points"] = int((thin_dark > 0.5).sum())
    np.savez_compressed(out / "skin.npz", points=(points / scale).astype(np.float32), front=front.astype(np.float32),
                        paint_gain=point_gain.astype(np.float32), thin_dark=thin_dark.astype(np.float32),
                        skin_centres=(points[triangles[skin]].mean(axis=1) / scale).astype(np.float32),
                        tzone=zone.astype(np.float32), box=np.asarray(grid["box"]) / scale,
                        close_point=close_point(grid, tip) / scale)
    stats.update({"points_with_photo": int((shares > 0.5).sum()), "points": len(points),
                  "shading_range": [round(float(coarse["shading"][coarse["share"] > 0.5].min()), 3),
                                    round(float(coarse["shading"][coarse["share"] > 0.5].max()), 3)],
                  "light_fit": np.round(coarse["light_fit"], 4).tolist(),
                  "texture_mm_per_px": round((grid["box"][1] - grid["box"][0]) / TEXTURE * 1000.0, 4)})
    (out / "stats.json").write_text(json.dumps(stats, indent=1))
    share = np.repeat(coarse["share"][..., None], 3, axis=-1)
    rows, cols = np.indices(coarse["share"].shape)
    board = ((rows // CHECK_SQUARE + cols // CHECK_SQUARE) % 2 == 0)[..., None]
    both = np.where(board, grid["colour"], encoded(coarse["photo"]))
    check = np.concatenate([both, encoded(coarse["photo"]), share], axis=1)[::-1]
    Image.fromarray(np.round(np.clip(check, 0, 1) * 255).astype(np.uint8)).save(out / "check.png")


def corner_split(points, triangles, corner_uv):
    """A mesh with its UVs per triangle corner (`lids.py`'s mended head) as one with a point per corner, as the
    front's raster reads it: (points, triangles, uv)."""
    count = len(triangles)
    return points[triangles].reshape(-1, 3), np.arange(3 * count).reshape(count, 3), corner_uv.reshape(-1, 2)


def repainted(painted, texture, photo, model_pupils, floor, raw=None, marks=None):
    """The photo registered on one head (`painted` its (points in metres, triangles, uv); `model_pupils` its painted
    pupils' (x, y), `floor` the painted eye's floor points, none when its lids are laid on the photo's): (the front
    grid, its coarse maps, the nose tip, the stats, the warp). Registered on the `raw`
    paint where given (`colour.py`'s toning moves the face's clusters apart and the detail match lost its patches,
    round 1, 2026-11-26: correlation 0.25 to 0.16); toned towards `texture`. The photo's lid openings (`marks`,
    marks.json's) are kept off the model where given."""
    view = eyes.front_view(*painted, texture)
    tip = eyes.nose_tip(view)
    _, photo_pupils, _ = eyes.photo_iris(photo)
    box = face_box(tip)
    grid = front_grid(*painted, texture, box, STEP_M)
    grid["box"] = box
    grid["floor_distance"] = eye_floor_distance(grid, floor)
    start = similarity(model_pupils, photo_pupils)
    matched = grid if raw is None else {**grid, "colour": eyes.painted(raw, grid["texel"])}
    warp, stats = registered(matched, photo, start)
    close = close_point(grid, tip)
    column, row = mapped(warp, close[:1], close[1:2])
    stats.update({"photo_pupils_px": photo_pupils.round(1).tolist(),
                  "photo_px_per_m": round(float(np.sqrt(abs(np.linalg.det(warp["matrix"][:, :2])))), 1),
                  "close_photo_px": [round(float(column[0, 0]), 1), round(float(row[0, 0]), 1)]})
    return grid, coarse_maps(grid, warp, photo, (model_pupils, photo_pupils), marks), tip, stats, warp


def repainted_written(mesh, painted, texture, photo, model_pupils, floor, out, scale, raw=None, marks=None):
    """`repainted`, then which of `mesh`'s triangles (its (points in metres, triangles), one for one with `painted`'s)
    are skin, the paint on them toned to the photo's skin (`paint_toned`) and face.png (faded into that paint),
    paint.png (the toned texture, sRGB), skin.npz, stats.json and check.png written under `out` (the model's units,
    `scale` its to metres); (its stats, the toned texture)."""
    grid, coarse, tip, stats, warp = repainted(painted, texture, photo, model_pupils, floor, raw, marks)
    points, triangles = mesh
    likeness = labels.skin_like(labels.face_colours(painted[1], painted[2], texture * 255.0)).astype(np.float64)
    skin = skin_triangles(points, triangles, likeness, point_shares(grid, coarse, points))
    stats["skin_triangles"] = int(skin.sum())
    corner_uv = painted[2][painted[1]]
    mask = texture_mask(corner_uv, skin, texture.shape)
    toned, stats["paint_toned"] = paint_toned(texture, mask, texels_per_m(painted[0], painted[1], corner_uv, skin,
                                                                          texture.shape), *photo_skin(coarse))
    grid["colour"] = eyes.painted(toned, grid["texel"])
    coarse.update(fade_toning(grid, coarse))
    out.mkdir(parents=True, exist_ok=True)
    face_texture(grid, warp, photo, coarse, out / "face.png")
    Image.fromarray(np.round(toned * 255.0).astype(np.uint8)).save(out / "paint.png")
    written(out, scale, grid, coarse, points, triangles, tip, stats, skin)
    return stats, toned


def arguments():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("model", type=pathlib.Path)
    parser.add_argument("photo", type=pathlib.Path)
    parser.add_argument("eyes", type=pathlib.Path, help="the eyes step's eyes.npz")
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--height", type=float, required=True, help="the model's height in metres as drawn")
    return parser.parse_args()


def main():
    options = arguments()
    points, triangles, uv, texture = eyes.loaded(options.model)
    scale = options.height / float(np.ptp(points[:, 1]))
    points = points * scale
    photo = np.asarray(Image.open(options.photo).convert("RGB"), np.float64) / 255.0
    found = np.load(options.eyes)
    floor = np.concatenate([found["moved_from"], found["removed"]]) * scale
    view = eyes.front_view(points, triangles, uv, texture)
    model_pupils = eyes.pupils(view, eyes.nose_tip(view))
    stats, _ = repainted_written((points, triangles), (points, triangles, uv), texture, photo, model_pupils, floor,
                                 options.out, scale)
    print(f"skin: {options.out}/face.png, {stats['points_with_photo']} of {stats['points']} points wear the photo, "
          f"detail correlation {stats['detail_correlation_before']} -> {stats['detail_correlation_after']}, "
          f"shading {stats['shading_range']}")


if __name__ == "__main__":
    main()
