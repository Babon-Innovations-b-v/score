"""The earth seed rows' own checks, with no spend: the kit row plans only code-built pieces, every row that read a
round-three seed reads earth-seed instead, a reader is handed its seeds under their
old names, the export leaves out and names a piece no row made, and the gates fail by name; a kit is the base's only
when laid for its locked plan's room, and a design base (no kit) stands its room shell round its plan and passes the
seed gates and the placeholder gate.

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

PLACES = ("hangar", "wreck", "street", "airlock", "launch", "camp")


KIT = {"room": "x", "models": {"wall_1": {"route": "code"}, "lamp_1": {"route": "code"}, "crane_1": {"route": "model"}},
       "pieces": [{"kind": "x_wall", "model": "wall_1", "at": [0, 0, 0], "y": [0.0, 0.0, 1.0]},
                  {"kind": "x_lamp", "model": "lamp_1", "at": [0, 2, 0]},
                  {"kind": "x_lamp", "model": "lamp_1_glow", "part": "glow", "at": [0, 2, 0]},
                  {"kind": "x_crane", "model": "crane_1", "at": [3, 0, 0]}]}


def test_the_kit_row_plans_its_named_code_fallbacks_only():
    named = earth_seed.fallbacks(KIT, "x", set())  # nothing handed: every row is named, by its route
    why = earth_seed.NOT_HANDED
    assert named == {"crane": {"route": "stored take", "why": why}, "lamp": {"route": "code", "why": why},
                     "wall": {"route": "code", "why": why}}, named
    pieces = earth_seed.code_layout(KIT, "x", named)["pieces"]
    assert [piece["model"] for piece in pieces] == ["wall_1", "lamp_1"], pieces
    assert pieces[0]["y"] == [0.0, 0.0, 1.0] and pieces[1]["y"] == earth_seed.UPRIGHT, pieces
    assert [piece["model"] for piece in earth_seed.code_layout(KIT, "x", {"lamp": "why"})["pieces"]] == ["lamp_1"]


def test_a_row_handed_to_the_loop_leaves_the_kit_row():
    assert set(earth_seed.fallbacks(KIT, "x", {"wall", "crane"})) == {"lamp"}  # the wall's and crane's are the loop's
    handed = earth_seed.handed_in({"wall": {"route": "prop", "layer": "kit"}, "chair": {"route": "prop"}})
    assert handed == {"wall"}, handed  # a row with no layer is the objects layer's (closeup_row.layer_of)


def write(folder, name, record):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(record))
    return folder / name


def base_stage(seed, objects):
    """An earth seed's output: place x's base stage with `objects` ({name: (row, spot)}) under /x/Objects."""
    from pxr import Gf, Sdf, Usd, UsdGeom
    (seed / "x/layers").mkdir(parents=True)
    (seed / "x/x.usda").write_text("#usda 1.0\n")
    stage = Usd.Stage.CreateNew(str(seed / "x/layers/base.usda"))
    for name, (row, spot) in objects.items():
        xform = UsdGeom.Xform.Define(stage, f"/x/Objects/{name}")
        xform.AddTranslateOp().Set(Gf.Vec3d(*spot))
        xform.GetPrim().CreateAttribute("score:row", Sdf.ValueTypeNames.String).Set(row)
    stage.GetRootLayer().Save()
    return seed


def section_inputs(root):
    """Place x's base with two wall panels, a trim, a floor plate and a pipe, its plan's two sections, the loop's ends
    (the wall made, take wall-k1, its parts two finishes; the trim made, take trim-k1, steel; the floor a gap) and
    earth-kit's fallbacks (the pipe, code)."""
    sections = [{"name": "bolted walls", "surface": "walls", "rows": ["wall", "trim"]},
                {"name": "deck plates", "surface": "floor", "rows": ["floor", "pipe", "vent"]}]
    rows = [{"id": "wall", "take": "wall-k1", "layer": "kit"}, {"id": "trim", "take": "trim-k1", "layer": "kit"},
            {"id": "floor", "take": "floor-k1", "layer": "kit"}]
    parts = {"takes": {"wall-k1": {"parts": [{"judge": "dark_panel", "share": 0.3}, {"judge": "painted_panel",
                                                                                        "share": 0.7}]},
                       "trim-k1": {"parts": [{"judge": "steel", "share": 1.0}]}}}
    objects = {"wall_1": ("wall", (2.0, 0.0, 5.0)), "wall_2": ("wall", (3.2, 0.0, 5.0)),
               "trim_1": ("trim", (2.6, 2.0, 5.0)), "floor_1": ("floor", (0.0, 0.0, 0.0)),
               "pipe_1": ("pipe", (1.0, 0.0, 1.0))}
    named = {"pipe": {"route": "code", "why": earth_seed.NOT_HANDED}}
    return {"earth-seed": base_stage(root / "seed", objects),
            "plan": write(root / "plan", "x.json", {"sections": sections}),
            "places": write(root, "place.json", {"x_library": {"wear": {"level": "worked", "dirt": 0.4}}}),
            "surfaces": write(root / "surfaces", "x.json", {"library": "x_library"}),
            "props-inputs": write(root / "inputs", "rows.json", {"rows": rows}).parent,
            "likeness": write(root / "likeness", "likeness.json", {"objects": {"wall": {"route": "prop"}, "trim": {
                "route": "prop"}, "floor": {"missing": "no model"}}}).parent,
            "surfaces-bake": write(root / "bake", "baked.json", {"wall_1": {"parts": "wall-k1"},
                                                                 "trim_1": {"parts": "trim-k1"}}).parent,
            "earth-kit": write(root / "kit", earth_seed.FALLBACKS, named).parent,
            "surfaces-parts": write(root / "parts", "parts.json", parts).parent}


