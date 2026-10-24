"""The character maker's prop route for a person (owner, 2026-10-10: "soma is for the rig, not the mesh ... we should
fit the prop pipeline mesh to the rig, and maybe on top of that do some part segmentations, and for the clothing parts
some drape shaping"), with the people route on its built body (owner, 2026-10-18). The people's body rows
(score/stages/people_bodies) run its stages on the look the people line drew and Pixal3D made (its take, laid in
the props' work folder); the clips and the mean rig are the row people-clips-made's (`clips_rig`). Experimental (#5),
so by hand only with --experimental (docs/bible.md, architecture/experimental).

    .venv/bin/python tools/characters/maker/prop_person.py data/people/specs/<name>.json --who "<session>"
        --experimental [--outfit work] [--stages parts,build,route,checks-cloud] [--held <characters run folder>]
        [--dry-run]

Everything lands in ~/.farm-factory-motion/candidates/prop-people/<name>/<outfit>/. The stages, each a cloud job
through the repo's runners (only plain CPU geometry runs on this PC):
  parts    SAM 2.1's regions of the close-up (segment.py), GeoSAM2 seeded with them on the raw model (meshparts.py),
           the judge naming each part's and each finish region's material (judge.py), the regions carried onto the
           faces the camera sees, laid onto the finished model (prop_parts.py)
  identity on a characters machine (prop_chain.py): the body under the clothes read off the kept take's close-up by
           SAM 3D Body (body_picture.py), <candidate>/fit/identity.npz, for the people route's base (route_base.py);
           run by name (`--stages identity`); `route` reads it again itself
  build    SOMA-X's skeleton placed inside the Pixal3D mesh here (prop_rig.py: its bone lengths and rest pose fitted to
           the mesh's limbs; no SOMA surface is shown or shapes the mesh), SOMA-X's body fitted to its outside on a
           characters machine (prop_shell.py), then on that machine (prop_chain.py) the glTF with Kimodo's clips,
           UsdSkel and joins.py
  route    the people route on a characters machine: the identity read, then the built body rebuilt on SOMA-X's base
           under the look, garments bound by limb, the correctives as morph targets (prop_chain.py route):
           <candidate>/route/<name>.glb, its record, its UsdSkel asset and joins.py's record
  checks-cloud  the per-frame pokes (pokes.py), the A-pose outline (outline.py) and the reviewer's skin through cloth
           count side by side on a rented processor machine (inside/body_checks.py), written with joins.py's record
           to checks.txt
`--held` runs the characters stages on a machine characters.py --hold keeps (its run folder), as a step is tried.
"""
import argparse
import contextlib
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
CLOUD = REPO / "tools/cloud"
sys.path.insert(0, str(HERE))

import spec as specs  # noqa: E402

MOTION_HOME = pathlib.Path.home() / ".farm-factory-motion"
CANDIDATES = MOTION_HOME / "candidates" / "prop-people"
PROPS_PYTHON = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
STAGES = ("parts", "build", "route", "checks-cloud")
POLL_SECONDS = 30


def folder_of(spec, outfit):
    """The candidate's folder for one outfit."""
    return CANDIDATES / spec["name"] / outfit


def make_place(folder, stage):
    """A stage's make folder in the candidate's folder, named for the person, the outfit and the stage, since a held
    machine keeps each make under its folder's name (two people's settles in one "settle-make" ran over each other,
    2026-10-10)."""
    return folder / f"{folder.parent.name}-{folder.name}-{stage}"


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


HOLD_WAIT_MINUTES = 45


