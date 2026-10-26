"""Run the USD correctness check over places and write what each composed stage breaks:

    .venv/bin/python -m score.stages.complete.usd [--place P ...] [--out FOLDER]

For each place, <out>/<place>/findings.json ({"place", "answer", "reason", "outputs": {node: the stage judged},
"counts": {"error", "warning"}, "findings": [the errors, {"rule", "severity", "prim", "prims", "count", "kind",
"sentence"}], "warnings": [the same, the warnings]}); then <out>/summary.json. The stage judged is the place's
accepted neighbours output where it has one, else its accepted assembly (the stage complete judges). The default
out is WORK/checks/usd, where the cockpit reads the errors as the place's problems. Reads the store only; never
writes to it. Prints one line a place and one summary line.
"""
import argparse
import json
import pathlib
import tempfile

from score.stages.complete.library import stored
from score.stages.complete.usd import judged
from score.store import PROPS_HOME

OUT = PROPS_HOME / "work/checks/usd"
FINDINGS = "findings.json"
JUDGED = ("neighbours@{place}", "assembly@{place}")  # the first accepted of these is the place's composed stage


def composed(store, place):
    """(node, output) of the place's composed stage, or (None, None) when neither stands accepted."""
    for pattern in JUDGED:
        node = pattern.format(place=place)
        output = store.accepted(node)
        if output:
            return node, output
    return None, None


def answer(errors):
    return "fail" if errors else "pass"


def written_for(place, node, output, found):
    """findings.json's object for a judged place."""
    groups = judged.grouped(found)
    errors = [group for group in groups if group["severity"] == "error"]
    warnings = [group for group in groups if group["severity"] == "warning"]
    counts = {"error": sum(group["count"] for group in errors), "warning": sum(group["count"] for group in warnings)}
    reason = (f"{counts['error']} USD errors under {len(errors)} rules" if errors
              else f"no USD error ({counts['warning']} warnings)")
    return {"place": place, "answer": answer(errors), "reason": reason, "outputs": {node: output}, "counts": counts,
            "findings": errors, "warnings": warnings}


def judged_place(store, place, folder):
    """Judge one place's composed stage and write findings.json; the object written."""
    folder.mkdir(parents=True, exist_ok=True)
    node, output = composed(store, place)
    if not output:
        written = {"place": place, "answer": "unknown", "reason": "no accepted assembly", "outputs": {},
                   "counts": {"error": 0, "warning": 0}, "findings": [], "warnings": []}
    else:
        with tempfile.TemporaryDirectory(prefix=f"usd-check-{place}-") as scratch:
            laid = stored.laid_out(store, output, pathlib.Path(scratch) / place)
            found = judged.issues(judged.opened(laid / f"{place}.usda"))
        written = written_for(place, node, output, found)
    (folder / FINDINGS).write_text(json.dumps(written, indent=1))
    return written


def places_of(chosen):
    """The places asked for, else every place of environment 1."""
    if chosen:
        return chosen
    from score import stages
    return stages.places(stages.world1())


def summary_line(written):
    counts = written["counts"]
    return f"{written['place']}: {written['answer']} ({counts['error']} errors, {counts['warning']} warnings)"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--place", action="append", default=[])
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    options = parser.parse_args(argv)
    store = stored.reading()
    summary = {}
    for place in places_of(options.place):
        written = judged_place(store, place, options.out / place)
        summary[place] = {"answer": written["answer"], **written["counts"]}
        print(summary_line(written), flush=True)
    options.out.mkdir(parents=True, exist_ok=True)
    (options.out / "summary.json").write_text(json.dumps(summary, indent=1))
    failed = sorted(place for place, entry in summary.items() if entry["answer"] == "fail")
    print(f"usd check: {len(summary)} places, {len(failed)} with USD errors; {options.out / 'summary.json'}")


if __name__ == "__main__":
    main()
