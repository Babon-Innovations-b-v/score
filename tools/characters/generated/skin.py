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
   broad shading fitted to the front's slope (`shading`, first-order in the normal over the skin) divided out, and the
   highlights pressed down (`gloss_free`: brightness over the matte skin round them, `matte_skin`, past a pore's own
   scaled down, their colour moved to the matte skin's); then toned towards the model's own paint over BLEND_SIGMA_M
   where it fades into it, so the two meet with no step. Its alpha is the photo's share (`grid_share`): the photo's
   face (`face_mask`: its skin in one piece, its holes, brows, eyes and lips, filled), how squarely the point faces the
   camera (FACING) and how far from the eye's opening (EYE_CLEAR_M of the painted eye's floor `eyes.py` pushes back),
   smoothed so the edge is soft.
4. `point_shares` / `visible`: which model points are the front the photo saw (VISIBLE_M); `skin_triangles`: which
   triangles are painted skin (the rest keeps the model's own material); `tzone`: the oily T-zone (the forehead's
   middle, the nose, the chin), for the skin's `sheen` region.

Writes <out>/face.png (TEXTURE square, sRGB, its alpha the photo's share), <out>/skin.npz (the box in the model's own
units, every model point with whether it is the front the photo saw and its T-zone, the middles of the painted skin's
triangles) and <out>/stats.json; prints one line. `blender_skin.py` lays it.
"""
import argparse
import json
import pathlib

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.color import rgb2lab

from tools.characters.generated import eyes

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
FACING = (0.25, 0.6)  # a point's share rises from the first to the second (the normal's forward part)
VISIBLE_M = 0.0015  # a point wears the photo when it is within this of the front-most surface over it
EYE_CLEAR_M = (0.0008, 0.0025)  # the photo fades in from the first to the second away from the painted eye's floor
SHARE_SIGMA_M = 0.001  # the share smoothed over this, so its edge is soft
MASK_ERODE_M = 0.002  # the photo's face mask pulled this far in from hair and background
SHADING_SIGMA_M = 0.004  # the shading fitted to the photo's brightness smoothed over this
SHADING_RANGE = (0.8, 1.25)  # a fitted shading outside this is clipped (a crease's shade is the skin's own)
# the highlights: brighter than the matte skin (the brightness's lower `percentile` within `matte_m`) by more than
# `kept`, the rest of the excess pressed to `left` of it and its colour moved to the matte skin's over `recolour`
GLOSS = {"matte_m": 0.006, "percentile": 35, "kept": 0.05, "left": 0.25, "recolour": 0.1}
CLOSE_AIM_M = (0.022, 0.012)  # the cheek and nose close-up aimed this far beside and over the nose tip
BLEND_SIGMA_M = 0.012  # the photo is toned to the paint's broad colour where it fades into the paint
CHECK_SQUARE = 40  # check.png's board of paint and registered photo, squares this many front pixels
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
    return {"depth": depth, "colour": colour, "xs": xs, "ys": ys, "facing": facing, "seen": seen,
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


def face_mask(photo, pixels_per_m):
    """The photo's face (0 to 1): its skin-coloured pixels (`labels.SKIN_HUE`) in one piece, the holes in it (brows,
    eyes, lips, nostrils) filled, pulled MASK_ERODE_M in from the hair and the background and softened."""
    from tools.characters.generated import labels
    lab = rgb2lab(np.stack([ndimage.gaussian_filter(photo[..., channel], 2.0) for channel in range(3)], axis=-1))
    skin = labels.skin_like(lab.reshape(-1, 3)).reshape(lab.shape[:2])
    pieces, count = ndimage.label(skin)
    if not count:
        raise ValueError("the photo shows no skin-coloured piece")
    largest = np.bincount(pieces.ravel())[1:].argmax() + 1
    face = ndimage.binary_fill_holes(ndimage.binary_closing(pieces == largest, iterations=int(0.003 * pixels_per_m)))
    face = ndimage.binary_fill_holes(face)
    face = ndimage.binary_erosion(face, iterations=max(1, int(MASK_ERODE_M * pixels_per_m)))
    return ndimage.gaussian_filter(face.astype(np.float64), MASK_ERODE_M * pixels_per_m / 2.0)


def smoothed_over(values, weight, sigma):
    """`values` (H x W x C or H x W) averaged over `sigma` pixels where `weight` holds (normalised convolution)."""
    total = ndimage.gaussian_filter(weight, sigma) + 1e-9
    if values.ndim == 2:
        return ndimage.gaussian_filter(values * weight, sigma) / total
    return np.stack([ndimage.gaussian_filter(values[..., channel] * weight, sigma) / total
                     for channel in range(values.shape[-1])], axis=-1)


def shading(grid, photo_linear, skin):
    """The photo's broad light over the front grid: its brightness over SHADING_SIGMA_M fitted as first order in the
    surface normal over the skin, over its mean there; clipped to SHADING_RANGE."""
    brightness = smoothed_over(eyes.luminance(photo_linear), skin, SHADING_SIGMA_M / STEP_M)
    normal = np.stack([np.ones_like(grid["facing"]), grid["normal_x"], grid["normal_y"], grid["facing"]], axis=-1)
    held = skin > 0.5
    fitted, *_ = np.linalg.lstsq(normal[held], brightness[held], rcond=None)
    light = normal @ fitted
    return np.clip(light / light[held].mean(), *SHADING_RANGE), fitted


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


def matte_skin(flat, skin):
    """The matte skin's brightness and chromaticity (each channel over red) over the front grid: the brightness's
    lower GLOSS `percentile` within `matte_m` (a highlight is smaller than that), smoothed; the chromaticity averaged
    over it where the skin is no brighter than that."""
    brightness = eyes.luminance(flat)
    reach = int(GLOSS["matte_m"] / STEP_M)
    matte = ndimage.gaussian_filter(ndimage.percentile_filter(brightness, GLOSS["percentile"], size=reach), reach / 4.0)
    weight = skin * (brightness < matte * (1.0 + GLOSS["kept"]))
    chroma = smoothed_over(flat / np.maximum(flat[..., :1], 1e-4), weight, reach / 2.0)
    return matte, chroma


def ramp(values, low, high):
    """0 under `low`, 1 over `high`, smooth between."""
    share = np.clip((values - low) / (high - low), 0.0, 1.0)
    return share * share * (3.0 - 2.0 * share)


def eye_floor_distance(grid, floor_points):
    """Each front pixel's distance (m) from the painted eye's floor (points the eyes step pushes back or removes)."""
    near = np.zeros(grid["depth"].shape, bool)
    cols = np.round((floor_points[:, 0] - grid["xs"][0]) / STEP_M).astype(int)
    rows = np.round((floor_points[:, 1] - grid["ys"][0]) / STEP_M).astype(int)
    inside = (rows >= 0) & (rows < near.shape[0]) & (cols >= 0) & (cols < near.shape[1])
    near[rows[inside], cols[inside]] = True
    return ndimage.distance_transform_edt(~near) * STEP_M


def grid_share(grid, mask_on_grid, floor_distance):
    """How much of the photo each front pixel wears: the photo's face, how squarely it faces forward (FACING) and how
    far from the eye's floor (EYE_CLEAR_M), softened over SHARE_SIGMA_M."""
    share = mask_on_grid * ramp(grid["facing"], *FACING) * ramp(floor_distance, *EYE_CLEAR_M) * grid["seen"]
    return ndimage.gaussian_filter(share, SHARE_SIGMA_M / STEP_M)