def test_kit_sections_lay_one_style_one_finish_and_wear_across_the_seams():
    from pxr import Gf, Usd
    from score.stages.earth_seed import kit_sections
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        inputs, out = section_inputs(root), root / "out"
        out.mkdir()
        kit_sections.make(inputs, out, 0, {})
        assert kit_sections.faults(out) == []
        walls, deck = json.loads((out / kit_sections.OUTPUT).read_text())["sections"]
        # two wall panels at 0.7 painted panel outweigh one trim at 1.0 steel: shares weighted by pieces laid
        assert walls["finish"] == "painted_panel" and walls["made"] == {"wall": "wall-k1", "trim": "trim-k1"}, walls
        assert walls["shares"] == {"dark_panel": 0.6, "painted_panel": 1.4, "steel": 1.0}, walls
        assert walls["origin"] == [2.0, 0.0, 5.0] and walls["gaps"] == {} and walls["wear"]["level"] == "worked"
        assert deck["finish"] is None and deck["made"]["floor"].startswith("gap: no model"), deck
        assert deck["made"]["pipe"] == f"fallback: code: {earth_seed.NOT_HANDED}", deck  # named, not a gap
        assert set(deck["gaps"]) == {"floor", "vent"}, deck  # vent: neither handed nor named
        layer = Usd.Stage.Open(str(out / kit_sections.LAYER))
        first, second = (layer.GetPrimAtPath(f"/x/Objects/wall_{number}") for number in (1, 2))
        assert second.GetAttribute("score:section").Get() == "bolted walls"
        assert second.GetAttribute("score:finish").Get() == "painted_panel"
        assert second.GetAttribute("score:wear_seed").Get() == first.GetAttribute("score:wear_seed").Get()
        assert second.GetAttribute("score:wear_at").Get() == Gf.Vec3f(1.2, 0.0, 0.0)  # wear runs on past the seam
        verdict = kit_sections.judge_sections(out, inputs, {})
        assert verdict.answer == checks.PASS and verdict.measures["gaps"] == 2, verdict
        twice = [{"name": "a", "surface": "walls", "rows": ["wall"]}, {"name": "b", "surface": "walls",
                                                                        "rows": ["wall", "door"]}]
        write(root / "plan", "x.json", {"sections": twice})
        again = root / "again"
        again.mkdir()
        kit_sections.make(inputs, again, 0, {})
        failed = kit_sections.judge_sections(again, inputs, {})
        assert failed.answer == checks.FAIL and any("in two sections" in line for line in failed.findings), failed
    finally:
        shutil.rmtree(root)


