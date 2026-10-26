"""segment.py's invariant: a picture whose masks came back is never segmented (or paid for) again, whether the masks
came back from a machine or from the cluster. The cluster share's outputs land in <folder>/masks/, the folder
`to_segment` reads, and every picture of the share goes up under its own name.

Break that turns it red: in `cluster_job`, send the outputs to `folder` instead of `folder / "masks"` (the masks then
land beside the pictures and `to_segment` lists them again); or drop the `.exists()` check in `to_segment`.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import segment  # noqa: E402


def bring_back(job, names):
    """What the cluster does with a finished share: every file the job left in its output path lands at `local`."""
    for output in job["outputs"]:
        local = pathlib.Path(output["local"])
        local.mkdir(parents=True, exist_ok=True)
        for name in names:
            (local / name).write_bytes(b"npz")


def test_masks_the_cluster_brought_back_take_their_pictures_off_the_list(tmp_path):
    for name in ("crate", "lamp", "barrel"):
        (tmp_path / f"{name}.png").write_bytes(b"png")
    assert [path.stem for path in segment.to_segment(tmp_path)] == ["barrel", "crate", "lamp"]
    share = [tmp_path / "crate.png", tmp_path / "lamp.png"]
    job = segment.cluster_job(share, tmp_path)
    assert sorted(item["path"] for item in job["inputs"]) == ["/work/in/crate.png", "/work/in/lamp.png"]
    bring_back(job, ["crate.npz", "lamp.npz"])
    assert [path.stem for path in segment.to_segment(tmp_path)] == ["barrel"]
