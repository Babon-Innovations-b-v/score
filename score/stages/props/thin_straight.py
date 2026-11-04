"""The code route for thin straight objects (owner, 2026-10-25, asked "May the framework build exactly this kind
(straight thin things, swept along their path) in code, with a library finish?": "Yes, code-build thin straight
things"): an object whose row is thin and straight is built here, its close-up passed or failed (`coded`), by the
Pixal3D row (pixal_row.py), as its take's files, so the finish route paints it and
the likeness row checks it like any take.

Thin and straight (`thin_straight`): the row's size is slender by the model gate's own rule (tools/props/gates/model.py
shape_class: its middle side under SLENDER_SHARE of its longest), and its name or noun names a straight kind
(STRAIGHT) or a railing (RAILING: its posts and rails built, `railing`), or its row kind glows (`slender_light`: a
lamp on its own stem, its post built here and its head the library's lamp at the head mount; a light bar, a strip light or a string of lights along its cable, its body built here
and its light the library's lamp for its mount, laid by the light layer). Every such row is built along its SAM 3
mask's centreline (`path_build`): skeletonised, a ball at each skeleton point as wide as the mask is there, the union
of them laid in its picture's plane at its metres, at most the row's thinnest side deep, and leaned to face the
outline's view, so the outline holds the build to the thing's own path and width, straight or not (a bent pipe
network, a sagging string, a railing's ladder of posts and rails, a bundle of parallel cables: world 1's masks,
2026-10-26; a post's flared foot, a lamp post's head). A straight sweep of the box for a mask that looked one
straight run hid a wide band's bends (walkway's wall pipes 0.438) and took its section from the wrong side of its box
(stairwell's conduit 0.346): of round 25's 57 code builds 11 failed their outline swept so, none along the
centreline (#36, 2026-10-30).
A row with no mask is swept straight along its longest side at its box's section (round for the kinds in ROUND, a
rectangle for the rest).

Its take (`write_take`), in WORK/pixal where the batch would bring one: `<take>.glb` (raw) and the slimmed
`<take>-<faces>.glb` and `<take>-final.glb`, all three the same model in the pose it is built in (it knows its up and
its lie, so nothing stands it again: the paint's replay of the finish's turn, labels.finish_turn, finds none),
and `<take>.svviews/` with `input.png`, the row's
concept crop (the close-up stage's crop of its box, tools/props/closeup/stage.py) cut out by the row's own SAM 3 mask
on its concept (`concept_masks`: box_masks.py's instance that best matches the row's box, on one rented card for every
row built at once), which the finish route reads as the take's close-up and the likeness row holds the model to, and
`code.json` naming the build. The cut is by the thing's shape, never its box: the close-up mask's border colour
(`cut_out`) on a busy concept crop kept wall and neighbours: 3 of world 1's 26 builds passed their outline on it
(2026-10-25). The model carries its cut-out as its own texture (`textured`), as a Pixal3D take carries the picture it
was made from: laid on from the way its outline matches the crop, on a sweep built in SWEEP_RINGS rings, so the finish
route's views see each colour where it lies, its list labels those regions with the close-up's finishes and its split
gives each finish its part; the texture is measured, never shown (every finish a library surface). Made in one colour
on 12 faces, a lamp bar's metal end caps were no part's and its likeness check's "close-up parts present" could never
pass (2026-10-29). A build already made is made again from its own crop by every run of the Pixal3D row (`rebuilt`),
so a builder's fix reaches it (a lamp kept from before its section was the picture's read 0.408, 2026-10-29). A row SAM 3 finds no instance of is no build: it stays a gap. A path build of a
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
# A row this flat (its thinnest side under this share of its longest) is spread across a floor, wall or ceiling: a
# straight kind so is a network (`network`), any other a sheet (flat_sheet.SHEET_SHARE).
FLAT_SHARE = 0.05
# Metres between a railing's posts at most: a guard's usual post spacing (no library row gives one), so a run of its
# length has ceil(length / POST_GAP) bays.
POST_GAP = 1.5
SEGMENTS = 32
# A run off a fork with a free end shorter than this many of its widths is a spur of the mask's ragged edge (`spine`):
# a finger on a hand-like blob, not a run of the thing.
SPUR_WIDTHS = 2.0
# A railing's run drawn wider than this many of its rails is the band of its posts and what is seen between them, built
# as posts and rails (`ladder`), never a slab.
LADDER_WIDTHS = 3.0
# A hole inside a mask under this many of its drawn widths squared is a pinhole of its ragged cut (`filled`).
HOLE_WIDTHS = 2.0
# A band at most this share of its length across (`balls`): the model gate's slender share (tools/props/gates/model.py
# SLENDER_SHARE), so a mask drawn fatter than a thin thing never builds a chunky one.
SECTION_SHARE = 0.25
# A mask's piece under this share of its largest piece's area is a speck SAM 3 left, not a run of the thing (pieces).
PIECE_SHARE = 0.1
# Grid cells across a path build's tube (swelled): enough for a round section, few enough faces for the model gate.
TUBE_CELLS = 6
# Faces a path build is slimmed to at most (a 4 m railing's grid made 54,000), as Pixal3D's takes are slimmed.
PATH_FACES = 20000
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
# Rings a straight sweep is built in along its length (`prism`): its faces must be small enough for the finish route's
# split to give a finish its own part (a lamp bar's end caps, a pipe's valve paint, a tube's glazing band). Swept in one
# length, a bar was 12 faces and its finish route split it into one part (2026-10-29: airlock's wall lamp, its close-up's
# grey metal trim owned by no part); 128 rings are about 6 mm on its 0.8 m and 8,256 faces on any sweep.
SWEEP_RINGS = 128
# The crop's turns in the picture's plane (in degrees, every TEXTURE_TURN) the texture's projection tries (`laid_on`).
TEXTURE_TURN = 5
# The 26 ways a code build is seen from when its crop is laid on it as its texture (`laid_on`): a cube's faces, edges
# and corners, so an opposite way sees the crop mirrored.
TEXTURE_WAYS = tuple(np.array(way, dtype=float) / np.linalg.norm(way) for way in
                     ((x, y, z) for x in (0, -1, 1) for y in (0, 1, -1) for z in (1, -1, 0)) if any(way))
MARK = "code.json"
# The texture a build carries, named in its mark (`write_take`): a build whose mark names none is made again from its
# own crop (pixal_row.code_builds), so the builds made in one colour before 2026-10-29 carry their crop too.
TEXTURE = "its concept crop, laid on from the way its outline matches"
# The tool files it runs, declared by the Pixal3D row (pixal_row.files): SAM 3's masks, the crop, the close-up's view
# (a path build is leaned to face its look-down) and the slender rule.
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
    """Whether an inventory row is a thin straight thing (module docstring), or a network of them (`network`)."""
    return (bool(kind_words(row) & (STRAIGHT | RAILING)) or slender_light(row)) and slender(row["size"]) or network(row)


def network(row):
    """Whether a row is a network of straight runs: its kind (its noun, else its name) a straight one, its size not
    slender but spread flat (its thinnest side under FLAT_SHARE of its longest). Its box spans the runs, not one: the
    engineroom's pipes, 9.3 by 10.9 by 0.2 m, went to flat_sheet as one slab, DINOv2 0.041 (env1 round 35). Built
    along its mask's centreline, each run held across to the row's thinnest side (`run_holds`); a flag on a pole, a
    coiled cable or a computer tower is no network."""
    kind = kind_words({"name": row.get("noun") or row.get("name") or ""})
    smallest, _, largest = sorted(float(value) for value in row.get("read_size") or row["size"])
    return bool(kind & STRAIGHT) and not slender(row["size"]) and smallest < FLAT_SHARE * largest


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
    z: glb_file.squared; the inventory's size is wide, deep, tall), centred on the origin: along its mask's (`alpha`,
    its cut's) centreline (`path_build`), then turned in the picture's plane so its long axis follows its row
    (`slanted` undone) and held across it to its row's section (`held_across`), or, with no mask, its profile swept
    straight along its longest side."""
    import trimesh
    if alpha is not None and alpha.any():
        return path_build(row, alpha, axis_turn(row, alpha)).apply_transform(
            as_built(row, alpha) @ np.linalg.inv(slanted(row, alpha)))
    wide, deep, tall = (float(value) for value in row["size"])
    extents = np.array([min(wide, deep), tall, max(wide, deep)])
    along = int(np.argmax(extents))
    mesh = prism(section(profile(row)), SWEEP_RINGS)  # along z, centred
    mesh.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], np.eye(3)[along]))
    mesh.apply_scale(extents / mesh.extents)
    mesh.apply_translation(-mesh.bounds.mean(0))
    return mesh


