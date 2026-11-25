"""bone_groups: a `{Side}` name is written out for both sides, each segment rides its group's frame body, one of the
group's own bodies on its side, and every bone group spans the same joints as its SOMA segment: its SOMA stretch runs
from the segment's joint to that joint's child in SOMA's tree (SOMA_PARENTS: the template rig's, written out by hand),
each SOMA joint is the same MyoFullBody centre in every group it ends or starts (and each centre one SOMA joint), every
body is in one group of its own side (pure: the score venv runs it). One test reads the written-out table `groups()`
once: its entries worked by hand (WRITTEN) and `sided` over GROUPS' names, then every group's stretch and bodies.

Breaks (each applied once, seen red, reverted), 2026-10-28, again 2026-11-13 on the one test:
- _written's `side=side[0].lower()` made `side=side[0]`: LeftLeg's entry writes `femur_L`, not `femur_l`.
- sided's `("Left", "Right")` made `("Left",)`: `{Side}Arm` is LeftArm only, not the table's segments.
- GROUPS' Spine2 MyoFullBody start `"L3_L4"` made `"L2_L3"`: SOMA's Spine2 is two MyoFullBody centres.
- GROUPS' `{Side}Shin` SOMA end `"{Side}Foot"` made `"{Side}ToeBase"`: the shin's stretch skips a joint.
- GROUPS' `{Side}Foot` bodies `"talus_{side}"` made `"talus_l"`: the right foot holds a left body.
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

# Entries of the written-out table worked by hand (stretch, centres, frame, first bodies): a plain name stays, a
# `{Side}` name gives LeftX and RightX with `_l` and `_r` bodies, a nested tuple written out part by part.
WRITTEN = {
    "Hips": (("hipmid", "Spine1"), ("hipmid", "L5_S1"), "pelvis", ("Full Body", "pelvis", "sacrum")),
    "LeftLeg": (("LeftLeg", "LeftShin"), ("hip_l", "knee_l"), "femur_l", ("femur_l",)),
    "RightLeg": (("RightLeg", "RightShin"), ("hip_r", "knee_r"), "femur_r", ("femur_r",)),
    "LeftHand": (("LeftHand", "LeftHand tip"), ("wrist_l", "finger_tip_l"), "lunate_l", ("lunate_l", "scaphoid_l")),
    "RightHand": (("RightHand", "RightHand tip"), ("wrist_r", "finger_tip_r"), "lunate_r", ("lunate_r", "scaphoid_r")),
}


def test_each_segment_rides_and_groups_bodies_of_its_side_joint_to_joint():
    """The written-out table holds WRITTEN's entries and exactly `sided`'s names of GROUPS; each group's SOMA stretch
    runs from its joint (Hips from the hip joints' middle, `hipmid`) to its joint's child or its own mesh tip, each SOMA
    joint one MyoFullBody centre wherever it appears and each centre one joint, each body in one group, a side's group
    holding only its side's bodies, its frame one of its bodies."""
    written = bone_groups.groups()
    problems = [] if list(written) == bone_groups.sided(list(bone_groups.GROUPS)) else [
        f"sided gave {bone_groups.sided(list(bone_groups.GROUPS))}, the table {list(written)}"]
    for segment, (stretch, centres, frame, bodies) in WRITTEN.items():
        found = written.get(segment)
        if found is None or found[:3] != (stretch, centres, frame) or found[3][:len(bodies)] != bodies:
            problems.append(f"{segment} written {found}, by hand {(stretch, centres, frame, bodies)}")
    centre_of, joint_of, owner = {}, {}, {}
    for segment, ((start, end), (myo_start, myo_end), frame, bodies) in written.items():
        if start != ("hipmid" if segment == "Hips" else segment):
            problems.append(f"{segment} starts at {start}")
        if end.endswith(" tip") and end != f"{segment} tip":
            problems.append(f"{segment} ends at {end}")
        if not end.endswith(" tip") and SOMA_PARENTS.get(end) != segment:
            problems.append(f"{segment} ends at {end}, not a child of its joint")
        for joint, centre in ((start, myo_start), (end, myo_end)):
            if centre_of.setdefault(joint, centre) != centre:
                problems.append(f"SOMA's {joint} is {centre_of[joint]} and {centre}")
            if joint_of.setdefault(centre, joint) != joint:
                problems.append(f"{centre} is SOMA's {joint_of[centre]} and {joint}")
        letter = {"Left": "_l", "Right": "_r"}.get(segment[:4] if segment.startswith("Left") else segment[:5])
        for body in bodies:
            if owner.setdefault(body, segment) != segment:
                problems.append(f"{body} is in {owner[body]} and {segment}")
            if letter and not body.endswith(letter):
                problems.append(f"{segment} holds {body}")
        if bodies and frame not in bodies:
            problems.append(f"{segment}'s frame {frame} is not one of its bodies")
    assert not problems, "\n".join(problems)
