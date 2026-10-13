"""A far-only look is judged on what is drawn (captain, 2026-10-13): the far crowd draws the far body, not the near
outfit, so a far-only body row gates on its joins, its likeness and the far body's own triangles (at most
FAR_TRIANGLES), and records the near outfit's triangles and shell offset without gating on them; complete's
far-only-close check keeps such a look from being shown near. A module of its own, wired in the stage table, so the
full bodies' code versions do not move with it."""
import json

from score.checks import FAIL, PASS, Verdict

# The far body prop_far.py makes: the whole mesh thinned to 1,220 triangles, as body.py's far body.
FAR_TRIANGLES = 1220


def judge_far_triangles(output, inputs, evidence):
    found = json.loads((output / "checks" / "build.json").read_text())["levels"]["far"]["triangles"]
    failing = [] if found <= FAR_TRIANGLES else [f"far body {found} triangles over {FAR_TRIANGLES}"]
    return Verdict("far triangles", FAIL if failing else PASS, failing[0] if failing else f"far body {found} triangles",
                   {"failing": len(failing), "triangles": found}, {"failing": "lower"}, tuple(failing))


def judge_near_recorded(output, inputs, evidence):
    """The near outfit's triangles and its shell offset, recorded, not gating (a far-only look is never drawn near)."""
    levels = json.loads((output / "checks" / "build.json").read_text())["levels"]
    near = sum(level["triangles"] for name, level in levels.items() if name != "far")
    shell = json.loads((output / "checks" / "shell.json").read_text())["offset_most_m"]
    return Verdict("near outfit recorded", PASS,
                   f"near outfit {near} triangles, {shell} m at most off the fitted body (not drawn: far only)",
                   {"near_triangles": near, "shell_most_m": shell})
