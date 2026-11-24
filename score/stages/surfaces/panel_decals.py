"""Printed panels (#159 round 15; r14's gas stove: its red and white control panel, a Chinese name box, OFF and Max
marks and dial arcs, came out as torn white and red pieces with a grey box). A printed panel or sticker, a printed area
of several inks together on one flat face, is one mark of shape `panel` (finish_ask.PANEL): its picture is made from
the close-up's own pixels, rectified onto the panel's plate, and laid as one picture decal, so it is whole, crisp and in
place. Its legible words are text marks of their own, set as text decals in a library face over it (text_decals.py),
their ink taken out of the panel's picture first so no blurred copy shows under them. The route's print finishes under
the panel take the finish it is printed on (route_parts.covered_prints), so TRELLIS.2's torn pieces no longer show; the
plate under it is pressed flat and closed as a vent's is (decal_plates.held, #214).

The picture's colours are its paint's under plain even light, as the list's tokens are (route_list: the close-up's
studio light lifts a print's lightness and chroma): each pixel's CIELAB lightness mapped by the line fitted from the
close-up colour of each finish the panel covers to its palette token's (`unlit`), its chroma scaled by their ratio, its
hue kept. Where something stands in front of the panel in the close-up (a knob), its pixels are filled from the
nearest panel pixels.

    SHAPE                                   the mark shape
    framed(mark, number, seen, part_of)     (placement, None) on the panel's plate, or (None, why)
    unlit(pairs)                            the map from close-up colours to their paint's
    drawn(placement, picture, seen, part_of, erase, colours)  its picture (RGBA)
"""
import numpy as np

SHAPE = "panel"
GRID = 48  # rays across a panel's box each way that find its plate
PLATE_SHARE = 0.3  # at least this share of them meet the panel's part
# A ray of the box's grid that meets the model within this of the plate gives the panel's span, whatever part it meets
# (r15p: its print's torn parts left out, the stove's panel spanned 6 cm of its 10).
PLATE_NEAR = 0.01
PX_PER_M = 3000  # as text_decals: a part with print is baked at about 3,000 px a metre
MOST_PX = 2048
# A close-up pixel whose ray meets the model further than this in front of the panel's plate sees something standing
# in front of it (the stove's knobs, 2.5 cm proud): its colour is filled from the nearest panel pixels.
IN_FRONT = 0.003
# and grown by this many pixels: the knob's own edge and shadow on the plate stand under IN_FRONT, and filled from them
# the r15p panel showed grey fans round each knob.
FRONT_GROW = 8
ERASE_GROW = 2  # close-up pixels a text mark's ink is grown by before it is taken out of the panel's picture
# How far off its plate a panel prints (its placement's `reach`, recipes.decal_depth): a quarter of its short side
# (3 cm on the stove) printed its picture's top rows on the rounded lip over its front (r15p's first look).
REACH = 0.008
PLATE_APART = 12.0  # CIE76: a pixel this near the plate's own close-up colour is the plate, not print
SCALE_LIMITS = (0.6, 1.2)  # the lightness line's slope is held inside these
CHROMA_LIMITS = (0.5, 1.0)  # and the chroma's scale inside these
CHROMA_FEWEST = 12.0  # a finish under this chroma in the close-up does not set the chroma's scale
# A finish whose close-up colour's hue and chroma (a* b*, at three quarters) lie further than this from its token's
# was read off another colour (r15p: the stove's yellow ink #b88820 measured L* 100 white), and sets no map.
PAIR_APART = 25.0


def projected(camera, size, points):
    """[[column, row], ...] of model-frame `points` in the close-up (`camera` route_cast.close_up_camera's, `size`
    its width and height); NaN behind the eye."""
    eye, right, up, field = camera
    focal = size[0] / 2 / np.tan(field / 2)
    ahead = np.cross(up, right)
    relative = np.asarray(points, dtype=float) - eye
    depth = relative @ ahead
    depth = np.where(depth > 1e-9, depth, np.nan)
    return np.c_[size[0] / 2 + focal * (relative @ right) / depth, size[1] / 2 - focal * (relative @ up) / depth]


