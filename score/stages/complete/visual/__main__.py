"""Run the visual check over places and write what it found, with pictures:

    .venv/bin/python -m score.stages.complete.visual [--place P ...] [--out FOLDER] [--judge-only]

For each place, <out>/<place>/: evidence.json and pictures/ (measure.py), findings.json ({"place", "answer",
"reason", "outputs": {node: the film or still output judged}, "pictures", "findings": [{"rule", "prim", "share",
"name", "sentence", "picture"}]}) and marks/<place>-<rule>-<n>.png, a picture a
finding; then <out>/summary.json and <out>/contact_sheet.png. `--judge-only` judges evidence measured before. The
default out is WORK/checks/visual, where the cockpit reads it. Prints one line a place and one summary line.
"""
import argparse
import json
import pathlib

from PIL import Image

from score.stages.complete.visual import judge, marks, measure
from score.store import PROPS_HOME, Store

OUT = PROPS_HOME / "work/checks/visual"
FINDINGS = "findings.json"


def reason(answer, found):
    """The place's answer in words."""
    if answer == "unknown":
        return "no film frame or still with its stage to judge"
    if answer == "pass":
        return "no blocking plane, untextured surface or one-object picture in its film frames and stills"
    return "; ".join(f"{item['rule']}: {item['prim']}" for item in found[:4]) + (
        f" and {len(found) - 4} more" if len(found) > 4 else "")


def marked_findings(place, found, evidence, folder):
    """Each finding's marked picture written under marks/; the findings as findings.json lists them."""
    listed = []
    for number, item in enumerate(found):
        source = Image.open(folder / evidence["pictures"][item["picture"]]["file"])
        name = f"marks/{place}-{item['rule'].replace(' ', '-')}-{number}.png"
        marks.marked(source, item, folder / name)
        listed.append({"rule": item["rule"], "prim": item["prim"], "share": item["share"], "name": item["name"],
                       "sentence": item["sentence"], "picture": name})
    return listed


def judged(place, folder):
    """Judge a place's evidence folder and write its findings.json; the findings as written."""
    evidence = judge.read(folder)
    found = judge.findings(evidence, folder)
    answer = judge.verdict(evidence, found)
    written = {"place": place, "answer": answer, "reason": reason(answer, found), "outputs": evidence["outputs"],
               "pictures": len(evidence["pictures"]),
               "findings": marked_findings(place, found, evidence, folder)}
    (folder / FINDINGS).write_text(json.dumps(written, indent=1))
    return written


def sheet_row(written, folder):
    """A place's contact sheet row: its marked pictures, else its first picture."""
    pictures = [folder / item["picture"] for item in written["findings"]]
    if not pictures and (folder / "pictures/0.png").exists():
        pictures = [folder / "pictures/0.png"]
    return written["place"], written["answer"], pictures, written["reason"]


def places_of(chosen):
    """The places asked for, else every place of world 1."""
    if chosen:
        return chosen
    from score import stages
    return stages.places(stages.runner(world=stages.WORLDS["world1"]()).world)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--place", action="append", default=[])
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    parser.add_argument("--judge-only", action="store_true", help="judge evidence measured before")
    options = parser.parse_args(argv)
    store = None if options.judge_only else Store.default()
    rows, summary = [], {}
    for place in places_of(options.place):
        folder = options.out / place
        if store is not None:
            measure.gather(store, place, folder)
        written = judged(place, folder)
        summary[place] = {"answer": written["answer"], "findings": len(written["findings"])}
        rows.append(sheet_row(written, folder))
        print(f"{place}: {written['answer']} ({written['reason']})", flush=True)
    (options.out / "summary.json").write_text(json.dumps(summary, indent=1))
    sheet = marks.sheet(rows, options.out / "contact_sheet.png")
    failed = sorted(place for place, entry in summary.items() if entry["answer"] == "fail")
    print(f"{len(summary)} places, {len(failed)} fail ({', '.join(failed)}); contact sheet {sheet}")


if __name__ == "__main__":
    main()
