"""The space suit's shapes: GarmentCode's draped coverall, raised bands and straps lying on it, and
hard parts seated on it by measuring the cloth under them (the neck ring, the helmet and its
visor, the chest box and its flag, the pack, the pads, the wrist rings and mitts), and the moon
boots Hi3DGen made, kept as `SPACE_BOOT` in the look.

Every part carries its weights on the skeleton: cloth and anything lying on it the cloth's,
anything hard one joint's, or, for a hard part that must stay seated on moving cloth, the cloth's
at one spot. Everything faces +z with y up, in metres.
"""
import blender
import drape
import fit
import networkx
import numpy as np
import shapes
import skin
import trimesh
from paths import SPACE_BOOT
from person import WHO
from scipy.spatial import cKDTree

SIDES = (("Left", 1.0, "l"), ("Right", -1.0, "r"))
# The moon boot's shaft middle in its own units, and how it is scaled onto the leg's end.
BOOT_SHAFT_MIDDLE = np.array([0.0, 0.0, -0.098])
BOOT_SCALE = np.array([0.36, 0.29, 0.38]) * fit.leg_share()
# A moon boot is soft: below the first height it follows the foot, above the second the shin.
BOOT_BLEND = (0.10, 0.19)
# The coverall is thinned to about this many triangles when its drape comes out finer.
CLOTH_TRIANGLES = 12500
HELMET_RADIUS = 0.185 * float(np.clip(fit.head_scale()[1], 0.9, 1.15))


def open_loops(points, faces):
    """Each open edge loop of a mesh, as a list of point indices."""
    mesh = trimesh.Trimesh(points, faces, process=False)
    unique, counts = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    graph = networkx.Graph()
    graph.add_edges_from(unique[counts == 1].tolist())
    return [list(component) for component in networkx.connected_components(graph)]


