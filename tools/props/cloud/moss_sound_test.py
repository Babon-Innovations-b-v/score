"""Checks for a MOSS share as a cluster job (SCORE_CLOUD=k8s), without renting anything."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import moss_sound  # noqa: E402


def test_a_share_runs_moss_run_and_comes_back_to_the_cache(tmp_path):
    jobs = [{"sound": "door", "prompt": "a heavy door", "seed": 1, "seconds": 2, "file": "door-1.wav"}]
    job = moss_sound.cluster_job(2, jobs, tmp_path / "jobs-2.json", tmp_path / "out")
    assert json.loads((tmp_path / "jobs-2.json").read_text()) == jobs
    assert job["command"] == ["moss-run", "/root/sfx/jobs-2.json", "2"]
    assert job["inputs"] == [{"local": str(tmp_path / "jobs-2.json"), "path": "/root/sfx/jobs-2.json"}]
    assert job["outputs"] == [{"path": "/root/sfx/out", "local": str(tmp_path / "out")}]
    assert job["models"] == ["moss-soundeffect-v2", "clap-larger-general"]
    assert "tools/props/cloud/moss_generate.py" in job["code"]
