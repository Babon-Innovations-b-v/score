"""Where the basket is kept and how it is read, in the dashboard's home. Plain files only: no store, no stages.

    <root>/index.json                       the basket (make.py): {made_at, commit, refusal, missing, items}
    <root>/declared.json                    a department's items, by id (`declared`): kept across makes
    <root>/answers.json                     the owner's answers to the items' questions (`answers`): agents read them
    <root>/<place>/details.json             a place's details, as older makes wrote them (none since the cockpit
                                            went, 2026-11-16)

An item: {id, title (a declared item's), places, place (its one place, else None), layers, nodes: {node: price},
why: {node: why}, again: [node], missing: [words], declared, for (the places whose line holds it), totals, version}. `version` hashes its nodes and why,
so a buy is of the item he saw.

A declared item (`python -m score.dashboard basket-item`): {title, sentence, nodes: [patterns of the paid nodes it
takes, any place], pictures: [paths], files: [paths], questions: [{ask, recommended}]}. A declaration with an
automatic item's id and no node patterns gives that item its words and questions.
"""
import json
import pathlib
import re

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
INDEX = "index.json"
DETAILS = "details.json"
DECLARED = "declared.json"
ANSWERS = "answers.json"
ENVIRONMENT = "environment"
# How the free after took each node (assemble.py names the same three; the package's test file holds them equal).
AS_NOW, MADE, PAID = "as now", "made", "needs the paid batch"


class BadName(ValueError):
    """A place, item or file name the basket cannot have."""


def checked(name):
    """The name, when it is a plain place or item name (no path, no dots in front); BadName otherwise."""
    if not NAME.match(name or "") or ".." in name:
        raise BadName(f"{name!r} is not a scene or item name")
    return name


def folder(root, place):
    """The folder of one place's details (ENVIRONMENT for the environment's own rows)."""
    return pathlib.Path(root) / checked(place or ENVIRONMENT)


def read_json(path, empty):
    return json.loads(path.read_text()) if path.is_file() else empty


def index(root):
    """The basket as make.py left it, or {} when none is made yet."""
    return read_json(pathlib.Path(root) / INDEX, {})


def items(root):
    """Every item of the basket, in its order ([] when none is made yet)."""
    return index(root).get("items", [])


def item(root, ident):
    """One item by its id, or None."""
    return next((found for found in items(root) if found["id"] == ident), None)


def details(root, place):
    """A place's details (details.py), or None."""
    return read_json(folder(root, place) / DETAILS, None)


def declared(root):
    """{item id: declaration} of the departments' items."""
    return read_json(pathlib.Path(root) / DECLARED, {})


def declared_folder(ident):
    """The folder name of a declared item's own pictures and files."""
    return f"item-{checked(ident)}"


def answers(root):
    """{item id: {question number: {question, answer, by, at}}} the owner gave."""
    return read_json(pathlib.Path(root) / ANSWERS, {})


def swapped_json(path, found):
    """Write `found` as JSON to `path`, swapped in whole."""
    partial = path.with_name(f"{path.name}.partial")
    partial.write_text(json.dumps(found, indent=1))
    partial.replace(path)


def put_declared(root, ident, fields):
    """Keep a department's item (its fields over what it declared before); every declared item."""
    found = declared(root)
    found[checked(ident)] = {**found.get(ident, {}), **fields}
    pathlib.Path(root).mkdir(parents=True, exist_ok=True)
    swapped_json(pathlib.Path(root) / DECLARED, found)
    return found


def put_answer(root, ident, number, given):
    """Keep the owner's answer to an item's question; every answer."""
    found = answers(root)
    found.setdefault(checked(ident), {})[str(int(number))] = given
    pathlib.Path(root).mkdir(parents=True, exist_ok=True)
    swapped_json(pathlib.Path(root) / ANSWERS, found)
    return found


def put_index(root, found):
    """Write the basket's index, swapped in whole."""
    pathlib.Path(root).mkdir(parents=True, exist_ok=True)
    swapped_json(pathlib.Path(root) / INDEX, found)
