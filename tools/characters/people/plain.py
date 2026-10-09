"""Plain clothes and the small built parts that go with them (#112): the prologue's people.

Jackets, coats and trousers are GarmentCode drapes on the build, as the work suit is (the jacket
and coat are the work suit's design cut to a hip or knee length with no trousers, the trousers
its lower half cut to the shoe), and everything else is built on them by measuring the cloth:

- the jacket's stand collar, exactly the work suit's (`work_suit.collar`), and its front opening,
  a narrow raised strip like the work suit's zip line;
- buttons, pocket flaps and a pin, small plates and discs laid on the cloth;
- shoes, the work boot (`boots.py`) cut off below the ankle, under the trouser hem; tall boots,
  the work boot's shaft drawn up;
- caps: a crown standing on the head over the hair, a band, and a peak;
- glasses: two rims in front of the eyes, a bridge and two arms back to the ears;
- things held: a clipboard, a spare glove.

A jacket drapes alone on the body, so where it hangs over the trousers it is pushed out over
them. Every part carries its weights like the work suit's: cloth from the body under it, anything
lying on cloth from the cloth, anything hard from one joint.
"""
import boots
import drape
import fit
import numpy as np
import shapes
import skin
import trimesh
import work_suit
from scipy.spatial import cKDTree

# The front opening of a jacket: half its width, how proud of the cloth.
OPENING_HALF = 0.012
OPENING_PROUD = 0.002
# A button: radius, how proud, and how many points round it.
BUTTON_RADIUS = 0.0085
BUTTON_PROUD = 0.004
BUTTON_SIDES = 12
# Over the trousers, a jacket stays this far out.
OVER_TROUSERS = 0.006
# Trousers tucked into boots end this far below the boots' tops.
TUCKED_BELOW = 0.04
# Trousers over shoes end this far below the shoes' tops.
OVER_SHOES = 0.02
# A jacket's stand collar closes further at the front than the work suit's.
JACKET_COLLAR_GAP = 0.004
# A shoe is the boot cut this high over the floor (on the template; carried to the build).
SHOE_TOP = 0.085
# A cap's crown: how far above the brows its band starts, the band's height, the crown's height
# over the band, how much wider its top is, and the peak's reach and droop.
CAP_ABOVE_BROWS = 0.012
CAP_BAND = 0.028
CAP_CROWN = 0.045
CAP_TOP_FLARE = 0.028
CAP_PEAK = 0.062
CAP_PEAK_DROOP = 0.018
CAP_CLEAR = 0.006


def thin(folder):
    """A drape thinned, as the work suit's: trimesh, panels, limbs."""
    return work_suit.thin_cloth(folder)


def over_the_trousers(jacket, trousers, body):
    """The jacket's points pushed out of the trousers where it hangs over them, the move spread
    to the points round each so the hem stays smooth."""
    points = np.asarray(jacket.vertices).copy()
    closest, _, triangle = trimesh.proximity.closest_point(trousers, points)
    normal = trousers.face_normals[triangle]
    _, nearest = cKDTree(body.points).query(closest)
    flip = np.einsum("ij,ij->i", normal, closest - body.points[nearest]) < 0
    normal[flip] *= -1
    side = np.einsum("ij,ij->i", points - closest, normal)
    top = trousers.vertices[:, 1].max()
    push = np.where(points[:, 1] < top + 0.02, np.clip(OVER_TROUSERS - side, 0.0, 0.08), 0.0)
    moves = normal * push[:, None]
    edges = jacket.edges_unique
    for _ in range(4):
        total = moves.copy()
        count = np.ones(len(points))
        np.add.at(total, edges[:, 0], moves[edges[:, 1]])
        np.add.at(total, edges[:, 1], moves[edges[:, 0]])
        np.add.at(count, edges.ravel(), 1)
        smooth = total / count[:, None]
        longer = np.linalg.norm(smooth, axis=1) > np.linalg.norm(moves, axis=1)
        moves = np.where(longer[:, None], smooth, moves)
    print(f"jacket: {int((push > 0).sum())} points pushed out over the trousers")
    return trimesh.Trimesh(points + moves, jacket.faces, process=False)


