"""A garment's sim mesh (#223, round 2 of the cloth; cloth.py's step 3b): the shell's own triangles are no cloth.
TRELLIS.2's garment surface is a thin two-sided sheet cut by paint (its walls 3 to 4 mm apart on the median, a third to
two fifths of a garment's faces an inner wall), with slivers (round 1's jacket held a 2.7e-11 m^2 triangle of aspect
27,000 whose point went non-finite in the hang before the first frame), duplicate faces, edges shared by three or more
faces and hundreds of loose specks. VBD on it blew up; taking its outer wall alone left a surface of 28 pieces with
rims metres long. So the cloth is laid over the body instead, and the shell's surface rides it.

1. `laid_over`: the collision body (a clean closed SOMA surface) split to under EDGE_M, each point sent out along its
   normal to the garment's first face within REACH_M whose joint is on the point's own limb or next to its joint
   (`near_joints`: an armpit's ray never lands on the sleeve beside it, a hip's never on the hand hanging by it, a
   thigh's never on the other leg; a trunk point looking up, UP_LEAST, lands on the shoulder's sleeve, and an arm's
   point on trunk-weighted cloth within ARM_CLOSE_M, a sleeve's inner wall fused to the side). How far each
   point goes out is smoothed over its landed neighbours (SMOOTH_ROUNDS: the sim mesh is the garment's broad shape,
   its walls and folds ride on it as the render surface), and a body face whose three points all land is the
   garment's. The head, hands and feet lay nothing (UNLAID): a hem
   ends at the ankle, a cuff at the wrist, the collar at the neck.
2. `cleaned`: the laid faces with every face past two on an edge dropped, pieces under PIECE_LEAST_M2 dropped, holes
   with a rim under HOLE_M closed (a fan round the rim's middle), the faces wound one way: a manifold mesh whose rims
   are the garment's openings (the waist, the hems, the collar, the cuffs, the open front).
3. `remeshed`: the rims resampled to EDGE_M along themselves (`rims_split`, `rims_merged`: Botsch and Kobbelt's
   remesher keeps every rim point where it stands), then `cloth_remesh.py` in its own Python (gpytoolbox's
   remesh_botsch, MIT; kept out of the repo's environment as MediaPipe is) makes an even mesh of EDGE_M edges over the
   surface, reprojected onto it; a triangle left with a corner under ANGLE_LEAST has its shortest edge collapsed
   (`slivers_collapsed`: the remesher left a 1e-19 m^2 needle, 2026-11-26).
4. `bound` and `displaced`: each point of the detailed render surface (the garment as the shell has it, both walls and
   its specks) bound to its sim mesh's nearest triangle at its barycentric place, and moved off its own skinned place
   by as much as the cloth there stands off its target, so its folds and paint ride along, the rest shape comes back
   exactly and a cloth on its targets is drawn as the skinned person is (round 4, 2026-11-27: carried in a frame of
   the triangle's normal, a puffer standing up to 10 cm off its sim mesh was drawn 17 mm rough at its 95th
   percentile against the skinned shell, lumpy and dark beside it); `blended` carries any per-point value (skin
   weights, riding) from the shell's garment onto the sim mesh.
"""
import json
import pathlib
import subprocess
import tempfile

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = pathlib.Path(__file__).resolve().parent
EDGE_M = 0.012  # the sim mesh's edge (the brief's 1 to 1.5 cm)
REACH_M = 0.25  # a body point reaches its garment this far out at most (the puffer stands 10 cm off at its 90th)
UP_LEAST = 0.5  # a trunk point's normal this far up (cosine) looks over the shoulder
SMOOTH_ROUNDS = 4  # rounds the reach is averaged over landed neighbours (more pulls the sim mesh inside a
# flare: 10 rounds left 18% of the jeans' drawn points over 3 cm off it, 4 rounds 12%)
UNLAID = ("Head", "HeadEnd", "LeftHand", "RightHand", "LeftFoot", "LeftToeBase", "LeftToeEnd", "RightFoot",
          "RightToeBase", "RightToeEnd")  # body points that never lay a garment (a hem ends at the ankle)
