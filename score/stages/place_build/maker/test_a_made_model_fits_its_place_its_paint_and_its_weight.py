"""A made model is set over the library model it replaces, its paint is moved toward its place's palette (a far colour
named a mismatch, never forced), its GLB is edited losslessly, and it is weighed and classed by #161's rules: each
hull its faces' surface class's NVIDIA row, a real-world mass a part, its friction its hulls' rows by volume.

Breaks that turn this red (each applied once and seen red, then reverted):
- maker.picture_of returning a loose picture's path as said -> the public record names a path on this PC
- maker.flat_card: always False -> the 1 mm card passes as a model
- maker.cut_out: its rectangle refusal dropped -> a box-cut crop (the capsule's uncut lever, #156) goes to TRELLIS.2;
  maker.concept_picture: its missing-mask refusal dropped -> concept/<n> with no SAM 3 mask is made from no cut
- maker.lock_file: the lock under `<root>/.git` -> a library checkout that is a git worktree (its .git a file) cannot
  take in (round 1 of 2099 #161's car: NotADirectoryError after TRELLIS.2 had made the car); maker.brought_forward
  pulling with no remote branch named -> the detached worktree is not brought forward ("not currently on a branch")
- maker.faces_for: FACES for every size -> the 0.3 m sprout is made at 500k faces, not LEAST_FACES
- fit.size_matrix: one uniform scale (TRELLIS.2's proportions kept), or its sides read as wide, deep, tall in the
  model's Y-up order -> the L drawn 10% tall and 12% shallow is not laid at the size, the L's at twice (#170);
  STRETCH made unbounded -> the L drawn twice as deep is squashed to the size's depth, not held a quarter off;
  maker.size_of: `size` ignored -> a model made at a size is made at FACES, not its size's faces
- fit.fitted_matrix: YAWS made (0.0,) -> the L turned a quarter is not covered (yaw and distance wrong)
- fit.headed: its quarter turns not tried (TRELLIS.2's own heading kept), or fit.view_axes turned the other way, or
  straight down taken with the front up -> a desk L made long along x, its close-up long along depth, is laid
  wide and shallow (#166: desk, rack and sign); its mirror tried and taken (the 0.05 gain hand drill b01 was
  mirrored on, #159 r15) -> the L is laid mirrored; `pick` not asked
  (the outline's earliest kept), or FRONT_BAND made 0 -> the desk top TRELLIS.2 laid a half turn off keeps its cable
  hole in the far corner (#192, tc4r's desk)
- front.drawn laying the model unturned (`matrix` not applied) -> every open turn is drawn alike and the first is
  picked; front.picked numbering its drawings from 0 -> the turn after the picked one is laid
- generate.band_for: BAND for every model (#191's rule alone) -> the drill and the cart with no glass are remeshed at
  band 3, their gear teeth and pegboard holes closed (#159 r15); band 1 for every model -> the fridge's glass door
  keeps its pinholes
- glb.with_image: the later views not moved -> the second image's bytes read back wrong
- glb.root_matrix not turned back to row-major (`.T` dropped) -> the decoded mesh's matrix reads its move in the bottom
  row; maker.decoded_placed laying the decoded mesh with no matrix (`with_root_matrix` dropped) -> it is not set in
  the place
- grade.graded: `moves` made the token minus the centre without GRADE -> the near colour moves all the way
- sim.surface_class: the NVIDIA name's class not read (the recipe's taken first), or the aluminium base ignored ->
  the painted steel surface reads as its recipe's or the brushed aluminium one as steel's row (0.3, not 0.61);
  sim.hull_classes: the first face inside a hull taken, not most of its area -> the wooden cube's hull reads metal;
  sim.physical: friction an unweighted mean of the hulls -> 0.4, not the volume-weighted 0.3667 (cube 1 m3 metal,
  cube 2 m3 wood); its mass not the parts' sum, or bulk's band read off the shortest side -> 2 m^3 box is "small";
  sim.weighed: an answer missing a part kept -> the one-part answer to two parts passes; every part asked (no
  UNWEIGHED skip) -> the ink of share 0.0 is asked, the two-part answer refused (#159 r11d's toaster); UNWEIGHED 1e-4
  (#210) -> what the locker's vent holes show, share 0.0004, is asked and the answer refused
- parts (#177, the cabinet's door and drawer): parts.checked keeping a box turned inside out, a hinge on no side or
  an unknown joint -> the three wrong answers pass; parts.cut with no thickness bound (the frustum alone) -> the
  carcass's front is cut into the door; parts.hinge_line taking the first edge -> the door hinges at its top;
  jointed's way not flipped -> the door swings in (sign 1); the slide not held to the depth -> 0.6 m;
  parts.projected's rows not turned down -> its rays are not route_cast's; parts.written laying a part's
  pieces without its pivot taken off -> the door's points stand 0.24 m off; parts.part_masses by face counts -> 2
  and 2; parts.part_classes by face counts -> the body is a tie, read metal; parts.made's `kg=round(mass, 4)` -> `kg=0.0`
  -> the made cabinet's parts and body no longer weigh its 12 kg (seen red 2026-11-25)
- cloud.job_of: a model it names missing from the meshparts image's models.json, two pictures made in one process
  (generate.py drops its flow models after one), or a picture's output not brought back where its out.glb lies;
  cloud.brought_back leaving the decoded mesh behind -> its folder is not removed (rmdir refuses) and no
  trellis-decoded.glb lies beside the model (#209)
- shim/flash_attn: the padded batch's key mask dropped -> padded keys are attended (checked where torch is, as in
  the maker's own Python, with the three below)
- generate.chunked_layer_norm: a block normalised in float16 -> the norm is not LayerNorm32's bit for bit;
  generate.layer_norm_in_place: its eps dropped -> not F.layer_norm's at the decoders' eps
- remesh.crossing: the crossing edges taken edge by edge (axis first) -> not in cumesh's voxel-by-voxel order
- repair.unrepeated: every face kept -> the membrane and the doubled face stay (an edge four faces hold);
  repair.wedge_pairs: a four-face edge's faces paired with the other neighbour -> the checker's cubes stay joined
  (3 pieces, not 6); repair.stuck: nothing cut -> the fold's edge stays held by four faces; repair.NUDGE made 0 ->
  the copies stay one corner; repair.LOOSE made 0 -> the crumb stays; repair.outward: the piece never turned to its
  normals -> the inside-out cube stays inside out; repair.facing_normals: no normal set to its faces' -> the five
  normals turned into the cubes stay turned (#159: the printer box's black holes); generate.unfilled (#159): the
  unread-weight refusal dropped -> a checkpoint missing 0.bias builds; the fills not given back -> torch's fills after it
  are the stand-ins (where torch is); generate.OnUse: its read outside torch.random.fork_rng -> the seeded draws after
  it change; its cpu not to the meta device -> the flow model stays in RAM after its stage; glb.with_views: a view it does not replace left where it was ->
  the second image's bytes read back wrong
"""
import importlib.util
import json
import pathlib

