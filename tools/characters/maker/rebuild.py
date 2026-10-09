"""Rebuild people the world already has with new drapes: each kept look's drapes hung again from their own sewing
patterns (each drape folder's <tag>_specification.json, the pattern as it was sized then) on the look's own body at
rest, by a commercial-OK simulator, into a NEW look copy; the people built again from it; and pictures of the old and
the new body taken with the same cameras (job drapes, 2026-10-09: the looks kept before were draped by GarmentCode's
non-commercial Warp fork).

    .venv/bin/python tools/characters/maker/rebuild.py bundle [<person> ...] [--simulator blender]
    .venv/bin/python tools/props/cloud/characters.py ~/.farm-factory-motion/rebuild/make/<group> ... --who "<session>"
    .venv/bin/python tools/characters/maker/rebuild.py land [<group> ...]

`bundle` writes a make folder for each drape group under ~/.farm-factory-motion/rebuild/make/<group>/in/: a group is
one person whose drapes are draped here and the people whose looks carry byte copies of those drapes and body (the
prologue's guard, driver and technicians wear their kit build's), so each pattern is draped once. characters.py runs
it on a rented card, one group a machine, with this file as the program (`spec.json`'s `program`). `land` copies
what came back into ~/.farm-factory-motion/rebuild/: look/<person>/ (the new look copy), bodies/<person>.glb and
.json (with crowd_body/ for kit_m_avg), review/<person>/{old,new}/ (front, side, back and the other side of each
outfit, standing) and results/<person>.json (each drape's measurements old and new, drape_measure.py's numbers,
whether the build passed, the picture paths). Nothing here touches ~/.farm-factory-motion/look or work/bodies.

On the machine (`run`, /root/envs/motion/bin/python rebuild.py run /root/make/<group>): the lead's rest body
(export_body.py), each drape again from its pattern with the measurements it was sized on (bodies/ours.yaml, the
waist the cloth is held at), the drape folders copied into every member's new look, every member built
(people/body.py, its report beside the glb), the crowd's animation texture when the group is kit_m_avg's, the
measurements, and the review renders (blender_review.py). The drapes' simulator is the bundle's `simulator`.
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PEOPLE_TOOLS = HERE.parent / "people"
MOTION_HOME = pathlib.Path(os.environ.get("MOTION_HOME", pathlib.Path.home() / ".farm-factory-motion"))
REBUILD = MOTION_HOME / "rebuild"
# Everybody who is rebuilt, in paths.PEOPLE's order (a person whose drapes copy an earlier one's joins that group).
PEOPLE = ("take_c", "nev", "oona", "bram", "sefa", "kit_m_slim", "kit_m_avg", "kit_m_broad", "kit_w_slim",
          "kit_w_avg", "kit_w_broad", "leader", "guard", "driver", "tech_man", "tech_woman")
# The garment design whose cloth settings (data/characters/garments/<design>/cloth.json) each kind is draped with.
DESIGNS = {"work": "work_suit", "space": "space_suit", "jacket": "jacket", "coat": "coat", "trousers": "trousers"}
WOMEN = ("nev", "oona", "kit_w_slim", "kit_w_avg", "kit_w_broad", "tech_woman")
# The crowd's far body is kit_m_avg's (people/run.sh --crowd) with these clips.
CROWD_LEAD = "kit_m_avg"
CROWD_CLIPS = ("standing", "shifting", "clapping", "cheering")
# Front, side, back, other side: blender_review.py's turntable at four angles, standing.
REVIEW_ANGLES = 4
REVIEW_SIZE = 640


# ---- plain pieces (no numpy: the gate tests them) ---------------------------------------------------------------

def drape_folders(look):
    """A look's drape folders (<kind>_drape), sorted."""
    return sorted(folder for folder in pathlib.Path(look).glob("*_drape") if folder.is_dir())


def kind_of(drape_folder):
    """The garment kind a drape folder holds: work, space, jacket, coat or trousers."""
    return pathlib.Path(drape_folder).name[:-len("_drape")]


def tag_of(specification):
    """The pattern's name a <tag>_specification.json carries."""
    return pathlib.Path(specification).name[:-len("_specification.json")]


def file_digest(path):
    return hashlib.md5(pathlib.Path(path).read_bytes()).hexdigest()


def look_digest(look):
    """One digest of what draping reads from a look: the body's identity and every file of every drape folder."""
    look = pathlib.Path(look)
    parts = [f"identity {file_digest(look / 'identity.npz')}"]
    for folder in drape_folders(look):
        parts += [f"{folder.name}/{path.name} {file_digest(path)}" for path in sorted(folder.iterdir())]
    return hashlib.md5("\n".join(parts).encode()).hexdigest()