def test_the_kit_adapter_is_on_the_loop_and_no_place_lays_a_kit():
    """The kit adapter stays on the loop; no place lays a kit now (the old concepts' kits were retired, 2026-10-21),
    so no place has kit sections and every base is its design's."""
    from score.stages import assembly, shapes_first
    assert shapes_first.KIT in shapes_first.ADAPTERS and shapes_first.KIT.layer == earth_seed.KIT_LAYER
    step = next(row for row in shapes_first.rows() if row.name == "kit-sections")
    assert not step.applies("hangar")  # no kit row handed to the loop yet (earth_seed.NOT_HANDED)
    from score.stages.earth_seed import kit_sections
    kept = earth_seed.DESIGN
    root = with_designs({})
    try:
        assert not any(kit_sections.applies(place) or earth_seed.kit_is_base(place)
                       for place in ("hangar", "wreck", "cockpit", "street"))
    finally:
        shutil.rmtree(root, ignore_errors=True)
        earth_seed.DESIGN = kept
    assert "kit-sections" in assembly.LAYERS


def test_no_row_reads_an_earth_place_s_round_three_seed():
    readers = set()
    for row in stages.STAGES:
        for place in PLACES:
            if row.applies is not None and not row.applies(place):
                continue
            found = row.files(place) if callable(row.files) else row.files
            if any(stages.seed_named(path, place) for path in found.values()):
                readers.add(row.name)
    assert not readers, readers  # terrain-look, the last, retired (#27)
    # kit-sections reads its own place's earth seed (its base stage), never the round-three folder
    reading = ({row.name for row in stages.STAGES if "earth-seed" in row.after}
               - {stages.library.PLACE_ROW, "kit-sections"})
    assert reading == set(stages.EARTH_SEEDED), reading ^ set(stages.EARTH_SEEDED)


def test_a_reader_gets_its_seeds_under_their_old_names():
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        for node, place in (("own", "airlock"), ("hub", "hub")):
            (root / node / place).mkdir(parents=True)
        inputs = {"earth-seed": root / "own", "earth-seed@hub": root / "hub", "kit": "k"}
        found = {"seed": "{seeds}/usd-r3/{place}", "neighbour hub": "{seeds}/usd-r3/hub",
                 "neighbour far_city": "{seeds}/usd-r3/far_city", "kit": "{data}/kit/{place}.json"}
        assert stages.seeded_place(inputs) == "airlock"
        taken = stages.seed_inputs(inputs, found, "airlock")
        assert taken["seed"] == root / "own/airlock" and taken["neighbour hub"] == root / "hub/hub", taken
        assert "neighbour far_city" not in taken and taken["kit"] == "k", taken  # no kit: still a declared file
    finally:
        shutil.rmtree(root)


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


def volume(triangles):
    """A closed triangle soup's volume (the divergence theorem: each face's tetrahedron to the origin)."""
    corners = numpy.asarray(triangles, float).reshape(-1, 3, 3)
    return float(numpy.einsum("ij,ij->i", corners[:, 0], numpy.cross(corners[:, 1], corners[:, 2])).sum() / 6)


def test_a_design_shell_stands_round_its_plan():
    """Worked by hand: the deck and the roof each 4.3 x 3.3 x 0.2 m (the room grown 0.15 m to the walls' inside);
    the walls a ring 0.15 to 0.35 m out (4.7 x 3.7 less 4.3 x 3.3 = 3.2 m2) from the deck's foot (-0.242 m) to 2.5 m,
    less the door's hole of 1.0 x 0.2 x 2.0 m; the room's middle the place's origin."""
    from score.stages.earth_seed import design_shell
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
    assert (design_shell.SURFACE, design_shell.BACKING, design_shell.DECK_BELOW) == \
        (writer.SHELL_SURFACE, writer.BACKING, writer.DECK_BELOW)  # the scene record's backing shell


