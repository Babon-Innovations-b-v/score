"""Settle at work in the workshop: every loose object where it came to rest (settle.json of the library's settle
layer entry), sorted by what the settle did to it: let down onto what holds it, dropped and turned to rest, carried
with what it lies on, or left as laid; each object's own sentence is its label."""
from score.stages.library.demo import _trial

ALGORITHM = "settle"
PLACE = "workshop"
ENTRY = f"layer/settle.{PLACE}@1"
# What the settle did, by the start of its sentence (settle.json `said`), in the order the steps show them.
DONE = (("moved", "c1", "Let straight down onto what holds it"),
        ("turns", "c2", "Dropped: turned and slid a little to rest"),
        ("stood", "c2", "Stood upright or flush on the slope under it"),
        ("carried", "c3", "Carried along with what it lies on"),
        ("", "warn", "Left as laid, where settling would make it rest worse"))


def plan_point(east, south):
    return [round(float(east), 2), round(float(-south), 2)]


def rest_of(matrix):
    """Where an object rests in plan: its matrix's translation (column vectors)."""
    return plan_point(matrix[0][3], matrix[2][3])


def done_of(said):
    return next(index for index, (start, _, _) in enumerate(DONE) if said.startswith(start))


def floor_outline(scene):
    (low_x, low_z), (high_x, high_z) = scene["floor"]
    return [plan_point(x, z) for x, z in ((low_x, low_z), (high_x, low_z), (high_x, high_z), (low_x, high_z))]


def made(inputs):
    record = inputs.json(ENTRY, "settle.json")
    scene = _trial.scene(inputs, PLACE)
    objects = record["objects"]
    done = {name: done_of(entry["said"]) for name, entry in objects.items()}
    steps = [{"label": "Every loose object of the room",
              "shapes": [{"kind": "area", "points": floor_outline(scene), "tone": "ground", "label": "the floor"},
                         *[{"kind": "dots", "points": [rest_of(entry["matrix"])], "r": 0.3, "tone": "ghost",
                            "id": name, "label": name.replace("_", " ")} for name, entry in objects.items()]]}]
    for index, (_, tone, label) in enumerate(DONE):
        own = [name for name in objects if done[name] == index]
        if own:
            steps.append({"label": f"{label}: {len(own)} objects", "shapes": [
                {"kind": "dots", "points": [rest_of(objects[name]["matrix"])], "r": 0.3, "tone": tone, "id": name,
                 "label": f"{name.replace('_', ' ')}: {objects[name]['said']}"} for name in own]})
    (low_x, low_z), (high_x, high_z) = scene["floor"]
    return {"example": f"the {PLACE}'s {len(objects)} loose objects", "view": "plan",
            "bounds": [low_x - 0.5, -high_z - 0.5, high_x + 0.5, -low_z + 0.5], "steps": steps,
            "numbers": [{"label": "objects", "value": len(objects), "unit": "", "tip": "loose objects settled"},
                        {"label": "at rest", "value": sum(entry["rested"] for entry in objects.values()), "unit": "",
                         "tip": "objects the settle laid where they rest"}]}
