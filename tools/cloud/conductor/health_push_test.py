"""The conductor's small pieces with no cloud: the health record's shrink-guard counts, the secret reader finding its
project by name, and score-secrets writing the file-shaped secrets whole, at mode 600, to the runtime folder only."""
import base64
import datetime
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import health_push  # noqa: E402


def executable(path, text):
    path.write_text(text)
    path.chmod(0o755)
    return path


def test_record_counts_live_claims_parked_and_frozen():
    with tempfile.TemporaryDirectory() as folder:
        home = pathlib.Path(folder)
        (home / "runs").mkdir()
        dead = subprocess.Popen(["true"])
        dead.wait()
        claims = {str(os.getpid()): {"commit": "c"}, str(dead.pid): {"commit": "c"}}
        (home / "runs" / "active.json").write_text(json.dumps(claims))
        (home / "cloud" / "parked").mkdir(parents=True)
        (home / "cloud" / "parked" / "machine-1.json").write_text("{}")
        for copy in ("run-a", "run-waiting", "run-left-behind"):
            (home / "frozen" / copy).mkdir(parents=True)
        (home / "runs" / "waiting.json").write_text(json.dumps({"state": "waiting-for-size",
                                                                 "worktree": str(home / "frozen" / "run-waiting")}))
        working = [subprocess.Popen(["sleep", "30"], cwd=home / "frozen" / copy) for copy in ("run-a", "run-waiting")]
        (home / "conductor").mkdir()
        (home / "conductor" / "health.json").write_text(json.dumps({"disk": 12}))
        os.environ["SCORE_HEALTH_FILE"] = str(home / "conductor" / "health.json")
        try:
            record = health_push.record(home, datetime.datetime(2026, 10, 22, tzinfo=datetime.timezone.utc))
        finally:
            del os.environ["SCORE_HEALTH_FILE"]
            for process in working:
                process.kill()
                process.wait()
        # run-a has a process in it; the waiting run's copy waits for the grow itself; the left-behind one is idle
        assert record["active_runs"] == 1 and record["parked"] == 1 and record["frozen"] == 1
        assert record["health"] == {"disk": 12} and record["written_at"].startswith("2026-10-22T00:00:00")


def test_record_of_an_empty_home_is_idle():
    with tempfile.TemporaryDirectory() as folder:
        record = health_push.record(pathlib.Path(folder), datetime.datetime.now(datetime.timezone.utc))
        assert (record["active_runs"], record["parked"], record["frozen"], record["health"]) == (0, 0, 0, None)


def test_an_unreadable_claims_file_is_never_read_as_idle():
    with tempfile.TemporaryDirectory() as folder:
        home = pathlib.Path(folder)
        (home / "runs").mkdir()
        (home / "runs" / "active.json").write_text('{"123": ')
        try:
            health_push.record(home, datetime.datetime.now(datetime.timezone.utc))
            raise AssertionError("a claims file that does not parse was pushed as a record")
        except ValueError:
            pass


SCW_SHIM = """#!/bin/sh
echo "$*" >> "{log}"
case "$1 $2" in
  "account project")
    echo '[{{"name": "other", "id": "p-0"}}, {{"name": "secrets-here", "id": "p-1"}}]' ;;
  "secret version")
    echo '{{"data": "{data}"}}' ;;
  "secret secret")
    echo '[{{"name": "gemini-api-key", "id": "s-1"}}]' ;;
esac
"""
# A secret reader printing each secret's name as its value, past the optional flag.
READER_SHIM = "#!/bin/sh\n[ \"$1\" = --if-present ] && shift\nprintf 'value of %s' \"$1\"\n"


def test_reader_finds_the_project_by_name():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        log = folder / "scw.log"
        data = base64.b64encode(b"the value").decode()
        scw = executable(folder / "scw", SCW_SHIM.format(log=log, data=data))
        env = {**os.environ, "SCORE_SCW": str(scw), "SCORE_SECRETS_PROJECT": "secrets-here",
               "SCORE_READER_PYTHON": sys.executable}
        done = subprocess.run(["sh", str(HERE / "secret_reader.sh"), "gemini-api-key"], env=env, capture_output=True,
                              text=True, timeout=30)
        assert done.returncode == 0 and done.stdout == "the value", done.stderr
        calls = log.read_text().splitlines()
        assert calls[0].startswith("account project list name=secrets-here")
        assert "secret-name=gemini-api-key project-id=p-1 revision=latest region=fr-par" in calls[1]
        env["SCORE_SECRETS_PROJECT"] = "missing"
        refused = subprocess.run(["sh", str(HERE / "secret_reader.sh"), "x"], env=env, capture_output=True, text=True,
                                 timeout=30)
        assert refused.returncode != 0 and "found 0" in refused.stderr


