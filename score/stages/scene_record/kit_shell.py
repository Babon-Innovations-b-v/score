"""The scene record of a place whose kit holds its own walls and floors (plan shell `kit`): the Earth's rooms (the flat,
the stairwell) and its open places (the street, the square, the launch view). The record holds what the kit does not:

    structure    the block a room stands in (the plan's `block`): its mass over the room, from the storey line over the
                 room's ceiling to the block's roof over the block's whole footprint, and its mass under the room, from
                 the street to just under the room's floor over the room's floor grown by the block's walls; none for
                 an open place
    lights       one at each lamp the kit lays of the scene's glowing rows (each inventory row whose row kind glows,
                 score/stages/row_kinds.py): on its glow part's middle, else just in front of the piece; its numbers
                 the library's lamp (data/library/lamps.json) for the row's mount, its reach from how high the row's
                 lamps hang over the plan's floor; a row the plan aims (`aims`) the library's aimed lamp, a spot
                 aimed where the plan says, reaching past what it aims at, with its shaft
    environment  the body's night air (the sky record), its haze ring standing on the body's shared ground
    kit_glow, water   the body's (the sky record), in the place's frame; the water at the made ground's level
    objects      each plan item a released world model makes (the plan's `objects`), on its item's middle
    places       the seated places (writer.neighbours) and what the plan `shows` (the far city), where its frame stands

The body's shared frame is the frame its sky record's numbers are written in (`frame_of`: the street's, EarthSite's
own); the made ground's seats stand it in this place's frame. Its sky (the Moon, its light, the stars) is the
environment concept's physics, the light layer's (score/stages/light/sky.py), never the record's.
"""
import json
import math
import pathlib

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
# A kit floor piece is what a plan object stands on when its top lies this near the plan's level (metres).
SUPPORT_REACH = 0.5

# A light stands this far in front of a lamp piece with no glow part (metres), as a kit lamp's does.
LAMP_OUT = 0.05
# Two pieces of one lamp row this close are one lamp (a cage and its lens).
SAME_LAMP = 0.3
# The block's mass under a room stops this far under the room's floor (the kit's floorboards lie on it).
UNDER_FLOOR = 0.02


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def shared_pose(place, grounds, sky, pose_in):
    """The body's shared frame (its sky record's `frame_of` place) in this place's frame: (position, axes)."""
    if sky["frame_of"] == place:
        return np.zeros(3), np.eye(3)
    return pose_in(grounds[place].laid, grounds[sky["frame_of"]].laid)


def in_place(point, pose):
    position, axes = pose
    return np.asarray(point, dtype=float) @ axes + position


# --- the block --------------------------------------------------------------------------------------------------

def over_from(plan):
    """Where the block's mass over a room starts: the first storey line at or over the room's ceiling."""
    walls, block = plan["walls"], plan["block"]
    storeys = (plan["floor_height"] + walls["high"] - block["street"]) / walls["storey"]
    return block["street"] + math.ceil(storeys - 1e-6) * walls["storey"]


def box_entry(name, low, high, surface, said):
    low, high = np.asarray(low, dtype=float), np.asarray(high, dtype=float)
    return {"name": name, "builder": "box", "centre": np.round((low + high) / 2, 4).tolist(),
            "size": np.round(high - low, 4).tolist(), "surface": surface, "plain": "shell", "from": said}


def block(plan):
    """The block's masses over and under the room (module docstring); none without a block."""
    found = plan.get("block")
    if not found:
        return []
    said = f"plan block ({found['why']})"
    (low_x, low_z), (high_x, high_z) = found["low"], found["high"]
    over = over_from(plan)
    entries = [box_entry("block_over", [low_x, over, low_z], [high_x, found["top"], high_z], found["surface"],
                         f"{said}: over the room from the storey line {over:g} m (floor to floor "
                         f"{plan['walls']['storey']} m over the street) to its roof")]
    floor = plan["floor_height"]
    if floor - found["street"] > UNDER_FLOOR:
        (room_low_x, room_low_z), (room_high_x, room_high_z) = plan["floor"]
        wall = found["wall"]
        entries.append(box_entry(
            "block_under", [max(low_x, room_low_x - wall), found["street"], max(low_z, room_low_z - wall)],
            [min(high_x, room_high_x + wall), floor - UNDER_FLOOR, min(high_z, room_high_z + wall)],
            found["surface"], f"{said}: under the room's floor (the plan's inside grown by the block's {wall} m "
                              f"walls) down to the street"))
    return entries


