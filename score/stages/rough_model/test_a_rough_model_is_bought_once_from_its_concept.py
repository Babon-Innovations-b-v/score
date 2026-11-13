"""A place's rough model is bought once from its concept: every place with a kept plan has the row, reading its
design's concept and inventory; the make sends the concept to the batch once (the raw take alone, through _cloud.py,
whose own check approves the hand-in it is sent) and finishes the raw take on a rented machine (a take already back is
only finished, a finished one never sent again; a place with no concept is refused before any batch); its gates pass
a model made from the concept read and measure it, and fail one from another concept or a file that is no model. No
spend, no model made: a stand-in batch command and rented machine, a one-triangle binary glTF measured by hand
(2 x 3 x 1, one triangle).

One world: kept plans for the base, the airlock (designed: its hand-in) and the galley; three makes in order (the
airlock's first, the airlock's again, the galley's with its raw take already back) and one refused, each row naming
what it must send; then a table of gate cases on the airlock's model.

Each break turns the test red (`Break: <file>: `old` -> `new``); each was applied once and seen red.
Break: score/stages/scene_record/__init__.py: `return path.exists() and "leads" in json.loads(path.read_text())`
    -> `return False`
Break: score/stages/__init__.py: `return {**found, "concept": "{home}/design/concepts/" + f"{place}.png",
    "inventory": prop_data.keyed(place)}` -> `return found`
Break: score/stages/rough_model/__init__.py: `    if not raw.exists():` -> `    if True:`
Break: score/stages/rough_model/__init__.py: `    if not final.exists():` -> `    if False:`
Break: score/stages/rough_model/__init__.py: `if "concept" not in inputs:` -> `if False:`
Break: score/stages/rough_model/__init__.py: `sent = [raw, *([views] if views.exists() else []), picture,`
    -> `sent = [raw, picture,`
Break: score/stages/rough_model/__init__.py: `"--inventory", str(inventory), "--no-finish"]`
    -> `"--inventory", str(inventory)]`
Break: score/stages/rough_model/__init__.py: `["count"] // 3` -> `["count"]`
Break: score/stages/rough_model/__init__.py: `return tuple(round(high[axis] - low[axis], 4) for axis in range(3))`
    -> `return tuple(round(high[axis] + low[axis] + 1, 4) for axis in range(3))`
Break: score/stages/rough_model/__init__.py: `failing = [] if record["concept_sha256"] == read else [`
    -> `failing = [] if True else [`
Break: score/stages/rough_model/__init__.py: `    except ValueError as wrong:` -> `    except KeyError as wrong:`
Break: score/stages/rough_model/_cloud.py: `        sys.path.insert(0, str(BATCH.parent))` -> `        pass`
Break: score/stages/rough_model/_cloud.py: `            batch.built_from(path)` -> `            pass`

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest
    score/stages/rough_model/test_a_rough_model_is_bought_once_from_its_concept.py
"""
import hashlib
import json
import pathlib
import shutil
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

REPO = pathlib.Path(__file__).resolve().parents[3]
RUN = subprocess.run  # the real one: the make's stand-in replaces it on the module
CONCEPT, GALLEY_CONCEPT = b"a concept picture", b"the galley's concept picture"
MEASURED = {"failing": 0, "triangles": 1, "wide": 2.0, "high": 3.0, "deep": 1.0}

# The makes in order: (id, place, concept picture's bytes or None, its raw take already back, the batch commands it
# sends, the finishes it sends, the camera folder sent up with its finish).
MAKES = [
    ("first make", "airlock", CONCEPT, False, 1, 1, True),
    ("again: the take is back", "airlock", CONCEPT, False, 0, 0, None),
    ("raw take already back", "galley", GALLEY_CONCEPT, True, 0, 1, False),
    ("no concept: refused", "airlock", None, False, 0, 0, None),
]

# The gates on the airlock's model: (id, the concept the gates read, rough.glb as made / words / gone, answers).
GATES = [
    ("made from the concept read", "own", "made", {"made": checks.PASS, "concept": checks.PASS}),
    ("another concept's picture", "other", "made", {"made": checks.PASS, "concept": checks.FAIL}),
    ("a file that is no binary glTF", "own", "words", {"made": checks.FAIL, "concept": checks.PASS}),
    ("no model at all", "own", "gone", {"made": checks.UNKNOWN, "concept": checks.PASS}),
]


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


def stand_ins(work, monkeypatch):
    """(batch commands, finishes) recorded by a stand-in for every command the make runs on this PC (the batch: it
    brings the raw take and its camera folder back, unfinished) and a stand-in rented machine (the finish: it brings
    the finished model back where take_files reads it)."""
    commands, finishes = [], []
    monkeypatch.setattr(rough_model, "take_files", lambda take: (work / f"{take}.glb", work / f"{take}-final.glb"))

    def batch(command, **_):
        commands.append(command)
        take = pathlib.Path(command[2]).read_text().split(" ", 1)[0]
        glb(work / f"{take}.glb")
        (work / f"{take}.svviews").mkdir()
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(rough_model.subprocess, "run", batch)

    def run_elsewhere(*arguments):
        finishes.append(arguments)
        glb(arguments[3][0])
    monkeypatch.setattr(rough_model, "blender_cloud", lambda: types.SimpleNamespace(run_elsewhere=run_elsewhere))
    return commands, finishes


