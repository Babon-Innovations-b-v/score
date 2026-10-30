"""Level 2 across sets in lockstep (`_lockstep`) on fit's toy: three sets, each its own fitting and path, solved side
by side with one card call a round equal each set solved alone on its own card, bit for bit, same evaluations."""

import numpy as np

from card_level2 import SPREAD, problem_and_point

LOCKSTEP_SETS = 3


def _set_inputs(folder, index):
    """Set `index`'s staged inputs: its own toy fitting, its path moved its own way off the poses."""
    problem, _ = problem_and_point(f"{folder}/{index}")
    path = problem.path.copy()
    unturned = [column for column in range(path.shape[1]) if column not in range(3, 7)]
    path[:, unturned] += np.random.default_rng(10 + index).normal(0.0, SPREAD, (len(path), len(unturned)))
    return problem.fitting, path, problem.turns, problem.points, problem.given, problem.free


def the_sets_in_lockstep_equal_each_set_alone():
    import os
    import tempfile
    from fit._card import _level2, _level2_card, _lockstep
    from fit._constants import staged
    problems = []
    with tempfile.TemporaryDirectory() as folder:
        for index in range(LOCKSTEP_SETS):
            os.makedirs(f"{folder}/{index}")
        inputs = [_set_inputs(folder, index) for index in range(LOCKSTEP_SETS)]
        alone = []
        for given in inputs:
            card = _level2_card.CardKinematics(given[0], len(given[1]))
            alone.append(staged(*given, jacobian=lambda problem, unknowns, card=card:
                                _level2.jacobian(problem, unknowns, card)))
        inputs = [_set_inputs(folder, index) for index in range(LOCKSTEP_SETS)]  # fresh fittings, same start
        lockstep = _lockstep.Lockstep(inputs[0][0], len(inputs[0][1]), LOCKSTEP_SETS)
        together = _lockstep.run(lockstep, [lambda jacobian, given=given: staged(*given, jacobian=jacobian)
                                            for given in inputs])
    for index, ((constants, angles, count), (mine, my_angles, my_count)) in enumerate(zip(alone, together)):
        worst = max(np.abs(constants - mine).max(), np.abs(angles - my_angles).max())
        problems += [f"set {index} off its solve alone by {worst:.2e}"] if worst > 0 else []
        problems += [f"set {index} took {my_count} evaluations against {count} alone"] if count != my_count else []
    if len({count for _, _, count in alone}) < 2:
        problems.append("every set took the same evaluations: the drop-out is not tested")
    return problems
