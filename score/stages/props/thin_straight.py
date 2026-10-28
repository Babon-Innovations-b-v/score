"""The code route for thin straight objects (owner, 2026-10-25, asked "May the framework build exactly this kind
(straight thin things, swept along their path) in code, with a library finish?": "Yes, code-build thin straight
things"): an object whose row is thin and straight is built here, its close-up passed or failed (`coded`), by the
Pixal3D row (pixal_row.py), as its take's files, so the finish route paints it and
the likeness row checks it like any take.

Thin and straight (`thin_straight`): the row's size is slender by the model gate's own rule (tools/props/gates/model.py
shape_class: its middle side under SLENDER_SHARE of its longest), and its name or noun names a straight kind
(STRAIGHT) or a railing (RAILING: its posts and rails built, `railing`), or its row kind glows (`slender_light`: a
lamp on its own stem, its post built here and its head the library's lamp at the head mount; a light bar, a strip light or a string of lights along its cable, its body built here
and its light the library's lamp for its mount, laid by the light layer). Its profile is swept along its longest side, the row's straight length: round (an ellipse filling the two
short sides) for the kinds in ROUND, a rectangle of the two short sides for the rest (posts, beams, pillars).
That straight sweep is for a row whose SAM 3 mask is one straight run (`one_run`); any other mask (a bent pipe
network, a sagging string, a railing's ladder of posts and rails, a bundle of parallel cables: world 1's masks,
2026-10-26) is followed instead (`path_build`): skeletonised, traced, laid in the row's plane at its metres and swept
as round tubes, so the outline holds the build to the thing's own path.

Its take (`write_take`), in WORK/pixal where the batch would bring one: `<take>.glb` (raw) and the slimmed
`<take>-<faces>.glb` and `<take>-final.glb`, all three the same model in the pose it is built in (it knows its up and
its lie, so nothing stands it again: the paint's replay of the finish's turn, labels.finish_turn, finds none),
and `<take>.svviews/` with `input.png`, the row's
concept crop (the close-up stage's crop of its box, tools/props/closeup/stage.py) cut out by the row's own SAM 3 mask
on its concept (`concept_masks`: box_masks.py's instance that best matches the row's box, on one rented card for every
row built at once), which the finish route reads as the take's close-up and the likeness row holds the model to, and
`code.json` naming the build. The cut is by the thing's shape, never its box: the close-up mask's border colour
(`cut_out`) on a busy concept crop kept wall and neighbours: 3 of world 1's 26 builds passed their outline on it
(2026-10-25). The model's one colour is the cut-out's median (the model's own texture, which the finish route measures
and replaces with a library surface). A row SAM 3 finds no instance of is no build: it stays a gap. A path build of a
rigid run (FITTED) carries its fittings made here on its one surface (`fittings`: an elbow at each bend, a tee at
each fork, a clamp every BRACKET_GAP on a wall), finished by the finish route like the rest; score_lib's own pipe
pieces, made by today's library methods, are to replace them (#55: every older piece is withdrawn since 2026-10-21).
"""
import json
import pathlib
import re
import shutil

import numpy as np
from PIL import Image

import score.stages.props.prop_data as prop_data

# The straight kinds, by a word of the row's name or its noun (a plural's s dropped): a coil is not one straight thing,
# so it is not here; a railing is posts and rails (RAILING).
STRAIGHT = frozenset(("pipe", "cable", "conduit", "post", "pole", "rail", "handrail", "rod", "beam", "pillar", "girder",
                      "strut", "mast", "tower", "hose", "wire", "duct", "tube", "bar"))
ROUND = frozenset(("pipe", "cable", "conduit", "pole", "rail", "handrail", "rod", "mast", "hose", "wire", "tube",
                   "string"))
