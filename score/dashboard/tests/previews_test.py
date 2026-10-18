"""Every step card has a picture: an output with no image of its own gets one drawn from its own files (each kind
makes a real picture), made once and kept, served and listed like any picture; never made in a hosted process
(hosted_light_test checks the modules)."""
import json
import pathlib
import struct
import wave

import pytest
from PIL import Image

from score.dashboard import previews

pytestmark = pytest.mark.django_db
KNOWN = {"bare_steel": ((140, 145, 150), 0.5, 0.8), "rubber": ((30, 30, 30), 0.9, 0.0)}
PLAN = {"place": "alpha", "title": "ALPHA", "walls": {"wide": 8}, "floor": [[-4, -6], [4, 6]],
        "items": [{"name": "BENCH", "box": [-3, -5, -1, -3]}, {"name": "RACK", "box": [1, 2, 3, 5]}],
        "doors": [{"name": "S", "middle": [0, 0, 6]}], "standing": [{"at": [0, 0]}]}


def written(folder, name, data):
    path = folder / name.replace("/", "_")
    path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())
    return name, path


def ply(points):
    header = f"ply\nformat ascii 1.0\nelement vertex {len(points)}\nproperty float x\nproperty float y\n" \
             "property float z\nend_header\n"
    return (header + "".join(f"{x} {y} {z}\n" for x, y, z in points)).encode()


def wav(folder):
    path = folder / "hum.wav"
    with wave.open(str(path), "wb") as sound:
        sound.setnchannels(1)
        sound.setsampwidth(2)
        sound.setframerate(8000)
        sound.writeframes(b"".join(struct.pack("<h", int(8000 * ((step % 40) / 20 - 1))) for step in range(8000)))
    return "sounds/hum.wav", path


USDA = """#usda 1.0
def Xform "alpha" {
    def Xform "lamp_1" {
        double3 xformOp:translate = (1, 2, 3)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
    def Xform "lamp_2" {
        double3 xformOp:translate = (-2, 2, -1)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
}
"""


def kinds(folder):
    """{kind: the output's files} of every drawer."""
    return {
        "plan": [written(folder, "plan.json", PLAN)],
        "settle": [written(folder, "settle.json", {"place": "alpha", "objects": {
            "crate_1": {"rested": True, "matrix": [[1, 0, 0, 1.0], [0, 1, 0, 0], [0, 0, 1, 2.0], [0, 0, 0, 1]]},
            "desk_1": {"rested": False, "matrix": [[1, 0, 0, -2.0], [0, 1, 0, 0], [0, 0, 1, -1.0], [0, 0, 0, 1]]}}})],
        "swatches": [written(folder, "desk.json", {"take": "desk", "finishes": [
            {"parts": "top", "surface": "bare_steel"}, {"parts": "feet", "surface": "rubber"}]})],
        "paint": [written(folder, "labelled/desk/bare_steel.ply", ply([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]))],
        "sound": [wav(folder)],
        "layer": [written(folder, "layers/light.usda", USDA.encode())],
        "positions": [written(folder, "lamps.json", {"place": "alpha", "lamps": [
            {"path": "/alpha/l1", "spot": [1, 3, 1]}, {"path": "/alpha/l2", "spot": [-1, 3, -2]}]})],
        "tiles": [written(folder, "rows.json", {"rows": [{"id": "ship"}, {"id": "engine"}]})],
    }


def test_each_kind_draws_a_real_picture(tmp_path):
    for kind, files in kinds(tmp_path).items():
        path = previews.picture(files, PLAN, KNOWN, tmp_path / "home", f"output-{kind}", kind)
        with Image.open(path) as drawn:
            colours = drawn.convert("RGB").getcolors(1 << 20)
        assert drawn.width > 100 and colours and len(colours) > 2, kind


def test_the_drawer_follows_the_files_not_the_stage(tmp_path, monkeypatch):
    chosen = []
    for module, function in ((previews.maps, "plan_picture"), (previews.maps, "settle_picture"),
                             (previews.swatches, "picture"), (previews.paint, "picture"),
                             (previews.sheets, "waveforms"), (previews.maps, "positions_picture"),
                             (previews.sheets, "tiles")):
        real = getattr(module, function)
        monkeypatch.setattr(module, function, lambda *args, real=real, name=function, **kwargs: (
            chosen.append(name), real(*args, **kwargs))[1])
    for kind, files in kinds(tmp_path).items():
        chosen.clear()
        previews.draw(files, PLAN, KNOWN, tmp_path / f"{kind}.png", "same words")
        made = [name for name in chosen if name not in ("picture", "waveforms") or chosen[-1] == name]
        assert made, kind
    assert chosen[-1] == "tiles"


def test_a_picture_is_made_once_and_kept(tmp_path, monkeypatch):
    files = kinds(tmp_path)["plan"]
    first = previews.picture(files, PLAN, KNOWN, tmp_path / "home", "output-1", "plan")
    monkeypatch.setattr(previews, "draw", lambda *args: pytest.fail("drawn again"))
    assert previews.picture(files, PLAN, KNOWN, tmp_path / "home", "output-1", "plan") == first
    assert previews.preview_id("output-1") != previews.preview_id("output-2")
    assert len(previews.preview_id("output-1")) == 64


def test_a_step_with_no_picture_of_its_own_gets_its_preview(world):
    from score.dashboard.state.files import SHA
    detail = world.source.step_detail("alpha", "plan")
    pictures = [ref for ref in detail.files if ref.kind == "image"]
    assert [ref.name for ref in pictures] == [previews.PREVIEW_NAME] and SHA.match(pictures[0].sha)
    assert world.source.thumb_path(pictures[0].sha) is not None
    cards = [card for layer in world.source.layer_groups("alpha", with_thumbs=True) for card in layer.steps]
    assert all(card.thumb for card in cards if card.output), [card.stage for card in cards if not card.thumb]
    closeup = world.source.step_detail("alpha", "closeup")
    assert previews.PREVIEW_NAME not in [ref.name for ref in closeup.files]
    assert pathlib.Path(world.source.home / "previews").is_dir()
