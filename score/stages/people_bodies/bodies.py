"""The people's body rows (#5, the owner's plan of 2026-10-11: people are made like every prop): two world rows a look,
`people-look-parts-<look>` and `people-body-<look>`, paid, each a node of its own so the looks run side by side. A
look is a take of data/surfaces/people.json with its `spec` and `outfit`: the shared loop's model of it (#41: its
parts row waits on the loop's hand-on, people-made@people, and refuses a look the loop made none for), SOMA-X's
body fitted under it as its moving base (only the rig, so the clips of people-clips-made play), its parts, the
people route on the built body (owner, 2026-10-18, #26: SOMA-X's base under the look from SAM 3D Body's read of the
close-up, the garments bound by limb, the face by route_head.FACE, the pose correctives as morph targets; it replaced
the garment settle), and its checks (tools/characters/maker/prop_person.py's stages build, route and checks-cloud,
the checks side by side on a rented processor machine), on the parts its own priced row made,
`people-look-parts-<look>` (PARTS, #21: never a purchase hidden inside the body row; gated on `parts`, every part
named with a role and a material). When the paid checks find a tuck over the gate in every clip (pokes.json), the
look's record of it (prop_person.tucks_record) carries its inputs' hash, and while that stands the row is refused
before any machine (prop_person.predicted_tucks): the same failure is never bought twice.
The maker works in its candidate folder (~/.farm-factory-motion/candidates/prop-people/<name>/<outfit>/); the row
copies the made body and every record the gates read into its output. Both rows read the look's take from the store,
as people-made@people handed it on (its takes/<take>/: raw and finished Pixal3D model and close-up), and lay it where
the maker reads it (`laid_take`), never from the work folder alone (#26: lost on 2026-10-19).

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
from score.stages.people_bodies import full, made_clips

REPO = pathlib.Path(__file__).resolve().parents[3]
MAKER = REPO / "tools/characters/maker"
DATA = REPO / "data/surfaces/people.json"
# The people's after-step on the shared loop and its line (score/stages/people/loop.py), named, not imported: nothing of
# the people package goes into a body row's code version (the overlay).
MADE, LINE = "people-made", "people"
DESIGN = REPO / "data/people/rows.json"
# A look's estimate: the build and the settle each on an L4 for about an hour with its setup (EUR 0.79 an hour),
# measured on the player 2026-10-10; the route (identity and CPU work on the same held machine) has no measure yet
# and is held inside it; its parts are their own priced row (PARTS, #21), never bought inside it.
EUROS = 2.0
# A look's parts (prop_person.parts: SAM 2.1's regions, GeoSAM2, the judge's materials), about EUR 1 (the player,
# 2026-10-10): free where its candidate folder already holds them.
PARTS = "people-look-parts"
PARTS_EUROS = 1.0
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
# Hard parts worn as cloth, on the shell (prop_build.py's CLOTH_WORDS; owner, 2026-10-13).
CLOTH_WORDS = ("belt", "buckle")


def looks():
    """{look: take entry} of every take in the people's data with a spec: the look is <name>-<outfit>; `far_only`
    unless the design makes it in full (full.full_looks of data/people/rows.json: a person row near enough the
    concept's view; the take's own flag is not read: the people's data is the surface line's input, so a cut there
    would paint every look again)."""
    takes = json.loads(DATA.read_text())["takes"]
    made_full = full.full_looks(json.loads(DESIGN.read_text()))
    found = {}
    for take, entry in takes.items():
        if entry.get("spec"):
            look = f"{json.loads((REPO / entry['spec']).read_text())['name']}-{entry['outfit']}"
            found[look] = {**{key: value for key, value in entry.items() if key != "far_only"}, "take": take,
                           **({} if look in made_full else {"far_only": True})}
    return found


def files(look, entry):
    """The world files a look's body reads: its spec and the maker's and people tools' code (run by path, so not in
    the code version otherwise). Its take's model and close-up are no file of the work folder: they come from the
    store, as people-made@people handed them on (`laid_take`, #26); its clips and rig from people-clips-made's output.
    Its entry in the people's data is its row's parameters, so another look's edit there leaves its key alone."""
    return {"spec": "{repo}/" + entry["spec"],
            "maker": "{repo}/tools/characters/maker", "people tools": "{repo}/tools/characters/people"}


def parts_files(entry):
    """The world files a look's parts read: its spec and the maker's code."""
    return {name: path for name, path in files(None, entry).items() if name != "people tools"}


def made(look, entry):
    """The make of one look's row."""
    def make(inputs, out, seed, params):
        handed = pathlib.Path(inputs[f"{MADE}@{LINE}"])
        refused_on_gap(handed, look)
        sys.path.insert(0, str(MAKER))
        import prop_person
        import spec as specs
        spec = specs.read(pathlib.Path(inputs["spec"]))
        outfit, who = entry["outfit"], f"people-body-{look}"
        folder = prop_person.folder_of(spec, outfit)
        folder.mkdir(parents=True, exist_ok=True)
        laid_take(handed, look, prop_person.PIXAL)
        (folder / "take.txt").write_text(entry["take"])
        laid_parts(pathlib.Path(inputs[f"{PARTS}-{look}"]), folder / "parts" / entry["take"])
        shutil.copyfile(pathlib.Path(inputs[made_clips.ROW]) / "rig.npz", folder.parent / "rig.npz")
        if not entry.get("far_only"):
            refused_on_record(prop_person.predicted_tucks(spec, outfit), who)
        stages = ("build",) if entry.get("far_only") else ("build", "route")
        with prop_person.machine_held(spec, outfit, who) as held:  # one machine, set up once: shell, build, route
            for stage in stages:
                prop_person.record_stage(folder, stage, *timed(prop_person.STAGE_WORK[stage], spec, outfit, who,
                                                               held))
        if entry.get("far_only"):
            kept_far(folder, spec["name"], entry, out, take_folder(handed, look))
            return
        prop_person.record_stage(folder, "checks-cloud", *timed(prop_person.checks_cloud, spec, outfit, who, None))
        prop_person.tucks_record(spec, outfit)
        kept(folder, spec["name"], entry, out, take_folder(handed, look))
    return make


def take_folder(handed, look):
    """The look's Pixal3D files as people-made@people handed them on (takes/<take>/ in its stored output)."""
    return handed / json.loads((handed / "made.json").read_text())[look]["files"]


def laid_take(handed, look, target):
    """The look's Pixal3D files, from the store, laid where the maker reads them (`target`, its work folder; each
    file copied plain, not as the checkout's read-only mode), over whatever is there."""
    source = take_folder(handed, look)
    for path in sorted(source.rglob("*")):
        if path.is_file():
            laid = target / path.relative_to(source)
            laid.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, laid)


