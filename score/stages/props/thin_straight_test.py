"""The thin straight code route (thin_straight.py): which rows it takes, the model it sweeps, the take it writes where
the finish route and the likeness row read one, and the Pixal3D row building it for a row whose close-up failed.

Breaks (applied once, seen red, reverted): build ignoring its mask (always the one straight sweep) turns
test_a_thin_row_whose_mask_is_not_one_straight_run_is_built_along_its_mask_s_path red (the elbow's outline 0.04);
write_take standing its final again (`mesh.apply_transform(finish_turn(pixal / f"{take}.glb"))` before the final's
export) turns it red too (the elbow turned off its mask). likeness_row.model_checks fitting a slender model to its box
side by side again (`if thin_straight.slender(size):` -> `if False:`) turns
test_a_thin_run_is_held_to_its_path_s_own_size_never_crushed_to_its_box red (the sag's tube read 2 mm thick); so do
thin_straight.upward laying a tie on the ground (`return 0`: the sag's outline 0.155) and fittings returning none
(`if not kind_words(row) & FITTED:` -> `if True:`: the bend no thicker at its elbow).

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/stages/props/thin_straight_test.py
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import score.stages.batch_gaps as batch_gaps  # noqa: E402
import score.stages.props.likeness as likeness  # noqa: E402
import score.stages.props.pixal_row as pixal_row  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402
import score.stages.props.thin_straight as thin_straight  # noqa: E402

PIPE = {"id": "pipe", "name": "wall pipe", "noun": "pipe", "size": [4.0, 0.1, 0.1], "view": "v1",
        "box": [40, 90, 560, 110]}
POST = {"id": "porch_post", "name": "wooden post", "size": [0.1, 0.1, 2.5], "view": "v1", "box": [290, 0, 310, 200]}


def concept(path, colour=(180, 30, 30)):
    """A busy concept: a thin bar across it, on a wall with a crate behind it that its box's cut would keep."""
    pixels = np.full((200, 600, 3), 140, dtype=np.uint8)
    pixels[60:140, 200:320] = (60, 90, 200)
    pixels[90:110, 40:560] = colour
    Image.fromarray(pixels).save(path)
    return path


def bar_mask(path, box):
    """SAM 3's mask of the thing in `box` on the concept: exactly its pixels."""
    pixels = np.zeros((200, 600), dtype=np.uint8)
    pixels[box[1]:box[3], box[0]:box[2]] = 255
    Image.fromarray(pixels).save(path)
    return path


def cut(tmp_path, row):
    """The row's concept crop cut out by its SAM 3 mask."""
    return thin_straight.cut_by_mask(concept(tmp_path / "concept.png"), row["box"],
                                     bar_mask(tmp_path / f"{row['id']}.png", row["box"]))


def test_only_thin_rows_of_a_straight_kind_are_taken():
    assert thin_straight.thin_straight(PIPE) and thin_straight.thin_straight(POST)
    assert thin_straight.thin_straight({"name": "bundles of cables", "size": [0.2, 0.1, 4.35]})
    assert not thin_straight.thin_straight({"name": "coiled hose", "size": [0.4, 0.4, 0.2]})  # not slender
    assert thin_straight.thin_straight({"name": "communications tower", "noun": "tower", "size": [2.0, 2.0, 15.0]})
    assert not thin_straight.thin_straight({"name": "computer tower", "noun": "computer", "size": [0.2, 0.4, 0.5]})
    assert not thin_straight.thin_straight({"name": "wall poster", "size": [0.4, 0.01, 0.6]})  # post is not poster
    assert thin_straight.thin_straight({"name": "metal railings", "size": [9.435, 0.1, 1.0]})  # posts and rails
    assert thin_straight.profile({"name": "glass balustrade"}) == "railing"
    assert thin_straight.thin_straight({"name": "strip floor light", "noun": "light", "size": [0.8, 0.1, 0.05]})  # glows
    assert thin_straight.thin_straight({"name": "string lights", "noun": "lights", "size": [3.0, 0.05, 0.05]})
    assert thin_straight.profile({"name": "lantern string", "noun": "lanterns"}) == "round"  # its cable
    assert not thin_straight.thin_straight({"name": "wall poster", "noun": "poster", "size": [3.0, 0.05, 0.05]})
    assert thin_straight.thin_straight({"name": "street lamp", "noun": "lamp", "size": [0.5, 0.5, 6.0]})  # a stem lamp
    assert not thin_straight.thin_straight({"name": "desk lamp", "noun": "lamp", "size": [0.2, 0.2, 0.5]})  # no stem


