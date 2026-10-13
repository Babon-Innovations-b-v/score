"""The finish-map method's own checks, with no spend: a map drawn larger and off centre is laid back on its picture
and passes, one missing a listed finish or mostly off its label colours fails, and one left partly photographic is
filled from its labelled neighbours only when enough of it is labelled; a view's map is asked with the close-up and its
map as the reference; the walk names unvoted faces from the nearest voted ones along the surface; a SegviGen part
takes its voted faces' finish only when they are pure; loose bits join the nearest larger island in space; the
measures count agreement and mixing parts; a finish list reply is parsed to library names.

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

from score.stages.surfaces import finish_ask, finish_maps, finish_parts, turntable_row  # noqa: E402
from PIL.PngImagePlugin import PngInfo  # noqa: E402


def close_up_alpha():
    alpha = np.zeros((200, 200), dtype=bool)
    alpha[50:150, 60:140] = True
    return alpha


def drawn(top_colour, bottom_colour):
    """A map drawn 1.5 times larger, shifted, on white: the box's top half one label, its bottom half another."""
    pixels = np.full((400, 400, 3), 255, dtype=np.uint8)
    pixels[100:175, 130:250] = top_colour
    pixels[175:250, 130:250] = bottom_colour
    return Image.fromarray(pixels)


def test_a_larger_shifted_map_is_laid_back_and_passes():
    alpha = close_up_alpha()
    measures, per_pixel = finish_maps.check(drawn(finish_ask.LABELS[0], finish_ask.LABELS[1]), alpha, 2,
                                            finish_ask.LABELS)
    assert measures["passes"] and measures["iou"] > 0.95, measures
    assert per_pixel[60, 100] == 0 and per_pixel[140, 100] == 1 and per_pixel[10, 10] == -1


def test_a_map_missing_a_finish_or_off_its_colours_fails():
    alpha = close_up_alpha()
    missing, _ = finish_maps.check(drawn(finish_ask.LABELS[0], finish_ask.LABELS[0]), alpha, 2, finish_ask.LABELS)
    assert not missing["passes"] and missing["labels_used"] == 1, missing
    shaded, _ = finish_maps.check(drawn((90, 90, 90), finish_ask.LABELS[1]), alpha, 2, finish_ask.LABELS)
    assert not shaded["passes"] and shaded["near_label"] < 0.6, shaded
    _, view_labels = finish_maps.check(drawn(finish_ask.LABELS[0], finish_ask.LABELS[0]), alpha, 2,
                                       finish_ask.LABELS, every_label=False)
    seen, _ = finish_maps.check(drawn(finish_ask.LABELS[0], finish_ask.LABELS[0]), alpha, 2, finish_ask.LABELS,
                                every_label=False)
    assert seen["passes"] and (view_labels[alpha] == 0).all()  # a view need not show every finish


def test_a_partly_photographic_map_is_filled_only_when_most_of_it_is_labelled():
    alpha = close_up_alpha()
    door = drawn(finish_ask.LABELS[0], finish_ask.LABELS[1])
    pixels = np.asarray(door).copy()
    pixels[110:150, 150:200] = (120, 120, 120)  # a photographic door: 22% of the object near no label
    measures, per_pixel = finish_maps.check(Image.fromarray(pixels), alpha, 2, finish_ask.LABELS)
    assert not measures["passes"] and finish_maps.fillable(measures), measures
    index, filled, was_filled = finish_maps.settled([(measures, per_pixel)], alpha)
    assert index == 0 and was_filled and (filled[alpha] >= 0).all() and (filled[~alpha] == -1).all()
    pixels[100:250, 130:250] = (120, 120, 120)
    pixels[100:130, 130:250] = finish_ask.LABELS[0]
    pixels[220:250, 130:250] = finish_ask.LABELS[1]
    mostly, labels_left = finish_maps.check(Image.fromarray(pixels), alpha, 2, finish_ask.LABELS)
    assert finish_maps.settled([(mostly, labels_left)], alpha) is None, mostly


