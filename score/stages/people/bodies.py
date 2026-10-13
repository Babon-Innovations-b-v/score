"""The people's body rows (#5, the owner's plan of 2026-10-11: people are made like every prop): one world row a look,
`people-body-<look>`, paid, each a node of its own so the looks run side by side. A look is a take of
data/people/surfaces.json with its `spec` and `outfit`: the prop route's Pixal3D take, SOMA-X's body fitted under it
as its moving base (only the rig, so Kimodo's clips play), its parts, its garments settled through every clip, and
its checks (tools/characters/maker/prop_person.py's stages build, settle and checks-cloud, the checks side by side on
a rented processor machine; its parts first when the take has none). The maker works in its candidate folder
(~/.farm-factory-motion/candidates/prop-people/<name>/<outfit>/); the row copies the made body and every record the
gates read into its output.

Gates (unknown blocks): joins (wrist, ankle, stance; people/joins.py), clips (the body judged clip by clip, clips.py:
tucks, rigid, cloth through cloth and body through cloth per clip; every clip judged, the failing ones named with
their numbers, a cast held to the passing ones by people-clips), outline (outline.py: the built A-pose against the
close-up's cut-out), likeness (the props' likeness gate, score/stages/props/likeness.py: the body's best outline of
eight ways round against its close-up, at least its OUTLINE_LEAST), triangles (within the shipped player's budget)
and shell (SHELL_SHARE of the soft parts' points within OFFSET_MOST of SOMA-X's body fitted to the look's
outside, prop_shell.py; the worst point recorded).
"""
import json
import pathlib
import shutil
import sys

import numpy as np

from score import contracts, graph
from score.checks import FAIL, PASS, Check, Verdict

REPO = pathlib.Path(__file__).resolve().parents[3]
MAKER = REPO / "tools/characters/maker"
DATA = REPO / "data/people/surfaces.json"
CUT = REPO / "data/people/bodies.json"
MOTION_HOME = pathlib.Path.home() / ".farm-factory-motion"
PIXAL = "{home}/work/pixal"
# A look's estimate: its parts when missing (about EUR 1), the build and the settle each on an L4 for about an hour
# with its setup (EUR 0.79 an hour), measured on the player 2026-10-10.
EUROS = 3.0
# A far-crowd look: its build alone on an L4 with its setup, about 20 minutes.
FAR_EUROS = 0.5
SHIPPED_TRIANGLES = 29849
# The shell's reach: a part other than a rigid one more than this off SOMA-X's fitted body is not carried as a thin
# shell. First set at 5 cm, about a coat's and a padded suit's thickness over the body, before any fit was measured;
# the player's fit is the first measure (#5).
OFFSET_MOST = 0.05
# The share of the soft points the reach holds for (captain, 2026-10-13): the rest, under 1% on every look, are
# loose cloth edges (cuffs, hems, caps) inside a garment's part.
SHELL_SHARE = 0.99
RIGID_ROLES = ("hard", "hair")
# Parts by name that ride one joint whatever their role (prop_build.py's RIGID_NAMES less the hair, a role here).
RIGID_NAMES = ("skin_hands",)


def looks():
    """{look: take entry} of every take in the people's data with a spec: the look is <name>-<outfit>; `far_only`
    unless data/people/bodies.json makes it in full (the take's own flag is not read: the people's data is the
    surface line's input, so a cut there would paint every look again)."""
    takes = json.loads(DATA.read_text())["takes"]
    full = set(json.loads(CUT.read_text())["full"])
    found = {}
    for take, entry in takes.items():
        if entry.get("spec"):
            look = f"{json.loads((REPO / entry['spec']).read_text())['name']}-{entry['outfit']}"
            found[look] = {**{key: value for key, value in entry.items() if key != "far_only"}, "take": take,
                           **({} if look in full else {"far_only": True})}
    return found


