"""Runs in Newton's own Python (score/stages/physics/inside/newton_env.sh, pinned; Newton and Warp, Apache-2.0): an
outfit of GarmentCode garments sewn, draped and worn over one clip on Newton's SolverVBD, against the person's body as
one moving triangle mesh. Never GarmentCode's own simulator (its Warp fork is non-commercial).

    <env>/bin/python tools/characters/garments/inside/drape.py <job.json> <out.npz>

job.json (written by tools/characters/garments): {"device", "rate" (frames a second), "substeps", "iterations",
"gravity" (m/s2), "body": <npz: `bind` points x 3 (m), `faces`, `frames` frames x points x 3 (the body's skin every
frame of the run: its turn from the bind to the clip's first frame, then the clip), `clip_start`>, "sew_seconds",
"still_seconds", "garments": [{"name", "record": <pattern.py's npz>, "offset": [x, y, z] (m, the record's frame to the
body's), "worn": [labels of the record's points worn on the body], "holds": [{"label", "axis" (0 x, 1 y, 2 z),
"value" (m), "side" (+1 or -1)}: points past a level drawn back to it, those on its side left], "layer_m" (an outer
garment's box points laid that much further off the skin, `laying.laid_out`), "material":
{"density" kg/m2, "mu" N/m, "lambda" N/m, "bending" N, "radius" m}}], "contact": {"mu", "ke", "kd", "margin" (m)},
"self": {"margin", "gap" (m)}, "neck": [the body's points round its neck's base: the holds' levels move with their
mean], "holds_until": "sewn", "turned" or "worn" (the drawn points held while sewing, through the turn too, or
through the clip too), "belt" (optional): {"on": the garment it is worn on, "under_top", "width", "reach" (m),
"limits": {garment name: m} (the garments it holds in), "outside": {garment name: m} (the garments over it)}}.

The run, in the order GarmentCode's own drape goes: each garment's box mesh (its panels laid round the body, each seam's
points shared) is one cloth whose triangles rest first as laid and go over to their flat panels' shapes in the first
fifth of sewing (`laying.rest_lengths`), and whose edges bend flat, so the seams pull shut and the panels take their
sewn shape round the body; a garment's held points (its waistband's top,
GarmentCode's `lower_interface`) are carried from where the box lays them to the body's skin under them at the waist
level and then ride the skin as a worn waistband does, every other point is cloth; a garment's drawn points (a
neckline's halves, GarmentCode's `right_collar` and `left_collar`) that stand out past their level are drawn back to it,
as GarmentCode's attachments (a plane and its normal) draw them, while sewing and as long as the job's `holds_until`
says, the levels moving with the body's neck; a point inside the level is left (drawn both ways, every point of a half
pulled to the neck's side, the neckline's middle was torn open sideways and the tee sewn several centimetres off centre,
2026-11-24), a point past it put back on it each substep (moved a twentieth of the way, the cloth pulled the neckline 5
cm past its planes and the tee was sewn up to 4 cm to her left, 2026-11-24). Gravity is off for the first fifth of
`sew_seconds`, then on; speeds are capped at SEW_SPEED while sewing (GarmentCode's global cap), never after. Then the
body turns from its bind to the clip's first frame (the job's frames up to `clip_start`), stands `still_seconds`, and
plays the clip. Each substep the body mesh's points and velocities are set where the skin is at the substep's end and
the mesh refitted, so the cloth meets the moving body with its own speed (Newton reads mesh velocities for contact).
A belt, once sewn (from the turn on), holds the cloth under it in: each substep a point of a belted garment over
the band's skin and further off it than that garment's limit is moved BELT_SHARE of the way back to its limit along
the skin's normal; a point of a garment over the belt nearer the skin than its `outside` is moved out the same way. Cloth and cloth collide (self contact, between garments too). No cloth damping of its
own. VBD's run-to-run deterministic mode is off: on this card it took a substep from 10 ms to 180 ms (2026-11-24).

out.npz: per garment `<name>` clip frames x points x 3 (m, world, each clip frame's end), `<name>/sewn` points x 3 (at
the bind after sewing), `inside/<name>` clip frames x points (each point's signed distance to the body at that frame,
m, negative inside), `seconds/clip` (the clip's wall seconds), `seconds/sew`, `engine` (text).
"""
import json
import pathlib
import sys
import time

import newton
import numpy as np
import warp as wp

import laying

