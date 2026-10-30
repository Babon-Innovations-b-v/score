"""The taped gradient test's run in Newton's own Python (`python _check_taped.py <this folder>`): prints GAP, the
largest gap to central differences."""
import sys, numpy as np, warp as wp, newton
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
print("GAP", max(gaps))
