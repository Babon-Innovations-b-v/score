"""A kept scene inventory reading fixed where both readers put a row inside another row's thing (2026-10-26: camp's
right-dome "door", Gemini's region of it the fridge's region and SAM 3's box of it the fridge's glass door; its
close-ups failed every take in Batch 1 try 4): that row is a part of the other's thing, read as a thing of its own,
and is merged into it, as reading.merged_rows merges two rows of one thing. Free, from the reading's own rows and
boxes: no Gemini call, no SAM 3. So is a row whose words say it sits on or at a seat another row is (`seats_named`): it
is anchored on that seat, so the cast seats it there (8 seated people sat on the floor, 2026-11-04). A person row
whose words name a seat no row holds (`seats_missing`: airlock's astronaut "sitting on bench" with no bench row, the
street's diner "sitting at a table" with no chair row, 2026-11-05) gets that seat added as a row of its own, sized from
the person, and is anchored on it: a design fix under the owner's standing word (STANDING), its reason in the row's
`added`.

The fixed reading is a new reading of the same lock (reading.kept, written once): its rows without the parts, each
child of one re-anchored on the thing it went into, `merged` naming them, `from` the reading it was fixed from, its
parts carried over, nothing spent. Its plan is written again from it on its own (plan_writing.owed) and its concept's
light asked of it (reading.lit), as for any new reading. The sync pass runs it before the parts, light and plans
(score/dashboard/sync/client.py readings_fixed).

Here, not in reading.py, which is in the code version of 74 paid rows (score.stages.moved, 2026-10-26): an edit
there re-keys them all; no stage imports this module.

    python -m score.review.reading_fixes [<place> ...]     # every locked place when none is named
"""
import re
import sys

from score.review import concepts, reading
from score.store import Store, locked, stamp_key

# A row's boxes lie inside another row's when this share of each is in one of its (`part_of`): the camp door's box
# lies wholly in the fridge's; the lab's chairs, under the people sitting in them, about 60%.
INSIDE = 0.9
# What a row's words say it sits on or at (its name, then where it is): "sitting on bench 1", "sitting at dining table".
SITS = re.compile(r"\b(?:sitting|seated) (on|at) ([a-z_ ]+)")
# What a person sits on at these (`seat_said`): a chair at a table, a desk, a counter, a console.
AT_SEAT = {"table": "chair", "desk": "chair", "counter": "stool", "bar": "stool", "console": "chair",
           "workstation": "chair", "terminal": "chair"}
# A seat added under a sitter is sized from the person (`seat_row`): its seat this share of the seated person's height
# over the floor (a seated body 1.3 m tall sits 0.46 m up, a dining chair's seat height, 0.43-0.48 m), a chair's back
# rising to twice that (a dining chair's 0.9 m); its footprint the person's, a bench's as wide as its sitters.
SEAT_SHARE = 0.35
BACKED = {"chair": 2.0, "armchair": 2.0}
# The owner's standing word a seat added under a sitter stands on (#72, as the plans' redrawings).
STANDING = {"words": "the owner's standing word, relayed by the score session (#72, 2026-11-05): design fixes that "
                     "follow his rules are ours to make; follow the concept", "at": "2026-11-05"}


def part_of(row, other, size):
    """Whether object row `row` is a part of `other`'s thing: neither stands on the other, Gemini's regions of the two
    are one thing (reading.same), and every box SAM 3 found of it lies INSIDE a box of `other`, the bigger."""
    if (row is other or reading.structural(row) or reading.structural(other)
            or not (row["region"] and other["region"] and row["boxes"] and other["boxes"])
            or row["anchor"] == f"on:{other['id']}" or other["anchor"] == f"on:{row['id']}"):
        return False
    return (reading.same(reading.pixels(row["region"], size, 0), reading.pixels(other["region"], size, 0))
            and all(any(reading.shared(box, held) >= INSIDE * reading.area(box) for held in other["boxes"])
                    for box in row["boxes"])
            and sum(map(reading.area, row["boxes"])) < sum(map(reading.area, other["boxes"])))


