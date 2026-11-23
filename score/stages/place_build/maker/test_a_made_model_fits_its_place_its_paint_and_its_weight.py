"""A made model is set over the library model it replaces, its paint is moved toward its place's palette (a far colour
named a mismatch, never forced), its GLB is edited losslessly, and its mass is its hulls' outside skin, not every face.

Breaks that turn this red (each applied once and seen red, then reverted):
- maker.picture_of returning a loose picture's path as said -> the public record names a path on this PC
- maker.flat_card: always False -> the 1 mm card passes as a model
- maker.cut_out: its rectangle refusal dropped -> a box-cut crop (the capsule's uncut lever, #156) goes to TRELLIS.2;
  maker.concept_picture: its missing-mask refusal dropped -> concept/<n> with no SAM 3 mask is made from no cut
- maker.faces_for: FACES for every size -> the 0.3 m sprout is made at 500k faces, not LEAST_FACES
- fit.size_matrix: scaled by the size's tallest side, not its longest -> the L laid at (2.0, 0.5, 0.3) is 0.6 m long;
  maker.size_of: `size` ignored -> a model made at a size is made at FACES, not its size's faces
- fit.fitted_matrix: YAWS made (0.0,) -> the L turned a quarter is not covered (yaw and distance wrong)
- fit.headed: its quarter turns not tried (TRELLIS.2's own heading kept), or fit.view_axes turned the other way, or
  straight down taken with the front up -> a desk L made long along x, its close-up long along depth, is laid
  wide and shallow (#166: desk, rack and sign); MIRROR_GAIN made -1 -> the L is laid mirrored
- glb.with_image: the later views not moved -> the second image's bytes read back wrong
- grade.graded: `moves` made the token minus the centre without GRADE -> the near colour moves all the way
- sim: INSIDE made -1e-4 -> the face where the two cubes meet counts as skin (mass 20% high)
- cloud.job_of: a model it names missing from the meshparts image's models.json, two pictures made in one process
  (generate.py drops its flow models after one), or a picture's output not brought back where its out.glb lies
- shim/flash_attn: the padded batch's key mask dropped -> padded keys are attended (checked where torch is, as in
  the maker's own Python, with the three below)
- generate.chunked_layer_norm: a block normalised in float16 -> the norm is not LayerNorm32's bit for bit;
  generate.layer_norm_in_place: its eps dropped -> not F.layer_norm's at the decoders' eps
- remesh.crossing: the crossing edges taken edge by edge (axis first) -> not in cumesh's voxel-by-voxel order
"""
import importlib.util
import json
import pathlib

import numpy as np

from score.stages.place_build.maker import cloud, fit, glb, grade, sim

HERE = pathlib.Path(__file__).resolve().parent


def ell_points():
    """Points over an L of two boxes (no quarter-turn symmetry), metres."""
    random = np.random.default_rng(1)
    long_bar = random.random((600, 3)) * [1.0, 0.2, 0.3]
    foot = random.random((300, 3)) * [0.3, 0.6, 0.3] + [0.7, 0.2, 0.0]
    return np.concatenate([long_bar, foot])


def cube(low):
    """A unit cube from corner `low`: its points and outward triangles."""
    corners = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], float) + low
    triangles = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6],
                          [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return corners, triangles


def drawn(boxes, turn, down):
    """A close-up's cut-out (opaque pixels, rows down) of Z-up boxes (low, high) worked out here apart from fit: an
    orthographic camera turned `turn` degrees from the front (-y) about z, looking down `down`; from straight above
    the back (+y) is up. Each box's outline is its corners' convex hull."""
    from PIL import Image, ImageDraw
    from scipy.spatial import ConvexHull
    turn, down = np.radians(turn), np.radians(down)
    back = np.array([np.sin(turn) * np.cos(down), -np.cos(turn) * np.cos(down), np.sin(down)])
    up = np.array([0.0, 1.0, 0.0]) if down > 1.5 else np.array([0.0, 0.0, 1.0])
    right = np.cross(up, back) / np.linalg.norm(np.cross(up, back))
    true_up = np.cross(back, right)
    picture = Image.new("L", (300, 300))
    for low, high in boxes:
        corners = np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])
        flat = np.stack([corners @ right, -(corners @ true_up)], 1) * 100 + 150
        ImageDraw.Draw(picture).polygon([tuple(point) for point in flat[ConvexHull(flat).vertices]], fill=255)
    return np.asarray(picture) > 127


def z_up_to_model(boxes, yaw, count=4000):
    """Points in the boxes (Z up) as TRELLIS.2 would lay them: glTF's Y up (x, z, -y), then turned `yaw` about y."""
    random = np.random.default_rng(5)
    points = np.concatenate([random.random((count, 3)) * (np.array(high) - low) + low for low, high in boxes])
    return fit.applied(fit.yawed(yaw), points[:, [0, 2, 1]] * [1, 1, -1])


