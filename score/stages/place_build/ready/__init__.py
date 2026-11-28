"""Physics ready: everything about a place_build scene that keeps the walkers (sim body, MuJoCo) from walking in it and
pushing its objects, told per object for the placing agent, and the `on` helper that lays an object at rest on a
named support.

    check(folder, settle=True, neighbours=None) -> {counts..., "file": <folder>/ready.json}
    on(folder, name, support, level=None, height=None)
    solids(folder) -> {object: triangles}       what a walker stands on and runs into (sim body's, scene clips' ground)
    route(folder, through) -> (points, length)  a walker's way through spots on the walkers' floor WALKWAY wide
    swing_of(laid, door) -> {hinge, degrees}    how a door marked `score:opens` swings open for the walkers
    slide_of(laid, door) -> {by}                how a door marked `score:move` slide slides open for them

Each object of /<place>/Objects has a role, from its `score:role` when it has one, else from what it is: `ground` (a
laid ground or terrain), `shell` and `connector` (the dome shell algorithm's domes and tubes), `door` (a door, hatch or
airlock), `structure` (a wall, bulkhead, frame), `fixed` (a rock bedded in the ground, or `score:fixed`), `mount` (on a
wall: `on ... wall:<object>`), `character` (a person, posed as the renderer poses it: people.py), `light` (a sky dome
laid as an object, `score:kind` light: light the renderer draws, never a solid, so left out of every measure), `prop`
(everything else: it can be pushed) or `scenery` (a ground or fixed piece lying wholly more than GROUND_REACH past every
walker's reach, the box of the people and of everything a walker meets: a far shore, the horizon's mesas; only seen, so
left out of every measure, `out_of_reach`). The faults, each with its measure:

- `no collision geometry`: an object with no triangles to collide by.
- `floating`: a prop, fixed piece, structure or door whose lowest points clear what is under them by over TOLERANCE
  (the gap and the support named); `no support`: nothing at all under it; `tips`: its weight (the middle of its
  surface) falls over BALANCE outside what it touches (resting.py's measures); `tilted`: a prop whose base (the largest
  flat face of its convex hull looking down, holding its lowest point: a crate's bottom, the face its legs' ends span)
  turns more than TILT degrees off level.
- `penetration`: a sample of an object's surface lies inside another (a ray from the object's middle to the point
  crosses the other's surface an odd number of times; the depth is how far past its last crossing), or its middle
  lies inside another closed object; joined structure and a rock bedded in the ground are not faults.
- `door not in an opening`: a door with no wall or shell round its sides and top within FRAME, or a wall straight
  behind it (no opening cut).
- `door does not fit`: seen straight through the door's plane on a FIT_CELL grid, the opening round it (what no wall,
  shell or connector closes within FIT_DEPTH of it, from its threshold up) shows a gap wider than FIT between the
  door's outline and the wall, or the door lies over the wall further than FIT past the opening's edge (a hinge or a
  latch, shorter than HINGE, lies on its jamb): a leaf that is not the opening's shape and size (a rectangular
  door in a round opening, a hatch too small for it). The outline is the door's whole shape, its holes filled: a
  lattice gate's gaps between its bars are the gate's, never the opening's.
- `person floating` / `person sinks`: a person's feet (each foot's lowest skin; a walker's planted, lower foot alone,
  `walks`), or, seated, the seat, more than
  CONTACT over or into what is under them; a person's skin inside another object is `penetration` as above. A crowd
  (a PointInstancer of laid people) is judged copy by copy, each named as the package names it (`<crowd>_<n>`).
- `broken body`: a person's skin torn by its skinning, a missing head, hand or foot, or a height or proportions no
  person has (people.shape_faults).
- `walkway`: the walkers' floor (reach.py's Recast-style spans of every surface, doors open, eroded by half of WALKWAY)
  does not join both sides of every door, and every shell and connector, in one walkable piece WALKWAY wide. A door
  marked as opening onto a seat (SEAT, place_build.door --seat: a crew capsule's hatch, climbed through into the pilot's
  seat, no corridor behind it) needs that seat within SEAT_REACH of its side nearer the seat, not floor there; its
  other side is a walkway target as any door's.
- `connector`: a tube whose end ring stays over JOIN from every other shell or structure, or that has no walkable floor
  along its length.
- `unstable`: let go in MuJoCo (settle_mujoco.py, in the physics trial's Python), it moves over SETTLE_MOVE or turns
  over SETTLE_TURN.

The check holds no more than MEMORY: before the walkers' floor and the settle it works out what they need (the walkers'
grid a cell at a time, its spans, the settle's models side by side) and, when that and what it holds already would pass
MEMORY, refuses with what needs it, never freezing the machine (the Hong Kong square, 2026-11-19: a walkers' grid
1.6 km across ran the check to 33 GB). The settle runs as many models side by side as fit.

Beside the physics, ready.json's `finishes` holds every object whose shown finish is not the library's (finished/:
no material, its model's own paint no library surface made, a look naming no library surface, one surface over a
model's painted parts); and `shapes` every made object whose shape reads wrong (shapes/: a pipe that swells along
its run, a hard thing with too few flat faces), each for a remake; and `plan` every way the place strays from its
plan (plan_fit/: a room bigger than its plan, a plan item missing, stood in for by blocks or at the wrong scale, a wall
dressing the plan names left bare; null when no plan was taken in). The place is ready only with none of them.
"""
import ast
import contextlib
import gc
import json
import os
import pathlib
import subprocess
import sys

import numpy as np
import trimesh
from scipy import ndimage
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

from score.stages import place_build

from score.stages.place_build import finished, plan_fit, shapes
from score.stages.place_build.ready import people

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "tools/usd"))
import physics as usd_physics  # noqa: E402  (tools/usd/physics.py: an adopted asset's own physics, #155)
import reach  # noqa: E402
import resting  # noqa: E402

TOLERANCE = resting.TOLERANCE  # metres off a support, or into another, that still rests
BALANCE = resting.BALANCE
RAY_START = 0.1  # rays down start this far over each point, so a point bedded a little still finds its support's top
FOOT = 300  # how many of an object's lowest points look down for its support
BASE_ANGLE = 30.0  # degrees off straight down a face of an object's hull may look and still be its base (`base_of`)
BASE_SHARE = 0.3  # of its foot's box an object's base covers at least, else it has none (a round bottom)
BASE_SLICE = 0.1  # of its height over its lowest point an object's foot reaches (`base_of`)
TILT = 2.0  # degrees a prop's base may turn off level before it stands at a wrong angle (`tilt_faults`)
SAMPLES = 500  # how many points of an object's surface are tested for lying inside another
MOUNT_SAMPLES = 1000  # points of a mount's surface whose nearest to its wall is its gap (200 read a street lantern
# touching its string, 7 mm off, as hanging 3.1 cm off it: 2099 #161)
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
OPENS = "score:opens"  # a door's mark: it swings open for the walkers; a door without it stays shut, a solid
MOVE = "score:move"  # how a door opens (place_build.MOVES): on a hinge at an edge (none given), or slid aside
SWING = 90.0  # degrees an opening door's leaf turns about its hinge
ROOM = 1.0  # metres of room round an open leaf past which more room is no better a swing
CONTACT = 0.01  # metres a person's foot or seat may stand off, or sink into, what is under it
SETTLE_MOVE = 0.05  # metres
SEES = 40.0  # metres a ray from the walkers' floor goes meeting nothing before it is taken to see the outside (at
# least; across a bigger building, its box's diagonal: `sight`)
COVER = 12.0  # metres over a floor point a roof, slab or flight must stand for the point to be inside
ROOFED = 0.05  # an inside place with less of its walkers' floor under a roof, slab or flight has none (#128,
# 2026-11-20: roofless engineroom@1 0.01; built closed: hangar 0.15, shiplock 0.17, stairwell 0.29, engineroom 0.33,
# their plazas and roof tops counted)
BUILT = ("structure", "shell", "connector")  # what an outside place's rooms are rooms of: never a model's own hollow
INSIDE_SHARE = 0.6  # a covered point whose rays meet something at least this often is inside (under an awning, less)
DOOR_REACH = 4.0  # metres round a door's leaf and its width where its swing or slide is judged (door_window)
LOOK_HEIGHTS = (0.5, 1.6)  # metres over the walkers' floor the looks start (a child's, a grown walker's eyes)
LOOK_STRIDE = 0.5  # metres between the floor points looked from
LOOK_AZIMUTHS = 16  # ways round a point
LOOK_ELEVATIONS = (0.0, 20.0, 45.0, 70.0)  # degrees up of each ring of ways
SHOWN_OPEN = 12  # at most this many of a place's open looks are listed (the rest counted)
SETTLE_TURN = 8.0  # degrees
CAST_AT_ONCE = 2 ** 15  # rays a query casts at once, each batch against the faces its own box meets (2099's square,
# 2026-11-22: its looks, cast all at once against the whole plaza's faces, held past 12 GB)
COLLECTED = 200_000  # faces of a cast past which its ray structure is collected at once (`cast`)
FACES_AT_ONCE = 2_000_000  # faces one ray structure is built over at most, a larger cast taken a part at a time
# (2099 pad, 2026-11-28: its made poles and legs, ~500k faces each, 19.8 million in all, met by one far look, built
# one structure past 20 GB)
RAYS = 32  # rays the exact intersector casts at once (each holds every face its box meets: 30 000 in the hangar)
PAST = 1e-3  # metres past a ray's last kept hit embree is asked again whether it meets anything more
NEAR = 0.15  # how far past a loose object's box its statics reach in the settle (metres)
ROLES = ("ground", "shell", "connector", "door", "structure", "fixed", "mount", "character", "light", "prop",
         "scenery")
