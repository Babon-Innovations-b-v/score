"""Wear decals and their carrier plate (2099 ADR-0008, the prologue places' lay plans, 2026-11-26): the marks weather
leaves on a place (grime, scorch, wet and damp stains, hairline cracks, rain and rust streaks) drawn in code as
library decals, and one thin plate a decal is laid on. No picture of a model and no texture of a route: each mark is a
field of seeded noise inked in one palette token, its transparency the mark's strength, so a stain reads on whatever
finish the plate's edge or the part under it wears; the decal is a score_lib surface of family `decal` (decal.png
and surface.json, as part_looks' decal_written writes them) and place_build lays its page through decal_read.

    KINDS                               {kind: how it is drawn}
    drawn(kind, size_m, ink, seed)      the decal's picture (RGBA), `size_m` [wide, tall] metres at PX_PER_M
    written(mark, folder)               one mark's decal.png and surface.json in `folder`, and its take-in row
    plate()                             (trimesh.Scene, record) of the carrier: a 1 x 1 m face PLATE_DEEP deep

    python -m score.stages.surfaces.wear_decals <marks.json> --into DIR

reads a list of marks ({id, kind, size_m, ink (#rrggbb), token, place, class, seed, title}) and writes each decal under
DIR/decals/<id>/, the plate under DIR/plate/ and DIR/listing.json, a `score-lib take-in` list; one line.

The plate's frame is the lightbox's (score/stages/signs): y up, its face towards +z, its foot on y 0, centred across
and in depth. It is laid scaled to its mark's size ([wide, tall, deep / PLATE_DEEP]), its `face` part bound to the
decal and its `edge` part to the finish of what it is laid on, so one carrier serves every mark.
"""
import argparse
import json
import pathlib

import numpy as np

PX_PER_M = 512  # a wear mark is soft: half a metre of stain needs no more than 2 px a millimetre
LEAST_PX, MOST_PX = 256, 2048
PLATE_DEEP = 0.002  # metres: a decal card stands 2 mm proud, under a walker's notice and over the finish's relief
CLASS_WORDS = ("plastic", "metal", "rubber", "glass", "paper", "cardboard", "wood", "fabric", "ceramic", "leather",
               "stone", "concrete", "organic")  # score_lib decals.CLASSES: what a decal is printed on
MAKER = "score/stages/surfaces/wear_decals"


def pixels(size_m):
    """The picture's [wide, tall] pixels for a mark of `size_m` metres: PX_PER_M, its longer side held within
    LEAST_PX and MOST_PX."""
    wide, tall = (float(side) for side in size_m)
    longer = max(wide, tall) * PX_PER_M
    scale = min(MOST_PX, max(LEAST_PX, longer)) / longer
    return max(1, round(wide * PX_PER_M * scale)), max(1, round(tall * PX_PER_M * scale))


def noise(shape, rng, cells=4, octaves=5):
    """Fractal value noise in [0, 1] of `shape` (rows, columns): `octaves` grids of random values, the first `cells`
    across the longer side, each twice as fine and half as strong, smoothly resized to the shape (a one-row field is
    a noise along its columns)."""
    from PIL import Image
    rows, columns = shape
    total, weight, strength = np.zeros(shape, np.float32), 0.0, 1.0
    for octave in range(octaves):
        across = cells * 2 ** octave
        grid = rng.random((max(2, round(across * rows / max(shape))) + 1,
                           max(2, round(across * columns / max(shape))) + 1)).astype(np.float32)
        total += strength * np.asarray(Image.fromarray(grid, "F").resize((columns, rows), Image.BICUBIC))
        weight += strength
        strength *= 0.5
    total /= weight
    return (total - total.min()) / max(float(np.ptp(total)), 1e-6)


def smooth(low, high, value):
    """Hermite step from 0 at `low` to 1 at `high`."""
    step = np.clip((value - low) / (high - low), 0.0, 1.0)
    return step * step * (3.0 - 2.0 * step)


