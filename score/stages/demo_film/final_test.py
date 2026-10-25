"""The environment-film row with no Blender and no spend: its script checks before anything is cut (the creator's yes,
every segment's seconds, only cuts it makes), the owner's pacing as faults, k9's own script read, and one small cut
with ffmpeg over two films made here, its gate passing at one loudness and failing a place cut at 3.5 s.

Run: .venv/bin/python score/stages/demo_film/final_test.py
"""
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks, graph  # noqa: E402
from score.stages.demo_film import final, needs  # noqa: E402


def a_script(segments):
    return {"format": "score-film-script", "version": 1, "film": "toy", "size": [1280, 720], "rate": 24,
            "segments": segments}


WALKS = [{"cut": "title", "shows": {"world": "toy"}, "sound": "bed", "text": "Toy", "seconds": 2.0},
         {"cut": "walk-through", "shows": {"place": "alpha"}, "sound": "place", "text": "Alpha", "seconds": 7.0},
         {"cut": "walk-through", "shows": {"place": "beta"}, "sound": "place", "text": "Beta", "seconds": 7.0}]


def refused(call):
    try:
        call()
    except graph.Blocked as blocked:
        return str(blocked)
    raise AssertionError("not blocked")


def test_nothing_is_cut_before_the_creators_yes_and_a_sound_plan():
    assert "no film script locked" in refused(lambda: final.require_yes({}))
    final.require_yes({"toy": a_script(WALKS)})
    assert final.plan_faults(a_script(WALKS)) == []
    unsound = a_script([{"cut": "exploded", "shows": {"place": "alpha"}},
                        {"cut": "walk-through", "shows": {"place": "alpha"}, "sound": "bed", "seconds": 7.0}])
    assert final.plan_faults(unsound) == ["segment 1 (exploded) names no seconds",
                                          "segment 1: no row makes exploded frames yet",
                                          "segment 2: a walk-through plays its place's own sound, not bed"]
    assert final.plan_faults(a_script(WALKS[:1])) == ["it shows no place's film and names no bed"]
    assert final.plan_faults(dict(a_script(WALKS[:1]), bed="sound/hum")) == []


def test_the_owners_pacing_fails_a_place_cut_at_three_and_a_half_seconds():
    """The owner's review of 2026-10-18: about 3.5 s a place, far too fast; about 7 s, two steady shots."""
    assert final.pacing_faults(final.script_segments(a_script(WALKS))) == []
    fast = [dict(WALKS[1], seconds=3.5), dict(WALKS[2], seconds=3.0)]
    assert final.pacing_faults(final.script_segments(a_script(fast))) == [
        "beta: a walk-through of 3 s, under 3.5 s", "alpha: on screen 3.5 s, under 7 s", "beta: on screen 3 s, under 7 s"]
    two_shots = [dict(WALKS[1], seconds=3.5), dict(WALKS[1], seconds=3.5)]
    assert final.pacing_faults(final.script_segments(a_script(two_shots))) == []


def locked_in(home, *films):
    """The cockpit's home `home` holding `films` ({film: script}) locked, as the Film step's Lock keeps them."""
    folder = home / final.LOCKED
    folder.mkdir(parents=True, exist_ok=True)
    for path in folder.glob("*.json"):
        path.unlink()
    for film, script in films:
        (folder / f"{film}.json").write_text(json.dumps(script))
    final.DASHBOARD = home


def test_world1s_script_is_paced_and_names_the_cuts_no_row_makes_yet():
    k9 = json.loads((REPO / "data/films/k9.json").read_text())
    assert final.pacing_faults(final.script_segments(k9)) == []
    faults = final.plan_faults(k9)
    assert faults and all("no row makes" in fault for fault in faults), faults
    kept = final.DASHBOARD
    locked_in(pathlib.Path(tempfile.mkdtemp()), ("k9", k9))
    try:
        assert len(final.shown_places()) == 24 and final.film_node(
            {"shows": {"place": "hangar", "film": "hull"}}) == ("demo-film-extra@hangar", "hull")
    finally:
        final.DASHBOARD = kept


def test_the_locked_script_is_the_rows_input_and_a_new_lock_moves_its_key():
    """The Film step's seam: the environment-film row reads only the locked scripts in the cockpit's home, so a lock,
    a changed lock and an unlock each move the files part of its key; the starters and his unlocked edits do not."""
    from score import stages
    from score.store import Store
    home, kept = pathlib.Path(tempfile.mkdtemp()), final.DASHBOARD
    world = graph.Environment("world1", 0, {**stages.world1().roots, "dashboard": str(home)})
    runner = graph.Runner(stages.STAGES, world, Store.in_folder(home / "store"))
    row = runner.stages["environment-film"]
    try:
        locked_in(home)
        assert not any(name.startswith("script ") for name in runner.file_keys(row, None))
        locked_in(home, ("toy", a_script(WALKS)))
        first = runner.file_keys(row, None)["script toy"]
        assert final.shown_places() == ["alpha", "beta"]
        locked_in(home, ("toy", a_script(WALKS[:2])))
        assert runner.file_keys(row, None)["script toy"] != first
        assert final.shown_places() == ["alpha"]
    finally:
        final.DASHBOARD = kept


