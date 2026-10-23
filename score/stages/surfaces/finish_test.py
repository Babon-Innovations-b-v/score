"""The finish route's shared steps on a take's faces and its finish check (finish_parts.py) and its Google ask
(finish_ask.py), with no spend: the walk names unvoted faces from the nearest voted ones along the surface; loose bits
join the nearest larger island in space; cleaning never removes a finish whole; agreement counts against the views;
a finish takes the nearest surface of its family by colour and keeps the close-up's lightness order; an ask is made
once; a finish list reply is parsed to library names.

Run: .venv/bin/python score/stages/surfaces/finish_test.py
"""
import json
import pathlib
import sys

import numpy as np
import trimesh
from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score.stages.surfaces import finish_ask, finish_parts  # noqa: E402


def test_unvoted_faces_take_the_nearest_voted_label_along_the_surface():
    mesh = trimesh.creation.icosphere(subdivisions=3)
    seen = np.full(len(mesh.faces), -1)
    middles = mesh.triangles_center
    seen[(middles[:, 2] > 0.5) & (middles[:, 0] > 0)] = 0
    seen[(middles[:, 2] > 0.5) & (middles[:, 0] <= 0)] = 1
    walked = finish_parts.walked(mesh, seen)
    assert (walked >= 0).all()
    back = middles[:, 2] < -0.5
    assert (walked[back & (middles[:, 0] > 0.3)] == 0).mean() > 0.9
    assert (walked[back & (middles[:, 0] < -0.3)] == 1).mean() > 0.9


def test_a_loose_bit_joins_the_nearest_larger_island_of_its_own_finish():
    big = trimesh.creation.box(extents=(1, 1, 1))
    loose = trimesh.creation.box(extents=(0.02, 0.02, 0.02))
    loose.apply_translation((0.53, 0, 0))
    far = trimesh.creation.box(extents=(1, 1, 1))
    far.apply_translation((3, 0, 0))
    mesh = trimesh.util.concatenate([big, loose, far])
    label = np.r_[np.zeros(len(big.faces)), np.ones(len(loose.faces)), np.ones(len(far.faces))].astype(int)
    part_of, merged = finish_parts.merged_islands(mesh, label)
    bit = slice(len(big.faces), len(big.faces) + len(loose.faces))
    assert len(np.unique(part_of)) == 2 and (part_of[bit] == part_of[-1]).all() and (merged[bit] == 1).all()


def test_a_finish_of_crumbs_only_keeps_them_as_one_part_however_small():
    host = trimesh.creation.box(extents=(1, 1, 1))
    bands = []
    for number in range(4):  # thin stripes beside the box, each a crumb, together over ISLAND_LEAST
        band = trimesh.creation.box(extents=(0.04, 0.04, 0.04))
        band.apply_translation((0.6, -0.3 + 0.2 * number, 0))
        bands.append(band)
    mesh = trimesh.util.concatenate([host, *bands])
    band_share = sum(band.area for band in bands) / mesh.area
    assert all(band.area / mesh.area < finish_parts.ISLAND_LEAST for band in bands)
    assert band_share >= finish_parts.ISLAND_LEAST
    label = np.r_[np.zeros(len(host.faces)), np.ones(len(mesh.faces) - len(host.faces))].astype(int)
    part_of, merged = finish_parts.merged_islands(mesh, label)
    striped = slice(len(host.faces), None)
    assert len(np.unique(part_of)) == 2 and (merged[striped] == 1).all() and len(np.unique(part_of[striped])) == 1
    one = trimesh.util.concatenate([host, bands[0]])  # one crumb alone keeps its finish as a part of its own
    label = np.r_[np.zeros(len(host.faces)), np.ones(len(bands[0].faces))].astype(int)
    part_of, merged = finish_parts.merged_islands(one, label)
    assert len(np.unique(part_of)) == 2 and (merged[len(host.faces):] == 1).all()


def test_cleaning_never_removes_a_finish_whole():
    mesh = trimesh.creation.icosphere(subdivisions=4)
    middles = mesh.triangles_center
    label = np.zeros(len(mesh.faces), dtype=int)
    dots = np.flatnonzero((middles[:, 1] > 0.9) | (middles[:, 0] > 0.97))[::3]  # scattered single faces of finish 1
    label[dots] = 1
    without = finish_parts.cleaned(mesh, label, 2)
    assert (without[dots] == 1).all() and (without[label == 0] == 0).mean() > 0.99
    kept = finish_parts.kept_finishes(np.array([0, 1, 2, 2]), np.array([0, 0, 0, 2]))
    assert kept.tolist() == [0, 1, 0, 2]  # a finish left with any face stays as the cleaning left it


