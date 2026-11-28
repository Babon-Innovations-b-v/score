"""A square's crowd laid in its scene (2099 #161; owner, 2026-11-26: "a lot of people walking through walls and the
stage", "u fill them with quick made garbage and throw out the entire openusd scene"): where every person of the
crowd stands, faces and walks is the scene's, measured on its solids, never the game's.

    crowd(folder, toward, prefix="person") -> {faced, packed, walkers, lanes, removed, levels}

The crowd is the laid people whose names start with `prefix` (SkelRoots under Objects). On every floor at least LEAST
of them stand on (to 0.1 m), the floor round them is packed: a jittered CELL grid kept at the spacing of a spot's
distance from `toward` (PACKED within PACKED_WITHIN, thinning to THIN from THIN_FROM; never two nearer than NEAREST),
each spot kept only where its body's column is clear: rays straight down at its middle and eight BODY round it each find that
floor, facing up, with no solid within HEADROOM over it (a stage's top, a stair, a wall, a lamp), and level rays
from its middle at REACH_HEIGHTS meet no solid within its body's reach (REACH, or the most the prototypes' posed
skins reach round their feet) nor, all eight ways at one height, one object (inside a hollow building). Two lanes run out
from `toward` through the crowd (LANE_ANGLE either side of the way to its middle, from LANES_FROM), each as long as
its LANE_WIDTH corridor finds the same clear floor every LANE_STEP; no one stands on a lane, and WALKERS_EVERY metres of
lane gets a walker. Every person faces `toward` by its toes (score_lib's people face their model's -Z), and stands
on its floor by its feet as the check reads them (ready.person_faults: each foot's lowest skin, rays down from
ready.RAY_START over it): lifted or lowered so its lower foot stands on what is under it, and taken out where its other
foot would stand more than STEP off (a step's edge, a kerb), so none sinks or floats (2099 #161: a laid person turned
about its feet on the promenade stood its left foot 1.5 cm in).

What it writes: each laid crowd person turned to face `toward` (its rotateXYZ's y), a laid person whose column is not
clear (inside the stage, a wall) or who stands on a lane taken out; `Objects/crowd`, a PointInstancer of PROTOTYPES of
the laid people (each one's prim copied whole, its Held pose with it) at the packed spots, each turned to `toward`
(its turns written in float as `orientationsf` beside USD's half `orientations`, which no half can hold at unit length:
each copy read as stretched 0.05% across, so the package converted every copy apart and passed 24 GB); and
`Objects/crowd_walkers`, one of the same prototypes at its lane's near or far end, facing along it, its far end in
`score:walks_to` (the package carries it as the copy's `walks`; a game walks it there, over and over, on its walking
clip).
"""
import math

import numpy as np
import trimesh
from pxr import Gf, Sdf, Usd, UsdGeom, UsdSkel, Vt

from score.stages import place_build
from score.stages.place_build import ready

PACKED = 0.5  # metres between two people's middles before the stage: shoulder to shoulder
THIN = 1.9  # ... at the crowd's thin edge
PACKED_WITHIN = 14.0  # metres from `toward` the crowd stands packed
THIN_FROM = 48.0  # ... and from where it stands thin
NEAREST = 0.44  # metres: the nearest two people stand
CELL = 0.4  # metres: the fine grid candidates are laid on
SHAKE = 0.12  # metres a candidate is shaken off its cell's middle either way
HEADROOM = 2.4  # metres over a spot's floor no solid may stand
ON_LEVEL = 0.12  # metres a floor hit may stand off a crowd's floor
BODY = 0.22  # metres round a spot's middle its body's column is read (four rays)
# metres a standing person's skin reaches round its feet in plan (score_lib's people: 0.30 to 0.33 m, a hand at hip
# height; the square's crowd stood 0.22 m clear of the east tenement's facade and its hands cut 26 cm into it, 2099 #161)
REACH = 0.36
REACH_HEIGHTS = (0.25, 0.6, 0.95, 1.3, 1.65)  # metres over a spot's floor its body's reach is read across
LEAST = 40  # a floor is a crowd's when at least this many of its people stand on it
AREA_ROUND = 4.5  # metres round its own people a floor is packed
LANES_FROM = 7.0  # metres from `toward` a lane may start
LANE_ANGLE = 0.42  # radians either side of the way to the crowd's middle the two lanes run
LANE_WIDTH = 1.5  # metres a lane is kept clear of standing people
LANE_STEP = 0.25  # metres between the lane's corridor reads
LANE_REACH = 70.0  # metres from `toward` a lane runs at most
LANE_LEAST = 8.0  # metres: a shorter clear run is no lane
WALKERS_EVERY = 7.0  # metres of lane a walker
WALKER_SIDE = 0.35  # metres off the lane's line a walker keeps (out on one side, back on the other)
PROTOTYPES = 24  # the laid people the packed crowd is copied from
RAY_TOP = 40.0  # metres over the highest floor the rays down start
TILE = 12.0  # metres of plan whose rays are cast together, against the objects whose box meets it
MARGIN = 2.0  # metres round a tile an object's box may stand off and still be cast against (over any reach read)
CHUNK = 20000  # rays cast at once
STEP = 0.5 * ready.CONTACT  # metres a person's two feet may stand apart off their floors: it stands on its lower one


