"""Physics ready: everything about a place_build scene that keeps the walkers (sim body, MuJoCo) from walking in it and
pushing its objects, told per object for the placing agent, and the `on` helper that lays an object at rest on a
named support.

    check(folder, settle=True) -> {counts..., "file": <folder>/ready.json}
    on(folder, name, support, level=None, height=None)
    solids(folder) -> {object: triangles}       what a walker stands on and runs into (sim body's, scene clips' ground)
    route(folder, through) -> (points, length)  a walker's way through spots on the walkers' floor WALKWAY wide

Each object of /<place>/Objects has a role, from its `score:role` when it has one, else from what it is: `ground` (a
laid ground or terrain), `shell` and `connector` (the dome shell algorithm's domes and tubes), `door` (a door, hatch or
airlock), `structure` (a wall, bulkhead, frame), `fixed` (a rock bedded in the ground, or `score:fixed`), `mount` (on a
wall: `on ... wall:<object>`), `character` (a person, posed as the renderer poses it: people.py), `light` (a sky dome
laid as an object, `score:kind` light: light the renderer draws, never a solid, so left out of every measure) or `prop`
(everything else: it can be pushed). The faults, each with its measure:

- `no collision geometry`: an object with no triangles to collide by.
- `floating`: a prop, fixed piece, structure or door whose lowest points clear what is under them by over TOLERANCE
  (the gap and the support named); `no support`: nothing at all under it; `tips`: its weight (the middle of its
  surface) falls over BALANCE outside what it touches (resting.py's measures).
- `penetration`: a sample of an object's surface lies inside another (a ray from the object's middle to the point
  crosses the other's surface an odd number of times; the depth is how far past its last crossing), or its middle
  lies inside another closed object; joined structure and a rock bedded in the ground are not faults.
- `door not in an opening`: a door with no wall or shell round its sides and top within FRAME, or a wall straight
  behind it (no opening cut).
- `door does not fit`: seen straight through the door's plane on a FIT_CELL grid, the opening round it (what no wall,
  shell or connector closes within FIT_DEPTH of it, from its threshold up) shows a gap wider than FIT between the
  door's outline and the wall, or the door lies over the wall further than FIT past the opening's edge (a hinge or a
  latch, shorter than HINGE, lies on its jamb): a leaf that is not the opening's shape and size (a rectangular
  door in a round opening, a hatch too small for it).
- `person floating` / `person sinks`: a person's feet (each foot's lowest skin; a walker's planted, lower foot alone,
  `walks`), or, seated, the seat, more than
  CONTACT over or into what is under them; a person's skin inside another object is `penetration` as above.
- `broken body`: a person's skin torn by its skinning, a missing head, hand or foot, or a height or proportions no
  person has (people.shape_faults).
- `walkway`: the walkers' floor (reach.py's Recast-style spans of every surface, doors open, eroded by half of WALKWAY)
  does not join both sides of every door, and every shell and connector, in one walkable piece WALKWAY wide.
- `connector`: a tube whose end ring stays over JOIN from every other shell or structure, or that has no walkable floor
  along its length.
- `unstable`: let go in MuJoCo (settle_mujoco.py, in the physics trial's Python), it moves over SETTLE_MOVE or turns
  over SETTLE_TURN.
"""
import json
import os
import pathlib
import subprocess
import sys

import numpy as np
import trimesh
from scipy import ndimage
from pxr import Sdf, Usd, UsdGeom

from score.stages import place_build

from score.stages.place_build.ready import people

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "tools/usd"))
import reach  # noqa: E402
import resting  # noqa: E402