def refused_on_record(foretold, who):
    """Blocked, before any machine is rented, when the look's settled tucks failed in every clip on the same inputs
    (#21: prop_person.predicted_tucks): a predicted gap, never bought again. A body batch whose every look is foretold so
    spends nothing."""
    if foretold:
        raise graph.Blocked(f"{who}: a predicted gap, its settled tucks over the gate in all {foretold['clips']} clips "
                            f"({foretold['worst_tuck_out_mm']} mm at the worst) on these same inputs; change the take, "
                            "its parts or the maker first")


def laid_parts(accepted, target):
    """The look's accepted parts (its PARTS row's output) laid where the maker reads them, unless already there."""
    target.mkdir(parents=True, exist_ok=True)
    for name in ("parts.npz", "parts.json"):
        if not (target / name).exists():
            shutil.copyfile(accepted / name, target / name)  # not the checkout's read-only mode


def the_line(place):
    """The line whose hand-on a look's parts read (their `neighbours`): the people's, which no place owns."""
    return [LINE]


def refused_on_gap(handed, look):
    """Blocked, before anything is bought, when the shared loop made the look no model (its gap in made.json)."""
    entry = json.loads((handed / "made.json").read_text()).get(look, {"gap": "no row of the people line"})
    if "gap" in entry:
        raise graph.Blocked(f"{look}: the shared loop made no model: {entry['gap']}")


