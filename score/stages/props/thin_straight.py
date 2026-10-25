"""The code route for thin straight objects (owner, 2026-10-25, asked "May the framework build exactly this kind
(straight thin things, swept along their path) in code, with a library finish?": "Yes, code-build thin straight
things"): an object every Pro close-up failed (closeup@<place>'s batch gap) whose row is thin and straight is built
here instead of left a gap, by the Pixal3D row (pixal_row.py), as its take's files, so the finish route paints it and
the likeness row checks it like any take.

Thin and straight (`thin_straight`): the row's size is slender by the model gate's own rule (tools/props/gates/model.py
shape_class: its middle side under SLENDER_SHARE of its longest), and its name or noun names a straight kind
(STRAIGHT). Its profile is swept along its longest side, the row's straight length: round (an ellipse filling the two
short sides) for the kinds in ROUND, a rectangle of the two short sides for the rest (posts, beams, pillars).

Its take (`write_take`), in WORK/pixal where the batch would bring one: `<take>.glb` (raw) and the slimmed
`<take>-<faces>.glb` (the same model), `<take>-final.glb` (it stood by the finish's own turn, which the paint replays),
and `<take>.svviews/` with `input.png`, the row's
concept crop (closeup@<place>'s crops/<id>.jpg) cut out by the likeness row's mask (`cut_out`, kept here), which the finish route reads as
the take's close-up and the likeness row holds the model to, and `code.json` naming the build. The model's one colour
is the cut-out's median (the model's own texture, which the finish route measures and replaces with a library surface).
A crop the mask finds no object in is no build: the row stays a gap. Joints and brackets are not built: no world 1 row
names any (2026-10-25).
"""
import json
import pathlib
import re
import shutil

import numpy as np
from PIL import Image

import score.stages.props.prop_data as prop_data

# The straight kinds, by a word of the row's name or its noun (a plural's s dropped): a railing (posts and rails) and
# a coil are not one straight thing, so neither is here.
STRAIGHT = frozenset(("pipe", "cable", "conduit", "post", "pole", "rail", "handrail", "rod", "beam", "pillar", "girder",
                      "strut", "mast", "hose", "wire", "duct", "tube", "bar"))
ROUND = frozenset(("pipe", "cable", "conduit", "pole", "rail", "handrail", "rod", "mast", "hose", "wire", "tube"))
SEGMENTS = 32
# The raw take's tilt off the axes (write_take): radians about one level axis between x and z, so every side of the
# box leans and the finish's stand (the shortest turn back up) undoes it exactly.
RAW_TILT = (0.2, (1.0, 0.0, 1.0))
# The turns about up tried first (write_take keeps the one the stand undoes best): a square section's ground spread has
# no long side, so glb_file.squared turns a square post set square 45 degrees, and one set at 45 degrees back square.
RAW_YAWS = (0.0, np.pi / 4)
MARK = "code.json"
# The tool files it runs, declared by the Pixal3D row (pixal_row.files): the cut-out's mask and the slender rule.
TOOLS = {"close-up mask": "{repo}/tools/usd/compare.py", "model gate": "{repo}/tools/props/gates/model.py",
         "glb file": "{repo}/tools/props/glb_file.py"}


def kind_words(row):
    """The row's name's and noun's words, each without a plural's s."""
    words = re.findall(r"[a-z]+", f"{row['name']} {row.get('noun') or ''}".lower())
    return {word[:-1] if word.endswith("s") and word[:-1] in STRAIGHT else word for word in words}


def slender(size):
    """The model gate's own slender rule on a size (tools/props/gates/model.py shape_class)."""
    with prop_data.tools("props/gates", "props/library", "props"):
        import model as model_gate
    smallest, middle, largest = sorted(float(value) for value in size)
    return largest > 0 and middle / largest < model_gate.SLENDER_SHARE


def thin_straight(row):
    """Whether an inventory row is a thin straight thing (module docstring)."""
    return bool(kind_words(row) & STRAIGHT) and slender(row["size"])


def profile(row):
    """"round" or "rect": the profile its kind sweeps."""
    return "round" if kind_words(row) & ROUND else "rect"


def build(row):
    """The row's model at its size, in a raw take's frame as the finish leaves it (y up, the longer ground side along
    z: glb_file.squared; the inventory's size is wide, deep, tall), centred on the origin: its profile swept straight
    along its longest side."""
    import trimesh
    wide, deep, tall = (float(value) for value in row["size"])
    extents = np.array([min(wide, deep), tall, max(wide, deep)])
    along = int(np.argmax(extents))
    if profile(row) == "round":
        mesh = trimesh.creation.cylinder(radius=0.5, height=1.0, sections=SEGMENTS)  # along z, centred
        mesh.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], np.eye(3)[along]))
    else:
        mesh = trimesh.creation.box(extents=[1.0, 1.0, 1.0])
    mesh.apply_scale(extents / mesh.extents)
    mesh.apply_translation(-mesh.bounds.mean(0))
    return mesh


def finish_turn(raw):
    """The turn the finish gives a raw take (pixal.py's stand: glb_file.upright_turn, then level_turn), as the paint
    replays it (tools/props/library/labels.py finish_turn's first option), so the final model is the raw one stood."""
    with prop_data.tools("props"):
        import glb_file
    document, views = glb_file.read(raw)
    turn = glb_file.upright_turn(glb_file.positions(document, views))
    glb_file.turned(document, views, turn)
    whole = np.eye(4)
    whole[:3, :3] = glb_file.level_turn(*glb_file.faces(document, views)) @ turn
    return whole