def low_shoes(body):
    """Both shoes, left then right, as (points, faces): the work boot cut off below the ankle,
    open at the top, under the trouser hem."""

    left, right, faces = boots.fitted(body)
    height = float(fit.y(SHOE_TOP))
    cut = []
    for points, side_faces in ((left, faces), (right, faces[:, ::-1])):
        kept_points, kept_faces = trimesh.intersections.slice_faces_plane(
            points, side_faces, np.array([0.0, -1.0, 0.0]), np.array([0.0, height, 0.0]))[:2]
        kept = trimesh.Trimesh(kept_points, kept_faces, process=True)
        cut.append((np.asarray(kept.vertices), np.asarray(kept.faces)))
    return cut


def tall_boots(body, stretch):
    """Both boots with their shafts drawn up by `stretch` above the ankle."""
    left, right, faces = boots.fitted(body)
    ankle = float(fit.y(0.09))
    made = []
    for points, side_faces in ((left, faces), (right, faces[:, ::-1])):
        points = points.copy()
        above = points[:, 1] > ankle
        points[above, 1] = ankle + (points[above, 1] - ankle) * stretch
        made.append((points, side_faces))
    return made


def trousers(body, folder, shoes, into_boots=False, lines=None):
    """The trousers on the body, their legs gathered just outside the shoes and cut off just over
    them, or, `into_boots`, gathered over the boots' tops and cut off a little below them, as if
    tucked in: points, faces, weights."""
    mesh, _, limbs = thin(folder)
    faces = np.asarray(mesh.faces)
    before = np.asarray(mesh.vertices)
    points = before
    for side, (shoe_points, shoe_faces) in zip(("Left", "Right"), shoes):
        points = boots.lengthened(points, limbs, shoe_points, side)
        points = boots.gather(points, limbs, shoe_points, boots.Walls(shoe_points, shoe_faces), side)
    points = boots.smoothed_moves(before, points, faces)
    if lines is not None:
        lines["seams"] = stitched_lines(folder, before, points)
    # Cut off where it would pool on the floor: into boots a little below their tops, over shoes
    # just over them, so the hem covers the shoe's open top and nothing drags.
    top = min(shoe_points[:, 1].max() for shoe_points, _ in shoes)
    below = TUCKED_BELOW if into_boots else OVER_SHOES
    if lines is not None:
        points, faces, limbs = straight_hem(points, faces, limbs, float(fit.y(TAILORED_CUT)), top - below)
    else:
        kept = faces[(points[faces][:, :, 1] > top - below).any(axis=1)]
        used, renumbered = np.unique(kept, return_inverse=True)
        points, faces, limbs = points[used], renumbered.reshape(-1, 3), limbs[used]
    weights = skin.of_a_drape(points, faces, limbs, body)
    for side, (shoe_points, _) in zip(("Left", "Right"), shoes):
        shoe_weights = boots.weights(shoe_points, side, body)
        weights = boots.hem_follows_boot(points, weights, shoe_points, shoe_weights)
    return points, faces, weights


# A tailored trouser leg (the leader's) is cut clean at this height on the template, above the
# folds the drape piles up over the shoe, and hangs straight down from there to its hem.
TAILORED_CUT = 0.17
HEM_ROWS = 4


def straight_hem(points, faces, limbs, cut, hem):
    """The legs cut level at `cut` and each dropped straight down from its cut edge to `hem`, in
    HEM_ROWS rows: points, faces and limbs, the new points taking the limb of the edge point above
    them. What the drape heaped up below the cut is gone, so the hem is one clean line on the
    shoe."""
    sliced_points, sliced_faces = trimesh.intersections.slice_faces_plane(
        points, faces, np.array([0.0, 1.0, 0.0]), np.array([0.0, cut, 0.0]))[:2]
    mesh = trimesh.Trimesh(sliced_points, sliced_faces, process=True)
    sliced_points, sliced_faces = np.asarray(mesh.vertices), np.asarray(mesh.faces)
    _, nearest = cKDTree(points).query(sliced_points)
    sliced_limbs = limbs[nearest]
    directed = np.concatenate([sliced_faces[:, [0, 1]], sliced_faces[:, [1, 2]], sliced_faces[:, [2, 0]]])
    undirected = np.sort(directed, axis=1)
    _, inverse, counts = np.unique(undirected, axis=0, return_inverse=True, return_counts=True)
    open_edge = counts[inverse.ravel()] == 1
    on_the_cut = (np.abs(sliced_points[directed[:, 0], 1] - cut) < 1e-6) & (np.abs(sliced_points[directed[:, 1], 1] - cut) < 1e-6)
    edges = directed[open_edge & on_the_cut]
    ring = np.unique(edges)
    all_points, all_limbs, new_faces = [sliced_points], [sliced_limbs], [sliced_faces]
    previous = {index: index for index in ring}
    count = len(sliced_points)
    for row in range(1, HEM_ROWS + 1):
        height = cut + (hem - cut) * row / HEM_ROWS
        row_points = sliced_points[ring].copy()
        row_points[:, 1] = height
        current = {index: count + number for number, index in enumerate(ring)}
        count += len(ring)
        all_points.append(row_points)
        all_limbs.append(sliced_limbs[ring])
        for first, second in edges:
            # The open edge runs first -> second in its face, so the new band runs the other way.
            new_faces.append(np.array([[previous[second], previous[first], current[first]],
                                       [previous[second], current[first], current[second]]]))
        previous = current
    return np.vstack(all_points), np.vstack(new_faces), np.concatenate(all_limbs)


