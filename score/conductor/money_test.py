"""The conductor's own bill never enters the batch's spend: the stop line reads the batch project's bill alone, and
every paid run is refused if the batch project is ever the conductor's.

Run: .venv/bin/python score/conductor/money_test.py
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import conductor  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.adapters.compute import guard  # noqa: E402

LINE = {"world": "world1", "euros": 100.0, "at": "2026-10-22T09:00:00+00:00"}
PROJECTS = [{"id": "batch-id", "name": "farm-factory"}, {"id": "conductor-id", "name": "score-conductor"}]
LINES = [{"project_id": "batch-id", "product_name": "Instances", "value": {"units": 40, "nanos": 0}},
         {"project_id": "conductor-id", "product_name": "Instances", "value": {"units": 75, "nanos": 0}}]


def test_the_bill_the_stop_line_counts_is_the_batch_projects_alone():
    compute.ledger()  # puts tools/props/cloud on the path
    import provider
    asked = []

    def scw(*arguments):
        asked.append(arguments)
        if arguments[:3] == ("account", "project", "list"):
            name = arguments[3].partition("=")[2]
            return [project for project in PROJECTS if project["name"] == name]
        if arguments[:3] == ("billing", "consumption", "list"):
            return LINES  # the API's answer may hold lines of other projects: each is checked to be the project's
        raise AssertionError(arguments)
    kept = provider.cloud.scw
    provider.cloud.scw = scw
    try:
        assert compute.cloud_bill() == 40.0
    finally:
        provider.cloud.scw = kept
    assert ("account", "project", "list", "name=farm-factory") in asked
    assert ("billing", "consumption", "list", "project-id=batch-id") in asked
    assert not any("conductor-id" in word for arguments in asked for word in arguments)


def test_every_paid_run_is_refused_while_the_batch_project_is_the_conductors():
    kept = os.environ.get("SCORE_SCALEWAY_PROJECT")
    try:
        os.environ.pop("SCORE_SCALEWAY_PROJECT", None)
        assert guard.refusal(LINE, 0.0, {}, 1.0) is None
        os.environ["SCORE_SCALEWAY_PROJECT"] = conductor.CONDUCTOR_PROJECT
        refused = guard.refusal(LINE, 0.0, {}, 1.0)
        assert refused and "the conductor's own project" in refused, refused
    finally:
        os.environ.pop("SCORE_SCALEWAY_PROJECT", None)
        if kept is not None:
            os.environ["SCORE_SCALEWAY_PROJECT"] = kept


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
