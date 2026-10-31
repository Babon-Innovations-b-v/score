"""A scene's base stands from its own design, with no spend: every row that read a round-three seed or an old kit reads
earth-seed instead, a reader is handed its seeds and design kits under their old names, the export leaves out and
names a piece no row made, and the gates fail by name; a shell stands round its locked plan (a room's deck, walls and
roof, an open place's raised levels; every other shell and every stair the scene record's, each laid once), each part
painted from the scene's own surface library or named missing, and a design base passes the seed gates, the
placeholder gate and the collision gate. Volumes and corners are worked out by hand from the plans below.

Each test names the break that turns it red (`Break: <file>: `old` -> `new``); each was applied once and seen red.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest
score/stages/earth_seed/test_a_scene_s_base_stands_from_its_design.py
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


def test_no_row_reads_an_earth_place_s_round_three_seed_or_old_kit():
    """#27: the round-three seeds were lost (2026-10-19) and the old kits retired (2026-10-21): no row of an earth place
    declares one, and every row that read one reads earth-seed instead (stages.EARTH_SEEDED, every reader).
    Every row's declared files are read whether or not it applies here: scene-clips (people places only) declared
    the round-three seed and was missed by a check that skipped it (env1, 2026-10-28: "its input seed is missing").
    Break: score/stages/__init__.py: `return {name: path for name, path in found.items() if read_from_seed(path, place)
        is None}` -> `return found`; or drop "scene-clips" from EARTH_SEEDED."""
    readers = set()
    for row in stages.STAGES:
        for place in PLACES:
            found = row.files(place) if callable(row.files) else row.files
            if any(stages.read_from_seed(path, place) for path in found.values()):
                readers.add(row.name)
    assert not readers, readers  # terrain-look, the last, retired (#27)
    # whatever this home's designs hold: no row outside EARTH_SEEDED declares a round-three seed or an old kit
    declaring = {row.name for row in stages.STAGES if row.name not in stages.EARTH_SEEDED for place in PLACES
                 for path in (row.files(place) if callable(row.files) else row.files).values()
                 if isinstance(path, str) and path.startswith((f"{{seeds}}/{stages.OLD_SEED}/", stages.KITS))}
    assert not declaring, declaring
    reading = {row.name for row in stages.STAGES if "earth-seed" in row.after} - {stages.library.PLACE_ROW}
    assert reading == set(stages.EARTH_SEEDED), reading ^ set(stages.EARTH_SEEDED)


def test_a_reader_gets_its_seeds_and_design_kits_under_their_old_names():
    """A reader's old names point into earth-seed's outputs: its own seed and design kit from its own row, a shown
    place's from beside; a place with no earth-seed row (no design locked) stays a declared file, named lost.
    Break: score/stages/__init__.py: `taken[name] = output / named if seed_named(pattern, place) else
        earth_seed.kit_in(output)` -> `taken[name] = output / named`"""
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
    """The export the seed runs leaves out a piece whose model no row made (the lamp) and names it once, however often
    it is asked.
    Break: tools/usd/export.py: `gaps.extend({"model": model} for model in sorted(missing) if {"model": model} not in
        gaps)` -> `gaps.extend({"model": model} for model in sorted(missing))`"""
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
    """An output with no design kit is no seed; one with it is; a model no row made fails `laid` by name and a pick not
    shown fails `picks` by its row.
    Break: score/stages/earth_seed/__init__.py: `return faults + [f"no {name}" for name in (GAPS, KIT_FILE) if not
        (folder / name).exists()]` -> `return faults`
    Break: score/stages/earth_seed/__init__.py: `checks.FAIL if missing else checks.PASS, reason, {"missing"` ->
        `checks.PASS, reason, {"missing"`"""
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
    the walls a ring 0.15 to 0.35 m out (4.7 x 3.7 less 4.3 x 3.3 = 3.2 m2) from the deck's foot (-0.2 m) to 2.5 m,
    less the door's hole of 1.0 x 0.2 x 2.0 m; the room's middle the place's origin; the deck's top the floor itself
    (the lab's things all stood 0.042 m over its deck, laid by the retired kits' floor plates, motion@lab round 35).
    Break: score/stages/earth_seed/design_shell.py: `        if head < high:` -> `        if False:`
    Break: score/stages/earth_seed/design_shell.py: `DECK_BELOW = 0.0` -> `DECK_BELOW = 0.042`"""
    parts = {name: triangles for name, triangles, _ in design_shell.shell(ROOM)}
    assert sorted(parts) == ["deck_1", "roof_1", "wall_1", "wall_2", "wall_3", "wall_4"], sorted(parts)
    assert abs(volume(parts["deck_1"]) - 4.3 * 3.3 * 0.2) < 1e-6, volume(parts["deck_1"])
    assert abs(volume(parts["roof_1"]) - 4.3 * 3.3 * 0.2) < 1e-6, volume(parts["roof_1"])
    walls = sum(volume(parts[f"wall_{number}"]) for number in range(1, 5))
    assert abs(walls - ((4.7 * 3.7 - 4.3 * 3.3) * (2.5 + 0.2) - 1.0 * 0.2 * 2.0)) < 1e-6, walls
    north = numpy.asarray(parts["wall_1"], float).mean(axis=1)  # [x, up, y] of each face's middle
    in_door = (north[:, 0] > 1.5 + 1e-6) & (north[:, 0] < 2.5 - 1e-6) & \
        (north[:, 1] > 1e-6) & (north[:, 1] < 2.0 - 1e-6)
    assert not in_door.any(), north[in_door]
    points = numpy.vstack([design_shell.placed(triangles, ROOM) for triangles in parts.values()])
    assert numpy.allclose(points.min(axis=0), [-2.35, -0.2, -1.85]) and \
        numpy.allclose(points.max(axis=0), [2.35, 2.7, 1.85]), (points.min(axis=0), points.max(axis=0))
    assert abs(numpy.asarray(parts["deck_1"], float)[..., 1].max()) < 1e-9, "the deck's top is the floor"
    from score.stages.scene_record import writer
    assert (design_shell.BACKING, design_shell.DECK_BELOW) == (writer.BACKING, writer.DECK_BELOW)
    assert design_shell.footprint(ROOM) == [[-2.0, -1.5], [2.0, 1.5]]
    # a pitched roof rising 1 m: a closed gable over the 4.3 x 3.3 m grown box, half its box's volume
    pitched = {name: triangles for name, triangles, _ in design_shell.shell(
        dict(ROOM, roofs=[{"kind": "pitched", "points": BOX, "eave": 2.5, "top": 3.5}]))}
    assert abs(volume(pitched["roof_1"]) - 4.3 * 3.3 * 1.0 / 2) < 1e-6, volume(pitched["roof_1"])


