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
from django.utils.html import escape
from PIL import Image

from score.dashboard.pages import concepts
from score.dashboard.pages.models import SyncRequest
from score.dashboard.sync import listen
from score.dashboard.tests.pages_test import signed_in
from score.dashboard.tests.sync_test import TOKEN, hosted_client, remote_of
from score.review import concepts as drawing
from score.review import web
from score.store import runtime_store

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
    offsite = world.source.store.cache.parent / "bucket"  # the private bucket's stand-in
    monkeypatch.setattr(drawing, "offsite_store", lambda: runtime_store.FolderStore(offsite))
    monkeypatch.setattr(drawing, "handed_over", lambda store, place: "library: stand-in")

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


def test_a_places_page_names_the_places_listed_inside_it_that_its_draw_holds(world, stand_in):
    (world.data / "places").mkdir(exist_ok=True)
    (world.data / "places/within.json").write_text(json.dumps({
        "shells": {"yard": {"name": "Yard"}}, "within": {"alpha": {"within": "beta"}, "beta": {"within": "yard"}}}))
    owner = signed_in()
    page = owner.get("/concept/yard/").content.decode()
    assert "drawn to hold" in page and "data-v>Beta</b>" in page and "data-v>Alpha</b>" not in page  # direct only
    assert "data-v>Alpha</b>" in owner.get("/concept/beta/").content.decode()  # every place: what is listed in it
    assert "drawn to hold" not in owner.get("/concept/alpha/").content.decode()  # it holds nothing


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
    marks = [{"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "note": "a window"}]
    owner.post("/concept/beta/draw/", json.dumps({"marks": marks, "base": state["newest"], "euros": PRICE}),
               content_type="application/json")
    assert "Box 1: a window." in stand_in[-1]
    newest = owner.get("/concept/beta/state/").json()["newest"]
    assert owner.post("/concept/beta/pick/", json.dumps({"sha": newest}), content_type="application/json").json()
    assert 'ptile-review" href="/concept/beta/"' not in owner.get("/").content.decode()  # locked: no review button
    assert owner.post("/concept/beta/draw/", json.dumps({"euros": PRICE}),
                      content_type="application/json").status_code == 409
    owner.post("/concept/beta/pick/", json.dumps({"sha": None}), content_type="application/json")
    assert 'href="/concept/beta/"' in owner.get("/").content.decode()


def test_with_no_mark_and_no_note_the_one_button_draws_fresh_from_the_places_wording(world, stand_in):
    owner = signed_in()
    owner.post("/concept/beta/draw/", json.dumps({"euros": PRICE}), content_type="application/json")
    page = owner.get("/concept/beta/").content.decode()
    assert page.count('id="concept-draw"') == 1 and '<span data-slot="label" data-v>Draw fresh</span>' in page
    owner.post("/concept/beta/draw/", json.dumps({"marks": [], "note": "", "base": None, "euros": PRICE}),
               content_type="application/json")  # what the button posts with nothing asked of the shown draw
    first, fresh = drawing.draws(world.source.store, "beta")
    assert fresh["base"] is None and fresh["marks"] == [] and fresh["sha"] != first["sha"]
    assert stand_in[-1] == stand_in[0] and "Box" not in stand_in[-1]  # the place's own first-draw wording again
    assert fresh["yes"] != first["yes"] and fresh["euros"] == PRICE  # its own spend yes, one call
    assert world.source.store.cache.parent.joinpath("bucket", f"concept-draws/{fresh['sha']}.png").is_file()


def test_the_page_shows_the_wording_a_draw_sends_and_his_edit_is_sent_and_kept_until_back_to_generated(world,
                                                                                                    stand_in):
    owner = signed_in()
    generated = escape(drawing.generated(world.source.store, "beta"))
    page = owner.get("/concept/beta/").content.decode()
    assert 'id="concept-wording"' in page and generated in page and "back to generated" not in page
    owner.post("/concept/beta/draw/", json.dumps({"euros": PRICE}), content_type="application/json")
    page = owner.get("/concept/beta/").content.decode()
    assert "Redraw with notes sends" in page and "&lt;mark 1&#x27;s note&gt;" in page
    edited = "One concept painting of beta at dusk, its doors open."
    owner.post("/concept/beta/draw/", json.dumps({"marks": [], "note": "", "base": None, "euros": PRICE,
                                                  "wording": edited}), content_type="application/json")
    assert stand_in[-1] == edited and drawing.own_wording(world.source.store, "beta") == edited
    page = owner.get("/concept/beta/").content.decode()
    assert f">{edited}</textarea>" in page and "back to generated" in page and "(your wording)" in page
    assert signed_in("mallory").post("/concept/beta/generated/").status_code == 403
    assert owner.post("/concept/beta/generated/").json()["said"] == "back to the generated wording"
    page = owner.get("/concept/beta/").content.decode()
    assert f">{generated}</textarea>" in page and "back to generated" not in page


def test_a_hosted_edit_shows_as_his_wording_before_the_next_export(world, stand_in, settings):
    owner = signed_in()
    settings.SCORE_MODE = settings.HOSTED
    try:
        owner.post("/concept/beta/draw/", json.dumps({"euros": PRICE, "wording": "beta, my words"}),
                   content_type="application/json")
        page = owner.get("/concept/beta/").content.decode()
        assert ">beta, my words</textarea>" in page and "back to generated" in page
        owner.post("/concept/beta/generated/")
        assert ">beta, my words</textarea>" not in owner.get("/concept/beta/").content.decode()
    finally:
        settings.SCORE_MODE = settings.LOCAL


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

    class Old:  # a hosted side that answers at once, not holding the call
        def waiting(self, kinds, wait):
            return []
    paused.clear()
    listen.listen(Old(), world.source, rounds=3, log=said.append, pause=paused.append)
    assert paused == [listen.SHORTEST_ROUND] * 3


def test_draw_all_draws_every_undrawn_place_at_once_its_click_the_yes_for_that_total(world, stand_in):
    owner = signed_in()
    html = owner.get("/").content.decode()
    assert "Draw all 2, EUR 0.30" in html and "/concepts/draw-all/" in html
    shown = concepts.draw_all(concepts.light_world(world.source))
    answer = owner.post("/concepts/draw-all/", json.dumps({"places": shown["places"], "euros": 0.30}),
                        content_type="application/json")
    assert answer.status_code == 200, answer.content
    for place in ("alpha", "beta"):
        found = drawing.draws(world.source.store, place)
        assert len(found) == 1 and found[0]["base"] is None and found[0]["euros"] == PRICE
        yes = world.source.store.spend_yes("override", found[0]["yes"])
        assert yes["euros"] == PRICE and "Draw all, 2 first draws for EUR 0.30" in yes["purpose"]
    assert "Draw all" not in owner.get("/").content.decode()  # nothing left undrawn: the button is gone


def test_draw_all_is_refused_when_the_total_or_the_places_changed_or_for_anyone_else(world, stand_in):
    owner = signed_in()
    places = concepts.draw_all(concepts.light_world(world.source))["places"]
    for body in ({"places": places, "euros": 0.15}, {"places": ["alpha"], "euros": 0.15}):
        assert owner.post("/concepts/draw-all/", json.dumps(body), content_type="application/json").status_code == 409
    assert signed_in("mallory").post("/concepts/draw-all/", json.dumps({"places": places, "euros": 0.30}),
                                     content_type="application/json").status_code == 403
    assert SyncRequest.objects.count() == 0
    owner.post("/concept/beta/draw/", json.dumps({"euros": PRICE}), content_type="application/json")
    with pytest.raises(web.review.Refused, match="changed"):  # on the store's machine: drawn since the click
        web.concept_draw(world.source.store, "beta", {}, PRICE, by="joey", first=True)
    assert len(drawing.draws(world.source.store, "beta")) == 1


def test_the_page_lists_the_pictures_a_draw_sends_and_why_it_waits(world, stand_in, monkeypatch):
    sent = ["the picked concept of the yard this place sits within", "a reference for its look only"]
    monkeypatch.setattr(drawing, "sent_pictures", lambda store, place: [(words, None) for words in sent]
                        if place == "beta" else [])
    monkeypatch.setattr(drawing, "waits", lambda store, place: "waits for yard's concept to be picked")
    page = signed_in().get("/concept/beta/").content.decode()
    assert all(f"<li data-v>{words}</li>" in page for words in sent)
    assert "waits for yard&#x27;s concept to be picked" in page


def test_draw_all_leaves_out_a_place_that_cannot_be_drawn_now_and_says_how_many(world, stand_in, monkeypatch):
    waits = drawing.waits
    monkeypatch.setattr(drawing, "waits", lambda store, place: "waits for yard's concept to be picked"
                        if place == "alpha" else waits(store, place))
    html = signed_in().get("/").content.decode()
    assert "Draw all 1, EUR 0.15" in html and "1 more with none cannot be drawn now" in html


def test_the_listener_answers_a_draw_alls_draws_side_by_side(world, stand_in, settings):
    owner = signed_in()
    places = concepts.draw_all(concepts.light_world(world.source))["places"]
    settings.SCORE_MODE = settings.HOSTED
    try:
        owner.post("/concepts/draw-all/", json.dumps({"places": places, "euros": 0.30}),
                   content_type="application/json")
        assert concepts.draw_all(concepts.light_world(world.source)) is None  # on their way: not offered twice
    finally:
        settings.SCORE_MODE = settings.LOCAL
    with override_settings(SCORE_SYNC_TOKEN=TOKEN):
        answered = listen.round_once(remote_of(hosted_client()), world.source)
    assert sorted(state for _, state in answered) == ["done", "done"]
    assert all(len(drawing.draws(world.source.store, place)) == 1 for place in places)


def test_draws_on_their_way_show_on_the_button_and_their_cards_until_they_land(world, stand_in):
    owner = signed_in()
    for place in ("alpha", "beta"):  # queued, not yet answered (hosted: the listener's to answer)
        SyncRequest.objects.create(kind=concepts.DRAW, user="joey", payload={"place": place, "euros": PRICE})
    html = owner.get("/").content.decode()
    assert "Drawing 2..." in html and "data-drawing" in html and html.count('class="draw-busy"') == 2
    assert "Draw all" not in html
    SyncRequest.objects.filter(payload__place="alpha").update(state="done")
    SyncRequest.objects.filter(payload__place="beta").update(state="refused", detail="refused: the price moved")
    html = owner.get("/").content.decode()
    assert "data-drawing" not in html and "draw-busy" not in html
    assert 'class="draw-refused" title="refused: the price moved"' in html


def test_a_picked_concepts_page_shows_its_scene_inventory_made_or_to_read(world):
    from score.dashboard.tests import fixture
    alpha = json.loads((world.data / "places/concepts.json").read_text())["concepts"]["alpha"]["sha256"]
    assert "scene inventory" not in signed_in().get("/concept/alpha/").content.decode()  # not picked: none
    fixture.an_inventory_read(world.store, world.data, "alpha", alpha)
    world.source.refresh()
    page = signed_in("joey2").get("/concept/alpha/").content.decode()
    assert "scene inventory" in page and "data-v>lamp</span>" in page and "&times;2" in page
    older = world.data / "inventory/alpha.json"
    older.write_text(older.read_text().replace(alpha, "o" * 64))  # read from an older concept: counts for nothing
    world.source.refresh()
    page = signed_in("joey3").get("/concept/alpha/").content.decode()
    assert "data-v>lamp</span>" not in page and "data-v>to read</span>" in page and "older concept" in page