def test_agreement_counts_against_the_maps():
    mesh = trimesh.creation.icosphere(subdivisions=2)
    top = mesh.triangles_center[:, 1] > 0
    face_label = np.zeros(len(mesh.faces), dtype=int)
    front = np.where(top, 1, 0)  # the map says finish 1 on top, the paint says 0 everywhere
    agreement = finish_parts.agreement(mesh, face_label, {"front": front})
    assert 0.4 < agreement["front"] < 0.6, agreement


def test_a_finish_out_of_order_is_found_and_a_see_through_finish_is_known():
    greys = {"anodized_natural": {"colour": [0.2843] * 3}, "dust_coated_paint": {"colour": [0.4075] * 3}}  # L* 60, 70
    lightness = finish_parts.opaque_lightness(greys)
    white = {"surface": "anodized_natural", "measured_lab": [80.6, 1.0, 2.0]}  # the campgrounds' power unit
    dusty = {"surface": "dust_coated_paint", "measured_lab": [69.7, 0, 0]}
    assert finish_parts.out_of_order(white, dusty, greys, lightness)
    assert not finish_parts.out_of_order(dusty, white, greys, lightness)
    assert not finish_parts.out_of_order(white, dict(dusty, measured_lab=None), greys, lightness)
    # a finish route's finish paints in its own colour (its settings' token) while it keeps its listed surface:
    # astronaut-made (2026-10-23): its white shell in suit-white, its variant's own token base-grey
    shell = dict(white, colour=[0.9131] * 3, listed_surface="anodized_natural")
    fabric = dict(dusty, colour=[0.4075] * 3, listed_surface="dust_coated_paint")
    assert not finish_parts.out_of_order(shell, fabric, greys, lightness)
    assert finish_parts.out_of_order(dict(shell, listed_surface="other"), fabric, greys, lightness)  # moved: library's
    every = {"red_plastic": {"family": "plastic"}, "cast_steel": {"family": "steel"}, "glass": {"family": "glass"}}
    listed = [{"finish": "Red transparent plastic", "parts": "lamp dome", "surface": "red_plastic"},
              {"finish": "Polished reflective metal", "parts": "internal reflector", "surface": "cast_steel"},
              {"finish": "Grey painted steel", "parts": "housing", "surface": "cast_steel"}]
    assert [finish_parts.see_through(finish, every) for finish in listed] == [True, False, False]


def library_of(**colours):
    """{surface: spec} with each surface's family and linear colour, from name=(family, colour)."""
    return {name: {"family": family, "colour": colour} for name, (family, colour) in colours.items()}


def test_an_ask_is_made_once_a_timeout_reaches_the_row_and_only_a_refusal_is_asked_again():
    import io
    import urllib.error
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import google_spend
    asked = []

    def answering(*faults):
        def answer(model, body, key, timeout, caller, cache):
            asked.append(body.get("serviceTier"))
            if len(asked) <= len(faults):
                raise faults[len(asked) - 1]
            return "answered"
        return answer

    def refusal(code):
        return urllib.error.HTTPError("url", code, "refused", {}, io.BytesIO())
    saved = google_spend.generate, finish_ask.REFUSED_WAIT
    finish_ask.REFUSED_WAIT = 0
    try:
        google_spend.generate = answering(TimeoutError("The read operation timed out"))
        try:
            finish_ask.generated(finish_ask.LIST_MODEL, {"serviceTier": "flex"}, "key", 1, "test", False)
        except TimeoutError:
            pass
        else:
            raise AssertionError("a timeout reaches the row")
        assert asked == ["flex"], asked
        asked.clear()
        google_spend.generate = answering(refusal(429), refusal(503))
        assert finish_ask.generated(finish_ask.LIST_MODEL, {}, "key", 1, "test", False) == "answered"
        assert len(asked) == 3, asked
        asked.clear()
        google_spend.generate = answering(refusal(500), refusal(504))  # audit, 2026-10-22: these stopped the row
        assert finish_ask.generated(finish_ask.LIST_MODEL, {}, "key", 1, "test", False) == "answered"
        assert len(asked) == 3, asked
        asked.clear()
        google_spend.generate = answering(refusal(400))
        try:
            finish_ask.generated(finish_ask.LIST_MODEL, {}, "key", 1, "test", False)
        except urllib.error.HTTPError:
            pass
        assert len(asked) == 1, asked
        asked.clear()
        rooms = []
        google_spend.generate = answering(refusal(429), refusal(503), refusal(429))
        try:
            finish_ask.generated(finish_ask.LIST_MODEL, {}, "key", 1, "test", False, room=lambda: rooms.append(1))
        except finish_ask.NoAnswer:
            pass
        else:
            raise AssertionError("refused every time is no answer")
        assert len(asked) == finish_ask.REFUSED_ASKS == len(rooms), (asked, rooms)
        asked.clear()
        google_spend.generate = answering(urllib.error.URLError(ConnectionRefusedError(111, "refused")))
        try:
            finish_ask.generated(finish_ask.LIST_MODEL, {}, "key", 1, "test", False)
        except finish_ask.NoAnswer:
            pass
        else:
            raise AssertionError("a lost connection is no answer")
        assert len(asked) == 1, asked
    finally:
        google_spend.generate, finish_ask.REFUSED_WAIT = saved


