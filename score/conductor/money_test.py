"""The conductor's own bill never enters the batch's spend: the stop line reads the batch project's bill alone, and
every paid run is refused if the batch project is ever the conductor's.

Run: .venv/bin/python score/conductor/money_test.py
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

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


def test_every_clearance_and_rent_point_refuses_while_the_batch_project_is_the_conductors():
    """Not the stop line alone: a benchmark grant's and a reading's clearance (books_refusal) and every rent point,
    the owner's override included (require_books), refuse too; and the machine's record names its project even when
    the env file lost SCORE_CONDUCTOR_SIZE_URL."""
    kept = {name: os.environ.get(name) for name in ("SCORE_SCALEWAY_PROJECT", conductor.FREE_ONLY, conductor.SIZE_URL)}
    record = pathlib.Path(tempfile.mkdtemp()) / "machine.json"
    try:
        for name in kept:
            os.environ.pop(name, None)
        os.environ["SCORE_SCALEWAY_PROJECT"] = conductor.CONDUCTOR_PROJECT
        assert "the conductor's own project" in compute.books_refusal()
        try:
            compute.require_books("a card")
            raise AssertionError("a rent point cleared in the conductor's project")
        except compute.Refused as refused:
            assert "the conductor's own project" in str(refused), refused
        os.environ["SCORE_SCALEWAY_PROJECT"] = "batch-of-another-name"
        record.write_text(json.dumps({"project": "batch-of-another-name"}))
        assert conductor.machine(record) is None  # not a conductor by the size function's name...
        assert "the conductor's own project" in conductor.project_refusal(record)  # ...yet its own project
        record.write_text(json.dumps({"project": "score-conductor-elsewhere"}))
        assert conductor.project_refusal(record) is None
    finally:
        for name, value in kept.items():
            os.environ.pop(name, None) if value is None else os.environ.update({name: value})
        shutil.rmtree(record.parent)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