@contextlib.contextmanager
def machine_held(spec, outfit, who, minutes=150):
    """One characters machine rented and set up once for a look's build and route (characters.py --hold on a make
    with no steps), its run folder for `on_held`; let go when done. Two rentals each set up for about 15 minutes
    before (2026-10-12)."""
    place = make_place(folder_of(spec, outfit), "hold")
    make_folder(place, dict(spec, name=f"{spec['name']}-{outfit}-hold"), (), {})
    shutil.rmtree(place / "out", ignore_errors=True)  # a last run's out would read as this machine set up
    log = place / "characters.log"
    with log.open("w") as written:
        process = subprocess.Popen([str(PROPS_PYTHON), str(CLOUD / "characters.py"), str(place), "--who", who,
                                    "--hold", "--minutes", str(minutes)], stdout=written, stderr=subprocess.STDOUT)
    run = None
    try:
        began = time.time()
        while run is None or not (run / "host").exists() or not (place / "out").exists():
            if process.poll() is not None:
                raise SystemExit(f"the held machine's run ended with {process.returncode} ({log})")
            if time.time() - began > HOLD_WAIT_MINUTES * 60:
                raise SystemExit(f"no held machine after {HOLD_WAIT_MINUTES} min ({log})")
            named = [line.split("run folder ", 1)[1].split(" (")[0] for line in log.read_text().splitlines()
                     if "run folder " in line]
            run = pathlib.Path(named[0]) if named else None
            time.sleep(POLL_SECONDS)
        yield run
    finally:
        if run is not None:
            (run / "release").touch()
        else:
            process.terminate()
        process.wait(timeout=900)


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


PIXAL = pathlib.Path.home() / ".farm-factory-props/work/pixal"
# The welded mesh is thinned part by part to this many triangles before the rig (prop_rig.py --faces), so the outfit
# with its tucks and its piping's cuts stays within the shipped player's 29,849 (the player: 28,500 made 29,244 with
# the tucks, and the piping's cuts add about 1,650).
NEAR_FACES = 27300


def cloud(tool, *arguments):
    """A cloud runner of tools/cloud as its own process, in the props environment; raises when it fails."""
    subprocess.run([str(PROPS_PYTHON), str(CLOUD / tool), *map(str, arguments)], check=True)


def local(script, *arguments):
    """A CPU step (a script of this folder, or one by its own path) under the memory cap, in the props environment;
    raises when it fails."""
    subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=16G", str(PROPS_PYTHON),
                    str(HERE / script), *map(str, arguments)], check=True)


def parts(spec, outfit, who, held, dry_run):
    """The kept take's parts (prop_parts.py): SAM 2.1's regions, GeoSAM2 seeded with them, the judge's materials."""
    folder = folder_of(spec, outfit)
    take = (folder / "take.txt").read_text().strip()
    run = folder / "parts"
    pictures = run / "pictures"
    pictures.mkdir(parents=True, exist_ok=True)
    spec_file = folder / "spec.json"
    spec_file.write_text(json.dumps(spec, indent=1))
    local("prop_parts.py", "check", run, take, spec_file, "--outfit", outfit)  # refused here, before any machine
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
    local("prop_parts.py", "questions", run, take, spec_file, "--outfit", outfit)
    local("prop_parts.py", "regions", run, take, spec_file, "--outfit", outfit)
    cloud("judge.py", run / "questions" / "questions.json", run / "answers")
    local("prop_parts.py", "parts", run, take, spec_file, "--outfit", outfit)
    return json.loads((run / take / "parts.json").read_text())


def build(spec, outfit, who, held, dry_run):
    """The rig fitted into the kept take (prop_rig.py, here) and its far body (prop_far.py, here), then the person built
    on a characters machine
    (prop_chain.py build): <candidate>/out/. The pictures are the route body's, made after the route."""
    folder = folder_of(spec, outfit)
    take = (folder / "take.txt").read_text().strip()
    rig_file = CANDIDATES / spec["name"] / "rig.npz"
    parts_file = folder / "parts" / take / "parts.npz"
    local("prop_rig.py", PIXAL / f"{take}-final.glb", rig_file, folder / "fit", "--size",
          spec.get("look", {}).get("scale", 1.0), "--parts", parts_file, "--faces", NEAR_FACES)
    shelled(spec, outfit, who, held, dry_run)
    local("prop_far.py", folder / "fit" / "rig.npz", parts_file, folder / "fit" / "far.npz")
    local("prop_prints.py", take, folder / "fit" / "rig.npz", parts_file, folder / "fit" / "prints.npz")
    make = make_place(folder, "build")
    machine_spec = dict(spec, name=f"{spec['name']}-{outfit}-build", person=spec["name"], outfit=outfit)
    make_folder(make, machine_spec, ("build",),
                {"fit": folder / "fit" / "rig.npz", "mean": rig_file, "parts": parts_file,
                 "far": folder / "fit" / "far.npz", "prints": folder / "fit" / "prints.npz"})
    on_characters(make, who, held, dry_run)
    if not dry_run:
        if (folder / "out").exists():
            shutil.rmtree(folder / "out")
        shutil.copytree(make / "out", folder / "out")
    return json.loads((folder / "fit" / "rig.json").read_text())["matched_share"]


