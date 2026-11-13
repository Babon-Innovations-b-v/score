"""A scene's base stands from its own design, with no spend: every row that read a round-three seed or an old kit reads
earth-seed instead, a reader is handed its seeds and design kits under their old names, the export leaves out and
names a piece no row made, and the gates fail by name; a shell stands round its locked plan (a room's deck, walls and
roof, an open place's raised levels; every other shell and every stair the scene record's, each laid once), each part
painted from the scene's own surface library or named missing, and a design base passes the seed gates, the
placeholder gate and the collision gate. Volumes and corners are worked out by hand from the plans below.

Breaks (each applied once, seen red, reverted), as `Break: <file>: `old` -> `new``:
Break: score/stages/__init__.py: drop "scene-clips" from EARTH_SEEDED. (Not caught: `return {name: path for name,
    path in found.items() if read_from_seed(path, place) is None}` -> `return found` stays green here, as on the
    unfolded file.)
Break: score/stages/__init__.py: `taken[name] = output / named if seed_named(pattern, place) else
    earth_seed.kit_in(output)` -> `taken[name] = output / named`
Break: tools/usd/export.py: `gaps.extend({"model": model} for model in sorted(missing) if {"model": model} not in
    gaps)` -> `gaps.extend({"model": model} for model in sorted(missing))`
Break: score/stages/earth_seed/__init__.py: `return faults + [f"no {name}" for name in (GAPS, KIT_FILE) if not
    (folder / name).exists()]` -> `return faults`
Break: score/stages/earth_seed/__init__.py: `checks.FAIL if missing else checks.PASS, reason, {"missing"` ->
    `checks.PASS, reason, {"missing"`
Break: score/stages/earth_seed/design_shell.py: `    if not entry:
    return BACKING` -> `    if True:
    return BACKING`
Break: score/stages/earth_seed/design_shell.py: `            ON_WALL:` -> `            ON_WALL + 1.0:`
Break: score/stages/earth_seed/design_shell.py: `        if head < high:` -> `        if False:`
Break: score/stages/earth_seed/design_shell.py: `DECK_BELOW = 0.0` -> `DECK_BELOW = 0.042`
Break: score/stages/earth_seed/design_shell.py: `if not rising and holes:` -> `if False:` (the hangar's roof one
    solid slab though its plan opens it 27 x 55 m for the ship, 2026-11-04)
Break: score/stages/earth_seed/design_shell.py: `if abs(high - height) <= 1e-3 and low < height - 1e-3 and` ->
    `if False and`
Break: score/stages/earth_seed/design_shell.py: `blocked = sorted((begin - half, finish + half) for begin, finish,
    *_ in cuts)` -> `blocked = []`
Break: score/stages/earth_seed/design_shell.py: `across = 0 if high[0] - low[0] <= high[1] - low[1] else 1` ->
    `across = 0`
Break: score/stages/earth_seed/design_shell.py: `size, count = sized(row), max(int(row.get("count") or 1),
    len(items))` -> `size, count = sized(row), len(items)`
Break: score/stages/earth_seed/design_shell.py: `return found + inner_pieces(plan, len(outline), openings,
    roof_eave)` -> `return found`
Break: score/stages/earth_seed/design_shell.py: `and not on_outline(entry, outline) for start, end in` -> `for
    start, end in`
Break: score/stages/earth_seed/design_shell.py: `written_lines(entry) + gap_lines(entry, openings)` ->
    `written_lines(entry)`
Break: score/stages/earth_seed/design_shell.py: `domed, vaulted = entry.get("kind") == "dome",` -> `domed, vaulted =
    False,`
Break: score/stages/earth_seed/design_shell.py: `, entry.get("kind") == "vault"` -> `, False`
Break: score/stages/earth_seed/design_shell.py: `return ends >= sides` -> `return True`
Break: score/stages/shell_parts.py: `walled = len({(float(x), float(y)) for x, y in corners}) > 1` -> `walled = False`
Break: score/stages/earth_seed/design_shell.py: `if any(np.linalg.norm(np.subtract(at, other["at"])) < (wide +
    other["wide"]) / 2 for other in own):` -> `if False:`
Break: score/stages/earth_seed/design_shell.py: `return (bool(words & OPENING_KINDS) and` -> `return (bool(words)
    and`
Break: score/stages/earth_seed/design_shell.py: `for row, cut in relation_cuts(relations):` -> `for row, cut in
    []:`
Break: score/stages/earth_seed/design_shell.py: `other.get("row") != row` -> `on_a_wall(plan, other)`
Break: score/stages/earth_seed/design_shell.py: `for row, cut in relation_cuts(relations):` -> `for row, cut in
    relation_cuts(relations)[:1]:`
Break: score/stages/shell_parts.py: `return plan.get("shell") == "kit" and (bool(inside) if inside is
    not None else bool(plan.get("walls")))` -> `return plan.get("shell") == "kit"`
Break: score/stages/shell_parts.py: `return bool(plan.get("walls") or plan.get("roofs")) and not
    (plan.get("terrain") or {}).get("spots")` -> `return bool(plan.get("walls"))`
Break: score/stages/earth_seed/design_shell.py: `standing = 0.0 < height <= STOREY` -> `standing = False`
Break: score/stages/earth_seed/design_shell.py: `words = palette_library.SHELL_KINDS[kind]` -> `words =
    palette_library.SHELL_KINDS[kind][:1]` (surface_for no longer reads palette_library.shell_surface, so the old
    break there was green)
Break: score/stages/earth_seed/design_shell.py: `    if library is None:` -> `    if False:`
Break: score/stages/earth_seed/__init__.py: `return own if name == place else name` -> `return own`
Break: score/stages/earth_seed/__init__.py: `return sorted({claim["place"] for claim in
    surface_data.record(place).get("elsewhere", {}).values()})` -> `return []`
Break: score/stages/earth_seed/__init__.py: `found["surfaces"] = surface_data.pattern(place)` -> `pass`
Break: score/stages/earth_seed/design_shell.py: `tools.colliders.solid(prim.GetPrim(), mesh["points"],
    mesh["triangles"])` -> `pass`
Break: score/stages/earth_seed/design_shell.py: `paint(stage, prim, place, part_kind(name), library, scene)` ->
    `pass`

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest
score/stages/earth_seed/test_a_scene_s_base_stands_from_its_design.py
"""
import json
import pathlib
import sys

