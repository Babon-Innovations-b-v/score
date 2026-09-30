"""The work suit's shapes: GarmentCode's draped one-piece, thinned, with a stiff stand collar on its
neckline, a raised zip line from the collar to the crotch, a chest pocket with a flap, a belt
round the waistband and a bevelled buckle; the boots and the trouser legs tucked into them are
`boots.py`'s, the face's parts `face.py`'s.

Every hard part is measured off the cloth under it rather than placed by hand, so a new drape
moves them with it. Everything faces +z with y up, in metres.
"""
import blender
import boots
import drape
import fit
import numpy as np
import shapes
import skin
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

# The drape is thinned to about this many triangles, keeping the left and right alike.
CLOTH_TRIANGLES = 9000
# Stand collar: height over the neckline, how far it overlaps the cloth below it, how far its
# top leans in, wall thickness, and the half-width of the front opening.
COLLAR_HEIGHT = 0.040
COLLAR_OVERLAP = 0.012
COLLAR_LEAN = 0.006
COLLAR_WALL = 0.004
COLLAR_GAP = 0.009
NECK_CLEARANCE = 0.004
# The collar hugs an ellipse round the neck (x and z half-axes about a centre at this x, z), a
# little wider than the neck; its front never dips below FRONT_LOWEST.
NECK_CENTRE = np.array([0.0, fit.neck_z(-0.019)])
NECK_ELLIPSE = (0.066 * fit.head_scale()[0], 0.071 * fit.head_scale()[0])
FRONT_LOWEST = float(fit.y(1.445))
# Zip line: half width, how proud of the cloth, where it stops at the crotch, its step down.
PLACKET_HALF = 0.014
PLACKET_PROUD = 0.0025
PLACKET_LOW = float(fit.y(0.86))
PLACKET_STEP = 0.015
# Over how many rows the zip line's top is smoothed across the cloth's folds: it followed every
# fold, and its piping wobbled (the owner's notes, #100).
PLACKET_BRIDGE = 3
# Belt: height, thickness, gap off the cloth. Buckle: size, window, thickness, bevel.
BELT_HEIGHT = 0.035
BELT_THICK = 0.005
BELT_GAP = 0.004
BUCKLE = (0.062, 0.046)
BUCKLE_WINDOW = (0.040, 0.024)
BUCKLE_THICK = 0.006
BUCKLE_BEVEL = 0.0018
# How many steps round the neck and the waist.
ANGLES = 96
# The chest pocket, on the wearer's left, and its flap, which is the flag: x span, y span, and
# how proud of the cloth each stands.
POCKET = ((float(fit.x(0.035, 1.28)), float(fit.x(0.145, 1.28))), (float(fit.y(1.215)), float(fit.y(1.335))), 0.003)
FLAP = ((float(fit.x(0.031, 1.28)), float(fit.x(0.149, 1.28))), (float(fit.y(1.30)), float(fit.y(1.352))), 0.0055)
# How many rounds the collar's weights are averaged round the band, and the belt's.
COLLAR_SMOOTHING = 6
BELT_SMOOTHING = 2


def circular_smooth(values, passes):
    """Values round a loop, each averaged with its two neighbours `passes` times."""
    for _ in range(passes):
        values = (np.roll(values, 1, axis=0) + 2 * values + np.roll(values, -1, axis=0)) / 4
    return values


def thin_cloth(folder):
    """The drape, thinned, with each thinned point's panel and limb from the nearest full point:
    a trimesh, panels, limbs."""
    points, faces, panels, limbs = drape.work_suit_cloth(folder)
    thin_points, thin_faces = blender.thinned("work_cloth", points, faces, CLOTH_TRIANGLES,
                                              symmetric=True)
    _, nearest = cKDTree(points).query(thin_points)
    mesh = trimesh.Trimesh(thin_points, thin_faces, process=False)
    trimesh.repair.fix_normals(mesh, multibody=True)
    return mesh, panels[nearest], limbs[nearest]


def open_edge_points(mesh):
    """Every point on an open edge of the mesh."""
    edges, counts = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    return np.unique(edges[counts == 1])