# --- lights -----------------------------------------------------------------------------------------------------

def lamp_spots(kit, row, lamp):
    """Each lamp of an inventory row the kit lays: its glow parts' middles, else each piece's middle just in front of
    it (a kit piece's front is against its z); the lamp row's `out` and `rise` (metres in front and up) when it names
    them. A row's pieces this close together are one lamp (a cage and its lens)."""
    kind = f"{kit['room']}_{row}"
    pieces = [piece for piece in kit["pieces"] if piece["kind"] == kind]
    glows = [piece for piece in pieces if piece.get("part") == "glow"]
    found = []
    for piece in glows or [piece for piece in pieces if "part" not in piece]:
        size = np.asarray(piece["size"], dtype=float)
        up, front = np.asarray(piece["y"], dtype=float), -np.asarray(piece["z"], dtype=float)
        out = lamp.get("out", 0.0 if glows else size[2] / 2 + LAMP_OUT)
        spot = np.asarray(piece["at"], dtype=float) + up * (size[1] / 2 + lamp.get("rise", 0.0)) + front * out
        if all(np.linalg.norm(spot - other) > SAME_LAMP for other in found):
            found.append(spot)
    return found


def aim_of(plan, aim):
    """Where a spot lamp row aims: the middle of the plan item it names, `up` metres over the place's floor."""
    item = next(item for item in plan["items"] if item["name"] == aim["at"])
    low_x, low_z, high_x, high_z = item["box"]
    return [round((low_x + high_x) / 2, 4), round(plan["floor_height"] + aim.get("up", 0.0), 4),
            round((low_z + high_z) / 2, 4)]


def game_lamp():
    """The game lamp the library's strengths are shares of (tools/usd/scene.py): (energy, colour, attenuation)."""
    import sys
    sys.path.insert(0, str(REPO / "tools/usd"))
    import scene
    return scene.LAMP_ENERGY, scene.LAMP_COLOUR, scene.LAMP_ATTENUATION


def library_lamps():
    """The library's lamp code (tools/props/scene/lamps.py: its mounts, its aimed lamp)."""
    import sys
    sys.path.insert(0, str(REPO / "tools/props/scene"))
    import lamps as library
    return library


def hung_light(row, spots, floor, library, path, rows):
    """A glowing row's light at the library's lamp for its mount (among its inventory's `rows`): its reach from how
    high its lamps hang over the floor (their middle), in the game lamp's numbers."""
    energy, colour, attenuation = game_lamp()
    high = float(np.median([spot[1] for spot in spots])) - floor
    light = library.light_at(row, high, rows, library.mounts(path), library.mount_words(path))
    return {"type": "omni", "colour": colour, "energy": round(energy * light["strength"], 4), "range": light["reach"],
            "attenuation": attenuation, "shadows": light["shadows"],
            "from": f"library lamp (data/library/lamps.json) for its mount, {high:.2f} m over the floor"}


def aimed_light(plan, row, spot, library, path):
    """A glowing row the plan aims: the library's aimed lamp, a spot at what the plan says, reaching past it."""
    energy = game_lamp()[0]
    lamp, aim = library.aimed(path), plan["aims"][row["id"]]
    target = aim_of(plan, aim)
    reach = round(float(lamp["reach_per_aim"]) * float(np.linalg.norm(np.asarray(target) - spot)), 2)
    strength = float(lamp["strength_per_reach"]) * reach
    return {"type": "spot", "colour": lamp["colour"], "energy": round(energy * strength, 4), "range": reach, "angle": lamp["angle"], "attenuation": lamp["attenuation"], "shadows": lamp["shadows"],
            "shaft": lamp["shaft"], "aim": target,
            "from": f"library aimed lamp (data/library/lamps.json), aimed at plan item {aim['at']!r}"}


