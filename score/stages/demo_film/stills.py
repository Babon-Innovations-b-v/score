"""demo-stills: single pictures of a place's final stage for the paper's demos (K3's tool board, K5's lit Earth and
swept room, K6's lift-off and rover strips), from named cameras of the place's scene record at given seconds of the
stage's time, once the place passes complete; one place node, paid (one Blender job on the cheapest card through
tools/props/cloud/blender_cloud.py, drawn by tools/blender/inside/usd_views.py, look only).

    data/definitions/demo_stills/<place>.json   {"why", "stills": [{"name", "camera", "seconds"}]}

The camera is read from the record the stage was assembled from (its scene.json where it carries cameras, else
data/scene/<place>.json), never placed by hand. The output: <name>.png for each still and stills.json (each still's
view and frame). The gate `drawn`: every still came back and none is blank (its pixels' spread at least SPREAD_LEAST).
"""
import json
import pathlib
import shutil
import subprocess

from PIL import Image, ImageStat

from score import checks, contracts
import score.stages.demo_film as demo_film

REPO = pathlib.Path(__file__).resolve().parents[3]
STILLS = REPO / "data/definitions/demo_stills"
SIZE = (1920, 1080)
# One L4 job: set-up and about 5 min a still (the light overlay's measure, shortlist), at EUR 0.013 a minute.
EUROS_A_STILL = 0.07
SETUP_EUROS = 0.2
MINUTES_A_STILL = 5
SPREAD_LEAST = 4.0


def record_path(place):
    return STILLS / f"{place}.json"


def applies(place):
    return record_path(place).exists()


def files(place):
    """The place's stills record and the renderer (its cameras are its own stage's record: the seed records were
    retired, 2026-10-21)."""
    return {"stills": "{data}/definitions/demo_stills/" + place + ".json",
            "renderer": "{repo}/tools/blender/inside/usd_views.py"}


def euros(place=None):
    """The estimate: set-up and each still of the largest record (a row's estimate is one number)."""
    counts = [len(json.loads(path.read_text())["stills"]) for path in STILLS.glob("*.json")] or [1]
    return round(SETUP_EUROS + EUROS_A_STILL * max(counts), 2)


def cameras(stage_folder, scene_file):
    """{name: view} of the record the stage was assembled from (module docstring)."""
    kept = stage_folder / "scene.json"
    own = json.loads(kept.read_text()) if kept.exists() else {}
    record = own if own.get("views") or not scene_file else json.loads(pathlib.Path(scene_file).read_text())
    return {view["name"]: view for view in record.get("views", [])}


def still_views(stills, found, rate):
    """Each still as usd_views.py's view: its camera's eye, aim and fov at its frame of the stage's time, look only."""
    missing = [still["camera"] for still in stills if still["camera"] not in found]
    if missing:
        raise RuntimeError(f"the stage's record has no camera {', '.join(missing)}")
    return [{"name": still["name"], "eye": found[still["camera"]]["eye"], "aim": found[still["camera"]]["aim"],
             "up": [0.0, 1.0, 0.0], "fov": found[still["camera"]].get("fov", 75.0),
             "frame": round(float(still["seconds"]) * rate), "look_only": True} for still in stills]


def make(inputs, out, seed, params):
    """Every still of the record, rendered in one Blender job from the place's final stage."""
    demo, _ = demo_film.film_tools()
    stage_folder = demo_film.final_stage(inputs)
    place = demo_film.place_of(stage_folder)
    work = out / ".work"
    shutil.copytree(stage_folder, work / place)
    subprocess.run(["chmod", "-R", "u+w", str(work)], check=True)
    stage = work / place / f"{place}.usda"
    stills = json.loads(pathlib.Path(inputs["stills"]).read_text())["stills"]
    views = still_views(stills, cameras(stage_folder, inputs.get("scene")), demo.renders.stage_rate(stage))
    spec = work / "views.json"
    spec.write_text(json.dumps({"size": list(SIZE), "views": views}, indent=1))
    job = work / "job.json"
    job.write_text(json.dumps({"script": "tools/blender/inside/usd_views.py",
                               "args": [str(stage), str(spec), str(work / "frames")],
                               "inputs": [str(work / place), str(spec)], "outputs": [str(work / "frames")],
                               "minutes": 10 + MINUTES_A_STILL * len(views)}, indent=1))
    demo_film.render([job], out)
    for view in views:
        shutil.copy(work / "frames" / f"{view['name']}-look.png", out / f"{view['name']}.png")
    (out / "stills.json").write_text(json.dumps({"size": list(SIZE), "stills": views}, indent=1))
    shutil.rmtree(work)


def output_faults(folder):
    return [] if (pathlib.Path(folder) / "stills.json").exists() else ["no stills.json"]


CONTRACT = contracts.Contract("demo-stills", 1, output_faults)


def still_faults(name, folder):
    path = pathlib.Path(folder) / f"{name}.png"
    if not path.exists():
        return [f"{name}: no picture came back"]
    spread = max(ImageStat.Stat(Image.open(path).convert("RGB")).stddev)
    return [f"{name}: blank (pixel spread {spread:.1f})"] if spread < SPREAD_LEAST else []


def judge_drawn(output, inputs, evidence):
    """Every still came back drawn (module docstring)."""
    asked = json.loads((pathlib.Path(output) / "stills.json").read_text())["stills"]
    faults = [fault for view in asked for fault in still_faults(view["name"], output)]
    reason = "; ".join(faults[:3]) if faults else f"all {len(asked)} stills drawn"
    return checks.Verdict("drawn", checks.FAIL if faults else checks.PASS, reason,
                          {"stills": len(asked), "faults": len(faults)}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("drawn", judge_drawn),)
