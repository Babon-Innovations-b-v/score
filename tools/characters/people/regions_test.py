"""Checks the joint-to-surface rules, with the system python and nothing installed.

Run by the gate (`tools/test/run.sh`), which has no numpy and no tool chain built, so nothing
here may import either.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from regions import BOOTS, CLOTHES, SKIN, region_of, regions_of, surfaces  # noqa: E402

# A real slice of the body model's 78 joints, names copied from what it reports.
SKELETON = [
    "Root", "Hips", "Spine1", "Chest", "Neck1", "Head", "HeadEnd", "Jaw", "LeftEye",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumb1", "LeftHandPinkyEnd",
    "RightLeg", "RightShin", "RightFoot", "RightToeBase", "RightToeEnd",
]


def check(what, got, wanted):
    if got != wanted:
        raise AssertionError(f"{what}: got {got!r}, wanted {wanted!r}")


def a_face_is_skin():
    for joint in ("Head", "HeadEnd", "Jaw", "LeftEye", "RightEye", "Neck1", "Neck2"):
        check(joint, region_of(joint), SKIN)


def a_bare_hand_is_skin():
    for joint in ("LeftHand", "RightHand", "LeftHandThumb1", "RightHandPinkyEnd"):
        check(joint, region_of(joint), SKIN)


def a_foot_wears_a_boot():
    for joint in ("LeftFoot", "RightFoot", "LeftToeBase", "RightToeEnd"):
        check(joint, region_of(joint), BOOTS)


def everything_else_is_clothed():
    for joint in ("Root", "Hips", "Spine1", "Spine2", "Chest", "LeftShoulder", "LeftArm",
                  "LeftForeArm", "RightLeg", "RightShin"):
        check(joint, region_of(joint), CLOTHES)


def a_forearm_is_not_a_hand():
    """`Hand` appears inside no other joint's name, which is what the rule leans on."""
    check("LeftForeArm", region_of("LeftForeArm"), CLOTHES)


def the_whole_skeleton_is_answered():
    answers = regions_of(SKELETON)
    check("one answer a joint", len(answers), len(SKELETON))
    check("every answer is a surface", set(answers) <= {SKIN, CLOTHES, BOOTS}, True)


def the_surfaces_come_in_a_fixed_order():
    check("order", surfaces(SKELETON), [SKIN, CLOTHES, BOOTS])
    check("only what is there", surfaces(["Hips", "Spine1"]), [CLOTHES])


def main():
    for name, check_this in sorted(globals().items()):
        if name.startswith(("a_", "the_", "everything_")) and callable(check_this):
            check_this()
    print("regions: green")


main()
