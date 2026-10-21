"""Scene inventory reading (CONTEXT.md "scene inventory"; the owner, 2026-10-21): a picked concept read into its rows
in two steps, no agent in the loop, run on its own after his pick (root CLAUDE.md: readings run without asking; every
reading's cost is recorded and its running total shown in the cockpit).

1. Gemini 3.1 Pro gets the picked concept and the picked concept of the place it sits within and answers its rows
   (ASKED: kind, name, the noun SAM 3 finds it by, count, its size in metres judged from what it is and the picture,
   wide, deep and tall, against the place's own outline from the layer above's plan when it has one (OUTLINE), and
   in words, where it stands, children on their parent) in the inventory's row schema
   (tools/props/scene/inventory.py: `size` the metres, `size_words` the words), one direct call on the Google ledger.
   A row whose metres are not three lengths has no size, a gap of its place (`gaps`); SAM 3 gives where, never size.
2. SAM 3 finds each row's noun in the concept (tools/props/scene/box_masks.py on one rented card through
   tools/props/cloud/box_masks_cloud.py, every place of one reading run on the same card), each instance's pixel box
   kept on its row, and asks PROBES, generic words, for what no row names. Where the two disagree it is a gap on the
   place (`gaps`), never guessed past: a row SAM 3 finds none of, a count SAM 3 finds another number of, a thing
   found that no row's instances cover.

A run is cleared by compute.reading_clearance (the owner's standing allowance, or a benchmark grant when
SCORE_BENCHMARK_GRANT names one) and each place's reading kept in the store, written once:

    inventory-readings/<place>/<time>.json  {place, concept, above, at, by, size [w, h], inventory {scene, place,
                                             concept_pick {sha256}, rows}, gaps [{kind, row, words, ...}],
                                             euros {rows, boxes, total}, seconds {rows, boxes, card}, clearance}

A place whose picked draw has a reading already is not read again (`to_read`). A place whose rows answer is off the
row schema is kept with `refused` (why) and its call's euros, no SAM 3 asked for it, and is read again next time.

    python -m score.review.reading <place> [<place> ...] [--by <name>]
"""
import argparse
import concurrent.futures
import contextlib
import json
import os
import pathlib
import sys
import time
import urllib.error

from score.review import concepts
from score.store import Store, locked, stamp_key

