"""fit/_card: on 12 rows (frames) of a small chain (20 hinge dofs, two frozen, two followers on one leader and one
without a leader, bounds with some rows sitting on them), seeded alike, one step at a time: the card's damped reduced
step equals the CPU prototype's (card/proto/lm.py: mink's damping 1e-3 |r|^2 + 1e-9, frozen out, followers through
their coupling's slope, three active-set passes holding dofs at a bound that push out, holds kept) to 1e-5 rad, and
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
equals mink's answer to the moved clip to 0.01 deg and 0.01 mm (a cold seed only reported).

Breaks (each applied once, seen red, reverted):
- (2026-10-29) _step's `LM_DAMPING * squared + DAMPING` made `DAMPING`: mink's damping is lost, the step differs.
- (2026-10-29) _reduced_jacobian's `* slopes[row, coupling]` dropped: followers ride their leader at slope 1.
- (2026-10-29) _step's `HOLD_PASSES = 3` made `0`: a dof at its bound is not held; the clip's rows never stop.
- (2026-10-29) _kept's `keep[row, column]` made `1.0`: a hold from an earlier pass is let go, the step differs.
- (2026-10-29) _turn_jacobian's `rate[axis]` made `motion[3 + axis]` (Newton's spin alone): the turn's
  Jacobian is no longer the log's exact one.
- (2026-10-29) solved_in_chunks' `values[start:stop]` made `values[:stop - start]`: every chunk solves the first rows.
- (2026-10-29) _projected's `power *= lead` made `power *= 1.0`: a coupling is no longer polyval of its leader.
- (2026-10-29) _turn_jacobian's `weight[problem] * rate[axis]` made `rate[axis]`: the weight is lost.
- (2026-10-29) _turn_residuals' angle `2 atan2(length, w) / length` made `2`: the turn is no longer the log map.
- (2026-10-29) _solve's `CYCLE_STEP = 1e-5` made `0.0`: a seeded toy row cycles at its float32 pose's floor and never
  stops (NotConverged).

Run: .venv/bin/python score/stages/sim_body/inside/fit/_card/test_the_card_step_and_projection_equal_the_cpu_prototype.py
"""
import os
import pathlib
import subprocess
import sys

INSIDE = pathlib.Path(__file__).resolve().parents[2]
IN_ENV = "SIM_BODY_INSIDE_TEST"
ROWS, RESIDUALS, DOFS = 12, 30, 20
FROZEN = (3, 7)
COUPLINGS = ((5, 2, (0.01, 0.6, -0.2, 0.05, 0.01)), (9, 2, (0.0, -0.4, 0.1, 0.0, 0.02)),
             (11, -1, (0.05, 0.0, 0.0, 0.0, 0.0)))  # follower, leader (-1: none), polyval coefficients
BOUND = 0.25  # float32-exact; dofs 0, 1, 4 and 6 range over +-BOUND
BOUNDED = (0, 1, 4, 6)
LINKS = 6
OBJECTIVE_ROWS = 6
HOLD_PASSES = 3  # as _step.HOLD_PASSES: solves after the first, holds only ever added


def fixture():
    """The rows' Jacobians, residuals, poses (some on their bounds), rest pose and seeds, float32-exact."""
    import numpy as np
    generator = np.random.default_rng(7)
    jacobian = generator.normal(size=(ROWS, RESIDUALS, DOFS)).astype(np.float32).astype(float)
    residuals = generator.normal(scale=1.0, size=(ROWS, RESIDUALS)).astype(np.float32).astype(float)
    qpos = generator.uniform(-0.2, 0.2, size=(ROWS, DOFS))
    qpos[::2, BOUNDED] = BOUND
    qpos[1::2, BOUNDED] = -BOUND
    rest = generator.uniform(-0.05, 0.05, size=DOFS).astype(np.float32).astype(float)
    seeds = generator.uniform(-0.2, 0.2, size=(ROWS, DOFS)).astype(np.float32).astype(float)
    lower = np.full(DOFS, -1e30)
    upper = np.full(DOFS, 1e30)
    lower[list(BOUNDED)], upper[list(BOUNDED)] = -BOUND, BOUND
    return jacobian, residuals, qpos.astype(np.float32).astype(float), rest, seeds, lower, upper


