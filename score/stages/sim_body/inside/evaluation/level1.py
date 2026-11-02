"""level1.py <run dir> --python <Newton's Python> [--hours H] [--card <seeds root> [--exact]] [--processes N]: starts level 1 (#70, `tuning.whole`) on the run dir's
bodies. The run dir holds cases.json ({case: job.json}), split.json ({"tuning": [bodies], "check": [bodies]}) and
table.json (the starting landmark rows, each link its anatomical start) and rig.npz (SOMA's template rig, the
calibration table's rest); it gets evals/ (the latest evaluations),
checkpoint.jsonl (every evaluation and iteration; a restart resumes from its best), check.jsonl (the held-out score
every --every iterations, 3 unless given, and at the end), steps.jsonl (each check against the one before: per-case paired changes of
the honest measures, tuning and check bodies apart, verdicts past floor.json when the run dir has it, `tuning._paired`), result_table.json (its trusts relative, the largest 1), result_weights.json and held_out.json (the check bodies'
score against the tuning bodies', accepted within 10 %). Each card process holds its own share of this PC's card
queue while it runs (`evaluation.CardShares`, sim-body priority), so start level 1 outside the queue; --hours counts
no second a process waited for its share. With --card every evaluation runs on the card
(`evaluation.measured_many`, seeded from the seeds root's angles), a Jacobian's nudged sets in one process, at most
--processes bodies side by side (`evaluation.SET_PROCESSES` unless given: a rented machine with the cores runs every
tuning body at once, tools/cloud/level1); with --exact too the Jacobian is exact
(`exact_stacked`: each tuning case's block, `evaluation.blocked`, then the prior's columns). The unknowns are the
links, trusts and the two global weights (`tuning.layout` with no group-end centres: since 2026-11-01 level 1 aims at
the bones inside the skin, and the centres were tuned mostly for the joint error, which is now reported only; they
stay at MyoFullBody's own). Every evaluation's line also gives the turns check and the joints, never tuned
(`evaluation.reported`). Any Python with numpy and scipy; the workers run in Newton's."""
import argparse
import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import evaluation  # noqa: E402
import landmarks  # noqa: E402
import numpy as np  # noqa: E402
import tuning  # noqa: E402
from tuning import _paired  # noqa: E402
from tuning._adjoint import by_columns  # noqa: E402

GLOBALS = {"marker goal": 1.0, "end weight": 1.0}
PRIOR_STEP = 1.0  # the prior is linear in every unknown, so any step gives its exact columns


