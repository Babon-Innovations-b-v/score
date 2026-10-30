"""The toy problems the adjoint's test drives (two-level poses and constants, level 2's constants-first Problem, a
toy case's measures and their central differences, a toy landmark table); test support only, never imported by the
adjoint's modules."""

import numpy as np
import scipy.optimize

from score.stages.sim_body.inside.tuning import _adjoint


FRAMES, POSE, CONSTANTS, SPREAD = 4, 2, 2, 0.3
TIMES = np.linspace(0.0, 1.0, FRAMES)


def parts(inner, outer):
    poses = inner[: FRAMES * POSE].reshape(FRAMES, POSE)
    constants = inner[FRAMES * POSE:]
    first, second = poses[:, 0], poses[:, 1]
    sine = np.sin(first) + constants[0] - outer[0] * (1 + TIMES)
    product = first * second + constants[1] - outer[1]
    return poses, constants, first, second, sine, product


def gradient(inner, outer):
    poses, constants, first, second, sine, product = parts(inner, outer)
    along_first = sine * np.cos(first) + product * second + (first - 0.5)
    along_second = product * first + (second - outer[2])
    by_constants = [sine.sum() + SPREAD * constants[0], product.sum() + SPREAD * constants[1]]
    return np.concatenate([np.stack([along_first, along_second], axis=1).ravel(), by_constants])


def cost(inner, outer):
    poses, constants, first, second, sine, product = parts(inner, outer)
    return 0.5 * (np.sum(sine ** 2) + np.sum(product ** 2) + np.sum((second - outer[2]) ** 2)
                  + np.sum((first - 0.5) ** 2) + SPREAD * np.sum(constants ** 2))


def residuals(inner, outer):
    poses, constants, first, second, _, _ = parts(inner, outer)
    return np.concatenate([first + second - outer[2], first * constants[0], [constants[1] * outer[1]]])


def solved(outer):
    found = scipy.optimize.minimize(cost, np.full(FRAMES * POSE + CONSTANTS, 0.2), args=(outer,), jac=gradient,
                                    method="BFGS", options={"gtol": 1e-13, "maxiter": 10000})
    return found.x


OUTER = np.array([0.4, 0.9, -0.3])


def toy_rows(inner, outer):
    """The toy residuals' exact R_z and R_theta, written out by hand (standing in for taped rows)."""
    poses, constants, first, _, _, _ = parts(inner, outer)
    by_inner, by_outer = np.zeros((2 * FRAMES + 1, len(inner))), np.zeros((2 * FRAMES + 1, len(outer)))
    for frame in range(FRAMES):
        by_inner[frame, [frame * POSE, frame * POSE + 1]] = 1.0
        by_inner[FRAMES + frame, frame * POSE] = constants[0]
        by_inner[FRAMES + frame, FRAMES * POSE] = first[frame]
    by_outer[:FRAMES, 2] = -1.0
    by_inner[2 * FRAMES, FRAMES * POSE + 1] = outer[1]
    by_outer[2 * FRAMES, 1] = constants[1]
    return by_inner, by_outer


def body(name, inner):
    return _adjoint.Body(name, residuals, gradient, inner, FRAMES, POSE)


def prior(outer):
    return outer ** 2


def differences(unknowns):
    times = np.linspace(0.0, 1.0, 5)[:, None]
    return np.concatenate([np.sin(unknowns[0] + 3 * times), unknowns[1] * times + 0.2, np.cos(unknowns[2] * (1 + times))],
                          axis=1)


def outer_values(unknowns):
    lengths, _ = _adjoint.distance_rows(differences(unknowns), np.zeros((5, 3, 3)))
    return np.array([np.median(lengths), np.sqrt(np.mean(np.square(lengths)))])


TABLE = {"knee_l": {"segment": "LeftLeg", "solver": True, "trust": 2.0, "link": [0.1, 0.2, 0.3]},
          "knee_r": {"segment": "RightLeg", "solver": True, "trust": 2.0, "link": [0.1, 0.2, -0.3]},
          "hip": {"segment": "Hips", "solver": False, "trust": 1.0, "link": [0.0, 0.1, 0.0]}}
STARTS = {name: row["link"] for name, row in TABLE.items()}
GLOBALS = {"marker goal": 3.0, "end weight": 0.5}
TURN = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
ENDS = [("LeftUpLeg", np.array([0.0, -0.4, 0.0]), TURN)]
LANDMARKS = ["knee_l", "knee_r", "hip"]


