"""A look is made by the shared loop, dressed only in the library surfaces the loop painted, baked onto its body,
and judged by measure, never passed on a missing record (people/__init__.py, loop.py, dress.py, baked_body.py, and
the body rows of ../people_bodies, which has no test file of its own).

Made-up records (no cloud, no models). One test: a case table of judging calls (a body's records written to a folder
and judged, or a pure judging function's inputs) with the answer each must give, then the few worlds the rest needs:
the loop's hand-on of three takes, the stage table and the design's full-or-far share, a look's parts on its take,
the glTF binary round trip and the bake's coordinates, a garment's under layer, and the people line's scene library.

Breaks that turn it red (each applied once and seen red, then reverted):
- `loop.take_faults`: the `file_hash(path) != recorded...` test dropped  -> the loop's take "another finish".
- `loop.judge_made`: `PASS if through else FAIL` read as `PASS`  -> the loop's take "another finish" (no look came
  through).
- `loop.handed`: the missing labelled take's gap made a `pass`  -> the loop's take "unpainted"; `in_bake(found["model"],
  bake)` read as `found["model"]`  -> the loop's take "as made" (a home's absolute path handed on, 2026-11-10).
- `stages.BATCH_GATES`: its `people-made` entry dropped  -> the loop's batch gaps (a look a batch gap left out
  fails the place's people-made, camp's astronaut_1 2026-11-10).
- `bodies.laid_take`: the `filecmp.cmp` skip dropped  -> the loop's laid take (a file of the same bytes written
  again); `os.replace(partial, laid)` made `shutil.copyfile(path, laid)`  -> the loop's laid take (another take's
  file rewritten in place).
- `bodies.judge_shell`: `& (offsets[soft] <= depths)` dropped  -> case "tight garment off its person" passes;
  `(offsets[soft] > 0) &` dropped  -> case "body standing out through the look" passes.
- `bodies.rigid_part`: the CLOTH_WORDS test made `if False`  -> cases "a belt is cloth", "a buckle is cloth".
- `bodies.refused_on_record`: `if foretold:` read as `if False:`  -> case "failed tucks record refused".
- `bodies.parts_fit`: its pairs faces seven apart in the file instead of neighbouring ones (`face_adjacency`)  ->
  the parts world (the fitting parts read under PARTS_FIT_LEAST); `bodies.judge_parts`: `and fit >= PARTS_FIT_LEAST`
  dropped  -> the parts world (the parts of another finished model pass); `bodies.refused_on_misfit`: `fit <` read as
  `False and fit <`  -> the parts world (a body built on scattered parts); `bodies.laid_parts`: the `filecmp.cmp`
  test dropped  -> the parts world (the candidate's older parts left under the accepted ones, env1 2026-11-08);
  `bodies.kept_parts`: `recorded == sorted(painted) and` dropped  -> the parts world (parts judged on the work suit's
  names kept for a made look, the astronaut's boots "steel buckle", 2026-11-08).
- `dress.outer_labels`: every point kept at its nearest sample (`if not near` read as `if True`)  -> case "the
  outer boot, not the suit inside".
- `dress.without_strays`: `rounds=0`  -> the stray blotch case.
- `dress.painted_primitives`: `under = primitive["material"] in garments` read as `False`  -> the under layer world
  (the under layer reads the collar's skin above it and fails aligned with the garment's skin, pilot 2026-11-11).
- `dress.flat_materials`: the normal map left out of the maps it asks for  -> case "three maps baked".
- `dress.worn_name`: `role in KEPT_ROLES` read as `False`  -> case "the visor kept in variant 1".
- `dress.worn_name`: its refusal of a worn surface the library lacks dropped  -> case "suit_blue the library lacks"
  (suit_blue worn unnamed, the bake's "names no library surface" after the work, 2026-11-10).
- `clips.usable`: `if not passes` read as `if False`  -> the clip cases.
- `bodies.judge_clips`: `PASS if passing else FAIL` read as `PASS`  -> case "tucks over the gate in every clip"
  (accepted, the astronaut 2026-11-08).
- `clips.per_clip`: the flexible check's `<= FLEX_MOST` read as `<= float("inf")`  -> case "the 2.4x boot shaft";
  `bar is None or` dropped (a body with no shipped record held to its own bind pose)  -> case "no shipped record,
  crossings not judged" (the pilot's 2026-11-11); the shipped bar read as None always  -> case "30 crossings over
  the shipped 20".
- `full.full_looks`: `>= FAR_SHARE` read as `>= 0.0`  -> case "full or far by share" and the design's shares.
- `bodies.laid_take`: the `filecmp.cmp(...)` skip and the rename dropped (copied over in place)  -> the loop's laid
  take (the same bytes written again over the people line's own inputs).
"""
import io
import json
import pathlib
import struct
import sys
from typing import NamedTuple

import numpy as np
import trimesh
from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/characters/maker"))
sys.path.insert(0, str(REPO / "tools/usd"))

import score.stages.people as people  # noqa: E402
import score.stages.props.pixal_row as pixal_row  # noqa: E402
from score import graph, stages  # noqa: E402
from score.stages import batch_gaps, people_rows, shapes_first  # noqa: E402
from score.stages.cast import spread  # noqa: E402
from score.stages.people import baked_body, dress, look, loop  # noqa: E402  (baked_body puts tools/props on the path)
from score.stages.people_bodies import bodies, clips, far, full, made_clips  # noqa: E402
import clearance  # noqa: E402
import contents  # noqa: E402
import glb_file  # noqa: E402
import labels  # noqa: E402


class In(NamedTuple):
    """A path inside the case's own folder (its records written there); the folder itself when unnamed."""
    name: str = ""


class Raises(NamedTuple):
    kind: type
    words: tuple


class Verdict(NamedTuple):
    """A check's verdict: its answer, its whole measures (`measures`) or some of them (`has`), and the words its
    reason and first finding carry."""
    answer: str
    measures: dict = None
    has: dict = None
    reason: tuple = ()
    finding: tuple = ()


class Holds(NamedTuple):
    text: str
    predicate: object


class At(NamedTuple):
    path: tuple
    expected: object


class Contains(NamedTuple):
    words: tuple


class Case(NamedTuple):
    name: str
    function: object
    args: tuple
    expected: object
    records: dict = None


def resolved(value, folder):
    if isinstance(value, In):
        return folder / value.name if value.name else folder
    if isinstance(value, dict):
        return {key: resolved(item, folder) for key, item in value.items()}
    return value


def written(folder, records):
    """The case's records in its folder: .npz arrays, bytes as they are, anything else as JSON."""
    folder.mkdir(parents=True)
    for name, content in records.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name.endswith(".npz"):
            np.savez(path, **content)
        elif isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(json.dumps(content))


