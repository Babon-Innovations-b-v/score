"""The relaxed hands a rigged person wears in place of its picture-made ones (#223): a generated person's TRELLIS.2
hands are fused lumps with no fingers apart, and on a skeleton with one joint a hand they read as claws and mittens
curled against the coat (owner, 2026-11-27, of the round 6 cloth sheets). The whole route's skin has real ones:
SOMA-X's mid body of an MHR identity, its fingers laid at rest (`tools.characters.whole.carried_skin`,
`relaxed_hands`, whose posture checks fail a hand that still splays). That rest is the whole route's open hand; laid
on a coated person it read as fingers splayed stiffly apart (coordinator, 2026-11-27, of gen9's close-ups), so each
hand is laid again a little more closed (`curled`: the fingers gently curled and together, the thumb in against the
index finger), its nails found on the back of each end bone (`nails`). Each side's hand is cut from that skin with a
stub of forearm above the wrist that hides in the sleeve, and written beside the clips rig it is bound to, at its
bind and with its weights; `still_rig --person` lays them on the person.

    .venv/bin/python -m tools.characters.still_rig.hands <face.npz> <body.npz> <clips rig.npz>

<face.npz> and <body.npz> are the whole route's (`../face/face.py`, `../face/body_face.py`). Writes <clips rig
folder>/hands.npz: each side's `points` (metres, the clips rig's bind frame), `faces`, `weights` (points x the clips
rig's joints, its order) and `tones` (whole's hand tones: flush, thin; and the nail's share), and the rig's `names`.
"""
import argparse
import pathlib

from unittest import mock

import numpy as np

FILE = "hands.npz"  # beside the clips rig it is bound to
STUB = 0.05  # metres of forearm above the wrist kept with a hand: hidden in the sleeve, where the cuff meets it
HAND_SHARE = 0.5  # a point hanging this much or more from a Hand joint is that hand's (whole's own share)
ARM_SHARE = 0.5  # a point whose forearm and hand weights reach this is on that arm (never the thigh it rests by)
SIDES = ("Left", "Right")
# The hand laid again from whole's open rest (posture's own rest, its constants given these): each finger's bend from
# its palm bone to its end bone, degrees (whole's 36 to 63 read as stiff and splayed on a coated person; its 55 to 85
# of round 1 as a mannequin's claw); each finger's first bone's angle off the middle finger's, nearly parallel so the
# fingers lie together; the thumb's two joints bent this much more, and its tip laid this near the index finger's
# middle bone (towards the thumb's side, the palm's), m.
CURL_DEGREES = {"Index": 50.0, "Middle": 58.0, "Ring": 65.0, "Pinky": 72.0}
TOGETHER_DEGREES = {"Index": -2.0, "Middle": 0.0, "Ring": 2.0, "Pinky": 4.0}
THUMB_MORE_DEGREES = (6.0, 10.0)
THUMB_IN_M = (0.006, 0.008)
# A nail: the skin over the back of a finger's end bone (its last joint to its tip), from this share along it on,
# within this angle of the back's direction round the bone.
NAIL_FROM = 0.3
NAIL_DEGREES = 50.0


def curled(points, weights, names, joints):
    """The skin's points with each hand (its points hanging HAND_SHARE or more from that Hand joint) laid again from
    whole's rest a little more closed, by posture's own rest (`hand_rested`) given CURL_DEGREES, TOGETHER_DEGREES,
    THUMB_MORE_DEGREES and THUMB_IN_M, and failed by posture's hand checks as whole's rest is; (points, joints so
    laid)."""
    from tools.characters import posture
    names = [str(name) for name in names]
    moved, placed = points.copy(), dict(joints)
    with mock.patch.multiple(posture, FINGER_BEND_DEGREES=CURL_DEGREES, FINGER_SPREAD_DEGREES=TOGETHER_DEGREES,
                             THUMB_BEND_DEGREES=THUMB_MORE_DEGREES, THUMB_REST_OFF_M=THUMB_IN_M):
        for side in SIDES:
            hand = weights[:, names.index(side + "Hand")] > HAND_SHARE
            mine = {name: place for name, place in placed.items() if name.startswith(side + "Hand")}
            moved[hand], laid = posture.hand_rested(points[hand], mine, side)
            faults = posture.hand_faults(posture.hand_measured(laid, side), side)
            if faults:
                raise ValueError("the curled hand: " + "; ".join(faults))
            placed.update(laid)
    return moved, placed