def lamps(plan, kit, glowing, path, rows=()):
    """A light at each lamp the kit lays of the scene's glowing rows (`glowing`: its inventory rows whose row kind
    glows, row_kinds.rows_that; `rows` all of them, what a row is mounted on), numbers from the library's lamp
    (`path`: data/library/lamps.json; module docstring)."""
    library = library_lamps()
    found = []
    for row in glowing:
        spots = lamp_spots(kit, row["id"], {})
        aimed = row["id"] in plan.get("aims", {})
        hung = None if aimed or not spots else hung_light(row, spots, plan["floor_height"], library, path, rows)
        for number, spot in enumerate(spots, 1):
            light = aimed_light(plan, row, spot, library, path) if aimed else dict(hung)
            light.update(at=np.round(spot, 4).tolist(),
                         **{"from": f"inventory row {row['id']} (row kind {row['row_kind']}, it glows), its lamp "
                                    f"{number} as the kit lays it; {light['from']}"})
            found.append(light)
    return found


# --- the body's air, glow and water -------------------------------------------------------------------------------

def environment(plan, sky, pose):
    """The body's night air, inside or out as the plan says, its haze ring standing on the shared ground."""
    night = sky["night"]
    ground = float(pose[0][1])
    haze = dict(night["haze"])
    haze.update({"low": round(ground, 4), "high": round(ground + haze.pop("tall"), 4)})
    return {**{key: value for key, value in night.items() if key not in ("haze", "from")}, "inside": plan["inside"],
            "haze": haze,
            "from": f"sky record (data/definitions/sky.json) {sky['body']} night ({night['from']}); the haze ring on "
                    f"the shared ground ({sky['frame_of']}'s frame, its seat)"}


def water(sky, made, pose):
    """The body's water at the made ground's level, its mirror's lit columns on the shared ground."""
    harbour = sky["harbour"]
    level = float(pose[0][1]) + float(made["water"]["level"])
    mirror = {**harbour["mirror"], "lit": [
        {**column, "at": np.round(in_place([column["at"][0], 0.0, column["at"][1]], pose)[[0, 2]], 4).tolist(),
         "low": round(float(pose[0][1]) + column["low"], 4), "high": round(float(pose[0][1]) + column["high"], 4)}
        for column in harbour["mirror"]["lit"]]}
    low = in_place([harbour["low"][0], 0.0, harbour["low"][1]], pose)
    high = in_place([harbour["high"][0], 0.0, harbour["high"][1]], pose)
    return [{"name": "harbour", "builder": "grid", "low": np.round(low[[0, 2]], 4).tolist(),
             "high": np.round(high[[0, 2]], 4).tolist(), "height": round(level, 4), "surface": made["water"]["surface"],
             "step": harbour["step"], "mirror": mirror,
             "from": f"the made ground's water (terrain stage: level {made['water']['level']} m, surface "
                     f"{made['water']['surface']}); its reach and mirror from the sky record (data/definitions/"
                     f"sky.json) {sky['body']} harbour ({harbour['from']})"}]


def kit_glow(sky):
    return {**{key: value for key, value in sky["kit_glow"].items() if key != "from"},
            "from": f"sky record (data/definitions/sky.json) {sky['body']} kit_glow ({sky['kit_glow']['from']})"}


# --- objects and shown places -----------------------------------------------------------------------------------

