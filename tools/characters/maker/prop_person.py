"""The character maker's prop route for a person (owner, 2026-10-10: "soma is for the rig, not the mesh ... we should
fit the prop pipeline mesh to the rig, and maybe on top of that do some part segmentations, and for the clothing parts
some drape shaping"): a spec with "route": "prop" is made here; every other person spec keeps the shipped route.

    .venv/bin/python tools/characters/maker/prop_person.py data/characters/makes/<name>.json --who "<session>"
        [--outfit work] [--stages closeup,mesh,parts,build,checks] [--held <characters run folder>] [--dry-run]

Everything lands in ~/.farm-factory-motion/candidates/prop-people/<name>/<outfit>/, never in a kept look or a built
body. The stages, each a cloud job through the repo's runners (only plain CPU geometry runs on this PC):
  closeup  on a characters machine (prop_chain.py): the bind pose measured on SOMA-X's skeleton, the close-up drawn
           by klein in it (two seeds); no body is read off it (SAM3DBody-cpp is not used on this route)
  rig      on a characters machine (prop_skeleton.py): SOMA-X's mean skeleton, its surface's weights (the source the
           weights are moved from, never drawn) and the clips Kimodo made, against their parents
  mesh     Pixal3D on every close-up that passed (../../props/cloud/batch.py --characters, as the animals' meshes),
           finished here as every batch model is; the gaps between arms and body and between the legs checked on
           its cut-out; the take with the most of its figure separated is kept
  parts    SAM 2.1's regions of the close-up (segment.py), GeoSAM2 seeded with them on the raw model (meshparts.py),
           the judge naming each part's material (judge.py), laid onto the finished model (prop_parts.py)
  build    on a characters machine (prop_chain.py): SOMA-X's skeleton placed inside the Pixal3D mesh (its bone
           lengths and rest pose fitted to the mesh's limbs; no SOMA surface is shown or shapes the mesh), its skin
           weights moved onto the mesh, the glTF with Kimodo's clips, UsdSkel, joins.py, and the review renders
  checks   the per-frame pokes (pokes.py), the A-pose outline (outline.py) and drape_measure.py where a Warp drape
           is kept, written with joins.py's record to checks.txt
`--held` runs the characters stages on a machine characters.py --hold keeps (its run folder), as a step is tried.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
CLOUD = REPO / "tools/props/cloud"
sys.path.insert(0, str(HERE))

import spec as specs  # noqa: E402

MOTION_HOME = pathlib.Path.home() / ".farm-factory-motion"
CANDIDATES = MOTION_HOME / "candidates" / "prop-people"
PROPS_PYTHON = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
MOTIONS = MOTION_HOME / "work" / "motions"
STAGES = ("closeup", "rig", "mesh", "parts", "build", "checks")
POLL_SECONDS = 30


def folder_of(spec, outfit):
    """The candidate's folder for one outfit."""
    return CANDIDATES / spec["name"] / outfit


def take_name(spec, outfit, seed):
    """A close-up's name, which is also its Pixal3D model's name under the props' work folder."""
    return f"pp-{spec['name']}-{outfit}-s{seed}"


def make_folder(place, spec, steps, files):
    """A make folder characters.py runs prop_chain.py on: in/spec.json with its `steps`, and `files` copied into
    in/files/ (each named in the spec by where it lies up there). The folder."""
    inputs = place / "in"
    if inputs.exists():
        shutil.rmtree(inputs)
    (inputs / "files").mkdir(parents=True)
    machine_spec = {key: value for key, value in spec.items() if key != "references"}
    machine_spec.update(program="prop_chain.py", steps=list(steps), references=[])
    for name, path in files.items():
        target = inputs / "files" / f"{name}{''.join(pathlib.Path(path).suffixes)}"
        if pathlib.Path(path).is_dir():
            shutil.copytree(path, target)
        else:
            shutil.copy2(path, target)
        if name.startswith("reference_"):
            machine_spec["references"].append(f"in/files/{target.name}")
        else:
            machine_spec.setdefault("files", {})[name] = f"in/files/{target.name}"
    if "rig" in steps:
        shutil.copytree(MOTIONS, inputs / "motions", ignore=shutil.ignore_patterns("*.bvh"))
    (inputs / "spec.json").write_text(json.dumps(machine_spec, indent=1))
    return place


def on_characters(place, who, held, dry_run):
    """Run a make folder's prop_chain.py on a characters machine: a held one (its run folder), else one rented."""
    if held:
        return on_held(place, held)
    command = [PROPS_PYTHON, CLOUD / "characters.py", place, "--who", who] + (["--dry-run"] if dry_run else [])
    subprocess.run([str(part) for part in command], check=True)
    return place


