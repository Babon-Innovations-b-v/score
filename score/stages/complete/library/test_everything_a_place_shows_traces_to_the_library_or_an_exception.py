"""Invariant: everything a place shows traces to the library or to a written exception. The known-bad fixture (a
picture's own texture, a default grey, a model no entry holds) fails on exactly those three, the known-good one passes;
each way of tracing holds (score:library, a surface by name, the gltf, the prim an entry names through a variant, an
effect's placements, the content hash, the finish record); a withdrawn entry traces nothing; the library comes only
from SCORE_LIB_ROOT; exceptions refuse without a reason or an owner and end at their expiry; findings group one kind
of piece into one problem. The library is a temp folder written here (no entry data is kept in this repository).

Breaks that turn this red (each applied once and seen red, then reverted):
- trace.BUILT_KINDS: the structure alone -> the night's moon light, built by night_sky, traces to nothing
- trace.thing_kind: a look (a Material) with a reference taken for a model -> the place_build scene's chair look,
  referencing its surface's material.usda, reads as a model no entry holds
- trace.judged: an untraced row answers LIBRARY -> test_the_known_bad_fixture_fails_on_its_texture_its_grey_and_its_model
- trace.traced_finish: the surface-by-name branch dropped -> test_the_known_good_fixture_passes_and_a_guide_mesh_is_not_a_finish
- trace.traced_finish: the finish record not read (`node = None`) -> test_a_finish_record_traces_a_baked_models_finish
- trace.traced_finish: an entry's finish record not read (`entry = None`), or a surface by address not read ->
  test_a_finish_record_traces_a_baked_models_finish (a place_build scene's painted console, or its chair's look)
- entries.Shelf.newest: an address with no version not read -> test_a_finish_record_traces_a_baked_models_finish
  (its hull's kit)
- trace.laid_character: `[]` always -> test_a_finish_record_traces_a_baked_models_finish (the player model's paint
  a finding under its exception)
- trace.traced_source: the content-hash loop dropped -> test_a_model_traces_by_the_content_hash_of_its_file
- entries.unvarianted: the variant selection kept -> test_an_effect_traces_by_the_prim_its_entry_names_through_a_variant
- trace.traced_source: the score:from algorithm branch dropped -> test_an_effect_traces_by_the_prim_its_entry_names_through_a_variant
  (a wall kit piece no longer traces to its algorithm entry)
- entries.prim_paths: the placements not read -> test_an_effect_one_entry_holds_for_every_spot_traces_by_its_placements
- entries.read: withdrawn entries shelved too -> test_a_withdrawn_entry_traces_nothing
- trace.rows: a character's poses not read (no pose_rows) -> test_a_withdrawn_entry_traces_nothing (the smoker's held
  pose has no row)
- entries.from_environment: the repository's default library when unset -> test_the_library_comes_only_from_score_lib_root
- exceptions.checked: `missing = []` -> test_an_exception_without_its_reason_or_owner_is_refused
- exceptions.in_force: always True -> test_an_exception_covers_its_prims_until_it_expires
- data/checks/library-exceptions.json: an entry with no `why` -> test_the_repositorys_exceptions_file_reads (a check
  on the owner's data, not the code)
- findings.grouped: grouped by prim, not by group -> test_findings_group_one_kind_of_piece_into_one_problem
"""
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