def identity(spec, outfit, who, held, dry_run):
    """The body under the clothes read off the kept take's close-up by SAM 3D Body (prop_chain.py identity, on a
    characters machine): <candidate>/fit/identity.npz, which the people route's base reads (route_base.py). The
    A-pose picture it was read from before is lost (2026-10-19); the close-up is the person front on in the rig's
    A-pose."""
    folder = folder_of(spec, outfit)
    take = (folder / "take.txt").read_text().strip()
    make = make_place(folder, "identity")
    make_folder(make, dict(spec, name=f"{spec['name']}-{outfit}-identity", person=spec["name"]), ("identity",),
                {"closeup": PIXAL / f"{take}.svviews" / "input.png"})
    on_characters(make, who, held, dry_run)
    if dry_run:
        return None
    (folder / "fit").mkdir(exist_ok=True)
    shutil.copy2(make / "out" / "identity.npz", folder / "fit" / "identity.npz")
    return str(folder / "fit" / "identity.npz")


def shelled(spec, outfit, who, held, dry_run):
    """The look bound to SOMA-X's body fitted to its outside (prop_shell.py, owner 2026-10-12): the fit on a characters
    machine, the binding here; <candidate>/fit/rig.npz takes the body's weights (the RSWT ones kept in it),
    fit/shell.npz and fit/shell.json the body and its offsets."""
    folder = folder_of(spec, outfit)
    make = make_place(folder, "shell")
    make_folder(make, dict(spec, name=f"{spec['name']}-{outfit}-shell", person=spec["name"]), ("shell",),
                {"fit": folder / "fit" / "rig.npz"})
    on_characters(make, who, held, dry_run)
    if dry_run:
        return None
    shutil.copy2(make / "out" / "shell.npz", folder / "fit" / "shell.npz")
    local("prop_shell.py", "bind", folder / "fit" / "rig.npz", folder / "fit" / "shell.npz", folder / "fit" / "rig.npz",
          folder / "fit" / "shell.json")
    return json.loads((folder / "fit" / "shell.json").read_text())


def route(spec, outfit, who, held, dry_run):
    """The people route on the built person (owner, 2026-10-18; prop_chain.py identity then route, on a characters
    machine): SAM 3D Body's read of the take's close-up (<candidate>/fit/identity.npz), and the body rebuilt on
    SOMA-X's base under the look, its garments bound by limb, its correctives as morph targets
    (<candidate>/route/<name>.glb, its record, usd/ and checks/). Replaces the garment settle (#26)."""
    folder = folder_of(spec, outfit)
    take = (folder / "take.txt").read_text().strip()
    make = make_place(folder, "route")
    make_folder(make, dict(spec, name=f"{spec['name']}-{outfit}-route", person=spec["name"]), ("identity", "route"),
                {"closeup": PIXAL / f"{take}.svviews" / "input.png", "fit": folder / "fit" / "rig.npz",
                 "shell": folder / "fit" / "shell.json", "body": folder / "out" / f"{spec['name']}.glb"})
    on_characters(make, who, held, dry_run)
    if dry_run:
        return None
    shutil.copy2(make / "out" / "identity.npz", folder / "fit" / "identity.npz")
    if (folder / "route").exists():
        shutil.rmtree(folder / "route")
    shutil.copytree(make / "out" / "route", folder / "route")
    return json.loads((folder / "route" / f"{spec['name']}.json").read_text())


