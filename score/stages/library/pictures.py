"""The library's pictures the cockpit shows, fetched into the library cache on the store's machine, so its tiles and
the state export have their bytes (#42: every place showed "no picture yet" while score_lib held each one).

    .venv/bin/python -m score.stages.library.pictures [--kind place ...]

Each entry of the kinds (default: place) that names a picture is fetched once by the library's own command into
`$PROPS_HOME/cache/library/score_lib/<kind>/<id>/<version>/<file>` and checked against the sha256 its entry records
(tools/library/library_files.py `from_library`; a cached file that still hashes right is not fetched again). The
cockpit's library reads that cache when it has no blob folder (score/dashboard/state/library.py). Read only on the
library side; never a row, so nothing keys on it. A fetch costs one object read.
"""
import argparse

from score import library
from score.stages.library import backend

KINDS = ("place",)


def pictured(root, kinds):
    """[(entry address, picture file)] of every entry of `kinds` that names a picture it lists."""
    found = []
    for record in library.entries(root):
        named = (record.get("picture") or {}).get("file")
        if record["kind"] in kinds and named in record.get("files", {}):
            found.append((record["address"], named))
    return found


def fetched(address, named):
    """The picture's path in the library cache, fetched when missing or changed; None when the library lost it."""
    files = backend.library_files
    return files.from_library(files.reference(address, named), files.parsed(files.reference(address, named)))


def run(kinds=KINDS):
    """Fetch every picture of `kinds` into the library cache; the summary line. Raises LibraryUnreachable on the
    first that cannot be fetched (the caller says it)."""
    root = backend.settings().get("SCORE_LIB_ROOT")
    if not root:
        return "library pictures: no library folder (SCORE_LIB_ROOT, or the score_lib checkout beside score)"
    wanted = pictured(root, kinds)
    held = sum(1 for address, named in wanted if fetched(address, named) is not None)
    return f"library pictures: {held} of {len(wanted)} ({', '.join(kinds)}) in the cache"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--kind", action="append", help="an entry kind whose pictures to fetch (default: place)")
    options = parser.parse_args(argv)
    print(run(tuple(options.kind or KINDS)))


if __name__ == "__main__":
    main()
