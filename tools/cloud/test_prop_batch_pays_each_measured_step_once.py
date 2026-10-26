"""prop_batch.py's invariants, with stand-in ledgers and makers (no cloud): the price comes from measured numbers
only (an unmeasured step is said and priced at nothing, never guessed; owner, 2026-10-20); each job is priced once,
its predicted gaps beside it, never as reruns (a batch runs every job once, CONTEXT.md); a kept step and a prop whose
inputs did not change are never paid again; a prop that fails a free check stops before the next paid step; a
batch's ledger euros are split over the props it made by their job seconds; and `run` is refused without --yes after
printing its price, before anything is written.

Break that turns it red: in `to_make` ignore the earlier manifest's keys (every prop made again); in `run` hand a prop
that failed its check to the step's maker; or make `makes_step` always True (a kept step paid again).
"""
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import prop_batch  # noqa: E402

PROPS = [{"name": "ship-s1", "place": "hangar", "picture": None, "body": "ship-s1"},
         {"name": "crane-r1", "place": "campgrounds", "picture": None, "body": None}]


def card_line(kind, seconds, batch="b1", euros=0.3, models=None, done=None, job_seconds=None):
    """One ledger line of a `kind` batch on one measured L4."""
    line = {"kind": kind, "batch": batch, "started": f"2026-10-10T00:00:{len(seconds):02d}Z", "euros": euros,
            "machines": [{"type": "L4-1-24G", "cards": 1, "started": True, "start_wait_minutes": 0.5,
                          "setup_minutes": 1.0, "work_minutes": 20.0, "minutes": 22.0, "euros": euros,
                          "unit_seconds": list(seconds)}]}
    if models is not None:
        line.update(models=models, models_done=done)
    if job_seconds:
        line["job_seconds"] = job_seconds
    return line


def google_lines(caller, euros, count):
    return [{"caller": caller, "state": "finished", "euros": euros, "call": f"{caller}-{index}"} for index in range(count)]


def measured_ledgers():
    """Three measured machines for each card step, ten calls at EUR 0.14 (Pro) and 0.02 (the list) for Google's."""
    lines = [card_line("pixal", [600, 660, 720], batch=f"p{index}", models=4, done=3) for index in range(3)]
    lines += [card_line("library", [40, 50], batch=f"l{index}") for index in range(3)]
    return lines, google_lines("pro", 0.14, 10) + google_lines("finishmap-list", 0.02, 10)


def makers(asked):
    """A maker per step that records the props it was handed and makes them all."""
    def maker(step):
        def make(props):
            asked.setdefault(step, []).extend(prop["name"] for prop in props)
            return {prop["name"]: {"batch": f"{step}-batch"} for prop in props}
        return make
    return {step.name: maker(step.name) for step in prop_batch.STEPS}


def test_the_price_is_measured_and_an_unmeasured_step_is_said():
    lines, google = measured_ledgers()
    plan = prop_batch.price(PROPS, lines, google)
    assert plan["unmeasured"] == []
    assert plan["steps"]["closeup"]["likely"] == 0.28  # two props, one Pro ask each at EUR 0.14
    assert 0 < plan["likely"] <= plan["high"]
    assert plan["per_prop"]["likely"] == round(plan["likely"] / 2, 3)
    unbaked = prop_batch.price(PROPS, [line for line in lines if line["kind"] != "library"], google)
    assert unbaked["unmeasured"] == ["bake"] and unbaked["steps"]["bake"]["likely"] == 0.0