def test_every_wall_the_plan_writes_is_built_and_cut_where_its_opening_sits():
    """The test room with an inner wall across it at y 1.5 (0.2 m thick, 2.5 m high), a door 1 m wide in its middle,
    and a quarter arc of 1 m round its middle: the outline's own written walls are built once (wall_1 to wall_4), the
    inner wall centred on its line (y 1.4 to 1.6) from the deck's foot to 2.5 m less the door's hole (4 x 0.2 x 2.7 -
    1.0 x 0.2 x 2.0 = 1.76 m3), the arc in six 15 degree pieces; the door is on a wall the shell builds. The lab's
    doors stood in their entry passages' end walls, which the outline does not hold, and hung on nothing (motion@lab,
    round 35).
    Break: score/stages/earth_seed/design_shell.py: `return found + inner_pieces(plan, len(outline), openings,
        roof_eave)` -> `return found`
    Break: score/stages/earth_seed/design_shell.py: `and not on_outline(entry, outline) for start, end in` -> `for
        start, end in`"""
    plan = {**ROOM, "walls": ROOM["walls"] + [
        {"from": [0.0, 1.5], "to": [4.0, 1.5], "thick": 0.2, "tall": 2.5},
        {"arc": {"centre": [2.0, 1.5], "radius": 1.0, "start": 0.0, "end": 90.0}, "thick": 0.2, "tall": 2.5}],
        "openings": [{"kind": "door", "at": [2.0, 1.5], "wide": 1.0, "sill": 0.0, "head": 2.0, "to": "lab"}]}
    parts = {name: triangles for name, triangles, _ in design_shell.shell(plan)}
    assert sorted(name for name in parts if name.startswith("wall")) == [f"wall_{number}" for number in
                                                                         sorted(range(1, 12), key=str)], sorted(parts)
    assert abs(volume(parts["wall_5"]) - (4 * 0.2 * 2.7 - 1.0 * 0.2 * 2.0)) < 1e-6, volume(parts["wall_5"])
    across = numpy.asarray(parts["wall_5"], float)[..., 2]
    assert numpy.isclose(across.min(), 1.4) and numpy.isclose(across.max(), 1.6), (across.min(), across.max())
    ends = numpy.asarray([corner for number in range(6, 12) for triangle in parts[f"wall_{number}"]
                          for corner in triangle], float)[:, [0, 2]]
    assert numpy.allclose(numpy.linalg.norm(ends - [2.0, 1.5], axis=1).max(), 1.1, atol=0.01), "the arc's pieces"
    assert design_shell.on_a_wall(plan, plan["openings"][0]) and not design_shell.on_a_wall(
        ROOM, {"at": [2.0, 1.5], "wide": 1.0, "sill": 0.0, "head": 2.0})