def clips_rig(clips, out, who, dry_run):
    """The people's Kimodo clips (`clips`, by name, made with clips.CLIP_SEED) and SOMA-X's rig with them
    (prop_skeleton.py), on one rented characters machine (prop_chain.py clips then rig): out/rig.npz and out/motions/
    (each clip's npz and record). The rig is the mean body's, every look's (prop_rig.py fits it into each)."""
    make = CANDIDATES / "people-clips" / "people-clips-make"
    make_folder(make, {"name": "people-clips", "approved": "the people line's batch (#26)", "clips": list(clips)},
                ("clips", "rig"), {})
    on_characters(make, who, None, dry_run)
    if dry_run:
        return None
    shutil.copy2(make / "out" / "rig.npz", out / "rig.npz")
    shutil.copytree(make / "out" / "motions", out / "motions")
    shutil.copy2(make / "out" / "make.json", out / "make.json")
    return json.loads((out / "make.json").read_text())


CHECKS_TABLE = pathlib.Path.home() / ".farm-factory-props/score-coordinator/prop-people"
# The reviewer's count of skin and hard parts through cloth (2026-10-10), in the repo with its depth beyond the margin.
BODYCLOTH = HERE / "bodycloth.py"
RIGID_MOST = 1.2
SHIPPED_TRIANGLES = 29849
LEAN_MOST_CM = 1.5
# The shipped bodies' outfit nodes by the prop route's outfit names; each is measured alone.
SHIPPED_OUTFIT = {"space": "suit"}
FEET_MIRROR_CM = 3.0


def materials_line(parts):
    """The parts' surface shares summed by material, largest first, as one line."""
    shares = {}
    for part in parts["parts"]:
        shares[part["material"]] = shares.get(part["material"], 0.0) + part["share"]
    return ", ".join(f"{name} {share:.1%}" for name, share in sorted(shares.items(), key=lambda item: -item[1]))


def table_rows(spec, outfit, folder, take):
    """The checks' rows: (check, measure, value, gate, verdict)."""
    rig = json.loads((folder / "fit" / "rig.json").read_text())
    joined = json.loads((folder / "route" / "checks" / f"{spec['name']}.json").read_text())["verdict"]
    poked =json.loads((folder / "checks" / "pokes.json").read_text())
    outlined = json.loads((folder / "checks" / "outline.json").read_text())
    parts = json.loads((folder / "parts" / take / "parts.json").read_text())
    rows = [("rig", "limbs apart (crotch, armpit found)", f"crotch {rig['fit']['crotch']:.3f} m, armpit "
             f"{rig['fit']['armpit']:.3f} m", "found", "pass"),
            ("rig", "mesh vertices matched by RSWT", f"{rig['matched_share']:.1%} (rest inpainted)", "record", "-"),
            level_row(rig), feet_row(rig),
            ("parts", "GeoSAM2 parts by material, share of the surface", materials_line(parts), "record", "-")]
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
    rows.append(("pokes.py", "tuck outside the person's surface, worst frame", f"{worst:.1f} mm ({over} frames over)",
                 f"<= {5.0} mm every frame", "pass" if poked["verdict"]["tucks"] else "FAIL"))
    crossing = max(clip["most_crossings"] for clip in poked["clips"].values())
    reference = folder / "checks" / "pokes_shipped.json"
    if reference.exists():
        shipped = json.loads(reference.read_text())
        shipped_worst = max(clip["most_crossings"] for clip in shipped["clips"].values())
        rows.append(("pokes.py", "cloth through cloth (crossings), rest / worst frame; shipped body's",
                     f"{poked['rest_crossings']} / {crossing}; shipped {shipped['rest_crossings']} / {shipped_worst}",
                     "no clip above the shipped body's", "pass" if poked["verdict"]["cloth_through_cloth"] else "FAIL"))
    else:
        rows.append(("pokes.py", "cloth through cloth (crossings), rest / worst frame; no shipped body wears it",
                     f"{poked['rest_crossings']} / {crossing}", "no clip above its own rest",
                     "pass" if poked["verdict"]["cloth_through_cloth"] else "FAIL"))
    stretched = max(clip["rigid_stretch"] for clip in poked["clips"].values())
    rows.append(("pokes.py", "hard parts' edges at their longest against the bind, worst frame", f"{stretched:.3f}x",
                 f"<= {RIGID_MOST}x", "pass" if poked["verdict"]["rigid"] else "FAIL"))
    triangles = json.loads((folder / "out" / f"{spec['name']}.json").read_text())["levels"][outfit]["triangles"]
    rows.append(("build", "outfit triangles (tucks and prints in)", f"{triangles:,}", f"<= {SHIPPED_TRIANGLES:,}",
                 "pass" if triangles <= SHIPPED_TRIANGLES else "FAIL"))
    rows += bodycloth_rows(folder)
    routed = json.loads((folder / "route" / f"{spec['name']}.json").read_text())
    rows.append(("route_build.py", "web edges cut / closings / corrective shapes (energy kept) / face",
                 f"{routed['web_edges']} / {routed['closings']} / {routed['corrective_shapes']} "
                 f"({routed['corrective_energy_kept']}) / {routed['head']['face']}", "record", "-"))
    rows.append(("outline.py", "A-pose IoU against the cut-out, finished take / built",
                 f"{outlined['iou_finished']} / {outlined['iou_built']} (drop {outlined['iou_drop']})",
                 "drop <= 0.01, bands <= 1 %", "pass" if outlined["pass"] else "FAIL"))
    rows.append(("outline.py", "the finished take's own drop against the raw Pixal3D model",
                 f"{outlined['iou_raw']} / {outlined['iou_finished']} (drop {outlined['finish_drop']})", "record",
                 "-"))
    return rows


