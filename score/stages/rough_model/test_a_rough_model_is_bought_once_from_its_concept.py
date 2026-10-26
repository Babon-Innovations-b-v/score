"""A place's rough model is bought once from its concept: every place with a kept plan has the row, reading its
design's concept and inventory; the make sends the concept to the batch once and keeps the finished model (a take
already back is finished, never sent again; the finish runs on a rented machine); its gates pass a model made from
the concept read and measure it, and fail one from another concept or a file that is no model. No spend, no model
made: a stand-in batch and finish, a one-triangle binary glTF measured by hand (2 x 3 x 1, one triangle).

Each test names the break that turns it red (`Break: <file>: `old` -> `new``); each was applied once and seen red.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest
    score/stages/rough_model/test_a_rough_model_is_bought_once_from_its_concept.py
"""
import hashlib
import json
import pathlib
import struct
import subprocess
import sys
import types

import pytest

from score import checks, stages
from score.stages import rough_model, scene_record
import score.stages.rough_model._cloud as cloud
import score.stages.props.prop_data as prop_data
from score.stages.surfaces import surface_data

import score.stages.surfaces  # noqa: E402


@pytest.fixture(autouse=True)
def no_design(tmp_path, monkeypatch):
    """No designed place's hand-in is read unless a test writes one (the home's design/, which the sandbox links)."""
    nowhere = tmp_path / "no design"
    monkeypatch.setattr(prop_data, "DESIGN", nowhere)
    monkeypatch.setattr(surface_data, "DESIGN", nowhere)
    monkeypatch.setattr(score.stages.surfaces.data, "DESIGN", nowhere)  # the table's own import of it

REPO = pathlib.Path(__file__).resolve().parents[3]


def glb(path, positions=((0, 0, 0), (2, 0, 0), (0, 3, 1))):
    """A binary glTF of one triangle primitive (positions only), written to `path`."""
    data = b"".join(struct.pack("<3f", *point) for point in positions)
    low = [min(point[axis] for point in positions) for axis in range(3)]
    high = [max(point[axis] for point in positions) for axis in range(3)]
    gltf = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(data)}],
            "bufferViews": [{"buffer": 0, "byteLength": len(data)}],
            "accessors": [{"bufferView": 0, "componentType": 5126, "count": len(positions), "type": "VEC3",
                           "min": low, "max": high}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}]}
    text = json.dumps(gltf).encode()
    text += b" " * (-len(text) % 4)
    body = struct.pack("<II", len(text), 0x4E4F534A) + text + struct.pack("<II", len(data), 0x004E4942) + data
    path.write_bytes(b"glTF" + struct.pack("<II", 2, 12 + len(body)) + body)
    return path


def plan_output(folder, place):
    (folder / "plan.json").parent.mkdir(parents=True, exist_ok=True)
    (folder / "plan.json").write_text(json.dumps({"place": place}))
    return folder


@pytest.fixture
def made(tmp_path, monkeypatch):
    """(output, inputs, calls) of a make through a stand-in batch that brings one take back into a work folder of
    the test's own."""
    work, calls = tmp_path / "pixal", []
    work.mkdir()
    monkeypatch.setattr(rough_model, "take_files",
                        lambda take: (work / f"{take}.glb", work / f"{take}-final.glb"))

    def batch(take, picture, place, inventory, out):
        calls.append((take, pathlib.Path(picture).name, place, inventory))
        glb(work / f"{take}.glb")
        glb(work / f"{take}-final.glb")
    monkeypatch.setattr(rough_model, "dispatch", batch)
    concept = tmp_path / "K02.png"
    concept.write_bytes(b"a concept picture")
    inputs = {"plan": plan_output(tmp_path / "plan", "airlock"), "concept": concept,
              "inventory": tmp_path / "airlock.json"}
    out = tmp_path / "out"
    out.mkdir()
    rough_model.make(inputs, out, 1, {})
    return out, inputs, calls


def verdicts(output, inputs):
    return {check.name: checks.judge(check, output, inputs, None) for check in rough_model.CHECKS}