def neckline(mesh):
    """The open edge loop highest up the suit, as angles evenly round the neck with the loop's
    height there."""
    edges, counts = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    graph = trimesh.graph.nx.Graph()
    graph.add_edges_from(edges[counts == 1].tolist())
    loops = [np.array(sorted(component)) for component in trimesh.graph.nx.connected_components(graph)]
    top = max(loops, key=lambda indices: mesh.vertices[indices, 1].mean())
    ring = mesh.vertices[top]
    centre = ring.mean(axis=0)
    angle = np.arctan2(ring[:, 0] - centre[0], ring[:, 2] - centre[2])
    order = np.argsort(angle)
    samples = np.linspace(-np.pi, np.pi, ANGLES, endpoint=False)
    wrapped = np.concatenate([angle[order] - 2 * np.pi, angle[order], angle[order] + 2 * np.pi])
    height = np.interp(samples, wrapped, np.tile(ring[order, 1], 3))
    return samples, circular_smooth(height, 4)


def radius_at(mesh, angles, heights, centre, reach=0.16):
    """How far a mesh reaches from a vertical axis at `centre` (x, z), per angle, at each angle's
    own height: the outermost section point within a few degrees of that angle."""
    radii = np.zeros(len(angles))
    cache = {}
    for index, (angle, height) in enumerate(zip(angles, heights)):
        key = round(float(height), 3)
        if key not in cache:
            section = mesh.section(plane_origin=[0, key, 0], plane_normal=[0, 1, 0])
            ring = np.zeros((0, 3)) if section is None else np.asarray(section.vertices)
            ring = ring[np.abs(ring[:, 0] - centre[0]) < reach]
            cache[key] = (np.arctan2(ring[:, 0] - centre[0], ring[:, 2] - centre[1]),
                          np.hypot(ring[:, 0] - centre[0], ring[:, 2] - centre[1]))
        ring_angles, ring_radii = cache[key]
        near = np.abs(np.angle(np.exp(1j * (ring_angles - angle)))) < 0.09
        radii[index] = ring_radii[near].max() if near.any() else 0.0
    return radii


def collar_line(mesh, body_mesh):
    """Where the collar sits, per angle round the neck: angles, bottom height, bottom radius and
    top radius. It never comes nearer the body than NECK_CLEARANCE."""
    angles, cloth_height = neckline(mesh)
    ellipse = 1.0 / np.sqrt((np.sin(angles) / NECK_ELLIPSE[0]) ** 2
                            + (np.cos(angles) / NECK_ELLIPSE[1]) ** 2)
    bottom = circular_smooth(np.maximum(cloth_height, FRONT_LOWEST), 4)
    top = bottom + COLLAR_HEIGHT
    radius_bottom = np.maximum(ellipse, radius_at(body_mesh, angles, bottom, NECK_CENTRE) + NECK_CLEARANCE)
    radius_top = np.maximum(ellipse - COLLAR_LEAN,
                            radius_at(body_mesh, angles, top, NECK_CENTRE) + NECK_CLEARANCE)
    return angles, bottom, circular_smooth(radius_bottom, 3), circular_smooth(radius_top, 3)


def tailored_neckline(mesh, body_mesh, line):
    """The cloth with its neckline pulled in and up to sit just under the collar's bottom edge,
    the cloth near it dragged along with a smooth falloff, then kept off the body."""
    angles, bottom, radius_bottom, _ = line
    points = np.asarray(mesh.vertices).copy()
    boundary = open_edge_points(mesh)
    boundary = boundary[points[boundary, 1] > fit.y(1.35)]
    edge = points[boundary]
    edge_angle = np.arctan2(edge[:, 0] - NECK_CENTRE[0], edge[:, 2] - NECK_CENTRE[1])
    wrapped = np.concatenate([angles - 2 * np.pi, angles, angles + 2 * np.pi])
    target_radius = np.interp(edge_angle, wrapped, np.tile(radius_bottom, 3)) - 0.002
    target_height = np.interp(edge_angle, wrapped, np.tile(bottom, 3)) - COLLAR_OVERLAP / 2
    target = np.stack([NECK_CENTRE[0] + target_radius * np.sin(edge_angle), target_height,
                       NECK_CENTRE[1] + target_radius * np.cos(edge_angle)], axis=1)
    moves = target - edge
    distance, nearest = cKDTree(edge).query(points)
    falloff = np.clip(1.0 - distance / 0.07, 0.0, 1.0) ** 2
    points += moves[nearest] * falloff[:, None]
    near = distance < 0.1
    closest, gap, triangle = trimesh.proximity.closest_point(body_mesh, points[near])
    outside = ((points[near] - closest) * body_mesh.face_normals[triangle]).sum(axis=1) > 0
    too_close = np.where(outside, gap, -gap) < 0.003
    fixed = points[near]
    fixed[too_close] = closest[too_close] + body_mesh.face_normals[triangle][too_close] * 0.003
    points[near] = fixed
    print(f"neckline: moved {len(boundary)} edge points by up to "
          f"{np.linalg.norm(moves, axis=1).max() * 1000:.0f} mm, "
          f"{int(too_close.sum())} cloth points pushed off the body")
    return trimesh.Trimesh(points, mesh.faces, process=False)