def parts_apart(rows, size):
    """(the rows without each one that is a part of another's thing (`part_of`), [{name, row, into}] of those)."""
    kept, merged = list(rows), []
    while found := next(((row, other) for row in kept for other in kept if part_of(row, other, size)), None):
        kept.remove(found[0])
        merged.append({"name": found[0]["name"], "row": found[0]["id"], "into": found[1]["id"]})
    return kept, merged


def words_of(text):
    return set(re.split(r"[^a-z]+", text.lower())) - {"", "a", "an", "the", "of"}


def seats_named(rows):
    """{row id: "on:<seat>"} of each row whose words say it sits on or at a thing (SITS) that names exactly one other
    row, a seat (its id's words name one: people_rows.seat_of), and that is not anchored on it already."""
    from score.stages import people_rows
    seats = [row for row in rows if people_rows.seat_of({"anchor": f"on:{row['id']}"})]
    found = {}
    for row in rows:
        said = [words for _, words in said_seats(row)]
        named = [seat["id"] for seat in seats if seat is not row and said
                 and words_of(said[0]) & words_of(f"{seat['id']} {seat['name']}")]
        if len(named) == 1 and row["anchor"] != f"on:{named[0]}":
            found[row["id"]] = f"on:{named[0]}"
    return found


def said_seats(row):
    """[(on or at, the words after)] of each seat a row's words say it sits on or at (SITS): its name's, then its
    where's."""
    return [match.groups() for text in (row["name"], row.get("where") or "")
            for match in [SITS.search(text.lower())] if match]


def seat_said(said):
    """The seat (a people_rows.SEAT_WORDS word) a sitter's words (`said_seats`' first) put it on: the seat named
    ("on bench"), or the one a person sits on at the thing named ("at a table": AT_SEAT); None for the floor or
    anything else."""
    from score.stages import people_rows
    how, words = said
    named = [word for word in re.split(r"[^a-z]+", words) if word in people_rows.SEAT_WORDS]
    if named:
        return named[0]
    at = [AT_SEAT[word] for word in re.split(r"[^a-z]+", words) if word in AT_SEAT] if how == "at" else []
    return at[0] if at else None


def seats_missing(rows):
    """{person row id: its seat word} of each person row (plan_checks.people) that sits on or at a seat its words
    name (`seat_said`), whose words name no seat row (as `seats_named` reads them) and that is not anchored on a seat
    already."""
    from score.review import plan_checks
    from score.stages import people_rows
    people, found = plan_checks.people({"rows": rows}), {}
    for row in rows:
        said = said_seats(row)
        if row["id"] in people and said and not people_rows.seat_of(row) \
                and (seat := seat_said(said[0])) and not any(
                    words_of(said[0][1]) & words_of(f"{other['id']} {other['name']}") for other in rows
                    if other is not row and people_rows.seat_of({"anchor": f"on:{other['id']}"})):
            found[row["id"]] = seat
    return found


def seat_row(person, seat, ids):
    """The seat row added under `person` (a row of the reading) sitting on a `seat`: its own id (the person's and the
    seat's, numbered past any id taken in `ids`), standing on what the person stood on, sized from the person
    (SEAT_SHARE, BACKED), its region the lower half of the person's (the seat is under the sitter; no SAM 3 box of
    its own, the sitter hides it), and `added` saying why, under the owner's standing word (STANDING)."""
    row_id, number = f"{person['id']}_{seat}", 1
    while row_id in ids:
        number += 1
        row_id = f"{person['id']}_{seat}_{number}"
    wide, deep, tall = (float(side) for side in person["size"]) if isinstance(person.get("size"), list) \
        else (None, None, None)
    count = int(person.get("count") or 1)
    size = None if tall is None else [round(wide * (count if seat == "bench" else 1), 3), round(deep, 3),
                                      round(tall * SEAT_SHARE * BACKED.get(seat, 1.0), 3)]
    region = person.get("region")
    how, words = said_seats(person)[0]
    return {"id": row_id, "name": seat, "noun": seat, "kind": "generate", "terrain": False,
            "count": 1 if seat == "bench" else count, "anchor": person["anchor"], "where": f"under {person['id']}",
            "region": [region[0] + (region[2] - region[0]) / 2, region[1], region[2], region[3]] if region else None,
            "size": size, "view": person.get("view"), "box": None, "boxes": [],
            "size_words": "sized from the person on it", "thing": "", "part": "object", "seat_for": person["id"],
            "added": {**STANDING, "reason": f"the {person['name']} ({person['id']}) sits {how} {words.strip()} in "
                                            f"the concept and no row holds its {seat}: a {seat} added under it, "
                                            "sized from the person, so the cast seats it there, not on the floor"}}