AREA = "inventory-readings"
MODEL = "gemini-3.1-pro-preview"
CALLER = "inventory-reading"
TIMEOUT = 400
KINDS = ("generate", "code")
ANCHORS = ("floor", "wall", "ceiling", "roof", "ground", "sky")
# Generic words SAM 3 is asked on every concept, for the things no row names.
PROBES = ("object", "machine", "furniture", "container", "vehicle", "person")
PROBE_KEEP = 40
# A thing SAM 3 finds under a probe counts only above this share of the picture, and below box_check's BROAD.
SMALLEST = 0.001
BROAD = 0.5
# A probe's instance is covered when this share of its box lies in a row's instance; two probes' instances are one
# thing when they share this much of their union.
COVERED = 0.5
SAME = 0.6
KEEP_MOST = 120
# A row's region (Gemini's box round all of it) widened by this share of the picture each way when SAM 3's instances
# of its noun are given to the rows that name it.
MARGIN = 0.05
# The reading's method: a reading made by another counts for nothing and is read again (2: rows with regions, SAM 3
# asked once a noun and its instances given to the row whose region holds them; 3: terrain features are rows, tagged
# `terrain`, and letters drawn onto the picture are none: owner, 2026-10-21; 4: each row's size in metres, against
# the place's outline: #10, 2026-10-21).
METHOD = 4
ASKED = """You are reading a concept painting of one place of a game environment into its scene inventory: the hard
list of exactly what the picture shows, every object one row. {within}

Answer one JSON object {{"rows": [row, ...]}}, a row for every distinct kind of thing the first picture shows (its
shell, floors, walls, roof, openings and doors too, and every object, fitting, machine, plant and person, and every
terrain feature: rocks, boulders, outcrops, craters, ridges, dunes, cairns, stone rings, tracks in the ground and any
other feature of the ground, each a row like any object). Letters, numbers, labels or any text drawn onto the picture
are no rows: skip them. Each row with:
- "id": a short snake_case id, unique;
- "name": what it is in a few plain words, as a maker would name it ("white louvred locker", "rusted fuel drum");
- "noun": one to three words a segmentation model finds it by in the picture ("locker", "fuel drum");
- "kind": "generate" for an object made as a model of its own, "code" for structure and repeated fittings (walls,
  floor plates, roof panels, pipes, cables, rails, lamps on a wall, signs);
- "terrain": true for a terrain feature (the ground itself and anything formed of it or lying on it as part of the
  land: rocks, boulders, craters, ridges, dunes, cairns, tracks), else false;
- "count": how many of it the picture shows, counted, not guessed (a repeated panel counted as it shows);
- "size": its rough size in words, against a person (1.8 m) or the thing it stands on ("waist high, two strides
  long", "as tall as the hall");
- "metres": its size in metres, [wide, deep, tall], of one of it, judged from what it is and how big it shows
  against the people and things around it (a car about [4.8, 1.9, 1.5], a person [0.5, 0.3, 1.8], a door
  [1.0, 0.1, 2.1]); wide across its front, deep front to back, tall upright; a thing on a wall or a ceiling too,
  and a thing standing on another row its own size, not its parent's;{outline}
- "anchor": "floor", "wall", "ceiling", "roof", "ground", "sky" (a planet, a moon, a backdrop), or "on:<id>" for a
  thing standing on, hung on or fixed to another row (a radio on a desk, a lamp on a mast);
- "where": where in the picture it stands, in a few words ("left wall, by the door", "centre, under the crane");
- "region": the box round every one of it in the first picture, [ymin, xmin, ymax, xmax] on a 0 to 1000 scale.
Only what this picture shows; nothing hidden, nothing added for the game. No text besides the JSON."""
OUTLINE = (" the whole place is about {wide:g} m wide and {deep:g} m deep (its outline in its plan), so no row is "
           "bigger than it and every row's metres fit it")
WITHIN = ("The second picture is the picked concept of {holder}, the place this one sits within: it shows where this "
          "place stands; read only the first picture's place.")


def picture_path(store, sha, folder):
    """A stored picture's bytes as a file under `folder` (SAM 3's jobs and the call read files); its path."""
    path = pathlib.Path(folder) / f"{sha}.png"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(store.objects.read_bytes(f"blobs/{sha}"))
    return path


def readings(store, place):
    """The place's readings, oldest first."""
    return [store.read(key) for key in sorted(store.objects.keys(f"{AREA}/{place}/"))]


def reading_of(store, place):
    """The newest reading of the place's picked draw by today's METHOD, or None (none picked, none read from this
    pick by it, or only ones whose rows answer was refused: those are read again)."""
    sha = concepts.picked(store, place)
    return next((found for found in reversed(readings(store, place))
                 if sha and found["concept"] == sha and found.get("method") == METHOD and not found.get("refused")),
                None)


def to_read(store, places):
    """The places of `places` with a picked draw that has no reading yet."""
    return [place for place in places if concepts.picked(store, place) and not reading_of(store, place)]


def row_boxes(store, place, row):
    """The pixel boxes [left, top, right, bottom] on the place's picked concept of every instance of its inventory row
    `row` (its id) that SAM 3 found, surest first; [] when it found none; None while the place's picked draw has no
    reading or the reading has no such row."""
    found = reading_of(store, place)
    rows = {item["id"]: item for item in (found["inventory"]["rows"] if found else [])}
    return rows[row]["boxes"] if row in rows else None


def spent(store, places):
    """The euros every reading of `places` cost, in sum (the cockpit's running total)."""
    return round(sum(found["euros"]["total"] for place in places for found in readings(store, place)), 4)


