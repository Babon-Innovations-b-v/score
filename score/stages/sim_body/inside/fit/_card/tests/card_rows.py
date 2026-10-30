"""The across-sets check: on the six-link chain with three sets of joint places (the base and two with their inside
joints moved), the per-row FK (_per_row.per_row_fk) over rows = set x frame equals Newton's eval_fk_batched on each
set's own model, bit for bit (test fixture, test_the_card_step_and_projection_equal_the_cpu_prototype.py)."""
SETS = 3
FRAMES = 4


def set_places(model):
    """[SETS, joints] joint places: the base, then each set's joints moved by its own small offsets."""
    import numpy as np
    base = model.joint_X_p.numpy()
    generator = np.random.default_rng(5)
    places = np.repeat(base[None], SETS, axis=0)
    places[1:, :, :3] += generator.normal(0.0, 0.02, size=(SETS - 1, base.shape[0], 3)).astype(np.float32)
    return places


def the_rows_equal_each_set_alone():
    """Rows' body frames against each set alone; problems as text."""
    import numpy as np
    import warp as wp
    from newton._src.sim.ik.ik_common import eval_fk_batched
    from card_chain import chain_model
    from fit._card._per_row import per_row_fk
    model = chain_model()
    places = set_places(model)
    poses = np.random.default_rng(9).uniform(-1.0, 1.0, size=(SETS * FRAMES, model.joint_coord_count))
    joint_q = wp.array(poses.astype(np.float32), dtype=wp.float32, device="cuda:0")
    joint_qd = wp.zeros((SETS * FRAMES, model.joint_dof_count), dtype=wp.float32, device="cuda:0")
    body_q = wp.zeros((SETS * FRAMES, model.body_count), dtype=wp.transform, device="cuda:0")
    body_qd = wp.zeros((SETS * FRAMES, model.body_count), dtype=wp.spatial_vector, device="cuda:0")
    row_set = wp.array(np.repeat(np.arange(SETS, dtype=np.int32), FRAMES), dtype=wp.int32, device="cuda:0")
    per_row_fk(model, wp.array(places, dtype=wp.transform, device="cuda:0"), row_set, joint_q, joint_qd, body_q,
               body_qd)
    batched = body_q.numpy()
    problems = []
    for index in range(SETS):
        model.joint_X_p.assign(places[index])
        rows = slice(index * FRAMES, (index + 1) * FRAMES)
        alone_q = wp.zeros((FRAMES, model.body_count), dtype=wp.transform, device="cuda:0")
        alone_qd = wp.zeros((FRAMES, model.body_count), dtype=wp.spatial_vector, device="cuda:0")
        eval_fk_batched(model, wp.array(poses[rows].astype(np.float32), dtype=wp.float32, device="cuda:0"),
                        joint_qd[rows], alone_q, alone_qd)
        if not np.array_equal(batched[rows], alone_q.numpy()):
            problems.append(f"set {index}: off by {np.abs(batched[rows] - alone_q.numpy()).max():.3g}")
    return problems
