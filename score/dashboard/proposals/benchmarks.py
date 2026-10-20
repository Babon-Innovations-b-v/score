"""The benchmarks as one basket item (#21): "Benchmarks", its estimate and ETA from prepare's record
(score/stages/complete/prepare/benchmarks.py, `benchmarks.listed` in WORK/checks/prepare/remake.json), so the owner
buys all of them with one Buy, its stop the batch's high plus 10% like any item's. Each benchmark is one entry of the
item's `nodes` (`benchmark-<id>`, none of them a runner node) priced as prepare estimated it: likely and high, or its
row's estimate as `guess_euros` while its stages have no measured per unit; its minutes on one line (they run one
after another). A benchmark prepare names a gap is said in `gaps` and is in no price. The checkout launches the item
as one batch (`RunGroup.benchmarks`), never through the runner's plan of nodes. Plain files only, as records.py.
"""
import json
import pathlib

from score.dashboard.checkout import pricing
from score.dashboard.proposals import records

ID = "benchmarks"
TITLE = "Benchmarks"
NODE = "benchmark-"
RECORD = "work/checks/prepare/remake.json"  # prepare's record, under PROPS_HOME


def node_price(each):
    """A benchmark as a priced node of pricing.totals: prepare's euros and minutes, never measured runs (`runs` 0)."""
    return {"likely_euros": each["likely_euros"], "high_euros": each["high_euros"], "guess_euros": each["guess_euros"],
            "likely_minutes": each["likely_minutes"], "high_minutes": each["high_minutes"], "runs": 0}


def item(listed):
    """The basket item of prepare's listed benchmarks, or None when none of them can run."""
    running = [each for each in listed if not each.get("gap")]
    if not running:
        return None
    nodes = {f"{NODE}{each['id']}": node_price(each) for each in running}
    why = {f"{NODE}{each['id']}": f"benchmark: {each['what']}" for each in running}
    return {"id": ID, "title": TITLE, "places": [], "place": None, "layers": ["benchmarks"], "nodes": nodes,
            "why": why, "again": [], "missing": [], "declared": False, "benchmarks": True,
            "gaps": [{"id": each["id"], "what": each["what"], "why": each["gap"]}
                     for each in listed if each.get("gap")],
            "totals": pricing.totals(nodes), "version": version(nodes, why)}


def version(nodes, why):
    from score.dashboard.proposals.make import version as hashed  # one version rule for every item
    return hashed(nodes, why)


def from_record(props_home):
    """The item from prepare's record under `props_home`, or None before prepare listed any benchmark."""
    path = pathlib.Path(props_home) / RECORD
    if not path.is_file():
        return None
    return item(json.loads(path.read_text()).get("benchmarks", {}).get("listed", []))


def with_item(items, found):
    """The basket's items with the benchmarks item in place of an older one (dropped when `found` is None)."""
    kept = [each for each in items if each["id"] != ID]
    return kept + [found] if found else kept


def put(root, props_home):
    """Write prepare's benchmarks item into the basket's index at `root` (made when there is none yet); its words."""
    found = from_record(props_home)
    index = records.index(root)
    records.put_index(root, {**index, "items": with_item(index.get("items", []), found)})
    if found is None:
        return "benchmarks: none listed"
    return (f"benchmarks: EUR {found['totals']['likely_euros']:.2f} to {pricing.cleared_high(found['totals']):.2f}, "
            f"{len(found['nodes'])} to run, {len(found['gaps'])} gaps")
