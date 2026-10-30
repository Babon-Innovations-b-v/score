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
# Metres between a railing's posts at most: a guard's usual post spacing (no library row gives one), so a run of its
# length has ceil(length / POST_GAP) bays.
POST_GAP = 1.5
SEGMENTS = 32
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
    z: glb_file.squared; the inventory's size is wide, deep, tall), centred on the origin: along its mask's (`alpha`,
    its cut's) centreline (`path_build`), then turned in the picture's plane so its long axis follows its row
    (`slanted` undone), or, with no mask, its profile swept straight along its longest side."""
    import trimesh
    if alpha is not None and alpha.any():
        return path_build(row, alpha, axis_turn(row, alpha)).apply_transform(np.linalg.inv(slanted(row, alpha)))
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


def view(row, alpha):
    """The turn (4 by 4) the likeness row sees a code build by: back into its picture's slant (`slanted`) and
    leaned to face the look-down (`facing`), so its outline is held to its crop as the picture draws it while the
    model keeps its row's pose."""
    return facing(row) @ slanted(row, alpha)


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
    """The row's model along its mask's centreline (owner's ask, 2026-10-26: bent pipe networks, a sagging lantern
    string, a railing's posts and rails, a bundle of parallel cables were each built as one straight sweep and failed
    their outline): a ball at each point of the mask's skeleton as wide as the mask is there (`balls`: its distance to
    the mask's edge), the union of them one closed surface (`swelled`), so a sag stays a sag, an elbow a bend, a ladder
    its posts and rails, a band its band, a post its flared foot and a lamp post its head (a tube of one width along
    the centreline lost the airlock porch post's foot, 0.75 to 0.46, and the street lamp post's head, 0.61 to 0.494;
    #36, 2026-10-30), laid in the picture's plane at one scale, the mask's longest reach (as it lies turned `turn`
    degrees along its row, `axis_turn`) the row's longest side and its
    other reach the path's own, never a box side (a thin run's box is its thickness on its two short sides: a sagging
    string 8 by 0.01 by 0.01; a railing curving round a floor drawn from above shows its plan's depth as its picture's
    height: the greenhouse's held to its 1 m read 0.023, 2026-10-28); held at most the row's thinnest side deep
    through the picture's plane (a 5 m drape's box 1 m deep is no 1 m tube, a flat wall run of pipes no round one),
    never under `least_tube`, in its row's pose (the likeness row sees it in its picture's, `view`); a rigid run's
    fittings
    (`fittings`: elbows, tees, wall clamps on its traced runs) made in code on the same surface, its finish the finish
    route's like the rest."""
    from skimage.morphology import skeletonize
    kept = pieces(alpha)
    skeleton = skeletonize(kept)
    sides = sorted(float(value) for value in row["size"])
    down, across = np.nonzero(kept)
    low = np.array([across.min(), down.min()], dtype=float)
    angle = np.radians(turn)  # the build turned along its row (build: inverse `slanted`), in pixels
    reach = float(max(np.ptp(np.sin(angle) * down + np.cos(angle) * across),
                      np.ptp(np.sin(angle) * across - np.cos(angle) * down)) + 1)
    scale = sides[2] / reach  # metres a pixel
    off, ball = balls(kept, skeleton, scale, reach)
    width = float(np.median(2 * ball[skeleton]))
    laid = laid_runs(skeleton, low, scale, width)
    fitted = [pair for pairs in fittings(laid, row, width * scale).values() for pair in pairs]
    mesh = swelled(off, ball, [[(point[2] / scale + low[0], -point[1] / scale + low[1]) for point in pair]
                               for pair in fitted], width, scale)
    deep = max(sides[0], least_tube())
    mesh.apply_transform(np.diag([min(1.0, deep / max(float(np.ptp(mesh.vertices[:, 0])), 1e-9)), 1.0, 1.0, 1.0]))
    return mesh.apply_translation(-mesh.bounds.mean(0))


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


def balls(kept, skeleton, scale, reach):
    """(each pixel's distance to the skeleton, the radius of the skeleton's ball nearest it), in pixels: a skeleton
    pixel's ball is its distance to the mask's edge, at least half `least_tube` (the gate's thinnest, at `scale`
    metres a pixel) and at most half SECTION_SHARE of the mask's `reach` (a mask SAM 3 drew as a blob is no thin
    thing, and no chunky build is made of it)."""
    from scipy import ndimage
    edge = ndimage.distance_transform_edt(np.pad(kept, 1))[1:-1, 1:-1]  # the picture's border is an edge too
    radius = np.clip(edge, least_tube() / 2 / scale, SECTION_SHARE * reach / 2)
    off, (near_down, near_across) = ndimage.distance_transform_edt(~skeleton, return_indices=True)
    return off, radius[near_down, near_across]


def laid_runs(skeleton, low, scale, width):
    """The skeleton's runs (`traces`, forks kept, each kept to within a quarter of the band's `width` of its pixels)
    in the build's frame: across the picture z, up it y (the picture's down is the world's up), metres from the mask's
    corner `low`."""
    from skimage.measure import approximate_polygon
    runs = [approximate_polygon(np.asarray(run, dtype=float), tolerance=width / 4) for run in traces(skeleton)
            if len(run) > 1]
    return [np.c_[np.zeros(len(run)), -(run[:, 1] - low[1]) * scale, (run[:, 0] - low[0]) * scale] for run in runs]


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
    mesh = textured(build(row, alpha), picture)
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
