"""fit/_card: on 12 rows (frames) of a small chain (20 hinge dofs, two frozen, two followers on one leader and one
without a leader, bounds with some rows sitting on them), seeded alike, one step at a time: the card's damped reduced
step equals the CPU prototype's (card/proto/lm.py: mink's damping 1e-2 |r|^2 + 1e-9 on every full dof, so S^T S in
the reduced dofs (a leader's damping times 1 plus its followers' slopes squared), frozen out, followers through
their coupling's slope, three active-set passes holding dofs at a bound that push out, a held one released when its descent points back inside) to 1e-5 rad, and
the card's projection equals the prototype's (ranges, couplings by polyval, frozen) with every follower on polyval of
its leader to 1e-6 rad and every coordinate inside its range. Rows whose dofs are held must exist (else the hold is
not tested). On a six-link hinge chain, the per-problem place and turn objectives (_objective.py) give the residuals
and analytic Jacobian of Newton's own IKObjectivePosition and IKObjectiveRotation made with each row's offset and
weight, the turn's Jacobian through the log's inverse left Jacobian (mink's exact one, Newton's is the spin alone), to
1e-6. Runs in Newton's own Python on a CUDA card; with no Newton env or no card it prints `skipped`. On a toy MJCF (a
free root, three ranged hinges, a follower coupled by polyval in its own body, a frozen hinge), the card loop on a
10-frame clip, each row seeded as mink's frame was, equals mink (../_frames.solved, targets set as _frames.Frames sets
them) to 0.01 deg and its sites to 0.01 mm, with a frame holding h1 at its range; in chunks of 3 rows it equals
itself in one batch. Seeded from that clip's answers (its angles.npz, `_seeds`) with the places 3 mm on, the card
equals mink's answer to the moved clip to 0.01 deg and 0.01 mm (a cold seed only reported). On a toy body
(`card_body.py`), the card's measures (_measure.py) equal evaluation._measure's to 1e-9 (joints mm, turns deg) and
its bones-outside shares exactly (every point's count), their depths outside (level 1's skin residual, the same
kernel on both devices) to DEPTH_MM. On fit's own toy (`card_level2.py`), level 2's exact
Jacobian (_level2.py) equals its residuals' central differences to 1e-6 of each column's largest entry from the
host's kinematics, to 1e-5 from the card's (_level2_card.py), nothing outside `Problem.sparsity`; level 2 solved with it (`_constants.staged(jacobian=...)`) from a path moved
0.05 off equals the 2-point solve to 1e-3 mm and 1e-4 deg.

Breaks (each applied once, seen red, reverted):
- (2026-10-29) _kept's release `wp.where(inside, 1.0, 0.0)` made `0.0` (holds only added): rows 0 and 1 keep dof 0
  held on its bound though its descent points inside, the step 1 rad off.
- (2026-10-29) _step's `LM_DAMPING * squared + DAMPING` made `DAMPING`: mink's damping is lost, the step differs.
- (2026-10-29) _normal_equations' `* spread` dropped (damping lambda I in the reduced dofs, not mink's S^T S): the
  step differs from the prototype's by 7.7e-5 rad; on heavy_squat cache 3 mm row 148 swung elv_angle_r 1 rad a step.
- (2026-10-29) _reduced_jacobian's `* slopes[row, coupling]` dropped: followers ride their leader at slope 1.
- (2026-10-29) _clip's joint types compared as mjtJoint enums with the model's ints (never equal): no range held,
  the toy's clip 27 deg and 55 mm off mink's.
- (2026-10-29) _step's `HOLD_PASSES = 3` made `0`: a dof at its bound is not held; the clip's rows never stop.
- (2026-10-29) _kept's `keep[row, column]` made `1.0`: a hold from an earlier pass is let go, the step differs.
- (2026-10-29) _turn_jacobian's `rate[axis]` made `motion[3 + axis]` (Newton's spin alone): the turn's
  Jacobian is no longer the log's exact one.
- (2026-10-29) solved_in_chunks' `values[start:stop]` made `values[:stop - start]`: every chunk solves the first rows.
- (2026-10-29) _measure.joint_table's `* scales[bone]` dropped: the joints miss by the unscaled offset.
- (2026-10-29) _measure.skin_shares' "hand" merge dropped: the hand's parts are scored apart, the keys differ.
- (2026-10-30) _per_row._per_row_fk's `set_places[row_set[problem_idx]]` made `set_places[0]`: every row takes
  the first set's joint places, sets 1 and 2 off theirs alone by 0.05-0.08 m (card_rows: per-row FK, rows = set x
  frame, equals Newton's eval_fk_batched on each set alone bit for bit).
- (2026-10-30) _per_row.rowwise's `optimizer._compute_motion_subspace = motion_subspace` dropped: the Jacobian
  reads the model's one joint places, sets 1 and 2's columns off theirs alone by 0.025-0.035 (card_rows).
- (2026-10-30) _forward._frames' `joint_x_p[row_set[row], joint]` made `joint_x_p[0, joint]`: the float64 frames take
  the first set's places, sets 1 and 2 off theirs alone by 0.056-0.074 m (card_rows).
- (2026-10-30) _solve.solved's `Forward(optimizer.model, set_places, row_set)` made `Forward(optimizer.model)`: the
  float64 residuals read the base set's places, sets 1 and 2 off theirs alone by 4-9 deg and 4-19 mm (card_across:
  the toy's clip as 3 sets solved in one batch equals each set alone to 0.01 deg and 0.01 mm).
- (2026-10-30) _sets.Sets.optimizer_for's offsets of each set made the base set's (`base.mjm.site_pos`): sets 1
  and 2 solve with set 0's marker offsets, off their Clip alone (card_sets; also: sets whose frozen dofs differ are
  refused, `_sets.refusal` returning None lets them through).
- (2026-10-30) _measure.skin_depths' `depths[:, ...]` made `depths[:1, ...]`: the card's depths read the first skin
  frame only, off the CPU's.
- (2026-10-29) _projected's `power *= lead` made `power *= 1.0`: a coupling is no longer polyval of its leader.
- (2026-10-29) _turn_jacobian's `weight[problem] * rate[axis]` made `rate[axis]`: the weight is lost.
- (2026-10-29) _turn_residuals' angle `2 atan2(length, w) / length` made `2`: the turn is no longer the log map.
- (2026-10-29) _level2.dof_map's root `right_jacobian(rotation)` made `np.eye(3)`: the root's rotation-vector
  columns are off their differences.
- (2026-10-29) _level2.frame_rows' inside joint `body_turns[parent]` made `body_turns[fitting.inside[joint]]`: the
  knee's move columns are off.
- (2026-10-29) _level2_card.CardKinematics.frames' `body_pos.assign(...)` dropped: the card keeps the model's base
  inside joint places, the knee's move columns are off.
- (2026-10-29) _constants.staged's `jacobian(problem, unknowns)` made `jacobian(problem, begin)` (the Jacobian
  frozen at the start): the toy's constants 0.027 mm off the 2-point solve's.
- (2026-10-29) _solve's `CYCLE_STEP = 1e-5` made `0.0`: a seeded toy row cycles at its float32 pose's floor and never
  stops (NotConverged).

Run: .venv/bin/python score/stages/sim_body/inside/fit/_card/tests/test_the_card_step_and_projection_equal_the_cpu_prototype.py
"""
import os
import pathlib
import subprocess
import sys