class SpaceSuit:
    """The coverall on the body, and the parts made on it so far, in the order they were made."""

    def __init__(self, body, folder):
        points, faces, self.limbs = drape.space_suit_cloth(folder)
        if len(faces) > CLOTH_TRIANGLES * 1.2:
            # A bigger body's drape comes out finer than take C's 12.5k triangles (#112):
            # thinned to about his, each thinned point keeping the nearest full point's limb.
            thin_points, faces = blender.thinned("space_cloth", points, faces, CLOTH_TRIANGLES, symmetric=True)
            _, nearest = cKDTree(points).query(thin_points)
            points, self.limbs = thin_points, self.limbs[nearest]
        self.body = body
        self.body_tree = cKDTree(body.points)
        self.cloth_weights = skin.of_a_drape(points, faces, self.limbs, body)
        self.cloth = trimesh.Trimesh(points, faces, process=False)
        self.loops = [self.cloth.vertices[loop] for loop in open_loops(points, faces)]
        self.parts = {}

    def keep(self, name, mesh, weights):
        self.parts[name] = (np.asarray(mesh.vertices), np.asarray(mesh.faces), weights)

    def rigid(self, name, mesh, joint):
        self.keep(name, mesh, skin.on_one_joint(len(mesh.vertices), self.body.joint_names, joint))

    def riding(self, name, mesh, spot):
        """A hard part moving as one piece with the cloth at `spot`, so it stays seated where
        the cloth under it goes."""
        weights = skin.at_the_cloth(self.cloth, self.cloth_weights, np.asarray([spot], dtype=float))
        self.keep(name, mesh, np.repeat(weights, len(mesh.vertices), axis=0))

    def first_hits(self, origins, direction):
        """Where rays from `origins` along one direction first meet the cloth, and the cloth's
        normal there turned back along the ray; a miss falls back to the nearest point."""
        origins = np.asarray(origins, dtype=float)
        places, rays, triangles = self.cloth.ray.intersects_location(
            origins, np.tile(direction, (len(origins), 1)), multiple_hits=True)
        hit = np.full((len(origins), 3), np.nan)
        normal = np.zeros((len(origins), 3))
        best = np.full(len(origins), np.inf)
        for place, ray, triangle in zip(places, rays, triangles):
            distance = np.dot(place - origins[ray], direction)
            if distance < best[ray]:
                best[ray] = distance
                hit[ray] = place
                normal[ray] = self.cloth.face_normals[triangle]
        missed = np.isnan(hit[:, 0])
        if missed.any():
            closest, _, triangle = trimesh.proximity.closest_point(self.cloth, origins[missed])
            hit[missed] = closest
            normal[missed] = self.cloth.face_normals[triangle]
        normal[(normal @ direction) > 0] *= -1
        return hit, normal, missed

    def limb_piece(self, limbs):
        """The cloth triangles with any corner on these limbs (any, so a band round a limb
        closes across the seam points that carry the neighbour's label)."""
        keep = np.isin(self.limbs[self.cloth.faces], limbs).any(axis=1)
        return trimesh.Trimesh(self.cloth.vertices, self.cloth.faces[keep], process=True)

    def raised(self, surface, low, high):
        """A strip of cloth made a solid band lying on it: the strip offset outward by `high`,
        its underside by `low`, closed round its edges, weighted from the cloth under it."""
        surface = trimesh.Trimesh(surface.vertices, surface.faces, process=True)
        normals = surface.vertex_normals.copy()
        _, nearest = self.body_tree.query(surface.vertices)
        away = surface.vertices - self.body.points[nearest]
        normals[np.einsum("ij,ij->i", normals, away) < 0] *= -1
        count = len(surface.vertices)
        points = np.concatenate([surface.vertices + normals * high, surface.vertices + normals * low])
        faces = [surface.faces, surface.faces[:, ::-1] + count]
        unique, counts = np.unique(np.sort(surface.edges, axis=1), axis=0, return_counts=True)
        for first, second in unique[counts == 1]:
            faces.append(np.array([[first, second, second + count],
                                   [first, second + count, first + count]]))
        solid = trimesh.Trimesh(points, np.concatenate(faces), process=False)
        trimesh.repair.fix_normals(solid)
        weights = skin.at_the_cloth(self.cloth, self.cloth_weights, surface.vertices)
        return solid, np.concatenate([weights, weights])

    def band(self, name, limbs, centre, axis, low, high):
        """A raised band round one limb between two planes square to `axis`."""
        axis = np.asarray(axis, dtype=float) / np.linalg.norm(axis)
        piece = strip(self.limb_piece(limbs), [(centre + axis * low, axis), (centre + axis * high, -axis)])
        self.keep(name, *self.raised(piece, -0.001, 0.006))

    def pad(self, name, joint, origin, direction, across, half, height, rings=7, count=28):
        """A domed cap lying on the cloth: rays from round `origin` along `direction` find the
        cloth; the cap's underside sits 2 mm off it and its top rises by `height` at the middle."""
        direction = np.asarray(direction, dtype=float) / np.linalg.norm(direction)
        across = np.asarray(across, dtype=float) - direction * np.dot(across, direction)
        across /= np.linalg.norm(across)
        other = np.cross(direction, across)
        samples, reach = [np.array(origin, dtype=float)], [0.0]
        for ring in range(1, rings + 1):
            fraction = ring / rings
            for step in range(count):
                around = 2 * np.pi * step / count
                samples.append(origin + fraction * (half[0] * np.cos(around) * across
                                                    + half[1] * np.sin(around) * other))
                reach.append(fraction)
        samples, reach = np.array(samples), np.array(reach)
        hit, normal, _ = self.first_hits(samples - direction * 0.3, direction)
        lift = 0.006 + height * np.sqrt(np.clip(1 - reach ** 2, 0, 1))
        top = hit + normal * (0.002 + lift)[:, None]
        bottom = hit + normal * 0.002
        size = len(samples)
        faces = [[0, 1 + step, 1 + (step + 1) % count] for step in range(count)]
        for ring in range(1, rings):
            inner, outer = 1 + (ring - 1) * count, 1 + ring * count
            for step in range(count):
                following = (step + 1) % count
                faces += [[inner + step, outer + step, outer + following],
                          [inner + step, outer + following, inner + following]]
        faces = np.array(faces)
        edge = 1 + (rings - 1) * count
        sides = []
        for step in range(count):
            following = (step + 1) % count
            sides += [[edge + step, edge + following, size + edge + following],
                      [edge + step, size + edge + following, size + edge + step]]
        mesh = trimesh.Trimesh(np.concatenate([top, bottom]),
                               np.concatenate([faces, faces[:, ::-1] + size, np.array(sides)]),
                               process=True)
        trimesh.repair.fix_normals(mesh)
        self.rigid(name, mesh, joint)

    def conformed_box(self, name, holder, centre_xy, half, depth, corner, facing, sink=0.004, count=10):
        """A rounded box whose face toward the body follows the cloth under it and whose far face
        is flat, `depth` out past the cloth's furthest point under it. `facing` is +1 on the
        front, -1 on the back. `holder` is a joint, or "cloth" to ride the cloth at the box's
        middle. Returns where its far face is."""
        box = shapes.rounded_box((half[0], half[1], 0.5), corner, count)
        points = box.vertices.copy()
        points[:, 0] += centre_xy[0]
        points[:, 1] += centre_xy[1]
        hit, _, _ = self.first_hits(np.column_stack([points[:, 0], points[:, 1],
                                                     np.full(len(points), facing * 1.0)]),
                                    np.array([0.0, 0.0, -facing]))
        cloth = hit[:, 2]
        # A ray through an opening (the neck) lands on the far side of the suit: take the usual
        # depth there instead.
        usual = np.median(cloth)
        cloth[(cloth - usual) * facing < -0.04] = usual
        far = (cloth.max() if facing > 0 else cloth.min()) + facing * depth
        along = points[:, 2] * facing + 0.5  # 0 at the body side, 1 at the far face
        near = cloth - facing * sink
        points[:, 2] = near + along * (far - near)
        mesh = trimesh.Trimesh(points, box.faces, process=False)
        trimesh.repair.fix_normals(mesh)
        if holder == "cloth":
            middle = hit[np.argmin(np.hypot(points[:, 0] - centre_xy[0], points[:, 1] - centre_xy[1]))]
            self.riding(name, mesh, middle)
        else:
            self.rigid(name, mesh, holder)
        return far

    def the_cloth(self):
        self.keep("cloth", self.cloth, self.cloth_weights)

    def the_neck_ring(self):
        """A wide ring low on the shoulders over the neck opening, in the opening's own
        (forward-tilted) plane: its inner edge 2 cm inside the opening's so the cloth's cut edge
        is under it, its underside following the cloth all round, its top flat. Returns the
        ring's frame: the centre of its top, its up axis, its across axis, its inner radii."""
        opening = max(self.loops, key=lambda ring: ring[:, 1].mean())
        centre = opening.mean(axis=0)
        normal = np.linalg.svd(opening - centre, full_matrices=False)[2][2]
        normal = normal if normal[1] > 0 else -normal
        across = np.array([1.0, 0.0, 0.0]) - normal * normal[0]
        across /= np.linalg.norm(across)
        ahead = np.cross(across, normal)
        flat = opening - centre
        inside = np.array([np.abs(flat @ across).max(), np.abs(flat @ ahead).max()]) - 0.02
        width = 0.032
        angles = np.linspace(0, 2 * np.pi, 64, endpoint=False)
        heights = []
        for reach in (0.0, width * 0.5, width):
            spots = (centre + np.outer((inside[0] + reach) * np.cos(angles), across)
                     + np.outer((inside[1] + reach) * np.sin(angles), ahead) + normal * 0.3)
            hit, _, missed = self.first_hits(spots, -normal)
            height = (hit - centre) @ normal
            height[missed | (height < -0.12)] = np.nan
            heights.append(height)
        heights = np.array(heights)
        highest = np.nanmax(heights, axis=0)
        outer = np.where(np.isnan(heights[2]), highest, heights[2])
        # Where no ray met the cloth (over the edge of the back), take the heights either side.
        for values in (highest, outer):
            known = ~np.isnan(values)
            values[~known] = np.interp(angles[~known], angles[known], values[known], period=2 * np.pi)
        smooth = np.convolve(np.concatenate([highest[-2:], highest, highest[:2]]), np.ones(5) / 5, "valid")
        top = np.nanmax(highest) + 0.025
        # Down to the cloth all round; where the cloth falls away steeply it stops at 10 cm.
        bottom = np.maximum(np.minimum(smooth, outer) - 0.006, top - 0.10)

        def profile(angle):
            low = bottom[int(round(angle / (2 * np.pi) * 64)) % 64]
            return np.array([(0.0, low), (width, low), (width, top - 0.012), (width - 0.004, top - 0.004),
                             (width - 0.012, top), (0.010, top), (0.003, top - 0.004), (0.0, top - 0.012)])

        self.rigid("neck_ring", shapes.loft(centre, across, normal, inside, profile, 64), "Chest")
        return centre + normal * top, normal, across, inside

    def the_helmet(self, ring_top, normal, across, inside):
        """A round helmet sat down into the neck ring: shell, a gold-rimmed black visor, two ear
        pucks and a bearing, tilted as the ring is, filling its hole."""
        radius = HELMET_RADIUS
        # The shell comes down until it is as narrow as the bearing, just inside the ring's top.
        bearing_radii = inside - 0.005
        down = np.sqrt(radius ** 2 - bearing_radii.max() ** 2)
        centre = ring_top + np.array([0.0, down - 0.008, 0.0])
        shell = shapes.spherical_cap(centre, radius, [0.0, 1.0, 0.0],
                                     np.pi - np.arcsin(bearing_radii.max() / radius), rings=18, count=44)
        bearing = shapes.loft(ring_top, across, normal, bearing_radii,
                              lambda angle: shapes.rounded_rectangle(-0.014, 0.0, -0.035, 0.06, 0.003), 40)
        self.rigid("helmet", shapes.joined([shell, bearing]), "Head")
        axis = np.array([0.0, -0.12, 1.0])
        axis /= np.linalg.norm(axis)
        half_angle = np.radians(50)
        self.rigid("visor", shapes.spherical_cap(centre, radius + 0.003, axis, half_angle), "Head")
        rim_centre = centre + axis * (radius + 0.004) * np.cos(half_angle)
        rim_radius = (radius + 0.004) * np.sin(half_angle)
        rim = shapes.loft(rim_centre, [1, 0, 0], axis, (rim_radius, rim_radius),
                          lambda angle: shapes.circle(0.010, 8), 56)
        pucks = [shapes.loft(centre + np.array([sign * (radius - 0.006), -0.01, 0.0]), [0, 1, 0],
                             [sign, 0, 0], (0.0, 0.0),
                             lambda angle: shapes.rounded_rectangle(0.0, 0.034, 0.0, 0.022, 0.006), 18)
                 for sign in (1.0, -1.0)]
        self.rigid("visor_rim", shapes.joined([rim] + pucks), "Head")

    def the_chest(self):
        wide = float(fit.width_share(1.268))
        far = self.conformed_box("chest_box", "Chest", fit.xy(0.0, 1.268), (0.125 * wide, 0.08), 0.05, 0.016, 1.0)
        flag = shapes.placed(shapes.rounded_box((0.075, 0.032, 0.005), 0.003, 4),
                             np.array([0.0, float(fit.y(1.303)), far + 0.002]), np.eye(3))
        self.rigid("flag", flag, "Chest")
        knobs = [shapes.placed(shapes.rounded_box((0.014, 0.014, 0.010), 0.009, 4),
                               np.array([spot * wide, float(fit.y(1.222)), far + 0.006]), np.eye(3)) for spot in (-0.055, 0.055)]
        self.rigid("chest_knobs", shapes.joined(knobs), "Chest")
        wide = float(fit.width_share(1.045))
        self.conformed_box("waist_box", "cloth", fit.xy(0.0, 1.045), (0.075 * wide, 0.04), 0.04, 0.012, 1.0, count=7)
        for _, sign, side in SIDES:
            self.conformed_box(f"waist_light_{side}", "cloth", fit.xy(sign * 0.108, 1.045), (0.026, 0.03),
                               0.03, 0.008, 1.0, count=5)

    def the_pack(self):
        wide = float(fit.width_share(1.215))
        self.conformed_box("pack", "cloth", fit.xy(0.0, 1.215), (0.165 * wide, 0.215 * fit.leg_share()), 0.16, 0.04, -1.0, count=10)

    def the_straps(self):
        """Harness straps down the front beside the chest box, and a belt."""
        torso = self.limb_piece(["torso"])
        for _, sign, side in SIDES:
            inner, outer = sorted((sign * float(fit.x(0.140, 1.3)), sign * float(fit.x(0.176, 1.3))))
            piece = strip(torso, [((inner, 0, 0), (1, 0, 0)), ((outer, 0, 0), (-1, 0, 0)),
                                  ((0, float(fit.y(1.07)), 0), (0, 1, 0))])
            self.keep(f"strap_{side}", *self.raised(piece, -0.001, 0.005))
        belt = strip(torso, [((0, float(fit.y(1.005)), 0), (0, 1, 0)), ((0, float(fit.y(1.062)), 0), (0, -1, 0))])
        self.keep("belt", *self.raised(belt, -0.001, 0.006))

    def the_bands(self):
        joints = self.body.joints
        for name, sign, side in SIDES:
            shoulder, elbow = joints[f"{name}Arm"], joints[f"{name}ForeArm"]
            axis = elbow - shoulder
            length = np.linalg.norm(axis)
            arm = [f"{'left' if sign > 0 else 'right'}_arm"]
            leg = [f"{'left' if sign > 0 else 'right'}_leg"]
            self.band(f"band_red_arm_{side}", arm, shoulder, axis, 0.50 * length, 0.58 * length)
            self.band(f"band_gold_arm_{side}", arm, shoulder, axis, 0.63 * length, 0.73 * length)
            self.band(f"band_red_shin_{side}", leg, np.zeros(3), np.array([0.0, 1.0, 0.0]), float(fit.y(0.275)), float(fit.y(0.310)))
            self.band(f"band_red_thigh_{side}", leg, np.zeros(3), np.array([0.0, 1.0, 0.0]), float(fit.y(0.600)), float(fit.y(0.635)))
            if WHO["botanist"] and sign > 0:
                self.band(f"band_green_arm_{side}", arm, shoulder, axis, 0.30 * length, 0.40 * length)

    def the_pads(self):
        joints = self.body.joints
        for name, _, side in SIDES:
            knee = joints[f"{name}Shin"]
            self.pad(f"knee_pad_{side}", f"{name}Shin", knee + np.array([0.0, 0.005, 0.0]),
                     np.array([0.0, 0.0, -1.0]), np.array([1.0, 0.0, 0.0]), (0.068, 0.088), 0.026)
            elbow = joints[f"{name}ForeArm"]
            down = joints[f"{name}Hand"] - elbow
            self.pad(f"elbow_pad_{side}", f"{name}ForeArm", elbow + down * 0.05,
                     np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0]), (0.048, 0.055), 0.016)

    def the_wrist_and_mitt(self, name, sign, side):
        """A ring on the sleeve's end, in the end's own slanted plane, and the mitt in it: a
        padded block for the fingers, a thumb and a wide cuff starting inside the ring. The
        sleeve hangs a few cm below the wrist, so the mitt is moved square to the forearm onto
        the sleeve's end (the hand inside is never drawn)."""
        wrist, elbow = self.body.joints[f"{name}Hand"], self.body.joints[f"{name}ForeArm"]
        along = (wrist - elbow) / np.linalg.norm(wrist - elbow)
        sleeve_end = min(self.loops, key=lambda ring: np.linalg.norm(ring.mean(0) - wrist))
        axis = np.linalg.svd(sleeve_end - sleeve_end.mean(0), full_matrices=False)[2][2]
        axis = axis if np.dot(axis, along) > 0 else -axis
        centre, across, first, second = ellipse_of(sleeve_end, axis)
        inside = (first + 0.004, second + 0.004)
        ring = shapes.loft(centre + axis * 0.004, across, axis, inside,
                           lambda angle: shapes.rounded_rectangle(-0.002, 0.017, -0.018, 0.018, 0.006), 40)
        self.rigid(f"wrist_ring_{side}", ring, f"{name}ForeArm")
        shift = centre - wrist
        shift -= axis * np.dot(shift, axis)
        wrist = wrist + shift
        axes = shapes.frame(np.array([0.59 * sign, -0.77, 0.23]), [-0.05 * sign, 0.24, 0.97])
        block = shapes.placed(shapes.rounded_box((0.078, 0.066, 0.046), 0.040, 10),
                              wrist + axes[:, 0] * 0.112 + axes[:, 2] * 0.006 * sign, axes)
        thumb_axes = shapes.frame(axes[:, 0] * 0.75 + axes[:, 1] * 0.62, axes[:, 2])
        thumb = shapes.placed(shapes.rounded_box((0.040, 0.026, 0.025), 0.024, 8),
                              wrist + axes[:, 0] * 0.085 + axes[:, 1] * 0.062, thumb_axes)
        cuff = shapes.loft(wrist + axis * 0.004, across, axis, (inside[0] - 0.004, inside[1] - 0.004),
                           lambda angle: np.array([(-0.030, -0.025), (0.0, -0.025), (0.0, 0.020),
                                                   (-0.008, 0.045), (-0.030, 0.045)]), 36)
        self.rigid(f"mitt_{side}", shapes.joined([block, thumb, cuff]), f"{name}Hand")

    def the_boots(self):
        """The moon boots on the legs' ends, the right the left mirrored, soft: the foot's below
        the ankle, the shin's above it."""
        data = np.load(SPACE_BOOT)
        names = self.body.joint_names
        for name, sign, side in SIDES:
            leg_end = min(self.loops, key=lambda ring: np.linalg.norm(ring.mean(0) - self.body.joints[f"{name}Foot"]))
            centre = leg_end.mean(0)
            points = (data["points"] - BOOT_SHAFT_MIDDLE) * BOOT_SCALE
            points[:, 1] -= points[:, 1].min()
            points[:, 0] *= sign
            points += [centre[0], 0.0, centre[2]]
            faces = data["faces"] if sign > 0 else data["faces"][:, ::-1]
            rise = np.clip((points[:, 1] - BOOT_BLEND[0]) / (BOOT_BLEND[1] - BOOT_BLEND[0]), 0, 1)
            rise = rise * rise * (3 - 2 * rise)
            weights = np.zeros((len(points), len(names)))
            weights[:, names.index(f"{name}Foot")] = 1 - rise
            weights[:, names.index(f"{name}Shin")] = rise
            self.keep(f"boot_{side}", trimesh.Trimesh(points, faces, process=False), weights)