SEW_SPEED = 0.25  # m/s, GarmentCode's global_max_velocity while the panels close (sim_config.py)
CENTIMETRES = 0.01
HOLDING = {"sewn": 0, "turned": 1, "worn": 2}  # how long the drawn points are held: sewing, the turn too, the clip too
BLOWN = None  # where a clip that blows up keeps its garments' frames before it (run's out.npz, .blown.npz)
BELT_REACH = 0.1  # m: a cloth point further than this from the skin is not looked at by the belt
# Of the way back to its limit a cloth point past it under the belt moves each substep: moved the whole way (with its
# speed outward taken away, and the arms' skin still posed otherwise than the clips rig's bind) the cloth blew up at
# walk frame 25 (2026-11-24).
BELT_SHARE = 0.1
HOLD_SHARE = 1.0  # of the way back to its level a drawn point past it moves each substep while held
UNDER_FOOT_M = 0.03  # sewn cloth whose nearest skin lies this near an outer point's is the cloth under it
CROSS_STEP_M = 0.004  # how far out a laid point whose cloth crosses the cloth under it is moved a round
CROSS_ROUNDS = 40  # rounds of that before the laying is refused (16 cm out)


def arguments():
    given = sys.argv[1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), pathlib.Path(given[1])


def bending_edges(faces):
    """Each inner edge of the welded mesh with its two triangles' far corners, as Newton's (o1, o2, v1, v2), and the
    triangle each side came from."""
    found, sides = {}, []
    for number, face in enumerate(faces):
        for corner in range(3):
            one, other, far = face[corner], face[(corner + 1) % 3], face[(corner + 2) % 3]
            key = (min(one, other), max(one, other))
            if key in found:
                first_far, first_face = found.pop(key)
                sides.append(((first_far, far, key[0], key[1]), (first_face, number)))
            else:
                found[key] = (far, number)
    return sides


@wp.kernel
def capped(velocities: wp.array[wp.vec3], most: float):
    index = wp.tid()
    speed = wp.length(velocities[index])
    if speed > most:
        velocities[index] = velocities[index] * (most / speed)


@wp.kernel
def signed_distance(mesh: wp.uint64, points: wp.array[wp.vec3], reach: float, found: wp.array[wp.float32]):
    """Each point's distance to the body's surface, negative inside (winding number), `reach` when farther."""
    index = wp.tid()
    query = wp.mesh_query_point_sign_winding_number(mesh, points[index], reach)
    if query.result:
        nearest = wp.mesh_eval_position(mesh, query.face, query.u, query.v)
        found[index] = query.sign * wp.length(points[index] - nearest)
    else:
        found[index] = reach


@wp.kernel
def nearest(mesh: wp.uint64, points: wp.array[wp.vec3], reach: float, faces: wp.array[wp.int32],
            uvs: wp.array[wp.vec2]):
    """Each point's nearest place on the mesh: its triangle (-1 past `reach`) and barycentric u, v."""
    index = wp.tid()
    query = wp.mesh_query_point_no_sign(mesh, points[index], reach)
    faces[index] = -1
    if query.result:
        faces[index] = query.face
        uvs[index] = wp.vec2(query.u, query.v)


def body_inside(skin, faces):
    """Which of a set of points stand inside the body at `skin` (the card's winding number, a metre's reach): for
    laying.laid_out."""
    mesh = wp.Mesh(points=wp.array(skin, dtype=wp.vec3), indices=wp.array(faces.ravel(), dtype=wp.int32),
                   support_winding_number=True)

    def inside(points):
        found = wp.zeros(len(points), dtype=wp.float32)
        wp.launch(signed_distance, dim=len(points), inputs=[mesh.id, wp.array(points, dtype=wp.vec3), 1.0, found])
        return found.numpy() < 0.0
    return inside


@wp.kernel
def drawn(particles: wp.array[wp.int32], axis: int, levels: wp.array[wp.float32], moved: float, side: float,
          share: float, positions: wp.array[wp.vec3]):
    """Each point past its level (`levels`, moved by `moved`) along `axis` moved `share` of the way back to it, a
    point on its `side` of it left (GarmentCode's attachment: a plane at the level whose normal is `side` along the
    axis)."""
    index = wp.tid()
    particle = particles[index]
    position = positions[particle]
    value = levels[index] + moved
    if side * (position[axis] - value) < 0.0:
        position[axis] = position[axis] + share * (value - position[axis])
        positions[particle] = position


@wp.kernel
def cinched(mesh: wp.uint64, particles: wp.array[wp.int32], limits: wp.array[wp.float32],
            least: wp.array[wp.float32], banded: wp.array[wp.int32], reach: float, share: float,
            positions: wp.array[wp.vec3]):
    """Each point over the belt's band of skin (`banded` triangles) further off it than its limit moved `share` of
    the way back to the limit along the skin's normal (the belt holding the cloth in), and one nearer it than its
    `least` moved `share` of the way out to it (cloth over the belt)."""
    index = wp.tid()
    particle = particles[index]
    query = wp.mesh_query_point_no_sign(mesh, positions[particle], reach)
    if query.result:
        if banded[query.face] == 1:
            on = wp.mesh_eval_position(mesh, query.face, query.u, query.v)
            normal = wp.mesh_eval_face_normal(mesh, query.face)
            off = wp.dot(positions[particle] - on, normal)
            if off > limits[index]:
                positions[particle] = positions[particle] - normal * (off - limits[index]) * share
            elif off < least[index]:
                positions[particle] = positions[particle] + normal * (least[index] - off) * share