def prototype_step(jacobian, residuals, qpos, rest, lower, upper):
    """card/proto/lm.py's step in float64 (hinge-only: coordinate = dof), its holds over HOLD_PASSES passes, with its
    held count."""
    import numpy as np
    jac = jacobian.copy()
    for follower, leader, poly in COUPLINGS:
        if leader >= 0:
            lead = qpos[:, leader] - rest[leader]
            slope = sum(power * poly[power] * lead ** (power - 1) for power in range(1, 5))
            jac[:, :, leader] += jac[:, :, follower] * slope[:, None]
    free = [dof for dof in range(DOFS) if dof not in FROZEN and dof not in {c[0] for c in COUPLINGS}]
    sub = jac[:, :, free]
    grad = np.einsum("frd,fr->fd", sub, residuals)
    hess = np.einsum("frd,fre->fde", sub, sub)
    hess[:, range(len(free)), range(len(free))] += (1e-3 * (residuals ** 2).sum(1) + 1e-9)[:, None]
    step = -np.linalg.solve(hess, grad[..., None])[..., 0]
    at = qpos[:, free]
    held = np.zeros_like(step, dtype=bool)
    for _ in range(HOLD_PASSES):
        held |= ((at <= lower[free] + 1e-9) & (step < 0)) | ((at >= upper[free] - 1e-9) & (step > 0))
        keep = ~held
        hess_kept = hess * (keep[:, :, None] & keep[:, None, :]) + np.eye(len(free))[None] * held[:, :, None]
        step = -np.linalg.solve(hess_kept, (grad * keep)[..., None])[..., 0] * keep
    full = np.zeros((ROWS, DOFS))
    full[:, free] = step
    return full, np.linalg.norm(step, axis=1), int(held.any(1).sum()), free


def prototype_projected(qpos, rest, seeds, lower, upper):
    """card/proto/gpu.py's `projected`: ranges, couplings by polyval, frozen from the seeds."""
    import numpy as np
    found = np.clip(qpos, lower, upper)
    for follower, leader, poly in COUPLINGS:
        lead = found[:, leader] - rest[leader] if leader >= 0 else 0.0
        found[:, follower] = rest[follower] + sum(poly[power] * lead ** power for power in range(5))
    found[:, list(FROZEN)] = seeds[:, list(FROZEN)]
    return found


def the_step_equals_the_prototype():
    import numpy as np
    import warp as wp
    from fit._card import Reduction, damped_step
    jacobian, residuals, qpos, rest, _, lower, upper = fixture()
    wanted, wanted_norms, held_rows, free = prototype_step(jacobian, residuals, qpos, rest, lower, upper)
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


def chain_model():
    """A six-link hinge chain (axes x, y, z in turn, 0.3 m apart) on the card."""
    import newton
    import warp as wp
    builder = newton.ModelBuilder()
    parent, joints = -1, []
    for link in range(LINKS):
        body = builder.add_link(xform=wp.transform((0.0, 0.0, 0.3 * link), wp.quat_identity()))
        builder.add_shape_sphere(body, radius=0.05)
        axis = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))[link % 3]
        joints.append(builder.add_joint_revolute(parent, body, axis=axis, parent_xform=wp.transform(
            (0.0, 0.0, 0.3 if parent >= 0 else 0.0), wp.quat_identity())))
        parent = body
    builder.add_articulation(joints)
    return builder.finalize(device="cuda:0")


def residuals_and_jacobian(model, poses, objectives):
    """Newton's IK residuals and analytic Jacobian at poses [rows, coords] for one objective list."""
    import warp as wp
    from newton import ik
    solver = ik.IKSolver(model, poses.shape[0], objectives, optimizer="lm",
                         jacobian_mode=ik.IKJacobianType.ANALYTIC)._impl
    context = solver._ctx_solver(wp.array(poses.astype("float32"), dtype=wp.float32, device="cuda:0"))
    solver._residuals_analytic(context)
    return context.residuals.numpy().copy(), solver._jacobian_at(context).numpy().copy()


def log_rate(turn):
    """SO(3)'s inverse left Jacobian at a log turn: the exact turn Jacobian is it times Newton's spin rows."""
    import numpy as np
    angle = np.linalg.norm(turn)
    across = np.array([[0.0, -turn[2], turn[1]], [turn[2], 0.0, -turn[0]], [-turn[1], turn[0], 0.0]])
    bend = 1.0 / angle ** 2 - (1.0 + np.cos(angle)) / (2.0 * angle * np.sin(angle))
    return np.eye(3) - 0.5 * across + bend * across @ across