def spacing(metres):
    """The spacing the crowd stands at `metres` from `toward`: PACKED near it, THIN far off, smooth between."""
    share = min(max((metres - PACKED_WITHIN) / (THIN_FROM - PACKED_WITHIN), 0.0), 1.0)
    return PACKED + (THIN - PACKED) * share * share * (3.0 - 2.0 * share)


def spread(seed, salt):
    """A stable spread of `seed` over [0, 1) (a salted 32-bit integer hash), the same every run."""
    value = (seed ^ salt) & 0xFFFFFFFF
    value ^= value >> 16
    value = (value * 0x7FEB352D) & 0xFFFFFFFF
    value ^= value >> 15
    value = (value * 0x846CA68B) & 0xFFFFFFFF
    value ^= value >> 16
    return value / 4294967296.0


def levels_of(heights, least=LEAST):
    """The floors a crowd stands on: the mean of each 0.1 m height at least `least` of `heights` stand at, low first."""
    groups = {}
    for height in heights:
        groups.setdefault(round(float(height), 1), []).append(float(height))
    return sorted(float(np.mean(group)) for group in groups.values() if len(group) >= least)


def floor_of(hits, levels):
    """The floor of `levels` a ray straight down stands on, or None: `hits` [(height, faces up)] from the top; the
    first upward hit on a level (within ON_LEVEL) with nothing hit within HEADROOM over it and not inside a solid (an
    odd count of faces over it: a wall taller than HEADROOM stands on the floor with only its top over it)."""
    for number, (height, upward) in enumerate(hits):
        if not upward:
            continue
        level = next((candidate for candidate in levels if abs(candidate - height) <= ON_LEVEL), None)
        if level is None:
            continue
        over = [above for above, _ in hits[:number] if above > height + 0.05]
        covered = any(above < height + HEADROOM for above in over) or len(over) % 2 == 1
        return None if covered else level
    return None


class Lane:
    """A walkers' lane: from `start` (x, z) along the level unit way `along` for `length` metres, LANE_WIDTH wide."""

    def __init__(self, start, along, length, level):
        self.start, self.along, self.length, self.level = np.asarray(start, float), np.asarray(along, float), length, level

    def holds(self, x, z):
        offset = np.array([x, z]) - self.start
        ahead = offset @ self.along
        across = offset @ np.array([-self.along[1], self.along[0]])
        return 0.0 <= ahead <= self.length and abs(across) <= LANE_WIDTH / 2.0


def fill(low, high, toward, in_area, lanes):
    """The spots [(x, z)] in the box `low`..`high` (x, z) that `in_area` admits, at the spacing of their distance from
    `toward` (x, z), never two nearer than NEAREST and none on a lane."""
    spots, taken = [], {}
    columns = int(math.ceil((high[0] - low[0]) / CELL))
    rows = int(math.ceil((high[1] - low[1]) / CELL))
    for row in range(rows):
        for column in range(columns):
            seed = ((row * 73856093) ^ (column * 19349663)) & 0xFFFFFFFF
            x = low[0] + (column + 0.5) * CELL + SHAKE * (2.0 * spread(seed, 0x9E3779B9) - 1.0)
            z = low[1] + (row + 0.5) * CELL + SHAKE * (2.0 * spread(seed, 0x85EBCA6B) - 1.0)
            gap = spacing(math.hypot(x - toward[0], z - toward[1]))
            if spread(seed, 0xC2B2AE35) >= CELL * CELL / (gap * gap):
                continue
            if any(lane.holds(x, z) for lane in lanes) or not in_area(x, z) or crowded(taken, x, z):
                continue
            spots.append((x, z))
            taken.setdefault((math.floor(x / NEAREST), math.floor(z / NEAREST)), []).append((x, z))
    return spots


