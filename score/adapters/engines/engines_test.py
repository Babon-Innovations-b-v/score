"""A Blender job runs the pinned image headless, and the machine path never starts for a node the compute adapter
refuses. No machine is rented: the machine runner's run_elsewhere is replaced by a recorder.

Run: .venv/bin/python score/adapters/engines/engines_test.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import graph  # noqa: E402
from score.adapters import compute, engines  # noqa: E402
from score.store import Store  # noqa: E402

STARTED = []


def make_nothing(inputs, out, seed, params):
    raise AssertionError("not made in this test")


RENDER = graph.Stage("render", "place", make_nothing, paid=True)


def test_a_blender_job_runs_the_pinned_image_headless():
    spec = engines.blender_job("tools/blender/inside/warm_kernels.py", ["/work/out.json"], [], "code/x.tar.gz", 5)
    assert spec["image"] == compute.job_contract.image("blender") and "@sha256:" in spec["image"]
    assert spec["command"][:3] == [engines.BLENDER, "-b", "-setaudio"] and spec["command"][-2:] == ["--",
                                                                                                    "/work/out.json"]


def test_the_machine_path_starts_only_for_a_cleared_node():
    runner = graph.Runner([RENDER], graph.World("toy", 1, {}), Store.in_folder(tempfile.mkdtemp()))
    blender_cloud = engines.machine_runner()
    real = blender_cloud.run_elsewhere
    blender_cloud.run_elsewhere = lambda *arguments: STARTED.append(arguments)
    try:
        try:
            engines.blender_on_machines(runner, "render@hangar", "s.py", [], [], [], ["cpu-32c-128gb"], 5)
        except compute.Refused as refusal:
            assert "has not said yes" in str(refusal)
        assert STARTED == []
        key = runner.ticket("render@hangar")["key"]
        runner.store.write_spend_yes("render@hangar", key, {"euros": 0.5, "at": graph.now()})
        engines.blender_on_machines(runner, "render@hangar", "s.py", [], [], [], ["cpu-32c-128gb"], 5)
        assert STARTED == [("s.py", [], [], [], ["cpu-32c-128gb"], f"render@hangar {key[:12]}", 5)]
    finally:
        blender_cloud.run_elsewhere = real


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