# A railing's kinds: posts standing along its length under a top rail and a mid rail (`railing`; Batch 1's retry: the
# greenhouse's 9.4 m railing piece, every close-up of it failed as a rod).
RAILING = frozenset(("railing", "balustrade", "guardrail", "banister"))
# Metres between a railing's posts at most: a guard's usual post spacing (no library row gives one), so a run of its
# length has ceil(length / POST_GAP) bays.
POST_GAP = 1.5
SEGMENTS = 32
# A mask is one straight run (one_run) while it lies across its long axis within twice its line's width plus this share
# of its length: a lantern string sagging 13% of its span is not; a pipe drawn 2% off true is.
RUN_BEND = 0.05
# A mask's piece under this share of its largest piece's area is a speck SAM 3 left, not a run of the thing (pieces).
PIECE_SHARE = 0.1
# Grid cells across a path build's tube (tubes): enough for a round section, few enough faces for the model gate.
TUBE_CELLS = 6
# Faces a path build is slimmed to at most (a 4 m railing's grid made 54,000), as Pixal3D's takes are slimmed.
PATH_FACES = 20000
# The anchors (score/review/reading.py) of a row lying on a level face: a path build whose box gives no plane
# (its height tied for its thinnest side: a 10 m cable 0.1 by 0.1) is laid in the ground's plane only on one of these,
# else in a wall's (a lantern string 8 by 0.01 by 0.01 hangs: laid on the ground, its 13% sag read 2 to 4 times deeper).
LYING = frozenset(("floor", "ground", "ceiling", "roof"))
# The rigid run kinds that carry fittings (`fittings`): a pipe, conduit, duct or tube is joined by an elbow at a bend
# and a tee at a fork, and held by a clamp on a wall, as a handrail by its brackets; a cable, wire, hose or string bends
# on its own and hangs free.
FITTED = frozenset(("pipe", "conduit", "duct", "tube", "handrail"))
# A bend over this many degrees takes an elbow; a slighter one is the run's own curve (a sag's polygon turns by less).
ELBOW_TURN = 30.0
# A fitting's thickness over its tube's: a socket elbow, tee or clamp stands proud of its pipe by about a wall's
# thickness each side (a DN25 steel pipe 33.7 mm across, its fittings about 42).
FITTING_SHARE = 1.25
# Metres between a wall run's clamps: a usual support spacing for a small pipe or a handrail's brackets (no library
# row gives one), the first half a gap in.
BRACKET_GAP = 1.5
MARK = "code.json"
# The tool files it runs, declared by the Pixal3D row (pixal_row.files): SAM 3's masks, the crop, the close-up's view
# (a path build is seen back from its look-down) and the slender rule.
TOOLS = {"masks": "{repo}/tools/props/scene/box_masks.py", "masks runner": "{repo}/tools/cloud/box_masks_cloud.py",
         "close-up crop": "{repo}/tools/props/closeup/stage.py", "close-up view": "{repo}/tools/props/closeup/check.py",
         "model gate": "{repo}/tools/props/gates/model.py", "glb file": "{repo}/tools/props/glb_file.py"}


def kind_words(row):
    """The row's name's and noun's words, each without a plural's s."""
    words = re.findall(r"[a-z]+", f"{row['name']} {row.get('noun') or ''}".lower())
    return {word[:-1] if word.endswith("s") and word[:-1] in STRAIGHT | RAILING else word for word in words}


def coded(rows):
    """The ids of `rows` ({id: inventory row}: one place's prop objects) that take the code route: every thin straight
    one with a box, its close-up passed or not. Pixal3D's take of a thin straight thing failed its outline whenever its
    close-up passed (2026-10-28: the tube's cable bundles 0.399, the street's lantern string 0.443, the old station's
    antenna mast 0.214), so the qualifying check, not the close-up, decides; and a place never mixes code-built and
    Pixal3D-made runs of one kind (owner, 2026-10-26: "mixing code build and prop pipeline made pipes and cables will
    prob look bad"). The Pixal3D row builds them; prepare's prediction holds them the same way."""
    return {row for row, entry in rows.items() if entry.get("box") and thin_straight(entry)}