def box_grid(box, count=GRID):
    """count x count close-up pixels evenly inside a box [left, top, wide, tall]."""
    left, top, wide, tall = box
    steps = (np.arange(count) + 0.5) / count
    return np.array([[left + across * wide, top + down * tall] for down in steps for across in steps])


def plane_of(points, normals):
    """(a point, the unit normal) of the plane the points lie on: the median facing, its offset the points' median
    along it."""
    normal = np.median(normals, axis=0)
    normal = normal / np.linalg.norm(normal)
    return np.median(points @ normal) * normal, normal


def take_up(normal):
    """The take's own up (+y; +z where its face lies flat) laid on a face of `normal`: the close-up is drawn upright."""
    for way in ([0.0, 1.0, 0.0], [0.0, 0.0, 1.0]):
        upward = np.asarray(way) - (np.asarray(way) @ normal) * normal
        if np.linalg.norm(upward) >= 0.5:
            return upward / np.linalg.norm(upward)
    return None


def framed(mark, number, seen, part_of, layer=None):
    """A panel mark's placement on its plate ({decal None, part, at, normal, up, size, layer, shape, what, from}, the
    take's own frame): its box's grid cast through the close-up (`seen`: route_cast Model, camera, size), the plate the
    plane of the rays that meet its part (the part most of them meet), its size the span across and up it of the rays
    that meet the model within PLATE_NEAR of it; or
    (None, why) when under PLATE_SHARE of the grid meets one part."""
    import route_cast as cast
    model, camera, size = seen
    faces, points = cast.cast_points(model, camera, size, box_grid(mark["box"]))
    met = faces >= 0
    if not met.any():
        return None, "its box meets no model"
    part = int(np.bincount(part_of[faces[met]]).argmax())
    mine = met & (part_of[np.maximum(faces, 0)] == part)
    if mine.sum() < PLATE_SHARE * len(faces):
        return None, f"under {PLATE_SHARE} of its box meets one part"
    point, normal = plane_of(points[mine], model.mesh.face_normals[faces[mine]])
    near = met & (np.abs((points - point) @ normal) <= PLATE_NEAR)
    up = take_up(normal)
    if up is None or near.sum() < 3:
        return None, "its plate has no up"
    right = np.cross(up, normal)
    offset = points[near] - point
    low = np.array([(offset @ right).min(), (offset @ up).min()])
    high = np.array([(offset @ right).max(), (offset @ up).max()])
    grown = (high - low) / (GRID - 1) / 2  # the grid's half step: its rays lie half a cell inside the box
    low, high = low - grown, high + grown
    middle = (low + high) / 2
    at = point + middle[0] * right + middle[1] * up + ((points[near] - point) @ normal).mean() * normal
    rounded = lambda vector: [round(float(value), 5) for value in vector]  # noqa: E731
    return {"decal": None, "part": part, "at": rounded(at), "normal": rounded(normal), "up": rounded(up),
            "size": [round(float(high[0] - low[0]), 5), round(float(high[1] - low[1]), 5)], "turn": 0.0,
            "layer": number if layer is None else layer, "ink_token": None, "what": mark.get("what", ""),
            "shape": SHAPE, "reach": REACH,
            "from": {"close_up_box": mark["box"], "seen": "close-up", "made": "close-up pixels"}}, None