def level_row(rig):
    """The head joint over the hips joint across the body at the bind (the review found 8.7 cm before levelling)."""
    lean = (rig["joints"]["Head"][0] - rig["joints"]["Hips"][0]) * 100
    return ("rig", "head joint over the hips joint, across, at the bind", f"{lean:+.1f} cm", "within 1.5 cm",
            "pass" if abs(lean) <= LEAN_MOST_CM else "FAIL")


def feet_row(rig):
    """Each foot joint across from the hips joint at the bind (the review found +27.8 and -3.2 cm before levelling)."""
    left, right = ((rig["joints"][side + "Foot"][0] - rig["joints"]["Hips"][0]) * 100 for side in ("Left", "Right"))
    return ("rig", "feet across from the hips at the bind, left / right", f"{left:+.1f} / {right:+.1f} cm",
            "mirror within 3 cm", "pass" if abs(left + right) <= FEET_MIRROR_CM else "FAIL")


def bodycloth_rows(folder):
    """The reviewer's skin-and-hard-through-cloth count (BODYCLOTH): as the engine draws the body
    (bodycloth_shaped.py, the corrective shapes in) and as the reviewer's reader takes it (without them)."""
    rows = []
    for name, how in (("bodycloth.json", "with the corrective shapes"), ("bodycloth_plain.json", "without them")):
        if not (folder / "checks" / name).exists():
            rows.append(("bodycloth.py", f"skin and hard edges through cloth, {how}", "not finished", "record",
                         "the count did not finish (see the report)"))
            continue
        found = json.loads((folder / "checks" / name).read_text())
        clips = list(found["clips"].values())
        for kind in ("skin", "hard"):
            worst = max(clip[kind]["worst"] for clip in clips)
            frames = sum(clip[kind]["frames_with_any"] for clip in clips)
            total = sum(clip["frames"] for clip in clips)
            rows.append(("bodycloth.py", f"{kind} edges through cloth, {how}: bind / worst frame / frames with any",
                         f"{found['bind'][kind]} / {worst} / {frames} of {total}", "record", "-"))
    return rows