PLACED = """def Xform "fixture"
{
    def Scope "Objects"
    {
        def Mesh "console" (prepend apiSchemas = ["MaterialBindingAPI"])
        {
            custom string score:library = "model/console@1"
            rel material:binding = </fixture/Objects/console/paint>
            def Material "paint" {}
        }
        def Mesh "chair" (prepend apiSchemas = ["MaterialBindingAPI"])
        {
            custom string score:library = "model/chair@1"
            rel material:binding = </fixture/Looks/chair>
        }
        def Mesh "pilot" (prepend apiSchemas = ["MaterialBindingAPI"])
        {
            custom string score:kind = "character"
            custom string score:library = "character/pilot@1"
            rel material:binding = </fixture/Objects/pilot/dress>
            def Material "dress" {}
        }
        def Mesh "hull" (prepend apiSchemas = ["MaterialBindingAPI"])
        {
            custom string score:library = "kit/fixture"
            rel material:binding = </fixture/Looks/chair>
        }
    }
    def Scope "Looks"
    {
        def Material "chair" (prepend references = @./surface/deck/1/material.usda@)
        {
            custom string score:surface = "surface/deck@1"
        }
    }
}
"""
PLAYER = {"place": "*", "prim": "/*/Characters/*", "aspect": "finish", "what": "a player model's own texture",
          "why": "repainting loses its seams", "allowed_by": "@owner", "allowed_on": "2026-10-18"}


def test_a_finish_record_traces_a_baked_models_finish(tmp_path):
    rows = judged_fixture("bad.usda", library(tmp_path), baked={"0" * 64: "surfaces-bake@fixture"})
    textured = [row for row in rows if row.get("material", "") and row["material"].endswith("/picture")]
    assert textured[0]["answer"] == trace.LIBRARY and textured[0]["by"] == "surfaces-bake@fixture"
    # A place_build scene: a model the surface line painted traces by its entry's record, one it did not is a
    # finding; a look names its surface by address; a code-built piece names its kit with no version; a character
    # laid in Objects keeps its own paint only under the player models' exception.
    painted = {"made_with": [{"by": "score", "what": "console: painted from the library surfaces and baked"}]}
    for kind, entry_id, provenance in (("model", "console", painted), ("model", "chair", None),
                                       ("character", "pilot", None)):
        entry(tmp_path / "lib", kind, entry_id, provenance=provenance)
    shelf = library(tmp_path / "lib")
    stage = stage_with(tmp_path, PLACED)
    for excepted, pilot in (([PLAYER], trace.EXCEPTION), ([], trace.NEITHER)):
        rows = trace.rows(stage, trace.Context(place="fixture", shelf=shelf, exceptions=excepted, today=TODAY))
        answers = {(row["prim"].rsplit("/", 1)[1], row["aspect"]): row["answer"] for row in rows}
        assert answers == {**{(name, aspect): trace.LIBRARY for name in ("console", "chair", "pilot", "hull")
                              for aspect in ("source", "finish")}, ("pilot", "finish"): pilot}, rows
    entry(tmp_path / "lib2", "model", "console")
    rows = trace.rows(stage, trace.Context(place="fixture", shelf=library(tmp_path / "lib2"), today=TODAY))
    assert [row["answer"] for row in rows if row["prim"].endswith("console") and row["aspect"] == "finish"] \
        == [trace.NEITHER], rows


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
    # a code-built structure piece traces to the algorithm entry its score:from names, and to nothing when none is held
    kit_folder = tmp_path / "kit"
    kit_folder.mkdir()
    kit = ('def Xform "fixture"\n{\n    def Mesh "kit_frames_wall_1"\n    {\n        custom string score:kind = '
           '"structure"\n        custom string score:from = "the frames of wall_1 (wall_kit.frames)"\n    }\n}\n')
    sources = [(row["kind"], row["by"]) for row in trace.rows(stage_with(kit_folder, kit), trace.Context(
        place="fixture", shelf=entries.read(root))) if row["aspect"] == "source"]
    assert sources == [("structure", None)], sources
    entry(root, "algorithm", "wall_kit")
    sources = [(row["kind"], row["by"]) for row in trace.rows(stage_with(kit_folder, kit), trace.Context(
        place="fixture", shelf=entries.read(root))) if row["aspect"] == "source"]
    assert sources == [("structure", "algorithm/wall_kit@1")], sources
    # a night's moon light the night algorithm built traces to it as a structure piece does
    night_folder = tmp_path / "night"
    night_folder.mkdir()
    entry(root, "algorithm", "night_sky")
    night = ('def Xform "fixture"\n{\n    def Scope "Lights"\n    {\n        def DistantLight "moon"\n        {\n'
             '            custom string score:from = "the night\'s physics (night_sky.night)"\n        }\n    }\n}\n')
    sources = [(row["kind"], row["by"]) for row in trace.rows(stage_with(night_folder, night), trace.Context(
        place="fixture", shelf=entries.read(root))) if row["aspect"] == "source"]
    assert sources == [("light", "algorithm/night_sky@1")], sources


