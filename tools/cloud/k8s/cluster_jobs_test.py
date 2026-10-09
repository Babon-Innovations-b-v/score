"""Checks for the runners' door to the cluster, with the store a folder and the cluster stubbed: inputs go up (a
folder as one key a file) at their paths, the job.json is the runtime's, outputs come back where the runner wants them,
and a job that did not finish is reported by its number."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import cluster_jobs  # noqa: E402


class Helper:
    """The runtime's submit side over a folder store, with a fixed image."""

    def __init__(self, store_folder):
        self.real = cluster_jobs.submitter.runtime()
        self.store = self.real.stores.FolderStore(store_folder)

    def __getattr__(self, name):
        return getattr(self.real, name)

    def cloud_store(self):
        return self.store

    def image(self, kind):
        return f"registry.example/score-{kind}:1@sha256:00"


def finish(store, run, specs, failing):
    """What the cluster would leave: each output in the store and done.json, except for the failing jobs."""
    for job_id, spec in specs.items():
        prefix = f"runs/{run}/{job_id}/"
        if job_id in failing:
            store.write_bytes(prefix + "failed-1.json", json.dumps({"stage": "command", "error": "exit 1"}).encode())
            continue
        uploaded = []
        for output in spec["outputs"]:
            key = output["key"] + ("/part/a.txt" if output["path"].endswith("folder") else "")
            store.write_bytes(key, f"made by {job_id}".encode())
            uploaded.append(key)
        store.write_bytes(prefix + "done.json", json.dumps({"outputs": uploaded, "timings": {}}).encode())


def test_jobs_run_and_outputs_come_back(tmp_path, monkeypatch):
    helper = Helper(tmp_path / "store")
    monkeypatch.setattr(cluster_jobs.submitter, "runtime", lambda: helper)
    seen = {}

    def submit(run, specs, store, wait_scale_down=True, who=None, parallel=None):
        seen.update(run=run, specs=specs, wait=wait_scale_down, who=who)
        finish(store, run, specs, failing={"1"})
        return []
    monkeypatch.setattr(cluster_jobs.submitter, "submit", submit)
    stage = tmp_path / "in" / "stage"
    (stage / "textures").mkdir(parents=True)
    (stage / "place.usda").write_text("usda")
    (stage / "textures" / "wall.png").write_text("png")
    single = tmp_path / "in" / "job.json"
    single.write_text("{}")
    out_file, out_folder = tmp_path / "out" / "result.json", tmp_path / "out" / "folder"
    jobs = [{"command": ["true"], "code": ["tools/cloud/k8s"], "inputs": [str(stage), str(single)],
             "outputs": [str(out_file), str(out_folder)], "minutes": 3, "kernel_cache": "blender-5.0.1"},
            {"command": ["false"], "code": ["tools/cloud/k8s"], "inputs": [], "outputs": [], "minutes": 3}]
    failed = cluster_jobs.run("blender", jobs, who="test", classes=["gpu-24gb"])
    assert failed == [1]
    assert seen["wait"] is False and seen["who"] == "test"
    spec = seen["specs"]["0"]
    assert spec["image"].startswith("registry.example/score-blender") and spec["classes"] == ["gpu-24gb"]
    assert spec["kind"] == "blender" and spec["capacity_kind"] == "blender"
    assert spec["kernel_cache"] == "blender-5.0.1" and spec["minutes"] == 3
    paths = sorted(entry["path"] for entry in spec["inputs"])
    assert paths == sorted([str(stage / "place.usda"), str(stage / "textures/wall.png"), str(single)])
    assert out_file.read_text() == "made by 0"
    assert (out_folder / "part" / "a.txt").read_text() == "made by 0"
