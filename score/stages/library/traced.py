"""The `traced` check's wrap of the library-finish check (score/stages/complete/library, its overlay), taken as it
landed and never edited here: every thing and every finish of the place's assembled stage traced to a library entry
or a written exception.

    context = traced.context_of(place, library_root, exceptions_file, store, data)
    traced.untraced(stage_file, context)     # the findings' sentences, [] when everything traces

The library is read from its folder after the handover (the shelf of entry.json files, read only), so what the node
just handed is on it; the store the assembled stage was checked out of gives its blobs and the accepted bakes'
finish records (read only, never a checkout or a write).
"""
import pathlib

from pxr import Usd

from score.stages.complete.library import entries, exceptions, findings, stored, trace
from score.store import PROPS_HOME, Store

# A world's places: each with a kept plan, its design's (stages.places; the filed kits and plans were retired, 2026-10-21).
KEPT_PLANS = PROPS_HOME / "design" / "plans"


def store_of(checkout):
    """The read-only store a checkout was made from (<root>/cache/checkouts/<output>), or None when it was not."""
    root = pathlib.Path(checkout).resolve().parents[2]
    if not (root / "objects").is_dir():
        return None
    return Store(stored.NodeFolders(root / "objects"), root / "cache")


def places_in(data):
    """Every place of the world (each with a kept plan; `data`, its data folder, holds none since 2026-10-21)."""
    return sorted(path.stem for path in KEPT_PLANS.glob("*.json"))


def context_of(place, library_root, exceptions_file, store, data):
    """The library-finish check's context: the shelf, the store's blobs, every place's accepted bakes, the written
    exceptions (exceptions.Refused when the file refuses one)."""
    return trace.Context(place=place, shelf=entries.read(library_root),
                         blobs=stored.blobs(store) if store else "",
                         baked=stored.baked(store, places_in(data)) if store else {},
                         exceptions=exceptions.read(exceptions_file) if exceptions_file else [])


def untraced(stage_file, context):
    """The sentences of every group of things or finishes that trace neither to the library nor to an exception."""
    rows = trace.rows(Usd.Stage.Open(str(stage_file)), context)
    return [group["sentence"] for group in findings.grouped(rows)]