UNSOLID = ("character", "light")  # roles that are no solid of their own (a person is posed apart: people.py)
REACHED = ("shell", "connector", "door", "structure", "mount", "prop")  # what a walker meets, besides the people
SCENERY = ("ground", "fixed")  # what never moves, so beyond every walker's reach it is only seen (far scenery)
DOOR_WORDS = ("door", "hatch", "airlock")
INWARD_LEAST = 0.5  # metres a structure's middle stands off a door's plane for the door to be set in it
LEVEL_RAYS = 5
CROUCH = "score:crouch"  # a door's mark: a hatch the walkers cross crouching (place_build.door --crouch)
CROUCH_HEAD = 1.0  # metres of room over a crouching walker's floor
CROUCH_KNEE = 0.45  # metres a crouching walker steps up over a hatch's sill
SEAT = "score:seat"  # a door's mark: the seat it opens onto, climbed into through it (place_build.door --seat)
SEAT_REACH = 0.6  # metres from a seat-entry door's seat-side spot (a body's depth through it) to its seat's surface
HATCH_REACH = 0.6  # metres either side of a hatch's plane the crouch lasts  # rays a side over an object's footprint that find the levels of the support under it
STRUCTURE_WORDS = ("wall", "bulkhead", "partition", "frame", "fence")
CONNECTOR_WORDS = ("tube", "tunnel", "corridor", "connector")
BEDDED_WORDS = ("rock", "boulder", "stone")
SUPPORTED = ("prop", "fixed", "structure", "door")
JUDGED_INSIDE = ("prop", "fixed", "structure", "door", "mount")
SETTLE_ENV = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "envs/newton_env"
SETTLE_SCRIPT = pathlib.Path(__file__).resolve().parent / "settle_mujoco.py"
MEMORY = 8 * 2 ** 30  # bytes the check may hold, the settle's models included
SPAN_BYTES = 200  # bytes the walkers' floor holds a span (or a cell of its grid): 160 measured on a flat 120 m floor
FLOOR_BYTES = 24  # bytes a floor height kept while the walkers' floor is read (sorted with what it joins)
CHUNK_BYTES = 150 * reach.CHUNK  # what one chunk of a surface's points holds while it is read
PAIRS = 2 ** 20  # point and face pairs nearest_to_surface weighs at once (about 400 MB with its arrays)
PLATE_BYTES = 16 * 1024  # bytes a static triangle's plate holds in a settle model (15 KB measured at 2,000 and 20,000)
SETTLE_POOL = 8  # settle models side by side at most


# --- the memory budget ------------------------------------------------------------------------------------------