ARM_CLOSE_M = 0.04  # an arm's point lands on cloth weighted to the trunk this near (a fused sleeve's inner wall)
ANGLE_LEAST = 5.0  # degrees: a remeshed triangle with a corner under this has its shortest edge collapsed
AREA_LEAST = 1e-9  # m^2: a sliver
PIECE_LEAST_M2 = 0.002  # a piece under 20 cm^2 is a speck, not cloth
HOLE_M = 0.12  # a rim shorter than this is a hole a missed ray left, never an opening (a cuff's is about 25 cm)
REMESH = ["uv", "run", "--no-project", "-p", "3.12", "--with", "gpytoolbox==0.3.8", "python"]
REMESH_ROUNDS = 10  # remesh_botsch's rounds of split, collapse, flip and smooth
REMESH_SECONDS = 300  # a garment remeshes in seconds; past this it has gone wrong
REMESH_BYTES = 4 << 30  # and never takes more memory than this (a bad mesh grew it until the kernel killed it)


def limbs_of(names):
    """Each joint's limb: "trunk" (no side in its name: hips, spine, chest, neck, head), else its side and "arm" (a
    shoulder, arm or hand) or "leg"."""
    found = []
    for name in names:
        side = next((side for side in ("Left", "Right") if name.startswith(side)), None)
        limb = "arm" if any(part in name for part in ("Shoulder", "Arm", "Hand")) else "leg"
        found.append("trunk" if side is None else f"{side}{limb}")
    return np.array(found)


def near_joints(names, parents):
    """(joints x joints) bool: which garment joint a body point's ray may land on, by their joints: the same limb, a
    joint's parent or child (the shoulder over the chest, the hips over a thigh)."""
    limbs = limbs_of(names)
    found = limbs[:, None] == limbs[None, :]
    for child, parent in enumerate(parents):
        if 0 <= parent < len(parents):
            found[child, parent] = found[parent, child] = True
    return found


def arm_over_trunk(names):
    """(joints x joints) bool: a trunk joint and an arm's (allowed on a ray looking up, over the shoulder, UP_LEAST)."""
    limbs = limbs_of(names)
    arm, trunk = np.char.endswith(limbs.astype(str), "arm"), limbs == "trunk"
    return (trunk[:, None] & arm[None, :]) | (arm[:, None] & trunk[None, :])


def laid_over(body, body_joint, shell, garment, garment_joint, skeleton, edge=EDGE_M):
    """The body (points, faces) split to under `edge` and laid out onto the garment (module docstring step 1):
    (points, faces) of the laid faces. `body_joint` is each body point's strongest joint, `garment` the shell's
    (points, faces) face numbers of the garment, `garment_joint` each of their strongest joint, `skeleton` (joint
    names, parents)."""
    points, faces, origin = trimesh.remesh.subdivide_to_size(body[0], body[1], max_edge=edge, return_index=True)
    # each split point's joint: its first original face's corner nearest it
    corner_points = body[0][body[1][origin]]
    nearest = np.linalg.norm(corner_points[:, None] - points[faces][:, :, None], axis=3).argmin(2)
    joint = np.zeros(len(points), int)
    joint[faces.ravel()] = body_joint[body[1][origin[:, None], nearest]].ravel()
    mesh = trimesh.Trimesh(points, faces, process=False)
    normals = mesh.vertex_normals
    target = trimesh.Trimesh(shell[0], shell[1][garment], process=False)
    hit_at, ray, hit = target.ray.intersects_location(points, normals, multiple_hits=True)
    distance = np.einsum("pd,pd->p", hit_at - points[ray], normals[ray])
    pair = joint[ray], garment_joint[hit]
    across = arm_over_trunk(skeleton[0])[pair]
    allowed = (near_joints(*skeleton)[pair] | (across & (normals[ray, 1] > UP_LEAST))
               | (across & np.char.endswith(limbs_of(skeleton[0])[joint[ray]].astype(str), "arm")
                  & (distance < ARM_CLOSE_M)))
    unlaid = np.isin(np.asarray(skeleton[0])[joint[ray]], UNLAID)
    good = (distance > 0) & (distance < REACH_M) & allowed & ~unlaid
    reach, landed = np.zeros(len(points)), np.zeros(len(points), bool)
    order = np.lexsort((distance[good], ray[good]))
    first = np.unique(ray[good][order], return_index=True)[1]
    rows = ray[good][order][first]
    reach[rows], landed[rows] = distance[good][order][first], True
    laid = points + smoothed(reach, landed, faces)[:, None] * normals
    return laid, faces[landed[faces].all(1)]


