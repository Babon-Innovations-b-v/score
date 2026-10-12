"""The people's body rows (#5, the owner's plan of 2026-10-11: people are made like every prop): one world row a look,
`people-body-<look>`, paid, each a node of its own so the looks run side by side. A look is a take of
data/surfaces/people.json with its `spec` and `outfit`: the prop route's Pixal3D take, SOMA-X's skeleton placed
inside it (only the rig, so Kimodo's clips play), its parts, its garments settled through every clip, and its checks
(tools/characters/maker/prop_person.py's stages build, settle and checks-cloud, the checks side by side on a rented
processor machine; its parts first when the take has none). The maker works in its candidate folder (~/.farm-factory-motion/candidates/prop-people/<name>/<outfit>/); the row
copies the made body and every record the gates read into its output.

Gates (unknown blocks): joins (wrist, ankle, stance; people/joins.py), tucks (no tuck point over pokes.POKE_MM
outside the person's surface in any frame), cloth through cloth (no clip's garments cross more than the shipped
body's), rigid (hard parts unstretched), body through cloth (no clip frame puts any skin or hard part deeper than
bodycloth.MARGIN_MM through the cloth more often than the bind pose does: the bind's crossings are the parts' own
joins, held by tucks and joins), outline (outline.py: the built A-pose against the close-up's cut-out) and likeness
(the props' likeness gate, score/stages/props/likeness.py: the body's best outline of eight ways round against its
close-up, at least its OUTLINE_LEAST), triangles (within the shipped player's budget).
"""
import json
import pathlib
import shutil
import sys

from score import contracts, graph
from score.checks import FAIL, PASS, Check, Verdict

REPO = pathlib.Path(__file__).resolve().parents[3]
MAKER = REPO / "tools/characters/maker"
DATA = REPO / "data/surfaces/people.json"
MOTION_HOME = pathlib.Path.home() / ".farm-factory-motion"
PIXAL = "{home}/work/pixal"
# A look's estimate: its parts when missing (about EUR 1), the build and the settle each on an L4 for about an hour
# with its setup (EUR 0.79 an hour), measured on the player 2026-10-10.
EUROS = 3.0
# A far-crowd look: its build alone on an L4 with its setup, about 20 minutes.
FAR_EUROS = 0.5
SHIPPED_TRIANGLES = 29849


def looks():
    """{look: take entry} of every take in the people's data with a spec: the look is <name>-<outfit>."""
    takes = json.loads(DATA.read_text())["takes"]
    return {f"{json.loads((REPO / entry['spec']).read_text())['name']}-{entry['outfit']}": dict(entry, take=take)
            for take, entry in takes.items() if entry.get("spec")}


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
        if entry.get("far_only"):
            prop_person.record_stage(folder, "build", *timed(prop_person.build, spec, outfit, who, None))
            kept_far(folder, spec["name"], entry, out)
            return
        with prop_person.machine_held(spec, outfit, who) as held:  # one machine, set up once, builds and settles
            for stage in ("build", "settle"):
                prop_person.record_stage(folder, stage, *timed(prop_person.STAGE_WORK[stage], spec, outfit, who,
                                                               held))
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
    for record in ("pokes.json", "pokes_shipped.json", "outline.json", "bodycloth.json", "bodycloth_plain.json",
                   "checks.txt"):
        shutil.copy2(folder / "checks" / record, checks / record)
    shutil.copy2(folder / "out" / "checks" / f"{name}.json", checks / "joins.json")
    shutil.copy2(folder / "out" / f"{name}.json", checks / "build.json")
    shutil.copy2(folder / "settle" / f"{name}.bake.json", checks / "bake.json")
    shutil.copy2(folder / "fit" / "rig.json", checks / "rig.json")
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


def pokes_gate(name, key, what):
    def judge(output, inputs, evidence):
        found = record(output, "pokes.json")
        clips = found["clips"]
        measures = {"worst_tuck_mm": max(clip["worst_tuck_out_mm"] for clip in clips.values()),
                    "rigid_stretch": max(clip["rigid_stretch"] for clip in clips.values())}
        failing = [] if found["verdict"][key] else [what(found)]
        return verdict(name, failing, f"{name} pass over {len(clips)} clips", measures)
    return Check(name, judge)


def tucks_fault(found):
    over = {clip: round(entry["worst_tuck_out_mm"], 1) for clip, entry in found["clips"].items()
            if entry["frames_tuck_over"]}
    return f"tucks showing over 5 mm in {over}"


def judge_body_through_cloth(output, inputs, evidence):
    """No clip frame puts a skin or hard part deeper than the margin through the cloth more often than the bind does
    (per part; the bind's deep crossings are the parts' joins, which tucks and joins hold)."""
    found = record(output, "bodycloth.json")
    bind = found["bind"]["deep_by_part"]
    failing = [f"{clip}: {part} {deep} edges over {found['margin_mm']} mm deep (bind {bind.get(part, 0)})"
               for clip, entry in found["clips"].items() for part, deep in entry["deep_by_part"].items()
               if deep > bind.get(part, 0)]
    deepest = max(entry["deepest_mm"] for entry in found["clips"].values())
    return verdict("body through cloth", failing, f"no clip deeper than its bind over {found['margin_mm']} mm",
                   {"deepest_mm": deepest, "margin_mm": found["margin_mm"]})


def judge_outline(output, inputs, evidence):
    found = record(output, "outline.json")
    failing = [] if found["pass"] else [f"A-pose outline drop {found['iou_drop']} (raw {found['iou_raw']}, built "
                                        f"{found['iou_built']})"]
    return verdict("outline", failing, f"built A-pose IoU {found['iou_built']}", {"iou_built": found["iou_built"]})


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


def checks():
    tucks = pokes_gate("tucks", "tucks", tucks_fault)
    cloth = pokes_gate("cloth through cloth", "cloth_through_cloth",
                       lambda found: f"clips crossing more than the shipped body: {found.get('cloth_worse_than_shipped')}")
    rigid = pokes_gate("rigid", "rigid", lambda found: "a hard part stretches over 1.2x")
    return (guarded("joins", judge_joins), guarded("tucks", tucks.judge), guarded("cloth through cloth", cloth.judge),
            guarded("rigid", rigid.judge), guarded("body through cloth", judge_body_through_cloth),
            guarded("outline", judge_outline), guarded("likeness", judge_likeness),
            guarded("triangles", judge_triangles))


BODY = "people-body"


def far_checks():
    """A far-crowd look's gates: its joins, its likeness and its triangles (no settle, so no cloth gates)."""
    return tuple(check for check in checks() if check.name in ("joins", "likeness", "triangles"))


def rows():
    """One paid world row a look; a far-crowd look (`far_only`) is built only and gated on what a far body shows."""
    return tuple(graph.Stage(f"{BODY}-{look}", "world", made(look, entry), contracts.Contract(BODY, 1, body_faults),
                             far_checks() if entry.get("far_only") else checks(), files=files(look, entry),
                             params={key: value for key, value in entry.items() if key != "object"}, paid=True,
                             euros=FAR_EUROS if entry.get("far_only") else EUROS)
                 for look, entry in looks().items())