def test_each_job_is_priced_once_with_its_predicted_gaps_beside():
    lines, google = measured_ledgers()
    lines += [{**card_line("pixal", [600], batch=f"o{index}", models=4, done=3), "gaps": ["a", "z"], "unsent": ["z"]}
              for index in range(4)]
    google += [{"caller": "pro", "state": "failed", "call": "pro-x", "error": "HTTPError 429"}] * 6
    earlier = {"props": {**{f"p{index}": {"status": "done", "steps": {"closeup": {"caller": "pro"}}}
                            for index in range(9)},
                         "lost": {"status": "failed", "at": "closeup", "steps": {}},
                         "kept": {"status": "done", "steps": {"closeup": {"kept": True}}}}}
    plan = prop_batch.price(PROPS * 2, lines, google, manifests=[earlier, earlier])
    assert plan["steps"]["closeup"]["high"] == round(4 * 0.14, 4)  # four asks, never eight
    assert plan["steps"]["closeup"]["gap_share"] == 0.1  # 2 failed of 20 made or failed; the 429s asked again free
    assert plan["steps"]["closeup"]["predicted_gaps"] == 0
    assert plan["steps"]["image-to-3d"]["gap_share"] == 0.333  # 4 gaps of 12 sent; the unsent left out
    assert plan["predicted_gaps"]["image-to-3d"] == 1
    assert plan["gaps_unmeasured"] == ["finish-pick", "bake"]


def test_an_unchanged_prop_and_a_kept_step_are_not_paid_again(tmp_path):
    previous = {"props": {"ship-s1": {"key": prop_batch.prop_key(PROPS[0]), "status": "done"}}}
    assert [prop["name"] for prop in prop_batch.to_make(PROPS, previous)] == ["crane-r1"]
    moved = {"props": {"ship-s1": {"key": "an older key", "status": "done"}}}
    assert len(prop_batch.to_make(PROPS, moved)) == 2
    lines, google = measured_ledgers()
    kept = [{**prop, "keep": ["closeup"]} for prop in PROPS]
    assert prop_batch.price(kept, lines, google)["steps"]["closeup"]["likely"] == 0.0
    asked = {}
    manifest = prop_batch.run(kept, makers(asked), {step.name: lambda prop: (True, "") for step in prop_batch.STEPS},
                              tmp_path)
    assert "closeup" not in asked and manifest["props"]["ship-s1"]["status"] == "done"


def test_a_failed_check_stops_before_the_next_paid_step(tmp_path):
    asked = {}

    def check(step):
        return lambda prop: (False, "no body parts") if step == "bake" and prop["name"] == "crane-r1" else (True, "")
    manifest = prop_batch.run(PROPS, makers(asked), {step.name: check(step.name) for step in prop_batch.STEPS},
                              tmp_path)
    assert manifest["props"]["ship-s1"]["status"] == "done"
    assert manifest["props"]["crane-r1"]["status"] == "stopped" and manifest["props"]["crane-r1"]["at"] == "bake"
    assert asked["bake"] == ["ship-s1"]
    assert json.loads((tmp_path / "records/crane-r1.json").read_text())["why"] == "no body parts"


def test_a_batches_euros_are_split_by_job_seconds():
    manifest = {"props": {"ship-s1": {"steps": {"image-to-3d": {"batch": "p9"}}},
                          "crane-r1": {"steps": {"image-to-3d": {"batch": "p9"}}}}}
    line = card_line("pixal", [300, 100], batch="p9", euros=0.4, job_seconds={"ship-s1": 300, "crane-r1": 100})
    costs = prop_batch.measured_costs(manifest, [line])
    assert costs["ship-s1"]["image-to-3d"] == 0.3 and costs["crane-r1"]["total"] == 0.1


def test_run_is_refused_without_yes_after_its_price(tmp_path):
    props = tmp_path / "trial.json"
    props.write_text(json.dumps([{**prop, "row": prop["name"].split("-")[0], "take": prop["name"], "seed": 1,
                                  "picture": f"/pics/{prop['name']}.png", "parts": "/parts", "keep": ["closeup"]}
                                 for prop in PROPS]))
    done = subprocess.run([sys.executable, str(pathlib.Path(prop_batch.__file__)), "run", str(props), "--folder",
                           str(tmp_path / "batch")], capture_output=True, text=True)
    assert done.returncode == 1
    assert done.stdout.startswith("2 of 2 props to make, EUR ")
    assert "nothing is paid without --yes" in done.stderr
    assert not (tmp_path / "batch").exists()