def outcome(case, root):
    folder = root / case.name.replace(" ", "_").replace("/", "_")
    if case.records is not None:
        written(folder, case.records)
    try:
        return case.function(*(resolved(arg, folder) for arg in case.args))
    except (RuntimeError, graph.Blocked) as error:
        return error


def meets(result, expected, name):
    """The one check every case goes through: the call's result against the answer the case expects."""
    if isinstance(expected, Raises):
        assert isinstance(result, expected.kind), f"{name}: not refused, {result!r}"
        assert all(word in str(result) for word in expected.words), f"{name}: {result}"
        return
    assert not isinstance(result, Exception), f"{name}: refused, {result!r}"
    if isinstance(expected, Verdict):
        assert result.answer == expected.answer, f"{name}: {result}"
        assert expected.measures is None or result.measures == expected.measures, f"{name}: {result}"
        assert all(result.measures[key] == value for key, value in (expected.has or {}).items()), f"{name}: {result}"
        assert all(word in result.reason for word in expected.reason), f"{name}: {result}"
        assert all(word in result.findings[0] for word in expected.finding), f"{name}: {result}"
    elif isinstance(expected, At):
        for key in expected.path:
            result = result[key]
        meets(result, expected.expected, name)
    elif isinstance(expected, Contains):
        assert all(word in result for word in expected.words), f"{name}: {result}"
    elif isinstance(expected, Holds):
        assert expected.predicate(result), f"{name}: {expected.text}, {result}"
    elif isinstance(expected, set):
        assert set(result) == expected, f"{name}: {result}"
    else:
        found = result.tolist() if isinstance(result, np.ndarray) else result
        assert found == expected, f"{name}: {found}"


def clip_records(deep=13, tuck_over=0, flex=1.3, crossings=10, standing_tucks=None, shipped=True):
    """A body's records with two clips: walking with the given counts, standing clean unless `standing_tucks`
    (worst mm, frames over) puts it over the gate too."""
    clip = {"worst_tuck_out_mm": 2.0, "frames_tuck_over": 0, "rigid_stretch": 1.0, "flex_stretch": 1.3,
            "most_crossings": 10}
    standing = clip if standing_tucks is None else dict(clip, worst_tuck_out_mm=standing_tucks[0],
                                                         frames_tuck_over=standing_tucks[1])
    records = {"checks/bodycloth.json": {
        "margin_mm": 3.0, "bind": {"deep_by_part": {"boot_r": 13}},
        "clips": {"walking": {"deep_by_part": {"boot_r": deep}, "deepest_mm": 9.0},
                  "standing": {"deep_by_part": {"boot_r": 13}, "deepest_mm": 2.0}}},
        "checks/pokes.json": {"rest_crossings": 10, "clips": {
            "walking": dict(clip, worst_tuck_out_mm=2.0 + tuck_over, frames_tuck_over=tuck_over, flex_stretch=flex,
                            most_crossings=crossings),
            "standing": standing}}}
    if shipped:
        records["checks/pokes_shipped.json"] = {"rest_crossings": 10, "clips": {
            "walking": {"most_crossings": 20}, "standing": {"most_crossings": 20}}}
    return records


def shell_records(soft_tail, tail_offset=0.08, under_depth=None):
    """A look of 1,000 soft points, `soft_tail` of them `tail_offset` off the fitted body, and a hand and a boot 12 cm
    off; with `under_depth`, the body under the clothes lies that far inside every point (a plane under the look,
    checks/base.npz)."""
    near, far_tail = [0] * 21, [0] * 81
    near[20], far_tail[80] = 1000 - soft_tail, soft_tail
    rigid = [0] * 121
    rigid[120] = 50
    part_of = np.r_[np.full(1000 - soft_tail, 1), np.full(soft_tail, 2), np.full(50, 3), np.full(50, 4)]
    offsets = np.r_[np.full(1000 - soft_tail, 0.02), np.full(soft_tail, tail_offset), np.full(100, 0.12)]
    points = np.c_[np.random.default_rng(0).uniform(-0.5, 0.5, (len(part_of), 2)), np.zeros(len(part_of))]
    records = {
        "checks/shell.json": {"scale": 1.0, "parts": {
            "1": {"most_m": 0.02, "offsets_mm": near}, "2": {"most_m": 0.08, "offsets_mm": far_tail},
            "3": {"most_m": 0.12, "offsets_mm": rigid}, "4": {"most_m": 0.12, "offsets_mm": rigid}}},
        "checks/parts.json": {"parts": [
            {"part": 1, "role": "garment", "name": "cloth"}, {"part": 2, "role": "garment", "name": "cloth"},
            {"part": 3, "role": "hard", "name": "boot"}, {"part": 4, "role": "skin", "name": "skin_hands"}]},
        "rig.npz": {"points": points, "faces": np.repeat(np.arange(len(points))[:, None], 3, 1),
                    "part_of": part_of, "shell_offsets": offsets}}
    if under_depth is not None:  # a square of two triangles facing up, under_depth below the look
        records["checks/base.npz"] = {"faces": np.array([[0, 1, 2], [0, 2, 3]]), "under_points": np.array(
            [[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0]]) - [0, 0, under_depth]}
    return records


def glb(document):
    """A glb of its JSON chunk and an empty binary one."""
    text = json.dumps(document).encode()
    text += b" " * (-len(text) % 4)
    return (struct.pack("<III", 0x46546C67, 2, 28 + len(text)) + struct.pack("<II", len(text), 0x4E4F534A) + text
            + struct.pack("<I", 0) + b"BIN\x00")


def joins_records(hand):
    """A body with no wrist measured, drawing its second piece in `hand`."""
    return {"checks/joins.json": {"verdict": {"wrist": None, "ankle": {"pass": True}, "stance": {"pass": True}}},
            "body.glb": glb({"nodes": [{"name": "work", "mesh": 0, "skin": 0}],
                             "materials": [{"name": "cloth"}, {"name": hand}],
                             "meshes": [{"primitives": [{"material": 0}, {"material": 1}]}]})}


def rig_records(unseeded=(), rig=True):
    records = {f"motions/{clip}.record.json": {"clip": clip} if clip in unseeded else {"clip": clip, "seed": 1}
               for clip in made_clips.CLIPS}
    if rig:
        records["rig.npz"] = {f"clip_{clip}": np.zeros(1) for clip in made_clips.CLIPS}
    return records


def png(colour):
    picture = io.BytesIO()
    Image.new("RGB", (8, 8), tuple(int(round(value * 255)) for value in colour)).save(picture, "PNG")
    return picture.getvalue()