def unlit(pairs):
    """The map (CIELAB arrays -> CIELAB) from colours as the close-up shows them to their paint's under plain even
    light, fitted from `pairs` [(the close-up's colour, the palette token's, weight)] of the finishes a panel covers:
    lightness on the weighted line through them (its slope inside SCALE_LIMITS; one finish or one lightness: its
    offset alone), chroma scaled by their weighted ratio (inside CHROMA_LIMITS; of the finishes over CHROMA_FEWEST),
    hue kept; a pair read off another colour (PAIR_APART) left out while one is not."""
    seen = np.array([pair[0] for pair in pairs], dtype=float)
    token = np.array([pair[1] for pair in pairs], dtype=float)
    weight = np.array([pair[2] for pair in pairs], dtype=float)
    kept = np.hypot(*(token[:, 1:] - 0.75 * seen[:, 1:]).T) <= PAIR_APART
    if kept.any():  # r15p: the stove's yellow and orange inks read white where TRELLIS.2's faces of them were cast
        seen, token, weight = seen[kept], token[kept], weight[kept]
    weight = weight / weight.sum()
    middle_seen, middle_token = weight @ seen[:, 0], weight @ token[:, 0]
    spread = weight @ (seen[:, 0] - middle_seen) ** 2
    slope = (weight @ ((seen[:, 0] - middle_seen) * (token[:, 0] - middle_token)) / spread) if spread > 4.0 else 1.0
    slope = float(np.clip(slope, *SCALE_LIMITS))
    chroma_seen, chroma_token = np.hypot(seen[:, 1], seen[:, 2]), np.hypot(token[:, 1], token[:, 2])
    strong = chroma_seen >= CHROMA_FEWEST
    scale = float(np.clip((weight[strong] @ (chroma_token[strong] / chroma_seen[strong])) / weight[strong].sum(),
                          *CHROMA_LIMITS)) if strong.any() else 0.75

    def mapped(lab):
        lab = np.asarray(lab, dtype=float)
        lightness = np.clip(middle_token + slope * (lab[..., 0] - middle_seen), 0.0, 100.0)
        return np.stack([lightness, lab[..., 1] * scale, lab[..., 2] * scale], -1)
    return mapped


def in_front(seen, part_of, placement, box):
    """(a mask over the close-up's pixels of `box` [left, top, wide, tall], int: True where the close-up sees something
    standing further than IN_FRONT in front of the panel's plate, or another part's face off it; the box's left and
    top)."""
    import route_cast as cast
    model, camera, size = seen
    left, top, wide, tall = (int(np.floor(value)) for value in box)
    columns, rows = np.meshgrid(np.arange(left, left + wide + 1), np.arange(top, top + tall + 1))
    faces, points = cast.cast_points(model, camera, size, np.c_[columns.ravel() + 0.5, rows.ravel() + 0.5])
    normal, at = np.asarray(placement["normal"]), np.asarray(placement["at"])
    height = np.where(faces >= 0, (np.nan_to_num(points) - at) @ normal, 0.0)
    from scipy import ndimage
    front = ((faces >= 0) & (height > IN_FRONT)).reshape(columns.shape)
    return (ndimage.binary_dilation(front, iterations=FRONT_GROW) if front.any() else front), left, top


def erased(picture, boxes_ink):
    """A mask over the close-up (`picture` RGBA 0-255) of each placed text mark's ink (`boxes_ink`: [(its box, its
    ink "#rrggbb" or None)]): every pixel of its box nearer its ink's colour than the box's median, grown by
    ERASE_GROW; taken out of the panel's picture, the text decal printed over it (r15p's first draw: the stove name's
    ink read at most INK_MOST pixels evenly, its strokes left half there under the decal)."""
    from scipy import ndimage
    picture = np.asarray(picture)
    mask = np.zeros(picture.shape[:2], dtype=bool)
    for box, token in boxes_ink:
        if token is None:
            continue
        ink = np.array([int(token.lstrip("#")[at:at + 2], 16) for at in (0, 2, 4)], dtype=float)
        left, top, wide, tall = (int(round(value)) for value in box)
        crop = picture[top:top + tall, left:left + wide]
        shown = crop[..., 3] > 127
        if not shown.any():
            continue
        colours = crop[..., :3].astype(float)
        base = np.median(colours[shown], axis=0)
        mask[top:top + tall, left:left + wide] |= shown & (np.linalg.norm(colours - ink, axis=-1)
                                                           < np.linalg.norm(colours - base, axis=-1))
    return ndimage.binary_dilation(mask, iterations=ERASE_GROW) if mask.any() else mask