def asked_body(place, concept, holder_picture, holder=None, outline=None):
    """The Gemini request: the wording (with the place's outline (wide, deep) in metres when it has one), the concept
    and, for a place within another, that one's picked concept."""
    from PIL import Image
    pro, _, _ = concepts.tools()
    holder = holder or concepts.above(place)
    within = WITHIN.format(holder=concepts.name_of(holder)) if holder_picture else ""
    told = OUTLINE.format(wide=outline[0], deep=outline[1]) if outline and all(outline) else ""
    parts = [{"text": ASKED.format(within=within, outline=told)},
             pro.part(Image.open(concept), max(Image.open(concept).size))]
    if holder_picture:
        parts.append(pro.part(Image.open(holder_picture), max(Image.open(holder_picture).size)))
    return {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}


def answer_text(response):
    return "".join(part.get("text", "") for candidate in response.get("candidates", [])
                   for part in candidate.get("content", {}).get("parts", []) if not part.get("thought"))


def call_euros(response):
    """What one answered call cost, as google_spend wrote it on its ledger."""
    _, google_spend, _ = concepts.tools()
    usage = response.get("usageMetadata", {})
    tier = usage.get("serviceTier") or response.get("serviceTier")
    return round(google_spend.dollars(MODEL, usage) * google_spend.TIER_PRICE.get(str(tier).lower(), 1.0)
                 * google_spend.EUROS_PER_DOLLAR, 6)


def asked(body):
    """One Gemini call (google_spend, on its ledger, never cached: each reading its own call); (response, seconds)."""
    _, google_spend, secret_store = concepts.tools()
    began = time.time()
    try:
        response = google_spend.generate(MODEL, body, secret_store.secret("gemini-api-key"), TIMEOUT, caller=CALLER)
    except urllib.error.HTTPError as error:
        raise concepts.Refused(f"the model refused ({error.code})") from error
    return response, round(time.time() - began, 1)


def rows_of(text):
    """The answered rows, each checked against the row schema; concepts.Refused for an answer off it. An anchor that
    names a row bare is read as on it; an anchor or region off the schema is None, a gap of its row (`gaps`)."""
    try:
        rows = json.loads(text)["rows"]
    except (ValueError, KeyError, TypeError) as failed:
        raise concepts.Refused(f"the rows answer is no JSON object with rows: {str(failed)[:200]}") from failed
    ids = [row.get("id") for row in rows]
    for row in rows:
        wrong = [name for name in ("id", "name", "noun", "size", "where") if not str(row.get(name) or "").strip()]
        wrong += [] if row.get("kind") in KINDS else ["kind"]
        wrong += [] if isinstance(row.get("count"), int) and row["count"] > 0 else ["count"]
        wrong += [] if isinstance(row.get("terrain"), bool) else ["terrain"]
        if wrong:
            raise concepts.Refused(f"row {row.get('id')!r} has no valid {', '.join(wrong)}")
        row["anchor"] = anchor_of(str(row.get("anchor", "")), ids)
        row["region"] = region_of(row.get("region"))
    if len(set(ids)) != len(ids):
        raise concepts.Refused("two rows share an id")
    return rows


def anchor_of(anchor, ids):
    """A row's anchor in the schema's words, or None."""
    if anchor in ANCHORS or anchor.startswith("on:") and anchor[3:] in ids:
        return anchor
    return f"on:{anchor}" if anchor in ids else None


def metres_of(metres):
    """[wide, deep, tall] metres, three positive numbers, or None."""
    if (isinstance(metres, list) and len(metres) == 3
            and all(isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 for value in metres)):
        return [float(value) for value in metres]
    return None


def outline_of(store, place):
    """(wide, deep) metres of the place's outline: its box in the layer above's plan, else its own data/plans plan;
    None when neither gives one."""
    from score.review import plans
    found = plans.outline_from_holder(store, place, plans.base_plan(place))
    return found if all(found) else None


def region_of(region):
    """[ymin, xmin, ymax, xmax] on the 0 to 1000 scale, or None."""
    if (isinstance(region, list) and len(region) == 4 and all(isinstance(value, (int, float)) for value in region)
            and 0 <= region[0] < region[2] <= 1000 and 0 <= region[1] < region[3] <= 1000):
        return region
    return None