def kept_plans(folder, monkeypatch, places):
    """scene_record.KEPT and plans.KEPT pointed at `folder` of kept plans, each with its leads, for `places` (the old
    filed plans were retired, 2026-10-21: a place has a plan row by its kept plan alone)."""
    from score.review import plans
    folder.mkdir()
    for place in places:
        (folder / f"{place}.json").write_text(json.dumps({"leads": {}}))
    monkeypatch.setattr(scene_record, "KEPT", folder)
    monkeypatch.setattr(plans, "KEPT", folder)


def test_every_place_with_a_plan_has_a_rough_model_node_shell_or_inside_alike(tmp_path, monkeypatch):
    """The base (a shell) and the airlock (inside) both have kept plans and a rough-model node; nowhere has none.
    Break: score/stages/scene_record/__init__.py: `return path.exists() and "leads" in json.loads(path.read_text())`
        -> `return False`"""
    kept_plans(tmp_path / "kept", monkeypatch, ["base", "airlock"])
    runner = stages.runner()
    with_node = {place for stage, place in runner.nodes(["base", "airlock", "nowhere"]) if stage.name == "rough-model"}
    assert with_node == {"base", "airlock"}, with_node


def test_a_place_reads_its_design_s_concept_and_inventory(tmp_path, monkeypatch):
    """A designed place's rough model reads its picked concept and its hand-in (the scene inventory the batch builds
    from); one with no hand-in its kept inventory, and no concept: its make refuses it by name. No place reads the
    concept views, whose requests name no place they are the concept of.
    Break: score/stages/__init__.py: `return {**found, "concept": "{home}/design/concepts/" + f"{place}.png",
        "inventory": prop_data.keyed(place)}` -> `return found`"""
    kept_plans(tmp_path / "kept", monkeypatch, ["airlock", "galley"])
    monkeypatch.setattr(prop_data, "DESIGN", tmp_path / "design")
    prop_data.DESIGN.mkdir()
    (prop_data.DESIGN / "airlock.json").write_text(json.dumps({"objects": {}}))
    runner = stages.runner()
    row = runner.stages["rough-model"]
    assert set(runner.reads(row, "airlock")) == set(runner.reads(row, "galley")) == {"plan"}
    airlock = runner.files_of(row, "airlock")
    assert airlock["concept"] == "{home}/design/concepts/airlock.png", airlock
    assert airlock["inventory"][0] == "{home}/design/props/airlock.json", airlock
    galley = runner.files_of(row, "galley")
    assert "concept" not in galley and galley["inventory"] == "{home}/design/inventory/{place}.json", galley
    assert "places" not in airlock  # no style is read: Pixal3D is worded by nothing
    for name in rough_model.TOOLS:
        assert name in airlock


def test_the_make_sends_the_concept_to_the_batch_once_and_keeps_the_finished_model(made, tmp_path):
    """The take is named by the place and the concept's own sha256 (worked out here), sent once with the concept and
    the inventory; a second make finds the take back and sends nothing.
    Break: score/stages/rough_model/__init__.py: `    if not raw.exists():` -> `    if True:`"""
    out, inputs, calls = made
    record = json.loads((out / "rough.json").read_text())
    concept_hash = hashlib.sha256(b"a concept picture").hexdigest()
    assert record["take"] == f"airlock-rough-{concept_hash[:12]}" and record["concept_sha256"] == concept_hash
    assert calls == [(record["take"], "K02.png", "airlock", inputs["inventory"])]
    again = tmp_path / "again"
    again.mkdir()
    rough_model.make(inputs, again, 1, {})  # the take is back: no second batch
    assert len(calls) == 1 and (again / "rough.glb").read_bytes() == (out / "rough.glb").read_bytes()