def the_objectives_equal_newtons_own_row_by_row():
    """Per-problem place and turn equal Newton's built-in objective made with that row's offset and weight, the turn's
    Jacobian Newton's spin rows through the log's inverse left Jacobian (mink's exact one)."""
    import numpy as np
    import warp as wp
    from newton import ik
    from fit._card import PlacePerProblem, TurnPerProblem
    model = chain_model()
    generator = np.random.default_rng(11)
    poses = generator.uniform(-1.0, 1.0, size=(OBJECTIVE_ROWS, model.joint_coord_count))
    offsets = generator.normal(0.0, 0.05, size=(OBJECTIVE_ROWS, 3)).astype(np.float32)
    turns = generator.normal(size=(OBJECTIVE_ROWS, 4)).astype(np.float32)
    turns /= np.linalg.norm(turns, axis=1, keepdims=True)
    weights = generator.uniform(0.5, 2.0, OBJECTIVE_ROWS).astype(np.float32)
    places = generator.normal(0.0, 0.5, size=(OBJECTIVE_ROWS, 3)).astype(np.float32)
    wanted = generator.normal(size=(OBJECTIVE_ROWS, 4)).astype(np.float32)
    wanted /= np.linalg.norm(wanted, axis=1, keepdims=True)
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


TOY = """<mujoco><compiler angle="radian"/><worldbody><body name="root"><freejoint/><geom size="0.05"/>
 <body name="a" pos="0 0 0.3"><joint name="h0" axis="1 0 0" range="-1.2 1.2"/><geom size="0.05"/>
  <body name="b" pos="0 0 0.3"><joint name="h1" axis="0 1 0" range="-1.2 1.2"/><geom size="0.05"/>
   <body name="c" pos="0 0 0.3"><joint name="h2" axis="0 0 1" range="-1.2 1.2"/><geom size="0.05"/>
   <body name="cf"><joint name="f" axis="1 0 0"/><geom size="0.02"/>
    <site name="t" pos="0.05 0 0.2" quat="0.9 0.1 0.3 0.2"/><site name="p2" pos="0 0.1 0.25"/>
    <body name="d" pos="0 0 0.3"><joint name="z" axis="0 1 0"/><geom size="0.05"/><site name="p3" pos="0.1 0 0.2"/>
 </body></body></body></body><site name="p1" pos="0.05 0 0.2"/></body><site name="p0" pos="0.1 0.1 0"/></body></worldbody>
 <equality><joint joint1="f" joint2="h1" polycoef="0 0.5 0.2 0 0"/></equality></mujoco>"""
CHUNK = 3  # solved_in_chunks' rows a chunk on the toy: three full chunks and one of one
CLIP_FRAMES, PLACE_SITES, TURN_COST, PLACE_COST = 10, ("p0", "p1", "p2", "p3"), 0.7, 3.0


def toy_clip(mjm):
    """The toy's targets: a path of poses (one hinge driven past its range) through its sites, the places 2 mm off."""
    import mujoco
    import numpy as np
    data, generator = mujoco.MjData(mjm), np.random.default_rng(5)
    turns, places, path = [], [], np.linspace(0.0, 1.0, CLIP_FRAMES)
    for moment in path:
        data.qpos[:] = mjm.qpos0
        data.qpos[:3] = (0.1 * moment, 0.0, 0.05 * moment)
        data.qpos[7:10] = (0.8 * np.sin(2.0 * moment), 1.5 * moment, -0.6 * moment)
        data.qpos[10] = 0.5 * data.qpos[8] + 0.2 * data.qpos[8] ** 2
        mujoco.mj_kinematics(mjm, data)
        turns.append(data.site("t").xmat.reshape(3, 3).copy())
        places.append([data.site(name).xpos + generator.normal(0.0, 0.002, 3) for name in PLACE_SITES])
    return np.array(turns), np.array(places)


def mink_frames(mjm, turns, places):
    """mink (../_frames.solved) frame by frame, each frame from the one before, its targets set as _frames.Frames sets
    them (a place's target turned as its site turns now, so the error is the plain place error; limits at gain 1):
    the reference angles."""
    import mink
    import numpy as np
    from fit import _frames
    configuration = mink.Configuration(mjm)
    turn = mink.FrameTask("t", "site", position_cost=0.0, orientation_cost=TURN_COST, lm_damping=_frames.LM_DAMPING)
    marks = [mink.FrameTask(name, "site", position_cost=PLACE_COST, orientation_cost=0.0,
                            lm_damping=_frames.LM_DAMPING) for name in PLACE_SITES]
    frozen = mink.DofFreezingTask(mjm, dof_indices=[int(mjm.jnt_dofadr[mjm.joint("z").id])])
    constraints = [mink.EqualityConstraintTask(mjm, cost=1.0, gain=1.0), frozen]
    def marked(frame):
        for mark, place in zip(marks, places[frame], strict=True):
            now = configuration.get_transform_frame_to_world(mark.frame_name, "site").rotation()
            mark.set_target(mink.SE3.from_rotation_and_translation(now, place))
    found = []
    for frame in range(len(turns)):
        turn.set_target(mink.SE3.from_rotation(mink.SO3.from_matrix(turns[frame])))
        marked(frame)
        found.append(_frames.solved(configuration, [turn, *marks], [mink.ConfigurationLimit(mjm, gain=1.0)],
                                    constraints, lambda: marked(frame)))
    return np.array(found)


