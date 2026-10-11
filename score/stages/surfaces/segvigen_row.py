"""The finish-map method's paid card row, in a module of its own so a change to the free steps does not rent again:
SegviGen (MIT, on TRELLIS.2; tools/props/cloud/meshparts.py, nvdiffrast and RMBG-2.0 never installed) splits each raw
model guided by its close-up's finish map in SegviGen's part colours, unseen sides included.

Row (place grain, surfaces-segvigen@<place>), every take whose close-up map settled (finish_rows.passed_takes): each
raw model goes up turned half round (labels.VIEW_TURN), as SegviGen's camera looks at the raw model's back; each
take's down/ is kept, its uploads removed after.
"""
import json
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROPS = REPO / "tools/props"
for folder in (HERE, PROPS, PROPS / "library", PROPS / "cloud"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the method modules must not shadow the framework's
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import prop_env  # noqa: E402
import surface_gates as gates  # noqa: E402

# One or two cards for SegviGen's 15 min set-up and about 6 min a take (meshparts.py's guesses).
SEGVIGEN_EUROS = 3.0
FILES = {"meshparts": "{repo}/tools/props/cloud/meshparts.py",
         "segvigen worker": "{repo}/tools/props/cloud/segvigen_worker.py"}


def passed(inputs):
    """The takes whose close-up's finish map settled (finish_rows' map.json); a failed one the owner waived is left
    out from here on."""
    return sorted(path.parent.name for path in inputs["maps"].glob("*/map.json")
                  if json.loads(path.read_text())["passes"])


def make_segvigen(inputs, out, seed, params):
    """SegviGen guided by each settled finish map on a rented card."""
    import numpy as np
    import trimesh
    import labels
    import split_compare
    inputs = prop_env.short(inputs)
    takes = passed(inputs)
    turn = np.eye(4)
    turn[:3, :3] = labels.VIEW_TURN
    for take in takes:
        up = out / take / "up"
        up.mkdir(parents=True)
        scene = trimesh.load(labels.PIXAL / f"{take}.glb", force="scene")
        for geometry in scene.geometry.values():  # into the vertices, not a node: every reader then sees it turned
            geometry.apply_transform(turn)
        scene.export(up / "raw.glb")
        split_compare.guide_map(np.load(inputs["maps"] / take / "front.npy").astype(int)).save(up / "map.png")
    command = [sys.executable, str(PROPS / "cloud/meshparts.py"), str(out), "--who", "surfaces", "--methods",
               "segvigen", "--takes", ",".join(takes)]
    done = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
    (out / "meshparts.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    for take in takes:
        shutil.rmtree(out / take / "up")
    if done.returncode:
        raise RuntimeError(f"meshparts.py failed: {done.stderr[-2000:]}")


def segvigen_faults(folder):
    return [] if (folder / "meshparts.log").exists() else ["no meshparts.log"]


def judge_segvigen(output, inputs, evidence):
    """Every take with a settled map came back with SegviGen's guided split."""
    takes = passed(prop_env.short(inputs))
    missing = [take for take in takes if not (output / take / "down" / "segvigen_guided.npz").exists()]
    return gates.verdict("split back", [f"{take}: no guided split" for take in missing], len(takes),
                         "takes without SegviGen's split")