def groups_of(looks):
    """People grouped by identical drapes and body ({lead: [lead, member, ...]}), the lead the first in order."""
    groups, leads = {}, {}
    for person, look in looks.items():
        digest = look_digest(look)
        lead = leads.setdefault(digest, person)
        groups.setdefault(lead, []).append(person)
    return groups


def patterns_by_digest(root):
    """Every GarmentCode pattern folder kept under `root` (…/patterns/<tag>/), by its specification's digest and by
    its tag; a pattern folder holds the body_measurements.yaml and design.yaml it was sized with."""
    by_digest, by_tag = {}, {}
    for specification in sorted(pathlib.Path(root).glob("**/patterns/*/*_specification.json")):
        folder = specification.parent
        if not (folder / "body_measurements.yaml").exists():
            continue
        by_digest.setdefault(file_digest(specification), folder)
        by_tag.setdefault(tag_of(specification), folder)
    return by_digest, by_tag


def sized_with(specification, by_digest, by_tag):
    """The kept pattern folder a drape's specification came from: the same file, else the same pattern name."""
    return by_digest.get(file_digest(specification)) or by_tag.get(tag_of(specification))


def results_row(old, new):
    """drape_measure's numbers old beside new, and new minus old where both are numbers."""
    row = {"old": old, "new": new, "change": {}}
    for key, value in (new or {}).items():
        before = (old or {}).get(key)
        if isinstance(value, (int, float)) and isinstance(before, (int, float)):
            row["change"][key] = round(value - before, 3)
    return row


# ---- here: bundle and land ---------------------------------------------------------------------------------------

def bundle_group(lead, members, simulator, pattern_index):
    """Write <rebuild>/make/<lead>/in/ for one group; the make folder."""
    looks = MOTION_HOME / "look"
    folder = REBUILD / "make" / lead
    inputs = folder / "in"
    for stale in (inputs, folder / "out"):
        if stale.exists():
            shutil.rmtree(stale)
    (inputs / "old").mkdir(parents=True)
    for person in members:
        shutil.copytree(looks / person, inputs / "look" / person)
        for suffix in (".glb", ".json"):
            if (MOTION_HOME / "work/bodies" / f"{person}{suffix}").exists():
                shutil.copy2(MOTION_HOME / "work/bodies" / f"{person}{suffix}", inputs / "old" / f"{person}{suffix}")
    drapes = []
    for drape in drape_folders(looks / lead):
        specification = next(drape.glob("*_specification.json"))
        source = sized_with(specification, *pattern_index)
        if source is None:
            raise SystemExit(f"no kept pattern folder holds the measurements {specification} was sized on")
        kept = inputs / "sized" / drape.name
        kept.mkdir(parents=True)
        for name in ("body_measurements.yaml", "design.yaml"):
            if (source / name).exists():
                shutil.copy2(source / name, kept / name)
        drapes.append({"folder": drape.name, "kind": kind_of(drape), "tag": tag_of(specification),
                       "design": DESIGNS[kind_of(drape)], "sized_from": str(source.relative_to(MOTION_HOME))})
    shared = inputs / "shared/look"
    shutil.copytree(looks / "kit", shared / "kit")
    (shared / "take_c").mkdir(parents=True)
    shutil.copy2(looks / "take_c/eyes.npz", shared / "take_c/eyes.npz")
    shutil.copytree(MOTION_HOME / "work/motions", inputs / "motions", ignore=shutil.ignore_patterns("*.bvh"))
    spec = {"name": lead, "program": "rebuild.py", "people": members, "drapes": drapes, "simulator": simulator,
            "reference": "mean_female" if lead in WOMEN else "mean_male", "crowd": lead == CROWD_LEAD}
    (inputs / "spec.json").write_text(json.dumps(spec, indent=1))
    return folder


def bundle(people, simulator):
    """Make folders for the groups the wanted people fall in; the folders."""
    looks = {person: MOTION_HOME / "look" / person for person in PEOPLE}
    groups = groups_of(looks)
    pattern_index = patterns_by_digest(MOTION_HOME / "rnd")
    folders = []
    for lead, members in groups.items():
        if any(person in members for person in people):
            folders.append(bundle_group(lead, members, simulator, pattern_index))
            print(f"{lead}: {', '.join(members)} -> {folders[-1]}", flush=True)
    return folders