def cloth_material(maps, library=True):
    """A body of one cloth material: its library surface baked into `maps` (base, rough, normal), or with none of
    them the library's colour as a flat factor."""
    material = {"name": "cloth", "extras": {"library": "suit"} if library else {}}
    textures = {"base": ("pbrMetallicRoughness", "baseColorTexture", 0),
                "rough": ("pbrMetallicRoughness", "metallicRoughnessTexture", 1), "normal": (None, "normalTexture", 2)}
    if not maps:
        material["pbrMetallicRoughness"] = {"baseColorFactor": [0.5, 0.5, 0.5, 1.0]}
    for name in maps:
        group, key, index = textures[name]
        (material.setdefault(group, {}) if group else material)[key] = {"index": index}
    return {"materials": [material], "meshes": [{"primitives": [{"material": 0}]}]}


def grid_cloth(size=20):
    """A flat square of cloth, size by size cells of two triangles: (corners per triangle, faces over them)."""
    cells = [(column, row) for row in range(size) for column in range(size)]
    triangles = []
    for column, row in cells:
        low, right, up, both = (column, row), (column + 1, row), (column, row + 1), (column + 1, row + 1)
        triangles += [[low, right, up], [right, both, up]]
    corners = np.array(triangles, dtype=float).reshape(-1, 2)
    return np.column_stack([corners, np.zeros(len(corners))]), np.arange(len(corners)).reshape(-1, 3)


def stray_cloth():
    """The grid cloth half brown (a panel), one cell dark (0.25%, a stray), one cell a kept one-surface part's visor,
    the rest grey: (points, faces, labels, kept)."""
    points, faces = grid_cloth()
    painted = np.array(["grey"] * len(faces), dtype=object)
    painted[:400] = "brown"
    painted[[500, 501]] = "dark"
    kept = np.zeros(len(faces), dtype=bool)
    kept[[700, 701]] = True
    painted[[700, 701]] = "visor"
    return points, faces, painted, kept


STRIP_FACES = np.array([[0, 1, 2], [1, 3, 2], [2, 3, 4], [3, 5, 4], [4, 5, 6], [5, 7, 6]])
STRIP = np.array([[number // 2, number % 2, 0.0] for number in range(8)])
SQUARE = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]])
TAKE_SAMPLES = np.array([[0.0, 0, 0.0], [0.001, 0, 0.0], [0.0, 0, -0.006], [0.001, 0, -0.006], [0.0, 0.001, -0.006]])
UP = np.array([[0.0, 0, 1.0]])
SURFACES = {"skin_a": {"family": "skin", "colour": [0.5, 0.4, 0.3]},
            "skin_b": {"family": "skin", "colour": [0.4, 0.3, 0.2]},
            "skin_c": {"family": "skin", "colour": [0.1, 0.1, 0.1]},
            "suit_white": {"family": "fabric", "colour": [0.9, 0.9, 0.9]},
            "suit_grey": {"family": "fabric", "colour": [0.6, 0.6, 0.6]},
            "visor": {"family": "glass", "colour": [0.1, 0.1, 0.1]},
            "visor_smoke": {"family": "glass", "colour": [0.2, 0.2, 0.2]}}
WORN = {"skin#0": {"painted": "skin_a", "role": "skin"}, "suit#1": {"painted": "suit_white", "role": "cloth"},
        "visor#2": {"painted": "visor", "role": "hard"}}
SUIT = {"colour": [0.2, 0.3, 0.6], "family": "fabric"}
BAKED = (np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float64), np.array([[0, 1, 2]]), np.array([0]),
         ["suit"], np.array([[[0.1, 0.1], [0.9, 0.1], [0.1, 0.9]]]), In("base_color.png"), {"suit": SUIT}, {},
         (0.0, 0.0))
SHARE_DESIGN = {"places": {"a": {"rows": {"near": {"looks": ["near-work"], "share": 0.25},
                                          "far": {"looks": ["far-work"], "share": 0.05},
                                          "unmeasured": {"looks": ["plain-work"], "share": None},
                                          "crowd": {"crowd": "crowd-coat", "share": 0.4}}}}}
TALLEST = {"boxes": [[0, 100, 50, 484], [0, 0, 10, 100]], "box": [0, 0, 10, 100]}
CAST = {"rows.json": {"places": {"lab": {"concept": "a test", "rows": {
            "a": {"name": "person walking", "count": 1, "looks": ["bram-work"]},
            "b": {"name": "person", "where": "at a desk", "count": 1, "looks": ["bram-work"]}}}}, "new": {}},
        "usable.json": {"bram-work": {"usable": ["standing"], "failing": {"walking": ["tucks: 5.1 mm"]}}}}
JOINS = dict((check.name, check) for check in bodies.checks())["joins"].judge
ROUTE_BODY = {"accessors": [{"count": 30}, {"count": 12}, {"count": 3000}],
              "meshes": [{"primitives": [{"indices": 0}, {"indices": 1}]}, {"primitives": [{"indices": 2}]}],
              "nodes": [{"name": "work", "mesh": 0}, {"name": "far", "mesh": 1}, {"name": "Hips"}]}
BODY = (In(), {}, {})

