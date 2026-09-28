"""Check standing a model upright, padding its maps and cutting triangles out, on shapes whose
right answer is obvious.

The step needs numpy, scipy, trimesh and Pillow, which only the prop environment has. Run by the gate with
the system python, this hands itself to the prop environment when the box has one, and says it
skipped when it does not, so a box without the tool chain still passes.

Run: python3 tools/props/glb_file_test.py
"""
import io
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
    from PIL import Image
    import scipy  # noqa: F401
    import trimesh  # noqa: F401
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("GLB_FILE_TEST_HANDED") != "1":
        os.environ["GLB_FILE_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import glb_file  # noqa: E402

UP = np.array([0.0, 1.0, 0.0])


def tilted(points, degrees, axis=(1.0, 0.0, 0.0)):
    """The points turned `degrees` about `axis`, the way a picture's camera leaves a model."""
    axis = np.array(axis) / np.linalg.norm(axis)
    angle = np.radians(degrees)
    skew = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    turn = np.eye(3) + np.sin(angle) * skew + (1 - np.cos(angle)) * skew @ skew
    return points @ turn.T


def box(width, height, depth, count=4000, seed=0):
    """Points filling a box standing on the ground, centred over the origin."""
    return (np.random.default_rng(seed).random((count, 3)) - [0.5, 0.0, 0.5]) * [width, height, depth]


def one_quad_file(size=16):
    """A model file holding one square facing up, whose UVs cover the left half of a picture that
    is red there and black elsewhere, as a bake leaves it."""
    positions = np.array([[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]], dtype=np.float32)
    normals = np.tile(np.array([0, 1, 0], dtype=np.float32), (4, 1))
    uv = np.array([[0, 0], [0.5, 0], [0.5, 1], [0, 1]], dtype=np.float32)
    indices = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint16)
    pixels = np.zeros((size, size, 3), dtype=np.uint8)
    pixels[:, : size // 2] = [200, 30, 30]
    picture = io.BytesIO()
    Image.fromarray(pixels).save(picture, "PNG")
    views = [positions.tobytes(), normals.tobytes(), uv.tobytes(), indices.tobytes(), picture.getvalue()]
    document = {
        "asset": {"version": "2.0"},
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2}, "indices": 3}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "type": "VEC3", "count": 4,
             "min": positions.min(0).tolist(), "max": positions.max(0).tolist()},
            {"bufferView": 1, "componentType": 5126, "type": "VEC3", "count": 4},
            {"bufferView": 2, "componentType": 5126, "type": "VEC2", "count": 4},
            {"bufferView": 3, "componentType": 5123, "type": "SCALAR", "count": 6},
        ],
        "bufferViews": [{"buffer": 0, "byteLength": len(view)} for view in views],
        "images": [{"bufferView": 4, "mimeType": "image/png"}],
    }
    return document, views


def a_tilted_crate_stands_back_up():
    points = tilted(box(1.0, 0.6, 0.8), 35)
    turn = glb_file.upright_turn(points)
    height = np.ptp(points @ turn.T, axis=0)[1]
    return [] if abs(height - 0.6) < 0.03 else [f"a crate 0.6 tall stood up {height:.2f} tall"]


def a_tall_rocket_stands_on_its_long_side():
    points = tilted(box(0.5, 2.0, 0.5), 50, (1.0, 0.0, 1.0))
    turn = glb_file.upright_turn(points, long=True)
    height = np.ptp(points @ turn.T, axis=0)[1]
    return [] if abs(height - 2.0) < 0.1 else [f"a rocket 2.0 tall stood up {height:.2f} tall"]


def a_model_on_legs_is_levelled_on_its_feet():
    """Four thin legs under a body that leans in the model's own box: the feet decide level."""
    rng = np.random.default_rng(1)
    body = box(1.0, 1.0, 1.0, 3000) + [0.4, 0.6, 0.0]
    corners = [(x, z) for x in (-0.8, 0.8) for z in (-0.8, 0.8)]
    feet = [rng.normal([x, 0.0, z], 0.005, (200, 3)) for x, z in corners]
    points = tilted(np.vstack([body, *feet]), 20)
    turn = glb_file.upright_turn(points, feet=True)
    heights = [float((tilted(foot, 20) @ turn.T)[:, 1].mean()) for foot in feet]
    spread = max(heights) - min(heights)
    return [] if spread < 0.02 else [f"the feet stand {spread:.2f} apart in height, not level"]


