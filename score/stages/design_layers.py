"""Which layers a scene has, from its own design alone (the owner, 2026-10-21: "the modules are not agnostic"): its
locked concept's scene inventory, kept where the plan stage reads it ({home}/design/inventory/<place>.json, written
by score/review/plans.keep from the reading of the locked draw), each row's kind by the one row-kind classification
(row_kinds.py, data/checks/row-kinds.json). One answer for the stage table (which layer rows a place has:
score/stages `designed`) and the assembly's layers gate (which layers it waits on: assembly.needed_layers), so the
two cannot disagree, and a new environment or a scene added in the app needs no hand-written list. A scene's design
shows a layer of kind:

    people         a row that acts (a person, an astronaut, a crowd): its cast and characters layer
    crops          a row that grows standing on a bed (BEDS, or a row that grows itself: a planter): the beds' crops
    effects        a row that emits (a kettle, a stove): its effects layer
    motion         a row that moves (a door, a crane, a lift, a machine): its motion layer, which moves the row's
                   own laid objects (their models are the prop pipeline's, laid by the assembly like any other)
    physics        a row that is loose (a chair, a crate): where it settles, its physics layer and trial
    light, sound   every designed scene (EVERY_SCENE)

A place with no kept inventory (its concept not locked, or not read) has no design: no layer row applies there, and
its assembly's layers gate answers unknown.
"""
import functools
import json
import pathlib

from score.stages import row_kinds
from score.store import PROPS_HOME

KEPT = PROPS_HOME / "design" / "inventory"
PATTERN = "{home}/design/inventory/{place}.json"
# What a crop row stands on: a row of one of these nouns, or a row that grows itself (a planter).
BEDS = {"bed", "beds", "planter", "planters", "plot", "plots", "trough", "troughs", "field", "fields"}
EVERY_SCENE = ("light", "sound")
# The layer a row shows by what its kind does (row_kinds.does); crops by its own rule (row_layers).
DOES = {"acts": "people", "emits": "effects", "moves": "motion", "loose": "physics"}


def holder_of(row, rows):
    """The row a row stands on (its anchor `on:<id>`), None for one on the floor, a wall or nothing named."""
    anchor = str(row.get("anchor") or "")
    return rows.get(anchor.removeprefix("on:")) if anchor.startswith("on:") else None


def on_bed(row, rows, kinds):
    """Whether a row stands on a bed: a row whose noun is a bed's (BEDS) or that grows itself."""
    holder = holder_of(row, rows)
    return holder is not None and (row_kinds.words(holder.get("noun")) in BEDS
                                   or "grows" in row_kinds.does(row_kinds.kind_of(holder, kinds), kinds))


def row_layers(row, rows, kinds):
    """The layer kinds one row shows (module docstring)."""
    done = row_kinds.does(row_kinds.kind_of(row, kinds), kinds)
    found = {DOES[what] for what in done if what in DOES}
    if "grows" in done and on_bed(row, rows, kinds):
        found.add("crops")
    return found


def kinds_of(inventory, kinds=None):
    """Every layer kind a scene's design (its scene inventory) shows: EVERY_SCENE and each row's (row_layers), by the
    row-kind rules `kinds` (the house's, data/checks/row-kinds.json, by default)."""
    kinds = row_kinds.table() if kinds is None else kinds
    rows = {row["id"]: row for row in inventory.get("rows", [])}
    return set(EVERY_SCENE).union(*(row_layers(row, rows, kinds) for row in rows.values()))


def plants_of(inventory, kinds):
    """A design's plants (CONTEXT.md "plant"), every one a model of the prop pipeline: {rows, objects (their
    counts), crops (the rows of them growing on a bed, which the crops layer also lays), beds (the objects those
    stand on)}. A planter its crops stand on is their bed, not a plant of its own."""
    rows = {row["id"]: row for row in inventory.get("rows", [])}
    growing = row_kinds.rows_that(inventory, "grows", kinds)
    crops = [row for row in growing if on_bed(row, rows, kinds)]
    beds = {holder_of(row, rows)["id"] for row in crops}
    plants = [row for row in growing if row["id"] not in beds]
    return {"rows": len(plants), "objects": sum(int(row.get("count") or 1) for row in plants), "crops": len(crops),
            "beds": sum(int(rows[bed].get("count") or 1) for bed in beds)}


def has_layer(place, kind):
    """Whether the place's design shows a layer of `kind`; False for a place with no design."""
    path = KEPT / f"{place}.json"
    if place is None or not path.is_file():
        return False
    return kind in kept_kinds(str(path), path.stat().st_mtime_ns, row_kinds.TABLE.stat().st_mtime_ns)


@functools.lru_cache(maxsize=256)
def kept_kinds(path, stamp, rules_stamp):
    """kinds_of a kept inventory, read once while neither it nor the rules change (the table asks every row's
    `applies` many times a status); `stamp` and `rules_stamp` are their files' times, the cache's key only."""
    return frozenset(kinds_of(json.loads(pathlib.Path(path).read_text())))
