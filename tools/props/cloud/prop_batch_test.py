"""Checks for the prop batch (prop_batch.py) with stand-in ledgers and makers: the price comes from measured numbers
only (an unmeasured step is said, never guessed), a prop whose inputs did not change is kept, a prop that fails a free
check stops before the next paid step, and a batch's ledger euros are split over the props it made. No cloud.

Run: python3 tools/props/cloud/prop_batch_test.py   (make tests runs it in a sandbox home)
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import prop_batch  # noqa: E402


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
    """Three measured machines for each card step, ten calls for each Google step."""
    lines = [card_line("pixal", [600, 660, 720], batch=f"p{index}", models=4, done=3) for index in range(3)]
    lines += [card_line("library", [40, 50], batch=f"l{index}") for index in range(3)]
    return lines, google_lines("pro", 0.14, 10) + google_lines("finishmap-list", 0.02, 10)


PROPS = [{"name": "ship-s1", "place": "hangar", "picture": None, "body": "ship-s1"},
         {"name": "crane-r1", "place": "campgrounds", "picture": None, "body": None}]


def test_price_is_measured():
    lines, google = measured_ledgers()
    plan = prop_batch.price(PROPS, lines, google)
    assert plan["unmeasured"] == [], plan["unmeasured"]
    assert plan["steps"]["closeup"]["likely"] == 0.28, plan["steps"]["closeup"]
    assert plan["steps"]["image-to-3d"]["failed_share"] == 0.25
    assert 0 < plan["likely"] <= plan["high"], plan
    assert plan["per_prop"]["likely"] == round(plan["likely"] / 2, 3)


def test_each_job_is_priced_once_with_its_predicted_holes_beside():
    """A batch runs every job once (CONTEXT.md, owner 2026-10-20): the close-up was priced at two asks and Pixal3D at
    its jobs times one plus the failure share, as reruns."""
    lines, google = measured_ledgers()
    google += [{"caller": "pro", "state": "failed", "call": "pro-x"}] * 2
    plan = prop_batch.price(PROPS * 2, lines, google)
    assert plan["steps"]["closeup"]["high"] == round(4 * 0.14, 4), plan["steps"]["closeup"]  # four asks, never eight
    assert plan["steps"]["closeup"]["predicted_holes"] == 1  # 2 failed of 12 ended calls, over four jobs
    one_run = prop_batch.preflight.batch(4, prop_batch.card_numbers(lines, "pixal", "L4"), prop_batch.CAP,
                                         prop_batch.STEPS[1].slots)
    assert plan["steps"]["image-to-3d"]["likely"] == round(one_run["euros"] * prop_batch.BILL_SHARE, 4)
    assert plan["predicted_holes"]["image-to-3d"] == 1  # a quarter of four Pixal3D jobs
    assert not hasattr(prop_batch.STEPS[0], "tries")


def test_unmeasured_step_is_said_not_guessed():
    lines, google = measured_ledgers()
    plan = prop_batch.price(PROPS, [line for line in lines if line["kind"] != "library"], google)
    assert plan["unmeasured"] == ["bake"], plan["unmeasured"]
    assert plan["steps"]["bake"]["likely"] == 0.0


def test_unchanged_prop_is_kept():
    previous = {"props": {"ship-s1": {"key": prop_batch.prop_key(PROPS[0]), "status": "done"}}}
    assert [prop["name"] for prop in prop_batch.to_make(PROPS, previous)] == ["crane-r1"]
    moved = {"props": {"ship-s1": {"key": "an older key", "status": "done"}}}
    assert len(prop_batch.to_make(PROPS, moved)) == 2


def test_failed_check_stops_before_the_next_paid_step():
    asked = {step.name: [] for step in prop_batch.STEPS}

    def maker(step):
        def make(props):
            asked[step].extend(prop["name"] for prop in props)
            return {prop["name"]: {"batch": f"{step}-batch"} for prop in props}
        return make

    def check(step):
        return lambda prop: (False, "no body parts") if step == "bake" and prop["name"] == "crane-r1" else (True, "")

    with tempfile.TemporaryDirectory() as out:
        manifest = prop_batch.run(PROPS, {step.name: maker(step.name) for step in prop_batch.STEPS},
                                  {step.name: check(step.name) for step in prop_batch.STEPS}, out)
        assert manifest["props"]["ship-s1"]["status"] == "done"
        assert manifest["props"]["crane-r1"]["status"] == "stopped"
        assert manifest["props"]["crane-r1"]["at"] == "bake"
        assert asked["bake"] == ["ship-s1"], asked
        assert json.loads((pathlib.Path(out) / "records/crane-r1.json").read_text())["why"] == "no body parts"


def test_kept_step_is_not_paid():
    lines, google = measured_ledgers()
    kept = [{**prop, "keep": ["closeup"]} for prop in PROPS]
    assert prop_batch.price(kept, lines, google)["steps"]["closeup"]["likely"] == 0.0
    asked = []

    def maker(name):
        def make(props):
            asked.append(name)
            return {prop["name"]: {"batch": name} for prop in props}
        return make

    makers = {step.name: maker(step.name) for step in prop_batch.STEPS}
    with tempfile.TemporaryDirectory() as out:
        manifest = prop_batch.run(kept, makers, {step.name: lambda prop: (True, "") for step in prop_batch.STEPS}, out)
    assert "closeup" not in asked and manifest["props"]["ship-s1"]["status"] == "done", (asked, manifest)


def test_batch_euros_split_by_job_seconds():
    manifest = {"props": {"ship-s1": {"steps": {"image-to-3d": {"batch": "p9"}}},
                          "crane-r1": {"steps": {"image-to-3d": {"batch": "p9"}}}}}
    line = card_line("pixal", [300, 100], batch="p9", euros=0.4, job_seconds={"ship-s1": 300, "crane-r1": 100})
    costs = prop_batch.measured_costs(manifest, [line])
    assert costs["ship-s1"]["image-to-3d"] == 0.3, costs
    assert costs["crane-r1"]["total"] == 0.1, costs


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, function in list(globals().items()):
        if name.startswith("test_"):
            function()
    print("prop_batch: 6 checks passed")
