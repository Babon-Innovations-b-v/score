"""The recheck's picks applied (#118, point 3): a take the finish list matched wrongly (copper on a painted pipe,
leather on grey seats, a glowing panel on a steel housing) is made again on the library token the recheck names for
it, not left a gap with its `suggested` unread. A list asked again cannot do it: its ask is cached by request
(claude_code.py), so the same inputs give the same mis-pick; the recheck already judges against the close-up and names
a palette token, roughness and metal of the scene library for each finish it fails.

Two makes, each set on its row in the table (stages.picks_applied), so no row reading route_recheck.py, route_parts.py
or parts_kept.py (the bake, the recheck, the people's dress) moves for them:

- `finish-route-picks` (`make_picks`; Claude on this PC, EUR 0, never Gemini): the parts drafted as surfaces-parts
  makes them (parts_kept.make_parts, in a folder of its own), then the recheck's one question asked of them
  (route_recheck.make_recheck: the request the recheck row sends, so its cached answer). A take is picked only when
  the answer names a library token, roughness and metal for every finish it fails, and every such token lies within
  finish_parts.COLOUR_DELTA_E of that finish's colour in the close-up (the parts' own free colour check, `fitting`).
  A take the free colour check failed (never asked), a failing finish with no token, or one whose token lies off the
  close-up's colour is not picked, its reason kept (`not_picked`). picks.json; nothing here is a gap: its fails are
  the picks', and the recheck row after the bake judges every take again.
- `surfaces-parts` (`make_parts`): the finish list with the picks over it (each picked finish in the pick's token,
  roughness and metal, its seed and own wear kept, its colour the token's, `picked` its record), then
  parts_kept.make_parts as before, so the parts' free colour check, the bake, the paint's gates and the recheck judge
  a pick as they judge the list's own. With no pick it is the same make on the same inputs: the same output, so the
  rows reading it keep their keys (stages.REMADE_SAME).

A pick is applied once: the recheck after the bake asks again of the picked parts, and a take it fails then is a gap
as before (owner, 2026-10-28: one remake, no loops).
"""
import contextlib
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import numpy as np  # noqa: E402

import finish_parts  # noqa: E402
import palette_library  # noqa: E402
import surface_gates as gates  # noqa: E402
import score.stages.batch_gaps as batch_gaps  # noqa: E402
from score.stages.surfaces import parts_kept, route_recheck  # noqa: E402  (the table's own: one module each)

ROW = "finish-route-picks"
CALLER = ROW
FILE = "picks.json"
GATE = "picks fit the close-up"
SETTINGS = ("token", "roughness", "metal")

# The per-take function the table answers through kept.call while either row runs (stages.PER_TAKE sets it in this
# module's namespace): parts_kept.make_parts calls whatever parts_kept.parts_take holds then.
parts_take = parts_kept.parts_take


def ask(bodies):
    """The recheck's asks of Claude Code on this PC (EUR 0, cached by request); NotHere on a machine without it."""
    from score.adapters.models import claude_code
    return claude_code.asked(bodies, CALLER)


@contextlib.contextmanager
def through_this_module():
    """parts_kept's per-take calls through this module's parts_take, and the recheck's asks through this module's
    ask, while the block runs."""
    take, recheck_ask = parts_kept.parts_take, route_recheck.ask
    parts_kept.parts_take = parts_take
    route_recheck.ask = lambda bodies: ask(bodies)
    try:
        yield
    finally:
        parts_kept.parts_take, route_recheck.ask = take, recheck_ask


def make_picks(inputs, out, seed, params):
    """The parts drafted and rechecked in one ask; picks.json: each picked take's picks, each other failing take's
    reason."""
    with tempfile.TemporaryDirectory() as temporary, through_this_module():
        drafted = pathlib.Path(temporary) / "parts"
        drafted.mkdir()
        parts_kept.make_parts(inputs, drafted, seed, params)
        route_recheck.make_recheck({**inputs, "surfaces-parts": drafted}, out, seed, params)
        records = json.loads((drafted / "parts.json").read_text())["takes"]
    (out / batch_gaps.FILE).unlink(missing_ok=True)  # a fail here is a pick or the recheck's to judge, never a gap
    tokens = palette_library.library_tokens(palette_library.read(inputs))
    found, refused = {}, {}
    for take, record in json.loads((out / "recheck.json").read_text()).items():
        if record["passed"]:
            continue
        picks, why = fitting(record, records[take]["finishes"], tokens)
        if picks:
            found[take] = picks
        else:
            refused[take] = why
    (out / FILE).write_text(json.dumps({"takes": found, "not_picked": refused}, indent=1))