@wp.kernel
def skin_at(frames: wp.array[wp.vec3], count: int, frame: int, after: int, share: float, rate: float,
            points: wp.array[wp.vec3], velocities: wp.array[wp.vec3]):
    """The body's skin `share` of the way from `frame` to `after` (frames stored one after another, `count` points
    each), and its velocity over the frame."""
    index = wp.tid()
    one, other = frames[frame * count + index], frames[after * count + index]
    points[index] = one * (1.0 - share) + other * share
    velocities[index] = (other - one) * rate


@wp.kernel
def held_on(particles: wp.array[wp.int32], corners: wp.array[wp.vec3i], weights: wp.array[wp.vec3],
            start: wp.array[wp.vec3], radius: float, carry: float, skin: wp.array[wp.vec3], rate: float,
            positions: wp.array[wp.vec3], velocities: wp.array[wp.vec3]):
    """Each held point `carry` of the way from where the box laid it to its place on the skin (out by `radius`), its
    velocity the move over the substep."""
    index = wp.tid()
    triangle, weight = corners[index], weights[index]
    one, two, three = skin[triangle[0]], skin[triangle[1]], skin[triangle[2]]
    normal = wp.normalize(wp.cross(two - one, three - one))
    on = one * weight[0] + two * weight[1] + three * weight[2] + normal * radius
    target = start[index] * (1.0 - carry) + on * carry
    particle = particles[index]
    velocities[particle] = (target - positions[particle]) * rate
    positions[particle] = target


def laid_over(points, faces, skin, skin_faces, under, clear):
    """A garment sewn alone on the body (`points`, its `faces`) laid outside the cloth sewn under it (`under`: its
    points and faces): each point moved out along the skin's normal at the skin point nearest it until it stands
    `clear` (m) further off the skin than that cloth (where the cloth's nearest skin lies within UNDER_FOOT_M of the
    point's), then `uncrossed`. Its box mesh laid over the sewn cloth, a seam's long triangles (a front panel's edge to
    the back panel's, 16 to 18 cm) cut through it however far out the points were laid: a jacket's side seams through
    the trousers' waistband, a coat's through its shirt at the sides and armpits (2026-11-25); sewn, every triangle is
    the cloth's own small one. Moved along the way from its nearest skin point instead, cloth sewn a centimetre off a
    skin of 4.5 mm triangles went along the skin as much as off it (for 30% of woman_stair_modern's tee more than 60
    degrees off the normal), neighbouring points apart, and a tee triangle at her back's waist was pulled to 18 cm
    and through her jeans however far out (2026-11-25)."""
    from scipy.spatial import cKDTree
    skin_tree = cKDTree(skin)
    normals = laying.skin_normals(skin, skin_faces)
    _, nearest = skin_tree.query(points)
    away = normals[nearest]
    height = np.sum((points - skin[nearest]) * away, axis=1)
    least = height.copy()
    under_points, under_faces = under
    _, under_nearest = skin_tree.query(under_points)
    under_height = np.sum((under_points - skin[under_nearest]) * normals[under_nearest], axis=1)
    feet = cKDTree(skin[under_nearest])
    for index, near in enumerate(feet.query_ball_point(skin[nearest], UNDER_FOOT_M)):
        if near:
            least[index] = max(least[index], under_height[near].max() + clear)
    return uncrossed(points + away * (least - height)[:, None], faces, away, under_points, under_faces)


def edges_of(faces):
    """The mesh's edges, each once (point pairs, the lower first)."""
    found = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    return np.unique(found, axis=0)


