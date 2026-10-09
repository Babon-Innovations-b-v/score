"""A scene's inventory, data/inventory/<scene>.json: the hard list of exactly what is in the scene,
every row pointing at a box on a kept plan view, and the room's own rows (the scene workflow of
2026-10-04, #121). Nothing is generated for a scene, and nothing placed in it, that is not a row
the owner approved on page A.

    {"scene": "habitat", "place": "habitat",
     "plan": {"world": "<Marble world id>", "seed": 7,
              "views": [{"id": "v1", "picture": "WORK/scene/habitat/views/habitat-north.png"}],
              "dimensioned": ["<the dimensioned plan's plan.json, or its picture when it has no plan.json>"]},
     "approved": "2026-10-05, plan: <world id>",     # the owner's pick on page A; "" until then
     "migrated": "2026-10-06",                        # page C picked, built to it; "" until then
     "room": {"shell": "<shell_hash()>", "light": "place", "backdrop": "", "wall_fill": []},
     "rows": [
       {"id": "r1", "view": "v1", "box": [412, 230, 690, 610], "name": "white louvred locker",
        "kind": "generate", "anchor": "wall", "size": [0.6, 0.5, 1.9], "count": 2,
        "thing": "prop:habitat_locker"},
       {"id": "r2", "view": "v1", "box": [...], "name": "room name sign", "kind": "code",
        "anchor": "wall", "size": [1.3, 0.03, 0.24], "count": 1, "thing": "gear:sign"},
       {"id": "r3", "view": "v2", "box": [...], "name": "workstation desk", "kind": "mechanic",
        "anchor": "floor", "size": [1.6, 0.8, 0.75], "count": 1, "thing": "node:Workstation",
        "prop": "habitat_workstation_desk"},
       {"id": "r4", "view": "v2", "box": [...], "name": "radio", "kind": "generate",
        "anchor": "on:r3", "size": [0.3, 0.2, 0.15], "count": 1, "thing": "prop:habitat_radio"}]}

A row the concept does not show (hidden behind the camera, added for the game) has `"box": null` and says why in
`"unseen"`; the box check (`box_check.py`) holds every other box to the thing it names on the picture.

A row's `kind` is `generate` (a model made from its plan crop), `code` (wall fittings, signs,
moving parts, built from the place's materials) or `mechanic` (a generated model tied to a game
node). Its `anchor` is `floor`, `wall`, `ceiling` or `on:<row id>`; its `size` is wide, deep and
tall in metres; its `thing` is what in the game stands for it, in the words `placed.py` collects
by (`prop:<kind>`, `model:<folder>`, `gear:<kind>`, `scene:<name>`, `code:<script>`,
`mesh:<node>`, `node:<node>`, `machine:<kind>`, `fittings:<name>`). The room's `wall_fill` lists
the kit's wall runs the plan shows (`fill:<set>`); empty leaves the walls bare. `shell` is the
hash of the shell the plan was painted on: a shell changed since fails the check until the room is
repainted or the owner approves again.

    python3 tools/props/scene/inventory.py <scene>      # print the scene's current shell hash
"""
import hashlib
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
INVENTORIES = REPO / "data/inventory"
ROW_KINDS = ("generate", "code", "mechanic")
# `roof`: on a module's roof, outside its shell (the airlock's beacon, modules round).
ANCHORS = ("floor", "wall", "ceiling", "roof")
ROW_FIELDS = ("id", "view", "box", "name", "kind", "anchor", "size", "count", "thing")
ROOM_FIELDS = ("shell", "light", "backdrop", "wall_fill")
# A comment line in a script or a scene, which never changes a shell.
COMMENT = re.compile(r"^\s*(#|;)")

