"""library_bake.py's invariants: a bake's job is rewritten to the machine's paths and every file it names goes up to
exactly those paths (a parts folder's files but its labels; a .gltf with its .bin and its textures), its out folder
comes back to where the job says; Cycles follows the machine (card or cores), the card's kernel cache only on a card;
a piece stands (make_chunky levels its feet) only when its paint levelled its feet; a call's class is fixed at price
time, and no card in stock keeps the first card asked, never a processor machine in its place (owner, 2026-10-20 and
2026-10-23); a failed job names its log's last error (camp's bake, 2026-10-12).

Break that turns it red: in `files_of` keep labels.json; in `remote_job` drop the .gltf's .bin and textures; in
`stands` drop the `"skipped" not in` test; or in `last_error` take `lines[0]`.
"""
import json
import pathlib
import shlex
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import library_bake  # noqa: E402
import provider  # noqa: E402


def uploaded(job):
    return {entry["path"]: entry["local"] for entry in job["inputs"]}


def test_a_chunky_bake_sends_its_parts_to_the_paths_its_job_file_names(tmp_path):
    parts = tmp_path / "parts" / "crate"
    parts.mkdir(parents=True)
    (parts / "part_0.glb").write_text("glb")
    (parts / "labels.json").write_text(json.dumps({"feet": {"feet": 4, "levelled": [0.01]}}))
    job = {"script": "make_chunky.py", "out": str(tmp_path / "baked"),
           "chunky": [{"name": "crate", "parts": str(parts)}],
           "picture": str(library_bake.REPO / "data/library/x.png")}
    found = library_bake.cluster_job(job, 3, True, tmp_path / "job3.json")
    written = json.loads((tmp_path / "job3.json").read_text())
    piece = written["chunky"][0]
    assert uploaded(found) == {"/root/lib/job3.json": str(tmp_path / "job3.json"),
                               f"{piece['parts']}/part_0.glb": str(parts / "part_0.glb")}
    assert piece["stands"] is True
    assert written["picture"] == "/work/repo/data/library/x.png", "repo paths read from the image's checkout"
    assert found["outputs"] == [{"path": written["out"], "local": str(tmp_path / "baked")}]
    words = shlex.split(found["command"][2])
    assert words[:3] == ["mkdir", "-p", written["out"]] and words[-1] == "/root/lib/job3.json"


def test_a_gltf_row_goes_up_with_its_bin_and_its_textures(tmp_path):
    model = tmp_path / "models" / "lamp.gltf"
    model.parent.mkdir()
    job = {"script": "rows.py", "out": str(tmp_path / "out"), "rows": [{"models": [str(model)]}]}
    moved, sends = library_bake.remote_job(job, 1)
    [(files, place)] = sends
    assert set(files) == {model, model.with_suffix(".bin"), model.parent / "textures"}
    assert moved["rows"][0]["models"] == [str(place / "lamp.gltf")]


def test_cycles_follows_the_machine():
    job = {"script": "make_chunky.py", "out": "/tmp/out"}
    card = library_bake.cluster_job(job, 0, True, pathlib.Path("/dev/null"))
    cores = library_bake.cluster_job(job, 0, False, pathlib.Path("/dev/null"))
    assert card["env"] == {"FARM_CYCLES_GPU": "1"} and "kernel_cache" in card
    assert cores["env"] == {"FARM_CYCLES_CPU": "1"} and "kernel_cache" not in cores


def test_a_piece_stands_only_when_its_paint_levelled_its_feet(tmp_path):
    assert not library_bake.stands(tmp_path), "no labels: no feet report"
    (tmp_path / "labels.json").write_text(json.dumps({"feet": {"feet": 5, "levelled": [0.0116]}}))
    assert library_bake.stands(tmp_path)
    (tmp_path / "labels.json").write_text(json.dumps({"feet": {"skipped": "no floor or held row of its place"}}))
    assert not library_bake.stands(tmp_path)


def test_no_card_in_stock_waits_for_a_card_never_a_processor_machine(monkeypatch):
    def offers(classes):
        return [provider.Offer(0.02, 0, f"{name}-type", "zone-a", 0.02, name, 0,
                               "available" if name.startswith("cpu") else "shortage") for name in classes]
    monkeypatch.setattr(library_bake.batch, "offers", offers)
    monkeypatch.setattr(library_bake.batch, "month_spent", lambda account: 0.0)
    found, _, _ = library_bake.price([{"materials": [1]}], "acct", ["gpu-24gb", "gpu-48gb"])
    assert {offer.machine_class for offer in found} == {"gpu-24gb"}


def test_a_failed_job_names_its_last_error(tmp_path):
    (tmp_path / "library-1").mkdir()
    (tmp_path / "library-1" / "job6.log").write_text("Error: first\nBlender 5.0.1\nRuntimeError: Error: Cannot read "
                                                     "'/gone/x.png'\nBlender quit\n")
    assert library_bake.last_error(tmp_path, 6) == "RuntimeError: Error: Cannot read '/gone/x.png'"
    assert library_bake.last_error(tmp_path, 7) == "never ran, or its log says no error"
