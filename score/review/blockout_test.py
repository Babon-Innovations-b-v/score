"""The blockout (score/review/blockout.py): built from a fixture plan, rendered free, and sent first with a draw."""
import numpy as np
import pytest

from score.review import blockout, concepts, plans
from score.store import Store

HOLDER = {"w": 20.0, "d": 12.0, "height": "walls 6 m to a flat roof",
          "doors": [["S", 10.0, 2.0, "BIG DOOR (2 x 2.6 m)"]],
          "holds": [{"place": "room_a", "row": "hull", "x": 2.0, "y": 2.0, "w": 6.0, "d": 4.0},
                    {"place": "room_b", "row": None, "x": 9.0, "y": 2.0, "w": 5.0, "d": 4.0}]}
ROOM_A = {"w": 6.0, "d": 4.0, "height": "ceiling 2.5 m", "doors": [["E", 2.0, 1.0, "DOOR"]],
          "people": [[1.0, 1.0, 0.0, "DESK"]]}  # a data plan's standing spot: x, y, facing, words


def test_an_inside_places_blockout_is_its_own_room_alone():
    parts, framed = blockout.inside_parts("room_a", HOLDER, ROOM_A, blockout.corner_way())
    kinds = {kind for _, kind in parts}
    assert {"wall", "floor", "person"} <= kinds and not kinds & {"holder", "sibling", "roof"}  # no hull, no roof
    points = np.concatenate([np.asarray(triangles).reshape(-1, 3) for triangles, _ in parts])
    assert points[:, 0].min() >= 2.0 - 0.5 and points[:, 0].max() <= 8.0 + 0.5  # no room beside it
    assert framed == [2.0, 2.0, 6.0, 4.0, 2.5]
    walls = np.concatenate([np.asarray(triangles).reshape(-1, 3) for triangles, kind in parts if kind == "wall"])
    assert walls[:, 1].max() == pytest.approx(2.5)  # its own ceiling, in metres
    assert walls[:, 0].min() >= 2.0 - 1e-6 and walls[:, 0].max() <= 8.0 + 1e-6  # inside its box on the holder
    with pytest.raises(blockout.Missing):
        blockout.inside_parts("room_c", HOLDER, {}, blockout.corner_way())


def test_a_thing_in_a_room_stands_in_its_blockout_as_a_labelled_box_at_its_spot_and_size():
    """Owner, 2026-10-21: the add-scene box dropped inside a room is a thing of that room, in its grey blockout."""
    room = {**HOLDER["holds"][0], "things": [{"name": "nav module", "x": 2.0, "y": 1.0, "w": 2.0, "d": 2.0}]}
    holder = {**HOLDER, "holds": [room, HOLDER["holds"][1]]}
    things, labels = blockout.thing_parts("room_a", holder)
    points = blockout.points_of(things)
    assert points.min(axis=0).tolist() == [4.0, 0.0, 3.0]  # the room's corner (2, 2) plus the thing's (2, 1)
    assert points.max(axis=0).tolist() == [6.0, blockout.THING_TALL, 5.0]
    assert labels == [("nav module", [5.0, blockout.THING_TALL, 4.0])]
    assert blockout.thing_parts("room_b", holder) == ([], [])
    shell, framed = blockout.inside_parts("room_a", holder, ROOM_A, blockout.corner_way())
    camera = blockout.fixed_camera(shell + things, framed)
    bare = np.asarray(blockout.render(shell + things, camera))
    written = np.asarray(blockout.drawn((shell + things, framed, [], None, labels)))
    assert (written != bare).any(axis=-1).sum() > 200  # its name written over it


def test_a_door_is_a_hole_in_its_wall():
    whole = blockout.shell_parts({"w": 6.0, "d": 4.0, "height": "walls 3 m"})
    holed = blockout.shell_parts(ROOM_A)
    count = sum(len(triangles) for triangles, kind in holed if kind == "wall")
    assert count > sum(len(triangles) for triangles, kind in whole if kind == "wall")  # the east wall cut in three
    door = blockout.data_openings({"doors": [[90, 2.2, "HATCH 90 (2.2 x 2.6 m)"]]}, 9.0, 9.0)
    assert door == [{"at": [9.0, 4.5], "wide": 2.2, "head": 2.6}]  # a bearing meets the box's east wall


def test_a_blockout_renders_grey_from_the_fixed_view():
    parts, framed = blockout.inside_parts("room_a", HOLDER, ROOM_A, blockout.corner_way())
    picture = blockout.render(parts, blockout.fixed_camera(parts, framed))
    assert picture.size == (blockout.WIDE, blockout.TALL)
    pixels = np.asarray(picture)
    assert (pixels[..., 0] == pixels[..., 1]).all() and (pixels[..., 1] == pixels[..., 2]).all()  # neutral grey
    assert (pixels != blockout.BACKGROUND).any(axis=-1).mean() > 0.2  # its room alone fills the frame