import numpy as np

from score.stages.place_build.maker import cloud, fit, front, glb, grade, repair, sim
from score.stages.place_build.maker import parts as made_parts

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


def holed_slab(path):
    """A desk top as TRELLIS.2 gives one (a GLB, Y up, its own texture): a 1.8 x 0.8 m slab 6 cm thick, white, a dark
    cable hole painted near its front left corner; its outline from the close-up's camera the same a half turn round."""
    import trimesh
    from PIL import Image
    slab = trimesh.creation.box((1.8, 0.06, 0.8)).subdivide().subdivide().subdivide()
    slab = trimesh.Trimesh(slab.vertices[slab.faces].reshape(-1, 3), np.arange(len(slab.faces) * 3).reshape(-1, 3),
                           process=False)
    middles = slab.triangles_center
    hole = (middles[:, 1] > 0.02) & (middles[:, 0] < -0.6) & (middles[:, 2] > 0.15)
    uv = np.repeat(np.where(hole[:, None], [[0.75, 0.5]], [[0.25, 0.5]]), 3, axis=0)
    texture = Image.fromarray(np.array([[[245, 245, 245], [20, 20, 20]]], np.uint8))
    material = trimesh.visual.material.PBRMaterial(baseColorTexture=texture)
    slab.visual = trimesh.visual.TextureVisuals(uv=uv, material=material)
    slab.export(path)
    return path


def darkest(picture):
    """The middle of a picture's dark pixels (a PNG's bytes): where its cable hole is drawn."""
    import io
    from PIL import Image
    rows, columns = np.nonzero(np.asarray(Image.open(io.BytesIO(picture)).convert("L")) < 60)
    return np.array([columns.mean(), rows.mean()])


def nearest_hole(body):
    """A stand-in for the front ask: the drawing whose cable hole lies nearest the picture's, as its answer's JSON."""
    import base64
    shown = [base64.b64decode(part["inline_data"]["data"]) for part in body["contents"][0]["parts"]
             if "inline_data" in part]
    gaps = [np.linalg.norm(darkest(drawing) - darkest(shown[0])) for drawing in shown[1:]]
    return json.dumps({"pick": int(np.argmin(gaps)) + 1, "reason": "the cable hole"})