def keep_of(rows, noun):
    """How many instances of `noun` SAM 3 keeps: twice what the rows naming it count, at least 5, at most KEEP_MOST."""
    return min(KEEP_MOST, max(5, 2 * sum(row["count"] for row in rows if row["noun"] == noun)))


def sam_job(place, picture, rows, size):
    """box_masks.py's job for one concept: each noun the rows name once (`<place>.=<noun>`) and each probe
    (`<place>.~<word>`), over the whole picture."""
    whole = [0, 0, size[0], size[1]]
    return {"picture": str(picture),
            "rows": [{"key": f"{place}.={noun}", "nouns": [noun], "box": whole, "keep": keep_of(rows, noun)}
                     for noun in sorted({row["noun"] for row in rows})]
            + [{"key": f"{place}.~{word}", "nouns": [word], "box": whole, "keep": PROBE_KEEP} for word in PROBES]}


def area(box):
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def shared(first, second):
    """The area two boxes share."""
    return area([max(first[0], second[0]), max(first[1], second[1]), min(first[2], second[2]),
                 min(first[3], second[3])])


def distinct(boxes):
    """The boxes with every one that is the same thing as an earlier one dropped (SAME of their union)."""
    kept = []
    for box in boxes:
        if all(shared(box, other) < SAME * (area(box) + area(other) - shared(box, other)) for other in kept):
            kept.append(box)
    return kept


def pixels(region, size):
    """A 0 to 1000 [ymin, xmin, ymax, xmax] region as a pixel box [left, top, right, bottom], widened by MARGIN."""
    wide, tall = size
    return [(region[1] / 1000 - MARGIN) * wide, (region[0] / 1000 - MARGIN) * tall,
            (region[3] / 1000 + MARGIN) * wide, (region[2] / 1000 + MARGIN) * tall]


def holder_of(box, rows, size):
    """The row of `rows` (all naming one noun) an instance's box is given to: the one whose widened region holds its
    centre, the smallest when several do; the only row when it has no region; else None."""
    across, down = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    regions = [(pixels(row["region"], size), number) for number, row in enumerate(rows) if row["region"]]
    holding = [(area(region), number) for region, number in regions
               if region[0] <= across <= region[2] and region[1] <= down <= region[3]]
    if holding:
        return rows[min(holding)[1]]
    return rows[0] if len(rows) == 1 and not rows[0]["region"] else None


def boxed_rows(place, rows, measured, size):
    """(the rows with the pixel boxes of SAM 3's instances of their noun given to them (`boxes`, surest first, one
    thing once; the surest as `box`), [{noun, box}] of the instances no row of their noun holds)."""
    given, loose = {row["id"]: [] for row in rows}, []
    for noun in sorted({row["noun"] for row in rows}):
        naming = [row for row in rows if row["noun"] == noun]
        for box in distinct([item["box"] for item in measured.get(f"{place}.={noun}", [])]):
            holder = holder_of(box, naming, size)
            (given[holder["id"]] if holder else loose).append(box if holder else {"noun": noun, "box": box})
    return [{**{key: value for key, value in row.items() if key != "metres"}, "view": "v1",
             "box": (given[row["id"]] or [None])[0], "boxes": given[row["id"]], "size": metres_of(row.get("metres")),
             "size_words": row["size"], "thing": ""} for row in rows], loose


def unnamed(place, rows, measured, size):
    """[{word, box}] of what SAM 3 finds under a probe that no row's instance covers, each thing once."""
    whole = size[0] * size[1]
    named = [box for row in rows for box in row["boxes"]]
    found = [(word, item["box"]) for word in PROBES for item in measured.get(f"{place}.~{word}", [])
             if SMALLEST * whole <= area(item["box"]) < BROAD * whole]
    loose = [(word, box) for word, box in found if all(shared(box, other) < COVERED * area(box) for other in named)]
    kept = distinct([box for _, box in loose])
    return [{"word": next(word for word, box in loose if box is kept_box), "box": kept_box} for kept_box in kept]


