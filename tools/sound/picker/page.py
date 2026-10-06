"""A picking page: every need on it with its candidates fetched, made safe and laid out for the owner to play and
pick (page.html). The page is built into a folder outside the repo, published as an Artifact with its takes beside
it, and keeps the owner's picks in the Artifact's own store (collection `picks`, one document a need:
`{take, more, at}`), which apply.py reads back.
"""
import html
import json
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sources  # noqa: E402
import takes  # noqa: E402

TEMPLATE = pathlib.Path(__file__).resolve().parent / "page.html"
## How many candidates a need gets on the page, besides the take in the game now.
CANDIDATES = 5
## How many each source is asked for: more than are shown, since some are dropped by the loudness rule.
ASKED = {"freesound": 7, "kenney": 2}
LABELS = {"steps": "Footsteps", "shot": "One-shot", "loop": "Hum", "room": "Room tone"}


def slug(key):
    """A candidate's key as a folder name."""
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", key).strip("_")[:80]


def fetched(candidate):
    """A candidate's audio in the cache, fetched once."""
    if candidate.audio.startswith("file://"):
        return pathlib.Path(candidate.audio.removeprefix("file://"))
    path = sources.CACHE / "fetched" / (slug(candidate.key) + pathlib.Path(candidate.audio).suffix)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(sources.fetch(candidate.audio, timeout=120))
    return path


def candidates_for(need, finders, more_like=None):
    """A need's candidates from every source, the ones like `more_like` first; each unique by key."""
    found, keys = [], set()
    for finder in finders:
        asked = ASKED.get(finder.name, 1)
        offered = finder.similar(more_like, asked) if more_like and more_like.source == finder.name else []
        for candidate in offered + finder.search(need, asked):
            if candidate.key not in keys:
                keys.add(candidate.key)
                found.append(candidate)
    return found


def made_safe(need, candidates, folder):
    """The candidates that come through trimming and the loudness rule, as page takes, at most CANDIDATES besides
    the game's own."""
    kept = []
    for candidate in candidates:
        if len([take for take in kept if take["source"] != "game"]) >= CANDIDATES:
            break
        where = folder / "takes" / need["name"] / slug(candidate.key)
        try:
            made = takes.prepare(fetched(candidate), where, need["category"])
        except (OSError, ValueError, RuntimeError) as failed:
            print(f"  {candidate.key}: left out ({failed})")
            continue
        if made is None:
            print(f"  {candidate.key}: left out, no safe take in it")
            shutil.rmtree(where, ignore_errors=True)
            continue
        kept.append(page_take(need, candidate, made, where.relative_to(folder)))
        print(f"  {candidate.key}: {made['measures'][made['preview']]['lufs']:.1f} LUFS, "
              f"{made['measures'][made['preview']]['true_peak']:.1f} dBTP")
    return kept


def page_take(need, candidate, made, relative):
    """One take as the page and apply.py read it."""
    preview = made["measures"][made["preview"]]
    return {**candidate.to_json(), "preview": (relative / made["preview"]).as_posix(),
            "files": [(relative / name).as_posix() for name in made["takes"]],
            "measures": {(relative / name).as_posix(): measure for name, measure in made["measures"].items()},
            "peaks": made["peaks"], "seconds": made["seconds"], "loop": need["loop"],
            "steps": len(made["takes"]) if need["category"] == "steps" else 0,
            "lufs": preview["lufs"], "peak": preview["true_peak"]}


def page_need(need, kept):
    return {"name": need["name"], "title": need["name"].replace("_", " ").capitalize(), "category": need["category"],
            "label": LABELS[need["category"]], "where": need["where"], "takes": kept}


def write(folder, title, intro, needs):
    """The page and its record: index.html for the owner, candidates.json for apply.py."""
    data = {"title": title, "intro": intro, "needs": needs}
    (folder / "candidates.json").write_text(json.dumps(data, indent="\t") + "\n")
    page = TEMPLATE.read_text().replace("<title>Sound Picks</title>", f"<title>{html.escape(title)}</title>", 1)
    page = page.replace("/*DATA*/null", json.dumps(data).replace("</", "<\\/"))
    (folder / "index.html").write_text(page)
    return folder / "index.html"


def check_safe(folder):
    """Every file the page plays, measured again: the page is not written if one is over the limits."""
    over = []
    for path in sorted((folder / "takes").rglob("*.ogg")):
        measure = takes.loudness.measure(path)
        if measure["true_peak"] > takes.loudness.CEILING_DBTP or measure["lufs"] > takes.loudness.LIMIT_LUFS:
            over.append(f"{path.relative_to(folder)}: {measure['lufs']:.1f} LUFS, {measure['true_peak']:.1f} dBTP")
    return over