def slender(size):
    """The model gate's own slender rule on a size (tools/props/gates/model.py shape_class), its edge taken in: a middle
    side of exactly SLENDER_SHARE of the longest is slender here. The share is a cut-off, not a measured break, and
    readings round to it (the stairwell's 4 m stair railing 1 m tall read exactly 0.25, 2026-10-28)."""
    with prop_data.tools("props/gates", "props/library", "props"):
        import model as model_gate
    smallest, middle, largest = sorted(float(value) for value in size)
    return largest > 0 and middle / largest <= model_gate.SLENDER_SHARE


def thin_straight(row):
    """Whether an inventory row is a thin straight thing (module docstring)."""
    return (bool(kind_words(row) & (STRAIGHT | RAILING)) or slender_light(row)) and slender(row["size"])


def slender_light(row):
    """Whether a row's kind glows (tools/props/scene/lamps.py glows): slender, it is a lamp on its own stem (a street
    lamp, a floodlight mast: its post built here, its head the library's lamp at the head mount) or a straight light
    (a wall light bar, a strip floor light, string lights: its body built here, its light the library's lamp for its
    mount, data/library/lamps.json), lit by the light layer. Batch 1 try 4: every street lamp's close-up failed, and
    the conductor's prediction of 2026-10-26 01:52 left every light bar and string a rod's gap."""
    with prop_data.tools("props/scene"):
        import lamps
    return lamps.glows(row)


def profile(row):
    """"railing", "round" or "rect": what its kind builds (a railing's posts and rails, else the profile it sweeps)."""
    words = kind_words(row)
    return "railing" if words & RAILING else "round" if words & ROUND else "rect"


def build(row, alpha=None):
    """The row's model at its size, in a final take's frame (y up, the longer ground side along
    z: glb_file.squared; the inventory's size is wide, deep, tall), centred on the origin: its profile swept straight
    along its longest side, upright only when it `stands` (its mask, `alpha`, its cut's, says so too), or, when its
    mask is not one straight run, its mask's own path (`path_build`)."""
    import trimesh
    if alpha is not None and alpha.any() and not one_run(alpha):
        return path_build(row, alpha)
    wide, deep, tall = (float(value) for value in row["size"])
    extents = np.array([min(wide, deep), tall, max(wide, deep)])
    if tall >= max(wide, deep) and not stands(row, alpha):  # the reading's box stood a run its picture shows lying
        extents = np.array([min(wide, deep), max(wide, deep), tall])
    along = int(np.argmax(extents))
    if profile(row) == "round":
        mesh = trimesh.creation.cylinder(radius=0.5, height=1.0, sections=SEGMENTS)  # along z, centred
        mesh.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], np.eye(3)[along]))
    else:
        mesh = trimesh.creation.box(extents=[1.0, 1.0, 1.0])
    mesh.apply_scale(extents / mesh.extents)
    mesh.apply_translation(-mesh.bounds.mean(0))
    return mesh


def slant(alpha):
    """The degrees a mask's long axis (second moments) rises from level in the picture, -90 to 90."""
    down, across = np.nonzero(alpha)
    down, across = down - down.mean(), across - across.mean()
    return float(0.5 * np.degrees(np.arctan2(2 * (across * down).mean(), (across ** 2).mean() - (down ** 2).mean())))


def stands(row, alpha):
    """Whether a straight run stands upright: its box's longest side is its height and its mask (when there is one)
    rises within 45 degrees of upright. The direction is the picture's, the metres the box's: a reading's box stood
    pipes its picture shows lying (the greenhouse's and the quarters' pipes, outlines 0.02 and 0.03 on 2026-10-26),
    and a view tilts an upright thing, never lays it down; a level thing may show at any slant (one running away from
    the camera stands steep), so a level box stays level."""
    upright = float(row["size"][2]) >= max(float(value) for value in row["size"])
    return upright and (alpha is None or not alpha.any() or abs(slant(alpha)) >= 45.0)