def section(shape):
    """A sweep's cross-section, SEGMENTS points anticlockwise one unit across: a circle for "round", else a square
    with SEGMENTS / 4 points along each side (so a finish across a post's face has faces of its own too)."""
    if shape == "round":
        turns = np.linspace(0.0, 2 * np.pi, SEGMENTS, endpoint=False)
        return 0.5 * np.c_[np.cos(turns), np.sin(turns)]
    steps = np.linspace(-0.5, 0.5, SEGMENTS // 4, endpoint=False)
    return np.vstack([np.c_[steps, np.full_like(steps, -0.5)], np.c_[np.full_like(steps, 0.5), steps],
                      np.c_[-steps, np.full_like(steps, 0.5)], np.c_[np.full_like(steps, -0.5), -steps]])


def prism(outline, rings):
    """One closed surface swept along z from -0.5 to 0.5: the `outline` (anticlockwise points in x and y) at `rings` + 1
    stations, side faces between each two and a fan over each end."""
    import trimesh
    count = len(outline)
    stations = np.linspace(-0.5, 0.5, rings + 1)
    points = np.vstack([np.c_[outline, np.full(count, station)] for station in stations] + [[0, 0, -0.5], [0, 0, 0.5]])
    ring, turn = np.meshgrid(np.arange(rings), np.arange(count), indexing="ij")
    here, on = ring * count + turn, ring * count + (turn + 1) % count
    sides = np.vstack([np.c_[here.ravel(), on.ravel(), (on + count).ravel()],
                       np.c_[here.ravel(), (on + count).ravel(), (here + count).ravel()]])
    low, high = len(points) - 2, len(points) - 1
    top = rings * count
    ends = np.vstack([np.c_[np.full(count, low), (np.arange(count) + 1) % count, np.arange(count)],
                      np.c_[np.full(count, high), top + np.arange(count), top + (np.arange(count) + 1) % count]])
    return trimesh.Trimesh(points, np.vstack([sides, ends]), process=True)


def pieces(alpha):
    """The mask but its specks: its pieces at least PIECE_SHARE of its largest's area."""
    from scipy import ndimage
    labels, count = ndimage.label(alpha, structure=np.ones((3, 3)))
    if count == 0:
        return alpha
    areas = ndimage.sum(alpha, labels, range(1, count + 1))
    return np.isin(labels, 1 + np.flatnonzero(areas >= PIECE_SHARE * areas.max()))


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


def slant(alpha):
    """The degrees a mask's long axis (second moments) rises from level in the picture, -90 to 90."""
    down, across = np.nonzero(alpha)
    down, across = down - down.mean(), across - across.mean()
    return float(0.5 * np.degrees(np.arctan2(2 * (across * down).mean(), (across ** 2).mean() - (down ** 2).mean())))


def axis_turn(row, alpha):
    """The degrees (anticlockwise in the picture, as PIL turns) that lay a mask's long axis along its row: upright when
    the row stands (its height its longest side) and its mask rises within 45 degrees of upright, else level. The
    direction is the row's, the picture's slant its view's: a ceiling rail running away from the camera is drawn
    steep, and built in the picture's slant it was laid 38 to 60 degrees off level and the docking airlock's
    resting failed on 22 objects (round 32, 2026-10-30); a level box stays level, and a reading's box stood over a
    run its mask shows lying is laid lying (the greenhouse's and the quarters' pipes, 2026-10-26)."""
    turn = slant(pieces(alpha))
    upright = float(row["size"][2]) >= max(float(value) for value in row["size"])
    return turn - np.copysign(90.0, turn) if upright and abs(turn) >= 45.0 else turn


def slanted(row, alpha):
    """The turn (4 by 4, about the picture's normal x) from a build laid along its row to its picture's slant: its
    mask `alpha`'s axis_turn in the build's frame (across the picture z, up it y)."""
    angle = np.radians(axis_turn(row, alpha))
    turn = np.eye(4)
    turn[1:3, 1:3] = [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
    return turn


def held_across(row, alpha):
    """The scale (4 by 4) holding a slender row's build, laid along its row (`slanted` undone), to its row's section
    across its run: its reach across the run (y, or z where axis_turn stands it) times the row's thinnest side over
    its tube's drawn width at the picture's scale along it (`path_build`: twice its balls' median radius), at most
    one. A picture's scale is its length's, and a run going away from the camera is foreshortened along its length
    but not across it: the walkway's 12 m wall pipes, on a 0.1 m section, were built 2.9 m tall, its ceiling duct
    (0.3 m) 3.4 m (#36, 2026-10-31). Its bends and sag across keep their share of its tube. A row that is not
    slender keeps its picture's metres (the bake fits it to its row side by side); nor does a railing, its section its
    rails' (`ladder`), its band across its posts' height."""
    from skimage.morphology import skeletonize
    hold = np.eye(4)
    if alpha is None or not alpha.any() or not slender(row["size"]) or profile(row) == "railing":
        return hold
    kept = pieces(alpha)
    skeleton = skeletonize(kept)
    turn = axis_turn(row, alpha)
    scale, reach = picture_scale(row, kept, turn)
    tube = float(np.median(2 * balls(kept, skeleton, scale, reach)[1][skeleton])) * scale
    across = 2 if turn != slant(kept) else 1  # stood upright by axis_turn's quarter turn: across is z
    hold[across, across] = min(1.0, min(float(value) for value in row["size"]) / max(tube, 1e-9))
    return hold


def as_built(row, alpha):
    """The turn (4 by 4) from a build laid along its row in its picture's plane to the pose it is built in: held across
    its run (`held_across`), and a network lying on a floor or under a ceiling (`network`, its height its thinnest
    side) laid down, its picture's plane level and its normal up (the engineroom's pipes, 0.2 m tall over 9.3 by
    10.9, would stand 3 m up a wall)."""
    lay = np.eye(4)
    if network(row) and float(row["size"][2]) <= min(float(value) for value in row["size"]):
        lay[:2, :2] = [[0.0, -1.0], [1.0, 0.0]]  # x, the picture's normal, up; its up across the ground
    return lay @ held_across(row, alpha)


def view(row, alpha):
    """The turn (4 by 4) the likeness row sees a code build by: across its run as the picture draws it
    (`held_across` undone), back into its picture's slant (`slanted`) and leaned to face the look-down (`facing`), so
    its outline is held to its crop as the picture draws it while the model keeps its row's pose and section."""
    return facing(row) @ slanted(row, alpha) @ np.linalg.inv(as_built(row, alpha))


def facing(row):
    """The turn (4 by 4) leaning a build laid in the picture's plane (x its normal) back about z by the close-up's
    look-down (the outline's view, tools/props/closeup/check.py look_down), its top away from a camera on -x, so that
    view sees the picture's own path square on; the likeness row's view of a code build only (`view`), never the
    model's own pose, which is its row's (a post leaned 15 degrees stands on no feet): a plane stood
    upright and stretched by the look-down's cosine left
    the view's keystone in it (the old station's cables, laid so, 0.42; leaned, 0.66), and one laid on the ground
    showed a level run squashed to the look-down's sine (0.068, 2026-10-28)."""
    with prop_data.tools("props/closeup", "props", "cloud"):
        import check
    down = np.radians(check.look_down(row["size"]))
    turn = np.eye(4)
    turn[:2, :2] = [[np.cos(down), np.sin(down)], [-np.sin(down), np.cos(down)]]
    return turn


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
    each run of a row on a wall (`on_wall`). None for any other kind: what the mask does not
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
    if on_wall(row):
        for run in laid:
            lengths = np.linalg.norm(np.diff(run, axis=0), axis=1)
            along = np.concatenate([[0.0], np.cumsum(lengths)])
            for at in np.arange(BRACKET_GAP / 2, along[-1], BRACKET_GAP):
                piece = min(int(np.searchsorted(along, at, side="right")) - 1, len(lengths) - 1)
                way = (run[piece + 1] - run[piece]) / max(lengths[piece], 1e-12)
                middle = run[piece] + way * (at - along[piece])
                found["clamps"].append((middle - way * thick / 4, middle + way * thick / 4))
    return found


def path_build(row, alpha, turn=0.0):
    """The row's model swept along its mask's centreline (owner's ask, 2026-10-26: bent pipe networks, a sagging
    lantern string, a railing's posts and rails, a bundle of parallel cables were each built as one straight sweep and
    failed their outline): each run of the mask's skeleton, its spurs dropped, a straight polyline at one width of its
    own (`spine`), so a sag stays a sag, an elbow a bend, a ladder its posts and rails, a separate foot its own width,
    and a railing drawn as one band its posts and rails (`ladder`); the union of those clean tubes one closed surface
    (`swelled`). A ball at each skeleton point as wide as the mask was there made every ragged mask edge a lump and
    every spur a finger: the stairwell's conduit and railing, the quarters' desk cables, the hub's cable bundles, the
    street's lamp posts and the base's link tube rendered as black hand-like blobs (eyes-on review, 2026-11-02; the
    likeness row's `swept clean` check fails such a model now). Laid in the picture's plane at one scale, the mask's
    longest reach (as it lies turned `turn` degrees along its row, `axis_turn`) the row's longest side and its other
    reach the path's own, never a box side (a thin run's box is its thickness on its two short sides: a sagging string
    8 by 0.01 by 0.01; a railing curving round a floor drawn from above shows its plan's depth as its picture's height:
    the greenhouse's held to its 1 m read 0.023, 2026-10-28); held at most the row's thinnest side deep through the
    picture's plane (a 5 m drape's box 1 m deep is no 1 m tube, a flat wall run of pipes no round one), never under
    `least_tube`, in its row's pose (the likeness row sees it in its picture's, `view`); a rigid run's fittings
    (`fittings`: elbows, tees, wall clamps on its runs) made in code on the same surface, its finish the finish
    route's like the rest."""
    from skimage.morphology import skeletonize
    from scipy import ndimage
    from PIL import ImageDraw
    kept = filled(pieces(alpha))
    skeleton = skeletonize(kept)
    sides = sorted(float(value) for value in row["size"])
    scale, reach = picture_scale(row, kept, turn)
    _, ball = balls(kept, skeleton, scale, reach)
    if network(row):
        _, ball = balls(kept, skeleton, scale, reach, run_holds(row, skeleton, ball, scale))
    runs = spine(skeleton, ball)
    if profile(row) == "railing":
        rail = max(sides[0], least_tube()) / 2 / scale
        runs = [part for points, radius in runs for part in
                (ladder(points, radius, rail, POST_GAP / scale, kept) if 2 * radius > LADDER_WIDTHS * 2 * rail
                 else [(points, radius)])]
    lengths = np.array([max(float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum()), 1.0) for points, _ in runs])
    radii = np.array([radius for _, radius in runs])
    width = 2 * float(radii[np.argsort(radii)][np.searchsorted(np.cumsum(lengths[np.argsort(radii)]),
                                                                lengths.sum() / 2)])  # its length's median width
    margin = int(np.ceil(radii.max() * FITTING_SHARE)) + 2  # room round the picture for the tubes and fittings
    drawn = Image.new("I", (kept.shape[1] + 2 * margin, kept.shape[0] + 2 * margin), 0)
    draw = ImageDraw.Draw(drawn)
    for number, (points, _) in enumerate(runs, 1):
        draw.line([(float(x) + margin, float(y) + margin) for x, y in points], fill=number, width=1)
    lines = np.asarray(drawn)
    off, (near_down, near_across) = ndimage.distance_transform_edt(lines == 0, return_indices=True)
    ball = np.concatenate([[0.0], radii])[lines[near_down, near_across]]
    laid = [np.c_[np.zeros(len(points)), -(points[:, 1] + margin) * scale, (points[:, 0] + margin) * scale]
            for points, _ in runs]
    fitted = [pair for pairs in fittings(laid, row, width * scale).values() for pair in pairs]
    mesh = swelled(off, ball, [[(point[2] / scale, -point[1] / scale) for point in pair] for pair in fitted], width,
                   scale)
    deep = max(sides[0], least_tube())
    mesh.apply_transform(np.diag([min(1.0, deep / max(float(np.ptp(mesh.vertices[:, 0])), 1e-9)), 1.0, 1.0, 1.0]))
    return mesh.apply_translation(-mesh.bounds.mean(0))


def filled(kept):
    """The mask with its pinholes filled: each hole under HOLE_WIDTHS squared of its drawn widths' area (twice its
    median distance to its edge along its skeleton). A hole a ragged mask leaves inside a pipe splits its skeleton
    into a loop, two runs side by side that swept as a bulge (the stairwell's conduit, 2026-11-04); a railing's bays,
    many widths across, stay open."""
    from scipy import ndimage
    from skimage.morphology import skeletonize
    edge = ndimage.distance_transform_edt(np.pad(kept, 1))[1:-1, 1:-1]
    width = 2 * float(np.median(edge[skeletonize(kept)]))
    holes, count = ndimage.label(ndimage.binary_fill_holes(kept) & ~kept)
    if count == 0:
        return kept
    areas = ndimage.sum(np.ones_like(kept), holes, range(1, count + 1))
    return kept | np.isin(holes, 1 + np.flatnonzero(areas < (HOLE_WIDTHS * width) ** 2))


def spine(skeleton, ball, tolerance=None, spur=SPUR_WIDTHS):
    """[(points, radius)]: the skeleton's runs (`traces`) as the clean tubes a path build sweeps, in pixels (across,
    down), at one radius for each piece of the skeleton, its runs' balls' median along their length (`ball`): a piece
    is one thing of one section, so no joint, knot or ragged stretch swells, while a post's separate foot keeps its
    own. The skeleton's knots (run ends within its radius of each other: a ragged edge's pixel forks) are one joint
    each (`joints`), the runs inside one dropped; a spur (a run from a free end to a fork, shorter than SPUR_WIDTHS
    of its widths, or `spur`) is a ragged edge's, not a run of the thing, and is dropped; runs meeting two at a joint are one
    run; each run a polyline within `tolerance` pixels of its pixels (approximate_polygon; by default half its
    width, so a ragged edge's wobble is a straight run). A knot's three short runs each took a tee (`fittings`) and
    swelled the stairwell's conduit every few pixels (2026-11-04)."""
    from scipy import ndimage
    from skimage.measure import approximate_polygon
    runs = [np.asarray(run, dtype=float) for run in traces(skeleton) if len(run) > 1]
    if not runs:  # a skeleton a pixel long
        down, across = np.nonzero(skeleton)
        point = np.array([[across[0], down[0]]], dtype=float)
        return [(np.vstack([point, point]), float(ball[down[0], across[0]]))]
    piece_of = ndimage.label(skeleton, structure=np.ones((3, 3)))[0]
    piece = [int(piece_of[int(run[0, 1]), int(run[0, 0])]) for run in runs]
    medians = [float(np.median(ball[run[:, 1].astype(int), run[:, 0].astype(int)])) for run in runs]
    radius = {}
    for label in set(piece):
        own = sorted((medians[number], run_length(runs[number])) for number in range(len(runs))
                     if piece[number] == label)
        along = np.cumsum([max(length, 1.0) for _, length in own])
        radius[label] = own[int(np.searchsorted(along, along[-1] / 2))][0]
    found = joints([(run, radius[piece[number]], piece[number]) for number, run in enumerate(runs)], spur)
    return [(approximate_polygon(run, tolerance=width if tolerance is None else tolerance), width)
            for run, width in found]


def run_length(run):
    """A polyline's length."""
    return float(np.linalg.norm(np.diff(run, axis=0), axis=1).sum())


def joints(runs, spur=SPUR_WIDTHS):
    """[(points, radius)]: `runs` (each (points, radius, its piece), pixels) with each knot of their ends (ends within
    the radius of each other) one joint at its ends' middle, the runs inside a knot dropped, the spurs dropped (a run
    from a free end to a joint of three or more, shorter than `spur` of its widths), and the runs meeting two at
    a joint joined into one; a piece all knot (a post's foot drawn as wide as it is long) keeps its longest run."""
    from scipy.spatial import cKDTree
    ends = np.array([end for run, _, _ in runs for end in (run[0], run[-1])])
    reach = np.repeat([width for _, width, _ in runs], 2)
    parent = list(range(len(ends)))

    def root(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for first, second in cKDTree(ends).query_pairs(float(reach.max())):
        if np.linalg.norm(ends[first] - ends[second]) <= min(reach[first], reach[second]):
            parent[root(first)] = root(second)
    knot = [root(index) for index in range(len(ends))]
    middle = {label: ends[[index for index in range(len(ends)) if knot[index] == label]].mean(0) for label in set(knot)}
    kept = []
    for number, (run, width, _) in enumerate(runs):
        start, end = knot[2 * number], knot[2 * number + 1]
        if start == end and run_length(run) < 2 * width:
            continue  # inside a knot
        kept.append([np.vstack([middle[start], run[1:-1], middle[end]]), width, start, end])
    pieces_kept = {runs[number][2] for number in range(len(runs))
                   if knot[2 * number] != knot[2 * number + 1] or run_length(runs[number][0]) >= 2 * runs[number][1]}
    for label in {piece for _, _, piece in runs} - pieces_kept:
        run, width, _ = max((entry for entry in runs if entry[2] == label), key=lambda entry: run_length(entry[0]))
        kept.append([run, width, ("piece", label, 0), ("piece", label, 1)])

    def degrees():
        count = {}
        for _, _, start, end in kept:
            count[start] = count.get(start, 0) + 1
            count[end] = count.get(end, 0) + 1
        return count

    count = degrees()
    kept = [entry for entry in kept if not ({count[entry[2]], count[entry[3]]} & {1} and max(
        count[entry[2]], count[entry[3]]) >= 3 and run_length(entry[0]) < spur * 2 * entry[1])]
    count = degrees()
    joined = True
    while joined:
        joined = False
        for label, many in count.items():
            meeting = [entry for entry in kept if label in (entry[2], entry[3])]
            if many != 2 or len(meeting) != 2 or meeting[0] is meeting[1]:
                continue
            first, second = meeting
            ahead = first[0] if first[3] == label else first[0][::-1]
            after = second[0] if second[2] == label else second[0][::-1]
            kept = [entry for entry in kept if entry is not first and entry is not second]
            kept.append([np.vstack([ahead, after[1:]]), first[1],
                         first[2] if first[3] == label else first[3], second[3] if second[2] == label else second[2]])
            count = degrees()
            joined = True
            break
    return [(run, width) for run, width, _, _ in kept]


def ladder(points, radius, rail, gap, kept):
    """[(points, radius)]: a railing drawn as one band (its run `points`, `radius` pixels either side) built as a
    railing (`railing`'s parts, along its path): a top rail along its band's top, a mid rail along its centreline and
    posts from its top rail to its foot at least every `gap` pixels, each `rail` pixels round, its ends reaching its
    band's within its mask `kept` (its skeleton stops up to a half-width short of them). Swept as one band, the
    stairwell's stair railing, its mask the stairs seen between its posts, was a lumpy slab (2026-11-02)."""
    rise = np.array([0.0, radius - rail])  # the picture's down is the world's down
    points = np.asarray(points, dtype=float).copy()
    for end, inward in ((0, 1), (-1, -2)):  # a band's skeleton stops short of its ends: reach them, within its mask
        way = points[end] - points[inward]
        way = way / max(float(np.linalg.norm(way)), 1e-9)
        for _ in range(int(radius)):
            ahead = points[end] + way
            down, across = int(round(ahead[1])), int(round(ahead[0]))
            if not (0 <= down < kept.shape[0] and 0 <= across < kept.shape[1] and kept[down, across]):
                break
            points[end] = ahead
    steps = np.linalg.norm(np.diff(points, axis=0), axis=1)
    along = np.concatenate([[0.0], np.cumsum(steps)])
    stations = np.linspace(0.0, along[-1], max(1, int(np.ceil(along[-1] / gap))) + 1)
    middles = np.c_[np.interp(stations, along, points[:, 0]), np.interp(stations, along, points[:, 1])]
    return [(points - rise, rail), (points, rail), *((np.vstack([middle - rise, middle + rise]), rail)
                                                      for middle in middles)]


def picture_scale(row, kept, turn):
    """(metres a pixel, the mask `kept`'s longest reach in pixels as it lies turned `turn` degrees along its row): that
    reach the row's longest side."""
    down, across = np.nonzero(kept)
    angle = np.radians(turn)  # the build turned along its row (build: inverse `slanted`), in pixels
    reach = float(max(np.ptp(np.sin(angle) * down + np.cos(angle) * across),
                      np.ptp(np.sin(angle) * across - np.cos(angle) * down)) + 1)
    return max(float(value) for value in row["size"]) / reach, reach


def drawn_thin(alpha):
    """Whether a mask draws a thin thing: its drawn width (twice its median distance to its edge along its skeleton)
    at most SECTION_SHARE of its reach. A blob SAM 3 found in a thin row's box (one lantern of a string's eight, a
    crate behind a pipe) is no thin thing: built along its centreline it made a disc whose outline, judged without
    scale, passed (#36, 2026-10-30), so it is no build; of round 25's 57 builds the widest drew 0.233, but the
    square's lantern string cut from one lantern's box (0.459)."""
    from skimage.morphology import skeletonize
    from scipy import ndimage
    kept = pieces(alpha)
    down, across = np.nonzero(kept)
    reach = max(np.ptp(across), np.ptp(down)) + 1
    edge = ndimage.distance_transform_edt(np.pad(kept, 1))[1:-1, 1:-1]
    return 2 * float(np.median(edge[skeletonize(kept)])) <= SECTION_SHARE * reach


def run_holds(row, skeleton, ball, scale):
    """Each skeleton pixel's hold across (`balls`' `hold`) for a network (`network`): its run's (`traces`) the row's
    thinnest side over that run's drawn width (twice its balls' median radius at `scale` metres a pixel), at most one,
    the least where runs meet. held_across's rule, run by run: a network's runs go every way, so no one turn holds
    them, and at its spread's scale the engineroom's pipes would be drawn metres across."""
    hold = np.ones(skeleton.shape)
    thinnest = min(float(value) for value in row["size"])
    for run in traces(skeleton):
        across, down = np.asarray(run).T
        drawn = float(np.median(2 * ball[down, across])) * scale
        hold[down, across] = np.minimum(hold[down, across], min(1.0, thinnest / max(drawn, 1e-9)))
    return hold


def balls(kept, skeleton, scale, reach, hold=None):
    """(each pixel's distance to the skeleton, the radius of the skeleton's ball nearest it), in pixels: a skeleton
    pixel's ball is its distance to the mask's edge times its `hold` (`run_holds`; none by default), at least half `least_tube` (the gate's thinnest, at `scale`
    metres a pixel) and at most half SECTION_SHARE of the mask's `reach` (a mask SAM 3 drew as a blob is no thin
    thing, and no chunky build is made of it)."""
    from scipy import ndimage
    edge = ndimage.distance_transform_edt(np.pad(kept, 1))[1:-1, 1:-1]  # the picture's border is an edge too
    radius = np.clip(edge * (1.0 if hold is None else hold), least_tube() / 2 / scale, SECTION_SHARE * reach / 2)
    off, (near_down, near_across) = ndimage.distance_transform_edt(~skeleton, return_indices=True)
    return off, radius[near_down, near_across]


def swelled(off, ball, fitted, width, scale):
    """One closed surface round the skeleton's balls (`balls`' `off` and `ball`, pixels) and round the `fitted`
    segments (pairs of picture points), FITTING_SHARE of the band's `width` across: on a grid TUBE_CELLS cells across
    the band, each cell's distance through the third axis to its nearest ball's centre less its radius, cut at nought
    (marching cubes), so joints, forks, a flared foot and the fittings are one surface with no shell inside another
    (the model gate's wall rays read overlapping tubes 0.3 mm thick); in the build's frame (x the picture's normal),
    `scale` metres a pixel, slimmed to PATH_FACES."""
    import trimesh
    from PIL import ImageDraw
    from scipy import ndimage
    from skimage.measure import marching_cubes
    cell = max(width / TUBE_CELLS, 1.0)
    pad = int(np.ceil(max(float(ball.max()), width * FITTING_SHARE / 2) / cell)) + 2
    tall, wide = off.shape
    downs = np.arange(-pad, int(np.ceil(tall / cell)) + pad) * cell
    acrosses = np.arange(-pad, int(np.ceil(wide / cell)) + pad) * cell
    depth = np.arange(-pad, pad + 1) * cell
    inside = (downs[:, None] >= 0) & (downs[:, None] < tall) & (acrosses[None, :] >= 0) & (acrosses[None, :] < wide)
    picks = np.clip(downs.astype(int), 0, tall - 1)[:, None], np.clip(acrosses.astype(int), 0, wide - 1)[None, :]
    near = np.where(inside, off[picks], np.inf)
    field = np.sqrt(near[:, :, None] ** 2 + depth[None, None, :] ** 2) - np.where(inside, ball[picks], 0.0)[:, :, None]
    if fitted:
        centre = Image.new("1", (len(acrosses), len(downs)), 1)
        draw = ImageDraw.Draw(centre)
        for pair in fitted:
            draw.line([(point[0] / cell + pad, point[1] / cell + pad) for point in pair], fill=0)
        reach = ndimage.distance_transform_edt(np.asarray(centre)) * cell
        field = np.minimum(field, np.sqrt(reach[:, :, None] ** 2 + depth[None, None, :] ** 2)
                           - width * FITTING_SHARE / 2)
    vertices, faces = marching_cubes(field, 0.0, spacing=(cell, cell, cell), allow_degenerate=False)[:2]
    points = np.c_[vertices[:, 2] + depth[0], -(vertices[:, 0] + downs[0]), vertices[:, 1] + acrosses[0]] * scale
    mesh = trimesh.Trimesh(points, faces, process=True)
    if mesh.volume < 0:
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


def cut_box(row):
    """The concept box a row's build is masked and cropped in: a counted row's (`count` over 1) the union of its
    instances' `boxes`, the run they lie along (the square's 7.5 m lantern string, count 8: its `box` one lantern,
    the build swept a 7.5 m bar from that lantern's crop, outline 0.481, #36 2026-10-30); else its `box`."""
    boxes = [box for box in row.get("boxes") or [] if box]
    if int(row.get("count") or 1) <= 1 or len(boxes) < 2:
        return row.get("box")
    lefts, tops, rights, bottoms = zip(*boxes)
    return [min(lefts), min(tops), max(rights), max(bottoms)]


def mask_jobs(rows, concepts):
    """box_masks.py's jobs asking each row's own mask: one a concept, each row by its name and noun in its cut box
    (`cut_box`)."""
    jobs = {}
    for name, row in sorted(rows.items()):
        words = list(dict.fromkeys(word for word in (row["name"], row.get("noun")) if word))
        jobs.setdefault(str(concepts[name]), []).append({"key": name, "nouns": words, "box": cut_box(row),
                                                         "mask": True})
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


def boxed_grid(points):
    """(centre, scale) setting 2D `points` in a compare.SQUARE grid as compare.boxed sets a mask: their box's middle
    at the grid's, their box's longer side across it."""
    with prop_data.tools("usd", "props"):
        import compare
    low, high = points.min(0), points.max(0)
    return (low + high) / 2, (compare.SQUARE - 1) / max(float((high - low).max()), 1e-9)


def seen_flat(points, way):
    """The points as seen from `way` (orthographic): (across to the right, down), the picture's axes."""
    up = np.array([0.0, 1.0, 0.0]) if abs(way[1]) < 0.99 else np.array([0.0, 0.0, -1.0])
    right = np.cross(up, way)
    right /= np.linalg.norm(right)
    return np.c_[points @ right, -(points @ np.cross(way, right))]


def drawn(flat, triangles, centre, scale):
    """The triangles of `flat` points drawn filled in the compare.SQUARE grid at (centre, scale)."""
    from PIL import ImageDraw
    with prop_data.tools("usd", "props"):
        import compare
    grid = (flat - centre) * scale + compare.SQUARE / 2
    picture = Image.new("L", (compare.SQUARE, compare.SQUARE), 0)
    draw = ImageDraw.Draw(picture)
    for corner in grid[triangles]:
        draw.polygon([tuple(point) for point in corner], fill=255)
    return np.asarray(picture) > 127


def binned(points, centre, scale):
    """The points (pixel centres) set in the compare.SQUARE grid at (centre, scale), as a mask."""
    with prop_data.tools("usd", "props"):
        import compare
    cells = np.clip(((points - centre) * scale + compare.SQUARE / 2).astype(int), 0, compare.SQUARE - 1)
    found = np.zeros((compare.SQUARE, compare.SQUARE), dtype=bool)
    found[cells[:, 1], cells[:, 0]] = True
    return found


def turned(points, degrees):
    """2D points turned anticlockwise on the picture (its y down) by `degrees` round the origin."""
    angle = np.radians(degrees)
    return points @ np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])


