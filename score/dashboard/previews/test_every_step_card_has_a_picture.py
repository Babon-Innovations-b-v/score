"""Invariant: every step card has a picture: an output with no image of its own gets one drawn from its own files
(each kind a real picture, picked by its files, never its stage), made once and kept, served and listed like any
picture; a packaged texture is never a step's own picture; a gap's things found by path or name and said in plain
words; a film's middle still on the board's tile. Never made in a hosted process
(sync/test_the_cockpit_gets_the_store_whole_and_the_store_only_the_owners_asks.py checks the modules).

One test, test_every_step_card_has_a_picture: one fixture world and one folder of outputs, every output row drawn
through `previews.picture` with the drawers spied, the kept pictures asked again, the film made once and read both by
`films` and on the board tile, and the judging functions fed their input tables.

Breaks that turn this red (each applied once and seen red, then reverted):
- previews.picture: a blank picture saved in place of `draw(...)` -> an output row's picture is not a real picture
- previews.draw: `found = settle_document(parsed)` -> `found = None` -> the settle row misses maps.settle_picture
- previews.picture: both cache checks dropped -> the kept plan picture is drawn again
- previews.picture: drop its `except Exception` -> one model's fault raises through the pass
- state/local.with_preview: `made = None` -> the plan step lists no preview.png
- meshes: `file_hash(candidate) == sha` -> `True` -> the wrong-hash row draws a model instead of its tiles
- meshes.faces_of: drop the no-faces return -> the point-cloud row's colours raise IndexError, no picture
- meshes.faces_of: drop the plain-grey fallback -> the no-colour-array row raises IndexError, no picture
- state/files.packaged: `return False` -> the packaged-sound row draws waveforms, and the packaged table fails
- previews.record_name: `key` alone -> a named_things row loses its "missing"
- labels.free: `return inside` (taken labels ignored) -> the crowded labels overlap
- canvas.LARGE_DPI = 50 -> the plan row's picture is under 1000 px wide
- previews.stage_root: `if False and "subLayers" in ...` -> the stage row misses maps.stage_picture
- maps.placed_point: the untyped over's own ops -> `if False:` -> a layer_points row misplaces its over
- films.middle_frame: `len(views) // 3` -> the film's middle frame is not 36
- films.projected: `if depth < NEAREST:` -> `if False:` -> a point behind the camera is projected
- state/accepted_gaps.matched: `(_\\d+)?$` -> `.*$` -> the hose_reel row also matches the stand
- state/plain: the placeholders sentence reworded -> beta's accepted gap sentence differs
- state/plain: the plural reach sentence reworded -> the reach row's sentence differs
- state/local.own_image: the packaged filter dropped -> the assembly's picture is its packaged texture
- state/local.concept: K01.png -> K02.png -> alpha's concept is not found once K01.png is there
- state/local still: `path = None` -> alpha's board tile has no film still
"""
import hashlib
import json
import pathlib
import struct
import subprocess
import types
import wave

import numpy
import pytest
import trimesh
from PIL import Image

from score.dashboard import previews
from score.dashboard.previews import canvas, films, labels
from score.dashboard.state import accepted_gaps, plain
from score.dashboard.state.files import SHA, packaged
from score.dashboard.tests import fixture

pytestmark = pytest.mark.django_db
KNOWN = {"bare_steel": ((140, 145, 150), 0.5, 0.8), "rubber": ((30, 30, 30), 0.9, 0.0)}
PLAN = {"place": "alpha", "title": "ALPHA", "walls": {"wide": 8}, "floor": [[-4, -6], [4, 6]],
        "items": [{"name": "BENCH", "box": [-3, -5, -1, -3]}, {"name": "RACK", "box": [1, 2, 3, 5]}],
        "doors": [{"name": "S", "middle": [0, 0, 6]}], "standing": [{"at": [0, 0]}, [1, 1], [2, 0, 2]]}  # both shapes
VIEW = {"eye": [0.0, 1.0, 5.0], "aim": [0.0, 1.0, 0.0], "up": [0.0, 1.0, 0.0], "fov": 90.0}
AWAY = dict(VIEW, aim=[10.0, 1.0, 5.0])

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

MOTION = """#usda 1.0
over "alpha" {
    over "door_leaf" {
        double3 xformOp:translate.timeSamples = {0: (-1, 2, 0), 24: (-3, 2, 0)}
    }
}
"""