def two_colour_close_up():
    picture = np.zeros((200, 200, 4), dtype=np.uint8)
    picture[50:100, 60:140] = (200, 200, 195, 255)  # a light grey body
    picture[100:150, 60:140] = (40, 50, 90, 255)  # a dark blue window
    return Image.fromarray(picture)


def test_a_finish_takes_the_nearest_surface_of_its_family_by_colour_or_is_flagged():
    navy, grey, black = [0.03, 0.06, 0.10], [0.35, 0.35, 0.35], [0.01, 0.01, 0.01]
    library = {"vinyl_seat": {"family": "plastic", "colour": navy},
               "grey_plastic": {"family": "plastic", "colour": grey},
               "dark_panel": {"family": "steel", "colour": black}}
    light_grey = finish_parts.library_lab(library["grey_plastic"]) + np.array([3.0, 0, 0])
    found = finish_parts.checked_finishes(
        {"kind": "lab_chair", "object": "desk chair"},
        [{"finish": "grey vinyl", "parts": "seat", "surface": "vinyl_seat", "fits": True},
         {"finish": "grey steel", "parts": "body", "surface": "dark_panel", "fits": True}],
        [light_grey, light_grey], library)
    assert found[0]["surface"] == "grey_plastic" and found[0]["by"] == "nearest of its family by colour"
    assert found[1]["surface"] == "dark_panel" and found[1]["by"] == "off its colour" and not found[1]["fits"]
    assert found[1]["new_surface"]["lab"] == [round(float(value), 1) for value in light_grey]
    # a finish in its own token's colour (the finish route's settings) is held to that colour, not its surface's
    tinted = finish_parts.checked_finishes(
        {"kind": "lab_chair", "object": "desk chair"},
        [{"finish": "grey steel", "parts": "body", "surface": "dark_panel", "fits": True, "colour": grey}],
        [light_grey], library)
    assert tinted[0]["surface"] == "dark_panel" and tinted[0]["by"] == "the list", tinted[0]


def test_a_finish_keeps_the_close_ups_lightness_order_and_glass_keeps_its_own_colour():
    """The water tank: its panel 13 L* lighter than its steel in the close-up, painted_panel under bare_steel in the
    library; cream_paint keeps the order. Glass off the lit colour keeps its surface (owner, #8)."""
    every = {"painted_panel": {"family": "painted", "colour": [0.30, 0.31, 0.33]},
             "cream_paint": {"family": "painted", "colour": [0.55, 0.53, 0.46]},
             "bare_steel": {"family": "steel", "colour": [0.35, 0.36, 0.38]},
             "glass": {"family": "glass", "colour": [0.6, 0.65, 0.7]}}
    panel_lab = [round(float(value), 1) for value in finish_parts.library_lab(every["cream_paint"]) - [4, 0, 0]]
    steel_lab = [round(float(value), 1) for value in finish_parts.library_lab(every["bare_steel"]) - [8, 0, 0]]
    found = finish_parts.in_close_up_order({"object": "water tank"}, [
        {"finish": "off-white paint", "surface": "painted_panel", "measured_lab": panel_lab, "by": "the list"},
        {"finish": "steel legs", "surface": "bare_steel", "measured_lab": steel_lab, "by": "the list"}], every)
    assert found[0]["surface"] == "cream_paint" and found[0]["by"] == "nearest of its family in order", found[0]
    alone = {name: spec for name, spec in every.items() if name != "cream_paint"}
    flagged = finish_parts.in_close_up_order({"object": "water tank"}, [
        {"finish": "off-white paint", "surface": "painted_panel", "measured_lab": panel_lab, "by": "the list"},
        {"finish": "steel legs", "surface": "bare_steel", "measured_lab": steel_lab, "by": "the list"}], alone)
    assert flagged[0]["by"] == "off its colour" and "lighter than bare_steel" in flagged[0]["new_surface"]["why"]
    kept = [{"finish": "steel legs", "surface": "bare_steel", "measured_lab": steel_lab, "by": "the list"}]
    assert finish_parts.in_close_up_order({"object": "x"}, [dict(kept[0])], every) == kept  # nothing to order
    lit = finish_parts.checked_finishes({"kind": "lamp", "object": "lamp"},
                                        [{"finish": "red lit lens", "parts": "lens", "surface": "glass"}],
                                        [np.array([45.0, 60.0, 40.0])], every)
    assert lit[0]["surface"] == "glass" and lit[0]["by"] == "its own colour" and "cover" not in lit[0], lit[0]