def in_use():
    """Bytes this process holds now (its resident set)."""
    return int(pathlib.Path("/proc/self/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE")


def within_memory(needed, what):
    """Refuses (place_build.Refused) when `needed` more bytes for `what` would take the check past MEMORY."""
    held = in_use()
    if held + needed > MEMORY:
        raise place_build.Refused(f"the physics check would pass its memory budget of {MEMORY / 2 ** 30:.1f} GB: "
                                  f"{what} needs about {needed / 2 ** 30:.1f} GB more, and it holds "
                                  f"{held / 2 ** 30:.1f} GB")


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
    """Every drawn mesh and cube under an object, inside its instances too (an adopted SimReady model lays its shapes
    under an instanceable prim, #155), in the scene's frame, as one mesh; None when it has none."""
    pieces = []
    for inside in Usd.PrimRange(prim, Usd.TraverseInstanceProxies()):
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


def library_name(address):
    """A library address's own name, without its kind, its place (`<name>.<place>`) and its version: the words a
    role is read from (#154: model/pilot_console_1.airlock@1 read as a door by its place's name)."""
    entry = str(address or "").split("/", 1)[-1].split("@", 1)[0]
    return entry.split(".", 1)[0]


def role_of(prim):
    """An object's role (ROLES): its `score:role`, else read from its marks, kind, name and library address."""
    given = text_of(prim, "score:role")
    if given:
        return given
    if text_of(prim, "score:ground"):
        return "ground"
    words = f"{prim.GetName()} {library_name(text_of(prim, 'score:library'))}".lower()
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


def out_of_reach(roles, meshes, bodies):
    """The ground and fixed pieces lying wholly more than GROUND_REACH past every walker's reach on the plan (the box
    of every object a walker meets, REACHED, and of the people): far scenery (a far shore, the horizon's mesas), only
    seen, so no physics measure reads it; none when nothing is reached."""
    boxes = [mesh.bounds for name, mesh in meshes.items() if roles[name] in REACHED and mesh is not None
             and len(mesh.faces)] + [body.mesh.bounds for body in bodies.values() if body is not None]
    if not boxes:
        return []
    low = np.min([box[0] for box in boxes], axis=0)[[0, 2]] - GROUND_REACH
    high = np.max([box[1] for box in boxes], axis=0)[[0, 2]] + GROUND_REACH
    far = []
    for name, mesh in meshes.items():
        if roles[name] not in SCENERY or mesh is None or not len(mesh.faces):
            continue
        plan = mesh.bounds[:, [0, 2]]
        if np.any(plan[0] > high) or np.any(plan[1] < low):
            far.append(name)
    return far


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


def cast_in_parts(triangles, origins, directions, multiple_hits):
    """`cast` over FACES_AT_ONCE triangles at a time, the parts' hits joined (their faces numbered as in `triangles`);
    without `multiple_hits` each ray keeps only the nearest of its parts' first hits."""
    parts = [cast(triangles[start:start + FACES_AT_ONCE], origins, directions, multiple_hits)
             for start in range(0, len(triangles), FACES_AT_ONCE)]
    where = np.concatenate([part[0].reshape(-1, 3) for part in parts])
    rays = np.concatenate([part[1] for part in parts]).astype(int)
    faces = np.concatenate([part[2] + start for part, start in zip(parts, range(0, len(triangles), FACES_AT_ONCE))])
    if multiple_hits or not len(rays):
        return where, rays, faces
    along = np.einsum("ij,ij->i", where - origins[rays], trimesh.util.unitize(directions)[rays])
    order = np.lexsort((along, rays))
    nearest = order[np.r_[True, rays[order][1:] != rays[order][:-1]]]
    return where[nearest], rays[nearest], faces[nearest]


def cast(triangles, origins, directions, multiple_hits=True):
    """Where rays meet triangles (n, 3, 3): (where, which ray, which triangle). Embree (trimesh's mesh.ray) casts them,
    and every ray it gave up on is cast again by trimesh's exact ray_triangle, RAYS at a time: trimesh drops a ray whose
    hit face lies along it (its plane and the ray meet nowhere), and every later hit with it, so a look grazing a bevel
    read open (#128, 2026-11-20: engineroom's look from (-1.988, 0.76, -1.388) towards (0.707, 0, 0.707) first meets
    core_frame's 45-degree face edge on and kept none of the 13 faces it crosses). A ray was given up on when embree
    still meets a face past the last hit kept of it (from its origin when none was kept)."""
    origins, directions = np.asarray(origins, float), np.asarray(directions, float)
    if len(triangles) > FACES_AT_ONCE:
        return cast_in_parts(triangles, origins, directions, multiple_hits)
    local = trimesh.Trimesh(triangles.reshape(-1, 3), np.arange(3 * len(triangles)).reshape(-1, 3), process=False)
    where, rays, faces = local.ray.intersects_location(origins, directions, multiple_hits=multiple_hits)
    ways = trimesh.util.unitize(directions)
    farthest = np.full(len(origins), -np.inf)
    np.maximum.at(farthest, rays, np.einsum("ij,ij->i", where - origins[rays], ways[rays]))
    kept = np.isfinite(farthest)
    past = origins + ways * np.where(kept, farthest + PAST, 0.0)[:, None]
    doubtful = local.ray.intersects_first(past, ways) >= 0
    doubtful = np.flatnonzero(doubtful & ~kept if not multiple_hits else doubtful)
    if len(triangles) >= COLLECTED:
        del local
        gc.collect()  # a Trimesh holds itself round (its cache, its ray caster), so only the collector frees its ray
        # structure: the square's looks kept every batch's, past 12 GB (2099 #161, 2026-11-22)
    if not len(doubtful):
        return where, rays, faces
    exact = trimesh.ray.ray_triangle.RayMeshIntersector(trimesh.Trimesh(
        triangles.reshape(-1, 3), np.arange(3 * len(triangles)).reshape(-1, 3), process=False))
    unsure = np.isin(rays, doubtful)
    found = [(where[~unsure], rays[~unsure], faces[~unsure])]
    for start in range(0, len(doubtful), RAYS):
        batch = doubtful[start:start + RAYS]
        at, which, face = exact.intersects_location(origins[batch], directions[batch], multiple_hits=multiple_hits)
        found.append((at.reshape(-1, 3), batch[which], face))
    return tuple(np.concatenate(parts) for parts in zip(*found))


class Place:
    """A place's objects as solids for rays: each one's role and mesh, and the faces a query reaches, gathered per
    query from the objects whose box meets it (never every face of the scene in one ray structure: 660 rocks on a
    terrain are 7 million faces, which ran the check out of 14 GB)."""

    def __init__(self, stage, place):
        self.prims = {prim.GetName(): prim for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren()}
        self.roles = {name: role_of(prim) for name, prim in self.prims.items()}
        self.meshes = {name: solid_of(prim) for name, prim in self.prims.items() if self.roles[name] not in UNSOLID}
        self.people, self.walking = {}, set()  # a crowd's copies by the package's names; those that walk (crowd.py)
        for name, prim in self.prims.items():
            if self.roles[name] != "character":
                continue
            if not prim.IsA(UsdGeom.PointInstancer):
                self.people[name] = people.posed_body(prim)
                continue
            copies = people.copies_posed(prim)
            self.people.update(copies)
            if prim.HasAttribute("score:walks_to"):
                self.walking.update(copies)
        for name in out_of_reach(self.roles, self.meshes, self.people):
            self.roles[name] = "scenery"
            del self.meshes[name]
        laid = [mesh.bounds for name, mesh in self.meshes.items() if mesh is not None and len(mesh.faces)
                and self.roles[name] != "ground"]
        if laid:
            low, high = np.min([bounds[0] for bounds in laid], axis=0), np.max([bounds[1] for bounds in laid], axis=0)
            self.meshes.update({name: near_ground(mesh, low, high) for name, mesh in self.meshes.items()
                                if mesh is not None and self.roles[name] == "ground"})
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
        origins, directions = np.asarray(origins, float), np.asarray(directions, float)
        if len(origins) > CAST_AT_ONCE:
            parts = [self.hits(origins[start:start + CAST_AT_ONCE], directions[start:start + CAST_AT_ONCE], among,
                               length) for start in range(0, len(origins), CAST_AT_ONCE)]
            return tuple(np.concatenate([part[index] + (start if index == 1 else 0) for part, start in
                                         zip(parts, range(0, len(origins), CAST_AT_ONCE))]) for index in range(4))
        numbers = None if among is None else [self.number[name] for name in among]
        triangles, owners = self.triangles_in(*ray_box(origins, directions, length), among=numbers)
        if not len(triangles):
            return empty
        where, rays, faces = cast(triangles, origins, directions, multiple_hits=True)
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
    bedded = laid.roles[name] in ("fixed", "structure")  # a rock or a footing may lie sunk to any depth: its rays
    # start at its own top (2099 #161: the square's plaza, sunk 0.4 m into its promenade, read floating 3.4 cm over it)
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
    return tilt_faults(laid, name, support) if laid.roles[name] == "prop" else []


def base_of(mesh):
    """An object's base: the largest flat face of its convex hull that looks down within BASE_ANGLE of straight down
    and holds its lowest point (coplanar hull triangles merged), as (its normal, its area); None for an object with no
    flat base of at least BASE_SHARE of its foot's box (its hull's corners in its lowest BASE_SLICE of its height: a lamp's
    base, not its shade), so a bowl's round bottom or a ball has none."""
    hull = mesh.convex_hull
    groups = [list(facet) for facet in hull.facets]
    grouped = {int(face) for facet in hull.facets for face in facet}
    groups += [[face] for face in range(len(hull.faces)) if face not in grouped]
    lowest = float(hull.vertices[:, 1].min())
    low = hull.vertices[hull.vertices[:, 1] <= lowest + max(TOLERANCE, BASE_SLICE * float(np.ptp(hull.vertices[:, 1])))]
    footprint = float(np.prod(np.ptp(low[:, [0, 2]], axis=0)))
    best = None
    for faces in groups:
        area = float(hull.area_faces[faces].sum())
        normal = (hull.face_normals[faces] * hull.area_faces[faces][:, None]).sum(axis=0)
        normal = normal / (np.linalg.norm(normal) or 1.0)
        touches = float(hull.vertices[hull.faces[faces].ravel(), 1].min()) <= lowest + TOLERANCE
        if -normal[1] >= np.cos(np.radians(BASE_ANGLE)) and touches and (best is None or area > best[1]):
            best = (normal, area)
    return best if best is not None and best[1] >= BASE_SHARE * footprint else None


def tilt_faults(laid, name, support):
    """A prop standing at a wrong angle: its base (base_of, the flat underside it stands on: a crate's bottom, the
    face its legs' ends span) turned more than TILT degrees off level."""
    base = base_of(laid.meshes[name])
    if base is None:
        return []
    degrees = float(np.degrees(np.arccos(min(1.0, -float(base[0][1])))))
    if degrees <= TILT:
        return []
    return [{"fault": "tilted", "degrees": round(degrees, 1), "support": support,
             "why": f"stands {degrees:.1f} degrees off level on {support}"}]


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
    """A door's middle, its axes in the scene (across, up, through: up is whichever of its own axes stands most
    upright in the scene, a model laid lying down included (#154: the capsule's hatch); through is the thinner of the
    other two) and its half sizes along them."""
    matrix = np.asarray(UsdGeom.Xformable(laid.prims[name]).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    axes = matrix[:3, :3] / np.linalg.norm(matrix[:3, :3], axis=1)[:, None]
    points = np.asarray(laid.meshes[name].vertices)
    own = points @ axes.T
    low, high = own.min(axis=0), own.max(axis=0)
    middle = ((low + high) / 2) @ axes
    half = (high - low) / 2
    up = int(np.argmax(np.abs(axes[:, 1])))
    first, second = [axis for axis in range(3) if axis != up]
    across, through = (first, second) if half[first] >= half[second] else (second, first)
    upright = axes[up] * (1.0 if axes[up][1] >= 0 else -1.0)
    return middle, np.array([axes[across], upright, axes[through]]), half[[across, up, through]]


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
    where, rays, faces = cast(triangles, origins, np.tile(-axes[2], (len(origins), 1)), multiple_hits=True)
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
    door = ndimage.binary_fill_holes(door)  # its outline: a lattice gate's gaps between its bars are its own
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
    if name in laid.walking or (name in laid.prims and walks(laid.prims[name])):  # a walker always has a foot in the air: its planted (lower) foot is held to CONTACT
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


def door_window(laid, name):
    """The walkers' grid round a door, or round several (`name` a list: an airlock chamber's, scene_package.air_of)
    (x, z low, high): its leaf's box, its width and DOOR_REACH round it, within the
    whole grid (grid_rectangle). A swing or a slide changes the floor only where its leaf moves, so the floor a way
    keeps joined is judged there (the Moon base's 19 doors took 76 floors of the whole place, 47 s each)."""
    names = [name] if isinstance(name, str) else list(name)
    low = np.min([laid.meshes[one].bounds[0] for one in names], axis=0)
    high = np.max([laid.meshes[one].bounds[1] for one in names], axis=0)
    reach_out = max(float(np.max(laid.meshes[one].bounds[1] - laid.meshes[one].bounds[0])) for one in names) + DOOR_REACH
    whole = grid_rectangle(laid)
    return (max(whole[0], low[0] - reach_out), max(whole[1], low[2] - reach_out),
            min(whole[2], high[0] + reach_out), min(whole[3], high[2] + reach_out))


def walkers_grid(laid, near=None):
    """The walkers' grid's rectangle and grid, refused (within_memory) when its floor would not fit in MEMORY; `near`
    (a door's name) keeps only DOOR_REACH round that door's leaf (door_window)."""
    bounds = grid_rectangle(laid) if near is None else door_window(laid, near)
    grid = reach.Grid(bounds)
    cells = grid.shape[0] * grid.shape[1]
    within_memory(cells * SPAN_BYTES + CHUNK_BYTES, f"the walkers' grid ({bounds[2] - bounds[0]:.0f} x "
                  f"{bounds[3] - bounds[1]:.0f} m, {cells:,} cells of {reach.CELL} m, its edges set by "
                  f"{', '.join(widest(laid))})")
    return bounds, grid


def widest(laid):
    """The objects whose boxes set the walkers' grid's edges (grid_rectangle's): west, south, east and north."""
    names = laid.with_role("shell", "connector", "door", "structure", "prop", "mount") or laid.names
    boxes = np.array([laid.meshes[name].bounds for name in names])
    return list(dict.fromkeys(names[index] for index in (np.argmin(boxes[:, 0, 0]), np.argmin(boxes[:, 0, 2]),
                                                          np.argmax(boxes[:, 1, 0]), np.argmax(boxes[:, 1, 2]))))


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


def walkers_floor(laid, doors=None, near=None):
    """Where a walker WALKWAY wide stands: the grid, each span's cell and height, which spans it stands on, and each
    span's piece (spans joined by steps no higher than a knee). `doors`: each door's mesh as it stands for the walkers
    (doors_standing); None, every door open (the walkway check's: is every doorway a way). `near`: a door's name,
    the floor only round it (door_window)."""
    bounds, grid = walkers_grid(laid, near)
    solid = [laid.meshes[name] for name in laid.names if laid.roles[name] != "door"] + list((doors or {}).values())
    meshes = [mesh for mesh in (reach.over_grid(mesh, bounds) for mesh in solid) if mesh is not None]
    no_ground = lambda middles: np.full(len(middles), np.nan)  # noqa: E731 (every floor is a laid surface)
    room = lambda count: within_memory(count * FLOOR_BYTES + CHUNK_BYTES,  # noqa: E731
                                       f"{count:,} floor heights on the walkers' grid")
    span_cells, span_heights = reach.spans(*reach.floor_points(grid, meshes, no_ground, room))
    within_memory(len(span_cells) * SPAN_BYTES, f"the walkers' floor's {len(span_cells):,} spans")
    clear = reach.clear_overhead(grid, meshes, span_cells, span_heights)
    steps = reach.steps_between(grid, span_cells, span_heights)
    crouched = in_hatches(laid, grid, span_cells, span_heights)
    if crouched.any():  # through a hatch the walker crouches and steps over its sill (crouched_through)
        clear, steps = crouched_through(grid, meshes, span_cells, span_heights, crouched, clear, steps)
    standing = room_for_walkway(len(span_cells), steps, clear)
    return grid, span_cells, span_heights, standing, reach.components(len(span_cells), steps, standing)


def in_hatches(laid, grid, span_cells, span_heights):
    """Which spans stand in a hatch's way (a door marked CROUCH, place_build.door --crouch): within its leaf's width,
    HATCH_REACH either side of its plane, from a knee under its sill to its top."""
    inside = np.zeros(len(span_cells), dtype=bool)
    hatches = [name for name in laid.with_role("door") if text_of(laid.prims[name], CROUCH)]
    if not hatches or not len(span_cells):
        return inside
    middles = grid.middles()[span_cells]
    spots = np.column_stack([middles[:, 0], span_heights, middles[:, 1]])
    for name in hatches:
        middle, axes, half = frame_of(laid, name)
        sill = float(laid.meshes[name].bounds[0][1])
        off = spots - middle
        inside |= ((np.abs(off @ axes[0]) <= half[0]) & (np.abs(off @ axes[2]) <= half[2] + HATCH_REACH)
                   & (spots[:, 1] >= sill - CROUCH_KNEE) & (spots[:, 1] <= middle[1] + half[1]))
    return inside


def crouched_through(grid, meshes, span_cells, span_heights, crouched, clear, steps):
    """The clear spans and steps once a hatch's `crouched` spans are judged for a crouching walker: clear under
    CROUCH_HEAD, and steps up to CROUCH_KNEE between two of them (2099's capsule: a side hatch 1.1 m across, its sill
    0.26 m up, crossed crouching as crew do; #154)."""
    picked = np.flatnonzero(crouched)
    clear = clear.copy()
    clear[picked] |= reach.clear_overhead(grid, meshes, span_cells[picked], span_heights[picked], CROUCH_HEAD)
    low = reach.steps_between(grid, span_cells, span_heights, CROUCH_KNEE)
    both = crouched[low[0]] & crouched[low[1]]
    joined = np.concatenate([np.column_stack(steps), np.column_stack([part[both] for part in low])])
    joined = np.unique(joined, axis=0)
    return clear, (joined[:, 0], joined[:, 1], joined[:, 2])


def spans_near(grid, span_cells, span_heights, standing, spot, across=0.4):
    """The standing spans within `across` metres of a spot (x, z) and a knee of its height."""
    middles = grid.middles()[span_cells]
    near = np.hypot(middles[:, 0] - spot[0], middles[:, 1] - spot[2]) <= across
    return np.flatnonzero(standing & near & (np.abs(span_heights - spot[1]) <= reach.KNEE))


def door_sides(laid, name):
    """A door's two sides: {"front": spot, "back": spot}, each a body's depth out of its plane (WALKWAY/2 and 0.2 m past
    its leaf), at its foot."""
    middle, axes, half = frame_of(laid, name)
    foot = laid.meshes[name].bounds[0][1]
    sides = {}
    for side, sign in (("front", 1), ("back", -1)):
        spot = middle + axes[2] * sign * (half[2] + WALKWAY / 2 + 0.2)
        sides[side] = (np.array([spot[0], foot, spot[2]]), axes[2] * sign)
    return sides


def seat_side(laid, name):
    """A seat-entry door's (marked SEAT) side onto its seat, (side, its seat's distance from that side's spot), the
    side nearer the seat's surface; None for a door not marked, or (None, seat name) when the scene holds no such
    seat."""
    seat = text_of(laid.prims[name], SEAT)
    if not seat:
        return None
    if seat not in laid.meshes:
        return None, seat
    gaps = {side: nearest_to_surface(laid.meshes[seat], [spot]) for side, (spot, _) in door_sides(laid, name).items()}
    side = min(gaps, key=gaps.get)
    return side, gaps[side]


def walkway_targets(laid, joins=None):
    """Where the walkers must get to: each door's two sides (a body's depth out, at its foot) and the floor of each
    shell and connector (its box): {target name: spot (x, y, z)} and {target name: (low, high)}. A door leaf in a joined
    doorway (place.json `joins`, recorded from that leaf) leads into its neighbour on its far side: that side is the
    area's to judge (area/'s joins check walks a way through it, seated), never this place's alone (the pad's walkway
    hatch, whose far side is the capsule's, 2099 #161). A seat-entry door's side onto its seat (seat_side) is climbed
    into the seat, never walked (the capsule's hatch over the pilot's seat, 2099 #161): seat_faults judges it."""
    spots, zones = {}, {}
    for name in laid.with_role("door"):
        joined = (joins or {}).get(name)
        inward = np.asarray(joined["inward"], float) if joined and joined.get("from") == f"the door leaf {name}" \
            else None
        onto_seat = (seat_side(laid, name) or (None,))[0]
        for side, (spot, outward) in door_sides(laid, name).items():
            if inward is not None and float(np.dot(outward, inward)) < 0.0:
                continue
            if side == onto_seat:
                continue
            spots[f"{name} ({side})"] = spot
    for name in laid.with_role("shell", "connector"):
        zones[name] = laid.meshes[name].bounds
    return spots, zones


def seat_faults(laid):
    """Seat-entry doors (marked SEAT) whose seat is not in the scene or stands past SEAT_REACH of the door's side onto
    it: [{fault "walkway", target "<door> (seat)", why}]."""
    faults = []
    for name in laid.with_role("door"):
        found = seat_side(laid, name)
        if found is None:
            continue
        side, gap = found
        if side is None:
            faults.append({"fault": "walkway", "target": f"{name} (seat)",
                           "why": f"it opens onto the seat {gap}, which the scene does not hold"})
        elif gap > SEAT_REACH:
            faults.append({"fault": "walkway", "target": f"{name} (seat)", "gap": round(float(gap), 3),
                           "why": f"its seat stands {gap:.2f} m from its {side} side (at most {SEAT_REACH}): "
                                  f"no seat to climb into through it"})
    return faults


def walkway_faults(laid, joins=None):
    """Door sides and zones the walkers cannot reach from the rest on a way WALKWAY wide, and seat-entry doors with no
    seat in reach (seat_faults): [{target, why}] (a joined leaf's far side left to the area, walkway_targets)."""
    grid, span_cells, span_heights, standing, pieces = walkers_floor(laid)
    spots, zones = walkway_targets(laid, joins)
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
            for name, found in sorted(reached.items()) if main not in found] + seat_faults(laid), \
        (grid, span_cells, span_heights, standing)


# --- a closed inside (owner 2026-11-19: a concept's cut is the camera's, never the building's) --------------------

def look_ways():
    """The ways a floor point looks: LOOK_AZIMUTHS round each ring of LOOK_ELEVATIONS, and straight up (n, 3)."""
    turns = np.radians(np.arange(LOOK_AZIMUTHS) * 360.0 / LOOK_AZIMUTHS)
    ways = [(np.cos(np.radians(up)) * np.cos(turn), np.sin(np.radians(up)), np.cos(np.radians(up)) * np.sin(turn))
            for up in LOOK_ELEVATIONS for turn in turns]
    return np.array(ways + [(0.0, 1.0, 0.0)])


def met(laid, origins, directions, length):
    """Whether each ray meets any solid of the place (a door as laid, shut in its opening; glass; a window) within
    `length`."""
    origins, directions = np.asarray(origins, float), np.asarray(directions, float)
    if len(origins) > CAST_AT_ONCE:
        return np.concatenate([met(laid, origins[start:start + CAST_AT_ONCE], directions[start:start + CAST_AT_ONCE],
                                   length) for start in range(0, len(origins), CAST_AT_ONCE)])
    triangles, _ = laid.triangles_in(*ray_box(origins, directions, length))
    if not len(triangles) or not len(origins):
        return np.zeros(len(origins), bool)
    where, rays, _ = cast(triangles, origins, directions, multiple_hits=False)
    reached = np.zeros(len(origins), bool)
    reached[rays[np.linalg.norm(where - origins[rays], axis=1) <= length]] = True
    return reached


def look_points(floor):
    """Points LOOK_HEIGHTS over the walkers' floor (its standing spans, every LOOK_STRIDE on the plan): (n, 3)."""
    grid, span_cells, span_heights, standing = floor
    every = max(1, int(round(LOOK_STRIDE / reach.CELL)))
    columns, rows = np.unravel_index(span_cells, grid.shape)
    kept = standing & (columns % every == 0) & (rows % every == 0)
    middles = grid.middles()[span_cells[kept]]
    return np.concatenate([np.column_stack([middles[:, 0], span_heights[kept] + height, middles[:, 1]])
                           for height in LOOK_HEIGHTS]) if kept.any() else np.zeros((0, 3))


def sight(laid):
    """How far a look from the walkers' floor goes meeting nothing before it sees the outside: SEES, or across a
    bigger place the diagonal of its walkers' objects' box (grid_rectangle's), so a look from one wall always reaches the
    far one (#128, 2026-11-20: the hangar, 40 x 48 m and built closed, read 1156 points open, its looks running out 40 m
    along, short of its far walls)."""
    names = laid.with_role("shell", "connector", "door", "structure", "prop", "mount") or laid.names
    boxes = np.array([laid.meshes[name].bounds for name in names])
    return max(SEES, float(np.linalg.norm(boxes[:, 1].max(axis=0) - boxes[:, 0].min(axis=0))))


def nearest_owners(laid, origins, directions, length, among=None):
    """The name of the first solid (of `among`, names; every one when None) each ray meets within `length`, or
    None."""
    _, rays, owners, along = laid.hits(origins, directions, among=among, length=length)
    order = np.lexsort((along, rays))
    met_rays, first = np.unique(rays[order], return_index=True)
    named = np.full(len(origins), -1)
    named[met_rays] = owners[order][first]
    return [laid.names[owner] if owner >= 0 else None for owner in named]


def rooms(laid, points):
    """Which covered points of an outside place stand in a room of a structure: the object over the point (its first
    solid straight up) closes it round on the level, its looks along the floor meeting that object, a door, or
    something mounted on it (`score:support` wall:<it>, a window or its glass) at least INSIDE_SHARE of the time. Under
    an awning, an arcade or a building's overhang the looks run out along the street or meet the building across it,
    so a covered stretch of the outside is no room (#128, 2026-11-20: the street's pavement under its buildings read
    711 points open). The looks pass through props (unmoved): a small room's furniture is not its walls (#154: a
    cluttered room read 0 of 76 covered points a room, so it passed empty). The cover must be built (BUILT): the
    hollow inside a fixed model, its own ledges read as floor, is no room (2099 #161: the pad's rocket read its engine
    bay and nose ledge open to the outside). Nor is an open frame's (score:lattice, place_build.lattice): a lattice
    tower's members stop most level looks yet it stands in the open air (2099 #161: the pad's tower frame read its
    decks and its foot as rooms open to the outside)."""
    covers = nearest_owners(laid, points, np.tile([0.0, 1.0, 0.0], (len(points), 1)), COVER)
    level = look_ways()[:LOOK_AZIMUTHS]
    seen = np.array(nearest_owners(laid, np.repeat(points, len(level), axis=0), np.tile(level, (len(points), 1)),
                                   sight(laid), unmoved(laid)), dtype=object).reshape(len(points), len(level))
    mounted_on = {name: (text_of(laid.prims[name], "score:support") or "").removeprefix("wall:")
                  for name in laid.names}
    closing = np.array([[owner is not None and (owner == cover or laid.roles[owner] == "door"
                                                or mounted_on[owner] == cover) for owner in row]
                        for cover, row in zip(covers, seen)], dtype=bool).reshape(len(points), len(level))
    built = np.array([cover is not None and laid.roles[cover] in BUILT and not laid.prims[cover].HasAttribute(
        place_build.LATTICE) for cover in covers], dtype=bool)
    return built & (closing.mean(axis=1) >= INSIDE_SHARE)


def unmoved(laid):
    """Every object a level look may be stopped by: all but props (a room's furniture, a stall's goods)."""
    return [name for name in laid.names if laid.roles[name] != "prop"]


def walled(laid, points):
    """Which covered points of an inside place stand among walls: their level looks (props passed through, unmoved)
    meet a solid within `sight` at least INSIDE_SHARE of the time. A porch, stoop or landing under a roof outside the
    walls looks out along its open sides, so it is no inside (#154: the airlock's landing under its porch roof read 6
    points open)."""
    level = look_ways()[:LOOK_AZIMUTHS]
    _, rays, _, _ = laid.hits(np.repeat(points, len(level), axis=0), np.tile(level, (len(points), 1)),
                              among=unmoved(laid), length=sight(laid))
    reached = np.zeros(len(points) * len(level), bool)
    reached[rays] = True
    return reached.reshape(len(points), len(level)).mean(axis=1) >= INSIDE_SHARE


def look_floor(laid):
    """The walkers' floor the looks start from: every door shut in its doorway as laid, never swung open, since the
    looks meet each door shut (a gap no door, as laid, shut, closes); an open leaf lets the floor run through its
    doorway and its frame's points look out past it (#128, 2026-11-20: storage's two open points stood in
    door_1.storage's frame; #154: an airlock's outer door marked to open always read open)."""
    return walkers_floor(laid, {name: laid.meshes[name] for name in laid.with_role("door")})[:4]


def roofless(looked, covered):
    """An inside place whose walkers' floor is less than ROOFED under a roof, slab or flight within COVER (or has no
    floor to look from): no roof or ceiling, so its looks would judge nothing and pass empty (#128, 2026-11-20: the
    stored engineroom@1, its roof left out, read open 0). [{fault, why}] and how many floor points stand uncovered."""
    if not looked:
        return [{"fault": "no roof", "why": "no walkers' floor to look from: the closed-inside check judges nothing"}], 1
    share = 1.0 - covered / looked
    return [{"fault": "no roof", "why": f"{share:.0%} of the walkers' floor ({looked - covered} of {looked} look points) "
                                        f"has no roof, slab or flight within {COVER:.0f} m over it: an inside place "
                                        f"without its roof or ceiling (build it; an outside place is place.json `kind` "
                                        f"outside)"}], looked - covered


def through_joins(origins, directions, joins):
    """Whether each ray passes through a joined doorway (place.json `joins`: its sill middle, inward way, width, sill
    and head in the scene's frame): the place joined there closes it, whichever of the two lays its leaf (#154: the
    stairwell's joined storey read open to the void until a leaf was laid)."""
    passed = np.zeros(len(origins), bool)
    for spot in (joins or {}).values():
        middle, inward = np.asarray(spot["middle"], float), np.asarray(spot["inward"], float)
        across = np.cross([0.0, 1.0, 0.0], inward)
        facing = directions @ inward
        along = np.where(np.abs(facing) > 1e-9, (middle - origins) @ inward / np.where(facing == 0, 1, facing), -1.0)
        where = origins + directions * along[:, None]
        passed |= (along > 0) & (np.abs((where - middle) @ across) <= spot["wide"] / 2) \
            & (where[:, 1] >= spot["sill"]) & (where[:, 1] <= spot["head"])
    return passed


def open_faults(laid, outside=False, joins=None, lent=()):
    """An inside place with less than ROOFED of its walkers' floor covered is told `roofless`, never passed empty.
    Every look from the walkers' floor (look_floor) inside the place (a point under a roof, slab or flight within
    COVER among walls, `walled`, whose looks meet a solid INSIDE_SHARE of the time or more; in an `outside` place, place.json `kind`, only a
    point in a structure's room, `rooms`) that meets nothing within its `sight`: the inside sees the sky or the outside
    through a gap no door, window or glass closes (a cut-away built into the walls); a joined doorway (`joins`,
    place.json) is closed by its neighbour (through_joins). [{fault, at, towards, why}] (at
    most SHOWN_OPEN, each from another point) and how many inside points see out. Seated among neighbours (`lent`,
    their objects' names: check), only a point of the place's own floor and roof is looked from (own_spots)."""
    points, ways = look_points(look_floor(laid)), look_ways()
    if lent:
        points = points[own_spots(laid, points, lent)]
    covered = met(laid, points, np.tile([0.0, 1.0, 0.0], (len(points), 1)), COVER)
    if not outside and (not len(points) or covered.mean() < ROOFED):
        return roofless(len(points), int(covered.sum()))
    points = points[covered]
    if len(points):
        points = points[rooms(laid, points) if outside else walled(laid, points)]
    if not len(points):
        return [], 0
    origins, directions = np.repeat(points, len(ways), axis=0), np.tile(ways, (len(points), 1))
    seeing_far = sight(laid)
    reached = (met(laid, origins, directions, seeing_far)
               | through_joins(origins, directions, joins)).reshape(len(points), len(ways))
    inside = reached.mean(axis=1) >= INSIDE_SHARE
    seeing = np.flatnonzero(inside & ~reached.all(axis=1))
    faults = []
    for number in seeing[:SHOWN_OPEN]:
        towards = ways[np.flatnonzero(~reached[number])[0]]
        at = np.round(points[number], 2).tolist()
        faults.append({"fault": "open to the outside", "at": at, "towards": np.round(towards, 2).tolist(),
                       "why": f"from the walkers' floor at {at} the look towards {np.round(towards, 2).tolist()} "
                              f"meets nothing within {seeing_far:.0f} m: a gap no door, window or glass closes (build the "
                              f"inside closed; a cut-away is the camera's, place.json `cut`)"})
    return faults, len(seeing)


# --- the walkers' ground and routes (sim body, scene clips) -------------------------------------------------------

def opens(laid, name):
    """Whether a door swings open for the walkers: its OPENS mark (owner 2026-11-18: the stairwell's woman "does just
    walk through the door"); a door without it stays shut."""
    return bool(text_of(laid.prims[name], OPENS))


def turned(mesh, hinge, degrees):
    """A mesh turned about the scene's up axis through `hinge` (x, y, z) by `degrees` (right-handed, as USD's
    rotateY)."""
    return mesh.copy().apply_transform(trimesh.transformations.rotation_matrix(np.radians(degrees), (0, 1, 0), hinge))


def inward(laid, middle, through):
    """The side of a door's plane (+1, -1 along `through`) the shell or connector it is set in lies on (the one whose
    box holds the door's middle), else a structure's (blocks-built walls, #154: the capsule's hatch) whose box's
    middle stands INWARD_LEAST or more off the door's plane; None when it is set in none."""
    for roles, least in ((("shell", "connector"), 0.0), (("structure",), INWARD_LEAST)):
        for name in laid.with_role(*roles):
            low, high = laid.meshes[name].bounds
            off = ((low + high) / 2 - middle) @ through
            if np.all(middle >= low) and np.all(middle <= high) and abs(off) >= least:
                return 1.0 if off >= 0 else -1.0
    return None


def moves_by(laid, name):
    """How a door opens (MOVE): "slide" when marked so, else "hinge"."""
    return "slide" if text_of(laid.prims[name], MOVE) == "slide" else "hinge"


def floor_kept(standing, pieces):
    """The walkers' floor's standing pieces' sizes in cells, largest first, compared in turn: a door's open leaf that
    keeps the largest piece whole but cuts another in two ranks below one that cuts nothing (stairwell@32's entrance
    door hinged at its jamb by the stair's foot: the street's side the largest piece either way, its open leaf cut
    the core's floor from the foot of its flight and walled the walkers in at it, 2099 #161)."""
    sizes = np.bincount(pieces[standing]) if standing.any() else np.zeros(0, dtype=int)
    return tuple(sorted((int(size) for size in sizes if size), reverse=True))


def swing_of(laid, name, toward=None):
    """An opening door's swing: its hinge (an edge of its leaf, on its middle's plane) and its turn (SWING), the leaf
    swinging to the side `toward` (+1 or -1 along its through axis: a pressure door's high-pressure side,
    scene_package.locks_of), else into the shell it is set in (an entrance opens inward; either way when in none), on
    the hinge whose open leaf keeps the walkers' floor most whole (floor_kept: an open leaf never cuts a way off),
    then whose free half, above a knee, stands farthest (up to ROOM) from every other solid but the ground:
    {"hinge": [x, y, z], "degrees": d}."""
    middle, axes, half = frame_of(laid, name)
    leaf, others = laid.meshes[name], [laid.number[other] for other in laid.names
                                       if other != name and laid.roles[other] != "ground"]
    side = toward if toward is not None else inward(laid, middle, axes[2])
    best = None
    for edge in (1.0, -1.0):
        hinge = middle + axes[0] * half[0] * edge
        for degrees in (SWING, -SWING):
            opened = turned(leaf, hinge, degrees)
            if side is not None and (opened.centroid - middle) @ axes[2] * side < 0:
                continue
            *_, standing, pieces = walkers_floor(laid, {name: opened}, near=name)
            joined = floor_kept(standing, pieces)
            points = np.asarray(opened.vertices)
            free = points[(np.hypot(*(points - hinge)[:, [0, 2]].T) > half[0])
                          & (points[:, 1] > leaf.bounds[0][1] + reach.KNEE)]
            low, high = opened.bounds
            near, _ = laid.triangles_in(low - ROOM, high + ROOM, among=others)
            room = ROOM if not len(near) or not len(free) else min(ROOM, nearest_to_surface(
                trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(near.reshape(-1, 3), np.arange(3 * len(near)).reshape(
                    -1, 3), ROOM / 2), process=False), np.unique(free, axis=0)))  # edges cut to half ROOM, so the
            # nearest search keeps only the points near the least (the garage door beside a 17 m wall face: 434 s)
            if best is None or (joined, round(room, 3)) > best[0]:
                best = ((joined, round(room, 3)), {"hinge": np.round(hinge, 4).tolist(), "degrees": degrees})
    return best[1]


