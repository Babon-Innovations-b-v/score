"""The place page's breakdown: the paper's order, each step large beside what it read, a "show in 3D" per layer
that opens the viewer with only that layer and the base, problems beside their step, and the before and after
pairs read from the steps' files."""
import json
import re

import pytest

from score.dashboard.state import sliders
from score.dashboard.state.models import FileRef, PlaceDetail, StepDetail
from score.dashboard.tests.pages_test import signed_in

pytestmark = pytest.mark.django_db
ORDER = ["reference", "plan", "pieces", "ground", "base", "settle", "light", "motion", "effects", "sound",
         "characters", "machines", "crops", "result"]


def a_web_copy(world, place="alpha"):
    folder = world.root / "web" / place
    folder.mkdir(parents=True)
    (folder / f"{place}.json").write_text(json.dumps({
        "place": place, "from_output": world.outputs[f"assembly@{place}"], "made_at": "2026-10-18T12:00:00Z",
        "objects": [{"name": "Lamp", "layer": "light", "low": [0, 0, 0], "high": [1, 1, 1]}], "bytes": 10,
        "light_bytes": 5, "triangles": 12}))


def given_of(html):
    return json.loads(re.search(r'<script id="view3d-data" type="application/json">(.*?)</script>', html,
                                re.S).group(1))


def test_the_breakdown_runs_in_the_papers_order(world):
    html = signed_in().get("/place/alpha/").content.decode()
    found = [key for key in re.findall(r'<(?:article|div) class="bd-(?:section|absent)" id="bd-([a-z]+)"', html)]
    assert found == ORDER
    assert "made from" in html and 'data-fallback="/thumbs/' in html  # large, its thumbnail if the file is not there


def test_a_layer_shows_in_3d_alone_with_the_base_at_the_films_camera(world):
    a_web_copy(world)
    client = signed_in()
    html = client.get("/place/alpha/").content.decode()
    assert 'href="/view/alpha?only=light&amp;at=film"' in html and "Show in 3D: only light" in html
    shown = client.get("/view/alpha?only=light&at=film").content.decode()
    assert given_of(shown)["only"] == ["light", "base"] and "Showing only <b>light</b>" in shown
    assert given_of(client.get("/view/alpha?only=nothing").content.decode())["only"] is None
    assert given_of(client.get("/view/alpha").content.decode())["at"] is None


def test_a_problem_sits_beside_its_step(world):
    html = signed_in().get("/place/beta/").content.decode()
    before, result = html.split('id="bd-result"', 1)
    assert 'class="problem" href="/place/beta/step/assembly/"' in result.split("</article>")[0]
    assert 'class="problem"' not in before.split('class="breakdown"')[-1]


def ref(name, sha="a" * 64):
    return FileRef(name=name, kind="image", sha=sha, url=f"/files/{sha}", thumb_url=f"/thumbs/{sha}.jpg")


def test_the_pairs_wipe_only_where_the_camera_is_the_same():
    steps = {"light-passes": StepDetail(node="n", stage="light-passes", label="l",
                                        files=[ref("passes/p-0/shot0-000-look.png", "b" * 64)]),
             "light": StepDetail(node="n", stage="light", label="l", files=[ref("looks/p/shot0-000-look.png")]),
             "closeup": StepDetail(node="n", stage="closeup", label="c", files=[ref("closeups/lamp.png", "c" * 64)]),
             "likeness": StepDetail(node="n", stage="likeness", label="k", files=[ref("cut/lamp.png", "d" * 64)])}
    found = sliders.pairs(PlaceDetail(place="p", status=""), steps.get)
    assert [(pair["section"], pair["wipe"]) for pair in found] == [("pieces", False), ("light", True)]
    assert found[1]["before"].name.startswith("passes/") and found[1]["after"].name.startswith("looks/")