def land(group):
    """Copy one group's out/ into the rebuild folders: looks, bodies, review pictures and per-person results."""
    out = REBUILD / "make" / group / "out"
    if not out.exists():
        raise SystemExit(f"{out} is not back yet")
    for person in json.loads((REBUILD / "make" / group / "in/spec.json").read_text())["people"]:
        for source, target in ((out / "look" / person, REBUILD / "look" / person),
                               (out / "review" / person, REBUILD / "review" / person)):
            if source.exists():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(source, target)
        (REBUILD / "bodies").mkdir(parents=True, exist_ok=True)
        for suffix in (".glb", ".json"):
            if (out / "bodies" / f"{person}{suffix}").exists():
                shutil.copy2(out / "bodies" / f"{person}{suffix}", REBUILD / "bodies" / f"{person}{suffix}")
        result = out / "results" / f"{person}.json"
        if result.exists():
            (REBUILD / "results").mkdir(parents=True, exist_ok=True)
            row = json.loads(result.read_text())
            row["pictures"] = {which: sorted(str(path) for path in (REBUILD / "review" / person / which).glob("*.png"))
                               for which in ("old", "new")}
            (REBUILD / "results" / f"{person}.json").write_text(json.dumps(row, indent=1))
        print(f"landed {person}", flush=True)
    if (out / "bodies/crowd_body").exists():
        target = REBUILD / "bodies/crowd_body"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(out / "bodies/crowd_body", target)


# ---- up there: the run -------------------------------------------------------------------------------------------

ENVS = pathlib.Path("/root/envs")
MOTION = ENVS / "motion/bin/python"
GARMENT = ENVS / "garment/bin/python"
BLENDER = pathlib.Path("/root/blender/blender")
REMOTE_HOME = pathlib.Path("/root/motion-home")
CUDA_LIBRARIES = "/usr/local/cuda-12.6/lib64"


class Run:
    """One group's rebuild on the machine: its folders, its bundle and the record of every step."""

    def __init__(self, folder):
        self.folder = folder
        self.spec = json.loads((folder / "in/spec.json").read_text())
        self.out = folder / "out"
        self.work = folder / "work"
        for place in (self.out / "bodies", self.out / "results", self.work / "motionwork"):
            place.mkdir(parents=True, exist_ok=True)
        self.record = {"group": self.spec["name"], "simulator": self.spec["simulator"], "steps": []}

    def environment(self, person, look):
        return dict(os.environ, MOTION_HOME=str(REMOTE_HOME), MOTION_LOOK=str(look),
                    MOTION_WORK=str(self.work / "motionwork"), MOTION_PERSON=person, PROPS_BLENDER=str(BLENDER),
                    GARMENTCODE="/root/garmentcode", GARMENTCODE_PYTHON=str(GARMENT),
                    LD_LIBRARY_PATH=":".join(filter(None, [CUDA_LIBRARIES, os.environ.get("LD_LIBRARY_PATH")])))

    def program(self, command, person, look, **extra):
        print("$", " ".join(map(str, command)), flush=True)
        subprocess.run([str(part) for part in command], check=True,
                       env={**self.environment(person, look), **extra}, cwd=self.work)

    def step(self, name, work):
        """Run one step, timed into out/rebuild.json; a failed step is recorded and False returned."""
        began = time.time()
        entry = {"step": name}
        try:
            entry["notes"] = work() or ""
            entry["ok"] = True
        except Exception as failure:  # recorded, and the run goes on with what does not need this step
            entry.update(ok=False, failure=f"{type(failure).__name__}: {failure}")
        entry["minutes"] = round((time.time() - began) / 60, 2)
        self.record["steps"].append(entry)
        (self.out / "rebuild.json").write_text(json.dumps(self.record, indent=1))
        print(f"== {name}: {'ok' if entry['ok'] else 'FAILED ' + entry['failure']} in {entry['minutes']} min",
              flush=True)
        return entry["ok"]

    @property
    def lead(self):
        return self.spec["name"]

    def old_look(self, person):
        return self.folder / "in/look" / person

    def new_look(self, person):
        return self.out / "look" / person

    @property
    def rest(self):
        return self.work / "rest"