CASES = [
    # a body's clips, judged clip by clip on their records
    Case("clean clips all usable", clips.usable, (In(),), (["standing", "walking"], {}), clip_records()),
    Case("walking deep and tucked", clips.usable, (In(),), (["standing"], {"walking": [
        "tucks: worst tuck 5.0 mm", "body through cloth: over the bind {'boot_r': 50}, deepest 9.0 mm"]}),
        clip_records(deep=50, tuck_over=3)),
    Case("one failing clip passes the body", bodies.judge_clips, BODY,
         Verdict("pass", has={"failing": 1}, finding=("walking",)), clip_records(deep=50, tuck_over=3)),
    Case("tucks over the gate in every clip", bodies.judge_clips, BODY, Verdict("fail", reason=("every clip",)),
         clip_records(deep=50, tuck_over=3, standing_tucks=(52.81, 40))),  # the astronaut's, 2026-11-08
    Case("the 2.4x boot shaft", clips.usable, (In(),),  # the boot shaft's sharp blend, sitting
         (["standing"], {"walking": ["flexible: boot shafts at 2.4x"]}), clip_records(flex=2.4)),
    Case("30 crossings over the shipped 20", clips.usable, (In(),),  # the pilot of 2026-11-11
         (["standing"], {"walking": ["cloth through cloth: 30 crossings, the shipped body's 20"]}),
         clip_records(crossings=30)),
    Case("no shipped record, crossings usable", clips.usable, (In(),), (["standing", "walking"], {}),
         clip_records(crossings=30, shipped=False)),
    Case("no shipped record, crossings not judged", clips.per_clip, (In(),),
         At(("walking", "cloth through cloth", 1), Contains(("not judged",))),
         clip_records(crossings=30, shipped=False)),
    Case("a cast doing a failing clip", clips.judge_casts, (In(), {"casts": In("rows.json")}, {}),
         Verdict("fail", measures={"failing": 1, "judged": 2}), CAST),
    # the shell holds most soft points and leaves rigid parts out
    Case("9 soft points off the shell", bodies.judge_shell, BODY, Verdict(
        "pass", has={"offset_share_m": 0.02, "offset_most_m": 0.08}, reason=("part 2",)), shell_records(9)),
    Case("20 soft points off the shell", bodies.judge_shell, BODY, Verdict("fail", has={"offset_share_m": 0.08}),
         shell_records(20)),
    # a bulky suit 8 cm off its fitted body passes only where the person under it lies deeper still (its measured
    # thickness); a tight garment as far off, its person close under it, fails, and so does a fitted body standing
    # 8 cm out through the look
    Case("bulky suit over its person", bodies.judge_shell, BODY, Verdict("pass", has={"held_share": 1.0}),
         shell_records(200, under_depth=0.12)),
    Case("tight garment off its person", bodies.judge_shell, BODY, Verdict("fail", has={"held_share": 0.8}),
         shell_records(200, under_depth=0.03)),
    Case("body standing out through the look", bodies.judge_shell, BODY, Verdict("fail", has={"held_share": 0.8}),
         shell_records(200, tail_offset=-0.08, under_depth=0.12)),
    # an astronaut's gloves are its suit's cloth (2026-10-22): no wrist measured and no hand piece drawn is no join;
    # a body that draws a hand with no wrist measured fails, and no joins record at all is unknown
    Case("no hand piece, no wrist join", bodies.judge_joins, BODY, Verdict("pass"), joins_records("cloth")),
    Case("a hand drawn, no wrist measured", bodies.judge_joins, BODY, Verdict("fail"), joins_records("skin_hands")),
    Case("no joins record", JOINS, BODY, Verdict("unknown"), {}),
    # the route adds the under layer and the closings: the gate counts the body glTF's near nodes, never the far
    Case("triangles of the route body as drawn", bodies.judge_triangles, BODY,
         Verdict("pass", has={"triangles": 14}), {"body.glb": glb(ROUTE_BODY), "checks/route.json": {}}),
    Case("far-only look on its far body", far.judge_far_triangles, BODY, Verdict("pass"),
         {"checks/build.json": {"levels": {"far": {"triangles": 1220}, "coat": {"triangles": 34159}}},
          "checks/shell.json": {"offset_most_m": 0.09}}),
    Case("far-only look's near body recorded", far.judge_near_recorded, BODY,
         Verdict("pass", measures={"near_triangles": 34159, "shell_most_m": 0.09}),
         {"checks/build.json": {"levels": {"far": {"triangles": 1220}, "coat": {"triangles": 34159}}},
          "checks/shell.json": {"offset_most_m": 0.09}}),
    # the clips row passes only with every clip in the rig and its seed
    Case("every clip in the rig, seeded", made_clips.judged, BODY, Verdict("pass"), rig_records()),
    Case("bench with no seed", made_clips.judged, BODY, Verdict("fail"), rig_records(unseeded=("bench",))),
    Case("no rig", made_clips.judged, BODY, Verdict("unknown"), rig_records(unseeded=("bench",), rig=False)),
    # #21: a look whose settled tucks failed in every clip on the same inputs is Blocked, never rented for
    Case("no tucks record", bodies.refused_on_record, (None, "people-body-x"), None),
    Case("failed tucks record refused", bodies.refused_on_record, ({"worst_tuck_out_mm": 9.32, "clips": 4},
                                                                   "people-body-x"),
         Raises(graph.Blocked, ("predicted gap", "9.32"))),
    # a body's bake is checked by bake_check's own measures: on the surface's colour it lies, far off it is named
    Case("bake on its library colour", baked_body.checked, BAKED, At(("faults",), []),
         {"base_color.png": png(labels.srgb(np.array(SUIT["colour"])))}),
    Case("bake off its library colour", baked_body.checked, BAKED,
         Holds("one fault, over 20 delta E", lambda found: len(found["faults"]) == 1
               and found["surfaces"]["suit"]["delta_e"] > 20), {"base_color.png": png(np.array([1.0, 1.0, 0.0]))}),
    # a belt is worn as cloth; a boot and the hands are rigid
    Case("a belt is cloth", bodies.rigid_part, ({"role": "hard", "name": "black_leather_belt"},), False),
    Case("a buckle is cloth", bodies.rigid_part, ({"role": "hard", "name": "steel_buckle"},), False),
    Case("a boot is rigid", bodies.rigid_part, ({"role": "hard", "name": "boot"},), True),
    Case("the hands are rigid", bodies.rigid_part, ({"role": "skin", "name": "skin_hands"},), True),
    # the route names the body's node work while the look's outfit is made (2026-10-22): the one skinned node that
    # is not the far body
    Case("the routed body whatever its outfit is named", dress.outfit_node, (
        {"nodes": [{"name": "far", "mesh": 0, "skin": 0}, {"name": "work", "mesh": 1, "skin": 0}, {"name": "Hips"}]},),
         {"name": "work", "mesh": 1, "skin": 0}),
    # the take keeps faces Pixal3D grew inside (2026-10-22): the outermost samples along the point's normal vote
    Case("the outer boot, not the suit inside", dress.outer_labels, (
        np.array([[0.0, 0, -0.005]]), UP, TAKE_SAMPLES, np.array(["boot", "boot", "suit", "suit", "suit"]), 0.015,
        0.004), ["boot"]),
    Case("a point far from every sample", dress.outer_labels, (
        np.array([[5.0, 0, 0]]), UP, TAKE_SAMPLES, np.array(["boot", "boot", "suit", "suit", "suit"]), 0.015, 0.004),
         ["boot"]),
    # a garment splits where its paint changes (the astronaut's overalls and bib, 2026-10-22); a lone point's label
    # follows its neighbours; a hard part, the face and the hair take one surface, by area, not by points (the
    # helmet's visor on 53% of its area, its rim's dense ring more of its points, 2026-10-23)
    Case("a garment splits where its paint changes", dress.surfaces_of, (
        np.array(["brown"] * 4 + ["grey"] * 4), STRIP_FACES, "garment", STRIP), ["brown"] * 3 + ["grey"] * 3),
    Case("a lone point follows its neighbours", dress.surfaces_of, (
        np.array(["brown"] * 3 + ["grey"] + ["brown"] * 4), STRIP_FACES, "garment", STRIP), {"brown"}),
    Case("a hard part takes one surface", dress.surfaces_of, (
        np.array(["boot"] * 5 + ["suit"] * 3), STRIP_FACES, "hard", STRIP), {"boot"}),
    Case("by area, not by points", dress.surfaces_of, (
        np.array(["visor"] * 3 + ["rim"] * 4), np.array([[0, 1, 2], [1, 3, 2], [3, 4, 6], [4, 5, 6]]), "skin",
        np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [1.1, 1, 0], [1.2, 1, 0], [1.1, 1.1, 0]])), {"visor"}),
    *[Case(f"the {role} wears the paint", dress.surfaces_of, (
        np.array(["visor", "visor", "visor", "shell"]), STRIP_FACES[:2], role, SQUARE), {"visor"})
      for role in ("skin", "hair")],
    # the take's unseen paint left blotches of the joints' dark (2026-10-23): an island under STRAY_ISLAND joins the
    # surface round it; a large one and a one-surface part stay, and the strays measure sees it before, none after
    Case("a stray blotch measured", dress.stray_share, stray_cloth(), Holds("0.25%", lambda share: round(
        share, 6) == 0.0025)),
    Case("a stray blotch takes the surface round it", dress.without_strays, stray_cloth(), Holds(
        "the blotch grey, the panel brown, the visor kept, no stray left", lambda merged: (
            merged[500] == merged[501] == "grey" and set(merged[:400]) == {"brown"} and merged[700] == "visor"
            and dress.stray_share(*stray_cloth()[:2], merged, stray_cloth()[3]) == 0.0))),
    # a body in flat factors is not dressed; only its library surface in all three baked maps is
    Case("the library's colour as a flat factor", dress.flat_materials, (cloth_material(()),), ["cloth#0"]),
    Case("two maps of three", dress.flat_materials, (cloth_material(("base", "rough")),), ["cloth#0"]),
    Case("three maps baked", dress.flat_materials, (cloth_material(("base", "rough", "normal")),), []),
    Case("baked maps naming no library", dress.flat_materials,
         (cloth_material(("base", "rough", "normal"), library=False),), ["cloth#0"]),
    # owner, 2026-10-25, "Each one looks different": variant n wears the n-th of its surface's family by colour
    # nearness (itself first), a rigid part its own; a library too small to tell two apart is a gap
    *[Case(f"skin variant {number}", dress.worn_name, ("skin_a", SURFACES, {"variant": number}, "skin"), worn)
      for number, worn in enumerate(["skin_a", "skin_b", "skin_c", "skin_a"])],
    Case("the visor kept in variant 1", dress.worn_name, ("visor", SURFACES, {"variant": 1}, "hard"), "visor"),
    Case("worn as painted beside a named surface", dress.worn_name,
         ("suit_white", SURFACES, {"surface": "suit_grey", "variant": 1}, "cloth"), "suit_white"),
    Case("suit_blue the library lacks", dress.worn_name, ("suit_white", SURFACES, {"surface": "suit_blue"}, "cloth"),
         Raises(RuntimeError, ("suit_blue", "people_refresh"))),
    *[Case(f"variant {number} told apart", dress.variant_gap, (WORN, SURFACES, {"variant": number}), None)
      for number in range(6)],
    Case("variant 6 a gap", dress.variant_gap, (WORN, SURFACES, {"variant": 6}),
         Contains(("variant 0", "fabric, skin"))),
    # which looks get a full body is the design's: a quarter of the frame's height is full, a twentieth far, no
    # share measured full, a crowd's look far; the share is the tallest of the row's boxes over the picture's height
    Case("full or far by share", full.full_looks, (SHARE_DESIGN,), {"near-work", "plain-work"}),
    Case("the tallest box's share", people_rows.concept_share, (TALLEST, [2752, 1536]), 0.25),
    Case("one box's share", people_rows.concept_share, ({"box": [0, 0, 10, 153.6]}, [2752, 1536]), 0.1),
    Case("no box, no share", people_rows.concept_share, ({}, [2752, 1536]), None),
    Case("no picture size, no share", people_rows.concept_share, (TALLEST, None), None),
    Case("clearance eases out and back", clearance.spread, (np.eye(1, 20, 10).ravel() * 0.3,), Holds(
        "the peak kept, eased before it, still at the ends", lambda eased: eased[10] >= 0.3 and eased[8] > 0
        and eased[0] == 0 and eased[19] == 0)),
]


