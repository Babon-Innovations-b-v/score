"""Movers: the garage's motion layer as the motion stage wrote it (`score.stages.motion`, the library's
layer/motion.garage): the big door's two leaves sliding open and shut, the rover driving out through it onto the yard,
the beacon lit while the room has no air; over the garage cut at waist height from its own 3D stage. The slider is
the layer's clock."""
import math

from pxr import Usd

from score.stages.library.demo import camera_paths as stage_plan

ALGORITHM = "motion_movers"
PLACE = "garage"
TIMES = (0, 1, 2, 3, 4, 5, 6, 7, 8)  # seconds of the layer's clock the slider stops at: the door's round and the drive
TRAIL = 0.25  # seconds between the points of a mover's drawn path
MOVED = {"south_door_leaf_1": ("Places", "xformOp:translate", "the door's west leaf"),
         "south_door_leaf_2": ("Places", "xformOp:translate", "the door's east leaf"),
         "rover_1": ("Objects", "xformOp:translate:path", "the rover")}
BEACON = "/garage/Lights/big_door_beacon"


def attribute(stage, scope, name, op):
    return stage.GetPrimAtPath(f"/{PLACE}/{scope}/{name}").GetAttribute(op)


def plan_at(value):
    return [round(float(value[0]), 2), round(float(-value[2]), 2)]


def trail(stage, attr, until):
    """A mover's plan points from the layer's start to `until` seconds, every TRAIL seconds."""
    rate = stage.GetTimeCodesPerSecond()
    steps = int(until / TRAIL) + 1
    return [plan_at(attr.Get(rank * TRAIL * rate)) for rank in range(steps)]


def heading(stage, seconds):
    """The rover's forward on the plan at a moment: its own +z turned by its path's turn."""
    turn = math.radians(attribute(stage, "Objects", "rover_1", "xformOp:rotateY:path").Get(
        seconds * stage.GetTimeCodesPerSecond()) or 0.0)
    return [round(math.sin(turn), 3), round(-math.cos(turn), 3)]


def moment(stage, seconds):
    """Every mover where the layer has it at `seconds`, the rover's path so far, and the beacon lit or dark."""
    rate = stage.GetTimeCodesPerSecond()
    shapes = []
    for name, (scope, op, label) in MOVED.items():
        attr = attribute(stage, scope, name, op)
        shapes.append({"kind": "path" if name == "rover_1" else "line", "points": trail(stage, attr, seconds),
                       "tone": "accent" if name == "rover_1" else "c3", "label": f"{label} so far",
                       **({"look": [heading(stage, rank * TRAIL) for rank in range(int(seconds / TRAIL) + 1)]}
                          if name == "rover_1" else {})})
        shapes.append({"kind": "dots", "points": [plan_at(attr.Get(seconds * rate))], "r": 0.6, "id": name,
                       "tone": "accent" if name == "rover_1" else "c3", "label": label})
    beacon = stage.GetPrimAtPath(BEACON)
    lit = (beacon.GetAttribute("inputs:intensity").Get(seconds * rate) or 0) > 0
    shapes.append({"kind": "dots", "points": [plan_at(beacon.GetAttribute("xformOp:translate").Get())], "r": 0.5,
                   "tone": "warn" if lit else "ghost", "label": "the beacon, lit" if lit else "the beacon, dark"})
    return shapes


def made(inputs):
    layer = inputs.library(f"layer/motion.{PLACE}@1", "layer.usda")
    seconds = inputs.json(f"layer/motion.{PLACE}@1", "movers.json")["seconds"]
    camera = stage_plan.camera_code(inputs.repo)
    still = camera.place_scenes(stage_plan.fetched_stage(inputs, PLACE))["still"]
    stage = Usd.Stage.Open(str(layer))
    walls = stage_plan.waist_lines(still)
    end = TIMES[-1]
    shown = [point for shape in walls + moment(stage, end) for point in shape["points"]]
    xs, ys = [point[0] for point in shown], [point[1] for point in shown]
    return {
        "example": f"the {PLACE}'s big door and its rover",
        "view": "plan", "bounds": [min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1],
        "steps": [
            {"label": "The garage cut at waist height, from its own 3D stage", "shapes": walls},
            {"label": "What the layer moves, where each stands at the start", "shapes": moment(stage, 0)},
            {"label": f"The first {end} seconds: the leaves slide open and shut, the rover drives out, the beacon "
                      "blinks", "shapes": moment(stage, end)}],
        "slider": {"label": "time", "unit": "s", "values": list(TIMES), "at": len(TIMES) - 1,
                   "shapes": [moment(stage, each) for each in TIMES]},
        "numbers": [{"label": "movers", "value": len(MOVED) + 1, "unit": "",
                     "tip": "things the layer moves or switches: two door leaves, the rover, the beacon"},
                    {"label": "round", "value": seconds, "unit": "s", "tip": "the layer's whole length, it loops"}]}