def crowded(taken, x, z):
    """Whether a spot already taken lies within NEAREST of (x, z)."""
    cell = (math.floor(x / NEAREST), math.floor(z / NEAREST))
    return any(math.hypot(x - other[0], z - other[1]) < NEAREST
               for step_x in (-1, 0, 1) for step_z in (-1, 0, 1)
               for other in taken.get((cell[0] + step_x, cell[1] + step_z), ()))


class Solids:
    """The scene's solids near the crowd (every object under Objects but people and sky domes, ready.role_of), for rays
    straight down and across: a ground's faces within `low`..`high` (x, z), every other object's whole when any of its
    faces is (a building reaching out of the crowd still closes round a spot inside it). Rays are cast a TILE of plan
    at a time against the objects whose plan box meets it (MARGIN round it), never every face in one ray structure
    (ready.Place's rule: the square's made lamps, poles and screens, half a million faces each, came to 33 million
    faces, whose one structure ran the crowd past 24 GB, 2099 #161)."""

    def __init__(self, stage, place, low, high):
        self.parts, grounds = [], []
        for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren():
            if ready.role_of(prim) in ready.UNSOLID or prim.IsA(UsdGeom.PointInstancer):
                continue
            mesh = ready.solid_of(prim)
            if mesh is None or not len(mesh.faces):
                continue
            faces = mesh.triangles
            plan_low, plan_high = faces[:, :, [0, 2]].min(axis=1), faces[:, :, [0, 2]].max(axis=1)
            near = np.all(plan_high >= low, axis=1) & np.all(plan_low <= high, axis=1)
            if near.any():
                ground = ready.role_of(prim) == "ground"
                kept = faces[near] if ground else faces
                normals = np.cross(kept[:, 1] - kept[:, 0], kept[:, 2] - kept[:, 0])
                up = normals[:, 1] / np.maximum(np.linalg.norm(normals, axis=1), 1e-12)
                box = kept[:, :, [0, 2]].reshape(-1, 2)
                self.parts.append((kept, up, box.min(axis=0), box.max(axis=0)))
                grounds.append(ground)
        if not self.parts:
            raise place_build.Refused("no solid lies under the crowd")
        self.ground = np.array(grounds)

    def cast(self, origins, ways, multiple_hits=True):
        """ready.cast of each ray against the objects whose plan box meets its origin's TILE (MARGIN round it):
        (where, which ray, the object it meets, its face's up share); exact for every hit within MARGIN of its origin
        in plan, and for every hit of a ray straight down."""
        origins, ways = np.asarray(origins, float).reshape(-1, 3), np.asarray(ways, float).reshape(-1, 3)
        tiles = np.floor(origins[:, [0, 2]] / TILE).astype(np.int64)
        found = []
        for tile in np.unique(tiles, axis=0):
            rays = np.flatnonzero(np.all(tiles == tile, axis=1))
            low, high = tile * TILE - MARGIN, (tile + 1) * TILE + MARGIN
            meeting = [number for number, (_, _, part_low, part_high) in enumerate(self.parts)
                       if np.all(part_high >= low) and np.all(part_low <= high)]
            if not meeting:
                continue
            triangles = np.concatenate([self.parts[number][0] for number in meeting])
            owner = np.concatenate([np.full(len(self.parts[number][0]), number) for number in meeting])
            up = np.concatenate([self.parts[number][1] for number in meeting])
            for start in range(0, len(rays), CHUNK):
                chunk = rays[start:start + CHUNK]
                where, hit, faces = ready.cast(triangles, origins[chunk], ways[chunk], multiple_hits=multiple_hits)
                found.append((where.reshape(-1, 3), chunk[hit], owner[faces], up[faces]))
            del triangles, owner, up
        if not found:
            return np.zeros((0, 3)), np.zeros(0, int), np.zeros(0, int), np.zeros(0)
        return tuple(np.concatenate(parts) for parts in zip(*found))

    def down(self, points, top):
        """For each (x, z) of `points`, every hit of a ray straight down from height `top`: [[(height, faces up)]]
        from the top (a face's either side: a stage's underside reads as a solid over the floor)."""
        points = np.asarray(points, float).reshape(-1, 2)
        origins = np.column_stack([points[:, 0], np.full(len(points), top), points[:, 1]])
        where, rays, _, up = self.cast(origins, np.tile([0.0, -1.0, 0.0], (len(points), 1)))
        found = [[] for _ in points]
        for at, ray, share in zip(where, rays, up):
            found[ray].append((float(at[1]), bool(abs(share) > 0.7 and share != 0)))
        return [sorted(hits, key=lambda hit: -hit[0]) for hits in found]

    def across(self, origins, ways):
        """Each ray's first hit: (its distance, the object it meets: -1 for none), inf where it meets nothing; a
        distance is exact within MARGIN, and the object met is the first of those whose box meets its TILE."""
        origins = np.asarray(origins, float).reshape(-1, 3)
        distances, owners = np.full(len(origins), np.inf), np.full(len(origins), -1)
        where, rays, owner, _ = self.cast(origins, ways, multiple_hits=False)
        distances[rays] = np.linalg.norm(where - origins[rays], axis=1)
        owners[rays] = owner
        return distances, owners

    def under(self, points):
        """How far each of `points` (n, 3) stands over the nearest face straight under it, as ready.under_gap reads it
        (from ready.RAY_START over the point; negative: into it); inf where nothing lies under it."""
        points = np.asarray(points, float).reshape(-1, 3)
        gaps = np.full(len(points), np.inf)
        origins = points + [0.0, ready.RAY_START, 0.0]
        where, rays, _, _ = self.cast(origins, np.tile([0.0, -1.0, 0.0], (len(points), 1)))
        np.minimum.at(gaps, rays, origins[rays, 1] - where[:, 1] - ready.RAY_START)
        return gaps