INSIDE = pathlib.Path(__file__).resolve().parents[3]
IN_ENV = "SIM_BODY_INSIDE_TEST"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from card_chain import (LINKS, OBJECTIVE_ROWS, chain_model, log_rate, objective_rows,  # noqa: E402
                        residuals_and_jacobian)
from card_toy import CLIP_FRAMES, TOY, mink_frames, toy_card, toy_clip, toy_errors  # noqa: E402
from card_across import the_sets_solved_together_equal_each_set_alone  # noqa: E402
from card_sets import the_sets_batch_equals_each_clip_alone  # noqa: E402
from card_rows import (the_float64_frames_equal_each_set_alone, the_rows_equal_each_set_alone,  # noqa: E402
                       the_rowwise_optimizer_equals_each_set_alone)
from card_step import (BOUNDED, COUPLINGS, FROZEN, ROWS, fixture, prototype_projected,  # noqa: E402
                       prototype_step)
LEVEL2_CARD_MOST = 1e-5  # the same from the card's float32 kinematics (_level2_card)
LEVEL2_SOLVE_MM = 1e-3  # level 2 with jac=exact against 2-point differences on the exact toy: constants (the
LEVEL2_SOLVE_DEG = 1e-4  # plan's 0.05 mm / 0.01 deg is the real bodies'; a frozen Jacobian is 0.027 mm off here)
DEPTH_MM = 1e-4  # the depths' float32 closest points, card against CPU (measured 4.6e-6 mm on the toy, 2026-10-30)
LEVEL2_MOST = 1e-6  # a column's largest miss over its largest entry (measured 1.8e-10; the plan allows 1e-2 against 2-point)