def laid_on(mesh, alpha):
    """(way, turn) laying the crop on the build: of TEXTURE_WAYS and the crop's turns every TEXTURE_TURN degrees, the
    pair whose build outline and turned mask (`alpha`) overlap most (compare.outline, the likeness gate's measure),
    the first on a tie."""
    with prop_data.tools("usd", "props"):
        import compare
    inside = np.argwhere(alpha)[:, ::-1] + 0.5 - np.array(alpha.shape[::-1]) / 2  # (x, y) from the picture's middle
    masks = {turn: binned(turned(inside, turn), *boxed_grid(turned(inside, turn)))
             for turn in range(0, 360, TEXTURE_TURN)}
    best, found = -1.0, None
    for way in TEXTURE_WAYS:
        flat = seen_flat(mesh.vertices, way)
        outline = drawn(flat, mesh.faces, *boxed_grid(flat))
        for turn, mask in masks.items():
            overlap = compare.outline(outline, mask)
            if overlap > best:
                best, found = overlap, (way, turn)
    return found


def crop_texture(picture):
    """The crop's colours as a texture: its object's pixels, and every other pixel its nearest object pixel's colour
    (so no backdrop or neighbour of the concept reaches a face the projection lays at the outline's edge)."""
    from scipy import ndimage
    pixels = np.asarray(picture.convert("RGBA"))
    _, (down, across) = ndimage.distance_transform_edt(pixels[..., 3] <= 127, return_indices=True)
    return Image.fromarray(pixels[down, across, :3])


