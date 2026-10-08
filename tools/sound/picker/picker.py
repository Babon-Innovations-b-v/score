"""The game's sound, made in one go: every sound the game needs, generated, scored, levelled and put in; the owner's
page to listen and swap any of them is optional (the owner, 2026-10-06).

    ~/.farm-factory-props/env/bin/python tools/props/cloud/moss_sound.py game --who <session>   # the takes, on a card
    bash tools/sound/run.sh auto game [--out DIR] [--swaps picks.json]   # build, choose and put every sound in
    bash tools/sound/run.sh pick game [--out DIR] [--sources moss,game,freesound,kenney] [--more picks.json]
    bash tools/sound/run.sh apply DIR [picks.json]                       # put the chosen takes and the swaps in
    bash tools/sound/run.sh needs                                        # any sound with no prompts yet

`pick` asks each source (sources.py: MOSS's takes and the recording before by default; Freesound and Kenney's CC0
recordings when named) for each sound on the page (needs.py), makes every take safe (takes.py: trimmed, shaped,
brought to one loudness under a -3 dBTP true peak, dropped when it cannot be), scores it (choose.py: its CLAP match
less its faults), measures every file again and writes the page (page.py) into DIR, outside the repo. `apply` puts
each sound's chosen take into the game, or the owner's swap where the page's store holds one (the `picks`
collection read back as JSON). `auto` is `pick` then `apply`.
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
DEFAULT_SOURCES = ("moss", "game")
INTRO = ("Every sound the game needs, generated and chosen without you: the chosen take of each is already in the "
         "game. Play any of them; \"Other takes\" shows the rest, and \"Use this one\" swaps it in the next time the "
         "sounds are applied. Every take here is at the same loudness for its kind, peaks under -3 dBTP, and the "
         "volume starts low.")


def finders_for(names, page_name, wanted):
    """The sources named, in order."""
    before = {need["name"]: need["now"] for need in wanted}
    made = {
        "moss": lambda: sources.Moss(page_name),
        "game": lambda: sources.InTheGame(needs.licences_by_file(), lambda name: before.get(name, [])),
        "freesound": lambda: sources.Freesound(sources.freesound_key()),
        "kenney": lambda: sources.Kenney(),
    }
    return [made[name]() for name in names]


def build(page_name, out, source_names=DEFAULT_SOURCES, more_path=None):
    """Builds one page; gives back its index.html."""
    out.mkdir(parents=True, exist_ok=True)
    wanted = needs.needs_for(page_name)
    if not wanted:
        raise SystemExit(f"picker: no sound in data/sound/sounds.json is briefed for the '{page_name}' page")
    finders = finders_for(source_names, page_name, wanted)
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
    raw = applying.documents(json.loads(pathlib.Path(more_path).read_text()))
    asked = {}
    for need in record["needs"]:
        key = (raw.get(need["name"]) or {}).get("more")
        take = next((candidate for candidate in need["takes"] if candidate["key"] == key), None)
        if take:
            fields = {field: take[field] for field in sources.Candidate.__dataclass_fields__}
            asked[need["name"]] = sources.Candidate(**fields)
    return asked


def put_in(folder, swaps_path=None):
    """Every chosen take into the game, the owner's swaps over them; then every sound measured again."""
    swaps = applying.picks_from(json.loads(pathlib.Path(swaps_path).read_text())) if swaps_path else {}
    picks = applying.chosen_with_swaps(json.loads((folder / "candidates.json").read_text()), swaps)
    changed = applying.apply(folder, picks, swapped=set(swaps))
    print(f"put into the game: {len(changed)} sounds")
    print(f"wrote {applying.loudness.write_manifest()}")


def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("pick", "auto"):
        building = commands.add_parser(command)
        building.add_argument("page")
        building.add_argument("--out", type=pathlib.Path)
        building.add_argument("--sources", default=",".join(DEFAULT_SOURCES))
        building.add_argument("--more", type=pathlib.Path)
        building.add_argument("--swaps", type=pathlib.Path)
    applied = commands.add_parser("apply")
    applied.add_argument("folder", type=pathlib.Path)
    applied.add_argument("picks", type=pathlib.Path, nargs="?")
    commands.add_parser("needs")
    chosen = parser.parse_args(arguments)
    if chosen.command in ("pick", "auto"):
        out = chosen.out or OUT / chosen.page
        print(f"wrote {build(chosen.page, out, chosen.sources.split(','), chosen.more)}")
        if chosen.command == "auto":
            put_in(out, chosen.swaps)
    elif chosen.command == "apply":
        put_in(chosen.folder, chosen.picks)
    else:
        print(json.dumps(needs.unbriefed(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