def jacket(body, folder, under=None):
    """A jacket or coat and its stand collar: {name: (points, faces, weights)}, and the numbers
    the rest of it is laid out by (the cloth as a mesh, the collar's front height)."""
    mesh, panels, limbs = thin(folder)
    thinned = np.asarray(mesh.vertices).copy()
    body_mesh = trimesh.Trimesh(body.points, body.faces, process=False)
    line = work_suit.collar_line(mesh, body_mesh)
    mesh = work_suit.tailored_neckline(mesh, body_mesh, line)
    if under is not None:
        mesh = over_the_trousers(mesh, under, body)
    angles, bottom = line[0], line[1]
    neck_front = bottom[np.argmin(np.abs(angles))] - work_suit.COLLAR_OVERLAP
    points, faces = np.asarray(mesh.vertices), np.asarray(mesh.faces)
    weights = skin.of_a_drape(points, faces, limbs, body)
    open_gap, work_suit.COLLAR_GAP = work_suit.COLLAR_GAP, JACKET_COLLAR_GAP
    collar_points, collar_faces = work_suit.collar(mesh, line)
    work_suit.COLLAR_GAP = open_gap
    shaped = {"cloth": (points, faces, weights),
              "collar": (collar_points, collar_faces, skin.averaged(
                  skin.from_the_body(collar_points, body), collar_faces, work_suit.COLLAR_SMOOTHING))}
    return shaped, {"mesh": mesh, "weights": weights, "neck_front": neck_front, "panels": panels,
                    "seams": stitched_lines(folder, thinned, points)}


# A seam's samples are this far apart along it.
SEAM_STEP = 0.0015


def stitched_lines(folder, thinned, moved):
    """Where the pattern's panels were sewn together, as points every SEAM_STEP along each seam,
    carried onto the thinned cloth after it was moved (`thinned` before, `moved` after): the
    drape's stitched points are its seams, exactly, where the thinned cloth only knows them to
    within a triangle."""
    points, faces, labels = drape.read_cloth(folder)
    stitch = np.array([label.startswith("stitch") for label in labels])
    edges = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
    edges = edges[stitch[edges].all(axis=1)]
    return carried_onto(along_edges(points, edges), thinned, moved)


def along_edges(points, edges):
    """Points every SEAM_STEP along each edge."""
    samples = [points[edges[:, 0]]]
    lengths = np.linalg.norm(points[edges[:, 1]] - points[edges[:, 0]], axis=1)
    for share in np.arange(SEAM_STEP, lengths.max(), SEAM_STEP):
        within = lengths > share
        fraction = (share / lengths[within])[:, None]
        samples.append(points[edges[within, 0]] * (1 - fraction) + points[edges[within, 1]] * fraction)
    return np.vstack(samples)


def carried_onto(samples, before, after):
    """Points moved as the cloth round them was moved: each by the mean move of its four nearest
    cloth points."""
    _, nearest = cKDTree(before).query(samples, k=4)
    return samples + (after - before)[nearest].mean(axis=1)


def open_edges(points, faces):
    """Points every SEAM_STEP along a mesh's open edges (a hem, a cuff, a collar's rim)."""
    edges, counts = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1),
                              axis=0, return_counts=True)
    return along_edges(points, edges[counts == 1])


