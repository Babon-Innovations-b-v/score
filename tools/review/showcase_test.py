"""Check the showcase's measured numbers and its figure on pieces made here: each surface's share of a model's parts is
its share of their area, a film is shown by its first walking shot (else its second), and the figure lays one inked
frame of every film in story order, its frame list beside it. The whole cut needs the films and their stills; no
Blender, no cloud.

Run: .venv/bin/python tools/review/showcase_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

import numpy as np
import trimesh
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import showcase  # noqa: E402


def check_legend(folder):
    """Two parts, one three times the other's area: 75% and 25%, each with its library colour in sRGB."""
    big, small = trimesh.creation.box(extents=(3.0, 1.0, 1.0)), trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    files = []
    for name, mesh, area in (("hull", big, 14.0), ("steel", small, 14.0 / 3.0)):
        mesh.apply_scale(np.sqrt(area / mesh.area))
        mesh.export(folder / f"{name}.ply")
        files.append({"path": str(folder / f"{name}.ply"), "colour": [1.0, 0.0, 0.0]})
    shots = {"groups": [{"name": "aft_section-parts", "members": [{"files": files}]}]}
    assert showcase.surfaces_legend(shots) == [("hull", (255, 0, 0), "75%"), ("steel", (255, 0, 0), "25%")], \
        showcase.surfaces_legend(shots)


def films_folder(folder):
    """A films' out folder with every film's views and the middle frame of its shown shot, its lines drawn alone."""
    (folder / "views").mkdir()
    for number, (film, *_) in enumerate(showcase.PLACES):
        moves = [{"move": "stand"}, {"move": "walk" if number % 2 else "stand"}, {"move": "walk"}]
        (folder / "views" / f"{film}.json").write_text(json.dumps({"moves": moves}))
        frames = folder / "frames" / film
        frames.mkdir(parents=True)
        name = f"shot{showcase.shown_shot(folder, film)}-096"
        Image.new("RGB", (64, 36), (number * 10, 100, 100)).save(frames / f"{name}-look.png")
        Image.new("RGBA", (64, 36), (10, 9, 8, 255)).save(frames / f"{name}-lines.png")


def check_figure(folder):
    films_folder(folder)
    assert showcase.shown_shot(folder, "flat") == 2 and showcase.shown_shot(folder, "stairwell") == 1
    showcase.figure(folder, folder / "figure.jpg")
    used = json.loads((folder / "figure.json").read_text())
    assert [film for film, _, _ in used] == [film for film, *_ in showcase.PLACES], used
    assert all(path.endswith("-ink.png") and pathlib.Path(path).exists() for _, _, path in used), used
    assert used[-1][1] == "Mars camp grounds", used[-1]
    with Image.open(folder / "figure.jpg") as sheet:
        assert sheet.size == (3 * showcase.TILE[0] + 16, 6 * showcase.TILE[1] + 40), sheet.size


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temporary:
        for check in (check_legend, check_figure):
            place = pathlib.Path(temporary) / check.__name__
            place.mkdir()
            check(place)
    print("showcase_test: ok")