SETTLE = """#usda 1.0
over "alpha" {
    over "crate_1" {
        matrix4d xformOp:transform = ( (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (2, 0.5, -3, 1) )
        uniform token[] xformOpOrder = ["xformOp:transform"]
    }
}
"""


def written(folder, name, data):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name.replace("/", "_")
    path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())
    return name, path


def ply(points):
    header = f"ply\nformat ascii 1.0\nelement vertex {len(points)}\nproperty float x\nproperty float y\n" \
             "property float z\nend_header\n"
    return (header + "".join(f"{x} {y} {z}\n" for x, y, z in points)).encode()


def wav(folder, name):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "hum.wav"
    with wave.open(str(path), "wb") as sound:
        sound.setnchannels(1)
        sound.setsampwidth(2)
        sound.setframerate(8000)
        sound.writeframes(b"".join(struct.pack("<h", int(8000 * ((step % 40) / 20 - 1))) for step in range(8000)))
    return name, path


def glb(work, model, geometry):
    """A model saved as `<model>-final.glb` in a work folder one level down, and its hash."""
    path = work / "takes" / f"{model}-final.glb"
    path.parent.mkdir(parents=True, exist_ok=True)
    geometry.export(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def concept(folder):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "concept.png"
    Image.new("RGB", (64, 48), (90, 120, 160)).save(path)
    return str(path)


def film_file(folder, seconds=2):
    """A real two-second 24 fps film, 128 x 72."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "film.mp4"
    subprocess.run([films.tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc=size=128x72:rate=24:duration={seconds}", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def outputs(folder, work):
    """[(row, the output's files, the drawer its files must reach, its least width, colours given as no array)]."""
    crate = trimesh.creation.box(extents=(1, 2, 1))
    crate.visual.vertex_colors = (200, 80, 40, 255)
    crate_sha = glb(work, "crate", crate)
    dust_sha = glb(work, "dust", trimesh.PointCloud(numpy.arange(30, dtype=float).reshape(10, 3)))
    root = b'#usda 1.0\n(\n    subLayers = [@./layers/light.usda@]\n)\n'
    rows = {
        "plan": ([("plan.json", PLAN)], ("maps", "plan_picture"), 1000, False),
        "settle": ([("settle.json", {"place": "alpha", "objects": {
            "crate_1": {"rested": True, "matrix": [[1, 0, 0, 1.0], [0, 1, 0, 0], [0, 0, 1, 2.0], [0, 0, 0, 1]]},
            "desk_1": {"rested": False, "matrix": [[1, 0, 0, -2.0], [0, 1, 0, 0], [0, 0, 1, -1.0], [0, 0, 0, 1]]}}})],
            ("maps", "settle_picture"), 101, False),
        "swatches": ([("desk.json", {"take": "desk", "finishes": [
            {"parts": "top", "surface": "bare_steel"}, {"parts": "feet", "surface": "rubber"}]})],
            ("swatches", "picture"), 101, False),
        "paint": ([("labelled/desk/bare_steel.ply", ply([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]))],
                  ("paint", "picture"), 101, False),
        "sound": (["sounds/hum.wav"], ("sheets", "waveforms"), 101, False),
        "packaged sound": (["assets/sound/hum.wav"], ("sheets", "tiles"), 101, False),
        "layer": ([("layers/light.usda", USDA.encode())], ("maps", "positions_picture"), 101, False),
        "stage": ([("alpha.usda", root), ("layers/light.usda", USDA.encode())], ("maps", "stage_picture"), 1000,
                  False),
        "positions": ([("lamps.json", {"place": "alpha", "lamps": [
            {"path": "/alpha/l1", "spot": [1, 3, 1]}, {"path": "/alpha/l2", "spot": [-1, 3, -2]}]})],
            ("maps", "positions_picture"), 101, False),
        "motion": ([("layers/motion.usda", MOTION.encode())], ("maps", "drawn_route"), 101, False),
        "checks": ([("checks.json", {"crate": {"surfaces": {"bare_steel": {
            "share": 0.9, "surface_lab": [60, 0, 0], "baked_lab": [40, 20, 10], "delta_e": 30.0}}}})],
            ("checks", "picture"), 101, False),
        "model by its hash": ([("takes.json", {"crate": {"take": "crate-s1", "crate-final.glb": crate_sha}})],
                              ("meshes", "picture"), 101, False),
        "model by another hash": ([("takes.json", {"crate": {"crate-final.glb": "0" * 64}})],
                                  ("sheets", "tiles"), 101, False),
        "point cloud": ([("takes.json", {"dust": {"dust-final.glb": dust_sha}})], ("meshes", "picture"), 101, False),
        "colours as no array": ([("takes.json", {"crate": {"crate-final.glb": crate_sha}})], ("meshes", "picture"),
                                101, True),
        "crops": ([("props.json", {"rows": [{"id": "ship", "concept": concept(folder / "concept"),
                                             "box": [4, 4, 40, 30]}]})], ("crops", "picture"), 101, False),
        "tiles": ([("rows.json", {"rows": [{"id": "ship"}, {"id": "engine"}]})], ("sheets", "tiles"), 101, False),
    }
    made = []
    for number, (row, (entries, drawer, width, no_array)) in enumerate(rows.items()):
        here = folder / f"row{number}"
        files = [wav(here, entry) if isinstance(entry, str) else written(here, *entry) for entry in entries]
        made.append((row, files, drawer, width, no_array))
    return made


def spy_drawers(monkeypatch, drawers):
    """Each drawer wrapped to note itself in the returned list when it drew (a route is drawn onto axes and returns
    nothing)."""
    drew = []

    def spied(real, drawer):
        def drawing(*args, **kwargs):
            answer = real(*args, **kwargs)
            if answer is not None or drawer[1] == "drawn_route":
                drew.append(drawer)
            return answer
        return drawing
    for drawer in drawers:
        module = getattr(previews, drawer[0])
        monkeypatch.setattr(module, drawer[1], spied(getattr(module, drawer[1]), drawer))
    return drew


def colours_of(path):
    with Image.open(path) as drawn:
        return drawn.width, drawn.convert("RGB").getcolors(1 << 20)


def test_every_step_card_has_a_picture(world, tmp_path, monkeypatch):
    """Every output row draws a real picture through the drawer its files call for, whatever its words; the plan
    and a whole stage large, a layer alone never as a stage; models only by their hash; a packaged sound never as the
    step's own. Kept pictures and kept failures are never drawn again. The film gives its middle still and the board
    tile shows it; gaps are found and said; a step shows its own picture."""
    drawn = tmp_path / "drawn"  # the fixture world keeps its own folders beside it
    work = drawn / "work"
    home = drawn / "home"
    rows = outputs(drawn / "outputs", work)
    drew = spy_drawers(monkeypatch, {drawer for _, _, drawer, _, _ in rows} | {("maps", "stage_picture")})
    for row, files, drawer, width, no_array in rows:
        drew.clear()
        with pytest.MonkeyPatch.context() as patched:
            if no_array:  # colours trimesh gives as no array for its points: drawn plain grey
                patched.setattr(trimesh.visual.color.ColorVisuals, "to_color",
                                lambda self: types.SimpleNamespace(vertex_colors=numpy.zeros(0)), raising=False)
            path = previews.picture(files, PLAN, KNOWN, home, f"output-{row}", "same words", (work,))
        assert path is not None, (row, previews.failure(home, f"output-{row}"))
        drawn_width, colours = colours_of(path)
        assert drawn_width >= width and colours and len(colours) > 2, (row, drawn_width)
        assert drawer in drew, (row, drew)
        assert (("maps", "stage_picture") in drew) == (row == "stage"), (row, drew)

    plan_files = rows[0][1]
    kept = previews.cached(home, "output-plan")
    with pytest.MonkeyPatch.context() as patched:  # the world below draws its own previews again
        patched.setattr(previews, "draw", lambda *args: pytest.fail("drawn again"))
        assert previews.picture(plan_files, PLAN, KNOWN, home, "output-plan", "plan") == kept
        assert previews.preview_id("output-1") != previews.preview_id("output-2")
        assert len(previews.preview_id("output-1")) == 64

        def broken(*args):  # one model that cannot be drawn costs only its own picture, kept with its error
            raise IndexError("too many indices for array")
        patched.setattr(previews, "draw", broken)
        assert previews.picture(plan_files, PLAN, KNOWN, home, "output-broken", "plan") is None
        assert previews.failure(home, "output-broken") == {"output": "output-broken",
                                                           "error": "IndexError: too many indices for array"}
        patched.setattr(previews, "draw", lambda *args: pytest.fail("a failed picture drawn again"))
        assert previews.picture(plan_files, PLAN, KNOWN, home, "output-broken", "plan") is None
        assert not list((home / "previews" / previews.VERSION).glob("*.partial.png"))

    figure, (axes,) = canvas.blank(side=canvas.LARGE_INCHES, dpi=canvas.LARGE_DPI)
    crowded = [(f"A LONG ITEM NAME NUMBER {number}", (number * 0.1, number * 0.1)) for number in range(12)]
    canvas.box(axes, [-1, -1, 10, 10], canvas.FAINT, 0.2)
    canvas.fit([axes])
    labels.place(axes, crowded)  # twelve items crowded into one corner: drawn labels sit clear, the rest numbered
    renderer = figure.canvas.get_renderer()
    boxes = [text.get_window_extent(renderer) for text in axes.texts if text.get_text()]  # not the leader lines
    assert len(boxes) == len(crowded)
    assert not any(first.overlaps(second)  # matplotlib's own box test, not the code's
                   for number, first in enumerate(boxes) for second in boxes[number + 1:])
    canvas.write(figure, drawn / "crowded.png")

    points = {"layers/settle.usda": (SETTLE, "/alpha/crate_1", (2.0, 0.5, -3.0)),
              "layers/light.usda": (USDA, "/alpha/lamp_1", (1.0, 2.0, 3.0))}
    for name, (text, prim, expected) in points.items():  # a layer opened alone places its overs by their own ops
        assert previews.maps.layer_points(*written(drawn / "layers", name, text.encode()))[prim] == expected, name

    made = film_file(drawn / "film")
    views = json.dumps({"size": [128, 72], "views": [dict(VIEW, frame=number) for number in range(24)]})
    assert films.probe(made) == (48, 24.0)
    assert films.middle_frame(48, json.loads(views)["views"]) == 36  # the title card leads the shot
    with Image.open(films.middle_still(made, views, drawn / "still.jpg")) as still:
        assert still.size == (128, 72)
    assert films.middle_still(drawn / "missing.mp4", views, drawn / "none.jpg") is None
    projected = {"in the middle": ((0.0, 1.0, 0.0), [640, 360, 5]), "behind the camera": ((0.0, 1.0, 9.0), None)}
    for row, (point, expected) in projected.items():
        found = films.projected(VIEW, point, (1280, 720))
        assert (found and [round(value) for value in found]) == expected, row
    number, shown = films.best_view([AWAY, VIEW], [("crate_1", (1.0, 1.0, 0.0))], (1280, 720))
    assert number == 1 and shown[0][0] == "crate_1"
    assert films.best_view([AWAY], [("crate_1", (1.0, 1.0, 0.0))], (1280, 720)) is None
    frame = drawn / "frame.png"
    Image.new("RGB", (128, 72), (90, 90, 90)).save(frame)
    _, colours = colours_of(films.ringed(frame, [("crate_1", 700.0, 360.0, 40.0)], (1280, 720), drawn / "ringed.jpg"))
    assert colours and len(colours) > 2
    assert previews.maps.ringed_plan(PLAN, [("hose_reel_1", 1, 2)], "ALPHA", drawn / "ringed.png").is_file()

    reels = {"/alpha/Objects/hose_reel_1": (1, 0, 2), "/alpha/Objects/hose_reel_2": (2, 0, 2),
             "/alpha/Objects/hose_reel_stand_1": (3, 0, 3)}
    gaps = {"hose_reel": [("hose_reel_1", (1, 0, 2)), ("hose_reel_2", (2, 0, 2))],
            "/alpha/Objects/hose_reel_2": [("hose_reel_2", (2, 0, 2))], "bram": []}
    for named, expected in gaps.items():
        assert accepted_gaps.matched(reels, named) == expected, named
    sentences = [
        ({"name": "tube: readout and conduit box not laid in a 3-bay tube", "check": "reach",
          "objects": ["small_readout", "conduit_box"]}, "tube",
         "Small readout and conduit box are missing from the tube: its layout rule never places them here."),
        ({"name": "hangar: the hose reel's old model tips", "check": "resting",
          "objects": ["/hangar/Objects/hose_reel_1"]}, "hangar",
         "Hose reel in the hangar does not rest steadily where it stands."),
        ({"name": "lab: something new", "check": "unheard"}, "lab", "Something new."),
    ]
    for entry, place, expected in sentences:
        assert plain.accepted_gap_sentence(entry, place) == expected, entry["check"]
    assert plain.stop_sentence("completion", "completion answered fail: accepted gaps: tube: ...", "tube", 3) == (
        "The final check stopped the tube because of the 3 known gaps below, which are not fixed yet.")
    things = [({"place": "alpha", "looks": {"bram": {"missing": "no body"}, "sefa": {}}}, ["bram: missing", "sefa"]),
              ({"place": "alpha", "moved": [], "seconds": 4.0}, ["place: alpha", "moved: 0", "seconds: 4.0"])]
    for document, expected in things:  # a record that lacks something says so
        assert previews.named_things(document) == expected, document
    paths = {"assets/light/earth.png": True, "places/airlock/assets/textures/a_base_color.png": True,
             "looks/hangar/shot0.png": False, "assets.png": False}
    for name, expected in paths.items():
        assert packaged(name) == expected, name
    assert labels.item_words("SOLAR MAST (dead), 12 m with its blanket") == "SOLAR MAST (dead)"

    source = world.source
    newer = {"assembly": {"assets/textures/a_base_color.png": fixture.picture((200, 30, 30)),  # listed first
                          "looks/shot0.png": fixture.picture()},
             "demo-film": {"film.mp4": made.read_bytes(), "views.json": views.encode(),
                           "concept.png": fixture.picture()}}
    monkeypatch.setattr(fixture, "files_of", lambda stage, place, tweak: newer[stage])
    fixture.made(world.store, drawn / "again", "assembly", "alpha", tweak=6, minutes_ago=1)
    film = fixture.made(world.store, drawn / "again", "demo-film", "alpha", tweak=5, minutes_ago=1)
    source.refresh()  # the source keeps what it read: both made before it is first asked
    detail = source.step_detail("alpha", "plan")
    pictures = [ref for ref in detail.files if ref.kind == "image"]
    assert [ref.name for ref in pictures] == [previews.PREVIEW_NAME] and SHA.match(pictures[0].sha)
    assert source.thumb_path(pictures[0].sha) is not None
    cards = [card for layer in source.layer_groups("alpha", with_thumbs=True) for card in layer.steps]
    assert all(card.thumb for card in cards if card.output), [card.stage for card in cards if not card.thumb]
    assert previews.PREVIEW_NAME not in [ref.name for ref in source.step_detail("alpha", "closeup").files]
    assert pathlib.Path(source.home / "previews").is_dir()
    beta = source.place_detail("beta")
    gap = beta.accepted_gaps[0]
    assert gap.step == "assembly" and gap.step_url == "/place/beta/step/assembly/"
    assert gap.picture is not None and gap.picture_is == "the scene in its film"  # it names nothing on the stage
    assert source.thumb_path(gap.picture.sha) is not None
    assert gap.sentence == "Something in the beta is still a stand-in block: no finished model yet."
    stopped = beta.faults[0]
    assert stopped.step_url == "/place/beta/step/assembly/" and stopped.picture is not None
    assert stopped.sentence == "The OpenUSD stage step stopped: its placeholders check failed."

    views_folder = source.props_home / "work/scene/alpha/views"
    views_folder.mkdir(parents=True)
    Image.new("RGB", (16, 16), (200, 10, 10)).save(views_folder / "C4.png")
    assert source.look_picture("TMP/playtest3/moonground2/station/C4.png", ["alpha"]).name == "C4.png"
    assert source.look_picture("TMP/gone/K99.png", ["alpha"]) is None
    assert source.concept("alpha") is None  # its plan names no concept, and no K01.png is there
    Image.new("RGB", (16, 16), (10, 200, 10)).save(views_folder / "K01.png")
    assert source.concept("alpha").name == "K01.png"
    assert source.step_detail("alpha", "assembly").picture.name == "looks/shot0.png"  # its own, not the texture
    assert source.step_detail("alpha", "closeup").picture.name == "closeups/lamp.png"
    assert source.accepted_output("demo-film@alpha") == film
    card = source.place_card("alpha")
    assert card.still is not None and card.still.name == "still.jpg"
    assert source.thumb_path(card.still.sha) is not None
    assert source.place_card("beta").still is None  # its film cannot be read: the tile keeps its picture
    monkeypatch.setattr(source, "place_plan", lambda place: {"concept": {
        "picture": "{seeds}/scene/alpha/views/C4.png"}})
    assert source.concept("alpha").name == "C4.png"  # the picture its plan was read from
