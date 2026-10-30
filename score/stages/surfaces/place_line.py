"""The framework's half of a place's surface line, after the method's parts (PARTS in __init__.py: per model its
parts, each with the library surface the method named for it): every part painted from its surface alone, baked and
checked. Never a picture's colours: a part the method named nothing for takes the surface of the part it borders
most, else it stays unnamed and the gate fails. A new library surface the method proposed for a part goes into the
finish registry (registry.py) as proposed, for the owner; until he accepts it, the part keeps the nearest library
surface the method named.

Rows (place grain, surfaces-<step>@<place>):
    paint   (free)  per part its surface (the method's, else the bordering part's), the labelled folder written
                    (labels.write_parts) and its gate: one surface a part
    bake    (paid)  the labelled folders baked onto the place's made models (library_bake.py make_chunky), each by
                    the entry the place's data names (data/surfaces/<place>.json `bake`); the models the place lays
                    that another place claims (its data's `elsewhere`) named in elsewhere.json, read from that place's
                    bake: each model is painted once world-wide
    check   (free)  the baked models: every part's baked base colour lies on its library surface (CIE76 under
                    BAKE_DELTA_E, no near-black blotch), every map there, triangles within the job's budget
"""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROPS = REPO / "tools/props"
for folder in (HERE, PROPS, PROPS / "library", REPO / "tools/cloud"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the method modules must not shadow the framework's
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import surface_gates as gates  # noqa: E402
import prop_env  # noqa: E402

# A baked part lies on its surface when its median base colour is within BAKE_DELTA_E (CIE76) of the surface's
# colour: the bake's wear and dirt (0.4 each) move a surface's colour, a wrong surface moves it far more. A part
# whose surface is not dark (L* over DARK_SURFACE) fails with over BLOTCH_SHARE of its area under BLOTCH_L (the
# black blotches of round six). Parts under PART_LEAST of the model are not judged.
BAKE_DELTA_E = 20.0
DARK_SURFACE, BLOTCH_L, BLOTCH_SHARE = 35.0, 12.0, 0.05
PART_LEAST = 0.01
PART_POINTS = 60000  # labelled points kept per model to name each baked triangle (export.PART_POINTS)
CLASSES = "gpu-24gb"  # one class, the L4 the bake is priced on; never a fallback to a larger card (#21)
BAKE_EUROS = 2.0
# Two neighbouring parts of one surface join only when their colours lie within this (Lab) (MaPa's merge: same class
# and same unlit colour, its CIE threshold 2 on albedo is too fine for a picture's).
MERGE_COLOUR = 12.0
# A take's feet in its own frame (feet.py), levelled only when a row lays it loose on the floor or held
# (stands_on_feet): found within FOOT_BAND of its height over its lowest point, points within FOOT_LINK of its
# footprint's diagonal one foot. In shares of its size (its height or its footprint's diagonal, the larger: a pallet's
# feet are measured against its width, not its few centimetres of height), a foot may stand FOOT_TOLERANCE over the
# lowest and count as down (a hundredth: 2.3 cm on the water tank, inside the resting check's 3 cm), and a short leg
# is stretched down FOOT_MOST at most (a tenth: the water tank's shortest leg ends 6.4% of its size up); a foot further
# up is a missing leg, a fault of the model, and fails the gate "feet in one plane" by name.
FOOT_BAND, FOOT_TOLERANCE, FOOT_MOST, FOOT_LINK = 0.15, 0.01, 0.1, 0.03
# The band's most in metres, read through the tallest row that stands the take: the resting check's own feet band
# (tools/usd/triage.py LOW_BAND). Wider, a tall shelf's bottom rail joins its legs into one foot and a short leg is
# never levelled (2026-10-15: the garage's fluid shelves, 28 cm, kept a leg 3.7 cm up; the storage's cargo racks, 39 cm,
# one 3.4 cm up; the resting check, 10 cm, failed both).
FOOT_BAND_METRES = 0.1
# A foot counts as down within FOOT_TOLERANCE of the take's size, at most this many metres (the resting check's 3 cm,
# read through the standing height as the band is): a hundredth of the hangar's 31 m ship let its landing legs end
# 8 cm apart, and it stood on its rear ones and tipped (2026-10-15).
FOOT_TOLERANCE_METRES = 0.03
# A base that slopes as one piece (flattened_base): its bottom BASE_BAND of height, each footprint quadrant brought
# down level when over FOOT_TOLERANCE of its size up, refused over BASE_MOST (the rack's legs: 7.4% of its size).
BASE_BAND, BASE_MOST = 0.25, 0.15
# A base that slopes as one plane (sloped_base): its underside read as the lowest point of each BASE_CELL (a share of
# its footprint's diagonal) square of the bottom band, one plane when BASE_ON_PLANE of those lie within FOOT_TOLERANCE
# of the plane fitted to them. The quadrants above miss it: each quadrant's lowest point lies by the middle.
BASE_CELL, BASE_ON_PLANE = 1 / 16, 0.8
# The paint runs on processor machines, a job a take of about PAINT_MINUTES (campgrounds, 2026-10-12: twelve takes,
# eight machines of 3.3 to 4.7 min each for EUR 5.83 at 5; a job about 1.5 min, crane-r1 alone 34.8 GB at its peak); the
# keys of a take's listing besides the make's inputs (prop_env.short reads each as a path: the take is its name); the
# repository folders its code and data come from.
PAINT_CLASSES = "cpu-32c-128gb"  # one class, the one the paint was timed on; no fallback (#21)
PAINT_MINUTES, PAINT_EUROS = 2, 0.5
TAKE, RECORDS, HOME, CODE = "paint take", "paint records", "props home", "paint repo"
# A floor a scene reads as a row (on_floor) is a slab: its height at most this share of its narrower side (the
# designed floors read 0.1 to 0.2 m on 3 to 14 m, a stage 1.3 m on 8 m; a table, bed or counter half or more).
SLAB = 0.25
CLAIMED = "paint claimed rows"  # {take: the rows other places stand it with}, worked out before the job (claimed_rows)
PAINT_REPO = ("score", "tools/props", "data/library", "data/definitions", "design/tokens", "data/checks",
              "data/inventory")


def data_of(inputs):
    return json.loads(inputs["surfaces"].read_text())


# --- paint ---------------------------------------------------------------------------------------------------------

def method_surfaces(take, place, rows, registry):
    """Each part's record with the surface the method named for it; a new library surface the method proposed for a
    part goes into the registry as proposed (the standing proposal of its name is recorded on the part), the part
    keeping the method's nearest library surface meanwhile."""
    found = []
    for row in rows:
        record = dict(row)
        if row["judge"]:
            record.update(surface=row["judge"], by="the method")
        if row.get("proposed"):
            spec = {**row["proposed"], "status": "proposed", "stands_in": row["judge"]}
            standing = registry.propose_surface(row["proposed"]["name"], spec,
                                                {"line": place, "take": take, "part": row["part"]})
            record["proposed"] = standing["spec"]
        found.append(record)
    return found


def bordered(mesh, part_of, records, names):
    """Each part's index into `names` (appended to as needed), a part with no surface taking the one of the part it
    borders most; -1 where none does."""
    import numpy as np
    import labels
    chosen = np.full(len(records), -1)
    for record in records:
        if record.get("surface"):
            if record["surface"] not in names:
                names.append(record["surface"])
            chosen[record["part"]] = names.index(record["surface"])
    shared = labels.borders(mesh, part_of, len(records))
    for part in np.nonzero(chosen < 0)[0]:
        known = np.nonzero(chosen >= 0)[0]
        if len(known) and shared[part, known].max() > 0:
            chosen[part] = chosen[known[np.argmax(shared[part, known])]]
            records[part].update(surface=names[chosen[part]], by="the part it borders most")
    return chosen


def colour_joined_parts(mesh, part_of, chosen, colours):
    """labels.joined_parts with MaPa's second condition: neighbouring parts join where one surface is named for both
    and their colours (labels.part_colour, Lab) lie within MERGE_COLOUR; parts with too few seen faces for a colour
    (every part of a method that measures none) join on the surface alone."""
    import numpy as np
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    import labels
    count = len(chosen)
    seen = ~np.isnan(colours[:, 0])
    part_colours = np.full((count, 3), np.nan)
    for part in range(count):
        members = (part_of == part) & seen
        if members.sum() >= labels.SEEN_LEAST:
            part_colours[part] = labels.part_colour(colours[members])
    pairs = mesh.face_adjacency
    first, second = part_of[pairs[:, 0]], part_of[pairs[:, 1]]
    gap = np.linalg.norm(part_colours[first] - part_colours[second], axis=1)
    near = np.isnan(gap) | (gap <= MERGE_COLOUR)
    same = (first != second) & (chosen[first] == chosen[second]) & near
    links = sparse.coo_matrix((np.ones(same.sum()), (first[same], second[same])), shape=(count, count))
    return connected_components(links + links.T, directed=False)[1][part_of]


def finished_frame(mesh, take):
    """The raw model laid on its finished model (labels.onto_finished, seeded as labels.py seeds it); the matrix,
    the median gap and the finished model's bounds."""
    import numpy as np
    import trimesh
    import labels
    np.random.seed(0)
    final = trimesh.load(labels.PIXAL / f"{take}-final.glb", force="mesh")
    turn = recovered_turn(labels.PIXAL, take)
    matrix, gap = labels.onto_finished(mesh.sample(labels.SAMPLED, seed=1), final.sample(labels.SAMPLED, seed=2),
                                       labels.finish_turn(take) if turn is None else turn)
    return matrix, gap, final.bounds


# How far a recovered turn may land any vertex from the final model's own and still be the finish's turn (metres).
RECOVERED_MISS = 1e-4


def recovered_turn(pixal, take):
    """The turn the finish gave the take, read off its final model: of its finished files with the final's vertex
    count, the least-squares turn onto the final's same vertices (stand_and_pad turns them and writes them in order)
    when it is a rotation landing every vertex within RECOVERED_MISS; else None, and labels.finish_turn's replay of
    the finish's options decides. The replay, with today's glb_file, missed the takes stood before glb_file.squared
    changed (48939c57, 2026-10-26: four of the airlock's by 1.2 to 5.2 cm, env1 on the PC, each one exact here). Here,
    not in labels.py, so only the paint's rows re-key (labels.py is in 77 paid rows' code)."""
    import numpy as np
    import glb_file
    stood = glb_file.positions(*glb_file.read(pixal / f"{take}-final.glb"))
    for path in sorted(pixal.glob(f"{take}-[0-9]*.glb")):
        points = glb_file.positions(*glb_file.read(path))
        if len(points) != len(stood):
            continue
        turn, *_ = np.linalg.lstsq(points, stood, rcond=None)
        if np.allclose(turn @ turn.T, np.eye(3), atol=1e-6) and np.linalg.det(turn) > 0 \
                and float(np.abs(points @ turn - stood).max()) <= RECOVERED_MISS:
            return turn.T
    return None


def stands_on_feet(entry, inventory, rules_file, take=None):
    """Whether a row of the take's own place stands its kind on the floor or ground, on feet the paint may level: its
    anchor the floor or the ground, or a floor its scene reads as a row (on_floor), never mounted on another object;
    not fixed, not part of the room's shell (a designed row's `route` "shell"), not hung (its support, or the resting
    rules' hanging words in its id or name), not laid tilted on purpose (`leans`), and not a pile of ground debris
    (the rules' ground debris words: a cairn of stones). Every other row's take is left as made: the cockpit's flight
    stick set in its console and the campgrounds' cairn read as standing and failed "feet in one plane" on their
    resting faces, the wreck's debris before them (2026-10-15); nor a row the bake's guard list keeps (stands). A word
    of a description is not a cable's or a cloth's class: the garage's control cabinet, described "cables running up
    from its top", stands and is levelled. The inventory is
    the place's scene inventory: a designed place's hand-in, whose rows name their take (`prop:<take>`), else its
    old inventory, whose rows name the kind (`prop:<kind>`)."""
    return bool(standing_rows(entry, inventory, rules_file, take))


def standing_rows(entry, inventory, rules_file, take=None):
    """The rows of the take's own place that stand its kind, or the take itself, on feet the paint may level
    (stands_on_feet)."""
    rows = json.loads(pathlib.Path(inventory).read_text())["rows"] if inventory and pathlib.Path(inventory).exists() \
        else []
    things = {f"prop:{entry['kind']}", *([f"prop:{take}"] if take else [])}
    return [row for row in rows if row.get("thing") in things and stands(row, rules_file, rows)]


def stands(row, rules_file, rows=()):
    """Whether a row stands on the floor or ground on feet the paint may level (stands_on_feet's terms); `rows`, its
    inventory's, name what an `on:` anchor stands on. A row the bake's guard list keeps in its pose (tumble.keeps_pose
    over the resting rules: leaning, hanging, a person, no up) is left as made: old_station's limp cables, levelled,
    went from outline 0.637 to 0.207 (#36, 2026-10-30)."""
    import tumble
    return (not row.get("fixed") and row.get("support") in (None, "floor") and row.get("route") != "shell"
            and ((row.get("anchor") or "") in ("floor", "ground", "") or on_floor(row, rows))
            and not tumble.keeps_pose(row, tumble.rules_of({"resting rules": rules_file}), rows))


def on_floor(row, rows, seen=frozenset()):
    """Whether a row's `on:` anchor is a floor its scene reads as a row (is_floor). A designed scene reads its floor
    as a row (the airlock's floor plates, the street's surface), so what stands on it stands on the floor; a table, a
    shelf, a wall or a building holds what is on it, which is left as made."""
    anchor = str(row.get("anchor") or "")
    holder = {found.get("id"): found for found in rows}.get(anchor.removeprefix("on:"))
    if not anchor.startswith("on:") or holder is None or holder.get("id") in seen:
        return False
    return is_floor(holder, rows, seen | {holder.get("id")})


def is_floor(row, rows, seen=frozenset()):
    """Whether a row is a floor: the reading's floor piece (group "kit: floor", whatever it is mounted on: the
    cockpit's plates on its hull, a dome's floor in its dome, a landing on its stairs), its ground (route "ground"),
    or terrain or a slab (its height, the third of its size in metres, at most SLAB of its narrower side) resting on
    the floor, the ground or another floor (a stage on the plaza)."""
    if row.get("group") == "kit: floor" or row.get("route") == "ground":
        return True
    size = row.get("size") or ()
    flat = bool(row.get("terrain")) or (len(size) == 3 and size[2] <= SLAB * min(size[0], size[1]))
    return flat and (row.get("anchor") in ("floor", "ground") or on_floor(row, rows, seen))


def claimants(place):
    """{take: [(the place that lays it, the model it lays)]} of each of the place's takes another place claims (that
    place's `elsewhere`): the hangar lays old_station's parts_rack-r1 as parts_rack_1 to parts_rack_4. Here, not in
    surface_data.py, whose every reader is a paid row. Each place's surface data is its design's where designed
    (surface_data.record), else data/surfaces' (the people line's)."""
    import surface_data
    found = {}
    others = sorted({path.stem for folder in (surface_data.DESIGN, surface_data.FOLDER) for path in folder.glob("*.json")})
    for other in others:
        for model, claim in surface_data.record(other).get("elsewhere", {}).items():
            if claim["place"] == place:
                found.setdefault(claim["take"], []).append((other, model))
    return found


def claimed_rows(take, inputs):
    """The rows of the other places that lay the take by their claim (claimants) and stand it on feet:
    the hangar stands old_station's parts rack, whose own place lays none of its kind, so the rack was never levelled
    and stood in the hangar with feet ending up to 5.6 cm apart (2026-10-15)."""
    found = []
    for place, model in claimants(data_of(inputs)["place"]).get(take, []):
        inventory = inputs.get(f"inventory {place}")
        rows = json.loads(pathlib.Path(inventory).read_text())["rows"] if inventory else []
        row = model.rsplit("_", 1)[0]
        found += [found_row for found_row in rows
                  if found_row["id"] == row and stands(found_row, inputs["resting rules"], rows)]
    return found


def levelled_feet(vertices, faces, tall=None):
    """A take's vertices on its finished model (+y up, its own frame) with its feet brought onto one level plane
    (feet.level: FOOT_BAND of its height, at most FOOT_BAND_METRES when `tall`, its standing height in metres, is
    known; FOOT_LINK of its footprint, FOOT_TOLERANCE and FOOT_MOST of its size), and what was done, each gap as a
    share of its size."""
    import feet
    height, diagonal = feet.model_scale(vertices)
    size = max(height, diagonal)
    wide = FOOT_BAND * height
    band = wide if not tall else min(FOOT_BAND, FOOT_BAND_METRES / tall) * height
    down = FOOT_TOLERANCE * size if not tall else min(FOOT_TOLERANCE * size, FOOT_TOLERANCE_METRES / tall * height)
    points, record = feet.level(vertices, faces, band, FOOT_LINK * diagonal, down, FOOT_MOST * size)
    if record["feet"] == 2:
        points, record = two_feet_level(points, faces, band, FOOT_LINK * diagonal, down, FOOT_MOST * size)
    if band < wide:  # then in the whole band too: a leg ending over the narrow band is still a short leg (the
        # hangar's access stair, two legs 29 and 33 cm up, left unlevelled by the narrow band alone, 2026-10-15)
        points, again = feet.level(points, faces, wide, FOOT_LINK * diagonal, down, FOOT_MOST * size)
        found = max(record, again, key=lambda one: one["feet"])
        record = {"feet": found["feet"], "gaps": found["gaps"], "levelled": record["levelled"] + again["levelled"],
                  "refused": record["refused"] + again["refused"]}
    points, base = flattened_base(points, BASE_BAND * height, FOOT_TOLERANCE * size, BASE_MOST * size)
    points, plane = sloped_base(points, BASE_BAND * height, BASE_CELL * diagonal, FOOT_TOLERANCE * size,
                                BASE_MOST * size)
    points, rests = resting_base(points, faces, BASE_BAND * height, FOOT_TOLERANCE * diagonal, BASE_MOST * size)
    record["refused"] = record["refused"] + base["refused"] + plane["refused"] + rests["refused"]
    shares = {key: [round(gap / size, 4) for gap in record[key]] for key in ("gaps", "levelled", "refused")}
    found = {"feet": record["feet"], **shares, "base": [round(gap / size, 4) for gap in base["quadrants"]],
             "flattened": [round(gap / size, 4) for gap in base["flattened"]]}
    if plane["rise"] is not None:  # only a take whose base slopes as one plane says so: the others' reports as before
        found["sloped"] = round(plane["rise"] / size, 4)
    if rests["rise"] is not None:  # only a take whose resting face leans says so
        found["rests"] = round(rests["rise"] / size, 4)
    return points, found


def two_feet_level(vertices, faces, band, link, tolerance, most):
    """feet.level for a take on two feet, which feet.level leaves as they are (it levels three or more): the higher
    foot brought down onto the level plane through the lower one, its points stretched over the band, refused over
    `most` (the engine room's fuel tank stands on two cradle feet, one 5.9 cm up, and tipped onto it when dropped,
    2026-10-15). Here, not in feet.py, which the resting check and the settle read too."""
    import numpy as np
    import feet
    points = np.array(vertices, dtype=np.float64)
    found = [(members[members < len(points)], low)
             for members, low in feet.feet(feet.surface_points(points, faces), band, link)]
    gaps = [round(height - found[0][1], 6) for _, height in found]
    record = {"feet": len(found), "gaps": gaps, "levelled": [], "refused": []}
    top = points[:, 1].min() + band
    for (members, height), gap in zip(found, gaps):
        if gap <= tolerance:
            continue
        if gap > most or not len(members):
            record["refused"].append(gap)
            continue
        points[members, 1] -= gap * np.clip((top - points[members, 1]) / (top - height), 0.0, 1.0)
        record["levelled"].append(gap)
    return points, record


def flattened_base(points, band, tolerance, most):
    """A take's vertices with its base brought down level where it slopes as one piece (the hangar's parts rack stood
    on a middle part, its legs 22 cm up; the shelving's one side 10 cm short; the paint's legs check found one foot
    and passed them): each footprint quadrant of the bottom `band` whose lowest point lies over `tolerance` above the
    lowest is brought down, the drop spread over the footprint by inverse squared distance from the quadrants' lowest
    points (each of them comes down its whole gap) and faded over the band (one at the band's top moves none). Never by tipping the model. A quadrant over
    `most` up is a fault of the model: nothing moves and its gap comes back refused. Returns (vertices, {"quadrants":
    each quadrant's gap, "flattened": the gaps brought down, "refused": ...})."""
    import numpy as np
    points = np.array(points, dtype=np.float64)
    low = points[:, 1].min()
    base = points[points[:, 1] <= low + band]
    middle = (base.min(axis=0) + base.max(axis=0)) / 2
    gaps, places = np.zeros(4), np.zeros((4, 2))
    sides = [(x_side, z_side) for x_side in (base[:, 0] < middle[0], base[:, 0] >= middle[0])
             for z_side in (base[:, 2] < middle[2], base[:, 2] >= middle[2])]
    for number, (x_side, z_side) in enumerate(sides):
        chosen = base[x_side & z_side]
        lowest = chosen[chosen[:, 1].argmin()] if len(chosen) else np.array([middle[0], low, middle[2]])
        gaps[number], places[number] = lowest[1] - low, lowest[[0, 2]]
    record = {"quadrants": [float(gap) for gap in gaps], "flattened": [], "refused": []}
    if gaps.max() <= tolerance:
        return points, record
    if gaps.max() > most:
        record["refused"] = [float(gap) for gap in gaps if gap > most]
        return points, record
    drops = np.where(gaps > tolerance, gaps, 0.0)
    distance = ((points[:, None, [0, 2]] - places[None]) ** 2).sum(axis=2)
    weights = 1.0 / np.maximum(distance, 1e-12)
    drop = (weights * drops).sum(axis=1) / weights.sum(axis=1)
    fade = np.clip((low + band - points[:, 1]) / np.maximum(band - drop, 1e-9), 0.0, 1.0)  # a quadrant's low: all
    points[:, 1] -= drop * fade
    record["flattened"] = [float(gap) for gap in drops if gap > 0]
    return points, record


def sloped_base(points, band, cell, tolerance, most):
    """A take's vertices with its base brought down level where its underside is one sloping plane (the square's
    guard hut, 2026-10-14: its base rose 14 cm from one side to the other under a level roof, each quadrant's lowest
    point lay by the middle, so flattened_base found nothing and the hut stood on a strip, its weight outside it):
    the underside is the lowest point of each `cell` square of the bottom `band`; when the plane fitted to those lies
    within `tolerance` of BASE_ON_PLANE of them and rises over `tolerance`, every point comes down by the plane's
    height over its lowest (never past the lowest point), faded over the band as flattened_base fades it. Never by
    tipping the model. A
    rise over `most` is a fault of the model: nothing moves and it comes back refused. Returns (vertices, {"rise": the
    plane's rise when the underside is one sloping plane, else None; "refused": [...]})."""
    import numpy as np
    points = np.array(points, dtype=np.float64)
    low = points[:, 1].min()
    base = points[points[:, 1] <= low + band]
    _, square = np.unique(np.floor(base[:, [0, 2]] / cell).astype(int), axis=0, return_inverse=True)
    square = square.ravel()
    order = np.lexsort((base[:, 1], square))  # by square, then height: each square's lowest point comes first
    under = base[order][np.r_[0, np.nonzero(np.diff(square[order]))[0] + 1]]
    across = np.c_[under[:, 0], under[:, 2], np.ones(len(under))]
    fit = np.linalg.lstsq(across, under[:, 1], rcond=None)[0]
    plane = across @ fit
    rise = float(plane.max() - plane.min())
    record = {"rise": None, "refused": []}
    if len(under) < 3 or rise <= tolerance or np.mean(np.abs(under[:, 1] - plane) <= tolerance) < BASE_ON_PLANE:
        return points, record
    record["rise"] = rise
    if rise > most:
        record["refused"] = [rise]
        return points, record
    drop = np.clip(np.c_[points[:, 0], points[:, 2], np.ones(len(points))] @ fit - plane.min(), 0.0, rise)
    drop = np.minimum(drop, points[:, 1] - low)  # a point under the plane comes down to the lowest, never past it
    fade = np.clip((low + band - points[:, 1]) / np.maximum(band - drop, 1e-9), 0.0, 1.0)
    points[:, 1] -= drop * fade
    return points, record


def resting_base(points, faces, band, tolerance, most):
    """A take's vertices with the face it rests on brought down level: the face of its convex hull straight under its
    weight (the surface's middle, area-weighted, as the resting check weighs it) is the plane a level floor meets;
    when it rises over `tolerance` across the base, every point of the bottom `band` comes down by that plane's height
    over its lowest (never past the lowest point), faded over the band as flattened_base fades it. Never by tipping
    the model. The quadrants and the cells' plane miss a base on a rim with an open middle: the garage's control
    cabinet rested 2.1 degrees over on its plinth's rim, its middle 4 cm up (2026-10-15). A rise over `most` is a
    fault of the model: nothing moves and it comes back refused. Returns (vertices, {"rise": the resting face's rise
    across the base when it leans, else None; "refused": [...]})."""
    import numpy as np
    import trimesh
    points = np.array(points, dtype=np.float64)
    record = {"rise": None, "refused": []}
    mesh = trimesh.Trimesh(points, np.asarray(faces).reshape(-1, 3), process=False)
    if mesh.area <= 0:
        return points, record
    middle = (mesh.triangles_center * mesh.area_faces[:, None]).sum(axis=0) / mesh.area
    hull = trimesh.convex.convex_hull(points)
    hits, _, struck = hull.ray.intersects_location([[middle[0], points[:, 1].max() + 1.0, middle[2]]],
                                                    [[0.0, -1.0, 0.0]])
    if not len(struck):
        return points, record
    face = struck[np.argmin(hits[:, 1])]
    normal, corner = hull.face_normals[face], hull.vertices[hull.faces[face][0]]
    if normal[1] > -1e-6:  # no face under it that faces down
        return points, record
    low = points[:, 1].min()
    base = points[:, 1] <= low + band

    def height_at(found):
        return corner[1] - (normal[0] * (found[:, 0] - corner[0]) + normal[2] * (found[:, 2] - corner[2])) / normal[1]

    plane = height_at(points[base])
    rise = float(plane.max() - plane.min())
    if rise <= tolerance:
        return points, record
    record["rise"] = rise
    if rise > most:
        record["refused"] = [rise]
        return points, record
    drop = np.clip(height_at(points) - plane.min(), 0.0, rise)
    drop = np.minimum(drop, points[:, 1] - low)  # never past the lowest point
    fade = np.clip((low + band - points[:, 1]) / np.maximum(band - drop, 1e-9), 0.0, 1.0)
    points[:, 1] -= drop * fade
    return points, record


def feet_rows(entry, inputs, take):
    """(the rows the paint levels the take's feet by, the feet record it keeps when there are none): its place's rows
    standing it (standing_rows) and the other places' that stand it by their claim (CLAIMED); none for a code build
    (its take's code.json route "code", bake_job.code_built), which stands as its code made it (tumble.keeps_pose)."""
    import bake_job
    import tumble
    if HOME in inputs and bake_job.code_built(take, inputs[HOME]):
        return [], {"skipped": tumble.CODE_BUILD}
    standing = standing_rows(entry, inputs.get(f"inventory {entry['place']}"), inputs["resting rules"], take)
    standing += json.loads(inputs[CLAIMED].read_text()).get(take, []) if CLAIMED in inputs else []
    return standing, {"skipped": "no floor or held row of its place lays its kind"}


def paint_take(inputs, out, take, record, records):
    """One take painted from its part records (method_surfaces): each part's surface, the labelled folder and
    faces.npz, its report. The surfaces are the records' own (the scene palette offered them), named in the order the
    parts first name them; a take no part of which names a surface stops here."""
    import numpy as np
    import labels
    import patchy
    import split_compare
    import stored_parts
    entry = data_of(inputs)["takes"][take]
    part_of = np.load(inputs["parts"] / take / "parts.npy").astype(int)
    colours = np.load(inputs["parts"] / take / "colours.npy")
    mesh = split_compare.raw_model(take)
    if not any(record.get("surface") for record in records):
        raise RuntimeError(f"{take}: no part names a surface")
    names = []
    chosen = bordered(mesh, part_of, records, names)
    unnamed = [part for part in range(len(records)) if chosen[part] < 0]
    safe = np.where(chosen < 0, 0, chosen)
    painted_parts = colour_joined_parts(mesh, part_of, safe, colours)
    painted = safe[part_of]
    folder = out / "labelled" / take
    folder.mkdir(parents=True)
    np.savez_compressed(folder / "faces.npz", surface=painted.astype(np.int16), part=part_of.astype(np.int32),
                        painted_part=painted_parts.astype(np.int32), names=np.array(names))
    matrix, gap, bounds = finished_frame(mesh, take)
    order = sorted({names[index] for index in np.unique(painted)})
    face_labels = np.array([order.index(name) if name in order else -1 for name in names])[painted]
    moved = mesh.copy()
    moved.apply_transform(matrix)
    standing, levelled = feet_rows(entry, inputs, take)
    if standing:
        tall = max((row["size"][2] for row in standing if len(row.get("size") or ()) == 3), default=None)
        moved.vertices, levelled = levelled_feet(moved.vertices, moved.faces, tall)
    shares, _ = labels.write_parts(moved, face_labels, order, part_of, painted_parts, bounds, folder)
    kept, kept_labels, _, kept_parts = patchy.labelled_parts(folder)
    report = {"take": take, "method": record["method"], "kind": entry["kind"], "parts": records, "shares": shares,
              "judge_unknown": record["judge_unknown"], "unnamed_parts": unnamed,
              "finishes": record.get("finishes", []),
              "unnamed_share": round(sum(row["share"] for row in records if row["part"] in unnamed), 4),
              "painted_parts": int(painted_parts.max()) + 1, "upright_gap": round(gap, 4), "feet": levelled,
              "patchy": patchy.score(kept, kept_labels, kept_parts, patchy.labelled_regions(folder, kept))}
    stored_parts.write(folder, take, target=folder)
    (folder / "labels.json").write_text(json.dumps(report, indent=1))
    return report


def make_paint(inputs, out, seed, params):
    """Every take painted on rented processor machines, one job a take spread over them (blender_cloud.py,
    inside/paint_take.py: most takes peak at 1.5 to 3.4 GB, campgrounds' crane-r1 at 34.8 GB, past the PC's 14 GB cap,
    2026-10-12; heavy steps run in the cloud); the method's proposals go into the finish
    registry here first. painted.json (with the takes the method left out)."""
    from registry import Registry
    from score.store import Store
    short = prop_env.short(inputs)
    data = data_of(short)
    method = json.loads((short["parts"] / "parts.json").read_text())
    registry = Registry(Store.default())
    jobs = [paint_job(inputs, short, out, take,
                      method_surfaces(take, data["takes"][take]["place"], record["parts"], registry))
            for take, record in method["takes"].items()]
    done = subprocess.run([str(prop_env.PROPS_PYTHON), str(REPO / "tools/cloud/blender_cloud.py"), *map(str, jobs), "--who",
                           f"surfaces-paint-{data['place']}", "--classes", PAINT_CLASSES], cwd=REPO,
                          capture_output=True, text=True)
    (out / "paint.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    if done.returncode:
        raise RuntimeError(f"blender_cloud.py paint failed: {done.stderr[-3000:]}")
    for path in out.glob(".paint-*"):
        path.unlink()
    found = {take: json.loads((out / "labelled" / take / "labels.json").read_text()) for take in method["takes"]}
    (out / "painted.json").write_text(json.dumps({"takes": found, "left_out": method["left_out"]}, indent=1))


def paint_job(inputs, short, out, take, records):
    """One take's cloud job file: its listing (the make's inputs, the take, its part records, PROPS_HOME) and every
    file the paint reads at its own path (the repository's code and data it imports and reads, the take's raw,
    finished and turned models, its parts); its labelled folder comes back."""
    listing, kept = out / f".paint-{take}.json", out / f".paint-{take}-records.json"
    claimed = out / f".paint-{take}-claimed.json"
    kept.write_text(json.dumps(records))
    claimed.write_text(json.dumps({take: claimed_rows(take, inputs)}))
    listing.write_text(json.dumps({**{name: str(path) for name, path in inputs.items()}, TAKE: take,
                                   RECORDS: str(kept), CLAIMED: str(claimed), HOME: str(prop_env.PROPS_HOME),
                                   CODE: str(REPO)}))
    pixal = prop_env.PROPS_HOME / "work/pixal"
    models = sorted({pixal / f"{take}.glb", pixal / f"{take}-final.glb", *pixal.glob(f"{take}-[0-9]*.glb")})
    inventories = [path for name, path in short.items() if name.startswith("inventory ")]
    read = [listing, kept, claimed, short["surfaces"], short["parts"] / "parts.json", short["parts"] / take,
            short["resting rules"], *inventories, *models, *(REPO / folder for folder in PAINT_REPO)]
    job = out / f".paint-{take}-job.json"
    job.write_text(json.dumps({"script": "score/stages/surfaces/inside/paint_take.py", "args": [str(listing)],
                               "inputs": [str(path) for path in read], "outputs": [str(out / "labelled" / take)],
                               "minutes": PAINT_MINUTES}, indent=1))
    return job


def paint_take_step(inputs, out):
    """On the rented machine (inside/paint_take.py hands it here): one take painted (paint_take) from its listing's
    take and part records."""
    import heavy
    heavy.refuse_here("the surface stage's paint")
    take = inputs[TAKE].name
    record = json.loads((inputs["parts"] / "parts.json").read_text())["takes"][take]
    paint_take(inputs, out, take, record, json.loads(inputs[RECORDS].read_text()))


def paint_faults(folder):
    return [] if (folder / "painted.json").exists() else ["no painted.json"]


def judge_one_surface(output, inputs, evidence):
    """Every part of every painted model has exactly one library surface (the method's or its bordering part's)."""
    found = json.loads((output / "painted.json").read_text())["takes"]
    failing = [f"{take}: parts {report['unnamed_parts']} unnamed ({report['unnamed_share']:.1%})"
               for take, report in found.items() if report["unnamed_parts"]]
    return gates.verdict("one surface a part", failing, len(found), "models with a part no surface names")


def judge_feet(output, inputs, evidence):
    """Every painted take's feet lie in one plane in its own frame: short legs were stretched down (levelled_feet), a
    foot over FOOT_MOST of its height above the lowest fails by name."""
    found = json.loads((output / "painted.json").read_text())["takes"]
    failing = [f"{take}: {len(report['feet']['refused'])} of {report['feet']['feet']} feet end "
               f"{', '.join(f'{gap:.1%}' for gap in report['feet']['refused'])} of its size over its lowest "
               f"(over {FOOT_MOST:.0%}: a missing leg, not a short one)"
               for take, report in found.items() if report.get("feet", {}).get("refused")]
    levelled = sum(bool(report.get("feet", {}).get("levelled")) for report in found.values())
    return gates.verdict("feet in one plane", failing, len(found), "models with a foot off the plane",
                         {"levelled": levelled})


def judge_concept_colour(output, inputs, evidence):
    """Every finish's library surface lies near its colour in the close-up (the method's `finishes`, each with the
    measured colour and its surface's distance from it): a finish no library surface fits by colour is named, its
    proposed tinted surface in the registry for the owner."""
    found = json.loads((output / "painted.json").read_text())["takes"]
    failing = [f"{take}: {finish['finish']} measured L*a*b* {finish['measured_lab']}, {finish['surface']} dE "
               f"{finish['delta_e']} (proposed: {finish['new_surface']['name']})"
               for take, report in found.items() for finish in report.get("finishes", [])
               if finish.get("by") == "off its colour"]
    swapped = sum(finish.get("by") == "nearest of its family by colour" for report in found.values()
                  for finish in report.get("finishes", []))
    finishes = sum(len(report.get("finishes", [])) for report in found.values())
    return gates.verdict("colour against the close-up", failing, finishes, "finishes no surface fits by colour",
                         {"swapped": swapped})


# --- bake ----------------------------------------------------------------------------------------------------------

def bake_entries(inputs, labelled):
    """The place's bake job and its make_chunky entries for the labelled takes ({take: folder}), written from git
    (bake_job.py): each model the data names, by its entry written out in the data. A model with none stops the bake
    before anything is rented."""
    import bake_job
    data = data_of(inputs)
    import library
    job = bake_job.job_head(library.wear_of(data["library"]), bake_job.specs_of(data["library"]))
    written = data["bake"].get("entries", {})
    # regions: an old job's boxes that forced a variant over the paint (the water tank's top as glass): the method paints
    inventories = [path for key, path in inputs.items() if key.startswith("inventory ") and path]
    chunky = [dict(bake_job.entry_of(name, written.get(name), labelled[take],
                                     bake_job.code_built(take, prop_env.PROPS_HOME),
                                     *bake_job.drawn_guard(take, inventories, inputs)),
                   name=name, parts=str(labelled[take]), regions=[])
              for name, take in data["bake"]["models"].items() if take in labelled]
    return job, chunky


def baking_specs(library_name, specs, labelled):
    """The bake job's specs with every surface today's library knows, painted or the job's own (its decals, screens),
    taken from today's library in the place's palette tokens (library.by_library, the place's own names by
    library.resolved): a job's stored spec can name a picture at a path long gone (the greenhouse's screen and camp's
    locker label, from another checkout, 2026-10-12), and a surface of another library place the take may take from
    is not in it. A spec left naming a picture that is not there stops the bake before anything is rented."""
    import library
    painted = {path.stem for folder in labelled for path in folder.glob("*.ply")}
    every = {**library.by_library(library_name), **library.resolved(library_name)}
    unknown = sorted(painted - set(every) - set(specs))
    if unknown:
        raise RuntimeError(f"surfaces in no library: {unknown}")
    found = {**specs, **{name: every[name] for name in painted | set(specs) if name in every}}
    missing = sorted(name for name, spec in found.items()
                     if "image" in spec and not pathlib.Path(spec["image"]).exists())
    if missing:
        raise RuntimeError(f"specs whose picture is not there: {missing}")
    return found


def unwalked(specs, data):
    """The bake specs as the place paints them: in a place nobody walks (its surface data's `foot_traffic` false, the
    wreck's crash site, 2026-10-13) each says `kicks` 0, so recipes.kick_mask wears nothing there and wear comes only
    from its other causes; a walked place's specs as given."""
    if data.get("foot_traffic", True):
        return specs
    return {name: dict(spec, kicks=0.0) for name, spec in specs.items()}


def make_bake(inputs, out, seed, params):
    """The labelled folders baked on rented cards (library_bake.py make_chunky), one job per model."""
    inputs = prop_env.short(inputs)
    data = data_of(inputs)
    painted = inputs["paint"]
    takes = json.loads((painted / "painted.json").read_text())["takes"]
    labelled = {take: painted / "labelled" / take for take in takes}
    job, chunky = bake_entries(inputs, labelled)
    job["specs"] = unwalked(baking_specs(data["library"], job["specs"], list(labelled.values())), data)
    jobs = []
    for entry in chunky:
        one = dict(job, chunky=[entry], out=str(out / "made"), report=f"report-{entry['name']}.json")
        path = out / f".job-{entry['name']}.json"
        path.write_text(json.dumps(one, indent=1))
        jobs.append(str(path))
    done = subprocess.run([str(prop_env.PROPS_PYTHON), str(REPO / "tools/cloud/library_bake.py"), *jobs, "--who",
                           f"surfaces-{data['place']}", "--classes", CLASSES], cwd=REPO, capture_output=True,
                          text=True)
    (out / "bake.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    if done.returncode:
        raise RuntimeError(f"library_bake.py failed: {done.stderr[-2000:]}")
    (out / "baked.json").write_text(json.dumps({entry["name"]: dict(entry, parts=pathlib.Path(entry["parts"]).name)
                                                for entry in chunky}, indent=1))
    (out / "elsewhere.json").write_text(json.dumps(claims(inputs), indent=1))
    for path in jobs:
        pathlib.Path(path).unlink()


def claims(inputs):
    """The models the place lays that another place claims (its data's `elsewhere`), each read from that place's
    bake: {model: {take, place, node (that place's bake row), baked_as (the model that place bakes the take as, None
    when it bakes none)}}."""
    found = {}
    for model, claim in data_of(inputs).get("elsewhere", {}).items():
        other = json.loads(inputs[f"claimed {claim['place']}"].read_text())
        baked_as = sorted(name for name, take in other.get("bake", {}).get("models", {}).items()
                          if take == claim["take"] and claim["take"] in other["takes"])
        found[model] = dict(claim, node=f"surfaces-bake@{claim['place']}", baked_as=baked_as[0] if baked_as else None)
    return found


def bake_faults(folder):
    if not (folder / "baked.json").exists():
        return ["no baked.json"]
    missing = [name for name in json.loads((folder / "baked.json").read_text())
               if not (folder / "made" / f"{name}.gltf").exists()]
    return [f"no baked model for {missing}"] if missing else []


def judge_baked(output, inputs, evidence):
    """Every painted model came back baked, and every model the place lays that another place claims is baked by
    that place (its claim names a take that place lists and bakes); a model no place bakes fails."""
    baked = json.loads((output / "baked.json").read_text())
    painted = json.loads((prop_env.short(inputs)["paint"] / "painted.json").read_text())["takes"]
    failing = [f"{take}: not baked (no model of the place's data takes it)" for take in painted
               if take not in {entry["parts"] for entry in baked.values()}]
    claimed = json.loads((output / "elsewhere.json").read_text())
    failing += [f"{model}: claimed by {claim['place']}, which does not bake {claim['take']}"
                for model, claim in claimed.items() if claim["baked_as"] is None]
    return gates.verdict("baked", failing, len(painted) + len(claimed), "models not baked here or by their claim")


# --- check ---------------------------------------------------------------------------------------------------------

def baked_surfaces(geometry, labelled, entry):
    """Each baked triangle's surface (the labelled part, one .ply per surface, whose nearest point lies under the
    triangle's middle, the parts laid into the kit frame as make_chunky lays them, stored_parts.kit_frame) and
    whether it lies inside its part (all three corners' nearest points on it too)."""
    import numpy as np
    import trimesh
    from scipy.spatial import cKDTree
    import stored_parts
    points, names = [], []
    for path in sorted(labelled.glob("*.ply")):
        vertices = np.asarray(trimesh.load(path, process=False).vertices)
        vertices = vertices[::max(1, len(vertices) // PART_POINTS)]
        points.append(vertices)
        names += [path.stem] * len(vertices)
    laid = stored_parts.kit_frame(np.vstack(points), np.array(entry["base"]).reshape(3, 3), entry["size"])
    tree, names = cKDTree(laid), np.array(names)
    middles = geometry["positions"][geometry["triangles"]].mean(axis=1)
    surface = names[tree.query(middles)[1]]
    corners = names[tree.query(geometry["positions"])[1]][geometry["triangles"]]
    return surface, (corners == surface[:, None]).all(axis=1)


def check_model(name, entry, labelled, made, materials):
    """One baked model measured: per surface its parts' baked base colour (area-weighted median over its triangles'
    texture at their middles' coordinates; glTF's v runs down the picture) against the surface's colour, its
    near-black share, its maps and its triangles against the job's budget."""
    import numpy as np
    import labels
    import baked_gltf
    from bake_check import gltf_model, map_roles
    geometry, maps = gltf_model(made / f"{name}.gltf")
    roles, missing = map_roles(maps)
    record = {"triangles": int(len(geometry["triangles"])), "budget": int(entry["faces"]),
              "maps": roles, "surfaces": {}}
    record["missing_maps"] = missing
    if "base_color" in record["missing_maps"]:
        return record
    colour = labels.lab(baked_gltf.base_colours(geometry, maps)[0])
    corners = geometry["positions"][geometry["triangles"]]
    areas = 0.5 * np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
    surface, interior = baked_surfaces(geometry, labelled, entry)
    for name_of in sorted(set(surface.tolist())):
        chosen = surface == name_of
        order = np.argsort(colour[chosen, 0])
        weights = np.cumsum(areas[chosen][order])
        middle = colour[chosen][order][np.searchsorted(weights, weights[-1] / 2)]
        token = labels.lab(labels.srgb(np.array(materials[name_of]["colour"]))[None])[0] \
            if name_of in materials else None
        inside = chosen & interior  # a triangle across a border bakes its neighbour's colour (a paper label on black)
        blotch = float(areas[inside & (colour[:, 0] < BLOTCH_L)].sum() / max(areas[inside].sum(), 1e-12))
        record["surfaces"][name_of] = {
            "share": round(float(areas[chosen].sum() / areas.sum()), 4),
            "baked_lab": [round(float(value), 1) for value in middle],
            "surface_lab": None if token is None else [round(float(value), 1) for value in token],
            "delta_e": None if token is None else round(float(np.linalg.norm(middle - token)), 1),
            "near_black": round(blotch, 4)}
    return record


def make_check(inputs, out, seed, params):
    prop_env.handover(__file__, "check", inputs, out)


def check_step(inputs, out):
    """The prop environment's side: every baked model measured (checks.json)."""
    import library
    name = data_of(inputs)["library"]
    materials = {**library.by_library(name), **library.resolved(name)}
    found = {model: check_model(model, entry, inputs["paint"] / "labelled" / entry["parts"], inputs["bake"] / "made",
                                materials)
             for model, entry in json.loads((inputs["bake"] / "baked.json").read_text()).items()}
    (out / "checks.json").write_text(json.dumps(found, indent=1))


def check_faults(folder):
    return [] if (folder / "checks.json").exists() else ["no checks.json"]


def surface_faults(name, record):
    """A baked model's faults against its surfaces: parts off their surface's colour, near-black blotches, a
    surface not in the place's library."""
    faults = []
    for surface, entry in record["surfaces"].items():
        if entry["share"] < PART_LEAST:
            continue
        if entry["delta_e"] is None:
            faults.append(f"{name}: {surface} is not in the place's library")
        elif entry["delta_e"] > BAKE_DELTA_E:
            faults.append(f"{name}: {surface} baked {entry['baked_lab']} against {entry['surface_lab']} "
                          f"(dE {entry['delta_e']})")
        if entry["surface_lab"] and entry["surface_lab"][0] > DARK_SURFACE and entry["near_black"] > BLOTCH_SHARE:
            faults.append(f"{name}: {surface} {entry['near_black']:.1%} near black")
    return faults


def judge_lit(output, inputs, evidence):
    """The baked model matches its surfaces: every part's baked colour on its surface, no blotch, every map."""
    found = json.loads((output / "checks.json").read_text())
    failing = []
    for name, record in found.items():
        failing += [f"{name}: no {role} map" for role in record["missing_maps"]] + surface_faults(name, record)
    return gates.verdict("baked matches its surfaces", failing, len(found), "faults over the models")


def judge_triangles(output, inputs, evidence):
    """Triangles within the bake job's budget per model."""
    found = json.loads((output / "checks.json").read_text())
    failing = [f"{name}: {record['triangles']} triangles over {record['budget']}" for name, record in found.items()
               if record["triangles"] > record["budget"]]
    return gates.verdict("triangles within budget", failing, len(found), "models",
                         {"triangles": sum(record["triangles"] for record in found.values())})


STEPS = {"paint-take": paint_take_step, "check": check_step}

if __name__ == "__main__":
    prop_env.main(STEPS)
