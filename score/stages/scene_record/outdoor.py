"""The outdoor shell writer (plan `kind` "outdoor": the wreck, the old station, the camp grounds): a place with no
walls, whose ground is the terrain stage's place layer and whose things are its inventory rows. Its record holds what
stands round those and over them, every entry from the plan, the inventory, the seats or the world body's sky record:

    structure    the sky's bodies (the Earth over the Moon): each sphere hung its record's distance out along its way
                 from the place, turned by its axes, both turned from the body's frame into the place's by its seat
    lights       the body's suns (data/definitions/sky.json `outdoor`) turned into the place's frame, and each plan
                 lamp's light at its inventory row's laid spot on the made ground, `high` up the row's height
    environment  the body's outdoor sky record, with each plan beam (a column of light) stood on its row's spot, up
                 straight out from the body's middle there
    ground_decals  each plan decal (what is painted on the near ground: the wreck's burn), coloured by its design token
    objects      each plan item a released world model makes (the plan's `objects`: the camp grounds' boot rock, the
                 camp's furniture), on the made ground (on the place's own floor inside its kit's walls); one whose
                 model is not made yet carries the plan's `waiting` (the camp grounds' cairn)
    blocks       each plan block (structure: a plain box outside the kit, the camp airlock's footing and ramp)
    views        one from each of the plan's standing spots, at eye height over the made ground, to the site's middle
    places       every other place seated on the same made ground (writer.neighbours)

The floor is the plan's site (its w and d, laid by its frame): the openings gate's probes stand over it. A place
inside its kit's walls on open ground (the camp's domes, plan `inside`) gets the body's outdoor sky too (its windows
see it), its lamps where the kit hangs them, its ceiling and its views from its own floor.
"""
import json
import pathlib

import numpy as np

from score.stages.scene_record import kit_shell, writer


def tokens_of(path):
    """Each design token's value by its name."""
    found = {}

    def walk(value):
        if isinstance(value, dict):
            if "name" in value and isinstance(value.get("value"), str):
                found[value["name"]] = value["value"]
            for inner in value.values():
                walk(inner)
        elif isinstance(value, list):
            for inner in value:
                walk(inner)
    walk(json.loads(pathlib.Path(path).read_text()))
    return found


def srgb(hex_colour):
    """A #rrggbb colour as three sRGB shares."""
    return [round(int(hex_colour[index:index + 2], 16) / 255.0, 6) for index in (1, 3, 5)]


def in_place(way, laid):
    """A way in the body's frame turned into the place's (rows: across, up, along)."""
    return np.asarray(way, dtype=float) @ laid.frame.T


def bodies(sky, laid):
    """The sky's bodies, each a sphere hung out along its way from the place."""
    found = []
    for body in sky.get("bodies", []):
        at = in_place(body["way"], laid) * float(body["distance"])
        axes = np.asarray(body["axes"], dtype=float) @ laid.frame.T
        found.append({"name": body["name"], "builder": "sphere", "centre": [0.0, 0.0, 0.0], "radius": body["radius"],
                      "surface": body["surface"], "plain": "sky", "placed_at": np.round(at, 2).tolist(),
                      "placed_turn": writer.quaternion(axes),
                      "from": f"sky record (data/definitions/sky.json) {body['name']}, turned into the place's frame "
                              "by its seat"})
    return found


def suns(sky, laid, body):
    """The sky's suns, their ways turned into the place's frame; the main sun unnamed, as the stage builds it."""
    found = []
    for sun in sky["suns"]:
        toward = in_place(sun["toward"], laid)
        entry = {"type": "sun", "toward": np.round(toward / np.linalg.norm(toward), 5).tolist(),
                 "colour": sun["colour"], "energy": sun["energy"], "shadows": sun["shadows"],
                 "from": f"sky record (data/definitions/sky.json) {body} outdoor {sun['name']}, turned into the "
                         "place's frame by its seat"}
        if sun["name"] != "sun":
            entry["name"] = sun["name"]
        found.append(entry)
    return found


def row_spots(inventory):
    """Each inventory row's laid spots (x, y, z) and its size."""
    return {row["id"]: ([[spot["x"], spot.get("y", 0.0), spot["z"]] for spot in row.get("at", []) if "x" in spot],
                        row.get("size", [0.0, 0.0, 0.0])) for row in inventory["rows"]}