def overlap(low, high, boxes):
    """The volume a box (low, high) shares with each of the boxes (n x 2 x 3), summed."""
    sides = np.clip(np.minimum(high, boxes[:, 1]) - np.maximum(low, boxes[:, 0]), 0.0, None)
    return float(sides.prod(axis=1).sum())


def slide_of(laid, name):
    """An opening sliding door's slide: its leaf moved its own width along its face (frame_of's across axis), the way
    whose open leaf keeps the walkers' floor most whole (floor_kept), then whose box crosses the least of every other
    solid's but the ground's (it slides alongside its fixed pane or into its wall's pocket, not across a wall
    standing out of the face): {"by": [x, y, z]}."""
    middle, axes, half = frame_of(laid, name)
    leaf = laid.meshes[name]
    boxes = np.array([laid.meshes[other].bounds for other in laid.names
                      if other != name and laid.roles[other] != "ground"]).reshape(-1, 2, 3)
    best = None
    for way in (1.0, -1.0):
        by = axes[0] * 2 * half[0] * way
        opened = leaf.copy().apply_translation(by)
        *_, standing, pieces = walkers_floor(laid, {name: opened}, near=name)
        joined = floor_kept(standing, pieces)
        crossed = overlap(*opened.bounds, boxes)
        if best is None or (joined, -round(crossed, 6)) > best[0]:
            best = ((joined, -round(crossed, 6)), {"by": np.round(by, 4).tolist()})
    return best[1]