def exact_stacked(blocks, unknowns, entries):
    """Level 1's exact Jacobian in `tuning.whole`'s row order: each case's block ({case: npz path}, `evaluation.blocked`)
    in sorted case order, then the prior's columns."""
    rows = [np.load(blocks[case])["block"] for case in sorted(blocks)]
    return np.concatenate(rows + [by_columns(lambda moved: tuning.prior(moved, entries), unknowns, PRIOR_STEP)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=pathlib.Path)
    parser.add_argument("--python", required=True)
    parser.add_argument("--hours", type=float, default=8.0)
    parser.add_argument("--card", type=pathlib.Path, help="seeds root: evaluate on the card, sets batched")
    parser.add_argument("--exact", action="store_true",
                        help="with --card: the exact Jacobian, a block a case")
    parser.add_argument("--every", type=int, default=3, help="score the check bodies every this many iterations")
    parser.add_argument("--processes", type=int, default=evaluation.SET_PROCESSES,
                        help="with --card: bodies' card processes side by side")
    given = parser.parse_args()
    if given.exact and not given.card:
        parser.error("--exact needs --card (the blocks are seeded from its angles)")
    run = given.run.resolve()
    cases = json.loads((run / "cases.json").read_text())
    split = json.loads((run / "split.json").read_text())
    table = json.loads((run / "table.json").read_text())
    starts = {name: row["link"] for name, row in table.items()}
    entries = tuning.layout(table, held=landmarks.HELD, joints=set())
    count = [0]
    latest = {}
    sides = {case: name for name in ("tuning", "check") for case in evaluation.picked(cases, split, name)}
    noise = json.loads((run / "floor.json").read_text())["floor"] if (run / "floor.json").exists() else None
    sets_shares = evaluation.CardShares("sets", evaluation.SETS_CARD_GB) if given.card else None
    blocks_shares = evaluation.CardShares("blocks", evaluation.BLOCKS_CARD_GB) if given.exact else None
    jacobian_shares = evaluation.CardShares("jacobian", evaluation.CHUNK_CARD_GB) if given.card else None
    shares = (sets_shares, blocks_shares, jacobian_shares)  # their card waits are not level 1's --hours

    def worker_set(unknowns):
        rows, weights = tuning.applied(unknowns, entries, starts, table, GLOBALS)
        return rows, weights, {"centres": {}, "rig": str(run / "rig.npz")}

    def side(unknowns, name, label, unconverged=False):
        picked = evaluation.picked(cases, split, name)
        if given.card:
            return evaluation.measured_many([worker_set(unknowns)], picked, run / "evals" / label, given.python,
                                            given.card, unconverged=unconverged, shares=sets_shares,
                                            most=given.processes)[0]
        return evaluation.measured(*worker_set(unknowns), picked, run / "evals" / label, given.python)

    def evaluate_many(sets):
        return evaluation.measured_many([worker_set(unknowns) for unknowns in sets],
                                        evaluation.picked(cases, split, "tuning"), run / "evals" / "jacobian",
                                        given.python, given.card, unconverged=True, shares=jacobian_shares,
                                        most=given.processes)

    def evaluate(unknowns):
        count[0] += 1
        found = side(unknowns, "tuning", f"e{count[0]:05d}", unconverged=True)
        shutil.rmtree(run / "evals" / f"e{count[0] - 2:05d}", ignore_errors=True)
        if found is None:  # a body's level 3 did not stop on this trial point: tuning.whole refuses it
            print(f"eval {count[0]}: a tuning body's level 3 did not stop: trial refused", flush=True)
            return None
        latest["tuning"] = found
        print(f"eval {count[0]}: tuning score {evaluation.side_score(found):.4f} {evaluation.reported(found)}", flush=True)
        return found

    def exact(unknowns):
        blocks = evaluation.blocked(*worker_set(unknowns), evaluation.picked(cases, split, "tuning"),
                                    run / "evals" / "exact", given.python, given.card, shares=blocks_shares,
                                    most=given.processes)
        return exact_stacked(blocks, unknowns, entries)

    def check(unknowns):
        found = side(unknowns, "check", "check", unconverged=True)
        if found is None:  # a check body's level 3 did not stop here: no score, never used to choose
            with open(run / "check.jsonl", "a") as file:
                file.write(json.dumps({"evaluation": count[0], "check score": None, "unconverged": True}) + "\n")
            return float("nan")
        score = evaluation.side_score(found)
        now = {case: _paired.flattened(value) for case, value in {**latest["tuning"], **found}.items()}
        if "check" in latest:
            with open(run / "steps.jsonl", "a") as file:
                file.write(json.dumps({"evaluation": count[0], **_paired.stepped(latest["check"], now, sides, noise)})
                           + "\n")
        latest["check"] = now
        with open(run / "check.jsonl", "a") as file:
            file.write(json.dumps({"evaluation": count[0], "check score": score, **evaluation.reported(found)}) + "\n")
        return score
    result, checks = tuning.whole(evaluate, check, entries, run / "checkpoint.jsonl", given.hours * 3600,
                                  every=given.every, evaluate_many=evaluate_many if given.card else None,
                                  exact=exact if given.exact else None,
                                  paused=lambda: sum(kind.waited for kind in shares if kind))
    rows, weights = tuning.applied(result.x, entries, starts, table, GLOBALS)
    (run / "result_table.json").write_text(json.dumps(tuning.relative(rows), indent=1))
    (run / "result_weights.json").write_text(json.dumps(weights))
    final = side(result.x, "tuning", "final")
    tuned = evaluation.side_score(final)
    held = {"tuning score": tuned, "check score": checks[-1][1], "checks": checks,
            "clips with no unfolded frame": evaluation.reported(final)["clips with no unfolded frame"],
            "accepted": evaluation.accepted(checks[-1][1], tuned)}
    (run / "held_out.json").write_text(json.dumps(held, indent=1))
    print(f"done: {result.message} tuning {tuned:.4f} check {checks[-1][1]:.4f} accepted {held['accepted']} "
          f"-> {run / 'held_out.json'}", flush=True)


if __name__ == "__main__":
    main()