def through(points, edges, other, faces, edge_wise):
    """Which of the segments `edges` (on `points`) pass through which triangles `faces` (on `other`): (segment,
    triangle) index pairs. Candidates are the triangles near each segment (`edge_wise`: looked for round each
    segment, for long segments and small triangles; else round each triangle)."""
    from scipy.spatial import cKDTree
    middles, half = points[edges].mean(axis=1), np.linalg.norm(points[edges[:, 1]] - points[edges[:, 0]], axis=1) / 2.0
    centres = other[faces].mean(axis=1)
    sizes = np.linalg.norm(other[faces] - centres[:, None], axis=2).max(axis=1)
    if edge_wise:
        near = cKDTree(centres).query_ball_point(middles, half + sizes.max())
        segment = np.repeat(np.arange(len(edges)), [len(each) for each in near])
        triangle = np.fromiter((index for each in near for index in each), int, len(segment))
    else:
        near = cKDTree(middles).query_ball_point(centres, sizes + half.max())
        triangle = np.repeat(np.arange(len(faces)), [len(each) for each in near])
        segment = np.fromiter((index for each in near for index in each), int, len(triangle))
    start, along = points[edges[segment, 0]], points[edges[segment, 1]] - points[edges[segment, 0]]
    corner = other[faces[triangle, 0]]
    first, second = other[faces[triangle, 1]] - corner, other[faces[triangle, 2]] - corner
    across = np.cross(along, second)
    determinant = np.sum(first * across, axis=1)
    usable = np.abs(determinant) > 1e-14
    inverse = 1.0 / np.where(usable, determinant, 1.0)
    offset = start - corner
    one = np.sum(offset * across, axis=1) * inverse
    turned = np.cross(offset, first)
    two = np.sum(along * turned, axis=1) * inverse
    share = np.sum(second * turned, axis=1) * inverse
    hit = usable & (one >= 0.0) & (two >= 0.0) & (one + two <= 1.0) & (share >= 0.0) & (share <= 1.0)
    return segment[hit], triangle[hit]


def uncrossed(points, faces, away, under_points, under_faces):
    """An outer garment's laid points moved out (`away`: each point's way off the skin) CROSS_STEP_M a round until
    none of its edges passes through the cloth under it and none of that cloth's edges through its triangles, at
    most CROSS_ROUNDS rounds, else refused: cloth that starts crossed stays tangled, VBD's self contact keeps a
    crossed point from moving (a coat's and shirt's crossed points were left in the air as the body walked on, and the
    trousers caught in them blew up at clip frame 29, 2026-11-25)."""
    points = np.array(points, dtype=float)
    edges, under_edges = edges_of(faces), edges_of(under_faces)
    for _ in range(CROSS_ROUNDS):
        crossing, _ = through(points, edges, under_points, under_faces, edge_wise=True)
        _, pierced = through(under_points, under_edges, points, faces, edge_wise=False)
        moved = np.unique(np.concatenate([edges[crossing].ravel(), faces[pierced].ravel()]))
        if not len(moved):
            return points
        points[moved] += away[moved] * CROSS_STEP_M
    raise RuntimeError(f"a garment laid {CROSS_ROUNDS * CROSS_STEP_M * 100:.0f} cm out still crosses the cloth under "
                       f"it at {len(moved)} points")


def levels(points, hold):
    """Each drawn point's level: the hold's, or where the box lays the point when it is already past it (the
    pattern's neckline wider than the neck: drawn in to the neck's planes at once, the dress's and the jacket's
    neckline ends, laid 1.6 to 2.9 cm past them, were gathered into lumps on the shoulders, 2026-11-24); a point is
    kept from going further out, never pulled in past where its pattern puts it."""
    along = np.asarray(points, dtype=float)[:, hold["axis"]]
    past = hold["side"] * (along - hold["value"]) < 0.0
    return np.where(past, along, hold["value"]).astype(np.float32)


