"""The taped gradient test's run in Newton's own Python (`python _check_taped.py <this folder>`): prints GAP, the
largest gap to central differences."""
import pathlib, sys, numpy as np, warp as wp, newton
sys.path.insert(0, sys.argv[1])
import _taped
builder = newton.ModelBuilder()
parent = -1
for index in range(4):
    body = builder.add_link(mass=1.0)
    place = wp.transform(wp.vec3(0.0, 0.0, 0.3 if index else 0.0), wp.quat_identity())
    axis = (1.0, 0.0, 0.0) if index % 2 == 0 else (0.0, 1.0, 0.0)
    builder.add_joint_revolute(parent, body, parent_xform=place, axis=axis)
    parent = body
builder.add_articulation(list(range(4)))
model = builder.finalize(device="cuda:0", requires_grad=True)
turns = ([2, 3], [1.5, 0.7], [[0.1, 0.2, 0.0, 0.9747], [0.0, -0.3, 0.1, 0.9487]],
         [[0.0, 0.0, 0.0, 1.0], [0.05, 0.0, 0.0, 0.99875]])
sites = _taped.TapedSites(model, [1, 3, 3], [1.0, 2.0, 0.5], [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]],
                          turns)
pose = np.array([0.2, 0.4, -0.3, 0.6])
outer = np.array([0.05, 0.0, 0.1, 0.02, 0.03, 0.1, -0.04, 0.0, 0.05])
sites.gradient(pose, outer)
taped = sites.gradient(pose, outer)
def cost(moved):
    found = sites.residuals(moved, outer)
    return 0.5 * float(found @ found)
step = 1e-3
differences = np.array([(cost(pose + step * np.eye(4)[axis]) - cost(pose - step * np.eye(4)[axis])) / (2 * step)
                        for axis in range(4)])
assert np.abs(sites.residuals(pose, outer)[9:]).min() > 1e-3, "turn rows missing from the cost"
coupled = _taped.TapedSites(model, [1, 3, 3], [1.0, 2.0, 0.5],
                            [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]], turns,
                            ([0, 1, 2], [3], [1], [0.1], [0.05], [[0.0, 0.8, -0.6, 0.3, 0.0]], [0.0, 0.0, 0.0, 0.1]))
free = np.array([0.2, 0.4, -0.3])
coupled.gradient(free, outer)
coupled_taped = coupled.gradient(free, outer)
def coupled_cost(moved):
    found = coupled.residuals(moved, outer)
    return 0.5 * float(found @ found)
coupled_differences = np.array([(coupled_cost(free + step * np.eye(3)[axis])
                                 - coupled_cost(free - step * np.eye(3)[axis])) / (2 * step) for axis in range(3)])
lead = free[1] - 0.05
expanded = np.append(free, 0.1 + 0.8 * lead - 0.6 * lead ** 2 + 0.3 * lead ** 3)
assert np.abs(coupled.residuals(free, outer) - sites.residuals(expanded, outer)).max() < 1e-5, "follower not coupled"
constant = _taped.TapedSites(model, [1, 3, 3], [1.0, 2.0, 0.5],
                             [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]], turns, None, ([0, 2], [2]))
moved_inner = np.concatenate([pose, [0.02, -0.01, 0.03, 0.0, 0.04, -0.02, 0.01, 0.02, -0.03]])
constant.gradient(moved_inner, outer)
constant_taped = constant.gradient(moved_inner, outer)
def constant_cost(moved):
    found = constant.residuals(moved, outer)
    return 0.5 * float(found @ found)
width = len(moved_inner)
constant_differences = np.array([(constant_cost(moved_inner + step * np.eye(width)[axis])
                                  - constant_cost(moved_inner - step * np.eye(width)[axis])) / (2 * step)
                                 for axis in range(width)])
assert np.abs(constant_differences[-3:]).max() > 1e-3, "inside joint's move not in the cost"
gaps = [np.abs(taped - differences).max() / np.abs(differences).max(),
        np.abs(coupled_taped - coupled_differences).max() / np.abs(coupled_differences).max(),
        np.abs(constant_taped - constant_differences).max() / np.abs(constant_differences).max()]