def site_places(mjm, poses):
    """Every site's world place [poses, sites, 3] by MuJoCo's own kinematics."""
    import mujoco
    import numpy as np
    data, found = mujoco.MjData(mjm), []
    for pose in poses:
        data.qpos[:] = pose
        mujoco.mj_kinematics(mjm, data)
        found.append(data.site_xpos.copy())
    return np.array(found)


def toy_card(mjm, turns, places):
    """The card loop's parts for the toy's clip: (optimizer_for(start, stop), reduction, projection)."""
    import newton
    import numpy as np
    import warp as wp
    from scipy.spatial.transform import Rotation
    from newton import ik
    from fit._card import PlacePerProblem, Projection, Reduction, TurnPerProblem
    path = pathlib.Path(os.environ["PROPS_HOME"]) / "toy.xml"
    path.write_text(TOY)
    builder = newton.ModelBuilder(up_axis=newton.Axis.Z)
    builder.add_mjcf(str(path), convert_mjc_equality_constraints=False, parse_meshes=False)
    model = builder.finalize(device="cuda:0")
    body = {label.split("/")[-1]: index for index, label in enumerate(model.body_label)}
    card = lambda values, kind: wp.array(np.ascontiguousarray(values, dtype=np.float32), dtype=kind, device="cuda:0")
    site = lambda name: (body[mjm.body(int(mjm.site(name).bodyid[0])).name], mjm.site(name))

    def optimizer_for(start, stop):
        """Newton's IKOptimizerLM for the clip's frames start:stop."""
        rows = stop - start
        link, turn_site = site("t")
        objectives = [TurnPerProblem(link, card(np.tile(turn_site.quat[[1, 2, 3, 0]], (rows, 1)), wp.quat),
                                     card(Rotation.from_matrix(turns[start:stop]).as_quat(), wp.vec4),
                                     card(np.full(rows, TURN_COST), wp.float32))]
        for index, name in enumerate(PLACE_SITES):
            link, mark = site(name)
            objectives.append(PlacePerProblem(link, card(np.tile(mark.pos, (rows, 1)), wp.vec3),
                                              card(places[start:stop, index], wp.vec3),
                                              card(np.full(rows, PLACE_COST), wp.float32)))
        return ik.IKSolver(model, rows, objectives, optimizer="lm", jacobian_mode=ik.IKJacobianType.ANALYTIC)._impl
    hinge = lambda name: int(mjm.jnt_qposadr[mjm.joint(name).id])  # a hinge's coordinate; its dof is one less
    poly = np.array([[0.0, 0.5, 0.2, 0.0, 0.0]])
    free = [0, 1, 2, 3, 4, 5, 6, 7, 8]
    reduction = Reduction(free, [0] * 6 + [7, 8, 9], [-1e30] * 6 + [-1.2] * 3, [1e30] * 6 + [1.2] * 3,
                          [hinge("f") - 1], [hinge("h1") - 1], [hinge("h1")], [0.0], poly, "cuda:0")
    big = [1e30] * 7
    projection = Projection([-b for b in big] + [-1.2] * 3 + [-1e30] * 2, big + [1.2] * 3 + [1e30] * 2,
                            [hinge("f")], [hinge("h1")], [0.0], [0.0], poly, [hinge("z")], "cuda:0")
    return optimizer_for, reduction, projection


def toy_errors(mjm, found, reference):
    """(largest angle miss in degrees, largest site miss in mm) of `found` against `reference` on the toy."""
    import numpy as np
    angles = np.degrees(np.abs(found[:, 7:] - reference[:, 7:])).max()
    return angles, 1000.0 * np.abs(site_places(mjm, found) - site_places(mjm, reference)).max()


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


CHECKS = (the_step_equals_the_prototype, the_projection_equals_the_prototype,
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
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[6] / "conftest.py"))["refuse_outside_sandbox"]()
    env = pathlib.Path(os.environ["PROPS_HOME"]) / "envs/newton_env"
    if not list(env.glob(".built-*")):
        print(f"skipped: no Newton env built at {env} (score/stages/physics/inside/newton_env.sh)")
        sys.exit(0)
    sys.exit(subprocess.run([str(env / "bin/python"), "-B", __file__], env={**os.environ, IN_ENV: "1"}).returncode)
