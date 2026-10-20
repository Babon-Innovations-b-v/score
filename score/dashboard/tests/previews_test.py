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
from score.dashboard.previews import films

pytestmark = pytest.mark.django_db
KNOWN = {"bare_steel": ((140, 145, 150), 0.5, 0.8), "rubber": ((30, 30, 30), 0.9, 0.0)}
PLAN = {"place": "alpha", "title": "ALPHA", "walls": {"wide": 8}, "floor": [[-4, -6], [4, 6]],
        "items": [{"name": "BENCH", "box": [-3, -5, -1, -3]}, {"name": "RACK", "box": [1, 2, 3, 5]}],
        "doors": [{"name": "S", "middle": [0, 0, 6]}], "standing": [{"at": [0, 0]}, [1, 1], [2, 0, 2]]}  # both shapes


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


MOTION = """#usda 1.0
over "alpha" {
    over "door_leaf" {
        double3 xformOp:translate.timeSamples = {0: (-1, 2, 0), 24: (-3, 2, 0)}
    }
}
"""


def glb(folder):
    """A coloured box saved as a .glb in a work folder one level down, and its hash."""
    import hashlib
    import trimesh
    mesh = trimesh.creation.box(extents=(1, 2, 1))
    mesh.visual.vertex_colors = (200, 80, 40, 255)
    path = folder / "work" / "takes" / "crate-final.glb"
    path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def concept(folder):
    path = folder / "concept.png"
    Image.new("RGB", (64, 48), (90, 120, 160)).save(path)
    return str(path)


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
        "motion": [written(folder, "layers/motion.usda", MOTION.encode())],
        "checks": [written(folder, "checks.json", {"crate": {"surfaces": {"bare_steel": {
            "share": 0.9, "surface_lab": [60, 0, 0], "baked_lab": [40, 20, 10], "delta_e": 30.0}}}})],
        "meshes": [written(folder, "takes.json", {"crate": {"take": "crate-s1", "crate-final.glb": glb(folder)}})],
        "crops": [written(folder, "props.json", {"rows": [{"id": "ship", "concept": concept(folder),
                                                          "box": [4, 4, 40, 30]}]})],
        "tiles": [written(folder, "rows.json", {"rows": [{"id": "ship"}, {"id": "engine"}]})],
    }


def test_each_kind_draws_a_real_picture(tmp_path):
    for kind, files in kinds(tmp_path).items():
        path = previews.picture(files, PLAN, KNOWN, tmp_path / "home", f"output-{kind}", kind, (tmp_path / "work",))
        with Image.open(path) as drawn:
            colours = drawn.convert("RGB").getcolors(1 << 20)
        assert drawn.width > 100 and colours and len(colours) > 2, kind


def test_the_drawer_follows_the_files_not_the_stage(tmp_path, monkeypatch):
    chosen = []
    for module, function in ((previews.maps, "plan_picture"), (previews.maps, "settle_picture"),
                             (previews.swatches, "picture"), (previews.paint, "picture"),
                             (previews.sheets, "waveforms"), (previews.maps, "positions_picture"),
                             (previews.maps, "drawn_route"), (previews.checks, "picture"),
                             (previews.meshes, "picture"), (previews.crops, "picture"), (previews.sheets, "tiles")):
        real = getattr(module, function)
        monkeypatch.setattr(module, function, lambda *args, real=real, name=function, **kwargs: (
            chosen.append(name), real(*args, **kwargs))[1])
    for kind, files in kinds(tmp_path).items():
        chosen.clear()
        previews.draw(files, PLAN, KNOWN, tmp_path / f"{kind}.png", "same words", (tmp_path / "work",))
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