def smoothed(values, landed, faces, rounds=SMOOTH_ROUNDS):
    """Per-point values averaged with their landed edge neighbours (`landed` ones only), `rounds` times."""
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges = edges[landed[edges].all(1)]
    graph = coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(len(values),) * 2).tocsr()
    graph = ((graph + graph.T) > 0).astype(float)
    degree = np.asarray(graph.sum(1)).ravel()
    for _ in range(rounds):
        values = np.where(landed, (values + graph @ values) / (1.0 + degree), values)
    return values


def areas(points, faces):
    return 0.5 * np.linalg.norm(np.cross(points[faces[:, 1]] - points[faces[:, 0]],
                                         points[faces[:, 2]] - points[faces[:, 0]]), axis=1)


def manifold_edges(points, faces):
    """`faces` with duplicates dropped and, on an edge three or more faces share, the smallest past two dropped."""
    _, first = np.unique(np.sort(faces, axis=1), axis=0, return_index=True)
    faces = faces[np.sort(first)]
    order = np.argsort(-areas(points, faces))
    faces = faces[order]
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, edge = np.unique(edges, axis=0, return_inverse=True)
    edge = edge.ravel()
    keep = np.ones(len(faces), bool)
    seen = np.zeros(edge.max() + 1, int)
    for face in range(len(faces)):  # largest first: a face is kept while each of its edges has fewer than two kept
        mine = edge[[face, face + len(faces), face + 2 * len(faces)]]
        if (seen[mine] >= 2).any():
            keep[face] = False
            continue
        seen[mine] += 1
    return faces[keep]


def pieces_of(faces, count):
    """Each face's piece (faces joined through an edge)."""
    mesh = trimesh.Trimesh(np.zeros((count, 3)), faces, process=False)
    pairs = mesh.face_adjacency
    graph = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(faces), len(faces)))
    return connected_components(graph, directed=False)[1]


def rims(faces):
    """The mesh's rims: each a list of point numbers in order round it (edges used by one face, walked)."""
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    keys = np.sort(edges, axis=1)
    _, inverse, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    single = edges[counts[inverse.ravel()] == 1]
    following = {}
    for start, end in single:
        following.setdefault(int(start), []).append(int(end))
    found, used = [], set()
    for start, end in single:
        if (int(start), int(end)) in used:
            continue
        loop, here = [int(start)], int(end)
        used.add((int(start), int(end)))
        while here != loop[0] and len(loop) <= len(single):
            loop.append(here)
            step = next((after for after in following.get(here, []) if (here, after) not in used), None)
            if step is None:
                break
            used.add((here, step))
            here = step
        found.append(loop)
    return found


def holes_closed(points, faces):
    """Each rim shorter than HOLE_M closed by a fan round its middle: (points, faces)."""
    points, added = list(points), []
    for loop in rims(faces):
        ring = np.asarray(points)[loop]
        length = np.linalg.norm(ring - np.roll(ring, -1, axis=0), axis=1).sum()
        if len(loop) < 3 or length >= HOLE_M:
            continue
        middle = len(points)
        points.append(ring.mean(0))
        # a rim walked along its faces' own edges: the fan runs the other way round, so it winds as they do
        added.extend([[loop[(index + 1) % len(loop)], loop[index], middle] for index in range(len(loop))])
    if not added:
        return np.asarray(points), faces
    return np.asarray(points), np.concatenate([faces, np.asarray(added)])


