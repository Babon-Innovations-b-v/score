"""What makes a made proposal ready for the owner, on the store's machine and free: its paid part priced at the
runner's own numbers (the compute backend's `price`, `score price`, C19) for the commit it was made at, its own
stills when it was made without them (its assembled stage, kept in the proposals' scratch store), its before
pictures, the proposal's own drawing (drawing.py: the same cameras, moments, size and lamps rule) on the place as it
stands accepted now (one small local Blender job under the machine's one-heavy-job lock, as the stills), and the
measure of the one against the other (compare.py): a proposal whose after shows nothing its before does not is
held out of the basket with its plain reason. The propose command finishes each proposal it makes;

    .venv/bin/python -m score.dashboard proposals-finish [--no-before]

finishes every proposal not finished at its commit, and each sync pass prices and measures any not done before the
export (sync/client.py), so no proposal reaches the basket unpriced or unmeasured because somebody forgot a step.
"""
import json
import pathlib
import shutil
import subprocess
import tempfile
import time

from score.dashboard.checkout import WORLD, pricing
from score.dashboard.checkout.pricing import totals
from score.dashboard.launch import guard
from score.dashboard.proposals import compare, drawing, pictures, records
from score.dashboard.web3d import convert

BEFORE = "before"
CLIP = "before-after-moments.mp4"  # the clip of the drawing's moments (compare.clip), in the proposal's media/
WORK = "proposals-work"  # propose.py's scratch folder in the dashboard's home: its store keeps each proposal's stage
MOVED = {}  # (base, commit): the paid nodes its moved rows make again, worked out once a process


def moved_paid(record):
    """The paid nodes the proposal's branch makes again, at every place (checkout/pricing.py, as the basket prices
    the branch): the record's own list from propose.py, else the moved-rows check of its commits, once a commit."""
    if "moved_paid" in record:
        return record["moved_paid"]
    key = (record["base"], record["commit"])
    if key not in MOVED:
        from django.conf import settings
        MOVED[key] = pricing.paid_nodes(pricing.moved_rows(settings.SCORE_REPO, *key))
    return MOVED[key]


def paid_nodes(record, branch_nodes):
    """The place's paid nodes, sorted: those the proposal could not make for free (taken as "needs the paid batch")
    and those of `branch_nodes` (the branch's paid nodes) at its place."""
    taken = {item["node"] for item in record.get("layers", []) if item["how"] == records.PAID}
    return sorted(taken | {node for node in branch_nodes if node.endswith(f"@{record['place']}")})


def priced(record, chosen=None):
    """The proposal's paid part priced at the runner's numbers: {commit, at, moved, nodes, totals, branch_nodes}, or
    {commit, at, error}. `nodes` are the place's; `branch_nodes` the rest of what buying its branch makes again
    (other places, the environment's own rows), so a fix's total is what the checkout buys."""
    at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        branch_nodes = moved_paid(record)
        nodes = paid_nodes(record, branch_nodes)
        wanted = sorted(set(nodes) | set(branch_nodes))
        prices = (chosen or guard.backend()).price(WORLD, wanted) if wanted else {}
    except (RuntimeError, ValueError, OSError) as failed:  # said on the page as "price not worked out"
        return {"commit": record["commit"], "at": at, "error": str(failed)[-600:]}
    here = {node: prices[node] for node in nodes if node in prices}
    return {"commit": record["commit"], "at": at, "moved": True, "nodes": here, "totals": totals(here),
            "branch_nodes": {node: price for node, price in prices.items() if node not in here}}


def price_due(record):
    """True when the proposal has no price for the commit it was made at (or its last pricing failed)."""
    price = record.get("price") or {}
    return price.get("commit") != record["commit"] or "error" in price or not price.get("moved")


def drawing_due(record):
    """True when the proposal was put together but has no drawing (drawing.py) to draw its pictures from."""
    return bool(record.get("assembly")) and not record.get("drawing")


def worked_drawing(record, roots):
    """The drawing of a proposal made before drawings were kept: from its own assembled stage (its scene record's
    cameras and time span) and its layers; no film plan, the branch's checkout being gone."""
    work = pathlib.Path(tempfile.mkdtemp(prefix="proposal-drawing-"))
    try:
        stage_folder = linked_from(roots, record["assembly"], work / "stage")
        stage_file = stage_folder / f"{record['place']}.usda"
        return drawing.plan(record.get("layers") or [], pictures.record_views(stage_folder, pictures.REPO,
                                                                              record["place"]),
                            span=pictures.time_span(stage_file))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def before_due(record):
    """True when the proposal has stills but no before stills drawn for its commit (or the last drawing failed)."""
    drawn = record.get("before_commit") == record["commit"] and not any("error" in still
                                                                       for still in record.get("before") or [])
    return not drawn and any("file" in still for still in record.get("stills") or [])


def before_stills(record, store_root, out):
    """The before stills into `out`: [{name, file}] Blender drew, or [{"error": why}] when there is nothing accepted
    to draw or Blender could not. The same drawing as the proposal's own stills (its cameras, moments, size, and
    its lamps rule: lit by the accepted stage's own lamps), on the same row's accepted output (the place, with its
    neighbours where the proposal shows them)."""
    node = f"{record.get('target') or 'assembly'}@{record['place']}"
    accept = convert.standing_accept(pathlib.Path(store_root), node)
    if accept is None:
        return [{"error": f"{record['place']} {compare.NOTHING_ACCEPTED}: no before picture"}]
    work = pathlib.Path(tempfile.mkdtemp(prefix="proposal-before-"))
    try:
        stage_folder = convert.linked_output(pathlib.Path(store_root), accept["output"], work / "stage")
        return pictures.stills(stage_folder / f"{record['place']}.usda", record["drawing"], out, BEFORE)
    except RuntimeError as failed:
        return [{"error": str(failed)[-1000:]}]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def stills_due(record):
    """True when the proposal was put together but has no still drawn (made with --no-stills, or drawing failed)."""
    return bool(record.get("assembly")) and not any("file" in still for still in record.get("stills") or [])