def test_the_gates_pass_a_made_model_from_the_concept_read_and_measure_it(made):
    """The one triangle from (0, 0, 0), (2, 0, 0), (0, 3, 1): one triangle, 2 wide, 3 high, 1 deep.
    Break: score/stages/rough_model/__init__.py: `["count"] // 3` -> `["count"]`
    Break: score/stages/rough_model/__init__.py: `return tuple(round(high[axis] - low[axis], 4) for axis in range(3))`
        -> `return tuple(round(high[axis] + low[axis] + 1, 4) for axis in range(3))`"""
    out, inputs, _ = made
    found = verdicts(out, inputs)
    assert {name: verdict.answer for name, verdict in found.items()} == {"made": "pass", "concept": "pass"}
    assert found["made"].measures == {"failing": 0, "triangles": 1, "wide": 2.0, "high": 3.0, "deep": 1.0}


def test_the_gates_fail_a_model_from_another_concept_and_a_file_that_is_no_model(made, tmp_path):
    """Another concept's picture fails `concept`; a file that is no binary glTF fails `made`; none is unknown.
    Break: score/stages/rough_model/__init__.py: `failing = [] if record["concept_sha256"] == read else [`
        -> `failing = [] if True else [`
    Break: score/stages/rough_model/__init__.py: `    except ValueError as wrong:` -> `    except KeyError as wrong:`"""
    out, inputs, _ = made
    other = tmp_path / "other.png"
    other.write_bytes(b"another picture")
    assert verdicts(out, {**inputs, "concept": other})["concept"].answer == checks.FAIL
    (out / "rough.glb").write_bytes(b"not a model: these are only words")
    assert verdicts(out, inputs)["made"].answer == checks.FAIL
    (out / "rough.glb").unlink()
    assert verdicts(out, inputs)["made"].answer == checks.UNKNOWN


def test_a_place_with_no_concept_is_refused_before_any_batch(tmp_path, monkeypatch):
    """A plan naming no concept picture is refused by name before any batch is sent.
    Break: score/stages/rough_model/__init__.py: `if "concept" not in inputs:` -> `if False:`"""
    monkeypatch.setattr(rough_model, "dispatch", lambda *arguments: pytest.fail("a batch was sent"))
    with pytest.raises(ValueError, match="no concept picture"):
        rough_model.make({"plan": plan_output(tmp_path / "plan", "airlock")}, tmp_path, 1, {})


def test_a_take_brought_back_raw_is_finished_not_sent_again(tmp_path, monkeypatch):
    """A raw model already brought back (kept in WORK/pixal) is finished, never sent to Pixal3D again (the batch
    refuses to overwrite a raw take).
    Break: score/stages/rough_model/__init__.py: `    if not final.exists():` -> `    if False:`"""
    work, finished = tmp_path / "pixal", []
    work.mkdir()
    monkeypatch.setattr(rough_model, "take_files", lambda take: (work / f"{take}.glb", work / f"{take}-final.glb"))
    monkeypatch.setattr(rough_model, "dispatch", lambda *arguments: pytest.fail("the take was sent again"))

    def finish(take, picture):
        finished.append((take, pathlib.Path(picture).name))
        glb(work / f"{take}-final.glb")
    monkeypatch.setattr(rough_model, "finish", finish)
    concept = tmp_path / "K02.png"
    concept.write_bytes(b"a concept picture")
    take = rough_model.take_name("airlock", hashlib.sha256(b"a concept picture").hexdigest())
    glb(work / f"{take}.glb")
    out = tmp_path / "out"
    out.mkdir()
    rough_model.make({"plan": plan_output(tmp_path / "plan", "airlock"), "concept": concept}, out, 1, {})
    assert finished == [(take, "K02.png")] and (out / "rough.glb").exists()


