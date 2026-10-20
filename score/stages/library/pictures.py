"""The library's pictures the cockpit shows, and the small files its item pages play, fetched into the library cache on
the store's machine, so its tiles, its viewers and the state export have their bytes (#42: every place showed "no
picture yet" while score_lib held each one).

    .venv/bin/python -m score.stages.library.pictures [--kind place ...]

Each entry of the kinds (default: every kind, so the Library screen's branches have their thumbnails) that names a
picture is fetched once by the library's own command into `$PROPS_HOME/cache/library/score_lib/<kind>/<id>/<version>/<file>` and checked against the sha256 its entry records
(tools/library/library_files.py `from_library`; a cached file that still hashes right is not fetched again). The
cockpit's library reads that cache when it has no blob folder (score/dashboard/state/library.py). Read only on the
library side; never a row, so nothing keys on it. A fetch costs one object read.

The viewer files (`viewed`) are what an item page plays: a light web copy, a model's close-up, a surface's material and print, a
sound's first takes, an effect's settings, a sky's OpenUSD, a light layer's lamps.json. One the blob store answers 404 for is marked lost
(`<file>.lost` beside it, holding the sha the entry records) and not asked for again until the entry names other bytes;
the cockpit says such a file is missing. `FETCHES` fetches run side by side (each a process of the library's command
waiting on one object read).
"""
import argparse
from concurrent.futures import ThreadPoolExecutor

from score import library
from score.stages.library import backend

KINDS = None  # every kind
TAKES = 4  # a sound's takes an item page plays (score/dashboard/state/library.py MAX_TAKES)
FETCHES = 8  # fetches at once: a lone fetch waits about 1.6 s on its read (2026-10-20), so 3,000 took over an hour


def pictured(root, kinds):
    """[(entry address, picture file)] of every entry of `kinds` that names a picture it lists."""
    found = []
    for record in library.entries(root):
        named = (record.get("picture") or {}).get("file")
        if (kinds is None or record["kind"] in kinds) and named in record.get("files", {}):
            found.append((record["address"], named))
    return found


def role_files(record, role, suffixes):
    """The names of a record's files of `role` ending in `suffixes`, sorted (the order the cockpit reads them in)."""
    return sorted(name for name, described in record.get("files", {}).items()
                  if described.get("role") == role and name.lower().endswith(suffixes))


def viewer_files(record):
    """The files of one record its item page's viewer reads."""
    copy = record.get("web3d") if isinstance(record.get("web3d"), dict) else {}
    named = [copy.get("light")]
    if record["kind"] == "surface":
        named += role_files(record, "usd", (".usda",))[:1] + role_files(record, "texture", (".png", ".jpg", ".jpeg"))[:1]
    elif record["kind"] == "sound":
        named += role_files(record, "audio", (".ogg", ".wav", ".mp3", ".flac"))[:TAKES]
    elif record["kind"] == "effect":
        named.append("settings.json")
    elif record["kind"] == "light":
        named += role_files(record, "usd", (".usda",))
    elif record["kind"] == "model":
        named += role_files(record, "closeup", (".png", ".jpg", ".jpeg", ".webp"))[:1]  # the close-up it came from
    elif record["kind"] == "layer" and record["id"].startswith("light."):
        named.append("lamps.json")  # a place's lamps: where each stands and its strength
    return [name for name in named if name in record.get("files", {})]


def viewed(root, kinds):
    """[(entry address, file)] of every file an item page's viewer reads, for the entries of `kinds`."""
    return [(record["address"], named) for record in library.entries(root)
            if kinds is None or record["kind"] in kinds for named in viewer_files(record)]


def fetched(address, named):
    """The picture's path in the library cache, fetched when missing or changed; None when the library lost it."""
    files = backend.library_files
    return files.from_library(files.reference(address, named), files.parsed(files.reference(address, named)))


def lost_marker(root, address, named):
    """(the marker's path, the sha the entry records) of one file; the path None when the entry records none."""
    files = backend.library_files
    parts = files.parsed(files.reference(address, named))
    sha = files.recorded_sha(root, parts) if parts else None
    if sha is None:
        return None, None
    folder = files.cache_folder() / "score_lib" / parts["kind"] / parts["id"] / parts["version"]
    return folder / f"{parts['file']}.lost", sha


def held_or_why(address, named, root=None):
    """(True, None) when the file is in the cache, (False, why) when the library lost it or its fetch failed. A file
    the blob store answered 404 for is marked lost and not asked for again while its entry names the same bytes."""
    marker, sha = lost_marker(root, address, named) if root else (None, None)
    if marker and marker.is_file() and marker.read_text() == sha:
        return False, f"{address}: {named} lost (404 before)"
    try:
        return fetched(address, named) is not None, None
    except backend.library_files.LibraryUnreachable as failed:
        if marker and "(404)" in str(failed):
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(sha)
        return False, f"{address}: {str(failed).splitlines()[-1][-160:]}"


def fetched_line(label, wanted, root):
    """Fetch each (address, file) into the cache; its words: how many are there, how many not, the first error."""
    with ThreadPoolExecutor(FETCHES) as pool:
        found = list(pool.map(lambda pair: held_or_why(*pair, root), wanted))
    failed = [why for _, why in found if why]
    return f"{label}: {sum(held for held, _ in found)} of {len(wanted)}" + (
        f" ({len(failed)} not fetched, first: {failed[0]})" if failed else "")


def run(kinds=KINDS):
    """Fetch every picture and viewer file of `kinds` into the library cache; the summary line, naming how many
    could not be fetched and the first one's error (one lost file never stops the others)."""
    root = backend.settings().get("SCORE_LIB_ROOT")
    if not root:
        return "library pictures: no library folder (SCORE_LIB_ROOT, or the score_lib checkout beside score)"
    which = ", ".join(kinds) if kinds else "every kind"
    return (fetched_line(f"library pictures ({which}) in the cache", pictured(root, kinds), root) + "; "
            + fetched_line("viewer files", viewed(root, kinds), root))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--kind", action="append", help="an entry kind whose pictures to fetch (default: every kind)")
    options = parser.parse_args(argv)
    print(run(tuple(options.kind) if options.kind else KINDS))


if __name__ == "__main__":
    main()
