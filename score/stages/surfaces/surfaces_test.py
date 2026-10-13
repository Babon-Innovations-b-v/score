"""The surface stage's framework side: the finish registry keeps each proposed library surface as first proposed, the
per-place data names each take once world-wide and every model a place lays that another place claims is baked by
that place, every place's line is rows of world 1's table, the paint takes the method's surface and records its
proposal, and a gate that cannot read what it needs, or a model whose finish map never settled, blocks with a reason on
that model instead of crashing or passing. No cloud, no paid step.

Run: .venv/bin/python score/stages/surfaces/surfaces_test.py
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks, graph, stages  # noqa: E402
from score.stages import surfaces  # noqa: E402
from score.stages.surfaces import finish_rows, registry, surface_data, surface_gates  # noqa: E402
from score.store import Store  # noqa: E402


def a_store():
    return Store.in_folder(tempfile.mkdtemp())


def test_a_proposed_library_surface_stands_as_first_proposed():
    store = a_store()
    first = registry.Registry(store).propose_surface("Aluminium tape, silver", {"stands_in": "galvanized_dull"},
                                                     {"take": "a"})
    second = registry.Registry(store).propose_surface("Aluminium tape, silver", {"stands_in": "bare_steel"},
                                                      {"take": "b"})
    assert first["spec"] == second["spec"] == {"stands_in": "galvanized_dull"}
    assert len(store.registry("surfaces")) == 1


def test_names_alike_but_for_case_stand_as_one_entry():
    store = a_store()
    first = registry.Registry(store).propose_surface("Polished Chrome", {"stands_in": "pipe_steel"}, {"take": "a"})
    second = registry.Registry(store).propose_surface("polished chrome", {"stands_in": "bare_steel"}, {"take": "b"})
    assert second == first and len(store.registry("surfaces")) == 1
    other = registry.Registry(store).propose_surface("Polished brass", {"stands_in": "brass"}, {"take": "c"})
    assert other["name"] == "Polished brass" and len(store.registry("surfaces")) == 2


def test_the_paint_takes_the_method_s_surface_and_records_its_proposal():
    store = a_store()
    rows = [{"part": 0, "judge": "dark_panel", "proposed": None},
            {"part": 1, "judge": "galvanized_dull", "proposed": {"name": "aluminium tape", "description": "shiny",
                                                                  "why": "thinner than steel"}}]
    found = surfaces.place_line.method_surfaces("power_unit-r3", "old_station", rows, registry.Registry(store))
    assert [record["surface"] for record in found] == ["dark_panel", "galvanized_dull"]
    assert found[1]["proposed"]["stands_in"] == "galvanized_dull" and found[1]["proposed"]["status"] == "proposed"
    assert [entry["name"] for entry in store.registry("surfaces")] == ["aluminium tape"]


def test_each_take_is_painted_by_one_place_and_every_claim_is_baked_by_its_place():
    owner = {}
    records = {path.stem: json.loads(path.read_text()) for path in sorted(surface_data.FOLDER.glob("*.json"))}
    for place, record in records.items():
        assert (REPO / "data/kit" / f"{place}.json").exists(), f"{place}: no such place"
        assert record["takes"] or record.get("nothing"), f"{place}: lists nothing to paint and says not why"
        assert surface_data.paints(place) == bool(record["takes"]), place
        for take, entry in record["takes"].items():
            assert take not in owner, f"{take}: painted by {owner.get(take)} and {place}"
            owner[take] = place
            assert {"place", "kind", "object", "library_places"} <= set(entry), f"{place} {take}"
        bake = record.get("bake")
        if bake:
            assert set(bake["models"].values()) <= set(record["takes"]), f"{place}: bakes a take it does not paint"
    for place, record in records.items():
        for model, claim in record.get("elsewhere", {}).items():
            other = records[claim["place"]]
            assert claim["take"] in other["takes"], f"{place} {model}: {claim['place']} does not paint {claim['take']}"
            assert claim["take"] in other["bake"]["models"].values(), f"{place} {model}: {claim['place']} bakes none"


def test_every_place_s_surface_line_is_rows_of_world_one():
    names = [stage.name for stage in stages.STAGES]
    assert {"surfaces-inputs", "surfaces-maps", "surfaces-parts", "surfaces-paint", "surfaces-bake",
            "surfaces-check"} <= set(names)
    rows = {stage.name: stage for stage in surfaces.ROWS}
    assert all(stage.grain == "place" for stage in surfaces.ROWS)
    assert set(rows["surfaces-paint"].after) == {"surfaces-parts"}  # the method's interface
    assert all(stage.euros for stage in surfaces.ROWS if stage.paid)


def test_a_new_library_surface_moves_only_the_rows_that_read_the_library():
    """Lists, names, parts, paint, bake and check read the library; inputs, turntable, maps and SegviGen never do, so
    a new surface re-asks the cheap lists and leaves the renders, the drawn maps and the split where they stood (maps
    read the lists' answers: identical answers keep their key, the graph's own test)."""
    data, home = pathlib.Path(tempfile.mkdtemp()), pathlib.Path(tempfile.mkdtemp())
    for folder in ("library", "definitions"):
        shutil.copytree(REPO / "data" / folder, data / folder)
    (data / "surfaces").mkdir()
    shutil.copy(surface_data.path("greenhouse"), data / "surfaces")
    world = graph.World("world1", 1, {"data": str(data), "home": str(home), "repo": str(REPO), "seeds": str(home)})
    runner = graph.Runner(surfaces.ROWS, world, a_store(), model_record=lambda kind: {"kind": kind})
    for stage in surfaces.ROWS:  # each file a row names, written small in the test's own home
        for name in runner.files_of(stage, "greenhouse"):
            path = runner.file_path(stage, name, "greenhouse")
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name)
    before = {stage.name: runner.file_keys(stage, "greenhouse") for stage in surfaces.ROWS}
    library = json.loads((data / "library" / "materials.json").read_text())
    library["families"]["plastic"]["variants"]["test_surface"] = {"recipe": "rubber", "token": "danger"}
    (data / "library" / "materials.json").write_text(json.dumps(library))
    moved = {stage.name for stage in surfaces.ROWS if runner.file_keys(stage, "greenhouse") != before[stage.name]}
    assert moved == {"surfaces-lists", "surfaces-names", "surfaces-parts", "surfaces-paint", "surfaces-bake",
                     "surfaces-check"}, moved
    shutil.rmtree(data)
    shutil.rmtree(home)


def test_the_turntable_job_names_no_folder_of_the_run_that_made_it():
    from score.stages.surfaces import turntable_views
    import split_compare
    saved = turntable_views.views_of, split_compare.raw_model
    turntable_views.views_of = lambda take, mesh: [{"name": "c"}]
    split_compare.raw_model = lambda take: None
    try:
        made = []
        for _ in range(2):
            folder = pathlib.Path(tempfile.mkdtemp())
            turntable_views.cameras(folder, ["box"])
            made.append((folder / "multiview" / "job.json").read_bytes())
            assert str(folder).encode() not in made[-1]
    finally:
        turntable_views.views_of, split_compare.raw_model = saved
    assert made[0] == made[1]


def test_a_place_without_data_blocks_before_anything_is_spent_and_one_with_nothing_to_paint_has_no_rows():
    world = graph.World("world1", 1, {"data": str(REPO / "data"), "home": tempfile.mkdtemp(), "repo": str(REPO),
                                      "seeds": tempfile.mkdtemp()})
    runner = graph.Runner(surfaces.ROWS, world, a_store(), model_record=lambda kind: {"kind": kind})
    rows = {stage.name: stage for stage in surfaces.ROWS}
    assert "its input surfaces is missing" in runner.node_status(rows["surfaces-inputs"], "nowhere")
    assert not any(node.endswith("@tube") for node in runner.status(["tube"]))  # code-built pieces only
    try:
        runner.file_keys(rows["surfaces-bake"], "nowhere")
    except graph.Blocked as block:
        assert "nowhere.json" in str(block)
        return
    raise AssertionError("a place with no data did not block at its bake row")


def test_a_gate_that_cannot_read_its_evidence_answers_unknown():
    folder = pathlib.Path(tempfile.mkdtemp())
    check = surface_gates.guarded("maps checked", finish_rows.judge_maps)
    found = checks.judge(check, folder, {"surfaces-inputs": str(folder)}, None)
    assert found.answer == checks.UNKNOWN and "takes.json" in found.reason
    shutil.rmtree(folder)


def test_a_model_whose_finish_map_never_settled_is_named_and_blocks():
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "flat").mkdir()
    (folder / "flat" / "takes.json").write_text(json.dumps({"chair-b": {}, "power_unit-r3": {}}))
    (folder / "chair-b").mkdir()
    (folder / "chair-b" / "map.json").write_text(json.dumps(
        {"take": "chair-b", "passes": True, "front": {"attempts": [], "passes": True}, "views": {}}))
    (folder / "power_unit-r3").mkdir()
    attempt = {"seed": 3, "iou": 0.99, "near_label": 0.6, "labels_used": 3, "labels_listed": 3, "passes": False}
    (folder / "power_unit-r3" / "map.json").write_text(json.dumps(
        {"take": "power_unit-r3", "passes": False, "front": {"attempts": [attempt], "passes": False}, "views": {}}))
    found = checks.judge(surface_gates.guarded("maps checked", finish_rows.judge_maps), folder,
                         {"surfaces-inputs": str(folder)}, None)
    assert found.answer == checks.FAIL and checks.blocks(found.answer)
    assert len(found.findings) == 1 and found.findings[0].startswith("power_unit-r3: no finish map settled")
    shutil.rmtree(folder)


# The seed tray's paper label on black plastic, as baked (greenhouse bake output 439948bc): each of its 65 triangles'
# baked L*a*b*, area (to the largest), the surfaces within its reach (potting_soil, printed_paper, tray_plastic) and
# whether its corners straddle a part border. 19 of them bake the plastic's near black.
SEED_TRAY_PAPER = [
    (79.2, -0.7, 7.6, 0.1987, "011", False),
    (79.2, -0.7, 7.6, 0.8008, "011", False),
    (9.9, 0.7, -0.5, 0.2788, "011", True),
    (79.2, -0.7, 7.6, 0.534, "011", False),
    (9.3, 0.5, -1.4, 0.4221, "011", True),
    (9.9, 0.7, -0.5, 0.1251, "011", True),
    (9.9, 0.7, -0.5, 0.1117, "011", True),
    (9.9, 0.7, -0.5, 0.1437, "011", True),
    (9.9, 0.7, -0.5, 0.4054, "111", True),
    (79.2, -0.7, 7.6, 0.2535, "011", False),
    (9.9, 0.7, -0.5, 0.1022, "011", True),
    (78.8, -0.7, 7.7, 0.8483, "111", False),
    (10.0, 1.2, -0.3, 0.4276, "011", True),
    (77.7, -0.7, 7.7, 0.5298, "011", False),
    (79.2, -0.7, 7.6, 0.3602, "011", False),
    (79.2, -0.7, 7.6, 0.2877, "011", False),
    (78.5, -0.5, 7.2, 0.5201, "011", False),
    (77.0, -0.7, 7.7, 0.2867, "011", False),
    (75.1, -1.1, 7.6, 0.3235, "011", False),
    (79.2, -0.7, 7.6, 0.1694, "011", False),
    (79.2, -0.7, 7.6, 0.676, "011", False),
    (74.5, -0.5, 7.2, 0.0633, "011", False),
    (74.9, -0.5, 7.2, 0.1252, "011", True),
    (20.8, -0.0, 1.4, 0.105, "011", True),
    (72.3, -0.5, 7.3, 0.3978, "011", True),
    (79.2, -0.7, 7.6, 0.226, "011", False),
    (76.7, -0.7, 7.7, 0.608, "011", True),
    (79.2, -0.7, 7.6, 0.7381, "011", True),
    (10.0, 1.2, -0.3, 0.0822, "011", True),
    (74.1, -0.5, 7.2, 0.2326, "011", False),
    (74.1, -0.5, 7.2, 0.1202, "010", False),
    (79.2, -0.7, 7.6, 0.0853, "011", True),
    (79.2, -0.7, 7.6, 0.4938, "011", False),
    (78.1, -0.7, 7.7, 0.3396, "011", False),
    (10.7, 1.7, 1.4, 0.1247, "011", True),
    (75.6, -0.5, 7.2, 0.5145, "011", False),
    (79.2, -0.7, 7.6, 0.896, "011", False),
    (79.2, -0.7, 7.6, 0.1385, "011", False),
    (78.8, -0.7, 7.7, 0.6235, "111", False),
    (9.9, 0.7, -0.5, 0.3203, "111", True),
    (79.2, -0.7, 7.6, 0.1366, "011", False),
    (9.9, 0.7, -0.5, 0.757, "111", True),
    (65.5, -0.5, 6.3, 0.118, "011", False),
    (79.2, -0.7, 7.6, 0.0903, "011", False),
    (9.4, 1.0, -1.2, 0.0811, "011", False),
    (73.0, -0.5, 7.3, 0.4309, "011", True),
    (79.2, -0.7, 7.6, 0.5007, "011", False),
    (10.0, 1.2, -0.3, 0.125, "011", True),
    (9.3, 0.5, -1.4, 0.4311, "011", True),
    (75.6, -0.5, 7.2, 0.3532, "011", False),
    (77.7, -0.7, 7.7, 0.5297, "011", False),
    (78.8, -0.7, 7.7, 0.5839, "011", False),
    (79.2, -0.7, 7.6, 0.1448, "011", True),
    (79.2, -0.7, 7.6, 1.0, "011", False),
    (10.7, 1.7, 1.4, 0.4031, "011", True),
    (10.7, 1.7, 1.4, 0.2377, "011", True),
    (79.2, -0.7, 7.6, 0.098, "011", False),
    (79.2, -0.7, 7.6, 0.6058, "111", True),
    (10.0, 1.2, -0.3, 0.2574, "011", False),
    (74.5, -0.5, 7.2, 0.2059, "011", False),
    (79.2, -0.7, 7.6, 0.1615, "011", False),
    (9.4, 1.0, -1.2, 0.5341, "011", True),
    (77.7, -0.7, 7.7, 0.6325, "011", False),
    (76.3, -0.7, 7.7, 0.4506, "011", False),
    (71.5, -0.5, 7.3, 0.4865, "011", True),
]
SEED_TRAY_SURFACES = [(30.5, 7.6, 15.6), (79.2, -0.7, 7.6), (9.3, 0.5, -1.4)]


def paper_record(rows):
    import numpy as np
    from score.stages.surfaces import bake_check
    colour = np.array([row[:3] for row in rows])
    reach = np.array([[flag == "1" for flag in row[4]] for row in rows])
    share = bake_check.blotch_share(colour, np.array([row[3] for row in rows]), np.ones(len(rows), dtype=bool), reach,
                                    SEED_TRAY_SURFACES)
    return {"surfaces": {"printed_paper": {"share": 0.0117, "baked_lab": [77.7, -0.7, 7.7],
                                           "surface_lab": list(SEED_TRAY_SURFACES[1]), "delta_e": 1.5,
                                           "near_black": share}}}


def test_a_clean_label_border_passes_and_a_black_smudge_along_it_fails():
    from score.stages.surfaces import bake_check
    assert bake_check.surface_faults("seed_tray_1", paper_record(SEED_TRAY_PAPER)) == []
    smudge, area = [], 0.0  # light triangles across the label's border turned black until a tenth of its area
    total = sum(row[3] for row in SEED_TRAY_PAPER)
    for row in SEED_TRAY_PAPER:
        if row[5] and row[0] > bake_check.BLOTCH_L and area < 0.1 * total:
            row, area = (0.0, 0.0, 0.0, *row[3:]), area + row[3]
        smudge.append(row)
    faults = bake_check.surface_faults("seed_tray_1", paper_record(smudge))
    assert len(faults) == 1 and "printed_paper" in faults[0] and "near black" in faults[0], faults
    assert {stage.name: stage for stage in stages.STAGES}["surfaces-check"].make is bake_check.make_check


WATER_TANK_CLOSE_UP = {"painted_panel": [80.3, -0.2, 6.0], "bare_steel": [67.3, -0.3, 1.0],
                       "tank_water": [53.2, -3.2, -2.3]}  # the finish-map method's measures, greenhouse, 2026-10-12


def baked_record(surfaces, close_up):
    """A checks.json record of a model baked exactly on its surfaces ({surface: (share, L*a*b*)})."""
    return {"surfaces": {name: {"share": share, "baked_lab": list(colour), "surface_lab": list(colour),
                                "delta_e": 0.0, "near_black": 0.0} for name, (share, colour) in surfaces.items()},
            "close_up": close_up}


def greenhouse_lab(surface):
    """A greenhouse surface's colour in today's library, L*a*b*."""
    import numpy as np
    import labels
    import library
    spec = {**library.by_library("greenhouse"), **library.resolved("greenhouse")}[surface]
    return [round(float(value), 1) for value in labels.lab(labels.srgb(np.array(spec["colour"]))[None])[0]]


def test_the_water_tank_s_three_greys_fail_as_one_look_and_its_cream_paint_passes():
    from score.stages.surfaces import bake_check
    before = baked_record({"painted_panel": (0.7253, [61.6, -1.5, -6.5]), "bare_steel": (0.1536, [66.3, -1.1, -4.5]),
                           "tank_water": (0.1212, [58.7, -1.7, 2.4])}, WATER_TANK_CLOSE_UP)  # its stored check
    faults = bake_check.surface_faults("water_tank_1", before)
    assert len(faults) == 2 and "one grey look" in faults[0] and "painted_panel is 13.0 L* lighter than bare_steel" \
        in faults[1], faults
    grey_body = baked_record({"painted_panel": (0.7253, [61.6, -1.5, -6.5]),
                              "bare_steel": (0.1536, greenhouse_lab("bare_steel")),
                              "tank_water": (0.1212, greenhouse_lab("tank_water"))}, WATER_TANK_CLOSE_UP)
    faults = bake_check.surface_faults("water_tank_1", grey_body)  # the water fixed, the body still grey
    assert len(faults) == 1 and "lighter than bare_steel" in faults[0], faults
    after = baked_record({"cream_paint": (0.7253, greenhouse_lab("cream_paint")),
                          "bare_steel": (0.1536, greenhouse_lab("bare_steel")),
                          "tank_water": (0.1212, greenhouse_lab("tank_water"))},
                         {"cream_paint": WATER_TANK_CLOSE_UP["painted_panel"],
                          **{name: WATER_TANK_CLOSE_UP[name] for name in ("bare_steel", "tank_water")}})
    assert bake_check.surface_faults("water_tank_1", after) == [], bake_check.surface_faults("water_tank_1", after)
    assert greenhouse_lab("tank_water") != greenhouse_lab("deck"), "the tank's water still takes the deck's colour"
    one = baked_record({"painted_panel": (1.0, [61.6, -1.5, -6.5])}, {"painted_panel": [80.3, -0.2, 6.0]})
    assert bake_check.surface_faults("panel_1", one) == [], "one surface is one look by design"
    dark = baked_record({"painted_panel": (0.9, [61.6, -1.5, -6.5]), "rubber": (0.1, [9.3, 0.5, -1.4])},
                        {"painted_panel": [61.0, 0.0, 0.0], "rubber": [62.0, 0.0, 0.0]})
    faults = bake_check.surface_faults("cabinet_1", dark)
    assert len(faults) == 1 and "rubber" in faults[0] and "over 32" in faults[0], faults


def tank_mesh(ends, height=1.6):
    """A tank's (vertices, faces), its own frame (+y up), on four corner legs ending `ends` up (the water tank's
    measured)."""
    import numpy as np
    import trimesh
    body = trimesh.creation.box(bounds=((-0.7, 0.3, -0.7), (0.7, height, 0.7)))
    legs = [trimesh.creation.box(bounds=((across - 0.05, end, along - 0.05), (across + 0.05, 0.3, along + 0.05)))
            for (across, along), end in zip(((-0.6, -0.6), (0.6, -0.6), (-0.6, 0.6), (0.6, 0.6)), ends)]
    mesh = trimesh.util.concatenate([body, *legs])
    return np.asarray(mesh.vertices), np.asarray(mesh.faces)


def test_a_take_s_short_legs_are_levelled_before_its_bake_and_a_missing_leg_fails_by_name():
    from score.stages.surfaces import place_line
    import feet
    vertices, faces = tank_mesh((0.0, 0.022, 0.052, 0.127))
    points, record = place_line.levelled_feet(vertices, faces)
    assert record["feet"] == 4 and len(record["levelled"]) == 3 and not record["refused"], record
    lows = [low for _, low in feet.feet(feet.surface_points(points, faces), 0.15 * 1.6, 0.05)]
    assert len(lows) == 4 and max(lows) - min(lows) < 1e-9, lows
    points, refused = place_line.levelled_feet(*tank_mesh((0.0, 0.0, 0.0, 0.22)))
    assert refused["refused"] == [round(0.22 / max(1.6, 1.4 * 2 ** 0.5), 4)] and not refused["levelled"], refused
    folder = pathlib.Path(tempfile.mkdtemp())
    for found, verdict in ((record, checks.PASS), (refused, checks.FAIL)):
        (folder / "painted.json").write_text(json.dumps({"takes": {"water_tank-r1": {"feet": found}}}))
        judged = place_line.judge_feet(folder, {}, None)
        assert judged.answer == verdict and (verdict == checks.PASS or "water_tank-r1" in judged.findings[0]), judged
    shutil.rmtree(folder)
    paint = {stage.name: stage for stage in stages.STAGES}["surfaces-paint"]
    assert "feet in one plane" in [check.name for check in paint.checks]
    rules = REPO / "data/checks/resting.json"
    tank = {"place": "greenhouse", "kind": "greenhouse_water_tank"}
    glove = {"place": "lab", "kind": "lab_hanging_glove"}  # held on its cabinet, but it hangs: no feet to level
    assert place_line.stands_on_feet(tank, REPO / "data/inventory/greenhouse.json", rules)
    assert not place_line.stands_on_feet(glove, REPO / "data/inventory/lab.json", rules)
    assert paint.files("greenhouse")["inventory greenhouse"] == "{data}/inventory/greenhouse.json"


def test_the_bake_takes_every_spec_today_s_library_knows_and_stops_on_a_missing_picture():
    """camp's bake, 2026-10-12: a locker label's spec in the job named a picture in another checkout."""
    from score.stages.surfaces import place_line
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary) / "take"
        folder.mkdir()
        (folder / "dark_panel.ply").write_text("")
        stale = {"label_crew_lockers": {"recipe": "printed", "image": "/gone/label_crew_lockers.png"},
                 "dark_panel": {"recipe": "painted_metal", "colour": [0, 0, 0]}}
        found = place_line.baking_specs("hangar", stale, [folder])
        assert pathlib.Path(found["label_crew_lockers"]["image"]).exists(), found["label_crew_lockers"]
        assert found["dark_panel"]["library"] == "dark_panel", found["dark_panel"]
        try:
            place_line.baking_specs("hangar", {**stale, "own_decal": {"image": "/gone/own.png"}}, [folder])
        except RuntimeError as refused:
            assert "own_decal" in str(refused), refused
        else:
            raise AssertionError("a spec naming a missing picture was baked")


def test_a_killed_paint_on_the_machine_says_its_signal_and_peak():
    sys.path.insert(0, str(REPO / "score/stages/surfaces/inside"))
    import paint_take
    code, peak = paint_take.measured([sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGKILL)"],
                                     dict(os.environ))
    assert code == -9 and peak > 0, (code, peak)


def test_a_take_s_paint_job_sends_what_it_reads_and_brings_its_folder_back():
    from score.stages.surfaces import place_line
    with tempfile.TemporaryDirectory() as temporary:
        out, parts = pathlib.Path(temporary) / "out", pathlib.Path(temporary) / "parts"
        out.mkdir()
        inputs = {"surfaces": REPO / "data/surfaces/campgrounds.json", "surfaces-parts": parts,
                  "inventory campgrounds": REPO / "data/inventory/campgrounds.json",
                  "resting rules": REPO / "data/checks/resting.json"}
        job = json.loads(place_line.paint_job(inputs, place_line.prop_env.short(inputs), out, "crane-r1",
                                              [{"part": 0}]).read_text())
        assert job["script"] == "score/stages/surfaces/inside/paint_take.py" and job["outputs"] == [
            str(out / "labelled" / "crane-r1")]
        sent = set(job["inputs"])
        assert {str(parts / "crane-r1"), str(parts / "parts.json"), str(REPO / "score"), str(REPO / "tools/props"),
                str(REPO / "data/library")} <= sent, sent
        assert any(path.endswith("work/pixal/crane-r1-final.glb") for path in sent), sent
        listing = json.loads(pathlib.Path(job["args"][0]).read_text())
        assert listing["paint take"] == "crane-r1" and listing["paint repo"] == str(REPO)  # data may lie elsewhere
        assert json.loads(pathlib.Path(listing["paint records"]).read_text()) == [{"part": 0}]


def test_a_bake_is_held_against_its_surface_dirtied_as_far_as_its_place_s_dirt():
    """The wreck: dirt 0.6 in regolith (L* 56.8); its white hull (89.6) bakes to 69.0 and is on its surface; the same
    white at a clean place, or baked darker than its dirt reaches, is not; a wrong surface is not."""
    import numpy as np
    from score.stages.surfaces import bake_check
    white, regolith = np.array([89.6, -1.7, 1.6]), np.array([56.8, 0.2, 3.1])
    baked = np.array([69.0, -0.8, -3.2])
    assert bake_check.on_surface(baked, white, regolith, 0.6) < 6
    assert bake_check.on_surface(baked, white, regolith, 0.0) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(np.array([40.0, 0, 0]), white, regolith, 0.6) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(baked, white, None, 0.6) > bake_check.BAKE_DELTA_E

def test_a_standing_model_with_a_foot_off_the_floor_fails_and_lying_wreckage_is_left_out():
    """The hangar's parts rack stood on a middle part, its legs 22 cm up."""
    import numpy as np
    from score.stages.surfaces import bake_check
    feet = [(x, z) for x in (-0.5, 0.5) for z in (-0.3, 0.3)]
    level = np.array([[x, 0.0, z] for x, z in feet] + [[0, 1.0, 0]])
    rack = np.array([[x, 0.22 if x > 0 else 0.0, z] for x, z in feet] + [[0, 1.0, 0]])
    assert max(bake_check.stance_lows(level)) == 0.0
    assert abs(max(bake_check.stance_lows(rack)) - 0.22) < 1e-6
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        (folder / "labels.json").write_text(json.dumps({"feet": {"feet": 4}}))
        rows = [{"id": "parts_rack_1", "name": "steel parts rack"}, {"id": "leg_strut", "name": "torn-off landing leg"}]
        assert bake_check.stands("parts_rack_1", folder, rows, ["torn"])
        assert not bake_check.stands("leg_strut", folder, rows, ["torn"])
        (folder / "labels.json").write_text(json.dumps({"feet": {"skipped": "no floor or held row lays its kind"}}))
        assert not bake_check.stands("parts_rack_1", folder, rows, ["torn"])
        (folder / "checks.json").write_text(json.dumps({
            "parts_rack_1": {"stands": True, "stance_lows": [0.0, 0.221, 0.0, 0.24]},
            "leg_strut": {"stands": False, "stance_lows": [0.0, 0.3, 0.2, 0.0]},
            "crate": {"stands": True, "stance_lows": [0.0, 0.01, 0.0, 0.02]}}))
        verdict = bake_check.judge_stance(folder, {}, None)
    assert verdict.answer == "fail" and len(verdict.findings) == 1 and "parts_rack_1: a foot 24.0 cm" in verdict.findings[0]
    assert set(json.loads((REPO / "data/checks/stance.json").read_text())) == {"about", "lies"}

if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