def loop_ends(folder, finish=None, painted=True):
    """The shared loop's ends (made.ENDS) for two looks of the people line and one object: the player made and
    painted, Nev's take never baked; `finish` written over the take's finished model after pixal recorded it, and
    with `painted` False the bake's labelled take of the player missing."""
    ends = {name: folder / name for name in ("props-inputs", "surfaces-bake", "surfaces-parts", "likeness", "pixal")}
    for path in ends.values():
        path.mkdir(parents=True)
    for path in pixal_row.take_files("pp-player"):  # where pixal@people's batch brought the take
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".svviews":
            path.mkdir(exist_ok=True)
            (path / "input.png").write_bytes(b"the close-up")
        else:
            path.write_bytes(path.name.encode())
    (ends["pixal"] / "takes.json").write_text(json.dumps({"player-work": {
        "take": "pp-player", **{path.name: pixal_row.file_hash(path) for path in pixal_row.take_files("pp-player")}}}))
    if finish is not None:
        pixal_row.take_files("pp-player")[1].write_bytes(finish)
    rows = [{"id": "player-work", "take": "pp-player", "layer": "people", "failures": {"take": "made before the loop"}},
            {"id": "nev-space", "take": "pp-nev", "layer": "people"}, {"id": "crate", "take": "crate-s1"}]
    (ends["props-inputs"] / "rows.json").write_text(json.dumps({"rows": [dict({"layer": "objects"}, **row)
                                                                         for row in rows]}))
    (ends["likeness"] / "likeness.json").write_text(json.dumps({"objects": {
        row["id"]: {"route": "prop"} for row in rows}}))
    (ends["surfaces-bake"] / "baked.json").write_text(json.dumps({"player-work": {"parts": "pp-player"}}))
    (ends["surfaces-bake"] / "labelled" / "pp-player").mkdir(parents=True)
    if painted:
        np.savez(ends["surfaces-bake"] / "labelled" / "pp-player" / "pp-player.npz", points=np.zeros((1, 3)),
                 names=np.array(["navy_twill__navy_r080_m000_s7"]), surface=np.zeros(1, int))
    (ends["surfaces-bake"] / "specs.json").write_text(json.dumps({
        "navy_twill__navy_r080_m000_s7": {"library": "navy_twill", "metal": 0.0}, "steel": {"library": "steel"}}))
    (ends["surfaces-parts"] / "parts.json").write_text(json.dumps({"takes": {
        "pp-player": {"parts": [{"part": 0, "surface": "navy_twill"}]}}}))
    return ends