def test_each_kind_gets_its_own_drawer(tmp_path):
    """The routes of what a layer moves, a surface check's colour pairs, the models named by hash, the pictures
    records point at: each output reaches its own drawer, not a tile sheet."""
    expected = {"motion": "drawn_route", "checks": "checks", "meshes": "meshes", "crops": "crops"}
    found = kinds(tmp_path)
    for kind, drawer in expected.items():
        chosen = []
        module = previews.maps if drawer == "drawn_route" else getattr(previews, drawer)
        function = "drawn_route" if drawer == "drawn_route" else "picture"
        real = getattr(module, function)
        setattr(module, function, lambda *args, real=real: (chosen.append(kind), real(*args))[1])
        try:
            previews.draw(found[kind], PLAN, KNOWN, tmp_path / f"own-{kind}.png", kind, (tmp_path / "work",))
        finally:
            setattr(module, function, real)
        assert chosen, kind


def test_a_model_is_drawn_only_when_its_hash_matches(tmp_path):
    sha = glb(tmp_path)
    assert previews.meshes.picture({"crate": {"crate-final.glb": sha}}, (tmp_path / "work",), tmp_path / "a.png")
    assert previews.meshes.picture({"crate": {"crate-final.glb": "0" * 64}}, (tmp_path / "work",),
                                   tmp_path / "b.png") is None


def test_a_packaged_file_is_not_the_steps_own(tmp_path):
    from score.dashboard.state.files import packaged
    assert packaged("assets/light/earth.png") and packaged("places/airlock/assets/textures/a_base_color.png")
    assert not packaged("looks/hangar/shot0.png") and not packaged("assets.png")
    sound = wav(tmp_path)
    assert previews.sheets.waveforms(previews.own_files([("assets/sound/" + sound[0], sound[1])]),
                                     tmp_path / "c.png") is None


def test_a_record_that_lacks_something_says_so():
    assert previews.named_things({"place": "alpha", "looks": {"bram": {"missing": "no body"}, "sefa": {}}}) == [
        "bram: missing", "sefa"]
    assert previews.named_things({"place": "alpha", "moved": [], "seconds": 4.0}) == [
        "place: alpha", "moved: 0", "seconds: 4.0"]


def test_plan_labels_never_cover_each_other(tmp_path):
    """Twelve items crowded into one corner: every label that is drawn sits clear of every other, the rest are
    numbered in the key."""
    from score.dashboard.previews import canvas, labels
    figure, (axes,) = canvas.blank(side=canvas.LARGE_INCHES, dpi=canvas.LARGE_DPI)
    crowded = [(f"A LONG ITEM NAME NUMBER {number}", (number * 0.1, number * 0.1)) for number in range(12)]
    canvas.box(axes, [-1, -1, 10, 10], canvas.FAINT, 0.2)
    canvas.fit([axes])
    labels.place(axes, crowded)
    renderer = figure.canvas.get_renderer()
    boxes = [text.get_window_extent(renderer) for text in axes.texts if text.get_text()]  # not the leader lines
    assert len(boxes) == len(crowded)
    assert not any(labels.overlaps(first, second)
               for number, first in enumerate(boxes) for second in boxes[number + 1:])
    assert labels.item_words("SOLAR MAST (dead), 12 m with its blanket") == "SOLAR MAST (dead)"
    canvas.write(figure, tmp_path / "crowded.png")


def test_a_plan_is_drawn_large(tmp_path):
    path = previews.maps.plan_picture(PLAN, tmp_path / "plan.png")
    with Image.open(path) as drawn:
        assert drawn.width >= 1000


def test_a_whole_stage_is_drawn_over_its_labelled_plan(tmp_path, monkeypatch):
    root = written(tmp_path, "alpha.usda", b'#usda 1.0\n(\n    subLayers = [@./layers/light.usda@]\n)\n')
    chosen = []
    real = previews.maps.stage_picture
    monkeypatch.setattr(previews.maps, "stage_picture", lambda *args: (chosen.append(True), real(*args))[1])
    previews.draw([root, *kinds(tmp_path)["layer"]], PLAN, KNOWN, tmp_path / "stage.png", "OpenUSD stage")
    assert chosen
    chosen.clear()
    previews.draw(kinds(tmp_path)["layer"], PLAN, KNOWN, tmp_path / "layer.png", "light")
    assert not chosen  # a layer alone is not a stage


