"""Checks for a library bake as a cluster job (SCORE_CLOUD=k8s), without renting anything: its job file and inputs at
the machine's paths, its out folder back where the job says, Cycles on the card or the cores."""
import json
import pathlib
import shlex
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import library_bake  # noqa: E402


def test_a_bake_keeps_the_machines_paths(tmp_path):
    parts = tmp_path / "parts" / "crate"
    parts.mkdir(parents=True)
    (parts / "part_0.glb").write_text("glb")
    (parts / "labels.json").write_text("{}")
    job = {"script": "make_chunky.py", "out": str(tmp_path / "baked"),
           "chunky": [{"name": "crate", "parts": str(parts)}],
           "picture": str(library_bake.REPO / "data/library/x.png")}
    found = library_bake.cluster_job(job, 3, True, tmp_path / "job3.json")
    written = json.loads((tmp_path / "job3.json").read_text())
    assert written["out"] == "/root/lib/out/3" and written["chunky"][0]["parts"] == "/root/lib/in/3/crate"
    assert written["picture"] == "/work/repo/data/library/x.png"
    places = {entry["path"] for entry in found["inputs"]}
    assert places == {"/root/lib/job3.json", "/root/lib/in/3/crate/part_0.glb"}
    assert found["outputs"] == [{"path": "/root/lib/out/3", "local": str(tmp_path / "baked")}]
    words = shlex.split(found["command"][2])
    assert words[:3] == ["mkdir", "-p", "/root/lib/out/3"] and words[-1] == "/root/lib/job3.json"
    assert "tools/props/library/inside/make_chunky.py" in words
    assert found["env"] == {"FARM_CYCLES_GPU": "1"} and found["kernel_cache"] == "blender-5.0.1"
    processor = library_bake.cluster_job(job, 3, False, tmp_path / "job3.json")
    assert processor["env"] == {"FARM_CYCLES_CPU": "1"} and "kernel_cache" not in processor