def column_floors(solids, spots, levels, top, reach=REACH):
    """The floor each spot's body column stands on (floor_of at its middle and at eight points BODY round it, all on
    one level), or None where any of its nine rays finds no clear floor or another level, or where its body is not
    clear round it (reached_into)."""
    turns = np.radians(np.arange(0.0, 360.0, 45.0))
    offsets = np.vstack([[0.0, 0.0], BODY * np.column_stack([np.cos(turns), np.sin(turns)])])
    spots = np.asarray(spots, float).reshape(-1, 2)
    hits = solids.down((spots[:, None, :] + offsets[None]).reshape(-1, 2), top)
    floors = []
    for number in range(len(spots)):
        found = {floor_of(hits[number * len(offsets) + ray], levels) for ray in range(len(offsets))}
        floors.append(found.pop() if len(found) == 1 else None)
    standing = [number for number, floor in enumerate(floors) if floor is not None]
    if standing:
        for number in np.asarray(standing)[reached_into(solids, spots[standing], [floors[n] for n in standing], reach)]:
            floors[number] = None
    return floors


def reached_into(solids, spots, floors, reach):
    """Which spots' bodies are not clear round them, read by level rays from the middle at REACH_HEIGHTS over its
    floor, eight ways: one meets a solid within `reach` (over by the most the eight ways leave between them: a hand
    in a facade the rays down never see, its wall a thin skin), or every ray at one height meets one object that is
    not a ground (the spot stands inside a hollow building, its roof and floor slabs an even count of faces over it)."""
    turns = np.radians(np.arange(0.0, 360.0, 45.0))
    ways = np.column_stack([np.cos(turns), np.zeros(len(turns)), np.sin(turns)])
    heights = np.asarray(REACH_HEIGHTS)
    limit = reach / math.cos(math.radians(22.5))
    if limit > MARGIN:
        raise place_build.Refused(f"a body's reach of {reach:.2f} m reads past the {MARGIN} m its rays' solids hold")
    middles = np.column_stack([spots[:, 0], floors, spots[:, 1]])
    origins = (middles[:, None, None, :] + heights[None, :, None, None] * [0.0, 1.0, 0.0]
               + np.zeros((1, 1, len(ways), 1))).reshape(-1, 3)
    distances, owners = solids.across(origins, np.tile(ways, (len(spots) * len(heights), 1)))
    distances = distances.reshape(len(spots), len(heights), len(ways))
    owners = owners.reshape(len(spots), len(heights), len(ways))
    near = (distances < limit).any(axis=(1, 2))
    walled = (owners >= 0) & ~solids.ground[np.maximum(owners, 0)]
    enclosed = (walled.all(axis=2) & (owners == owners[:, :, :1]).all(axis=2)).any(axis=1)
    return near | enclosed