def fitting(record, finishes, tokens):
    """({finish number: pick}, None) of a failed take whose answer names a library token, roughness and metal for every
    finish it failed, each token within COLOUR_DELTA_E of that finish's colour in the close-up; else ({}, why)."""
    if not record["asked"]:
        return {}, "the free colour check failed it, not asked"
    answers = record.get("gemini") or {}
    if not answers:
        return {}, str(record["fault"])[:300]
    failed = [number for number in range(1, len(finishes) + 1)
              if not answers.get(str(number), {}).get("matches", False)]
    found = {}
    for number in failed:
        answer, finish = answers.get(str(number), {}), finishes[number - 1]
        if any(answer.get(name) is None for name in SETTINGS) or answer["token"] not in tokens:
            return {}, f"{finish['finish']}: no library token, roughness and metal named"
        if finish.get("measured_lab") is None:
            return {}, f"{finish['finish']}: no colour measured in the close-up"
        apart = token_apart(answer["token"], finish["measured_lab"], tokens)
        if apart > finish_parts.COLOUR_DELTA_E:
            return {}, f"{finish['finish']}: {answer['token']} lies dE {apart:.1f} from its close-up colour"
        found[str(number)] = {"finish": finish["finish"], "token": answer["token"],
                              "roughness": round(float(np.clip(answer["roughness"], 0, 1)), 3),
                              "metal": round(float(np.clip(answer["metal"], 0, 1)), 3),
                              "measured_lab": finish["measured_lab"], "delta_e": round(apart, 1),
                              "was": {"surface": finish["surface"], "settings": finish.get("settings")},
                              "why": str(answer.get("why", ""))[:300]}
    return found, None


def token_apart(token, measured_lab, tokens):
    """CIE76 distance between a palette token's colour (`tokens`: {token: linear RGB}) and a close-up's L*a*b*."""
    return float(np.linalg.norm(finish_parts.library_lab({"colour": tokens[token]}) - np.asarray(measured_lab)))


def picks_faults(folder):
    return [] if (folder / FILE).exists() else [f"no {FILE}"]


def judge_picks(output, inputs, evidence):
    """Gate "picks fit the close-up": every pick is a token of the scene library within COLOUR_DELTA_E of its
    finish's colour in the close-up; the takes picked and not picked as measures."""
    found = json.loads((output / FILE).read_text())
    tokens = palette_library.library_tokens(palette_library.read(inputs))
    failing = [f"{take}: {pick['finish']}: {pick['token']}" + (
        " is no token of the scene library" if pick["token"] not in tokens else
        f" lies dE {token_apart(pick['token'], pick['measured_lab'], tokens):.1f} from its close-up colour")
        for take, picks in found["takes"].items() for pick in picks.values()
        if pick["token"] not in tokens
        or token_apart(pick["token"], pick["measured_lab"], tokens) > finish_parts.COLOUR_DELTA_E]
    picked = sum(len(picks) for picks in found["takes"].values())
    return gates.verdict(GATE, failing, picked, "picks", {"picked_takes": len(found["takes"]),
                                                          "not_picked_takes": len(found["not_picked"])})


def make_parts(inputs, out, seed, params):
    """parts_kept.make_parts on the finish list with the picks over it; with no pick, on the list as it is."""
    picks = json.loads((pathlib.Path(inputs[ROW]) / FILE).read_text())["takes"]
    rest = {name: path for name, path in inputs.items() if name != ROW}
    with contextlib.ExitStack() as stack:
        stack.enter_context(through_this_module())
        if picks:
            temporary = pathlib.Path(stack.enter_context(tempfile.TemporaryDirectory()))
            tokens = palette_library.library_tokens(palette_library.read(rest))
            rest["finish-route-list"] = picked_list(pathlib.Path(rest["finish-route-list"]), picks, tokens,
                                                    temporary / "list")
        return parts_kept.make_parts(rest, out, seed, params)


def picked_list(listed, picks, tokens, folder):
    """The list row's output in `folder`: each file linked, each picked take's list written with its picks over it."""
    folder.mkdir()
    for path in listed.iterdir():
        if path.stem not in picks or path.suffix != ".json":
            (folder / path.name).symlink_to(path.resolve())
    for take, take_picks in picks.items():
        entry = json.loads((listed / f"{take}.json").read_text())
        entry["finishes"] = [with_pick(finish, take_picks.get(str(number + 1)), tokens)
                             for number, finish in enumerate(entry["finishes"])]
        (folder / f"{take}.json").write_text(json.dumps(entry, indent=1))
    return folder


def with_pick(finish, pick, tokens):
    """A list finish in its pick's token, roughness and metal (its seed and own wear kept; its colour the token's,
    as route_list.finishes_of gives it), `picked` the pick; as it was with no pick. A pick for other words refuses."""
    if pick is None:
        return finish
    if pick["finish"] != finish["finish"]:
        raise ValueError(f"a pick for {pick['finish']!r} lies on the list's {finish['finish']!r}")
    settings = {**(finish.get("settings") or {}), **{name: pick[name] for name in SETTINGS}}
    return {**finish, "settings": settings, "colour": [round(float(value), 5) for value in tokens[pick["token"]]],
            "picked": pick}