def test_no_settled_draw_falls_back_to_the_close_ups_colours_split_and_the_draws_names():
    """old_station's lab module, 2026-10-12: every draw left half the photo unpainted. The close-up's colours split
    it; the few labelled pixels of the draws name each region."""
    alpha = close_up_alpha()
    picture = np.full((200, 200, 4), 0, dtype=np.uint8)
    picture[50:100, 60:140] = (200, 200, 195, 255)  # a light grey body
    picture[100:150, 60:140] = (40, 50, 90, 255)  # a dark blue window
    pixels = np.asarray(drawn((120, 120, 120), (120, 120, 120))).copy()
    pixels[100:115, 130:250] = finish_ask.LABELS[0]
    pixels[235:250, 130:250] = finish_ask.LABELS[1]
    measures, per_pixel = finish_maps.check(Image.fromarray(pixels), alpha, 2, finish_ask.LABELS)
    assert finish_maps.settled([(measures, per_pixel)], alpha) is None, measures
    split = finish_maps.colour_split(Image.fromarray(picture), alpha, [(measures, per_pixel)])
    assert (split[50:100, 60:140] == 0).all() and (split[100:150, 60:140] == 1).all() and (split[~alpha] == -1).all()

def test_a_one_finish_take_takes_its_mask_and_a_two_finish_take_still_needs_a_settled_draw():
    import tempfile
    from score.stages.surfaces import finish_rows
    import finish_ask as asks  # finish_rows imports its siblings by name, from its own folder
    picture = np.zeros((200, 200, 4), dtype=np.uint8)
    picture[close_up_alpha()] = (90, 90, 90, 255)
    saved = finish_rows.close_up, asks.draw_map
    finish_rows.close_up = lambda inputs, take: Image.fromarray(picture)
    try:
        def never(*arguments, **options):
            raise AssertionError("a one-finish take is never drawn")
        asks.draw_map = never
        one = pathlib.Path(tempfile.mkdtemp())
        finish_rows.take_maps({}, "box", [{"finish": "grey fabric", "parts": "all"}], one)
        record = json.loads((one / "map.json").read_text())
        front = np.load(one / "front.npy")
        assert record["passes"] and record["views"] == {}, record
        assert (front[close_up_alpha()] == 0).all() and (front[~close_up_alpha()] == -1).all()
        tinted = np.asarray(drawn(finish_ask.LABELS[0], (120, 120, 120))).copy()
        tinted[175:250, 130:250] = (120, 120, 120)  # half the object left photographic, as lab_module's draws
        asks.draw_map = lambda *arguments, **options: Image.fromarray(tinted)
        two = pathlib.Path(tempfile.mkdtemp())
        finish_rows.take_maps({}, "module", [{"finish": "paint", "parts": "body"},
                                             {"finish": "glass", "parts": "porthole"}], two)
        assert not json.loads((two / "map.json").read_text())["passes"] and not (two / "front.npy").exists()
    finally:
        finish_rows.close_up, asks.draw_map = saved


def test_a_view_map_is_asked_with_the_close_up_and_its_map():
    picture = Image.new("RGBA", (64, 64), (100, 100, 100, 255))
    finishes = [{"finish": "gold foil", "parts": "the hull"}]
    body = finish_ask.view_body(picture, picture, picture, finishes, 1)
    parts = body["contents"][0]["parts"]
    assert len(parts) == 4 and "pure red" in parts[0]["text"] and body["generationConfig"]["seed"] == 1
    strict = finish_ask.map_body(picture, finishes, 3, strict=True)["contents"][0]["parts"][0]["text"]
    assert finish_ask.STRICT in strict
    assert finish_ask.STRICT not in finish_ask.map_body(picture, finishes, 1)["contents"][0]["parts"][0]["text"]


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


def test_a_segvigen_part_takes_its_voted_faces_finish_only_when_pure():
    mesh = trimesh.creation.icosphere(subdivisions=2)
    middles = mesh.triangles_center
    part_of = (middles[:, 1] > 0).astype(int)
    votes = np.zeros((len(mesh.faces), 2))
    votes[middles[:, 1] > 0.5, 1] = 1.0  # the top part: voted finish 1 only
    votes[(middles[:, 1] < -0.3) & (middles[:, 0] > 0), 0] = 1.0  # the bottom part: half 0, half 1
    votes[(middles[:, 1] < -0.3) & (middles[:, 0] <= 0), 1] = 1.0
    named = finish_parts.segvigen_labels(mesh, part_of, votes)
    assert (named[part_of == 1] == 1).all() and (named[part_of == 0] == -1).all()


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


