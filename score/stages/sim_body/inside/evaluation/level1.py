"""level1.py <run dir> --python <Newton's Python> [--hours H]: starts level 1 (#70, `tuning.whole`) on the run dir's
bodies. The run dir holds cases.json ({case: job.json}), split.json ({"tuning": [bodies], "check": [bodies]}) and
table.json (the starting landmark rows, each link its anatomical start) and rig.npz (SOMA's template rig, the
calibration table's rest); it gets evals/ (the latest evaluations),
checkpoint.jsonl (every evaluation and iteration; a restart resumes from its best), check.jsonl (the held-out score
every few iterations and at the end), result_table.json, result_weights.json, result_centres.json (each group end's offset) and held_out.json (the check bodies'
score against the tuning bodies', accepted within 10 %). Any Python with numpy and scipy; the workers run in Newton's."""
import argparse
import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import evaluation  # noqa: E402
import landmarks  # noqa: E402
import tuning  # noqa: E402
from bone_groups import groups  # noqa: E402

GLOBALS = {"marker goal": 1.0, "end weight": 1.0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=pathlib.Path)
    parser.add_argument("--python", required=True)
    parser.add_argument("--hours", type=float, default=8.0)
    given = parser.parse_args()
    run = given.run.resolve()
    cases = json.loads((run / "cases.json").read_text())
    split = json.loads((run / "split.json").read_text())
    table = json.loads((run / "table.json").read_text())
    starts = {name: row["link"] for name, row in table.items()}
    entries = tuning.layout(table, held=landmarks.HELD, joints=set(),
                            ends=tuning.ended(groups(), landmarks.MIDDLE_CENTRES))
    count = [0]

    def side(unknowns, name, label):
        rows, weights = tuning.applied(unknowns, entries, starts, table, GLOBALS)
        rest = {"centres": tuning.offsets(unknowns, entries), "rig": str(run / "rig.npz")}
        found = evaluation.measured(rows, weights, rest, evaluation.picked(cases, split, name),
                                    run / "evals" / label, given.python)
        return found

    def evaluate(unknowns):
        count[0] += 1
        found = side(unknowns, "tuning", f"e{count[0]:05d}")
        shutil.rmtree(run / "evals" / f"e{count[0] - 2:05d}", ignore_errors=True)
        print(f"eval {count[0]}: tuning score {evaluation.side_score(found):.4f}", flush=True)
        return found

    def check(unknowns):
        score = evaluation.side_score(side(unknowns, "check", "check"))
        with open(run / "check.jsonl", "a") as file:
            file.write(json.dumps({"evaluation": count[0], "check score": score}) + "\n")
        return score
    result, checks = tuning.whole(evaluate, check, entries, run / "checkpoint.jsonl", given.hours * 3600)
    rows, weights = tuning.applied(result.x, entries, starts, table, GLOBALS)
    (run / "result_table.json").write_text(json.dumps(rows, indent=1))
    (run / "result_weights.json").write_text(json.dumps(weights))
    (run / "result_centres.json").write_text(json.dumps(tuning.offsets(result.x, entries), indent=1))
    tuned = evaluation.side_score(side(result.x, "tuning", "final"))
    held = {"tuning score": tuned, "check score": checks[-1][1], "checks": checks,
            "accepted": evaluation.accepted(checks[-1][1], tuned)}
    (run / "held_out.json").write_text(json.dumps(held, indent=1))
    print(f"done: {result.message} tuning {tuned:.4f} check {checks[-1][1]:.4f} accepted {held['accepted']} "
          f"-> {run / 'held_out.json'}", flush=True)


if __name__ == "__main__":
    main()