def textured(mesh, picture):
    """The build with its crop (`picture`, its object its alpha) laid on as its own texture, as a Pixal3D take carries
    the picture it was made from: each point's UV the crop's pixel under it seen from the way its outline matches the
    crop (`laid_on`), its box set on the crop's box, so the finish route's views (route_views: the model's own texture
    in k-means regions) see the crop's colours where they lie on the thing, and its list and split give each finish
    its part. The texture is only measured, never shown: every finish is a library surface."""
    import trimesh
    alpha = np.asarray(picture.convert("RGBA"))[..., 3] > 127
    way, turn = laid_on(mesh, alpha)
    middle = np.array(alpha.shape[::-1]) / 2
    inside = turned(np.argwhere(alpha)[:, ::-1] + 0.5 - middle, turn)
    flat = seen_flat(mesh.vertices, way)
    (here, scale), (there, crop_scale) = boxed_grid(flat), boxed_grid(inside)
    pixel = turned((flat - here) * scale / crop_scale + there, -turn) + middle
    wide, tall = alpha.shape[::-1]
    uv = np.c_[np.clip(pixel[:, 0] / wide, 0.0, 1.0 - 1e-6), np.clip(1.0 - pixel[:, 1] / tall, 1e-6, 1.0)]
    material = trimesh.visual.material.PBRMaterial(baseColorTexture=crop_texture(picture),
                                                   baseColorFactor=[1.0, 1.0, 1.0, 1.0])
    mesh.visual = trimesh.visual.TextureVisuals(uv=uv, material=material)
    return mesh


