"""Drape one garment on one body: GarmentCode's pattern and box mesh (`garment.py`, in a GarmentCode environment),
then a cloth simulator, into a drape folder `people/drape.py` reads as it read GarmentCode's Warp drapes. The simulator
is Newton (`newton_drape.py`, Apache-2.0, the default: it runs in the newton environment, on a card) or Blender's
cloth (`cloth_drape.py`, on this machine with --blender or on a rented one through tools/props/cloud/blender_cloud.py).

On the maker's own rented box (characters_setup.sh: GarmentCode, the garment, newton and Blender environments):
    GARMENTCODE=/root/garmentcode GARMENTCODE_PYTHON=/root/envs/garment/bin/python python3 \
        tools/characters/maker/drape_garment.py <body folder> work_suit <drape folder> --kind work \
        --reference mean_female [--simulator newton|blender] [--blender /root/blender/blender] [key=value ...]

A kept look redraped 1:1 on its body, its own sized pattern rather than the design sized again:
    ... drape_garment.py <body folder> work_suit <drape folder> --kind work --reference mean_female \
        --pattern ~/.farm-factory-motion/look/<person>/work_drape/work_0_specification.json \
        [--measurements <the body_measurements.yaml the pattern was sized on>]

<design> is a folder of data/characters/garments (design.yaml and cloth.json) or its name; key=value pairs change the
design (GarmentCode's dotted parameter paths; not with --pattern). The drape folder gets <kind>_0_sim.obj
(centimetres, the box mesh's point order), <kind>_0_sim_segmentation.txt, <kind>_0_specification.json, design.yaml (the
design as sized, or the kept pattern's own when it has one) and the simulator's record (newton_cloth.json: the
simulator's name, version and licence and what came out; or blender_cloth.json); the work files (body measurements,
pattern, box mesh) stay in <drape folder>.work/. A maker calls `drape(...)`, with a held `blender_cloud.Machine` when
it drapes several with Blender.

The GarmentCode steps run with GARMENTCODE_PYTHON (default ~/.farm-factory-motion/rnd/garmentcode/venv/bin/python),
Newton with NEWTON_PYTHON (default /root/envs/newton/bin/python): the GarmentCode steps are plain geometry, seconds
long, no model; Newton's drape is about a minute on a card.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "tools/props/cloud"))

GARMENTS = REPO / "data/characters/garments"
GARMENTCODE_PYTHON = pathlib.Path(os.environ.get(
    "GARMENTCODE_PYTHON", pathlib.Path.home() / ".farm-factory-motion/rnd/garmentcode/venv/bin/python"))
NEWTON_PYTHON = pathlib.Path(os.environ.get("NEWTON_PYTHON", "/root/envs/newton/bin/python"))
SIMULATORS = ("newton", "blender")
# About how long one drape runs on a 32-core processor machine, for the cloud runner's estimate.
CLOUD_MINUTES = 20


def design_folder(design):
    """A design by its folder or its name under data/characters/garments."""
    folder = pathlib.Path(design)
    return folder if folder.is_dir() else GARMENTS / design


def garmentcode(*arguments):
    """One step of garment.py in the GarmentCode environment."""
    subprocess.run([str(GARMENTCODE_PYTHON), str(HERE / "garment.py"), *map(str, arguments)], check=True)


def kept_pattern(pattern, work, name, measurements=None):
    """A kept look's own sized pattern (its <name>_specification.json) as the work folder's pattern, with the
    pattern's design.yaml beside it when it has one; `measurements` (the body_measurements.yaml it was sized on)
    replaces the body's measured ones, so the waist and collars are held where they were for it."""
    folder = work / "patterns" / name
    folder.mkdir(parents=True)
    shutil.copy(pattern, folder / f"{name}_specification.json")
    if (pattern.parent / "design.yaml").exists():
        shutil.copy(pattern.parent / "design.yaml", folder / "design.yaml")
    if measurements is not None:
        shutil.copy(measurements, work / "bodies" / "ours.yaml")
        shutil.copy(measurements, folder / "body_measurements.yaml")