def at_points(grid, values, points):
    """A front grid's values at model points (x, y), bilinear."""
    cols = (points[:, 0] - grid["xs"][0]) / STEP_M
    rows = (points[:, 1] - grid["ys"][0]) / STEP_M
    return ndimage.map_coordinates(values, [rows, cols], order=1, mode="constant", cval=0.0)


def visible(grid, points):
    """Which model points lie on the front-most surface over them (within VISIBLE_M)."""
    depth = np.where(grid["seen"], grid["depth"], -1e3)
    return np.abs(points[:, 2] - at_points(grid, depth, points)) < VISIBLE_M


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

    colour = colour / coarse_at(coarse["shading"])[..., None]
    colour, _ = gloss_free(colour, coarse_at(coarse["matte"]), coarse_at(coarse["chroma"]))
    toning = coarse_at(coarse["toning"])
    colour = colour * coarse_at(coarse["tone_ratio"]) ** toning[..., None]
    return colour, np.clip(coarse_at(coarse["share"]), 0.0, 1.0)


def coarse_maps(grid, warp, photo):
    """The front grid's photo (linear), its face mask, shading, the matte skin and the tone moved towards the
    paint where the photo fades out; with the grid's photo share."""
    pixels_per_m = float(np.sqrt(abs(np.linalg.det(warp["matrix"][:, :2]))))
    column, row = mapped(warp, grid["xs"], grid["ys"])
    photo_linear = linear(photo)
    seen = sampled(photo_linear, column, row)
    mask = ndimage.map_coordinates(face_mask(photo, pixels_per_m), [row, column], order=1, mode="constant")
    skin = mask * grid["seen"] * (grid["facing"] > 0.3)
    light, fitted = shading(grid, seen, skin)
    flat = seen / light[..., None]
    matte, chroma = matte_skin(flat, skin)
    cleaned, _ = gloss_free(flat, matte, chroma)
    share = grid_share(grid, mask, grid["floor_distance"])
    paint = linear(grid["colour"])
    sigma = BLEND_SIGMA_M / STEP_M
    held = (share > 0.05).astype(np.float64)
    tone_ratio = np.clip(smoothed_over(paint, held, sigma) / np.maximum(smoothed_over(cleaned, held, sigma), 1e-4),
                         0.5, 2.0)
    whole = ndimage.binary_fill_holes(share > 0.3).astype(np.float64)  # the eyes, nostrils and lips' edges are inside
    toning = 1.0 - ndimage.gaussian_filter(np.clip(ndimage.gaussian_filter(whole, sigma / 2.0) - 0.5, 0.0, 0.5) * 2.0,
                                           sigma / 4.0)
    return {"shading": light, "matte": matte, "chroma": chroma, "tone_ratio": tone_ratio, "toning": toning,
            "share": share,
            "light_fit": fitted, "photo": seen}


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