def test_a_film_a_script_shows_waits_on_its_lock():
    """The film layer's gaps (needs.py), worked out from the scripts alone: a film a starter shows that no locked
    script shows waits on his lock, its node named; a locked one is no gap."""
    import shutil
    from score.stages import demo_film
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "films").mkdir()
    walk = {"cut": "walk-through", "seconds": 4.0}
    script = {"segments": [dict(walk, shows={"place": "alpha"}), dict(walk, shows={"place": "beta"})]}
    (data / "films/env.json").write_text(json.dumps(script))
    real = final.scripts
    final.scripts = lambda: {"env": {"segments": [dict(walk, shows={"place": "beta"})]}}
    try:
        assert [(gap["id"], gap["node"]) for gap in needs.gaps("alpha", data)] == [
            ("film:yes:alpha", "demo-film@alpha")]
        assert needs.gaps("beta", data) == [] and needs.gaps("gamma", data) == []
        assert demo_film.films()["beta"]["final"] is True, "the lock is the yes"
    finally:
        final.scripts = real
        shutil.rmtree(data)


def a_film(folder, tone, volume):
    """A place film as demo-film keeps one: 9 s at 1280x720, its sound a tone at `volume`."""
    folder.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc2=size=1280x720:rate=24:duration=9", "-f", "lavfi", "-i",
                    f"sine=frequency={tone}:duration=9,volume={volume}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", str(folder / "film.mp4")], check=True)
    return folder


def test_a_cut_runs_at_one_loudness_and_its_gate_holds_the_pacing():
    root = pathlib.Path(tempfile.mkdtemp())
    script = root / "toy.json"
    script.write_text(json.dumps(a_script(WALKS)))
    inputs = {"script toy": script, "demo-film@alpha": a_film(root / "alpha", 330, 0.05),
              "demo-film@beta": a_film(root / "beta", 440, 0.6)}
    out = root / "out"
    out.mkdir()
    final.make(inputs, out, 0, {})
    assert final.output_faults(out) == []
    timeline = json.loads((out / "toy" / "timeline.json").read_text())
    assert [segment["film"] for segment in timeline["segments"]] == [None, "demo-film@alpha", "demo-film@beta"]
    assert timeline["seconds"] == 15.0
    verdict = final.judge(out, inputs, {})
    assert verdict.answer == checks.PASS, verdict
    timeline["segments"][1]["seconds"] = 3.5  # the 18 Oct cut's pace, written into the record
    (out / "toy" / "timeline.json").write_text(json.dumps(timeline))
    verdict = final.judge(out, inputs, {})
    assert verdict.answer == checks.FAIL and "toy: alpha: on screen 3.5 s, under 7 s" in verdict.findings, verdict


def test_a_recorded_segment_is_cut_from_the_previews_take_of_that_very_segment():
    """A screen take, physics animation or scale zoom is the free preview's take, only while the preview was recorded
    from the segment the lock holds; then cut with the cards on the script's bed, every film matched in exposure."""
    root = pathlib.Path(tempfile.mkdtemp())
    take = {"cut": "screen-take", "shows": {"page": "/"}, "sound": "bed", "seconds": 3.0}
    script = a_script([WALKS[0], take, WALKS[1]])
    (root / "toy.json").write_text(json.dumps({"script": script}))
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc2=size=1280x720:rate=24:duration=3", "-pix_fmt", "yuv420p", str(root / "002.mp4")],
                   check=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=220:duration=5", str(root / "bed.wav")], check=True)
    inputs = {"preview toy": root / "toy.json", "take toy 2": root / "002.mp4"}
    assert final.takes("toy", script, inputs) == {2: root / "002.mp4"}
    assert set(final.recorded_files("toy", script)) == {"preview toy", "take toy 2"}
    moved = dict(script, segments=[WALKS[0], dict(take, seconds=4.0), WALKS[1]])
    assert "segment(s) 2 of the free preview" in refused(lambda: final.takes("toy", moved, inputs))
    assert final.matched_gain(116.0, 116.0) == 1.0 and final.matched_gain(40.0, 200.0) == final.GAIN_RANGE[1]
    alpha = a_film(root / "alpha", 330, 0.2) / "film.mp4"
    still = {"cut": "hero-still", "shows": {"place": "alpha"}, "sound": "bed", "text": "Alpha", "seconds": 3.0}
    out = root / "out"
    final.cut_one(dict(script, segments=[*script["segments"], still]), {3: alpha, 4: alpha}, out,
                  {2: root / "002.mp4"}, root / "bed.wav")
    timeline = json.loads((out / "timeline.json").read_text())
    assert [segment["cut"] for segment in timeline["segments"]] == ["title", "screen-take", "walk-through",
                                                                    "hero-still"]
    assert timeline["segments"][2]["exposure_gain"] == 1.0 and timeline["seconds"] == 13.5



def test_a_locked_script_with_recorded_segments_wants_its_preview_until_it_is_made_from_the_lock():
    """previews_wanted, what the sync pass makes: a lock with a recorded segment and no preview, or one recorded from
    another script, wants it; a preview of the very lock, or a script with no recorded segment, does not."""
    home, kept = pathlib.Path(tempfile.mkdtemp()), final.DASHBOARD
    take = {"cut": "screen-take", "shows": {"page": "/"}, "sound": "bed", "seconds": 3.0}
    script = a_script([WALKS[0], take, WALKS[1]])
    try:
        locked_in(home, ("toy", script), ("plain", a_script(WALKS)))
        assert final.previews_wanted() == ["toy"]
        (home / final.PREVIEWS).mkdir(parents=True)
        (home / final.PREVIEWS / "toy.json").write_text(json.dumps({"script": script}))
        assert final.previews_wanted() == []
        locked_in(home, ("toy", dict(script, segments=[WALKS[0], dict(take, seconds=4.0), WALKS[1]])))
        assert final.previews_wanted() == ["toy"]
    finally:
        final.DASHBOARD = kept

if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