def lying_on(points, cloth, cloth_weights):
    """Weights for something lying on the cloth: the cloth's at its middle, one set for all of
    it, so it moves as one piece."""
    middle = skin.at_the_nearest_point(points, np.asarray(cloth.vertices), cloth_weights).mean(axis=0)
    return np.tile(middle / middle.sum(), (len(points), 1))


def opening(made, low):
    """The jacket's front opening, a strip from `low` up to the collar: (points, faces, weights,
    each point's place across it)."""
    xs = np.array([-OPENING_HALF, -OPENING_HALF / 2, 0.0, OPENING_HALF / 2, OPENING_HALF])
    while not work_suit.all_on_the_cloth(made["mesh"], xs, low):
        low += 0.005
    ys = np.arange(low, made["neck_front"] - 0.002, work_suit.PLACKET_STEP)
    points, faces, across = work_suit.raised_patch(made["mesh"], xs, ys, OPENING_PROUD, work_suit.PLACKET_BRIDGE)
    weights = skin.at_the_nearest_point(points, np.asarray(made["mesh"].vertices), made["weights"])
    return points, faces, weights, across


def front_hit(mesh, x, y):
    """Where a ray straight back through (x, y) meets the cloth's front, and its normal there."""
    hits, normals = work_suit.cast(mesh, np.array([[x, y, 1.0]]), np.array([0.0, 0.0, -1.0]))
    normal = normals[0] if normals[0, 2] > 0 else -normals[0]
    return hits[0], normal


def disc(centre, normal, radius, proud, sides=BUTTON_SIDES):
    """A flat round button standing `proud` off a surface, its back sunk a little into it."""
    axes = shapes.frame(normal, [0.0, 1.0, 0.0] if abs(normal[1]) < 0.9 else [1.0, 0.0, 0.0])
    ring = np.array([[np.cos(angle), np.sin(angle)] for angle in
                     np.linspace(0, 2 * np.pi, sides, endpoint=False)]) * radius
    top = centre + normal * proud + ring[:, 0:1] * axes[:, 1] + ring[:, 1:2] * axes[:, 2]
    base = centre - normal * 0.001 + ring[:, 0:1] * axes[:, 1] + ring[:, 1:2] * axes[:, 2]
    middle = centre + normal * (proud * 1.15)
    points = np.vstack([top, base, middle[None]])
    faces = []
    for index in range(sides):
        following = (index + 1) % sides
        faces += [[2 * sides, index, following], [index, index + sides, following + sides],
                  [index, following + sides, following]]
    mesh = trimesh.Trimesh(points, np.array(faces), process=True)
    trimesh.repair.fix_normals(mesh)
    return np.asarray(mesh.vertices), np.asarray(mesh.faces)


def buttons(made, heights, x=0.0, radius=BUTTON_RADIUS):
    """Buttons down the front at these heights (on the build): one mesh, each on the cloth."""
    pieces = []
    for height in heights:
        hit, normal = front_hit(made["mesh"], x, height)
        pieces.append(disc(hit, normal, radius, BUTTON_PROUD))
    return joined(pieces)


def joined(pieces):
    points, faces, count = [], [], 0
    for piece_points, piece_faces in pieces:
        points.append(piece_points)
        faces.append(np.asarray(piece_faces) + count)
        count += len(piece_points)
    return np.vstack(points), np.vstack(faces)


def flaps(made, places, size, proud=0.004):
    """Pocket flaps: small plates on the cloth's front, each centred at an (x, y) on the build,
    `size` (width, height). One mesh."""
    pieces = []
    for x, y in places:
        xs = np.linspace(x - size[0] / 2, x + size[0] / 2, 8)
        ys = np.linspace(y - size[1] / 2, y + size[1] / 2, 4)
        points, faces, _ = work_suit.raised_patch(made["mesh"], xs, ys, proud)
        pieces.append((points, faces))
    return joined(pieces)


