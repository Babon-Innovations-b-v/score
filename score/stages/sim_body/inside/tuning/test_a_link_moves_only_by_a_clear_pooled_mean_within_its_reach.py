"""tuning: a link moves by its pooled offset only when the mean clears two standard errors, a joint-defining one only
across its bone, shrunk by the 10 mm prior and never past 20 mm from its anatomical start; a held link stays; a left
and a right landmark pool together and stay mirrored; trusts are 1 / (MAD + 5 mm) at the old total; the table's
source gets the tuned rows (all worked out by hand; pure: the score venv runs it).

Breaks (each applied once, seen red, reverted):
- (2026-10-29) stepped's `<= GATE * np.linalg.norm(error)` made `<= 0 * np.linalg.norm(error)`: a noisy mean moves
  the link.
- (2026-10-29) stepped's `across(mean) if joint else` dropped: a joint-defining link slides along its bone.
- (2026-10-29) paired's `return name[:-2] + "_l", MIRROR` made `return name, MIRROR`: the right side pools alone.
- (2026-10-29) trusts' `+ TRUST_FLOOR` dropped: an exact landmark's trust is everything.

Run: .venv/bin/python score/stages/sim_body/inside/tuning/test_a_link_moves_only_by_a_clear_pooled_mean_within_its_reach.py
"""
import pathlib
import sys

import numpy as np

INSIDE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSIDE))
import tuning  # noqa: E402

CLEAR = [[0.003, 0, 0], [0.005, 0, 0], [0.004, 0, 0]]  # mean 4 mm, standard error 0.577 mm: clear
NOISY = [[0.004, 0, 0], [-0.004, 0, 0], [0.003, 0, 0]]  # mean 1 mm, standard error 2.517 mm: noise


def a_clear_mean_moves_the_link_shrunk_by_the_prior():
    """CLEAR from a link at its start: 4 mm x 100 / (100 + 1/3) = 3.98671 mm on in x; NOISY leaves the link."""
    mean, error = tuning.pooled(CLEAR)
    moved = tuning.stepped([0, 0, 0], [0, 0, 0], mean, error, joint=False)
    wanted = 0.004 * 1e-4 / (1e-4 + (0.001 / np.sqrt(3)) ** 2)
    problems = [] if np.allclose(moved, [wanted, 0, 0], atol=1e-8) else [f"clear move {moved}, not {wanted}"]
    mean, error = tuning.pooled(NOISY)
    stayed = tuning.stepped([0.001, 0, 0], [0, 0, 0], mean, error, joint=False)
    return problems + ([] if np.allclose(stayed, [0.001, 0, 0]) else [f"noisy mean moved the link to {stayed}"])


def a_joint_landmark_moves_across_its_bone_only():
    """A clear 4 mm mean along y (the bone) and 4 mm in z: a joint-defining link moves in z only."""
    mean, error = tuning.pooled([[0, value, value] for value in (0.003, 0.005, 0.004)])
    moved = tuning.stepped([0, 0, 0], [0, 0, 0], mean, error, joint=True)
    return [] if abs(moved[1]) < 1e-12 and moved[2] > 0.0039 else [f"joint move {moved}"]


def no_link_ends_past_its_reach():
    """A link already 18 mm out in x and a clear 4 mm more: clamped to 20 mm from its start."""
    mean, error = tuning.pooled(CLEAR)
    moved = tuning.stepped([0.018, 0.01, 0], [0, 0.01, 0], mean, error, joint=False)
    return [] if np.allclose(moved, [0.020, 0.01, 0]) else [f"past reach: {moved}"]


def mirrored_pairs_pool_and_stay_mirrored():
    """ASIS_l on +z and ASIS_r on -z by 4 mm on every body pool to one clear mean; the right's link is the left's
    mirror; trusts are equal and keep the total; a held name stays."""
    rows = {"ASIS_l": ((0, 0, 0.001), 0.5), "ASIS_r": ((0, 0, -0.001), 0.5), "heel_plantar_l": ((0, -0.017, 0), 0.4)}
    starts = {name: link for name, (link, _) in rows.items()}
    bodies = {"ASIS_l": [((0, 0, 0.004), 0.002)] * 2 + [((0, 0, 0.005), 0.002)],
              "ASIS_r": [((0, 0, -0.004), 0.002)] * 2 + [((0, 0, -0.003), 0.002)],
              "heel_plantar_l": [((0, 0.009, 0), 0.001)] * 3}
    found = tuning.tuned(rows, starts, bodies, held=("heel_plantar_l",), joints=())
    problems = [] if np.allclose(np.array(found["ASIS_l"][0]) * [1, 1, -1], found["ASIS_r"][0]) else [
        f"pair {found['ASIS_l'][0]} against {found['ASIS_r'][0]}"]
    if found["ASIS_l"][0][2] <= 0.004 or found["ASIS_l"][1] != found["ASIS_r"][1]:
        problems.append(f"ASIS_l {found['ASIS_l']}, ASIS_r {found['ASIS_r']}")
    if found["heel_plantar_l"][0] != (0, -0.017, 0):
        problems.append(f"held link moved to {found['heel_plantar_l'][0]}")
    total = sum(trust for _, trust in found.values())
    return problems + ([] if abs(total - 1.4) < 0.002 else [f"trust total {total}, not 1.4"])


def trusts_follow_the_mad_with_its_floor():
    """MADs 0 and 5 mm: raw trusts 200 and 100, at a total of 3: 2 and 1."""
    found = tuning.trusts({"one": 0.0, "two": 0.005}, 3.0)
    return [] if np.allclose([found["one"], found["two"]], [2.0, 1.0]) else [f"trusts {found}"]


def the_tables_source_gets_the_tuned_row():
    """A two-row source: ASIS_l's link and trust replaced, its other fields and the other row untouched."""
    source = ('    "ASIS_l": (1970, (0.1, 0.2, 0.7), "Hips", "pelvis",\n        (0, 0, -0.12), (-0.003, 0, 0), 0.462, True),\n'
              '    "ASIS_r": (1971, (0.1, 0.2, 0.7), "Hips", "pelvis",\n        (0, 0, 0.12), (-0.003, 0, 0), 0.462, True),\n')
    found = tuning.rewritten(source, {"ASIS_l": ((0.001, 0, -0.002), 0.5)})
    wanted = source.replace("(-0.003, 0, 0), 0.462, True),\n    \"ASIS_r\"", "(0.001, 0, -0.002), 0.5, True),\n    \"ASIS_r\"")
    return [] if found == wanted else [f"rewritten:\n{found}"]


CHECKS = (a_clear_mean_moves_the_link_shrunk_by_the_prior, a_joint_landmark_moves_across_its_bone_only,
          no_link_ends_past_its_reach, mirrored_pairs_pool_and_stay_mirrored, trusts_follow_the_mad_with_its_floor,
          the_tables_source_gets_the_tuned_row)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[5] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
