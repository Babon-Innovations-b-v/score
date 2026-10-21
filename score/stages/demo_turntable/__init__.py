"""demo-turntables: models that already exist turned round for the paper's demos, one world node, paid (one Blender job
on the cheapest card, tools/props/cloud/blender_cloud.py inside the runner's clearance, drawn by the review page's
model script tools/blender/inside/review_models.py, run by turntable_models.py with its frame widened: Workbench,
studio light, each model framed whole on its own). The first: demo K2, four of the hub comparison's objects, each one's generated model and code build where it has them.

    data/definitions/demo_turntables.json   {"why", "headings" (degrees round the model),
                                             "objects": [{"id", "models": {<what>: [the model file, its side files]}}]}

The output: renders/<id>--<what>--<heading>.png for every model at every heading, shots.json (what was asked) and
renders/shots-report.json (Blender's triangles and size of each). The gate `drawn`: every model came back at every
heading and none is blank (its pixels' spread at least SPREAD_LEAST); a missing or blank one fails by name.
"""
import json
import os
import pathlib
import subprocess

from PIL import Image, ImageStat

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
RECORD = REPO / "data/definitions/demo_turntables.json"
SCRIPT = "score/stages/demo_turntable/turntable_models.py"
DRAWER = "tools/blender/inside/review_models.py"
PROPS_HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", PROPS_HOME / "env/bin/python"))
# Workbench needs a card's OpenGL: one class, the L4; none in stock makes the models gaps, never a larger card (#21).
CLASSES = "gpu-24gb"
SIZE = (1024, 1024)
MINUTES = 15
# One L4 job: set-up and a few minutes of Workbench renders at about EUR 0.013 a minute, rounded up.
EUROS = 0.5
SPREAD_LEAST = 4.0


def record():
    """The world's demo turntables (none when the world has no record)."""
    return json.loads(RECORD.read_text()) if RECORD.exists() else {"headings": [], "objects": []}


def files(place=None):
    """The record and every model's files (the model first, then its buffers and textures)."""
    return {"turntables": "{data}/definitions/demo_turntables.json",
            "model script": "{repo}/" + SCRIPT, "drawer": "{repo}/" + DRAWER,
            **{f"{item['id']} {what} {number}": pattern
               for item in record()["objects"] for what, patterns in item["models"].items()
               for number, pattern in enumerate(patterns)}}


def euros():
    return EUROS


def member_name(item, what, heading):
    return f"{item['id']}--{what}--{heading:03d}"


def shots(turntables, inputs):
    """review_models.py's shots: one group a model and heading, so each model is framed on its own."""
    return {"size": list(SIZE),
            "groups": [{"name": member_name(item, what, heading), "heading": heading,
                        "members": [{"name": member_name(item, what, heading),
                                     "files": [{"path": str(inputs[f"{item['id']} {what} 0"])}]}]}
                       for item in turntables["objects"] for what in item["models"]
                       for heading in turntables["headings"]]}


def make(inputs, out, seed, params):
    """Every model at every heading, rendered in one Blender job on a rented card."""
    turntables = json.loads(pathlib.Path(inputs["turntables"]).read_text())
    renders = out / "renders"
    (out / "shots.json").write_text(json.dumps(shots(turntables, inputs), indent=1))
    job = out / ".job.json"
    job.write_text(json.dumps({"script": SCRIPT, "args": [str(out / "shots.json"), str(renders)],
                               "inputs": [str(out / "shots.json"),
                                          *(str(path) for name, path in inputs.items()
                                            if name not in ("turntables", "model script", "drawer"))],
                               "outputs": [str(renders)], "minutes": MINUTES}, indent=1))
    done = subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/props/cloud/blender_cloud.py"), str(job),
                           "--who", "demo-turntables", "--classes", CLASSES], cwd=REPO, capture_output=True, text=True)
    (out / "turntables.log").write_text(done.stdout[-30000:] + "\n" + done.stderr[-30000:])
    job.unlink()
    if done.returncode:
        raise RuntimeError(f"blender_cloud.py failed: {done.stderr[-2000:]}")


def output_faults(folder):
    return [] if (pathlib.Path(folder) / "shots.json").exists() else ["no shots.json"]


CONTRACT = contracts.Contract("demo-turntables", 1, output_faults)


def picture_faults(name, folder):
    """Why one model's picture at one heading is missing or blank; none when it is drawn."""
    path = pathlib.Path(folder) / "renders" / f"{name}.png"
    if not path.exists():
        return [f"{name}: no picture came back"]
    spread = max(ImageStat.Stat(Image.open(path).convert("RGB")).stddev)
    return [f"{name}: blank (pixel spread {spread:.1f})"] if spread < SPREAD_LEAST else []


def judge_drawn(output, inputs, evidence):
    """Every model came back drawn at every heading (module docstring)."""
    asked = json.loads((pathlib.Path(output) / "shots.json").read_text())["groups"]
    faults = [fault for group in asked for fault in picture_faults(group["name"], output)]
    reason = "; ".join(faults[:3]) if faults else f"all {len(asked)} pictures drawn"
    return checks.Verdict("drawn", checks.FAIL if faults else checks.PASS, reason,
                          {"pictures": len(asked), "faults": len(faults)}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("drawn", judge_drawn),)
