"""The bodies' faces (body_faces.py): one row a body of the setting that does not shine, its face made from one
(faked) ask in the method's recipes and its own palette, face.json beside the loader's library, and the gate naming a
face off its palette or the method."""
import json
import pathlib

from score.review import setting as settings
from score.stages.surfaces import body_faces

METHOD = pathlib.Path(__file__).resolve().parents[3] / "data/library/materials.json"
ANSWER = {"palette": [{"token": "regolith-grey", "colour": "#8a8580"}, {"token": "crater-dark", "colour": "#3b3a38"}],
          "face": {"family": "Regolith", "recipe": "regolith", "token": "regolith-grey", "roughness": 0.95,
                   "metal": 0.0, "colours": [{"setting": "second", "token": "crater-dark"}]}}
GROUND = ["regolith", "Moon: airless, its dust ground by impacts"]


def test_every_body_that_does_not_shine_has_a_paid_row_of_its_own(monkeypatch):
    monkeypatch.setattr(body_faces.environment_concept, "in_force", lambda store: None)
    rows = body_faces.rows(None)
    assert [row.name for row in rows] == ["body-face-earth", "body-face-moon", "body-face-mars"]  # not the Sun
    assert all(row.paid and row.grain == "world" and row.euros == body_faces.FACE_EUROS for row in rows)
    moon = body_faces.body_param("moon")(type("Runner", (), {"store": None}))
    assert moon["radius_km"] == settings.reference()["bodies"]["moon"]["radius_km"]  # the cited table's value
    assert "radius 1,737 km" in body_faces.facts_of(moon)
    runner = type("Runner", (), {"store": None})
    grounds = {key: body_faces.ground_param(key)(runner)[0] for key in ("earth", "moon", "mars")}
    assert grounds == {"earth": "ocean", "moon": "regolith", "mars": "sand"}  # by their physics, no name read


def test_the_face_is_made_from_one_ask_in_the_methods_recipes(tmp_path, monkeypatch):
    asked = []
    monkeypatch.setattr(body_faces.route_ask, "asked", lambda bodies, caller: asked.append((bodies, caller)) or
                        {key: json.dumps(ANSWER) for key in bodies})
    moon = {"body": "moon", "name": "Moon", "radius_km": 1737.4}
    body_faces.make_face({"library": str(METHOD)}, tmp_path, 0, {"body": moon, "style": "worn NASA-punk",
                                                                 "ground": GROUND})
    (bodies, caller), = asked
    assert caller == "body-face" and "worn NASA-punk" in json.dumps(bodies["moon"])
    schema = bodies["moon"]["generationConfig"]["responseSchema"]["properties"]["face"]["properties"]
    assert schema["recipe"]["enum"] == ["regolith"] and "airless" in json.dumps(bodies["moon"])
    face = json.loads((tmp_path / "face.json").read_text())
    assert face["surface"] == "moon_face" and face["family"] == "regolith" and face["hex"] == "#8a8580"
    assert abs(face["colour"][0] - 0.2541) < 1e-3  # #8a = 138: sRGB to linear
    library = json.loads((tmp_path / "materials.json").read_text())
    assert library["families"]["regolith"]["variants"]["moon_face"]["second"] == "crater-dark"
    assert face["recipe"] == "regolith" and face["recipe_by"] == GROUND[1]
    assert body_faces.face_findings("moon", library) == []
    assert body_faces.judge_face(tmp_path, {}, {}).answer == "pass"


def test_a_face_off_its_palette_or_the_method_fails_and_no_answer_is_named(tmp_path, monkeypatch):
    method = json.loads(METHOD.read_text())
    library = body_faces.library_of("mars", json.dumps(ANSWER), method)
    variant = library["families"]["regolith"]["variants"]["mars_face"]
    variant.update(token="rust", recipe="moon_dust", roughness=1.5)
    found = body_faces.face_findings("mars", library)
    assert any("recipe moon_dust" in fault for fault in found) and any("token rust" in fault for fault in found)
    assert any("moon_dust is no natural ground" in fault for fault in found)
    assert any("roughness 1.5" in fault for fault in found)
    monkeypatch.setattr(body_faces.route_ask, "asked",
                        lambda bodies, caller: {key: ValueError("no json") for key in bodies})
    body_faces.make_face({"library": str(METHOD)}, tmp_path, 0, {"body": {"body": "mars", "name": "Mars"}, "style": "",
                                                                 "ground": GROUND})
    assert not (tmp_path / "face.json").exists() and body_faces.judge_face(tmp_path, {}, {}).answer == "fail"


def test_a_body_whose_physics_the_setting_lacks_gets_no_face(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="no natural ground for its face: Vesta: no surface pressure"):
        body_faces.make_face({"library": str(METHOD)}, tmp_path, 0, {
            "body": {"body": "vesta", "name": "Vesta"}, "style": "",
            "ground": [None, "Vesta: no surface pressure in the setting"]})
