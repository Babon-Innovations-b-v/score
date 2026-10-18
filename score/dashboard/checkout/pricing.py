"""A fix branch's price: the paid rows it moves from where it left main (score.stages.moved, run on the store's
machine), each paid node priced by the compute backend on the runner's measured numbers (score price, C19), and the
totals of an item and of the basket. Never per-piece prices alone: the pages show the basket's total against the stop.
"""
import json
import subprocess
import sys
import threading

from django.conf import settings
from django.utils import timezone

from score.dashboard.checkout import WORLD, git
from score.dashboard.launch import guard
from score.dashboard.pages.models import BranchPrice

_pricing = threading.Lock()


def moved_rows(repo, base, head):
    """{row: {paid, code, files, places}} of every row `head` moves against `base` (the moved-rows check)."""
    done = subprocess.run([sys.executable, "-m", "score.stages.moved", base, head, "--json"], cwd=repo,
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"the moved-rows check failed: {(done.stderr or done.stdout)[-600:]}")
    return json.loads(done.stdout.strip().splitlines()[-1])


def node_of(row, place):
    return row if place in ("None", "", None) else f"{row}@{place}"


def row_places(moved):
    """The places a moved row is made again at: every place it is declared at when its code moved, else the places
    of the files that moved."""
    if moved["code"]:
        return moved["places"]
    return sorted({place for places in moved["files"].values() for place in places})


def paid_nodes(rows):
    """The paid nodes the moved rows make again, sorted."""
    return sorted({node_of(row, place) for row, moved in rows.items() if moved["paid"] for place in row_places(moved)})


def line_of(node):
    return node.split("@")[1] if "@" in node else "world"


def span(prices, field, jobs):
    """The minutes a batch of these nodes takes at `field`: the longer of the longest line's sum and the total over
    `jobs` at once (an unmeasured node counts nothing; it is listed apart)."""
    lines = {}
    for node, price in prices.items():
        lines[line_of(node)] = lines.get(line_of(node), 0.0) + (price.get(field) or 0.0)
    return round(max(max(lines.values(), default=0.0), sum(lines.values()) / max(1, jobs)), 1)


def totals(prices, jobs=guard.DEFAULT_JOBS):
    """{likely_euros, high_euros, guessed_euros, likely_minutes, high_minutes, cards, nodes, unmeasured, unpriced} of
    nodes priced ({node: price}): likely and high the measured nodes' sums; `guessed_euros` the stage estimates of
    the nodes not measured yet (`unmeasured`), never part of the price; `unpriced` the nodes the runner could not
    price (each counts nothing)."""
    priced = {node: price for node, price in prices.items() if "error" not in price}
    measured = [price for price in priced.values() if price["likely_euros"] is not None]
    return {"likely_euros": round(sum(price["likely_euros"] for price in measured), 2),
            "high_euros": round(sum(price["high_euros"] for price in measured), 2),
            "guessed_euros": round(sum(price.get("guess_euros") or 0.0 for price in priced.values()
                                       if price["likely_euros"] is None), 2),
            "likely_minutes": span(priced, "likely_minutes", jobs), "high_minutes": span(priced, "high_minutes", jobs),
            "cards": sum(price.get("cards") or 0 for price in priced.values()), "nodes": len(prices),
            "unmeasured": sorted(node for node, price in priced.items() if not price.get("runs")),
            "unpriced": sorted(node for node in prices if node not in priced)}


def basket_prices(items):
    """{node: price} of every item's nodes, each node once (two branches that move one node buy it once)."""
    found = {}
    for item in items:
        found.update(item["nodes"])
    return found


def price_body(rows, prices):
    return {"rows": rows, "nodes": prices, "totals": totals(prices)}


def work_out(record, repo, chosen=None):
    """Fill a BranchPrice row (state working) with its body, in this thread; one branch priced at a time."""
    with _pricing:
        try:
            rows = moved_rows(repo, record.base, record.head)
            nodes = paid_nodes(rows)
            prices = (chosen or guard.backend()).price(WORLD, nodes) if nodes else {}
            record.body, record.state = price_body(rows, prices), "ready"
        except Exception as error:  # the page shows why the branch could not be priced
            record.state, record.error = "failed", f"{type(error).__name__}: {error}"
        record.finished = timezone.now()
        record.save()
    return record


def current(branch):
    """The BranchPrice row of the branch's commit now (made, still working, or failed), or None."""
    repo = settings.SCORE_REPO
    commit = git.head(repo, branch)
    return BranchPrice.objects.filter(branch=branch, head=commit, base=git.base(repo, commit)).first()


def start(branch):
    """Start pricing the branch's commit now in the background, unless it is priced or being priced; its row."""
    repo = settings.SCORE_REPO
    commit = git.head(repo, branch)
    record, made = BranchPrice.objects.get_or_create(branch=branch, head=commit, base=git.base(repo, commit))
    if made or record.state == "failed":
        record.state, record.error = "working", ""
        record.save()
        price_soon(record, repo)
    return record


def price_soon(record, repo):
    threading.Thread(target=work_out, args=(record, repo), daemon=True).start()