def strip(mesh, planes):
    """What is left of `mesh` on the positive side of every (origin, normal) plane."""
    vertices, faces = mesh.vertices, mesh.faces
    for origin, normal in planes:
        vertices, faces = trimesh.intersections.slice_faces_plane(
            vertices, faces, np.asarray(normal, dtype=float), np.asarray(origin, dtype=float))[:2]
    return trimesh.Trimesh(vertices, faces, process=True)


def ellipse_of(ring_points, axis):
    """Centre, and the half extents along two axes square to `axis`, of a loop of points."""
    axis = np.asarray(axis, dtype=float) / np.linalg.norm(axis)
    centre = ring_points.mean(axis=0)
    flat = ring_points - centre
    flat -= np.outer(flat @ axis, axis)
    _, _, directions = np.linalg.svd(flat, full_matrices=False)
    first = directions[0] - axis * np.dot(directions[0], axis)
    first /= np.linalg.norm(first)
    second = np.cross(axis, first)
    return centre, first, np.abs(flat @ first).max(), np.abs(flat @ second).max()


def pieces(body, folder):
    """Every shape of the space suit, from the drape in `folder`, with its weights:
    {name: (points, faces, weights)}, in the order they are drawn."""
    suit = SpaceSuit(body, folder)
    suit.the_cloth()
    suit.the_helmet(*suit.the_neck_ring())
    suit.the_chest()
    suit.the_pack()
    suit.the_straps()
    suit.the_bands()
    suit.the_pads()
    for name, sign, side in SIDES:
        suit.the_wrist_and_mitt(name, sign, side)
    suit.the_boots()
    return suit.parts