def seats_added(rows):
    """(the rows with a seat row added under each person `seats_missing` finds, each such person anchored on its
    own seat; {person id: "on:<seat>"})."""
    found, ids, added = seats_missing(rows), {row["id"] for row in rows}, {}
    kept = []
    for row in rows:
        if row["id"] in found:
            seat = seat_row(row, found[row["id"]], ids)
            ids.add(seat["id"])
            added[row["id"]] = f"on:{seat['id']}"
            kept += [dict(row, anchor=added[row["id"]]), seat]
        else:
            kept.append(row)
    return kept, added


def to_fix(store, places):
    """The places of `places` whose current reading holds a row that is a part of another's thing, one sitting on
    a seat it is not anchored on, or one sitting on a seat no row holds."""
    return [place for place in places if (found := reading.reading_of(store, place))
            and (parts_apart(found["inventory"]["rows"], found["size"])[1] or seats_named(found["inventory"]["rows"])
                 or seats_missing(found["inventory"]["rows"]))]


def fixed_record(store, found, by):
    """The new reading of `found` (the current one, its parts read over its rows) with its parts merged away and each
    row sitting on a seat anchored on it (`seated`), a seat no row held added under its sitter (`seats_added`)."""
    rows, merged = parts_apart(found["inventory"]["rows"], found["size"])
    rows = reading.reanchored([dict(row) for row in rows], {item["row"]: f"on:{item['into']}" for item in merged})
    seated = seats_named(rows)
    rows = [dict(row, anchor=seated.get(row["id"], row["anchor"])) for row in rows]
    rows, added = seats_added(rows)
    seated = {**seated, **added}
    parted = all("part" in row for row in rows) and reading.parts_current(store, found)
    return {**{key: value for key, value in found.items() if key != "parts_version"},
            **({"parts_version": reading.PARTS_VERSION} if parted else {}),
            "at": concepts.now(), "by": by, "from": f"{reading.AREA}/{found['place']}/{stamp_key(found['at'])}.json",
            "inventory": {**found["inventory"], "rows": rows}, "gaps": reading.gaps(rows),
            "merged": found.get("merged", []) + merged,
            "seated": found.get("seated", []) + [{"row": row, "anchor": anchor} for row, anchor in seated.items()],
            "euros": {"rows": 0.0, "boxes": 0.0, "total": 0.0},
            "seconds": {"rows": 0.0, "boxes": 0.0, "card": 0.0}}


def fix(store, places, by):
    """Each place of `places` whose current reading holds a part fixed (`fixed_record`), under its reading lock (a
    reading under way finishes first); the fixed records."""
    found = []
    for place in to_fix(store, places):
        with locked(store.cache / reading.AREA / "locks" / f"{place}.lock"):
            if place in to_fix(store, [place]):
                found.append(reading.kept(store, fixed_record(store, reading.reading_of(store, place), by)))
    return found


def said(records):
    """The fixes in words."""
    return f"readings fixed: {', '.join(record['place'] for record in records)}" if records else "readings: none to fix"


if __name__ == "__main__":
    folder = Store.default()
    print(said(fix(folder, sys.argv[1:] or concepts.placed(folder), "python -m score.review.reading_fixes")))
