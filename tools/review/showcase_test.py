"""Check the showcase's measured numbers and its figure on pieces made here: each surface's share of a model's parts is
its share of their area, a film is shown by its first walking shot (else its second), and the figure lays one inked
frame of every film in story order, its frame list beside it; the world video shows the framework's chain once, then
the hero's film and the store's other films made here in the order given, stops on a missing one and, as a draft,
names it; world 1's timeline stays within its cap. The whole cut needs the films and their stills; no
Blender, no cloud.

Run: .venv/bin/python tools/review/showcase_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import subprocess
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
        assert sheet.size == (4 * showcase.TILE[0] + 24, 7 * showcase.TILE[1] + 48), sheet.size


def store_film(path, shade):
    """A film as the runner keeps it: 5.5 s at 1280x720 with a sound track."""
    path.parent.mkdir(parents=True)
    showcase.demo.ffmpeg("-f", "lavfi", "-i", f"color=c=0x{shade:02x}6464:s=1280x720:d=5.5:r=24", "-f", "lavfi", "-i",
                         "sine=frequency=440:duration=5.5", "-c:a", "aac", "-shortest", *showcase.demo.encode(path))
    return path


def check_chain():
    """The chain's cards keep its order (a step may take two cards), and a step it does not have, steps out of order or
    more than CHAIN_MOST cards stop the cut."""
    steps = [{"step": "References and style", "pictures": ["r.png"]}, {"step": "Concept", "pictures": ["c.png"]},
             {"step": "Plan", "pictures": ["p.png"]}, {"step": "Pieces", "pictures": ["a.png", "b.png"]},
             {"step": "Pieces", "pictures": ["d.png"]}]
    cards = showcase.chain_cards({"steps": steps})
    assert [step for step, _, _ in cards] == ["References and style", "Concept", "Plan", "Pieces", "Pieces"], cards
    for wrong in ([steps[2], steps[1]], [{"step": "Place", "pictures": ["f.png"]}],
                  [steps[0]] * (showcase.CHAIN_MOST + 1)):
        try:
            showcase.chain_cards({"steps": wrong})
            raise AssertionError(f"cut with {wrong}")
        except SystemExit:
            pass


def check_credit():
    """A credited picture carries its credit at the bottom right; an uncredited one is left as it was."""
    plain = Image.new("RGB", (showcase.W, showcase.H), (200, 200, 200))
    assert np.array_equal(np.asarray(showcase.credited(plain.copy(), None)), np.asarray(plain))
    marked = np.asarray(showcase.credited(plain.copy(), "Generated using World Labs"))
    assert (marked[-60, -60] != 200).any() and (marked[60, 60] == 200).all()


def check_timeline():
    """World 1 as cut on 18 Oct (four chain cards, 27 films, the two ending clips joined): every place PLACE_MOST, the
    places most of the time, and the whole within WORLD_MOST."""
    shown = [(film, showcase.PLACE_MOST) for film, *_ in showcase.PLACES] + [("hull", showcase.PLACE_MOST)]
    parts = showcase.timeline(4, shown, 14.0 + 20.0 - showcase.FADE)
    assert [name for name, _ in parts][:2] == ["chain", "flat"] and parts[-1][0] == "ending", parts
    whole = showcase.total(parts)
    assert whole <= showcase.WORLD_MOST, whole
    assert sum(seconds for _, seconds in shown) / whole > 0.75, whole


def check_world(folder):
    """The hero's film comes right after the chain whatever its story place, a missing film stops the cut but not a
    draft, the video is as long as its timeline, and its sound never drops below a whisper."""
    films = [("stairwell", "Stairwell", store_film(folder / "a/film.mp4", 40), "a"), ("street", "Street", None, None),
             ("flat", "Flat", store_film(folder / "b/film.mp4", 200), "b")]
    for number in range(4):
        Image.new("RGB", (300, 200), (60 * number, 90, 90)).save(folder / f"{number}.png")
    steps = [{"step": "Concept", "line": "a concept", "pictures": [str(folder / "0.png")]},
             {"step": "Pieces", "line": "pieces", "pictures": [str(folder / "2.png"), str(folder / "3.png")]}]
    assets = folder / "assets.json"
    assets.write_text(json.dumps({"hero": "flat", "opening": str(folder / "1.png"), "steps": steps,
                                  "credits": {str(folder / "0.png"): "Generated using World Labs"}}))
    showcase.ENDING = folder / "ending"
    try:
        showcase.world(folder / "out", folder / "fig.jpg", films, assets)
        raise AssertionError("a missing film was cut")
    except SystemExit as stop:
        assert "street" in str(stop), stop
    showcase.world(folder / "out", folder / "fig.jpg", films, assets, draft=True)
    record = json.loads((folder / "out/world1.json").read_text())
    assert [film["film"] for film in record["films"]] == ["flat", "stairwell"] and record["missing"] == ["street"]
    assert record["steps"] == ["Concept", "Pieces"], record
    shown = [(film["film"], 5.5 - showcase.demo.TITLE_SECONDS) for film in record["films"]]
    expected = showcase.total(showcase.timeline(2, shown, 0))
    measured = showcase.length(folder / "out/world1.mp4")
    assert abs(measured - expected) < 0.2, (measured, expected)
    quiet = subprocess.run(["ffmpeg", "-v", "info", "-i", str(folder / "out/world1.mp4"), "-ss", "0.5", "-af",
                            "silencedetect=n=-60dB:d=0.3", "-f", "null", "-"], capture_output=True, text=True).stderr
    assert "silence_start" not in quiet, quiet
    with Image.open(folder / "fig.jpg") as sheet:
        assert sheet.size == (4 * showcase.TILE[0] + 24, showcase.TILE[1]), sheet.size


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    with tempfile.TemporaryDirectory() as temporary:
        check_chain()
        check_credit()
        check_timeline()
        for check in (check_legend, check_figure, check_world):
            place = pathlib.Path(temporary) / check.__name__
            place.mkdir()
            check(place)
    print("showcase_test: ok")


def test_many_clips_join_in_groups_as_long_as_one_join(tmp_path):
    """57 clips in one ffmpeg graph stalled (2026-10-18): the world joins in groups of JOIN_GROUP, every cross-fade
    kept, so 10 one-second clips still come out 10 - 9 x FADE_SECONDS long."""
    import subprocess
    clips = []
    for index in range(10):
        clip = tmp_path / f"c{index}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=64x36:d=1:r=24",
                        "-pix_fmt", "yuv420p", str(clip)], check=True)
        clips.append(clip)
    out = tmp_path / "world.mp4"
    showcase.joined_in_groups(clips, [1.0] * 10, out, tmp_path)
    seconds = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    str(out)], capture_output=True, text=True, check=True).stdout)
    assert abs(seconds - (10 - 9 * showcase.demo.FADE_SECONDS)) < 0.1


def test_clips_whose_picture_outlasts_their_sound_join_with_both(tmp_path):
    """A film clip's picture runs 3.54 s, its sound 3.5 s; 8 such clips in one graph wrote nothing (2026-10-18). Joined
    apart, the picture is as long as one join and the sound is there."""
    import subprocess
    clips = []
    for index in range(8):
        clip = tmp_path / f"s{index}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=64x36:d=3.5417:r=24",
                        "-f", "lavfi", "-i", "sine=f=440:d=3.5", "-pix_fmt", "yuv420p", "-c:a", "aac", str(clip)],
                       check=True)
        clips.append(clip)
    out = tmp_path / "joined.mp4"
    showcase.joined_in_groups(clips, [3.5417] * 8, out, tmp_path)
    kinds = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True, check=True).stdout.split()
    seconds = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    str(out)], capture_output=True, text=True, check=True).stdout)
    assert sorted(kinds) == ["audio", "video"]
    assert abs(seconds - (8 * 3.5417 - 7 * showcase.demo.FADE_SECONDS)) < 0.2