from scipy.spatial.transform import Rotation  # noqa: E402
turn = np.array([0.04, -0.02, 0.03])
turned_by_hand = [list(offset) for offset in turns[3]]
turned_by_hand[1] = list((Rotation.from_rotvec(-turn) * Rotation.from_quat(turns[3][1])).as_quat())
rebuilt = _taped.TapedSites(model, [1, 3, 3], [1.0, 2.0, 0.5], [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]],
                            (*turns[:3], turned_by_hand))
unturned = sites.gradient(pose, outer)
turned = _taped.turned_offsets(sites, {1: turn}, lambda: sites.gradient(pose, outer))
expected = rebuilt.gradient(pose, outer)
assert np.abs(turned - unturned).max() > 1e-4, "the turned offset does not reach the gradient"
gaps.append(np.abs(turned - expected).max() / np.abs(expected).max())
gaps.append(np.abs(sites.gradient(pose, outer) - unturned).max() / np.abs(unturned).max())
print("TURNED", gaps[-2], "PUT BACK", gaps[-1])
batch_builder = newton.ModelBuilder()
for copy in range(2):
    parent = -1
    for index in range(4):
        body = batch_builder.add_link(mass=1.0)
        place = wp.transform(wp.vec3(0.0, 0.0, 0.3 if index else 0.0), wp.quat_identity())
        axis = (1.0, 0.0, 0.0) if index % 2 == 0 else (0.0, 1.0, 0.0)
        batch_builder.add_joint_revolute(parent, body, parent_xform=place, axis=axis)
        parent = body
    batch_builder.add_articulation(list(range(4 * copy, 4 * copy + 4)))
batch_model = batch_builder.finalize(device="cuda:0", requires_grad=True)
batch_targets = [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8], [0.2, 0.1, 0.4], [0.1, -0.1, 0.9], [-0.1, 0.2, 0.7]]
batched = _taped.TapedSites(batch_model, [1, 3, 3, 5, 7, 7], [1.0, 2.0, 0.5, 1.0, 2.0, 0.5], batch_targets, None, None,
                            ([[0, 2], [3, 5]], [[2], [6]]))
second_pose = np.array([-0.1, 0.3, 0.2, -0.4])
batch_inner = np.concatenate([pose, second_pose, moved_inner[4:]])
batch_outer = np.concatenate([outer, outer])
batched.gradient(batch_inner, batch_outer)
batch_taped = batched.gradient(batch_inner, batch_outer)
def batch_cost(moved):
    found = batched.residuals(moved, batch_outer)
    return 0.5 * float(found @ found)
batch_width = len(batch_inner)
batch_differences = np.array([(batch_cost(batch_inner + step * np.eye(batch_width)[axis])
                               - batch_cost(batch_inner - step * np.eye(batch_width)[axis])) / (2 * step)
                              for axis in range(batch_width)])
assert np.abs(batch_differences[8:11]).max() > 1e-3, "a free site's move not in the batched cost"
gaps.append(np.abs(batch_taped - batch_differences).max() / np.abs(batch_differences).max())
trusted = _taped.TapedSites(model, [1, 3, 3], [9.0, 9.0, 9.0],
                            [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]], turns, trusted=True)
trust = np.array([1.0, 2.0, 0.5])
assert np.abs(trusted.residuals(pose, np.concatenate([outer, trust])) - sites.residuals(pose, outer)).max() < 1e-6, \
    "trust not read from the outer unknowns"
doubled = trusted.residuals(pose, np.concatenate([outer, 2 * trust]))
assert np.abs(doubled[:9] - 2 * sites.residuals(pose, outer)[:9]).max() < 1e-5, "trust not scaling its site's rows"
trusted_outer = np.concatenate([outer, trust])
trusted.gradient(pose, trusted_outer)
trusted_taped = trusted.gradient(pose, trusted_outer)
def trusted_cost(moved):
    found = trusted.residuals(moved, trusted_outer)
    return 0.5 * float(found @ found)
trusted_differences = np.array([(trusted_cost(pose + step * np.eye(4)[axis])
                                 - trusted_cost(pose - step * np.eye(4)[axis])) / (2 * step) for axis in range(4)])