def box_mesh(body, design, work, name, reference, overrides, simulator, pattern=None, measurements=None):
    """GarmentCode's body measurements, pattern (the design sized to the body, or the kept `pattern`) and box mesh
    for the body at the design's spacing, and for Blender at its coarse spacing too (<name>_coarse, which
    cloth_drape.py sews first); the box mesh's folder."""
    cloth = json.loads((design / "cloth.json").read_text())
    garmentcode("measure", body, work, reference)
    if (body.parent / "joints.json").exists():  # where the sleeves are checked against (sewing.uncovered)
        shutil.copy(body.parent / "joints.json", work / "bodies" / "joints.json")
    if pattern is None:
        garmentcode("pattern", design, work, name, *(f"{key}={value}" for key, value in overrides.items()))
    else:
        kept_pattern(pattern, work, name, measurements)
    garmentcode("box", work, name, cloth["resolution_scale"])
    if simulator == "blender":
        garmentcode("box", work, name, cloth["coarse_resolution"], f"{name}_coarse")
    return work / "box" / name


def cloth_job(box, work, design, out, name):
    """The job file cloth_drape.py reads."""
    coarse = box.with_name(f"{name}_coarse") / f"{name}_coarse_sewing.npz"
    job = {"sewing": str(box / f"{name}_sewing.npz"), "coarse": str(coarse),
           "box_mesh": str(box / f"{name}_boxmesh.obj"),
           "body": str(work / "bodies" / "ours.obj"),
           "joints": str(work / "bodies" / "joints.json") if (work / "bodies" / "joints.json").exists() else None,
           "cloth": json.loads((design / "cloth.json").read_text()),
           "out": str(out), "name": name}
    path = work / f"{name}_cloth_job.json"
    path.write_text(json.dumps(job, indent=1))
    return path


def newton_job(box, work, design, out, name):
    """The job file newton_drape.py reads."""
    joints = work / "bodies" / "joints.json"
    job = {"sewing": str(box / f"{name}_sewing.npz"), "box_mesh": str(box / f"{name}_boxmesh.obj"),
           "labels": str(box / f"{name}_vertex_labels.yaml"), "measurements": str(work / "bodies" / "ours.yaml"),
           "body": str(work / "bodies" / "ours.obj"), "joints": str(joints) if joints.exists() else None,
           "cloth": json.loads((design / "cloth.json").read_text()), "out": str(out), "name": name}
    path = work / f"{name}_newton_job.json"
    path.write_text(json.dumps(job, indent=1))
    return path


def run_newton(job):
    """newton_drape.py in the newton environment on this machine (a card box)."""
    if not NEWTON_PYTHON.exists():
        raise SystemExit(f"no newton environment at {NEWTON_PYTHON} (set NEWTON_PYTHON): Newton drapes on a card "
                         "box set up by tools/props/cloud/characters_setup.sh, or pass --simulator blender")
    subprocess.run([str(NEWTON_PYTHON), str(HERE / "newton_drape.py"), str(job)], check=True)


def run_cloth_here(job, blender):
    """cloth_drape.py with a Blender on this machine (the maker's own rented box)."""
    subprocess.run([str(blender), "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
                    str(HERE / "cloth_drape.py"), "--", str(job)], check=True)


def run_cloth(job, work, out, machine, classes, who):
    """cloth_drape.py on a rented machine: the held one if given, else one rented for this drape."""
    import blender_cloud
    script = HERE / "cloth_drape.py"
    inputs, outputs = [job, work / "box", work / "bodies"], [out]
    if machine is not None:
        machine.run(script, [job], inputs, outputs, CLOUD_MINUTES)
    else:
        blender_cloud.run_elsewhere(script, [job], inputs, outputs, classes or blender_cloud.DEFAULT_CLASSES, who,
                                    CLOUD_MINUTES)