def test_a_door_in_a_round_wall_s_gap_has_its_wall_built_round_it():
    """Camp (2026-10-31): its dome's round wall is drawn from 190 to 170 degrees, its gap where its entry tube meets
    it, and the plan's door stands in that gap. In the test room, a round wall of 1.4 m round its middle with a 40
    degree gap at the west and a 1 m door there (about 41 degrees of it): the pieces across the gap are built, the door
    sits on a built wall, cut in them; a round wall's gap with no opening stays open.
    Break: score/stages/earth_seed/design_shell.py: `for start, end in written_lines(entry) + gap_lines(entry,
        openings)` -> `for start, end in written_lines(entry)`"""
    round_wall = {"arc": {"centre": [2.0, 1.5], "radius": 1.4, "start": 200.0, "end": 160.0}, "thick": 0.2, "tall": 2.5}
    door = {"kind": "door", "at": [0.6, 1.5], "wide": 1.0, "sill": 0.0, "head": 2.0, "to": "tube"}
    plan = {**ROOM, "walls": ROOM["walls"] + [round_wall], "openings": [door]}
    assert design_shell.on_a_wall(plan, door), "the door in the gap is on a built wall"
    gap = design_shell.gap_lines(round_wall, design_shell.openings_of(plan))
    assert gap and all(abs(numpy.linalg.norm(numpy.subtract(point, [2.0, 1.5])) - 1.4) < 1e-6
                       for line in gap for point in line), gap
    assert all(point[0] < 1.0 for line in gap for point in line), "across the west gap only"
    assert design_shell.gap_lines(round_wall, []) == []


def test_a_dome_roof_stands_as_a_dome():
    """Batch 1 of 2026-10-27: the greenhouse's glass dome stood as a gable along its box's longer side, so over its
    3 m walk two of the five astronauts its concept stands there ran into the roof and the cast left them out. A dome
    is a sphere's cap over the circle round the grown box's middle (2.15 x 1.65 m to a corner, so 2.7102 m), rising
    from its eave to its top, as tools/usd/builders' `dome` draws it from the scene record's entry.
    Break: score/stages/earth_seed/design_shell.py: `domed = entry.get("kind") == "dome"` -> `domed = False`"""
    sys.path.insert(0, str(REPO / "tools" / "usd"))
    import builders
    from score.stages.scene_record import writer
    domed = dict(ROOM, roofs=[{"kind": "dome", "points": BOX, "eave": 2.5, "top": 4.0}])
    name, (piece,), said = design_shell.roofs(domed, design_shell.outline_of(domed), 2.5)[0]
    assert piece["builder"] == "dome" and "a dome" in said, (piece, said)
    assert numpy.allclose(piece["centre"], [2.0, 1.5]) and abs(piece["radius"] - (2.15 ** 2 + 1.65 ** 2) ** 0.5) < 1e-9
    roof = numpy.asarray({part: triangles for part, triangles, _ in design_shell.shell(domed)}["roof_1"]).reshape(-1, 3)
    assert abs(roof[:, 1].max() - 4.0) < 1e-9 and abs(roof[:, 1].min() - 2.5) < 1e-9, (roof[:, 1].min(), roof[:, 1].max())
    entry = writer.shell_entry(name, 0, piece, domed, said)
    drawn = builders.dome(**{key: entry[key] for key in ("radius", "base", "rise", "centre")}, surface=None)["points"]
    # the record keeps its numbers to 0.1 mm
    seed = design_shell.placed(roof, domed)
    apart = numpy.linalg.norm(seed[:, None] - numpy.asarray(drawn)[None], axis=2)
    assert apart.min(axis=1).max() < 1e-3 and apart.min(axis=0).max() < 1e-3, "the record's dome is not the seed's"