def pressure_sides(laid):
    """{door: +1 or -1 along its through axis} for every pressure door of an airlock chamber: the side it opens to
    (scene_package.locks_of: the chamber for its outer door, away from it for its inner)."""
    from score.stages.place_build import scene_package
    return {name: door["toward"] for name, door in scene_package.locks_of(laid)[0].items() if "toward" in door}


def opening(laid, name, toward=None):
    """How an opening door opens for the walkers: slid aside, {"by"} (slide_of), when it slides (MOVE), else swung,
    {"hinge", "degrees"} (swing_of, to the side `toward` when given: a pressure door's, pressure_sides)."""
    return slide_of(laid, name) if moves_by(laid, name) == "slide" else swing_of(laid, name, toward)


def opened_leaf(laid, name, how):
    """A door's leaf as it stands opened `how` (opening): moved by its slide, or turned about its hinge."""
    if "by" in how:
        return laid.meshes[name].copy().apply_translation(how["by"])
    return turned(laid.meshes[name], how["hinge"], how["degrees"])


def doors_standing(laid):
    """{door: its mesh as it stands for the walkers}: a shut door its own leaf (a solid in its doorway), one marked
    OPENS its leaf opened (opening: slid aside, or swung, a pressure door to its high-pressure side), so its doorway
    is a way and the open leaf is walked round."""
    standing = {name: laid.meshes[name] for name in laid.with_role("door")}
    opened = [name for name in standing if opens(laid, name)]
    toward = pressure_sides(laid) if opened else {}
    for name in opened:
        standing[name] = opened_leaf(laid, name, opening(laid, name, toward.get(name)))
    return standing


