"""The sound picker: the owner picks every recording the game plays, by ear, from CC0 takes made safe to hear.

    bash tools/sound/run.sh pick hub [--out DIR] [--more picks.json]   # build the hub's picking page
    bash tools/sound/run.sh apply DIR picks.json                       # put the owner's picks into the game
    bash tools/sound/run.sh needs                                      # what the world's data names, unbriefed

`pick` asks every source (sources.py) for each need on the page (needs.py), makes every candidate safe (takes.py:
trimmed, shaped, brought to one loudness under a -3 dBTP true peak, dropped when it cannot be), measures every
file again and writes the page (page.py) into DIR, outside the repo. Publish DIR/index.html as an Artifact with
`takes/` beside it and the `db` capability; the picks land in its `picks` collection. `--more` reads that
collection back and puts takes like the ones marked "more like this" first.

`apply` copies each picked take into game/sound/recordings/, credits it on the licence list, sets its entry and
level in data/sound/sounds.json and measures every game sound again into the loudness manifest.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import apply as applying  # noqa: E402
import needs  # noqa: E402
import page  # noqa: E402
import sources  # noqa: E402

OUT = pathlib.Path.home() / ".cache" / "farm-factory" / "sound-picker" / "pages"
INTRO = ("Play each take and pick one per sound. Every take here was brought to the same loudness for its kind, "
         "with its peaks held under -3 dBTP, and the volume starts low: raise it with the slider. "
         "\"More like this\" asks the next run for takes like that one.")


def build(page_name, out, more_path=None):
    """Builds one picking page; gives back its index.html."""
    out.mkdir(parents=True, exist_ok=True)
    wanted = needs.needs_for(page_name)
    if not wanted:
        raise SystemExit(f"picker: no sound in data/sound/sounds.json is briefed for the '{page_name}' page")
    licences = needs.licences_by_file()
    now = {need["name"]: need["now"] for need in wanted}
    finders = [sources.InTheGame(licences, lambda name: now.get(name, [])),
               sources.Freesound(sources.freesound_key()), sources.Kenney()]
    asked_more = more_like(out, more_path)
    built = []
    for need in wanted:
        print(f"{need['name']} ({need['category']})")
        candidates = page.candidates_for(need, finders, asked_more.get(need["name"]))
        built.append(page.page_need(need, page.made_safe(need, candidates, out)))
    over = page.check_safe(out)
    if over:
        raise SystemExit("picker: these takes are over the loudness limits, so no page was written:\n" + "\n".join(over))
    return page.write(out, f"{page_name.capitalize()} Sounds", INTRO, built)


def more_like(out, more_path):
    """The candidate each need asked "more like this" of, from the last page's record and its picks."""
    if not more_path or not (out / "candidates.json").exists():
        return {}
    record = json.loads((out / "candidates.json").read_text())
    raw = json.loads(pathlib.Path(more_path).read_text())
    if isinstance(raw, list):
        raw = {document.get("id") or document.get("doc_id"): document.get("data", document) for document in raw}
    asked = {}
    for need in record["needs"]:
        key = (raw.get(need["name"]) or {}).get("more")
        take = next((candidate for candidate in need["takes"] if candidate["key"] == key), None)
        if take:
            fields = {field: take[field] for field in sources.Candidate.__dataclass_fields__}
            asked[need["name"]] = sources.Candidate(**fields)
    return asked


def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    picking = commands.add_parser("pick")
    picking.add_argument("page")
    picking.add_argument("--out", type=pathlib.Path)
    picking.add_argument("--more", type=pathlib.Path)
    applied = commands.add_parser("apply")
    applied.add_argument("folder", type=pathlib.Path)
    applied.add_argument("picks", type=pathlib.Path)
    commands.add_parser("needs")
    chosen = parser.parse_args(arguments)
    if chosen.command == "pick":
        print(f"wrote {build(chosen.page, chosen.out or OUT / chosen.page, chosen.more)}")
    elif chosen.command == "apply":
        picks = applying.picks_from(json.loads(chosen.picks.read_text()))
        changed = applying.apply(chosen.folder, picks)
        print(f"picked into the game: {', '.join(changed) or 'nothing new'}")
        print(f"wrote {applying.loudness.write_manifest()}")
    else:
        print(json.dumps(needs.unbriefed(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
