"""The first expedition's American space suit (#112): the same draped coverall and neck ring as
take C's suit, with its own hard parts after the drawings of Oona, Bram and Sefa: an open-faced
bubble helmet with the gold visor pushed up (the face shows, as in the drawings), a slim grey
control box on the chest with a screen, knobs and two hoses down to the hips, a name tag above
it, a big boxy pack, harness straps and a belt, pairs of blue stripes on the arms and legs, a
US flag on the left upper arm, thigh pockets, white gloves and white moon boots.

Every part carries its weights as in `space_suit.py`; the painter reads the few that carry a
pattern (the flag, the name tag, the screen) off `extra`.
"""
import face
import fit
import numpy as np
import shapes
import skin
import space_suit
import trimesh
import work_suit
from scipy.spatial import cKDTree
from space_suit import SIDES

# The helmet's front window, round the face: how far from straight ahead it opens (degrees), and
# the gold visor pushed up over the top: its middle's tilt up from ahead and its half angle.
WINDOW = 62.0
VISOR_UP = 58.0
VISOR_HALF = 44.0
# The US flag on the left upper arm: where along the upper arm (shares), its half height round
# the arm (m) and how proud of the cloth.
ARM_FLAG = (0.18, 0.42, 0.030, 0.003)
# Blue stripes as shares of the upper arm, and heights on take C's legs.
ARM_STRIPES = ((0.54, 0.59), (0.64, 0.69))
LEG_STRIPES = ((0.262, 0.284), (0.300, 0.322), (0.598, 0.620))


class AmericanSuit(space_suit.SpaceSuit):

    def the_helmet(self, ring_top, normal, across, inside):
        """Shell open at the front, drawn from both sides; the gold visor raised over it; a
        white rim round the window and the bearing into the ring."""
        radius = space_suit.HELMET_RADIUS
        bearing_radii = inside - 0.005
        down = np.sqrt(radius ** 2 - bearing_radii.max() ** 2)
        centre = ring_top + np.array([0.0, down - 0.008, 0.0])
        ahead = np.array([0.0, 0.05, 1.0])
        ahead /= np.linalg.norm(ahead)
        shell = open_sphere(centre, radius, ahead, np.radians(WINDOW),
                            np.pi - np.arcsin(bearing_radii.max() / radius))
        self.rigid("helmet", shell, "Head")
        bearing = shapes.loft(ring_top, across, normal, bearing_radii,
                              lambda angle: shapes.rounded_rectangle(-0.014, 0.0, -0.035, 0.06, 0.003), 40)
        self.rigid("helmet_bearing", bearing, "Head")
        tilt = np.radians(VISOR_UP)
        visor_axis = np.array([0.0, np.sin(tilt), np.cos(tilt)])
        self.rigid("visor", shapes.spherical_cap(centre, radius + 0.004, visor_axis, np.radians(VISOR_HALF)), "Head")
        rim_centre = centre + ahead * radius * np.cos(np.radians(WINDOW))
        rim_radius = radius * np.sin(np.radians(WINDOW))
        rim = shapes.loft(rim_centre, [1, 0, 0], ahead, (rim_radius, rim_radius),
                          lambda angle: shapes.circle(0.006, 8), 64)
        self.rigid("helmet_rim", rim, "Head")
        self.helmet_centre = centre

    def the_chest(self):
        wide = float(fit.width_share(1.24))
        box_y = float(fit.y(1.235))
        far = self.conformed_box("chest_box", "Chest", (0.0, box_y), (0.095 * wide, 0.068), 0.045, 0.010, 1.0)
        screen = shapes.placed(shapes.rounded_box((0.052 * wide, 0.040, 0.004), 0.003, 4),
                               np.array([0.0, box_y + 0.008, far + 0.002]), np.eye(3))
        self.rigid("chest_screen", screen, "Chest")
        knobs = [shapes.placed(shapes.rounded_box((0.010, 0.010, 0.008), 0.007, 4),
                               np.array([side * 0.075 * wide, box_y + height, far + 0.004]), np.eye(3))
                 for side in (-1.0, 1.0) for height in (0.030, -0.005)]
        self.rigid("chest_knobs", shapes.joined(knobs), "Chest")
        tag_y = box_y + 0.068 + 0.030
        self.conformed_box("name_tag", "Chest", (0.0, tag_y), (0.060 * wide, 0.016), 0.006, 0.003, 1.0, count=5)
        self.hoses(box_y, far, wide)
        self.extra["tag_y"] = tag_y

    def hoses(self, box_y, far, wide):
        """Two hoses from under the chest box's sides, looping down to the hips' fronts, each
        point riding the cloth under it."""
        for sign in (1.0, -1.0):
            start = np.array([sign * 0.070 * wide, box_y - 0.060, far - 0.015])
            end_x = sign * float(fit.x(0.150, 1.02))
            end_y = float(fit.y(1.02))
            path = []
            for share in np.linspace(0, 1, 14):
                x_here = start[0] + (end_x - start[0]) * share
                y_here = start[1] + (end_y - start[1]) * share - 0.05 * np.sin(np.pi * share)
                path.append([x_here, y_here])
            path = np.array(path)
            hit, normal, _ = self.first_hits(np.column_stack([path, np.full(len(path), 1.0)]), np.array([0.0, 0.0, -1.0]))
            lift = 0.012 + 0.018 * np.sin(np.pi * np.linspace(0, 1, len(path)))
            points = hit + normal * lift[:, None]
            points[0, 2] = max(points[0, 2], start[2])
            tube_points, tube_faces = face.tube(points, 0.009)
            mesh = trimesh.Trimesh(tube_points, tube_faces, process=False)
            _, nearest = cKDTree(points).query(tube_points)
            weights = skin.at_the_cloth(self.cloth, self.cloth_weights, hit[nearest])
            self.keep(f"hose_{'l' if sign > 0 else 'r'}", mesh, weights)

    def the_pack(self):
        wide = float(fit.width_share(1.215))
        self.conformed_box("pack", "cloth", fit.xy(0.0, 1.20), (0.195 * wide, 0.27 * fit.leg_share()),
                           0.17, 0.022, -1.0, count=8)

    def the_bands(self):
        joints = self.body.joints
        for name, sign, side in SIDES:
            shoulder, elbow = joints[f"{name}Arm"], joints[f"{name}ForeArm"]
            axis = elbow - shoulder
            length = np.linalg.norm(axis)
            arm = [f"{'left' if sign > 0 else 'right'}_arm"]
            leg = [f"{'left' if sign > 0 else 'right'}_leg"]
            for index, (low, high) in enumerate(ARM_STRIPES):
                self.band(f"band_blue_arm{index}_{side}", arm, shoulder, axis, low * length, high * length)
            for index, (low, high) in enumerate(LEG_STRIPES):
                self.band(f"band_blue_leg{index}_{side}", leg, np.zeros(3), np.array([0.0, 1.0, 0.0]),
                          float(fit.y(low)), float(fit.y(high)))

    def the_pockets(self):
        for name, sign, side in SIDES:
            self.conformed_box(f"thigh_pocket_{side}", f"{name}Leg", fit.xy(sign * 0.150, 0.56),
                               (0.050, 0.060), 0.022, 0.008, 1.0, count=5)

    def the_arm_flag(self):
        """A thin curved plate on the outside of the left upper arm, cast onto the sleeve."""
        shoulder, elbow = self.body.joints["LeftArm"], self.body.joints["LeftForeArm"]
        axis = (elbow - shoulder) / np.linalg.norm(elbow - shoulder)
        outward = np.array([1.0, 0.0, 0.0]) - axis * axis[0]
        outward /= np.linalg.norm(outward)
        around = np.cross(axis, outward)
        low, high, half, proud = ARM_FLAG
        length = np.linalg.norm(elbow - shoulder)
        rows, columns = 8, 12
        down = np.linspace(low, high, rows) * length
        across = np.linspace(-half, half, columns)
        grid_down, grid_across = np.meshgrid(down, across, indexing="ij")
        middles = shoulder + grid_down.ravel()[:, None] * axis + grid_across.ravel()[:, None] * around
        hit, normal, _ = self.first_hits(middles + outward * 0.3, -outward)
        top = hit + normal * proud
        base = hit - normal * 0.001
        faces = work_suit.grid_faces(rows, columns) + work_suit.walls(work_suit.rim_of(rows, columns), rows * columns)
        mesh = trimesh.Trimesh(np.concatenate([top, base]), np.array(faces), process=False)
        trimesh.repair.fix_normals(mesh)
        self.rigid("arm_flag", mesh, "LeftArm")
        # Per point: 0 at the shoulder end to 1 at the elbow end, and round the arm -1 to 1.
        self.extra["arm_flag"] = np.tile(np.column_stack([(grid_down.ravel() - down[0]) / (down[-1] - down[0]),
                                                          grid_across.ravel() / half]), (2, 1))


