"""The one row-kind classification (CONTEXT.md "row kind"): what a scene inventory row's objects do in their scene,
worked out free from the reading's own words by the rules of data/checks/row-kinds.json (a kind whose nouns hold the
row's reading noun, or the longest end of its name that ends in that noun: a "yellow overhead crane" read as a crane is
an overhead crane, a "robotic arm" read as an arm a robot; its name's last word only for a row read with no noun), never from a model call or a record
written per scene. The effects, motion and physics stages read their work from it, and the layers a scene needs follow
from it (design_layers.py, the stage table's and the assembly's one answer): a scene needs effects when a row emits,
motion when a row moves, physics when a row is loose, crops when a row grows on a bed, people when a row acts. A row
that roams (an animal) gets its own body and clips rows (score/stages/animals).

    kind_of(row, table)          the row's kind, or None
    does(kind, table)            what a kind's objects do: {"emits", "moves", "loose", "glows", "shows", "grows",
                                 "acts", "roams"}
    rows_that(inventory, what, table)   the inventory's rows whose kind does `what`
    uncovered(inventory, table)  the rows a moving word or an unmade `does` leaves with no stage to make them
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
    """The first kind whose nouns hold one of the row's said nouns (said_nouns: the longest first); else the kind it
    is held by (held_kind); None when no kind does, and for a row the reading made an opening (its part: a hole in a
    wall or floor, never the door filling it, score/review/reading.py), which has no object to move, emit or act
    (workshop's "doorway" read as a door)."""
    if row.get("part") == "opening":
        return None
    for wanted in said_nouns(row):
        found = next((kind for kind, rule in kinds.items() if wanted in rule["nouns"]), None)
        if found:
            return found
    return held_kind(row, kinds)


def said_nouns(row):
    """The nouns a row is said to be, the longest first: each end of its name (its id's when it has no name) that
    ends in its reading noun, down to the noun itself ("yellow overhead crane", "overhead crane", "crane"); a name
    that does not end in its noun, the whole name, then the noun (a "coffee maker" read as a machine); a row read
    with no noun, its name's last word. Never a word after the noun alone: a "floor plate" is no plate."""
    noun = words(row.get("noun"))
    said = words(row.get("name") or row.get("id")).split()
    if not noun:
        return said[-1:]
    if " ".join(said).endswith(noun) and len(said) > len(noun.split()):
        ends = [" ".join(said[start:]) for start in range(len(said) - len(noun.split()))]
        return [end for end in ends if end.endswith(" " + noun)] + [noun]
    return [" ".join(said), noun] if said and " ".join(said) != noun else [noun]


def held_kind(row, kinds):
    """The first kind whose `held_by` words end the row's name (its id's when it has no name) right after one of its
    nouns: a "floodlight tower" read as a tower is a lamp; None when no kind's does."""
    said = words(row.get("name") or row.get("id")).split()
    return next((kind for kind, rule in kinds.items() if len(said) > 1 and said[-1] in rule.get("held_by", ())
                 and said[-2] in rule["nouns"]), None)


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


def coverage(path=TABLE):
    """The table's words for what no stage makes: {"moving_words", "read_by"} (uncovered)."""
    found = json.loads(pathlib.Path(path).read_text())
    return {"moving_words": found["moving_words"], "read_by": found["read_by"]}


def uncovered(inventory, kinds, rules=None):
    """The rows no stage makes what they are: [why] for each row whose reading noun's head word is a moving word
    (row-kinds.json `moving_words`: a rocket, a flag, a police car) whose kind neither moves, is loose nor `stands`
    with a written reason, and for each row whose kind does a thing no stage reads (`read_by` null: a screen's
    picture). `rules` are the table's coverage words (coverage(), the house's by default)."""
    rules = coverage() if rules is None else rules
    moving, read_by = set(rules["moving_words"]), rules["read_by"]
    faults = []
    for row in inventory.get("rows", []):
        kind = kind_of(row, kinds)
        done = does(kind, kinds)
        heard = moving & set(said_nouns(row)[-1].split()[-1:])  # its head word: a "rocket section" is a section
        if heard and not done & {"moves", "loose"} and not (kind and kinds[kind].get("stands")):
            faults.append(f"{row['id']}: \"{row.get('name') or row['id']}\" names a moving thing "
                          f"({', '.join(sorted(heard))}), and its kind ({kind or 'none'}) gives it no move and no "
                          "written reason to stand (data/checks/row-kinds.json)")
        faults += [f"{row['id']}: its kind {kind} {what}, and no stage makes that (row-kinds.json `read_by`)"
                   for what in sorted(done) if read_by.get(what, "") is None]
    return faults


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
