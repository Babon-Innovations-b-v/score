"""The duplicate check: no real-world object is made twice. Two places' inventories that name the same object (a
desk lamp in the hub and in the workshop) lay one made model, placed again (the owner, 2026-10-09: "no duplicates";
reuse an existing model, or the same model with another wear, before making a new one).

    python3 tools/props/scene/duplicates.py            # every inventory; exit 1 on a duplicate

Only made rows count (`generate` and `mechanic`): a code row is built by a shared builder in its room's surfaces, so
the same builder in two rooms is one design already. A row's object is its `object` when it names one, else its id
without the far scenery's `far_` prefix. A row's model is the labelled take its place's entry in
`data/parts/models.json` names for it (`<row>` or `<row>_1`); a row not made yet has none. A scene with no entry
there at all (its models were made before the takes were stored: the habitat) is not known either way, so its rows
are held only to rows that name the take they reuse.

A pair of rows naming one object fails when
  - both are made and their takes differ (the same object made twice), or
  - one is made and the other not yet (about to be made again rather than placed),
unless the row that differs says why in `own_model` (a different object of the same name: the campgrounds' small
ground power unit is not the old station's power cabinet), or points at the row it reuses in `reuse`
(`<scene>:<row id>`), which must then be made from the same take once both are made.
"""
import json
import pathlib
import sys
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
INVENTORIES = REPO / "data/inventory"
MODELS = REPO / "data/parts/models.json"
MADE_KINDS = ("generate", "mechanic")
FAR_PREFIX = "far_"
UNKNOWN = "unknown"


def object_of(row):
    """The real-world object a row names."""
    if row.get("object"):
        return row["object"]
    return row["id"][len(FAR_PREFIX):] if row["id"].startswith(FAR_PREFIX) else row["id"]


def models_key(scene):
    """The scene's key in data/parts/models.json (the prologue's rooms are kept under their short names)."""
    return scene[len("prologue_"):] if scene.startswith("prologue_") else scene


def take_of(row, scene, models):
    """The labelled take a row's made model was painted from, None while it is not made, or UNKNOWN for a scene whose
    takes are not stored."""
    if models_key(scene) not in models:
        return UNKNOWN
    entries = models[models_key(scene)]
    return entries.get(row["id"]) or entries.get(f"{row['id']}_1")


def made_rows(inventories, models):
    """Every made row: {object: [(scene, row, take)]}."""
    found = defaultdict(list)
    for scene, inventory in sorted(inventories.items()):
        for row in inventory["rows"]:
            if row["kind"] in MADE_KINDS:
                found[object_of(row)].append((scene, row, take_of(row, scene, models)))
    return found


def excused(row):
    """Whether a row says why it is its own model, or names the row it reuses."""
    return bool(row.get("own_model") or row.get("reuse"))


def reuse_problems(inventories, models):
    """A row's `reuse` must name a row that exists, and be made from that row's take once both are made."""
    found = []
    for scene, inventory in sorted(inventories.items()):
        for row in inventory["rows"]:
            if not row.get("reuse"):
                continue
            other_scene, _, other_id = row["reuse"].partition(":")
            other = next((entry for entry in inventories.get(other_scene, {}).get("rows", []) if entry["id"] == other_id),
                         None)
            if other is None:
                found.append(f"{scene}:{row['id']}: reuses {row['reuse']}, which is no inventory row")
                continue
            mine, theirs = take_of(row, scene, models), take_of(other, other_scene, models)
            if mine and theirs and UNKNOWN not in (mine, theirs) and mine != theirs:
                found.append(f"{scene}:{row['id']}: says it reuses {row['reuse']} ({theirs}) but is made from {mine}")
    return found


def pair_problem(first, second):
    """What is wrong with two made rows naming one object, or None."""
    (scene_a, row_a, take_a), (scene_b, row_b, take_b) = first, second
    if excused(row_a) or excused(row_b) or UNKNOWN in (take_a, take_b):
        return None
    if take_a and take_b and take_a != take_b:
        return (f"{object_of(row_a)}: {scene_a}:{row_a['id']} ({take_a}) and {scene_b}:{row_b['id']} ({take_b}) are "
                f"one object made twice; place one model in both, or say why in own_model")
    if bool(take_a) != bool(take_b):
        made, unmade = (first, second) if take_a else (second, first)
        return (f"{object_of(row_a)}: {unmade[0]}:{unmade[1]['id']} is not made yet and {made[0]}:{made[1]['id']} "
                f"is ({made[2]}); reuse it (reuse: \"{made[0]}:{made[1]['id']}\") or say why in own_model")
    return None


def problems(inventories, models):
    """Every duplicate and every broken `reuse`, as lines."""
    found = reuse_problems(inventories, models)
    for rows in made_rows(inventories, models).values():
        for index, first in enumerate(rows):
            for second in rows[index + 1:]:
                if first[0] != second[0]:
                    problem = pair_problem(first, second)
                    if problem:
                        found.append(problem)
    return found


def load():
    """The repository's inventories by scene, and its made models' takes."""
    inventories = {path.stem: json.loads(path.read_text()) for path in sorted(INVENTORIES.glob("*.json"))}
    return inventories, json.loads(MODELS.read_text())


def main():
    found = problems(*load())
    for line in found:
        print(line)
    print(f"{len(found)} duplicate(s)" if found else "no duplicates")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
