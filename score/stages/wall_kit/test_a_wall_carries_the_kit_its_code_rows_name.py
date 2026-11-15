"""Invariant: a room's walls carry the kit its code rows name, from the plan alone: a frame round every opening cut,
riveted panels on every face once (none across an opening), a padded section at its plan item on the wall it stands
on, a facade raised to its row's tall with windows over its ground storey, a ceiling hung in riveted panels under its
flat roof (none under a steep one); each piece painted with the scene library
variant its words choose (else the wall's), laid by the scene record as `slab` and `specks` entries tools/usd builds.

Breaks that turn this red (each applied once and seen red, then reverted):
- wall_kit.open_spans: openings not left out (`blocked = []`) -> a panel crosses the door
- wall_kit.pieces: `clad_by` not kept (every panel row clads) -> two claddings of one room
- wall_kit.faces: an outline face not moved out by its face_reach -> the panels stand off the wall
- wall_kit.item_spot: the nearest face not taken -> the padded section lands on another wall
- wall_kit.facade: the wall not raised -> the facade stops at the wall's top
- wall_kit.surface: the wall's surface always -> the padded section is painted as the wall
- scene_record.writer.kit_entries: the place's frame not applied -> the entries stand in plan metres
- wall_kit.is_ceiling_row: `row.get("part") == "roof"` made `False` -> the ceiling row hangs no panels
- wall_kit.ceiling: the CEILING_SLOPE skip dropped -> panels hang under the steep roof
- wall_kit.under_spots: corners not pulled in (`* 0.99` made `* 1.0`) -> a corner on the roof's edge reads no roof
  and the edge panels are left out
"""
import numpy as np

from score.stages import wall_kit
from score.stages.scene_record import writer
from tools.usd import scene


def room():
    """A 6 by 4 m room, walls 0.2 m thick on their lines (outline round their outer faces), 2.5 m high, a door
    0.9 m wide in its north wall at x 3, a padded section's plan item against its west wall."""
    walls = [{"from": [0.1, 0.1], "to": [5.9, 0.1]}, {"from": [5.9, 0.1], "to": [5.9, 3.9]},
             {"from": [5.9, 3.9], "to": [0.1, 3.9]}, {"from": [0.1, 3.9], "to": [0.1, 0.1]}]
    return {"w": 6.0, "d": 4.0, "outline": [[0, 0], [6, 0], [6, 4], [0, 4]],
            "walls": [dict(wall, thick=0.2, tall=2.5) for wall in walls],
            "openings": [{"kind": "door", "at": [3.0, 0.1], "wide": 0.9, "sill": 0.0, "head": 2.1}],
            "items": [["PADDED 1", 0.2, 1.0, 0.1, 1.2, "E", "item"]],
            "rows": {"PADDED 1": ["padded_wall_1"]}, "shapes": {"PADDED 1": {"shape": "rect", "tall": 2.0, "base": 0.0}}}


ROWS = [{"id": "wall_panels", "name": "wall panels", "noun": "wall", "part": "wall", "size": [6, 0.2, 2.5],
         "route": "plan"},
        {"id": "hull", "name": "ship hull", "noun": "hull", "part": "wall", "size": [6, 4, 2.5], "route": "plan"},
        {"id": "padded_wall_1", "name": "padded wall section", "noun": "padded wall", "part": "wall",
         "size": [1.2, 0.1, 2.0], "route": "plan"}]
LIBRARY = {"kinds": {"wall": ["hull_panel_paint"], "seat": ["cushion_vinyl_padded"], "floor": ["deck_plate"]}}


def bounds(piece):
    points = np.array([point for part in piece.parts for point in part["points"]])
    heights = [value for part in piece.parts for value in (part["low"], part["high"])]
    return points.min(axis=0), points.max(axis=0), min(heights), max(heights)