def followed(couplings, pose):
    """joint_q from a free pose as `_taped._Couplings.write` lays it (base, free coordinates, followers)."""
    free, followers, leaders, follower_rest, leader_rest, poly, base = couplings
    found = base.copy()
    found[free] = pose
    for follower, leader, rest, lead_rest, terms in zip(followers, leaders, follower_rest, leader_rest, poly):
        found[follower] = rest + np.polyval(terms[::-1], pose[leader] - lead_rest if leader >= 0 else 0.0)
    return found


def measured(unknowns):
    """A toy case's taped per-frame measures as functions of a 3-unknown inner pose (metres and degrees)."""
    lean = differences(unknowns)
    return {"joints": {"LeftLeg": 0.01 * lean, "Hips": 0.02 * lean[::-1] + 0.005},
            "turns": {"Hips": 4 + 3 * lean[:, 0] * lean[:, 1], "LeftLeg": 6 + 2 * lean[:, 2]},
            "skins": {"pelvis": 0.002 * lean[:, 1], "thigh": 0.001 * (lean[:, 0] + 2)}}


def found(unknowns):
    taken = measured(unknowns)
    return {"per joint mm": {key: [np.median(1000 * np.linalg.norm(value, axis=1))]
                             for key, value in taken["joints"].items()},
            "per group deg": {key: [np.median(value)] for key, value in taken["turns"].items()},
            "bones outside depth mm": {key: 1000 * np.sqrt(np.mean(np.square(value)))
                                       for key, value in taken["skins"].items()}}


def case_found(joints, turns, skins):
    """`case_residuals`' measures of per-frame joint differences (m), turn degrees and bone points' depths outside (m)."""
    return {"per joint mm": {key: [np.median(1000 * np.linalg.norm(value, axis=1))] for key, value in joints.items()},
            "per group deg": {key: [np.median(value)] for key, value in turns.items()},
            "bones outside depth mm": {key: 1000 * np.sqrt(np.mean(np.square(value))) for key, value in skins.items()}}


def taped_parts(found, key):
    """A measures check's JSON `found[key]` as `case_rows`' joints, turns and skins (each value's parts as arrays)."""
    return [{name: tuple(np.array(part) for part in value) for name, value in found[key][kind].items()}
            for kind in ("joints", "turns", "skins")]


