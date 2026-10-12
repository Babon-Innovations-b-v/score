"""Hair stays on its own route (owner, 2026-10-11: people are made like props, the hair as it works today): the
people's paint check "colour against the close-up" judges the library-painted finishes only; a hair finish (its
words naming hair: the method painted the guard's brown leather with a hair surface, so the surface does not tell)
goes to the hair route, and the verdict names those it left out. A module of its own, so only the paint row's key
moves with it."""
import json
import re

from score.checks import FAIL, PASS, Verdict

HAIR = re.compile(r"\b(hair|beard|eyebrows?|brows?)\b")  # "brown" is not a brow


def is_hair(finish):
    """Whether a finish is hair, by its words."""
    return bool(HAIR.search(finish.get("finish", "").lower()))


def judge_colour(output, inputs, evidence):
    """The surface stage's "colour against the close-up" on every finish but hair: one no library surface fits by
    colour fails by name; the hair finishes are listed as gone to the hair route."""
    found = json.loads((output / "painted.json").read_text())["takes"]
    hair = [f"{take}: {finish['finish']}" for take, report in found.items() for finish in report.get("finishes", [])
            if is_hair(finish)]
    failing = [f"{take}: {finish['finish']} measured L*a*b* {finish['measured_lab']}, {finish['surface']} dE "
               f"{finish['delta_e']} (proposed: {finish['new_surface']['name']})"
               for take, report in found.items() for finish in report.get("finishes", [])
               if finish.get("by") == "off its colour" and not is_hair(finish)]
    painted = sum(len(report.get("finishes", [])) for report in found.values()) - len(hair)
    reason = (f"{len(failing)} of {painted} library finishes no surface fits by colour" if failing
              else f"all {painted} library finishes fit") + f"; {len(hair)} hair finishes to the hair route"
    return Verdict("colour against the close-up", FAIL if failing else PASS, reason,
                   {"failing": len(failing), "hair": len(hair)}, {"failing": "lower"}, tuple(failing + hair)[:60])