def toes_forward(prim):
    """The way a laid person faces in its own frame (before its own transform), level and of unit length: its feet to
    its toes at rest, both feet summed (score_lib's toes splay 18 degrees out to each side)."""
    skeleton = next(UsdSkel.Skeleton(inside) for inside in Usd.PrimRange(prim) if inside.IsA(UsdSkel.Skeleton))
    query = UsdSkel.Cache().GetSkelQuery(skeleton)
    order = [str(path).split("/")[-1] for path in query.GetJointOrder()]
    rest = query.ComputeJointSkelTransforms(Usd.TimeCode.Default(), True)
    frame = np.asarray(UsdGeom.XformCache().ComputeRelativeTransform(skeleton.GetPrim(), prim)[0])
    way = np.zeros(3)
    for side in ("Left", "Right"):
        foot, toe = order.index(f"{side}Foot"), order.index(f"{side}ToeBase")
        points = np.array([list(rest[foot].ExtractTranslation()) + [1.0], list(rest[toe].ExtractTranslation()) + [1.0]])
        placed = points @ frame
        way += placed[1, :3] - placed[0, :3]
    way[1] = 0.0
    return way / np.linalg.norm(way)


def heading(way):
    """The heading of a level way, radians, as a turn about +y increases it (USD's rotateY)."""
    return math.atan2(way[0], way[2])


def yaw_to(forward, at, toward):
    """The turn about +y, degrees, that points `forward` (the person's own) from `at` at `toward`."""
    return math.degrees(heading(np.array([toward[0] - at[0], 0.0, toward[2] - at[2]])) - heading(forward))


def laid_crowd(stage, place, prefix):
    """The laid crowd: every SkelRoot under Objects whose name starts with `prefix`."""
    return [prim for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren()
            if prim.GetName().startswith(prefix) and prim.IsA(UsdSkel.Root)]


def feet_of(prim):
    return np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))[3, :3]