def collar(mesh, line):
    """The stand collar: an open band round the neck, its front gap COLLAR_GAP each side of the
    middle, its foot spread to stay outside the cloth it covers. Points, faces."""
    angles, bottom, radius_bottom, radius_top = line
    keep = np.abs(np.angle(np.exp(1j * angles))) > COLLAR_GAP / radius_bottom.mean()
    # Start the open band just past the gap on one side and run round to the other.
    start = np.argmax(keep & ~np.roll(keep, 1))
    order = np.roll(np.arange(ANGLES), -start)
    order = order[keep[order]]
    angles, bottom = angles[order], bottom[order]
    radius_bottom, radius_top = radius_bottom[order], radius_top[order]
    low = bottom - COLLAR_OVERLAP
    top = bottom + COLLAR_HEIGHT
    radius_low = np.clip(radius_at(mesh, angles, low, NECK_CENTRE, reach=0.11) + 0.0015,
                         radius_bottom, radius_bottom + 0.008)
    radius_low = np.convolve(np.pad(radius_low, 4, mode="edge"), np.ones(9) / 9, mode="valid")
    rings = [(radius_low, low), (radius_bottom, bottom), (radius_top, top),
             (radius_top + COLLAR_WALL, top), (radius_bottom + COLLAR_WALL, bottom),
             (radius_low + COLLAR_WALL, low)]
    return shapes.ring_band(angles, np.array([NECK_CENTRE[0], 0.0, NECK_CENTRE[1]]), rings,
                            closed=False)


def cast(mesh, origins, direction):
    """First hit of rays from each origin along `direction`: point and face normal (NaN on a
    miss)."""
    locations, ray_index, triangle = mesh.ray.intersects_location(
        origins, np.tile(direction, (len(origins), 1)), multiple_hits=True)
    hits = np.full((len(origins), 3), np.nan)
    normals = np.full((len(origins), 3), np.nan)
    best = np.full(len(origins), np.inf)
    for location, ray, face in zip(locations, ray_index, triangle):
        travel = np.dot(location - origins[ray], direction)
        if travel < best[ray]:
            best[ray] = travel
            hits[ray] = location
            normals[ray] = mesh.face_normals[face]
    return hits, normals


def grid_faces(rows, columns):
    """Two triangles for every cell of a rows x columns grid of points, row after row."""
    faces = []
    for row in range(rows - 1):
        for column in range(columns - 1):
            corner = row * columns + column
            faces += [[corner, corner + 1, corner + columns + 1],
                      [corner, corner + columns + 1, corner + columns]]
    return faces


def rim_of(rows, columns):
    """The points round the edge of a rows x columns grid, in order."""
    return ([column for column in range(columns)]
            + [row * columns + columns - 1 for row in range(1, rows)]
            + [(rows - 1) * columns + column for column in range(columns - 2, -1, -1)]
            + [row * columns for row in range(rows - 2, 0, -1)])


def walls(rim, offset):
    """Triangles joining a top rim to the same rim `offset` points later."""
    faces = []
    for index in range(len(rim)):
        here, there = rim[index], rim[(index + 1) % len(rim)]
        faces += [[here, there + offset, there], [here, here + offset, there + offset]]
    return faces


def bridged(hits, normals, rows, columns, reach):
    """A plate's top lifted over the cloth's folds: down each column its depth and its normal
    are smoothed over about `reach` rows, and it never sinks below the cloth. Its walls still
    run down to the cloth, so the plate stands on it rather than floating."""
    depth = hits[:, 2].reshape(rows, columns)
    top = hits.copy()
    top[:, 2] = np.maximum(depth, ndimage.gaussian_filter1d(depth, reach, axis=0, mode="nearest")).ravel()
    smooth = ndimage.gaussian_filter1d(normals.reshape(rows, columns, 3), reach, axis=0, mode="nearest")
    smooth = smooth.reshape(-1, 3)
    return top, smooth / np.linalg.norm(smooth, axis=1, keepdims=True)