TOLERANCE = resting.TOLERANCE  # metres off a support, or into another, that still rests
BALANCE = resting.BALANCE
RAY_START = 0.1  # rays down start this far over each point, so a point bedded a little still finds its support's top
FOOT = 300  # how many of an object's lowest points look down for its support
SAMPLES = 500  # how many points of an object's surface are tested for lying inside another
PIECE = 0.01  # a connected part with less of an object's surface is no piece of its own (its middle unused)
INSIDE_WAYS = ((0.0, 1.0, 0.0), (0.37, 0.81, 0.45), (-0.52, 0.29, -0.8))  # odd ways, off any axis
MAX_SPLIT = 200_000  # an object with more faces is taken whole, not split into its pieces
FRAME = 0.3  # how far past a door's edge its wall must be (metres)
GROUND_REACH = 20.0  # metres of ground kept round the laid objects (a walker's stroll past the place's edge)
WALKWAY = 0.9  # the narrowest way the walkers need (owner's brief, 2026-11-16: at least 0.9 m)
ERODED = int((WALKWAY / reach.CELL - 1) // 2)  # cells taken off each side of a way, so one WALKWAY wide keeps one
INPUT = "place-build"  # the input a sim body or scene clips run takes a place_build scene's folder by
ROUND = 0.6  # metres before and after a route's corner its turn starts and ends (at most a third of either leg)
TURN_POINTS = 7  # points along a corner's turn
JOIN = 0.3  # how near a connector's end ring must come to the structure it joins (metres)
CONNECTOR_STEP = 0.25  # a connector's floor is looked for this often along it (metres)
FIT = 0.05  # metres a door's outline may stand off its opening's edge, or lie over the wall past it
FIT_CELL = 0.02  # metres between the rays read through a door's plane
FIT_DEPTH = 0.5  # metres before and behind a door's plane where a wall closes its opening
HINGE = 0.25  # metres: what juts from a door's edge on a shorter stretch (a hinge, a latch) may lie on its jamb
CONTACT = 0.01  # metres a person's foot or seat may stand off, or sink into, what is under it
SETTLE_MOVE = 0.05  # metres
SETTLE_TURN = 8.0  # degrees
NEAR = 0.15  # how far past a loose object's box its statics reach in the settle (metres)
ROLES = ("ground", "shell", "connector", "door", "structure", "fixed", "mount", "character", "light", "prop")
UNSOLID = ("character", "light")  # roles that are no solid of their own (a person is posed apart: people.py)
DOOR_WORDS = ("door", "hatch", "airlock")
STRUCTURE_WORDS = ("wall", "bulkhead", "partition", "frame", "fence")
CONNECTOR_WORDS = ("tube", "tunnel", "corridor", "connector")
BEDDED_WORDS = ("rock", "boulder", "stone")
SUPPORTED = ("prop", "fixed", "structure", "door")
JUDGED_INSIDE = ("prop", "fixed", "structure", "door", "mount")
SETTLE_ENV = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "envs/newton_env"
SETTLE_SCRIPT = pathlib.Path(__file__).resolve().parent / "settle_mujoco.py"


# --- the scene as solids ----------------------------------------------------------------------------------------

def fans(counts, indices):
    """A mesh's faces (`counts` corners each, `indices` in a row) as triangles fanned from each face's first corner."""
    triangles, at = [], 0
    for count in counts:
        triangles += [(indices[at], indices[at + corner], indices[at + corner + 1]) for corner in range(1, count - 1)]
        at += count
    return np.asarray(triangles, dtype=np.int64).reshape(-1, 3)


def gprim_triangles(prim):
    """A drawn Mesh or Cube's points in its own frame and its triangles; None for any other prim."""
    if prim.IsA(UsdGeom.Mesh):
        mesh = UsdGeom.Mesh(prim)
        points = mesh.GetPointsAttr().Get()
        if not points:
            return None
        return np.asarray(points, dtype=np.float64), fans(mesh.GetFaceVertexCountsAttr().Get(),
                                                           mesh.GetFaceVertexIndicesAttr().Get())
    if prim.IsA(UsdGeom.Cube):
        box = trimesh.creation.box([UsdGeom.Cube(prim).GetSizeAttr().Get()] * 3)
        return np.asarray(box.vertices), np.asarray(box.faces)
    return None


def solid_of(prim):
    """Every drawn mesh and cube under an object, in the scene's frame, as one mesh; None when it has none."""
    pieces = []
    for inside in Usd.PrimRange(prim):
        imageable = UsdGeom.Imageable(inside)
        if not imageable or imageable.ComputeVisibility() == UsdGeom.Tokens.invisible \
                or imageable.ComputePurpose() not in (UsdGeom.Tokens.default_, UsdGeom.Tokens.render):
            continue
        found = gprim_triangles(inside)
        if found is None or not len(found[1]):
            continue
        matrix = np.asarray(UsdGeom.Xformable(inside).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        pieces.append(trimesh.Trimesh(found[0] @ matrix[:3, :3] + matrix[3, :3], found[1], process=False))
    return trimesh.util.concatenate(pieces) if pieces else None


def text_of(prim, name):
    attribute = prim.GetAttribute(name)
    return attribute.Get() if attribute and attribute.HasValue() else None


def role_of(prim):
    """An object's role (ROLES): its `score:role`, else read from its marks, kind, name and library address."""
    given = text_of(prim, "score:role")
    if given:
        return given
    if text_of(prim, "score:ground"):
        return "ground"
    words = f"{prim.GetName()} {text_of(prim, 'score:library') or ''}".lower()
    kind = text_of(prim, "score:kind")
    if kind in ("character", "light"):
        return kind
    if kind == "algorithm":
        tube = "tube_" in str(prim.GetMetadata("references")) or any(word in words for word in CONNECTOR_WORDS)
        return "connector" if tube else "shell"
    if any(word in words for word in DOOR_WORDS):
        return "door"
    if any(word in words for word in STRUCTURE_WORDS):
        return "structure"
    if text_of(prim, "score:fixed") or any(word in words for word in BEDDED_WORDS):
        return "fixed"
    return "prop"


def near_ground(mesh, low, high, reach=None):
    """The ground's faces with a corner within `reach` (GROUND_REACH) of the laid objects' box (`low`, `high`) on the
    plan: a terrain reaching to the horizon (a HiRISE relief, 800 000 faces, 2.8 km across) held whole ran the check
    out of 8 GB, though nothing judged lies past its few metres round the place."""
    reach = GROUND_REACH if reach is None else reach
    plan = mesh.vertices[:, [0, 2]]
    near = ((plan >= low[[0, 2]] - reach) & (plan <= high[[0, 2]] + reach)).all(axis=1)
    kept = near[mesh.faces].any(axis=1)
    if kept.all():
        return mesh
    return trimesh.Trimesh(mesh.vertices, mesh.faces[kept], process=False)


def ray_box(origins, directions, length=np.inf):
    """The box every point of the rays lies in: their origins to `length` along them, open to infinity on an axis a
    ray of unbounded length runs along."""
    origins, directions = np.asarray(origins, float), np.asarray(directions, float)
    if np.isfinite(length):
        ends = origins + directions * length
        return np.minimum(origins, ends).min(axis=0), np.maximum(origins, ends).max(axis=0)
    low, high = origins.min(axis=0), origins.max(axis=0)
    low = np.where((directions < 0).any(axis=0), -np.inf, low)
    high = np.where((directions > 0).any(axis=0), np.inf, high)
    return low, high


class Place:
    """A place's objects as solids for rays: each one's role and mesh, and the faces a query reaches, gathered per
    query from the objects whose box meets it (never every face of the scene in one ray structure: 660 rocks on a
    terrain are 7 million faces, which ran the check out of 14 GB)."""

    def __init__(self, stage, place):
        self.prims = {prim.GetName(): prim for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren()}
        self.roles = {name: role_of(prim) for name, prim in self.prims.items()}
        self.meshes = {name: solid_of(prim) for name, prim in self.prims.items() if self.roles[name] not in UNSOLID}
        laid = [mesh.bounds for name, mesh in self.meshes.items() if mesh is not None and len(mesh.faces)
                and self.roles[name] != "ground"]
        if laid:
            low, high = np.min([bounds[0] for bounds in laid], axis=0), np.max([bounds[1] for bounds in laid], axis=0)
            self.meshes.update({name: near_ground(mesh, low, high) for name, mesh in self.meshes.items()
                                if mesh is not None and self.roles[name] == "ground"})
        self.people = {name: people.posed_body(prim) for name, prim in self.prims.items()
                       if self.roles[name] == "character"}
        self.names = sorted(name for name, mesh in self.meshes.items() if mesh is not None and len(mesh.faces))
        if not self.names:
            raise place_build.Refused("the scene holds no object with triangles to check")
        self.number = {name: index for index, name in enumerate(self.names)}
        self.boxes = np.array([self.meshes[name].bounds for name in self.names])
        self.face_boxes = {}

    def faces_meeting(self, number, low, high):
        """The faces of one object whose box meets [low, high] (each object's face boxes worked out once)."""
        if number not in self.face_boxes:
            triangles = self.meshes[self.names[number]].triangles
            self.face_boxes[number] = (triangles.min(axis=1), triangles.max(axis=1))
        face_low, face_high = self.face_boxes[number]
        return np.flatnonzero(np.all(face_high >= low, axis=1) & np.all(face_low <= high, axis=1))

    def triangles_in(self, low, high, among=None, without=()):
        """The triangles (n, 3, 3) of the objects `among` (their numbers; every object when None), `without` those,
        whose box meets [low, high], and each one's owner's number."""
        numbers = range(len(self.names)) if among is None else among
        triangles, owners = [], []
        for number in numbers:
            box = self.boxes[number]
            if number in without or np.any(box[0] > high) or np.any(box[1] < low):
                continue
            faces = self.faces_meeting(number, low, high)
            if len(faces):
                triangles.append(self.meshes[self.names[number]].triangles[faces])
                owners.append(np.full(len(faces), number))
        if not triangles:
            return np.zeros((0, 3, 3)), np.zeros(0, int)
        return np.concatenate(triangles), np.concatenate(owners)

    def hits(self, origins, directions, among=None, length=np.inf):
        """Every surface the rays meet (of the objects `among`, their names; every object when None), no further than
        `length` along them: (where, which ray, whose face, how far along). Only the faces in the rays' box are cast
        against, so a query costs what lies near it, not the scene."""
        empty = np.zeros((0, 3)), np.zeros(0, int), np.zeros(0, int), np.zeros(0)
        if not len(origins):
            return empty
        numbers = None if among is None else [self.number[name] for name in among]
        triangles, owners = self.triangles_in(*ray_box(origins, directions, length), among=numbers)
        if not len(triangles):
            return empty
        local = trimesh.Trimesh(triangles.reshape(-1, 3), np.arange(3 * len(triangles)).reshape(-1, 3), process=False)
        where, rays, faces = local.ray.intersects_location(origins, directions, multiple_hits=True)
        along = np.linalg.norm(where - origins[rays], axis=1)
        kept = along <= length
        return where[kept], rays[kept], owners[faces[kept]], along[kept]

    def with_role(self, *roles):
        return [name for name in self.names if self.roles[name] in roles]

    def overlapping(self, name, margin=0.0):
        """The other objects whose box meets this one's, grown by `margin`."""
        low, high = self.meshes[name].bounds
        return [other for other in self.names if other != name
                and np.all(self.meshes[other].bounds[0] <= high + margin)
                and np.all(self.meshes[other].bounds[1] >= low - margin)]


# --- resting on a support -----------------------------------------------------------------------------------------

def lowest_points(mesh, count=FOOT):
    """The object's lowest points: of its corners and a seeded sample of its surface, the `count` lowest, or, when
    more than `count` lie within TOLERANCE of the lowest (a flat foot: a mat, a crate's base), `count` of those drawn
    evenly, so the foot is read across its whole area and not where it dips a millimetre."""
    points = np.vstack([np.asarray(mesh.vertices), mesh.sample(count * 4, seed=0)])
    foot = points[points[:, 1] <= points[:, 1].min() + TOLERANCE]
    if len(foot) > count:
        return foot[np.random.default_rng(0).choice(len(foot), count, replace=False)]
    return points[np.argsort(points[:, 1])[:count]]


def gaps_down(laid, name, points, only=None, start=RAY_START):
    """How far each point stands over the surface straight under it, not its own (inf where none is), and whose
    surface that is (-1 where none); `only`, a list of objects, limits what counts; the rays start `start` over the
    points."""
    origins = points + [0.0, start, 0.0]
    _, rays, owners, along = laid.hits(origins, np.tile([0.0, -1.0, 0.0], (len(origins), 1)), among=only)
    allowed = owners != laid.number[name] if only is None else np.isin(owners, [laid.number[other] for other in only])
    gaps, under = np.full(len(points), np.inf), np.full(len(points), -1)
    order = np.argsort(along[allowed])[::-1]  # the nearest last, so it is the one kept
    picked_rays = rays[allowed][order]
    gaps[picked_rays] = along[allowed][order] - start
    under[picked_rays] = owners[allowed][order]
    return gaps, under


def support_faults(laid, name):
    """A standing object's floating, missing support and tipping, each with its measure."""
    mesh = laid.meshes[name]
    lowest = lowest_points(mesh)
    bedded = laid.roles[name] == "fixed"  # a rock may lie sunk to any depth: its rays start at its own top
    gaps, under = gaps_down(laid, name, lowest, start=float(np.ptp(mesh.bounds[:, 1])) if bedded else RAY_START)
    if not np.isfinite(gaps).any():
        return [{"fault": "no support", "why": "nothing lies under it to stand on"}]
    nearest = int(np.argmin(gaps))
    support = laid.names[under[nearest]]
    if gaps[nearest] > TOLERANCE:
        return [{"fault": "floating", "gap": round(float(gaps[nearest]), 3), "support": support,
                 "why": f"floats {gaps[nearest] * 100:.1f} cm over {support}"}]
    resting_on = lowest[gaps <= TOLERANCE][:, [0, 2]]
    outside = resting.outside_by(resting.weight_at(mesh), resting_on)
    if outside > BALANCE and laid.roles[name] == "prop":
        return [{"fault": "tips", "outside": round(float(outside), 3), "support": support,
                 "why": f"its weight falls {outside * 100:.0f} cm outside what it stands on ({support})"}]
    return []


# --- one solid inside another -------------------------------------------------------------------------------------

def surface_samples(mesh, count=SAMPLES):
    corners = np.asarray(mesh.vertices)
    corners = corners[np.random.default_rng(0).permutation(len(corners))[:count]]
    return np.vstack([corners, mesh.sample(count, seed=0)])


def judged_others(laid, name):
    """The objects whose surface this one may not cross: every other whose box meets its own, but structure joined to
    structure, and the ground under a bedded rock or a wall."""
    role = laid.roles[name]
    others = laid.overlapping(name)
    if role in ("fixed", "structure"):
        others = [other for other in others if laid.roles[other] != "ground"]
    if role == "structure":
        others = [other for other in others if laid.roles[other] not in ("structure", "shell", "connector")]
    return others


def bodies(mesh):
    """An object's pieces (its connected parts holding at least PIECE of its surface; the whole when none does), so a
    wall with a doorway is three blocks, each with a middle inside itself, never one middle in its doorway."""
    pieces = mesh.split(only_watertight=False) if len(mesh.faces) <= MAX_SPLIT else [mesh]
    kept = [piece for piece in pieces if piece.area >= PIECE * mesh.area]
    return kept or [mesh]


def body_samples(mesh):
    """Points of an object's surface and, for each, the middle of the piece it lies on: (points, middles)."""
    points, middles = [], []
    pieces = bodies(mesh)
    total = sum(piece.area for piece in pieces)
    for piece in pieces:
        found = surface_samples(piece, max(20, int(SAMPLES * piece.area / total)))
        points.append(found)
        middles.append(np.tile(piece.bounds.mean(axis=0), (len(found), 1)))
    return np.vstack(points), np.vstack(middles)


def crossing_depths(laid, name, others, mesh=None):
    """How deep this object's surface (or `mesh`, a person's skin) lies inside each other object: {other: the furthest
    such point's distance to the other's surface}, a point counted inside where a ray from the middle of its piece to
    it crosses the other an odd number of times."""
    points, middles = body_samples(laid.meshes[name] if mesh is None else mesh)
    lengths = np.linalg.norm(points - middles, axis=1)
    keep = lengths > 1e-6
    points, middles, lengths = points[keep], middles[keep], lengths[keep]
    _, rays, owners, along = laid.hits(middles, (points - middles) / lengths[:, None], among=others,
                                       length=float(lengths.max(initial=0.0)))
    numbers = np.array([laid.number[other] for other in others])
    before = np.isin(owners, numbers) & (along < lengths[rays] - 1e-6)
    rays, owners = rays[before], owners[before]
    keys = rays * len(laid.names) + owners
    unique, counts = np.unique(keys, return_counts=True)
    inside = {}
    for key, count in zip(unique, counts):
        if count % 2:
            inside.setdefault(laid.names[key % len(laid.names)], []).append(key // len(laid.names))
    return {other: float(trimesh.proximity.closest_point(laid.meshes[other], points[found])[1].max())
            for other, found in inside.items()}


def middle_inside(laid, name, others):
    """The closed objects (props, fixed pieces, doors, structure) the middle of one of this object's pieces lies
    inside: rays from it each way of INSIDE_WAYS all cross them an odd number of times (one ray along an edge counts
    a face twice or not at all)."""
    middles = np.array([piece.bounds.mean(axis=0) for piece in bodies(laid.meshes[name])])
    ways = np.asarray(INSIDE_WAYS) / np.linalg.norm(INSIDE_WAYS, axis=1)[:, None]
    closed_names = [other for other in others if laid.roles[other] in JUDGED_INSIDE]
    _, rays, owners, _ = laid.hits(np.repeat(middles, len(ways), axis=0), np.tile(ways, (len(middles), 1)),
                                   among=closed_names)
    closed = [laid.number[other] for other in closed_names]
    inside = set()
    for number in closed:
        odd = np.array([np.count_nonzero((owners == number) & (rays == ray)) % 2
                        for ray in range(len(middles) * len(ways))]).reshape(len(middles), len(ways))
        if odd.all(axis=1).any():
            inside.add(laid.names[number])
    return sorted(inside)


def penetration_faults(laid, name):
    others = judged_others(laid, name)
    if not others:
        return []
    faults = [{"fault": "penetration", "other": other, "depth": round(depth, 3),
               "why": f"lies {depth * 100:.1f} cm inside {other}"}
              for other, depth in sorted(crossing_depths(laid, name, others).items()) if depth > TOLERANCE]
    named = {fault["other"] for fault in faults}
    faults += [{"fault": "penetration", "other": other, "depth": None, "why": f"its middle lies inside {other}"}
               for other in middle_inside(laid, name, others) if other not in named]
    return faults


# --- doors --------------------------------------------------------------------------------------------------------

def frame_of(laid, name):
    """A door's middle, its axes in the scene (across, up, through: through is the thinner of its own x and z) and its
    half sizes along them."""
    matrix = np.asarray(UsdGeom.Xformable(laid.prims[name]).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    axes = matrix[:3, :3] / np.linalg.norm(matrix[:3, :3], axis=1)[:, None]
    points = np.asarray(laid.meshes[name].vertices)
    own = points @ axes.T
    low, high = own.min(axis=0), own.max(axis=0)
    middle = ((low + high) / 2) @ axes
    half = (high - low) / 2
    across, through = (0, 2) if half[0] >= half[2] else (2, 0)
    return middle, axes[[across, 1, through]], half[[across, 1, through]]


def door_faults(laid, name):
    """A door set in no opening: no wall or shell round its sides and top, or one straight behind it."""
    wall_names = laid.with_role("structure", "shell", "connector")
    walls = [laid.number[other] for other in wall_names]
    middle, axes, half = frame_of(laid, name)
    ways = {"left": -axes[0], "right": axes[0], "top": axes[1], "front": axes[2], "back": -axes[2]}
    reach_of = {"left": half[0], "right": half[0], "top": half[1], "front": half[2], "back": half[2]}
    _, rays, owners, along = laid.hits(np.tile(middle, (len(ways), 1)), np.array(list(ways.values())),
                                       among=wall_names)
    nearest = {}
    for ray, owner, distance in zip(rays, owners, along):
        if owner in walls:
            way = list(ways)[ray]
            nearest[way] = min(nearest.get(way, np.inf), distance)
    open_sides = [way for way in ("left", "right", "top") if nearest.get(way, np.inf) > reach_of[way] + FRAME]
    behind = [way for way in ("front", "back") if nearest.get(way, np.inf) <= reach_of[way] + FRAME]
    faults = []
    if open_sides:
        faults.append({"fault": "door not in an opening", "open": open_sides,
                       "why": f"no wall or shell round its {', '.join(open_sides)} within {FRAME} m: it stands free "
                              "of any wall"})
    if behind:
        faults.append({"fault": "door not in an opening", "blocked": behind,
                       "why": f"a wall lies straight {' and '.join(behind)} of it: no opening is cut where it stands"})
    return faults


def door_outline(laid, name):
    """What the door's plane shows, seen straight through it on a FIT_CELL grid from its threshold to FRAME over its
    top and FRAME past each side: (the door's cells, the cells a wall closes within FIT_DEPTH of it). Only the
    triangles of the door and its walls within that slab are cast against, so a big terrain or shell costs nothing."""
    walls = [laid.number[other] for other in laid.with_role("structure", "shell", "connector")]
    middle, axes, half = frame_of(laid, name)
    across = np.arange(-half[0] - FRAME, half[0] + FRAME + 1e-9, FIT_CELL)
    up = np.arange(-half[1] + FIT_CELL / 2, half[1] + FRAME + 1e-9, FIT_CELL)
    grid_u, grid_v = np.meshgrid(across, up, indexing="ij")
    depth = half[2] + FIT_DEPTH
    origins = middle + grid_u.reshape(-1, 1) * axes[0] + grid_v.reshape(-1, 1) * axes[1] + depth * axes[2]
    ends = np.vstack([origins, origins - 2 * depth * axes[2]])
    triangles, close_owners = laid.triangles_in(ends.min(axis=0), ends.max(axis=0), among=walls + [laid.number[name]])
    if not len(triangles):
        shape = grid_u.shape
        return np.zeros(shape, dtype=bool), np.zeros(shape, dtype=bool)
    local = trimesh.Trimesh(triangles.reshape(-1, 3), np.arange(3 * len(triangles)).reshape(-1, 3), process=False)
    where, rays, faces = local.ray.intersects_location(origins, np.tile(-axes[2], (len(origins), 1)),
                                                       multiple_hits=True)
    owners, along = close_owners[faces], np.linalg.norm(where - origins[rays], axis=1)
    near = along <= 2 * depth
    door = np.zeros(len(origins), dtype=bool)
    door[rays[near & (owners == laid.number[name])]] = True
    wall = np.zeros(len(origins), dtype=bool)
    wall[rays[near & np.isin(owners, walls)]] = True
    return door.reshape(grid_u.shape), wall.reshape(grid_u.shape)


def fit_faults(laid, name):
    """A door that does not fill its opening: the widest gap between its outline and the wall round it (the free
    cells joined to the door's own), and how far it lies over the wall past the opening's edge."""
    door, wall = door_outline(laid, name)
    if not door.any():
        return []
    labels, _ = ndimage.label(door | ~wall)
    opening = np.isin(labels, np.unique(labels[door])) & ~door
    gap = float(ndimage.distance_transform_edt(~door)[opening].max()) * FIT_CELL if opening.any() else 0.0
    leaf = ndimage.binary_opening(door, structure=np.ones((1, int(round(HINGE / FIT_CELL)) + 1), dtype=bool))
    over = leaf & wall
    past = float(ndimage.distance_transform_edt(wall)[over].max()) * FIT_CELL if over.any() else 0.0
    faults = []
    if gap > FIT:
        leaks = opening[0].any() or opening[-1].any() or opening[:, -1].any()
        faults.append({"fault": "door does not fit", "gap": round(gap, 3),
                       "why": f"its opening stands {'over ' if leaks else ''}{gap * 100:.0f} cm clear of its outline "
                              f"(at most {FIT * 100:.0f}): the door is not the opening's shape and size"})
    if past > FIT:
        faults.append({"fault": "door does not fit", "over": round(past, 3),
                       "why": f"it lies over the wall {past * 100:.0f} cm past its opening's edge (at most "
                              f"{FIT * 100:.0f})"})
    return faults


# --- people -------------------------------------------------------------------------------------------------------

def under_gap(laid, points):
    """How far the lowest of `points` stands over the nearest surface straight under them (negative: sunk into it),
    and whose surface that is; (inf, None) when nothing lies under them."""
    origins = points + [0.0, RAY_START, 0.0]
    _, rays, owners, along = laid.hits(origins, np.tile([0.0, -1.0, 0.0], (len(origins), 1)))
    if not len(rays):
        return np.inf, None
    gaps = np.full(len(points), np.inf)
    whose = np.full(len(points), -1)
    order = np.argsort(along)[::-1]
    gaps[rays[order]] = along[order] - RAY_START
    whose[rays[order]] = owners[order]
    lowest = int(np.argmin(gaps))
    return float(gaps[lowest]), (laid.names[whose[lowest]] if np.isfinite(gaps[lowest]) else None)


def contact_of(laid, points):
    """A part's contact: its lowest skin's gap to what is under it, and that support."""
    if not len(points):
        return np.inf, None
    return under_gap(laid, points[np.argsort(points[:, 1])[:FOOT // 10]])


def walks(prim):
    """Whether a person moves through the stage's time (a walker laid with its route as time samples), not held still."""
    return any(op.GetAttr().GetNumTimeSamples() > 1 for op in UsdGeom.Xformable(prim).GetOrderedXformOps())


def person_faults(laid, name):
    """A person not standing on both feet (or sitting on its seat) within CONTACT of a support, or inside another
    object, or with a broken body."""
    body = laid.people[name]
    if body is None:
        return [{"fault": "no collision geometry", "why": "it has no skinned mesh to collide by"}]
    feet = {side[0]: contact_of(laid, body.points_of(*people.PARTS["feet"], side=side))
            for side in (people.LEFT, people.RIGHT)}
    if walks(laid.prims[name]):  # a walker always has a foot in the air: its planted (lower) foot is held to CONTACT
        planted = min(feet, key=lambda side: abs(feet[side][0]) if np.isfinite(feet[side][0]) else np.inf)
        feet = {planted: feet[planted]}
    seat_joints = body.seat_joints()
    seat = contact_of(laid, np.asarray(body.mesh.vertices)[[path in seat_joints for path in body.joint_of]])
    standing = all(abs(gap) <= CONTACT for gap, _ in feet.values())
    faults = []
    if not standing and not abs(seat[0]) <= CONTACT:
        for side, (gap, support) in feet.items():
            if not np.isfinite(gap):
                faults.append({"fault": "person floating", "foot": side, "gap": None,
                               "why": f"nothing lies under its {side} foot"})
            elif abs(gap) > CONTACT:
                kind = "person floating" if gap > 0 else "person sinks"
                faults.append({"fault": kind, "foot": side, "gap": round(gap, 3), "support": support,
                               "why": f"its {side} foot stands {abs(gap) * 100:.1f} cm "
                                      f"{'over' if gap > 0 else 'into'} {support} (at most {CONTACT * 100:.0f})"})
    others = [other for other in laid.names if laid.roles[other] != "ground"
              and np.all(laid.meshes[other].bounds[0] <= body.mesh.bounds[1])
              and np.all(laid.meshes[other].bounds[1] >= body.mesh.bounds[0])]
    if others:
        faults += [{"fault": "penetration", "other": other, "depth": round(depth, 3),
                    "why": f"its skin lies {depth * 100:.1f} cm inside {other}"}
                   for other, depth in sorted(crossing_depths(laid, name, others, body.mesh).items())
                   if depth > TOLERANCE]
    return faults + people.shape_faults(body)


# --- walkways -----------------------------------------------------------------------------------------------------

def grid_rectangle(laid):
    """The walkers' grid: every shell, connector, door, structure and prop with a metre round it (x, z low, high)."""
    boxes = np.array([laid.meshes[name].bounds for name in
                      laid.with_role("shell", "connector", "door", "structure", "prop", "mount")])
    if not len(boxes):
        boxes = np.array([laid.meshes[name].bounds for name in laid.names])
    low, high = boxes[:, 0].min(axis=0) - 1.0, boxes[:, 1].max(axis=0) + 1.0
    return low[0], low[2], high[0], high[2]


def room_for_walkway(span_count, steps, clear):
    """reach.room_for_body for a way WALKWAY wide: the clear spans left once ERODED cells are taken off every border
    (a span missing a climbable step to a clear span on one of its four sides is a border), so a way of
    2 * ERODED + 1 cells is the narrowest kept: 7 cells of reach.CELL, 0.875 m, the nearest under WALKWAY."""
    starts, ends, axes = steps
    joined = clear[starts] & clear[ends]
    starts, ends, axes = starts[joined], ends[joined], axes[joined]
    ways = np.zeros((span_count, 4), dtype=bool)
    ways[starts, axes] = True
    ways[ends, axes + 2] = True
    near = clear & ~ways.all(axis=1)
    for _ in range(ERODED - 1):
        grown = near.copy()
        grown[ends[near[starts]]] = True
        grown[starts[near[ends]]] = True
        near = grown
    return clear & ~near


def walkers_floor(laid):
    """Where a walker WALKWAY wide stands, every door open: the grid, each span's cell and height, which spans it
    stands on, and each span's piece (spans joined by steps no higher than a knee)."""
    bounds = grid_rectangle(laid)
    grid = reach.Grid(bounds)
    solid = [laid.meshes[name] for name in laid.names if laid.roles[name] != "door"]
    meshes = [mesh for mesh in (reach.over_grid(mesh, bounds) for mesh in solid) if mesh is not None]
    no_ground = lambda middles: np.full(len(middles), np.nan)  # noqa: E731 (every floor is a laid surface)
    span_cells, span_heights = reach.spans(*reach.floor_points(grid, meshes, no_ground))
    clear = reach.clear_overhead(grid, meshes, span_cells, span_heights)
    steps = reach.steps_between(grid, span_cells, span_heights)
    standing = room_for_walkway(len(span_cells), steps, clear)
    return grid, span_cells, span_heights, standing, reach.components(len(span_cells), steps, standing)


def spans_near(grid, span_cells, span_heights, standing, spot, across=0.4):
    """The standing spans within `across` metres of a spot (x, z) and a knee of its height."""
    middles = grid.middles()[span_cells]
    near = np.hypot(middles[:, 0] - spot[0], middles[:, 1] - spot[2]) <= across
    return np.flatnonzero(standing & near & (np.abs(span_heights - spot[1]) <= reach.KNEE))


def walkway_targets(laid):
    """Where the walkers must get to: each door's two sides (a body's depth out, at its foot) and the floor of each
    shell and connector (its box): {target name: spot (x, y, z)} and {target name: (low, high)}."""
    spots, zones = {}, {}
    for name in laid.with_role("door"):
        middle, axes, half = frame_of(laid, name)
        foot = laid.meshes[name].bounds[0][1]
        for side, sign in (("front", 1), ("back", -1)):
            spot = middle + axes[2] * sign * (half[2] + WALKWAY / 2 + 0.2)
            spots[f"{name} ({side})"] = np.array([spot[0], foot, spot[2]])
    for name in laid.with_role("shell", "connector"):
        zones[name] = laid.meshes[name].bounds
    return spots, zones


def walkway_faults(laid):
    """Door sides and zones the walkers cannot reach from the rest on a way WALKWAY wide: [{target, why}]."""
    grid, span_cells, span_heights, standing, pieces = walkers_floor(laid)
    spots, zones = walkway_targets(laid)
    reached = {name: set(pieces[spans_near(grid, span_cells, span_heights, standing, spot)])
               for name, spot in spots.items()}
    middles = grid.middles()[span_cells]
    for name, (low, high) in zones.items():
        inside = standing & (middles[:, 0] >= low[0]) & (middles[:, 0] <= high[0]) & (middles[:, 1] >= low[2]) \
            & (middles[:, 1] <= high[2]) & (span_heights >= low[1] - reach.KNEE) & (span_heights <= high[1])
        reached[name] = set(pieces[inside])
    counted = np.bincount([piece for found in reached.values() for piece in found], minlength=1)
    main = int(np.argmax(counted)) if counted.any() else None
    return [{"fault": "walkway", "target": name,
             "why": (f"no floor {WALKWAY} m wide to stand on there" if not found else
                     f"no way {WALKWAY} m wide joins it to the rest")}
            for name, found in sorted(reached.items()) if main not in found], (grid, span_cells, span_heights, standing)


# --- the walkers' ground and routes (sim body, scene clips) -------------------------------------------------------

def solids(folder):
    """{object: its triangles in the scene's frame (n x 3 x 3)} of every object a walker may stand on or run into:
    each one the check reads, doors left out as the walkers' floor leaves them (open), characters never."""
    stage, place = place_build.opened(folder)
    laid = Place(stage, place)
    return {name: np.asarray(laid.meshes[name].triangles) for name in laid.names if laid.roles[name] != "door"}


def span_at(grid, span_cells, span_heights, standing, spot):
    """The standing span nearest a spot (x, y, z) within a knee of its height; Refused when none is."""
    middles = grid.middles()[span_cells]
    near = standing & (np.abs(span_heights - spot[1]) <= reach.KNEE)
    if not near.any():
        raise place_build.Refused(f"no floor a walker stands on within a knee of {np.round(spot, 2).tolist()}")
    candidates = np.flatnonzero(near)
    return int(candidates[np.argmin(np.hypot(middles[candidates, 0] - spot[0], middles[candidates, 1] - spot[2]))])


def in_sight(points, standing_at):
    """Whether a straight line between two route points keeps to the walkers' floor: every sample along it, a fifth of
    a cell apart, over a standing span within half a knee of the line's height there."""
    start, end = points
    count = max(2, int(np.linalg.norm(end[[0, 2]] - start[[0, 2]]) / (reach.CELL / 5)) + 1)
    return all(standing_at(start + (end - start) * share) for share in np.linspace(0.0, 1.0, count))


def straightened(path, standing_at):
    """The grid path's corners alone: from each kept point, the farthest later point in sight of it."""
    kept, at = [path[0]], 0
    while at < len(path) - 1:
        reach_to = at + 1
        for later in range(len(path) - 1, at + 1, -1):
            if in_sight((path[at], path[later]), standing_at):
                reach_to = later
                break
        kept.append(path[reach_to])
        at = reach_to
    return np.array(kept)


def rounded(corners, radius=ROUND):
    """The corners' route with each inner corner turned through a quadratic curve from `radius` before it to `radius`
    after it (at most a third of either leg), so a walker's heading turns over a few steps, not in one frame."""
    if len(corners) < 3:
        return corners
    points = [corners[0]]
    for before, corner, after in zip(corners[:-2], corners[1:-1], corners[2:]):
        into = min(radius, np.linalg.norm((corner - before)[[0, 2]]) / 3)
        out = min(radius, np.linalg.norm((after - corner)[[0, 2]]) / 3)
        first = corner + (before - corner) / np.linalg.norm((before - corner)[[0, 2]]) * into
        last = corner + (after - corner) / np.linalg.norm((after - corner)[[0, 2]]) * out
        for share in np.linspace(0.0, 1.0, TURN_POINTS):
            points.append((1 - share) ** 2 * first + 2 * (1 - share) * share * corner + share ** 2 * last)
    points.append(corners[-1])
    return np.array(points)


def route(folder, through):
    """A walker's route through the given spots (x, y, z) on the walkers' floor WALKWAY wide (the check's own, doors
    open): the shortest way over standing spans between each spot and the next, its corners kept and rounded.
    [[x, y, z], ...] and its length along the ground; Refused when a spot has no floor or no way joins two."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    stage, place = place_build.opened(folder)
    laid = Place(stage, place)
    grid, span_cells, span_heights, standing, pieces = walkers_floor(laid)
    starts, ends, _ = reach.steps_between(grid, span_cells, span_heights)
    both = standing[starts] & standing[ends]
    graph = coo_matrix((np.full(both.sum(), reach.CELL), (starts[both], ends[both])), shape=(len(span_cells),) * 2)
    graph = graph.tocsr()
    middles = grid.middles()[span_cells]
    spans = [span_at(grid, span_cells, span_heights, standing, np.asarray(spot, float)) for spot in through]
    legs = [] if len(spans) > 1 else [[spans[0]]]
    for start, end in zip(spans[:-1], spans[1:]):
        distances, before = dijkstra(graph, directed=False, indices=start, return_predecessors=True)
        if not np.isfinite(distances[end]):
            raise place_build.Refused(f"no way {WALKWAY} m wide joins {np.round(middles[start], 2).tolist()} to "
                             f"{np.round(middles[end], 2).tolist()}")
        leg, at = [], end
        while at != start:
            leg.append(at)
            at = before[at]
        legs.append([start, *leg[::-1]])
    cell_of = {}
    for span in np.flatnonzero(standing):
        cell_of.setdefault(int(span_cells[span]), []).append(float(span_heights[span]))

    def standing_at(point):
        column = int(np.floor((point[0] - (grid.xs[0] - reach.CELL / 2)) / reach.CELL))
        row = int(np.floor((point[2] - (grid.zs[0] - reach.CELL / 2)) / reach.CELL))
        if not (0 <= column < grid.shape[0] and 0 <= row < grid.shape[1]):
            return False
        heights = cell_of.get(int(np.ravel_multi_index((column, row), grid.shape)), [])
        return any(abs(height - point[1]) <= reach.KNEE / 2 for height in heights)

    corners = [straightened(np.column_stack([middles[leg, 0], span_heights[leg], middles[leg, 1]]), standing_at)
               for leg in legs]  # each leg on its own, so every given spot stays a corner of the route
    walked = rounded(np.concatenate([corners[0], *[leg[1:] for leg in corners[1:]]]))
    length = float(np.linalg.norm(np.diff(walked[:, [0, 2]], axis=0), axis=1).sum())
    return np.round(walked, 4).tolist(), round(length, 3)


# --- connectors ---------------------------------------------------------------------------------------------------

def connector_axis(mesh):
    """A tube's two ends (its axis' ends, at its middle height) and its half width. The axis is the level way its
    skin's faces turn least towards (a tube's skin faces out across its axis, weighed by area), so neither a tube as
    wide as it is long nor a finely cut end wall turns it across the tube."""
    normals = np.asarray(mesh.face_normals)[:, [0, 2]] * np.sqrt(np.asarray(mesh.area_faces))[:, None]
    _, vectors = np.linalg.eigh(normals.T @ normals)
    axis = vectors[:, 0]
    points = np.asarray(mesh.vertices)
    flat = points[:, [0, 2]] - points[:, [0, 2]].mean(axis=0)
    along = flat @ axis
    middle = points.mean(axis=0)
    direction = np.array([axis[0], 0.0, axis[1]])
    ends = [middle + direction * along.min(), middle + direction * along.max()]
    return ends, direction, float(np.abs(flat @ np.array([-axis[1], axis[0]])).max())


def ring_distance(mesh, ring):
    """How far an end ring comes to a mesh: its nearest point's distance, or, when the mesh's box lies further than
    JOIN from the ring's, that box gap (a lower bound, so a far shell is never searched point by point)."""
    low, high = mesh.bounds
    box_gap = float(np.linalg.norm(np.maximum(0.0, np.maximum(low - ring.max(axis=0), ring.min(axis=0) - high))))
    if box_gap > JOIN:
        return box_gap
    return nearest_to_surface(mesh, ring)


def nearest_to_surface(mesh, points, chunk=64):
    """The least distance from any of `points` to the mesh's surface, exact: only the points whose nearest vertex lies
    within the mesh's longest edge of the least such vertex distance can be nearest (any point of a face lies within
    its longest edge of one of its corners), searched a chunk at a time, so a dense made model (half a million faces,
    TRELLIS.2's) and a ring standing a hand off it cost no more memory than a small one (they took 8 GB at once)."""
    from scipy.spatial import cKDTree
    vertex_gaps = cKDTree(np.asarray(mesh.vertices)).query(points)[0]
    longest = float(mesh.edges_unique_length.max()) if len(mesh.edges_unique) else 0.0
    near = np.asarray(points)[vertex_gaps <= vertex_gaps.min() + longest]
    return min(float(trimesh.proximity.closest_point(mesh, near[start:start + chunk])[1].min())
               for start in range(0, len(near), chunk))


def connector_faults(laid, name, floor):
    """A connector with an end joined to nothing (a shell, wall, another connector, or a door closing it: an
    airlock's outer end), or no walkable floor along it."""
    mesh = laid.meshes[name]
    ends, direction, _ = connector_axis(mesh)
    points = np.asarray(mesh.vertices)
    structure = [other for other in laid.with_role("shell", "structure", "connector", "door") if other != name]
    faults = []
    for label, end in zip(("start", "end"), ends):
        ring = points[np.abs((points - end) @ direction) <= 0.15]
        nearest = min((ring_distance(laid.meshes[other], ring) for other in structure), default=np.inf)
        if nearest > JOIN:
            faults.append({"fault": "connector", "end": label, "gap": round(nearest, 3) if np.isfinite(nearest) else None,
                           "why": f"its {label} joins nothing: the nearest shell or wall is "
                                  f"{nearest:.2f} m from its end ring"})
    grid, span_cells, span_heights, standing = floor
    floor_y = mesh.bounds[0][1]
    length = float(np.linalg.norm(ends[1] - ends[0]))
    stations = [ends[0] + direction * along for along in np.arange(CONNECTOR_STEP, length - CONNECTOR_STEP / 2,
                                                                       CONNECTOR_STEP)]
    missing = [station for station in stations
               if not len(spans_near(grid, span_cells, span_heights, standing,
                                     np.array([station[0], floor_y, station[2]]), across=0.3))
               and not len(spans_near(grid, span_cells, span_heights, standing,
                                      np.array([station[0], floor_y + 0.3, station[2]]), across=0.3))]
    if missing:
        faults.append({"fault": "connector", "unwalkable": round(len(missing) * CONNECTOR_STEP, 2),
                       "why": f"no walkable floor {WALKWAY} m wide over {len(missing) * CONNECTOR_STEP:.2f} m of its "
                              f"{length:.2f} m"})
    return faults


# --- settle in MuJoCo ---------------------------------------------------------------------------------------------

def held_by(laid, name):
    """The objects this one holds (their box middle inside its box): left out of its statics, since its one convex
    hull would close over what a cabinet stores. What holds it stays in: a laptop on a desk with a raised back lies
    inside the desk's box and rests on its top's triangles."""
    low, high = laid.meshes[name].bounds
    held = []
    for other in laid.overlapping(name):
        other_low, other_high = laid.meshes[other].bounds
        middle = (other_low + other_high) / 2
        if laid.roles[other] in ("prop", "mount") and np.all((middle >= low) & (middle <= high)):
            held.append(other)
    return held


def statics_near(laid, name):
    """The triangles of everything near a loose object (its box grown by NEAR), what it holds aside: (count, 3, 3)."""
    low, high = laid.meshes[name].bounds
    low, high = low - NEAR, high + NEAR
    left_out = {laid.number[other] for other in [name, *held_by(laid, name)]}
    return laid.triangles_in(low, high, without=left_out)[0]


def settle_faults(laid, folder):
    """Each prop let go in MuJoCo (settle_mujoco.py in the physics trial's Python): {name: [fault]}, and how it ran."""
    loose = laid.with_role("prop")
    python = SETTLE_ENV / "bin/python"
    if not loose:
        return {}, "nothing loose"
    if not python.exists():
        return {}, f"not run: no physics trial Python at {SETTLE_ENV} (score/stages/physics/inside/newton_env.sh)"
    job, out = pathlib.Path(folder) / "ready-settle.npz", pathlib.Path(folder) / "ready-settle.json"
    arrays = {"names": np.array(loose)}
    for name in loose:
        vertices = np.asarray(laid.meshes[name].convex_hull.vertices)
        arrays[f"hull_{name}"], arrays[f"statics_{name}"] = vertices, statics_near(laid, name)
    np.savez(job, **arrays)
    done = subprocess.run([str(python), str(SETTLE_SCRIPT), str(job), str(out)], capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"the MuJoCo settle failed: {done.stderr.strip()[-600:]}")
    found = json.loads(out.read_text())
    faults = {}
    for name, measure in found["objects"].items():
        if measure["moved"] > SETTLE_MOVE or measure["turned"] > SETTLE_TURN:
            faults[name] = [{"fault": "unstable", "moved": round(measure["moved"], 3),
                             "turned": round(measure["turned"], 1),
                             "why": f"let go, it moves {measure['moved'] * 100:.0f} cm and turns "
                                    f"{measure['turned']:.0f} degrees"}]
    return faults, found["engine"]


# --- the check ----------------------------------------------------------------------------------------------------

def object_faults(laid, name):
    """One object's own faults: support, penetration, door."""
    role = laid.roles[name]
    faults = []
    if role in SUPPORTED:
        faults += support_faults(laid, name)
    if role in JUDGED_INSIDE:
        faults += penetration_faults(laid, name)
    if role == "door":
        faults += door_faults(laid, name) + fit_faults(laid, name)
    if role == "mount":
        faults += mount_faults(laid, name)
    return faults


def mount_faults(laid, name):
    """A wall-mounted object that does not touch the wall it is mounted on."""
    support = (text_of(laid.prims[name], "score:support") or "").removeprefix("wall:")
    if support not in laid.meshes or laid.meshes[support] is None:
        return [{"fault": "no support", "why": f"mounted on {support or 'no wall'}, which the scene does not hold"}]
    distance = float(trimesh.proximity.closest_point(laid.meshes[support],
                                                     surface_samples(laid.meshes[name], 200))[1].min())
    if distance > TOLERANCE:
        return [{"fault": "floating", "gap": round(distance, 3), "support": support,
                 "why": f"hangs {distance * 100:.1f} cm off {support}, the wall it is mounted on"}]
    return []


def check(folder, settle=True):
    """Every reason the place is not physics ready, per object, written to <folder>/ready.json; the counts."""
    stage, place = place_build.opened(folder)
    laid = Place(stage, place)
    found = {name: [{"fault": "no collision geometry", "why": "it has no triangles to collide by"}]
             for name in laid.prims if laid.roles[name] not in UNSOLID and name not in laid.names}
    for name in laid.names:
        faults = object_faults(laid, name)
        if faults:
            found.setdefault(name, []).extend(faults)
    for name in laid.people:
        faults = person_faults(laid, name)
        if faults:
            found.setdefault(name, []).extend(faults)
    walkways, floor = walkway_faults(laid)
    for fault in walkways:
        found.setdefault(fault["target"].split(" (")[0], []).append(fault)
    for name in laid.with_role("connector"):
        for fault in connector_faults(laid, name, floor):
            found.setdefault(name, []).append(fault)
    settled, engine = settle_faults(laid, folder) if settle else ({}, "not asked")
    for name, faults in settled.items():
        found.setdefault(name, []).extend(faults)
    counts = {}
    for faults in found.values():
        for fault in faults:
            counts[fault["fault"]] = counts.get(fault["fault"], 0) + 1
    path = pathlib.Path(folder) / "ready.json"
    path.write_text(json.dumps({"place": place, "roles": laid.roles, "objects": found, "settle": engine}, indent=1))
    return {"ready": not found, "objects": len(laid.prims), "with_faults": len(found), "counts": counts,
            "settle": engine, "file": str(path)}


# --- the `on` helper ----------------------------------------------------------------------------------------------

def levels_under(laid, support, spot):
    """The heights of the support's surfaces that look up, straight under a spot (x, z), lowest first, those within
    2 cm of each other one level."""
    origin = np.array([[spot[0], laid.meshes[support].bounds[1][1] + 1.0, spot[1]]])
    where, _, owners, _ = laid.hits(origin, np.array([[0.0, -1.0, 0.0]]), among=[support])
    heights = np.sort(where[owners == laid.number[support], 1])
    levels = []
    for height in heights:
        if not levels or height - levels[-1] > 0.02:
            levels.append(float(height))
        else:
            levels[-1] = float(height)
    return levels


def placed_on(stage, place, name, support, level=None, height=None):
    """The object moved to rest in contact on its support (see `on`); its new spot and what it rests on."""
    laid = Place(stage, place)
    if name not in laid.meshes or laid.meshes[name] is None:
        raise place_build.Refused(f"the scene holds no object {name} with a shape")
    prim = laid.prims[name]
    at, turn, scale = place_build.pose_of(prim)
    mesh = laid.meshes[name]
    if support.startswith("wall:"):
        return mounted(laid, name, support.removeprefix("wall:"), height, (at, turn, scale))
    if support == "floor":
        only = laid.with_role("ground", "shell", "connector", "structure")
    elif support in laid.meshes and laid.meshes[support] is not None:
        only = [support]
    else:
        raise place_build.Refused(f"no support {support} (floor, wall:<object> or an object of the scene)")
    shift = 0.0
    if support != "floor":
        levels = levels_under(laid, support, mesh.bounds.mean(axis=0)[[0, 2]])
        level = -1 if level is None else level
        if not -len(levels) <= level < len(levels):
            raise place_build.Refused(f"{support} has {len(levels)} levels under {name}, no level {level}")
        shift = levels[level] + 0.02 - mesh.bounds[0][1]
    gaps, _ = gaps_down(laid, name, lowest_points(mesh) + [0.0, shift, 0.0], only=only)
    if not np.isfinite(gaps).any():
        raise place_build.Refused(f"{support} lies under no part of {name}")
    spot = [at[0], at[1] + shift - float(gaps[np.isfinite(gaps)].min()), at[2]]
    place_build.posed(prim, spot, turn, scale)
    prim.CreateAttribute("score:support", Sdf.ValueTypeNames.String).Set(support)
    return {"name": name, "on": support, "at": spot}


def mounted(laid, name, wall, height, pose):
    """The object at `height` over the floor under it, moved straight to the wall's nearest face until it touches."""
    if wall not in laid.meshes or laid.meshes[wall] is None:
        raise place_build.Refused(f"no wall {wall} in the scene")
    at, turn, scale = pose
    mesh = laid.meshes[name]
    middle = mesh.bounds.mean(axis=0)
    floor_gap, _ = gaps_down(laid, name, mesh.bounds[0][None] * [0, 1, 0] + [middle[0], 0, middle[2]],
                             only=laid.with_role("ground", "shell", "connector"))
    floor_y = mesh.bounds[0][1] - float(floor_gap[0]) if np.isfinite(floor_gap[0]) else 0.0
    lift = (floor_y + float(height or 0.0)) - mesh.bounds[0][1]
    nearest, _, _ = trimesh.proximity.closest_point(laid.meshes[wall], middle[None])
    towards = nearest[0] - middle
    towards[1] = 0.0
    towards /= max(np.linalg.norm(towards), 1e-9)
    points = surface_samples(mesh, 300) + [0.0, lift, 0.0]
    _, rays, owners, along = laid.hits(points, np.tile(towards, (len(points), 1)), among=[wall])
    hit = owners == laid.number[wall]
    if not hit.any():
        raise place_build.Refused(f"{wall} lies in no straight line from {name}")
    move = float(along[hit].min())
    spot = [at[0] + towards[0] * move, at[1] + lift, at[2] + towards[2] * move]
    prim = laid.prims[name]
    place_build.posed(prim, spot, turn, scale)
    prim.CreateAttribute("score:support", Sdf.ValueTypeNames.String).Set(f"wall:{wall}")
    prim.CreateAttribute("score:role", Sdf.ValueTypeNames.String).Set("mount")
    return {"name": name, "on": f"wall:{wall}", "at": spot}


def on(folder, name, support, level=None, height=None):
    """Lay an object at rest, in contact, on a named support: `floor` (the ground, a deck or a floor under it),
    an object (its top under the object, or with `level` its n-th surface that looks up, from 0 at the bottom, -1 the
    top: a shelf level), or `wall:<object>` (mounted `height` metres over the floor, moved straight to the wall until it
    touches). Only its height (or, mounted, its height and its way to the wall) changes; the scene is saved."""
    stage, place = place_build.opened(folder)
    answer = placed_on(stage, place, name, support, level, height)
    place_build.saved(stage)
    return answer