def linked_from(roots, output, folder):
    """The output's files as links into `folder`, its listing and each blob read from the first root that has it
    (the proposals' scratch store, then the store): the folder."""
    listing = next(json.loads(path.read_text()) for path in (root / "objects" / "outputs" / f"{output}.json"
                                                               for root in roots) if path.is_file())
    for name, sha in listing.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(next(blob for blob in (root / "objects" / "blobs" / sha for root in roots)
                               if blob.is_file()))
    return folder


def after_stills(record, roots, out):
    """The proposal's own stills of its assembled stage into `out`, from its drawing (as propose.py draws them):
    [{name, file}], or [{"error": why}]."""
    work = pathlib.Path(tempfile.mkdtemp(prefix="proposal-after-"))
    try:
        stage_folder = linked_from(roots, record["assembly"], work / "stage")
        return pictures.stills(stage_folder / f"{record['place']}.usda", record["drawing"], out)
    except (RuntimeError, StopIteration) as failed:
        return [{"error": f"{type(failed).__name__}: {str(failed)[-1000:]}"}]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def scratch_roots(root, store_root):
    """Where a proposal's own outputs are read: the proposals' scratch store, then the store."""
    return [pathlib.Path(root).parent / WORK / "store", pathlib.Path(store_root)]


def with_drawing(root, record, store_root):
    """The drawing worked out for a proposal made before drawings were kept; the record's new fields."""
    try:
        return {"drawing": worked_drawing(record, scratch_roots(root, store_root))}
    except (RuntimeError, StopIteration) as failed:
        return {"drawing": None, "drawing_error": f"{type(failed).__name__}: {str(failed)[-600:]}"}


def with_stills(root, record, store_root):
    """Draw the proposal's own stills into its folder's stills/ (swapped in whole); the record's new fields."""
    folder = records.folder(root, record["branch"], record["place"])
    partial = pathlib.Path(tempfile.mkdtemp(prefix=".stills-", dir=folder))
    made = after_stills(record, scratch_roots(root, store_root), partial)
    shutil.rmtree(folder / "stills", ignore_errors=True)
    partial.rename(folder / "stills")
    return {"stills": made, "hero": next((still["file"] for still in made if "file" in still), None)}


def with_before(root, record, store_root):
    """Draw the proposal's before stills into its folder's before/ (swapped in whole); the record's new fields."""
    folder = records.folder(root, record["branch"], record["place"])
    partial = pathlib.Path(tempfile.mkdtemp(prefix=".before-", dir=folder))
    made = before_stills(record, store_root, partial)
    shutil.rmtree(folder / BEFORE, ignore_errors=True)
    partial.rename(folder / BEFORE)
    return {"before": made, "before_commit": record["commit"]}


def measured_of(record):
    """What a difference is measured from: the commit and every still and before still drawn."""
    return {"commit": record["commit"],
            "of": sorted(still["file"] for still in (record.get("stills") or []) + (record.get("before") or [])
                         if "file" in still)}


def difference_due(record):
    """True when the proposal's after and before were never measured against each other as they stand now."""
    found = record.get("difference") or {}
    return {"commit": found.get("commit"), "of": found.get("of")} != measured_of(record)


def with_difference(root, record):
    """Each after still measured against its before (compare.py), and the before-and-after clip of the drawing's
    moments where it has one, into media/; the record's new fields."""
    folder = records.folder(root, record["branch"], record["place"])
    fields = {"difference": {**compare.difference(folder, record), **measured_of(record)}}
    media = [item for item in record.get("media") or [] if item.get("name") != CLIP]
    try:
        made = compare.clip(folder, record, folder / "media" / CLIP)
    except (OSError, subprocess.CalledProcessError) as failed:  # said on the record; the stills stand without it
        fields["clip_error"] = str(failed)[-600:]
        made = None
    fields["media"] = media + ([made] if made else [])
    return fields


def finish(root, branch, place, store_root, with_pictures=True, chosen=None):
    """Price the proposal, draw its stills and before stills where due and measure the one against the other; the
    finished record, or None when there is none."""
    record = records.read(root, branch, place)
    if record is None:
        return None
    fields = {}
    if price_due(record):
        fields["price"] = priced(record, chosen)
    if with_pictures and (stills_due(record) or before_due(record)) and drawing_due(record):
        fields.update(with_drawing(root, record, store_root))
        record = {**record, **fields}
    if with_pictures and stills_due(record) and record.get("drawing"):
        fields.update(with_stills(root, record, store_root))
        record = {**record, **fields}
    if with_pictures and before_due(record) and record.get("drawing"):
        fields.update(with_before(root, record, store_root))
        record = {**record, **fields}
    if difference_due(record):
        fields.update(with_difference(root, record))
    return records.amend(root, branch, place, fields) if fields else record


def finish_all(root, store_root, with_pictures=True, chosen=None):
    """Finish every proposal under `root`; [(branch, place)] of those it changed."""
    changed = []
    for summary in records.listing(root):
        record = records.read(root, summary["branch"], summary["place"])
        if record and (price_due(record) or difference_due(record) or
                       (with_pictures and (stills_due(record) or before_due(record)))):
            finish(root, record["branch"], record["place"], store_root, with_pictures, chosen)
            changed.append((record["branch"], record["place"]))
    return changed
