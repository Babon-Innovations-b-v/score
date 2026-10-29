"""The toy clip the loop checks run on: a toy MJCF (a free root, three ranged hinges, a polyval follower in its own
body, a frozen hinge), its 10-frame targets, mink's answer set up as _frames.Frames, the card's setup and the errors
between two answers (test fixture, test_the_card_step_and_projection_equal_the_cpu_prototype.py)."""
import os
import pathlib

TOY = """<mujoco><compiler angle="radian"/><worldbody><body name="root"><freejoint/><geom size="0.05"/>
 <body name="a" pos="0 0 0.3"><joint name="h0" axis="1 0 0" range="-1.2 1.2"/><geom size="0.05"/>
  <body name="b" pos="0 0 0.3"><joint name="h1" axis="0 1 0" range="-1.2 1.2"/><geom size="0.05"/>
   <body name="c" pos="0 0 0.3"><joint name="h2" axis="0 0 1" range="-1.2 1.2"/><geom size="0.05"/>
   <body name="cf"><joint name="f" axis="1 0 0"/><geom size="0.02"/>
    <site name="t" pos="0.05 0 0.2" quat="0.9 0.1 0.3 0.2"/><site name="p2" pos="0 0.1 0.25"/>
    <body name="d" pos="0 0 0.3"><joint name="z" axis="0 1 0"/><geom size="0.05"/><site name="p3" pos="0.1 0 0.2"/>
 </body></body></body></body><site name="p1" pos="0.05 0 0.2"/></body><site name="p0" pos="0.1 0.1 0"/></body></worldbody>
 <equality><joint joint1="f" joint2="h1" polycoef="0 0.5 0.2 0 0"/></equality></mujoco>"""
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