# The loop's takes: (name, bytes over the finished model, the bake painted it, the player's entry when a gap, the
# made check's answer). #26: only the bytes pixal@people's takes.json names are handed on.
TAKES = [("as made", None, True, None, "pass"),
         ("another finish", b"another finish", True, {"gap": "pp-player-final.glb not the bytes pixal made"}, "fail"),
         ("unpainted", None, False, {"gap": "the bake painted no labelled take pp-player"}, "fail")]


def baked_document():
    """A two-triangle skinned primitive with a morph target, in glb_file's form (document, views)."""
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.float32)
    arrays = [points, np.tile(np.array([[0, 0, 1]], np.float32), (4, 1)), np.arange(16, dtype=np.uint8).reshape(4, 4),
              points * 0.5, np.array([0, 1, 2, 1, 3, 2], dtype=np.uint32)]
    kinds = [(5126, "VEC3"), (5126, "VEC3"), (5121, "VEC4"), (5126, "VEC3"), (5125, "SCALAR")]
    document = {"bufferViews": [{"buffer": 0, "byteLength": array.nbytes} for array in arrays],
                "accessors": [{"bufferView": number, "componentType": kind, "count": len(array), "type": shape}
                              for number, (array, (kind, shape)) in enumerate(zip(arrays, kinds))],
                "materials": [{"name": "cloth", "extras": {"library": "suit"}}],
                "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "JOINTS_0": 2},
                                            "targets": [{"POSITION": 3}], "indices": 4, "material": 0}]}]}
    return document, [array.tobytes() for array in arrays]


class CollarTake:
    """The take under an open collar: the garment's suit, the collar's skin past x 2, and deeper than 5 mm only skin,
    18 mm off."""
    def labels(self, points, normals):
        sunk = points[:, 2] < -0.005
        return (np.where(sunk | (points[:, 0] >= 2), "skin", "suit"), np.where(sunk, 0.018, 0.004))