def cleaned(points, faces):
    """A garment's laid faces made a manifold mesh (module docstring step 2): (points, faces), unused points
    dropped."""
    faces = faces[areas(points, faces) > AREA_LEAST]
    faces = faces[(faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])]
    faces = manifold_edges(points, faces)
    piece = pieces_of(faces, len(points))
    piece_area = np.bincount(piece, weights=areas(points, faces))
    faces = faces[piece_area[piece] >= PIECE_LEAST_M2]
    points, faces = holes_closed(points, faces)
    faces = manifold_edges(points, faces)
    return tidy(points, faces)


def fans_split(points, faces):
    """A point two fans of faces share only by that point (a bow tie) made one point a fan: (points, faces)."""
    corners = np.column_stack([faces.ravel(), np.repeat(np.arange(len(faces)), 3)])  # (point, face) per corner
    node = {(int(point), int(face)): index for index, (point, face) in enumerate(corners)}
    links = []
    mesh = trimesh.Trimesh(np.zeros((len(points), 3)), faces, process=False)
    for (one, other), edge in zip(mesh.face_adjacency, mesh.face_adjacency_edges):
        for point in edge:
            links.append((node[(int(point), int(one))], node[(int(point), int(other))]))
    links = np.asarray(links, int).reshape(-1, 2)
    graph = coo_matrix((np.ones(len(links)), (links[:, 0], links[:, 1])), shape=(len(corners),) * 2)
    fan = connected_components(graph, directed=False)[1]
    pairs = np.unique(np.column_stack([corners[:, 0], fan]), axis=0)
    first = np.unique(pairs[:, 0], return_index=True)[1]
    extra = np.setdiff1d(np.arange(len(pairs)), first)
    number = {(int(point), int(piece)): int(point) for point, piece in pairs[first]}
    points = list(points)
    for point, piece in pairs[extra]:
        number[(int(point), int(piece))] = len(points)
        points.append(points[point])
    faces = np.array([number[(int(point), int(piece))] for point, piece in zip(corners[:, 0], fan)]).reshape(-1, 3)
    return np.asarray(points), faces


def tidy(points, faces):
    """Bow ties split, unused points dropped and every piece's faces wound one way (the shell's are wound either
    way)."""
    points, faces = fans_split(points, faces)
    mesh = trimesh.Trimesh(points, faces, process=False)
    mesh.remove_unreferenced_vertices()
    trimesh.repair.fix_winding(mesh)
    return np.asarray(mesh.vertices, float), np.asarray(mesh.faces, int)


def rims_split(points, faces, edge):
    """Each rim edge longer than `edge` split evenly along itself (its face fanned from its far corner): (points,
    faces)."""
    points, kept, added = list(points), [], []
    single = {}
    for loop in rims(faces):
        for index, start in enumerate(loop):
            single[(start, loop[(index + 1) % len(loop)])] = True
    for face in faces:
        pieces = None
        for corner in range(3):
            start, end, far = face[corner], face[(corner + 1) % 3], face[(corner + 2) % 3]
            if (start, end) not in single and (end, start) not in single:
                continue
            count = int(np.ceil(np.linalg.norm(points[end] - points[start]) / edge))
            if count > 1 and pieces is None:
                made = [start]
                for step in range(1, count):
                    made.append(len(points))
                    points.append(points[start] + (points[end] - points[start]) * step / count)
                made.append(end)
                pieces = [[made[index], made[index + 1], far] for index in range(count)]
        if pieces is None:
            kept.append(face)
        else:
            added.extend(pieces)
    return np.asarray(points), np.asarray(kept + added, int).reshape(-1, 3)


def rims_merged(points, faces, edge):
    """Each rim's points thinned to about `edge` apart along it (a point nearer than that to the last one kept is
    merged into it), the faces that closed up dropped: (points, faces)."""
    into = np.arange(len(points))
    for loop in rims(faces):
        last = loop[0]
        for point in loop[1:]:
            if np.linalg.norm(points[point] - points[last]) < 0.75 * edge:
                into[point] = last
            else:
                last = point
        # the loop's end against its start
        if into[loop[-1]] == loop[-1] and np.linalg.norm(points[loop[-1]] - points[loop[0]]) < 0.5 * edge:
            into[loop[-1]] = loop[0]
    while not np.array_equal(into, into[into]):
        into = into[into]
    faces = into[faces]
    faces = faces[(faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])]
    faces = manifold_edges(points, faces[areas(points, faces) > AREA_LEAST])
    return tidy(points, faces)