def the_step_equals_the_prototype():
    import numpy as np
    import warp as wp
    from fit._card import Reduction, damped_step
    jacobian, residuals, qpos, rest, _, lower, upper = fixture()
    wanted, wanted_norms, held_rows, released, free = prototype_step(jacobian, residuals, qpos, rest, lower, upper)
    coupled = COUPLINGS
    reduction = Reduction(free, free, lower[free], upper[free], [c[0] for c in coupled], [c[1] for c in coupled],
                          [c[1] for c in coupled], [rest[c[1]] if c[1] >= 0 else 0.0 for c in coupled],
                          np.array([c[2] for c in coupled]), "cuda:0")
    card = lambda values: wp.array(values.astype(np.float32), dtype=wp.float32, device="cuda:0")
    active = wp.array(np.ones(ROWS, np.int32), dtype=wp.int32, device="cuda:0")
    full, norms = damped_step(reduction, card(jacobian), card(residuals), card(qpos), active)
    problems = []
    if held_rows == 0:
        problems.append("no row holds a dof at its bound: the fixture does not test the hold")
    if released == 0:
        problems.append("no held dof is released: the fixture does not test the active set's exit")
    miss = np.abs(full.numpy() - wanted).max()
    if miss > 1e-5:
        problems.append(f"step differs from the prototype's by {miss:.2e} rad (most 1e-5)")
    if np.abs(norms.numpy() - wanted_norms).max() > 1e-5:
        problems.append("step lengths differ from the prototype's")
    return problems


def the_projection_equals_the_prototype():
    import numpy as np
    import warp as wp
    from fit._card import Projection, project
    _, _, qpos, rest, seeds, lower, upper = fixture()
    stepped = qpos + np.random.default_rng(8).normal(scale=0.3, size=qpos.shape)
    stepped = stepped.astype(np.float32).astype(float)
    wanted = prototype_projected(stepped, rest, seeds, lower, upper)
    projection = Projection(lower, upper, [c[0] for c in COUPLINGS], [c[1] for c in COUPLINGS],
                            [rest[c[0]] for c in COUPLINGS], [rest[c[1]] if c[1] >= 0 else 0.0 for c in COUPLINGS],
                            np.array([c[2] for c in COUPLINGS]), list(FROZEN), "cuda:0")
    card = wp.array(stepped.astype(np.float32), dtype=wp.float32, device="cuda:0")
    project(projection, card, wp.array(seeds.astype(np.float32), dtype=wp.float32, device="cuda:0"))
    found = card.numpy().astype(float)
    problems = []
    if np.abs(found - wanted).max() > 1e-6:
        problems.append(f"projection differs from the prototype's by {np.abs(found - wanted).max():.2e} rad")
    for follower, leader, poly in COUPLINGS:
        lead = found[:, leader] - rest[leader] if leader >= 0 else 0.0
        miss = np.abs(found[:, follower] - rest[follower] - sum(poly[p] * lead ** p for p in range(5))).max()
        if miss > 1e-6:
            problems.append(f"follower {follower} off polyval of its leader by {miss:.2e} rad")
    leaders = [dof for dof in BOUNDED if dof not in {c[0] for c in COUPLINGS}]
    if (found[:, leaders] < lower[leaders]).any() or (found[:, leaders] > upper[leaders]).any():
        problems.append("a coordinate left its range")
    if not np.array_equal(found[:, list(FROZEN)], seeds[:, list(FROZEN)].astype(np.float32)):
        problems.append("a frozen coordinate moved off its seed")
    return problems


def the_objectives_equal_newtons_own_row_by_row():
    """Per-problem place and turn equal Newton's built-in objective made with that row's offset and weight, the turn's
    Jacobian Newton's spin rows through the log's inverse left Jacobian (mink's exact one)."""
    import numpy as np
    import warp as wp
    from newton import ik
    from fit._card import PlacePerProblem, TurnPerProblem
    model = chain_model()
    poses, offsets, turns, weights, places, wanted = objective_rows(model.joint_coord_count)
    link = LINKS - 1
    card = lambda values, kind: wp.array(values, dtype=kind, device="cuda:0")
    mine = residuals_and_jacobian(model, poses, [
        PlacePerProblem(link, card(offsets, wp.vec3), card(places, wp.vec3), card(weights, wp.float32)),
        TurnPerProblem(link, card(turns, wp.quat), card(wanted, wp.vec4), card(weights, wp.float32))])
    problems = []
    for row in range(OBJECTIVE_ROWS):
        theirs = residuals_and_jacobian(model, poses, [
            ik.IKObjectivePosition(link, wp.vec3(*offsets[row]), card(places, wp.vec3), weight=float(weights[row])),
            ik.IKObjectiveRotation(link, wp.quat(*turns[row]), card(wanted, wp.vec4), weight=float(weights[row]))])
        exact = theirs[1][row].copy()
        exact[3:] = log_rate(theirs[0][row][3:] / weights[row]) @ exact[3:]
        for name, found, reference in (("residuals", mine[0][row], theirs[0][row]),
                                       ("Jacobian", mine[1][row], exact)):
            if np.abs(found - reference).max() > 1e-6:
                problems.append(f"row {row}: {name} differ from Newton's by {np.abs(found - reference).max():.2e}")
    if np.abs(mine[0][:, 3:]).max() < 1e-3:
        problems.append("the turn residuals are all near zero: the fixture does not test the turn")
    return problems