def test_a_vault_roof_stands_as_an_arc():
    """Round 33 of 2026-10-30: the tube's vault (eave 0 m, top 3.2 m) stood as a gable, so its flat sides came down
    through the room: the cast stood person_mid_left_1 on a 32 degree side 0.27 m up (sim-body: 0.147 m into it) and
    the other two under it at 1.86 and 2.09 m. A vault is a circle's arc from its eave up to its top across its grown
    box, along the longer side: over BOX's 4.3 x 3.3 m from 0 to 2 m, a circle of (1.65^2 + 2^2) / 4 = 1.680625 m, so
    1 m off the ridge it stands sqrt(1.680625^2 - 1) - (1.680625 - 2) = 1.670 m (a gable's 0.788 m); as
    tools/usd/builders' `tube_arc` draws it from the scene record's entry, the box either way round.
    Break: score/stages/earth_seed/design_shell.py: `entry.get("kind") == "vault"` -> `False`"""
    sys.path.insert(0, str(REPO / "tools" / "usd"))
    import scene
    from score.stages.scene_record import writer
    for box, across in ((BOX, 2), ([[y, x] for x, y in BOX], 0)):
        vaulted = dict(ROOM, outline=box, roofs=[{"kind": "vault", "points": box, "eave": 0.0, "top": 2.0}])
        name, (piece,), said = design_shell.roofs(vaulted, design_shell.outline_of(vaulted), 0.0)[0]
        assert piece["builder"] == "vault" and "arc" in said, (piece, said)
        roof = numpy.asarray({part: tris for part, tris, _ in design_shell.shell(vaulted)}["roof_1"]).reshape(-1, 3)
        assert abs(roof[:, 1].max() - 2.0) < 1e-9 and abs(roof[:, 1].min()) < 1e-9, (roof[:, 1].min(), roof[:, 1].max())
        order = numpy.argsort(roof[:, across])
        assert abs(numpy.interp(1.5 + 1.0, roof[order, across], roof[order, 1]) - 1.670) < 0.01
        entry = writer.shell_entry(name, 0, piece, vaulted, said)
        assert entry["builder"] == "tube_arc", entry
        drawn = numpy.vstack([mesh["points"] for mesh in scene.built_meshes(dict(entry, surface=None))])
        # the record keeps its numbers to 0.1 mm
        seed = design_shell.placed(roof, vaulted)
        apart = numpy.linalg.norm(seed[:, None] - drawn[None], axis=2)
        assert apart.min(axis=1).max() < 1e-3 and apart.min(axis=0).max() < 1e-3, "the record's vault is not the seed's"


def test_the_parts_a_shell_lays_are_named_without_building_it():
    """2026-10-27: the scene library and the surface tiles asked which parts a shell lays by building it, so every
    change to how a part is built keyed them (and the people, sound and palette rows behind them). shell_parts.parts
    names them from the plan's words alone, the same kinds design_shell's pieces and levels lay.
    Break: score/stages/shell_parts.py: `walled = len({(float(x), float(y)) for x, y in corners}) > 1` -> `walled = False`"""
    from score.stages import shell_parts
    domed = dict(ROOM, roofs=[{"kind": "dome", "points": BOX, "eave": 2.5, "top": 4.0}])
    for plan in (ROOM, OPEN, domed, dict(OPEN, levels=OPEN["levels"][:1]), dict(ROOM, shell="domed", inside=None)):
        laid = design_shell.pieces(plan) if design_shell.encloses(plan) or design_shell.laid_for(plan) else \
            design_shell.levels(plan)
        assert shell_parts.parts(plan) == {design_shell.part_kind(name) for name, _, _ in laid}, plan["title"]


