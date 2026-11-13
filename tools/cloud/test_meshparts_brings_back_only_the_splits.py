"""meshparts.py's invariants for a share: each take's up/ goes in under its own name and comes back into its own
<take>/down/, the folder `to_split` reads, so a split take is never sent (or paid for) again; only the files the
machine path's bring_back keeps come back (the share's own find(1) line deletes the rest); and a share asked for one
splitter runs only that one.

One share of two takes is run through `cluster_job`'s own line: crate-s1's splitters leave their results beside
scratch files, lamp-s1's leave only scratch; the outputs are brought back as the job maps them and `to_split` is asked
again.

Break that turns it red: drop `! ` from the find line in `cluster_job` (it then deletes the results and keeps the
rest), or map the outputs to `run / take` instead of `run / take / "down"`.
"""
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import meshparts  # noqa: E402

TAKES = ["crate-s1", "lamp-s1"]
RESULTS = ["segvigen_auto.npz", "segvigen_guided.npz", "geosam2.npz", "seg_timing.json", "render.png",
           "result/inference.log"]
SCRATCH = ["mesh.glb", "views/view-01.png", "scratch.npz", "inference.log"]
# What each take's /work/out holds when its splitters end: crate-s1 split, lamp-s1 left only scratch.
MACHINE_OUT = {"crate-s1": RESULTS + SCRATCH, "lamp-s1": SCRATCH}


def files_under(folder):
    """The files below `folder`, as sorted paths relative to it."""
    return sorted(str(path.relative_to(folder)) for path in folder.rglob("*") if path.is_file())


def test_a_share_brings_back_only_its_splits_into_down_and_runs_only_the_splitters_asked(tmp_path):
    run = tmp_path / "run"
    for take in TAKES:
        (run / take / "up").mkdir(parents=True)
        (run / take / "up" / "raw.glb").write_text("glb")
    assert meshparts.to_split(run) == TAKES

    job = meshparts.cluster_job(TAKES, run)
    line = job["command"][2]
    assert [item["path"] for item in job["inputs"]] == ["/work/in/crate-s1", "/work/in/lamp-s1"]
    assert line.index("segvigen-run") < line.index("geosam2-run") < line.index("find /work/out")
    only = meshparts.cluster_job(["crate-s1"], run, ("geosam2",))["command"][2]
    assert "geosam2-run" in only and "segvigen-run" not in only

    machine = tmp_path / "work" / "out"
    for take, names in MACHINE_OUT.items():
        for name in names:
            (machine / take / name).parent.mkdir(parents=True, exist_ok=True)
            (machine / take / name).write_text("x")
    clean = line[line.index("find /work/out"):].replace("/work/out", str(machine))
    subprocess.run(["bash", "-c", clean], check=True)
    for output in job["outputs"]:
        shutil.copytree(machine / pathlib.PurePosixPath(output["path"]).name, output["local"], dirs_exist_ok=True)

    assert files_under(run / "crate-s1" / "down") == sorted(RESULTS)
    assert files_under(run / "lamp-s1" / "down") == []
    assert meshparts.to_split(run) == ["lamp-s1"]