def open_sphere(centre, radius, ahead, window, lowest, rings=20, count=48):
    """A sphere round `centre` with a round window `window` from `ahead` and cut off below
    `lowest` from straight up: a single surface."""
    points, faces = [], []
    polar = np.linspace(0.0, lowest, rings + 1)
    azimuth = np.linspace(-np.pi, np.pi, count, endpoint=False)
    kept = np.zeros((rings + 1, count), dtype=bool)
    index = -np.ones((rings + 1, count), dtype=int)
    for row, angle in enumerate(polar):
        for column, turn in enumerate(azimuth):
            direction = np.array([np.sin(angle) * np.sin(turn), np.cos(angle), np.sin(angle) * np.cos(turn)])
            index[row, column] = len(points)
            points.append(centre + radius * direction)
            kept[row, column] = np.degrees(np.arccos(np.clip(direction @ ahead, -1, 1))) > np.degrees(window)
    for row in range(rings):
        for column in range(count):
            following = (column + 1) % count
            corners = [(row, column), (row, following), (row + 1, following), (row + 1, column)]
            if all(kept[corner] for corner in corners):
                first, second, third, fourth = (index[corner] for corner in corners)
                faces += [[first, third, second], [first, fourth, third]]
    mesh = trimesh.Trimesh(np.array(points), np.array(faces), process=True)
    mesh.remove_unreferenced_vertices()
    return mesh


def pieces(body, folder):
    """Every shape of the American suit, and the painter's extra numbers."""
    suit = AmericanSuit(body, folder)
    suit.extra = {}
    suit.the_cloth()
    suit.the_helmet(*suit.the_neck_ring())
    suit.the_chest()
    suit.the_pack()
    suit.the_straps()
    suit.the_bands()
    suit.the_pockets()
    suit.the_arm_flag()
    for name, sign, side in SIDES:
        suit.the_wrist_and_mitt(name, sign, side)
    suit.the_boots()
    return suit.parts, suit.extra
