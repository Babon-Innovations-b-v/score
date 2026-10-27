"""Check the film checks on films made here: a short video with a tone passes the video checks and fails them when too
short or silent; on two rooms with a person standing in one (tools/usd camera_paths.py's test) a shot whose eye walks
through the person fails, as the square's first take walked through its crowd, and so does one that passes 0.1 m from
a wall, while a shot clear of both passes; a frame with no ink lines fails, and so does a shot whose lines touch
nothing in any frame, and a frame whose lines are faint or empty (a far view) fails unless the experimental
past-fade rule counts it; and the summary adds up each cloud batch's own cost line. ffmpeg on the path; no Blender,
no cloud.

Breaks (each applied once, seen red, reverted), in tools/review/film_checks.py:
- the video checks: video_checks' length test becomes `if False:`.
- the clearance: clearance_checks never counts a frame near a person (`+= 0`).
- the ink: ink_checks never fails the frames inked nowhere at half strength (`if False:`).
- the report: cost_lines keeps only the last batch's euros (`total = float(euros)`).

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python tools/review/test_a_film_is_shown_only_when_its_measures_pass.py
"""
import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import film_checks  # noqa: E402
import test_a_walk_goes_through_doorways_clear_of_everything as camera_paths_test  # noqa: E402  (tools/usd, on the path through demo)


def a_folder():
    """A fresh folder in the run's own temp folder (removed with it)."""
    return pathlib.Path(tempfile.mkdtemp())


def tone_video(path, seconds, sound=True):
    """A 1920x1080 test picture for `seconds`, with a tone under it or none."""
    audio = ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"] if sound else []
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc2=size=1920x1080:rate=24:duration={seconds}", *audio, "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", *(["-c:a", "aac", "-shortest"] if sound else []), str(path)], check=True)
    return path


def test_a_film_too_short_or_silent_fails_its_video_checks():
    folder = a_folder()
    video = tone_video(folder / "tone.mp4", 3)
    passed = film_checks.video_checks(video, 2.0, 4.0)
    assert not passed["failures"] and passed["size"] == [1920, 1080] and passed["mean_db"] > -50, passed
    short = film_checks.video_checks(video, 20.0, 40.0)
    assert short["failures"] == ["length 3.0 s outside 20-40"], short["failures"]
    silent = film_checks.video_checks(tone_video(folder / "silent.mp4", 3, sound=False), 2.0, 4.0)
    assert silent["failures"] == ["no sound track"], silent["failures"]


def walk(name, start, end, frames=12):
    """A shot's views walking straight from one eye to another, at the stage's first moment."""
    return [{"name": f"{name}-{index:03d}", "eye": list(np.asarray(start) + (np.asarray(end) - start) * index
                                                       / (frames - 1)), "frame": 0} for index in range(frames)]


def test_a_shot_through_a_person_or_past_a_wall_fails_its_clearance():
    folder = a_folder()
    stage = camera_paths_test.rooms_stage(folder)
    camera_paths_test.add_person(stage, "stander", (0.6, 1.8, 0.6), (-2.0, 0.9, 0.0))
    views = (walk("shot0", [-3.0, 1.6, 2.0], [-1.0, 1.6, 2.0]) + walk("shot1", [-3.0, 1.6, 0.0], [-1.0, 1.6, 0.0])
             + walk("shot2", [-3.9, 1.6, -2.0], [-3.9, 1.6, 2.0]))
    shots, failures = film_checks.clearance_checks(stage, views)
    assert shots["shot0"]["near_walls"] == 0 and shots["shot0"]["near_people"] == 0, shots["shot0"]
    assert shots["shot1"]["near_people"] > 0 and shots["shot1"]["people"] == 0.0, shots["shot1"]
    assert shots["shot2"]["near_walls"] == 12 and abs(shots["shot2"]["walls"] - 0.1) < 1e-3, shots["shot2"]
    assert len(failures) == 2 and failures[0].startswith("shot1:") and "person" in failures[0], failures


def test_a_frame_with_no_ink_fails_unless_past_the_fade():
    folder = a_folder()
    frames = folder / "frames"
    frames.mkdir()
    names = ["shot0-000", "shot0-001", "shot0-002", "shot0-003", "shot1-000"]
    for name, ink in (("shot0-000", 255), ("shot0-001", 0), ("shot0-003", 10), ("shot1-000", 0)):
        lines = Image.new("RGBA", (8, 4), (10, 9, 8, 0))
        lines.putpixel((2, 2), (10, 9, 8, ink))
        lines.save(frames / f"{name}-lines.png")
        Image.new("RGB", (8, 4)).save(frames / f"{name}-ink.png")
    found, failures = film_checks.ink_checks(frames, [{"name": name} for name in names], past_fade=True)
    assert found == {"missing": 1, "empty": 2, "faint": 1, "fewest_inked_pixels": 0}, found
    assert failures == ["1 frames with no ink (first shot0-002)", "shot1: the ink touches no pixel in any frame"], \
        failures
    # Fault (audit of 2026-10-11, item 7): 0e68b5e's rule passed a whole shot with no line at half strength (launch
    # shot 1); it is experimental, so by default such frames fail.
    found, failures = film_checks.ink_checks(frames, [{"name": name} for name in names])
    assert failures[-1] == "3 frames inked nowhere at half strength (first shot0-001)", failures


def test_the_report_adds_up_each_batchs_own_cost():
    folder = a_folder()
    (folder / "out" / "checks").mkdir(parents=True)
    video = tone_video(folder / "out" / "flat.mp4", 3)
    (folder / "out" / "checks" / "flat.json").write_text(json.dumps(film_checks.video_checks(video, 2.0, 4.0)))
    logs = []
    for number, euros in enumerate(("1.25", "0.50")):
        logs.append(folder / f"batch{number}.log")
        logs[-1].write_text(f"[cloud] 18:00 blender: 2 jobs in 3.0 min on 2 machines, €{euros}\n")
    logs.append(folder / "unfinished.log")
    logs[-1].write_text("[cloud] 18:00 renting\n")
    film_checks.report(folder / "out", folder / "summary.txt", logs)
    text = (folder / "summary.txt").read_text()
    assert "PLACE FILMS" in text and ": PASS" in text and text.strip().endswith("total €1.75"), text
    assert "unfinished.log: no summary line (did not finish)" in text, text


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(HERE.parents[1] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