def towards_middle(shape):
    """Each pixel's distance from the picture's middle, 1 at the middle of an edge (an ellipse fitted to it)."""
    rows, columns = shape
    down, across = np.mgrid[0:rows, 0:columns].astype(np.float32)
    return np.hypot((across + 0.5) / columns * 2.0 - 1.0, (down + 0.5) / rows * 2.0 - 1.0)


def grime(shape, rng):
    """Blotches of dirt: noise over a threshold, fading out before the edges, its strength varied finely."""
    blotch = smooth(0.42, 0.72, noise(shape, rng, cells=3) * (1.25 - 0.55 * towards_middle(shape)))
    return blotch * (0.35 + 0.35 * noise(shape, rng, cells=12, octaves=3)) * smooth(1.0, 0.8, towards_middle(shape))


def scorch(shape, rng):
    """A burn: soot darkest at the middle, its reach ragged by noise, rays of it thrown out by a noise of angle."""
    distance = towards_middle(shape)
    rows, columns = shape
    down, across = np.mgrid[0:rows, 0:columns].astype(np.float32)
    angle = np.arctan2(down - rows / 2.0, across - columns / 2.0)
    rays = noise((1, 720), rng, cells=24, octaves=3)[0][((angle + np.pi) / (2 * np.pi) * 719).astype(int)]
    reach = 0.45 + 0.4 * rays + 0.15 * noise(shape, rng, cells=4)
    return 0.9 * smooth(reach, 0.12, distance) * (0.75 + 0.25 * noise(shape, rng, cells=16, octaves=3))


def wet_stain(shape, rng):
    """A wet patch: a ragged pool, darker by a tide line where it dries at its rim."""
    pool = noise(shape, rng, cells=2) * (1.3 - 0.75 * towards_middle(shape))
    inside = smooth(0.48, 0.58, pool)
    rim = smooth(0.5, 0.54, pool) - smooth(0.56, 0.64, pool)
    return np.clip(0.32 * inside + 0.3 * rim, 0.0, 1.0) * smooth(1.0, 0.85, towards_middle(shape))


def damp_stain(shape, rng):
    """Rising damp or a leak from above: a stain hanging from the top edge, its lower edge ragged, ringed by tide lines
    where it dried back by turns."""
    rows, columns = shape
    reach = 0.45 + 0.5 * noise((1, columns), rng, cells=3)[0]
    down = (np.arange(rows, dtype=np.float32)[:, None] + 0.5) / rows
    wet = reach[None, :] - down + 0.08 * (noise(shape, rng, cells=6) - 0.5)
    stain = smooth(-0.02, 0.06, wet)
    rings = 0.5 + 0.5 * np.cos(wet * 22.0)
    sides = smooth(0.0, 0.12, np.minimum(np.linspace(0, 1, columns), np.linspace(1, 0, columns)))[None, :]
    return np.clip(stain * (0.3 + 0.06 * rings) + 0.25 * (smooth(-0.02, 0.0, wet) - smooth(0.0, 0.02, wet)),
                   0.0, 1.0) * sides