def held_machine(run):
    """The held machine's host and its folder (where its ssh known_hosts lie)."""
    host = (run / "host").read_text().strip()
    folders = [path.parent for path in run.glob("*/known_hosts")]
    if not folders:
        raise SystemExit(f"{run}: no machine folder with known_hosts")
    return host, folders[0]


def on_held(place, run):
    """A make folder's program run on the held machine of characters.py's run folder `run`: in/ up, the program in
    the background, its exit waited for, out/ and the log back (characters.make_one's steps on a held machine)."""
    sys.path.insert(0, str(CLOUD))
    import batch
    import characters
    host, machine = held_machine(run)
    remote = characters.REMOTE / place.name
    batch.remote(machine, host, f"rm -rf {remote} && mkdir -p {remote}", check=True)
    batch.copy(machine, [place / "in"], f"root@{host}:{remote}/")
    batch.copy(machine, [REPO / "tools"], f"root@{host}:/root/score/", "--exclude", "__pycache__")
    batch.remote(machine, host, characters.chain_line(place.name, characters.program_of(place)), check=True)
    code = None
    while (code := characters.exit_code(machine, host, place.name)) is None:
        time.sleep(POLL_SECONDS)
    characters.bring_back(machine, host, place)
    if code:
        raise SystemExit(f"{place.name} ended with {code} ({place / 'out' / 'chain.log'})")
    return place


def closeup(spec, outfit, who, held, dry_run):
    """The close-ups and their checks, into <candidate>/closeup/."""
    folder = folder_of(spec, outfit)
    make = folder / "closeup-make"
    machine_spec = dict(spec, name=f"{spec['name']}-{outfit}", outfit=outfit, who=spec["description"],
                        outfit_words=spec["outfit_words"][outfit])
    references = {f"reference_{number}": pathlib.Path(path).expanduser()
                  for number, path in enumerate(spec.get("references", []))}
    make_folder(make, machine_spec, ("pose", "closeup"), references)
    on_characters(make, who, held, dry_run)
    if dry_run:
        return []
    out = folder / "closeup"
    out.mkdir(exist_ok=True)
    shutil.copy2(make / "out" / "pose.json", out / "pose.json")
    made = []
    for picture in sorted((make / "out" / "closeup").glob("*_s*.png")):
        name = take_name(spec, outfit, picture.stem.rsplit("_s", 1)[1])
        shutil.copy2(picture, out / f"{name}.png")
        made.append(name)
    return made


def rig(spec, outfit, who, held, dry_run):
    """SOMA-X's rig and the clips (prop_skeleton.py) into <candidate person>/rig.npz, shared by the outfits."""
    make = CANDIDATES / spec["name"] / "rig-make"
    make_folder(make, dict(spec, name=f"{spec['name']}-rig"), ("rig",), {})
    on_characters(make, who, held, dry_run)
    if dry_run:
        return None
    shutil.copy2(make / "out" / "rig.npz", CANDIDATES / spec["name"] / "rig.npz")
    return str(CANDIDATES / spec["name"] / "rig.npz")


PIXAL = pathlib.Path.home() / ".farm-factory-props/work/pixal"
REVIEW_CLIPS = ("standing", "walking", "bench", "waiting", "suit")


def cloud(tool, *arguments):
    """A cloud runner of tools/props/cloud as its own process, in the props environment; raises when it fails."""
    subprocess.run([str(PROPS_PYTHON), str(CLOUD / tool), *map(str, arguments)], check=True)


def local(script, *arguments):
    """A CPU step of this folder under the memory cap, in the props environment; raises when it fails."""
    subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=16G", str(PROPS_PYTHON),
                    str(HERE / script), *map(str, arguments)], check=True)


def closeups(spec, outfit):
    """The candidate's close-ups: their take names."""
    return sorted(path.stem for path in (folder_of(spec, outfit) / "closeup").glob("pp-*.png"))