def test_an_effect_one_entry_holds_for_every_spot_traces_by_its_placements(tmp_path):
    root = tmp_path / "lib"
    entry(root, "effect", "drift", provenance={"place": "other", "prim": "/other/Effects/drift_0_0", "placements": [
        {"place": "other", "prim": "/other/Effects/drift_0_0"},
        {"place": "fixture", "prim": "/fixture/Effects{weather=calm}drift_1_1"}]})
    stage = stage_with(tmp_path, 'def Xform "fixture"\n{\n    def Scope "Effects"\n    {\n        def Xform "drift_1_1"\n'
                                 '        {\n            custom string score:effect:kind = "dust"\n        }\n    }\n}\n')
    rows = trace.rows(stage, trace.Context(place="fixture", shelf=entries.read(root)))
    assert [(row["kind"], row["by"]) for row in rows] == [("effect", "effect/drift@1")]


def test_a_withdrawn_entry_traces_nothing(tmp_path):
    entry(tmp_path, "surface", "bare_steel", state="withdrawn")
    assert entries.read(tmp_path).surface("bare_steel", "fixture") is None
    entry(tmp_path, "character", "body")
    entry(tmp_path, "character", "hold")
    entry(tmp_path, "character", "old_hold", state="withdrawn")
    smokers = "".join(f'        def SkelRoot "{name}"\n        {{\n            custom string score:kind = "character"\n'
                      f'            custom string score:library = "character/body@1"\n'
                      f'            def SkelAnimation "Held"\n            {{\n'
                      f'                custom string score:pose = "character/{pose}@1"\n            }}\n        }}\n'
                      for name, pose in (("smoker", "hold"), ("stale", "old_hold")))
    stage = stage_with(tmp_path, f'def Xform "fixture"\n{{\n    def Scope "Objects"\n    {{\n{smokers}    }}\n}}\n')
    rows = trace.rows(stage, trace.Context(place="fixture", shelf=entries.read(tmp_path)))
    assert [(row["prim"], row["by"]) for row in rows] == [
        ("/fixture/Objects/smoker", "character/body@1"), ("/fixture/Objects/smoker/Held", "character/hold@1"),
        ("/fixture/Objects/stale", "character/body@1"), ("/fixture/Objects/stale/Held", None)]


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
    crate = ('        def Xform "crate_{n}"\n        {{\n            custom string score:kind = "fixture_crate"\n'
             '            custom string score:model = "crate"\n            def Mesh "geo"\n            {{\n                int[] faceVertexCounts = [3]\n'
             '                int[] faceVertexIndices = [0, 1, 2]\n'
             '                point3f[] points = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]\n            }}\n        }}\n')
    stage = stage_with(tmp_path, 'def Xform "fixture"\n{\n    def Xform "Objects"\n    {\n'
                       + crate.format(n=1) + crate.format(n=2) + '    }\n}\n')
    rows = trace.rows(stage, trace.Context(place="fixture", shelf=library(tmp_path / "lib"), today=TODAY))
    # two grey crates of one kind: two problems (their source, their finish), each counting both crates
    assert sorted((item["aspect"], item["group"], item["count"]) for item in findings.grouped(rows)) == [
        ("finish", "fixture_crate: no material", 2), ("source", "fixture_crate", 2)]