def feet_points(body):
    """The lowest skin of each foot of a posed body (ready.contact_of's FOOT // 10 points), left then right; None for a
    body with no skin or no foot."""
    if body is None:
        return None
    feet = []
    for side in (ready.people.LEFT, ready.people.RIGHT):
        points = body.points_of(*ready.people.PARTS["feet"], side=side)
        if not len(points):
            return None
        feet.append(points[np.argsort(points[:, 1])[:ready.FOOT // 10]])
    return feet


def lifts_of(solids, people_feet):
    """How far each person of `people_feet` (feet_points each) moves up so its lower foot stands on what is under it,
    or None where a foot finds nothing under it or its other foot would then stand over STEP off its own (all their
    rays cast at once: one ray structure of the solids, never one a person)."""
    feet = [foot for one in people_feet if one is not None for foot in one]
    gaps = solids.under(np.vstack(feet)) if feet else np.zeros(0)
    lifts, start = [], 0
    for one in people_feet:
        if one is None:
            lifts.append(None)
            continue
        lowest = []
        for foot in one:
            lowest.append(float(gaps[start:start + len(foot)].min()))
            start += len(foot)
        standing = all(np.isfinite(lowest)) and abs(lowest[0] - lowest[1]) <= STEP
        lifts.append(-min(lowest) if standing else None)
    return lifts


def stood(stage, solids, people_laid):
    """The laid crowd stood on its floor by its feet (lift_of, each one's translate moved up or down); the names of
    those that cannot stand, their prims removed."""
    fallen = set()
    lifts = lifts_of(solids, [feet_points(ready.people.posed_body(prim)) for prim in people_laid])
    for prim, lift in zip(people_laid, lifts):
        if lift is None:
            fallen.add(prim.GetName())
            continue
        translate = {op.GetOpName(): op for op in UsdGeom.Xformable(prim).GetOrderedXformOps()}["xformOp:translate"]
        at = translate.Get()
        translate.Set(type(at)(at[0], at[1] + lift, at[2]))
    for path in [prim.GetPath() for prim in people_laid if prim.GetName() in fallen]:
        stage.RemovePrim(path)
    return fallen


def stood_rows(stage, solids, path, prototypes, rows):
    """`rows` [(prototype number, feet, yaw, ...)] stood on their floor by their copies' feet (lifts_of over the copies
    as the package and the check read it, skinned.copies_of), those that cannot stand left out; the instancer at
    `path` written with them."""
    from score.stages.place_build import skinned  # skinned reads the package, which reads this module's place_build
    instancer = instanced(stage, path, prototypes, rows)
    feet, frames, copied = {}, {}, []
    for root, _, world in skinned.copies_of(instancer.GetPrim()):
        key = str(root.GetPath())
        if key not in feet:
            feet[key] = feet_points(ready.people.posed_body(root))
            frames[key] = np.linalg.inv(np.asarray(
                UsdGeom.Xformable(root).ComputeLocalToWorldTransform(Usd.TimeCode.Default())))
        move = frames[key] @ world
        copied.append(None if feet[key] is None else [points @ move[:3, :3] + move[3, :3] for points in feet[key]])
    kept = [(row[0], (row[1][0], row[1][1] + lift, row[1][2]), *row[2:])
            for row, lift in zip(rows, lifts_of(solids, copied)) if lift is not None]
    instanced(stage, path, prototypes, kept)
    return kept


def faced(prim, toward):
    """The laid person `prim` turned about its feet to face `toward` (its rotateXYZ's y, kept level)."""
    ops = {op.GetOpName(): op for op in UsdGeom.Xformable(prim).GetOrderedXformOps()}
    turn = ops["xformOp:rotateXYZ"]
    turn.Set(Gf.Vec3f(0.0, float(yaw_to(toes_forward(prim), feet_of(prim), toward)), 0.0))


def lanes_of(solids, middle, toward, levels, top):
    """The two lanes out from `toward` through the crowd's `middle`, LANE_ANGLE either side, each from where its
    corridor first finds a clear crowd floor to where it stops finding that one (at least LANE_LEAST long)."""
    outward = np.array([middle[0] - toward[0], middle[2] - toward[2]])
    outward /= np.linalg.norm(outward)
    found = []
    for angle in (-LANE_ANGLE, LANE_ANGLE):
        along = np.array([outward[0] * math.cos(angle) - outward[1] * math.sin(angle),
                          outward[0] * math.sin(angle) + outward[1] * math.cos(angle)])
        across = np.array([-along[1], along[0]])
        steps = np.arange(LANES_FROM, LANE_REACH, LANE_STEP)
        centres = np.array([toward[0], toward[2]]) + steps[:, None] * along
        reads = (centres[:, None, :] + np.array([-1.0, 0.0, 1.0])[None, :, None] * (LANE_WIDTH / 2.0) * across).reshape(-1, 2)
        floors = column_floors(solids, reads, levels, top)
        level, start, length = None, None, 0.0
        for number, metres in enumerate(steps):
            row = set(floors[number * 3:number * 3 + 3])
            clear = len(row) == 1 and None not in row
            if level is None:
                if clear:
                    level, start = row.pop(), metres
                continue
            if not clear or row.pop() != level:
                break
            length = metres - start
        if level is not None and length >= LANE_LEAST:
            found.append(Lane(np.array([toward[0], toward[2]]) + start * along, along, length, level))
    return found


def prototypes_of(stage, place, people, count=PROTOTYPES):
    """`count` of the laid people spread over them in name order, each copied whole under Objects/crowd/Prototypes
    (its look, dress and Held pose), stood at the origin unturned with its own size: [(path, its forward)]."""
    layer = stage.GetRootLayer()
    holder = f"/{place}/Objects/crowd/Prototypes"
    UsdGeom.Scope.Define(stage, holder)
    chosen = sorted(people, key=lambda prim: prim.GetName())
    chosen = [chosen[int(number * len(chosen) / count)] for number in range(min(count, len(chosen)))]
    made = []
    for number, prim in enumerate(chosen):
        path = f"{holder}/p{number}"
        if not Sdf.CopySpec(layer, prim.GetPath(), layer, Sdf.Path(path)):
            raise place_build.Refused(f"{prim.GetName()}: its prim could not be copied into the crowd")
        copied = stage.GetPrimAtPath(path)
        _retarget(copied, prim.GetPath(), copied.GetPath())
        ops = {op.GetOpName(): op for op in UsdGeom.Xformable(copied).GetOrderedXformOps()}
        ops["xformOp:translate"].Set(Gf.Vec3d(0.0, 0.0, 0.0))
        ops["xformOp:rotateXYZ"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
        made.append((path, toes_forward(copied)))
    return made


def _retarget(prim, old, new):
    """Every relationship under `prim` that named a path under `old` (its Held pose) pointed under `new` instead."""
    for inside in Usd.PrimRange(prim):
        for relation in inside.GetRelationships():
            targets = relation.GetTargets()
            if any(target.HasPrefix(old) for target in targets):
                relation.SetTargets([target.ReplacePrefix(old, new) for target in targets])


def instanced(stage, path, prototypes, rows):
    """A PointInstancer at `path` of `prototypes` (paths), one instance per row (prototype number, feet, yaw degrees)."""
    instancer = UsdGeom.PointInstancer.Define(stage, path)
    instancer.CreatePrototypesRel().SetTargets([Sdf.Path(prototype) for prototype in prototypes])
    instancer.CreateProtoIndicesAttr().Set(Vt.IntArray([row[0] for row in rows]))
    instancer.CreatePositionsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*map(float, row[1])) for row in rows]))
    turns = [Gf.Rotation(Gf.Vec3d(0.0, 1.0, 0.0), float(row[2])).GetQuat() for row in rows]
    instancer.CreateOrientationsAttr().Set(Vt.QuathArray([Gf.Quath(turn) for turn in turns]))
    instancer.CreateOrientationsfAttr().Set(Vt.QuatfArray([Gf.Quatf(turn) for turn in turns]))
    instancer.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("character")
    return instancer


