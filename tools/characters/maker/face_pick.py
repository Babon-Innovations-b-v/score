"""Keep one face drawing in the person's look: `look/face/drawn.png`, `depth.npy` and `view.json` with the pixel boxes
round the nose and the mouth whose drawn lines the paint keeps (take C's boxes, moved with the eyes).

    /root/envs/motion/bin/python face_pick.py <work folder> <seed> [mouth_drop=<metres>] [nose_only]

`nose_only` keeps only the nose's lines, for a bearded face (the drawing's beard is solid black round the mouth and
the painted beard leaves the lips clear); `mouth_drop` lets the mouth's box reach further down. Moved here from the
nev_mars job's face_pick.py (#112).
"""
import json
import pathlib
import shutil
import sys

TAKE_C_EYE_X, TAKE_C_EYE_Y, TAKE_C_TOP = 0.031, 1.649, 1.757
# Take C's boxes (paint.KEEP) in metres off his eyes: across, then how far under the eyes the box starts and ends.
NOSE = (-0.0135, 0.0145, 0.035, 0.050)
MOUTH = (-0.0350, 0.0350, 0.059, 0.086)


def boxes(joints, view, mouth_drop, nose_only):
    """The kept boxes in pixels of the face view."""
    eye_y = joints["LeftEye"][1]
    across = joints["LeftEye"][0] / TAKE_C_EYE_X
    up = (joints["HeadEnd"][1] - eye_y) / (TAKE_C_TOP - TAKE_C_EYE_Y)
    left_edge, right_edge, bottom, top = view["window"]
    size = view["size"]

    def column(metres):
        return int(round((metres * across - left_edge) / (right_edge - left_edge) * size))

    def row(drop):
        return int(round((top - (eye_y - drop * up)) / (top - bottom) * size))

    def box(left, right, top_drop, bottom_drop):
        return [column(left), row(top_drop), column(right), row(bottom_drop)]
    kept = [box(*NOSE)]
    if not nose_only:
        kept.append(box(*MOUTH[:3], MOUTH[3] + mouth_drop))
    return kept


def main():
    work, seed = pathlib.Path(sys.argv[1]), sys.argv[2]
    options = dict(argument.split("=") if "=" in argument else (argument, "") for argument in sys.argv[3:])
    joints = json.loads((work / "gc/body/joints.json").read_text())
    view = json.loads((work / "face/view.json").read_text())
    view["keep"] = boxes(joints, view, float(options.get("mouth_drop", 0.0)), "nose_only" in options)
    look = work / "look/face"
    look.mkdir(parents=True, exist_ok=True)
    shutil.copy(work / f"face/drawn_s{seed}.png", look / "drawn.png")
    shutil.copy(work / "face/depth.npy", look / "depth.npy")
    (look / "view.json").write_text(json.dumps(view))
    print("face kept: seed", seed, "boxes", view["keep"], flush=True)


if __name__ == "__main__":
    main()