gaps.append(np.abs(trusted_taped - trusted_differences).max() / np.abs(trusted_differences).max())
ended = _taped.TapedSites(model, [1, 3, 3], [9.0, 9.0, 9.0],
                          [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]], turns, trusted=True, ends=1)
landmarks, end_weight, goal = np.array([1.0, 2.0]), 0.5, 3.0
all_trusts = np.array([1.0, 2.0, 0.5 * 1.5])
by_hand = np.sqrt(goal * all_trusts / all_trusts.sum())
ended_rows = ended.residuals(pose, np.concatenate([outer, landmarks, [end_weight, goal]]))
assert np.abs(ended_rows - trusted.residuals(pose, np.concatenate([outer, by_hand]))).max() < 1e-5, \
    "end weight and marker goal not read from the outer unknowns"
goal_doubled = ended.residuals(pose, np.concatenate([outer, landmarks, [end_weight, 2 * goal]]))
assert np.abs(goal_doubled[:9] - np.sqrt(2) * ended_rows[:9]).max() < 1e-5, "marker goal not scaling every site"
frame_targets = [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]]
copied = _taped.TapedSites(batch_model, [1, 3, 3, 5, 7, 7], [9.0] * 6, frame_targets * 2, trusted=True, ends=1, copies=2)
copied_outer = np.concatenate([outer, landmarks, [end_weight, goal]])
copied_inner = np.concatenate([pose, second_pose])
by_copy = np.concatenate([ended.residuals(pose, copied_outer)[:9], ended.residuals(second_pose, copied_outer)[:9]])
assert np.abs(copied.residuals(copied_inner, copied_outer) - by_copy).max() < 1e-5, "a copy's ends not its own last sites"
copied.gradient(copied_inner, copied_outer)
copied_taped = copied.gradient(copied_inner, copied_outer)
def copied_cost(moved):
    found = copied.residuals(moved, copied_outer)
    return 0.5 * float(found @ found)
copied_differences = np.array([(copied_cost(copied_inner + step * np.eye(8)[axis])
                                - copied_cost(copied_inner - step * np.eye(8)[axis])) / (2 * step) for axis in range(8)])
gaps.append(np.abs(copied_taped - copied_differences).max() / np.abs(copied_differences).max())
def outer_gap(taped_sites, inner, at):
    """The outer gradient's largest gap to central differences of the cost over every outer unknown."""
    def outer_cost(moved):
        found = taped_sites.residuals(inner, moved)
        return 0.5 * float(found @ found)
    eye = np.eye(len(at))
    differences = np.array([(outer_cost(at + step * eye[axis]) - outer_cost(at - step * eye[axis])) / (2 * step)
                            for axis in range(len(at))])
    taped_sites.outer_gradient(inner, at)
    return np.abs(taped_sites.outer_gradient(inner, at) - differences).max() / np.abs(differences).max()
gaps.append(outer_gap(ended, pose, np.concatenate([outer, landmarks, [end_weight, goal]])))
gaps.append(outer_gap(copied, copied_inner, copied_outer))
print("OUTER", gaps[-2:])
sys.path.insert(0, str(pathlib.Path(sys.argv[1]).parent.parent))
from _bodies import Pinned, level3_body  # noqa: E402
from tuning._adjoint import mixed  # noqa: E402
class Unturned:
    """`RootTurns`' chart as the identity, for a chain with no free root."""
    def __init__(self, pose):
        self.full_pose, self.per_copy = np.asarray(pose, dtype=float), len(pose) + 1
    def reduced(self):
        return self.full_pose.copy()
    def full(self, reduced):
        return np.asarray(reduced, dtype=float)
    def pulled(self, reduced, gradient):
        return np.asarray(gradient, dtype=float)
picks = np.random.default_rng(3).normal(size=(13, 2)) * 0.05
picked_at = np.concatenate([outer, landmarks, [end_weight, goal]])
chain = level3_body("chain", ended, Unturned(pose), Pinned(pose, np.zeros(4, dtype=bool)),
                    lambda theta: picked_at + picks @ theta, 2, 1, columns=picks, step=step)