def gaps(rows, things, loose=()):
    """Where Gemini's rows and SAM 3's instances disagree, a gap each (CONTEXT.md "gap"), never guessed past: an
    anchor, region or size not read, a row none of whose noun is found in its region, a count found otherwise, an
    instance of a row's noun where no row of it stands, a thing found that no row names."""
    found = [{"kind": name, "row": row["id"], "words": f"its {name} not read"}
             for row in rows for name in ("anchor", "region", "size") if not row[name]]
    for row in rows:
        seen, keep = len(row["boxes"]), keep_of(rows, row["noun"])
        if not seen:
            found.append({"kind": "not found", "row": row["id"], "words": f"no {row['noun']} found"})
        elif seen != row["count"]:
            more = "at least " if seen >= keep else ""
            found.append({"kind": "count", "row": row["id"], "rows_count": row["count"], "found": seen,
                          "words": f"{row['count']} read, {more}{seen} found"})
    return found + [{"kind": "outside", "row": None, "box": item["box"],
                     "words": f"a {item['noun']} found where no row of it stands"} for item in loose] + [
        {"kind": "unnamed", "row": None, "box": thing["box"], "words": f"a {thing['word']} found that no row names"}
        for thing in things]


def card_estimate(jobs):
    """The euros SAM 3's card is forecast at for `jobs` (box_masks_cloud's minutes at the dearest card offered)."""
    sys.path.insert(0, str(concepts.REPO / "tools/props/cloud"))
    import batch
    import box_masks_cloud
    import capacity
    import ledger
    found = batch.offers(list(capacity.classes_for(box_masks_cloud.KIND)))
    if not found:
        raise concepts.Refused("no card for SAM 3 is sold in the zones used")
    minutes = box_masks_cloud.SETUP_MINUTES + len(jobs) * box_masks_cloud.SECONDS_A_PICTURE / 60
    return ledger.cost(minutes, max(offer.per_card for offer in found)), minutes


def boxes_of(jobs, folder):
    """SAM 3 on one rented card over every job; (instances by key, its ledger entry)."""
    sys.path.insert(0, str(concepts.REPO / "tools/props/cloud"))
    import box_masks_cloud
    (folder / "jobs.json").write_text(json.dumps(jobs, indent=1))
    entry = box_masks_cloud.mask(folder / "jobs.json", folder / "masks.json")
    return json.loads((folder / "masks.json").read_text()), entry


def card_seconds(entry):
    """(seconds SAM 3 ran on the card, seconds the card took to answer and be set up) of box_masks_cloud's entry."""
    working = sum(second for machine in entry.get("machines", []) for second in machine.get("unit_seconds", []))
    return round(working, 1), round(entry["wall_minutes"] * 60 - working, 1)


def asked_rows(store, place, folder):
    """Step 1 for one place: (rows, the call's euros, seconds, the concept's path, its size); rows is why it was
    refused (a string) when the answer is off the row schema."""
    from PIL import Image
    sha = concepts.picked(store, place)
    concept = picture_path(store, sha, folder)
    holder = concepts.above(place, store)
    holder_sha = holder and concepts.picked(store, holder)
    holder_picture = holder_sha and picture_path(store, holder_sha, folder)
    response, seconds = asked(asked_body(place, concept, holder_picture, holder, outline_of(store, place)))
    (folder / f"{place}-answer.json").write_text(json.dumps(response, indent=1))
    try:
        rows = rows_of(answer_text(response))
    except concepts.Refused as refused:
        rows = str(refused)
    return rows, call_euros(response), seconds, concept, Image.open(concept).size


def read(store, places, by, **steps):
    """read_now holding each place's lock (taken in order, across processes), so a second run of the same place (a
    second pick, the backfill) waits for the first and then finds it read: nothing is paid twice."""
    with contextlib.ExitStack() as held:
        for place in sorted(set(places)):
            held.enter_context(locked(store.cache / AREA / "locks" / f"{place}.lock"))
        return read_now(store, places, by, **steps)