def parts_made(look, entry):
    """The make of one look's parts row: the parts the candidate folder holds, else bought once
    (prop_person.parts), copied into the output."""
    def make(inputs, out, seed, params):
        handed = pathlib.Path(inputs[f"{MADE}@{LINE}"])
        refused_on_gap(handed, look)
        sys.path.insert(0, str(MAKER))
        import prop_person
        import spec as specs
        spec = specs.read(pathlib.Path(inputs["spec"]))
        folder = prop_person.folder_of(spec, entry["outfit"])
        folder.mkdir(parents=True, exist_ok=True)
        laid_take(handed, look, prop_person.PIXAL)
        (folder / "take.txt").write_text(entry["take"])
        made_parts = folder / "parts" / entry["take"]
        if not (made_parts / "parts.npz").exists():
            prop_person.parts(spec, entry["outfit"], f"{PARTS}-{look}", None, False)
        for name in ("parts.npz", "parts.json"):
            shutil.copy2(made_parts / name, out / name)
    return make


def parts_faults(folder):
    return [f"no {name}" for name in ("parts.npz", "parts.json") if not (pathlib.Path(folder) / name).exists()]


def judge_parts(output, inputs, evidence):
    """Pass when the take is split into named parts, each with its role and material."""
    found = json.loads((pathlib.Path(output) / "parts.json").read_text())["parts"]
    named = [part for part in found if part.get("name") and part.get("role") and part.get("material")]
    return Verdict("parts", PASS if found and len(named) == len(found) else FAIL,
                   f"{len(named)} of {len(found)} parts named with a role and a material",
                   {"parts": len(found), "named": len(named)})


def timed(stage, spec, outfit, who, held):
    import time
    began = time.time()
    return began, stage(spec, outfit, who, held, False)


def kept(folder, name, entry, out, takes):
    """The route's body, its UsdSkel asset and every record the gates read, copied out of the candidate folder."""
    shutil.copy2(folder / "route" / f"{name}.glb", out / "body.glb")
    shutil.copytree(folder / "route" / "usd", out / "usd")
    checks = out / "checks"
    checks.mkdir()
    for record in ("pokes.json", "outline.json", "bodycloth.json", "bodycloth_plain.json", "checks.txt",
                   "cloth_reference.txt"):
        shutil.copy2(folder / "checks" / record, checks / record)
    if (folder / "checks" / "pokes_shipped.json").exists():  # none where no shipped body wears the outfit
        shutil.copy2(folder / "checks" / "pokes_shipped.json", checks / "pokes_shipped.json")
    shutil.copy2(folder / "route" / "checks" / f"{name}.json", checks / "joins.json")
    shutil.copy2(folder / "out" / f"{name}.json", checks / "build.json")
    shutil.copy2(folder / "route" / f"{name}.json", checks / "route.json")
    shutil.copy2(folder / "fit" / "rig.json", checks / "rig.json")
    shutil.copy2(folder / "fit" / "shell.json", checks / "shell.json")
    shutil.copy2(folder / "parts" / entry["take"] / "parts.json", checks / "parts.json")
    shutil.copy2(folder / "fit" / "rig.npz", out / "rig.npz")  # the stand (turn, scale, shift) the dress row reads
    likened(out, takes / f"{entry['take']}.svviews" / "input.png")
    (out / "look.json").write_text(json.dumps({"name": name, **entry}, indent=1))


def kept_far(folder, name, entry, out, takes):
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
    likened(out, takes / f"{entry['take']}.svviews" / "input.png")
    (out / "look.json").write_text(json.dumps({"name": name, **entry}, indent=1))


def likened(out, closeup):
    """The props' likeness gate's record of the body against its close-up (the stored take's)."""
    import score.stages.props.likeness as likeness
    (out / "checks" / "likeness.json").write_text(json.dumps(likeness.best_way(out / "body.glb", closeup), indent=1))


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


# A join's inner side by joins.py's names: the hand a sleeve covers, the boot a trouser leg covers.
INNER = {"wrist": "HANDS", "ankle": "BOOTS"}


def joinless(output, kind):
    """Whether the body draws no piece of a join's inner side (joins.py's hands for the wrist, boots for the ankle):
    the sleeve or trouser leg runs on as that piece (an astronaut's gloves are its suit's cloth), so there is no such
    join to open and joins.py measured none."""
    sys.path.insert(0, str(REPO / "tools/characters/people"))
    import joins
    document, _ = joins.read_glb(output / "body.glb")
    drawn = {document["materials"][primitive["material"]]["name"] for node in document["nodes"]
             if "mesh" in node and "skin" in node and node.get("name") != "far"
             for primitive in document["meshes"][node["mesh"]]["primitives"] if "material" in primitive}
    return not drawn & set(getattr(joins, INNER[kind]))


