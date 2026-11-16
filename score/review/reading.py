"""The kept scene inventory readings, read only (CONTEXT.md "scene inventory"). Readings are made no more: the owner
dropped the per-picture reading chain (#128, 2026-11-16: "also code for just score, like we have seen this approach
just doesnt work"; the Gemini rows, their counts and the plan writing wiped). The SAM 3 boxes and masks of a concept
picture are the new placing agent's object list (score/review/concept_objects.py). What the old chain kept in the
store stays readable here for the stages that still lay the places from it (prepare, the scene record, the light
layer), until they go too:

    inventory-readings/<place>/<time>.json  {place, concept, at, by, method, inventory {rows}, gaps, ...}
    inventory-parts/<place>/<time>.json     {place, reading (the reading's `at`), version, parts {row id: part}}
    inventory-light/<place>/<time>.json     {place, reading, light {rows, scene}}

A reading counts only when made by METHOD from the place's picked draw (`reading_of`), its rows' parts read over it
(`with_parts`) and its concept's light beside it (`concept_light`).
"""
from score.review import concepts
from score.store import stamp_key

AREA = "inventory-readings"
PARTS_AREA = "inventory-parts"  # the parts asked of a reading answered before `part` was
LIGHT_AREA = "inventory-light"  # the concept's light asked of a reading
ANCHORS = ("floor", "wall", "ceiling", "roof", "ground", "sky")
# What part of the place a row is (`part`, answered with the rows; a reading answered before it was asked got its rows'
# parts in one call of their own, `parted`): prepare routes each row by it (score/stages/complete/prepare/groups.py),
# never by a list of nouns (owner, 2026-10-25: "no hax tho ... framework remember").
PARTS = {"object": "a thing made as a model of its own: furniture, a machine, a vehicle, a plant, a lamp, a sign, a "
                   "person, a rock, a boulder or any other feature lying on the land",
         "floor": "a floor, deck or raised level people stand on, or its plates",
         "wall": "a wall of the place, or its panels, or the hull, dome or tube enclosing the room the picture is "
                 "inside of, whole",
         "roof": "a roof or ceiling over the place, or its panels",
         "opening": "a doorway, an open gap or a hole cut in a wall (not the door or window filling it)",
         "structure": "any other built structure: a door, a window, stairs, a ramp, beams, pillars, ribs, a "
                      "building's dome, hull or tube seen standing in the place, a whole building's shell",
         "ground": "the land or street surface itself the place stands on (the ground, the road, the pavement, the "
                   "plaza, the hills), never a feature lying on it",
         "sky": "the sky, a planet, a moon",
         "effect": "water, rain, smoke, mist, steam or fog",
         "backdrop": "a far city or landscape well beyond the place, seen as its backdrop"}
# The parts' version: a reading whose rows were answered under an older PARTS (its `parts_version`, 1 when it has none)
# has the newest parts record of this version read over them.
PARTS_VERSION = 2
# The reading's method: a reading made by another counts for nothing (5: only what both readers agreed on is a row).
METHOD = 5


def readings(store, place):
    """The place's readings, oldest first."""
    return [store.read(key) for key in sorted(concepts.keys_under(store, f"{AREA}/{place}/"))]


def reading_of(store, place):
    """The newest reading of the place's picked draw by today's METHOD, or None (none picked, none read from this
    pick by it, or only ones whose rows answer was refused: those are read again)."""
    sha = concepts.picked(store, place)
    found = next((found for found in reversed(readings(store, place))
                  if sha and found["concept"] == sha and found.get("method") == METHOD and not found.get("refused")),
                 None)
    return found and with_parts(store, found)


def part_records(store, place):
    """The place's parts records (`parted`), oldest first."""
    return [store.read(key) for key in sorted(concepts.keys_under(store, f"{PARTS_AREA}/{place}/"))]


def asked_parts_of(store, record, current=False):
    """The parts of the newest parts record asked of a reading (`parted`), of today's PARTS_VERSION when `current`;
    None without one."""
    return next((found["parts"] for found in reversed(part_records(store, record["place"]))
                 if found["reading"] == record["at"] and "parts" in found
                 and (not current or found.get("version", 1) >= PARTS_VERSION)), None)


def with_parts(store, record):
    """A reading with each row's part: from the newest parts record of today's PARTS_VERSION asked of it where its own
    are older, else as answered, else from the newest parts record asked of it (`parted`); a row none gives keeps none
    (prepare waits on it)."""
    rows = record["inventory"]["rows"]
    again = None if record.get("parts_version", 1) >= PARTS_VERSION else asked_parts_of(store, record, current=True)
    if again is not None:
        return {**record, "inventory": {**record["inventory"], "rows": [
            {**row, "part": again[row["id"]]} if row["id"] in again else row for row in rows]}}
    if all("part" in row for row in rows):
        return record
    given = asked_parts_of(store, record)
    if given is None:
        return record
    return {**record, "inventory": {**record["inventory"], "rows": [
        {**row, "part": given[row["id"]]} if "part" not in row and row["id"] in given else row for row in rows]}}


def light_records(store, place):
    """The place's concept light records (`lit`), oldest first."""
    return [store.read(key) for key in sorted(concepts.keys_under(store, f"{LIGHT_AREA}/{place}/"))]


def concept_light(store, place):
    """The light of the place's current reading's concept (`lit`: {rows: {id: {glows, glowing, colour, brightness}},
    scene: {daylight, unseen, unseen_colour}}), or None while it has none."""
    found = reading_of(store, place)
    return found and next((record["light"] for record in reversed(light_records(store, place))
                           if record["reading"] == found["at"] and "light" in record), None)


def row_boxes(store, place, row):
    """The pixel boxes [left, top, right, bottom] on the place's picked concept of every instance of its inventory row
    `row` (its id) that SAM 3 found, surest first; [] when it found none; None while the place's picked draw has no
    reading or the reading has no such row."""
    found = reading_of(store, place)
    rows = {item["id"]: item for item in (found["inventory"]["rows"] if found else [])}
    return rows[row]["boxes"] if row in rows else None


def kept(store, record):
    """One reading record written once in the store (the stand-in readings the tests of the stages that still read
    them lay); the record."""
    store.write_once(f"{AREA}/{record['place']}/{stamp_key(record['at'])}.json", record)
    return record
