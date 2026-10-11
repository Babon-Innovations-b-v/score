"""The finish-map route's own checks, with no spend: a map drawn larger and off centre is laid back on the close-up and
passes, one missing a listed finish or mostly off its label colours fails; the walk names unseen faces from the
nearest seen ones along the surface; a SegviGen part takes its seen faces' label; a finish list reply is parsed to
library names; the rows hold together.

Run: .venv/bin/python score/stages/finishmap/finishmap_test.py
"""
import json
import pathlib
import sys

import numpy as np
import trimesh
from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score.stages.finishmap import ask, lay, maps, trial  # noqa: E402


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
    measures, per_pixel = maps.check(drawn(ask.LABELS[0], ask.LABELS[1]), alpha, 2, ask.LABELS)
    assert measures["passes"] and measures["iou"] > 0.95, measures
    assert per_pixel[60, 100] == 0 and per_pixel[140, 100] == 1 and per_pixel[10, 10] == -1


def test_a_map_missing_a_finish_or_off_its_colours_fails():
    alpha = close_up_alpha()
    missing, _ = maps.check(drawn(ask.LABELS[0], ask.LABELS[0]), alpha, 2, ask.LABELS)
    assert not missing["passes"] and missing["labels_used"] == 1, missing
    shaded, _ = maps.check(drawn((90, 90, 90), ask.LABELS[1]), alpha, 2, ask.LABELS)
    assert not shaded["passes"] and shaded["near_label"] < 0.6, shaded


def test_unseen_faces_take_the_nearest_seen_label_along_the_surface():
    mesh = trimesh.creation.icosphere(subdivisions=3)
    seen = np.full(len(mesh.faces), -1)
    middles = mesh.triangles_center
    seen[(middles[:, 2] > 0.5) & (middles[:, 0] > 0)] = 0
    seen[(middles[:, 2] > 0.5) & (middles[:, 0] <= 0)] = 1
    walked = lay.walked(mesh, seen)
    assert (walked >= 0).all()
    back = middles[:, 2] < -0.5
    assert (walked[back & (middles[:, 0] > 0.3)] == 0).mean() > 0.9
    assert (walked[back & (middles[:, 0] < -0.3)] == 1).mean() > 0.9


def test_a_segvigen_part_takes_its_seen_faces_label():
    mesh = trimesh.creation.icosphere(subdivisions=2)
    part_of = (mesh.triangles_center[:, 1] > 0).astype(int)
    seen = np.full(len(mesh.faces), -1)
    seen[(mesh.triangles_center[:, 1] > 0.5)] = 1
    walked = np.zeros(len(mesh.faces), dtype=int)
    named = lay.part_labels(mesh, part_of, seen, walked, 2)
    assert (named[part_of == 1] == 1).all() and (named[part_of == 0] == 0).all()


def test_a_finish_list_reply_is_parsed_to_library_names():
    surfaces = {"mli_gold": {}, "bare_steel": {}}
    reply = json.dumps({"finishes": [{"parts": "foil", "finish": "gold foil", "surface": "M1", "fits": True},
                                     {"parts": "legs", "finish": "steel", "surface": "M2", "fits": True}]})
    assert [entry["surface"] for entry in ask.parsed_list(reply, surfaces)] == ["mli_gold", "bare_steel"]


def test_the_rows_hold_together():
    names = [stage.name for stage in trial.stages()]
    assert names == ["fm-lists", "fm-maps", "fm-segvigen", "fm-arms"], names
    assert all(stage.euros for stage in trial.stages() if stage.paid)


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