def shoulder_boards(made, body, length=0.11, width=0.045, proud=0.005):
    """A flat board on top of each shoulder, from the collar out along the shoulder."""
    pieces = []
    mesh = made["mesh"]
    for side in (1.0, -1.0):
        arm = body.joints["LeftArm" if side > 0 else "RightArm"]
        inner = np.array([side * 0.07 * float(fit.width_share(1.43)), arm[1] + 0.06, arm[2]])
        outer = np.array([arm[0] - side * 0.01, arm[1] + 0.035, arm[2]])
        along = np.linspace(0.0, 1.0, 8)
        across = np.linspace(-width / 2, width / 2, 4)
        grid = np.array([inner + (outer - inner) * a + np.array([0.0, 0.0, c]) for c in across for a in along])
        origins = grid + np.array([0.0, 0.3, 0.0])
        hits, normals = work_suit.cast(mesh, origins, np.array([0.0, -1.0, 0.0]))
        hits = np.where(np.isnan(hits), grid, hits)
        normals = np.where(np.isnan(normals), np.array([0.0, 1.0, 0.0]), normals)
        normals[normals[:, 1] < 0] *= -1
        rows, columns = len(across), len(along)
        points = np.concatenate([hits + normals * proud, hits - normals * 0.001])
        faces = work_suit.grid_faces(rows, columns) + work_suit.walls(work_suit.rim_of(rows, columns), rows * columns)
        piece = trimesh.Trimesh(points, np.array(faces), process=True)
        trimesh.repair.fix_normals(piece)
        pieces.append((np.asarray(piece.vertices), np.asarray(piece.faces)))
    return joined(pieces)


# ---- the head's own things: caps and glasses -------------------------------------------------

def head_outline(head_points, height, centre):
    """How far the head (with its hair) reaches from a vertical axis at `centre` (x, z), by
    angle, at one height: 64 radii."""
    band = head_points[np.abs(head_points[:, 1] - height) < 0.008]
    angle = np.arctan2(band[:, 0] - centre[0], band[:, 2] - centre[1])
    radius = np.hypot(band[:, 0] - centre[0], band[:, 2] - centre[1])
    bins = ((angle + np.pi) / (2 * np.pi) * 64).astype(int) % 64
    radii = np.zeros(64)
    np.maximum.at(radii, bins, radius)
    for _ in range(64):
        empty = radii == 0
        if not empty.any():
            break
        radii[empty] = np.maximum(np.roll(radii, 1), np.roll(radii, -1))[empty]
    return radii


