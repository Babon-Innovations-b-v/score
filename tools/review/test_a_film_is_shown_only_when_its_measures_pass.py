"""A film is shown only when its measures pass: six films are checked through film_checks.film_checks on one stage of
two rooms with a person standing in one (tools/usd camera_paths.py's test), each a row of FILMS with the failures, the
clearance and the ink its checks must find. A 3 s video with a tone, a shot clear of the walls and the person and every
frame inked passes; the same video held to 20-40 s fails as too short, and one with no sound track fails as silent; a
shot whose eye walks through the person fails, as the square's first take walked through its crowd, and so does one
that passes 0.1 m from a wall; a frame with no ink lines fails, and so does a shot whose lines touch nothing in any
frame, and a frame whose lines are faint or empty (a far view) fails unless the experimental past-fade rule counts
it. The summary then shows the passing film as PASS, the other five as FAIL, and adds up each cloud batch's own cost
line. ffmpeg on the path; no Blender, no cloud.

Breaks (each applied once, seen red, reverted), in tools/review/film_checks.py:
- the video checks: video_checks' length test becomes `if False:` (the short row passes).
- the clearance: clearance_checks never counts a frame near a person (`+= 0`) (the crowded row).
- the ink: ink_checks never fails the frames inked nowhere at half strength (`if False:`) (the unfaded row).
- the report: cost_lines keeps only the last batch's euros (`total = float(euros)`).

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python tools/review/test_a_film_is_shown_only_when_its_measures_pass.py
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pytest
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import film_checks  # noqa: E402
import test_a_walk_goes_through_doorways_clear_of_everything as camera_paths_test  # noqa: E402  (tools/usd, on the path through demo)


def tone_video(path, seconds, sound=True):
    """A 1920x1080 test picture for `seconds`, with a tone under it or none."""
    audio = ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"] if sound else []
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc2=size=1920x1080:rate=24:duration={seconds}", *audio, "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", *(["-c:a", "aac", "-shortest"] if sound else []), str(path)], check=True)
    return path


def walk(name, start, end, frames=12):
    """A shot's views walking straight from one eye to another, at the stage's first moment."""
    step = (np.asarray(end) - np.asarray(start)) / max(frames - 1, 1)
    return [{"name": f"{name}-{index:03d}", "eye": list(np.asarray(start) + step * index), "frame": 0}
            for index in range(frames)]


def ink_frames(folder, views, ink):
    """Each view's lines picture with one pixel at the ink's alpha (`ink[name]`, 255 when not named) and its inked
    picture; a view named with None gets neither."""
    folder.mkdir(parents=True)
    for view in views:
        alpha = ink.get(view["name"], 255)
        if alpha is None:
            continue
        lines = Image.new("RGBA", (8, 4), (10, 9, 8, 0))
        lines.putpixel((2, 2), (10, 9, 8, alpha))
        lines.save(folder / f"{view['name']}-lines.png")
        Image.new("RGB", (8, 4)).save(folder / f"{view['name']}-ink.png")


# Shots: one clear of the walls and the person, one walking through the person (as the square's first take walked
# through its crowd), one passing 0.1 m from a wall; and a four-frame shot plus a one-frame shot, both clear.
CLEAR = walk("shot0", [-3.0, 1.6, 2.0], [-1.0, 1.6, 2.0])
CROWDED = (CLEAR + walk("shot1", [-3.0, 1.6, 0.0], [-1.0, 1.6, 0.0])
           + walk("shot2", [-3.9, 1.6, -2.0], [-3.9, 1.6, 2.0]))
FADED = walk("shot0", [-3.0, 1.6, 2.0], [-1.0, 1.6, 2.0], frames=4) + walk("shot1", [-2.0, 1.6, 2.0], [-2.0, 1.6, 2.0], frames=1)
UNLINED = {"shot0-001": 0, "shot0-002": None, "shot0-003": 10, "shot1-000": 0}
ALL_INKED = {"missing": 0, "empty": 0, "faint": 0, "fewest_inked_pixels": 1}
UNLINED_INK = {"missing": 1, "empty": 2, "faint": 1, "fewest_inked_pixels": 0}
UNLINED_FAILS = ["1 frames with no ink (first shot0-002)", "shot1: the ink touches no pixel in any frame"]
CLEAR_SHOT = {"near_walls": 0, "near_people": 0}

# A film: its video (tone or silent), the length its checks allow, its views, the ink of its frames, the experimental
# past-fade rule, and the failures, the clearance per shot and the ink its checks find.
FILMS = [
    ("clear", "tone", (2.0, 4.0), CLEAR, {}, False, [], {"shot0": CLEAR_SHOT}, ALL_INKED),
    ("short", "tone", (20.0, 40.0), CLEAR, {}, False, ["length 3.0 s outside 20-40"], {"shot0": CLEAR_SHOT},
     ALL_INKED),
    ("silent", "silent", (2.0, 4.0), CLEAR, {}, False, ["no sound track"], {"shot0": CLEAR_SHOT}, ALL_INKED),
    ("crowded", "tone", (2.0, 4.0), CROWDED, {}, False,
     ["shot1: 6 frames nearer than 0.25 m to a person or a moving thing (nearest 0.000 m)",
      "shot2: 12 frames nearer than 0.25 m to a mesh (nearest 0.100 m)"],
     {"shot0": CLEAR_SHOT, "shot1": {"near_walls": 0, "near_people": 6, "people": 0.0},
      "shot2": {"near_walls": 12, "near_people": 0, "walls": pytest.approx(0.1, abs=1e-3)}}, ALL_INKED),
    ("faded", "tone", (2.0, 4.0), FADED, UNLINED, True, UNLINED_FAILS, {"shot0": CLEAR_SHOT, "shot1": CLEAR_SHOT},
     UNLINED_INK),
    # Fault (audit of 2026-10-11, item 7): 0e68b5e's rule passed a whole shot with no line at half strength (launch
    # shot 1); it is experimental, so by default such frames fail.
    ("unfaded", "tone", (2.0, 4.0), FADED, UNLINED, False,
     UNLINED_FAILS + ["3 frames inked nowhere at half strength (first shot0-001)"],
     {"shot0": CLEAR_SHOT, "shot1": CLEAR_SHOT}, UNLINED_INK),
]


def test_a_film_is_shown_only_when_its_measures_pass(monkeypatch):
    folder = pathlib.Path(tempfile.mkdtemp())
    out = folder / "out"
    (out / "videos").mkdir(parents=True)
    stage = camera_paths_test.rooms_stage(folder)
    camera_paths_test.add_person(stage, "stander", (0.6, 1.8, 0.6), (-2.0, 0.9, 0.0))
    videos = {"tone": tone_video(folder / "tone.mp4", 3), "silent": tone_video(folder / "silent.mp4", 3, sound=False)}
    for film, video, seconds, views, ink, past_fade, failures, clearance, inked in FILMS:
        shutil.copy(videos[video], out / "videos" / f"{film}.mp4")
        (out / "views").mkdir(exist_ok=True)
        (out / "views" / f"{film}.json").write_text(json.dumps({"stage": str(stage), "views": views}))
        ink_frames(out / "frames" / film, views, ink)
        monkeypatch.setattr(film_checks, "FILM_SECONDS", seconds)
        result = film_checks.film_checks(out, film, past_fade)
        assert result["failures"] == failures, (film, result["failures"])
        assert result["size"] == [1920, 1080] and (video == "silent" or result["mean_db"] > -50), (film, result)
        found = {shot: {key: result["clearance"][shot][key] for key in want} for shot, want in clearance.items()}
        assert found == clearance and set(result["clearance"]) == set(clearance), (film, result["clearance"])
        assert result["ink"] == inked, (film, result["ink"])
        assert json.loads((out / "checks" / f"{film}.json").read_text())["failures"] == failures, film
    logs = []
    for number, euros in enumerate(("1.25", "0.50")):
        logs.append(folder / f"batch{number}.log")
        logs[-1].write_text(f"[cloud] 18:00 blender: 2 jobs in 3.0 min on 2 machines, €{euros}\n")
    logs.append(folder / "unfinished.log")
    logs[-1].write_text("[cloud] 18:00 renting\n")
    film_checks.report(out, folder / "summary.txt", logs)
    text = (folder / "summary.txt").read_text()
    assert "PLACE FILMS" in text and "clear.mp4" in text and ": PASS" in text, text
    assert text.count(": FAIL") == len(FILMS) - 1 and text.strip().endswith("total €1.75"), text
    assert "unfinished.log: no summary line (did not finish)" in text, text


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(HERE.parents[1] / "conftest.py"))["refuse_outside_sandbox"]()
    with pytest.MonkeyPatch.context() as patch:
        test_a_film_is_shown_only_when_its_measures_pass(patch)
    print("ok")