def test_a_sites_world_is_drawn_at_its_true_size_where_it_stands():
    site = {"size": [20.0, 20.0, 5.0], "footprint": None, "terrain": {"spots": [[0, 0, 0], [30, 0, -2], [0, 30, -2]]},
            "blocks": [{"points": blockout.rectangle(-5, -5, 10, 10), "tall": 5.0, "base": 0.0, "roof": "dome",
                        "rise": 2.0}]}
    earth = {"world": "earth", "name": "Earth", "azimuth": 180.0, "altitude": 30.0, "across": 2.0, "lit": 0.5,
             "lit_from": [1.0, 0.0, 0.0]}
    parts = blockout.site_parts(site)
    assert blockout.unseen(parts, [earth]) == [earth]  # 40 degrees down with a long lens: no sky in frame
    picture = np.asarray(blockout.render(parts, blockout.overhead_camera(parts, earth), [earth]))
    lit = np.all(picture == blockout.LIT, axis=-1)
    dark = np.all(picture == blockout.UNLIT, axis=-1)
    across = np.ptp(np.nonzero(lit | dark)[1]) + 1
    focal = blockout.TALL / 2 / np.tan(np.radians(blockout.OVERHEAD_LENS) / 2)
    assert across == pytest.approx(2 * focal * np.tan(np.radians(1.0)), abs=2)  # 2 degrees across, in pixels
    assert np.nonzero(lit)[1].mean() < np.nonzero(dark)[1].mean()  # half lit from the east: facing south, its left


def test_a_top_places_draw_carries_its_sites_blockout(tmp_path):
    store = Store.in_folder(tmp_path)
    found = concepts.structure_pictures(store, "campgrounds")
    assert found[0][1] == ("blockout", "campgrounds")
    assert concepts.sent_pictures(store, "campgrounds")[0] == found[0]
    assert concepts.sent_picture(store, found[0][1]).size == (blockout.WIDE, blockout.TALL)


def test_a_place_held_by_its_parents_walls_is_laid_out_once_its_outline_is_there(tmp_path, monkeypatch):
    store = Store.in_folder(tmp_path)
    square = {"w": 120.0, "d": 110.0, "holds": [{"place": "flat", "row": None, "x": 3.4, "y": 0.3, "w": 6.0,
                                                 "d": 5.0}]}
    monkeypatch.setattr(plans, "current", lambda _store, place: {"plan": square} if place == "square" else None)
    monkeypatch.setattr(plans, "inventory_of", lambda _store, place: {"rows": []})
    assert concepts.outlined(store, "flat")  # no inventory row holds it: the square's own walls do
    assert plans.holder_of(store, "flat")["row"] is None
    found = concepts.structure_pictures(store, "flat")  # and its draw is sent its blockout in the square's walls
    assert found[0][1] == ("blockout", "flat") and "from the square's plan" in found[0][0]
    assert concepts.sent_picture(store, found[0][1]).size == (blockout.WIDE, blockout.TALL)
    monkeypatch.setattr(plans, "current", lambda _store, place: {"plan": {**square, "holds": []}})
    assert not concepts.outlined(store, "flat")


DOMED = {"w": 8.0, "d": 8.0, "height": "walls 3 m", "people": [[4.0, 4.0]],
         "walls": [{"arc": {"centre": [4.0, 4.0], "radius": 4.0, "start": 0.0, "end": 360.0}, "thick": 0.3,
                    "tall": 3.0}],
         "roofs": [{"kind": "dome", "points": blockout.ellipse(0, 0, 8, 8), "eave": 3.0, "top": 5.0}],
         "items": [["TANK 1", 1.0, 1.0, 2.0, 2.0, None, "item"], ["FAR SKYLINE 1", -400.0, -40.0, 900.0, 50.0, None,
                                                                    "item"]],
         "shapes": {"TANK 1": {"shape": "circle", "tall": 2.0, "base": 0.0},
                    "FAR SKYLINE 1": {"shape": "rect", "tall": 90.0, "base": 0.0}}}