def remeshed(points, faces, edge=EDGE_M):
    """An even mesh of `edge` edges over (points, faces), its rims resampled along themselves (module docstring step
    3): (points, faces)."""
    points, faces = rims_merged(*rims_split(points, faces, edge), edge)
    with tempfile.TemporaryDirectory() as folder:
        given, made = pathlib.Path(folder) / "in.npz", pathlib.Path(folder) / "out.npz"
        np.savez(given, points=points, faces=faces)
        subprocess.run([*REMESH, str(HERE / "cloth_remesh.py"), str(given), str(made),
                        json.dumps({"edge": edge, "rounds": REMESH_ROUNDS})], check=True, capture_output=True,
                       timeout=REMESH_SECONDS, preexec_fn=memory_capped)
        found = np.load(made)
        return slivers_collapsed(found["points"].astype(float), found["faces"].astype(int))


def corner_angles(points, faces):
    """Each face's three corner angles (faces x 3, degrees)."""
    found = []
    for corner in range(3):
        one = points[faces[:, (corner + 1) % 3]] - points[faces[:, corner]]
        other = points[faces[:, (corner + 2) % 3]] - points[faces[:, corner]]
        cosine = np.einsum("ij,ij->i", one, other) / np.maximum(
            np.linalg.norm(one, axis=1) * np.linalg.norm(other, axis=1), 1e-30)
        found.append(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))
    return np.column_stack(found)


def slivers_collapsed(points, faces, least=ANGLE_LEAST, rounds=5):
    """Each face with a corner under `least` degrees has its shortest edge collapsed to its middle (the faces that
    closed up dropped, made manifold again), up to `rounds` times: (points, faces)."""
    points = points.copy()
    for _ in range(rounds):
        thin = np.flatnonzero(corner_angles(points, faces).min(1) < least)
        if not len(thin):
            break
        into = np.arange(len(points))
        for face in faces[thin]:
            lengths = [np.linalg.norm(points[face[(corner + 1) % 3]] - points[face[corner]]) for corner in range(3)]
            start, end = face[int(np.argmin(lengths))], face[(int(np.argmin(lengths)) + 1) % 3]
            if into[start] != start or into[end] != end:
                continue  # one collapse a point a round
            points[start] = (points[start] + points[end]) / 2.0
            into[end] = start
        faces = into[faces]
        faces = faces[(faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])]
        points, faces = tidy(points, manifold_edges(points, faces))
    return points, faces


def memory_capped():
    """The remesh's process held to REMESH_BYTES (it fails with MemoryError instead of the PC running out)."""
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (REMESH_BYTES, REMESH_BYTES))


def barycentric(points, triangles):
    """Each point's barycentric place on its triangle (points x 3)."""
    return trimesh.triangles.points_to_barycentric(triangles, points)


def blended(values, points, faces, at):
    """Per-point `values` of (points, faces) read at the places `at` (their nearest triangle's barycentric blend)."""
    mesh = trimesh.Trimesh(points, faces, process=False)
    nearest, _, triangle = trimesh.proximity.closest_point(mesh, at)
    weights = barycentric(nearest, mesh.triangles[triangle])
    return np.einsum("pk,pk...->p...", weights, values[faces[triangle]])


def bound(render, points, faces):
    """The render points bound to the sim mesh (points, faces) at rest: {triangle, weights} (each point's nearest
    triangle and its barycentric place there)."""
    mesh = trimesh.Trimesh(points, faces, process=False)
    nearest, _, triangle = trimesh.proximity.closest_point(mesh, render)
    return {"triangle": triangle, "weights": barycentric(nearest, mesh.triangles[triangle])}


def displaced(binding, positions, targets, faces):
    """How far the sim mesh at `positions` stands off its `targets` (both frames x points x 3) at each bound render
    point (frames x render x 3): the moves of its triangle's corners blended by its barycentric place."""
    moves = (positions - targets)[:, faces[binding["triangle"]]]
    return np.einsum("pk,fpkd->fpd", binding["weights"], moves)