def cap(head_points, brow_height, peaked=True):
    """A cap on the head, over the hair: {"cap_crown", "cap_band", "cap_peak": (points, faces)},
    in the head's place, to be fixed on the Head joint.

    Peaked (a uniform's or a driver's cap): a band round the head just over the brows, the crown
    pinched in over it and flaring out to a wide flat top plate, tipped up at the front, and a
    stiff peak. Soft (the technicians'): a rounded crown close over the head and a short peak."""
    base = brow_height + CAP_ABOVE_BROWS
    upper = head_points[head_points[:, 1] > base - 0.01]
    centre = np.array([upper[:, 0].mean(), upper[:, 2].mean()])
    angles = np.linspace(-np.pi, np.pi, 64, endpoint=False) + np.pi / 64
    reach = np.maximum(head_outline(head_points, base, centre), head_outline(head_points, base + 0.02, centre))
    reach = work_suit.circular_smooth(reach, 3) + CAP_CLEAR
    over_the_top = max(0.05, head_points[:, 1].max() + 0.004 - base)
    tilt = np.cos(angles)

    def ring(radius_add, height, lift=0.0):
        return np.stack([centre[0] + (reach + radius_add) * np.sin(angles), height + lift * tilt,
                         centre[1] + (reach + radius_add) * np.cos(angles)], axis=1)

    if peaked:
        profile = [(0.0, 0.0, 0.0), (0.0, CAP_BAND, 0.0), (-0.002, CAP_BAND + 0.008, 0.002),
                   (0.040, over_the_top - 0.004, 0.012), (0.046, over_the_top + 0.002, 0.014),
                   (0.030, over_the_top + 0.008, 0.014)]
        lid_height = over_the_top + 0.009
    else:
        dome = over_the_top + 0.012
        profile = [(0.0, 0.0, 0.0), (0.0, CAP_BAND * 0.7, 0.0)] + [
            (0.006 * np.sin(np.pi * share) - 0.03 * share ** 3, CAP_BAND * 0.7 + (dome - CAP_BAND * 0.7) * np.sin(np.pi / 2 * share), 0.0)
            for share in (0.3, 0.55, 0.75, 0.9)]
        lid_height = dome
    rings = [ring(add, base + height, lift) for add, height, lift in profile]
    lid_centre = np.array([centre[0], base + lid_height, centre[1]])
    if not peaked:
        lid_centre[1] = base + lid_height
    points = np.vstack(rings + [lid_centre[None]])
    faces = []
    for level in range(len(rings) - 1):
        for index in range(64):
            following = (index + 1) % 64
            here, there = level * 64, (level + 1) * 64
            faces += [[here + index, here + following, there + following],
                      [here + index, there + following, there + index]]
    lid = len(points) - 1
    last = (len(rings) - 1) * 64
    for index in range(64):
        faces.append([last + index, last + (index + 1) % 64, lid])
    crown = trimesh.Trimesh(points, np.array(faces), process=True)
    trimesh.repair.fix_normals(crown)
    band_height = CAP_BAND if peaked else CAP_BAND * 0.7
    band = trimesh.Trimesh(np.vstack([ring(0.002, base - 0.001), ring(0.002, base + band_height)]),
                           np.array([f for index in range(64) for f in (
                               [index, (index + 1) % 64, 64 + (index + 1) % 64],
                               [index, 64 + (index + 1) % 64, 64 + index])]), process=True)
    band = shell_of(band, 0.002)
    front = np.abs(angles) < np.radians(72)
    edge = ring(0.001, base)[front]
    order = np.argsort(angles[front])
    edge = edge[order]
    outward = np.stack([np.sin(angles[front][order]), np.zeros(len(edge)), np.cos(angles[front][order])], axis=1)
    reach_out = CAP_PEAK if peaked else CAP_PEAK * 0.75
    tip = edge + outward * reach_out
    tip[:, 1] -= CAP_PEAK_DROOP if peaked else CAP_PEAK_DROOP * 0.6
    curve = np.sin(np.linspace(0, np.pi, len(edge)))[:, None]
    tip = edge + (tip - edge) * (0.25 + 0.75 * curve)
    peak_points = np.vstack([edge, tip])
    count = len(edge)
    peak_faces = [f for index in range(count - 1) for f in (
        [index, index + 1, count + index + 1], [index, count + index + 1, count + index])]
    peak = shell_of(trimesh.Trimesh(peak_points, np.array(peak_faces), process=True), 0.003)
    return {"cap_crown": (np.asarray(crown.vertices), np.asarray(crown.faces)),
            "cap_band": (np.asarray(band.vertices), np.asarray(band.faces)),
            "cap_peak": (np.asarray(peak.vertices), np.asarray(peak.faces))}


def shell_of(surface, thickness):
    """An open surface given a thickness: two copies, offset along the normals, closed round the
    edge."""
    surface = trimesh.Trimesh(surface.vertices, surface.faces, process=True)
    normals = surface.vertex_normals
    count = len(surface.vertices)
    points = np.vstack([surface.vertices + normals * thickness / 2, surface.vertices - normals * thickness / 2])
    faces = [surface.faces, surface.faces[:, ::-1] + count]
    unique, counts = np.unique(np.sort(surface.edges, axis=1), axis=0, return_counts=True)
    for first, second in unique[counts == 1]:
        faces.append(np.array([[first, second, second + count], [first, second + count, first + count]]))
    solid = trimesh.Trimesh(points, np.concatenate(faces), process=True)
    trimesh.repair.fix_normals(solid)
    return solid


def rounded_rectangle(width, height, radius, per_corner=6):
    """A rectangle's outline with round corners, anticlockwise from the right: (n, 2)."""
    corners = [(width / 2 - radius, height / 2 - radius, 0.0), (-width / 2 + radius, height / 2 - radius, np.pi / 2),
               (-width / 2 + radius, -height / 2 + radius, np.pi), (width / 2 - radius, -height / 2 + radius, 1.5 * np.pi)]
    outline = []
    for x_centre, y_centre, start in corners:
        for angle in np.linspace(start, start + np.pi / 2, per_corner):
            outline.append([x_centre + radius * np.cos(angle), y_centre + radius * np.sin(angle)])
    return np.array(outline)


