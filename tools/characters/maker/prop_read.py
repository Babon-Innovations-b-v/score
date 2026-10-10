"""The bind pose the prop route's close-up is drawn in, measured on SOMA-X's mean skeleton, on the rented card in the
motion environment:

    /root/envs/motion/bin/python prop_read.py <pose.json>

Writes the arm's angle below level from the shoulder joint (LeftArm) to the hand joint (LeftHand), how far the hands
stand in front of the shoulders, and the ankles' spacing (the foot joints), never typed. Only the skeleton's joints are
read: on the prop route SOMA-X gives the rig and its skin weights, never a surface (owner, 2026-10-10), and no body is
read off the picture (SAM3DBody-cpp is not used on this route: its body is SOMA-like and would shape the mesh).
"""
import json
import math
import pathlib
import sys

MAKER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(MAKER.parent / "people"))


def bind_pose():
    """The mean skeleton's bind pose: the arm angle (degrees), the hands' forward offset and the ankles' spacing (m)."""
    import body
    layer = body.build_layer("low")
    world, _ = body.average_bind_pose(layer)
    names = list(layer.public_joint_names)
    place = {name: world[names.index(name)][:3, 3] for name in ("LeftArm", "LeftHand", "LeftFoot", "RightFoot")}
    arm = place["LeftHand"] - place["LeftArm"]
    return {"arm_degrees": round(math.degrees(math.atan2(-arm[1], abs(arm[0]))), 2),
            "hands_forward_m": round(float(arm[2]), 3),
            "ankles_m": round(float(abs(place["LeftFoot"][0] - place["RightFoot"][0])), 3),
            "from": "SOMA-X mean skeleton's bind pose (people/body.py build_layer('low'))"}


def main():
    out = pathlib.Path(sys.argv[1])
    out.write_text(json.dumps(bind_pose(), indent=1))
    print(out.read_text(), flush=True)


if __name__ == "__main__":
    main()