def test_the_profile_is_swept_along_the_longest_side_at_the_row_s_size():
    pipe = thin_straight.build(PIPE)
    assert np.allclose(pipe.extents, [0.1, 0.1, 4.0]) and np.allclose(pipe.bounds.mean(0), 0.0)  # along z
    assert pipe.is_watertight and thin_straight.profile(PIPE) == "round"
    assert len(pipe.vertices) > 8  # round, not a box
    post = thin_straight.build(POST)  # size is wide, deep, tall: the post stands 2.5 m up y
    assert np.allclose(post.extents, [0.1, 2.5, 0.1]) and thin_straight.profile(POST) == "rect"
    assert len(post.vertices) == 8


def test_a_railing_is_posts_at_most_a_post_gap_apart_under_a_top_and_a_mid_rail(tmp_path):
    row = {"id": "railing", "name": "metal railing", "noun": "railing", "size": [9.435, 0.1, 1.0], "view": "v1"}
    built = thin_straight.build(row)
    assert np.allclose(built.extents, [0.1, 1.0, 9.435]) and np.allclose(built.bounds.mean(0), 0.0)
    parts = thin_straight.railing(*built.extents)
    posts = [part for part in parts if np.allclose(part.extents, [0.1, 1.0, 0.1])]
    rails = [part for part in parts if part.extents[2] > 9.4]
    assert len(posts) == 8 and len(rails) == 2  # 9.435 m in bays of at most 1.5 m: 7 bays
    gaps = np.diff(sorted(post.bounds.mean(0)[2] for post in posts))
    assert gaps.max() <= thin_straight.POST_GAP and np.allclose(gaps, gaps[0])
    assert sorted(round(rail.bounds[1][1], 3) for rail in rails) == [0.025, 0.5]  # the mid rail, the top rail
    pixal = tmp_path / "pixal"
    pixal.mkdir()
    picture = Image.new("RGBA", (40, 10), (90, 90, 90, 255))
    assert thin_straight.write_take("railing_1", row, picture, 4000, pixal, tmp_path / "railing.png")
    import trimesh
    assert np.allclose(trimesh.load(pixal / "railing_1-final.glb", force="mesh").extents, [0.1, 1.0, 9.435], atol=0.01)


def test_the_take_is_written_where_the_finish_route_and_the_likeness_row_read_it(tmp_path, monkeypatch):
    pixal = tmp_path / "pixal"
    pixal.mkdir()
    assert thin_straight.write_take("garage_pipe_1", PIPE, cut(tmp_path, PIPE), 4000, pixal, tmp_path / "pipe.png")
    for name in ("garage_pipe_1.glb", "garage_pipe_1-final.glb", "garage_pipe_1-4000.glb",
                 "garage_pipe_1.svviews/input.png"):
        assert (pixal / name).exists(), name
    assert thin_straight.code_built("garage_pipe_1", pixal)
    # its one colour is the bar's, which the finish route measures as the model's own texture (route_cast)
    import trimesh
    loaded = trimesh.load(pixal / "garage_pipe_1.glb", force="scene")
    factor = next(iter(loaded.geometry.values())).visual.material.baseColorFactor
    assert np.abs(factor[:3].astype(int) - [180, 30, 30]).max() <= 6, factor  # the crop is a JPEG
    # the paint replays the finish's turn from the slimmed file onto the final one (labels.finish_turn): none here
    with prop_data.tools("props/library", "props"):
        import labels
    monkeypatch.setattr(labels, "PIXAL", pixal)
    assert np.array_equal(labels.finish_turn("garage_pipe_1"), np.eye(3))  # made in its own pose, never stood
    assert np.allclose(trimesh.load(pixal / "garage_pipe_1-final.glb", force="mesh").extents, [0.1, 0.1, 4.0], atol=0.01)
    # the likeness row holds it to the crop cut by its mask: the bar's own outline matches it, not the crate's
    outline = likeness.best_way(pixal / "garage_pipe_1-final.glb", pixal / "garage_pipe_1.svviews/input.png",
                                PIPE["size"])["outline"]
    assert outline >= likeness.OUTLINE_LEAST, outline
    # a square post comes out of the finish's stand square, as built (glb_file.squared turned one set square 45 degrees)
    assert thin_straight.write_take("post_1", POST, cut(tmp_path, POST), 4000, pixal, tmp_path / "porch_post.png")
    assert np.allclose(trimesh.load(pixal / "post_1-final.glb", force="mesh").extents, [0.1, 2.5, 0.1], atol=0.01)
    labels.finish_turn("post_1")
    thin_straight.unbuild("post_1", pixal)
    thin_straight.unbuild("garage_pipe_1", pixal)
    assert not list(pixal.iterdir())