def pieces(alpha):
    """The mask but its specks: its pieces at least PIECE_SHARE of its largest's area."""
    from scipy import ndimage
    labels, count = ndimage.label(alpha, structure=np.ones((3, 3)))
    if count == 0:
        return alpha
    areas = ndimage.sum(alpha, labels, range(1, count + 1))
    return np.isin(labels, 1 + np.flatnonzero(areas >= PIECE_SHARE * areas.max()))


def one_run(alpha):
    """Whether a mask is one straight run: one piece lying across its long axis within twice its line's width (its
    area over its length) plus RUN_BEND of its length. A sag, an elbow, a ladder of posts and rails or a band of
    parallel lines is not: path_build follows it."""
    from scipy import ndimage
    kept = pieces(alpha)
    if ndimage.label(kept, structure=np.ones((3, 3)))[1] != 1:
        return False
    down, across = np.nonzero(kept)
    points = np.c_[across, down].astype(float)
    points -= points.mean(0)
    axes = np.linalg.svd(points, full_matrices=False)[2]
    length = np.ptp(points @ axes[0]) + 1
    return np.ptp(points @ axes[1]) + 1 <= 2 * len(points) / length + RUN_BEND * length


def traces(skeleton):
    """The skeleton's runs, each a list of (x, y) pixels from an end or a fork to the next one (a loop with neither
    from any of its pixels round to it)."""
    points = {(int(across), int(down)) for down, across in zip(*np.nonzero(skeleton))}
    steps = [(across, down) for across in (-1, 0, 1) for down in (-1, 0, 1) if across or down]

    def around(point):
        return [(point[0] + across, point[1] + down) for across, down in steps
                if (point[0] + across, point[1] + down) in points]

    nodes = {point for point in points if len(around(point)) != 2}
    walked, runs = set(), []

    def walk(start, step):
        run = [start, step]
        walked.update({(start, step), (step, start)})
        while run[-1] not in nodes:
            ahead = [point for point in around(run[-1]) if point != run[-2] and (run[-1], point) not in walked]
            if not ahead:
                break
            walked.update({(run[-1], ahead[0]), (ahead[0], run[-1])})
            run.append(ahead[0])
        return run

    for start in sorted(nodes):
        runs.extend(walk(start, step) for step in around(start) if (start, step) not in walked)
    left = points - {point for run in runs for point in run}
    while left:  # a closed loop: no end or fork on it
        start = min(left)
        nodes.add(start)
        runs.append(walk(start, around(start)[0]))
        left -= {start, *runs[-1]}
    return runs


def least_tube():
    """The thinnest tube a path build is made: the model gate's wall (tools/props/gates/model.py THINNEST_LIMIT) over
    the share of its thickness a solid one reads through (SOLID_SHARE: its inward rays cross it whole), so a solid
    tube is judged as solid, as a flat sheet is, and a 1 mm wire is never laid thinner than the gate can pass."""
    with prop_data.tools("props/gates", "props/library", "props"):
        import model as model_gate
    return model_gate.THINNEST_LIMIT / model_gate.SOLID_SHARE


def upward(row):
    """The build axis the picture's up is laid along: 1, a wall's plane, or 0, the ground's for a row whose height is
    its one thinnest side, or tied for it on a level face (LYING: a tie alone names no plane)."""
    wide, deep, tall = (float(value) for value in row["size"])
    if tall > min(wide, deep):
        return 1
    return 0 if tall < min(wide, deep) or row.get("anchor") in LYING else 1