def hairline_crack(shape, rng):
    """A hairline crack: a wandering line across the picture with a few short branches, a pixel or two wide."""
    from PIL import Image, ImageDraw, ImageFilter
    rows, columns = shape
    picture = Image.new("L", (columns, rows), 0)
    draw = ImageDraw.Draw(picture)
    width = max(1, round(min(shape) / 220))

    def wander(start, heading, steps, stride):
        aim = heading
        point, line = np.array(start, float), [tuple(start)]
        for _ in range(steps):
            heading += rng.normal(0.0, 0.3) - 0.25 * (heading - aim)
            point = point + stride * np.array([np.cos(heading), np.sin(heading)])
            line.append(tuple(point))
        draw.line(line, fill=235, width=width, joint="curve")
        return line

    stride = max(columns, rows) / 40.0
    trunk = wander((columns * 0.05, rows * (0.3 + 0.4 * rng.random())), rng.normal(0.0, 0.3), 40, stride)
    for _ in range(int(rng.integers(2, 5))):
        start = trunk[int(rng.integers(5, len(trunk) - 5))]
        wander(start, rng.choice([-1.0, 1.0]) * (0.6 + 0.6 * rng.random()), int(rng.integers(5, 12)), stride * 0.7)
    return np.asarray(picture.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255.0


def streak(shape, rng):
    """Rain or rust streaks run down from the top edge: thin columns of differing strength and length, strongest
    where they leave the edge, fading as they run."""
    rows, columns = shape
    strength = smooth(0.45, 0.85, noise((1, columns), rng, cells=max(8, columns // 24), octaves=3)[0])
    length = 0.35 + 0.65 * noise((1, columns), rng, cells=max(4, columns // 64), octaves=2)[0]
    down = (np.arange(rows, dtype=np.float32)[:, None] + 0.5) / rows
    fade = np.clip(1.0 - down / length[None, :], 0.0, 1.0) ** 1.5
    return 0.75 * strength[None, :] * fade * (0.8 + 0.2 * noise(shape, rng, cells=10, octaves=3))


KINDS = {"grime": grime, "scorch": scorch, "wet_stain": wet_stain, "damp_stain": damp_stain,
         "hairline_crack": hairline_crack, "streak": streak}


def drawn(kind, size_m, ink, seed=0):
    """The mark's picture: `ink` (#rrggbb, a palette token's colour) through the kind's strength as its transparency,
    `size_m` [wide, tall] metres at PX_PER_M; the same kind, size, ink and seed draw the same picture."""
    from PIL import Image
    if kind not in KINDS:
        raise ValueError(f"no wear decal kind {kind!r}: one of {', '.join(KINDS)}")
    wide, tall = pixels(size_m)
    alpha = np.clip(KINDS[kind]((tall, wide), np.random.default_rng(seed)), 0.0, 1.0)
    colour = [int(ink.lstrip("#")[index:index + 2], 16) for index in (0, 2, 4)]
    rgba = np.empty((tall, wide, 4), np.uint8)
    rgba[..., :3] = colour
    rgba[..., 3] = np.round(alpha * 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def written(mark, folder):
    """One mark's decal.png and surface.json in `folder` (part_looks' decal_written's shape), and its take-in row;
    ValueError for a class score_lib's decals refuse or a picture with no mark in it."""
    if mark["class"] not in CLASS_WORDS:
        raise ValueError(f"{mark['id']}: class {mark['class']!r} is not one of {', '.join(CLASS_WORDS)}")
    picture = drawn(mark["kind"], mark["size_m"], mark["ink"], mark.get("seed", 0))
    if picture.getchannel("A").getextrema()[1] == 0:
        raise ValueError(f"{mark['id']}: its {mark['kind']} drew nothing")
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    picture.save(folder / "decal.png")
    size = [float(side) for side in mark["size_m"]]
    record = {"variant": mark["id"], "family": "decal", "recipe": "decal", "size_m": size, "class": mark["class"],
              "opacity": "trans", "ink": "one", "words": [], "kind": mark["kind"], "token": mark["token"],
              "seed": mark.get("seed", 0), "maps": {"decal": "decal.png"}, "source": "score"}
    (folder / "surface.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    what = (f"{mark['id']}: a {mark['kind'].replace('_', ' ')} drawn in code by score's wear decals ({MAKER}, seed "
            f"{mark.get('seed', 0)}), inked in the {mark['place']} palette's {mark['token']} ({mark['ink']}), "
            f"{size[0]:.2f} x {size[1]:.2f} m")
    return {"kind": "surface", "id": mark["id"], "title": mark["title"],
            "files": {"decal.png": {"path": str(folder / "decal.png"), "from": f"drawn by {MAKER}"},
                      "surface.json": {"path": str(folder / "surface.json"), "from": "written beside it"}},
            "made_with": [{"what": what, "source": "score"}],
            "tags": {"family": ["decal"], "class": [mark["class"]], "ink": ["one"], "words": [],
                     "size_m": ["{0:.3f}x{1:.3f}".format(*size)], "wear": [mark["kind"]]}}


def plate():
    """(trimesh.Scene, record) of the carrier plate: a `face` quad 1 x 1 m at the front (+z, its texture coordinates
    spanning the unit square, so a decal's page covers it once) and the `edge` part, its back and four sides,
    PLATE_DEEP deep; y up, foot on y 0, centred across and in depth."""
    import trimesh
    half = PLATE_DEEP / 2.0
    corners = np.array([[-0.5, 0.0, half], [0.5, 0.0, half], [0.5, 1.0, half], [-0.5, 1.0, half]])
    face = trimesh.Trimesh(vertices=corners, faces=[[0, 1, 2], [0, 2, 3]], process=False)
    face.visual = trimesh.visual.TextureVisuals(uv=np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]))
    block = trimesh.creation.box(extents=[1.0, 1.0, PLATE_DEEP],
                                 transform=trimesh.transformations.translation_matrix([0.0, 0.5, 0.0]))
    front = block.face_normals[:, 2] > 0.5
    edge = trimesh.Trimesh(vertices=block.vertices, faces=block.faces[~front], process=False)
    scene = trimesh.Scene()
    scene.add_geometry(face, node_name="face", geom_name="face")
    scene.add_geometry(edge, node_name="edge", geom_name="edge")
    record = {"rule": "decal plate", "size": [1.0, 1.0, PLATE_DEEP],
              "parts": [{"name": "face", "takes": "the decal laid on it (a library surface of family decal)"},
                        {"name": "edge", "takes": "the finish of what it is laid on"}],
              "laid": "scaled [wide, tall, deep / PLATE_DEEP] to its mark's size"}
    return scene, record


def plate_row(folder):
    """The plate's glb and record in `folder`, and its take-in row (model/decal_plate)."""
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    scene, record = plate()
    scene.export(folder / "decal_plate.glb")
    (folder / "decal_plate.json").write_text(json.dumps(record, indent=1) + "\n")
    return {"kind": "model", "id": "decal_plate", "title": "Decal plate (code-built carrier, 1 x 1 m face)",
            "files": {"decal_plate.glb": {"path": str(folder / "decal_plate.glb"), "from": f"{MAKER}.plate()"},
                      "decal_plate.json": {"path": str(folder / "decal_plate.json"), "from": "plate()'s parts record"}},
            "made_with": [{"what": f"a 1 x 1 m decal carrier plate {PLATE_DEEP * 1000:.0f} mm deep built in code "
                                   f"({MAKER}): its face takes a library decal, its edge the finish it is laid on; "
                                   f"laid scaled to its mark", "source": "score"}],
            "tags": {"maker": ["code"], "family": ["decal carrier"]}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("marks", help="a JSON list of marks")
    parser.add_argument("--into", required=True)
    arguments = parser.parse_args(argv)
    into = pathlib.Path(arguments.into)
    marks = json.loads(pathlib.Path(arguments.marks).read_text())
    entries = [written(mark, into / "decals" / mark["id"]) for mark in marks] + [plate_row(into / "plate")]
    (into / "listing.json").write_text(json.dumps({
        "world": "world1", "entries": entries,
        "taken_from": f"score's wear decals ({MAKER}): weather marks drawn in code in each place's palette tokens, "
                      "and their carrier plate (2099 ADR-0008 lay plans, 2026-11-26)"}, indent=1) + "\n")
    print(f"wear_decals: {len(marks)} decals and the plate written; {into / 'listing.json'}")

