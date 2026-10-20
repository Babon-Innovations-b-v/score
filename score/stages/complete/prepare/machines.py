"""One machine class and zone a layer, fixed before the batch (#21: no class chain inside it). The class is the
first of the layer's runner's classes in its kind's own order (capacity.order_for: the cheapest card per job first,
measured), leaving out a class the kind never takes (capacity.NEVER) and, when a free stock read is given, a class
with no zone in stock. The zone is the one of that class with the best boot record in the cloud ledgers (machines
that came up over every start tried, out-of-stock refusals apart; most starts breaking ties), in stock where the
stock was read. A layer of Google calls rents nothing.

The ledgers read are the paper's copy (paper/evidence/cloud/ledger.jsonl) and the live one, each batch once; the
live ledger began again on 2026-10-19, so the copy holds most of the record.
"""
import json
import pathlib

from score.adapters import compute

REPO = pathlib.Path(__file__).resolve().parents[4]
EVIDENCE_LEDGER = REPO / "paper/evidence/cloud/ledger.jsonl"
OUT_OF_STOCK = "out of stock"
SHORTAGE = "shortage"  # the backend's stock word for none to be had
# Each card or processor layer of the remake: (its ledger kind, the classes its runner asks for, where they are set).
LAYERS = {
    "pixal": ("pixal", None, "tools/props/cloud/capacity.py KINDS['pixal']"),
    "surfaces-paint": ("blender", ("cpu-32c-128gb", "cpu-32c-64gb", "cpu-32c-256gb", "cpu-16c-64gb"),
                       "score/stages/surfaces/place_line.py PAINT_CLASSES"),
    "surfaces-bake": ("library", ("gpu-24gb", "gpu-48gb", "gpu-80gb"), "score/stages/surfaces/place_line.py CLASSES"),
    "settle": ("blender", ("cpu-4c-32gb",), "#20: every drop on one 4-core machine"),
}


def capacity():
    """tools/props/cloud/capacity.py (the runner's classes and order)."""
    compute.ledger()  # puts tools/props/cloud on the path
    import capacity as found
    return found


def ledger_entries(live=None):
    """Every batch of the paper's ledger copy and the live ledger (`live`, else ledger.entries()), each batch once."""
    seen, found = set(), []
    copy = [json.loads(line) for line in EVIDENCE_LEDGER.read_text().splitlines() if line.strip()]
    for entry in copy + (compute.ledger().entries() if live is None else live):
        name = entry.get("batch") or json.dumps(entry, sort_keys=True)
        if name not in seen:
            seen.add(name)
            found.append(entry)
    return found


def class_names(backend_classes):
    """{machine type: class} from the backend's {class: (machine types)}."""
    return {machine_type: machine_class for machine_class, types in backend_classes.items() for machine_type in types}


def boot_records(entries, classes_of):
    """{(kind, class, zone): {"up", "failed", "out_of_stock"}} of every machine start in the ledgers: a machine row
    not marked as never started came up; an attempt is out of stock or a failed start."""
    found = {}
    for entry in entries:
        kind = entry.get("kind") or "pixal"  # an entry from before kinds were named was a Pixal3D batch
        for row in entry.get("machines") or []:
            tally(found, kind, row, classes_of)["up" if row.get("started", True) else "failed"] += 1
        for row in entry.get("attempts") or []:
            outcome = "out_of_stock" if row.get("why") == OUT_OF_STOCK else "failed"
            tally(found, kind, row, classes_of)[outcome] += 1
    return found


def tally(found, kind, row, classes_of):
    """The boot record a ledger row counts in."""
    key = (kind, classes_of.get(row.get("type"), row.get("type")), row.get("zone"))
    return found.setdefault(key, {"up": 0, "failed": 0, "out_of_stock": 0})


def candidates(stage, cap):
    """(kind, the layer's classes in its kind's order, without the classes it never takes), or None for a layer of
    calls. `cap` is capacity.py."""
    if stage not in LAYERS:
        return None
    kind, classes, _ = LAYERS[stage]
    listed = classes or cap.classes_for(kind)
    usable = [name for name in listed if name not in cap.NEVER.get(kind, ())]
    return kind, sorted(usable, key=lambda name: (cap.speed_rank(name, kind), listed.index(name)))


def in_stock(stock):
    """{(class, zone)} of the offers of a free stock read that are not short."""
    return {(offer.machine_class, offer.zone) for offer in stock if offer.stock_word != SHORTAGE}


def best_zone(kind, machine_class, records, stocked):
    """The zone of a class with the best boot record (most up over all starts tried, then most starts), among the
    stocked zones when `stocked` is given; (zone, record) or (None, None)."""
    zones = [(zone, record) for (each, name, zone), record in records.items() if each == kind and name == machine_class
             and (stocked is None or (machine_class, zone) in stocked)]
    if not zones:
        return None, None
    tried = lambda record: record["up"] + record["failed"]  # noqa: E731
    return max(zones, key=lambda pair: (pair[1]["up"] / max(1, tried(pair[1])), tried(pair[1])))


def fixed(stage, records, cap, stock=None):
    """{kind, class, zone, boot, why} fixed for a layer: None for a layer of calls. `stock` is a free stock read
    (provider Offers) or None when not read."""
    found = candidates(stage, cap)
    if found is None:
        return None
    kind, classes = found
    stocked = in_stock(stock) if stock is not None else None
    for machine_class in classes:
        if stocked is not None and not any(name == machine_class for name, _ in stocked):
            continue
        zone, record = best_zone(kind, machine_class, records, stocked)
        why = "first class in the kind's order" + (", in stock" if stocked is not None else ", stock not read")
        return {"kind": kind, "class": machine_class, "zone": zone, "boot": record,
                "why": why if zone else why + "; no boot record of it in the ledgers, zone left to the claim"}
    return {"kind": kind, "class": None, "zone": None, "boot": None,
            "why": "no class of the layer in stock: its jobs are holes unless stock comes back before the batch"}
