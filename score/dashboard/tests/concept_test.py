"""The concept review (pages/concepts.py): each card whose concept is not locked opens its page; the owner's Draw
click is his spend yes for one call at the price shown, applied here at once in local mode and by the store's
machine's listener when hosted (one held call, claimed once, its picture sent back and served before the next
export); Pick locks the concept (its card loses the button) and Unlock frees it; anyone but the owner is refused.
The model is a stand-in: no call is made, nothing is spent."""
import io
import json
import subprocess

import pytest
from django.test import override_settings
from PIL import Image

from score.dashboard.pages import concepts
from score.dashboard.pages.models import SyncRequest
from score.dashboard.sync import listen
from score.dashboard.tests.pages_test import signed_in
from score.dashboard.tests.sync_test import TOKEN, hosted_client, remote_of
from score.review import concepts as drawing
from score.review import web

pytestmark = pytest.mark.django_db(transaction=True)
PRICE = 0.15


def a_png(colour):
    buffer = io.BytesIO()
    Image.new("RGB", (96, 60), colour).save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def stand_in(world, monkeypatch):
    """The draw's own process run in-process with a stand-in model; [what each draw was asked]."""
    asked = []
    monkeypatch.setattr("score.adapters.compute.require_books", lambda what: None)  # the books' own test
    monkeypatch.setattr(drawing, "draw_euros", lambda per_unit=None: PRICE)
    monkeypatch.setattr(concepts, "in_background", concepts.applied_here)  # the thread's work, now

    def run(argv, env, **kwargs):
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        model = lambda wording, pictures: asked.append(wording) or a_png((30 * len(asked), 90, 140))  # noqa: E731
        record = drawing.draw(world.source.store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1], caller=model)
        return subprocess.CompletedProcess(argv, 0, json.dumps(record) + "\n", "")
    drawn_here = web.concept_draw
    monkeypatch.setattr(web, "concept_draw", lambda *args, **named: drawn_here(*args, run=run, **named))
    return asked


def test_each_card_not_locked_opens_its_concept_review(world, stand_in):
    html = signed_in().get("/").content.decode()
    assert 'href="/concept/alpha/"' in html
    page = signed_in("joey2").get("/concept/alpha/")
    assert page.status_code == 200 and signed_in("joey3").get("/concept/nowhere/").status_code == 404


def test_a_local_draw_is_drawn_at_the_price_shown_then_picked_and_unlocked(world, stand_in):
    owner = signed_in()
    page = owner.get("/concept/beta/").content.decode()  # beta's concept is lost
    assert "Draw concept" in page and "EUR 0.15" in page
    answer = owner.post("/concept/beta/draw/", json.dumps({"note": "dusty", "euros": PRICE}),
                        content_type="application/json")
    assert answer.status_code == 200, answer.content
    state = owner.get("/concept/beta/state/").json()
    assert state["pending"] is False and state["refused"] is None and state["newest"]
    yes = world.source.store.spend_yes("override", drawing.draws(world.source.store, "beta")[0]["yes"])
    assert yes["by"] == "joey" and yes["euros"] == PRICE and "beta" in yes["purpose"]
    assert "Redraw" in owner.get("/concept/beta/").content.decode()
    marks = [{"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "note": "a window"}]
    owner.post("/concept/beta/draw/", json.dumps({"marks": marks, "base": state["newest"], "euros": PRICE}),
               content_type="application/json")
    assert "Box 1: a window." in stand_in[-1]
    newest = owner.get("/concept/beta/state/").json()["newest"]
    assert owner.post("/concept/beta/pick/", json.dumps({"sha": newest}), content_type="application/json").json()
    assert 'href="/concept/beta/"' not in owner.get("/").content.decode()  # locked: no review button
    assert owner.post("/concept/beta/draw/", json.dumps({"euros": PRICE}),
                      content_type="application/json").status_code == 409
    owner.post("/concept/beta/pick/", json.dumps({"sha": None}), content_type="application/json")
    assert 'href="/concept/beta/"' in owner.get("/").content.decode()


def test_a_draw_at_another_price_or_by_anyone_else_is_refused(world, stand_in):
    owner = signed_in()
    owner.post("/concept/beta/draw/", json.dumps({"euros": 0.05}), content_type="application/json")
    assert "measured price" in owner.get("/concept/beta/state/").json()["refused"]
    assert drawing.draws(world.source.store, "beta") == []
    other = signed_in("mallory")
    assert other.post("/concept/beta/draw/", json.dumps({"euros": PRICE}),
                      content_type="application/json").status_code == 403
    assert other.post("/concept/beta/pick/", json.dumps({"sha": None}),
                      content_type="application/json").status_code == 403


def test_a_hosted_click_reaches_the_listener_in_one_held_call_and_its_picture_is_served(world, stand_in, settings):
    owner = signed_in()
    settings.SCORE_MODE = settings.HOSTED
    try:
        owner.post("/concept/beta/draw/", json.dumps({"euros": PRICE}), content_type="application/json")
        assert owner.get("/concept/beta/state/").json()["pending"] is True
    finally:
        settings.SCORE_MODE = settings.LOCAL
    with override_settings(SCORE_SYNC_TOKEN=TOKEN):
        web = hosted_client()
        remote = remote_of(web)
        assert web.post(f"/api/sync/requests/{SyncRequest.objects.get().pk}/claim",
                        headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200
        SyncRequest.objects.update(state="waiting")  # a second caller is refused only after the first claimed
        assert listen.round_once(remote, world.source) == [(SyncRequest.objects.get().pk, "done")]
        assert remote.waiting(listen.LISTENED, 0) == [] and not remote.claim(SyncRequest.objects.get().pk)
    item = SyncRequest.objects.get()
    record = json.loads(item.detail)
    assert sorted(path.name for path in (settings.SCORE_HOME / "request-files").iterdir()) == [
        f"{record['sha']}-1280.jpg", f"{record['sha']}-360.jpg"]
    drawn = concepts.answered_draws("beta")
    assert [draw.picture.sha for draw in drawn] == [record["sha"]] and drawn[0].picture.thumb_url


def test_an_approved_designs_concept_cannot_be_unlocked(world, stand_in, monkeypatch):
    monkeypatch.setattr(concepts, "approved", lambda source, place: True)
    answer = signed_in().post("/concept/beta/pick/", json.dumps({"sha": None}), content_type="application/json")
    assert answer.status_code == 409 and "approved" in answer.json()["detail"]


def test_the_listener_says_an_unreachable_hosted_side_and_asks_again(world):
    import urllib.error

    class Down:
        def waiting(self, kinds, wait):
            raise urllib.error.URLError("refused")
    said, paused = [], []
    listen.listen(Down(), world.source, rounds=2, log=said.append, pause=paused.append)
    assert len(said) == 2 and "did not answer" in said[0] and paused == [listen.RETRY_SECONDS] * 2