def files(look, entry):
    """The world files a look's body reads: its spec, the maker's and people tools' code (run
    by path, so not in the code version otherwise), its take's model and close-up, and the clips. Its entry in the
    people's data is its row's parameters, so another look's edit there leaves its key alone."""
    take = entry["take"]
    return {"spec": "{repo}/" + entry["spec"],
            "maker": "{repo}/tools/characters/maker", "people tools": "{repo}/tools/characters/people",
            "model": f"{PIXAL}/{take}.glb", "finished": f"{PIXAL}/{take}-final.glb",
            "close-up": f"{PIXAL}/{take}.svviews", "clips": str(MOTION_HOME / "work/motions")}


def made(look, entry):
    """The make of one look's row."""
    def make(inputs, out, seed, params):
        sys.path.insert(0, str(MAKER))
        import prop_person
        import spec as specs
        spec = specs.read(pathlib.Path(inputs["spec"]))
        outfit, who = entry["outfit"], f"people-body-{look}"
        folder = prop_person.folder_of(spec, outfit)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "take.txt").write_text(entry["take"])
        if not (folder / "parts" / entry["take"] / "parts.npz").exists():
            prop_person.parts(spec, outfit, who, None, False)
        stages = ("build",) if entry.get("far_only") else ("build", "settle")
        with prop_person.machine_held(spec, outfit, who) as held:  # one machine, set up once: shell, build, settle
            for stage in stages:
                prop_person.record_stage(folder, stage, *timed(prop_person.STAGE_WORK[stage], spec, outfit, who,
                                                               held))
        if entry.get("far_only"):
            kept_far(folder, spec["name"], entry, out)
            return
        prop_person.record_stage(folder, "checks-cloud", *timed(prop_person.checks_cloud, spec, outfit, who, None))
        kept(folder, spec["name"], entry, out)
    return make


def timed(stage, spec, outfit, who, held):
    import time
    began = time.time()
    return began, stage(spec, outfit, who, held, False)


def kept(folder, name, entry, out):
    """The made body, its UsdSkel asset and every record the gates read, copied out of the candidate folder."""
    shutil.copy2(folder / "settle" / f"{name}.glb", out / "body.glb")
    shutil.copytree(folder / "settle" / "usd", out / "usd")
    checks = out / "checks"
    checks.mkdir()
    for record in ("pokes.json", "outline.json", "bodycloth.json", "bodycloth_plain.json", "checks.txt",
                   "cloth_reference.txt"):
        shutil.copy2(folder / "checks" / record, checks / record)
    if (folder / "checks" / "pokes_shipped.json").exists():  # none where no shipped body wears the outfit
        shutil.copy2(folder / "checks" / "pokes_shipped.json", checks / "pokes_shipped.json")
    shutil.copy2(folder / "out" / "checks" / f"{name}.json", checks / "joins.json")
    shutil.copy2(folder / "out" / f"{name}.json", checks / "build.json")
    shutil.copy2(folder / "settle" / f"{name}.bake.json", checks / "bake.json")
    shutil.copy2(folder / "fit" / "rig.json", checks / "rig.json")
    shutil.copy2(folder / "fit" / "shell.json", checks / "shell.json")
    shutil.copy2(folder / "parts" / entry["take"] / "parts.json", checks / "parts.json")
    shutil.copy2(folder / "fit" / "rig.npz", out / "rig.npz")  # the stand (turn, scale, shift) the dress row reads
    likened(entry, out)
    (out / "look.json").write_text(json.dumps({"name": name, **entry}, indent=1))


