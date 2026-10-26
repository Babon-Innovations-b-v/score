"""The environment concept page (pages/environment.py): environment 1's shows today's data locked; Unlock asks to be
sure and puts the draws out of date; the owner's Save, Send (his spend yes for one model call at the price shown), Take
and Add each reach the store's machine, here at once in local mode and through the listener when hosted; anyone but
the owner is refused. The model and the bucket are stand-ins: no call is made, nothing is spent."""
import base64
import io
import json
import subprocess

import pytest
from django.test import override_settings
from PIL import Image

from score.dashboard.pages import concepts, environment, setting_picture
from score.dashboard.pages.models import SyncRequest
from score.dashboard.sync import listen
from score.dashboard.tests.pages_test import signed_in
from score.dashboard.tests.fixture import TOKEN, hosted_client, remote_of
from score.review import concepts as drawing
from score.review import environment_concept, web
from score.store import runtime_store

pytestmark = pytest.mark.django_db(transaction=True)
PRICE = 0.05
PAGE = "/environments/world1/"


def a_png(colour=(40, 90, 160)):
    buffer = io.BytesIO()
    Image.new("RGB", (96, 60), colour).save(buffer, "PNG")
    return buffer.getvalue()


def posted(client, path, body):
    return client.post(f"{PAGE}{path}/", json.dumps(body), content_type="application/json")


@pytest.fixture
def stand_in(world, monkeypatch):
    """The ask's own process run in-process with a stand-in model, the bucket a folder; [each question asked]."""
    asked = []
    monkeypatch.setattr("score.adapters.compute.require_books", lambda what: None)
    monkeypatch.setattr(environment_concept, "ask_euros", lambda *given: PRICE)
    monkeypatch.setattr(concepts, "in_background", concepts.applied_here)
    bucket = world.source.store.cache.parent / "bucket"
    monkeypatch.setattr(drawing, "offsite_store", lambda: runtime_store.FolderStore(bucket))
    monkeypatch.setattr(environment_concept, "running_under_agent", lambda: False)
    monkeypatch.setattr(environment_concept, "PROPS_HOME", world.source.store.cache.parent / "home")
    monkeypatch.setattr(drawing, "PROPS_HOME", world.source.store.cache.parent / "home")

    def run(argv, env, **kwargs):
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        model = lambda question, pictures: asked.append(question) or '{"style": "Bright frontier"}'  # noqa: E731
        record = environment_concept.ask(world.source.store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1],
                                         reviser=model)
        return subprocess.CompletedProcess(argv, 0, json.dumps(record) + "\n", "")
    asked_here = web.environment_ask
    monkeypatch.setattr(web, "environment_ask", lambda *args, **named: asked_here(*args, run=run, **named))
    return asked


def test_environment_1s_concept_is_todays_data_shown_locked(world):
    html = signed_in().get(PAGE).content.decode()
    assert ">locked</b>" in html and "2099 space base" in html and "Unlock" in html
    assert "orbits Earth every 27 days, one face to Earth; gravity 1.6 m/s²" in html  # a plain line a thing
    assert "orbits Sun every 687 days, a day of 25 h; gravity 3.7 m/s²" in html and ">backdrop<" in html
    assert "radius_km 1737.4" in html and "gravity 1.624" in html  # the raw numbers as hover text only
    assert "Moon&#x27;s orbit ×" in html and "sizes enlarged to read" in html  # what is drawn bigger, said
    assert "Question 1 of" not in html and "data-f=" not in html  # owner 2026-10-21: fields only while unlocked
    assert [(name, question) for name, _, question in environment.QUESTIONS] == list(environment_concept.QUESTIONS)
    assert [environment.steps_around(name)["number"] for name, _, _ in environment.QUESTIONS] == [1, 2, 3, 4, 5]
    assert signed_in("ann").get("/environments/world9/").status_code == 404


def test_a_house_setting_is_its_plot_from_above_with_its_suns_path_and_no_bodies():
    from score.review import overhead, setting
    from score.review.setting_test import HOUSE
    house = setting.checked(HOUSE)
    found = setting_picture.view_of(house, {"house": "2024-03-20T12:00:00Z"}, {"house": "House"})
    assert len(found["pictures"]) == 1 and "sp-path" in found["pictures"][0]["svg"]  # no system, one plot
    svg = found["pictures"][0]["svg"]
    assert "scene time 2024-03-20T12:00:00Z" in svg and ">House</text>" in svg
    assert 'class="sp-body"' not in svg  # no body: the sun is a light on its path
    assert [(card["name"], card["kind"]) for card in found["cards"]] == [
        ("Sun", "light"), ("Sky", "backdrop"), ("Meadow", "ground")]
    assert found["cards"][0]["line"] == "a far light crossing the sky every 24 h; 100,000 lux"
    assert found["cards"][2]["sites"] == ["House"]
    light = house["lights"][0]
    for when in ("2024-03-20T12:00:00Z", "2024-05-02T07:30:00Z", "2024-12-21T15:00:00Z"):  # the page's sum: overhead's
        seen = overhead.far_light(light, when)
        since = overhead.day_of(when) - overhead.day_of(light["equinox"])
        assert setting_picture.far_way(light, since) == pytest.approx((seen["azimuth"], seen["altitude"]), abs=0.01)


