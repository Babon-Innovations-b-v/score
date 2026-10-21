"""The blockout (score/review/blockout.py): built from a fixture plan, rendered free, and sent first with a draw."""
import numpy as np
import pytest

from score.review import blockout, concepts, plans
from score.store import Store

HOLDER = {"w": 20.0, "d": 12.0, "height": "walls 6 m to a flat roof",
          "doors": [["S", 10.0, 2.0, "BIG DOOR (2 x 2.6 m)"]],
          "holds": [{"place": "room_a", "row": "hull", "x": 2.0, "y": 2.0, "w": 6.0, "d": 4.0},
                    {"place": "room_b", "row": None, "x": 9.0, "y": 2.0, "w": 5.0, "d": 4.0}]}
ROOM_A = {"w": 6.0, "d": 4.0, "height": "ceiling 2.5 m", "doors": [["E", 2.0, 1.0, "DOOR"]]}


def own_plans(place):
    return {"room_a": ROOM_A}.get(place, {})


def test_an_inside_places_blockout_holds_its_own_shell_its_siblings_and_its_holder():
    parts, framed = blockout.inside_parts("room_a", HOLDER, ROOM_A, own_plans, blockout.corner_way())
    kinds = {kind for _, kind in parts}
    assert {"holder", "sibling", "wall", "floor"} <= kinds and "roof" not in kinds  # a cutaway: no roofs
    assert framed == [2.0, 2.0, 6.0, 4.0, 2.5]
    walls = np.concatenate([np.asarray(triangles).reshape(-1, 3) for triangles, kind in parts if kind == "wall"])
    assert walls[:, 1].max() == pytest.approx(2.5)  # its own ceiling, in metres
    assert walls[:, 0].min() >= 2.0 - 1e-6 and walls[:, 0].max() <= 8.0 + 1e-6  # inside its box on the holder
    with pytest.raises(blockout.Missing):
        blockout.inside_parts("room_c", HOLDER, {}, own_plans, blockout.corner_way())


def test_a_door_is_a_hole_in_its_wall():
    whole = blockout.shell_parts({"w": 6.0, "d": 4.0, "height": "walls 3 m"})
    holed = blockout.shell_parts(ROOM_A)
    count = sum(len(triangles) for triangles, kind in holed if kind == "wall")
    assert count > sum(len(triangles) for triangles, kind in whole if kind == "wall")  # the east wall cut in three
    door = blockout.data_openings({"doors": [[90, 2.2, "HATCH 90 (2.2 x 2.6 m)"]]}, 9.0, 9.0)
    assert door == [{"at": [9.0, 4.5], "wide": 2.2, "head": 2.6}]  # a bearing meets the box's east wall


def test_a_blockout_renders_grey_from_the_fixed_view():
    parts, framed = blockout.inside_parts("room_a", HOLDER, ROOM_A, own_plans, blockout.corner_way())
    picture = blockout.render(parts, blockout.fixed_camera(parts, framed))
    assert picture.size == (blockout.WIDE, blockout.TALL)
    pixels = np.asarray(picture)
    assert (pixels[..., 0] == pixels[..., 1]).all() and (pixels[..., 1] == pixels[..., 2]).all()  # neutral grey
    assert (pixels != blockout.BACKGROUND).any(axis=-1).mean() > 0.3  # the model fills the frame


def test_a_sites_world_is_drawn_at_its_true_size_where_it_stands():
    site = {"size": [20.0, 20.0, 5.0], "footprint": None, "terrain": {"spots": [[0, 0, 0], [30, 0, -2], [0, 30, -2]]},
            "blocks": [{"points": blockout.rectangle(-5, -5, 10, 10), "tall": 5.0, "base": 0.0, "roof": "dome",
                        "rise": 2.0}]}
    earth = {"world": "earth", "name": "Earth", "azimuth": 180.0, "altitude": 30.0, "across": 2.0, "lit": 0.5,
             "lit_from": [1.0, 0.0, 0.0]}
    parts = blockout.site_parts(site)
    assert blockout.unseen(parts, [earth]) == [earth]  # 40 degrees down with a long lens: no sky in frame
    picture = np.asarray(blockout.render(parts, blockout.sky_camera(parts, earth), [earth]))
    lit = np.all(picture == blockout.LIT, axis=-1)
    dark = np.all(picture == blockout.UNLIT, axis=-1)
    across = np.ptp(np.nonzero(lit | dark)[1]) + 1
    focal = blockout.TALL / 2 / np.tan(np.radians(blockout.SKY_LENS) / 2)
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