def voxels(cells, low=(0.0, 0.0, 0.0), side=1.0):
    """The outward boundary of unit cells (x, y, z) laid from `low`, `side` long: its points and triangles."""
    cells = {tuple(cell) for cell in cells}
    quads = []
    for cell in cells:
        for axis in range(3):
            across, up = np.eye(3)[(axis + 1) % 3], np.eye(3)[(axis + 2) % 3]
            for sign in (1, -1):
                if tuple(np.add(cell, np.eye(3, dtype=int)[axis] * sign)) in cells:
                    continue
                base = np.array(cell, float) + np.eye(3)[axis] * (sign > 0)
                quad = [base, base + across, base + across + up, base + up]
                quads.append(quad if sign > 0 else quad[::-1])
    points, corners = np.unique(np.array(quads).reshape(-1, 3), axis=0, return_inverse=True)
    corners = corners.reshape(-1, 4)
    return points * side + low, np.concatenate([corners[:, [0, 1, 2]], corners[:, [0, 2, 3]]])


CHECKER = [(0, 0, 0), (1, 1, 0), (0, 1, 1), (1, 0, 1)]


def mended_fixture():
    """(points, faces, normals, faces wound inside out): four cubes each touching the others along an edge (a checker,
    three such edges at its middle corner), a fold (two slabs joined by two columns that touch along an edge), a cube
    wound inside out, a crumb, a membrane, a doubled face and a collapsed one; the normals outward."""
    parts = [voxels(CHECKER),
             voxels([(x, y, z) for x in (0, 1) for y in (0, 1) for z in (-1, 1)] + [(0, 0, 0), (1, 1, 0)], (10, 0, 0)),
             voxels([(0, 0, 0)], (20, 0, 0)), voxels([(0, 0, 0)], (30, 0, 0), 0.01)]
    offsets = np.cumsum([0] + [len(part) for part, _ in parts])
    points = np.concatenate([part for part, _ in parts])
    faces = np.concatenate([triangles + offset for (_, triangles), offset in zip(parts, offsets)])
    normals = np.zeros_like(points)
    np.add.at(normals, faces, np.repeat(repair.crossed(points, faces)[:, None], 3, 1))
    inside_out = np.flatnonzero((points[faces[:, 0], 0] >= 20) & (points[faces[:, 0], 0] < 30))
    faces[inside_out] = faces[inside_out][:, ::-1]
    at = {tuple(point): number for number, point in enumerate(points[:offsets[1]])}
    membrane = [at[(0, 0, 0)], at[(1, 0, 0)], at[(1, 1, 1)]]
    seam = len(points)  # a seam's copy of the first corner, a face on it collapsed
    extra = np.array([membrane, membrane[::-1], faces[offsets[1]], [at[(0, 0, 0)], seam, at[(1, 0, 0)]]])
    return (np.concatenate([points, points[at[(0, 0, 0)]][None]]), np.concatenate([faces, extra]),
            np.concatenate([normals, normals[at[(0, 0, 0)]][None]]), len(inside_out))


