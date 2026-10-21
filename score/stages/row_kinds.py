"""The one row-kind classification (CONTEXT.md "row kind"): what a scene inventory row's objects do in their scene,
worked out free from the reading's own words by the rules of data/checks/row-kinds.json (a kind whose nouns hold the
row's reading noun; its name's last word only for a row read with no noun), never from a model call or a record
written per scene. The effects, motion and physics stages read their work from it, and the layers a scene needs follow
from it (design_layers.py, the stage table's and the assembly's one answer): a scene needs effects when a row emits,
motion when a row moves, physics when a row is loose, crops when a row grows on a bed, people when a row acts.

    kind_of(row, table)          the row's kind, or None
    does(kind, table)            what a kind's objects do: {"emits", "moves", "loose", "glows", "shows", "grows",
                                 "acts"}
    rows_that(inventory, what, table)   the inventory's rows whose kind does `what`
    objects_of(stage, place, row)       the prims of a row's objects on a composed stage (`<row>` or `<row>_<n>`)
    strangers(names, inventory)         the names no row's object has (the layers' `designed` gate)
"""
import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
TABLE = REPO / "data/checks/row-kinds.json"
# A layer stage's declared inputs for the design: the scene's kept inventory and these rules.
DESIGNED = {"design": "{home}/design/inventory/{place}.json", "row kinds": "{data}/checks/row-kinds.json"}
# The prims of a place no row's object stands under: the layers' own.
NOT_OBJECTS = ("Effects", "Physics", "Looks", "Sky", "Lights", "Shafts")


def table(path=TABLE):
    """The row-kind rules: {kind: {nouns, does, effects?, motion?}}, in their order."""
    return json.loads(pathlib.Path(path).read_text())["kinds"]


def words(text):
    return " ".join(re.split(r"[\s_]+", str(text or "").strip().lower()))


def kind_of(row, kinds):
    """The first kind whose nouns hold the row's reading noun whole; for a row read with no noun, its name's last
    word (its id's when it has no name); None when no kind does."""
    wanted = words(row.get("noun")) or words(row.get("name") or row.get("id")).rsplit(" ", 1)[-1]
    return next((kind for kind, rule in kinds.items() if wanted and wanted in rule["nouns"]), None)


def does(kind, kinds):
    return set(kinds[kind]["does"]) if kind else set()


def rows_that(inventory, what, kinds):
    """The inventory's rows whose kind does `what`, each with its kind under `row_kind`."""
    found = []
    for row in inventory.get("rows", []):
        kind = kind_of(row, kinds)
        if what in does(kind, kinds):
            found.append(dict(row, row_kind=kind))
    return found


def of_row(name, row):
    """Whether a prim name is one of a row's objects: the row's id, or `<row>_<n>`."""
    return re.fullmatch(rf"{re.escape(row)}(_\d+)?", name) is not None


def strangers(names, inventory):
    """The prim names (a path's last part) that are no object of any row of the inventory: the layers' gate."""
    rows = [row["id"] for row in inventory.get("rows", [])]
    return [name for name in names if not any(of_row(name.rsplit("/", 1)[-1], row) for row in rows)]




def objects_of(stage, place, row):
    """The paths of the row's objects on the composed stage, in path order: every prim under the place named for the
    row, outside the layers' own scopes (NOT_OBJECTS), and not inside another object of the same row."""
    from pxr import Usd
    root = stage.GetPrimAtPath(f"/{place}")
    if not root:
        return []
    found = []
    walk = iter(Usd.PrimRange(root))
    for prim in walk:
        if prim.GetParent() == root and prim.GetName() in NOT_OBJECTS:
            walk.PruneChildren()
            continue
        if prim != root and of_row(prim.GetName(), row):
            found.append(prim.GetPath().pathString)
            walk.PruneChildren()
    return sorted(found)