def test_unlock_asks_to_be_sure_then_puts_every_draw_out_of_date(world, stand_in):
    owner = signed_in()
    assert posted(owner, "save", {"locked": False}).status_code == 409  # not sure: refused
    assert posted(owner, "save", {"sure": True, "locked": False}).status_code == 200
    store = world.source.store
    assert environment_concept.unlocked(store) and environment_concept.version(store) is not None
    assert drawing.waits(store, "alpha") == "waits for the environment concept to be locked"
    html = owner.get(PAGE).content.decode()
    assert ">unlocked</b>" in html and "Send, EUR 0.05" in html and ">Lock</button>" in html
    assert "Question 1 of 5" in html and 'data-f="around"' in html  # unlocked: the interview and the fields
    assert 'data-row="sites"' in html and 'data-f="latitude"' in html


def test_save_lock_send_and_take_reach_the_store(world, stand_in):
    owner = signed_in()
    posted(owner, "save", {"sure": True, "locked": False})
    concept = environment_concept.newest(world.source.store, "world1")["concept"]
    assert posted(owner, "save", {"concept": {**concept, "style": "Cold steel"}, "locked": False}).status_code == 200
    assert environment_concept.newest(world.source.store, "world1")["concept"]["style"] == "Cold steel"
    answer = posted(owner, "ask", {"topic": "style", "answer": "brighter", "euros": PRICE})
    assert answer.status_code == 200 and "brighter" in stand_in[0] and "Cold steel" in stand_in[0]
    item = SyncRequest.objects.get(kind="environment-ask")
    assert item.state == "done" and json.loads(item.detail)["proposed"] == {"style": "Bright frontier"}
    html = owner.get(f"{PAGE}?q=style").content.decode()
    assert "Bright frontier" in html and ">Take</button>" in html
    assert posted(owner, "take", {"ask": item.pk}).status_code == 200
    assert environment_concept.newest(world.source.store, "world1")["concept"]["style"] == "Bright frontier"
    assert posted(owner, "save", {"concept": concept, "locked": True}).status_code == 200
    assert environment_concept.in_force(world.source.store)["style"] == concept["style"]
    assert posted(owner, "ask", {"topic": "style", "answer": "x", "euros": PRICE}).status_code == 409  # locked


def test_a_send_at_another_price_or_by_anyone_else_is_refused(world, stand_in):
    owner = signed_in()
    posted(owner, "save", {"sure": True, "locked": False})
    posted(owner, "ask", {"topic": "style", "answer": "brighter", "euros": 0.04})
    item = SyncRequest.objects.get(kind="environment-ask")
    assert item.state == "refused" and "measured price" in item.detail and stand_in == []
    assert posted(signed_in("mallory"), "save", {"sure": True, "locked": False}).status_code == 403
    assert posted(signed_in("eve"), "ask", {"topic": "style", "answer": "x", "euros": PRICE}).status_code == 403


def test_a_new_reference_goes_to_the_bucket_and_shows_on_the_page(world, stand_in):
    owner = signed_in()
    posted(owner, "save", {"sure": True, "locked": False})
    data = base64.b64encode(a_png()).decode()
    answer = posted(owner, "reference", {"name": "dock.png", "data": data, "shows": "the dock's look", "place": "beta"})
    assert answer.status_code == 200, answer.content
    bucket = runtime_store.FolderStore(world.source.store.cache.parent / "bucket")
    assert "dock.png" in json.loads(bucket.read_bytes("references/index.json"))
    world.source.refresh()
    html = owner.get(PAGE).content.decode()
    assert SyncRequest.objects.get(kind="environment-reference").payload["data"] == ""  # read once: bytes dropped
    assert 'data-picture="{home}/references/dock.png"' in html and "the dock&#x27;s look" in html
    assert drawing.references_of(world.source.store, "beta") == []  # unlocked: the draws read nothing new yet


def test_a_hosted_send_reaches_the_listener_and_shows_his_version_before_the_next_export(world, stand_in, settings):
    owner = signed_in()
    settings.SCORE_MODE = settings.HOSTED
    try:
        assert posted(owner, "save", {"sure": True, "locked": False}).status_code == 200
        assert ">unlocked</b>" in owner.get(PAGE).content.decode()  # his version, before the export holds it
        assert posted(owner, "ask", {"topic": "style", "answer": "x", "euros": PRICE}).status_code == 409  # waiting
    finally:
        settings.SCORE_MODE = settings.LOCAL
    with override_settings(SCORE_SYNC_TOKEN=TOKEN):
        remote = remote_of(hosted_client())
        assert listen.round_once(remote, world.source) == [(SyncRequest.objects.get().pk, "done")]
    assert environment_concept.unlocked(world.source.store)


def test_an_export_made_before_the_environment_concept_shows_an_empty_page_and_takes_no_click(world, monkeypatch):
    monkeypatch.setattr(environment, "shown", lambda world_state: {})
    owner = signed_in()
    html = owner.get(PAGE).content.decode()
    assert "Unlock" not in html and ">locked</b>" in html
    assert posted(owner, "save", {"sure": True, "locked": False}).status_code == 409
    assert SyncRequest.objects.count() == 0