def shim():
    spec = importlib.util.spec_from_file_location("flash_attn_shim", HERE / "shim/flash_attn/__init__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cabinet_scene():
    """A cabinet in a made model's frame (glTF's y up, front +z): its carcass 0.5 x 0.8 x 0.4 m, a door 2 cm thick on
    its front's upper part and a drawer front under it; each its own mesh. Its camera looks from the front, to the
    right and above (route_cast.close_up_camera's eye, right, up, horizontal field)."""
    import trimesh
    scene = trimesh.Scene()
    for name, extents, middle in (("carcass", (0.5, 0.8, 0.4), (0.0, 0.4, 0.0)),
                                  ("door", (0.48, 0.48, 0.02), (0.0, 0.54, 0.21)),
                                  ("drawer", (0.48, 0.26, 0.02), (0.0, 0.15, 0.21))):
        scene.add_geometry(trimesh.creation.box(extents).apply_translation(middle), node_name=name, geom_name=name)
    eye, target = np.array([0.5, 0.9, 2.5]), np.array([0.0, 0.4, 0.0])
    ahead = (target - eye) / np.linalg.norm(target - eye)
    right = np.cross(ahead, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    return scene, (eye, right, np.cross(right, ahead), np.radians(40.0))


def picture_box(corners, camera, size):
    """[left, top, right, bottom] shares of the picture round the projected `corners`, a pixel out each way."""
    seen = made_parts.projected(corners, camera, size)
    return [*((seen.min(0) - 1) / size).tolist(), *((seen.max(0) + 1) / size).tolist()]


def test_a_made_model_fits_its_place_its_paint_and_its_weight(tmp_path):
    like = ell_points()
    made = fit.applied(fit.yawed(90.0), like) * 0.4 + [3.0, 1.0, -2.0]
    matrix, how = fit.fitted_matrix(made, like)
    assert how["yaw"] == 270.0 and abs(how["scale"] - 2.5) < 0.01 and how["distance_m"] < 0.02
    tall = fit.applied(fit.height_matrix(made, 1.8), made)
    assert abs(np.ptp(tall[:, 1]) - 1.8) < 1e-9 and abs(tall[:, 1].min()) < 1e-9
    true = np.ptp(like, 0) * 2  # the size is the L's at twice (Y up: wide x, tall y, deep z); TRELLIS.2 drew it off
    for drawn_as, laid_as, stretch, off in (([1.0, 1.1, 0.88], [1.0, 1.0, 1.0], [1.0, 1 / 0.88, 1 / 1.1], 0.0),
                                            ([1.0, 1.0, 2.0], [1.0, 1.0, 1.6], [1.0, 1 / 1.25, 1.0], 0.6)):
        drawn_model = like * 0.4 * drawn_as
        matrix, how = fit.size_matrix(drawn_model, (true[0], true[2], true[1]))  # wide, deep, tall
        sized = fit.applied(matrix, drawn_model)
        assert np.allclose(np.ptp(sized, 0), true * laid_as) and abs(sized[:, 1].min()) < 1e-9, (np.ptp(sized, 0), how)
        assert np.allclose(how["stretch"], stretch, atol=1e-4) and abs(how["off"] - off) < 1e-4, how
    desk = [([-0.4, -0.9, 0.7], [0.4, 0.9, 0.76]), ([0.2, -0.9, 0.0], [0.4, -0.3, 0.7])]  # a top, drawers right front
    sign = [([-0.5, -0.2, 0.0], [0.5, 0.2, 0.02]), ([-0.5, 0.2, 0.0], [-0.3, 0.3, 0.02])]  # flat, a tab back left
    for boxes, turn, down in ((desk, 35.0, 15.0), (sign, 0.0, 90.0)):
        truth = z_up_to_model(boxes, 0.0)
        for yaw in (90.0, 180.0):  # TRELLIS.2's own headings
            heading, how = fit.headed(z_up_to_model(boxes, yaw), drawn(boxes, turn, down), turn, down)
            laid = fit.applied(heading, z_up_to_model(boxes, yaw))
            assert np.linalg.det(heading[:3, :3]) > 0 and (how["yaw"] + yaw) % 360 == 0 and np.allclose(np.sort(laid, 0),
                                                                                          np.sort(truth, 0)), how
    slab = holed_slab(tmp_path / "slab.glb")
    mesh, texels, factor = front.textured(slab)
    shown = front.drawn(mesh, texels, factor, fit.yawed(180.0), (0, 0, 400, 400), (60, 130, 340, 270), (400, 400),
                        35.0, 15.0)  # the close-up: the slab TRELLIS.2 laid a half turn off, its hole far right
    from PIL import Image
    alpha = np.where(np.any(shown != front.BACKDROP.astype(np.uint8), -1), 255, 0).astype(np.uint8)
    Image.fromarray(np.dstack([shown, alpha]), "RGBA").save(tmp_path / "slab.png")
    cut = alpha > 127
    points = np.asarray(mesh.sample(4000, seed=2))
    heading, how = fit.headed(points, cut, 35.0, 15.0, lambda matrices: front.picked(
        "desk", slab, tmp_path / "slab.png", cut, 35.0, 15.0, matrices, ask=nearest_hole))
    assert how["open"] == [0.0, 180.0] and how["yaw"] == 180.0 and how["front"] == "the cable hole", how
    from score.stages.place_build import maker
    from score.stages.place_build.maker import generate
    assert [maker.faces_for(size) for size in (0.3, 1.0, 3.0, None)] == [maker.LEAST_FACES, 125000, generate.FACES,
                                                                       generate.FACES]  # a sprout, a chair, a wall
    assert [generate.band_for(clear) for clear in (0.0, 0.005, 0.02)] == [(1, 0.0), (1, 0.0), (
        generate.BAND, generate.PROJECT)]  # the drill, the cart and the locker at band 1; the fridge's glass at BAND
    import subprocess
    library, origin = tmp_path / "library", tmp_path / "origin.git"
    for command in (["init", "-q", "--bare", "-b", "main", str(origin)], ["init", "-q", "-b", "main", str(library)],
                    ["-C", str(library), "commit", "-q", "--allow-empty", "-m", "one"],
                    ["-C", str(library), "remote", "add", "origin", str(origin)],
                    ["-C", str(library), "push", "-q", "origin", "main"],
                    ["-C", str(library), "worktree", "add", "-q", "--detach", str(tmp_path / "beside")],
                    ["-C", str(library), "commit", "-q", "--allow-empty", "-m", "two"],
                    ["-C", str(library), "push", "-q", "origin", "main"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *command], check=True)
    maker.brought_forward(tmp_path / "beside")  # the detached worktree, one commit behind origin's main
    assert subprocess.run(["git", "-C", str(tmp_path / "beside"), "log", "-1", "--format=%s"], capture_output=True,
                          text=True).stdout.strip() == "two"
    assert maker.lock_file(library) == maker.lock_file(tmp_path / "beside") == (library / ".git" / "score-make.lock")
    open(maker.lock_file(tmp_path / "beside"), "w").close()  # a worktree's lock is written, one for both checkouts
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
    moved = np.eye(4)
    moved[:3, 3] = [1.0, 2.0, 3.0]  # the decoded mesh set in the place under the placed model's own matrix (#159)
    import shutil
    shutil.copyfile(slab, generate.decoded_path(tmp_path / "trellis.glb"))
    placed = glb.with_root_matrix(glb.read(slab)[0], moved)
    kept = [maker.decoded_placed(tmp_path / name, placed, tmp_path / "decoded.glb") for name in ("none.glb",
                                                                                                "trellis.glb")]
    shape, _ = glb.read(tmp_path / "decoded.glb")
    laid = shape["nodes"][shape["scenes"][0]["nodes"][0]]["matrix"]
    assert kept == [False, True] and np.allclose(glb.root_matrix(placed), moved) and laid == placed["nodes"][-1][
        "matrix"], (kept, glb.root_matrix(placed), laid)

    tokens = {"olive": "#6e7052", "sky": "#1a2238"}
    near = np.ones((4, 4, 3)) * np.array([0x70, 0x78, 0x50]) / 255
    far = np.ones((4, 4, 3)) * np.array([0xe0, 0x20, 0xc0]) / 255
    picture = np.concatenate([near, far], 1)
    moved, groups = grade.graded(picture, picture.reshape(-1, 3), tokens)
    before, after, target = grade.lab(near[0, 0]), grade.lab(moved[0, 0]), grade.hex_lab(tokens["olive"])
    assert np.allclose(after - before, grade.GRADE * (target - before), atol=0.5)
    assert [group["mismatch"] for group in groups] == [False, True] or \
        [group["mismatch"] for group in sorted(groups, key=lambda group: group["delta_e"])] == [False, True]

    painted = {"material": "m_opaque__metal__painted_gray_a01", "nonvisual": {"base": "steel"},
               "recipe": {"recipe": "grained_wood"}}
    brushed = {"material": "m_opaque__metal__aluminium_brushed_e01", "nonvisual": {"base": "aluminum"}}
    assert [sim.surface_class(record) for record in (painted, brushed, {"recipe": "boards"}, {"recipe": "sand"})] \
        == ["metal", "aluminium", "wood", None]
    assert sim.material("aluminium")["static"] == 0.61 and sim.material("metal")["static"] == 0.3
    small, wide = cube(np.zeros(3)), cube(np.array([1.0, 0.0, 0.0]))
    wide = (wide[0] * np.array([2.0, 1.0, 1.0]) - np.array([1.0, 0.0, 0.0]), wide[1])  # x 1 to 3: 2 m^3
    faces = np.concatenate([small[1], wide[1] + 8])
    classes = sim.hull_classes(np.concatenate([small[0], wide[0]]), faces, ["metal"] * 12 + ["wood"] * 12,
                               [small, wide])
    assert classes == ["metal", "wood"]
    parts = [{"words": "frame", "class": "metal", "share": 0.5, "kg": 30.0},
             {"words": "top", "class": "wood", "share": 0.5, "kg": 12.0}]
    weighed = sim.physical([small, wide], classes, parts, [3.0, 1.0, 1.0])
    assert weighed["static"] == round((0.3 * 1 + 0.5 * 2) / 3, 4) and weighed["mass_kg"] == 42.0
    assert weighed["bulk"] == {"density": 14.0, "size_class": "large", "band": [6.5, 390.0], "in_band": True}
    asked = []
    answer = sim.weighed("a desk", [3.0, 1.0, 1.0], parts[:1], ask=lambda body: asked.append(body) or json.dumps(
        {"whole_kg": 30, "reason": "steel", "parts": [{"part": 0, "kg": 30}]}))
    assert answer == [30.0] and "a desk" in asked[0]["contents"][0]["parts"][-1]["text"]
    try:
        sim.weighed("a desk", [3.0, 1.0, 1.0], parts, ask=lambda body: json.dumps(
            {"whole_kg": 30, "reason": "steel", "parts": [{"part": 0, "kg": 30}]}))
        raise AssertionError("an answer that weighs one of two parts was kept")
    except ValueError:
        pass
    ink = [parts[0], {"words": "white printed ink", "class": "paper", "share": 0.0}, parts[1],
           {"words": "dark interior seen through vent holes", "class": "metal", "share": 0.0004}]
    assert sim.weighed("a toaster", [0.3, 0.2, 0.2], ink, ask=lambda body: json.dumps(
        {"whole_kg": 42, "reason": "steel", "parts": [{"part": 0, "kg": 30}, {"part": 1, "kg": 12}]})) \
        == [30.0, 0.0, 12.0, 0.0], "a part of no area is asked or weighed"

    # Moving parts (#177): the cabinet's door and drawer, seen in its close-up, cut and jointed as worked by hand.
    import trimesh
    scene, camera = cabinet_scene()
    size = (400, 400)
    meshes = scene.dump(concatenate=False)
    vertices = np.concatenate([mesh.vertices for mesh in meshes])
    faces = np.concatenate([mesh.faces + sum(len(other.vertices) for other in meshes[:index])
                            for index, mesh in enumerate(meshes)])
    door_corners, drawer_corners = (np.array([[x, y, 0.22] for x in (-0.24, 0.24) for y in ys])
                                    for ys in ((0.3, 0.78), (0.02, 0.28)))
    said = {"reason": "a cabinet", "parts": [
        {"name": "Door", "joint": "hinge", "box": picture_box(door_corners, camera, size), "hinge": "left",
         "opens": 100, "thick_m": 0.018},
        {"name": "drawer", "joint": "slide", "box": picture_box(drawer_corners, camera, size), "hinge": "none",
         "opens": 0.6, "thick_m": 0.018}]}
    import score.stages.surfaces  # noqa: F401  (its modules import one another through it)
    import route_cast
    ways = route_cast.pixel_ways(camera, size, made_parts.projected(door_corners, camera, size))
    assert np.allclose(ways, (door_corners - camera[0]) / np.linalg.norm(door_corners - camera[0], axis=1)[:, None])
    asked = []
    listed = made_parts.asked("a kitchen cabinet", [0.5, 0.4, 0.8],
                              ask=lambda body: asked.append(body) or json.dumps(said))
    assert "kitchen cabinet" in asked[0]["contents"][0]["parts"][-1]["text"] and listed[0]["name"] == "door"
    for wrong in ({"box": [0.6, 0.1, 0.4, 0.5]}, {"hinge": "none"}, {"joint": "twist"}):
        try:
            made_parts.asked("a cabinet", [0.5, 0.4, 0.8], ask=lambda body: json.dumps(
                {"reason": "", "parts": [{**said["parts"][0], **wrong}]}))
            raise AssertionError(f"a piece answered {wrong} was kept")
        except ValueError:
            pass
    face_part, left_out = made_parts.cut(vertices, faces, listed, camera, size)
    # Each slab's 12 triangles but its two at the back (z 0.2, behind its outer face 0.22 less 0.018 m) are its part.
    assert left_out == {} and [int((face_part[12 * slab:12 * slab + 12] == part).sum())
                               for slab, part in ((0, -1), (1, 0), (2, 1))] == [12, 10, 10], face_part
    joints = made_parts.jointed(vertices, faces, face_part, listed, camera, size)
    # The door hinges about the upright (y) at its left edge (x -0.24) and back (z 0.2); about +y its free edge
    # would swing in, so the way is -y. The drawer slides out along +z, its 0.6 m held to the model's 0.42 m depth.
    assert joints == {0: {"axis": "y", "sign": -1, "pivot": [-0.24, 0.54, 0.2], "limits": [0.0, 100.0]},
                      1: {"axis": "z", "sign": 1, "pivot": [0.0, 0.15, 0.21], "limits": [0.0, 0.42]}}, joints
    written = made_parts.record(listed, face_part, joints, left_out)
    assert [part["node"] for part in written["parts"]] == ["door_01__hinge_yn", "drawer_01__slide_z"]
    from score.stages.motion import from_design
    assert all(from_design.PART.match(part["node"]) for part in written["parts"])
    model = tmp_path / "cabinet.glb"
    scene.export(str(model))
    made_parts.written(model, face_part, written, tmp_path / "parted.glb")
    back = trimesh.load(str(tmp_path / "parted.glb"), force="scene")
    door_matrix, _ = back.graph["door_01__hinge_yn"]
    held = back.graph.transforms.children.get("door_01__hinge_yn", [])
    door_points = np.concatenate([trimesh.transform_points(back.geometry[back.graph[child][1]].vertices,
                                                           back.graph[child][0]) for child in held])
    assert np.allclose(door_matrix[:3, 3], [-0.24, 0.54, 0.2]) and np.allclose(door_points.min(0), [-0.24, 0.3, 0.2])
    # make's own cut (parts.made, #177): the close-up a cut-out drawn through the camera, its camera fitted from that
    # outline, the same answer: both parts cut and jointed, the model's kg shared by area, the parted GLB written
    from PIL import Image
    hit = route_cast.close_up_cast(route_cast.loaded(model), camera, size)[0] >= 0
    alpha = np.asarray(Image.fromarray((hit * 255).astype(np.uint8)).resize(size, Image.NEAREST))
    picture = tmp_path / "close_up.png"
    Image.fromarray(np.dstack([np.full(alpha.shape + (3,), 128, np.uint8), alpha])).save(picture)
    moving = made_parts.made(model, picture, "a kitchen cabinet", [0.5, 0.4, 0.8], 12.0, tmp_path / "made.glb",
                             ask=lambda body: json.dumps(said))
    assert [part["node"] for part in moving["parts"]] == ["door_01__hinge_yn", "drawer_01__slide_z"], moving
    assert abs(sum(part["kg"] for part in moving["parts"]) + moving["body"]["kg"] - 12.0) < 1e-3
    assert {"door_01__hinge_yn", "drawer_01__slide_z"} <= set(trimesh.load(str(tmp_path / "made.glb"),
                                                                         force="scene").graph.nodes)
    assert made_parts.made(model, picture, "a crate", [0.5, 0.4, 0.8], 12.0, tmp_path / "none.glb",
                           ask=lambda body: json.dumps({"reason": "nothing moves", "parts": []})) is None
    kg, body_kg = made_parts.part_masses([-1, -1, 0, 1], [0, 0, 1, 1], [6.0, 4.0], [1.0, 2.0, 1.0, 3.0], 2)
    assert kg == [1.0, 3.0] and body_kg == 6.0  # the second group's 4 kg by area, 1 to 3
    classes = made_parts.part_classes([-1, -1, 0, 0, 0], ["metal", "wood", "glass", "glass", "rubber"],
                                      [1.0, 2.0, 1.0, 1.0, 1.5], 2)
    assert classes == (["glass", None], "wood")  # the door's glass 2 against its rubber 1.5; the body's wood 2

    models = cloud.REPO / "tools/cloud/images/meshparts/models.json"
    listed = {model["name"] for model in json.loads(models.read_text())}
    job = cloud.job_of([("/pictures/a.png", "/made/a/a.glb"), ("/pictures/b.png", "/made/b/b.glb")])
    assert set(job["models"]) <= listed and job["command"][-1].count("generate.py") == 2
    assert [entry["local"] for entry in job["outputs"]] == ["/made/a/.cloud-0", "/made/b/.cloud-1"]
    for number, decoded in enumerate((True, False)):  # a model back from the cloud with its decoded mesh, and one without
        back, out = tmp_path / f".cloud-{number}", tmp_path / f"cloud{number}" / "trellis.glb"
        back.mkdir()
        out.parent.mkdir()
        for name in ("model.glb", "model.json") + (("model-decoded.glb",) if decoded else ()):
            (back / name).write_text(json.dumps({"from": name}))
        assert cloud.brought_back(back, out) == {"from": "model.json"} and not back.exists()
        assert (out.is_file(), generate.decoded_path(out).is_file()) == (True, decoded)

    points, faces, normals, inside_out = mended_fixture()  # #167: the mesh repaired, its shape kept
    sources, kept, mended, counts = repair.repaired(points, faces, normals)
    assert [counts[name] for name in ("collapsed", "repeated", "loose_pieces", "turned")] == [1, 3, 1, inside_out]
    corner = repair.corners_of(kept, repair.diagonal(kept))
    starts, ends, *_, held = repair.half_edges(corner[mended])
    assert (held == 2).all() and (np.unique(np.stack([starts, ends], 1), axis=0, return_counts=True)[1] == 1).all()
    assert len(np.unique(repair.pieces(corner[mended], corner.max() + 1))) == 6  # the checker's cubes parted, no crumb
    offset = kept - points[sources]
    length = np.linalg.norm(offset, axis=1)
    moved = np.flatnonzero(length)
    assert len(moved) == 11 and length.max() <= repair.NUDGE * repair.diagonal(points) * 1.001
    into = np.floor(kept[moved] + offset[moved] / length[moved, None] * 0.1).astype(int)  # each copy into its own cube
    assert all(tuple(cell) in CHECKER for cell, number in zip(into, moved) if kept[number, 0] < 5)
    assert (np.einsum("ij,ij->i", repair.crossed(kept, mended), normals[sources][mended].sum(1)) > 0).all()
    faced = np.zeros_like(kept)  # #159: a vertex normal turned into the body is set to its faces'
    np.add.at(faced, mended, np.repeat(repair.crossed(kept, mended)[:, None], 3, 1))
    turned_in = faced * np.where(np.arange(len(kept)) < 5, -1.0, 1.0)[:, None]
    fixed, count = repair.facing_normals(kept, mended, turned_in)
    assert count == 5 and np.allclose(fixed[5:], faced[5:]) and (np.einsum("ij,ij->i", fixed, faced) > 0).all()
    document = {"asset": {"version": "2.0"}, "meshes": [{"primitives": [{"attributes": {"POSITION": 0,
                "TEXCOORD_0": 1}, "indices": 2}]}], "images": [{"bufferView": 3}], "buffers": [{"byteLength": 0}],
                "accessors": [{"bufferView": 0, "componentType": 5126, "type": "VEC3", "count": len(points)},
                              {"bufferView": 1, "componentType": 5126, "type": "VEC2", "count": len(points)},
                              {"bufferView": 2, "componentType": 5125, "type": "SCALAR", "count": faces.size}]}
    pieces = [points.astype(np.float32).tobytes(), points[:, :2].astype(np.float32).tobytes(),
              faces.astype(np.uint32).tobytes(), b"picture!"]
    document["bufferViews"] = [{"buffer": 0, "byteOffset": int(sum(map(len, pieces[:number]))),
                                "byteLength": len(piece)} for number, piece in enumerate(pieces)]
    document, binary, _ = repair.repaired_glb(document, b"".join(pieces))
    glb.write(tmp_path / "mended.glb", document, binary)
    again, data = glb.read(tmp_path / "mended.glb")
    assert np.array_equal(repair.accessor_array(again, data, 2).reshape(-1, 3), repair.repaired(points, faces)[2])
    assert np.array_equal(repair.accessor_array(again, data, 1),
                          points[repair.repaired(points, faces)[0], :2].astype(np.float32))
    assert glb.image(again, data, 0) == b"picture!"

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

    def checkpoint_load(held):  # trellis2.models.from_pretrained's way: built, then read with strict=False
        def load(path):
            model = torch.nn.Sequential(torch.nn.Linear(4, 3), torch.nn.LayerNorm(3))
            model.register_buffer("rope_phases", torch.arange(3.0))  # made by the model itself
            model.load_state_dict(held, strict=False)
            return model
        return load
    saved = {key: torch.full_like(value, 0.5) for key, value in checkpoint_load({})("whole").state_dict().items()
             if key != "rope_phases"}
    fills = [getattr(torch.nn.init, name) for name in generate.FILLS]
    built = generate.unfilled(checkpoint_load(saved))("whole")
    assert all(torch.equal(built.state_dict()[key], value) for key, value in saved.items())
    assert fills == [getattr(torch.nn.init, name) for name in generate.FILLS]  # torch's fills given back
    try:
        generate.unfilled(checkpoint_load({key: value for key, value in saved.items() if key != "0.bias"}))("short")
        raise AssertionError("a checkpoint missing a weight was built unfilled")
    except SystemExit as why:
        assert "0.bias" in str(why), why

    def drawing_load(path):  # a model whose making draws from torch's generator, as a stand-in for any that might
        torch.rand(3)
        return torch.nn.Linear(2, 2)
    held = {"decoder": torch.nn.Linear(1, 1)}
    on_use = generate.OnUse(held, {"flow": "flow.safetensors"}, drawing_load)
    torch.manual_seed(42)
    expected = torch.rand(4)
    torch.manual_seed(42)
    assert "flow" in on_use and "flow" not in dict(on_use) and not on_use["flow"].training
    assert torch.equal(torch.rand(4), expected)  # read on use, the seeded draws as if it were read before
    on_use["flow"].cpu()
    assert next(on_use["flow"].parameters()).device.type == "meta" and set(on_use) == {"decoder", "flow"}
    coords = torch.tensor(random.integers(0, 50, (40, 3)), dtype=torch.int32)
    signs = torch.tensor(random.integers(-1, 2, (40, 3)), dtype=torch.int32)
    table = remesh.tables("cpu")
    every_edge = coords.reshape(40, 1, 1, 3) + table["edge_neighbours"].unsqueeze(0)  # cumesh's (voxel, edge) build
    connected, crossed = remesh.crossing(table, coords, signs)
    assert torch.equal(connected, every_edge[signs != 0]) and torch.equal(crossed, signs[signs != 0])