def kept_far(folder, name, entry, out):
    """A far-crowd look's built body (no settle: the crowd draws its far body), its UsdSkel asset and the records its
    gates read."""
    shutil.copy2(folder / "out" / f"{name}.glb", out / "body.glb")
    shutil.copytree(folder / "out" / "usd", out / "usd")
    checks = out / "checks"
    checks.mkdir()
    shutil.copy2(folder / "out" / "checks" / f"{name}.json", checks / "joins.json")
    shutil.copy2(folder / "out" / f"{name}.json", checks / "build.json")
    shutil.copy2(folder / "fit" / "rig.json", checks / "rig.json")
    shutil.copy2(folder / "fit" / "shell.json", checks / "shell.json")
    shutil.copy2(folder / "parts" / entry["take"] / "parts.json", checks / "parts.json")
    shutil.copy2(folder / "fit" / "rig.npz", out / "rig.npz")
    likened(entry, out)
    (out / "look.json").write_text(json.dumps({"name": name, **entry}, indent=1))


def likened(entry, out):
    """The props' likeness gate's record of the body against its close-up."""
    import score.stages.props.likeness as likeness
    closeup = pathlib.Path(PIXAL.format(home=str(prop_home()))) / f"{entry['take']}.svviews" / "input.png"
    (out / "checks" / "likeness.json").write_text(json.dumps(likeness.best_way(out / "body.glb", closeup), indent=1))


def prop_home():
    from score.store import PROPS_HOME
    return PROPS_HOME


def body_faults(folder):
    far = (folder / "look.json").exists() and json.loads((folder / "look.json").read_text()).get("far_only")
    wanted = ("body.glb", "look.json", "checks/joins.json", "checks/likeness.json") + (() if far else (
        "checks/pokes.json", "checks/bodycloth.json", "checks/outline.json"))
    missing = [name for name in wanted if not (folder / name).exists()]
    return [f"missing {', '.join(missing)}"] if missing else []


# --- gates ---------------------------------------------------------------------------------------------------------

def record(output, name):
    return json.loads((output / "checks" / name).read_text())


def verdict(name, failing, passed_reason, measures=None):
    return Verdict(name, FAIL if failing else PASS, "; ".join(failing[:6]) if failing else passed_reason,
                   {"failing": len(failing), **(measures or {})}, {"failing": "lower"}, tuple(failing[:40]))


def judge_joins(output, inputs, evidence):
    """Wrist and ankle overlaps and the standing stance, as joins.py judged them over every clip."""
    found = record(output, "joins.json")["verdict"]
    failing = [f"{kind}: {'not measured' if found.get(kind) is None else 'fails'}"
               for kind in ("wrist", "ankle", "stance") if found.get(kind) is None or not found[kind]["pass"]]
    return verdict("joins", failing, "wrist, ankle and stance pass")


def judge_outline(output, inputs, evidence):
    found = record(output, "outline.json")
    failing = [] if found["pass"] else [f"A-pose outline drop {found['iou_drop']} (finished take "
                                        f"{found['iou_finished']}, built {found['iou_built']})"]
    return verdict("outline", failing, f"built A-pose IoU {found['iou_built']}; the finished take's own drop against "
                   f"the raw model {found['finish_drop']}", {"iou_built": found["iou_built"],
                                                            "finish_drop": found["finish_drop"]})


def judge_likeness(output, inputs, evidence):
    import score.stages.props.likeness as likeness
    found = record(output, "likeness.json")
    failing = [] if found["outline"] >= likeness.OUTLINE_LEAST else \
        [f"best outline {found['outline']} under {likeness.OUTLINE_LEAST}"]
    return verdict("likeness", failing, f"best outline {found['outline']}", {"outline": found["outline"]})


def judge_triangles(output, inputs, evidence):
    found = record(output, "build.json")
    triangles = sum(level["triangles"] for name, level in found["levels"].items() if name != "far")
    failing = [] if triangles <= SHIPPED_TRIANGLES else [f"{triangles} triangles over {SHIPPED_TRIANGLES}"]
    return verdict("triangles", failing, f"{triangles} triangles", {"triangles": triangles})


def guarded(name, judge):
    """A judge whose missing record answers unknown, never passes."""
    import functools
    from score.checks import UNKNOWN

    @functools.wraps(judge)
    def judged(output, inputs, evidence):
        try:
            return judge(output, inputs, evidence)
        except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as missing:
            return Verdict(name, UNKNOWN, f"cannot tell: {type(missing).__name__}: {missing}")
    return Check(name, judged)