def nudged_differences(nudged, step):
    """Central differences of `case_residuals` over a measures check's nudged measures (each column +step, then -step)."""
    from score.stages.sim_body.inside.tuning import case_residuals
    scored = [case_residuals(case_found(*({key: np.array(value) for key, value in nudge[kind].items()}
                                          for kind in ("joints", "turns", "skins")))) for nudge in nudged]
    return np.stack([(scored[2 * column] - scored[2 * column + 1]) / (2 * step) for column in range(len(scored) // 2)], axis=1)


SEEN, TOLD = 3, np.array([True, False])
SEEN_TIMES = np.linspace(0.2, 0.8, SEEN)


def seen_parts(poses, outer):
    first, second, constants = poses[:, 0], poses[:, 1], outer[3:]
    sine = np.sin(first) + constants[0] - outer[0] * (1 + SEEN_TIMES)
    product = first * second + constants[1] - outer[1]
    return first, second, sine, product


def seen_gradient(inner, outer):
    first, second, sine, product = seen_parts(inner.reshape(SEEN, POSE), outer)
    along_first = sine * np.cos(first) + product * second + (first - 0.5)
    return np.stack([along_first, product * first + (second - outer[2])], axis=1).ravel()


def seen_cost(inner, outer):
    first, second, sine, product = seen_parts(inner.reshape(SEEN, POSE), outer)
    return 0.5 * (np.sum(sine ** 2) + np.sum(product ** 2) + np.sum((second - outer[2]) ** 2)
                  + np.sum((first - 0.5) ** 2))


def seen_residuals(inner, outer):
    poses = inner.reshape(SEEN, POSE)
    return np.concatenate([poses[:, 0] + poses[:, 1] - outer[2], poses[:, 0] * outer[3], [outer[4] * outer[1]]])


def level2_told(outer, untold):
    """Level 2 re-solved with the untold constant held at `untold`: its poses and constants."""
    count = FRAMES * POSE + int(TOLD.sum())

    def whole(point):
        return np.concatenate([point, [untold]])

    found = scipy.optimize.minimize(lambda point: cost(whole(point), outer), np.full(count, 0.2),
                                    jac=lambda point: gradient(whole(point), outer)[:count], method="BFGS",
                                    options={"gtol": 1e-13, "maxiter": 10000})
    return whole(found.x)


def chain_re_solved(outer, untold):
    constants = level2_told(outer, untold)[FRAMES * POSE:]
    joined = np.concatenate([outer, constants])
    found = scipy.optimize.minimize(seen_cost, np.full(SEEN * POSE, 0.2), args=(joined,), jac=seen_gradient,
                                    method="BFGS", options={"gtol": 1e-13, "maxiter": 10000})
    return seen_residuals(found.x, joined)


def seen_rows(inner, joined):
    """Level 3's residual rows by hand: over the poses, over theta, over the constants."""
    poses = inner.reshape(SEEN, POSE)
    by_poses = np.zeros((2 * SEEN + 1, SEEN * POSE))
    by_joined = np.zeros((2 * SEEN + 1, joined.size))
    for frame in range(SEEN):
        by_poses[frame, frame * POSE:frame * POSE + 2] = 1.0
        by_poses[SEEN + frame, frame * POSE] = joined[3]
        by_joined[frame, 2] = -1.0
        by_joined[SEEN + frame, 3] = poses[frame, 0]
    by_joined[-1, 1], by_joined[-1, 4] = joined[4], joined[1]
    return by_poses, by_joined[:, :3], by_joined[:, 3:]


def chain_bodies():
    """The chain toy's level 2 (untold constant pinned) and level 3 Bodies at their optima, and the untold value."""
    from score.stages.sim_body.inside.tuning._adjoint import _bodies
    untold = solved(OUTER)[-1]
    level2_inner = level2_told(OUTER, untold)
    held = np.zeros(level2_inner.size, dtype=bool)
    held[FRAMES * POSE:] = ~TOLD
    pinned = _bodies.Pinned(level2_inner, held)
    level2 = _adjoint.Body("level 2", None, lambda point, outer: pinned.gradient(
        point, gradient(pinned.whole(point), outer)), level2_inner, FRAMES, POSE)
    joined = np.concatenate([OUTER, level2_inner[FRAMES * POSE:]])
    level3_inner = scipy.optimize.minimize(seen_cost, np.full(SEEN * POSE, 0.2), args=(joined,), jac=seen_gradient,
                                           method="BFGS", options={"gtol": 1e-13, "maxiter": 10000}).x
    level3 = _adjoint.Body("level 3", seen_residuals, seen_gradient, level3_inner, SEEN, POSE)
    return level2, level3, untold


class ConstantsFirst:
    """A toy `fit/_constants.Problem`: its unknowns the constants first (c0 told, c1 untold), then three frames' two
    coordinates, frame 0's second bounded below at 0.5 (held there), a prior row per constant; `outer` level 1's."""
    slots, path, width, LOW = np.arange(2), np.zeros(3), 2, 0.5

    def __init__(self, outer):
        self.outer = np.asarray(outer, dtype=float)

    def bounds(self):
        low, high = np.full(8, -np.inf), np.full(8, np.inf)
        low[3] = self.LOW
        return low, high

    def residuals(self, unknowns):
        first, second = unknowns[2::2], unknowns[3::2]
        told, untold = unknowns[0], unknowns[1]
        found = [np.stack([first + told - self.outer[0] * np.arange(1, 4), second + told * first - self.outer[1],
                           0.5 * first * second - 0.2 * self.outer[0] + untold], axis=1).ravel(), 0.5 * unknowns[:2]]
        return np.concatenate(found)

    def jacobian(self, unknowns):
        rows = np.zeros((11, 8))
        for frame in range(3):
            first, second = unknowns[2 + 2 * frame], unknowns[3 + 2 * frame]
            at = 2 + 2 * frame
            rows[3 * frame, [0, at]] = 1.0
            rows[3 * frame + 1, [0, at, at + 1]] = first, unknowns[0], 1.0
            rows[3 * frame + 2, [1, at, at + 1]] = 1.0, 0.5 * second, 0.5 * first
        rows[9, 0], rows[10, 1] = 0.5, 0.5
        return rows


def constants_first_solved(outer, untold=0.1):
    """The toy level 2 re-solved at `outer` (Problem order), the untold constant held at `untold`."""
    problem = ConstantsFirst(outer)
    low, high = problem.bounds()
    kept = np.array([0, 2, 3, 4, 5, 6, 7])

    def whole(values):
        found = np.full(8, untold)
        found[kept] = values
        return found

    found = scipy.optimize.least_squares(lambda values: problem.residuals(whole(values)), np.full(7, 0.6),
                                         jac=lambda values: problem.jacobian(whole(values))[:, kept],
                                         bounds=(low[kept], high[kept]), xtol=1e-15, ftol=1e-15, gtol=1e-15)
    return whole(found.x), kept