def skin_triangles(points, triangles, uv, texture):
    """Which model triangles are painted skin: `labels.skin_like` on their paint (`labels.face_colours`), settled by
    their neighbours (`labels.settled`, so the hairline follows the paint's edge, not single triangles). The hair,
    brows and clothes the model paints keep the model's own material."""
    from tools.characters.generated import labels
    likeness = labels.skin_like(labels.face_colours(triangles, uv, texture * 255.0)).astype(np.float64)
    return labels.settled(likeness, labels.adjacency(points, triangles)) > 0.5


def written(out, scale, grid, coarse, points, triangles, tip, stats, skin):
    """skin.npz (the model's own units), stats.json and the check pictures under `out`."""
    shares = point_shares(grid, coarse, points)
    front = visible(grid, points)
    zone = tzone(points, tip) * visible(grid, points)
    np.savez_compressed(out / "skin.npz", points=(points / scale).astype(np.float32), front=front.astype(np.float32),
                        skin_centres=(points[triangles[skin]].mean(axis=1) / scale).astype(np.float32),
                        tzone=zone.astype(np.float32), box=np.asarray(grid["box"]) / scale,
                        close_point=close_point(grid, tip) / scale)
    stats.update({"points_with_photo": int((shares > 0.5).sum()), "points": len(points),
                  "shading_range": [round(float(coarse["shading"][coarse["share"] > 0.5].min()), 3),
                                    round(float(coarse["shading"][coarse["share"] > 0.5].max()), 3)],
                  "light_fit": [round(float(value), 4) for value in coarse["light_fit"]],
                  "texture_mm_per_px": round((grid["box"][1] - grid["box"][0]) / TEXTURE * 1000.0, 4)})
    (out / "stats.json").write_text(json.dumps(stats, indent=1))
    share = np.repeat(coarse["share"][..., None], 3, axis=-1)
    rows, cols = np.indices(coarse["share"].shape)
    board = ((rows // CHECK_SQUARE + cols // CHECK_SQUARE) % 2 == 0)[..., None]
    both = np.where(board, grid["colour"], encoded(coarse["photo"]))
    check = np.concatenate([both, encoded(coarse["photo"]), share], axis=1)[::-1]
    Image.fromarray(np.round(np.clip(check, 0, 1) * 255).astype(np.uint8)).save(out / "check.png")


def repainted(model, photo_path, eyes_npz, out, height):
    """The whole step for one head: registered, the texture and the shares written under `out`; its stats."""
    points, triangles, uv, texture = eyes.loaded(model)
    scale = height / float(np.ptp(points[:, 1]))
    points = points * scale
    photo = np.asarray(Image.open(photo_path).convert("RGB"), np.float64) / 255.0
    view = eyes.front_view(points, triangles, uv, texture)
    tip = eyes.nose_tip(view)
    model_pupils = eyes.pupils(view, tip)
    _, photo_pupils, _ = eyes.photo_iris(photo)
    box = face_box(tip)
    grid = front_grid(points, triangles, uv, texture, box, STEP_M)
    grid["box"] = box
    found = np.load(eyes_npz)
    floor = np.concatenate([found["moved_from"], found["removed"]]) * scale
    grid["floor_distance"] = eye_floor_distance(grid, floor)
    start = similarity(model_pupils, photo_pupils)
    warp, stats = registered(grid, photo, start)
    close = close_point(grid, tip)
    column, row = mapped(warp, close[:1], close[1:2])
    stats.update({"photo_pupils_px": photo_pupils.round(1).tolist(),
                  "photo_px_per_m": round(float(np.sqrt(abs(np.linalg.det(warp["matrix"][:, :2])))), 1),
                  "close_photo_px": [round(float(column[0, 0]), 1), round(float(row[0, 0]), 1)]})
    coarse = coarse_maps(grid, warp, photo)
    out.mkdir(parents=True, exist_ok=True)
    face_texture(grid, warp, photo, coarse, out / "face.png")
    skin = skin_triangles(points, triangles, uv, texture)
    stats["skin_triangles"] = int(skin.sum())
    written(out, scale, grid, coarse, points, triangles, tip, stats, skin)
    return stats


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
    stats = repainted(options.model, options.photo, options.eyes, options.out, options.height)
    print(f"skin: {options.out}/face.png, {stats['points_with_photo']} of {stats['points']} points wear the photo, "
          f"detail correlation {stats['detail_correlation_before']} -> {stats['detail_correlation_after']}, "
          f"shading {stats['shading_range']}")


if __name__ == "__main__":
    main()