def test_an_empty_mask_cuts_nothing(tmp_path):
    assert thin_straight.cut_by_mask(concept(tmp_path / "concept.png"), PIPE["box"],
                                     bar_mask(tmp_path / "empty.png", [0, 0, 0, 0])) is None


def test_the_mask_jobs_ask_each_row_s_own_mask_by_its_words_in_its_box():
    jobs = thin_straight.mask_jobs({"pipe": PIPE, "porch_post": POST}, {"pipe": "a.png", "porch_post": "a.png"})
    assert jobs == [{"picture": "a.png", "rows": [
        {"key": "pipe", "nouns": ["wall pipe", "pipe"], "box": PIPE["box"], "mask": True},
        {"key": "porch_post", "nouns": ["wooden post"], "box": POST["box"], "mask": True}]}]


def test_the_pixal_row_builds_a_failed_thin_row_and_drops_its_close_up_gap(tmp_path, monkeypatch):
    pixal = tmp_path / "pixal"
    pixal.mkdir()
    monkeypatch.setattr(pixal_row, "take_files",
                        lambda take: [pixal / f"{take}{suffix}" for suffix in pixal_row.SUFFIXES])
    closeup = tmp_path / "closeup"
    (closeup / "closeups").mkdir(parents=True)
    asked = []

    def masks(rows, concepts, folder):  # SAM 3 on its card, faked: the pipe's mask
        asked.append(sorted(rows))
        return {"pipe": bar_mask(tmp_path / "pipe.png", PIPE["box"])}

    monkeypatch.setattr(thin_straight, "concept_masks", masks)
    batch_gaps.write(closeup, [batch_gaps.gap(f"{row}: no close-up passed", "closeup", "close-up", (row, take),
                                              [], "every Pro take failed") for row, take in
                               (("pipe", "g_pipe"), ("hose", "g_hose"))])
    objects = {"pipe": {"route": "prop", "take": "g_pipe"}, "hose": {"route": "prop", "take": "g_hose"}}
    (tmp_path / "props.json").write_text(json.dumps({"place": "garage", "objects": objects}))
    (tmp_path / "inventory.json").write_text(json.dumps({"rows": [
        PIPE, {"id": "hose", "name": "coiled hose", "size": [0.4, 0.4, 0.2], "view": "v1", "box": [0, 0, 9, 9]}]}))
    (tmp_path / "surfaces.json").write_text(json.dumps({"takes": {"g_pipe": {}, "g_hose": {}}, "bake": {
        "models": {"garage_pipe": "g_pipe", "garage_hose": "g_hose"},
        "entries": {"garage_pipe": {"faces": 4000}, "garage_hose": {"faces": 4000}}}}))
    inputs = {"props": tmp_path / "props.json", "inventory": tmp_path / "inventory.json",
              "surfaces": tmp_path / "surfaces.json", "closeup": closeup, "view v1": concept(tmp_path / "concept.png")}
    out = tmp_path / "out"
    out.mkdir()
    pixal_row.make_pixal(inputs, out, 0, {})  # no close-up passed: nothing for the batch, so nothing rented
    takes = json.loads((out / "takes.json").read_text())
    assert list(takes) == ["pipe"] and "g_pipe.svviews" in takes["pipe"]
    gaps = [entry["name"] for entry in json.loads((out / batch_gaps.FILE).read_text())["gaps"]]
    assert gaps == ["hose: no close-up passed"], gaps  # the coiled hose is no straight thing: still a gap
    assert asked == [["pipe"]]  # only the thin straight row is masked
    pixal_row.make_pixal(inputs, out, 0, {})  # built already: kept, nothing masked again
    assert asked == [["pipe"]]