CHUNK = 3  # solved_in_chunks' rows a chunk on the toy: three full chunks and one of one


def the_clip_equals_mink_frame_by_frame():
    """The card loop on the toy's clip, each row seeded as mink's frame was, equals mink's angles to 0.01 deg and its
    sites to 0.01 mm, and solved in chunks of CHUNK rows it equals itself in one batch to 1e-6 rad."""
    import mujoco
    import numpy as np
    import warp as wp
    from fit._card import solved, solved_in_chunks
    from fit._card._seeds import newton_order
    mjm = mujoco.MjModel.from_xml_string(TOY)
    turns, places = toy_clip(mjm)
    reference = mink_frames(mjm, turns, places)
    seeds = np.vstack([mjm.qpos0[None], reference[:-1]])
    optimizer_for, reduction, projection = toy_card(mjm, turns, places)
    card = lambda values, kind: wp.array(np.ascontiguousarray(values, dtype=np.float32), dtype=kind, device="cuda:0")
    hinge = lambda name: int(mjm.jnt_qposadr[mjm.joint(name).id])
    newton_seeds = newton_order(seeds)
    found, _ = solved(optimizer_for(0, CLIP_FRAMES), reduction, projection, card(newton_seeds, wp.float32),
                      card(seeds, wp.float32))
    found = found.numpy().astype(float)
    chunked, _ = solved_in_chunks(optimizer_for, reduction, projection, newton_seeds, seeds, chunk_rows=CHUNK)
    problems = [] if np.abs(chunked - found).max() <= 1e-6 else ["in chunks of 3 rows the clip differs from one batch"]
    miss, sites = toy_errors(mjm, found, reference)
    if miss > 0.01:
        problems.append(f"angles {miss:.4f} deg off mink's (plan: 0.01)")
    if sites > 0.01:
        problems.append(f"sites {sites:.4f} mm off mink's (plan: 0.01)")
    if not (reference[:, hinge("h1")] >= 1.2 - 1e-6).any():
        problems.append("no frame holds h1 at its range: the clip does not test the limit")
    return problems


def the_next_iteration_from_its_seeds_equals_mink():
    """Level 1's next iteration (the places 3 mm on, the turn cost 1.5 times) seeded from the last iteration's
    angles of each frame (read back from its angles.npz, `_seeds.first`, then `_seeds.kept`) equals mink's
    frame-by-frame answer to it to 0.01 deg and 0.01 mm; a cold seed (the rest pose every frame) is only reported."""
    import mujoco
    import numpy as np
    from fit._card import solved_in_chunks
    from fit._card import _seeds
    mjm = mujoco.MjModel.from_xml_string(TOY)
    turns, places = toy_clip(mjm)
    folder = pathlib.Path(os.environ["PROPS_HOME"]) / "seeds"
    (folder / "toy").mkdir(parents=True, exist_ok=True)
    np.savez(folder / "toy" / _seeds.SEEDS, qpos=mink_frames(mjm, turns, places))
    seeds = {"toy": _seeds.first(folder, "toy")}
    moved = places + np.array([0.003, -0.002, 0.001])
    reference = mink_frames(mjm, turns, moved)
    optimizer_for, reduction, projection = toy_card(mjm, turns, moved)
    found, _ = solved_in_chunks(optimizer_for, reduction, projection, _seeds.newton_order(seeds["toy"]),
                                seeds["toy"])
    seeds = _seeds.kept(seeds, "toy", found)
    miss, sites = toy_errors(mjm, seeds["toy"], reference)
    problems = [f"from its seeds: angles {miss:.4f} deg off mink's (plan: 0.01)"] if miss > 0.01 else []
    if sites > 0.01:
        problems.append(f"from its seeds: sites {sites:.4f} mm off mink's (plan: 0.01)")
    cold = np.tile(mjm.qpos0, (CLIP_FRAMES, 1))
    cold_found, _ = solved_in_chunks(optimizer_for, reduction, projection, _seeds.newton_order(cold), cold)
    print("cold seed (reported, not used): angles %.4f deg, sites %.4f mm off mink's" % toy_errors(
        mjm, cold_found, reference))
    return problems


