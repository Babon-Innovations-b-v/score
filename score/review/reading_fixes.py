"""A kept scene inventory reading fixed where both readers put a row inside another row's thing (2026-10-26: camp's
right-dome "door", Gemini's region of it the fridge's region and SAM 3's box of it the fridge's glass door; its
close-ups failed every take in Batch 1 try 4): that row is a part of the other's thing, read as a thing of its own,
and is merged into it, as reading.merged_rows merges two rows of one thing. Free, from the reading's own rows and
boxes: no Gemini call, no SAM 3. So is a row whose words say it sits on or at a seat another row is (`seats_named`): it
is anchored on that seat, so the cast seats it there (8 seated people sat on the floor, 2026-11-04).

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
SITS = re.compile(r"\bsitting (?:on|at) ([a-z_ ]+)")


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
        said = [match.group(1) for text in (row["name"], row.get("where") or "")
                for match in [SITS.search(text.lower())] if match]
        named = [seat["id"] for seat in seats if seat is not row and said
                 and words_of(said[0]) & words_of(f"{seat['id']} {seat['name']}")]
        if len(named) == 1 and row["anchor"] != f"on:{named[0]}":
            found[row["id"]] = f"on:{named[0]}"
    return found


def to_fix(store, places):
    """The places of `places` whose current reading holds a row that is a part of another's thing, or one sitting on
    a seat it is not anchored on."""
    return [place for place in places if (found := reading.reading_of(store, place))
            and (parts_apart(found["inventory"]["rows"], found["size"])[1] or seats_named(found["inventory"]["rows"]))]


def fixed_record(store, found, by):
    """The new reading of `found` (the current one, its parts read over its rows) with its parts merged away and each
    row sitting on a seat anchored on it (`seated`)."""
    rows, merged = parts_apart(found["inventory"]["rows"], found["size"])
    rows = reading.reanchored([dict(row) for row in rows], {item["row"]: f"on:{item['into']}" for item in merged})
    seated = seats_named(rows)
    rows = [dict(row, anchor=seated.get(row["id"], row["anchor"])) for row in rows]
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
