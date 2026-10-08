"""Read what layout.py needs from each finished model: its size and the side the target saw.

    ~/.farm-factory-props/env/bin/python tools/props/scene/models.py <room> <prefix> <model> ...

For each model, pixal.py left WORK/pixal/<prefix><model>-<faces>.glb (finished, still in the
generator's camera frame, CAMERA_SIDE below) and <prefix><model>-final.glb
(stood upright and squared, the one placed). The turn between the two is solved from their
positions, which are the same points in the same order, and turns the side the camera saw into
the placed model's frame. Writes models.json in the room's folder: per model its file, its
size (x, y, z in its own units) and that side as a flat (x, z) direction.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402

import glb_file  # noqa: E402
from pixal import OUT  # noqa: E402
from paths import scene_folder as folder  # noqa: E402

# Where the picture's camera stands in a finished (not yet stood up) model's frame: -z. Measured
# 2026-10-02 by laying each model's outline seen from each side over its picture: from -z the
# habitat's bench and desk matched at 0.62 and 0.61 (overlap over union), from +z at 0.33 and
# 0.48. The camera file Pixal3D keeps (transforms.json) is in Blender's frame and reads as +z.
CAMERA_SIDE = np.array([0.0, 0.0, -1.0])


def points_of(path):
    """A model file's positions."""
    document, views = glb_file.read(path)
    return glb_file.positions(document, views)


def seen_side(finished, final):
    """The flat (x, z) direction, in the final model's frame, that the picture's camera saw it
    from: CAMERA_SIDE of the finished model carried through the turn that stood it up."""
    before, after = points_of(finished), points_of(final)
    turn = np.linalg.lstsq(before - before.mean(0), after - after.mean(0), rcond=None)[0].T
    side = turn @ CAMERA_SIDE
    flat = np.array([side[0], side[2]])
    return (flat / np.linalg.norm(flat)).round(4).tolist()


def facts(prefix, model):
    """One model's file, size and seen side."""
    final = OUT / f"{prefix}{model}-final.glb"
    finished = next(path for path in OUT.glob(f"{prefix}{model}-*.glb")
                    if path.stem.rsplit("-", 1)[1].isdigit())
    points = points_of(final)
    return {"file": str(final), "size": (points.max(0) - points.min(0)).round(4).tolist(),
            "front": seen_side(finished, final)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("room")
    parser.add_argument("prefix")
    parser.add_argument("models", nargs="+")
    options = parser.parse_args()
    found = {model: facts(options.prefix, model) for model in options.models}
    (folder(options.room) / "models.json").write_text(json.dumps(found, indent=1))
    for model, item in found.items():
        print(model, item["size"], item["front"])


if __name__ == "__main__":
    main()
