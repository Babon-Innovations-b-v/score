"""library_bake.py's invariants: a bake's job is rewritten to the machine's paths and every file it names goes up to
exactly those paths (a parts folder's files but its labels; a .gltf with its .bin and its textures), its out folder
comes back to where the job says; Cycles follows the machine (card or cores), the card's kernel cache only on a card;
a piece stands (make_chunky levels its feet) only when its paint levelled its feet; a call's class is fixed at price
time, and no card in stock keeps the first card asked, never a processor machine in its place (owner, 2026-10-20 and
2026-10-23); a failed job names its log's last error (camp's bake, 2026-10-12).

One bake is the world: a job of three pieces (feet levelled, feet skipped, no labels) and a .gltf row, made into its
cluster job on a card and on cores, priced with only a processor machine in stock, and failed with a log.

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

FEET = {"levelled": {"feet": 4, "levelled": [0.0116]}, "skipped": {"skipped": "no floor or held row of its place"},
        "unlabelled": None}


def a_bake(tmp_path):
    """A job of one piece per FEET report, a .gltf row and a picture at a repo path."""
    chunky = []
    for name, feet in FEET.items():
        parts = tmp_path / "parts" / name
        parts.mkdir(parents=True)
        (parts / "part_0.glb").write_text("glb")
        if feet is not None:
            (parts / "labels.json").write_text(json.dumps({"feet": feet}))
        chunky.append({"name": name, "parts": str(parts)})
    model = tmp_path / "models" / "lamp.gltf"
    return {"script": "make_chunky.py", "out": str(tmp_path / "baked"), "chunky": chunky,
            "rows": [{"models": [str(model)]}], "picture": str(library_bake.REPO / "data/library/x.png")}


def offers(classes):
    """Every class asked offered, only the processor machines in stock."""
    return [provider.Offer(0.02, 0, f"{name}-type", "zone-a", 0.02, name, 0,
                           "available" if name.startswith("cpu") else "shortage") for name in classes]


def test_a_library_bake_sends_what_its_job_names(tmp_path, monkeypatch):
    job = a_bake(tmp_path)
    card = library_bake.cluster_job(job, 3, True, tmp_path / "job3.json")
    written = json.loads((tmp_path / "job3.json").read_text())
    cores = library_bake.cluster_job(job, 3, False, tmp_path / "cores3.json")

    pieces = {piece["name"]: piece for piece in written["chunky"]}
    [row] = written["rows"]
    place = pathlib.PurePosixPath(row["models"][0]).parent
    model = pathlib.Path(job["rows"][0]["models"][0])
    expected = {"/root/lib/job3.json": str(tmp_path / "job3.json"),
                **{f"{pieces[name]['parts']}/part_0.glb": str(tmp_path / "parts" / name / "part_0.glb")
                   for name in FEET},
                **{str(place / sent.name): str(sent)
                   for sent in (model, model.with_suffix(".bin"), model.parent / "textures")}}
    assert {entry["path"]: entry["local"] for entry in card["inputs"]} == expected, \
        "a parts folder's files but its labels, a .gltf with its .bin and textures, at the job's paths"
    assert row["models"] == [str(place / "lamp.gltf")]
    assert {name: piece["stands"] for name, piece in pieces.items()} == \
        {"levelled": True, "skipped": False, "unlabelled": False}, "stands only when its paint levelled its feet"
    assert written["picture"] == "/work/repo/data/library/x.png", "repo paths read from the image's checkout"
    assert card["outputs"] == [{"path": written["out"], "local": str(tmp_path / "baked")}]
    words = shlex.split(card["command"][2])
    assert words[:3] == ["mkdir", "-p", written["out"]] and words[-1] == "/root/lib/job3.json"
    assert card["env"] == {"FARM_CYCLES_GPU": "1"} and "kernel_cache" in card
    assert cores["env"] == {"FARM_CYCLES_CPU": "1"} and "kernel_cache" not in cores

    monkeypatch.setattr(library_bake.batch, "offers", offers)
    monkeypatch.setattr(library_bake.batch, "month_spent", lambda account: 0.0)
    found, _, _ = library_bake.price([job], "acct", ["gpu-24gb", "gpu-48gb"])
    assert {offer.machine_class for offer in found} == {"gpu-24gb"}, "no card in stock keeps the first card asked"

    run = tmp_path / "run"
    (run / "library-1").mkdir(parents=True)
    (run / "library-1" / "job3.log").write_text("Error: first\nBlender 5.0.1\nRuntimeError: Error: Cannot read "
                                                "'/gone/x.png'\nBlender quit\n")
    assert library_bake.last_error(run, 3) == "RuntimeError: Error: Cannot read '/gone/x.png'"
    assert library_bake.last_error(run, 4) == "never ran, or its log says no error"