def lifted(runs, row, width):
    """(the runs' points in the build's frame, metres; the tube's thickness): the picture's runs, their direction and
    path the picture's own, laid in a wall's plane (across the picture z, up it y) or the ground's (up the picture x:
    `upward`), seen back from the close-up's look-down (the outline's view, tools/props/closeup/check.py look_down:
    its height foreshortened by its cosine, a ground run by its sine); one scale for the picture, so the run's longest
    reach is the row's longest side and its other reach the path's own, never the box's (a thin run's box is its
    thickness on its two short sides: a sagging string 8 by 0.01 by 0.01); the tube `width` picture pixels thick at
    that scale, at most the row's thinnest side (its thickness: a 5 m drape's box 1 m deep is no 1 m tube) and at
    least `least_tube`."""
    with prop_data.tools("props/closeup", "props", "cloud"):
        import check
    sides = sorted(float(value) for value in row["size"])
    up = upward(row)
    down = np.radians(check.look_down(row["size"]))
    seen = np.cos(down) if up == 1 else np.sin(down)
    flat = np.concatenate(runs) * [1.0, 1.0 / seen]
    low, span = flat.min(0), np.maximum(np.ptp(flat, axis=0), 1.0)
    scale = sides[2] / (span.max() + width)
    thick = max(min(width * scale, sides[0]), least_tube())
    scale = (sides[2] - thick) / span.max()
    laid = []
    for run in runs:
        point = np.zeros((len(run), 3))
        point[:, 2] = (run[:, 0] - low[0] - span[0] / 2) * scale
        point[:, up] = -(run[:, 1] / seen - low[1] - span[1] / 2) * scale  # the picture's down is the world's up
        laid.append(point)
    return laid, thick


def on_wall(row):
    """Whether a row hangs on a wall: anchored to one, or on a row its id names a wall or facade (reading.py's
    anchors: `wall`, `on:<id>`)."""
    anchor = str(row.get("anchor") or "")
    return anchor == "wall" or anchor.startswith("on:") and bool({"wall", "facade"} & set(re.findall(r"[a-z]+",
                                                                                                    anchor[3:])))


def leg(start, toward, length):
    """The point `length` metres from `start` toward `toward`, at most halfway there."""
    step = toward - start
    reach = float(np.linalg.norm(step))
    return start + step / reach * min(length, reach / 2) if reach > 0 else start


def fittings(laid, row, thick):
    """{"elbows", "tees", "clamps"}: the short segments (point pairs) each fitting of a FITTED kind is swept along,
    FITTING_SHARE of the tube thick: an elbow's two legs, a thickness long, at each bend of a run over ELBOW_TURN; a
    tee's legs at each fork (three runs or more meeting); a clamp half a thickness long every BRACKET_GAP metres along
    each run of a row on a wall (`on_wall`) laid in a wall's plane. None for any other kind: what the mask does not
    show (a valve) is never added."""
    found = {"elbows": [], "tees": [], "clamps": []}
    if not kind_words(row) & FITTED:
        return found
    for run in laid:
        for before, point, after in zip(run, run[1:], run[2:]):
            ahead, back = after - point, point - before
            cosine = ahead @ back / max(np.linalg.norm(ahead) * np.linalg.norm(back), 1e-12)
            if np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))) > ELBOW_TURN:
                found["elbows"] += [(leg(point, before, thick), point), (point, leg(point, after, thick))]
    ends = {}
    for run in laid:
        for end, next_point in ((run[0], run[1]), (run[-1], run[-2])):
            ends.setdefault(tuple(np.round(end, 6)), []).append((end, next_point))
    for meeting in ends.values():
        if len(meeting) >= 3:
            found["tees"] += [(end, leg(end, next_point, thick)) for end, next_point in meeting]
    if on_wall(row) and upward(row) == 1:
        for run in laid:
            lengths = np.linalg.norm(np.diff(run, axis=0), axis=1)
            along = np.concatenate([[0.0], np.cumsum(lengths)])
            for at in np.arange(BRACKET_GAP / 2, along[-1], BRACKET_GAP):
                piece = min(int(np.searchsorted(along, at, side="right")) - 1, len(lengths) - 1)
                way = (run[piece + 1] - run[piece]) / max(lengths[piece], 1e-12)
                middle = run[piece] + way * (at - along[piece])
                found["clamps"].append((middle - way * thick / 4, middle + way * thick / 4))
    return found