def test_a_layer_opened_alone_places_its_overs_by_their_own_ops(tmp_path):
    settle = """#usda 1.0
over "alpha" {
    over "crate_1" {
        matrix4d xformOp:transform = ( (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (2, 0.5, -3, 1) )
        uniform token[] xformOpOrder = ["xformOp:transform"]
    }
}
"""
    name, path = written(tmp_path, "layers/settle.usda", settle.encode())
    assert previews.maps.layer_points(name, path)["/alpha/crate_1"] == (2.0, 0.5, -3.0)
    name, path = written(tmp_path, "layers/light.usda", USDA.encode())
    assert previews.maps.layer_points(name, path)["/alpha/lamp_1"] == (1.0, 2.0, 3.0)


def film_file(folder, seconds=2):
    """A real two-second 24 fps film, 128 x 72."""
    import subprocess
    path = folder / "film.mp4"
    subprocess.run([films.tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc=size=128x72:rate=24:duration={seconds}", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


VIEW = {"eye": [0.0, 1.0, 5.0], "aim": [0.0, 1.0, 0.0], "up": [0.0, 1.0, 0.0], "fov": 90.0}


def test_a_film_gives_its_middle_still_once(tmp_path):
    made = film_file(tmp_path)
    views = json.dumps({"size": [128, 72], "views": [dict(VIEW, frame=number) for number in range(24)]})
    assert films.probe(made) == (48, 24.0)
    assert films.middle_frame(48, json.loads(views)["views"]) == 36  # the title card leads the shot
    still = films.middle_still(made, views, tmp_path / "still.jpg")
    with Image.open(still) as picture:
        assert picture.size == (128, 72)
    assert films.middle_still(tmp_path / "missing.mp4", views, tmp_path / "none.jpg") is None


def test_a_named_thing_is_found_in_the_frame_that_shows_it(tmp_path):
    middle = films.projected(VIEW, (0.0, 1.0, 0.0), (1280, 720))
    assert [round(value) for value in middle] == [640, 360, 5]
    assert films.projected(VIEW, (0.0, 1.0, 9.0), (1280, 720)) is None  # behind the camera
    away = dict(VIEW, aim=[10.0, 1.0, 5.0])
    number, shown = films.best_view([away, VIEW], [("crate_1", (1.0, 1.0, 0.0))], (1280, 720))
    assert number == 1 and shown[0][0] == "crate_1"
    assert films.best_view([away], [("crate_1", (1.0, 1.0, 0.0))], (1280, 720)) is None
    frame = tmp_path / "frame.png"
    Image.new("RGB", (128, 72), (90, 90, 90)).save(frame)
    path = films.ringed(frame, [("crate_1", 700.0, 360.0, 40.0)], (1280, 720), tmp_path / "ringed.jpg")
    with Image.open(path) as picture:
        assert picture.convert("RGB").getcolors(1 << 16) and len(picture.convert("RGB").getcolors(1 << 16)) > 2


def test_a_gap_names_its_things_by_path_or_by_name(tmp_path):
    from score.dashboard.state import accepted_gaps
    points = {"/alpha/Objects/hose_reel_1": (1, 0, 2), "/alpha/Objects/hose_reel_2": (2, 0, 2),
              "/alpha/Objects/hose_reel_stand_1": (3, 0, 3)}
    assert [name for name, _ in accepted_gaps.matched(points, "hose_reel")] == ["hose_reel_1", "hose_reel_2"]
    assert accepted_gaps.matched(points, "/alpha/Objects/hose_reel_2") == [("hose_reel_2", (2, 0, 2))]
    assert accepted_gaps.matched(points, "bram") == []
    path = previews.maps.ringed_plan(PLAN, [("hose_reel_1", 1, 2)], "ALPHA", tmp_path / "ringed.png")
    assert path.is_file()


def test_an_accepted_gap_has_its_step_and_a_picture(world):
    beta = world.source.place_detail("beta")
    gap = beta.accepted_gaps[0]
    assert gap.step == "assembly" and gap.step_url == "/place/beta/step/assembly/"
    assert gap.picture is not None and gap.picture_is == "the place in its film"  # it names nothing on the stage
    assert world.source.thumb_path(gap.picture.sha) is not None
    assert gap.sentence == "Something in the beta is still a stand-in block: no finished model yet."
    stopped = beta.faults[0]
    assert stopped.step_url == "/place/beta/step/assembly/" and stopped.picture is not None
    assert stopped.sentence == "The OpenUSD stage step stopped: its placeholders check failed."


def test_a_problem_is_said_in_plain_words():
    from score.dashboard.state import plain
    entry = {"name": "tube: readout and conduit box not laid in a 3-bay tube", "check": "reach",
             "objects": ["small_readout", "conduit_box"]}
    assert plain.accepted_gap_sentence(entry, "tube") == (
        "Small readout and conduit box are missing from the tube: its layout rule never places them here.")
    entry = {"name": "hangar: the hose reel's old model tips", "check": "resting",
             "objects": ["/hangar/Objects/hose_reel_1"]}
    assert plain.accepted_gap_sentence(entry, "hangar") == "Hose reel in the hangar does not rest steadily where it stands."
    assert plain.accepted_gap_sentence({"name": "lab: something new", "check": "unheard"}, "lab") == "Something new."
    assert plain.stop_sentence("completion", "completion answered fail: accepted gaps: tube: ...", "tube", 3) == (
        "The final check stopped the tube because of the 3 known gaps below, which are not fixed yet.")


def test_a_step_shows_its_own_picture_not_a_packaged_texture(world):
    from score.dashboard.state.files import packaged
    detail = world.source.step_detail("alpha", "assembly")
    assert detail.picture is not None and not packaged(detail.picture.name)
    assert world.source.step_detail("alpha", "closeup").picture.name == "closeups/lamp.png"


def test_concepts_and_look_pictures_are_found_where_they_live(world, monkeypatch):
    views = world.source.props_home / "work/scene/alpha/views"
    views.mkdir(parents=True)
    Image.new("RGB", (16, 16), (200, 10, 10)).save(views / "C4.png")
    assert world.source.look_picture("TMP/playtest3/moonground2/station/C4.png", ["alpha"]).name == "C4.png"
    assert world.source.look_picture("TMP/gone/K99.png", ["alpha"]) is None
    assert world.source.concept("alpha") is None  # its plan names no concept, and no K01.png is there
    Image.new("RGB", (16, 16), (10, 200, 10)).save(views / "K01.png")
    world.source.refresh()
    assert world.source.concept("alpha").name == "K01.png"
    monkeypatch.setattr(world.source, "place_plan", lambda place: {"concept": {
        "picture": "{seeds}/scene/alpha/views/C4.png"}})
    assert world.source.concept("alpha").name == "C4.png"  # the picture its plan was read from


def test_the_board_tile_gets_the_films_middle_still(world, tmp_path, monkeypatch):
    from score.dashboard.tests import fixture
    made = film_file(tmp_path)
    views = json.dumps({"size": [128, 72], "views": [dict(VIEW, frame=number) for number in range(24)]}).encode()
    monkeypatch.setattr(fixture, "files_of", lambda stage, place, tweak: {
        "film.mp4": made.read_bytes(), "views.json": views, "concept.png": fixture.picture()})
    output = fixture.made(world.store, tmp_path / "again", "demo-film", "alpha", tweak=5, minutes_ago=1)
    world.source.refresh()
    assert world.source.accepted_output("demo-film@alpha") == output
    card = world.source.place_card("alpha")
    assert card.still is not None and card.still.name == "still.jpg"
    assert world.source.thumb_path(card.still.sha) is not None
    assert world.source.place_card("beta").still is None  # its film cannot be read: the tile keeps its picture