def mesh(spec, outfit, who, held, dry_run):
    """Pixal3D on every close-up (batch.py --characters, as the animals' meshes), finished here; each finished take
    checked for limbs that stand apart (prop_rig.landmarks); the first that passes is kept (<candidate>/take.txt)."""
    folder = folder_of(spec, outfit)
    specs_folder = folder / "mesh"
    specs_folder.mkdir(exist_ok=True)
    wanted = []
    for take in closeups(spec, outfit):
        if (PIXAL / f"{take}-final.glb").exists():
            continue
        path = specs_folder / f"{take}.json"
        path.write_text(json.dumps({"name": take, "approved": spec["approved"],
                                    "picture": str(folder / "closeup" / f"{take}.png")}, indent=1))
        wanted.append(path)
    if wanted:
        cloud("batch.py", "--characters", *wanted, "--who", who, "--max-cards", "1", *(["--dry-run"] if dry_run else []))
    if dry_run:
        return None
    sys.path.insert(0, str(HERE))
    import prop_rig
    import trimesh
    found = {}
    for take in closeups(spec, outfit):
        model = trimesh.load(PIXAL / f"{take}-final.glb", force="mesh")
        turn, scale, shift = prop_rig.stood(model.vertices, 1.75)
        try:
            marks = prop_rig.landmarks(prop_rig.sampled(trimesh.Trimesh(model.vertices @ turn.T * scale + shift,
                                                                        model.faces, process=False)))
            found[take] = {"limbs_apart": True, "crotch_m": round(marks["crotch"], 3),
                           "armpit_m": round(marks["armpit"], 3)}
        except prop_rig.RigError as refused:
            found[take] = {"limbs_apart": False, "why": str(refused)}
    (folder / "mesh" / "takes.json").write_text(json.dumps(found, indent=1))
    kept = [take for take, entry in found.items() if entry["limbs_apart"]]
    if not kept:
        raise SystemExit(f"no take with its limbs apart: {found}")
    (folder / "take.txt").write_text(kept[0])
    return {"kept": kept[0], "takes": found}


def parts(spec, outfit, who, held, dry_run):
    """The kept take's parts (prop_parts.py): SAM 2.1's regions, GeoSAM2 seeded with them, the judge's materials."""
    folder = folder_of(spec, outfit)
    take = (folder / "take.txt").read_text().strip()
    run = folder / "parts"
    pictures = run / "pictures"
    pictures.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PIXAL / f"{take}.svviews" / "input.png", pictures / f"{take}.png")
    cloud("segment.py", pictures, "--who", who, *(["--dry-run"] if dry_run else []))
    if dry_run:
        return None
    sys.path.insert(0, str(REPO / "tools/props/library"))
    sys.path.insert(0, str(REPO / "tools/props"))
    import split_compare
    import split_spread
    if not (run / take / "up" / "seed_points.npz").exists():
        split_compare.write_inputs(run, take, pictures / "masks")
    cloud("meshparts.py", run, "--who", who, "--takes", take, "--methods", "geosam2")
    split_spread.lay_geosam2(run, take)
    spec_file = folder / "spec.json"
    spec_file.write_text(json.dumps(spec, indent=1))
    local("prop_parts.py", "questions", run, take, spec_file)
    cloud("judge.py", run / "questions" / "questions.json", run / "answers")
    local("prop_parts.py", "parts", run, take, spec_file)
    return json.loads((run / take / "parts.json").read_text())


def build(spec, outfit, who, held, dry_run):
    """The rig fitted into the kept take (prop_rig.py, here), then the person built on a characters machine
    (prop_chain.py build and review): <candidate>/out/."""
    folder = folder_of(spec, outfit)
    take = (folder / "take.txt").read_text().strip()
    rig_file = CANDIDATES / spec["name"] / "rig.npz"
    local("prop_rig.py", PIXAL / f"{take}-final.glb", rig_file, folder / "fit")
    make = folder / "build-make"
    machine_spec = dict(spec, name=f"{spec['name']}-{outfit}-build", person=spec["name"], outfit=outfit,
                        review_clips=list(REVIEW_CLIPS))
    make_folder(make, machine_spec, ("build", "review"),
                {"fit": folder / "fit" / "rig.npz", "mean": rig_file, "parts": folder / "parts" / take / "parts.npz"})
    on_characters(make, who, held, dry_run)
    if not dry_run:
        if (folder / "out").exists():
            shutil.rmtree(folder / "out")
        shutil.copytree(make / "out", folder / "out")
    return json.loads((folder / "fit" / "rig.json").read_text())["matched_share"]


CHECKS_TABLE = pathlib.Path.home() / ".farm-factory-props/score-coordinator/prop-people"


