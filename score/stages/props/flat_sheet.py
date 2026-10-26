"""The code route for flat sheets (a poster, a rug, a sticky note, a paper, a mat): an object whose row lies flat as a
sheet (`sheet`) and whose close-up passed, drawn from straight above (tools/props/closeup/check.py lies_flat), but
whose Pixal3D take came back with no usable model (no raw model, or its finish made none: Batch of 2026-10-26,
quarters' poster, rug and sticky note, every one "its finish made no model"), is built here by the Pixal3D row
(pixal_row.py) as its take's files instead of left a gap, so the finish route paints it with a library surface and the
likeness row holds it to its close-up like any take. The prop route first (owner, 2026-10-12): only a take the
picture route failed is built.

A sheet has no relief a picture could add: its model is its outline laid flat at its thickness. Its outline is its own
close-up's object, cut out (`cut_out`), since that close-up looks straight down on its face; its convex hull (every
sheet the readings name is a rectangle or a round) is stretched to the row's ground sides, the longer along z, and
given the row's height up y: the finish's own frame (glb_file.squared), so its stand leaves it as built. Its one
colour is the cut-out's median (the model's own texture, which the finish route measures and replaces with a library
surface). Its take's files are thin_straight's (raw, slimmed, final, `input.png` the cut
close-up, `code.json` naming this rule), so the finish route and the likeness row read it as a code take; the Pixal3D
take it replaces is removed first, and the row keeps the build (no close-up removes it: the close-up passed).
"""
import json

import numpy as np
from PIL import Image

import score.stages.props.prop_data as prop_data
import score.stages.props.thin_straight as thin_straight

# A sheet: it lies flat and its height is under this share of its longest side (a 2 cm mat on 52 cm, 0.04; a 1 mm
# note on 28 cm), so it has no relief beyond its outline. A keyboard, a book or a cabinet lying low is no sheet.
SHEET_SHARE = 0.05
RULE = "flat sheet (its Pixal3D take made no model)"


def sheet(row):
    """Whether the row lies flat (check.lies_flat, at the size its close-up was drawn at) as a sheet (SHEET_SHARE)."""
    with prop_data.tools("props/closeup", "props"):
        import check
    drawn = [float(value) for value in row.get("read_size") or row["size"]]
    return check.lies_flat(drawn) and drawn[2] < SHEET_SHARE * max(drawn)


def built(take, pixal):
    """Whether the take in `pixal` is this route's build."""
    mark = pixal / f"{take}.svviews" / thin_straight.MARK
    return mark.exists() and json.loads(mark.read_text()).get("rule") == RULE


def build(row, picture):
    """The sheet's model: the convex hull of `picture`'s object (alpha), stretched to the row's ground sides (the
    longer along z) and its height up y, centred on the origin."""
    import trimesh
    from scipy.spatial import ConvexHull
    inside = np.argwhere(np.asarray(picture)[..., 3] > 127)[:, ::-1].astype(float)  # (x, y) of the object's pixels
    corners = (inside[:, None, :] + np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])).reshape(-1, 2)
    outline = corners[ConvexHull(corners).vertices]
    outline = outline[:, np.argsort(np.ptp(outline, axis=0))]  # its shorter side first: x, then z
    outline = (outline - outline.min(0)) / np.ptp(outline, axis=0)
    wide, deep, tall = (float(value) for value in row["size"])
    ground = outline * [min(wide, deep), max(wide, deep)]
    points = np.vstack([np.c_[ground[:, 0], np.full(len(ground), height), ground[:, 1]] for height in (0.0, tall)])
    mesh = trimesh.convex.convex_hull(points)
    mesh.apply_translation(-mesh.bounds.mean(0))
    return mesh


def cut_out(closeup, folder):
    """The close-up with its sheet as alpha: every pixel off the backdrop (thin_straight.shading, fitted to the border)
    by the close-up check's figure step (tools/props/closeup/check.py BACKGROUND_STEP, an RGB distance), closed, its
    largest piece with its holes filled. The likeness row's cut (thin_straight.cut_out: one channel at a time, by
    compare's larger step, opened) lost a light sheet on a light backdrop (quarters' sticky note, 2026-10-26: a cream
    note 24 to 26 off the grey backdrop in its reddest channel, so its largest piece was its drop shadow, an L along
    two edges, and its build's outline 0.288); the backdrop is fitted to the border only, as a backdrop refitted to
    every pixel near it (check.figure_of) takes in a large sheet that near. A sheet's contact shadow seen from above
    is a thin rim, which its hull carries. A close-up already cut out is kept."""
    from scipy import ndimage
    picture = Image.open(closeup)
    if picture.mode == "RGBA" and np.asarray(picture)[..., 3].min() < 128:
        return closeup
    with prop_data.tools("props/closeup", "props"):
        import check
    pixels = np.asarray(picture.convert("RGB"), dtype=np.float64)
    apart = np.linalg.norm(pixels - thin_straight.shading(pixels), axis=2) > check.BACKGROUND_STEP
    labels, count = ndimage.label(ndimage.binary_closing(apart, np.ones((3, 3))))
    if count == 0:
        raise ValueError(f"{closeup}: no sheet off its backdrop")
    mask = ndimage.binary_fill_holes(labels == np.bincount(labels.ravel())[1:].argmax() + 1)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{closeup.stem}.png"  # a concept crop is a .jpg
    Image.fromarray(np.dstack([pixels.astype(np.uint8), np.where(mask, 255, 0).astype(np.uint8)])).save(path)
    return path


def write_take(take, row, closeup, faces, pixal, cuts):
    """The take's files (module docstring) in `pixal` from its passed `closeup`, cut out into `cuts`; the Pixal3D
    take's files there are removed first."""
    import trimesh
    if (pixal / f"{take}.svviews").exists():
        thin_straight.unbuild(take, pixal)
    picture = Image.open(cut_out(closeup, cuts)).convert("RGBA")
    mesh = build(row, picture)
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        baseColorFactor=[*(thin_straight.colour(picture) / 255.0), 1.0]))
    views = pixal / f"{take}.svviews"
    views.mkdir(parents=True)
    picture.save(views / "input.png")
    mesh.export(pixal / f"{take}.glb")
    mesh.export(pixal / f"{take}-{faces}.glb")  # the slimmed one the paint replays the finish's turn from
    mesh.apply_transform(thin_straight.finish_turn(pixal / f"{take}.glb"))
    mesh.export(pixal / f"{take}-final.glb")
    (views / thin_straight.MARK).write_text(json.dumps({"route": "code", "rule": RULE, "size": row["size"],
                                                        "closeup": str(closeup)}, indent=1))
    return views