def a_long_model_faces_along_an_axis():
    points = tilted(box(0.4, 0.3, 2.0), 40, (0.0, 1.0, 0.0))
    extents = np.ptp(points @ glb_file.upright_turn(points).T, axis=0)
    return [] if extents[2] > 1.9 else [f"the long side lies {extents.round(2)} rather than along Z"]


def a_rocket_section_stands_on_its_own_axis():
    """A tube with fins at its foot and a box on its side, tilted: fins and box fool the other
    ways of standing it up, the tube's axis does not."""
    rng = np.random.default_rng(2)
    angle = rng.random(6000) * 2 * np.pi
    height = rng.random(6000) * 2.0
    tube = np.c_[0.3 * np.cos(angle), height, 0.3 * np.sin(angle)]
    fins = np.vstack([box(0.05, 0.5, 1.4, 800, seed) for seed in (3, 4)])
    fins[800:] = fins[800:, [2, 1, 0]]
    side_box = box(0.3, 0.4, 0.3, 600, 5) + [0.4, 1.2, 0.0]
    points = tilted(np.vstack([tube, fins, side_box]), 12, (1.0, 0.0, 0.5))
    turn = glb_file.upright_turn(points, long=True, tube=True)
    axis = glb_file.tube_axis(points @ turn.T)
    lean = np.degrees(np.arccos(min(1.0, axis[1])))
    return [] if lean < 1.5 else [f"the section still leans {lean:.1f} degrees"]


def the_file_keeps_its_shape_and_turns_its_normals():
    document, views = one_quad_file()
    turn = glb_file.rotation_between(np.array([0.0, 1.0, 0.0]), np.array([1.0, 0.0, 0.0]))
    glb_file.turned(document, views, turn)
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "quad.glb"
        glb_file.write(document, views, path)
        document, views = glb_file.read(path)
    normals = glb_file.accessor_array(document, views, 1)
    found = []
    if not np.allclose(normals, [1, 0, 0], atol=1e-5):
        found.append(f"normals turned to {normals[0]}, not along X")
    if not np.allclose(document["accessors"][0]["max"][0], 0.0, atol=1e-5):
        found.append("the positions' bounds were not updated with the turn")
    return found


def cutting_a_triangle_keeps_the_rest_as_it_was():
    document, views = one_quad_file()
    glb_file.without_triangles(document, views, [False, True])
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "quad.glb"
        glb_file.write(document, views, path)
        document, views = glb_file.read(path)
    corners = glb_file.accessor_array(document, views, 0)[glb_file.accessor_array(document, views, 3)]
    uv = glb_file.accessor_array(document, views, 2)[glb_file.accessor_array(document, views, 3)]
    found = []
    if not np.allclose(corners, [[0, 0, 0], [1, 0, 0], [1, 0, 1]]):
        found.append(f"the kept triangle's corners moved: {corners.tolist()}")
    if not np.allclose(uv, [[0, 0], [0.5, 0], [0.5, 1]]):
        found.append(f"the kept triangle's UVs changed: {uv.tolist()}")
    if document["accessors"][0]["count"] != 3:
        found.append(f"{document['accessors'][0]['count']} corners kept, not the triangle's own 3")
    return found


def padding_fills_the_black_from_the_nearest_piece():
    document, views = one_quad_file()
    glb_file.padded(document, views)
    pixels = np.asarray(Image.open(io.BytesIO(views[4])).convert("RGB")).astype(int)
    darkest = pixels.sum(-1).min()
    return [] if darkest > 150 else [f"a texel is still near black ({darkest}) after padding"]


CHECKS = (
    a_tilted_crate_stands_back_up,
    a_tall_rocket_stands_on_its_long_side,
    a_model_on_legs_is_levelled_on_its_feet,
    a_long_model_faces_along_an_axis,
    a_rocket_section_stands_on_its_own_axis,
    the_file_keeps_its_shape_and_turns_its_normals,
    cutting_a_triangle_keeps_the_rest_as_it_was,
    padding_fills_the_black_from_the_nearest_piece,
)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