def table_rows(spec, outfit, folder, take):
    """The checks' rows: (check, measure, value, gate, verdict)."""
    rig = json.loads((folder / "fit" / "rig.json").read_text())
    joined = json.loads((folder / "out" / "checks" / f"{spec['name']}.json").read_text())["verdict"]
    poked = json.loads((folder / "checks" / "pokes.json").read_text())
    outlined = json.loads((folder / "checks" / "outline.json").read_text())
    parts = json.loads((folder / "parts" / take / "parts.json").read_text())
    rows = [("rig", "limbs apart (crotch, armpit found)", f"crotch {rig['fit']['crotch']:.3f} m, armpit "
             f"{rig['fit']['armpit']:.3f} m", "found", "pass"),
            ("rig", "mesh vertices matched by RSWT", f"{rig['matched_share']:.1%} (rest inpainted)", "record", "-"),
            ("parts", "GeoSAM2 parts on the finished model", ", ".join(f"{part['name']}:{part['material']}"
                                                                       for part in parts["parts"]), "record", "-")]
    for kind in ("wrist", "ankle"):
        value = joined.get(kind)
        rows.append(("joins.py", f"{kind} worst overlap over every clip",
                     "none" if value is None else f"{value['worstOverlapMetres'] * 100:.1f} cm",
                     ">= 1.0 cm", "none" if value is None else "pass" if value["pass"] else "FAIL"))
    stance = joined.get("stance")
    rows.append(("joins.py", "standing stance (ankles over hips)", "none" if stance is None else f"{stance['ratio']}",
                 "0.55 to 1.2", "none" if stance is None else "pass" if stance["pass"] else "FAIL"))
    worst = max(clip["worst_tuck_out_mm"] for clip in poked["clips"].values())
    over = sum(clip["frames_tuck_over"] for clip in poked["clips"].values())
    rows.append(("pokes.py", "tuck outside its garment, worst frame", f"{worst:.1f} mm ({over} frames over)",
                 f"<= {5.0} mm every frame", "pass" if poked["verdict"]["tucks"] else "FAIL"))
    crossing = max(clip["most_crossings"] for clip in poked["clips"].values())
    rows.append(("pokes.py", "cloth through cloth (crossings), rest / worst frame",
                 f"{poked['rest_crossings']} / {crossing}", "no frame above rest",
                 "pass" if poked["verdict"]["cloth_through_cloth"] else "FAIL"))
    rows.append(("outline.py", "A-pose IoU against the cut-out, raw / built",
                 f"{outlined['iou_raw']} / {outlined['iou_built']} (drop {outlined['iou_drop']})",
                 "drop <= 0.01, bands <= 1 %", "pass" if outlined["pass"] else "FAIL"))
    rows.append(("drape_measure.py", "silhouette against a Warp drape", "not applicable",
                 "record only", "a Pixal3D mesh has no GarmentCode panels to cut by; its self-crossings are "
                 "pokes.py's rest count"))
    return rows


def checks(spec, outfit, who, held, dry_run):
    """Every check of the plan on the built candidate (pokes.py, outline.py here; joins.py's record from the build)
    and the table, <candidate>/checks/checks.txt and the coordinator's copy."""
    folder = folder_of(spec, outfit)
    take = (folder / "take.txt").read_text().strip()
    (folder / "checks").mkdir(exist_ok=True)
    body = folder / "out" / f"{spec['name']}.glb"
    local("pokes.py", body, "--out", folder / "checks" / "pokes.json")
    local("outline.py", take, folder / "fit" / "rig.npz", body, "--out", folder / "checks" / "outline.json")
    rows = table_rows(spec, outfit, folder, take)
    widths = [max(len(str(row[column])) for row in rows) for column in range(4)]
    lines = [f"PROP PEOPLE CHECKS: {spec['name']} ({outfit}), take {take}, "
             f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC", ""]
    lines += ["  ".join(str(value).ljust(width) for value, width in zip(row[:4], widths)) + "  " + row[4]
              for row in rows]
    text = "\n".join(lines) + "\n"
    (folder / "checks" / "checks.txt").write_text(text)
    target = CHECKS_TABLE / spec["name"] / "checks.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    return str(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("spec", type=pathlib.Path)
    parser.add_argument("--who", required=True)
    parser.add_argument("--outfit", default="work")
    parser.add_argument("--stages", default=",".join(STAGES))
    parser.add_argument("--held", type=pathlib.Path, help="a characters.py --hold run folder")
    parser.add_argument("--dry-run", action="store_true")
    options = parser.parse_args()
    spec = specs.read(options.spec)
    if spec.get("route") != "prop":
        raise SystemExit(f"{options.spec}: not a prop route spec (\"route\": \"prop\")")
    folder = folder_of(spec, options.outfit)
    folder.mkdir(parents=True, exist_ok=True)
    for stage in options.stages.split(","):
        began = time.time()
        result = STAGE_WORK[stage](spec, options.outfit, options.who, options.held, options.dry_run)
        record_stage(folder, stage, began, result)


def record_stage(folder, stage, began, result):
    """One stage's minutes and result into <candidate>/make.json."""
    path = folder / "make.json"
    record = json.loads(path.read_text()) if path.exists() else {"stages": []}
    record["stages"].append({"stage": stage, "minutes": round((time.time() - began) / 60, 2),
                             "ended": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "result": result})
    path.write_text(json.dumps(record, indent=1, default=str))
    print(f"== {stage}: {result}", flush=True)


STAGE_WORK = {"closeup": closeup, "rig": rig, "mesh": mesh, "parts": parts, "build": build, "checks": checks}


if __name__ == "__main__":
    main()