def test_a_wall_carries_the_kit_its_code_rows_name():
    plan = room()
    pieces = wall_kit.pieces(plan, ROWS)
    named = {piece.name: piece for piece in pieces}
    # the door's frame on the north wall's room face (y 0.2), round the cut 2.55 to 3.45
    low, high, bottom, top = bounds(named["frames_wall_1"])
    assert np.allclose([low[0], high[0]], [2.45, 3.55]) and np.allclose([low[1], high[1]], [0.2, 0.25]), (low, high)
    assert np.isclose(top, 2.2) and np.isclose(bottom, 0.0)
    # one cladding, by the panel row, never also by the hull; on each of the four faces, flush on the room face
    clad = [piece for piece in pieces if piece.row in ("wall_panels", "hull") and piece.plain == "plate"]
    assert {piece.row for piece in clad} == {"wall_panels"} and len(clad) == 4, [piece.name for piece in clad]
    north = named["wall_panels_wall_1"]
    for part in north.parts:
        xs = [point[0] for point in part["points"]]
        assert not (min(xs) < 3.45 and max(xs) > 2.55 and part["low"] < 2.1), part
        assert min(point[1] for point in part["points"]) >= 0.2 - 1e-9
    assert max(part["high"] for part in north.parts) <= 2.5 + 1e-9
    # the padded section on the west wall's room face (x 0.2), cushions inside its frame
    low, high, bottom, top = bounds(named["padded_wall_1_1"])
    assert np.isclose(low[0], 0.2) and np.isclose(high[0], 0.2 + wall_kit.PAD_DEEP) and top <= 2.0, (low, high)
    assert wall_kit.surface(named["padded_wall_1_1"], LIBRARY) == "cushion_vinyl_padded"
    assert wall_kit.surface(named["frames_wall_1"], LIBRARY) == "hull_panel_paint"
    assert wall_kit.surface(named["frames_wall_1"], None) is None
    # a facade row raises the outline walls to its tall, with windows over the ground storey
    facade = wall_kit.pieces(plan, [{"id": "front", "name": "building facade", "noun": "facade", "part": "wall",
                                     "size": [3, 36, 12.0], "route": "plan"}])
    kinds = {piece.name.rsplit("_", 1)[1] for piece in facade if piece.row == "front"}
    assert {"raised", "panes", "frames", "bands", "balconies"} <= kinds, kinds
    assert max(bounds(piece)[3] for piece in facade if piece.row == "front") >= 12.0 - 1e-9
    panes = [piece for piece in facade if piece.name.endswith("panes")]
    assert min(part["low"] for piece in panes for part in piece.parts) >= wall_kit.STOREY
    # rivets at the panels' corners, on their faces
    rivets = named["wall_panels_wall_1_rivets"].specks
    assert len(rivets) == 4 * sum(1 for part in north.parts) and all(np.isclose(spot[1], 0.2 + wall_kit.RELIEF)
                                                                      for spot in rivets)
    # a ceiling panel row hangs the room's ceiling (its walls' room faces, 5.6 by 3.6 m) in 5 by 3 panels under its
    # flat roof, riveted, and none under a roof rising steeply across them (a dome's)
    ceiling_row = {"id": "ceiling_panels", "name": "ceiling panels", "noun": "ceiling", "part": "roof",
                   "size": [6, 4, 0.1], "route": "plan"}
    roofed = [[0.21, 0.21], [5.79, 0.21], [5.79, 3.79], [0.21, 3.79]]  # its roof read a cm inside the walls
    hung = {piece.name: piece for piece in wall_kit.pieces(
        plan, [ceiling_row], lambda spot: 2.5 if wall_kit.design_shell.inside(spot, roofed) else 3.6)}
    panels = hung["ceiling_panels_ceiling"].parts
    low, high, bottom, top = bounds(hung["ceiling_panels_ceiling"])
    assert len(panels) == 15 and np.allclose([*low, *high], [0.2, 0.2, 5.8, 3.8], atol=wall_kit.SEAM), (low, high)
    assert np.isclose(top, 2.5) and np.isclose(bottom, 2.5 - wall_kit.CEILING_RELIEF)
    assert len(hung["ceiling_panels_ceiling_rivets"].specks) == 4 * 15
    for under in (None, lambda spot: 2.5 + spot[0] ** 2 / 4):
        assert not [piece for piece in wall_kit.pieces(plan, [ceiling_row], under) if "ceiling" in piece.name]
    # the scene record lays each solid as a slab and each piece's rivets as specks in the place's frame, which
    # tools/usd builds, each saying the wall kit's code made it (the library check traces it so)
    entries = writer.kit_entries(plan, "room", LIBRARY, {"rows": ROWS})
    assert len(entries) == sum(len(piece.parts) + bool(piece.specks) for piece in pieces)
    assert {entry["builder"] for entry in entries} == {"slab", "specks"} and not any("row" in entry for entry in entries)
    cushion = next(entry for entry in entries if entry["name"] == "kit_padded_wall_1_1_1")
    corner, east, _ = writer.place_plan.frame_of(plan)
    assert np.isclose(min(point[0] for point in cushion["points"]), corner[0] + east[0] * 0.2)
    assert cushion["surface"] == "cushion_vinyl_padded" and cushion["from"].endswith("(wall_kit.padded)")
    for entry in (cushion, next(entry for entry in entries if entry["builder"] == "specks")):
        built = scene.built_meshes(entry)
        assert len(built) == 1 and len(built[0]["triangles"]) > 0
