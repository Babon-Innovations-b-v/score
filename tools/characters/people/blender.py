"""The two jobs the crew build hands to Blender: thinning a mesh and unwrapping it for a picture.

Each runs the prop chain's Blender in the background on files in the dressing folder, so the
build's own python never needs Blender's.
"""
import pathlib
import subprocess

import numpy as np
from paths import BLENDER, DRESSING

HERE = pathlib.Path(__file__).resolve().parent


def _run(script, *arguments):
    subprocess.run([str(BLENDER), "-b", "-P", str(HERE / script), "--", *map(str, arguments)],
                   check=True, capture_output=True)


def thinned(name, points, faces, triangles, symmetric=False):
    """The mesh thinned to about `triangles`, its open edges kept: points and faces."""
    source, out = DRESSING / f"{name}_full.npz", DRESSING / f"{name}_thin.npz"
    DRESSING.mkdir(parents=True, exist_ok=True)
    np.savez(source, points=points, faces=faces)
    _run("blender_thin.py", source, out, triangles, *(["symmetric"] if symmetric else []))
    data = np.load(out)
    return data["points"], data["faces"].astype(np.int64)


def corner_uv(name, points, faces, angle=66.0):
    """Texture coordinates for every corner of every face, by Blender's smart projection."""
    source, out = DRESSING / f"{name}_uv_in.npz", DRESSING / f"{name}_uv.npz"
    DRESSING.mkdir(parents=True, exist_ok=True)
    np.savez(source, points=points, faces=faces)
    _run("blender_unwrap.py", source, out, angle)
    return np.load(out)["corner_uv"]
