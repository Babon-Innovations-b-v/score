"""What makes a made proposal ready for the owner, on the store's machine and free: its paid part priced at the
runner's own numbers (the compute backend's `price`, `score price`, C19) for the commit it was made at, and its
before pictures, the same cameras on the place as it stands accepted now (one small local Blender job under the
machine's one-heavy-job lock, as the stills). The propose command finishes each proposal it makes;

    .venv/bin/python -m score.dashboard proposals-finish [--no-before]

finishes every proposal not finished at its commit, and each sync pass prices any not priced before the export
(sync/client.py), so no proposal reaches the basket without its price because somebody forgot a step.
"""
import pathlib
import shutil
import tempfile
import time

from score.dashboard.checkout import WORLD
from score.dashboard.checkout.pricing import totals
from score.dashboard.launch import guard
from score.dashboard.proposals import pictures, records
from score.dashboard.web3d import convert

BEFORE = "before"


def paid_nodes(record):
    """The nodes the proposal could not make for free (taken as "needs the paid batch"), sorted."""
    return sorted({item["node"] for item in record.get("layers", []) if item["how"] == records.PAID})


def priced(record, chosen=None):
    """The proposal's paid part priced at the runner's numbers: {commit, at, nodes, totals}, or {commit, at, error}."""
    nodes = paid_nodes(record)
    at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        prices = (chosen or guard.backend()).price(WORLD, nodes) if nodes else {}
    except (RuntimeError, ValueError, OSError) as failed:  # said on the page as "price not worked out"
        return {"commit": record["commit"], "at": at, "error": str(failed)[-600:]}
    return {"commit": record["commit"], "at": at, "nodes": prices, "totals": totals(prices)}


def price_due(record):
    """True when the proposal has no price for the commit it was made at (or its last pricing failed)."""
    price = record.get("price") or {}
    return price.get("commit") != record["commit"] or "error" in price


def before_due(record):
    return record.get("before_commit") != record["commit"] and bool(record.get("stills"))


def before_views(stage_folder, record):
    """The cameras of the proposal's own stills, read from the place as it stands (its scene record) or the main
    checkout's data/scene/<place>.json: those named like the stills, else the first few."""
    found = pictures.record_views(stage_folder, pictures.REPO, record["place"])
    named = {still.get("name") for still in record.get("stills", [])}
    views = [view for view in found if view.get("name") in named] or found
    return [{"name": view["name"], "eye": view["eye"], "aim": view["aim"], "up": view.get("up", pictures.UP),
             "fov": float(view.get("fov", 75.0)), "look_only": True} for view in views[:pictures.MOST_STILLS]]


def before_stills(record, store_root, out):
    """The before stills into `out`: [{name, file}] Blender drew, or [{"error": why}] when there is nothing accepted
    to draw or Blender could not."""
    node = f"{record.get('target') or 'assembly'}@{record['place']}"
    accept = convert.standing_accept(pathlib.Path(store_root), node)
    if accept is None:
        return [{"error": f"{record['place']} has nothing accepted yet: no before picture"}]
    work = pathlib.Path(tempfile.mkdtemp(prefix="proposal-before-"))
    try:
        stage_folder = convert.linked_output(pathlib.Path(store_root), accept["output"], work / "stage")
        convert.linked_neighbours(pathlib.Path(store_root), record["place"], work)
        made = pictures.stills(stage_folder / f"{record['place']}.usda", before_views(stage_folder, record), out)
        return [{**still, "file": f"{BEFORE}/{pathlib.Path(still['file']).name}"} for still in made]
    except RuntimeError as failed:
        return [{"error": str(failed)[-1000:]}]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def with_before(root, record, store_root):
    """Draw the proposal's before stills into its folder's before/ (swapped in whole); the record's new fields."""
    folder = records.folder(root, record["branch"], record["place"])
    partial = pathlib.Path(tempfile.mkdtemp(prefix=".before-", dir=folder))
    made = before_stills(record, store_root, partial)
    shutil.rmtree(folder / BEFORE, ignore_errors=True)
    partial.rename(folder / BEFORE)
    return {"before": made, "before_commit": record["commit"]}


def finish(root, branch, place, store_root, with_pictures=True, chosen=None):
    """Price the proposal and draw its before stills where due; the finished record, or None when there is none."""
    record = records.read(root, branch, place)
    if record is None:
        return None
    fields = {}
    if price_due(record):
        fields["price"] = priced(record, chosen)
    if with_pictures and before_due(record):
        fields.update(with_before(root, record, store_root))
    return records.amend(root, branch, place, fields) if fields else record


def finish_all(root, store_root, with_pictures=True, chosen=None):
    """Finish every proposal under `root`; [(branch, place)] of those it changed."""
    changed = []
    for summary in records.listing(root):
        record = records.read(root, summary["branch"], summary["place"])
        if record and (price_due(record) or (with_pictures and before_due(record))):
            finish(root, record["branch"], record["place"], store_root, with_pictures, chosen)
            changed.append((record["branch"], record["place"]))
    return changed
