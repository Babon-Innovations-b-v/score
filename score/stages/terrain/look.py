"""What `effects-look` and `physics-trial` render a place's stage with (the retired terrain look's, #27): the tree of a
place's stage beside its neighbours, the jobs run on rented cards through tools/props/cloud/blender_cloud.py inside
the runner's clearance, and a view's rendered picture found back.
"""
import json
import pathlib
import shutil
import subprocess

from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
PROPS_PYTHON = PROPS_HOME / "env/bin/python"
VIEWS = "demo/world1-r4/views"
FRAME = "-000"
CARDS = "gpu-24gb"  # one class, the L4 Blender was timed on; never a fallback to a larger card (#21, #27)
WHO = "score terrain look"


def neighbours(place):
    """The other places a place's stage references (its scene record's `places`), by their stage's name; none for a
    place with no scene record in the repository (one the game never had: the ship's rooms, a scene added in the app)."""
    path = REPO / f"data/scene/{place}.json"
    record = json.loads(path.read_text()) if path.is_file() else {}
    return sorted({entry["stage"] for entry in record.get("places", [])})


def tree(out, state, place, stage_folder, inputs):
    """A folder holding the place's stage (`stage_folder`, copied) and its neighbours (hard links to the seeds)."""
    folder = out / "stages" / state
    folder.mkdir(parents=True)
    shutil.copytree(stage_folder, folder / place)
    subprocess.run(["chmod", "-R", "u+w", str(folder / place)], check=True)
    for name in neighbours(place):
        subprocess.run(["cp", "-al", str(inputs[f"neighbour {name}"]), str(folder / name)], check=True)
    return folder


def render(jobs, folder):
    """Run the jobs on rented cards (the runner's clearance names them), spread over as many machines as suit."""
    paths = []
    for number, job in enumerate(jobs):
        path = folder / f"job-{number}.json"
        path.write_text(json.dumps(job, indent=1))
        paths.append(str(path))
    subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/props/cloud/blender_cloud.py"), *paths, "--who", WHO,
                    "--classes", CARDS], check=True, cwd=REPO)


def rendered(out, state, name, kind):
    """A view's rendered picture of one kind (look, mask) in one state, or None."""
    return next(iter(sorted(out.glob(f"{state}/*/{name}-{kind}.png"))), None)
