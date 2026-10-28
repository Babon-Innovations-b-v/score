"""bone_groups: a `{Side}` name is written out for both sides, every segment the fit follows rides a MyoFullBody
body of its own side, and every bone group spans the same joints as its SOMA segment: its SOMA stretch runs from the
segment's joint to that joint's child in SOMA's tree (SOMA_PARENTS: the template rig's, written out by hand), each
SOMA joint is the same MyoFullBody centre in every group it ends or starts (and each centre one SOMA joint), every
body is in one group of its own side (pure: the score venv runs it).

Breaks (each applied once, seen red, reverted), 2026-10-28:
- _written's `side=side[0].lower()` made `side=side[0]`: LeftLeg rides `femur_L`, not `femur_l`.
- sided's `("Left", "Right")` made `("Left",)`: no right-side segment is followed.
- GROUPS' Spine2 MyoFullBody start `"L3_L4"` made `"L2_L3"`: SOMA's Spine2 is two MyoFullBody centres.
- GROUPS' `{Side}Shin` SOMA end `"{Side}Foot"` made `"{Side}ToeBase"`: the shin's stretch skips a joint.
- GROUPS' `{Side}Foot` bodies `"talus_{side}"` made `"talus_l"`: the right foot holds a left body.

Run: .venv/bin/python score/stages/sim_body/inside/bone_groups/test_each_segment_rides_and_groups_bodies_of_its_side_joint_to_joint.py
"""
import pathlib
import sys

INSIDE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSIDE))
import bone_groups  # noqa: E402

# SOMA's template rig (people-clips-make rig.npz `names`, `parents`), each joint's parent, written out by hand.
SOMA_PARENTS = {"Hips": "Root", "Spine1": "Hips", "Spine2": "Spine1", "Chest": "Spine2", "Neck1": "Chest",
                "Neck2": "Neck1", "Head": "Neck2", "HeadEnd": "Head", **{
                    f"{side}{joint}": parent.format(side) for side in ("Left", "Right") for joint, parent in (
                        ("Shoulder", "Chest"), ("Arm", "{}Shoulder"), ("ForeArm", "{}Arm"), ("Hand", "{}ForeArm"),
                        ("Leg", "Hips"), ("Shin", "{}Leg"), ("Foot", "{}Shin"), ("ToeBase", "{}Foot"),
                        ("ToeEnd", "{}ToeBase"))}}


def a_side_name_is_written_for_both_sides():
    """Worked by hand: `{Side}Arm` is LeftArm and RightArm, a plain name stays; a `{Side}` table gives `_l` and `_r`
    bodies, a tuple value written out part by part."""
    problems = []
    if bone_groups.sided(["Hips", "{Side}Arm"]) != ["Hips", "LeftArm", "RightArm"]:
        problems.append(f"sided gave {bone_groups.sided(['Hips', '{Side}Arm'])}")
    wanted = {"LeftLeg": "femur_l", "RightLeg": "femur_r", "Hips": "pelvis", "LeftHand": ("lunate_l", "Left"),
              "RightHand": ("lunate_r", "Right")}
    found = bone_groups.sided_map({"{Side}Leg": "femur_{side}", "Hips": "pelvis",
                                   "{Side}Hand": ("lunate_{side}", "{Side}")})
    return problems + ([] if found == wanted else [f"sided_map gave {found}"])


def every_followed_segment_rides_a_body_on_its_side():
    """Every TARGETS segment, both sides, rides a body (RIDES), a left one a `_l` body and a right one a `_r` body;
    the hips are the femurs the leg segments ride; the feet are followed."""
    rides = bone_groups.sided_map(bone_groups.RIDES)
    followed = bone_groups.sided(bone_groups.TARGETS)
    problems = [f"{segment} rides no body" for segment in followed if segment not in rides]
    problems += [f"{segment} rides {rides[segment]}" for segment in followed if segment in rides and (
        (segment.startswith("Left") and not rides[segment].endswith("_l"))
        or (segment.startswith("Right") and not rides[segment].endswith("_r")))]
    problems += [f"{segment}'s hip is {femur}, it rides {rides.get(segment)}"
                 for segment, femur in bone_groups.HIPS.items() if rides.get(segment) != femur]
    if not {"LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase"} <= set(followed):
        problems.append(f"the feet are not all followed: {followed}")
    return problems


def every_bone_group_spans_its_segments_joints():
    """Each group's SOMA stretch: Hips from the hip joints' middle (`hipmid`) to Spine1, the hand to its mesh tip,
    every other segment from its own joint to its joint's child; each SOMA joint one MyoFullBody centre wherever it
    appears and each centre one joint; each body in one group, a side's group holding only its side's bodies."""
    problems, centres, joints, owner = [], {}, {}, {}
    for segment, ((start, end), (myo_start, myo_end), frame, bodies) in bone_groups.groups().items():
        wanted = "hipmid" if segment == "Hips" else segment
        if start != wanted:
            problems.append(f"{segment} starts at {start}")
        if not end.endswith(" tip") and SOMA_PARENTS.get(end) != segment:
            problems.append(f"{segment} ends at {end}, not a child of its joint")
        if end.endswith(" tip") and end != f"{segment} tip":
            problems.append(f"{segment} ends at {end}")
        for joint, centre in ((start, myo_start), (end, myo_end)):
            if centres.setdefault(joint, centre) != centre:
                problems.append(f"SOMA's {joint} is {centres[joint]} and {centre}")
            if joints.setdefault(centre, joint) != joint:
                problems.append(f"{centre} is SOMA's {joints[centre]} and {joint}")
        letter = {"Left": "_l", "Right": "_r"}.get(segment[:4] if segment.startswith("Left") else segment[:5])
        for body in bodies:
            if owner.setdefault(body, segment) != segment:
                problems.append(f"{body} is in {owner[body]} and {segment}")
            if letter and not body.endswith(letter):
                problems.append(f"{segment} holds {body}")
        if bodies and frame not in bodies:
            problems.append(f"{segment}'s frame {frame} is not one of its bodies")
    return problems


CHECKS = (a_side_name_is_written_for_both_sides, every_followed_segment_rides_a_body_on_its_side,
          every_bone_group_spans_its_segments_joints)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[5] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
