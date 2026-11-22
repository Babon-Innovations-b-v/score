"""A made model is set over the library model it replaces, its paint is moved toward its place's palette (a far colour
named a mismatch, never forced), its GLB is edited losslessly, and its mass is its hulls' outside skin, not every face.

Breaks that turn this red (each applied once and seen red, then reverted):
- maker.flat_card: always False -> the 1 mm card passes as a model
- maker.cut_out: its rectangle refusal dropped -> a box-cut crop (the capsule's uncut lever, #156) goes to TRELLIS.2;
  maker.concept_picture: its missing-mask refusal dropped -> concept/<n> with no SAM 3 mask is made from no cut
- maker.faces_for: FACES for every size -> the 0.3 m sprout is made at 500k faces, not LEAST_FACES
- fit.fitted_matrix: YAWS made (0.0,) -> the L turned a quarter is not covered (yaw and distance wrong)
- glb.with_image: the later views not moved -> the second image's bytes read back wrong
- grade.graded: `moves` made the token minus the centre without GRADE -> the near colour moves all the way
- sim: INSIDE made -1e-4 -> the face where the two cubes meet counts as skin (mass 20% high)
- cloud.job_of: a model it names missing from the meshparts image's models.json, two pictures made in one process
  (generate.py drops its flow models after one), or a picture's output not brought back where its out.glb lies
- shim/flash_attn: the padded batch's key mask dropped -> padded keys are attended (checked where torch is, as in
  the maker's own Python)
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
    from score.stages.place_build import maker
    from score.stages.place_build.maker import generate
    assert [maker.faces_for(size) for size in (0.3, 1.0, 3.0, None)] == [maker.LEAST_FACES, 125000, generate.FACES,
                                                                       generate.FACES]  # a sprout, a chair, a wall
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
