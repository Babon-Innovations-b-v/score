"""bone_groups: a `{Side}` name is written out for both sides, and every segment the fit follows rides a MyoFullBody
body of its own side (pure: the score venv runs it).

Breaks (each applied once, seen red, reverted), 2026-10-28:
- sided_map's `side[0].lower()` (the value's) made `side[0]`: LeftLeg rides `femur_L`, not `femur_l`.
- sided's `("Left", "Right")` made `("Left",)`: no right-side segment is followed.

Run: .venv/bin/python score/stages/sim_body/inside/bone_groups/test_every_followed_segment_rides_a_body_on_its_side.py
"""
import pathlib
import sys

INSIDE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSIDE))
import bone_groups  # noqa: E402


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


CHECKS = (a_side_name_is_written_for_both_sides, every_followed_segment_rides_a_body_on_its_side)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[5] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