def the_measures_equal_the_cpu_measure():
    import card_body
    import numpy as np
    from evaluation import _measure as cpu
    from fit._card import _measure as card
    clip = card_body.clip()
    slow, fast = cpu.measures(*clip), card.measures(*clip)
    keyed = [f"{key}: keys {sorted(fast[key])} against {sorted(slow[key])}" for key in fast
             if isinstance(fast[key], dict) and sorted(fast[key]) != sorted(slow[key])]
    return keyed or [f"{key}: {fast[key]} against {slow[key]}" for key in fast
                     if not np.allclose(np.ravel(_values(fast[key])), np.ravel(_values(slow[key])), rtol=0,
                                        atol=DEPTH_MM if key == "bones outside depth mm" else 1e-9)]


def the_level2_jacobian_equals_its_differences():
    import tempfile
    import card_level2
    import numpy as np
    from fit._card import _level2, _level2_card
    with tempfile.TemporaryDirectory() as folder:
        problem, unknowns = card_level2.problem_and_point(folder)
        card = _level2_card.CardKinematics(problem.fitting, len(problem.path))  # made at the start constants
        moved = card_level2.differences(problem, unknowns)
        outside = ~problem.sparsity().toarray().astype(bool)
        found = {"card": (_level2.jacobian(problem, unknowns, card).toarray(), LEVEL2_CARD_MOST),
                 "host": (_level2.jacobian(problem, unknowns).toarray(), LEVEL2_MOST)}
    problems = []
    for source, (exact, most) in found.items():
        worst = max(np.abs(exact[:, column] - moved[:, column]).max() / max(np.abs(moved[:, column]).max(), 1e-12)
                    for column in range(unknowns.size))
        problems += ([f"{source} Jacobian off its differences by {worst:.2e} of a column"] if worst > most else []) + (
            [f"{source} Jacobian outside the sparse pattern"] if np.abs(exact[outside]).max() > 0 else [])
    return problems


def the_level2_solve_with_the_exact_jacobian_equals_differences():
    import tempfile
    import card_level2
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        (moved, moved_angles, _), (exact, exact_angles, _) = card_level2.staged_both(folder)
    off_mm, off_angles = 1000 * np.abs(exact - moved).max(), np.abs(exact_angles - moved_angles).max()
    return ([f"level 2 with the exact Jacobian off differences' constants by {off_mm:.4f} mm"]
            if off_mm > LEVEL2_SOLVE_MM else []) + (
        [f"level 2 with the exact Jacobian off differences' angles by {off_angles:.2e}"]
        if off_angles > np.radians(LEVEL2_SOLVE_DEG) else [])


def _values(found):
    return [found[key] for key in sorted(found)] if isinstance(found, dict) else found


CHECKS = (the_rows_equal_each_set_alone, the_rowwise_optimizer_equals_each_set_alone,
          the_float64_frames_equal_each_set_alone, the_sets_solved_together_equal_each_set_alone,
          the_sets_batch_equals_each_clip_alone,
          the_level2_jacobian_equals_its_differences, the_level2_solve_with_the_exact_jacobian_equals_differences,
          the_measures_equal_the_cpu_measure, the_step_equals_the_prototype, the_projection_equals_the_prototype,
          the_objectives_equal_newtons_own_row_by_row, the_clip_equals_mink_frame_by_frame,
          the_next_iteration_from_its_seeds_equals_mink)


def in_newton():
    """The checks, in Newton's own Python, on the card."""
    import warp as wp
    if not wp.is_cuda_available():
        print("skipped: no CUDA card")
        return 0
    sys.path.insert(0, str(INSIDE))
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    if os.environ.get(IN_ENV):
        sys.exit(in_newton())
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[7] / "conftest.py"))["refuse_outside_sandbox"]()
    env = pathlib.Path(os.environ["PROPS_HOME"]) / "envs/newton_env"
    if not list(env.glob(".built-*")):
        print(f"skipped: no Newton env built at {env} (score/stages/physics/inside/newton_env.sh)")
        sys.exit(0)
    sys.exit(subprocess.run([str(env / "bin/python"), "-B", __file__], env={**os.environ, IN_ENV: "1"}).returncode)