import numpy
import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/usd"))

from score import checks, stages  # noqa: E402
from score.stages import earth_seed, shell_parts  # noqa: E402
from score.stages.earth_seed import design_shell  # noqa: E402
from score.stages.scene_record import writer  # noqa: E402
from score.stages.surfaces import surface_data  # noqa: E402

PLACES = ("hangar", "wreck", "street", "airlock", "launch", "camp")

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
ROOM_PARTS = ["deck_1", "roof_1", "wall_1", "wall_2", "wall_3", "wall_4"]


def write(folder, name, record):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(record))
    return folder / name


def volume(triangles):
    """A closed triangle soup's volume (the divergence theorem: each face's tetrahedron to the origin)."""
    corners = numpy.asarray(triangles, float).reshape(-1, 3, 3)
    return float(numpy.einsum("ij,ij->i", corners[:, 0], numpy.cross(corners[:, 1], corners[:, 2])).sum() / 6)


def shell_of(plan):
    """The shell design_shell lays for `plan`, {part name: its triangles}."""
    return {name: triangles for name, triangles, _ in design_shell.shell(plan)}


def middles(triangles):
    """Each face's middle, [x, up, y]."""
    return numpy.asarray(triangles, float).mean(axis=1)


def corners(parts, names):
    """Every corner of the named parts in plan metres, [x, y]."""
    found = [corner for name in names for triangle in parts[name] for corner in triangle]
    return numpy.asarray(found, float)[:, [0, 2]]


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


def designs(root, plans):
    """A design folder holding `plans` ({scene: its locked plan}) under plans/; the folder."""
    for scene, plan in plans.items():
        write(root / "plans", f"{scene}.json", plan)
    return root


