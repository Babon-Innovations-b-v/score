"""The earth seed row's own checks, with no spend: every row that read a round-three seed or an old kit reads
earth-seed instead, a reader is handed its seeds and design kits under their old names, the export leaves out and
names a piece no row made, and the gates fail by name; a shell stands round its locked plan (a room's deck, walls and
roof, an open place's raised levels; every other shell and every stair the scene record's, each laid once), each part
painted from the scene's own surface library or named missing, and a design base passes the seed gates, the
placeholder gate and the collision gate.

Run: .venv/bin/python score/stages/earth_seed/earth_seed_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

import numpy

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks, stages  # noqa: E402
from score.stages import earth_seed  # noqa: E402
from score.stages.earth_seed import design_shell  # noqa: E402

PLACES = ("hangar", "wreck", "street", "airlock", "launch", "camp")


def write(folder, name, record):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(record))
    return folder / name


def test_the_kit_adapter_is_on_the_loop_with_nothing_after_it():
    """The kit adapter stays on the loop with no after-step; the old kits' rows (earth-kit, kit-sections) and their
    layer are gone (the old kits were retired, 2026-10-21)."""
    from score.stages import assembly, shapes_first
    assert shapes_first.KIT in shapes_first.ADAPTERS and shapes_first.KIT.layer == earth_seed.KIT_LAYER
    assert shapes_first.KIT.after == ()
    names = {row.name for row in stages.STAGES}
    assert not names & {"earth-kit", "kit-sections"}, names & {"earth-kit", "kit-sections"}
    assert "kit-sections" not in assembly.LAYERS
    assert stages.EARTH_SEED.after == {"surface-library": ("surface-library", 1)}


def test_no_row_reads_an_earth_place_s_round_three_seed_or_old_kit():
    readers = set()
    for row in stages.STAGES:
        for place in PLACES:
            if row.applies is not None and not row.applies(place):
                continue
            found = row.files(place) if callable(row.files) else row.files
            if any(stages.read_from_seed(path, place) for path in found.values()):
                readers.add(row.name)
    assert not readers, readers  # terrain-look, the last, retired (#27)
    reading = {row.name for row in stages.STAGES if "earth-seed" in row.after} - {stages.library.PLACE_ROW}
    assert reading == set(stages.EARTH_SEEDED), reading ^ set(stages.EARTH_SEEDED)


def test_a_reader_gets_its_seeds_and_design_kits_under_their_old_names():
    root = pathlib.Path(tempfile.mkdtemp())
    kept = earth_seed.DESIGN
    with_designs({"airlock": {}, "hub": {}}, root / "design")
    try:
        for node, place in (("own", "airlock"), ("hub", "hub")):
            (root / node / place).mkdir(parents=True)
        inputs = {"earth-seed": root / "own", "earth-seed@hub": root / "hub"}
        found = {"seed": "{seeds}/usd-r3/{place}", "neighbour hub": "{seeds}/usd-r3/hub",
                 "neighbour far_city": "{seeds}/usd-r3/far_city", "kit": "{data}/kit/{place}.json",
                 "kit hub": "{data}/kit/hub.json", "kit far_city": "{data}/kit/far_city.json"}
        assert stages.seeded_place(inputs) == "airlock"
        taken = stages.seed_inputs(inputs, found, "airlock")
        assert taken["seed"] == root / "own/airlock" and taken["neighbour hub"] == root / "hub/hub", taken
        assert taken["kit"] == root / "own" / earth_seed.KIT_FILE, taken  # the design's kit, from its own seed
        assert taken["kit hub"] == root / "hub" / earth_seed.KIT_FILE, taken  # a shown place's, read beside
        # no earth-seed row (no design locked): still a declared file, named lost
        assert "neighbour far_city" not in taken and "kit far_city" not in taken, taken
    finally:
        shutil.rmtree(root)
        earth_seed.DESIGN = kept


def test_a_piece_no_row_made_is_left_out_and_named():
    sys.path.insert(0, str(REPO / "tools/usd"))
    import export
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        (root / "wall_1.gltf").write_text("{}")
        gaps = []
        pieces = [{"model": "wall_1"}, {"model": "lamp_1"}, {"model": "lamp_1"}]
        assert export.made_only(pieces, [root], gaps) == [{"model": "wall_1"}]
        export.made_only(pieces, [root], gaps)
        assert gaps == [{"model": "lamp_1"}], gaps
    finally:
        shutil.rmtree(root)


def test_the_seed_gates_fail_by_name():
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        (root / "wreck").mkdir()
        (root / "wreck/wreck.usda").write_text("#usda 1.0\n")
        (root / earth_seed.GAPS).write_text(json.dumps({"models": [], "picks": []}))
        assert earth_seed.seed_faults(root) == [f"no {earth_seed.KIT_FILE}"]  # the design's kit, which readers read
        (root / earth_seed.KIT_FILE).write_text(json.dumps({"room": "wreck", "pieces": []}))
        assert earth_seed.seed_faults(root) == []
        assert earth_seed.judge_laid(root, {}, {}).answer == checks.PASS
        (root / earth_seed.GAPS).write_text(json.dumps({"models": ["cable_run_1p4"], "picks": [
            {"row": "aft_section", "object": None, "why": "no object of this row is on the stage"}]}))
        laid, picked = earth_seed.judge_laid(root, {}, {}), earth_seed.judge_picks(root, {}, {})
        assert laid.answer == checks.FAIL and laid.findings == ("cable_run_1p4",), laid
        assert picked.answer == checks.FAIL and "aft_section" in picked.findings[0], picked
    finally:
        shutil.rmtree(root)


# A 4 x 3 m room in plan metres, its walls 0.2 m thick and 2.5 m high, a door 1 m wide and 2 m high in the middle of
# its north wall, a flat roof on 2.5 m (the written plan's schema, score/review/plan_writing.py).
BOX = [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]]
ROOM = {"title": "a test room", "shell": "kit", "inside": True, "w": 4.0, "d": 3.0, "outline": BOX,
        "walls": [{"from": one, "to": two, "thick": 0.2, "tall": 2.5} for one, two in zip(BOX, BOX[1:] + BOX[:1])],
        "openings": [{"kind": "door", "at": [2.0, 0.0], "wide": 1.0, "sill": 0.0, "head": 2.0, "to": "hangar"}],
        "roofs": [{"kind": "flat", "points": BOX, "eave": 2.5, "top": 2.5}], "levels": [], "doors": [], "items": []}
# An open place 10 x 10 m: a stage deck 1 m high on a 2 x 2 m patch, a balcony 6 m up on another, a stair of 4 steps
# from the plaza up to the deck on a 1 x 2 m footprint (its way up east, 0 degrees), and a ramp from 0 to 0.5 m over a
# 2 x 1 m footprint (its way up south, 90 degrees).
OPEN = {"title": "a test square", "shell": "kit", "inside": False, "w": 10.0, "d": 10.0,
        "levels": [{"name": "plaza", "height": 0.0, "points": [[0, 0], [10, 0], [10, 10], [0, 10]]},
                   {"name": "stage deck", "height": 1.0, "points": [[4, 4], [6, 4], [6, 6], [4, 6]]},
                   {"name": "balcony", "height": 6.0, "points": [[0, 0], [2, 0], [2, 2], [0, 2]]}],
        "stairs": [{"kind": "stair", "points": [[3, 4], [4, 4], [4, 6], [3, 6]], "from": 0.0, "to": 1.0, "angle": 0.0,
                    "steps": 4},
                   {"kind": "ramp", "points": [[7, 7], [9, 7], [9, 8], [7, 8]], "from": 0.0, "to": 0.5, "angle": 90.0,
                    "steps": 1}],
        "roofs": [], "openings": [], "doors": [], "items": []}


def volume(triangles):
    """A closed triangle soup's volume (the divergence theorem: each face's tetrahedron to the origin)."""
    corners = numpy.asarray(triangles, float).reshape(-1, 3, 3)
    return float(numpy.einsum("ij,ij->i", corners[:, 0], numpy.cross(corners[:, 1], corners[:, 2])).sum() / 6)


def test_a_room_shell_stands_round_its_plan():
    """Worked by hand: the deck and the roof each 4.3 x 3.3 x 0.2 m (the room grown 0.15 m to the walls' inside);
    the walls a ring 0.15 to 0.35 m out (4.7 x 3.7 less 4.3 x 3.3 = 3.2 m2) from the deck's foot (-0.242 m) to 2.5 m,
    less the door's hole of 1.0 x 0.2 x 2.0 m; the room's middle the place's origin."""
    parts = {name: triangles for name, triangles, _ in design_shell.shell(ROOM)}
    assert sorted(parts) == ["deck_1", "roof_1", "wall_1", "wall_2", "wall_3", "wall_4"], sorted(parts)
    assert abs(volume(parts["deck_1"]) - 4.3 * 3.3 * 0.2) < 1e-6, volume(parts["deck_1"])
    assert abs(volume(parts["roof_1"]) - 4.3 * 3.3 * 0.2) < 1e-6, volume(parts["roof_1"])
    walls = sum(volume(parts[f"wall_{number}"]) for number in range(1, 5))
    assert abs(walls - ((4.7 * 3.7 - 4.3 * 3.3) * (2.5 + 0.242) - 1.0 * 0.2 * 2.0)) < 1e-6, walls
    north = numpy.asarray(parts["wall_1"], float).mean(axis=1)  # [x, up, y] of each face's middle
    in_door = (north[:, 0] > 1.5 + 1e-6) & (north[:, 0] < 2.5 - 1e-6) & \
        (north[:, 1] > 1e-6) & (north[:, 1] < 2.0 - 1e-6)
    assert not in_door.any(), north[in_door]
    points = numpy.vstack([design_shell.placed(triangles, ROOM) for triangles in parts.values()])
    assert numpy.allclose(points.min(axis=0), [-2.35, -0.242, -1.85]) and \
        numpy.allclose(points.max(axis=0), [2.35, 2.7, 1.85]), (points.min(axis=0), points.max(axis=0))
    from score.stages.scene_record import writer
    assert (design_shell.BACKING, design_shell.DECK_BELOW) == (writer.BACKING, writer.DECK_BELOW)
    assert design_shell.footprint(ROOM) == [[-2.0, -1.5], [2.0, 1.5]]
    # a pitched roof rising 1 m: a closed gable over the 4.3 x 3.3 m grown box, half its box's volume
    pitched = {name: triangles for name, triangles, _ in design_shell.shell(
        dict(ROOM, roofs=[{"kind": "pitched", "points": BOX, "eave": 2.5, "top": 3.5}]))}
    assert abs(volume(pitched["roof_1"]) - 4.3 * 3.3 * 1.0 / 2) < 1e-6, volume(pitched["roof_1"])


def test_a_door_or_window_row_cuts_its_opening_where_its_plan_item_stands_on_a_wall():
    """2026-10-26: Batch 1's doors and windows stood at plan items the plan's openings missed, against uncut walls. A
    row filling an opening (a door, window, gate, hatch or shutter, a panel) cuts one at its item on a wall, its own
    wide, from its shape's base to its top; one at the plan's own opening cuts none more, and a box is no panel."""
    rows = [{"id": "window", "name": "porthole window", "noun": "window", "size": [1.0, 0.1, 1.0]},
            {"id": "door", "name": "door", "noun": "door", "size": [1.0, 0.1, 2.0]},
            {"id": "door_control_box", "name": "door control box", "noun": "box", "size": [0.2, 0.1, 0.3]}]
    plan = dict(ROOM, items=[["WINDOW 1", 3.95, 1.0, 0.1, 1.0, None, "item"], ["DOOR 1", 1.5, -0.05, 1.0, 0.1, None,
                                                                                "item"],
                             ["BOX 1", 0.0, 1.0, 0.1, 0.2, None, "item"]],
                rows={"WINDOW 1": ["window"], "DOOR 1": ["door"], "BOX 1": ["door_control_box"]},
                shapes={"WINDOW 1": {"base": 1.0, "tall": 1.0}, "DOOR 1": {"base": 0.0, "tall": 2.0}})
    assert design_shell.row_openings(plan, rows) == [{"at": [4.0, 1.5], "wide": 1.0, "sill": 1.0, "head": 2.0,
                                                     "row": "window"}]
    cut = {name: triangles for name, triangles, _ in design_shell.shell(design_shell.cut_for(plan, rows))}
    whole = {name: triangles for name, triangles, _ in design_shell.shell(plan)}
    assert abs(volume(whole["wall_2"]) - volume(cut["wall_2"]) - 1.0 * 0.2 * 1.0) < 1e-6  # the window's hole
    assert abs(volume(whole["wall_1"]) - volume(cut["wall_1"])) < 1e-9  # the door's is the plan's own


def test_a_room_is_a_kit_shell_inside_or_one_that_writes_walls():
    """A scene added in the app says neither inside nor out: it is a room the earth seed lays when its plan writes walls
    (the docking airlock), an open place when it writes none (the Moon base); a domed shell is the scene record's."""
    unsaid = {key: value for key, value in ROOM.items() if key != "inside"}
    assert design_shell.laid_for(ROOM) and design_shell.laid_for(unsaid)
    assert not design_shell.laid_for(dict(unsaid, walls=[])) and not design_shell.laid_for(OPEN)
    assert not design_shell.laid_for(dict(ROOM, shell="outdoor")) and not design_shell.laid_for(dict(ROOM, shell=None))


def test_the_earth_seed_and_the_scene_record_lay_each_shell_once():
    """The scene record encloses a place by the same rule (writer.inside is design_shell.encloses) and lays the shell of
    every enclosed place the earth seed does not (laid_for), and every stair; the earth seed lays a room's shell and an
    open place's raised levels, never a stair. Worked by hand on OPEN: the plaza (0 m) is the ground's, no part; the
    stage deck stands solid from the ground (2 x 2 x 1 m), the balcony is a slab (2 x 2 x 0.2 m)."""
    from score.stages.scene_record import writer
    domed = dict(OPEN, shell=None, walls=ROOM["walls"])
    for plan in (ROOM, OPEN, domed, dict(domed, terrain={"spots": [[1, 1, 0.5]]}), dict(OPEN, roofs=ROOM["roofs"])):
        assert writer.inside(plan) == design_shell.encloses(plan), plan.get("title")
    parts = {name: triangles for name, triangles, _ in design_shell.shell(OPEN)}
    assert sorted(parts) == ["level_2", "level_3"], sorted(parts)  # its stairs are the scene record's
    assert abs(volume(parts["level_2"]) - 4.0) < 1e-6 and abs(volume(parts["level_3"]) - 0.8) < 1e-6
    assert design_shell.shell(domed) == []  # enclosed, no room of the earth seed's: the scene record's shell
    room = {name for name, _, _ in design_shell.shell(dict(ROOM, stairs=OPEN["stairs"]))}
    assert not any(name.startswith(("stair_", "level_")) for name in room), room  # a room's levels are its decks
    recorded = writer.structure({"place": "room"}, dict(ROOM, stairs=OPEN["stairs"]))
    assert [entry["builder"] for entry in recorded] == ["stairs", "stairs"]  # the room's shell is the earth seed's


def test_each_part_takes_its_surface_from_the_scene_library():
    """A part's surface is the first variant the scene library's `kinds` gives one of its kinds; none, and the part
    names why."""
    library = {"kinds": {"floor": ["deck_plate", "rubber_mat"], "ceiling": ["ceiling_panel"], "wall": []}}
    assert design_shell.surface_for("deck", library) == "deck_plate"
    assert design_shell.surface_for("stair", library) == "deck_plate"  # no stairs kind: the floor's
    assert design_shell.surface_for("roof", library) == "ceiling_panel"
    assert design_shell.surface_for("wall", library) is None and design_shell.surface_for("wall", None) is None
    assert "names no surface" in design_shell.missing_why("x", "wall", library)
    assert "not made" in design_shell.missing_why("x", "wall", None)


def with_designs(plans, root=None):
    """earth_seed.DESIGN pointed at a folder holding `plans` ({scene: its locked plan}); the folder."""
    root = pathlib.Path(root or tempfile.mkdtemp())
    (root / "plans").mkdir(parents=True)
    for scene, plan in plans.items():
        (root / "plans" / f"{scene}.json").write_text(json.dumps(plan))
    earth_seed.DESIGN = root
    return root


def test_a_designed_base_takes_its_style_from_its_own_entry_else_the_scene_holding_it():
    """A design's base is its design's, never a kit's (the old concepts' kits were retired, 2026-10-21); a scene added
    in the app (not in place.json) takes the style of the scene whose plan holds it; a top scene place.json does not
    name (the Base, nothing holds it) takes the environment concept's, its library entries its own name's, and the
    scenes under it its; plans that hold each other round in a ring give none."""
    kept = earth_seed.DESIGN
    root = with_designs({"cockpit": {"w": 9.414, "d": 9.8},
                         "hangar": {"holds": [{"place": "cockpit", "row": "spaceship"},
                                              {"place": "docking_bay", "row": "spaceship"}]},
                         "outpost": {"holds": [{"place": "yard_shed", "row": "shed"}]},
                         "ring_a": {"holds": [{"place": "ring_b", "row": "b"}]},
                         "ring_b": {"holds": [{"place": "ring_a", "row": "a"}]}})
    try:
        declared = earth_seed.seed_files("cockpit")
        assert "kit" not in declared and declared["design plan"] == "{home}/design/plans/cockpit.json", declared
        assert not any(name.startswith("holder ") for name in declared), declared  # place.json names the cockpit
        declared = earth_seed.seed_files("docking_bay")
        assert declared["holder hangar"] == "{home}/design/plans/hangar.json", declared
        inputs = {"places": REPO / "data/definitions/place.json",
                  "holder hangar": earth_seed.DESIGN / "plans/hangar.json"}
        assert earth_seed.style_of("docking_bay", inputs) == "hangar"
        assert earth_seed.holders("outpost") == {} and earth_seed.style_of("outpost", inputs) == "outpost"
        assert earth_seed.holders("yard_shed") == {"outpost": "{home}/design/plans/outpost.json"}
        assert earth_seed.style_of("yard_shed", {**inputs, "holder outpost": earth_seed.DESIGN / "plans/outpost.json"}) \
            == "outpost"
        ring = {"places": inputs["places"], "holder ring_b": earth_seed.DESIGN / "plans/ring_b.json",
                "holder ring_a": earth_seed.DESIGN / "plans/ring_a.json"}
        try:  # plans holding each other round in a ring: refused by name, never a loop with no end
            earth_seed.style_of("ring_a", ring)
            raise AssertionError("a scene in a ring of holders was given a style")
        except ValueError as error:
            assert "ring_a" in str(error), error
        assert earth_seed.holders("ring_a") is None and not earth_seed.styled("ring_a")
        assert earth_seed.styled("docking_bay") and earth_seed.styled("cockpit") and earth_seed.styled("outpost")
    finally:
        shutil.rmtree(root, ignore_errors=True)
        earth_seed.DESIGN = kept


def test_the_seed_reads_the_design_s_surface_data():
    """A place's earth seed declares its design's surface data where it has one (surface_data.pattern, the one its
    finish route paints), the places it claims models from are that data's `elsewhere`, through the registered row
    too, and it declares no old scene record or kit."""
    from score.stages.surfaces import surface_data
    kept_surfaces, kept = surface_data.DESIGN, earth_seed.DESIGN
    root = with_designs({"hub": {"w": 12.0, "d": 12.0}})
    surface_data.DESIGN = root / "surfaces"
    surface_data.DESIGN.mkdir()
    (surface_data.DESIGN / "hub.json").write_text(json.dumps(
        {"library": "hub", "takes": {}, "elsewhere": {"rack_1": {"take": "rack-x", "place": "lab"}}}))
    try:
        declared = earth_seed.seed_files("hub")
        assert not {"scene", "kit"} & set(declared) and declared["surfaces"] == "{home}/design/surfaces/hub.json"
        assert earth_seed.claiming_places("hub") == ["lab"]
    finally:
        surface_data.DESIGN, earth_seed.DESIGN = kept_surfaces, kept
        shutil.rmtree(root, ignore_errors=True)


def scene_library(folder):
    """A surface-library output in `folder`: materials.json in the method's form with one scene's floor and wall
    surfaces in its own palette tokens, and no roof or ceiling surface."""
    method = json.loads((REPO / "data/library/materials.json").read_text())
    write(folder, earth_seed.LIBRARY_FILE, dict(
        method, tokens={"hull_grey": "#808890", "soot": "#202020"}, dirt="soot",
        families={"steel": {"surface": "metal", "variants": {
            "deck_steel": {"recipe": "chequer_plate", "token": "hull_grey", "roughness": 0.5, "metal": 0.6},
            "wall_paint": {"recipe": "painted_metal", "token": "hull_grey", "roughness": 0.6, "metal": 0.0}}}},
        kinds={"floor": ["deck_steel"], "wall": ["wall_paint"]}))
    return folder


def test_a_design_base_passes_the_seed_gates_the_placeholder_gate_and_collides():
    """earth-seed's make for a scene added in the app (no kit), on ROOM with its scene library: one stage under its
    name, no gap, its shell under /<place>/Shell, each part its library surface bound where the library gives its
    kind one (the deck, the walls) and named missing where it gives none (the roof), every part a collider (the
    collision gate holds the shell), the placeholder gate failing only the unpainted roof; its style the hangar's (the
    scene holding it), its kit the design's (no piece, the plan's box). The same plan as an open place gets no room;
    with no library every part is named missing."""
    from pxr import Usd, UsdShade
    sys.path.insert(0, str(REPO / "tools/usd"))
    import colliders
    import placeholders
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        write(root, "docking_bay.json", ROOM)
        write(root, "inventory.json", {"rows": []})
        write(root, "hangar.json", {"holds": [{"place": "docking_bay", "row": "spaceship"}]})
        inputs = {"design plan": root / "docking_bay.json", "design inventory": root / "inventory.json",
                  "places": REPO / "data/definitions/place.json", "holder hangar": root / "hangar.json",
                  earth_seed.LIBRARY_ROW: scene_library(root / "library")}
        out = root / "open"
        out.mkdir()
        earth_seed.make_seed(dict(inputs, **{"design plan": write(root / "open-plan", "docking_bay.json",
                                                                   dict(ROOM, inside=False))}), out, 0, {})
        assert json.loads((out / earth_seed.KIT_FILE).read_text())["shell"] == []
        assert not Usd.Stage.Open(str(out / "docking_bay/docking_bay.usda")).GetPrimAtPath("/docking_bay/Shell")
        out = root / "out"
        out.mkdir()
        earth_seed.make_seed(inputs, out, 0, {})
        assert earth_seed.seed_faults(out) == [], earth_seed.seed_faults(out)
        assert earth_seed.judge_laid(out, {}, {}).answer == checks.PASS
        assert earth_seed.judge_picks(out, {}, {}).answer == checks.PASS
        kit = json.loads((out / earth_seed.KIT_FILE).read_text())
        assert kit["place"] == "hangar" and kit["pieces"] == [] and len(kit["shell"]) == 6, kit
        assert kit["footprint"] == [[-2.0, -1.5], [2.0, 1.5]], kit
        assert kit["room"] == "docking_bay"  # no made ground seats it: it stands in its own frame, as a room
        stage_path = earth_seed.place_in(out) / "docking_bay.usda"
        stage = Usd.Stage.Open(str(stage_path))
        shell = stage.GetPrimAtPath("/docking_bay/Shell").GetChildren()
        assert sorted(prim.GetName() for prim in shell) == sorted(kit["shell"])
        painted = {"deck_1": "deck_steel", **{f"wall_{number}": "wall_paint" for number in range(1, 5)}}
        for prim in shell:
            material = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
            if prim.GetName() in painted:
                assert str(material.GetPath()) == f"/docking_bay/Library/{painted[prim.GetName()]}", prim
            else:
                assert not material and "names no surface" in prim.GetAttribute("score:surface:missing").Get()
        assert colliders.faults(stage) == [], colliders.faults(stage)
        assert sorted((fault["prim"], fault["rule"]) for fault in placeholders.check(stage_path)) == [
            ("/docking_bay/Shell/roof_1", "material")], placeholders.check(stage_path)
        bare = root / "bare"
        bare.mkdir()
        earth_seed.make_seed({key: value for key, value in inputs.items() if key != earth_seed.LIBRARY_ROW}, bare,
                             0, {})
        stage = Usd.Stage.Open(str(earth_seed.place_in(bare) / "docking_bay.usda"))
        assert all("not made" in prim.GetAttribute("score:surface:missing").Get()
                   for prim in stage.GetPrimAtPath("/docking_bay/Shell").GetChildren())
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