def crowd(folder, toward, prefix="person"):
    """The laid crowd faced, packed and walked as the module says; the scene saved. `toward` an object's name (the
    leader) or an (x, y, z)."""
    stage, place = place_build.opened(folder)
    if isinstance(toward, str):
        target = stage.GetPrimAtPath(f"/{place}/Objects/{toward}")
        if not target:
            raise place_build.Refused(f"the scene holds no {toward} to face")
        toward = feet_of(target)
    toward = np.asarray(toward, float)
    for stale in ("crowd", "crowd_walkers"):
        if stage.GetPrimAtPath(f"/{place}/Objects/{stale}"):
            stage.RemovePrim(f"/{place}/Objects/{stale}")
    people = laid_crowd(stage, place, prefix)
    if not people:
        raise place_build.Refused(f"the scene lays no person named {prefix}*")
    feet = np.array([feet_of(prim) for prim in people])
    levels = levels_of(feet[:, 1])
    if not levels:
        raise place_build.Refused(f"no floor holds {LEAST} of the crowd")
    plan = feet[:, [0, 2]]
    low, high = plan.min(axis=0) - AREA_ROUND, plan.max(axis=0) + AREA_ROUND
    low, high = np.minimum(low, toward[[0, 2]] - 1.0), np.maximum(high, toward[[0, 2]] + 1.0)
    solids = Solids(stage, place, low - 1.0, high + 1.0)
    top = max(levels) + RAY_TOP
    lanes = lanes_of(solids, feet.mean(axis=0), toward, levels, top)
    kept = [prim.GetPath() for prim in people]
    removed = laid_removed(stage, solids, people, feet, lanes, top)
    people = [stage.GetPrimAtPath(path) for path in kept if path.name not in removed]
    for prim in people:
        faced(prim, toward)
    kept = [prim.GetPath() for prim in people]
    fallen = stood(stage, solids, people)
    removed |= fallen
    people = [stage.GetPrimAtPath(path) for path in kept if path.name not in fallen]
    feet = np.array([feet_of(prim) for prim in people])
    prototypes = prototypes_of(stage, place, people)
    paths = [path for path, _ in prototypes]
    reach = max([REACH] + [reach_of(ready.people.posed_body(stage.GetPrimAtPath(path))) for path in paths])
    rows = stood_rows(stage, solids, f"/{place}/Objects/crowd", paths,
                      packed_rows(solids, feet, levels, lanes, toward, prototypes, top, reach))
    walkers = stood_rows(stage, solids, f"/{place}/Objects/crowd_walkers", paths, walker_rows(lanes, prototypes))
    walking = UsdGeom.PointInstancer(stage.GetPrimAtPath(f"/{place}/Objects/crowd_walkers"))
    walking.GetPrim().CreateAttribute("score:walks_to", Sdf.ValueTypeNames.Point3fArray).Set(
        Vt.Vec3fArray([Gf.Vec3f(*map(float, to)) for *_, to in walkers]))
    place_build.saved(stage)
    return {"faced": len(people), "packed": len(rows), "walkers": len(walkers), "removed": sorted(removed),
            "lanes": [{"from": [round(float(value), 3) for value in lane.start], "metres": round(lane.length, 2),
                       "level": round(lane.level, 3)} for lane in lanes],
            "levels": [round(level, 3) for level in levels]}