def prepare(run):
    """The motion home the people tools read (the motion environment, the kit's shared parts, take C's eyes), the
    clips, and each member's new look: the old look without its drapes."""
    REMOTE_HOME.mkdir(exist_ok=True)
    if not (REMOTE_HOME / "env").exists():
        (REMOTE_HOME / "env").symlink_to(ENVS / "motion")
    if (REMOTE_HOME / "look").exists():
        shutil.rmtree(REMOTE_HOME / "look")
    shutil.copytree(run.folder / "in/shared/look", REMOTE_HOME / "look")
    motions = run.work / "motionwork/motions"
    if not motions.exists():
        shutil.copytree(run.folder / "in/motions", motions)
    for person in run.spec["people"]:
        new = run.new_look(person)
        if new.exists():
            shutil.rmtree(new)
        shutil.copytree(run.old_look(person), new, ignore=shutil.ignore_patterns("*_drape"))


def rest_body(run):
    """The lead's body at rest, as the build skins it (export_body.py)."""
    look = run.old_look(run.lead)
    run.program([MOTION, HERE / "export_body.py", look / "identity.npz", run.rest], run.lead, look)


def redrape_blender(run, drape):
    """One drape again from its kept pattern on the rest body with Blender's cloth: GarmentCode's box meshes of the
    pattern as it was sized (no new pattern), the measurements it was sized on for the held waist, then
    cloth_drape.py; into the lead's new look."""
    os.environ.update(GARMENTCODE="/root/garmentcode", GARMENTCODE_PYTHON=str(GARMENT))
    sys.path.insert(0, str(HERE))
    import drape_garment
    tag, out = drape["tag"], run.new_look(run.lead) / drape["folder"]
    work = run.work / "drapes" / drape["folder"]
    for place in (out, work):
        if place.exists():
            shutil.rmtree(place)
        place.mkdir(parents=True)
    drape_garment.garmentcode("measure", run.rest / "ours.npz", work, run.spec["reference"])
    shutil.copy2(run.rest / "joints.json", work / "bodies/joints.json")
    sized = run.folder / "in/sized" / drape["folder"]
    shutil.copy2(sized / "body_measurements.yaml", work / "bodies/ours.yaml")
    pattern = work / "patterns" / tag
    pattern.mkdir(parents=True)
    shutil.copy2(run.old_look(run.lead) / drape["folder"] / f"{tag}_specification.json", pattern)
    shutil.copy2(sized / "body_measurements.yaml", pattern / "body_measurements.yaml")
    if (sized / "design.yaml").exists():
        shutil.copy2(sized / "design.yaml", pattern / "design.yaml")
    design = drape_garment.design_folder(drape["design"])
    cloth = json.loads((design / "cloth.json").read_text())
    drape_garment.garmentcode("box", work, tag, cloth["resolution_scale"])
    drape_garment.garmentcode("box", work, tag, cloth["coarse_resolution"], f"{tag}_coarse")
    job = drape_garment.cloth_job(work / "box" / tag, work, design, out, tag)
    drape_garment.run_cloth_here(job, BLENDER)
    box = work / "box" / tag
    for suffix in ("_sim_segmentation.txt", "_specification.json"):
        shutil.copy2(box / f"{tag}{suffix}", out / f"{tag}{suffix}")
    if (pattern / "design.yaml").exists():
        shutil.copy2(pattern / "design.yaml", out / "design.yaml")
    if not (out / f"{tag}_sim.obj").exists():
        raise RuntimeError(f"the cloth run wrote no {out / f'{tag}_sim.obj'}")
    return json.loads((out / "blender_cloth.json").read_text()).get("held_on_body")


SIMULATORS = {"blender": redrape_blender}


def share_drapes(run):
    """The lead's new drape folders copied into every other member's new look (their old ones were byte copies)."""
    for person in run.spec["people"][1:]:
        for drape in run.spec["drapes"]:
            target = run.new_look(person) / drape["folder"]
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(run.new_look(run.lead) / drape["folder"], target)


def measuring_look(run):
    """A look folder drape_measure.py can read for the lead: its joints (the rest body's when the look keeps none)."""
    look = run.work / "measure_look"
    look.mkdir(exist_ok=True)
    joints = run.old_look(run.lead) / "joints.json"
    shutil.copy2(joints if joints.exists() else run.rest / "joints.json", look / "joints.json")
    if (run.old_look(run.lead) / "person.json").exists():
        shutil.copy2(run.old_look(run.lead) / "person.json", look / "person.json")
    return look