def shim():
    spec = importlib.util.spec_from_file_location("flash_attn_shim", HERE / "shim/flash_attn/__init__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_made_model_fits_its_place_its_paint_and_its_weight(tmp_path):
    like = ell_points()
    made = fit.applied(fit.yawed(90.0), like) * 0.4 + [3.0, 1.0, -2.0]
    matrix, how = fit.fitted_matrix(made, like)
    assert how["yaw"] == 270.0 and abs(how["scale"] - 2.5) < 0.01 and how["distance_m"] < 0.02
    tall = fit.applied(fit.height_matrix(made, 1.8), made)
    assert abs(np.ptp(tall[:, 1]) - 1.8) < 1e-9 and abs(tall[:, 1].min()) < 1e-9
    sized = fit.applied(fit.size_matrix(made, (2.0, 0.5, 0.3)), made)  # wide, deep, tall: its longest side 2 m
    assert abs(np.ptp(sized, 0).max() - 2.0) < 1e-9 and abs(sized[:, 1].min()) < 1e-9
    desk = [([-0.4, -0.9, 0.7], [0.4, 0.9, 0.76]), ([0.2, -0.9, 0.0], [0.4, -0.3, 0.7])]  # a top, drawers right front
    sign = [([-0.5, -0.2, 0.0], [0.5, 0.2, 0.02]), ([-0.5, 0.2, 0.0], [-0.3, 0.3, 0.02])]  # flat, a tab back left
    for boxes, turn, down in ((desk, 35.0, 15.0), (sign, 0.0, 90.0)):
        truth = z_up_to_model(boxes, 0.0)
        for yaw in (90.0, 180.0):  # TRELLIS.2's own headings
            heading, how = fit.headed(z_up_to_model(boxes, yaw), drawn(boxes, turn, down), turn, down)
            laid = fit.applied(heading, z_up_to_model(boxes, yaw))
            assert not how["mirrored"] and (how["yaw"] + yaw) % 360 == 0 and np.allclose(np.sort(laid, 0),
                                                                                          np.sort(truth, 0)), how
    from score.stages.place_build import maker
    from score.stages.place_build.maker import generate
    assert [maker.faces_for(size) for size in (0.3, 1.0, 3.0, None)] == [maker.LEAST_FACES, 125000, generate.FACES,
                                                                       generate.FACES]  # a sprout, a chair, a wall
    assert maker.size_of(tmp_path, None, None, (0.5, 0.4, 1.0)) == 1.0  # a size's longest side, no place read
    assert maker.flat_card([0.3, 0.001, 0.05]) and not maker.flat_card([0.3, 0.02, 0.02]) \
        and not maker.flat_card([1.2, 0.006, 0.1])  # a 1 mm card; a stick; a 6 mm sign

    from PIL import Image
    from score.stages.place_build import Refused
    shape = np.zeros((40, 60, 4), np.uint8)
    shape[5:35, 10:50] = 200
    shape[5:20, 30:50, 3] = 0  # an L, cut out of its background
    pictures = {"cut": shape, "box": np.pad(np.full((30, 40, 4), 200, np.uint8), ((5, 5), (10, 10), (0, 0))),
                "opaque": np.full((40, 60, 4), 200, np.uint8)}
    refused = {}
    for name, pixels in pictures.items():
        Image.fromarray(pixels, "RGBA").save(tmp_path / f"{name}.png")
        try:
            maker.cut_out(tmp_path / f"{name}.png")
        except Refused:
            refused[name] = True
    Image.fromarray(shape[..., :3], "RGB").save(tmp_path / "rgb.png")
    (tmp_path / "objects.json").write_text(json.dumps([{"word": "lever", "box": [0, 0, 10, 10], "mask": None}]))
    for source in ("rgb.png", "concept/0"):
        try:
            maker.picture_of(tmp_path, str(tmp_path / source) if source.endswith("png") else source, None, tmp_path)
        except Refused:
            refused[source] = True
    assert refused == {"box": True, "opaque": True, "rgb.png": True, "concept/0": True}
    _, said = maker.picture_of(tmp_path, str(tmp_path / "cut.png"), None, tmp_path)
    assert said == "the picture cut.png"  # a public record names a loose picture, never its path on this PC

    document = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"name": "world"}],
                "buffers": [{"byteLength": 0}], "images": [{"bufferView": 0, "mimeType": "image/png"}],
                "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 5},
                                {"buffer": 0, "byteOffset": 8, "byteLength": 3}],
                "textures": [{"source": 0}], "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}]}
    binary = b"aaaaa\0\0\0bbb"
    binary = glb.with_image(document, binary, glb.base_colour_image(document), b"cccccccccc")
    glb.with_root_matrix(document, np.diag([2.0, 2.0, 2.0, 1.0]))
    glb.write(tmp_path / "made.glb", document, binary)
    again, data = glb.read(tmp_path / "made.glb")
    assert glb.image(again, data, 0) == b"cccccccccc" and glb.image(again, data, 0) != data[:3]
    assert data[again["bufferViews"][1]["byteOffset"]:][:3] == b"bbb"
    assert again["scenes"][0]["nodes"] == [1] and again["nodes"][1]["children"] == [0]
    assert again["nodes"][1]["matrix"][0] == 2.0 and json.dumps(again)

    tokens = {"olive": "#6e7052", "sky": "#1a2238"}
    near = np.ones((4, 4, 3)) * np.array([0x70, 0x78, 0x50]) / 255
    far = np.ones((4, 4, 3)) * np.array([0xe0, 0x20, 0xc0]) / 255
    picture = np.concatenate([near, far], 1)
    moved, groups = grade.graded(picture, picture.reshape(-1, 3), tokens)
    before, after, target = grade.lab(near[0, 0]), grade.lab(moved[0, 0]), grade.hex_lab(tokens["olive"])
    assert np.allclose(after - before, grade.GRADE * (target - before), atol=0.5)
    assert [group["mismatch"] for group in groups] == [False, True] or \
        [group["mismatch"] for group in sorted(groups, key=lambda group: group["delta_e"])] == [False, True]

    pair = [cube(np.zeros(3)), cube(np.array([1.0, 0.0, 0.0]))]
    steel = sim.material("steel")
    weighed = sim.physical(pair, "steel")
    assert abs(weighed["mass_kg"] / (10 * steel["sheet"] * steel["density"]) - 1) < 0.03
    assert sim.physical(pair, "stone")["mass_kg"] == round(2 * sim.material("stone")["density"], 2)

    models = cloud.REPO / "tools/cloud/images/meshparts/models.json"
    listed = {model["name"] for model in json.loads(models.read_text())}
    job = cloud.job_of([("/pictures/a.png", "/made/a/a.glb"), ("/pictures/b.png", "/made/b/b.glb")])
    assert set(job["models"]) <= listed and job["command"][-1].count("generate.py") == 2
    assert [entry["local"] for entry in job["outputs"]] == ["/made/a/.cloud-0", "/made/b/.cloud-1"]

    if importlib.util.find_spec("torch") is None:  # the maker's own Python has it (setup.sh); score's need not
        print("flash-attn stand-in: skipped (no torch in this Python)")
        return
    attention = shim()
    random = np.random.default_rng(3)
    import torch
    lengths = torch.tensor([3, 7, 5, 2, 6, 4, 7, 1, 5, 3])
    bounds = torch.cat([torch.zeros(1, dtype=torch.int32), lengths.cumsum(0).int()])
    packed = torch.tensor(random.standard_normal((int(lengths.sum()), 3, 2, 8)), dtype=torch.float32)
    together = attention.flash_attn_varlen_qkvpacked_func(packed, bounds, int(lengths.max()))
    alone = torch.cat([attention.attended(*(packed[bounds[at]:bounds[at + 1], part][None] for part in range(3)))[0]
                       for at in range(len(lengths))])
    assert len(lengths) > attention.FEW and torch.allclose(together, alone, atol=1e-5)

    from score.stages.place_build.maker import remesh  # #169: the lean decoders and remesh answer as TRELLIS.2's own
    rows_at_once, generate.ROWS_AT_ONCE = generate.ROWS_AT_ONCE, 12  # blocks of two and a part, as at the top level
    norm = torch.nn.LayerNorm(5, eps=1e-6)
    norm.weight.data, norm.bias.data = (torch.tensor(random.standard_normal(5) * 3, dtype=torch.float32)
                                        for _ in range(2))
    features = torch.tensor(random.standard_normal((23, 5)) * 40 + 7, dtype=torch.float16)
    chunked = generate.chunked_layer_norm(norm, features)
    whole = torch.nn.LayerNorm.forward(norm, features.float()).half()
    lone = features.float() / 1000  # a spread the eps shows in
    in_place = generate.layer_norm_in_place(lone.clone(), (5,), eps=1e-6)
    generate.ROWS_AT_ONCE = rows_at_once
    assert torch.equal(chunked, whole) and torch.equal(in_place, torch.nn.functional.layer_norm(lone, (5,), eps=1e-6))
    coords = torch.tensor(random.integers(0, 50, (40, 3)), dtype=torch.int32)
    signs = torch.tensor(random.integers(-1, 2, (40, 3)), dtype=torch.int32)
    table = remesh.tables("cpu")
    every_edge = coords.reshape(40, 1, 1, 3) + table["edge_neighbours"].unsqueeze(0)  # cumesh's (voxel, edge) build
    connected, crossed = remesh.crossing(table, coords, signs)
    assert torch.equal(connected, every_edge[signs != 0]) and torch.equal(crossed, signs[signs != 0])
