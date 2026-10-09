"""Checks for a SAM 2.1 share as a cluster job (SCORE_CLOUD=k8s), without renting anything."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import segment  # noqa: E402


def test_a_share_comes_back_as_the_folders_masks(tmp_path):
    picture = tmp_path / "crate.png"
    picture.write_text("png")
    job = segment.cluster_job([picture], tmp_path)
    assert job["command"] == ["sam-run", "tools/props/cloud/segment_worker.py", segment.WEIGHTS, "/work/in",
                              "/work/out"]
    assert job["inputs"] == [{"local": str(picture), "path": "/work/in/crate.png"}]
    assert job["outputs"] == [{"path": "/work/out", "local": str(tmp_path / "masks")}]
    assert job["models"] == ["sam2.1-hiera-large"]