def write_take(take, row, picture, faces, pixal, mask, box=None):
    """The take's files (module docstring) in `pixal` from `picture`, its concept crop of `box` (its row's `cut_box`
    by default) cut out by its SAM 3 `mask`; None, nothing written, when the mask is no thin thing (`drawn_thin`)."""
    alpha = np.asarray(picture.convert("RGBA"))[..., 3] > 127
    if alpha.any() and not drawn_thin(alpha):
        return None
    views = pixal / f"{take}.svviews"
    views.mkdir(parents=True, exist_ok=True)
    picture.save(views / "input.png")
    mesh = build(row, alpha)
    seen = mesh.copy().apply_transform(np.linalg.inv(as_built(row, alpha)))  # the crop lies on it as drawn
    mesh.visual = textured(seen, picture).visual
    for name in (f"{take}.glb", f"{take}-{faces}.glb", f"{take}-final.glb"):  # raw, slimmed, final: never stood
        mesh.export(pixal / name)
    mark = {"route": "code", "rule": "thin straight (owner, 2026-10-25)", "profile": "path" if alpha.any() else
            profile(row), "size": row["size"], "mask": str(mask), "box": cut_box(row) if box is None else box,
            "texture": TEXTURE}
    (views / MARK).write_text(json.dumps(mark, indent=1))
    return views


def rebuilt(take, row, faces, pixal):
    """The code build of `take` made again (write_take) from its own crop, mask and box as its mark names them."""
    views = pixal / f"{take}.svviews"
    mark = json.loads((views / MARK).read_text())
    return write_take(take, row, Image.open(views / "input.png").convert("RGBA"), faces, pixal, mark["mask"],
                      mark.get("box", row.get("box")))


def cut_as_built(take, row, pixal):
    """Whether the code build of `take` was cut from its row's `cut_box`: its mark's box, or, in a mark from before
    the box was named, its row's own `box` (a counted row's build cut from one instance is masked and cut again)."""
    return json.loads((pixal / f"{take}.svviews" / MARK).read_text()).get("box", row.get("box")) == cut_box(row)


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