def test_a_scene_s_base_stands_from_its_design(tmp_path, monkeypatch):
    """One store with no spend: the row registry, a made-only export, the shells of the plans below (each worked by
    hand), one earth-seed made for a scene added in the app, and one design home of locked plans; every behaviour a
    scene's base hangs on is asserted on those, the pure judgements as rows of tables naming their case."""
    import builders
    import colliders
    import export
    import placeholders
    import scene
    from pxr import Usd, UsdShade

    # --- the rows (#27): the round-three seeds were lost (2026-10-19) and the old kits retired (2026-10-21); every
    # row's declared files are read whether or not it applies here (scene-clips, people places only, declared the
    # round-three seed and was missed by a check that skipped it, env1 2026-10-28).
    declared = {(row.name, place): (row.files(place) if callable(row.files) else row.files)
                for row in stages.STAGES for place in PLACES}
    readers = {name for (name, place), found in declared.items()
               if any(stages.read_from_seed(path, place) for path in found.values())}
    assert not readers, readers  # terrain-look, the last, retired (#27)
    declaring = {name for (name, _), found in declared.items() if name not in stages.EARTH_SEEDED
                 for path in found.values()
                 if isinstance(path, str) and path.startswith((f"{{seeds}}/{stages.OLD_SEED}/", stages.KITS))}
    assert not declaring, declaring
    reading = {row.name for row in stages.STAGES if "earth-seed" in row.after} - {stages.library.PLACE_ROW}
    assert reading == set(stages.EARTH_SEEDED), reading ^ set(stages.EARTH_SEEDED)

    # --- the export the seed runs leaves out a piece whose model no row made (the lamp), named once however often
    (tmp_path / "made").mkdir()
    (tmp_path / "made/wall_1.gltf").write_text("{}")
    gaps, pieces = [], [{"model": "wall_1"}, {"model": "lamp_1"}, {"model": "lamp_1"}]
    assert export.made_only(pieces, [tmp_path / "made"], gaps) == [{"model": "wall_1"}]
    export.made_only(pieces, [tmp_path / "made"], gaps)
    assert gaps == [{"model": "lamp_1"}], gaps

    # --- the shells. Plans: ROOM; its walls drawn on lines 0.1 m inside its outline (its outer faces, as plan writing
    # draws them); a pitched roof rising 1 m; a flat roof with a 2 x 1 m opening (the hangar's roof door); a flight
    # from the floor down 1 m on a 1 x 1 m footprint (the hangar's floor hatch); an inner wall across at y 1.5 with a
    # door in its middle and a quarter arc of 1 m round its middle (the lab's doors stood in their entry passages' end
    # walls, which the outline does not hold, and hung on nothing, motion@lab round 35); OPEN; an enclosed place that is
    # no earth-seed room (the scene record's shell).
    inset = [[0.1, 0.1], [3.9, 0.1], [3.9, 2.9], [0.1, 2.9]]
    hatch = [[1.0, 1.0], [3.0, 1.0], [3.0, 2.0], [1.0, 2.0]]
    inner_door = {"kind": "door", "at": [2.0, 1.5], "wide": 1.0, "sill": 0.0, "head": 2.0, "to": "lab"}
    plans = {
        "room": ROOM,
        "inset": dict(ROOM, walls=[{"from": one, "to": two, "thick": 0.2, "tall": 2.5}
                                   for one, two in zip(inset, inset[1:] + inset[:1])]),
        "pitched": dict(ROOM, roofs=[{"kind": "pitched", "points": BOX, "eave": 2.5, "top": 3.5}]),
        "roof door": dict(ROOM, roofs=[{"kind": "flat", "points": BOX, "eave": 2.5, "top": 2.5,
                                        "openings": [{"points": hatch}]}]),
        "floor hatch": dict(ROOM, stairs=[{"kind": "stair", "points": [[1.0, 1.0], [2.0, 1.0], [2.0, 2.0], [1.0, 2.0]],
                                           "from": 0.0, "to": -1.0, "steps": 5}]),
        "inner walls": {**ROOM, "openings": [inner_door], "walls": ROOM["walls"] + [
            {"from": [0.0, 1.5], "to": [4.0, 1.5], "thick": 0.2, "tall": 2.5},
            {"arc": {"centre": [2.0, 1.5], "radius": 1.0, "start": 0.0, "end": 90.0}, "thick": 0.2, "tall": 2.5}]},
        "room with stairs": dict(ROOM, stairs=OPEN["stairs"]),
        "open": OPEN,
        "enclosed, not a room": dict(OPEN, shell=None, walls=ROOM["walls"]),
    }
    shells = {name: shell_of(plan) for name, plan in plans.items()}
    # the parts each lays: a room its deck, walls and roof (the inner plan's outline walls once, wall_1 to wall_4, the
    # inner wall wall_5 and the arc in six 15 degree pieces), never a stair or a level (a room's levels are its decks);
    # an open place its raised levels (the plaza is the ground's), never a stair; the scene record's enclosure none
    laid = [("room", ROOM_PARTS), ("room with stairs", ROOM_PARTS), ("open", ["level_2", "level_3"]),
            ("enclosed, not a room", []),
            ("inner walls", ["deck_1", "roof_1"] + [f"wall_{number}" for number in sorted(range(1, 12), key=str)])]
    for name, parts in laid:
        assert sorted(shells[name]) == parts, (name, sorted(shells[name]))
    # volumes worked by hand: the walls each on its written line, 0.1 m either side of the outline (4.2 x 3.2 less
    # 3.8 x 2.8 = 2.8 m2) from the deck's foot (-0.2 m) to 2.5 m, less the door's hole of 1.0 x 0.2 x 2.0 m; deck and
    # roof each 3.8 x 2.8 x 0.2 m (out to the walls' room faces), 3.6 x 2.6 m for the inset walls; a gable rising 1 m
    # half its box; a roof or deck less its opening; the inner wall 4 x 0.2 x 2.7 less its door; the stage deck solid
    # from the ground (2 x 2 x 1 m), the balcony a slab (2 x 2 x 0.2 m)
    volumes = [("room", ("deck_1",), 3.8 * 2.8 * 0.2), ("room", ("roof_1",), 3.8 * 2.8 * 0.2),
               ("room", ("wall_1", "wall_2", "wall_3", "wall_4"),
                (4.2 * 3.2 - 3.8 * 2.8) * (2.5 + 0.2) - 1.0 * 0.2 * 2.0),
               ("inset", ("deck_1",), 3.6 * 2.6 * 0.2), ("pitched", ("roof_1",), 3.8 * 2.8 * 1.0 / 2),
               ("roof door", ("roof_1",), (3.8 * 2.8 - 2.0) * 0.2),
               ("floor hatch", ("deck_1",), (3.8 * 2.8 - 1.0) * 0.2),
               ("inner walls", ("wall_5",), 4 * 0.2 * 2.7 - 1.0 * 0.2 * 2.0),
               ("open", ("level_2",), 4.0), ("open", ("level_3",), 0.8)]
    for name, parts, expected in volumes:
        measured = sum(volume(shells[name][part]) for part in parts)
        assert abs(measured - expected) < 1e-6, (name, parts, measured, expected)
    room = shells["room"]
    # the inset walls are built from the outline to 0.2 m in: each wall's room face is its written wall's, where holders
    # lays a wall thing (2026-11-07: storage's wall lights stood 0.31 m off its built walls, hanging free)
    faces = corners(shells["inset"], [f"wall_{number}" for number in range(1, 5)])
    assert numpy.allclose([faces.min(axis=0), faces.max(axis=0)], [[0.0, 0.0], [4.0, 3.0]]), faces
    north = middles(room["wall_1"])
    in_door = (north[:, 0] > 1.5 + 1e-6) & (north[:, 0] < 2.5 - 1e-6) & \
        (north[:, 1] > 1e-6) & (north[:, 1] < 2.0 - 1e-6)
    assert not in_door.any(), north[in_door]
    points = numpy.vstack([design_shell.placed(triangles, ROOM) for triangles in room.values()])
    assert numpy.allclose(points.min(axis=0), [-2.1, -0.2, -1.6]) and \
        numpy.allclose(points.max(axis=0), [2.1, 2.7, 1.6]), (points.min(axis=0), points.max(axis=0))
    # the deck's top is the floor itself (the lab's things stood 0.042 m over the retired kits' floor plates)
    assert abs(numpy.asarray(room["deck_1"], float)[..., 1].max()) < 1e-9, "the deck's top is the floor"
    over = middles(shells["roof door"]["roof_1"])
    assert not ((over[:, 0] > 1.0 + 1e-6) & (over[:, 0] < 3.0 - 1e-6) & (over[:, 2] > 1.0 + 1e-6)
                & (over[:, 2] < 2.0 - 1e-6)).any(), "the roof is closed over its opening"
    across = numpy.asarray(shells["inner walls"]["wall_5"], float)[..., 2]
    assert numpy.isclose(across.min(), 1.4) and numpy.isclose(across.max(), 1.6), (across.min(), across.max())
    arc = corners(shells["inner walls"], [f"wall_{number}" for number in range(6, 12)])
    assert numpy.allclose(numpy.linalg.norm(arc - [2.0, 1.5], axis=1).max(), 1.1, atol=0.01), "the arc's pieces"

    # --- the shell's own structural rows (the hangar's pillars, pad and grates, the garage's beams, 2026-11-05): 4
    # pillars 0.4 x 0.3 m spaced 3.5 m round the 14 m outline from 1.75 m, the first slid off the door (cut 1.5 to
    # 2.5 m) to end 0.2 m before it, its back on the north wall's room face at y 0.1, 2.5 m high (its 3 m capped at the
    # wall's top); 2 beams 0.2 x 0.3 m across the 3 m side at x 1 and 3, wall face to wall face, under the 2.5 m eave;
    # a grate row of 2 on one 2 x 1 m item split along it, 0.02 m thick
    rows = [{"id": "wall_pillars", "part": "structure", "name": "wall pillars", "size": [0.4, 0.3, 3.0], "count": 4},
            {"id": "ceiling_beam", "part": "structure", "name": "ceiling beam", "size": [5.0, 0.2, 0.3], "count": 2},
            {"id": "floor_grates", "part": "floor", "name": "floor grates", "count": 2},
            {"id": "floor_plates", "part": "floor", "name": "floor plates", "size": [4.0, 3.0, 0.1]}]
    built = {name: (piece, kind) for _, name, piece, _, kind in design_shell.row_pieces(
        dict(ROOM, items=[["GRATES", 1.0, 1.0, 2.0, 1.0, None, "item"], ["WALLS", 0.0, 0.0, 4.0, 3.0, None, "item"]],
             rows={"GRATES": ["floor_grates"], "WALLS": ["floor_plates", "wall_pillars", "ceiling_beam"]},
             shapes={"GRATES": {"shape": "rect", "tall": 0.0, "base": 0.0}}), rows)}
    assert sorted(built) == ["ceiling_beam_1", "ceiling_beam_2", "floor_grates_1", "floor_grates_2", "wall_pillars_1",
                             "wall_pillars_2", "wall_pillars_3", "wall_pillars_4"], sorted(built)
    pillar, kind = built["wall_pillars_1"]
    assert numpy.allclose(pillar["points"], [[1.1, 0.1], [1.5, 0.1], [1.5, 0.4], [1.1, 0.4]]) and \
        (pillar["low"], pillar["high"]) == (0.0, 2.5) and kind == "wall", pillar
    beam = built["ceiling_beam_1"][0]
    assert numpy.allclose(beam["points"], [[0.9, 0.1], [0.9, 2.9], [1.1, 2.9], [1.1, 0.1]]) and \
        numpy.allclose([beam["low"], beam["high"]], [2.2, 2.5]), beam
    assert numpy.allclose(built["ceiling_beam_2"][0]["points"][0], [2.9, 0.1]), built["ceiling_beam_2"]
    grates = [built[f"floor_grates_{number}"][0] for number in (1, 2)]
    assert [numpy.asarray(grate["points"])[:, 0].tolist() for grate in grates] == [[1.0, 2.0, 2.0, 1.0],
                                                                                [2.0, 3.0, 3.0, 2.0]] and \
        all((grate["low"], grate["high"]) == (0.0, design_shell.FLUSH) for grate in grates), grates

    # --- rising roofs stand as their kind, and the scene record's entry draws the seed's own roof (to 0.1 mm). A dome
    # (batch 1 of 2026-10-27: the greenhouse's glass dome stood as a gable and ran into two of its astronauts) is a
    # sphere's cap over the circle round the grown box's middle (walls unwritten, so 0.15 m out: 2.15 x 1.65 m to a
    # corner). A vault (round 33 of 2026-10-30: the tube's vault stood as a gable, its flat sides through the room) is a
    # circle's arc across its grown box along the longer side: over BOX's 4.3 x 3.3 m from 0 to 2 m a circle of
    # (1.65^2 + 2^2) / 4 = 1.680625 m, so 1 m off the ridge sqrt(1.680625^2 - 1) - (1.680625 - 2) = 1.670 m (a gable's
    # 0.788 m), the box either way round. A square box's vault runs between the ends its openings stand on (round 44
    # of 2026-11-02: the tube's vault ran across its length, came down to 1.3 m at its doorways, spot-1's eye stood
    # over the roof): over SQUARE (grown to 4.3) from 0 to 2 m, doors north and south, a circle of
    # (2.15^2 + 2^2) / 4 = 2.155625 m across x, its crown at x = 2 the full 2 m by the north door (run east it would
    # stand 0.951 m); doors west and east it runs east, turned a quarter in the scene record.
    square = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]

    def vaulted(box, doors=None):
        """ROOM on `box` under a vault from 0 to 2 m, its walls unwritten, a door at each of `doors`."""
        extra = {"w": 4.0, "d": 4.0, "openings": [{"kind": "door", "at": at, "wide": 1.0, "sill": 0.0, "head": 2.0,
                                                   "to": "hangar"} for at in doors]} if doors else {}
        return dict(ROOM, outline=box, walls=[], roofs=[{"kind": "vault", "points": box, "eave": 0.0, "top": 2.0}],
                    **extra)

    corner = (2.15 ** 2 + 1.65 ** 2) ** 0.5
    rising = [  # plan, eave, its piece's builder and fields, its words, a height off the ridge, a crown, turned
        ("dome", dict(ROOM, walls=[], roofs=[{"kind": "dome", "points": BOX, "eave": 2.5, "top": 4.0}]), 2.5, 4.0,
         "dome", {"centre": [2.0, 1.5], "radius": corner}, "a dome", None, None, None),
        ("vault along BOX", vaulted(BOX), 0.0, 2.0, "vault", {}, "arc", (2, 1.670), None, None),
        ("vault along BOX turned", vaulted([[y, x] for x, y in BOX]), 0.0, 2.0, "vault", {}, "arc", (0, 1.670),
         None, None),
        ("square vault, doors north and south", vaulted(square, ([2.0, 0.0], [2.0, 4.0])), 0.0, 2.0, "vault",
         {"lengthwise": False}, "arc", None, [2.0, 0.3], False),
        ("square vault, doors west and east", vaulted(square, ([0.0, 2.0], [4.0, 2.0])), 0.0, 2.0, "vault",
         {"lengthwise": True}, "arc", None, [0.3, 2.0], True)]
    for label, plan, eave, top, kind, fields, words, off_ridge, crown, turned in rising:
        name, (piece,), said = design_shell.roofs(plan, design_shell.outline_of(plan), eave)[0]
        assert piece["builder"] == kind and words in said, (label, piece, said)
        for key, value in fields.items():
            assert piece[key] is value if isinstance(value, bool) else \
                numpy.allclose(piece[key], value, rtol=0.0, atol=1e-9), (label, key, piece[key])
        roof = numpy.asarray(shell_of(plan)["roof_1"]).reshape(-1, 3)
        assert abs(roof[:, 1].max() - top) < 1e-9 and abs(roof[:, 1].min() - eave) < 1e-9, (label, roof[:, 1].min())
        if off_ridge:
            axis, height = off_ridge
            order = numpy.argsort(roof[:, axis])
            assert abs(numpy.interp(1.5 + 1.0, roof[order, axis], roof[order, 1]) - height) < 0.01, label
        if crown:
            solid = numpy.asarray(design_shell.solid(piece)).reshape(-1, 3)
            near = solid[numpy.argsort(numpy.hypot(solid[:, 0] - crown[0], solid[:, 2] - crown[1]))[:4]]
            assert abs(near[:, 1].max() - 2.0) < 0.05, (label, near)
        entry = writer.shell_entry(name, 0, piece, plan, said)
        assert entry["builder"] == {"dome": "dome", "vault": "tube_arc"}[kind], (label, entry)
        if turned is not None:
            assert (entry["placed_turn"] != [0.0, 0.0, 0.0, 1.0]) is turned, (label, entry["placed_turn"])
        if kind == "dome":
            drawn = builders.dome(**{key: entry[key] for key in ("radius", "base", "rise", "centre")},
                                  surface=None)["points"]
        else:
            drawn = numpy.vstack([mesh["points"] for mesh in scene.built_meshes(dict(entry, surface=None))])
        apart = numpy.linalg.norm(design_shell.placed(roof, plan)[:, None] - numpy.asarray(drawn)[None], axis=2)
        assert apart.min(axis=1).max() < 1e-3 and apart.min(axis=0).max() < 1e-3, \
            (label, "the record's is not the seed's")

    # --- openings: a row filling an opening (door, window, gate, hatch or shutter, a panel) cuts one at its item on a
    # wall, its own wide, from its shape's base to its top; one at the plan's own opening cuts none more; a box is no
    # panel and a panel-shaped lid fills none (2026-10-26: Batch 1's doors and windows stood against uncut walls). The
    # place's relations cut one for a door or window the plan's openings do not hold (#72) and replace a row's own
    # opening within their half widths, on the wall or off it (#36, cockpit 2026-10-30: its rear door's row opening
    # 0.75 m off its slanted wall, uncut; settle@engineroom 2026-11-08: its window's row opening kept 0.66 m from where
    # holders cut it, and door 3's cut beside it left out). Each row: the openings cut_for gives, and the cubic metres
    # each wall loses against ROOM's.
    fillers = [{"id": "window", "name": "porthole window", "noun": "window", "size": [1.0, 0.1, 1.0]},
               {"id": "door", "name": "door", "noun": "door", "size": [1.0, 0.1, 2.0]},
               {"id": "door_control_box", "name": "door control box", "noun": "box", "size": [0.2, 0.1, 0.3]},
               {"id": "lid", "name": "crate lid", "noun": "lid", "size": [1.0, 0.1, 1.0]}]
    window_only = fillers[:1]

    def windowed(x, y=1.0):
        """ROOM with a window row's item at (x, y), 1 m wide from 1 m up."""
        return dict(ROOM, items=[["WINDOW 1", x, y, 0.1, 1.0, None, "item"]], rows={"WINDOW 1": ["window"]},
                    shapes={"WINDOW 1": {"base": 1.0, "tall": 1.0}})

    cut = {"at": [4.0, 1.5], "wide": 1.0, "sill": 1.0, "head": 2.0}
    moved = {"at": [4.0, 2.0], "wide": 1.0, "sill": 1.0, "head": 2.0}
    door = {"at": [4.0, 0.6], "wide": 1.0, "sill": 0.0, "head": 2.0}
    walls_cut = {"relations": [{"item": "ON THE WALLS AND CEILING", "row": "window", "how": "in",
                                "opening": {**cut, "cut": True}}]}
    beside = {"relations": [{"item": "WINDOW 1", "row": "window", "how": "in", "opening": {**moved, "cut": True}},
                            {"item": "DOOR 1", "row": "door", "how": "in", "opening": {**door, "cut": True}}]}
    items = dict(ROOM, items=[["WINDOW 1", 3.95, 1.0, 0.1, 1.0, None, "item"],
                              ["DOOR 1", 1.5, -0.05, 1.0, 0.1, None, "item"],
                              ["BOX 1", 0.0, 1.0, 0.1, 0.2, None, "item"],
                              ["LID 1", -0.05, 2.0, 0.1, 1.0, None, "item"]],
                 rows={"WINDOW 1": ["window"], "DOOR 1": ["door"], "BOX 1": ["door_control_box"], "LID 1": ["lid"]},
                 shapes={"WINDOW 1": {"base": 1.0, "tall": 1.0}, "DOOR 1": {"base": 0.0, "tall": 2.0}})
    openings = [
        ("a window row cuts its own, a door at the plan's own none more, a box or lid none", items, fillers, None,
         [{**cut, "row": "window"}], {"wall_2": 1.0 * 0.2 * 1.0, "wall_1": 0.0}),
        ("the relations cut a window the plan does not hold", ROOM, [], walls_cut, [cut], {"wall_2": 1.0 * 0.2 * 1.0}),
        ("a relation's cut replaces a row's opening 0.6 m off the wall", windowed(3.35), window_only, walls_cut, [cut],
         {"wall_2": 1.0 * 0.2 * 1.0}),
        ("a relation's cut replaces a row's opening on the wall", windowed(3.95), window_only, walls_cut, [cut],
         {"wall_2": 1.0 * 0.2 * 1.0}),
        ("a relation moves a window and cuts another row's door beside it", windowed(3.95, 0.8), window_only, beside,
         [moved, door], {"wall_2": 1.0 * 0.2 * 1.0 + 1.0 * 0.2 * 2.0})]
    for label, plan, fills, relations, expected, lost in openings:
        opened = design_shell.cut_for(plan, fills, relations)
        assert opened["row_openings"] == expected, (label, opened["row_openings"])
        laid = shell_of(opened)
        for wall, hole in lost.items():
            measured = volume(room[wall]) - volume(laid[wall])
            assert abs(measured - hole) < (1e-9 if hole == 0.0 else 1e-6), (label, wall, measured, hole)
    assert design_shell.row_openings(items, fillers) == openings[0][4]
    # relations derived from another plan than the kept one are left out, with why
    write(tmp_path, "plan.json", ROOM)
    write(tmp_path, "relations.json", {**walls_cut, "plan": "another plan's sha"})
    kept_relations = design_shell.relations_read({"relations": tmp_path / "relations.json"}, tmp_path / "plan.json")

    # --- a round wall's gap (camp, 2026-10-31: its dome's wall drawn from 190 to 170 degrees, its door in the gap where
    # its entry tube meets it): in ROOM a round wall of 1.4 m round its middle with a 40 degree gap at the west and a
    # 1 m door there; the pieces across the gap are built, on its circle and only across the west gap
    round_wall = {"arc": {"centre": [2.0, 1.5], "radius": 1.4, "start": 200.0, "end": 160.0}, "thick": 0.2, "tall": 2.5}
    gap_door = {"kind": "door", "at": [0.6, 1.5], "wide": 1.0, "sill": 0.0, "head": 2.0, "to": "tube"}
    gap_plan = {**ROOM, "walls": ROOM["walls"] + [round_wall], "openings": [gap_door]}
    gap = design_shell.gap_lines(round_wall, design_shell.openings_of(gap_plan))
    assert gap and all(abs(numpy.linalg.norm(numpy.subtract(point, [2.0, 1.5])) - 1.4) < 1e-6
                       for line in gap for point in line), gap
    assert all(point[0] < 1.0 for line in gap for point in line), "across the west gap only"

    # --- judgements, each row (what, its answer, the answer it must be)
    library = {"kinds": {"floor": ["deck_plate", "rubber_mat"], "ceiling": ["ceiling_panel"], "wall": []}}
    unsaid = {key: value for key, value in ROOM.items() if key != "inside"}
    far = dict(ROOM, walls=[{"from": [0.0, 0.75], "to": [4.0, 0.75], "thick": 0.1, "tall": 2.5}])
    domed = dict(ROOM, roofs=[{"kind": "dome", "points": BOX, "eave": 2.5, "top": 4.0}])
    enclosed = plans["enclosed, not a room"]
    judged = [
        # a room is a kit shell inside, or one that writes walls when it says neither (the docking airlock); an open
        # place writes none (the Moon base); an outdoor or unnamed shell is the scene record's
        ("a room said inside is the earth seed's", design_shell.laid_for(ROOM), True),
        ("a room that does not say, writing walls, is the earth seed's", design_shell.laid_for(unsaid), True),
        ("a place that does not say, writing no walls, is not", design_shell.laid_for(dict(unsaid, walls=[])), False),
        ("an open place is not", design_shell.laid_for(OPEN), False),
        ("an outdoor shell is not", design_shell.laid_for(dict(ROOM, shell="outdoor")), False),
        ("a shell of no kind is not", design_shell.laid_for(dict(ROOM, shell=None)), False),
        # the scene record encloses by the same rule as the earth seed
        *((f"the scene record encloses {name} as the earth seed does", writer.inside(plan),
           design_shell.encloses(plan))
          for name, plan in (("the room", ROOM), ("the square", OPEN), ("an enclosure", enclosed),
                             ("an enclosure on terrain spots", dict(enclosed, terrain={"spots": [[1, 1, 0.5]]})),
                             ("a roofed square", dict(OPEN, roofs=ROOM["roofs"])))),
        ("the scene record lays a room's stairs, not its shell",
         [entry["builder"] for entry in writer.structure({"place": "room"}, plans["room with stairs"])],
         ["stairs", "stairs"]),
        # the parts a shell lays are named from the plan's words without building it (2026-10-27: asking by building
        # keyed the scene library, the surface tiles and the people, sound and palette rows behind them)
        *((f"the parts of {plan['title']} ({index}) are named without building", shell_parts.parts(plan),
           {design_shell.part_kind(name) for name, _, _ in (
               design_shell.pieces(plan) if design_shell.encloses(plan) or design_shell.laid_for(plan)
               else design_shell.levels(plan))})
          for index, plan in enumerate((ROOM, OPEN, domed, dict(OPEN, levels=OPEN["levels"][:1]),
                                        dict(ROOM, shell="domed", inside=None)))),
        # an outline wall stands on its written wall's line; a written wall 0.75 m in (airlock's room wall along its
        # porch's edge) is another part's, so that edge's wall stands BACKING behind it; the scene record's equal
        ("a written wall 0.75 m in is not its edge's", design_shell.written_wall(far, BOX[0], BOX[1]), {}),
        ("an edge with no written wall reaches BACKING", design_shell.face_reach({}, BOX[0], BOX[1]),
         design_shell.BACKING),
        ("the scene record backs and sinks decks as the seed", (design_shell.BACKING, design_shell.DECK_BELOW),
         (writer.BACKING, writer.DECK_BELOW)),
        ("the room's middle is the place's origin", design_shell.footprint(ROOM), [[-2.0, -1.5], [2.0, 1.5]]),
        ("a door in the inner wall is on a built wall", design_shell.on_a_wall(plans["inner walls"], inner_door), True),
        ("no wall stands across ROOM at y 1.5",
         design_shell.on_a_wall(ROOM, {"at": [2.0, 1.5], "wide": 1.0, "sill": 0.0, "head": 2.0}), False),
        ("a door in a round wall's gap is on a built wall", design_shell.on_a_wall(gap_plan, gap_door), True),
        ("a round wall's gap with no opening stays open", design_shell.gap_lines(round_wall, []), []),
        ("relations of another plan are left out", kept_relations[0], None),
        # a part's surface is the first variant the scene library's kinds give one of its kinds; none, and it says why
        ("a deck's surface is the floor's first", design_shell.surface_for("deck", library), "deck_plate"),
        ("a stair takes the floor's (no stairs kind)", design_shell.surface_for("stair", library), "deck_plate"),
        ("a roof's is the ceiling's", design_shell.surface_for("roof", library), "ceiling_panel"),
        ("a wall the library gives none has none", design_shell.surface_for("wall", library), None),
        ("no library, no surface", design_shell.surface_for("wall", None), None),
        ("a kind the library names none of says so",
         "names no surface" in design_shell.missing_why("x", "wall", library), True),
        ("no library says it is not made", "not made" in design_shell.missing_why("x", "wall", None), True)]
    for label, answer, expected in judged:
        assert answer == expected, (label, answer, expected)

    # --- earth-seed's make for a scene added in the app (no kit), on ROOM with its scene library: one stage under its
    # name, its shell under /<place>/Shell, each part its library surface where the library gives its kind one and named
    # missing where it gives none (the roof), every part a collider, the placeholder gate failing only the unpainted
    # roof; its style the hangar's (the scene holding it), its kit the design's. As an open place it gets no room; with
    # no library every part is named missing.
    made = tmp_path / "made-seed"
    inputs = {"design plan": write(made, "docking_bay.json", ROOM),
              "design inventory": write(made, "inventory.json", {"rows": []}),
              "places": REPO / "data/definitions/place.json",
              "holder hangar": write(made, "hangar.json", {"holds": [{"place": "docking_bay", "row": "spaceship"}]}),
              earth_seed.LIBRARY_ROW: scene_library(made / "library")}
    outs = {name: made / name for name in ("open", "out", "bare")}
    for out in outs.values():
        out.mkdir()
    earth_seed.make_seed(dict(inputs, **{"design plan": write(made / "open-plan", "docking_bay.json",
                                                               dict(ROOM, inside=False))}), outs["open"], 0, {})
    earth_seed.make_seed(inputs, outs["out"], 0, {})
    earth_seed.make_seed({key: value for key, value in inputs.items() if key != earth_seed.LIBRARY_ROW}, outs["bare"],
                         0, {})
    assert json.loads((outs["open"] / earth_seed.KIT_FILE).read_text())["shell"] == []
    assert not Usd.Stage.Open(str(outs["open"] / "docking_bay/docking_bay.usda")).GetPrimAtPath("/docking_bay/Shell")
    out = outs["out"]
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
    bare = outs["bare"]
    stage = Usd.Stage.Open(str(earth_seed.place_in(bare) / "docking_bay.usda"))
    assert all("not made" in prim.GetAttribute("score:surface:missing").Get()
               for prim in stage.GetPrimAtPath("/docking_bay/Shell").GetChildren())
    # the seed gates fail by name: an output with no design kit is no seed (the kit is what readers read); a model no
    # row made fails `laid` by name and a pick not shown fails `picks` by its row
    (bare / earth_seed.KIT_FILE).unlink()
    assert earth_seed.seed_faults(bare) == [f"no {earth_seed.KIT_FILE}"], earth_seed.seed_faults(bare)
    write(bare, earth_seed.GAPS, {"models": ["cable_run_1p4"], "picks": [
        {"row": "aft_section", "object": None, "why": "no object of this row is on the stage"}]})
    laid_gate, picked = earth_seed.judge_laid(bare, {}, {}), earth_seed.judge_picks(bare, {}, {})
    assert laid_gate.answer == checks.FAIL and laid_gate.findings == ("cable_run_1p4",), laid_gate
    assert picked.answer == checks.FAIL and "aft_section" in picked.findings[0], picked

    # --- one design home of locked plans. A design's base is its design's, never a kit's (the old concepts' kits were
    # retired, 2026-10-21); a scene added in the app takes the style of the scene whose plan holds it; a top scene
    # place.json does not name (the Base) takes its own; plans holding each other round in a ring give none. Its
    # surface data is declared where it has one, the places it claims models from that data's `elsewhere`.
    home = designs(tmp_path / "design", {
        "airlock": {}, "hub": {"w": 12.0, "d": 12.0}, "cockpit": {"w": 9.414, "d": 9.8},
        "hangar": {"holds": [{"place": "cockpit", "row": "spaceship"}, {"place": "docking_bay", "row": "spaceship"}]},
        "outpost": {"holds": [{"place": "yard_shed", "row": "shed"}]},
        "ring_a": {"holds": [{"place": "ring_b", "row": "b"}]}, "ring_b": {"holds": [{"place": "ring_a", "row": "a"}]}})
    write(home / "surfaces", "hub.json", {"library": "hub", "takes": {},
                                          "elsewhere": {"rack_1": {"take": "rack-x", "place": "lab"}}})
    monkeypatch.setattr(earth_seed, "DESIGN", home)
    monkeypatch.setattr(surface_data, "DESIGN", home / "surfaces")
    # what each place's seed declares: present {name: file}, and names it never declares ("holder " any holder)
    declares = [("cockpit", {"design plan": "{home}/design/plans/cockpit.json"}, ("kit", "holder ")),
                ("docking_bay", {"holder hangar": "{home}/design/plans/hangar.json"}, ("kit",)),
                ("hub", {"surfaces": "{home}/design/surfaces/hub.json"}, ("scene", "kit"))]
    for place, present, never in declares:
        found = earth_seed.seed_files(place)
        assert {name: found.get(name) for name in present} == present, (place, found)
        assert not [name for name in found for gone in never
                    if name == gone or (gone.endswith(" ") and name.startswith(gone))], (place, found)
    places = REPO / "data/definitions/place.json"
    plan_of = {place: home / f"plans/{place}.json" for place in ("hangar", "outpost", "ring_a", "ring_b")}
    styles = [
        ("a scene added in the app takes its holder's", earth_seed.style_of(
            "docking_bay", {"places": places, "holder hangar": plan_of["hangar"]}), "hangar"),
        ("a top scene nothing holds has no holder", earth_seed.holders("outpost"), {}),
        ("a top scene place.json does not name takes its own", earth_seed.style_of(
            "outpost", {"places": places, "holder hangar": plan_of["hangar"]}), "outpost"),
        ("a scene under it is held by it", earth_seed.holders("yard_shed"),
         {"outpost": "{home}/design/plans/outpost.json"}),
        ("a scene under it takes its", earth_seed.style_of(
            "yard_shed", {"places": places, "holder outpost": plan_of["outpost"]}), "outpost"),
        ("a ring of holders gives no holders", earth_seed.holders("ring_a"), None),
        ("a scene in a ring is not styled", bool(earth_seed.styled("ring_a")), False),
        *((f"{place} is styled", bool(earth_seed.styled(place)), True)
          for place in ("docking_bay", "cockpit", "outpost")),
        ("the hub claims models from the lab", earth_seed.claiming_places("hub"), ["lab"])]
    for label, answer, expected in styles:
        assert answer == expected, (label, answer, expected)
    with pytest.raises(ValueError, match="ring_a"):  # refused by name, never a loop with no end
        earth_seed.style_of("ring_a", {"places": places, "holder ring_b": plan_of["ring_b"],
                                       "holder ring_a": plan_of["ring_a"]})
    # a reader's old names point into earth-seed's outputs: its own seed and design kit from its own row, a shown
    # place's from beside; a place with no earth-seed row (no design locked) stays a declared file, named lost
    for node, place in (("own", "airlock"), ("hub", "hub")):
        (tmp_path / node / place).mkdir(parents=True)
    seeded = {"earth-seed": tmp_path / "own", "earth-seed@hub": tmp_path / "hub"}
    assert stages.seeded_place(seeded) == "airlock"
    taken = stages.seed_inputs(seeded, {
        "seed": "{seeds}/usd-r3/{place}", "neighbour hub": "{seeds}/usd-r3/hub",
        "neighbour far_city": "{seeds}/usd-r3/far_city", "kit": "{data}/kit/{place}.json",
        "kit hub": "{data}/kit/hub.json", "kit far_city": "{data}/kit/far_city.json"}, "airlock")
    expected = {"seed": tmp_path / "own/airlock", "neighbour hub": tmp_path / "hub/hub",
                "kit": tmp_path / "own" / earth_seed.KIT_FILE, "kit hub": tmp_path / "hub" / earth_seed.KIT_FILE}
    assert {name: taken.get(name) for name in expected} == expected, taken
    assert "neighbour far_city" not in taken and "kit far_city" not in taken, taken
