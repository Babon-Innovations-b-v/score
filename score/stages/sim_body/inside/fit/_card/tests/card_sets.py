"""`_sets.Sets` on the toy: three sets, each its own `_clip.Clip` (inside joints moved, marker offsets 1 mm apart,
place weights apart, targets 1 mm apart, the follower's polynomial apart: the break reading set 0's poly for every
row turns it red), solved as one batch equal each set's `Clip.angles` alone to 0.01 deg and
0.01 mm; sets whose frozen dofs differ are refused (test fixture,
test_the_card_step_and_projection_equal_the_cpu_prototype.py)."""
SETS = 3
SHIFT = 0.001  # m, each set's marker targets and offsets moved on from the last set's
SLOPE = 0.05  # each set's follower slope on its leader moved on from the last set's


def set_toy(index):
    """The toy's MJCF with set `index`'s follower polynomial (its slope SLOPE per set on)."""
    from card_toy import TOY
    return TOY.replace('polycoef="0 0.5 ', f'polycoef="0 {0.5 + SLOPE * index:.2f} ')


def toy_sets(frozen_last=("z",)):
    """SETS toy Clips, set 0 the toy's own; the last set's frozen joints `frozen_last`."""
    import mujoco
    from card_across import moved_places
    from card_toy import toy_clip_card
    clips = [toy_clip_card(mujoco.MjModel.from_xml_string(set_toy(index)),
                           frozen_last if index == SETS - 1 else ("z",)) for index in range(SETS)]
    places = moved_places(clips[0].model)
    for index, clip in enumerate(clips):
        clip.model.joint_X_p.assign(places[index])
        clip.mjm.site_pos[:] += index * SHIFT
        clip.place_costs = clip.place_costs * (1.0 + 0.1 * index)
    return clips


def the_sets_batch_equals_each_clip_alone():
    """Each set's angles from `Sets.angles` against its own `Clip.angles`; problems as text."""
    import mujoco
    import numpy as np
    from card_toy import TOY, mink_frames, toy_clip
    from fit._card._sets import Sets
    mjm = mujoco.MjModel.from_xml_string(TOY)
    turns, places = toy_clip(mjm)
    seeds = mink_frames(mjm, turns, places)
    clips = toy_sets()
    targets = [places + index * SHIFT for index in range(SETS)]
    together = Sets(clips).angles([turns[:, None]] * SETS, targets, [seeds] * SETS)
    problems = []
    for index, clip in enumerate(clips):
        alone, _ = clip.angles(turns[:, None], targets[index], seeds)
        miss = np.degrees(np.abs(together[index][0][:, 7:] - alone[:, 7:])).max()
        root = 1000.0 * np.abs(together[index][0][:, :3] - alone[:, :3]).max()
        if miss > 0.01 or root > 0.01:
            problems.append(f"Sets: set {index} angles {miss:.4f} deg, root {root:.4f} mm off its Clip alone")
    try:
        Sets(toy_sets(frozen_last=("z", "h2")))
        problems.append("Sets: sets with other frozen dofs were not refused")
    except ValueError:
        pass
    return problems