def tucks_inputs(spec, folder, take):
    """The hash of what a look's tucks are made from: its take, its spec, its parts and the maker's and the people
    tools' code (the rig, the shell's binding, the build, the route, the tucks and their measure; their tests left
    out): a failed tucks record on the same hash predicts the same failure (#21)."""
    digest = hashlib.sha256(json.dumps([take, spec], sort_keys=True).encode())
    code = sorted(path for path in (*HERE.glob("*.py"), *(HERE.parent / "people").glob("*.py"))
                  if not path.name.endswith("_test.py"))
    for path in (folder / "parts" / take / "parts.npz", *code):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def tucks_record(spec, outfit):
    """After the paid checks, the look's tucks as its route body's pokes.json measured them: when every clip had a frame
    with a tuck over the gate (frames_tuck_over), <candidate>/checks/failed_tucks.json with the worst and the hash of
    its inputs, the record; else any old record removed, None."""
    folder = folder_of(spec, outfit)
    clips = json.loads((folder / "checks" / "pokes.json").read_text())["clips"]
    written = folder / "checks" / "failed_tucks.json"
    if not clips or not all(clip["frames_tuck_over"] > 0 for clip in clips.values()):
        written.unlink(missing_ok=True)
        return None
    take = (folder / "take.txt").read_text().strip()
    record = {"worst_tuck_out_mm": max(clip["worst_tuck_out_mm"] for clip in clips.values()), "clips": len(clips),
              "inputs": tucks_inputs(spec, folder, take)}
    written.write_text(json.dumps(record, indent=1))
    return record


def predicted_tucks(spec, outfit):
    """The look's failed tucks record when it stands on the same inputs (tucks_inputs): a predicted gap, nothing to
    buy (#21); None when there is none or anything it was made from has changed."""
    folder = folder_of(spec, outfit)
    written = folder / "checks" / "failed_tucks.json"
    if not written.exists():
        return None
    record = json.loads(written.read_text())
    take = (folder / "take.txt").read_text().strip()
    return record if record.get("inputs") == tucks_inputs(spec, folder, take) else None


CHECK_CLASSES = "cpu-16c-64gb,cpu-32c-64gb"  # four checks at once; the cheapest machine first
CHECK_MINUTES = 90


COUNT_SHARES = 6


def counts_by_clips(body, checked):
    """The two body-through-cloth counts (with the corrective shapes and without), each over COUNT_SHARES shares of
    the body's clips side by side (a whole count took about an hour on one core): {name: command}. The outfit counted
    is the body's own skinned node, not its far body: the route names it `work` whatever the look's outfit
    (route_build.py NODE)."""
    sys.path.insert(0, str(HERE.parent / "people"))
    import joins
    document, _ = joins.read_glb(body)
    outfit, = [node["name"] for node in document["nodes"] if "mesh" in node and "skin" in node
               and node.get("name") != "far"]
    clips = [animation["name"] for animation in document.get("animations", [])]
    found = {}
    for share in range(COUNT_SHARES):
        mine = [str(clip) for clip in clips[share::COUNT_SHARES]] or ["none"]
        found[f"bodycloth plain {share}"] = [str(HERE / "bodycloth.py"), str(body), "--outfit", outfit, "--out",
                                             str(checked / f"bodycloth_plain.{share}.json"), "--clips", *mine]
        found[f"bodycloth {share}"] = [str(HERE / "bodycloth_shaped.py"), str(BODYCLOTH), str(body), "--outfit",
                                       outfit, "--out", str(checked / f"bodycloth.{share}.json"), "--clips", *mine]
    return found


def shipped_reference(spec, outfit):
    """The shipped body and the node of its outfit a look's cloth is held to: the outfit by the look's own name, as the
    kits name theirs (plain_uniform_olive for uniform-olive), or the spec's shipped_outfit (the driver's and the
    guard's "person"); (None, None) where no shipped body wears it (the 2026-10-13 batch asked the driver's body for
    "driver-suit" and failed)."""
    sys.path.insert(0, str(HERE.parent / "people"))
    import joins
    shipped = MOTION_HOME / "work" / "bodies" / f"{spec.get('shipped_body', spec['name'])}.glb"
    if not shipped.exists():
        return None, None
    worn = {node.get("name") for node in joins.read_glb(shipped)[0]["nodes"] if "mesh" in node}
    for wanted in (SHIPPED_OUTFIT.get(outfit, outfit), "plain_" + outfit.replace("-", "_"), spec.get("shipped_outfit")):
        if wanted in worn:
            return shipped, wanted
    return None, None