def on_ground(laid, spot, lift=0.0):
    """A row's laid spot stood on the made ground (a row's y is its height over the ground, as the export stands
    it), `lift` higher."""
    return laid.standing(spot[0], spot[2], spot[1] + lift)[0]


def lamp_spots(lamp, rows, laid, kit):
    """Where a plan lamp's lights stand: each laid spot of its row, `high` up the row's height over the made ground;
    a row the inventory lays nowhere at each lamp the kit hangs of it (kit_shell.lamp_spots)."""
    spots, size = rows[lamp["row"]]
    if not spots:
        return kit_shell.lamp_spots(kit, lamp["row"], lamp), "as the kit hangs it"
    return [on_ground(laid, spot, float(size[2]) * float(lamp["high"])) for spot in spots], \
        f"its laid spot on the made ground, {lamp['high']} of its height up"


def lamps(plan, rows, laid, kit):
    """Each plan lamp's light at each of its row's lamps (lamp_spots)."""
    found = []
    for lamp in plan["lamps"]:
        spots, said = lamp_spots(lamp, rows, laid, kit)
        for at in spots:
            found.append({"type": "omni", "at": np.round(at, 4).tolist(), "colour": lamp["colour"],
                          "energy": lamp["energy"], "range": lamp["range"], "attenuation": lamp["attenuation"],
                          "shadows": lamp["shadows"],
                          "from": f"plan lamp {lamp['name']} ({lamp['why']}): inventory row {lamp['row']}, "
                                  f"{said}"})
    return found


def beam_foot(beam, rows, laid, grounds, kits):
    """A beam's foot and way up in this place's frame: on its row's first laid spot here, or, for a beam of another
    place (`place`: the camp sees the camp grounds' mast), on the first piece of the row that place's kit lays, stood
    on that place's made ground and brought into this frame through the two seats."""
    if not beam.get("place"):
        foot = on_ground(laid, rows[beam["row"]][0][0])
        way = in_place(laid.direction(laid.frame, laid.origin, foot[0], foot[2]), laid)
        return foot, way
    other = grounds[beam["place"]].laid
    kit = writer.read(pathlib.Path(kits) / f"{beam['place']}.json")
    piece = next((piece for piece in kit["pieces"] if piece["kind"] == f"{beam['place']}_{beam['row']}"), None)
    if piece is None:
        raise ValueError(f"beam {beam['name']}: {beam['place']}'s kit lays no {beam['row']}")
    foot = on_ground(other, piece["at"])
    way = in_place(other.direction(other.frame, other.origin, foot[0], foot[2]), other)
    position, axes = writer.pose_in(laid, other)
    return position + foot @ axes, way @ axes


def beams(plan, rows, laid, grounds, kits):
    """Each plan beam on its row's first laid spot, straight up out of the body's middle there (beam_foot)."""
    found = []
    for beam in plan["beams"]:
        foot, way = beam_foot(beam, rows, laid, grounds, kits)
        whose = f"{beam['place']}'s kit's" if beam.get("place") else "inventory"
        found.append({"name": beam["name"], "foot": np.round(foot, 4).tolist(),
                      "way": np.round(way / np.linalg.norm(way), 6).tolist(),
                      **{key: beam[key] for key in ("low", "high", "radius", "sides", "least_half_angle", "colour",
                                                    "glow")},
                      "from": f"plan beam {beam['name']} ({beam['why']}): on {whose} row {beam['row']}'s laid "
                              "spot on the made ground, straight up out of the body's middle there"})
    return found


def decals(plan, tokens):
    """Each plan decal, its colour its design token's."""
    return [{"name": decal["name"], "centre": [decal["centre"][0], 0.0, decal["centre"][1]],
             **{key: decal[key] for key in ("radius", "solid", "rays", "ray_reach", "seed")},
             "colour": srgb(tokens[decal["token"]]),
             "from": f"plan decal {decal['name']} (concept element: {decal['element']}), coloured by design token "
                     f"{decal['token']}"} for decal in plan["decals"]]


def environment(sky, body, plan, rows, laid, grounds, kits):
    """The body's outdoor sky record, with the plan's beams."""
    found = {**json.loads(json.dumps(sky["environment"])),
             "from": f"sky record (data/definitions/sky.json) {body} outdoor"}
    stood = beams(plan, rows, laid, grounds, kits)
    if stood:
        found["beams"] = stood
    return found