def laid_removed(stage, solids, people, feet, lanes, top):
    """The laid crowd people taken out (by name): one standing on a lane, or whose body's column finds no clear floor
    at its own height (inside the stage, a wall or a lamp); each prim removed from the scene."""
    removed = set()
    columns = column_floors(solids, feet[:, [0, 2]], sorted({round(float(height), 3) for height in feet[:, 1]}), top)
    for prim, at, column in zip(people, feet, columns):
        if any(lane.holds(at[0], at[2]) for lane in lanes) or column is None or abs(column - at[1]) > ON_LEVEL:
            removed.add(prim.GetName())
    for path in [prim.GetPath() for prim in people if prim.GetName() in removed]:
        stage.RemovePrim(path)
    return removed


def reach_of(body):
    """How far a prototype's posed skin reaches round its feet (it stands unturned at the origin) in plan: 0 with no
    skin."""
    if body is None:
        return 0.0
    points = np.asarray(body.mesh.vertices)
    return float(np.hypot(points[:, 0], points[:, 2]).max(initial=0.0))


def packed_rows(solids, feet, levels, lanes, toward, prototypes, top, reach=REACH):
    """The packed crowd's instances [(prototype number, feet, yaw)]: fill's spots round each floor's own people whose
    body's column stands clear on that floor and clear of the laid people, each a prototype by a stable spread."""
    rows = []
    taken = {}
    for at in feet:
        taken.setdefault((math.floor(at[0] / NEAREST), math.floor(at[2] / NEAREST)), []).append((at[0], at[2]))
    for level in levels:
        own = feet[np.abs(feet[:, 1] - level) <= ON_LEVEL]
        if not len(own):
            continue
        cells = {(math.floor(at[0] / AREA_ROUND), math.floor(at[2] / AREA_ROUND)) for at in own}

        def in_area(x, z, cells=cells):
            cell = (math.floor(x / AREA_ROUND), math.floor(z / AREA_ROUND))
            return any((cell[0] + step_x, cell[1] + step_z) in cells for step_x in (-1, 0, 1) for step_z in (-1, 0, 1))

        low = own[:, [0, 2]].min(axis=0) - AREA_ROUND
        high = own[:, [0, 2]].max(axis=0) + AREA_ROUND
        spots = [spot for spot in fill(low, high, toward[[0, 2]], in_area, lanes)
                 if not crowded(taken, *spot)]
        floors = column_floors(solids, spots, levels, top, reach) if spots else []
        for number, ((x, z), floor) in enumerate(zip(spots, floors)):
            if floor is None or abs(floor - level) > 0.01:
                continue
            seed = (int(round(x * 100)) * 73856093 ^ int(round(z * 100)) * 19349663) & 0xFFFFFFFF
            prototype = int(spread(seed, 0x27D4EB2F) * len(prototypes))
            at = (x, floor, z)
            rows.append((prototype, at, yaw_to(prototypes[prototype][1], at, toward)))
    return rows


def walker_rows(lanes, prototypes):
    """The walkers [(prototype number, start, yaw, the end it walks to)]: WALKERS_EVERY metres of each lane one, each
    the whole lane from one end to the other, every other one walking back toward `toward`, each WALKER_SIDE off the
    line on its own side (a game spreads them along it, each starting at its own point of the way)."""
    rows = []
    for lane_number, lane in enumerate(lanes):
        for walker in range(max(1, int(lane.length / WALKERS_EVERY))):
            back = walker % 2 == 1
            side = np.array([-lane.along[1], lane.along[0]]) * (WALKER_SIDE if back else -WALKER_SIDE)
            near, far = lane.start + side, lane.start + lane.along * lane.length + side
            start, end = (far, near) if back else (near, far)
            seed = (lane_number * 92821 + walker * 68917) & 0xFFFFFFFF
            prototype = int(spread(seed, 0x7FEB352D) * len(prototypes))
            way = np.array([end[0] - start[0], 0.0, end[1] - start[1]])
            yaw = math.degrees(heading(way) - heading(prototypes[prototype][1]))
            rows.append((prototype, (start[0], lane.level, start[1]), yaw, (end[0], lane.level, end[1])))
    return rows
