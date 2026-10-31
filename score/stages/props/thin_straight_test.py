"""The thin straight code route (thin_straight.py): which rows it takes, the model it sweeps, the take it writes where
the finish route and the likeness row read one, and the Pixal3D row building every thin straight row, its close-up passed or failed.

Breaks (applied once, seen red, reverted): build ignoring its mask (always the one straight sweep) turns
test_a_thin_row_whose_mask_is_not_one_straight_run_is_built_along_its_mask_s_path red (the elbow's outline 0.04);
write_take standing its final again (`mesh.apply_transform(finish_turn(pixal / f"{take}.glb"))` before the final's
export) turns it red too (the elbow turned off its mask). likeness_row.model_checks fitting a slender model to its box
side by side again (`if thin_straight.slender(size):` -> `if False:`) turns
test_a_thin_run_is_held_to_its_path_s_own_size_never_crushed_to_its_box red (the sag's tube read 2 mm thick); so does
fittings returning none (`if not kind_words(row) & FITTED:` -> `if True:`: no elbow on the bend). make_pixal
handing coded only rows whose close-up failed (`and not (closeups / f"{row}.png").exists()` in its rows) turns
test_a_thin_straight_row_whose_close_up_passed_is_built_in_code_and_never_goes_to_pixal3d red (the pipe is batched).
slender's edge left out again (`<=` -> `<`) turns test_only_thin_rows_of_a_straight_kind_are_taken red (the 4 m
stair railing 1 m tall). path_build scaling its picture by the row's height (`scale = sides[2] / reach` -> `scale =
float(row["size"][2]) / reach`) turns test_a_path_is_built_in_its_picture_s_plane_facing_the_outline_s_view red (the
cables 0.1 m long); balls' radius its distance to the skeleton rather than to the edge (`distance_transform_edt(np.pad(kept, 1))[1:-1, 1:-1]`
-> `distance_transform_edt(~skeleton)`) turns it red too (the diagonal's tube). build laying a mask in its picture's slant again (`axis_turn(row, alpha)` ->
`0.0` in build) turns test_a_straight_thing_slanted_by_the_concept_s_view_passes_as_prepare_predicts red (the pipe 14
degrees off level); likeness_row.object_record seeing a code build in its row's pose (its `turn = ...` -> `turn = None`)
turns test_a_thin_row_whose_mask_is_not_one_straight_run_is_built_along_its_mask_s_path red; path_build measuring its
mask's reach in the picture's frame (`angle = np.radians(turn)` -> `angle = 0.0 * turn`) turns
test_a_thin_run_is_held_to_its_path_s_own_size_never_crushed_to_its_box red (the bend 4.08 m on its 4 m row). likeness_row.object_record's `lit` never set (`lit = False`)
turns test_a_code_built_light_is_not_held_to_the_lamp_its_route_leaves_to_the_light_layer red (the lamp face missed).
write_take leaving its crop off the build (`mesh = textured(build(row, alpha), picture)` -> `mesh = build(row, alpha)`)
turns test_a_code_build_carries_its_crop_where_it_lies_so_each_finish_has_faces_of_its_own red (one region).
build sweeping a masked row straight again (`if alpha is not None and alpha.any():` before path_build -> `if False:`)
turns test_a_band_is_its_drawn_width_across_its_picture_and_at_most_its_row_s_thinnest_side_deep and
test_a_thin_row_whose_mask_is_not_one_straight_run_is_built_along_its_mask_s_path red; so do, for the band test,
path_build not holding its depth to the row (the depth factor -> `1.0`: the conduit 0.27 m deep on its 0.1 m), and
balls giving every ball one width (`radius[near_down, near_across]` -> `np.full_like(off, np.median(radius[skeleton]))`:
the post's foot as thin as its shaft), and drawn_thin taking every mask (`return True`: the blob built). likeness_row.straight_cut turning its cut
(np.rot90 of the cut) turns test_a_straight_thing_slanted_by_the_concept_s_view_passes_as_prepare_predicts red.
cut_box giving the row's box always (`if True:`) turns test_the_mask_jobs_ask_each_row_s_own_mask_by_its_words_in_its_box
and test_the_pixal_row_builds_a_failed_thin_row_and_drops_its_close_up_gap red (one lantern's box); code_builds never
masking a kept build again (`if row not in kept}`) turns the latter red too (the counted pipe kept one instance's
crop). code_builds keeping a build already made as it is (`thin_straight.rebuilt(...)` under `if False:`) turns
test_the_pixal_row_builds_a_failed_thin_row_and_drops_its_close_up_gap red (the older builder's box kept).
held_across holding nothing (`hold[across, across] = min(...)` -> `hold[across, across] = 1.0`) turns
test_a_band_is_its_drawn_width_across_its_picture_and_at_most_its_row_s_thinnest_side_deep red (the conduit 0.3 m
across on its 0.1 m); view not undoing it (`@ np.linalg.inv(as_built(row, alpha))` dropped) turns that test,
test_a_thin_run_is_held_to_its_path_s_own_size_never_crushed_to_its_box and
test_a_path_is_built_in_its_picture_s_plane_facing_the_outline_s_view red (the rail's outline 0.445); write_take laying
its crop on the held build (`seen = mesh.copy()`) turns
test_a_code_build_carries_its_crop_where_it_lies_so_each_finish_has_faces_of_its_own red (the thin bar's crop 0.021 of
its 0.095 across). thin_straight leaving networks out (`or network(row)` dropped) and flat_sheet.sheet taking them
(`and not thin_straight.network(row)` dropped) each turn
test_a_flat_network_of_straight_runs_is_built_along_its_mask_each_run_held_across_never_a_flat_sheet red (the pipes a
sheet); run_holds holding nothing (`return np.ones(skeleton.shape)` first) turns it red too (its thick branch 0.84 m
across on 0.2 m), and as_built never laying it down (`if False:`) too (stood, its model check read spread 16.99).

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
        "box": [40, 93, 560, 106]}
POST = {"id": "porch_post", "name": "wooden post", "size": [0.1, 0.1, 2.5], "view": "v1", "box": [295, 0, 305, 200]}


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
    assert thin_straight.thin_straight({"name": "stair railing", "size": [4.0, 0.1, 1.0]})  # on the cut-off: taken
    assert not thin_straight.thin_straight({"name": "stair railing", "size": [3.9, 0.1, 1.0]})  # past it: a panel
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
    side = post.vertices[np.abs(np.abs(post.vertices[:, 1]) - 1.25) > 1e-9]  # its sides, not its end fans
    assert post.is_watertight and np.allclose(np.abs(side[:, [0, 2]]).max(1), 0.05)  # square, not round
    # built in rings along its length, so a finish along it has faces of its own (the lamp bar's end caps)
    assert len(np.unique(post.vertices[:, 1].round(6))) == thin_straight.SWEEP_RINGS + 1


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
    picture = Image.new("RGBA", (94, 10), (90, 90, 90, 255))
    assert thin_straight.write_take("railing_1", row, picture, 4000, pixal, tmp_path / "railing.png")
    import trimesh
    assert np.isclose(trimesh.load(pixal / "railing_1-final.glb", force="mesh").extents.max(), 9.435, rtol=0.02)


def test_the_take_is_written_where_the_finish_route_and_the_likeness_row_read_it(tmp_path, monkeypatch):
    pixal = tmp_path / "pixal"
    pixal.mkdir()
    assert thin_straight.write_take("garage_pipe_1", PIPE, cut(tmp_path, PIPE), 4000, pixal, tmp_path / "pipe.png")
    for name in ("garage_pipe_1.glb", "garage_pipe_1-final.glb", "garage_pipe_1-4000.glb",
                 "garage_pipe_1.svviews/input.png"):
        assert (pixal / name).exists(), name
    assert thin_straight.code_built("garage_pipe_1", pixal)
    # it carries its crop as its own texture, which the finish route measures (route_cast): the bar's red
    import trimesh
    loaded = trimesh.load(pixal / "garage_pipe_1.glb", force="scene")
    visual = next(iter(loaded.geometry.values())).visual
    texture = np.asarray(visual.material.baseColorTexture.convert("RGB"))
    tall, wide = texture.shape[:2]
    under = texture[np.clip(((1 - visual.uv[:, 1]) * tall).astype(int), 0, tall - 1),
                    np.clip((visual.uv[:, 0] * wide).astype(int), 0, wide - 1)]
    assert np.abs(np.median(under, axis=0) - [180, 30, 30]).max() <= 6, np.median(under, axis=0)  # the crop is a JPEG
    # the paint replays the finish's turn from the slimmed file onto the final one (labels.finish_turn): none here
    with prop_data.tools("props/library", "props"):
        import labels
    monkeypatch.setattr(labels, "PIXAL", pixal)
    assert np.array_equal(labels.finish_turn("garage_pipe_1"), np.eye(3))  # made in its own pose, never stood
    final = trimesh.load(pixal / "garage_pipe_1-final.glb", force="mesh")
    plane = final.extents  # along its mask's centreline
    assert np.isclose(plane[2], 4.0, rtol=0.02) and plane[0] <= 0.1 * 1.05 and plane[1] < 0.2, plane
    # the likeness row holds it to the crop cut by its mask: the bar's own outline matches it, not the crate's
    outline = likeness.best_way(pixal / "garage_pipe_1-final.glb", pixal / "garage_pipe_1.svviews/input.png",
                                PIPE["size"])["outline"]
    assert outline >= likeness.OUTLINE_LEAST, outline
    # a square post comes out of the finish's stand square, as built (glb_file.squared turned one set square 45 degrees)
    assert thin_straight.write_take("post_1", POST, cut(tmp_path, POST), 4000, pixal, tmp_path / "porch_post.png")
    post = trimesh.load(pixal / "post_1-final.glb", force="mesh")
    post = post.extents
    assert np.argmax(post) == 1 and np.isclose(post[1], 2.5, rtol=0.02), post  # it stands, as its picture shows
    labels.finish_turn("post_1")
    thin_straight.unbuild("post_1", pixal)
    thin_straight.unbuild("garage_pipe_1", pixal)
    assert not list(pixal.iterdir())


def test_a_code_build_carries_its_crop_where_it_lies_so_each_finish_has_faces_of_its_own(tmp_path):
    """A lamp bar whose crop shows grey end caps on a red tube: its build carries the crop as its texture, laid on from
    the way its outline matches, in rings fine enough that the finish route's views (route_views, the model's own
    texture in colour regions, the regions the list labels and the split votes) see grey on its ends and red between;
    swept in one length it was 12 faces of one colour, and its caps' finish no part's (airlock's wall lamp,
    2026-10-29)."""
    sys.path.append(str(REPO / "score/stages/surfaces"))
    import score.stages.surfaces as surfaces
    pixels = np.full((200, 600, 3), 140, dtype=np.uint8)
    pixels[90:110, 40:560] = (180, 30, 30)
    pixels[90:110, 40:100] = pixels[90:110, 500:560] = (90, 90, 90)
    Image.fromarray(pixels).save(tmp_path / "concept.png")
    lamp = {"id": "lamp", "name": "wall lamp", "noun": "lamp", "size": [0.8, 0.05, 0.05], "view": "v1",
            "box": [40, 90, 560, 110]}
    picture = thin_straight.cut_by_mask(tmp_path / "concept.png", lamp["box"],
                                        bar_mask(tmp_path / "lamp.png", lamp["box"]))
    pixal = tmp_path / "pixal"
    views = thin_straight.write_take("lamp_1", lamp, picture, 4000, pixal, tmp_path / "lamp.png")
    record = surfaces.route_views.view_take(pixal / "lamp_1.glb", views / "input.png", None, tmp_path / "views", 1)
    assert len(record["regions"]) >= 2, record["regions"]
    model = np.load(tmp_path / "views/model.npz")
    along = model["vertices"][model["faces"]].mean(1)[:, 2]  # the bar lies along z, a largest side of 1
    faces, colours = np.load(tmp_path / "views/faces.npz")["right"], np.load(tmp_path / "views/colours.npz")["right"]
    seen = faces >= 0
    ends, middle = np.abs(along[faces[seen]]) > 0.42, np.abs(along[faces[seen]]) < 0.3
    assert np.abs(np.median(colours[seen][ends], axis=0) - [90, 90, 90]).max() <= 12
    assert np.abs(np.median(colours[seen][middle], axis=0) - [180, 30, 30]).max() <= 12
    # a run drawn wider than its row's section (thin_straight.held_across) takes its crop across it as drawn
    import trimesh
    thin_straight.write_take("thin_1", {**lamp, "size": [0.8, 0.005, 0.005]}, picture, 4000, pixal,
                             tmp_path / "lamp.png")
    drawn = np.flatnonzero((np.asarray(picture)[..., 3] > 127).any(1))
    uv = trimesh.load(pixal / "thin_1.glb", force="mesh").visual.uv
    assert np.isclose(np.ptp(uv[:, 1]), np.ptp(drawn) / picture.height, rtol=0.25), (np.ptp(uv, axis=0), drawn)


def test_an_empty_mask_cuts_nothing(tmp_path):
    assert thin_straight.cut_by_mask(concept(tmp_path / "concept.png"), PIPE["box"],
                                     bar_mask(tmp_path / "empty.png", [0, 0, 0, 0])) is None


def test_the_mask_jobs_ask_each_row_s_own_mask_by_its_words_in_its_box():
    jobs = thin_straight.mask_jobs({"pipe": PIPE, "porch_post": POST}, {"pipe": "a.png", "porch_post": "a.png"})
    assert jobs == [{"picture": "a.png", "rows": [
        {"key": "pipe", "nouns": ["wall pipe", "pipe"], "box": PIPE["box"], "mask": True},
        {"key": "porch_post", "nouns": ["wooden post"], "box": POST["box"], "mask": True}]}]
    string = {"id": "string", "name": "lantern string", "noun": "lanterns", "size": [7.5, 0.5, 0.5], "count": 3,
              "box": [10, 10, 20, 20], "boxes": [[10, 10, 20, 20], [100, 5, 110, 15], None, [200, 12, 210, 30]]}
    assert thin_straight.mask_jobs({"string": string}, {"string": "a.png"})[0]["rows"][0]["box"] == [10, 5, 210, 30]
    assert thin_straight.cut_box({**string, "count": 1}) == string["box"]  # one thing: its own box


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
    import trimesh
    built = trimesh.load(pixal / "g_pipe.glb", force="mesh").extents
    trimesh.creation.box([1.0, 1.0, 1.0]).export(pixal / "g_pipe.glb")  # a build an older builder made
    pixal_row.make_pixal(inputs, out, 0, {})  # built already: made again from its own crop, nothing masked again
    assert asked == [["pipe"]]
    assert np.allclose(trimesh.load(pixal / "g_pipe.glb", force="mesh").extents, built)
    # a counted row built from one instance's box (the square's lantern string) is masked and cut again in their union
    rows = json.loads((tmp_path / "inventory.json").read_text())["rows"]
    counted = {**PIPE, "count": 2, "boxes": [PIPE["box"], [300, 60, 320, 140]]}
    (tmp_path / "inventory.json").write_text(json.dumps({"rows": [counted, rows[1]]}))
    pixal_row.make_pixal(inputs, out, 0, {})
    assert asked == [["pipe"], ["pipe"]]
    mark = json.loads((pixal / "g_pipe.svviews" / thin_straight.MARK).read_text())
    assert mark["box"] == thin_straight.cut_box(counted) == [40, 60, 560, 140], mark
    pixal_row.make_pixal(inputs, out, 0, {})  # cut in its union now: made again from its own crop
    assert asked == [["pipe"], ["pipe"]]


def test_a_thin_straight_row_whose_close_up_passed_is_built_in_code_and_never_goes_to_pixal3d(tmp_path, monkeypatch):
    """The qualifying check decides, not the close-up (thin_straight.coded): a lone pipe whose close-up passed comes out
    of the Pixal3D row built in code, and nothing goes to the batch; a crate whose close-up passed is not taken."""
    pixal = tmp_path / "pixal"
    pixal.mkdir()
    monkeypatch.setattr(pixal_row, "take_files",
                        lambda take: [pixal / f"{take}{suffix}" for suffix in pixal_row.SUFFIXES])
    closeup = tmp_path / "closeup"
    (closeup / "closeups").mkdir(parents=True)
    Image.new("RGB", (8, 8)).save(closeup / "closeups" / "pipe.png")  # its close-up passed
    monkeypatch.setattr(thin_straight, "concept_masks", lambda rows, concepts, folder: {
        row: bar_mask(tmp_path / f"{row}.png", PIPE["box"]) for row in rows})
    batch_gaps.write(closeup, [])
    (tmp_path / "props.json").write_text(json.dumps({"place": "garage", "objects": {
        "pipe": {"route": "prop", "take": "g_pipe"}}}))
    (tmp_path / "inventory.json").write_text(json.dumps({"rows": [PIPE]}))
    (tmp_path / "surfaces.json").write_text(json.dumps({"takes": {"g_pipe": {}}, "bake": {
        "models": {"garage_pipe": "g_pipe"}, "entries": {"garage_pipe": {"faces": 4000}}}}))
    inputs = {"props": tmp_path / "props.json", "inventory": tmp_path / "inventory.json",
              "surfaces": tmp_path / "surfaces.json", "closeup": closeup, "view v1": concept(tmp_path / "concept.png")}
    out = tmp_path / "out"
    out.mkdir()
    pixal_row.make_pixal(inputs, out, 0, {})  # a batch would need a cloud run: none is made
    assert not (out / "list.txt").exists()
    assert thin_straight.code_built("g_pipe", pixal)
    assert sorted(json.loads((out / "takes.json").read_text())) == ["pipe"]
    crate = {"id": "crate", "name": "crate", "size": [0.5, 0.5, 0.4], "box": [0, 0, 9, 9]}
    assert thin_straight.coded({"pipe": PIPE, "crate": crate, "boxless": {**PIPE, "box": None}}) == {"pipe"}


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


def held(tmp_path, row, lines, width=9, parts=None):
    """(the likeness row's record, prepare's predicted faults) of the code build from a concept whose SAM 3 mask is
    `lines` (each a list of (x, y) points) drawn `width` pixels wide on a 600 by 200 picture; `parts` the
    surfaces-parts record its parts check reads (none by default)."""
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
                                       inputs, {"take": pixal / "take-final.glb"}, parts or {"takes": {}},
                                       {"it": {**row, "box": box}}, set(), folder / "cuts")
    found["code"] = json.loads((views / thin_straight.MARK).read_text())
    return found, predict.build_faults(pixal / "take-final.glb", views / "input.png", "p", "it", row, folder,
                                       straight=True)


def test_a_straight_thing_slanted_by_the_concept_s_view_passes_as_prepare_predicts(tmp_path):
    """The concept draws a straight thing at its camera's slant: it is built along its mask's centreline laid along
    its row, level or upright (thin_straight.axis_turn: a rail drawn steep was laid 38 to 60 degrees off level, round
    32's docking airlock), the likeness row holds it to its crop turned the same and sees it leaned to its view
    (likeness_row.straight_cut, whole_best_way), and prepare's prediction holds the build the same way. A box the
    reading stood upright over a pipe its picture shows lying is built lying: the direction is the row's, the metres
    the box's."""
    import trimesh
    lying = {"id": "lying", "name": "wall pipe", "noun": "pipe", "size": [0.1, 0.1, 3.0], "view": "v1"}
    for row, line in ((POST, [(250, 190), (350, 10)]), (PIPE, [(60, 160), (540, 40)]), (lying, [(60, 120), (540, 90)])):
        found, faults = held(tmp_path, row, [line])
        assert found["outline"] >= likeness.OUTLINE_LEAST and found["code"]["profile"] == "path", (row["id"], found)
        assert not any(fault.startswith("outline") for fault in faults), faults
        made = trimesh.load(tmp_path / row["id"] / "pixal" / "take-final.glb", force="mesh")
        axis = np.linalg.svd(made.vertices - made.vertices.mean(0), full_matrices=False)[2][0]
        rise = np.degrees(np.arcsin(min(1.0, abs(axis[1]))))
        assert (rise > 87 if row is POST else rise < 3), (row["id"], rise)  # upright or level, as its row, not drawn
    extents = trimesh.load(tmp_path / "lying/pixal/take-final.glb", force="mesh").extents
    assert np.argmax(extents) == 2 and np.isclose(extents[2], 3.0, rtol=0.02), extents


def test_a_band_is_its_drawn_width_across_its_picture_and_at_most_its_row_s_thinnest_side_deep(tmp_path):
    """A box section the picture cannot show is never built: a mask drawn thinner or thicker than the box's short
    sides is held to its crop as drawn (storage's 0.6 m square pillar drawn 0.25 m, 0.399; the docking airlock's
    0.1 m ceiling rail drawn 0.28 m, 0.324; 2026-10-29), and a flat ribbon box is no flat ribbon where its picture
    draws a pipe (the stairwell's conduit, 3.0 by 0.1 m drawn 0.28 m, read 0.346 swept as its box, #36 2026-10-30):
    its depth at most the row's thinnest side, and a slender run drawn wider than that at its length's scale held
    across to it (thin_straight.held_across: a run going away from the camera is foreshortened along its length, not
    across; the walkway's 12 m wall pipes on 0.1 m were built 2.9 m tall, #36 2026-10-31), its outline seen as drawn
    (thin_straight.view)."""
    import trimesh
    pillar = {"id": "pillar", "name": "support pillar", "noun": "pillar", "size": [0.6, 0.6, 3.0], "view": "v1"}
    rail = {"id": "rail", "name": "ceiling rail", "noun": "rail", "size": [3.0, 0.1, 0.1], "view": "v1"}
    conduit = {"id": "conduit", "name": "conduit pipes", "noun": "conduit", "size": [12.0, 3.0, 0.1], "view": "v1"}
    for row, line, width in ((pillar, [(300, 190), (300, 10)], 9), (rail, [(60, 100), (540, 100)], 40),
                             (conduit, [(20, 100), (580, 100)], 13)):
        found, faults = held(tmp_path, row, [line], width)
        assert found["outline"] >= likeness.OUTLINE_LEAST, (row["id"], found["outline"])
        assert not any(fault.startswith("outline") for fault in faults), faults
    made = trimesh.load(tmp_path / "conduit/pixal/take-final.glb", force="mesh")
    plane = made.extents
    assert np.isclose(plane[2], 12.0, rtol=0.02) and plane[0] <= 0.1 * 1.05, plane  # its length, its depth
    assert np.isclose(plane[1], 0.1, rtol=0.1), plane  # 13 of its 573 pixels across, 0.27 m at its length's scale
    cut = np.asarray(Image.open(tmp_path / "conduit/pixal/take.svviews/input.png").convert("RGBA"))[..., 3] > 127
    drawn = made.vertices @ np.linalg.inv(thin_straight.held_across(conduit, cut))[:3, :3].T  # as view sees it
    assert np.isclose(np.ptp(drawn[:, 1]), 12.0 * 13 / 573, rtol=0.2), np.ptp(drawn, axis=0)
    # a post's flared foot keeps its own width: the build is as wide as its mask at each point of its centreline (a
    # tube of one width lost the airlock porch post's foot, 0.75 to 0.46, #36 2026-10-30)
    post = {"name": "wooden post", "noun": "post", "size": [0.5, 0.5, 2.5]}
    mask = np.zeros((400, 200), dtype=bool)
    mask[0:330, 90:110] = True  # the post, 20 pixels across
    mask[340:400, 60:140] = True  # its foot, a piece of its own 80 across
    made = thin_straight.path_build(post, mask)
    low = made.vertices[:, 1] < made.bounds[0][1] + 0.1 * np.ptp(made.vertices[:, 1])
    high = made.vertices[:, 1] > made.bounds[1][1] - 0.5 * np.ptp(made.vertices[:, 1])
    foot, shaft = np.ptp(made.vertices[low, 2]), np.ptp(made.vertices[high, 2])
    assert np.isclose(foot, 2.5 * 80 / 400, rtol=0.15) and np.isclose(shaft, 2.5 * 20 / 400, rtol=0.25), (foot, shaft)
    # a blob SAM 3 found in a thin row's box (one lantern of a string's eight) is no thin thing: no build, nothing written
    blob = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    blob.paste((90, 90, 90, 255), (100, 100, 200, 200))
    assert thin_straight.drawn_thin(mask) and not thin_straight.drawn_thin(np.asarray(blob)[..., 3] > 127)
    assert thin_straight.write_take("blob", post, blob, 4000, tmp_path / "blob", tmp_path / "blob.png") is None
    assert not (tmp_path / "blob").exists()


def test_a_thin_row_whose_mask_is_not_one_straight_run_is_built_along_its_mask_s_path(tmp_path):
    """A bent pipe, a sagging string, a bundle of two cables and a railing's ladder (world 1's straight-masks,
    2026-10-26) each failed as one straight sweep: their build follows the mask's own path, its longest reach the
    row's longest side, its other reach the path's own, and the likeness row's outline and
    prepare's prediction both pass it."""
    import trimesh
    sag = [(x, 50 + 120 * (1 - ((x - 300) / 260) ** 2)) for x in range(40, 561, 10)]
    posts = [[(x, 30), (x, 170)] for x in np.linspace(40, 560, 7)]
    shapes = {"elbow": ({"name": "wall pipe", "noun": "pipe", "size": [4.0, 0.1, 0.8]},
                        [[(40, 60), (40, 170), (560, 170)]]),
              "sag": ({"name": "lantern string", "noun": "lanterns", "size": [6.0, 0.1, 1.4]}, [sag]),
              "bundle": ({"name": "pipe bundle", "noun": "pipes", "size": [4.0, 0.1, 0.4]},
                         [[(40, 80), (560, 80)], [(40, 120), (560, 120)]]),
              "ladder": ({"name": "metal railing", "noun": "railing", "size": [4.2, 0.1, 1.2]},
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
    depth through the picture's plane at most the row's thinnest side (never under thin_straight.least_tube), a tie
    laid in the picture's plane;
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
        across = sorted(made.extents)  # in its plane
        assert np.isclose(across[2], row["size"][0], rtol=0.02), (name, made.extents)
        assert across[1] > 5 * tube, (name, made.extents)  # its path's reach, not its box's thickness
        assert np.isclose(across[0], tube, rtol=0.1), (name, made.extents)
        assert found["model_check"]["thinnest"] >= 0.5 * tube, (name, found["model_check"])
    assert np.argmax(trimesh.load(tmp_path / "sag/pixal/take-final.glb", force="mesh").extents) == 2
    assert np.ptp(trimesh.load(tmp_path / "sag/pixal/take-final.glb", force="mesh").vertices[:, 1]) > 1.0  # it hangs
    wire = {"name": "wire", "noun": "wire", "size": [3.0, 0.001, 0.001]}
    wire_mask = np.zeros((40, 400), dtype=bool)
    wire_mask[18:22, :] = True
    deep = thin_straight.path_build(wire, wire_mask)
    assert np.isclose(deep.extents[0], thin_straight.least_tube(), rtol=0.05), deep.extents  # 1 mm: held to the gate's
    bend = {"view": "v1", **shapes["bend"][0]}
    scale = 4.0 / 520  # the L's 520 pixels across, the pipe's 4 m
    laid = [np.array([[0.0, -(down - 40) * scale, (across - 40) * scale]
                      for across, down in ((40, 40), (40, 170), (560, 170))])]
    thick = 9 * scale
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


def test_a_path_is_built_in_its_picture_s_plane_facing_the_outline_s_view(tmp_path):
    """A railing curving round a floor drawn from above (the greenhouse's, 9.4 by 0.1 by 1 m: its curve held to its
    1 m height, outline 0.023, 2026-10-28) keeps its picture's curve, and cables lying on the ground (the old
    station's, 10 by 0.1 by 0.1: laid on the ground, outline 0.068) are laid in their picture's plane, turned so
    their long axis lies level as their row, seen back in their picture's slant and leaned to face the outline's
    look-down (thin_straight.view), its longest reach the row's, both passing the outline; a diagonal line's tube is its
    drawn width, its steps measured as lengths."""
    import trimesh
    arc = [(40 + 520 * (1 - np.cos(turn)), 20 + 160 * np.sin(turn)) for turn in np.linspace(0, np.pi / 2, 30)]
    posts = [[(x, y), (x, y + 25)] for x, y in arc[::6]]
    shapes = {"railing": ({"name": "metal railing", "noun": "railing", "size": [9.435, 0.1, 1.0],
                           "anchor": "on:upper_floor"}, [arc, *posts]),
              "cables": ({"name": "power cables", "noun": "cables", "size": [10.0, 0.1, 0.1], "anchor": "ground"},
                         [[(x, 110 + 60 * np.sin(x / 90)) for x in range(20, 581, 10)]])}
    for name, (row, lines) in shapes.items():
        found, faults = held(tmp_path, {"id": name, "view": "v1", **row}, lines)
        assert found["outline"] >= likeness.OUTLINE_LEAST and not faults, (name, found["outline"], faults)
        made = trimesh.load(tmp_path / name / "pixal" / "take-final.glb", force="mesh")
        plane = made.extents
        assert np.isclose(plane[2], row["size"][0], rtol=0.02), (name, plane)
        assert plane[1] > 1.1 and plane[0] <= 0.1 * 1.05, (name, plane)  # its path's reach, never its row's 1 m
    diagonal = {"name": "wire", "noun": "wire", "size": [6.0, 0.5, 0.5]}
    down, across = np.mgrid[0:400, 0:400]
    mask = np.abs(down - across) <= 10  # 21 pixels along a row, 14.8 square to its way
    made = thin_straight.path_build(diagonal, mask)
    thick = sorted(made.extents)[0]
    assert np.isclose(thick, 6.0 * 14.8 / (400 + 14.8), rtol=0.15), thick


def test_a_code_built_light_is_not_held_to_the_lamp_its_route_leaves_to_the_light_layer(tmp_path):
    """A stem lamp's code build is its post, its lamp the light layer's (the square's floodlight tower, 2026-10-28,
    failed only on "bright white glowing lamp face"): the parts check leaves its lit finishes out and still names any
    other it misses; a pipe, whose kind does not glow, is held to every finish."""
    parts = {"takes": {"take": {"parts": [{"words": "dark steel"}], "finishes": [
        {"finish": "dark steel", "family": "steel"}, {"finish": "bright white glowing lamp face", "family": "glass"},
        {"finish": "red paint band", "family": "paint"}]}}}
    lamp = {"id": "lamp", "view": "v1", "name": "street lamp", "noun": "lamp", "size": [0.3, 0.3, 6.0]}
    assert held(tmp_path, lamp, [[(300, 10), (300, 190)]], parts=parts)[0]["parts_missing"] == ["red paint band"]
    pipe = {"id": "pipe", "view": "v1", "name": "wall pipe", "noun": "pipe", "size": [6.0, 0.3, 0.3]}
    assert held(tmp_path, pipe, [[(10, 100), (590, 100)]], parts=parts)[0]["parts_missing"] == [
        "bright white glowing lamp face", "red paint band"]


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


def test_a_flat_network_of_straight_runs_is_built_along_its_mask_each_run_held_across_never_a_flat_sheet(tmp_path):
    """A straight kind spread flat over a floor (thin_straight.network: env1 round 35's engineroom pipes, 9.3 by 10.9
    by 0.2 m, went to flat_sheet as one slab, DINOv2 0.041) is built along its mask's centreline, forks kept, laid
    down on its floor, each run held across to the row's thinnest side (run_holds), never a flat sheet; a flag on a
    pole stays a sheet."""
    import score.stages.props.flat_sheet as flat_sheet
    from PIL import ImageDraw
    row = {"id": "network", "name": "pipes", "noun": "pipes", "size": [3.6, 10.9, 0.2], "view": "v1"}
    assert thin_straight.thin_straight(row) and not flat_sheet.sheet(row)
    assert flat_sheet.sheet({"name": "red flag on a pole", "noun": "flag", "size": [1.0, 0.04, 3.0]})
    found, faults = held(tmp_path, row, [[(40, 100), (560, 100)], [(300, 20), (300, 180)],
                                         [(120, 100), (120, 30), (200, 30)]])
    assert found["code"]["profile"] == "path" and found["outline"] >= likeness.OUTLINE_LEAST and not faults, found
    mask = Image.new("L", (600, 200), 0)
    ImageDraw.Draw(mask).line([(40, 100), (560, 100)], fill=255, width=9)
    ImageDraw.Draw(mask).line([(300, 100), (300, 180)], fill=255, width=40)  # a branch drawn 0.84 m across
    made = thin_straight.build(row, np.asarray(mask) > 127)
    assert np.isclose(made.extents[1], 0.2, rtol=0.05) and np.isclose(made.extents[2], 10.9, rtol=0.02), made.extents
    end = made.vertices[made.vertices[:, 0] > made.bounds[1][0] - 0.4]  # the branch's far end, past its tee
    assert np.ptp(end[:, 2]) <= 0.2 * 1.15, np.ptp(end[:, 2])