def yawed(degrees):
    """A turn about up by `degrees` (rows: the turned x, y, z axes)."""
    turn = np.radians(degrees)
    return np.array([[np.cos(turn), 0.0, -np.sin(turn)], [0.0, 1.0, 0.0], [np.sin(turn), 0.0, np.cos(turn)]])


def objects(plan, laid):
    """Each plan item a released world model makes (the plan's `objects`), on the made ground at its item's middle, its
    model's lowest point on the ground (kit_shell.model_low), turned by its `yaw` and tipped with the ground's seat
    there."""
    found = []
    for item in plan["items"]:
        made = plan["objects"].get(item["name"])
        if made is None:
            continue
        low_x, low_z, high_x, high_z = item["box"]
        lift = made.get("level", 0.0) + kit_shell.model_low(made)
        at, own = laid.standing((low_x + high_x) / 2, (low_z + high_z) / 2, lift)
        found.append({"name": made["name"], "model": made["model"], "at": np.round(at, 4).tolist(),
                      "rotation": writer.quaternion(yawed(made.get("yaw", 0.0)) @ own),
                      **{key: made[key] for key in ("row", "height", "kind", "waiting") if key in made},
                      "from": f"plan item {item['name']!r}: the released model {made['model']} ({made['why']}), on "
                              "the made ground"})
    return found


def blocks(plan):
    """Each plan block: a plain box stood where the plan says, turned as it says."""
    return [{"name": block["name"], "builder": block["builder"], "centre": [0.0, 0.0, 0.0], "size": block["size"],
             "surface": block["surface"], "placed_at": block["at"], "placed_turn": block["turn"],
             "plain": block["plain"], "from": f"plan block {block['name']} ({block['why']})"}
            for block in plan["blocks"]]


def views(plan, laid, eye_height):
    """One view from each standing spot, at eye height over the made ground, to the site's middle or the plan item
    it looks at, on the made ground."""
    found = []
    for number, spot in enumerate(plan["standing"], 1):
        aim = writer.item_middle(plan, spot["looks_at"]) if spot["looks_at"] else writer.middle_of(plan)
        eye = laid.standing(spot["at"][0], spot["at"][1], spot["level"] + eye_height)[0]
        found.append({"name": f"spot-{number}", "eye": np.round(eye, 3).tolist(),
                      "aim": np.round(laid.standing(aim[0], aim[1], writer.AIM_HEIGHT)[0], 3).tolist(),
                      "fov": writer.VIEW_FOV,
                      "from": f"plan standing spot {number}, at eye height over the made ground, looking to " +
                              (f"plan item {spot['looks_at']!r}" if spot["looks_at"] else "the site's middle")})
    return found


def record_of(place, plan, inputs, grounds):
    """The outdoor place's scene record (module docstring)."""
    seated = grounds[place]
    body, laid = seated.ground, seated.laid
    sky = writer.read(inputs["sky"])[body]["outdoor"]
    rows = row_spots(writer.read(inputs["inventory"]))
    kit = writer.read(pathlib.Path(inputs["kits"]) / f"{place}.json")
    eye = writer.read(inputs["places"])["shared"]["scale"]["eye_height"]
    record = {"place": place,
              "about": f"{plan['title']}, written by SCORE's scene-record stage from its plan "
                       f"(data/plans/{place}.json), "
                       "its inventory, the made ground's seats and the world's sky record; the ground and its rocks "
                       "are the terrain stage's place layer. Frame: the place's seat, x across, z along, y up.",
              "floor": plan["floor"], "inside": plan["inside"],
              "structure": bodies(sky, laid) + blocks(plan),
              "lights": suns(sky, laid, body) + lamps(plan, rows, laid, kit),
              "environment": environment(sky, body, plan, rows, laid, grounds, inputs["kits"]),
              # A place inside its kit's walls is viewed from its own floor, not the ground under it.
              "views": writer.views(plan, eye) if plan["inside"] else views(plan, laid, eye),
              "places": writer.places_of(place, plan, inputs, grounds)}
    if plan["inside"]:
        record["ceiling"] = round(plan["floor_height"] + plan["walls"]["high"], 4)
    if plan["decals"]:
        record["ground_decals"] = decals(plan, tokens_of(inputs["tokens"]))
    if plan["objects"]:
        record["objects"] = kit_shell.objects(plan, kit) if plan["inside"] else objects(plan, laid)
    return record