def pixels(placement):
    """(width, height) of a panel's picture: PX_PER_M, its longer side at most MOST_PX."""
    scale = min(PX_PER_M, MOST_PX / max(max(placement["size"]), 1e-6))
    return max(1, round(placement["size"][0] * scale)), max(1, round(placement["size"][1] * scale))


def drawn(placement, picture, seen, part_of, erase, colours, plate=None):
    """The panel's picture (RGBA, PIL): each of its pixels the point of its plate it covers, seen in the close-up
    (`picture` RGBA 0-255, `seen` route_cast Model, camera, size) and read there (bilinear) inside the mark's box,
    clear outside it; where the close-up sees something in front of the plate (in_front) or a placed text mark's ink
    (`erase`, erased's mask) it is filled from the nearest pixel read; its colours their paint's (`colours`, unlit's
    map); clear where the close-up shows within PLATE_APART of the `plate`'s colour (the finish it is printed on, its
    close-up CIELAB; r15p: the list's box held the stove's steel rim under its panel, drawn as flat grey paint)."""
    from PIL import Image
    from scipy import ndimage
    from skimage import color
    _, camera, size = seen
    wide, tall = pixels(placement)
    normal, up = np.asarray(placement["normal"]), np.asarray(placement["up"])
    right = np.cross(up, normal)
    across = ((np.arange(wide) + 0.5) / wide - 0.5) * placement["size"][0]
    upward = (0.5 - (np.arange(tall) + 0.5) / tall) * placement["size"][1]
    grid_across, grid_up = np.meshgrid(across, upward)
    points = (np.asarray(placement["at"]) + grid_across.reshape(-1, 1) * right + grid_up.reshape(-1, 1) * up)
    where = projected(camera, size, points)
    box = placement["from"]["close_up_box"]
    left, top, box_wide, box_tall = box
    inside = (np.isfinite(where).all(1) & (where[:, 0] >= left) & (where[:, 0] <= left + box_wide)
              & (where[:, 1] >= top) & (where[:, 1] <= top + box_tall))
    front, front_left, front_top = in_front(seen, part_of, placement, box)
    safe = np.nan_to_num(where)
    column, row = np.floor(safe[:, 0]).astype(int), np.floor(safe[:, 1]).astype(int)
    blocked = front[np.clip(row - front_top, 0, front.shape[0] - 1),
                    np.clip(column - front_left, 0, front.shape[1] - 1)]
    blocked |= erase[np.clip(row, 0, erase.shape[0] - 1), np.clip(column, 0, erase.shape[1] - 1)]
    rgba = np.asarray(picture, dtype=float)
    read = np.stack([ndimage.map_coordinates(rgba[..., channel], [safe[:, 1] - 0.5, safe[:, 0] - 0.5], order=1,
                                             mode="nearest") for channel in range(4)], -1)
    good = inside & ~blocked & (read[:, 3] > 127)
    if not good.any():
        raise ValueError(f"{placement['what']}: the close-up shows none of the panel")
    _, nearest = ndimage.distance_transform_edt(~good.reshape(tall, wide), return_indices=True)
    filled = read[:, :3].reshape(tall, wide, 3)[nearest[0], nearest[1]]
    seen_lab = color.rgb2lab(filled / 255.0)
    lab = colours(seen_lab)
    shown = np.clip(color.lab2rgb(lab), 0.0, 1.0)
    out = np.zeros((tall, wide, 4), dtype=np.uint8)
    out[..., :3] = np.round(shown * 255).astype(np.uint8)
    printed = inside.reshape(tall, wide)
    if plate is not None:
        printed &= np.linalg.norm(seen_lab - np.asarray(plate, dtype=float), axis=-1) > PLATE_APART
    out[..., 3] = np.where(printed, 255, 0)
    return Image.fromarray(out)
