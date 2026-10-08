"""Place a room's models from its measured boxes: the rules that turn boxes into a layout.

    python3 tools/props/scene/layout.py <room> <plan.json>

Plain python (no numpy), so its rules are checked by the gate on any box. The numbers it needs
from the models themselves (their size and which way the target saw them from) come from
models.py, which writes models.json beside the boxes.

The plan names which cut-outs become which model: {"objects": {"bench-1": "bench", "bench-2":
"bench", ...}, "lamps": ["desk_lamp-1"], "turns": {"bench": 90}}. A model may stand in for several
cut-outs (one bench model for both benches). "turns" is the hand fix, in degrees, for a model whose
front the rules got wrong, so the page can say how many needed one. What each rule does, in order:

  section  the module's round section as a list of (across, up) points from the floor's edge
           over the ceiling to the other side: a quarter ellipse from the floor's edge out to the
           widest point, another up to the ceiling. The stage builds its shell from these.
  turn     a model's front is the side its redrawn picture showed (models.py), and it is turned
           to face the aisle from the wall it stands at, or down the room from the far end, then
           squared so its sides lie along the room's (its front is rarely square to them). The
           other way to turn it, so the side the target's camera saw faces that camera again,
           is measured too: how far the two disagree is the turn error, reported per object.
           Turning by the camera alone was tried first and put the habitat's benches 35 to 45
           degrees off, their doors to the wall: the redraw does not keep the target's angle.
  height   a model is scaled, whole, to the box's height, or to the known measure for its kind
           when the box is within reach of it (KNOWN, TOLERANCE).
  rest     a box whose bottom is near the floor stands on the floor; one whose bottom is near the
           top of another object it overlaps stands on that; anything else hangs where it was seen.
  wall     a model's room-facing side stays where the target showed it, and it is then pulled in
           until its back fits inside the shell at its own height.
"""
import argparse
import json
import math
import pathlib
import sys

# Known measures, by model, in metres: the height an object of that kind is built at.
KNOWN = {"desk": 0.75, "counter_cabinet": 0.9, "bench": 0.45, "tall_cabinet": 1.9, "door": 2.0}
# How far a box may be from its known measure, as a share of it, and still be snapped to it.
TOLERANCE = 0.3
# A box whose bottom is this near the floor stands on it.
ON_FLOOR_M = 0.3
# A box whose bottom is this near another's top, over it, stands on that.
ON_TOP_M = 0.2
# An object this near the far end and this near the middle stands at the end wall and faces down
# the room; any other faces the aisle from its side wall.
AT_END_M = 0.8
AISLE_HALF_WIDTH_M = 0.7
# How many points each curve of the section is drawn with.
SECTION_STEPS = 8
# Where the shell stops behind the camera, past the picture's own camera.
BEHIND_CAMERA_M = 1.5


def section_points(measures):
    """The section's outline from one floor edge, over the top, to the other, as (across, up)."""
    floor, widest, at, ceiling = (measures["floor_half_width"], measures["widest_half_width"],
                                  measures["widest_height"], measures["ceiling"])
    right = [(floor + (widest - floor) * math.sin(math.pi / 2 * step / SECTION_STEPS),
              at * (1 - math.cos(math.pi / 2 * step / SECTION_STEPS)))
             for step in range(SECTION_STEPS + 1)]
    right += [(widest * math.cos(math.pi / 2 * step / SECTION_STEPS),
               at + (ceiling - at) * math.sin(math.pi / 2 * step / SECTION_STEPS))
              for step in range(1, SECTION_STEPS + 1)]
    left = [(-across, up) for across, up in reversed(right[:-1])]
    return [[round(across, 3), round(up, 3)] for across, up in right + left]


def half_width_at(outline, up):
    """How far from the middle the shell's wall is at a height, from the section's outline."""
    right = [point for point in outline if point[0] >= 0]
    for (low_across, low_up), (high_across, high_up) in zip(right, right[1:]):
        if low_up <= up <= high_up and high_up > low_up:
            share = (up - low_up) / (high_up - low_up)
            return low_across + (high_across - low_across) * share
    return 0.0


def heading(direction):
    """The turn about up, in degrees, that points the +z axis along a flat (x, z) direction."""
    return math.degrees(math.atan2(direction[0], direction[1]))


def squared(yaw):
    """A turn squared to the room, and how far that moved it: (squared turn, error), in degrees.
    A model's sides lie along its own x and z (models are stood up that way, glb_file.squared),
    so a whole number of quarter turns lays them along the room's."""
    error = (yaw - round(yaw / 90.0) * 90.0 + 180.0) % 360.0 - 180.0
    return yaw - error, error


def snapped_height(model, measured):
    """The height a model is built at: its known measure when the box is near it, else the box's."""
    known = KNOWN.get(model)
    if known is not None and abs(measured - known) <= TOLERANCE * known:
        return known
    return measured


def overlaps(first, second):
    """Whether two boxes overlap seen from above."""
    return (first["low"][0] < second["high"][0] and second["low"][0] < first["high"][0]
            and first["low"][2] < second["high"][2] and second["low"][2] < first["high"][2])


def resting_height(box, tops):
    """The height a box's bottom is set to: the floor, the top of what it stands on, or where it
    was seen. `tops` lists (box, built top height) for every object that stands on the floor."""
    if box["low"][1] < ON_FLOOR_M:
        return 0.0
    for under, top in tops:
        if under is not box and overlaps(box, under) and abs(box["low"][1] - under["high"][1]) < ON_TOP_M:
            return top
    return box["low"][1]