def test_a_pipe_whose_close_up_passed_is_built_in_code_with_its_place_s_failed_pipe(tmp_path, monkeypatch):
    """One route a kind in a place (thin_straight.kin): a pipe whose close-up failed and a pipe whose close-up passed
    both come out of the Pixal3D row built in code, and nothing goes to the batch."""
    pixal = tmp_path / "pixal"
    pixal.mkdir()
    monkeypatch.setattr(pixal_row, "take_files",
                        lambda take: [pixal / f"{take}{suffix}" for suffix in pixal_row.SUFFIXES])
    closeup = tmp_path / "closeup"
    (closeup / "closeups").mkdir(parents=True)
    Image.new("RGB", (8, 8)).save(closeup / "closeups" / "pipe_2.png")  # its close-up passed
    monkeypatch.setattr(thin_straight, "concept_masks", lambda rows, concepts, folder: {
        row: bar_mask(tmp_path / f"{row}.png", PIPE["box"]) for row in rows})
    batch_gaps.write(closeup, [batch_gaps.gap("pipe: no close-up passed", "closeup", "close-up", ("pipe", "g_pipe"),
                                              [], "every Pro take failed")])
    objects = {"pipe": {"route": "prop", "take": "g_pipe"}, "pipe_2": {"route": "prop", "take": "g_pipe_2"}}
    (tmp_path / "props.json").write_text(json.dumps({"place": "garage", "objects": objects}))
    (tmp_path / "inventory.json").write_text(json.dumps({"rows": [PIPE, {**PIPE, "id": "pipe_2"}]}))
    (tmp_path / "surfaces.json").write_text(json.dumps({"takes": {"g_pipe": {}, "g_pipe_2": {}}, "bake": {
        "models": {"garage_pipe": "g_pipe", "garage_pipe_2": "g_pipe_2"},
        "entries": {"garage_pipe": {"faces": 4000}, "garage_pipe_2": {"faces": 4000}}}}))
    inputs = {"props": tmp_path / "props.json", "inventory": tmp_path / "inventory.json",
              "surfaces": tmp_path / "surfaces.json", "closeup": closeup, "view v1": concept(tmp_path / "concept.png")}
    out = tmp_path / "out"
    out.mkdir()
    pixal_row.make_pixal(inputs, out, 0, {})  # a batch would need a cloud run: none is made
    assert not (out / "list.txt").exists()
    assert all(thin_straight.code_built(take, pixal) for take in ("g_pipe", "g_pipe_2"))
    assert sorted(json.loads((out / "takes.json").read_text())) == ["pipe", "pipe_2"]
    assert thin_straight.kin(set(), {"pipe": PIPE}) == set()  # no row of its kind failed: the picture route


def test_the_likeness_row_holds_a_code_take_to_its_crop_and_closes_its_gap_only_when_it_passes(tmp_path):
    import score.stages.props.likeness_row as likeness_row
    pixal = tmp_path / "pixal"
    pixal.mkdir()
    thin_straight.write_take("g_pipe", PIPE, cut(tmp_path, PIPE), 4000, pixal, tmp_path / "pipe.png")
    (tmp_path / "closeup/closeups").mkdir(parents=True)  # every Pro take failed: no close-up kept
    inputs = {"closeup": tmp_path / "closeup", "pixal input pipe": pixal / "g_pipe.svviews/input.png",
              "code take pipe": pixal / f"g_pipe.svviews/{thin_straight.MARK}"}
    record = {"place": "garage", "objects": {"pipe": {"route": "prop", "take": "g_pipe"}}}
    found = {"pipe": likeness_row.object_record(
        "pipe", record, inputs, {"g_pipe": pixal / "g_pipe-final.glb"},
        {"takes": {"g_pipe": {"parts": [{"words": "red pipe"}], "finishes": [{"finish": "red pipe"}]}}},
        {"pipe": PIPE}, set(), tmp_path / "cuts")}
    assert found["pipe"]["made"] == "code" and found["pipe"]["outline"] >= likeness.OUTLINE_LEAST, found
    assert likeness_row.free_passed(found, "pipe")
    assert not likeness_row.free_passed({"pipe": {**found["pipe"], "outline": 0.1}}, "pipe")