# Scene -> what its shell is made of: whole files, and for a scene built by one big script, the
# constants in it that draw its walls and floors. Comments and blank lines are left out, so a
# reworded comment changes no shell.
MODULE_SHELL_FILES = (
    "game/base/module_shell/module_shell.gd", "game/base/module_shell/shell_steps.gd",
    "game/base/module_shell/shell_lining.gd", "sim/base/stepped_floor.gd",
    "game/base/module_shell/shell_pit.gd", "game/base/module_shell/shell_facets.gd",
)
EARTH_SITE = "game/prologue/earth_site/earth_site.gd"
SHELLS = {
    "habitat": {"files": MODULE_SHELL_FILES, "shell_node": "game/base/habitat/habitat.tscn"},
    # The hub is the habitat's id drawn as the C12 room (2026-10-05): its scene is the same room file.
    "hub": {"files": MODULE_SHELL_FILES, "shell_node": "game/base/habitat/habitat.tscn"},
    "workshop": {"files": MODULE_SHELL_FILES, "shell_node": "game/base/workshop/workshop.tscn"},
    "greenhouse": {"files": MODULE_SHELL_FILES, "shell_node": "game/base/greenhouse/greenhouse.tscn"},
    "airlock": {"files": MODULE_SHELL_FILES, "shell_node": "game/base/airlock/airlock.tscn"},
    "lab": {"files": MODULE_SHELL_FILES, "shell_node": "game/base/lab_room/lab_room.tscn"},
    "prologue_flat": {"constants": (EARTH_SITE, (
        "WALL", "FLOOR_THICKNESS", "FLAT_LEVEL", "FLAT_GROUND", "FLAT_HEIGHT", "BALCONY_GROUND",
        "BALCONY_DOORWAY", "FRONT_DOORWAY", "FRONT_DOOR_Z", "DADO_HEIGHT", "RAIL_HEIGHT"))},
    "prologue_street": {"constants": (EARTH_SITE, (
        "WALL", "STAIRWELL_GROUND", "STREET_GROUND", "STREET_DOORWAY", "STAIR_LANE_A", "STAIR_LANE_B",
        "LANDING_DEPTH", "FLIGHT_RISE", "RISERS", "STEP_THICKNESS", "BUILDING_TOP",
        "ACROSS_THE_ROAD", "ACROSS_THE_ROAD_TOP"))},
    "prologue_square": {"constants": (EARTH_SITE, (
        "CROWD_SPREAD", "BIG_STAGE_AT", "BIG_STAGE_DECK", "PODIUM_AT", "PODIUM_SIZE"))},
}


def path_of(scene, folder=INVENTORIES):
    """Where a scene's inventory lives."""
    return pathlib.Path(folder) / f"{scene}.json"


def every_inventory(folder=INVENTORIES):
    """Scene -> its inventory, for every inventory file there is."""
    folder = pathlib.Path(folder)
    if not folder.is_dir():
        return {}
    return {path.stem: json.loads(path.read_text()) for path in sorted(folder.glob("*.json"))}


def problems(inventory, scene):
    """Everything wrong with an inventory's shape, one line each; none when it is sound."""
    found = []
    if inventory.get("scene") != scene:
        found.append(f"{scene}: its file says it is the scene '{inventory.get('scene')}'")
    for field in ("place", "plan", "approved", "migrated", "room", "rows"):
        if field not in inventory:
            found.append(f"{scene}: no '{field}'")
    room = inventory.get("room", {})
    found.extend(f"{scene}: its room has no '{field}'" for field in ROOM_FIELDS if field not in room)
    views = {view.get("id") for view in inventory.get("plan", {}).get("views", [])}
    rows = inventory.get("rows", [])
    ids = [row.get("id") for row in rows]
    found.extend(f"{scene}: the row id '{name}' is used twice" for name in sorted({i for i in ids if ids.count(i) > 1}))
    for row in rows:
        found.extend(row_problems(scene, row, views, set(ids)))
    if inventory.get("migrated") and not inventory.get("approved"):
        found.append(f"{scene}: migrated without the owner's approval on page A")
    return found