lifted = np.random.default_rng(4).normal(size=(4, 3))
by_mixed = lifted.T @ mixed(chain.gradient, pose, np.zeros(2), step)
products = chain.products(pose, np.zeros(2), lifted)
print("PRODUCTS", np.abs(products - by_mixed).max() / np.abs(by_mixed).max())
gaps.append(np.abs(products - by_mixed).max() / np.abs(by_mixed).max())
low, high = np.array([-0.05, -0.08, 0.0]), np.array([0.11, 0.08, 1.2])  # a box skin about the chain (MuJoCo's frame)
box = [[(low, high)[corner >> 2 & 1][0], (low, high)[corner >> 1 & 1][1], (low, high)[corner & 1][2]] for corner in range(8)]
box_faces = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4],
             [1, 5, 7], [1, 7, 3]]
skinned = _taped.TapedSites(model, [1, 3, 3], [1.0, 2.0, 0.5], [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]], turns,
                            skin=([2, 3, 3, 1], [[0.05, 0.0, 0.15], [0.0, 0.0, 0.1], [0.14, 0.02, 0.1], [0.0, 0.12, 0.0]],
                                  [(box, box_faces)], [0, 0, 0, 0], 3.0))
skinned.gradient(pose, outer)
skin_taped = skinned.gradient(pose, outer)
skin_rows = skinned.residuals(pose, outer)[-4:]
assert (skin_rows > 1e-3).any() and (skin_rows == 0).any(), f"the skin's points are not some outside, some in: {skin_rows}"
def skinned_cost(moved):
    found = skinned.residuals(moved, outer)
    return 0.5 * float(found @ found)
skin_differences = np.array([(skinned_cost(pose + step * np.eye(4)[axis]) - skinned_cost(pose - step * np.eye(4)[axis]))
                             / (2 * step) for axis in range(4)])
assert np.abs(skin_differences - differences).max() > 1e-3, "the skin rows do not reach the cost"
gaps.append(np.abs(skin_taped - skin_differences).max() / np.abs(skin_differences).max())
print("SKIN", gaps[-1], skin_rows.tolist())
half, out = 0.1, (0.01, 0.0101)  # an L prism's inner crease, the bone point just off its bisector (MuJoCo's frame)
profile = [(-half, -half), (half, -half), (half, 0.0), (0.0, 0.0), (0.0, half), (-half, half)]
skinned.skin.held = False
skinned.residuals(pose, outer)
crease = skinned.skin.placed.numpy()[0].astype(float) - np.array([out[0], out[1], 0.0])
prism = [[crease[0] + x, crease[1] + y, crease[2] + z] for z in (-half, half) for x, y in profile]
prism_faces = ([[0, corner + 1, corner] for corner in range(1, 5)]
               + [[6, 6 + corner, 6 + corner + 1] for corner in range(1, 5)]
               + [face for edge in range(6) for face in ([edge, (edge + 1) % 6, 6 + (edge + 1) % 6],
                                                         [edge, 6 + (edge + 1) % 6, 6 + edge])])
creased = _taped.TapedSites(model, [1, 3, 3], [1.0, 2.0, 0.5], [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]],
                            turns, skin=([2], [[0.05, 0.0, 0.15]], [(prism, prism_faces)], [0], 3.0))
free = creased.gradient(pose, outer)
creased.hold_skin(pose, outer)
held = creased.gradient(pose, outer)
assert creased.residuals(pose, outer)[-1] > 1e-3, "the creased point is not outside"
def columns(at):
    return np.stack([(creased.gradient(pose + at * np.eye(4)[axis], outer)
                      - creased.gradient(pose - at * np.eye(4)[axis], outer)) / (2 * at) for axis in range(4)], axis=1)
held_steps = np.abs(columns(1e-3) - columns(2.5e-4)).max() / np.abs(columns(2.5e-4)).max()
creased.skin.held = False
switching = np.abs(columns(1e-3) - columns(2.5e-4)).max() / np.abs(columns(2.5e-4)).max()
assert switching > 1e-2, f"the point's nearest sheet does not switch within the steps ({switching})"
gaps += [held_steps, np.abs(held - free).max() / np.abs(free).max()]
print("CREASE held steps", held_steps, "found each time", switching, "held gradient", gaps[-1])
print("GAP", max(gaps))