def test_a_rough_model_is_bought_once_from_its_concept(tmp_path, monkeypatch):
    for module in (surface_data, score.stages.surfaces.data):  # no other designed place's hand-in is read
        monkeypatch.setattr(module, "DESIGN", tmp_path / "no design")
    monkeypatch.setattr(prop_data, "DESIGN", tmp_path / "design")
    prop_data.DESIGN.mkdir()
    loaded = cloud.load_batch()  # _cloud.py's own batch.py, whose check the batch command runs
    hand_in = prop_data.DESIGN / "airlock.json"  # a hand-in: page A's row shape is never asked of it
    hand_in.write_text(json.dumps({"scene": "airlock", "approved": {"by": loaded.DESIGNED},
                                   "rows": [{"id": "moon", "anchor": "sky"}], "objects": {}}))
    kept_plans(tmp_path / "kept", monkeypatch, ["base", "airlock", "galley"])

    # The row: every place with a kept plan, shell or inside alike; a designed place reads its concept and hand-in.
    runner = stages.runner()
    places = ["base", "airlock", "galley", "nowhere"]
    assert {place for stage, place in runner.nodes(places) if stage.name == "rough-model"} == {"base", "airlock",
                                                                                               "galley"}
    row = runner.stages["rough-model"]
    assert set(runner.reads(row, "airlock")) == set(runner.reads(row, "galley")) == {"plan"}
    airlock, galley = runner.files_of(row, "airlock"), runner.files_of(row, "galley")
    assert airlock["concept"] == "{home}/design/concepts/airlock.png", airlock
    assert airlock["inventory"][0] == "{home}/design/props/airlock.json", airlock
    assert "concept" not in galley and galley["inventory"] == "{home}/design/inventory/{place}.json", galley
    assert "places" not in airlock and set(rough_model.TOOLS) <= set(airlock), airlock  # no style: Pixal3D

    work = tmp_path / "work" / "pixal"
    work.mkdir(parents=True)
    commands, finishes = stand_ins(work, monkeypatch)
    outputs = {}
    for name, place, concept, raw_back, batches, finished, views_sent in MAKES:
        inputs = {"plan": plan_output(tmp_path / name / "plan", place), "inventory": hand_in}
        if concept is not None:
            inputs["concept"] = tmp_path / name / f"{place}.png"
            inputs["concept"].write_bytes(concept)
            concept_hash = hashlib.sha256(concept).hexdigest()
            take = f"{place}-rough-{concept_hash[:12]}"
            if raw_back:
                glb(work / f"{take}.glb")
        out = tmp_path / name / "out"
        out.mkdir()
        sent_before, finished_before = len(commands), len(finishes)
        if concept is None:
            with pytest.raises(ValueError, match="no concept picture"):
                rough_model.make(inputs, out, 1, {})
        else:
            rough_model.make(inputs, out, 1, {})
        new_commands, new_finishes = commands[sent_before:], finishes[finished_before:]
        assert (len(new_commands), len(new_finishes)) == (batches, finished), (name, new_commands, new_finishes)
        for command in new_commands:  # the raw take alone, from the concept and its inventory, by _cloud.py
            assert command[1] == str(rough_model.CLOUD), (name, command)
            assert command[2:] == [str(out / "list.txt"), "--who", f"score rough-model {place}",
                                   "--inventory", str(hand_in), "--no-finish"], (name, command)
            assert (out / "list.txt").read_text() == f"{take} {inputs['concept']}\n", name
        for script, arguments, sent, brought, classes, _who, _minutes in new_finishes:  # on a rented machine
            raw = work / f"{take}.glb"
            assert script == rough_model.FINISH and script.exists(), name
            assert arguments == [rough_model.REPO, work.parent, inputs["concept"], take], (name, arguments)
            camera = [work / f"{take}.svviews"] if views_sent else []
            assert sent[:2 + len(camera)] == [raw, *camera, inputs["concept"]], (name, sent)
            assert {rough_model.REPO / "tools/props", rough_model.REPO / "vendor/image-to-3dlab"} <= set(sent), name
            assert brought == [work / f"{take}-final.glb"] and "gpu-80gb" not in classes, (name, brought, classes)
        if concept is None:
            continue
        record = json.loads((out / "rough.json").read_text())
        assert (record["take"], record["concept_sha256"]) == (take, concept_hash), (name, record)
        assert (out / "rough.glb").read_bytes() == (work / f"{take}-final.glb").read_bytes(), name
        found = verdicts(out, inputs)
        assert {gate: verdict.answer for gate, verdict in found.items()} == {"made": checks.PASS,
                                                                             "concept": checks.PASS}, name
        assert found["made"].measures == MEASURED, (name, found["made"].measures)
        outputs.setdefault(place, (out, inputs))

    # The gates on the airlock's model as made, from another concept, as words, and gone.
    made, made_inputs = outputs["airlock"]
    other = tmp_path / "other.png"
    other.write_bytes(b"another picture")
    for name, read, model, answers in GATES:
        out = tmp_path / "gates" / name
        shutil.copytree(made, out)
        if model == "words":
            (out / "rough.glb").write_bytes(b"not a model: these are only words")
        elif model == "gone":
            (out / "rough.glb").unlink()
        inputs = {**made_inputs, "concept": other if read == "other" else made_inputs["concept"]}
        found = verdicts(out, inputs)
        assert {gate: verdict.answer for gate, verdict in found.items()} == answers, name

    # The batch command the make ran loads batch.py with its siblings found (--help rents nothing); its check of the
    # inventory it was sent is the approval alone (the hand-in by its lock), and the command looks it up by name.
    done = RUN([sys.executable, commands[0][1], "--help"], cwd=REPO, capture_output=True, text=True,
               timeout=60)
    assert done.returncode == 0, done.stderr[-2000:]
    asked, approve = [], loaded.built_from
    monkeypatch.setattr(loaded, "built_from", lambda path: asked.append(path) or approve(path))
    cloud.concept_check(loaded)([object()], [commands[0][commands[0].index("--inventory") + 1]])
    assert asked == [str(hand_in)], asked