def test_a_finish_of_crumbs_only_keeps_them_as_one_part_when_they_add_up():
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
    one = trimesh.util.concatenate([host, bands[0]])  # one crumb alone still joins its neighbour with its finish
    label = np.r_[np.zeros(len(host.faces)), np.ones(len(bands[0].faces))].astype(int)
    part_of, merged = finish_parts.merged_islands(one, label)
    assert len(np.unique(part_of)) == 1 and (merged == 0).all()


def test_agreement_and_mixing_count_against_the_maps():
    mesh = trimesh.creation.icosphere(subdivisions=2)
    top = mesh.triangles_center[:, 1] > 0
    face_label = np.zeros(len(mesh.faces), dtype=int)
    front = np.where(top, 1, 0)  # the map says finish 1 on top, the paint says 0 everywhere
    agreement = finish_parts.agreement(mesh, face_label, {"front": front})
    assert 0.4 < agreement["front"] < 0.6, agreement
    mixing = finish_parts.mixing_parts(mesh, np.zeros(len(mesh.faces), dtype=int), face_label, {"front": front}, 2)
    assert mixing and mixing[0][0] == 0, mixing


def test_a_strongly_coloured_finish_is_asked_whether_it_is_lamp_light_and_no_other_question_moves():
    picture = Image.new("RGBA", (8, 8), (200, 30, 30, 255))
    finish = {"finish": "Polished reflective metal", "parts": "the lamp housing"}
    surfaces = {"cast_steel": {"family": "steel"}, "led_red": {"family": "light"}}
    plain = finish_ask.name_body(picture, picture, "a red warning lamp", 0, finish, surfaces)
    asked = finish_ask.name_body(picture, picture, "a red warning lamp", 0, finish, surfaces, glow=True)
    text = plain["contents"][0]["parts"][2]["text"]
    assert text.endswith("then by its colour in the first picture."), text  # word for word: its cache stands
    assert asked["contents"][0]["parts"][2]["text"] == text + finish_ask.GLOW_QUESTION


def test_a_naming_that_timed_out_is_asked_again_with_low_thinking():
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import google_spend
    asked = []

    def answer(model, body, key, timeout, caller, cache):
        asked.append(body["generationConfig"].get("thinkingConfig"))
        if len(asked) == 1:
            raise TimeoutError("The read operation timed out")
        return "answered"

    saved = google_spend.generate
    google_spend.generate = answer
    try:
        found = finish_ask.generated(finish_ask.LIST_MODEL, {"generationConfig": {"temperature": 0}}, "key", 1,
                                     "test", False)
    finally:
        google_spend.generate = saved
    assert found == "answered" and asked == [None, {"thinkingLevel": "low"}], asked


def test_a_dark_finish_is_measured_on_its_darker_pixels_and_a_grey_one_named_black_still_fails():
    """old_station's black rubber, 2026-10-12: the close-up's light lifts its brighter half to L* 42; its lightness
    here spread as the comms mast's was (median L* 33)."""
    black = {"colour": [0.01, 0.01, 0.01], "family": "rubber"}
    lightness = np.concatenate([np.linspace(10, 30, 50), np.linspace(35, 50, 50)])
    lit_black = np.stack([lightness, np.zeros(100), np.zeros(100)], axis=1)
    near = np.linalg.norm(finish_parts.library_lab(black) - finish_parts.finish_colour(lit_black, black))
    assert near < finish_parts.COLOUR_DELTA_E, near
    lifted = np.linalg.norm(finish_parts.library_lab(black) - finish_parts.finish_colour(lit_black, None))
    assert lifted > finish_parts.COLOUR_DELTA_E, lifted  # the brighter half alone failed it
    grey = np.stack([np.linspace(50, 62, 100), np.zeros(100), np.zeros(100)], axis=1)
    far = np.linalg.norm(finish_parts.library_lab(black) - finish_parts.finish_colour(grey, black))
    assert far > finish_parts.COLOUR_DELTA_E, far
    assert finish_parts.finish_colour(np.zeros((0, 3)), black) is None