def raised_patch(mesh, xs, ys, proud, bridge_rows=0):
    """A thin plate laid on the cloth's front over a grid of x by y, `proud` off the surface,
    with walls down into the cloth so no gap shows at its edge: points, faces, and each point's
    x on the grid (so a painter can find the plate's edges however the cloth under it folds).
    With `bridge_rows`, its top is lifted over the cloth's folds (`bridged`)."""
    grid_x, grid_y = np.meshgrid(xs, ys)
    origins = np.stack([grid_x.ravel(), grid_y.ravel(), np.full(grid_x.size, 1.0)], axis=1)
    hits, normals = cast(mesh, origins, np.array([0.0, 0.0, -1.0]))
    if np.isnan(hits).any():
        raise SystemExit(f"{int(np.isnan(hits).any(axis=1).sum())} patch rays missed the cloth")
    normals[normals[:, 2] < 0] *= -1
    rows, columns = len(ys), len(xs)
    top, top_normals = bridged(hits, normals, rows, columns, bridge_rows) if bridge_rows else (hits, normals)
    points = np.concatenate([top + top_normals * proud, hits - normals * 0.001])
    faces = grid_faces(rows, columns) + walls(rim_of(rows, columns), rows * columns)
    return points, np.array(faces), np.tile(grid_x.ravel(), 2)


def placket(mesh, neck_front_height):
    """The zip line, from the crotch to the collar's front."""
    xs = np.array([-PLACKET_HALF, -PLACKET_HALF / 2, 0.0, PLACKET_HALF / 2, PLACKET_HALF])
    ys = np.arange(PLACKET_LOW, neck_front_height - 0.002, PLACKET_STEP)
    return raised_patch(mesh, xs, ys, PLACKET_PROUD, PLACKET_BRIDGE)


def pocket(mesh):
    """The chest pocket and its flap: points, faces, and the index of the flap's first point."""
    (x_low, x_high), (y_low, y_high), proud = POCKET
    body_points, body_faces, _ = raised_patch(mesh, np.linspace(x_low, x_high, 12),
                                              np.linspace(y_low, y_high, 12), proud)
    (x_low, x_high), (y_low, y_high), proud = FLAP
    flap_points, flap_faces, _ = raised_patch(mesh, np.linspace(x_low, x_high, 12),
                                              np.linspace(y_low, y_high, 4), proud)
    return (np.concatenate([body_points, flap_points]),
            np.concatenate([body_faces, flap_faces + len(body_points)]), len(body_points))


def belt(mesh, waist_height):
    """A closed band round the waist, clear of the cloth (and the zip line) at every angle:
    points, faces, and how far forward its front face is."""
    angles = np.linspace(-np.pi, np.pi, ANGLES, endpoint=False)
    torso = mesh.vertices[np.abs(mesh.vertices[:, 0]) < 0.25]
    centre = np.array([0.0, waist_height,
                       torso[np.abs(torso[:, 1] - waist_height) < 0.03, 2].mean()])
    reach = np.zeros(ANGLES)
    for height in np.linspace(waist_height - BELT_HEIGHT / 2 - 0.005,
                              waist_height + BELT_HEIGHT / 2 + 0.005, 5):
        ring = np.asarray(mesh.section(plane_origin=[0, height, 0], plane_normal=[0, 1, 0]).vertices)
        ring = ring[np.abs(ring[:, 0]) < 0.25]
        angle = np.arctan2(ring[:, 0] - centre[0], ring[:, 2] - centre[2])
        radius = np.hypot(ring[:, 0] - centre[0], ring[:, 2] - centre[2])
        bins = np.round((angle + np.pi) / (2 * np.pi) * ANGLES).astype(int) % ANGLES
        for index in range(ANGLES):
            mine = radius[bins == index]
            if len(mine):
                reach[index] = max(reach[index], mine.max())
    front = np.abs(angles) < 0.12
    reach = reach + BELT_GAP + np.where(front, PLACKET_PROUD, 0.0)
    reach = np.maximum(reach, circular_smooth(reach, 3))
    low, high = waist_height - BELT_HEIGHT / 2, waist_height + BELT_HEIGHT / 2
    rings = [(reach, low), (reach, high), (reach + BELT_THICK, high), (reach + BELT_THICK, low)]
    points, faces = shapes.ring_band(angles, centre, rings, closed=True)
    return points, faces, centre[2] + reach[np.argmin(np.abs(angles))] + BELT_THICK