def checks_cloud(spec, outfit, who, held, dry_run):
    """`checks`' records made side by side on a rented processor machine (inside/body_checks.py through
    blender_cloud.py): the shipped body's pokes first where they are missing, then pokes, the outline and the two
    body-through-cloth counts at once; then the table."""
    folder = folder_of(spec, outfit)
    take = (folder / "take.txt").read_text().strip()
    checked = folder / "checks"
    checked.mkdir(exist_ok=True)
    body = folder / "route" / f"{spec['name']}.glb"
    shipped, shipped_outfit = shipped_reference(spec, outfit)
    python = lambda script, *arguments: [str(HERE / script), *map(str, arguments)]  # noqa: E731
    first = {} if shipped is None or (checked / "pokes_shipped.json").exists() else {
        "pokes shipped": python("pokes.py", shipped, "--out", checked / "pokes_shipped.json", "--outfit",
                                shipped_outfit)}
    against = [] if shipped is None else ["--against", checked / "pokes_shipped.json"]
    (checked / "cloth_reference.txt").write_text(
        f"the shipped {shipped.stem}'s {shipped_outfit}" if shipped else "the look's own rest crossings (no shipped body "
        "wears this outfit)")
    listing = {"repo": str(REPO), "props home": str(PIXAL.parents[1]), "first": first, "checks": {
        "pokes": python("pokes.py", body, "--out", checked / "pokes.json", *against),
        "outline": python("outline.py", take, folder / "fit" / "rig.npz", body, "--out", checked / "outline.json"),
        **counts_by_clips(body, checked)}, "then": {
        name: python("bodycloth.py", "merge", checked / f"{name}.json",
                     *(checked / f"{name}.{share}.json" for share in range(COUNT_SHARES)))
        for name in ("bodycloth", "bodycloth_plain")}}
    place = make_place(folder, "checks")
    place.mkdir(exist_ok=True)
    (place / "listing.json").write_text(json.dumps(listing, indent=1))
    takes = [PIXAL / f"{take}.glb", PIXAL / f"{take}-final.glb", PIXAL / f"{take}.svviews",
             *PIXAL.glob(f"{take}-[0-9]*.glb")]
    job = place / "job.json"
    job.write_text(json.dumps({
        "script": "tools/characters/maker/inside/body_checks.py", "args": [str(place / "listing.json")],
        "inputs": [str(path) for path in (place / "listing.json", body, folder / "fit" / "rig.npz", *([shipped] if shipped
                                                                                                     else []), checked,
                                          REPO / "tools/characters", REPO / "tools/props", *takes)],
        "outputs": [str(checked)], "minutes": CHECK_MINUTES}, indent=1))
    if dry_run:
        return None
    cloud("blender_cloud.py", job, "--who", who, "--classes", CHECK_CLASSES)
    return write_table(spec, outfit, folder, take)


def write_table(spec, outfit, folder, take):
    """The checks' table from their records: <candidate>/checks/checks.txt and the coordinator's copy."""
    rows = table_rows(spec, outfit, folder, take)
    widths = [max(len(str(row[column])) for row in rows) for column in range(4)]
    lines = [f"PROP PEOPLE CHECKS: {spec['name']} ({outfit}), take {take}, "
             f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC", ""]
    lines += ["  ".join(str(value).ljust(width) for value, width in zip(row[:4], widths)) + "  " + row[4]
              for row in rows]
    lines += ["", "The face is a print cut from the close-up (prop_prints.py), the overseer's decision of 2026-10-10 in the "
              "owner's absence; the owner may veto it, and the head is then the skin colour only."]
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
    parser.add_argument("--experimental", action="store_true", help="the prop route is experimental: required")
    options = parser.parse_args()
    if not options.experimental:
        raise SystemExit(f"{options.spec}: the prop route is experimental, so only with --experimental")
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


STAGE_WORK = {"parts": parts, "identity": identity, "build": build, "route": route, "checks-cloud": checks_cloud}


if __name__ == "__main__":
    main()