def with_designs(plans):
    """earth_seed.DESIGN pointed at a folder holding `plans` ({scene: its locked plan}); the folder."""
    root = pathlib.Path(tempfile.mkdtemp())
    (root / "plans").mkdir()
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
        assert not earth_seed.kit_is_base("cockpit")
        declared = earth_seed.seed_files("cockpit")
        assert "kit" not in declared and declared["design plan"] == "{home}/design/plans/cockpit.json", declared
        assert not any(name.startswith("holder ") for name in declared), declared  # place.json names the cockpit
        assert not earth_seed.kit_is_base("docking_bay")
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
        shutil.rmtree(earth_seed.DESIGN, ignore_errors=True)
        shutil.rmtree(root, ignore_errors=True)
        earth_seed.DESIGN = kept


def test_the_seed_and_its_sections_read_the_design_s_surface_data():
    """A place's earth seed and kit sections declare its design's surface data where it has one (surface_data.pattern,
    the one its finish route paints), the places it claims models from are that data's `elsewhere`, through the
    registered row too, and a design base declares no old scene record."""
    from score.stages.earth_seed import kit_sections
    from score.stages.surfaces import surface_data
    kept_surfaces, kept = surface_data.DESIGN, earth_seed.DESIGN
    root = with_designs({"hub": {"w": 12.0, "d": 12.0}})
    surface_data.DESIGN = root / "surfaces"
    surface_data.DESIGN.mkdir()
    (surface_data.DESIGN / "hub.json").write_text(json.dumps(
        {"library": "hub", "takes": {}, "elsewhere": {"rack_1": {"take": "rack-x", "place": "lab"}}}))
    try:
        assert not earth_seed.kit_is_base("hub")
        declared = earth_seed.seed_files("hub")
        assert "scene" not in declared and declared["surfaces"] == "{home}/design/surfaces/hub.json", declared
        assert earth_seed.claiming_places("hub") == ["lab"]
        assert stages.EARTH_SEED.neighbours("hub") == ["lab"]  # the registered row reads the design's claims
        assert kit_sections.files("hub")["surfaces"] == "{home}/design/surfaces/hub.json"
    finally:
        surface_data.DESIGN, earth_seed.DESIGN = kept_surfaces, kept
        shutil.rmtree(root, ignore_errors=True)


def test_a_design_base_passes_the_seed_gates_and_the_placeholder_gate():
    """earth-seed's make for a scene added in the app (no kit), on ROOM: one stage under its name, no gap, its shell
    under /<place>/Shell painted with the library's backing surface, nothing the placeholder gate fails, its style the
    hangar's (the scene holding it). The same plan as an open place (not inside) gets no room shell."""
    from pxr import Usd, UsdShade
    sys.path.insert(0, str(REPO / "tools/usd"))
    import placeholders
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        write(root, "docking_bay.json", ROOM)
        write(root, "inventory.json", {"rows": []})
        write(root, "hangar.json", {"holds": [{"place": "docking_bay", "row": "spaceship"}]})
        inputs = {"design plan": root / "docking_bay.json", "design inventory": root / "inventory.json",
                  "places": REPO / "data/definitions/place.json", "holder hangar": root / "hangar.json"}
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
        stage_path = earth_seed.place_in(out) / "docking_bay.usda"
        stage = Usd.Stage.Open(str(stage_path))
        shell = stage.GetPrimAtPath("/docking_bay/Shell").GetChildren()
        assert sorted(prim.GetName() for prim in shell) == sorted(kit["shell"])
        for prim in shell:  # its backing surface named, and missing while the library holds none (2026-10-21)
            assert prim.GetAttribute("score:surface").Get() == "roof_steel_paint"
            material = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
            assert (str(material.GetPath()) == "/docking_bay/Library/roof_steel_paint" if material else
                    "run surface-library first" in prim.GetAttribute("score:surface:missing").Get()), prim
        # the placeholder gate names only the shell's unpainted faces, each one its missing surface names
        unpainted = {f"/docking_bay/Shell/{prim.GetName()}" for prim in shell
                     if prim.GetAttribute("score:surface:missing").Get()}
        assert sorted((fault["prim"], fault["rule"]) for fault in placeholders.check(stage_path)) == [
            (prim, "material") for prim in sorted(unpainted)], placeholders.check(stage_path)
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