def kit_floors(kit, every=False):
    """The kit's floor pieces (its kinds' group `floors`), or with `every` all its pieces (a ground-free room's walls,
    roof and shut leaves too: it is judged against its own walls), as box entries round each piece (x across and z out
    centred on its `at`, y up from it).
    shortcut: a box round the piece, exact for a piece square to the axes (every Earth floor), wider for a turned one."""
    floors = {kind for kind, about in kit.get("kinds", {}).items() if every or about.get("group") == "floors"}
    found = []
    for number, piece in enumerate(piece for piece in kit.get("pieces", []) if piece["kind"] in floors):
        axes = np.array([piece[axis] for axis in ("x", "y", "z")], dtype=float)
        size = np.asarray(piece["size"], dtype=float)
        corners = np.array([[across, up, out] for across in (-0.5, 0.5) for up in (0.0, 1.0) for out in (-0.5, 0.5)])
        laid = np.asarray(piece["at"], dtype=float) + (corners * size) @ axes
        low, high = laid.min(axis=0), laid.max(axis=0)
        found.append({"name": f"kit_floor_{number}", "builder": "box", "centre": ((low + high) / 2).tolist(),
                      "size": (high - low).tolist(), "surface": "kit_floor"})
    return found


def model_low(made):
    """How far a plan object's released world model's lowest point lies under its origin once stood as the record
    stands it (scaled to its `height`, pressed by its `stretch`): metres, positive downward (the rocket's base 6 mm
    under its origin); 0 for an object still `waiting` on its model, or one whose model is a gap (not in the library:
    the scene leaves it out)."""
    if made.get("waiting"):
        return 0.0
    model, height, stretch = made["model"], made.get("height"), made.get("stretch")
    import sys
    import trimesh
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/usd"))
    import scene
    found = scene.world_file(None, model)
    if found is None:
        return 0.0
    low, high = trimesh.load(str(found), force="scene").bounds
    scale = float(height) / float(high[1] - low[1]) if height else 1.0
    return -float(low[1]) * scale * (float(stretch[1]) if stretch else 1.0)


def support(kit, across, along, nominal):
    """The top of what a plan object stands on at (across, along): the highest of the kit's floor pieces under that
    spot that tops out within SUPPORT_REACH of the plan's level, else the plan's level itself."""
    tops = [box["centre"][1] + box["size"][1] / 2 for box in kit_floors(kit or {})
            if abs(across - box["centre"][0]) <= box["size"][0] / 2 and abs(along - box["centre"][2]) <= box["size"][2] / 2]
    near = [top for top in tops if abs(top - nominal) <= SUPPORT_REACH]
    return max(near) if near else nominal


def objects(plan, kit=None):
    """Each plan item a released world model makes (the plan's `objects`), on its item's middle, its model's lowest
    point on the top of what it stands on (support: the kit's floor pieces there, else the plan's floor at its level),
    never its origin at the plan's level."""
    found = []
    for item in plan["items"]:
        made = plan["objects"].get(item["name"])
        if made is None:
            continue
        low_x, low_z, high_x, high_z = item["box"]
        across, along = (low_x + high_x) / 2, (low_z + high_z) / 2
        top = support(kit, across, along, plan["floor_height"] + made.get("level", 0.0))
        entry = {"name": made["name"], "model": made["model"],
                 "at": [round(across, 4), round(top + model_low(made),
                                                4), round(along, 4)],
                 **{key: made[key] for key in ("row", "yaw", "height", "stretch", "kind") if key in made},
                 "from": f"plan item {item['name']!r}: the released model {made['model']} ({made['why']})"}
        found.append(entry)
    return found


def shown(plan, place, grounds, pose_in, quaternion):
    """Each place the plan shows that no made ground seats, where the frame it is laid in stands (its `as`)."""
    found = []
    for name, show in sorted(plan["shows"].items()):
        position, axes = (np.zeros(3), np.eye(3)) if show["as"] == place else \
            pose_in(grounds[place].laid, grounds[show["as"]].laid)
        found.append({"name": name, "stage": show["stage"], "at": np.round(position, 4).tolist(),
                      "rotation": quaternion(axes),
                      "from": f"plan shows {name} ({show['why']}), laid in {show['as']}'s frame, its seat"})
    return found
