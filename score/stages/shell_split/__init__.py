"""shell-split: an outside shell's plan split into the shapes of its inside places (CONTEXT.md "shapes first",
"outside shell", "inside place"), one free place node per shell, local and deterministic. Generic: any shell (a ship's
hull, a base's outer wall) in any environment.

A place is an outside shell when its plan (`data/plans/<place>.json`) has a `split`:

    "split": {
      "outline": [[along, left, right, clear], ...],   # the inside's floor, front to back: metres along the long axis,
                                                       # the inner wall's distance from the middle line on each side,
                                                       # the clear height over the floor
      "least": {"clear": 2.2, "wide": 1.5},            # a person's clear height, a room's least width
      "door": {"wide": 0.9, "tall": 2.0},
      "partition": 0.1,                                # a wall between a side room and the spine
      "spine": {"place": "walkway", "wide": 1.5, "hall": 1.5},   # the corridor the side rooms open onto
      "rooms": [{"place", "name", "side": "whole" | "left" | "right", "long": [least, most]}, ...]   # front to back
    }

The room list comes from the shell's concept or plan; the outline from its plan, drawn to its rough model. The make
(`_split.py`, its rules in its docstring) writes `split.json` (the span, what is left out, every shape with its span,
lanes, widths, clear height and doors) and `places/<place>.json`, each inside place's own definition (its shape and
doors, and the shell it sits in), into the store; never into the hand data. Gates (`_gates.py`): `tiled`, `reached`,
`bounded`.

    shell_split.applies(place)    # the place is an outside shell (its plan has a split)
    shell_split.shell_of(place)   # [the shell whose split names the place], or []: what an inside place reads beside
"""
import functools
import json
import pathlib

from score import contracts
from score.stages.shell_split import _gates, _split

REPO = pathlib.Path(__file__).resolve().parents[3]
PLANS = REPO / "data/plans"
CHECKS = _gates.CHECKS


def files(place):
    """The shell's plan: its split's outline, bounds and room list."""
    return {"plan": "{data}/plans/{place}.json"}


def read_plan(path):
    return json.loads(pathlib.Path(path).read_text())


def applies(place):
    """Whether the place is an outside shell: its plan has a split."""
    path = PLANS / f"{place}.json"
    return path.exists() and "split" in read_plan(path)


@functools.cache
def shells_in(folder):
    """{inside place: its shell} over every plan in `folder` with a split (its rooms and its spine)."""
    found = {}
    for path in sorted(pathlib.Path(folder).glob("*.json")):
        split = read_plan(path).get("split")
        if not split:
            continue
        spine = [split["spine"]["place"]] if "spine" in split else []
        for inside in [room["place"] for room in split["rooms"]] + spine:
            if inside in found:
                raise ValueError(f"{inside} is split from two shells, {found[inside]} and {path.stem}")
            found[inside] = path.stem
    return found


def shell_chain(place, shells):
    """The shells holding a place, innermost first; ValueError when a place holds itself through them."""
    chain, start = [], place
    while place in shells:
        place = shells[place]
        if place == start or place in chain:
            raise ValueError(f"{place} holds itself through its shells: {[start, *chain, place]}")
        chain.append(place)
    return chain


def shell_of(place):
    """[the outside shell whose split names the place] (an inside place reads that shell's split beside it), or []."""
    shells = shells_in(str(PLANS))
    return shell_chain(place, shells)[:1]


def make(inputs, out, seed, params):
    """split.json and each inside place's definition (module docstring)."""
    out = pathlib.Path(out)
    shell = pathlib.Path(inputs["plan"]).stem
    layout = _split.split(shell, read_plan(inputs["plan"])["split"])
    (out / "split.json").write_text(json.dumps(layout, indent=1))
    (out / "places").mkdir()
    for item in layout["places"]:
        (out / "places" / f"{item['place']}.json").write_text(json.dumps({"shell": shell, **item}, indent=1))


def split_faults(folder):
    """Why an output is not a shell split: no split.json, or an inside place without its definition."""
    folder = pathlib.Path(folder)
    if not (folder / "split.json").exists():
        return ["no split.json"]
    layout = json.loads((folder / "split.json").read_text())
    missing = [item["place"] for item in layout.get("places", [])
               if not (folder / "places" / f"{item['place']}.json").exists()]
    return [f"{place}: no places/{place}.json" for place in missing] + \
        ([] if layout.get("places") else ["the split lays no inside place"])


CONTRACT = contracts.Contract("shell-split", 1, split_faults, {"length": "metre"})
