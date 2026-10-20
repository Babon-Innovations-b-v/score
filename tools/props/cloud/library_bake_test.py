"""Checks for a library bake as a cluster job (SCORE_CLOUD=k8s), without renting anything: its job file and inputs at
the machine's paths, its out folder back where the job says, Cycles on the card or the cores."""
import json
import pathlib
import shlex
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import library_bake  # noqa: E402


def test_no_card_in_stock_is_a_hole_never_a_processor_machine(monkeypatch):
    """A batch's class is fixed at price time (CONTEXT.md, owner 2026-10-20): --processor rented a 32-core processor
    machine when no card was in stock, and the claims moved between classes as stock moved."""
    import provider

    def offers(classes):
        return [provider.Offer(0.02, 0, f"{name}-type", "zone-a", 0.02, name, 0,
                               "available" if name.startswith("cpu") else "shortage") for name in classes]
    monkeypatch.setattr(library_bake.batch, "offers", offers)
    try:
        library_bake.price([{"materials": [1]}], "acct", ["gpu-24gb", "gpu-48gb"])
    except SystemExit as refused:
        assert "the jobs are holes" in str(refused)
    else:
        raise AssertionError("a bake with no card in stock was priced")
    assert not hasattr(library_bake, "PROCESSORS")


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
    assert written["chunky"][0]["stands"] is False, "no feet report: its paint levelled nothing"
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


def test_a_failed_job_names_its_last_error(tmp_path):
    (tmp_path / "library-1").mkdir()
    (tmp_path / "library-1" / "job6.log").write_text("Blender 5.0.1\nRuntimeError: Error: Cannot read '/gone/x.png'\n"
                                                     "Blender quit\n")
    assert library_bake.last_error(tmp_path, 6) == "RuntimeError: Error: Cannot read '/gone/x.png'"
    assert library_bake.last_error(tmp_path, 7) == "never ran, or its log says no error"


def test_a_piece_whose_paint_levelled_its_feet_stands_and_one_skipped_does_not(tmp_path):
    """The hangar's ship (feet levelled in its paint) has its cut-down copy levelled up there (make_chunky
    levelled_feet); a hung or mounted piece's paint skipped its feet and is left as made."""
    (tmp_path / "labels.json").write_text(json.dumps({"feet": {"feet": 5, "levelled": [0.0116]}}))
    assert library_bake.stands(tmp_path)
    (tmp_path / "labels.json").write_text(json.dumps({"feet": {"skipped": "no floor or held row of its place"}}))
    assert not library_bake.stands(tmp_path)
