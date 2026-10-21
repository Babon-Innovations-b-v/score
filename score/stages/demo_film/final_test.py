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


def a_script(segments, ready=True):
    return {"format": "score-film-script", "version": 1, "film": "toy", "size": [1280, 720], "rate": 24,
            "segments": segments, **({"final": True} if ready else {})}


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
    assert "no yes yet for the film toy" in refused(lambda: final.require_yes({"toy": a_script(WALKS, ready=False)}))
    final.require_yes({"toy": a_script(WALKS)})
    assert final.plan_faults(a_script(WALKS)) == []
    unsound = a_script([{"cut": "exploded", "shows": {"place": "alpha"}},
                        {"cut": "walk-through", "shows": {"place": "alpha"}, "sound": "bed", "seconds": 7.0}])
    assert final.plan_faults(unsound) == ["segment 1 (exploded) names no seconds",
                                          "segment 1: no row makes exploded frames yet",
                                          "segment 2: a walk-through plays its place's own sound, not bed"]
    assert final.plan_faults(a_script(WALKS[:1])) == ["it shows no place's film"]


def test_the_owners_pacing_fails_a_place_cut_at_three_and_a_half_seconds():
    """The owner's review of 2026-10-18: about 3.5 s a place, far too fast; about 7 s, two steady shots."""
    assert final.pacing_faults(final.script_segments(a_script(WALKS))) == []
    fast = [dict(WALKS[1], seconds=3.5), dict(WALKS[2], seconds=3.0)]
    assert final.pacing_faults(final.script_segments(a_script(fast))) == [
        "beta: a walk-through of 3 s, under 3.5 s", "alpha: on screen 3.5 s, under 7 s", "beta: on screen 3 s, under 7 s"]
    two_shots = [dict(WALKS[1], seconds=3.5), dict(WALKS[1], seconds=3.5)]
    assert final.pacing_faults(final.script_segments(a_script(two_shots))) == []


def test_world1s_script_is_paced_and_names_the_cuts_no_row_makes_yet():
    k9 = final.scripts()["k9"]
    assert final.pacing_faults(final.script_segments(k9)) == []
    faults = final.plan_faults(k9)
    assert faults and all("no row makes" in fault for fault in faults), faults
    assert len(final.shown_places()) == 25 and final.film_node(
        {"shows": {"place": "hangar", "film": "hull"}}) == ("demo-film-extra@hangar", "hull")


def test_a_place_a_script_shows_needs_its_film_record_its_yes_and_two_shots():
    """The film layer's gaps (needs.py), worked out from the scripts and records alone."""
    data = pathlib.Path(tempfile.mkdtemp())
    for folder in ("films", "definitions/demo_films", "scene"):
        (data / folder).mkdir(parents=True)
    (data / "films/toy.json").write_text(json.dumps(a_script(
        [*WALKS, {"cut": "walk-through", "shows": {"place": "alpha", "film": "wing"}, "seconds": 7.0}])))
    (data / "definitions/demo_films/alpha.json").write_text(json.dumps({"place": "alpha", "camera": "door"}))
    (data / "definitions/demo_films/beta.json").write_text(json.dumps({"place": "beta", "camera": "door",
                                                                       "then": "back", "final": True}))
    (data / "scene/alpha.json").write_text(json.dumps({"views": [{"name": "door"}]}))
    assert [(gap["id"], gap["node"]) for gap in needs.gaps("alpha", data)] == [
        ("film:yes:alpha", "demo-film@alpha"), ("film:shot:alpha", None), ("film:record:wing", None)]
    assert needs.gaps("beta", data) == [] and needs.gaps("gamma", data) == []


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


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
