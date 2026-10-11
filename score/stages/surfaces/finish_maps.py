"""A finish map measured against the picture it redraws, never judged by eye, and turned into one label per pixel of
that picture's frame (the close-up's, or a turntable view's).

A map is laid on the picture's frame by its object's box (one scale and a shift: a picture model may draw the object
a little larger or off centre), then checked: the object masks' overlap (IoU of the map's non-white pixels with the
picture's object), the share of the map's object pixels near a label colour, and the labels used against those
listed (a turntable view need not show every finish). It passes when all hold (IOU_LEAST, NEAR_LEAST, every listed
label used). A map short of NEAR_LEAST but over FILL_LEAST, its other measures held, is filled: each object pixel no
label is near takes the nearest labelled pixel's label (a door the picture model left photographic between painted
panels); one under FILL_LEAST fails.
"""
import numpy as np
from PIL import Image

# A map pixel is background within BACKGROUND_NEAR of white, a label's within LABEL_NEAR of its colour (RGB
# distance); a label counts as used over USED_LEAST of the map's object pixels.
BACKGROUND_NEAR = 60.0
LABEL_NEAR = 80.0
USED_LEAST = 0.001
IOU_LEAST = 0.85
NEAR_LEAST = 0.9
# The power unit's two first maps left its cabinet door photographic: 76 and 78% of the object near a label.
FILL_LEAST = 0.7


def object_box(mask):
    """(top, left, bottom, right) of a mask's pixels."""
    rows, columns = np.nonzero(mask)
    return rows.min(), columns.min(), rows.max() + 1, columns.max() + 1


def laid(finish_map, alpha):
    """The map resampled into the picture's frame (nearest pixel), its object's box matched to the picture's by one
    scale and a shift; outside the map it is white."""
    pixels = np.asarray(finish_map.convert("RGB"), dtype=np.float64)
    theirs = np.linalg.norm(pixels - 255.0, axis=2) > BACKGROUND_NEAR
    top, left, bottom, right = object_box(theirs)
    our_top, our_left, our_bottom, our_right = object_box(alpha)
    scale = ((bottom - top) + (right - left)) / ((our_bottom - our_top) + (our_right - our_left))
    rows, columns = np.mgrid[0:alpha.shape[0], 0:alpha.shape[1]]
    their_rows = np.round(((rows + 0.5) - (our_top + our_bottom) / 2) * scale + (top + bottom) / 2 - 0.5).astype(int)
    their_columns = np.round(((columns + 0.5) - (our_left + our_right) / 2) * scale + (left + right) / 2 - 0.5)
    their_columns = their_columns.astype(int)
    inside = ((their_rows >= 0) & (their_rows < pixels.shape[0]) & (their_columns >= 0)
              & (their_columns < pixels.shape[1]))
    found = np.full((*alpha.shape, 3), 255.0)
    found[inside] = pixels[their_rows[inside], their_columns[inside]]
    return found


def label_pixels(pixels, labels):
    """Each pixel's label index (nearest label colour within LABEL_NEAR), -1 for background or no label near."""
    colours = np.array(labels, dtype=np.float64)
    distance = np.linalg.norm(pixels[:, :, None, :] - colours[None, None], axis=3)
    found = distance.argmin(2)
    found[distance.min(2) > LABEL_NEAR] = -1
    found[np.linalg.norm(pixels - 255.0, axis=2) <= BACKGROUND_NEAR] = -1
    return found


def check(finish_map, alpha, listed, labels, every_label=True):
    """The map's measures on the picture's frame and whether it passes; (measures, label per pixel, -1 off the
    picture's object)."""
    pixels = laid(finish_map, alpha)
    theirs = np.linalg.norm(pixels - 255.0, axis=2) > BACKGROUND_NEAR
    iou = float((theirs & alpha).sum() / max((theirs | alpha).sum(), 1))
    per_pixel = label_pixels(pixels, labels[:listed])
    on_object = per_pixel[theirs]
    near = float((on_object >= 0).mean()) if on_object.size else 0.0
    shares = np.bincount(on_object[on_object >= 0], minlength=listed) / max(on_object.size, 1)
    used = int((shares >= USED_LEAST).sum())
    measures = {"iou": round(iou, 3), "near_label": round(near, 3), "labels_used": used, "labels_listed": listed,
                "label_shares": [round(float(share), 4) for share in shares],
                "passes": iou >= IOU_LEAST and near >= NEAR_LEAST and (used == listed or not every_label)}
    per_pixel[~alpha] = -1
    return measures, per_pixel


def filled(per_pixel, alpha):
    """Every object pixel with no label given the label of the nearest labelled pixel."""
    from scipy import ndimage
    unlabelled = per_pixel < 0
    _, (rows, columns) = ndimage.distance_transform_edt(unlabelled, return_indices=True)
    found = per_pixel[rows, columns]
    found[~alpha] = -1
    return found


def fillable(measures, every_label=True):
    """A map that failed only on its labelled share, over FILL_LEAST."""
    return (measures["iou"] >= IOU_LEAST and measures["near_label"] >= FILL_LEAST
            and (measures["labels_used"] == measures["labels_listed"] or not every_label))


def settled(attempts, alpha, every_label=True):
    """The kept label map of a picture's draws, each (measures, label per pixel): the first that passed, else the
    fillable one with the most labelled pixels, filled; (index of the draw kept, its labels, filled) or None."""
    for index, (measures, per_pixel) in enumerate(attempts):
        if measures["passes"]:
            return index, per_pixel, False
    usable = [index for index, (measures, _) in enumerate(attempts) if fillable(measures, every_label)]
    if not usable:
        return None
    best = max(usable, key=lambda index: attempts[index][0]["near_label"])
    return best, filled(attempts[best][1], alpha), True


def alpha_of(picture):
    """A picture's object mask (alpha over half)."""
    return np.asarray(picture.convert("RGBA"))[:, :, 3] > 127


def label_picture(per_pixel, labels):
    """A label-per-pixel array as a picture: each label its colour, the rest clear (RGBA)."""
    painted = np.zeros((*per_pixel.shape, 4), dtype=np.uint8)
    inside = per_pixel >= 0
    painted[inside, :3] = np.array(labels, dtype=np.uint8)[per_pixel[inside]]
    painted[inside, 3] = 255
    return Image.fromarray(painted)
