"""level1.py <run dir> --python <Newton's Python> [--hours H] [--card <seeds root> [--exact]] [--processes N]: starts level 1 (#70, `tuning.whole`) on the run dir's
bodies. The run dir holds cases.json ({case: job.json}), split.json ({"tuning": [bodies], "check": [bodies]}) and
table.json (the starting landmark rows, each link its anatomical start) and rig.npz (SOMA's template rig, the
calibration table's rest); it gets evals/ (the latest evaluations),
checkpoint.jsonl (every evaluation and iteration; a restart resumes from its best; each line also kept in SCORE's
store under the run's key, `stored.run_key`, and a run folder on any machine gets every kept line of its run back,
so it resumes from the best anywhere), check.jsonl (the held-out score
every --every iterations, 3 unless given, and at the end), steps.jsonl (each check against the one before: per-case paired changes of
the honest measures, tuning and check bodies apart, verdicts past floor.json when the run dir has it, `tuning._paired`), result_table.json (its trusts relative, the largest 1), result_weights.json, result_shifts.json (every segment end's shift, m, the person's frame) and held_out.json (the check bodies'
score against the tuning bodies', accepted within 10 %). Each card process holds its own share of this PC's card
queue while it runs (`evaluation.CardShares`, sim-body priority), so start level 1 outside the queue; --hours counts
no second a process waited for its share. With --card every evaluation runs on the card
(`evaluation.measured_many`, seeded from the seeds root's angles), a Jacobian's nudged sets in one process, at most
--processes bodies side by side (`evaluation.SET_PROCESSES` unless given: a rented machine with the cores runs every
tuning body at once, tools/cloud/level1); with --exact too the Jacobian is exact
(`exact_stacked`: each tuning case's block, `evaluation.blocked`, then the prior's columns). The unknowns are the
links, trusts, every segment end's shift and the two global weights (`laid_out`: no group-end centres, which stay at
MyoFullBody's own; owner, 2026-11-03: "what i didnt want anymore was joint centre to joint centre fitting, but segment
ends ... is better": each end marker shifted on its holder body, `tuning._ends`, from its shift read at rest in
SOMA's skin, `calibration.END_READS`, mirrored). The objective is the bones outside the skin and each segment's turn
against its bone group, each over its start value (`tuning.weights`); every evaluation's line also gives the joints,
never tuned (`evaluation.reported`). Every evaluation, block and seed is found in the store or made and kept there
(`evaluation.kept_run`, `stored`): evals/ holds read-only views of them. Any Python with numpy and scipy; the workers run in Newton's."""
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
from bone_groups import groups  # noqa: E402
from calibration import END_READS  # noqa: E402
from evaluation import stored  # noqa: E402
from tuning import _paired  # noqa: E402
from tuning._adjoint import by_columns  # noqa: E402

GLOBALS = {"marker goal": 1.0, "end weight": 1.0}
PRIOR_STEP = 1.0  # the prior is linear in every unknown, so any step gives its exact columns


def exact_stacked(blocks, unknowns, entries):
    """Level 1's exact Jacobian in `tuning.whole`'s row order: each case's block ({case: npz path}, `evaluation.blocked`:
    raw rows, as `tuning.case_residuals`; `tuning.whole` weighs them) in sorted case order, then the prior's columns."""
    rows = [np.load(blocks[case])["block"] for case in sorted(blocks)]
    return np.concatenate(rows + [by_columns(lambda moved: tuning.prior(moved, entries), unknowns, PRIOR_STEP)])


def laid_out(table):
    """Level 1's unknowns over the landmark `table` (`tuning.layout`): links, trusts, every segment end's shift
    (`tuning.segment_ends`), the two global weights."""
    return tuning.layout(table, held=landmarks.HELD, joints=set(),
                         shifted=tuning.segment_ends(groups(), landmarks.SOMA_MIDDLES))


def worker_set(unknowns, entries, table, rig):
    """The evaluation's set at `unknowns` (rows, weights, rest): the landmark rows and global weights
    (`tuning.applied`), no centre moved, each segment end's shift from its start (`tuning.shifts`), SOMA's `rig` path."""
    starts = {name: row["link"] for name, row in table.items()}
    rows, weights = tuning.applied(unknowns, entries, starts, table, GLOBALS)
    ends = tuning.mirrored_starts(END_READS, tuning.segment_ends(groups(), landmarks.SOMA_MIDDLES))
    return rows, weights, {"centres": {}, "shifts": tuning.shifts(unknowns, entries, ends, tuning.LINK_UNIT),
                           "rig": str(rig)}


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
    entries = laid_out(table)
    count = [0]
    latest = {}
    sides = {case: name for name in ("tuning", "check") for case in evaluation.picked(cases, split, name)}
    noise = json.loads((run / "floor.json").read_text())["floor"] if (run / "floor.json").exists() else None
    sets_shares = evaluation.CardShares("sets", evaluation.SETS_CARD_GB) if given.card else None
    blocks_shares = evaluation.CardShares("blocks", evaluation.BLOCKS_CARD_GB) if given.exact else None
    jacobian_shares = evaluation.CardShares("jacobian", evaluation.CHUNK_CARD_GB) if given.card else None
    shares = (sets_shares, blocks_shares, jacobian_shares)  # their card waits are not level 1's --hours
    store = stored.default_store()
    kept_as = stored.run_key(pathlib.Path(__file__), table, split, cases, run / "rig.npz",
                             {"every": given.every, "card": bool(given.card), "exact": given.exact})

    def lines_kept():
        """checkpoint.jsonl's lines kept in the store, and the store's lines of this run on any machine in it."""
        stored.lines_kept(store, kept_as, run / "checkpoint.jsonl")
    lines_kept()

    def side(unknowns, name, label, unconverged=False):
        picked = evaluation.picked(cases, split, name)
        if given.card:
            return evaluation.measured_many([worker_set(unknowns, entries, table, run / "rig.npz")], picked, run / "evals" / label, given.python,
                                            given.card, unconverged=unconverged, shares=sets_shares,
                                            most=given.processes, store=store)[0]
        return evaluation.measured(*worker_set(unknowns, entries, table, run / "rig.npz"), picked, run / "evals" / label, given.python, store=store)

    def evaluate_many(sets):
        return evaluation.measured_many([worker_set(unknowns, entries, table, run / "rig.npz") for unknowns in sets],
                                        evaluation.picked(cases, split, "tuning"), run / "evals" / "jacobian",
                                        given.python, given.card, unconverged=True, shares=jacobian_shares,
                                        most=given.processes, store=store)

    def evaluate(unknowns):
        lines_kept()
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
        lines_kept()
        blocks = evaluation.blocked(*worker_set(unknowns, entries, table, run / "rig.npz"), evaluation.picked(cases, split, "tuning"),
                                    run / "evals" / "exact", given.python, given.card, shares=blocks_shares,
                                    most=given.processes, store=store)
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
    lines_kept()
    rows, weights, rest = worker_set(result.x, entries, table, run / "rig.npz")
    (run / "result_shifts.json").write_text(json.dumps(rest["shifts"], indent=1))
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
