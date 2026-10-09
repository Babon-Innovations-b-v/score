"""Drape one garment on one body: GarmentCode's pattern and box mesh (`garment.py`, in a GarmentCode environment),
then Blender's cloth on a rented machine (`cloth_drape.py` through tools/props/cloud/blender_cloud.py), into a drape
folder `people/drape.py` reads as it read GarmentCode's Warp drapes.

    ~/.farm-factory-props/env/bin/python tools/characters/maker/drape_garment.py <body.npz> <design> <drape folder> \
        --kind work [--reference mean_female] [--who <session>] [--classes cpu-32c-128gb,...] [key=value ...]

On the maker's own rented box, everything there and no runner (GarmentCode and the garment environment as the
characters runner sets them up):
    GARMENTCODE=/root/garmentcode GARMENTCODE_PYTHON=/root/envs/garment/bin/python python3 \
        tools/characters/maker/drape_garment.py <body folder> work_suit <drape folder> --kind work \
        --reference mean_female --blender /root/blender/blender

<design> is a folder of data/characters/garments (design.yaml and cloth.json) or its name; key=value pairs change the
design (GarmentCode's dotted parameter paths). The drape folder gets <kind>_0_sim.obj (centimetres, the box mesh's
point order), <kind>_0_sim_segmentation.txt, <kind>_0_specification.json, blender_cloth.json (the cloth settings and
what came out) and design.yaml (the design as sized); the work files (body measurements, pattern, box mesh) stay in
<drape folder>.work/. A maker calls `drape(...)`, with a held `blender_cloud.Machine` when it drapes several.

The GarmentCode steps run with GARMENTCODE_PYTHON (default ~/.farm-factory-motion/rnd/garmentcode/venv/bin/python):
they are plain geometry, seconds long, no model.
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
# About how long one drape runs on a 32-core processor machine, for the cloud runner's estimate.
CLOUD_MINUTES = 20


def design_folder(design):
    """A design by its folder or its name under data/characters/garments."""
    folder = pathlib.Path(design)
    return folder if folder.is_dir() else GARMENTS / design


def garmentcode(*arguments):
    """One step of garment.py in the GarmentCode environment."""
    subprocess.run([str(GARMENTCODE_PYTHON), str(HERE / "garment.py"), *map(str, arguments)], check=True)


def box_mesh(body, design, work, name, reference, overrides):
    """GarmentCode's body measurements, pattern and box mesh for the body, at the design's spacing and at its coarse
    spacing (<name>_coarse, which cloth_drape.py sews first); the box mesh's folder."""
    cloth = json.loads((design / "cloth.json").read_text())
    garmentcode("measure", body, work, reference)
    if (body.parent / "joints.json").exists():  # where the sleeves are checked against (cloth_drape.bare_arm)
        shutil.copy(body.parent / "joints.json", work / "bodies" / "joints.json")
    garmentcode("pattern", design, work, name, *(f"{key}={value}" for key, value in overrides.items()))
    garmentcode("box", work, name, cloth["resolution_scale"])
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
    shutil.copy(work / "patterns" / name / "design.yaml", out / "design.yaml")
    if not (out / f"{name}_sim.obj").exists():
        raise RuntimeError(f"the cloth run wrote no {out / f'{name}_sim.obj'}")


def drape(body, design, out, kind, reference="mean_male", overrides=None, machine=None, classes=None,
          who="characters maker", blender=None):
    """Drape the design on the body into the folder `out`, its cloth named <kind>_0 as GarmentCode's were; returns
    the folder. `body` is a bind-pose body file (points in metres, faces, joint_names, weights) or a folder holding
    it as ours.npz (tools/characters/maker/export_body.py's); `reference` is GarmentCode's body its measurements are
    carried from (mean_female for a woman's build). With `blender` (a Blender binary) the cloth runs on this machine,
    else on a rented one (`machine`, held by the caller, or one rented for this drape)."""
    body = pathlib.Path(body).resolve()
    body = body / "ours.npz" if body.is_dir() else body
    out = pathlib.Path(out).resolve()
    work = out.with_name(out.name + ".work")
    name = f"{kind}_0"
    for folder in (out, work):
        if folder.exists():
            shutil.rmtree(folder)
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    design = design_folder(design)
    box = box_mesh(body, design, work, name, reference, overrides or {})
    job = cloth_job(box, work, design, out, name)
    if blender:
        run_cloth_here(job, blender)
    else:
        run_cloth(job, work, out, machine, classes, who)
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
    parser.add_argument("--blender", type=pathlib.Path, help="run the cloth with this Blender here, no rented machine")
    options = parser.parse_args()
    overrides = dict(argument.split("=", 1) for argument in options.overrides)
    drape(options.body, options.design, options.out, options.kind, options.reference, overrides,
          classes=options.classes.split(",") if options.classes else None, who=options.who, blender=options.blender)


if __name__ == "__main__":
    main()
