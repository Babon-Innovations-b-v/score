"""The light stage's kit pieces (experimental, score/stages/light): the square's backdrop as concept K04's proscenium
and its floodlight towers' round lamps, built in code and baked with the library's surfaces on rented cards
(tools/props/library/route.py late-plan, tools/props/cloud/library_bake.py), judged by the model check and the
concept's stage parts. A module of its own, so a change to the place stages does not bake these again.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import numpy as np

from score import checks, contracts, graph
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/props/scene"))
import earth_outside_kit  # noqa: E402

PROPS_PYTHON = PROPS_HOME / "env/bin/python"
WHO = "score light stage"
# The tools this stage runs write no bytecode beside their sources: those folders are its declared inputs, and a
# cache written mid-run would read as an input changed while the node ran.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def verdict(check, passed, reason, measures, better=None):
    return checks.Verdict(check, checks.PASS if passed else checks.FAIL, reason, measures, better or {})


# --- the kit pieces --------------------------------------------------------------------------------------------------

KIT_KINDS = {"square_far_backdrop": "far_backdrop_2", "square_far_floodlight_tower": "far_floodlight_tower_2"}


def late_layout(work):
    """The square's kit layout as earth_outside_kit.py lays it, cut to the backdrop and the floodlight towers, each
    naming its new model, written for route.py's late-plan."""
    layout = earth_outside_kit.layout_of("square")
    layout["pieces"] = [dict(laid, model=KIT_KINDS[laid["kind"]]) for laid in layout["pieces"]
                        if laid["kind"] in KIT_KINDS]
    layout["counts"] = {kind: sum(1 for laid in layout["pieces"] if laid["kind"] == kind) for kind in KIT_KINDS}
    path = work / "late-layout.json"
    path.write_text(json.dumps(layout, indent="\t") + "\n")
    return path


def make_kit(inputs, out, seed, params):
    """Plan the square's new code-built pieces (route.py late-plan), check them before the bake (route.py precheck),
    bake them on rented cards (library_bake.py) and keep the made models, the plan and the check."""
    work = out / "work"
    work.mkdir(parents=True)
    layout = late_layout(work)
    route = REPO / "tools/props/library/route.py"
    subprocess.run([str(PROPS_PYTHON), str(route), "late-plan", str(layout), str(work)], check=True)
    checked = subprocess.run([str(PROPS_PYTHON), str(route), "precheck", str(work)], check=True, capture_output=True,
                             text=True).stdout.strip().splitlines()[-1]
    (out / "precheck.txt").write_text(checked + "\n")
    jobs = sorted(str(path) for path in work.glob("job-*.json"))
    subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/props/cloud/library_bake.py"), *jobs, "--who", WHO],
                   check=True)
    shutil.move(str(work / "made"), str(out / "made"))


def kit_faults(folder):
    wanted = [f"made/{model}.gltf" for model in KIT_KINDS.values()] + ["precheck.txt", "work/plan.json"]
    return [f"no {name}" for name in wanted if not (folder / name).exists()]


KIT_MODELS = contracts.Contract("kit-models", 1, kit_faults, {"length": "metre", "up axis": "Y"})


def judge_model_check(output, inputs, evidence):
    """Every new piece passes the model check before its bake (route.py precheck: no wall under 3 mm)."""
    line = (output / "precheck.txt").read_text().strip()
    return verdict("model_check", line.endswith(": none"), line, {"failing": 0 if line.endswith(": none") else 1})


def baked_pieces(output):
    """Every baked piece's report (make_kit.py's report-*.json): its library surfaces (`slots`), its bounds and how
    much of each named part shows (`parts_seen`)."""
    found = {}
    for path in sorted((output / "made").glob("report-*.json")):
        found.update(json.loads(path.read_text())["pieces"])
    return found


# Concept K04's stage, part by part, as the backdrop's builder names them (pieces_earth.far_backdrop).
STAGE_PARTS = ("header", "label", "legs", "trim", "back_curtain", "batten", "lamps", "lens", "wing_curtain")


def judge_stage_parts(output, inputs, evidence):
    """The backdrop shows concept K04's stage: every one of its parts built and seen (STAGE_PARTS, at least a fifth
    of each in view from round it), its opening set back (the piece deeper than 1.5 m, where the game's flat wall was
    0.6 m) and its curtain wing beside the portal (wider than the 19.5 m stage); its lamps and the towers' banks of
    round lamps glow (a glowing part of their own)."""
    pieces = baked_pieces(output)
    backdrop = pieces["far_backdrop_2"]
    low, high = (np.asarray(corner) for corner in backdrop["bounds"])
    wide, deep = float(high[0] - low[0]), float(high[2] - low[2])
    lacking = [part for part in STAGE_PARTS if backdrop["parts_seen"].get(part, 0.0) < 0.2]
    glows = {model: f"{model}_glow" in pieces for model in KIT_KINDS.values()}
    passed = not lacking and all(glows.values()) and deep > 1.5 and wide > 19.5
    return verdict("stage_parts", passed, f"backdrop {wide:.2f} x {deep:.2f} m, parts seen "
                   f"{backdrop['parts_seen']}, surfaces {backdrop['slots']}, glowing parts {glows}"
                   + (f"; lacks {lacking}" if lacking else ""),
                   {"deep_m": round(deep, 3), "wide_m": round(wide, 3), "parts": len(STAGE_PARTS) - len(lacking)},
                   {"parts": "higher"})


KIT = graph.Stage("lightkit", "world", make_kit, KIT_MODELS,
                  (checks.Check("model_check", judge_model_check), checks.Check("stage_parts", judge_stage_parts)),
                  files={"site numbers": "{data}/definitions/earth_site.json", "library": "{data}/library",
                         "builders": "{data}/../tools/props/library/inside"},
                  paid=True, euros=2.0)