def judge_joins(output, inputs, evidence):
    """Wrist and ankle overlaps and the standing stance, as joins.py judged them over every clip. A wrist or ankle
    joins.py measured none of passes only when the body draws no piece of its inner side (`joinless`)."""
    found = record(output, "joins.json")["verdict"]
    open_ended = [kind for kind in INNER if found.get(kind) is None and joinless(output, kind)]
    failing = [f"{kind}: {'not measured' if found.get(kind) is None else 'fails'}"
               for kind in ("wrist", "ankle", "stance")
               if kind not in open_ended and (found.get(kind) is None or not found[kind]["pass"])]
    return verdict("joins", failing, "wrist, ankle and stance pass" + "".join(
        f"; no {kind} join: the body draws no {INNER[kind].lower()} apart from its cloth" for kind in open_ended),
        {"joinless": len(open_ended)})


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


def near_triangles(path):
    """The triangles of every drawn node of a body glTF but its far body (the route's under layer and closings in)."""
    import struct
    with open(path, "rb") as body:
        body.seek(12)
        length, _ = struct.unpack("<II", body.read(8))
        document = json.loads(body.read(length))
    return sum(document["accessors"][primitive["indices"]]["count"] // 3 for node in document["nodes"]
               if "mesh" in node and node.get("name") != "far"
               for primitive in document["meshes"][node["mesh"]]["primitives"])


def judge_triangles(output, inputs, evidence):
    """The near outfit's triangles as drawn: the route's body where it was made (checks/route.json), else the build's
    record."""
    if (output / "checks" / "route.json").exists():
        triangles = near_triangles(output / "body.glb")
    else:
        triangles = sum(level["triangles"] for name, level in record(output, "build.json")["levels"].items()
                        if name != "far")
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


def rigid_part(part):
    """A part that rides one joint (prop_build.py's rule): a hard part but a belt or a buckle, the hair, a bare hand."""
    name = str(part.get("name", ""))
    if any(word in name for word in CLOTH_WORDS):
        return False
    return part.get("role") in RIGID_ROLES or name in RIGID_NAMES


def judge_shell(output, inputs, evidence):
    """The look a thin shell over SOMA-X's fitted body (owner, 2026-10-12): SHELL_SHARE of the soft parts' points
    (every part but the rigid ones: hard parts other than belts and buckles, hair and the bare hands, which ride
    one joint) within OFFSET_MOST of
    the body. A proxy (captain, 2026-10-13, the owner may reverse it): the points past it are loose cloth edges, cuffs,
    hems and caps, which no part label names; the clips gate judges what the cloth does in every clip. The worst
    point's part and offset are recorded."""
    found = record(output, "shell.json")
    parts = {str(part["part"]): part for part in record(output, "parts.json")["parts"]}
    soft = {key: entry for key, entry in found["parts"].items() if not rigid_part(parts.get(key, {}))}
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
    from score.stages.people_bodies import clips
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
    """Two paid world rows a look: its parts (PARTS), priced on their own, and its body, which reads them; a far-crowd
    look (`far_only`) is built only and gated on what a far body shows."""
    return tuple(row for look, entry in looks().items() for row in (
        graph.Stage(f"{PARTS}-{look}", "world", parts_made(look, entry), contracts.Contract(PARTS, 1, parts_faults),
                    (guarded("parts", judge_parts),), files=parts_files(entry),
                    beside={MADE: (MADE, 1)}, neighbours=the_line,
                    params={"take": entry["take"], "outfit": entry["outfit"]}, paid=True, euros=PARTS_EUROS),
        graph.Stage(f"{BODY}-{look}", "world", made(look, entry), contracts.Contract(BODY, 1, body_faults),
                    far_checks() if entry.get("far_only") else checks(), files=files(look, entry),
                    after={f"{PARTS}-{look}": (PARTS, 1), made_clips.ROW: (made_clips.ROW, 1)},
                    beside={MADE: (MADE, 1)}, neighbours=the_line,
                    params={key: value for key, value in entry.items() if key != "object"}, paid=True,
                    euros=FAR_EUROS if entry.get("far_only") else EUROS)))