def cut_crop(crop, folder):
    """The concept crop cut out by the likeness row's mask (cut_out), or None when it finds no object."""
    picture = Image.open(cut_out(pathlib.Path(crop), pathlib.Path(folder))).convert("RGBA")
    return picture if (np.asarray(picture)[..., 3] > 127).any() else None


def shading(pixels):
    """A close-up's backdrop colour at every pixel: a quadratic in x and y fitted to its border's pixels."""
    tall, wide = pixels.shape[:2]
    down, across = np.mgrid[0:tall, 0:wide] / max(tall, wide)
    terms = np.stack([np.ones_like(across), across, down, across * across, across * down, down * down], axis=-1)
    border = np.zeros((tall, wide), dtype=bool)
    border[0], border[-1], border[:, 0], border[:, -1] = True, True, True, True
    return terms @ np.linalg.lstsq(terms[border], pixels[border], rcond=None)[0]


def cut_out(closeup, folder):
    """The close-up with its object as alpha, which likeness.closeup_object reads (the likeness row's; here so the Pixal3D row's code
    leaves the likeness modules out) before compare.closeup_mask: the
    mask taken on the close-up with its backdrop's shading levelled out. compare.closeup_mask's one border colour
    took a studio backdrop's darker corner for the object (engineroom's power core, 2026-10-15: border 176 to 229
    grey, the corner joined the core's foot and its outline fell from 0.76 to 0.46). A close-up already cut out is
    kept. A prop object's take's Pixal3D input, the same close-up as Pixal3D cut it out, is taken before this
    (object_record): on the galley's fold-down seat, 2026-10-15, white cushions on a white backdrop, this mask kept
    11% of the picture, the frame without its cushions, and the outline fell to 0.26."""
    picture = Image.open(closeup)
    if picture.mode == "RGBA" and np.asarray(picture)[..., 3].min() < 128:
        return closeup
    pixels = np.asarray(picture.convert("RGB"), dtype=np.float64)
    level = Image.fromarray(np.clip(pixels - shading(pixels) + 128, 0, 255).astype(np.uint8))
    with prop_data.tools("usd", "props"):  # likeness.candidate, kept out of the Pixal3D row's code
        import compare
    mask = compare.closeup_mask(level)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{closeup.stem}.png"  # a concept crop is a .jpg
    Image.fromarray(np.dstack([pixels.astype(np.uint8), np.where(mask, 255, 0).astype(np.uint8)])).save(path)
    return path


def colour(picture):
    """The cut-out's median colour (sRGB 0-255) over its object's pixels."""
    pixels = np.asarray(picture)
    return np.median(pixels[pixels[..., 3] > 127][:, :3], axis=0)


def raw_take(row, yaw, factor, path):
    """(how far the finish's stand leaves its box from the built one's, the raw take): the build turned by `yaw` about
    up and tilted (RAW_TILT), coloured `factor`, written to `path` to be stood."""
    import trimesh
    mesh = build(row)
    built = mesh.extents.copy()
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(baseColorFactor=factor))
    mesh.apply_transform(trimesh.transformations.rotation_matrix(yaw, (0.0, 1.0, 0.0)))
    mesh.apply_transform(trimesh.transformations.rotation_matrix(*RAW_TILT))
    mesh.export(path)
    return float(np.abs(mesh.copy().apply_transform(finish_turn(path)).extents - built).max()), mesh


def write_take(take, row, crop, faces, pixal, scratch):
    """The take's files (module docstring) in `pixal`, or None and the take unwritten when its crop holds no object."""
    import trimesh
    picture = cut_crop(crop, scratch)
    if picture is None:
        return None
    factor = [*(colour(picture) / 255.0), 1.0]
    views = pixal / f"{take}.svviews"
    views.mkdir(parents=True, exist_ok=True)
    picture.save(views / "input.png")
    raw = min((raw_take(row, yaw, factor, pixal / f"{take}.glb") for yaw in RAW_YAWS), key=lambda found: found[0])[1]
    raw.export(pixal / f"{take}.glb")
    raw.export(pixal / f"{take}-{faces}.glb")  # the slimmed one the paint replays the finish's turn from
    raw.apply_transform(finish_turn(pixal / f"{take}.glb"))
    raw.export(pixal / f"{take}-final.glb")
    (views / MARK).write_text(json.dumps({"route": "code", "rule": "thin straight (owner, 2026-10-25)",
                                          "profile": profile(row), "size": row["size"], "crop": str(crop)}, indent=1))
    return views


def code_built(take, pixal):
    """Whether the take in `pixal` is this route's build."""
    return (pixal / f"{take}.svviews" / MARK).exists()


def unbuild(take, pixal):
    """Remove a code build's files, so a close-up that passed since is made by Pixal3D (the picture route first)."""
    shutil.rmtree(pixal / f"{take}.svviews")
    for path in pixal.glob(f"{take}*.glb"):
        if re.fullmatch(rf"{re.escape(take)}(-final|-\d+)?\.glb", path.name):
            path.unlink()


def without_closeup_gaps(found, built):
    """The batch gaps but the close-up's of the rows built here (they are made now)."""
    return [entry for entry in found if not (entry["row"] == "closeup" and set(entry["objects"]) & set(built))]
