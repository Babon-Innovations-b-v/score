"""Run the library check over places and write what does not trace, with pictures:

    SCORE_LIB_ROOT=<the library folder> .venv/bin/python -m score.stages.complete.library [--place P ...]
        [--out FOLDER] [--no-pictures]

For each place, <out>/<place>/: rows.json (every thing's source and every bound material, each answered library,
exception or neither, with the entry or exception it traced to or what it is instead), findings.json ({"place",
"answer", "reason", "outputs": {node: the assembly judged}, "counts", "findings": [{"rule", "prim", "name",
"sentence", "picture", "count", "aspect", "kind", "prims"}]}) and marks/<place>-<n>.png, a picture a finding; then
<out>/summary.json. The default out is WORK/checks/library, where the cockpit reads it. Reads the store and the
library only; never writes to either. Prints one line a place and one summary line.
"""
import argparse
import json
import pathlib
import tempfile

from pxr import Usd, UsdGeom

from score.stages.complete.library import entries, exceptions, findings, pictures, seen, stored, trace
from score.store import PROPS_HOME

OUT = PROPS_HOME / "work/checks/library"
FINDINGS = "findings.json"
ROWS = "rows.json"


def bounds(stage, paths):
    """{prim path: (low, high)} of the prims' world boxes, the empty ones left out."""
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    found = {}
    for path in paths:
        prim = stage.GetPrimAtPath(path)
        box = cache.ComputeWorldBound(prim).ComputeAlignedRange() if prim else None
        if box is not None and not box.IsEmpty():
            found[path] = (tuple(box.GetMin()), tuple(box.GetMax()))
    return found


def chosen_view(film, scene, boxes, prims):
    """(view number, rectangle) of the frame whose camera sees one of the prims largest, or None."""
    seen_views = [pictures.best_view(film, boxes[path], lambda view, path=path: seen.sees(scene, view, path,
                                                                                        boxes[path]))
                  for path in prims if path in boxes]
    found = max((view for view in seen_views if view), key=lambda view: view[2], default=None)
    return found[:2] if found else None


def pictured(stage, film, found, place, folder):
    """The findings, each with the film crop that shows it (marks/<place>-<n>.png), or none when no frame does."""
    if film is None:
        return [dict(item, picture=None) for item in found]
    boxes = bounds(stage, {path for item in found for path in item["prims"]})
    scene = seen.gathered(stage)
    wanted, named = [], []
    for number, item in enumerate(found):
        view = chosen_view(film, scene, boxes, item["prims"])
        name = f"marks/{place}-{number}.png" if view else None
        if view:
            wanted.append((view[0], view[1], folder / name))
        named.append(dict(item, picture=name))
    (folder / "marks").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"library-frames-{place}-") as scratch:
        pictures.draw(film, wanted, pathlib.Path(scratch))
    return named


def listed(item):
    """A finding as findings.json lists it for the cockpit."""
    return {"rule": item["rule"], "prim": item["prims"][0], "name": item["group"], "sentence": item["sentence"],
            "picture": item["picture"], "count": item["count"], "aspect": item["aspect"], "kind": item["kind"],
            "prims": item["prims"]}


def judged(store, context, folder, with_pictures):
    """Judge one place's accepted assembly and write rows.json and findings.json; findings.json as written."""
    folder.mkdir(parents=True, exist_ok=True)
    node = stored.ASSEMBLY.format(place=context.place)
    output = store.accepted(node)
    if not output:
        written = {"place": context.place, "answer": "unknown", "reason": "no accepted assembly", "outputs": {},
                   "counts": findings.counts([]), "findings": []}
        (folder / FINDINGS).write_text(json.dumps(written, indent=1))
        return written
    with tempfile.TemporaryDirectory(prefix=f"library-{context.place}-") as scratch:
        laid = stored.laid_out(store, output, pathlib.Path(scratch) / context.place)
        stage = Usd.Stage.Open(str(laid / f"{context.place}.usda"))
        rows = trace.rows(stage, context)
        found = findings.grouped(rows)
        film = pictures.film(store, context.place) if with_pictures else None
        found = pictured(stage, film, found, context.place, folder)
    tallied = findings.counts(rows)
    (folder / ROWS).write_text(json.dumps(rows, indent=1))
    written = {"place": context.place, "answer": findings.answer(tallied), "reason": findings.reason(tallied, found),
               "outputs": {node: output}, "counts": tallied, "findings": [listed(item) for item in found]}
    (folder / FINDINGS).write_text(json.dumps(written, indent=1))
    return written


def places_of(chosen):
    """The places asked for, else every place of world 1."""
    if chosen:
        return chosen
    from score import stages
    return stages.places(stages.world1())


def summary_line(written):
    counts = written["counts"]
    return (f"{written['place']}: {written['answer']} (library {counts['library']}, exception "
            f"{counts['exception']}, neither {counts['neither']}; {len(written['findings'])} findings)")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--place", action="append", default=[])
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    parser.add_argument("--no-pictures", action="store_true", help="leave the film crops out")
    options = parser.parse_args(argv)
    shelf = entries.from_environment()
    if shelf is None:
        raise SystemExit("SCORE_LIB_ROOT is not set: the check needs the library folder to trace to")
    written_exceptions = exceptions.read()
    store = stored.reading()
    places = places_of(options.place)
    baked = stored.baked(store, places_of([]))
    summary = {}
    for place in places:
        context = trace.Context(place=place, shelf=shelf, blobs=stored.blobs(store), baked=baked,
                                exceptions=written_exceptions)
        written = judged(store, context, options.out / place, not options.no_pictures)
        summary[place] = {"answer": written["answer"], **written["counts"], "findings": len(written["findings"])}
        print(summary_line(written), flush=True)
    options.out.mkdir(parents=True, exist_ok=True)
    (options.out / "summary.json").write_text(json.dumps(summary, indent=1))
    failed = sorted(place for place, entry in summary.items() if entry["answer"] == "fail")
    print(f"{len(summary)} places, {len(failed)} with things not from the library; {options.out / 'summary.json'}")


if __name__ == "__main__":
    main()
