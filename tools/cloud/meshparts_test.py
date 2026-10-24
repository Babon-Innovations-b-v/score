"""Checks for a meshparts share as a cluster job (SCORE_CLOUD=k8s), without renting anything."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import meshparts  # noqa: E402


def test_a_share_runs_both_splitters_and_keeps_what_comes_back():
    job = meshparts.cluster_job(["crate-s1", "lamp-s1"], pathlib.Path("/run"))
    line = job["command"][2]
    assert line.startswith("mkdir -p /work/out/crate-s1 /work/out/lamp-s1 && segvigen-run ")
    assert line.index("segvigen-run") < line.index("geosam2-run") < line.index("find /work/out")
    assert "-name segvigen_guided.npz" in line and "-path '*/result/inference.log'" in line
    assert job["inputs"][0] == {"local": "/run/crate-s1/up", "path": "/work/in/crate-s1"}
    assert job["outputs"][1] == {"path": "/work/out/lamp-s1", "local": "/run/lamp-s1/down"}
    only = meshparts.cluster_job(["crate-s1"], pathlib.Path("/run"), ("geosam2",))
    assert "segvigen-run" not in only["command"][2] and only["models"] == ["geosam2"]