def test_looks_dressed_from_the_library_and_judged_by_measure(tmp_path):
    for case in CASES:
        meets(outcome(case, tmp_path / "cases"), case.expected, case.name)

    # the loop's hand-on (#41): people-made@people hands on every look of the people layer with its painted take,
    # names the rest by their gap, and fails only when none came through
    made = {}
    for name, finish, painted, gap, answer in TAKES:
        ends, out = loop_ends(tmp_path / name, finish, painted), tmp_path / name / "out"
        out.mkdir()
        loop.make(ends, out, 0, {})
        found = json.loads((out / "made.json").read_text())
        assert sorted(found) == ["nev-space", "player-work"], (name, found)  # the object is not the people layer's
        assert "no baked model" in found["nev-space"]["gap"], (name, found)
        assert gap is None or found["player-work"] == gap, (name, found)
        assert loop.judge_made(out, ends, {}).answer == answer, name
        made[name] = ends, out, found
    ends, out, found = made["as made"]
    player = found["player-work"]
    assert player["finishes"] == [{"part": 0, "surface": "navy_twill"}] and (out / player["labelled"]).exists()
    assert player["failures"] == {"take": "made before the loop"}, player  # named, never silent
    # its place in the bake output, never a home's absolute path (it moved with every frozen home, 2026-11-10)
    assert player["model"] == "made/player-work.gltf", player
    # the surfaces with the list's settings the bake painted, resolved from its specs.json for the dress
    assert player["specs"] == {"navy_twill__navy_r080_m000_s7": {"library": "navy_twill", "metal": 0.0}}, player
    assert (out / player["files"] / "pp-player.svviews" / "input.png").read_bytes() == b"the close-up"  # #26
    verdict = loop.judge_made(out, ends, {})
    assert verdict.measures["gaps"] == 1 and verdict.measures["named_failures"] == 1, verdict
    assert "nev-space" in verdict.findings[0], verdict
    assert dress.painted_take({f"{bodies.MADE}@{bodies.LINE}": out}, "player-work") == \
        out / "labelled" / "pp-player.npz"
    for gone in ("nev-space", "guard-guard-uniform"):
        refused = outcome(Case(gone, bodies.refused_on_gap, (out, gone), None), tmp_path / "refused")
        assert isinstance(refused, graph.Blocked) and "made no model" in str(refused), (gone, refused)
    # the laid take, the people line's own inputs: laid again over itself with plain copies, the same bytes never
    # written again, another's file replaced whole, no partial left
    laid = tmp_path / "laid"
    bodies.laid_take(out, "player-work", laid)
    stamps = {path: path.stat().st_ctime_ns for path in laid.rglob("*") if path.is_file()}
    bodies.laid_take(out, "player-work", laid)
    assert sorted(path.name for path in laid.iterdir()) == ["pp-player-final.glb", "pp-player.glb",
                                                            "pp-player.svviews"]
    assert {path: path.stat().st_ctime_ns for path in stamps} == stamps
    changed = laid / "pp-player.glb"
    changed.write_bytes(b"remade in place")
    before = changed.stat().st_ino
    bodies.laid_take(out, "player-work", laid)
    assert changed.read_bytes() == b"pp-player.glb" and changed.stat().st_ino != before
    assert not list(laid.glob(".*.laying"))
    # the batch gaps: a look whose take a paid step left out in the batch (a batch gap the likeness carries) moves by
    # name in the table's gate (stages.BATCH_GATES), camp's astronaut_1 2026-11-10; a gap naming another look moves
    # nothing
    ends, out, _ = made["another finish"]
    table = {row.name: row for row in stages.STAGES}
    gate = next(check for check in table[loop.ROW].checks if check.name == "made")
    for named, answer in ((["nev-space"], "fail"), (["nev-space", "player-work"], "pass")):
        batch_gaps.write(ends["likeness"], [batch_gaps.gap(f"{gone}: no finish list", "finish-route-list",
                                                           "library first", [gone], ["no answer"], "left out")
                                            for gone in named])
        assert gate.judge(out, ends, {}).answer == answer, named

    # the stage table: people are made by the loop on a line no place owns (#41), no side route of their own; the
    # looks' dress, parts and body rows wait on it, read the take from the store (#26), the parts are their own
    # priced row (#21), the clips made inside the batch (#26), and each full look has its own page row
    assert not [row for row in table if row.startswith(("people-route", "people-parts", "people-paint"))]
    assert table[loop.ROW].applies(bodies.LINE) and not table[loop.ROW].applies("hub")
    for name in ("props-inputs", "closeup", "pixal", "finish-route-views", "surfaces-bake", "likeness"):
        assert table[name].applies is None or table[name].applies(bodies.LINE), name
    for name in ("assembly", "complete", "library"):
        assert not table[name].applies(bodies.LINE) and table[name].applies("hub"), name
    assert loop.ROW == bodies.MADE and shapes_first.no_place(bodies.LINE)
    built = {row.name: row for row in bodies.rows()}
    assert made_clips.ROW_STAGE.paid and set(made_clips.CLIPS) >= {"standing", "walking", "bench"}
    assert {person["doing"] for place in json.loads((REPO / "data/people/rows.json").read_text())["places"]
            for person in people_rows.persons(place)} <= set(made_clips.CLIPS), "a cast does a clip no body has"
    for name in bodies.looks():
        dressed, parts, body = table[f"people-dress-{name}"], table[f"{bodies.PARTS}-{name}"], \
            table[f"{bodies.BODY}-{name}"]
        for row in (dressed, parts, body):
            assert bodies.MADE in row.beside and row.neighbours(None) == [bodies.LINE], row.name
        for row in (parts, body):
            files = row.files(None) if callable(row.files) else row.files
            assert not [path for path in files.values() if "work/pixal" in str(path)], files
        dress_row = people.dress_row(name)
        assert dress_row.paid and "baked" in {check.name for check in dress_row.checks}, dress_row
        assert set(dress_row.beside) == {bodies.MADE, "finish-route-palette", "surface-library", "surfaces-bake"}
        parts, body = built[f"{bodies.PARTS}-{name}"], built[f"{bodies.BODY}-{name}"]
        assert parts.paid and "clips" not in parts.files, parts
        assert body.after[parts.name] == (bodies.PARTS, 1) and body.euros < 3.0, body
        assert body.after[made_clips.ROW] == (made_clips.ROW, 1) and "clips" not in body.files, body
    variant = people.dress_row("astronaut-made", "suit_grey", 3)
    assert (variant.name, variant.params) == ("people-dress-astronaut-made-in-suit_grey-v3",
                                              {"surface": "suit_grey", "variant": 3})
    pages = {row.name: row for row in people.LOOKS}
    assert set(pages) == {f"{look.ROW}-{name}" for name in people.FULL}
    for name in people.FULL:  # one look runs without the others, reading its own body and dress only
        assert set(pages[f"{look.ROW}-{name}"].after) == {f"people-dress-{name}", f"{bodies.BODY}-{name}"}
    # the line's hand-in is approved by its picks, so its likeness is measured, not blocked
    assert json.loads((REPO / "data/props/people.json").read_text()).get("approved")

    # the body rows follow the design's share and nothing else: today's tube player is full and the square's crowd
    # far, every rule on one FAR_SHARE; the tube's person shrunk makes its look far, the crowd's look given to a near
    # person makes it full
    assert full.FAR_SHARE == spread.FAR_SHARE == contents.FAR_SHARE
    design = json.loads(bodies.DESIGN.read_text())
    tube = design["places"]["tube"]["rows"]["person_right"]
    assert tube["looks"] == ["person_uniform-made"], tube
    designs = [("today", design, {"person_uniform-made": False, "crowd-made": True}),
               ("tube shrunk", {**design, "places": {**design["places"], "tube": {
                   **design["places"]["tube"], "rows": {"person_right": {**tube, "share": 0.05}}}}},
                {"person_uniform-made": True}),
               ("crowd near", {"places": {"p": {"rows": {"near": {"looks": ["crowd-made"], "share": 0.3}}}}},
                {"person_uniform-made": True, "crowd-made": False})]
    held = bodies.DESIGN
    try:
        for name, shares, far_only in designs:
            bodies.DESIGN = tmp_path / f"{name}.json"
            bodies.DESIGN.write_text(json.dumps(shares))
            looks = bodies.looks()
            assert {key: bool(looks[key].get("far_only")) for key in far_only} == far_only, (name, looks)
    finally:
        bodies.DESIGN = held

    # a look's parts pass only when every part is named with a role and a material and the split fits the take's
    # finished model as the loop hands it on (env1, 2026-11-08: the astronaut's parts, made on an older finished
    # model, scattered over the new one, 0.604 of neighbouring faces in one part); a body is refused on parts that
    # do not fit, and the accepted parts replace older ones in the candidate
    folder, handed = tmp_path / "parts", tmp_path / "made"
    takes = handed / "takes" / "pp-a_s1"
    takes.mkdir(parents=True)
    sphere = trimesh.creation.icosphere(subdivisions=3)
    sphere.export(takes / "pp-a_s1-final.glb")
    quarters = (sphere.triangles_center[:, 0] > 0).astype(int) + 2 * (sphere.triangles_center[:, 1] > 0)
    named = [{"name": "coat", "role": "garment", "material": "FABRIC"}, {"name": "boot_r", "role": "hard"}]
    written(folder, {"parts.npz": {"part_of": quarters}, "parts.json": {"take": "pp-a_s1", "parts": named}})
    inputs = {"people-made@people": str(handed)}
    assert bodies.judge_parts(folder, inputs, {}).answer == "fail", "a part with no material passed"
    named[1]["material"] = "LEATHER"
    (folder / "parts.json").write_text(json.dumps({"take": "pp-a_s1", "parts": named}))
    judged = bodies.judge_parts(folder, inputs, {})
    assert judged.answer == "pass" and judged.measures["fit"] >= bodies.PARTS_FIT_LEAST, judged
    bodies.refused_on_misfit(folder, takes, "pp-a_s1", "people-body-x")
    laid = tmp_path / "candidate"
    written(laid, {"parts.npz": {"part_of": np.random.default_rng(1).permutation(quarters)},
                   "parts.json": {"take": "pp-a_s1", "parts": named}})
    assert bodies.judge_parts(laid, inputs, {}).answer == "fail", "parts of another finished model passed"
    meets(outcome(Case("scattered", bodies.refused_on_misfit, (laid, takes, "pp-a_s1", "people-body-x"), None),
                  tmp_path / "refused"), Raises(graph.Blocked, ("do not fit",)), "a body built on scattered parts")
    bodies.laid_parts(folder, laid)
    assert (laid / "parts.npz").read_bytes() == (folder / "parts.npz").read_bytes(), "the older parts stayed"
    painted = {"boots_brown__boot_brown_r065": {}, "helmet_visor__visor_black_r005": {}}
    assert not bodies.kept_parts(folder, takes, "pp-a_s1", painted), "parts judged on the work suit's names kept"
    (folder / "parts.json").write_text(json.dumps({"take": "pp-a_s1", "parts": named, "painted": sorted(painted)}))
    assert bodies.kept_parts(folder, takes, "pp-a_s1", painted)
    assert not bodies.kept_parts(laid, takes, "pp-a_s1", {}), "parts of another finished model kept"

    # the dress's binary chunk: written and read back whole, index lists appended to it
    blob = np.arange(9, dtype=np.float32).tobytes()
    document = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(blob)}],
                "bufferViews": [{"buffer": 0, "byteLength": len(blob)}],
                "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"}]}
    rest = len(blob).to_bytes(4, "little") + b"BIN\x00" + blob
    dress.write_glb(tmp_path / "a.glb", document, rest)
    read, kept = dress.read_glb(tmp_path / "a.glb")
    assert kept == rest and read["asset"] == document["asset"]
    assert np.allclose(dress.positions(read, kept, 0).ravel(), np.arange(9))
    binary = dress.Binary(read, kept)
    number = binary.indices(np.array([[0, 1, 2]]))
    kept = binary.rest()
    assert np.allclose(dress.positions(read, kept, 0).ravel(), np.arange(9))
    assert dress.accessor(read, kept, number).ravel().tolist() == [0, 1, 2]
    assert read["buffers"][0]["byteLength"] == len(kept) - 8
    # the bake's coordinates: a vertex whose corners the bake laid at two coordinates becomes two vertices, each
    # carrying its joints and its corrective's offset, and the triangles keep their corners
    document, views = baked_document()
    lists, points, _, triangles, owners = baked_body.triangles_of(document, views)
    assert owners == [(0, 0), (0, 0)] and triangles.tolist() == [[0, 1, 2], [1, 3, 2]]
    uvs = np.array([[[0, 0], [0.5, 0], [0, 0.5]], [[0.9, 0.9], [0.6, 0.6], [0, 0.5]]])  # vertex 1 lies twice
    baked_body.laid_coordinates(document, views, lists, uvs)
    primitive = document["meshes"][0]["primitives"][0]
    corners = glb_file.accessor_array(document, views, primitive["indices"]).reshape(-1, 3)
    laid_points = glb_file.accessor_array(document, views, primitive["attributes"]["POSITION"])
    assert len(laid_points) == 5 and np.allclose(laid_points[corners], points[triangles])
    assert np.allclose(glb_file.accessor_array(document, views, primitive["attributes"]["TEXCOORD_0"])[corners], uvs)
    joints = glb_file.accessor_array(document, views, primitive["attributes"]["JOINTS_0"])
    assert np.array_equal(joints[corners], np.arange(16).reshape(4, 4)[triangles])
    target = glb_file.accessor_array(document, views, primitive["targets"][0]["POSITION"])
    assert np.allclose(target[corners], points[triangles] * 0.5)
    # the route's under layer, a second primitive in the garment's material 1 cm under it, reads no paint of its own
    # (the pilot's read the open collar's skin and failed aligned at 1.38 cm with the garment's few skin points)
    collar = STRIP.copy()
    collar[6:, 0] = 2.2  # the skin of the open collar: less of the garment's area than its suit
    under = collar - [0.0, 0.0, 0.01]
    blob = b"".join(found.astype(dtype).tobytes() for found, dtype in (
        (collar, np.float32), (STRIP_FACES, np.uint32), (under, np.float32)))
    sizes = [(0, 96, 5126, "VEC3", 8), (96, STRIP_FACES.size * 4, 5125, "SCALAR", STRIP_FACES.size),
             (96 + STRIP_FACES.size * 4, 96, 5126, "VEC3", 8)]
    document = {"bufferViews": [{"buffer": 0, "byteOffset": start, "byteLength": size} for start, size, *_ in sizes],
                "accessors": [{"bufferView": number, "componentType": kind, "type": shape, "count": count}
                              for number, (_, _, kind, shape, count) in enumerate(sizes)]}
    primitives = [{"attributes": {"POSITION": 0}, "indices": 1, "material": 0},
                  {"attributes": {"POSITION": 2}, "indices": 1, "material": 0}]
    (_, worn, _), (_, layer, apart) = dress.painted_primitives(
        document, len(blob).to_bytes(4, "little") + b"BIN\x00" + blob, primitives, CollarTake(), ["garment"] * 2)
    assert set(worn) == {"suit", "skin"} and set(layer) == {"suit"} and set(apart) == {0.018}

    # the people line's scene library (batch 1, 2026-10-25): the variants come from surface-library@people, never
    # the repo's method library, which holds no variant; a named material forgets its print (the face was a cutout
    # of the close-up, owner 2026-10-23)
    method = json.loads((REPO / "data/library/materials.json").read_text())
    recipe = next(iter(method["recipes"]))
    scene = {**method, "tokens": {"pale": "#e0d0c0", "dark": "#302820", "blue": "#203060", "grey": "#808080"},
             "families": {"skin": {"variants": {"skin_pale": {"recipe": recipe, "token": "pale"},
                                                "skin_dark": {"recipe": recipe, "token": "dark"}}},
                          "fabric": {"variants": {"cloth_blue": {"recipe": recipe, "token": "blue"},
                                                  "cloth_grey": {"recipe": recipe, "token": "grey"}}}}}
    library = tmp_path / "scene"
    written(library, {"palette/palette.json": {"tokens": scene["tokens"], "wear": {
        "level": "worked", "dirt": 0.2, "dirt_token": "grey"}}, "library/materials.json": scene})
    surfaces = dress.library_surfaces({"finish-route-palette@people": library / "palette",
                                       "surface-library@people": library / "library"})
    assert {name: spec["family"] for name, spec in surfaces.items()} == {
        "skin_pale": "skin", "skin_dark": "skin", "cloth_blue": "fabric", "cloth_grey": "fabric"}
    assert dress.variant_gap({"skin#0": {"painted": "skin_pale", "role": "skin"},
                              "suit#1": {"painted": "cloth_blue", "role": "cloth"}}, surfaces, {"variant": 1}) is None
    assert dress.worn_name("cloth_blue", surfaces, {"variant": 1}, "cloth") == "cloth_grey"
    material = {"extras": {"role": "skin", "print": True}}
    dress.named(material, "visor__black_r005", {"library": "helmet_visor"})
    assert material["extras"] == {"role": "skin", "library": "visor__black_r005", "surface": "helmet_visor"}