def held(tmp_path, row, lines, width=9):
    """(the likeness row's record, prepare's predicted faults) of the code build from a concept whose SAM 3 mask is
    `lines` (each a list of (x, y) points) drawn `width` pixels wide on a 600 by 200 picture."""
    import score.stages.complete.prepare.predict as predict
    import score.stages.props.likeness_row as likeness_row
    from PIL import ImageDraw
    folder = tmp_path / row["id"]
    folder.mkdir()
    mask = Image.new("L", (600, 200), 0)
    for line in lines:
        ImageDraw.Draw(mask).line(line, fill=255, width=width, joint="curve")
    mask.save(folder / "mask.png")
    Image.merge("RGB", [mask.point(lambda value: 140 + value // 4)] * 3).save(folder / "concept.png")
    box = list(mask.getbbox())
    picture = thin_straight.cut_by_mask(folder / "concept.png", box, folder / "mask.png")
    pixal = folder / "pixal"
    views = thin_straight.write_take("take", row, picture, 4000, pixal, folder / "mask.png")
    inputs = {"closeup": folder / "closeup", "pixal input it": views / "input.png",
              "code take it": views / thin_straight.MARK}
    found = likeness_row.object_record("it", {"place": "p", "objects": {"it": {"route": "prop", "take": "take"}}},
                                       inputs, {"take": pixal / "take-final.glb"}, {"takes": {}},
                                       {"it": {**row, "box": box}}, set(), folder / "cuts")
    found["code"] = json.loads((views / thin_straight.MARK).read_text())
    return found, predict.build_faults(pixal / "take-final.glb", views / "input.png", "p", "it", row, folder,
                                       straight=True)


def test_a_straight_thing_slanted_by_the_concept_s_view_passes_as_prepare_predicts(tmp_path):
    """The concept draws a straight thing at its camera's slant: the likeness row turns its cut upright or level
    (likeness_row.straight_cut) before the outline, and prepare's prediction holds the build the same way; it is
    still the one straight sweep, not a path build. A box the reading stood upright over a pipe its picture shows
    lying is built lying: the direction is the picture's, the metres the box's."""
    lying = {"id": "lying", "name": "wall pipe", "noun": "pipe", "size": [0.1, 0.1, 3.0], "view": "v1"}
    for row, line in ((POST, [(250, 190), (350, 10)]), (PIPE, [(60, 160), (540, 40)]), (lying, [(60, 120), (540, 90)])):
        found, faults = held(tmp_path, row, [line])
        assert found["outline"] >= likeness.OUTLINE_LEAST and found["code"]["profile"] != "path", (row["id"], found)
        assert not any(fault.startswith("outline") for fault in faults), faults
    import trimesh
    assert np.allclose(trimesh.load(tmp_path / "lying/pixal/take-final.glb", force="mesh").extents, [0.1, 0.1, 3.0],
                       atol=0.01)


def test_a_thin_row_whose_mask_is_not_one_straight_run_is_built_along_its_mask_s_path(tmp_path):
    """A bent pipe, a sagging string, a bundle of two cables and a railing's ladder (world 1's straight-masks,
    2026-10-26) each failed as one straight sweep: their build follows the mask's own path, its longest reach the
    row's longest side (a slender box's other sides need not agree with the picture), and the likeness row's outline and
    prepare's prediction both pass it."""
    import trimesh
    sag = [(x, 50 + 120 * (1 - ((x - 300) / 260) ** 2)) for x in range(40, 561, 10)]
    posts = [[(x, 30), (x, 170)] for x in np.linspace(40, 560, 7)]
    shapes = {"elbow": ({"name": "wall pipe", "noun": "pipe", "size": [4.0, 0.1, 0.8]},
                        [[(40, 60), (40, 170), (560, 170)]]),
              "sag": ({"name": "lantern string", "noun": "lanterns", "size": [6.0, 0.1, 1.0]}, [sag]),
              "bundle": ({"name": "pipe bundle", "noun": "pipes", "size": [4.0, 0.1, 0.4]},
                         [[(40, 80), (560, 80)], [(40, 120), (560, 120)]]),
              "ladder": ({"name": "metal railing", "noun": "railing", "size": [4.2, 0.1, 1.0]},
                         [[(40, 30), (560, 30)], [(40, 170), (560, 170)], *posts])}
    for name, (row, lines) in shapes.items():
        found, faults = held(tmp_path, {"id": name, "view": "v1", **row}, lines)
        assert found["code"]["profile"] == "path", name
        assert found["outline"] >= likeness.OUTLINE_LEAST and not faults, (name, found["outline"], faults)
        made = trimesh.load(tmp_path / name / "pixal" / "take-final.glb", force="mesh")
        assert np.isclose(made.extents.max(), row["size"][0], rtol=0.02), (name, made.extents)
        built = thin_straight.build({"view": "v1", **row}, np.asarray(Image.open(
            tmp_path / name / "pixal" / "take.svviews" / "input.png"))[..., 3] > 127)
        assert np.allclose(made.bounds, built.bounds, atol=1e-5), name  # the final keeps the pose it was built in


def test_a_thin_run_is_held_to_its_path_s_own_size_never_crushed_to_its_box(tmp_path):
    """A thin run's box is its thickness on its two short sides (world 1's lantern string 8 by 0.01 by 0.01, cables 10
    by 0.1 by 0.1, 2026-10-26), while its path is wider: the build keeps its path's reach (its longest the row's), its
    tube the line's drawn width at most the row's thinnest side (never under thin_straight.least_tube), a tie laid in
    a wall's plane unless it lies;
    the model check lays it as one scale, so its tube is measured whole; a wall pipe's L bend carries an elbow and
    clamps, a bundle of cables none."""
    import trimesh
    import score.stages.props.likeness_row as likeness_row
    sag = [(x, 40 + 100 * (1 - ((x - 300) / 260) ** 2)) for x in range(40, 561, 10)]
    shapes = {"sag": ({"name": "string lights", "noun": "lights", "size": [8.0, 0.1, 0.1],
                       "anchor": "on:left_building_facade"}, [sag], 0.1),
              "bend": ({"name": "wall pipe", "noun": "pipe", "size": [4.0, 0.05, 0.05], "anchor": "wall"},
                       [[(40, 40), (40, 170), (560, 170)]], 0.05),
              "bundle": ({"name": "power cables", "noun": "cables", "size": [6.0, 0.08, 0.08], "anchor": "wall"},
                         [[(40, 70), (560, 70)], [(40, 100), (560, 100)], [(40, 130), (560, 130)]], 0.08)}
    for name, (row, lines, tube) in shapes.items():
        found, faults = held(tmp_path, {"id": name, "view": "v1", **row}, lines)
        assert found["code"]["profile"] == "path" and not faults, (name, faults)
        assert found["outline"] >= likeness.OUTLINE_LEAST and found["model_check"]["pass"], (name, found)
        made = trimesh.load(tmp_path / name / "pixal" / "take-final.glb", force="mesh")
        across = sorted(made.extents)
        assert np.isclose(across[2], row["size"][0], rtol=0.02), (name, made.extents)
        assert across[1] > 10 * tube, (name, made.extents)  # its path's reach, not its box's thickness
        assert np.isclose(across[0], tube * (thin_straight.FITTING_SHARE if name == "bend" else 1.0), rtol=0.1), \
            (name, made.extents)
        assert found["model_check"]["thinnest"] >= 0.5 * tube, (name, found["model_check"])
    assert np.argmax(trimesh.load(tmp_path / "sag/pixal/take-final.glb", force="mesh").extents) == 2
    assert np.ptp(trimesh.load(tmp_path / "sag/pixal/take-final.glb", force="mesh").vertices[:, 1]) > 1.0  # it hangs
    wire = {"name": "wire", "noun": "wire", "size": [3.0, 0.001, 0.001]}
    assert thin_straight.lifted([np.array([[0.0, 0.0], [100.0, 20.0]])], wire, 3.0)[1] == thin_straight.least_tube()
    bend = {"view": "v1", **shapes["bend"][0]}
    laid, thick = thin_straight.lifted([np.array([[40.0, 40.0], [40.0, 170.0], [560.0, 170.0]])], bend, 9.0)
    fitted = thin_straight.fittings(laid, bend, thick)
    assert len(fitted["elbows"]) == 2 and not fitted["tees"]  # one elbow, its two legs
    assert len(fitted["clamps"]) == int(sum(np.linalg.norm(np.diff(run, axis=0), axis=1).sum()
                                            for run in laid) // thin_straight.BRACKET_GAP + 0.5)
    assert not any(thin_straight.fittings(laid, {**bend, "anchor": "floor"}, thick)["clamps"])  # off a wall: none
    assert not any(thin_straight.fittings(laid, {**bend, "noun": "cables", "name": "cables"}, thick).values())
    fork = [np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]]), np.array([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
            np.array([[0.0, 0.0, 0.0], [0.0, 0.0, -1.0]])]
    assert len(thin_straight.fittings(fork, {"name": "pipe", "size": [2.0, 0.1, 1.0]}, 0.1)["tees"]) == 3
    # the model check fitting the sag's mesh to its box side by side read its tube crushed (the old way)
    sag_mesh = trimesh.load(tmp_path / "sag/pixal/take-final.glb", force="mesh")
    with prop_data.tools("props/gates", "props/library", "props"):
        import model as model_gate
    assert model_gate.thinnest(sag_mesh, [0.1, 0.1, 8.0]) < 0.02
    assert likeness_row.model_checks(tmp_path / "sag/pixal/take-final.glb", [8.0, 0.1, 0.1], "p_sag",
                                     False)["model_check"]["thinnest"] >= 0.05


def test_the_masks_row_cuts_only_the_kept_thin_straight_rows_by_their_own_mask(tmp_path, monkeypatch):
    import score.stages.props.masks_row as masks_row
    asked = []

    def masks(rows, concepts, folder):  # SAM 3 on its card, faked: the pipe's mask, nothing for the post
        asked.append(sorted(rows))
        return {"pipe": bar_mask(tmp_path / "pipe.png", PIPE["box"])}

    monkeypatch.setattr(thin_straight, "concept_masks", masks)
    objects = {row: {"route": "prop", "take": f"g_{row}"} for row in ("pipe", "porch_post", "hose")}
    (tmp_path / "props.json").write_text(json.dumps({"place": "garage", "objects": objects}))
    (tmp_path / "inventory.json").write_text(json.dumps({"rows": [
        PIPE, POST, {"id": "hose", "name": "coiled hose", "size": [0.4, 0.4, 0.2], "view": "v1", "box": [0, 0, 9, 9]}]}))
    inputs = {"props": tmp_path / "props.json", "inventory": tmp_path / "inventory.json",
              "view v1": concept(tmp_path / "concept.png")}
    out = tmp_path / "out"
    out.mkdir()
    masks_row.make_masks(inputs, out, 0, {})
    assert asked == [["pipe", "porch_post"]]  # the coiled hose is no straight thing
    assert json.loads((out / "masks.json").read_text()) == {"asked": ["pipe", "porch_post"], "cut": ["pipe"]}
    assert Image.open(out / "cuts/pipe.png").mode == "RGBA"
    verdict = masks_row.judge_masks(out, inputs, None)
    assert verdict.answer == "pass" and "porch_post" in verdict.findings[0], verdict
    other = tmp_path / "other"
    other.mkdir()
    masks_row.make_masks(inputs, other, 0, {"objects": ["g_pipe"]})  # the object filter keeps the pipe alone
    assert asked[-1] == ["pipe"]
