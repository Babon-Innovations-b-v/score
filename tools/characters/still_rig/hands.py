"""The relaxed hands a rigged person wears in place of its picture-made ones (#223): a generated person's TRELLIS.2
hands are fused lumps with no fingers apart, and on a skeleton with one joint a hand they read as claws and mittens
curled against the coat (owner, 2026-11-27, of the round 6 cloth sheets). The whole route's skin has real ones:
SOMA-X's mid body of an MHR identity, its fingers laid at rest (`tools.characters.whole.carried_skin`,
`relaxed_hands`, whose posture checks fail a hand that still splays). Each side's hand is cut from that skin with a
stub of forearm above the wrist that hides in the sleeve, and written beside the clips rig it is bound to, at its
bind and with its weights; `still_rig --person` lays them on the person.

    .venv/bin/python -m tools.characters.still_rig.hands <face.npz> <body.npz> <clips rig.npz>

<face.npz> and <body.npz> are the whole route's (`../face/face.py`, `../face/body_face.py`). Writes <clips rig
folder>/hands.npz: each side's `points` (metres, the clips rig's bind frame), `faces`, `weights` (points x the clips
rig's joints, its order) and `tones` (whole's hand tones: flush, thin), and the rig's `names`.
"""
import argparse
import pathlib

import numpy as np

FILE = "hands.npz"  # beside the clips rig it is bound to
STUB = 0.05  # metres of forearm above the wrist kept with a hand: hidden in the sleeve, where the cuff meets it
ARM_SHARE = 0.5  # a point whose forearm and hand weights reach this is on that arm (never the thigh it rests by)
SIDES = ("Left", "Right")


def cut(points, faces, weights, tones, names, bind):
    """Each side's hand from a whole skin at `bind`: its faces whose every corner hangs ARM_SHARE or more from that
    side's forearm and hand and lies past STUB above the wrist (the Hand joint) along the forearm. {f"{side}.points",
    ".faces" (renumbered), ".weights", ".tones"}."""
    names = [str(name) for name in names]
    found = {}
    for side in SIDES:
        wrist, elbow = (bind[names.index(side + joint), :3, 3] for joint in ("Hand", "ForeArm"))
        along = (points - wrist) @ ((wrist - elbow) / np.linalg.norm(wrist - elbow))
        arm = weights[:, [names.index(side + "ForeArm"), names.index(side + "Hand")]].sum(1) >= ARM_SHARE
        kept = ((along > -STUB) & arm)[faces].all(1)
        used, renumbered = np.unique(faces[kept], return_inverse=True)
        found.update({f"{side}.points": points[used], f"{side}.faces": renumbered.reshape(-1, 3),
                      f"{side}.weights": weights[used], f"{side}.tones": tones[used, :2]})
    return found


def made(face_path, body_path, rig_path):
    """The hands of the whole route's skin (`carried_skin` at the clips rig's own bind) written beside the clips rig;
    its path."""
    from tools.characters import whole
    rig = np.load(rig_path)
    bind = np.asarray(rig["bind"], float)
    carried = whole.carried_skin(np.load(face_path), np.load(body_path), rig, bind)
    found = cut(carried["points"], carried["faces"], carried["weights"], carried["tones"], rig["names"], bind)
    out = pathlib.Path(rig_path).parent / FILE
    np.savez_compressed(out, names=np.asarray(rig["names"]), **found)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("face", type=pathlib.Path)
    parser.add_argument("body", type=pathlib.Path)
    parser.add_argument("rig", type=pathlib.Path)
    options = parser.parse_args()
    out = made(options.face, options.body, options.rig)
    counts = {side: len(np.load(out)[f"{side}.points"]) for side in SIDES}
    print(f"hands: {counts} points; {out}", flush=True)


if __name__ == "__main__":
    main()
