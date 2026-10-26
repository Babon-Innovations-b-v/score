"""meshparts.py's invariants for a share: each take's up/ goes in under its own name and comes back into its own
<take>/down/, the folder `to_split` reads, so a split take is never sent (or paid for) again; only the files the
machine path's bring_back keeps come back (the share's own find(1) line deletes the rest); and a share asked for one
splitter runs only that one.

Break that turns it red: drop `! ` from the find line in `cluster_job` (it then deletes the results and keeps the
rest), or map the outputs to `run / take` instead of `run / take / "down"`.
"""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import meshparts  # noqa: E402


def test_the_shares_clean_up_keeps_exactly_what_bring_back_keeps(tmp_path):
    out = tmp_path / "work" / "out" / "crate-s1"
    kept = ["segvigen_auto.npz", "segvigen_guided.npz", "geosam2.npz", "seg_timing.json", "render.png",
            "result/inference.log"]
    dropped = ["mesh.glb", "views/view-01.png", "scratch.npz", "inference.log"]
    for name in kept + dropped:
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_text("x")
    line = meshparts.cluster_job(["crate-s1"], tmp_path)["command"][2]
    clean = line[line.index("find /work/out"):].replace("/work/out", str(tmp_path / "work" / "out"))
    subprocess.run(["bash", "-c", clean], check=True)
    left = sorted(str(path.relative_to(out)) for path in out.rglob("*") if path.is_file())
    assert left == sorted(kept)


def test_a_take_whose_splits_came_back_is_not_split_again(tmp_path):
    for take in ("crate-s1", "lamp-s1"):
        (tmp_path / take / "up").mkdir(parents=True)
        (tmp_path / take / "up" / "raw.glb").write_text("glb")
    assert meshparts.to_split(tmp_path) == ["crate-s1", "lamp-s1"]
    job = meshparts.cluster_job(["crate-s1", "lamp-s1"], tmp_path)
    assert [item["path"] for item in job["inputs"]] == ["/work/in/crate-s1", "/work/in/lamp-s1"]
    crate = pathlib.Path(next(output["local"] for output in job["outputs"] if output["path"] == "/work/out/crate-s1"))
    crate.mkdir(parents=True)
    for name in ("segvigen_auto.npz", "segvigen_guided.npz", "geosam2.npz"):
        (crate / name).write_text("npz")
    assert meshparts.to_split(tmp_path) == ["lamp-s1"]


def test_a_share_asked_for_one_splitter_runs_only_that_one(tmp_path):
    only = meshparts.cluster_job(["crate-s1"], tmp_path, ("geosam2",))
    assert "geosam2-run" in only["command"][2] and "segvigen-run" not in only["command"][2]
    both = meshparts.cluster_job(["crate-s1"], tmp_path)["command"][2]
    assert both.index("segvigen-run") < both.index("geosam2-run") < both.index("find /work/out")