def test_a_door_or_window_row_cuts_its_opening_where_its_plan_item_stands_on_a_wall():
    """2026-10-26: Batch 1's doors and windows stood at plan items the plan's openings missed, against uncut walls. A
    row filling an opening (a door, window, gate, hatch or shutter, a panel) cuts one at its item on a wall, its own
    wide, from its shape's base to its top; one at the plan's own opening cuts none more; a box is no panel, and a
    panel-shaped lid fills no opening.
    Break: score/stages/earth_seed/design_shell.py: `if any(np.linalg.norm(np.subtract(at, other["at"])) < (wide +
        other["wide"]) / 2 for other in own):` -> `if False:`
    Break: score/stages/earth_seed/design_shell.py: `return (bool(words & OPENING_KINDS) and` -> `return (bool(words)
        and`"""
    rows = [{"id": "window", "name": "porthole window", "noun": "window", "size": [1.0, 0.1, 1.0]},
            {"id": "door", "name": "door", "noun": "door", "size": [1.0, 0.1, 2.0]},
            {"id": "door_control_box", "name": "door control box", "noun": "box", "size": [0.2, 0.1, 0.3]},
            {"id": "lid", "name": "crate lid", "noun": "lid", "size": [1.0, 0.1, 1.0]}]
    plan = dict(ROOM, items=[["WINDOW 1", 3.95, 1.0, 0.1, 1.0, None, "item"], ["DOOR 1", 1.5, -0.05, 1.0, 0.1, None,
                                                                                "item"],
                             ["BOX 1", 0.0, 1.0, 0.1, 0.2, None, "item"],
                             ["LID 1", -0.05, 2.0, 0.1, 1.0, None, "item"]],
                rows={"WINDOW 1": ["window"], "DOOR 1": ["door"], "BOX 1": ["door_control_box"], "LID 1": ["lid"]},
                shapes={"WINDOW 1": {"base": 1.0, "tall": 1.0}, "DOOR 1": {"base": 0.0, "tall": 2.0}})
    assert design_shell.row_openings(plan, rows) == [{"at": [4.0, 1.5], "wide": 1.0, "sill": 1.0, "head": 2.0,
                                                     "row": "window"}]
    cut = {name: triangles for name, triangles, _ in design_shell.shell(design_shell.cut_for(plan, rows))}
    whole = {name: triangles for name, triangles, _ in design_shell.shell(plan)}
    assert abs(volume(whole["wall_2"]) - volume(cut["wall_2"]) - 1.0 * 0.2 * 1.0) < 1e-6  # the window's hole
    assert abs(volume(whole["wall_1"]) - volume(cut["wall_1"])) < 1e-9  # the door's is the plan's own


def test_the_walls_cut_an_opening_the_relations_cut_for_a_door_the_plan_s_openings_do_not_hold(tmp_path):
    """#72 (cockpit's four rear doors, one opening on its plan): the place's relations (score/review/holders) cut an
    opening for a door or window the plan's own openings each hold another of; the walls cut it, once where a row's
    own stands within their half widths. A 1 x 1 m window opening cut at (4, 1.5) from 1 m up takes 1.0 x 0.2 x 1.0
    out of the east wall. Relations derived from another plan than the kept one are left out, with why.
    Break: score/stages/earth_seed/design_shell.py: `for cut in relation_cuts(relations):` -> `for cut in []:`"""
    relations = {"relations": [{"item": "ON THE WALLS AND CEILING", "row": "window", "how": "in", "opening": {
        "at": [4.0, 1.5], "wide": 1.0, "sill": 1.0, "head": 2.0, "cut": True}}]}
    cut = {name: triangles for name, triangles, _ in design_shell.shell(design_shell.cut_for(ROOM, [], relations))}
    whole = {name: triangles for name, triangles, _ in design_shell.shell(ROOM)}
    assert abs(volume(whole["wall_2"]) - volume(cut["wall_2"]) - 1.0 * 0.2 * 1.0) < 1e-6
    (tmp_path / "plan.json").write_text(json.dumps(ROOM))
    (tmp_path / "relations.json").write_text(json.dumps({**relations, "plan": "another plan's sha"}))
    assert design_shell.relations_read({"relations": tmp_path / "relations.json"}, tmp_path / "plan.json")[0] is None


