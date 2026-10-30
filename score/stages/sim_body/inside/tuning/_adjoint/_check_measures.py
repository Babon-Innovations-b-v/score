"""The taped measures test's run in Newton's own Python (`python _check_measures.py <this folder>`): prints JSON of
the taped measures and their nudged values."""
import sys, json, numpy as np, warp as wp, newton
sys.path.insert(0, sys.argv[1])
import _taped, _measures
builder = newton.ModelBuilder()
for copy in range(3):
    parent = -1
    for index in range(4):
        body = builder.add_link(mass=1.0)
        place = wp.transform(wp.vec3(0.0, 0.0, 0.3 if index else 0.0), wp.quat_identity())
        builder.add_joint_revolute(parent, body, parent_xform=place, axis=(1.0, 0.0, 0.0) if index % 2 == 0 else (0.0, 1.0, 0.0))
        parent = body
    builder.add_articulation(list(range(4 * copy, 4 * copy + 4)))
model = builder.finalize(device="cuda:0", requires_grad=True)
sites = _taped.TapedSites(model, [1], [1.0], [[0.0, 0.0, 0.5]])
to_own = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]
joints = {"LeftLeg": ([[(4 * frame + 3, (0.0, 0.05, 0.1), 1.0)] for frame in range(3)], [[0.1, 0.8, -0.1], [0.0, 0.9, 0.0], [0.2, 0.7, 0.1]]),
          "Hips": ([[(4 * frame + 1, (0.02, 0.0, 0.0), 0.5), (4 * frame + 2, (0.0, 0.03, 0.0), 0.5)] for frame in range(3)],
                   [[0.05, 0.4, 0.0], [0.0, 0.45, 0.02], [0.03, 0.5, -0.02]])}
turns = {"LeftLeg": ([3, 7, 11], [0.05, 0.0, 0.0, 0.99875], [[0.1, 0.2, 0.0, 0.9747], [0.0, -0.3, 0.1, 0.9487], [0.2, 0.1, 0.1, 0.9695]]),
         "Hips": ([1, 5, 9], [0.0, 0.0, 0.0, 1.0], [[0.0, 0.1, 0.3, 0.9487], [0.1, 0.0, -0.2, 0.9747], [0.3, 0.0, 0.0, 0.9539]])}
def column(middle):
    low, high = np.array(middle) - [0.08, 0.6, 0.08], np.array(middle) + [0.08, 0.6, 0.08]
    verts = [[(low, high)[corner >> 2 & 1][0], (low, high)[corner >> 1 & 1][1], (low, high)[corner & 1][2]] for corner in range(8)]
    faces = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]
    return verts, faces
posed = [column([0.0, 0.55, 0.0]), column([0.02, 0.55, 0.0]), column([-0.02, 0.5, 0.01])]
skins = {"shin": ([[(4 * frame + 3, (0.05, 0.0, 0.15)), (4 * frame + 2, (0.0, 0.0, 0.1))] for frame in range(3)], posed),
         "thigh": ([[(4 * frame + 1, (0.0, 0.02, 0.05))] for frame in range(3)], posed)}
measures = _measures.TapedMeasures(sites, joints, to_own, turns, skins)
pose = np.array([0.2, 0.4, -0.3, 0.6, 0.1, -0.5, 0.3, 0.2, -0.2, 0.3, 0.5, -0.4])
outer = np.zeros(3)
def plain(found):
    return {kind: {key: [value[0].tolist(), value[1].tolist()] for key, value in part.items()} for kind, part in zip(("joints", "turns", "skins"), found)}
step, nudged = 1e-3, []
for column in range(len(pose)):
    for sign in (1, -1):
        moved = pose.copy(); moved[column] += sign * step
        nudged.append({kind: {key: value[0] for key, value in part.items()} for kind, part in plain(measures.measured(moved, outer)).items()})
print("JSON" + json.dumps({"taped": plain(measures.measured(pose, outer)), "nudged": nudged, "step": step}))