def test_a_finish_a_little_out_of_order_keeps_it_by_a_nearer_surface_of_either():
    """The hangar's parts shelving: its grey plastic bins 27.7 L* over its steel in the close-up, plastic_grey 1.5
    under galvanized_steel in the library (the steel baked 3 over its colour, the bins 4.5 under it). The steel, seen
    at L* 42, takes cast_steel, nearer its close-up colour; with none nearer, the order stays as it was."""
    every = {"galvanized_steel": {"family": "steel", "colour": [0.328, 0.361, 0.397]},
             "plastic_grey": {"family": "plastic", "colour": [0.386, 0.332, 0.258]},
             "cast_steel": {"family": "steel", "colour": [0.070, 0.084, 0.102]}}

    def shelving():
        return [{"finish": "Grey steel", "surface": "galvanized_steel", "measured_lab": [41.9, 0.6, -0.6],
                 "by": "the list"},
                {"finish": "Light grey plastic", "surface": "plastic_grey", "measured_lab": [69.6, 0.2, 0.9],
                 "by": "named again (its material)"}]
    found = finish_parts.in_close_up_order({"object": "parts shelving"}, shelving(), every)
    assert found[0]["surface"] == "cast_steel" and found[0]["by"] == "nearest of its family in order", found[0]
    assert found[1]["surface"] == "plastic_grey" and found[1]["by"] == "named again (its material)", found[1]
    bright = [dict(finish) for finish in shelving()]
    bright[0]["measured_lab"] = [66.0, -1.0, -4.0]  # the steel seen as light as galvanized_steel: none nearer
    bright[1]["measured_lab"] = [80.0, 0.0, 0.0]
    assert finish_parts.in_close_up_order({"object": "parts shelving"}, [dict(finish) for finish in bright],
                                          every) == bright


def test_a_coloured_see_through_finish_keeps_its_surface_against_its_highlights():
    """The beacon's red transparent dome measured pale pink on its brighter half: it keeps red_plastic, not the
    nearer plastic_grey; an opaque grey plastic that far off still moves."""
    library = {"red_plastic": {"family": "plastic", "colour": [0.45, 0.02, 0.01]},
               "plastic_grey": {"family": "plastic", "colour": [0.33, 0.31, 0.27]}}
    pale = np.array([70.8, 21.2, 11.5])
    found = finish_parts.checked_finishes(
        {"kind": "beacon", "object": "beacon"},
        [{"finish": "Red transparent plastic", "parts": "lamp dome", "surface": "red_plastic"},
         {"finish": "Red plastic", "parts": "knob", "surface": "red_plastic"}], [pale, pale], library)
    assert found[0]["surface"] == "red_plastic" and found[0]["by"] == "its own colour" and found[0]["cover"], found[0]
    assert found[1]["surface"] == "plastic_grey" and found[1]["by"] == "nearest of its family by colour", found[1]


def test_a_finish_list_reply_is_parsed_to_library_names():
    surfaces = {"mli_gold": {}, "bare_steel": {}}
    reply = json.dumps({"finishes": [{"parts": "foil", "finish": "gold foil", "surface": "M1", "fits": True},
                                     {"parts": "legs", "finish": "steel", "surface": "M2", "fits": True}]})
    assert [entry["surface"] for entry in finish_ask.parsed_list(reply, surfaces)] == ["mli_gold", "bare_steel"]


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
