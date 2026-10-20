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
    assert found["pixal"]["forecast"]["rule"] == "prop_takes" and "per_model" not in found["pixal"]["forecast"]
    assert found["closeup"]["forecast"]["per_model"] == round(25 / 21, 4)  # pictures a model, as recorded


def test_a_recorded_stage_is_priced_from_its_runs_with_their_sources_and_no_count_rule():
    """Each recorded run's euros over its units; likely their median; runs how many; the sources named."""
    found = per_unit.measure([], [], "google-ledger.jsonl")["surfaces-paint"]
    runs = per_unit.RECORDED["surfaces-paint"]["runs"]
    each = sorted(run["euros"] / run["units"] for run in runs)
    assert found["likely_euros"] == round((each[0] + each[1]) / 2, 5) and found["runs"] == len(runs)
    assert found["sources"]["recorded runs"] == [run["source"] for run in runs] and found["count"] is None
    assert found["forecast"]["rule"] == "models"


def test_a_maps_units_a_model_are_the_codes_bound_and_the_lists_price_says_its_tier():
    """Under the batch rule (#21) a model draws one close-up map and one of each map view, at most: the forecast is
    that bound from the code, said so, never a ratio of the old method's draws."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
    from score.stages.surfaces import finish_rows, turntable_views
    assert per_unit.MAP_DRAWS == len(finish_rows.SEEDS) + len(finish_rows.VIEW_SEEDS) * len(turntable_views.MAP_VIEWS)
    found = per_unit.forecast(per_unit.SPECS["surfaces-maps"])
    assert found["forecast"]["per_model"] == per_unit.MAP_DRAWS
    assert "not a measurement" in found["forecast"]["per_model_from"], found
    assert "standard tier" in per_unit.forecast(per_unit.SPECS["surfaces-lists"])["price_note"]
    assert "surfaces-names" not in per_unit.SPECS  # names by rule: free since #21


def test_every_stage_has_a_forecast_rule_with_its_source():
    for stage, spec in {**per_unit.SPECS, **per_unit.RECORDED}.items():
        found = per_unit.forecast(spec)
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
    assert found["stages"]["closeup"]["forecast"]["rule"] == "prop_takes"
    assert set(per_unit.RECORDED) <= set(found["stages"])  # the recorded stages written again


REPO = HERE.parents[1]
PAPER = REPO / "paper/evidence/cloud/ledger.jsonl"


def paper_line(batch):
    """One real line of the paper's ledger copy, by its batch."""
    return next((line, source) for line, source in per_unit.ledger_lines([PAPER]) if line["batch"] == batch)


def test_a_cloud_stages_time_is_read_from_its_machines_own_job_seconds():
    """Real lines: a settle run's one job and its card's start wait; a Pixal3D batch of three at once on one card."""
    settle = per_unit.cloud_times([paper_line("blender-20261008-165605-2054366")], per_unit.SPECS["settle"])
    assert settle["unit_seconds"] == {"likely": 539.6, "high": 539.6} and settle["slots"] == 1, settle
    # set-up: the card's 0.37 min start wait and its 2.93 min in the machine before its 539.6 s job (11.93 working)
    assert settle["setup_minutes"] == {"likely": 3.304, "high": 3.304}, settle
    assert settle["failed_start_share"] == 0 and settle["holds"] == "machines"
    pixal = per_unit.cloud_times([paper_line("batch-20261008-134426-1833430")], per_unit.SPECS["pixal"])
    assert pixal["unit_seconds"]["likely"] == 629.98 and pixal["slots"] == 3, pixal
    # 0.60 start wait and 13.33 working minutes less three jobs' 1589 s run three at once
    assert pixal["setup_minutes"] == {"likely": 5.102, "high": 5.102}, pixal
    assert per_unit.cloud_times([], per_unit.SPECS["settle"])["why"].startswith("no ledger line")


def test_a_stage_whose_lines_time_no_set_up_says_so_and_never_writes_a_zero():
    line = {"batch": "b", "kind": "pixal", "models_done": 2, "machine_minutes": 20.0, "euros": 1.0}
    found = per_unit.cloud_times([(line, "here line 1")], per_unit.SPECS["pixal"])
    assert found["unit_seconds"]["likely"] == 600.0 and found["setup_minutes"] == {
        "why": "no line read here timed a machine's set-up"}, found