def footprint(size, yaw):
    """A model's (across, along) extent seen from above once turned by `yaw` degrees."""
    angle = math.radians(yaw)
    width, depth = size[0], size[2]
    return (abs(width * math.cos(angle)) + abs(depth * math.sin(angle)),
            abs(width * math.sin(angle)) + abs(depth * math.cos(angle)))


def centre_across(box, extent, outline, top):
    """Where a model's middle stands across the room: its room-facing side where the target saw
    it, pulled in until its back fits inside the shell at its top."""
    if box["low"][0] + box["high"][0] >= 0:
        wanted = box["low"][0] + extent / 2
        return min(wanted, half_width_at(outline, top) - extent / 2)
    wanted = box["high"][0] - extent / 2
    return max(wanted, -half_width_at(outline, top) + extent / 2)


def facing(box, far_end):
    """The flat direction an object faces: into the aisle from the wall it stands at, or back
    down the room from the far end wall."""
    middle_across = (box["low"][0] + box["high"][0]) / 2
    if box["low"][2] < far_end + AT_END_M and abs(middle_across) < AISLE_HALF_WIDTH_M:
        return (0.0, 1.0)
    return (1.0, 0.0) if middle_across < 0 else (-1.0, 0.0)


def wrapped(degrees):
    """An angle in degrees brought into -180 to 180."""
    return (degrees + 180.0) % 360.0 - 180.0


def placed(key, model, box, facts, camera, outline, tops, far_end):
    """One object's place: where its bottom middle stands, its turn, its scale, and the errors."""
    middle = [(box["low"][index] + box["high"][index]) / 2 for index in range(3)]
    to_camera = (camera[0] - middle[0], camera[2] - middle[2])
    seen_yaw = heading(to_camera) - heading(facts["front"])
    yaw = squared(wrapped(heading(facing(box, far_end)) - heading(facts["front"])))[0]
    turn_error = wrapped(seen_yaw - yaw)
    measured = box["high"][1] - box["low"][1]
    bottom = resting_height(box, tops)
    # Standing on the floor, an object's bottom is mostly hidden (kick plates, shadow), so it
    # reaches from the floor to its top; standing on something else, it is as tall as it was seen.
    height = snapped_height(model, box["high"][1] if bottom == 0.0 else measured)
    scale = height / facts["size"][1]
    size = [side * scale for side in facts["size"]]
    across, along = footprint(size, yaw)
    seen_across = box["high"][0] - box["low"][0]
    return {
        "key": key, "model": model, "yaw": round(yaw, 2), "scale": round(scale, 4),
        "position": [round(centre_across(box, across, outline, bottom + height), 3), round(bottom, 3),
                     round(middle[2], 3)],
        "turn_error": round(turn_error, 1), "height": round(height, 3),
        "size_against_box": [round(across / max(seen_across, 0.01), 2),
                             round(along / max(box["high"][2] - box["low"][2], 0.01), 2)],
    }


def one_size_per_model(objects, by_key):
    """Give every copy of a model the scale of its best-seen copy, the one whose box holds the
    most points: two benches from one model are one size, however much of each the frame cut off."""
    best = {}
    for item in objects:
        seen = by_key[item["key"]].get("points", 0)
        if item["model"] not in best or seen > best[item["model"]][0]:
            best[item["model"]] = (seen, item["scale"], item["height"])
    for item in objects:
        item["scale"], item["height"] = best[item["model"]][1:]


def layout(boxes, plan, models):
    """The whole room's layout from its boxes, the plan and the models' facts."""
    by_key = {item["key"]: item for item in boxes["objects"]}
    outline = section_points(boxes["section"])
    camera = boxes["camera"]["position"]
    tops = [(by_key[key], snapped_height(model, by_key[key]["high"][1]))
            for key, model in plan["objects"].items() if by_key[key]["low"][1] < ON_FLOOR_M]
    far_end = boxes["section"]["far_end"]
    objects = [placed(key, model, by_key[key], models[model], camera, outline, tops, far_end)
               for key, model in plan["objects"].items()]
    for item in objects:
        item["yaw"] = wrapped(item["yaw"] + plan.get("turns", {}).get(item["model"], 0.0))
    one_size_per_model(objects, by_key)
    lamps = [[round((by_key[key]["low"][0] + by_key[key]["high"][0]) / 2, 3), round(by_key[key]["high"][1], 3),
              round((by_key[key]["low"][2] + by_key[key]["high"][2]) / 2, 3)] for key in plan.get("lamps", [])]
    return {"camera": boxes["camera"], "section": outline,
            "length": [boxes["section"]["far_end"], BEHIND_CAMERA_M],
            "objects": objects, "lamps": lamps}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("room_folder", type=pathlib.Path, help="WORK/scene/<room>")
    parser.add_argument("plan", type=pathlib.Path)
    parser.add_argument("--boxes", default="boxes.json")
    options = parser.parse_args()
    boxes = json.loads((options.room_folder / options.boxes).read_text())
    models = json.loads((options.room_folder / "models.json").read_text())
    result = layout(boxes, json.loads(options.plan.read_text()), models)
    for model in result["objects"]:
        model["file"] = models[model["model"]]["file"]
    out = options.room_folder / f"layout-{pathlib.Path(options.boxes).stem}.json"
    out.write_text(json.dumps(result, indent=1))
    for item in result["objects"]:
        print(item["key"], item["model"], item["position"], "yaw", item["yaw"], "turn error",
              item["turn_error"], "height", item["height"], "size/box", item["size_against_box"])
    print(out, file=sys.stderr)


if __name__ == "__main__":
    main()