def judge_shell(output, inputs, evidence):
    """The look a thin shell over SOMA-X's fitted body (owner, 2026-10-12): SHELL_SHARE of the soft parts' points
    (every part but the rigid ones: hard parts, hair and the bare hands, which ride one joint) within OFFSET_MOST of
    the body. A proxy (captain, 2026-10-13, the owner may reverse it): the points past it are loose cloth edges, cuffs,
    hems and caps, which no part label names; the clips gate judges what the cloth does in every clip. The worst
    point's part and offset are recorded."""
    found = record(output, "shell.json")
    parts = {str(part["part"]): part for part in record(output, "parts.json")["parts"]}
    soft = {key: entry for key, entry in found["parts"].items()
            if parts.get(key, {}).get("role") not in RIGID_ROLES and parts.get(key, {}).get("name") not in RIGID_NAMES}
    counts = np.zeros(max((len(entry["offsets_mm"]) for entry in soft.values()), default=1))
    for entry in soft.values():
        counts[:len(entry["offsets_mm"])] += entry["offsets_mm"]
    reach_m = float(np.searchsorted(np.cumsum(counts), SHELL_SHARE * counts.sum())) / 1000
    worst = max(soft, key=lambda key: soft[key]["most_m"], default=None)
    worst_m = soft[worst]["most_m"] if worst else 0.0
    failing = [] if reach_m <= OFFSET_MOST else [f"{SHELL_SHARE:.0%} of the soft points within {reach_m} m, over "
                                                f"{OFFSET_MOST} m"]
    where = (f"part {worst} ({parts.get(worst, {}).get('name')}, by {soft[worst].get('most_near', 'no joint recorded')})"
             if worst else "no soft part")
    return verdict("shell", failing, f"{SHELL_SHARE:.0%} of the soft points within {reach_m} m of the body; worst "
                   f"{worst_m} m, {where}", {"offset_share_m": reach_m, "offset_most_m": worst_m,
                                            "scale": found["scale"]})


def judge_clips(output, inputs, evidence):
    """The body judged clip by clip (captain, 2026-10-13; clips.py): tucks, rigid, cloth through cloth and body
    through cloth per clip. It passes once every clip is judged; each failing clip is named with its numbers, and a
    cast may use only the passing ones (people-clips holds the casts to it)."""
    from score.stages.people import clips
    passing, failing = clips.usable(output)
    findings = [f"{clip}: {'; '.join(faults)}" for clip, faults in sorted(failing.items())]
    return Verdict("clips", PASS, f"{len(passing)} of {len(passing) + len(failing)} clips usable"
                   + (f"; failing {', '.join(sorted(failing))}" if failing else ""),
                   {"usable": len(passing), "failing": len(failing)}, {"usable": "higher"}, tuple(findings))


def checks():
    return (guarded("joins", judge_joins), guarded("clips", judge_clips), guarded("outline", judge_outline),
            guarded("likeness", judge_likeness), guarded("triangles", judge_triangles),
            guarded("shell", judge_shell))


BODY = "people-body"


def far_checks():
    """A far-crowd look's gates: its joins, likeness, triangles and shell (no settle, so no cloth gates)."""
    return tuple(check for check in checks() if check.name in ("joins", "likeness", "triangles", "shell"))


def rows():
    """One paid world row a look; a far-crowd look (`far_only`) is built only and gated on what a far body shows."""
    return tuple(graph.Stage(f"{BODY}-{look}", "world", made(look, entry), contracts.Contract(BODY, 1, body_faults),
                             far_checks() if entry.get("far_only") else checks(), files=files(look, entry),
                             params={key: value for key, value in entry.items() if key != "object"}, paid=True,
                             euros=FAR_EUROS if entry.get("far_only") else EUROS)
                 for look, entry in looks().items())