def row_problems(scene, row, views, ids):
    """Everything wrong with one row, one line each."""
    name = f"{scene} row {row.get('id', '?')}"
    found = [f"{name}: no '{field}'" for field in ROW_FIELDS if field not in row]
    if found:
        return found
    if row["view"] not in views:
        found.append(f"{name}: its view '{row['view']}' is not one of the plan's views: no box, no row")
    if row["box"] is None and not row.get("unseen"):
        found.append(f"{name}: no box, and no 'unseen' saying why the concept does not show it")
    elif row["box"] is not None and not (isinstance(row["box"], list) and len(row["box"]) == 4):
        found.append(f"{name}: its box is not four numbers on its view")
    if row["kind"] not in ROW_KINDS:
        found.append(f"{name}: its kind '{row['kind']}' is not one of {', '.join(ROW_KINDS)}")
    anchor = row["anchor"]
    if anchor not in ANCHORS and not (anchor.startswith("on:") and anchor[3:] in ids):
        found.append(f"{name}: its anchor '{anchor}' is not floor, wall, ceiling, roof or on:<a row's id>")
    if not (isinstance(row["size"], list) and len(row["size"]) == 3 and all(side > 0 for side in row["size"])):
        found.append(f"{name}: its size is not three lengths in metres")
    if not (isinstance(row["count"], int) and row["count"] > 0):
        found.append(f"{name}: its count is not a whole number over nought")
    if row["kind"] == "mechanic" and not (row["thing"].startswith("node:") and row.get("prop")):
        found.append(f"{name}: a mechanic row names its game node (node:<name>) and its model's prop kind")
    return found


def approved(inventory):
    """Whether the owner picked this inventory on page A."""
    return bool(inventory.get("approved"))


def migrated(inventory):
    """Whether the scene was built to this inventory and pushed after the owner's pick on page C."""
    return bool(inventory.get("migrated"))


def approved_inventory(path):
    """An inventory the cloud may build from: its file, sound, and approved by the owner; refused
    otherwise, with the reason."""
    path = pathlib.Path(path)
    if not path.is_file():
        raise SystemExit(f"no inventory at {path}: every cloud run builds from an approved scene "
                         "inventory (data/inventory/<scene>.json, owner's page A)")
    inventory = json.loads(path.read_text())
    wrong = problems(inventory, path.stem)
    if wrong:
        raise SystemExit("the inventory is not sound:\n  " + "\n  ".join(wrong))
    if not approved(inventory):
        raise SystemExit(f"{path} is not approved: the owner picks it on page A first")
    return inventory


def code_lines(text):
    """A script's or a scene's lines with comments and blank lines left out."""
    return [line.rstrip() for line in text.splitlines() if line.strip() and not COMMENT.match(line)]


def shell_node_block(scene_text):
    """The lines of the node in a room's scene that the module shell's script is on."""
    shell_id = re.search(r'\[ext_resource [^\]]*path="res://game/base/module_shell/module_shell.gd" id="([^"]+)"\]', scene_text)
    if not shell_id:
        return []
    block, inside = [], False
    for line in scene_text.splitlines():
        if line.startswith("["):
            if inside:
                break
            block = [line]
            continue
        block.append(line)
        if line == f'script = ExtResource("{shell_id.group(1)}")':
            inside = True
    return block if inside else []


def constant_lines(script_text, names):
    """The lines declaring the named constants in a script, in the order of the names."""
    lines = []
    for name in names:
        lines.extend(re.findall(rf"^const {name}\b.*$", script_text, re.MULTILINE))
    return lines


def shell_hash(scene, repo=REPO):
    """The hash of what a scene's shell is made of, as its inventory records it."""
    made_of = SHELLS[scene]
    digest = hashlib.sha1()
    for path in made_of.get("files", ()):
        digest.update("\n".join(code_lines((repo / path).read_text())).encode())
    if "shell_node" in made_of:
        digest.update("\n".join(shell_node_block((repo / made_of["shell_node"]).read_text())).encode())
    if "constants" in made_of:
        path, names = made_of["constants"]
        digest.update("\n".join(constant_lines((repo / path).read_text(), names)).encode())
    return digest.hexdigest()[:16]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in SHELLS:
        raise SystemExit(f"{__doc__}\nscenes: {', '.join(SHELLS)}")
    print(shell_hash(sys.argv[1]))


if __name__ == "__main__":
    main()