class Garment:
    """One garment's cloth in the builder: its particles, triangles, bending edges and held points."""

    def __init__(self, builder, spec, skin, inside, clear, placed=None):
        record = dict(np.load(spec["record"]))
        offset = np.asarray(spec["offset"], dtype=float)
        self.name, self.first = spec["name"], builder.particle_count
        self.points = record["points"] * CENTIMETRES + offset
        copies, box, faces = record["copies"] * CENTIMETRES + offset, record["box"], record["faces"]
        welded = box[faces]
        self.faces, self.count = welded, len(self.points)
        material = spec["material"]
        flat = copies[faces]
        areas = 0.5 * np.linalg.norm(np.cross(flat[:, 1] - flat[:, 0], flat[:, 2] - flat[:, 0]), axis=1)
        masses = np.zeros(self.count)
        np.add.at(masses, welded.ravel(), np.repeat(areas / 3.0 * material["density"], 3))
        self.held = np.unique(np.concatenate([record[f"label/{key}"] for key in spec.get("worn", [])]
                                             or [np.zeros(0, int)]))
        self.holds = [(record[f"label/{hold['label']}"] + self.first, hold["axis"],
                       levels(self.points[record[f"label/{hold['label']}"]], hold), hold["side"])
                      for hold in spec.get("holds", [])]
        masses[self.held] = 0.0
        builder.add_particles([tuple(point) for point in self.points], [(0.0, 0.0, 0.0)] * self.count,
                              masses.tolist(), radius=[material["radius"]] * self.count)
        # A triangle's rest shape is read off its corners where they stand when it is added: each panel's corners are
        # put on its flat panel (laid in 3D) while its triangles go in, then every point goes back to the box mesh.
        order = []
        for panel in np.unique(record["panel"]):
            mine = np.flatnonzero(record["panel"] == panel)
            for copy in mine:
                builder.particle_q[self.first + int(box[copy])] = wp.vec3(*copies[copy])
            chosen = np.flatnonzero(record["panel"][faces[:, 0]] == panel)
            panel_faces = welded[chosen] + self.first
            count, before = len(panel_faces), builder.tri_count
            builder.add_triangles(panel_faces[:, 0], panel_faces[:, 1], panel_faces[:, 2],
                                  tri_ke=[material["mu"]] * count, tri_ka=[material["lambda"]] * count,
                                  tri_kd=[0.0] * count, tri_drag=[0.0] * count, tri_lift=[0.0] * count)
            if builder.tri_count - before != count:
                raise RuntimeError(f"{self.name}: a degenerate triangle on panel {panel} left out by Newton")
            order.append(chosen)
        order = np.concatenate(order)
        self.flat = laying.edge_lengths(copies, faces[order])  # each triangle's lengths on its flat panel, as added
        if placed is not None:
            self.points = np.asarray(placed, dtype=float)
        else:
            self.points = laying.laid_out(self.points, skin, float(spec.get("layer_m", 0.0)), clear, inside)
            left = np.flatnonzero(inside(self.points))
            if len(left):
                raise RuntimeError(f"{self.name}: {len(left)} of its box mesh's points still inside the body as laid")
        for index, point in enumerate(self.points):
            builder.particle_q[self.first + index] = wp.vec3(*point)
        self.laid = laying.edge_lengths(self.points, welded[order])
        sides = bending_edges(welded)
        corners = np.array([corner for corner, _ in sides], dtype=np.int64) + self.first
        builder.add_edges(corners[:, 0].tolist(), corners[:, 1].tolist(), corners[:, 2].tolist(),
                          corners[:, 3].tolist(), rest=[0.0] * len(sides),
                          edge_ke=[material["bending"]] * len(sides), edge_kd=[0.0] * len(sides))
        self.edges = len(sides)


def welded_faces(spec):
    """A garment's triangles on its box mesh's points (as `Garment` builds them)."""
    record = np.load(spec["record"])
    return record["box"][record["faces"]]


def sewn_cloth(points, faces):
    """The garments sewn before a stage as one cloth: (points, faces), or None when there are none."""
    if not points:
        return None
    firsts = np.cumsum([0] + [len(each) for each in points[:-1]])
    return (np.concatenate(points), np.concatenate([each + first for each, first in zip(faces, firsts)]))


