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

from score.stages.surfaces import finish_ask, finish_maps, finish_parts  # noqa: E402


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


def test_a_loose_bit_joins_the_nearest_larger_island_with_its_finish():
    big = trimesh.creation.box(extents=(1, 1, 1))
    loose = trimesh.creation.box(extents=(0.02, 0.02, 0.02))
    loose.apply_translation((0.53, 0, 0))
    far = trimesh.creation.box(extents=(1, 1, 1))
    far.apply_translation((3, 0, 0))
    mesh = trimesh.util.concatenate([big, loose, far])
    label = np.r_[np.zeros(len(big.faces)), np.ones(len(loose.faces)), np.ones(len(far.faces))].astype(int)
    part_of, merged = finish_parts.merged_islands(mesh, label)
    bit = slice(len(big.faces), len(big.faces) + len(loose.faces))
    assert len(np.unique(part_of)) == 2 and (part_of[bit] == part_of[0]).all() and (merged[bit] == 0).all()


def test_agreement_and_mixing_count_against_the_maps():
    mesh = trimesh.creation.icosphere(subdivisions=2)
    top = mesh.triangles_center[:, 1] > 0
    face_label = np.zeros(len(mesh.faces), dtype=int)
    front = np.where(top, 1, 0)  # the map says finish 1 on top, the paint says 0 everywhere
    agreement = finish_parts.agreement(mesh, face_label, {"front": front})
    assert 0.4 < agreement["front"] < 0.6, agreement
    mixing = finish_parts.mixing_parts(mesh, np.zeros(len(mesh.faces), dtype=int), face_label, {"front": front}, 2)
    assert mixing and mixing[0][0] == 0, mixing


def test_a_finish_list_reply_is_parsed_to_library_names():
    surfaces = {"mli_gold": {}, "bare_steel": {}}
    reply = json.dumps({"finishes": [{"parts": "foil", "finish": "gold foil", "surface": "M1", "fits": True},
                                     {"parts": "legs", "finish": "steel", "surface": "M2", "fits": True}]})
    assert [entry["surface"] for entry in finish_ask.parsed_list(reply, surfaces)] == ["mli_gold", "bare_steel"]


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