def path_build(row, alpha):
    """The row's model following its mask's own path (owner's ask, 2026-10-26: bent pipe networks, a sagging lantern
    string, a railing's posts and rails, a bundle of parallel cables were each built as one straight sweep and failed
    their outline): the mask skeletonised and traced into its runs (`traces`, forks kept), each run's bends kept to
    within half its line's width, laid in the row's plane at its metres (`lifted`), and a round tube of the line's
    thickness swept along them all as one closed surface (`tubes`), so a sag stays a sag, an elbow a bend, a ladder
    its posts and rails and a band of lines its tubes; a rigid run's fittings (`fittings`: elbows, tees, wall clamps)
    made in code on the same surface, its finish the finish route's like the rest."""
    from skimage.measure import approximate_polygon
    from skimage.morphology import skeletonize
    kept = pieces(alpha)
    skeleton = skeletonize(kept)
    width = kept.sum() / skeleton.sum()
    runs = [approximate_polygon(np.asarray(run, dtype=float), tolerance=1.0)
            for run in traces(skeleton) if len(run) > 1]
    laid, thick = lifted(runs, row, width)
    mesh = tubes(laid, thick, [pair for pairs in fittings(laid, row, thick).values() for pair in pairs])
    return mesh.apply_translation(-mesh.bounds.mean(0))


def tubes(laid, thick, fitted=()):
    """One closed surface round the runs `laid` (points in the build's frame, all in one axis plane), `thick` across,
    and round the `fitted` segments (point pairs in that plane), FITTING_SHARE of it across: the plane's distance to
    the nearest run and to the nearest fitting, drawn on a grid TUBE_CELLS cells across the tube, made round through
    the third axis and cut at each one's radius (marching cubes), so joints, forks and fittings are one surface with no
    shell inside another (the model gate's wall rays read overlapping tubes 0.3 mm thick)."""
    import trimesh
    from scipy import ndimage
    from skimage.measure import marching_cubes
    flat = np.concatenate(laid)
    plane = [axis for axis in range(3) if np.ptp(flat[:, axis]) > 0 or axis == 2][:2]
    if len(plane) < 2:
        plane = [1, 2]
    across = 3 - sum(plane)
    cell, radius = thick / TUBE_CELLS, thick / 2
    outer = radius * FITTING_SHARE if fitted else radius
    low = flat[:, plane].min(0) - outer - 2 * cell
    shape = np.ceil((np.ptp(flat[:, plane], axis=0) + 2 * outer + 4 * cell) / cell).astype(int) + 1
    steps = int(np.ceil(outer / cell)) + 2
    depth = np.arange(-steps, steps + 1) * cell

    def round_of(lines, reach_radius):
        """The signed distance to tubes `reach_radius` round `lines` (each a list of points) on the grid."""
        from PIL import ImageDraw
        centre = Image.new("1", (int(shape[0]), int(shape[1])), 1)
        draw = ImageDraw.Draw(centre)
        for points in lines:
            draw.line([tuple(point) for point in (np.asarray(points)[:, plane] - low) / cell], fill=0)
        reach = ndimage.distance_transform_edt(np.asarray(centre).T) * cell  # [first plane axis, second]
        return np.sqrt(reach[:, :, None] ** 2 + depth[None, None, :] ** 2) - reach_radius

    field = round_of(laid, radius)
    if fitted:
        field = np.minimum(field, round_of(fitted, outer))
    vertices, faces = marching_cubes(field, 0.0, spacing=(cell, cell, cell), allow_degenerate=False)[:2]
    points = np.zeros_like(vertices)
    points[:, plane[0]], points[:, plane[1]] = vertices[:, 0] + low[0], vertices[:, 1] + low[1]
    points[:, across] = vertices[:, 2] + depth[0]
    mesh = trimesh.Trimesh(points, faces, process=True)
    if np.linalg.det(np.eye(3)[[plane[0], plane[1], across]]) < 0:
        mesh.invert()
    return mesh.simplify_quadric_decimation(face_count=PATH_FACES) if len(mesh.faces) > PATH_FACES else mesh


