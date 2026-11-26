"""The hair labels as a picture (`label_picture`): the head's triangles drawn solid from the front, the side, the back
and above, each in its own paint, the hair's tinted red, so the hairline can be judged against the paint's own edge."""
import numpy as np
from PIL import Image, ImageDraw
from skimage.color import lab2rgb

PIXEL_M = 0.0005  # one pixel this many metres
FRAME_M = 0.40  # each view this wide and high round the head
TINT = ((255, 30, 30), 0.45)  # the hair's tint and its share
# Each view: the picture's right and up as directions in the head's frame (y up, the face along +z); the camera
# looks along right x up.
VIEWS = {"front": ((1, 0, 0), (0, 1, 0)), "side": ((0, 0, -1), (0, 1, 0)), "back": ((-1, 0, 0), (0, 1, 0)),
         "above": ((1, 0, 0), (0, 0, -1))}


def view_of(corners, shown, aim, right, up):
    """One view's picture: the triangles (`corners`, n x 3 x 3) drawn back to front in their colours (`shown`)."""
    right, up = np.asarray(right, float), np.asarray(up, float)
    towards = np.cross(right, up)  # out of the picture, towards the camera
    size = int(FRAME_M / PIXEL_M)
    flat = corners - aim
    across = flat @ right / PIXEL_M + size / 2.0
    height = size / 2.0 - flat @ up / PIXEL_M
    order = np.argsort((flat @ towards).mean(axis=1))
    picture = Image.new("RGB", (size, size), (255, 255, 255))
    draw = ImageDraw.Draw(picture)
    for index in order:
        draw.polygon(list(zip(across[index], height[index])), fill=tuple(shown[index]))
    return np.asarray(picture)


def label_picture(points, faces, colours, labels, frame, path):
    """The four views side by side, written to `path`."""
    aim = np.array([frame["middle_x"], frame["top"] - FRAME_M / 2.0 + 0.03, frame["centre"][2]])
    middles = points[faces].mean(axis=1)
    near = np.flatnonzero(np.linalg.norm(middles - aim, axis=1) < FRAME_M * 0.75)
    shown = lab2rgb(colours[near][None])[0] * 255.0
    hair = labels[near]
    shown[hair] = shown[hair] * (1.0 - TINT[1]) + np.asarray(TINT[0]) * TINT[1]
    shown = shown.astype(np.uint8)
    pictures = []
    for name, (right, up) in VIEWS.items():
        centre = aim if name != "above" else np.array([aim[0], frame["top"], frame["centre"][2]])
        pictures.append(view_of(points[faces[near]], shown, centre, right, up))
    Image.fromarray(np.concatenate(pictures, axis=1)).save(path)