def buckle(waist_height, front):
    """The buckle: a bevelled frame with a bar across its window, on the belt's front."""
    points, faces = shapes.picture_frame(BUCKLE, BUCKLE_WINDOW, BUCKLE_BEVEL, BUCKLE_THICK)
    bar_points, bar_faces = shapes.square_box(
        np.array([0.005, BUCKLE_WINDOW[1] + 0.002, BUCKLE_THICK * 0.8]),
        np.array([0.0, 0.0, BUCKLE_THICK * 0.4]))
    points = np.concatenate([points, bar_points])
    faces = np.concatenate([faces, bar_faces + len(points) - len(bar_points)])
    return points + [0.0, waist_height, front + 0.001], faces


def pieces(body, folder):
    """Every shape of the work suit below the head, from the drape in `folder`, each with its
    weights on the skeleton: {name: (points, faces, weights)}, plus the cloth's panels, and the
    zip line's and the pocket's extra numbers for the painter.

    The hard parts are measured off the cloth before its trouser legs are tucked into the boots;
    the tuck moves nothing above the boots."""
    mesh, panels, limbs = thin_cloth(folder)
    body_mesh = trimesh.Trimesh(body.points, body.faces, process=False)
    line = collar_line(mesh, body_mesh)
    mesh = tailored_neckline(mesh, body_mesh, line)
    angles, bottom = line[0], line[1]
    neck_front_height = bottom[np.argmin(np.abs(angles))] - COLLAR_OVERLAP
    waist_height = float(mesh.vertices[np.char.startswith(panels, "wb_")][:, 1].mean())
    left_boot, right_boot, boot_faces = boots.fitted(body)
    cloth_points = boots.tucked(np.asarray(mesh.vertices), mesh.faces, limbs,
                                {"Left": left_boot, "Right": right_boot}, boot_faces, body)
    cloth_faces = np.asarray(mesh.faces)
    cloth_weights = skin.of_a_drape(cloth_points, cloth_faces, limbs, body)
    boot_weights = {}
    for side, boot in (("Left", left_boot), ("Right", right_boot)):
        boot_weights[side] = boots.weights(boot, side, body)
        cloth_weights = boots.hem_follows_boot(cloth_points, cloth_weights, boot, boot_weights[side])
    shaped = {"work_cloth": (cloth_points, cloth_faces, cloth_weights)}
    collar_points, collar_faces = collar(mesh, line)
    shaped["work_collar"] = (collar_points, collar_faces, skin.averaged(
        skin.from_the_body(collar_points, body), collar_faces, COLLAR_SMOOTHING))
    placket_points, placket_faces, placket_across = placket(mesh, neck_front_height)
    shaped["work_placket"] = (placket_points, placket_faces,
                            skin.at_the_nearest_point(placket_points, cloth_points, cloth_weights))
    pocket_points, pocket_faces, flap_from = pocket(mesh)
    # One patch, one set of weights: a pocket that bends with the armpit crumples.
    pocket_weights = skin.at_the_nearest_point(pocket_points, cloth_points, cloth_weights).mean(axis=0)
    shaped["work_pocket"] = (pocket_points, pocket_faces, np.tile(pocket_weights, (len(pocket_points), 1)))
    belt_points, belt_faces, belt_front = belt(mesh, waist_height)
    belt_weights = skin.averaged(skin.at_the_nearest_point(belt_points, cloth_points, cloth_weights),
                                 belt_faces, BELT_SMOOTHING)
    shaped["work_belt"] = (belt_points, belt_faces, belt_weights)
    # The buckle moves as one rigid piece with the belt's front.
    front = belt_points[:, 2] > belt_points[:, 2].max() - 0.02
    one = belt_weights[front].mean(axis=0)
    buckle_points, buckle_faces = buckle(waist_height, belt_front)
    shaped["work_buckle"] = (buckle_points, buckle_faces, np.tile(one / one.sum(), (len(buckle_points), 1)))
    for side, boot in (("Left", left_boot), ("Right", right_boot)):
        shaped[f"work_boot_{side}"] = (boot, boot_faces if side == "Left" else boot_faces[:, ::-1],
                                     boot_weights[side])
    return shaped, panels, {"placket_across": placket_across, "flap_from": flap_from}