def test_a_relation_s_cut_replaces_a_row_s_opening_no_wall_cuts():
    """#36, cockpit 2026-10-30: its rear door's row opening stood at its plan item's middle, 0.75 m off its slanted
    wall's line, so no wall cut it, and the relation's opening on the wall's line was left out as standing within
    their half widths: the wall stood uncut and the door swung into it. A window row's item 0.6 m inside the east wall
    (past its 0.2 m and ON_WALL) gives way to the relation's cut at (4, 1.5), which takes its 1.0 x 0.2 x 1.0 m out of
    the wall; an item on the wall keeps its own opening and the relation's cuts none more.
    Break: score/stages/earth_seed/design_shell.py: `if not kept:` -> `if not near:`"""
    rows = [{"id": "window", "name": "porthole window", "noun": "window", "size": [1.0, 0.1, 1.0]}]
    cut = {"at": [4.0, 1.5], "wide": 1.0, "sill": 1.0, "head": 2.0}
    relations = {"relations": [{"item": "ON THE WALLS AND CEILING", "row": "window", "how": "in",
                                "opening": {**cut, "cut": True}}]}
    whole = {name: triangles for name, triangles, _ in design_shell.shell(ROOM)}
    for x, found in ((3.35, [cut]), (3.95, [{"at": [4.0, 1.5], "wide": 1.0, "sill": 1.0, "head": 2.0, "row": "window"}])):
        plan = dict(ROOM, items=[["WINDOW 1", x, 1.0, 0.1, 1.0, None, "item"]], rows={"WINDOW 1": ["window"]},
                    shapes={"WINDOW 1": {"base": 1.0, "tall": 1.0}})
        assert design_shell.cut_for(plan, rows, relations)["row_openings"] == found, x
        laid = {name: triangles for name, triangles, _ in design_shell.shell(design_shell.cut_for(plan, rows, relations))}
        assert abs(volume(whole["wall_2"]) - volume(laid["wall_2"]) - 1.0 * 0.2 * 1.0) < 1e-6, x


def test_a_room_is_a_kit_shell_inside_or_one_that_writes_walls():
    """A scene added in the app says neither inside nor out: it is a room the earth seed lays when its plan writes walls
    (the docking airlock), an open place when it writes none (the Moon base); a domed shell is the scene record's.
    Break: score/stages/earth_seed/design_shell.py: `return plan.get("shell") == "kit" and (bool(inside) if inside is
        not None else bool(plan.get("walls")))` -> `return plan.get("shell") == "kit"`"""
    unsaid = {key: value for key, value in ROOM.items() if key != "inside"}
    assert design_shell.laid_for(ROOM) and design_shell.laid_for(unsaid)
    assert not design_shell.laid_for(dict(unsaid, walls=[])) and not design_shell.laid_for(OPEN)
    assert not design_shell.laid_for(dict(ROOM, shell="outdoor")) and not design_shell.laid_for(dict(ROOM, shell=None))


def test_the_earth_seed_and_the_scene_record_lay_each_shell_once():
    """The scene record encloses a place by the same rule (writer.inside is design_shell.encloses) and lays the shell of
    every enclosed place the earth seed does not (laid_for), and every stair; the earth seed lays a room's shell and an
    open place's raised levels, never a stair. Worked by hand on OPEN: the plaza (0 m) is the ground's, no part; the
    stage deck stands solid from the ground (2 x 2 x 1 m), the balcony is a slab (2 x 2 x 0.2 m).
    Break: score/stages/earth_seed/design_shell.py: `return bool(plan.get("walls") or plan.get("roofs")) and not
        (plan.get("terrain") or {}).get("spots")` -> `return bool(plan.get("walls"))`
    Break: score/stages/earth_seed/design_shell.py: `standing = 0.0 < height <= STOREY` -> `standing = False`"""
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
    names why.
    Break: score/stages/surfaces/palette_library.py: `for wanted in SHELL_KINDS[part] if kinds.get(wanted)), None)` ->
        `for wanted in SHELL_KINDS[part][:1] if kinds.get(wanted)), None)`
    Break: score/stages/earth_seed/design_shell.py: `    if library is None:` -> `    if False:`"""
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
    scenes under it its; plans that hold each other round in a ring give none.
    Break: score/stages/earth_seed/__init__.py: `return own if name == place else name` -> `return own`"""
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
        outpost = {**inputs, "holder outpost": earth_seed.DESIGN / "plans/outpost.json"}
        assert earth_seed.style_of("yard_shed", outpost) == "outpost"
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
    too, and it declares no old scene record or kit.
    Break: score/stages/earth_seed/__init__.py: `return sorted({claim["place"] for claim in
        surface_data.record(place).get("elsewhere", {}).values()})` -> `return []`
    Break: score/stages/earth_seed/__init__.py: `found["surfaces"] = surface_data.pattern(place)` -> `pass`"""
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
    with no library every part is named missing.
    Break: score/stages/earth_seed/design_shell.py: `tools.colliders.solid(prim.GetPrim(), mesh["points"],
        mesh["triangles"])` -> `pass`
    Break: score/stages/earth_seed/design_shell.py: `paint(stage, prim, place, part_kind(name), library, scene)` ->
        `pass`"""
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