def read_now(store, places, by, clear=None, ask=asked_rows, boxes=boxes_of):
    """Read every place of `places` whose pick has no reading yet, inside one clearance (`clear(places, euros)`,
    compute.reading_clearance by default) and one SAM 3 card; the readings kept. concepts.Refused or
    compute.Refused when it may not run or a step fails (the steps already paid stay on their ledgers)."""
    from score.adapters import compute
    unpicked = [place for place in places if not concepts.picked(store, place)]
    if unpicked:
        raise concepts.Refused(f"{', '.join(unpicked)}: no picked concept; a place's inventory is read only after its "
                               "own pick")
    places = to_read(store, places)
    if not places:
        return []
    folder = store.cache / AREA / stamp_key(concepts.now())
    folder.mkdir(parents=True, exist_ok=True)
    estimate = compute.READING_GEMINI_EUROS * len(places) + (card_estimate([None] * len(places))[0]
                                                             if boxes is boxes_of else 0.0)
    ticket = (clear or compute.reading_clearance)(store, places, round(estimate, 4))
    with compute.spending(ticket):
        compute.require_cleared("a scene inventory reading", store)
        with concurrent.futures.ThreadPoolExecutor(len(places)) as pool:  # the asks side by side, each its own call
            asked_places = dict(zip(places, pool.map(lambda place: ask(store, place, folder), places)))
        refused = {place: answer for place, answer in asked_places.items() if isinstance(answer[0], str)}
        for place, (why, euros, seconds, _, _) in refused.items():
            kept(store, {"place": place, "concept": concepts.picked(store, place), "at": concepts.now(), "by": by,
                         "refused": why, "euros": {"rows": euros, "boxes": 0.0, "total": euros},
                         "seconds": {"rows": seconds, "boxes": 0.0, "card": 0.0}})
        asked_places = {place: answer for place, answer in asked_places.items() if place not in refused}
        if not asked_places:
            return []
        jobs =[sam_job(place, concept, rows, size) for place, (rows, _, _, concept, size) in asked_places.items()]
        measured, entry = boxes(jobs, folder)
    working, card = card_seconds(entry)
    found = []
    for place, (rows, euros, seconds, _, size) in asked_places.items():
        boxed, loose = boxed_rows(place, rows, measured, size)
        share = round(entry["euros"] / len(asked_places), 6)
        record = {"place": place, "concept": concepts.picked(store, place), "at": concepts.now(), "by": by,
                  "above": (holder := concepts.above(place, store)) and concepts.picked(store, holder),
                  "size": list(size),
                  "inventory": {"scene": place, "place": place, "concept_pick": {"sha256": concepts.picked(store, place)},
                                "plan": {"views": [{"id": "v1", "picture": f"blobs/{concepts.picked(store, place)}"}]},
                                "rows": boxed},
                  "gaps": gaps(boxed, unnamed(place, boxed, measured, size), loose), "method": METHOD,
                  "euros": {"rows": euros, "boxes": share, "total": round(euros + share, 6)},
                  "seconds": {"rows": seconds, "boxes": round(working / len(asked_places), 1), "card": card},
                  "clearance": {"node": ticket["node"], "key": ticket["key"]}}
        found.append(kept(store, record))
    return found


def kept(store, record):
    """One reading (or one refused) written once in the store; the record."""
    store.write_once(f"{AREA}/{record['place']}/{stamp_key(record['at'])}.json", record)
    return record


def main(argv):
    """Read the places named; one line a place (rows, gaps, euros, seconds), or the refusal on stderr with exit 1."""
    from score.adapters.compute import Refused as NotCleared
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("places", nargs="+")
    parser.add_argument("--by", default="the owner's standing allowance")
    options = parser.parse_args(argv)
    store = Store.in_folder(os.environ["SCORE_SPEND_STORE"]) if os.environ.get("SCORE_SPEND_STORE") else Store.default()
    try:
        found = read(store, options.places, options.by)
    except (concepts.Refused, NotCleared) as refused:
        print(f"refused: {refused}", file=sys.stderr)
        return 1
    for record in found:
        print(json.dumps({"place": record["place"], "rows": len(record["inventory"]["rows"]),
                          "gaps": len(record["gaps"]), "euros": record["euros"], "seconds": record["seconds"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