def round_cornered_frame(outer, bar, radius, depth):
    """A spectacle rim: a round-cornered rectangular ring `bar` wide and `depth` deep, back face at
    z=0. Points, faces."""
    rims = [rounded_rectangle(outer[0], outer[1], radius),
            rounded_rectangle(outer[0] - 2 * bar, outer[1] - 2 * bar, max(radius - bar, 0.001))]
    count = len(rims[0])
    layers = [np.column_stack([rims[0], np.zeros(count)]), np.column_stack([rims[0], np.full(count, depth)]),
              np.column_stack([rims[1], np.full(count, depth)]), np.column_stack([rims[1], np.zeros(count)])]
    points = np.concatenate(layers)
    faces = []
    for layer in range(4):
        following = (layer + 1) % 4
        for index in range(count):
            other = (index + 1) % count
            faces += [[layer * count + index, layer * count + other, following * count + other],
                      [layer * count + index, following * count + other, following * count + index]]
    return points, np.array(faces)


def glasses(eye_centres, skin_points, rim=(0.054, 0.036), bar=0.0032, depth=0.0035, radius=0.008):
    """Dark glasses (the leader's): a thin round-cornered rectangular rim round each eye a little in front of it,
    a bridge, and arms running back along the sides of the head, close to the skin, to the ears.
    One mesh, to be fixed on the Head joint. `skin_points` is the head's skin (not its hair), so
    the arms hug the head rather than the hair's outline."""
    pieces = []
    front = max(eye_centres[:, 2]) + 0.016
    height = eye_centres[:, 1].mean() + 0.002
    for centre in eye_centres:
        points, faces = round_cornered_frame(rim, bar, radius, depth)
        frame_mesh = trimesh.Trimesh(points + [centre[0], height, front - depth / 2], faces, process=True)
        trimesh.repair.fix_normals(frame_mesh)
        pieces.append((np.asarray(frame_mesh.vertices), np.asarray(frame_mesh.faces)))
    left, right = sorted(eye_centres, key=lambda centre: centre[0])
    gap = abs(right[0] - left[0]) - rim[0]
    bridge = shapes.rounded_box((gap / 2 + 0.002, 0.0022, depth / 2), 0.001, 3)
    bridge = shapes.placed(bridge, np.array([(left[0] + right[0]) / 2, height + 0.006, front]), np.eye(3))
    pieces.append((np.asarray(bridge.vertices), np.asarray(bridge.faces)))
    band = skin_points[np.abs(skin_points[:, 1] - (height + 0.01)) < 0.012]
    ear_z = band[:, 2].min() * 0.4 + band[:, 2].max() * 0.6 - 0.04
    for centre, sign in ((right, 1.0), (left, -1.0)):
        outer_x = centre[0] + sign * (rim[0] / 2 - 0.002)
        near = band[np.abs(band[:, 2] - ear_z) < 0.02]
        side = (near[:, 0].max() if sign > 0 else near[:, 0].min()) + sign * 0.003
        start = np.array([outer_x, height + 0.012, front - depth / 2])
        end = np.array([side, height + 0.006, ear_z])
        length = np.linalg.norm(end - start)
        axes = shapes.frame(end - start, [0.0, 1.0, 0.0])
        arm = shapes.rounded_box((length / 2 + 0.003, 0.0022, 0.0014), 0.0008, 3)
        arm = shapes.placed(arm, (start + end) / 2, axes)
        pieces.append((np.asarray(arm.vertices), np.asarray(arm.faces)))
    return joined(pieces)


def clipboard(body, side="Left"):
    """A clipboard held in one hand, flat against the hand's palm side: board and paper, fixed
    on the hand."""
    hand = body.joints[f"{side}Hand"]
    fore = body.joints[f"{side}ForeArm"]
    down = (hand - fore) / np.linalg.norm(hand - fore)
    axes = shapes.frame(down, [0.0, 0.0, 1.0])
    board = shapes.placed(shapes.rounded_box((0.16, 0.115, 0.005), 0.003, 3),
                          hand + down * 0.12 + axes[:, 1] * 0.03, axes)
    paper = shapes.placed(shapes.rounded_box((0.135, 0.1, 0.0015), 0.001, 2),
                          hand + down * 0.115 + axes[:, 1] * 0.03 + axes[:, 2] * 0.0055, axes)
    clip = shapes.placed(shapes.rounded_box((0.02, 0.035, 0.006), 0.003, 3),
                         hand + down * -0.02 + axes[:, 1] * 0.03 + axes[:, 2] * 0.006, axes)
    return {"clipboard": (np.asarray(board.vertices), np.asarray(board.faces)),
            "paper": (np.asarray(paper.vertices), np.asarray(paper.faces)),
            "clip": (np.asarray(clip.vertices), np.asarray(clip.faces))}