def finish(box, work, out, name):
    """What the drape folder needs beside the cloth: GarmentCode's segmentation and pattern, and the sized design."""
    for suffix in ("_sim_segmentation.txt", "_specification.json"):
        shutil.copy(box / f"{name}{suffix}", out / f"{name}{suffix}")
    if (work / "patterns" / name / "design.yaml").exists():
        shutil.copy(work / "patterns" / name / "design.yaml", out / "design.yaml")
    if not (out / f"{name}_sim.obj").exists():
        raise RuntimeError(f"the cloth run wrote no {out / f'{name}_sim.obj'}")


def drape(body, design, out, kind, reference="mean_male", overrides=None, machine=None, classes=None,
          who="characters maker", blender=None, simulator="newton", pattern=None, measurements=None, work=None):
    """Drape the design on the body into the folder `out`, its cloth named <kind>_0 as GarmentCode's were (or as the
    kept pattern is named); returns the folder; the work files go to `work` (default <out>.work beside it). `body` is a
    bind-pose body file (points in metres, faces, joint_names, weights) or a folder holding it as ours.npz
    (tools/characters/maker/export_body.py's); `reference` is GarmentCode's body its measurements are carried from
    (mean_female for a woman's build); `pattern` a kept look's <tag>_specification.json to drape as it is, instead of
    the design sized to the body, with `measurements` the body_measurements.yaml it was sized on (else the body is
    measured again). `simulator` is "newton" (here, in NEWTON_PYTHON) or "blender": with `blender` (a Blender binary) on
    this machine, else on a rented one (`machine`, held by the caller, or one rented for this drape)."""
    if simulator not in SIMULATORS:
        raise ValueError(f"simulator {simulator!r} is not one of {SIMULATORS}")
    if pattern is not None and overrides:
        raise ValueError("a kept pattern is draped as it is: no design changes with it")
    if measurements is not None and pattern is None:
        raise ValueError("measurements go with a kept pattern")
    body = pathlib.Path(body).resolve()
    body = body / "ours.npz" if body.is_dir() else body
    out = pathlib.Path(out).resolve()
    work = pathlib.Path(work).resolve() if work else out.with_name(out.name + ".work")
    name = pathlib.Path(pattern).name[:-len("_specification.json")] if pattern else f"{kind}_0"
    for folder in (out, work):
        if folder.exists():
            shutil.rmtree(folder)
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    design = design_folder(design)
    box = box_mesh(body, design, work, name, reference, overrides or {}, simulator,
                   pathlib.Path(pattern).resolve() if pattern else None,
                   pathlib.Path(measurements).resolve() if measurements else None)
    if simulator == "newton":
        run_newton(newton_job(box, work, design, out, name))
    elif blender:
        run_cloth_here(cloth_job(box, work, design, out, name), blender)
    else:
        run_cloth(cloth_job(box, work, design, out, name), work, out, machine, classes, who)
    finish(box, work, out, name)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("body", type=pathlib.Path)
    parser.add_argument("design")
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("overrides", nargs="*", help="design changes, key=value")
    parser.add_argument("--kind", required=True, help="the cloth's name in the folder: work, space, jacket, ...")
    parser.add_argument("--reference", default="mean_male", choices=("mean_male", "mean_female"))
    parser.add_argument("--who", default="characters maker drape")
    parser.add_argument("--classes", help="capability classes in the order to try, comma separated")
    parser.add_argument("--simulator", choices=SIMULATORS, default="newton")
    parser.add_argument("--pattern", type=pathlib.Path,
                        help="a kept look's <tag>_specification.json, draped as it is (no sizing, no changes)")
    parser.add_argument("--measurements", type=pathlib.Path,
                        help="with --pattern: the body_measurements.yaml the pattern was sized on")
    parser.add_argument("--blender", type=pathlib.Path,
                        help="with --simulator blender: run the cloth with this Blender here, no rented machine")
    options = parser.parse_args()
    overrides = dict(argument.split("=", 1) for argument in options.overrides)
    drape(options.body, options.design, options.out, options.kind, options.reference, overrides,
          classes=options.classes.split(",") if options.classes else None, who=options.who, blender=options.blender,
          simulator=options.simulator, pattern=options.pattern, measurements=options.measurements)


if __name__ == "__main__":
    main()
