"""prop_batch.py's invariants, with stand-in ledgers and makers (no cloud): the price comes from measured numbers
only (an unmeasured step is said and priced at nothing, never guessed; owner, 2026-10-20); each job is priced once,
its predicted gaps beside it, never as reruns (a batch runs every job once, CONTEXT.md); a kept step and a prop whose
inputs did not change are never paid again; a prop that fails a free check stops before the next paid step; a
batch's ledger euros are split over the props it made by their job seconds; and `run` is refused without --yes after
printing its price, before anything is written. One run and one measured ledger world; the prices are rows of one
case table read off them.

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


def test_batch_pays_each_measured_step_once(tmp_path):
    """One run (both props keep their close-up, crane-r1 fails its bake check) and one measured ledger world; the
    price table, the run's manifest, its measured costs and the refused command are all read off them."""
    lines, google = measured_ledgers()
    # one-shot image-to-3d lines (4 gaps of 12 sent, the unsent left out) and six 429s asked again free
    lines += [{**card_line("pixal", [600], batch=f"o{index}", models=4, done=3), "gaps": ["a", "z"], "unsent": ["z"]}
              for index in range(4)]
    google += [{"caller": "pro", "state": "failed", "call": "pro-x", "error": "HTTPError 429"}] * 6
    earlier = {"props": {**{f"p{index}": {"status": "done", "steps": {"closeup": {"caller": "pro"}}}
                            for index in range(9)},
                         "lost": {"status": "failed", "at": "closeup", "steps": {}},
                         "kept": {"status": "done", "steps": {"closeup": {"kept": True}}}}}
    kept = [{**prop, "keep": ["closeup"]} for prop in PROPS]
    asked = {}

    def check(step):
        return lambda prop: (False, "no body parts") if step == "bake" and prop["name"] == "crane-r1" else (True, "")
    manifest = prop_batch.run(kept, makers(asked), {step.name: check(step.name) for step in prop_batch.STEPS},
                              tmp_path / "made")
    moved = {"props": {"ship-s1": {**manifest["props"]["ship-s1"], "key": "an older key"}}}
    unbaked = [line for line in lines if line["kind"] != "library"]

    # id, props, cloud lines, previous manifest, earlier manifests, {(step or None, field): expected}
    cases = [
        ("measured", PROPS, lines, None, [earlier],
         {(None, "unmeasured"): [], ("closeup", "likely"): 0.28,  # two props, one Pro ask each at EUR 0.14
          ("closeup", "gap_share"): 0.1,  # 1 failed of 10 made or failed; the kept step and the 429s left out
          ("image-to-3d", "gap_share"): 0.333, (None, "gaps_unmeasured"): ["finish-pick", "bake"]}),
        ("each job once", PROPS * 2, lines, None, [earlier, earlier],
         {("closeup", "high"): round(4 * 0.14, 4),  # four asks, never eight
          ("closeup", "gap_share"): 0.1, ("closeup", "predicted_gaps"): 0,  # 2 failed of 20
          ("image-to-3d", "gap_share"): 0.333, (None, "predicted_gaps"): {"closeup": 0, "image-to-3d": 1},
          (None, "gaps_unmeasured"): ["finish-pick", "bake"]}),
        ("bake unmeasured", PROPS, unbaked, None, [],
         {(None, "unmeasured"): ["bake"], ("bake", "likely"): 0.0}),
        ("kept close-up", kept, lines, None, [],
         {("closeup", "likely"): 0.0, (None, "making"): ["ship-s1", "crane-r1"]}),
        ("unchanged prop", kept, lines, manifest, [],
         {(None, "making"): ["crane-r1"], (None, "kept"): 1}),  # ship-s1 done with the same key; crane-r1 stopped
        ("moved key", kept, lines, moved, [],
         {(None, "making"): ["ship-s1", "crane-r1"], (None, "kept"): 0}),
    ]
    for name, props, cloud, previous, manifests, expected in cases:
        plan = prop_batch.price(props, cloud, google, previous, manifests)
        assert 0 < plan["likely"] <= plan["high"], name
        assert plan["per_prop"]["likely"] == round(plan["likely"] / max(len(plan["making"]), 1), 3), name
        for (step, field), value in expected.items():
            found = plan["steps"][step][field] if step else plan[field]
            assert found == value, f"{name}: {step or 'plan'} {field} is {found!r}, expected {value!r}"

    assert "closeup" not in asked and asked["bake"] == ["ship-s1"]  # kept step unpaid; a failed check stops first
    assert manifest["props"]["ship-s1"]["status"] == "done"
    assert manifest["props"]["crane-r1"]["status"] == "stopped" and manifest["props"]["crane-r1"]["at"] == "bake"
    assert json.loads((tmp_path / "made/records/crane-r1.json").read_text())["why"] == "no body parts"

    # the image-to-3d batch's euros split over both props by job seconds; batches with no ledger line cost nothing
    paid = card_line("pixal", [300, 100], batch="image-to-3d-batch", euros=0.4,
                     job_seconds={"ship-s1": 300, "crane-r1": 100})
    costs = prop_batch.measured_costs(manifest, [paid])
    assert costs["ship-s1"]["image-to-3d"] == 0.3 and costs["crane-r1"]["total"] == 0.1

    props_file = tmp_path / "trial.json"
    props_file.write_text(json.dumps(kept))
    done = subprocess.run([sys.executable, str(pathlib.Path(prop_batch.__file__)), "run", str(props_file),
                           "--previous", str(tmp_path / "made/manifest.json"), "--folder", str(tmp_path / "batch")],
                          capture_output=True, text=True)
    assert done.returncode == 1
    assert done.stdout.startswith("1 of 2 props to make, EUR ")
    assert "nothing is paid without --yes" in done.stderr
    assert not (tmp_path / "batch").exists()
