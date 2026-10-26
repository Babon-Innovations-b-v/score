"""ending.py's counts: a stage's layer stack read bottom first, and each layer's prims counted, on a stage made here.

Break (applied once, seen red, reverted), in tools/review/ending.py: layer_stack reads the sublayers strongest first
(no `reversed`).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ending  # noqa: E402


def test_stack_and_prims_per_layer(tmp_path):
    (tmp_path / "layers").mkdir()
    (tmp_path / "layers/base.usda").write_text('#usda 1.0\ndef Xform "p" {\n def Xform "a" {}\n def Xform "b" {}\n}\n')
    (tmp_path / "layers/light.usda").write_text('#usda 1.0\nover "p" {\n def Xform "lamp" {}\n}\n')
    (tmp_path / "p.usda").write_text('#usda 1.0\n(\n subLayers = [@./layers/light.usda@, @./layers/base.usda@]\n)\n')
    assert ending.layer_stack(tmp_path / "p.usda") == ["base", "light"]
    points, prims = ending.layer_points(tmp_path / "p.usda")
    assert [len(points["base"]), len(points["light"])] == [3, 2]
    assert prims == {"base": 3, "light": 2}
