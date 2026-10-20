"""The library's pictures the cockpit shows, fetched into the library cache on the store's machine, so its tiles and
the state export have their bytes (#42: every place showed "no picture yet" while score_lib held each one).

    .venv/bin/python -m score.stages.library.pictures [--kind place ...]

Each entry of the kinds (default: every kind, so the Library screen's branches have their thumbnails) that names a
picture is fetched once by the library's own command into `$PROPS_HOME/cache/library/score_lib/<kind>/<id>/<version>/<file>` and checked against the sha256 its entry records
(tools/library/library_files.py `from_library`; a cached file that still hashes right is not fetched again). The
cockpit's library reads that cache when it has no blob folder (score/dashboard/state/library.py). Read only on the
library side; never a row, so nothing keys on it. A fetch costs one object read.
"""
import argparse

from score import library
from score.stages.library import backend

KINDS = None  # every kind


def pictured(root, kinds):
    """[(entry address, picture file)] of every entry of `kinds` that names a picture it lists."""
    found = []
    for record in library.entries(root):
        named = (record.get("picture") or {}).get("file")
        if (kinds is None or record["kind"] in kinds) and named in record.get("files", {}):
            found.append((record["address"], named))
    return found


def fetched(address, named):
    """The picture's path in the library cache, fetched when missing or changed; None when the library lost it."""
    files = backend.library_files
    return files.from_library(files.reference(address, named), files.parsed(files.reference(address, named)))


def held_or_why(address, named):
    """(True, None) when the picture is in the cache, (False, why) when the library lost it or its fetch failed."""
    try:
        return fetched(address, named) is not None, None
    except backend.library_files.LibraryUnreachable as failed:
        return False, f"{address}: {str(failed).splitlines()[-1][-160:]}"


def run(kinds=KINDS):
    """Fetch every picture of `kinds` into the library cache; the summary line, naming how many could not be
    fetched and the first one's error (one lost picture never stops the others)."""
    root = backend.settings().get("SCORE_LIB_ROOT")
    if not root:
        return "library pictures: no library folder (SCORE_LIB_ROOT, or the score_lib checkout beside score)"
    wanted = pictured(root, kinds)
    found = [held_or_why(address, named) for address, named in wanted]
    failed = [why for _, why in found if why]
    said = (f"library pictures: {sum(held for held, _ in found)} of {len(wanted)} "
            f"({', '.join(kinds) if kinds else 'every kind'}) in the cache")
    return said + (f"; {len(failed)} not fetched (first: {failed[0]})" if failed else "")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--kind", action="append", help="an entry kind whose pictures to fetch (default: every kind)")
    options = parser.parse_args(argv)
    print(run(tuple(options.kind) if options.kind else KINDS))


if __name__ == "__main__":
    main()
