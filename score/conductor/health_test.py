"""The conductor's health names its size, memory, disk, units, runs, backup and sync, and its log tails carry no
secret.

Run: .venv/bin/python score/conductor/health_test.py
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.conductor import health, logs  # noqa: E402

SHOWN = {"score-sync.timer": ("active", ""), "score-sync.service": ("inactive", "success"),
         "score-listen.service": ("failed", "exit-code"), "score-resume.service": ("inactive", "success"),
         "score-backup.timer": ("inactive", ""), "score-backup.service": ("inactive", "")}


def properties(unit):
    state, result = SHOWN[unit]
    return {"ActiveState": state, "Result": result,
            "ExecMainExitTimestamp": "@1792656000" if unit == "score-sync.service" else ""}


def test_each_unit_family_reads_active_failed_or_inactive():
    assert {name: health.unit_state(units, properties) for name, units in health.UNITS.items()} == {
        "sync": "active", "listen": "failed", "resume": "inactive", "backup": "inactive"}
    assert health.last_sync(properties) == {"at": "2026-10-22T08:00:00+00:00", "ok": True}


def test_the_health_has_every_field_the_machine_card_reads_and_is_written_whole():
    folder = pathlib.Path(tempfile.mkdtemp())
    kept = health.BACKUPS
    health.BACKUPS = folder
    try:
        for stamp, kind, ok in (("0900", "backup", False), ("0930", "backup", True), ("0945", "check-data", False)):
            (folder / f"backup-20261022T{stamp}.json").write_text(json.dumps(
                {"at": f"2026-10-22T{stamp[:2]}:{stamp[2:]}:00+00:00", "kind": kind, "ok": ok}))
        found = health.read(properties)
        assert set(found) == {"at", "machine", "size", "state", "cores", "memory_total", "memory_available", "memory",
                              "disk_free", "disk", "load", "units", "runs_active", "runs_waiting", "parked_machines",
                              "last_backup", "backup", "last_sync", "sync", "free_only"}, sorted(found)
        assert found["last_backup"] == found["backup"] == {"at": "2026-10-22T09:30:00+00:00", "ok": True}
        assert found["sync"]["at"] == "2026-10-22T08:00:00+00:00"
        assert found["memory_total"] >= found["memory_available"] > 0 and len(found["load"]) == 3
        assert found["disk"]["total_gb"] >= found["disk"]["free_gb"] == found["disk_free"]
        path = health.write(found, folder / "health.json")
        assert json.loads(path.read_text()) == found and not list(folder.glob("*.partial"))
    finally:
        health.BACKUPS = kept
        shutil.rmtree(folder)


def test_the_log_tails_leave_out_every_line_naming_or_holding_a_secret():
    folder = pathlib.Path(tempfile.mkdtemp())
    kept = os.environ.get("SCORE_SYNC_TOKEN")
    os.environ["SCORE_SYNC_TOKEN"] = "s3cr3t-sync-value"
    try:
        (folder / "logs").mkdir()
        (folder / "faults").mkdir()
        (folder / "logs" / "score-run-1.log").write_text(
            "brief@north: made\nreading gemini-api-key by name\nsent s3cr3t-sync-value along\n"
            "header X-Auth-Token: abc\nexit: ok\n")
        (folder / "faults" / "brief@south.txt").write_text("cause: the brief is empty\n")
        found = logs.tails(10, logs=folder / "logs", faults=folder / "faults",
                           read_journal=lambda unit, limit: [f"{unit}: fine"])
        assert found["run score-run-1.log"] == ["brief@north: made", "exit: ok"], found
        assert found["fault brief@south"] == ["cause: the brief is empty"]
        assert found["journal score-listen.service"] == ["score-listen.service: fine"]
        assert logs.tail(folder / "logs" / "score-run-1.log", 1) == ["exit: ok"]
    finally:
        os.environ.pop("SCORE_SYNC_TOKEN") if kept is None else os.environ.update({"SCORE_SYNC_TOKEN": kept})
        shutil.rmtree(folder)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