def test_secrets_go_to_the_runtime_folder_whole_and_private():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        runtime = folder / "run"
        runtime.mkdir()
        reader = executable(folder / "reader", READER_SHIM)
        gcloud = executable(folder / "gcloud", f"#!/bin/sh\necho \"$CLOUDSDK_CONFIG $*\" > {folder}/gcloud.log\n")
        env = {**os.environ, "XDG_RUNTIME_DIR": str(runtime), "SCORE_SECRET_READER": str(reader),
               "SCORE_GCLOUD": str(gcloud)}
        done = subprocess.run(["sh", str(HERE / "secrets.sh")], env=env, capture_output=True, text=True, timeout=30)
        assert done.returncode == 0, done.stderr
        secrets = runtime / "score"
        assert stat.S_IMODE(secrets.stat().st_mode) == 0o700
        key = secrets / "score-lib-deploy-key"
        assert key.read_text() == "value of score-lib-deploy-key\n"
        assert stat.S_IMODE(key.stat().st_mode) == 0o600
        assert (secrets / "google-billing-reader.json").read_text() == "value of google-billing-reader\n"
        assert sorted(path.name for path in secrets.iterdir()) == ["google-billing-reader.json",
                                                                  "score-lib-deploy-key"]
        gcloud_call = (folder / "gcloud.log").read_text()
        assert gcloud_call.startswith(f"{secrets}/gcloud auth activate-service-account")
        empty = executable(folder / "empty", "#!/bin/sh\n")
        env["SCORE_SECRET_READER"] = str(empty)
        refused = subprocess.run(["sh", str(HERE / "secrets.sh")], env=env, capture_output=True, text=True, timeout=30)
        assert refused.returncode != 0 and "empty" in refused.stderr
        assert key.read_text() == "value of score-lib-deploy-key\n", "an empty read replaced a good key"


def test_without_a_billing_reader_the_secrets_skip_it_with_a_note():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        (folder / "run").mkdir()
        # --if-present on a secret the project does not hold: nothing printed, exit 0
        reader = executable(folder / "reader", "#!/bin/sh\n[ \"$1\" = --if-present ] && exit 0\n"
                                               "printf 'value of %s' \"$1\"\n")
        env = {**os.environ, "XDG_RUNTIME_DIR": str(folder / "run"), "SCORE_SECRET_READER": str(reader),
               "SCORE_GCLOUD": "/bin/false"}
        done = subprocess.run(["sh", str(HERE / "secrets.sh")], env=env, capture_output=True, text=True, timeout=30)
        assert done.returncode == 0 and "skipped" in done.stdout, done.stderr
        secrets = folder / "run" / "score"
        assert sorted(path.name for path in secrets.iterdir()) == ["google-billing-reader.note", "score-lib-deploy-key"]
        failing = executable(folder / "failing", "#!/bin/sh\n[ \"$1\" = --if-present ] && exit 1\n"
                                                 "printf 'value of %s' \"$1\"\n")
        env["SCORE_SECRET_READER"] = str(failing)
        refused = subprocess.run(["sh", str(HERE / "secrets.sh")], env=env, capture_output=True, text=True, timeout=30)
        assert refused.returncode != 0 and "reading google-billing-reader failed" in refused.stderr


def test_reader_if_present_prints_nothing_for_a_secret_the_project_lacks():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        data = base64.b64encode(b"the value").decode()
        scw = executable(folder / "scw", SCW_SHIM.format(log=folder / "scw.log", data=data))
        env = {**os.environ, "SCORE_SCW": str(scw), "SCORE_SECRETS_PROJECT": "secrets-here",
               "SCORE_READER_PYTHON": sys.executable}
        absent = subprocess.run(["sh", str(HERE / "secret_reader.sh"), "--if-present", "google-billing-reader"],
                                env=env, capture_output=True, text=True, timeout=30)
        assert absent.returncode == 0 and absent.stdout == "", absent.stderr
        held = subprocess.run(["sh", str(HERE / "secret_reader.sh"), "--if-present", "gemini-api-key"], env=env,
                              capture_output=True, text=True, timeout=30)
        assert held.returncode == 0 and held.stdout == "the value", held.stderr


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"ok {name}")