def measure(run):
    """drape_measure.py's numbers for each drape, the old (Warp fork) and the new, on the same rest body."""
    look = measuring_look(run)
    rows = {}
    for drape in run.spec["drapes"]:
        numbers = {}
        for which, folder in (("old", run.old_look(run.lead)), ("new", run.new_look(run.lead))):
            target = run.work / f"measure_{which}_{drape['folder']}.json"
            try:
                run.program([MOTION, HERE / "drape_measure.py", folder / drape["folder"], run.rest / "ours_cm.obj",
                             look, "--json", target], run.lead, look)
                numbers[which] = json.loads(target.read_text())
            except subprocess.CalledProcessError as failure:
                numbers[which] = {"failure": str(failure)}
        rows[drape["folder"]] = results_row(numbers["old"], numbers["new"])
    run.measurements = rows


def build(run, person):
    """One member built from the new look, its report beside it."""
    look = run.new_look(person)
    run.program([MOTION, PEOPLE_TOOLS / "body.py", "--out", run.out / "bodies" / f"{person}.glb",
                 "--report", run.out / "bodies" / f"{person}.json"], person, look, CUDA_VISIBLE_DEVICES="")


def crowd(run):
    """The far crowd's animation texture from the lead's new look (people/run.sh --crowd)."""
    look = run.new_look(run.lead)
    run.program([MOTION, PEOPLE_TOOLS / "crowd_vat.py", run.out / "bodies/crowd_body", *CROWD_CLIPS], run.lead, look,
                CUDA_VISIBLE_DEVICES="")


def review(run, person, which, glb):
    """Front, side, back and other side of each outfit standing, Cycles on the card (blender_review.py)."""
    target = run.out / "review" / person / which
    target.mkdir(parents=True, exist_ok=True)
    run.program([BLENDER, "-b", "-P", HERE / "blender_review.py", "--", glb, target, "--clips", "standing",
                 "--angles", REVIEW_ANGLES, "--frames", 1, "--size", REVIEW_SIZE], person, run.new_look(person))


def write_results(run, built):
    """out/results/<person>.json for each member."""
    for person in run.spec["people"]:
        row = {"person": person, "group": run.lead, "simulator": run.spec["simulator"],
               "drapes": run.measurements, "build_ok": built.get(person, False),
               "held_on_body": run.held, "steps": run.record["steps"]}
        (run.out / "results" / f"{person}.json").write_text(json.dumps(row, indent=1))


def hang(run, redrape, drape):
    """One drape by the group's simulator, whether it held on the body recorded."""
    run.held[drape["folder"]] = redrape(run, drape)
    return f"held on body: {run.held[drape['folder']]}"


def run_group(folder):
    run = Run(folder)
    run.held, run.measurements = {}, {}
    redrape = SIMULATORS[run.spec["simulator"]]
    ready = run.step("prepare", lambda: prepare(run)) and run.step("rest", lambda: rest_body(run))
    draped = ready
    for drape in run.spec["drapes"]:
        if ready:
            done = run.step(f"drape {drape['folder']}", lambda drape=drape: hang(run, redrape, drape))
            draped = draped and done
    if draped:
        run.step("share", lambda: share_drapes(run))
        run.step("measure", lambda: measure(run))
    built = {}
    for person in run.spec["people"]:
        built[person] = draped and run.step(f"build {person}", lambda person=person: build(run, person))
    if run.spec.get("crowd") and built.get(run.lead):
        run.step(f"crowd {run.lead}", lambda: crowd(run))
    for person in run.spec["people"]:
        old = run.folder / "in/old" / f"{person}.glb"
        if old.exists():
            run.step(f"review old {person}", lambda person=person, old=old: review(run, person, "old", old))
        if built[person]:
            run.step(f"review new {person}", lambda person=person: review(
                run, person, "new", run.out / "bodies" / f"{person}.glb"))
    write_results(run, built)
    failed = [entry["step"] for entry in run.record["steps"] if not entry["ok"]]
    print(f"rebuilt {run.lead}: {len(failed)} failed steps {failed}", flush=True)
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    bundling = sub.add_parser("bundle", help="write the groups' make folders here")
    bundling.add_argument("people", nargs="*", help="whose groups (default everybody)")
    bundling.add_argument("--simulator", default="blender", choices=sorted(SIMULATORS))
    landing = sub.add_parser("land", help="copy the groups' out folders into the rebuild folders here")
    landing.add_argument("groups", nargs="*")
    running = sub.add_parser("run", help="on the machine: rebuild one group")
    running.add_argument("folder", type=pathlib.Path)
    options = parser.parse_args()
    if options.command == "bundle":
        bundle(options.people or list(PEOPLE), options.simulator)
    elif options.command == "land":
        for group in options.groups or sorted(path.name for path in (REBUILD / "make").iterdir()):
            land(group)
    else:
        sys.exit(run_group(options.folder.resolve()))


if __name__ == "__main__":
    main()
