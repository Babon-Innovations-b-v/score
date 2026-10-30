"""Newton's import of a MuJoCo body carrying several joints: one Newton joint into the body (its joints merged into
one D6 at the first joint's place), so `_clip.moved_inside`'s map of child body to joint names that one joint and
moving it moves the whole body (test fixture, test_the_card_step_and_projection_equal_the_cpu_prototype.py)."""
SEVERAL = """<mujoco><worldbody><body name="root" pos="0 0 1"><freejoint/><geom size="0.1"/>
<body name="arm" pos="0.2 0 0"><joint name="a1" type="hinge" axis="1 0 0"/><joint name="a2" type="hinge" axis="0 1 0"/>
<joint name="a3" type="slide" axis="0 0 1"/><geom size="0.05"/>
<body name="hand" pos="0.3 0 0"><joint name="h1" type="hinge" axis="0 0 1"/><geom size="0.03"/></body></body>
</body></worldbody></mujoco>"""
MOVE = (0.0, 0.01, 0.0)  # m, the arm's inside joint move
TOLERANCE = 1e-6  # m


def the_body_with_several_joints_moves_as_one():
    """The arm's one Newton joint placed at its file place plus the move, the hand's left alone; problems as text."""
    import types
    import mujoco
    import newton
    import numpy as np
    import warp as wp
    from fit._card._clip import moved_inside
    mjm = mujoco.MjModel.from_xml_string(SEVERAL)
    path = written_file(SEVERAL)
    arm = mujoco.mj_name2id(mjm, mujoco.mjtObj.mjOBJ_BODY, "arm")
    fitting = types.SimpleNamespace(model=mjm, base=[mjm.body_pos.copy()], inside=np.array([arm]))
    mjm.body_pos[arm] += MOVE
    builder = newton.ModelBuilder(up_axis=newton.Axis.Z)
    builder.add_mjcf(str(path), convert_mjc_equality_constraints=False, parse_meshes=False)
    into = {label.split("/")[-1]: [joint for joint, child in enumerate(builder.joint_child) if child == body]
            for body, label in enumerate(builder.body_label)}
    if len(into["arm"]) != 1:
        return [f"the arm has {len(into['arm'])} Newton joints, not one"]
    before = {name: np.asarray(wp.transform_get_translation(builder.joint_X_p[joints[0]])) for name, joints in into.items()}
    moved_inside(builder, fitting)
    after = {name: np.asarray(wp.transform_get_translation(builder.joint_X_p[joints[0]])) for name, joints in into.items()}
    wanted = {name: before[name] + (np.array(MOVE) if name == "arm" else 0.0) for name in before}
    return [f"{name}'s joint place off by {np.abs(after[name] - wanted[name]).max():.6f} m" for name in before
            if np.abs(after[name] - wanted[name]).max() > TOLERANCE]


def written_file(text):
    """A file holding `text` in a fresh temporary directory (Newton's import reads a path)."""
    import pathlib
    import tempfile
    path = pathlib.Path(tempfile.mkdtemp()) / "several.xml"
    path.write_text(text)
    return path
