"""The free colour check's picks (#118, group C "colour against the close-up"): a take the parts' free colour check
left off its colour is never asked by the recheck (route_recheck: nothing to draw a surface that is already off), so
recheck_picks.py had no pick for it and it stayed a gap with the close-up's own colour unread (116 of world 1's 226
failed takes on 2026-11-12). Its off finish is made again on the scene library's palette token nearest its colour in
the close-up, when that token lies within finish_parts.COLOUR_DELTA_E of it and is the colour the finish's words name
(finish_parts.hue_kept, the colour check's own meaning rule: "red valve paint" stays red, a finish whose words name no
colour keeps its listed hue within HUE_DE), its surface's recipe kept, roughness and metal its list settings'. A finish
whose nearest such token is the one it already has, or none within COLOUR_DELTA_E, is not picked, nor is its take:
the free colour check measured it and nothing in the library fits, so it stays a gap by name. Never a token off the
scene library, never the dE rule widened.

`make_picks` is set on the row finish-route-picks in the table (stages.picks_applied) over recheck_picks.make_picks,
which it runs as it is: the recheck's picks first, then these for the takes the recheck could not ask, written into
the same picks.json, so surfaces-parts (recheck_picks.make_parts) applies both alike, the pick's `by` naming which.
A take with no pick comes out as recheck_picks made it. One pick a take (owner, 2026-10-28: one remake, no loops): the
parts' colour check, the bake, the paint's gates and the recheck after the bake judge the pick as the list's own, and
a take they fail again is a gap.
"""
import contextlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import numpy as np  # noqa: E402

import finish_parts  # noqa: E402
import palette_library  # noqa: E402
from score.stages.surfaces import parts_kept, recheck_picks, route_recheck  # noqa: E402

NOT_ASKED = "the free colour check failed it, not asked"
BY = "nearest library token to its close-up colour"

# The per-take function the table answers through kept.call while the row runs (stages.PER_TAKE sets it in this
# module's namespace, the row's make being this module's): recheck_picks' drafting calls it through drafted_here.
parts_take = parts_kept.parts_take


@contextlib.contextmanager
def drafted_here(found):
    """While the block runs: recheck_picks' per-take parts calls through this module's parts_take, and the parts it
    drafts for the recheck read into `found` ({take: record}) as the recheck reads them."""
    take, make_recheck = recheck_picks.parts_take, route_recheck.make_recheck

    def recheck_read(inputs, out, seed, params):
        found.update(json.loads((pathlib.Path(inputs["surfaces-parts"]) / "parts.json").read_text())["takes"])
        return make_recheck(inputs, out, seed, params)
    recheck_picks.parts_take, route_recheck.make_recheck = parts_take, recheck_read
    try:
        yield
    finally:
        recheck_picks.parts_take, route_recheck.make_recheck = take, make_recheck


def make_picks(inputs, out, seed, params):
    """recheck_picks.make_picks, then each take it left unpicked as the free colour check's picked on the nearest
    library tokens (colour_fitting); picks.json with both."""
    records = {}
    with drafted_here(records):
        recheck_picks.make_picks(inputs, out, seed, params)
    path = out / recheck_picks.FILE
    found = json.loads(path.read_text())
    tokens = palette_library.library_tokens(palette_library.read(inputs))
    for take, why in sorted(found["not_picked"].items()):
        if why != NOT_ASKED:
            continue
        picks, refused = colour_fitting(records[take]["finishes"], tokens)
        if picks:
            found["takes"][take] = picks
            del found["not_picked"][take]
        else:
            found["not_picked"][take] = f"{NOT_ASKED}; {refused}"
    path.write_text(json.dumps({"takes": dict(sorted(found["takes"].items())), "not_picked": found["not_picked"]},
                               indent=1))


def colour_fitting(finishes, tokens):
    """({finish number: pick}, None) of a take whose every finish off its colour has a nearest token (nearest_token)
    other than its own; else ({}, why)."""
    found = {}
    for number, finish in enumerate(finishes, start=1):
        if finish.get("by") != "off its colour":
            continue
        if finish.get("measured_lab") is None:
            return {}, f"{finish['finish']}: no colour measured in the close-up"
        nearest = nearest_token(finish, tokens)
        if nearest is None:
            return {}, (f"{finish['finish']}: no library token of its listed hue lies within dE "
                        f"{finish_parts.COLOUR_DELTA_E:.0f} of its close-up colour")
        apart, token = nearest
        settings = finish.get("settings")
        if not settings:
            return {}, f"{finish['finish']}: no list settings to keep its roughness and metal"
        if token == settings["token"]:
            return {}, f"{finish['finish']}: its own token {token} is the nearest, off by its order in the close-up"
        found[str(number)] = {"finish": finish["finish"], "token": token,
                              "roughness": settings["roughness"], "metal": settings["metal"],
                              "measured_lab": finish["measured_lab"], "delta_e": round(apart, 1),
                              "was": {"surface": finish["surface"], "settings": finish.get("settings")},
                              "by": BY, "why": f"the free colour check left it off: dE {finish.get('delta_e')} "
                                               f"from {finish['surface']}"}
    return found, None


def nearest_token(finish, tokens):
    """(dE, token) of the scene library's palette token (`tokens`: {token: linear RGB}) nearest the finish's close-up
    colour among those that keep what the list meant by it (finish_parts.hue_kept, the colour check's own meaning rule:
    the colour its words name, else within HUE_DE of its listed colour in a*b*, so a dim close-up never pulls foliage
    to a ground grey or a label to rock), within COLOUR_DELTA_E; None when none is."""
    listed = (finish.get("looks") or {}).get("listed") or {}
    if "lab" in listed:
        listed_lab = listed["lab"]
    elif finish.get("colour"):
        listed_lab = finish_parts.library_lab({"colour": finish["colour"]})
    else:
        return None
    measured = np.asarray(finish["measured_lab"], dtype=float)
    fits = sorted((recheck_picks.token_apart(token, measured, tokens), token) for token in tokens
                  if finish_parts.hue_kept(finish["finish"], listed_lab,
                                           finish_parts.library_lab({"colour": tokens[token]}), listed.get("recipe")))
    return fits[0] if fits and fits[0][0] <= finish_parts.COLOUR_DELTA_E else None
