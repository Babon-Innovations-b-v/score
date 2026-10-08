"""Measure a room's target picture in metres with MoGe-2: a 3D point for every pixel, and the lens.

    ~/.farm-factory-props/env/bin/python tools/props/scene/depth.py <room>

Reads WORK/scene/<room>/<room>-target.png and writes depth.npz beside it: `points` (height x width
x 3, metres, in the picture camera's own frame: x right, y down, z ahead), `valid` (the pixels
MoGe-2 trusts) and `intrinsics` (3x3, normalised to the picture's width and height). boxes.py
turns these into the room's shape and each object's box.

MoGe-2 is Microsoft's (MIT, code and weights). Its code and its helper library utils3d-moge (MIT,
at the commit MoGe pins) are copies outside the repo, put on the path here rather than installed,
because the prop environment's own older utils3d belongs to TRELLIS: ~/.farm-factory-props/moge
and ~/.farm-factory-props/utils3d-moge (MOGE_SOURCE and UTILS3D_SOURCE). Its weights come from
Hugging Face. Holds the card. Runs on a rented card through cloud/scene.py (a plan's "depth"); on
this PC it is refused.
"""
import argparse
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402
import torch  # noqa: E402
from PIL import Image  # noqa: E402

from card import claimed  # noqa: E402
from local_models import refuse_here  # noqa: E402
from paths import HOME  # noqa: E402
from paths import scene_folder as folder  # noqa: E402

SOURCE = pathlib.Path(os.environ.get("MOGE_SOURCE", HOME / "moge"))
HELPERS = pathlib.Path(os.environ.get("UTILS3D_SOURCE", HOME / "utils3d-moge"))
WEIGHTS = "Ruicheng/moge-2-vitl-normal"


def measured(image):
    """MoGe-2's points, trusted pixels and lens for one picture, on the card."""
    refuse_here("MoGe-2", "tools/props/cloud/scene.py <plan.json> with \"depth\": true in the plan")
    sys.path[:0] = [str(SOURCE), str(HELPERS)]
    from moge.model.v2 import MoGeModel
    pixels = torch.tensor(np.asarray(image) / 255.0, dtype=torch.float32).permute(2, 0, 1)
    with claimed("MoGe-2 depth"):
        model = MoGeModel.from_pretrained(WEIGHTS).to("cuda").eval()
        with torch.no_grad():
            output = model.infer(pixels.to("cuda"))
    return {key: output[key].cpu().numpy() for key in ("points", "mask", "intrinsics")}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("room")
    options = parser.parse_args()
    out = folder(options.room)
    output = measured(Image.open(out / f"{options.room}-target.png").convert("RGB"))
    np.savez_compressed(out / "depth.npz", points=output["points"], valid=output["mask"],
                        intrinsics=output["intrinsics"])
    fov = np.degrees(2 * np.arctan(0.5 / output["intrinsics"][0, 0]))
    print(f"{out / 'depth.npz'}: horizontal lens {fov:.1f} degrees, "
          f"{output['mask'].mean():.0%} of pixels trusted")


if __name__ == "__main__":
    main()
