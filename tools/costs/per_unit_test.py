"""The per-unit measures (per_unit.py), on ledgers written in the test: no cloud, no real ledger.

    python3 tools/costs/per_unit_test.py
"""
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import per_unit  # noqa: E402

LINES = [
    {"batch": "batch-1", "kind": "pixal", "models_done": 10, "euros": 1.0},
    {"batch": "batch-2", "kind": "pixal", "models_done": 4, "euros": 2.0},
    {"batch": "batch-3", "kind": "pixal", "models_done": 0, "euros": 0.7},
    {"batch": "blender-1", "kind": "blender", "who": "score light stage", "jobs": ["a", "b", "c", "d"], "euros": 0.4},
    {"batch": "blender-2", "kind": "blender", "who": "settle", "jobs": ["settle_stage.py"], "euros": 0.0},
    {"batch": "blender-3", "kind": "blender", "who": "settle hangar", "jobs": ["settle_stage.py"], "euros": 9.0},
]
CALLS = [
    {"day": "2026-10-12", "caller": "pro", "state": "started", "estimate": 0.13},
    {"day": "2026-10-12", "caller": "pro", "state": "finished", "euros": 0.14},
    {"day": "2026-10-11", "caller": "pro", "euros": 0.12},
    {"day": "2026-10-12", "caller": "pro", "state": "failed"},
]


def written(rows):
    path = pathlib.Path(tempfile.mkdtemp()) / "ledger.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows) + "{torn\n")
    return path


def test_a_batch_is_read_once_and_priced_over_the_units_it_finished():
    """Each batch's euros over the units it finished; one finished nothing is left out; a batch in two ledgers once."""
    first, second = written(LINES), written(LINES[:1])
    lines = per_unit.ledger_lines([first, second])
    assert [line["batch"] for line, _ in lines] == [row["batch"] for row in LINES]
    each, batches = per_unit.cloud_measures(lines, per_unit.SPECS["pixal"])
    assert each == [0.1, 0.5] and batches == ["batch-1", "batch-2"]
    each, batches = per_unit.cloud_measures(lines, per_unit.SPECS["light-passes"])
    assert each == [0.1] and batches == ["blender-1"]
    each, batches = per_unit.cloud_measures(lines, per_unit.SPECS["settle"])
    assert each == [0.0] and batches == ["blender-2"]  # a free drop counts; another `who` is another job


def test_google_units_are_finished_calls_of_the_stages_caller():
    """A call counts once it finished (or in the first format, written only then); started and failed do not."""
    each, days = per_unit.google_measures(CALLS, "pro")
    assert each == [0.14, 0.12] and days == ["2026-10-11", "2026-10-12"]


def test_the_file_holds_measured_stages_only_with_median_high_and_runs():
    """Likely the median, high the HIGH quantile, runs what they rest on; a stage with no lines is left out."""
    found = per_unit.measure(per_unit.ledger_lines([written(LINES)]), CALLS, "google-ledger.jsonl")
    assert found["pixal"]["likely_euros"] == 0.3 and found["pixal"]["runs"] == 2
    assert 0.3 < found["pixal"]["high_euros"] <= 0.5 and found["pixal"]["count"] == {"json_keys": "takes.json"}
    assert found["closeup"]["runs"] == 2 and "surfaces-maps" not in found and "surfaces-bake" not in found
    assert found["pixal"]["forecast"]["rule"] == "prop_takes" and found["closeup"]["forecast"] is None


def test_every_stage_has_a_forecast_rule_with_its_source_or_says_why_not():
    for stage, spec in per_unit.SPECS.items():
        found = per_unit.forecast(spec)
        if found["forecast"] is None:
            assert found["forecast_why"], stage
        else:
            assert found["forecast"]["source"] == per_unit.FORECASTS[spec["forecast"]], stage


def test_rules_only_writes_the_rules_and_keeps_the_measured_numbers():
    measured = {"stage": "pixal", "unit": "model", "count": {"json_keys": "takes.json"}, "also": [],
                "likely_euros": 0.1, "high_euros": 0.4, "runs": 9, "sources": {"cloud batches": ["b1"]},
                "forecast": {"rule": "stale", "source": "old"}}
    out = pathlib.Path(tempfile.mkdtemp()) / "per-unit.json"
    out.write_text(json.dumps({"read": ["x"], "high_quantile": 0.9,
                               "stages": {"pixal": measured, "closeup": {**measured, "stage": "closeup"}}}))
    per_unit.main(["--rules-only", "--out", str(out)])
    found = json.loads(out.read_text())
    assert found["read"] == ["x"] and found["stages"]["pixal"]["likely_euros"] == 0.1
    assert found["stages"]["pixal"]["forecast"]["rule"] == "prop_takes"
    assert found["stages"]["closeup"]["forecast"] is None and found["stages"]["closeup"]["forecast_why"]


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