def test_a_line_without_machine_seconds_is_timed_by_its_working_minutes_and_slots_over_its_units():
    """A job's time, not the batch's throughput: the machines' working minutes times the jobs each ran at once."""
    line = {"batch": "b", "kind": "pixal", "models_done": 4, "machine_minutes": 20.0, "euros": 1.0}
    assert per_unit.unit_seconds(line, "models_done") == [300.0] * 4
    two = {**line, "per_card": 2, "machines": [{"cards": 1, "work_minutes": 10.0, "minutes": 11.0},
                                               {"cards": 1, "work_minutes": 10.0, "minutes": 11.0}]}
    assert per_unit.unit_seconds(two, "models_done") == [600.0] * 4
    assert per_unit.unit_seconds({**line, "machine_minutes": None}, "models_done") == []


def test_writing_times_in_place_keeps_a_measured_time_the_ledgers_read_here_do_not_hold():
    body = {"stages": {"closeup": {"time": {"unit_seconds": {"likely": 30.0, "high": 50.0}}},
                       "pixal": {"time": {"why": "none"}}}, "node_minutes": {"plan": {"likely": 2.0}}}
    stage_times, made = per_unit.kept_times(body, {"closeup": {"why": "no Google ledger read here"},
                                                   "pixal": {"unit_seconds": {"likely": 9.0, "high": 9.0}}}, {})
    assert stage_times["closeup"]["unit_seconds"]["likely"] == 30.0 and stage_times["pixal"]["unit_seconds"]
    assert made == {"plan": {"likely": 2.0}}


def test_a_google_stages_time_is_its_calls_started_to_finished_and_how_many_ran_at_once():
    calls = [{"call": "a", "caller": "pro", "state": "started", "time": "2026-10-12T10:00:00+02:00"},
             {"call": "b", "caller": "pro", "state": "started", "time": "2026-10-12T10:00:10+02:00"},
             {"call": "a", "caller": "pro", "state": "finished", "time": "2026-10-12T10:00:30+02:00", "euros": 0.1},
             {"call": "b", "caller": "pro", "state": "finished", "time": "2026-10-12T10:01:10+02:00", "euros": 0.1},
             {"call": "c", "caller": "pro", "state": "failed"}, {"caller": "pro", "euros": 0.1}]
    found = per_unit.google_times(calls, "pro", "google-ledger.jsonl")
    assert found["unit_seconds"]["likely"] == 45.0 and found["slots"] == 1 and found["holds"] == "calls"
    assert found["failed_start_share"] == round(1 / 3, 3) and found["lines"] == 2
    assert "why" in per_unit.google_times(calls, "pro", None) and "why" in per_unit.google_times([], "pro", "g")


def test_node_minutes_are_the_store_finish_records_minutes_by_stage():
    sys.path.insert(0, str(REPO))
    from score.graph import runs
    from score.store import Store
    root = pathlib.Path(tempfile.mkdtemp())
    store = Store.in_folder(root)
    for number, (node, minutes) in enumerate((("plan@hangar", 3.0), ("plan@lab", 5.0), ("concept@lab", 1.0))):
        store.write_record(node, f"key{number}", {"node": node, "stage": node.partition("@")[0], "place": "p",
                                                   "key": f"key{number}", "started": f"2026-10-20T0{number}",
                                                   "finished": f"2026-10-20T1{number}", "minutes": minutes})
    store.write_record("plan@flat", "key9", {"node": "plan@flat", "stage": "plan", "finished": "2026-10-20T19",
                                             "minutes": 99.0, "carried": {"reason": "kept over a no-op"}})
    made = runs.node_times(store)  # a carried record is no make
    assert [row["node"] for row in made] == ["plan@hangar", "plan@lab", "concept@lab"]
    found = per_unit.node_minutes(made, root)
    assert found["plan"]["likely"] == 4.0 and found["plan"]["makes"] == 2 and found["concept"]["high"] == 1.0


def test_writing_the_times_leaves_every_euro_of_the_per_unit_file_byte_identical():
    """The repository's own per-unit file, its time written again from the paper's ledger copy: every field but the
    time fields is the same, byte for byte."""
    out = pathlib.Path(tempfile.mkdtemp()) / "per-unit.json"
    before = json.loads((REPO / "data/costs/per-unit.json").read_text())
    out.write_text(json.dumps(before, indent=1) + "\n")
    per_unit.main(["--times-only", "--ledger", str(PAPER), "--out", str(out)])
    after = json.loads(out.read_text())

    def without_time(body):
        return json.dumps({**{name: value for name, value in body.items() if name != "node_minutes"},
                           "stages": {stage: {name: value for name, value in found.items() if name != "time"}
                                      for stage, found in body["stages"].items()}}, indent=1)

    assert without_time(after) == without_time(before)
    assert set(after["stages"]) == set(before["stages"]) and all("time" in found for found in after["stages"].values())


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