def test_a_plans_shapes_are_built_as_they_are_a_dome_round_walls_a_cylinder_and_nothing_from_beyond():
    parts = blockout.shell_parts(DOMED, on_ground=True)
    kinds = [kind for _, kind in parts]
    assert "floor" not in kinds and kinds.count("item") == 1  # on the ground: no slab; the skyline is beyond it
    walls = blockout.points_of(parts, ("wall",))
    radii = np.hypot(walls[:, 0] - 4.0, walls[:, 2] - 4.0)
    assert radii.min() > 3.6 and radii.max() < 4.05  # a round wall, its thickness inside its arc
    dome = blockout.points_of(parts, ("roof",))
    assert dome[:, 1].max() == pytest.approx(5.0) and len(dome) > 1000  # a dome, finely faceted
    tube = blockout.shell_parts({"w": 3.2, "d": 10.0, "shape": "tube", "radius": 1.6, "axis": 1.1}, on_ground=True)
    points = blockout.points_of(tube, ("wall",))
    assert np.ptp(points[:, 2]) == pytest.approx(10.0) and points[:, 1].max() == pytest.approx(2.7)  # along its length
    vault = np.asarray(blockout.vault(blockout.rectangle(0, 0, 10, 4), 2.0, 2.0)).reshape(-1, 3)
    assert vault[:, 1].max() == pytest.approx(4.0) and np.ptp(vault[:, 0]) == pytest.approx(10.0)  # along x


def test_a_site_stands_its_parts_plans_on_ground_curving_with_its_body_and_a_person_for_scale():
    site = {"place": "home", "size": [30.0, 30.0, 5.0], "radius_m": 1737400.0, "terrain": {"spots": []},
            "blocks": [{"name": "dome_room", "points": [[10.0, -4.0], [10.0, 4.0], [2.0, 4.0], [2.0, -4.0]],
                        "tall": 3.0, "base": 0.0, "roof": "flat", "rise": 0.0},
                       {"name": "shed", "points": blockout.rectangle(-10, -5, 4, 4), "tall": 2.0, "base": 0.0,
                        "roof": "flat", "rise": 0.0}]}
    plans = {"dome_room": DOMED, "home": {"people": [[0.0, 0.0]]}}
    parts = blockout.site_parts(site, lambda place: plans.get(place, {}))
    dome = blockout.points_of(parts, ("roof",))
    assert dome[:, 1].max() == pytest.approx(5.0)  # the part laid from its own plan, turned to its block
    assert dome[:, 0].min() == pytest.approx(2.0, abs=0.05) and dome[:, 0].max() == pytest.approx(10.0, abs=0.05)
    assert blockout.points_of(parts, ("person",))[:, 1].max() == pytest.approx(blockout.PERSON)
    ground = blockout.points_of(parts, ("ground",))
    far = np.hypot(ground[:, 0], ground[:, 2])
    fall = -far ** 2 / (2 * 1737400.0)
    assert ground[:, 1] == pytest.approx(fall, abs=1e-6)  # the Moon's true curve and nothing else, no spots given


def test_a_site_fills_the_frame_lit_by_its_sun_with_shadows():
    site = {"place": "home", "size": [20.0, 20.0, 8.0], "radius_m": None, "terrain": {"spots": []},
            "blocks": [{"name": "tower", "points": blockout.rectangle(-3, -3, 6, 6), "tall": 12.0, "base": 0.0,
                        "roof": "flat", "rise": 0.0}]}
    parts = blockout.site_parts(site)
    camera = blockout.fixed_camera(parts)
    xs, ys, _ = blockout.project(blockout.points_of([part for part in parts if part[1] != "ground"]), *camera)
    reach = max(np.abs(xs - blockout.WIDE / 2).max() / blockout.WIDE,
                np.abs(ys - blockout.TALL / 2).max() / blockout.TALL)
    assert reach * 2 == pytest.approx(blockout.FILL, abs=0.01)  # the place reaches FILL of the frame, no further
    way = blockout.sun_way((270.0, 30.0))  # the Sun low in the west: the tower's shadow falls east
    found = blockout.shadow_map(parts, way)
    east, west = np.array([[12.0, 0.0, 0.0]]), np.array([[-12.0, 0.0, 0.0]])
    up = np.array([[0.0, 1.0, 0.0]])
    assert blockout.sunlit(found, east, up)[0] == 0.0 and blockout.sunlit(found, west, up)[0] == 1.0
    picture = np.asarray(blockout.render(parts, camera, light=(270.0, 30.0)))
    assert picture[..., 0].min() < 90 and picture[..., 0].max() > 160  # light grey solids, a dark shadow


def test_a_render_is_keyed_by_what_it_is_built_from_and_the_code_that_draws_it(monkeypatch):
    parts, framed = blockout.inside_parts("room_a", HOLDER, ROOM_A, blockout.corner_way())
    key = blockout.scene_key((parts, framed, [], None, []))
    assert blockout.scene_key((parts, framed, [], (180.0, 40.0), [])) != key  # another sun
    monkeypatch.setattr(blockout, "VERSION", "older code")
    assert blockout.scene_key((parts, framed, [], None, [])) != key  # another code: rendered again, never served stale