def railing(thick, tall, length):
    """The boxes of a railing `length` metres along z, `tall` up y, `thick` across x, centred on the origin: square posts `thick`
    across at both ends and at most POST_GAP apart between, a top rail of the same section along their tops and a mid
    rail of half of it at half the height."""
    import trimesh
    bays = max(1, int(np.ceil(length / POST_GAP)))
    posts = [trimesh.creation.box(extents=[thick, tall, thick]).apply_translation([0.0, 0.0, along])
             for along in np.linspace(-(length - thick) / 2, (length - thick) / 2, bays + 1)]
    top = trimesh.creation.box(extents=[thick, thick, length]).apply_translation([0.0, (tall - thick) / 2, 0.0])
    middle = trimesh.creation.box(extents=[thick / 2, thick / 2, length])
    return [*posts, top, middle]


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


def mask_jobs(rows, concepts):
    """box_masks.py's jobs asking each row's own mask: one a concept, each row by its name and noun in its box."""
    jobs = {}
    for name, row in sorted(rows.items()):
        words = list(dict.fromkeys(word for word in (row["name"], row.get("noun")) if word))
        jobs.setdefault(str(concepts[name]), []).append({"key": name, "nouns": words, "box": row["box"], "mask": True})
    return [{"picture": picture, "rows": asked} for picture, asked in jobs.items()]


def concept_masks(rows, concepts, folder):
    """{row: its SAM 3 mask on its concept} of the inventory `rows` ({id: row}; `concepts`: {id: its concept}), made
    on one rented card (box_masks_cloud.py, its spend in the ledger); a row SAM 3 found nothing of is left out."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "jobs.json").write_text(json.dumps(mask_jobs(rows, concepts), indent=1))
    with prop_data.tools("props/scene", "props", "cloud"):
        import box_masks_cloud
        box_masks_cloud.mask(folder / "jobs.json", folder / "masks.json")
    return {name: folder / "masks.masks" / f"{name}.png" for name in rows
            if (folder / "masks.masks" / f"{name}.png").exists()}


def cut_by_mask(concept, box, mask):
    """The concept's crop of `box` as the close-up stage crops it (stage.crop) with the row's mask as alpha, or None
    when the mask holds nothing inside it."""
    with prop_data.tools("props/closeup", "props", "cloud"):
        import stage
    pixels = np.asarray(stage.crop(Image.open(concept), box))
    alpha = np.asarray(stage.crop(Image.open(mask), box).convert("L")) > 127
    return Image.fromarray(np.dstack([pixels, np.where(alpha, 255, 0).astype(np.uint8)])) if alpha.any() else None


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


def write_take(take, row, picture, faces, pixal, mask):
    """The take's files (module docstring) in `pixal` from `picture`, its concept crop cut out by its SAM 3 `mask`."""
    import trimesh
    factor = [*(colour(picture) / 255.0), 1.0]
    views = pixal / f"{take}.svviews"
    views.mkdir(parents=True, exist_ok=True)
    picture.save(views / "input.png")
    alpha = np.asarray(picture.convert("RGBA"))[..., 3] > 127
    mesh = build(row, alpha)
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(baseColorFactor=factor))
    for name in (f"{take}.glb", f"{take}-{faces}.glb", f"{take}-final.glb"):  # raw, slimmed, final: never stood
        mesh.export(pixal / name)
    path = alpha.any() and not one_run(alpha)
    mark = {"route": "code", "rule": "thin straight (owner, 2026-10-25)", "profile": "path" if path else profile(row),
            "size": row["size"], "mask": str(mask)}
    (views / MARK).write_text(json.dumps(mark, indent=1))
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