def nails(points, weights, names, joints):
    """Each skin point's nail share (0 or 1): the points of a hand (HAND_SHARE) nearest one of its fingers' end bones
    among all its bones, NAIL_FROM or more along it, and within NAIL_DEGREES of its back round it (away from the palm;
    the thumb's back turned towards the thumb's side, as it lies along the index finger)."""
    from tools.characters import posture
    names = [str(name) for name in names]
    found = np.zeros(len(points))
    for side in SIDES:
        hand = np.flatnonzero(weights[:, names.index(side + "Hand")] > HAND_SHARE)
        _, thumb_side, palm = posture.palm_frame(joints, side)
        chains = {finger: posture.finger_chain(side, finger) for finger in posture.FINGERS + ("Thumb",)}
        bones = [(finger, chain[index], chain[index + 1]) for finger, chain in chains.items()
                 for index in range(len(chain) - 1)]
        starts = np.array([joints[start] for _, start, _ in bones])
        ends = np.array([joints[end] for _, _, end in bones])
        nearest = posture.bone_distances(points[hand], starts, ends).argmin(1)
        for number, (finger, start, end) in enumerate(bones):
            if end != chains[finger][-1]:
                continue
            mine = hand[nearest == number]
            span = ends[number] - starts[number]
            along = (points[mine] - starts[number]) @ span / (span @ span)
            off = points[mine] - starts[number] - along[:, None] * span
            off /= np.maximum(np.linalg.norm(off, axis=1, keepdims=True), 1e-9)
            back = -palm + (thumb_side if finger == "Thumb" else 0.0)
            back = back - span * (back @ span) / (span @ span)
            back /= np.linalg.norm(back)
            found[mine[(along >= NAIL_FROM) & (off @ back >= np.cos(np.radians(NAIL_DEGREES)))]] = 1.0
    return found


def cut(points, faces, weights, tones, names, bind):
    """Each side's hand from a whole skin at `bind`: its faces whose every corner hangs ARM_SHARE or more from that
    side's forearm and hand and lies past STUB above the wrist (the Hand joint) along the forearm. {f"{side}.points",
    ".faces" (renumbered), ".weights", ".tones" (each point's row of `tones`)}."""
    names = [str(name) for name in names]
    found = {}
    for side in SIDES:
        wrist, elbow = (bind[names.index(side + joint), :3, 3] for joint in ("Hand", "ForeArm"))
        along = (points - wrist) @ ((wrist - elbow) / np.linalg.norm(wrist - elbow))
        arm = weights[:, [names.index(side + "ForeArm"), names.index(side + "Hand")]].sum(1) >= ARM_SHARE
        kept = ((along > -STUB) & arm)[faces].all(1)
        used, renumbered = np.unique(faces[kept], return_inverse=True)
        found.update({f"{side}.points": points[used], f"{side}.faces": renumbered.reshape(-1, 3),
                      f"{side}.weights": weights[used], f"{side}.tones": tones[used]})
    return found


def made(face_path, body_path, rig_path):
    """The hands of the whole route's skin (`carried_skin` at the clips rig's own bind), `curled`, their tones
    (flush, thin) with each point's nail share (`nails`), written beside the clips rig; its path."""
    from tools.characters import whole
    rig = np.load(rig_path)
    bind = np.asarray(rig["bind"], float)
    carried = whole.carried_skin(np.load(face_path), np.load(body_path), rig, bind)
    points, joints = curled(carried["points"], carried["weights"], rig["names"], carried["hand_joints"])
    tones = np.c_[carried["tones"][:, :2], nails(points, carried["weights"], rig["names"], joints)]
    found = cut(points, carried["faces"], carried["weights"], tones, rig["names"], bind)
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
    written = np.load(out)
    counts = {side: len(written[f"{side}.points"]) for side in SIDES}
    nailed = {side: int(written[f"{side}.tones"][:, 2].sum()) for side in SIDES}
    print(f"hands: {counts} points, {nailed} on nails; {out}", flush=True)


if __name__ == "__main__":
    main()