def test_a_finish_takes_the_nearest_surface_of_its_family_by_colour_or_is_flagged():
    import labels
    navy, grey, black = [0.03, 0.06, 0.10], [0.35, 0.35, 0.35], [0.01, 0.01, 0.01]
    library = {"vinyl_seat": {"family": "plastic", "colour": navy},
               "grey_plastic": {"family": "plastic", "colour": grey},
               "dark_panel": {"family": "steel", "colour": black}}
    saved = labels.allowed_materials
    labels.allowed_materials = lambda place, kind, without: library
    try:
        light_grey = finish_parts.library_lab(library["grey_plastic"]) + np.array([3.0, 0, 0])
        found = finish_parts.checked_finishes(
            {"library_places": ["lab"], "kind": "lab_chair", "object": "desk chair"},
            [{"finish": "grey vinyl", "parts": "seat", "surface": "vinyl_seat", "fits": True},
             {"finish": "grey steel", "parts": "body", "surface": "dark_panel", "fits": True}],
            [light_grey, light_grey])
    finally:
        labels.allowed_materials = saved
    assert found[0]["surface"] == "grey_plastic" and found[0]["by"] == "nearest of its family by colour"
    assert found[1]["surface"] == "dark_panel" and found[1]["by"] == "off its colour" and not found[1]["fits"]
    assert found[1]["new_surface"]["lab"] == [round(float(value), 1) for value in light_grey]


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
    import labels
    saved = labels.allowed_materials
    labels.allowed_materials = lambda place, kind, without: every
    try:
        lit = finish_parts.checked_finishes({"library_places": ["lab"], "kind": "lamp", "object": "lamp"},
                                            [{"finish": "red lit lens", "parts": "lens", "surface": "glass"}],
                                            [np.array([45.0, 60.0, 40.0])])
    finally:
        labels.allowed_materials = saved
    assert lit[0]["surface"] == "glass" and lit[0]["by"] == "its own colour" and "cover" not in lit[0], lit[0]


def test_a_finish_out_of_order_is_named_again_and_a_part_behind_a_see_through_cover_is_left_out():
    lightness = {"anodized_natural": 60.0, "dust_coated_paint": 70.0}
    white = {"surface": "anodized_natural", "measured_lab": [80.6, 1.0, 2.0]}  # the campgrounds' power unit
    dusty = {"surface": "dust_coated_paint", "measured_lab": [69.7, 0, 0]}
    assert finish_parts.out_of_order(white, dusty, lightness) and not finish_parts.out_of_order(dusty, white, lightness)
    assert not finish_parts.out_of_order(white, dict(dusty, measured_lab=None), lightness)
    every = {"red_plastic": {"family": "plastic"}, "cast_steel": {"family": "steel"}, "glass": {"family": "glass"}}
    listed = [{"finish": "Red transparent plastic", "parts": "lamp dome", "surface": "red_plastic"},
              {"finish": "Polished reflective metal", "parts": "internal reflector", "surface": "cast_steel"},
              {"finish": "Grey painted steel", "parts": "housing", "surface": "cast_steel"}]
    assert [finish_parts.see_through(finish, every) for finish in listed] == [True, False, False]
    front = np.array([[0, 1, 1], [2, 2, 1]])
    cover = np.array([[True, True, False], [False, False, False]])
    left = finish_parts.behind_left_out(front, cover, listed, every)
    assert (left == np.array([[0, -1, 1], [2, 2, 1]])).all(), left  # the dome kept, the reflector behind it left out
    assert (finish_parts.behind_left_out(front, np.zeros_like(cover), listed, every) == front).all()


