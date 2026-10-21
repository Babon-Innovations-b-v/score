"""shell-split: an outside shell's plan split into the shapes of its inside places (CONTEXT.md "shapes first",
"outside shell", "inside place"), one free place node per shell, local and deterministic. Generic: any shell (a ship's
hull, a base's outer wall) in any environment.

A place is an outside shell when its kept plan (`{home}/design/plans/<place>.json`) has a `split`:

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
(`_split.py`, its rules in its docstring) writes `split.json` (the outside shell, the span, what is left out, every
shape with its span, lanes, widths, clear height and doors) and `places/<place>.json`, each inside place's own
definition (its shape and doors, and `outside_shell`, the shell it sits in: never `shell`, the plan's shell kind),
into the store; never into the hand data. Gates (`_gates.py`): `tiled`, `reached`, `bounded`.

    shell_split.applies(place)    # the place is an outside shell (its plan has a split)
    shell_split.shell_of(place)   # [the shell whose split names the place], or []: what an inside place reads beside
"""
import functools
import json
import pathlib

from score import contracts
from score.stages.shell_split import _gates, _split
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
PLANS = PROPS_HOME / "design" / "plans"  # the kept plans (score/review/plans.py keep), the design's
CHECKS = _gates.CHECKS

SHELL_PLAN = _gates.SHELL_PLAN


def files(place):
    """The shell's plan: its split's outline, bounds and room list."""
    return {SHELL_PLAN: "{home}/design/plans/{place}.json"}


def read_plan(path):
    return json.loads(pathlib.Path(path).read_text())


def applies(place):
    """Whether the place is an outside shell: its kept plan has a split (as scene_record.written
    reads them: `applies` is given the place alone)."""
    path = PLANS / f"{place}.json"
    return path.exists() and "split" in read_plan(path)


def plans_read(folder):
    """((plan path, its modified time), ...) of every plan in `folder`: what the shells map is made from."""
    return tuple((str(path), path.stat().st_mtime_ns) for path in sorted(pathlib.Path(folder).glob("*.json")))


def inside_places(split):
    """The places a split names (its rooms and its spine); none for a split with no room list (its own node fails)."""
    if not isinstance(split, dict):
        return []
    named = [room.get("place") for room in split.get("rooms") or [] if isinstance(room, dict)]
    spine = split.get("spine") if isinstance(split.get("spine"), dict) else {}
    return [place for place in [*named, spine.get("place")] if place]


@functools.cache
def shells_in(read):
    """({inside place: its shell}, {inside place: every shell naming it, when more than one}) over the plans `read`
    names (plans_read): made again whenever a plan is added, removed or changed."""
    found, twice = {}, {}
    for path, _ in read:
        plan = read_plan(path)
        for inside in inside_places(plan.get("split") if isinstance(plan, dict) else None):
            if inside in found:
                twice.setdefault(inside, [found[inside]]).append(pathlib.Path(path).stem)
            found[inside] = pathlib.Path(path).stem
    return found, twice


def shell_chain(place, shells, twice):
    """The shells holding a place, innermost first; ValueError when a place holds itself through them or is split
    from more than one shell."""
    chain, start = [], place
    while place in shells:
        if place in twice:
            raise ValueError(f"{place} is split from more than one shell: {twice[place]}")
        place = shells[place]
        if place == start or place in chain:
            raise ValueError(f"{place} holds itself through its shells: {[start, *chain, place]}")
        chain.append(place)
    return chain


def shell_of(place):
    """[the outside shell whose split names the place] (an inside place reads that shell's split beside it), or []."""
    return shell_chain(place, *shells_in(plans_read(PLANS)))[:1]


def make(inputs, out, seed, params):
    """split.json and each inside place's definition (module docstring)."""
    out = pathlib.Path(out)
    shell = pathlib.Path(inputs[SHELL_PLAN]).stem
    layout = _split.split(shell, read_plan(inputs[SHELL_PLAN])["split"])
    (out / "split.json").write_text(json.dumps(layout, indent=1))
    (out / "places").mkdir()
    for item in layout["places"]:
        (out / "places" / f"{item['place']}.json").write_text(json.dumps({"outside_shell": shell, **item}, indent=1))


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
