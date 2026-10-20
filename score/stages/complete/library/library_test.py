"""The library check: the known-bad fixture (a picture's own texture, a default grey, a model no entry holds) fails,
the known-good one passes; each way of tracing (score:library, a surface by name, the gltf, the prim an entry names
through a variant, the content hash, the finish record); exceptions refuse without a reason or an owner and end at
their expiry; a withdrawn entry traces nothing. The library is a temp folder written here (no entry data is kept in
this repository)."""
import datetime
import hashlib
import json
import os
import pathlib

import pytest
from pxr import Usd

from score.stages.complete.library import entries, exceptions, findings, trace

REPO = pathlib.Path(__file__).resolve().parents[4]
FIXTURES = REPO / "data/checks/library"
TODAY = datetime.date(2026, 10, 18)


def entry(root, kind, entry_id, files=None, provenance=None, state="draft"):
    """Write one entry.json of the temp library."""
    folder = root / "entries" / kind / entry_id / "1"
    folder.mkdir(parents=True, exist_ok=True)
    record = {"schema": "score-lib-entry/1", "address": f"{kind}/{entry_id}@1", "kind": kind, "id": entry_id, "version": 1, "state": state,
              "files": files or {}, "provenance": provenance or {}}
    (folder / "entry.json").write_text(json.dumps(record))


def library(root, *more):
    """A temp library with the surfaces and entries the good fixture names, and any more given."""
    for kind, entry_id in (("surface", "bare_steel"), ("surface", "deck"), ("model", "crate_1"), ("kit", "fixture"),
                           ("light", "lamp"), ("sound", "hum"), *more):
        entry(root, kind, entry_id)
    return entries.read(root)


def judged_fixture(name, shelf, **given):
    stage = Usd.Stage.Open(str(FIXTURES / name))
    return trace.rows(stage, trace.Context(place="fixture", shelf=shelf, today=TODAY, **given))


def neither(rows):
    return [row for row in rows if row["answer"] == trace.NEITHER]


def test_the_known_bad_fixture_fails_on_its_texture_its_grey_and_its_model(tmp_path):
    rows = judged_fixture("bad.usda", library(tmp_path))
    said = [row["instead"] for row in neither(rows)]
    assert any("photo_of_a_crate.png" in words for words in said)
    assert trace.DEFAULT_GREY in said
    assert any(row["aspect"] == "source" and row["prim"] == "/fixture/Objects/crate_1" for row in neither(rows))
    assert findings.answer(findings.counts(rows)) == "fail"


def test_the_known_good_fixture_passes_and_a_guide_mesh_is_not_a_finish(tmp_path):
    rows = judged_fixture("good.usda", library(tmp_path))
    assert not neither(rows), neither(rows)
    assert findings.answer(findings.counts(rows)) == "pass"
    kinds = sorted({(row["aspect"], row["kind"]) for row in rows})
    assert kinds == [("finish", "model"), ("finish", "structure"), ("source", "light"), ("source", "model"),
                     ("source", "sound"), ("source", "structure")]
    assert [row["parts"] for row in rows if row["aspect"] == "finish" and row["kind"] == "model"] == [1]


def test_a_finish_record_traces_a_baked_models_finish(tmp_path):
    rows = judged_fixture("bad.usda", library(tmp_path), baked={"0" * 64: "surfaces-bake@fixture"})
    textured = [row for row in rows if row.get("material", "") and row["material"].endswith("/picture")]
    assert textured[0]["answer"] == trace.LIBRARY and textured[0]["by"] == "surfaces-bake@fixture"


def stage_with(folder, text):
    path = folder / "fixture.usda"
    path.write_text("#usda 1.0\n(\n    defaultPrim = \"fixture\"\n)\n" + text)
    return Usd.Stage.Open(str(path))