class Outfit:
    """The body and every garment in one Newton model, VBD over it."""

    def __init__(self, job, body, placed=None):
        """`placed`: {garment name: its points sewn in an earlier stage}; the other garments' box meshes are laid
        `laying.laid_out`."""
        placed = placed or {}
        builder = newton.ModelBuilder(up_axis=newton.Axis.Y, gravity=(0.0, 0.0, 0.0))
        self.frames, self.bind = body["frames"].astype(np.float32), body["bind"].astype(np.float32)
        self.faces = body["faces"].astype(np.int32)
        contact = job["contact"]
        shape = newton.ModelBuilder.ShapeConfig(mu=contact["mu"], ke=contact["ke"], kd=contact["kd"],
                                               margin=contact["margin"])
        self.body = newton.Mesh(self.bind, self.faces.ravel())
        builder.add_shape_mesh(body=-1, mesh=self.body, cfg=shape)
        inside = body_inside(self.bind, self.faces)
        self.garments = [Garment(builder, spec, self.bind.astype(float), inside,
                                 spec["material"]["radius"] + contact["margin"], placed.get(spec["name"]))
                         for spec in job["garments"]]
        builder.color(include_bending=True)
        self.model = builder.finalize(device=job["device"])
        self.laid = np.concatenate([garment.laid for garment in self.garments])
        self.flat = np.concatenate([garment.flat for garment in self.garments])
        self.share = None
        self.model.soft_contact_mu, self.model.soft_contact_ke = contact["mu"], contact["ke"]
        self.model.soft_contact_kd = contact["kd"]
        self.mesh = self.body.mesh  # the wp.Mesh the model collides with, its points moved each substep
        self.pipeline = newton.CollisionPipeline(self.model, soft_contact_gap=contact["margin"])
        self.contacts = self.pipeline.contacts()
        self.solver = newton.solvers.SolverVBD(
            self.model, iterations=job["iterations"], particle_enable_self_contact=True,
            particle_self_contact_margin=job["self"]["margin"], particle_self_contact_gap=job["self"]["gap"])
        self.now, self.next = self.model.state(), self.model.state()
        self.control = self.model.control()
        self.rate, self.substeps = job["rate"], job["substeps"]
        self.holds = [(wp.array(points.astype(np.int32), dtype=wp.int32), axis, wp.array(levels, dtype=wp.float32),
                       side) for garment in self.garments for points, axis, levels, side in garment.holds]
        self.frames_card = wp.array(self.frames.reshape(-1, 3), dtype=wp.vec3)
        self.held = [self.worn_on(garment) for garment in self.garments if len(garment.held)]
        self.neck = np.asarray(job.get("neck", []), dtype=np.int64)
        self.belt = self.belted(job.get("belt"))
        self.holding = HOLDING[job.get("holds_until", "sewn")]

    def rested(self, share):
        """Every triangle's rest `share` of the way from as laid to its flat panel (`laying.rest_lengths`), set on the
        model VBD reads each substep. The flat rest is the panel's own lengths: Newton's builder reads a triangle's
        rest off its points, and a box point with two copies on one panel (a panel sewn to itself) has one place
        there, so woman_stair_modern's jeans had 135 triangles resting up to 2.7 times their panel (2026-11-25)."""
        share = min(max(float(share), 0.0), 1.0)
        if share == self.share:
            return
        poses, areas = laying.rest_shapes(laying.rest_lengths(self.laid, self.flat, share))
        self.model.tri_poses.assign(poses.astype(np.float32))
        self.model.tri_areas.assign(areas.astype(np.float32))
        self.share = share

    def worn_on(self, garment):
        """Where each held point is worn: the body's nearest surface point to it at the bind, out by the cloth's
        radius along that triangle's normal, as arrays on the card: (particles, the triangles' corners, barycentric
        weights, the box mesh's start, the radius)."""
        mesh = wp.Mesh(points=wp.array(self.bind, dtype=wp.vec3), indices=wp.array(self.faces.ravel(), dtype=wp.int32))
        count = len(garment.held)
        faces, uvs = wp.zeros(count, dtype=wp.int32), wp.zeros(count, dtype=wp.vec2)
        wp.launch(nearest, dim=count, inputs=[mesh.id, wp.array(garment.points[garment.held], dtype=wp.vec3), 1.0,
                                              faces, uvs])
        faces, uvs = faces.numpy(), uvs.numpy()
        if (faces < 0).any():
            raise RuntimeError(f"{garment.name}: a held point is over a metre off the body")
        weights = np.stack([1.0 - uvs[:, 0] - uvs[:, 1], uvs[:, 0], uvs[:, 1]], axis=1)
        radius = float(self.model.particle_radius.numpy()[garment.first])
        return (wp.array((garment.first + garment.held).astype(np.int32), dtype=wp.int32),
                wp.array(self.faces[faces].astype(np.int32), dtype=wp.vec3i), wp.array(weights, dtype=wp.vec3),
                wp.array(garment.points[garment.held], dtype=wp.vec3), radius)

    def belted(self, belt):
        """The belt on the card (job `belt`: {"on": the garment whose waistband it is worn on, "under_top",
        "width", "reach" (m), "limits": {garment: how far off the skin its cloth may stand there}, "outside":
        {garment over the belt: how near the skin it may come there}}): (particles, their limits, their least, each
        body triangle under the band 1 else 0), or None with no belt. The band is the skin from
        `under_top` under the waistband's top, where its held points are worn at the bind, down `width`, no further
        round than `reach` past the waistband's widest (as the belt is laid, accessories.in_band)."""
        if not belt:
            return None
        on = next(number for number, garment in enumerate(self.garments) if garment.name == belt["on"])
        _, corners, weights, _, _ = self.held[[garment.name for garment in self.garments
                                               if len(garment.held)].index(belt["on"])]
        ring = np.einsum("pc,pcd->pd", weights.numpy(), self.bind[corners.numpy()])
        centre = ring.mean(axis=0)
        top = float(ring[:, 1].max())
        reach = np.hypot(self.bind[:, 0] - centre[0], self.bind[:, 2] - centre[2])
        widest = float(np.hypot(ring[:, 0] - centre[0], ring[:, 2] - centre[2]).max())
        under = ((self.bind[:, 1] < top - belt["under_top"]) & (self.bind[:, 1] > top - belt["under_top"]
                                                                  - belt["width"]) & (reach < widest + belt["reach"]))
        banded = under[self.faces].all(axis=1).astype(np.int32)
        print(f"belt: on {self.garments[on].name}, its top {top:.3f} m, {int(banded.sum())} skin triangles under it",
              flush=True)
        particles, limits, least = [], [], []
        outside = belt.get("outside", {})
        for garment in self.garments:
            if garment.name in belt["limits"] or garment.name in outside:
                particles.append(garment.first + np.arange(garment.count))
                limits.append(np.full(garment.count, belt["limits"].get(garment.name, np.inf)))
                least.append(np.full(garment.count, outside.get(garment.name, -np.inf)))
        return (wp.array(np.concatenate(particles).astype(np.int32), dtype=wp.int32),
                wp.array(np.concatenate(limits).astype(np.float32), dtype=wp.float32),
                wp.array(np.concatenate(least).astype(np.float32), dtype=wp.float32),
                wp.array(banded, dtype=wp.int32))

    def moved(self, frame, axis):
        """How far the body's neck has moved along `axis` from the bind by `frame` (m): a hold's level moves with it."""
        if not len(self.neck):
            return 0.0
        return float(self.frames[frame][self.neck, axis].mean() - self.bind[self.neck, axis].mean())

    def step(self, frame, share, carry, sewing, holding):
        """One substep ending `share` of the way from `frame` to the next: the body there (its mesh's points and
        velocities, refitted), the held points carried `carry` of the way to the skin, then VBD; the drawn points
        drawn while `holding`, the speeds capped while `sewing`."""
        after = min(frame + 1, len(self.frames) - 1)
        wp.launch(skin_at, dim=len(self.bind), inputs=[self.frames_card, len(self.bind), frame, after, share,
                                                        self.rate, self.mesh.points, self.mesh.velocities])
        self.mesh.refit()
        for particles, corners, weights, start, radius in self.held:
            wp.launch(held_on, dim=len(particles), inputs=[particles, corners, weights, start, radius, carry,
                                                           self.mesh.points, self.rate * self.substeps,
                                                           self.now.particle_q, self.now.particle_qd])
        self.now.clear_forces()
        self.pipeline.collide(self.now, self.contacts)
        self.solver.step(self.now, self.next, self.control, self.contacts, 1.0 / (self.rate * self.substeps))
        self.now, self.next = self.next, self.now
        if sewing:
            wp.launch(capped, dim=self.model.particle_count, inputs=[self.now.particle_qd, SEW_SPEED])
        if self.belt is not None and not sewing:
            particles, limits, least, banded = self.belt
            wp.launch(cinched, dim=len(particles), inputs=[self.mesh.id, particles, limits, least, banded, BELT_REACH,
                                                            BELT_SHARE, self.now.particle_q])
        if holding:
            after = min(frame + 1, len(self.frames) - 1) if share > 0.0 else frame
            for particles, axis, levels, side in self.holds:
                wp.launch(drawn, dim=len(particles), inputs=[particles, axis, levels, self.moved(after, axis), side,
                                                             HOLD_SHARE, self.now.particle_q])

    def frame(self, frame, carry=1.0, sewing=False, moving=True, holding=False):
        """Every substep from `frame` to the next (not `moving`: the body held at `frame`)."""
        for number in range(self.substeps):
            share = (number + 1) / self.substeps * moving
            self.step(frame, share, carry, sewing, holding or sewing)

    def points(self, garment):
        return self.now.particle_q.numpy()[garment.first:garment.first + garment.count].copy()

    def inside(self, frame, points):
        """Each point's signed distance to the body at `frame` (m, negative inside)."""
        mesh = wp.Mesh(points=wp.array(self.frames[frame], dtype=wp.vec3),
                       indices=wp.array(self.faces.ravel(), dtype=wp.int32), support_winding_number=True)
        found = wp.zeros(len(points), dtype=wp.float32)
        wp.launch(signed_distance, dim=len(points), inputs=[mesh.id, wp.array(points, dtype=wp.vec3), 0.1, found])
        return found.numpy()