def solids(folder):
    """{object: its triangles in the scene's frame (n x 3 x 3)} of every object a walker may stand on or run into:
    each one the check reads, every door as it stands for the walkers (doors_standing: shut, or swung open), characters
    never."""
    stage, place = place_build.opened(folder)
    laid = Place(stage, place)
    found = {name: np.asarray(laid.meshes[name].triangles) for name in laid.names if laid.roles[name] != "door"}
    return {**found, **{name: np.asarray(mesh.triangles) for name, mesh in doors_standing(laid).items()}}


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
    """A walker's route through the given spots (x, y, z) on the walkers' floor WALKWAY wide (the check's own, every
    door as it stands for the walkers: a shut one a solid, one marked OPENS swung open): the shortest way over standing spans between each spot and the next, its corners kept and rounded.
    [[x, y, z], ...] and its length along the ground; Refused when a spot has no floor or no way joins two."""
    stage, place = place_build.opened(folder)
    return route_on(Place(stage, place), through)


def route_on(laid, through, doors=None):
    """`route` over a Place already read (area/: the objects of two joined places round their doorway, seated), each
    door as `doors` stands it ({}: every doorway open, the walkway check's); every door as it stands for the walkers
    when None."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    grid, span_cells, span_heights, standing, pieces = walkers_floor(laid, doors_standing(laid) if doors is None
                                                                     else doors)
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


def nearest_to_surface(mesh, points, chunk=8, pairs=PAIRS):
    """The least distance from any of `points` to the mesh's surface, exact: only the points whose nearest vertex lies
    within the mesh's longest edge of the least such vertex distance can be nearest (any point of a face lies within
    its longest edge of one of its corners), searched nearest first, `chunk` points at a time, each against only the
    faces whose box comes within the least distance found so far (or its own nearest vertex's, when that is less), at
    most `pairs` point and face pairs held at once; so a dense made model (half a million faces, TRELLIS.2's) and a
    ring standing a hand off it cost no more memory than a small one (they took 8 GB at once; the capsule's hatch,
    beside 1.2 million faces of its frame and portholes, took a package past 12 GB through trimesh's closest_point,
    which holds every pair of a chunk's points and the faces in their boxes at once)."""
    from scipy.spatial import cKDTree
    points = np.asarray(points, dtype=np.float64)
    vertex_gaps = cKDTree(np.asarray(mesh.vertices)).query(points)[0]
    longest = float(mesh.edges_unique_length.max()) if len(mesh.edges_unique) else 0.0
    order = np.argsort(vertex_gaps)
    order = order[vertex_gaps[order] <= vertex_gaps.min() + longest]
    tree, triangles, least = mesh.triangles_tree, mesh.triangles, float(vertex_gaps.min())
    for start in range(0, len(order), chunk):
        chosen = points[order[start:start + chunk]]
        reach_out = np.minimum(vertex_gaps[order[start:start + chunk]], least)[:, None] + trimesh.tol.merge
        faces, counts = tree.intersection_v(chosen - reach_out, chosen + reach_out)
        faces = np.asarray(faces, dtype=np.int64)
        owners = np.repeat(np.arange(len(chosen)), np.asarray(counts, dtype=np.int64))
        for at in range(0, len(faces), pairs):
            gaps = trimesh.triangles.closest_point(triangles[faces[at:at + pairs]], chosen[owners[at:at + pairs]])
            least = min(least, float(np.linalg.norm(gaps - chosen[owners[at:at + pairs]], axis=1).min()))
    return least


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


def statics_near(laid, name, colliders):
    """The triangles near a loose object that its settle model holds still: every other object's whose box meets its
    own grown by NEAR, an adopted object's (`colliders`, #155) as its own MuJoCo physics collides, the object and what
    it holds left out."""
    low, high = colliders.get(name, laid.meshes[name]).bounds
    low, high = low - NEAR, high + NEAR
    left_out = {laid.number[other] for other in [name, *held_by(laid, name)]}
    found = [laid.triangles_in(low, high, without=left_out | {laid.number[other] for other in colliders})[0]]
    for other, collider in colliders.items():
        if laid.number[other] in left_out:
            continue
        triangles = collider.triangles
        meets = np.all(triangles.max(axis=1) >= low, axis=1) & np.all(triangles.min(axis=1) <= high, axis=1)
        found.append(triangles[meets])
    return np.concatenate(found)


@contextlib.contextmanager
def mujoco_chosen(laid, name):
    """An object's prim with its asset's MuJoCo physics variant chosen (usd_physics.engine_chosen: the variant set
    named for the engine, as a SimReady asset authors it) in the stage's session layer, the stage's own choice put
    back after, so what the scene shows never changes."""
    prim = laid.prims[name]
    stage, path = prim.GetStage(), prim.GetPath()
    with Usd.EditContext(stage, stage.GetSessionLayer()):
        chosen = usd_physics.engine_chosen(prim, "MuJoCo")
        try:
            yield stage.GetPrimAtPath(path)
        finally:
            for engine in chosen:
                stage.GetPrimAtPath(path).GetVariantSet(engine).ClearVariantSelection()
            laid.prims[name] = stage.GetPrimAtPath(path)  # a new variant recomposes the prim: its old handle is gone


def settle_mass(laid, name):
    """The mass an adopted prop authors for itself (#155) as MuJoCo reads it, its MuJoCo physics variant chosen
    (mujoco_chosen), times its laid scale cubed less its asset's unit scale (place_build.units_of: only the scale the
    agent chose weighs it) (kg); NaN when it authors none."""
    with mujoco_chosen(laid, name) as prim:
        mass = usd_physics.authored_mass(prim)
    if mass is None:
        return float("nan")
    linear = np.asarray(UsdGeom.Xformable(laid.prims[name]).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    return mass * abs(float(np.linalg.det(linear[:3, :3]))) / place_build.units_of(laid.prims[name]) ** 3


def collider_of(prim):
    """An object's colliders as its asset authors them (UsdPhysics' CollisionAPI on a mesh or cube, inside its
    instances too, the objects laid on it left out, a collider switched off skipped), in the scene's frame, as one
    mesh: each a convex hull where its MeshCollisionAPI approximation says `convexHull`, else its own triangles;
    None when it authors none."""
    pieces = []
    walk = iter(Usd.PrimRange(prim, Usd.TraverseInstanceProxies()))
    for part in walk:
        if part != prim and part.HasAttribute("score:library"):
            walk.PruneChildren()
            continue
        if not part.HasAPI(UsdPhysics.CollisionAPI) or UsdPhysics.CollisionAPI(part).GetCollisionEnabledAttr().Get() \
                is False:
            continue
        found = gprim_triangles(part)
        if found is None or not len(found[1]):
            continue
        matrix = np.asarray(UsdGeom.Xformable(part).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        piece = trimesh.Trimesh(found[0] @ matrix[:3, :3] + matrix[3, :3], found[1], process=False)
        approximation = UsdPhysics.MeshCollisionAPI(part).GetApproximationAttr().Get() \
            if part.HasAPI(UsdPhysics.MeshCollisionAPI) else None
        pieces.append(piece.convex_hull if approximation == UsdPhysics.Tokens.convexHull else piece)
    return trimesh.util.concatenate(pieces) if pieces else None


def settle_colliders(laid):
    """Each adopted object's (one authoring its own mass, #155) colliders as its MuJoCo physics variant has them
    (mujoco_chosen, collider_of): {name: mesh}. The desk SimReady lays collides by an `sdf` of its triangles in its
    default (PhysX) variant and by its convex hull in MuJoCo's; the settle holds it as MuJoCo does."""
    found = {}
    for name in laid.names:
        with mujoco_chosen(laid, name) as prim:
            collider = collider_of(prim) if usd_physics.authored_mass(prim) is not None else None
        if collider is not None:
            found[name] = collider
    return found


def settle_faults(laid, folder):
    """Each prop let go in MuJoCo (settle_mujoco.py in the physics trial's Python): {name: [fault]}, and how it ran."""
    loose = laid.with_role("prop")
    python = SETTLE_ENV / "bin/python"
    if not loose:
        return {}, "nothing loose"
    if not python.exists():
        return {}, f"not run: no physics trial Python at {SETTLE_ENV} (score/stages/physics/inside/newton_env.sh)"
    job, out = pathlib.Path(folder) / "ready-settle.npz", pathlib.Path(folder) / "ready-settle.json"
    arrays, colliders = {"names": np.array(loose)}, settle_colliders(laid)
    for name in loose:
        vertices = np.asarray(colliders.get(name, laid.meshes[name]).convex_hull.vertices)
        arrays[f"hull_{name}"], arrays[f"statics_{name}"] = vertices, statics_near(laid, name, colliders)
        arrays[f"mass_{name}"] = np.array(settle_mass(laid, name))
    workers = settle_workers({name: len(arrays[f"statics_{name}"]) for name in loose},
                             sum(array.nbytes for array in arrays.values()))
    np.savez(job, **arrays)
    done = subprocess.run([str(python), str(SETTLE_SCRIPT), str(job), str(out), str(workers)], capture_output=True,
                          text=True)
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


def settle_workers(plates, job_bytes):
    """How many settle models run side by side (SETTLE_POOL at most): as many of the largest (`plates`, each loose
    object's static triangles) as fit in MEMORY beside the job (`job_bytes`, held here and read whole by the settle);
    refused (within_memory) when not even one fits."""
    largest = max(plates.values()) * PLATE_BYTES + settle_arena()
    biggest = max(plates, key=plates.get)
    within_memory(2 * job_bytes + largest, f"the settle's job and its largest model ({biggest}, "
                                           f"{plates[biggest]:,} static triangles)")
    room = (MEMORY - in_use() - 2 * job_bytes) // largest
    return int(max(1, min(SETTLE_POOL, len(plates), room)))


def settle_arena():
    """Each settle model's arena (settle_mujoco.ARENA), read from its source: it imports MuJoCo, which only the
    physics trial's Python has."""
    for node in ast.parse(SETTLE_SCRIPT.read_text()).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "ARENA":
            return int(ast.literal_eval(node.value))
    raise RuntimeError(f"no ARENA in {SETTLE_SCRIPT}")


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
                                                     surface_samples(laid.meshes[name], MOUNT_SAMPLES))[1].min())
    if distance > TOLERANCE:
        return [{"fault": "floating", "gap": round(distance, 3), "support": support,
                 "why": f"hangs {distance * 100:.1f} cm off {support}, the wall it is mounted on"}]
    return []


SEPARATOR = "__"  # a seated neighbour's object in the check: <neighbour>__<its name> (area.SEPARATOR's form)
LENT = ("prop", "character")  # a neighbour's objects its own check judges that close no inside: left out of this one


def seat_of(folder):
    """The place's seat in its area (place.json `seat`, written by `area --seat`) as a 4 x 4 column matrix, and its
    area; Refused for a place the area has not seated."""
    seat = place_build.record_of(folder).get("seat")
    if not seat:
        raise place_build.Refused(f"{folder} holds no seat (place.json `seat`): seat it with `area --seat` first")
    return np.asarray(seat["matrix"], float).reshape(4, 4).T, seat["area"]


def within_sight(stage, place):
    """The level box (x, z low, high) a seated place's checks reach: its walkers' objects' box (REACHED, as `sight`
    reads it) grown by its sight (SEES, or that box's diagonal), so no look, walkway or support of its own meets
    anything past it."""
    boxes = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"])
    found = []
    for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren():
        if prim.IsActive() and role_of(prim) in REACHED:
            box = boxes.ComputeWorldBound(prim).ComputeAlignedRange()
            if not box.IsEmpty():
                found.append((np.asarray(box.GetMin())[[0, 2]], np.asarray(box.GetMax())[[0, 2]]))
    if not found:
        return np.full(2, -np.inf), np.full(2, np.inf)
    low, high = np.min([box[0] for box in found], axis=0), np.max([box[1] for box in found], axis=0)
    reach = max(SEES, float(np.linalg.norm(high - low)))
    return low - reach, high + reach


def box_meets(boxes, prim, into, low, high):
    """Whether a neighbour's object, its box put by `into` (its seat in this place's frame), meets the level box
    [low, high] (within_sight's); an object with no box never does."""
    box = boxes.ComputeWorldBound(prim).ComputeAlignedRange()
    if box.IsEmpty():
        return False
    least, most = np.asarray(box.GetMin()), np.asarray(box.GetMax())
    corners = np.array([[x, y, z] for x in (least[0], most[0]) for y in (least[1], most[1])
                        for z in (least[2], most[2])])
    level = (corners @ into[:3, :3].T + into[:3, 3])[:, [0, 2]]
    return bool(np.all(level.max(axis=0) >= low) and np.all(level.min(axis=0) <= high))


def seated_among(folder, neighbours):
    """The place's stage as its area seats it among `neighbours` ({place: folder}, all seated in its area by `area
    --seat`), on a session layer of its own (the scene file never moves): its backdrop (place.json `backdrop`, what a
    neighbour stands for) left out, as its seated package leaves it, and every object of each neighbour but its props,
    people and backdrop laid in when it stands within the place's sight (within_sight: 2099's prologue, 2026-11-22,
    the flat checked among the square's 848 objects ran past 12 GB casting its looks at all of them), seated into this
    place's frame, named <neighbour>__<object> and keeping its role, so
    a door set in the neighbour's wall and a room the neighbour closes are read as they stand in the game (2099's
    prologue, 2026-11-22: the street's block hollowed round the stairwell left the street's stair_door in no wall).
    The stage, its place and the neighbours' object names."""
    own, area = seat_of(folder)
    stage = Usd.Stage.Open(Sdf.Layer.FindOrOpen(str(place_build.scene_path(folder).resolve())),
                           Sdf.Layer.CreateAnonymous())
    place = stage.GetDefaultPrim().GetName()
    stage.SetEditTarget(stage.GetSessionLayer())
    for name in place_build.record_of(folder).get("backdrop") or []:
        prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
        if prim:
            prim.SetActive(False)
    lent = set()
    low, high = within_sight(stage, place)
    for neighbour, other in sorted(neighbours.items()):
        seat, seated_in = seat_of(other)
        if seated_in != area:
            raise place_build.Refused(f"{neighbour} is seated in the area {seated_in}, {folder} in {area}")
        into = np.linalg.inv(own) @ seat
        source, source_place = place_build.opened(other)
        path = str(place_build.scene_path(other).resolve())
        left_out = set(place_build.record_of(other).get("backdrop") or [])
        boxes = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"])
        for prim in source.GetPrimAtPath(f"/{source_place}/Objects").GetChildren():
            role = role_of(prim)
            if prim.GetName() in left_out or role in LENT or not box_meets(boxes, prim, into, low, high):
                continue
            name = f"{neighbour}{SEPARATOR}{prim.GetName()}"
            laid = stage.DefinePrim(f"/{place}/Objects/{name}")
            laid.GetReferences().AddReference(Sdf.Reference(path, prim.GetPath()))
            laid.CreateAttribute("score:role", Sdf.ValueTypeNames.String).Set(role)
            xform = UsdGeom.Xformable(laid)
            ops = xform.GetOrderedXformOps()
            outer = xform.AddTransformOp(opSuffix="seat")
            outer.Set(Gf.Matrix4d(into.T.tolist()))
            xform.SetXformOpOrder([outer, *ops], xform.GetResetXformStack())
            lent.add(name)
    return stage, place, lent


def lent_first(laid, points, way, length, lent):
    """Whether the first surface each point meets along `way` within `length` is a neighbour's (`lent`, their names),
    or one of the place's own no nearer than CONTACT before it (a floor laid flush on a neighbour's, the street's lot
    under the stairwell's slab, is the neighbour's). The two are cast apart, so a face flush with another is met."""
    ways = np.tile(way, (len(points), 1))
    nearest = []
    for among in ([name for name in laid.names if name not in lent], [name for name in laid.names if name in lent]):
        _, rays, _, along = laid.hits(points, ways, among=among, length=length)
        first = np.full(len(points), np.inf)
        np.minimum.at(first, rays, along)
        nearest.append(first)
    own, theirs = nearest
    return np.isfinite(theirs) & (theirs <= own + CONTACT)


def own_spots(laid, points, lent):
    """Which look points are the place's own to judge, seated among neighbours: the first surface straight under each
    (within the highest of LOOK_HEIGHTS and CONTACT) and straight over it (within COVER) are none of a neighbour's
    `lent` objects. A point on a neighbour's floor or under its roof is the neighbour's, judged in its own check
    (2099's prologue, 2026-11-22: the street read the seated stairwell's hall as its own open room, the stairwell its
    forecourt slab under the street's arcade as its own inside)."""
    under = lent_first(laid, points, [0.0, -1.0, 0.0], max(LOOK_HEIGHTS) + CONTACT, lent)
    over = lent_first(laid, points, [0.0, 1.0, 0.0], COVER, lent)
    return ~under & ~over


def check(folder, settle=True, neighbours=None):
    """Every reason the place is not physics ready, per object, written to <folder>/ready.json; the counts. With
    `neighbours` ({place: folder}) the place is read as its area seats it among them (seated_among): only its own
    objects are judged, and its looks start only on its own floor under its own roof (own_spots)."""
    stage, place = place_build.opened(folder)
    unfinished = finished.faults(stage, place)
    misread = shapes.faults(stage, place)
    plan = plan_fit.plan_of(folder)
    record = place_build.record_of(folder)
    strays = None if plan is None else plan_fit.faults(stage, place, plan, role_of, record.get("kind") == "outside",
                                                       set(record.get("backdrop") or []))
    lent = set()
    if neighbours:
        stage, place, lent = seated_among(folder, neighbours)
    laid = Place(stage, place)
    walkers_grid(laid)  # refused here, before the per-object measures, when the walkers' floor would not fit
    found = {name: [{"fault": "no collision geometry", "why": "it has no triangles to collide by"}]
             for name in laid.prims if laid.roles[name] not in UNSOLID + ("scenery",) and name not in laid.names
             and name not in lent}
    for name in laid.names:
        faults = object_faults(laid, name) if name not in lent else []
        if faults:
            found.setdefault(name, []).extend(faults)
    for name in laid.people:
        faults = person_faults(laid, name)
        if faults:
            found.setdefault(name, []).extend(faults)
    record = place_build.record_of(folder)
    # Seated among its neighbours their floor stands past a joined leaf (and the joins are in the place's own frame).
    walkways, floor = walkway_faults(laid, None if neighbours else record.get("joins"))
    for fault in walkways:
        if fault["target"].split(" (")[0] not in lent:
            found.setdefault(fault["target"].split(" (")[0], []).append(fault)
    for name in laid.with_role("connector"):
        for fault in (connector_faults(laid, name, floor) if name not in lent else []):
            found.setdefault(name, []).append(fault)
    del floor  # the looks start from a floor of their own, the doors shut (look_floor): one floor held at a time
    gaps, seeing = open_faults(laid, record.get("kind") == "outside", record.get("joins"), lent)
    settled, engine = settle_faults(laid, folder) if settle else ({}, "not asked")
    for name, faults in settled.items():
        found.setdefault(name, []).extend(faults)
    counts = {}
    for faults in found.values():
        for fault in faults:
            counts[fault["fault"]] = counts.get(fault["fault"], 0) + 1
    if seeing:
        counts[gaps[0]["fault"]] = seeing
    path = pathlib.Path(folder) / "ready.json"
    path.write_text(json.dumps({"place": place, "roles": {name: role for name, role in laid.roles.items()
                                                          if name not in lent},
                                "objects": found, "open": gaps, "finishes": unfinished, "shapes": misread, "plan": strays,
                                "settle": engine, "among": sorted(neighbours or {})}, indent=1))
    return {"ready": not found and not unfinished and not misread and not seeing and not strays,
            "objects": len(laid.prims) - len(lent), "with_faults": len(found), "counts": counts, "open": seeing,
            "unfinished": len(unfinished), "misread": len(misread),
            "plan": "no plan taken in" if strays is None else len(strays), "settle": engine,
            "among": sorted(neighbours or {}), "file": str(path)}


# --- the `on` helper ----------------------------------------------------------------------------------------------

def levels_under(laid, support, spot, across=(0.0, 0.0)):
    """The heights of the support's surfaces that look up, straight under a spot (x, z) and a LEVEL_RAYS grid over the
    footprint `across` (x, z metres) round it, lowest first, those within 2 cm of each other one level (#154: a stick
    whose middle stood over the console's slot read no level on the console's top)."""
    xs = spot[0] + np.linspace(-0.5, 0.5, LEVEL_RAYS) * across[0]
    zs = spot[1] + np.linspace(-0.5, 0.5, LEVEL_RAYS) * across[1]
    top = laid.meshes[support].bounds[1][1] + 1.0
    origin = np.array([[x, top, z] for x in xs for z in zs])
    where, _, owners, _ = laid.hits(origin, np.tile([0.0, -1.0, 0.0], (len(origin), 1)), among=[support])
    heights = np.sort(where[owners == laid.number[support], 1])
    levels = []
    for height in heights:
        if not levels or height - levels[-1] > 0.02:
            levels.append(float(height))
        else:
            levels[-1] = float(height)
    return levels


def levelled(turn, mesh):
    """The laid turn (rotateXYZ degrees) that stands the object's base (base_of) level, turned about its own spot, so
    its base looks straight down; the turn as it was for an object with no base."""
    from scipy.spatial.transform import Rotation
    base = base_of(mesh)
    if base is None:
        return list(turn)
    down = np.array([0.0, -1.0, 0.0])
    axis = np.cross(base[0], down)
    if np.linalg.norm(axis) < 1e-9:
        return list(turn)
    angle = float(np.arccos(np.clip(base[0] @ down, -1.0, 1.0)))
    fix = Rotation.from_rotvec(axis / np.linalg.norm(axis) * angle)
    # USD's rotateXYZ turns about x, then y, then z: scipy's extrinsic "xyz"
    return [float(value) for value in (fix * Rotation.from_euler("xyz", turn, degrees=True)).as_euler("xyz", degrees=True)]


def placed_on(stage, place, name, support, level=None, height=None, upright=False):
    """The object moved to rest in contact on its support (see `on`), first stood level on its base when `upright`
    (levelled); its new spot and what it rests on."""
    laid = Place(stage, place)
    if name not in laid.meshes or laid.meshes[name] is None:
        raise place_build.Refused(f"the scene holds no object {name} with a shape")
    prim = laid.prims[name]
    at, turn, scale = place_build.pose_of(prim)
    if upright:
        turn = levelled(turn, laid.meshes[name])
        place_build.posed(prim, at, turn, scale)
        laid = Place(stage, place)
        prim = laid.prims[name]
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
        levels = levels_under(laid, support, mesh.bounds.mean(axis=0)[[0, 2]], np.ptp(mesh.bounds, axis=0)[[0, 2]])
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


def floor_under(laid, name, wall):
    """The height of the floor under the object's middle (the ground, a shell's, a connector's or a structure's deck,
    the wall it is mounted on left out), else 0."""
    mesh = laid.meshes[name]
    middle = mesh.bounds.mean(axis=0)
    floor_gap, _ = gaps_down(laid, name, mesh.bounds[0][None] * [0, 1, 0] + [middle[0], 0, middle[2]],
                             only=[other for other in laid.with_role("ground", "shell", "connector", "structure")
                                   if other != wall])  # a blocks-built deck is a structure (#154: airlock@2's 0.42 m)
    return mesh.bounds[0][1] - float(floor_gap[0]) if np.isfinite(floor_gap[0]) else 0.0


def mount_height(laid, name, wall):
    """How high the mount stands over its floor (`floor_under`): the height `mounted` lays it at again."""
    return float(laid.meshes[name].bounds[0][1] - floor_under(laid, name, wall))


def mounted(laid, name, wall, height, pose):
    """The object at `height` over the floor under it (the ground, a shell's, a connector's or a structure's deck, the
    wall itself left out), moved straight to the wall's nearest face until it touches."""
    if wall not in laid.meshes or laid.meshes[wall] is None:
        raise place_build.Refused(f"no wall {wall} in the scene")
    at, turn, scale = pose
    mesh = laid.meshes[name]
    middle = mesh.bounds.mean(axis=0)
    lift = (floor_under(laid, name, wall) + float(height or 0.0)) - mesh.bounds[0][1]
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


def on(folder, name, support, level=None, height=None, upright=False):
    """Lay an object at rest, in contact, on a named support: `floor` (the ground, a deck or a floor under it),
    an object (its top under the object, or with `level` its n-th surface that looks up, from 0 at the bottom, -1 the
    top: a shelf level), or `wall:<object>` (mounted `height` metres over the floor, moved straight to the wall until it
    touches). Only its height (or, mounted, its height and its way to the wall) changes, and with `upright` its turn,
    so its base stands level (a model made leaning, told `tilted`); the scene is saved."""
    stage, place = place_build.opened(folder)
    answer = placed_on(stage, place, name, support, level, height, upright)
    place_build.saved(stage)
    return answer