def test_a_finish_drawn_within_a_see_through_cover_is_laid_as_the_cover():
    """The garage beacon: its reflector drawn inside its red dome is the dome's (the model has nothing inside); the
    note on the opaque housing stays the note."""
    every = {"red_plastic": {"family": "plastic"}, "cast_steel": {"family": "steel"},
             "printed_paper": {"family": "paper"}}
    listed = [{"finish": "Red transparent plastic", "parts": "lamp dome", "surface": "red_plastic"},
              {"finish": "Polished reflective metal", "parts": "internal reflector", "surface": "cast_steel"},
              {"finish": "Grey painted steel", "parts": "housing", "surface": "cast_steel"},
              {"finish": "Matte paper", "parts": "note", "surface": "printed_paper"}]
    front = np.full((40, 40), -1)
    front[2:18, 5:35] = 0
    front[6:14, 12:28] = 1
    front[18:38, 5:35] = 2
    front[24:32, 12:20] = 3
    within = finish_parts.seen_within(front, listed, every)
    assert within == {1: 0}, within
    taken = finish_parts.taken_in(front, within)
    assert (taken[6:14, 12:28] == 0).all() and (taken[24:32, 12:20] == 3).all()
    assert (finish_parts.taken_in(front, {}) == front).all()


def test_a_coloured_see_through_finish_keeps_its_surface_against_its_highlights():
    """The beacon's red transparent dome measured pale pink on its brighter half: it keeps red_plastic, not the
    nearer plastic_grey; an opaque grey plastic that far off still moves."""
    import labels
    library = {"red_plastic": {"family": "plastic", "colour": [0.45, 0.02, 0.01]},
               "plastic_grey": {"family": "plastic", "colour": [0.33, 0.31, 0.27]}}
    saved = labels.allowed_materials
    labels.allowed_materials = lambda place, kind, without: library
    try:
        pale = np.array([70.8, 21.2, 11.5])
        found = finish_parts.checked_finishes(
            {"library_places": ["garage"], "kind": "beacon", "object": "beacon"},
            [{"finish": "Red transparent plastic", "parts": "lamp dome", "surface": "red_plastic"},
             {"finish": "Red plastic", "parts": "knob", "surface": "red_plastic"}], [pale, pale])
    finally:
        labels.allowed_materials = saved
    assert found[0]["surface"] == "red_plastic" and found[0]["by"] == "its own colour" and found[0]["cover"], found[0]
    assert found[1]["surface"] == "plastic_grey" and found[1]["by"] == "nearest of its family by colour", found[1]


def test_a_finish_whose_words_name_another_material_is_named_again():
    assert finish_parts.contradicts("black rubber, on the lamp's foot", "steel")
    assert finish_parts.contradicts("printed paper, on the tray's label", "rubber")
    assert not finish_parts.contradicts("grey painted metal, on the frame", "steel")
    assert not finish_parts.contradicts("brown vinyl, on the seat", "plastic")
    assert not finish_parts.contradicts("dark finish, on the body", "steel")  # no material named: nothing to say


def test_a_finish_list_reply_is_parsed_to_library_names():
    surfaces = {"mli_gold": {}, "bare_steel": {}}
    reply = json.dumps({"finishes": [{"parts": "foil", "finish": "gold foil", "surface": "M1", "fits": True},
                                     {"parts": "legs", "finish": "steel", "surface": "M2", "fits": True}]})
    assert [entry["surface"] for entry in finish_ask.parsed_list(reply, surfaces)] == ["mli_gold", "bare_steel"]


def test_two_renders_of_the_same_pixels_are_the_same_file_once_their_text_is_dropped():
    """Blender stamps each render's date and Cycles' times into the PNG: the same pixels written twice with other
    times are byte-identical after without_text, and their pixels are untouched."""
    folder = REPO / "tmp/turntable-png-test"
    folder.mkdir(parents=True, exist_ok=True)
    pixels = np.random.default_rng(0).integers(0, 255, (32, 32, 4), dtype=np.uint8)
    paths = []
    for number, seconds in enumerate(("00:00.81", "00:00.67")):
        info = PngInfo()
        info.add_text("Date", f"2026/10/12 13:48:5{number}")
        info.add_text("cycles.ViewLayer.total_time", seconds)
        path = folder / f"render{number}.png"
        Image.fromarray(pixels).save(path, pnginfo=info)
        paths.append(path)
    assert paths[0].read_bytes() != paths[1].read_bytes()
    for path in paths:
        turntable_row.without_text(path)
    assert paths[0].read_bytes() == paths[1].read_bytes()
    assert (np.asarray(Image.open(paths[0])) == pixels).all()
    for path in paths:
        path.unlink()
    folder.rmdir()


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