def sewn(outfit, job):
    """The garments sewn and settled on the body held at its bind: gravity off for the first fifth, each triangle's
    rest going over from as laid to its flat panel's in it (`Outfit.rested`), the held points carried onto the skin
    over the first half; the wall seconds."""
    began, frames = time.monotonic(), int(job["sew_seconds"] * job["rate"])
    for count in range(frames):
        outfit.rested(count / (frames // 5))
        if count == frames // 5:
            outfit.model.set_gravity((0.0, -job["gravity"], 0.0))
        outfit.frame(0, carry=min(1.0, count / (frames / 2.0)), sewing=True, moving=False)
        if count % 30 == 29:
            if not np.isfinite(outfit.now.particle_q.numpy()).all():
                raise RuntimeError(f"the cloth blew up sewing, frame {count}")
            print(f"sewing: frame {count + 1} of {frames}, {time.monotonic() - began:.0f} s", flush=True)
    return time.monotonic() - began


def worn(outfit, job, clip_start):
    """The turn from the bind to the clip's first frame, `still_seconds` standing, then the clip: each garment's
    points at each clip frame's end, and the clip's wall seconds."""
    for frame in range(clip_start):
        outfit.frame(frame, holding=outfit.holding >= HOLDING["turned"])
    for _ in range(int(job["still_seconds"] * job["rate"])):
        outfit.frame(clip_start, moving=False, holding=outfit.holding >= HOLDING["turned"])
    found = {garment.name: [outfit.points(garment)] for garment in outfit.garments}
    wp.synchronize()
    began = time.monotonic()
    for frame in range(clip_start, len(outfit.frames) - 1):
        outfit.frame(frame, holding=outfit.holding >= HOLDING["worn"])
        for garment in outfit.garments:
            found[garment.name].append(outfit.points(garment))
        if not np.isfinite(outfit.now.particle_q.numpy()).all():
            blown = [name for name, frames in found.items() if not np.isfinite(frames[-1]).all()]
            np.savez_compressed(BLOWN, **{name: np.asarray(frames[:-1]) for name, frames in found.items()})
            raise RuntimeError(f"the cloth blew up at clip frame {frame - clip_start}: {', '.join(blown)} (the frames "
                               f"before it in {BLOWN})")
    wp.synchronize()
    return {name: np.asarray(value) for name, value in found.items()}, time.monotonic() - began


def sewn_in_layers(job, body):
    """The outfit sewn a layer at a time, innermost first (each garment's `layer_m`): a layer over sewn cloth is
    first sewn alone on the body, then `laid_over` that cloth, then sewn with it in place (all laid at once, a
    trousers' waistband carried in to the skin from its box passed through the jacket's hem over it, 2026-11-24).
    The last stage's outfit (the belt in it) and the wall seconds of every stage."""
    layers = sorted({float(spec.get("layer_m", 0.0)) for spec in job["garments"]})
    placed, seconds = {}, 0.0
    skin = body["bind"].astype(float)
    for number, layer in enumerate(layers):
        last = number == len(layers) - 1
        stage = {key: value for key, value in job.items() if key != "belt" or last}
        new = [spec for spec in job["garments"] if float(spec.get("layer_m", 0.0)) == layer]
        if placed:
            under = [spec for spec in job["garments"] if spec["name"] in placed]
            alone = Outfit({key: value for key, value in stage.items() if key != "belt"} | {"garments": new}, body)
            print(f"sewing layer {number + 1} of {len(layers)} alone: {', '.join(spec['name'] for spec in new)}",
                  flush=True)
            seconds += sewn(alone, job)
            cloth = sewn_cloth([placed[spec["name"]] for spec in under], [welded_faces(spec) for spec in under])
            clear = max(layer - max(float(spec.get("layer_m", 0.0)) for spec in under), 2.0 * job["self"]["gap"])
            for garment, spec in zip(alone.garments, new):
                placed[spec["name"]] = laid_over(alone.points(garment), garment.faces, skin, body["faces"], cloth,
                                                 clear)
        stage["garments"] = [spec for spec in job["garments"] if float(spec.get("layer_m", 0.0)) <= layer]
        outfit = Outfit(stage, body, placed)
        print(f"sewing layer {number + 1} of {len(layers)}: {', '.join(spec['name'] for spec in stage['garments'])}",
              flush=True)
        seconds += sewn(outfit, job)
        placed = {garment.name: outfit.points(garment) for garment in outfit.garments}
    return outfit, seconds


def run(job_path, out_path):
    global BLOWN
    BLOWN = out_path.with_suffix(".blown.npz")
    job = json.loads(job_path.read_text())
    body = dict(np.load(job["body"]))
    wp.init()
    with wp.ScopedDevice(job["device"]):
        outfit, sew_seconds = sewn_in_layers(job, body)
        sewn_points = {garment.name: outfit.points(garment) for garment in outfit.garments}
        clip_start = int(body["clip_start"])
        found, clip_seconds = worn(outfit, job, clip_start)
        out = {"engine": np.array(f"newton {newton.__version__} SolverVBD on warp {wp.__version__} "
                                  f"({job['iterations']} iterations, {job['substeps']} substeps a frame, not "
                                  f"run-to-run deterministic) on {wp.get_device()}"),
               "seconds/sew": np.array(sew_seconds), "seconds/clip": np.array(clip_seconds)}
        for garment in outfit.garments:
            out[garment.name] = found[garment.name]
            out[f"{garment.name}/sewn"] = sewn_points[garment.name]
            out[f"{garment.name}/faces"] = garment.faces
            out[f"inside/{garment.name}"] = np.array([outfit.inside(clip_start + number, points) for number, points
                                                      in enumerate(found[garment.name])])
        np.savez_compressed(out_path, **out)
    print(json.dumps({"sew seconds": round(sew_seconds, 1), "clip seconds": round(clip_seconds, 1),
                      "clip frames": len(found[outfit.garments[0].name])}), flush=True)


if __name__ == "__main__":
    run(*arguments())