def test_a_model_traces_by_the_content_hash_of_its_file(tmp_path):
    blobs = tmp_path / "blobs"
    blobs.mkdir()
    model = b"#usda 1.0\n(\n    defaultPrim = \"m\"\n)\ndef Xform \"m\"\n{\n}\n"
    sha = hashlib.sha256(model).hexdigest()
    (blobs / sha).write_bytes(model)
    (tmp_path / "assets").mkdir()
    os.symlink(blobs / sha, tmp_path / "assets/m.usda")
    library(tmp_path / "lib")
    entry(tmp_path / "lib", "model", "m", files={"model.usda": {"sha256": sha}})
    shelf = entries.read(tmp_path / "lib")
    stage = stage_with(tmp_path, 'def Xform "fixture"\n{\n    def Xform "m_1" (\n        prepend references = '
                                 '@./assets/m.usda@\n    )\n    {\n    }\n}\n')
    rows = trace.rows(stage, trace.Context(place="fixture", shelf=shelf, blobs=os.path.realpath(blobs)))
    assert [(row["by"], row["how"]) for row in rows] == [("model/m@1", "the content hash of a file it is made of")]


def test_an_effect_traces_by_the_prim_its_entry_names_through_a_variant(tmp_path):
    root = tmp_path / "lib"
    entry(root, "effect", "dust", provenance={"place": "fixture", "prim": "/fixture/Effects{weather=storm}dust"})
    stage = stage_with(tmp_path, 'def Xform "fixture"\n{\n    def Scope "Effects"\n    {\n        def Xform "dust"\n'
                                 '        {\n            custom string score:effect:kind = "dust"\n        }\n    }\n}\n')
    rows = trace.rows(stage, trace.Context(place="fixture", shelf=entries.read(root)))
    assert [(row["kind"], row["by"]) for row in rows] == [("effect", "effect/dust@1")]


def test_a_withdrawn_entry_traces_nothing(tmp_path):
    entry(tmp_path, "surface", "bare_steel", state="withdrawn")
    assert entries.read(tmp_path).surface("bare_steel", "fixture") is None


def test_the_library_comes_only_from_score_lib_root(tmp_path, monkeypatch):
    monkeypatch.delenv("SCORE_LIB_ROOT", raising=False)
    assert entries.from_environment() is None
    library(tmp_path)
    monkeypatch.setenv("SCORE_LIB_ROOT", str(tmp_path))
    assert entries.from_environment().has("surface/deck@1")


def written(folder, *listed):
    path = folder / "exceptions.json"
    path.write_text(json.dumps({"exceptions": list(listed)}))
    return path


ALLOWED = {"place": "fixture", "prim": "/fixture/Objects/*", "aspect": "both", "what": "a crate from a photo",
           "why": "kept until its library model is made", "allowed_by": "@JoeyKardolus", "allowed_on": "2026-10-18"}


@pytest.mark.parametrize("left_out", ["why", "allowed_by", "allowed_on", "what"])
def test_an_exception_without_its_reason_or_owner_is_refused(tmp_path, left_out):
    with pytest.raises(exceptions.Refused, match=left_out):
        exceptions.read(written(tmp_path, dict(ALLOWED, **{left_out: ""})))


def test_an_exception_covers_its_prims_until_it_expires(tmp_path):
    shelf = library(tmp_path / "lib")
    standing = exceptions.read(written(tmp_path, ALLOWED))
    rows = judged_fixture("bad.usda", shelf, exceptions=standing)
    assert not neither(rows) and {row["answer"] for row in rows} == {trace.EXCEPTION}
    ended = exceptions.read(written(tmp_path, dict(ALLOWED, expires="2026-10-17")))
    assert neither(judged_fixture("bad.usda", shelf, exceptions=ended))


def test_the_repositorys_exceptions_file_reads():
    assert isinstance(exceptions.read(), list)


def test_findings_group_one_kind_of_piece_into_one_problem(tmp_path):
    rows = judged_fixture("bad.usda", library(tmp_path))
    grouped = findings.grouped(rows)
    assert len(grouped) == len({(row["aspect"], row["group"]) for row in neither(rows)})
    assert all(item["sentence"] and item["prims"] for item in grouped)