def test_the_finish_runs_on_a_rented_machine_with_the_raw_take_sent_up(tmp_path, monkeypatch):
    """The finish is never run on this PC (2026-10-22 benchmark: no Blender or lab environment here): _finish.py
    through blender_cloud.run_elsewhere, the raw take, its camera folder, the prop tools and the lab's copy sent up
    at their own paths, the finished model brought back where take_files reads it; a stand-in runner, no spend.
    Break: score/stages/rough_model/__init__.py: `sent = [raw, *([views] if views.exists() else []), picture,`
        -> `sent = [raw, picture,`"""
    work = tmp_path / "work" / "pixal"
    (work / "airlock-rough-0.svviews").mkdir(parents=True)
    monkeypatch.setattr(rough_model, "take_files",
                        lambda take: (work / f"{take}.glb", work / f"{take}-final.glb"))
    asked = []
    runner = types.SimpleNamespace(run_elsewhere=lambda *arguments: asked.append(arguments))
    monkeypatch.setattr(rough_model, "blender_cloud", lambda: runner)
    monkeypatch.setattr(rough_model.subprocess, "run", lambda *_, **__: pytest.fail("a finish ran on this PC"))
    rough_model.finish("airlock-rough-0", tmp_path / "K02.png")
    [(script, arguments, sent, outputs, classes, _who, _minutes)] = asked
    assert script == rough_model.FINISH and script.exists()
    assert arguments == [rough_model.REPO, tmp_path / "work", tmp_path / "K02.png", "airlock-rough-0"]
    assert sent[:3] == [work / "airlock-rough-0.glb", work / "airlock-rough-0.svviews", tmp_path / "K02.png"]
    assert {rough_model.REPO / "tools/props", rough_model.REPO / "vendor/image-to-3dlab"} <= set(sent)
    assert outputs == [work / "airlock-rough-0-final.glb"] and "gpu-80gb" not in classes


def test_the_batch_brings_the_raw_take_back_unfinished(tmp_path, monkeypatch):
    """dispatch asks the batch for the raw take alone (--no-finish): the batch's finish runs on this PC.
    Break: score/stages/rough_model/__init__.py: `"--inventory", str(inventory), "--no-finish"]`
        -> `"--inventory", str(inventory)]`"""
    ran = []
    monkeypatch.setattr(rough_model.subprocess, "run",
                        lambda command, **_: ran.append(command) or types.SimpleNamespace(returncode=0, stdout="",
                                                                                         stderr=""))
    rough_model.dispatch("airlock-rough-0", tmp_path / "K02.png", "airlock", tmp_path / "airlock.json", tmp_path)
    assert ran[0][-1] == "--no-finish" and str(rough_model.CLOUD) in ran[0]


def test_its_cloud_command_loads_the_batch_as_the_stage_runs_it():
    """_cloud.py run as its own command (as dispatch runs it) loads batch.py with its sibling modules found; the
    2026-10-22 benchmark's rough model failed on `No module named 'capacity'` before renting anything. --help rents
    nothing.
    Break: score/stages/rough_model/_cloud.py: `        sys.path.insert(0, str(BATCH.parent))` -> `        pass`"""
    done = subprocess.run([sys.executable, str(cloud.__file__), "--help"], cwd=REPO, capture_output=True, text=True,
                          timeout=60)
    assert done.returncode == 0, done.stderr[-2000:]


def test_the_batch_check_keeps_the_owner_s_approval_without_the_rows(tmp_path):
    """The rough model is on no inventory row; the batch's own check is replaced by its approval half alone, and the
    batch's command still looks that check up by name, so the replacement takes; a hand-in is checked by its lock.
    Break: score/stages/rough_model/_cloud.py: `            batch.built_from(path)` -> `            pass`"""
    asked = []
    batch = types.SimpleNamespace(built_from=lambda path: asked.append(path) or {"place": "lab"})
    cloud.concept_check(batch)([object()], ["data/inventory/lab.json"])
    assert asked == ["data/inventory/lab.json"]
    loaded = cloud.load_batch()
    hand_in = tmp_path / "greenhouse.json"  # a hand-in: page A's row shape is never asked of it
    hand_in.write_text(json.dumps({"scene": "greenhouse", "approved": {"by": loaded.DESIGNED},
                                   "rows": [{"id": "moon", "anchor": "sky"}]}))
    cloud.concept_check(loaded)([object()], [str(hand_in)])
