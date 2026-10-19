"""The basket's pages: every item a run would buy, grouped by place, each opening to its details (the place in 3D with
what it changes outlined and a before and after switch, what changes in words, what it is made from, the price with
guesses apart, the questions with their recommended answers); only the owner buys, says not now or answers; an
answer is kept where agents read it (hosted: queued for the store's machine); a hosted checkout is queued with the
items he saw."""
import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from score.dashboard.pages import basket
from score.dashboard.pages.models import BasketAnswer, BasketChoice, SyncRequest
from score.dashboard.proposals import make, records
from score.dashboard.sync import applying

pytestmark = pytest.mark.django_db
MEASURED = {"likely_euros": 2.0, "high_euros": 3.0, "likely_minutes": 10.0, "high_minutes": 20.0, "runs": 4,
            "cards": 1}
GUESSED = {"likely_euros": None, "high_euros": None, "guess_euros": 2.7, "likely_minutes": None, "high_minutes": None,
           "runs": 0, "cards": None}
SHIP = {"title": "Ship room concepts", "sentence": "The eight rooms inside the ship, drawn as concepts.",
        "nodes": ["concept-views"],
        "questions": [{"ask": "One deck or two?", "recommended": "One deck, as in your cutaway picture."}]}
CHANGES = {"objects": {"added": {"count": 2, "listed": [
    {"name": "Objects/crate_1", "layer": "settle", "low": [0, 0, 0], "high": [1, 1, 1]},
    {"name": "Objects/crate_2", "layer": "settle", "low": [2, 0, 0], "high": [3, 1, 1]}]},
    "removed": {"count": 1, "listed": [{"name": "Objects/old_lamp", "layer": "base", "low": [5, 0, 0],
                                        "high": [5.2, 3, 0.2]}]},
    "moved": {"count": 0, "listed": []}, "reshaped": {"count": 0, "listed": []},
    "refinished": {"count": 1, "listed": [{"name": "Objects/floor", "layer": "base", "low": [-5, 0, -5],
                                           "high": [5, 0.1, 5]}]}},
    "lamps": {"added": {"count": 0, "listed": []}, "removed": {"count": 0, "listed": []},
              "changed": {"count": 1, "listed": [{"name": "light_1", "low": [0, 2.85, 0], "high": [0.3, 3.15, 0.3]}]}},
    "sounds": {"added": [], "removed": [], "changed": []}, "cameras": {"added": [], "removed": [], "changed": []}}


def signed_in(name="joey"):
    client = Client()
    client.force_login(get_user_model().objects.create_user(name, password="a long enough password"))
    return client


def a_place(root, place, found, picture=False):
    partial = root / f".{place}-partial"
    (partial / "inputs").mkdir(parents=True)
    if picture:
        (partial / "inputs" / "1.jpg").write_bytes(b"jpeg")
    records.put_place(root, partial, place, found)


@pytest.fixture
def home(world, settings, tmp_path):
    """A made basket: alpha's pieces (measured, what changes for free, a picture it is made from), the environment's
    people bodies (never measured), and the ship's declared item with a question."""
    settings.SCORE_HOME = tmp_path / "home"
    root = settings.SCORE_HOME / "proposals"
    root.mkdir(parents=True)
    records.put_declared(root, "ship-room-concepts", SHIP)
    buys = [{"node": "closeup@alpha", "why": "code changed", "again": True, "price": MEASURED},
            {"node": "people-body-bram-work", "why": "never ran", "again": False, "price": GUESSED},
            {"node": "concept-views", "why": "files changed", "again": True, "price": MEASURED}]
    items = make.grouped(buys, {"closeup": "pieces"}, [], records.declared(root))
    records.put_index(root, {"made_at": "2026-10-19T08:00:00Z", "items": items})
    a_place(root, "alpha", {"place": "alpha", "copy": {"triangles": 10}, "changes": CHANGES, "made": ["assembly"],
                            "inputs": {"closeup@alpha": {"reads": [{"node": "plan@alpha", "how": records.MADE}],
                                                         "files": [{"from": "plan@alpha", "how": records.MADE,
                                                                    "name": "props.png", "kind": "picture",
                                                                    "file": "inputs/1.jpg"}]}}}, picture=True)
    a_place(root, None, {"place": None, "inputs": {
        "people-body-bram-work": {"reads": [], "files": [
            {"from": "data", "how": None, "name": "brief: bram.txt", "kind": "text",
             "text": "Bram, the mechanic, in work clothes."}]},
        "concept-views": {"reads": [], "files": []}}})
    return root


def test_the_basket_lists_every_item_by_place_with_what_changes_and_its_price(home):
    page = signed_in().get("/basket/").content.decode()
    assert "Pieces" in page and "2 objects added · 1 object taken out · 1 object refinished" in page
    assert "about EUR 2.00" in page and "at most 3.00" in page
    assert "People body" in page and "not measured yet" in page and "guess EUR 2.70" in page
    assert "Ship room concepts" in page and "1 question" in page
    assert page.index("Ship room concepts") < page.index("Alpha") < page.index("The environment")
    assert "/basket/item/alpha-pieces/" in page and "Changes to buy" not in page and "proposal" not in page.lower()


def test_an_item_opens_to_its_3d_what_changes_what_it_is_made_from_and_its_price(home):
    page = signed_in().get("/basket/item/alpha-pieces/").content.decode()
    assert 'src="/view/alpha?item=alpha-pieces&amp;embed=1"' in page and ">Before<" in page and ">After<" in page
    assert "2 objects added" in page and "2 x crate" in page and "1 object taken out" in page and "old lamp" in page
    assert "1 lamp changed" in page and "Made for free: OpenUSD stage." in page
    assert "/basket-file/alpha/inputs/1.jpg" in page and "about EUR 2.00" in page and "at most EUR 3.00" in page
    assert 'value="buy"' in page and 'value="later"' in page
    environment = signed_in("visitor").get("/basket/item/environment-people-body/").content.decode()
    assert "Bram, the mechanic, in work clothes." in environment and "Only the owner buys" in environment
    assert "not measured yet" in environment and "EUR 2.70, which is not a price" in environment
    assert signed_in("other").get("/basket/item/nothing-here/").status_code == 404


def test_a_declared_item_shows_its_own_sentence_and_question_with_our_answer(home):
    page = signed_in().get("/basket/item/ship-room-concepts/").content.decode()
    assert "The eight rooms inside the ship, drawn as concepts." in page
    assert "One deck or two?" in page and "One deck, as in your cutaway picture." in page
    assert "Yes, as recommended" in page


def test_only_the_owner_buys_as_he_saw_it(home):
    item = records.item(home, "alpha-pieces")
    form = {"item": "alpha-pieces", "version": item["version"], "choice": "buy"}
    assert signed_in("visitor").post("/basket/choose/", form).status_code == 403 and not BasketChoice.objects.exists()
    signed_in().post("/basket/choose/", {**form, "version": "0" * 16})
    assert not BasketChoice.objects.exists()
    owner = Client()
    owner.force_login(get_user_model().objects.get(username="joey"))
    owner.post("/basket/choose/", form)
    assert BasketChoice.objects.get(item="alpha-pieces").choice == "buy"
    assert "You chose to buy" in owner.get("/basket/").content.decode() and "I buy these" in owner.get(
        "/basket/").content.decode()


def test_his_answer_is_kept_where_agents_read_it(home):
    signed_in().post("/basket/answer/", {"item": "ship-room-concepts", "number": "1", "take": "recommended"})
    assert records.answers(home)["ship-room-concepts"]["1"]["answer"] == "One deck, as in your cutaway picture."
    owner = Client()
    owner.force_login(get_user_model().objects.get(username="joey"))
    owner.post("/basket/answer/", {"item": "ship-room-concepts", "number": "1", "take": "own",
                                   "answer": "Two decks where they fit."})
    assert records.answers(home)["ship-room-concepts"]["1"]["answer"] == "Two decks where they fit."
    assert "Your answer:" in owner.get("/basket/item/ship-room-concepts/").content.decode()
    assert signed_in("visitor").post("/basket/answer/", {"item": "ship-room-concepts", "number": "1",
                                                          "take": "recommended"}).status_code == 403


def hosted(settings, home):
    settings.SCORE_MODE = settings.HOSTED
    (home.parent / "export" / "current").mkdir(parents=True)
    (home.parent / "export" / "current" / "proposals").symlink_to(home)


def test_hosted_an_answer_is_queued_and_the_stores_machine_keeps_it(home, settings):
    hosted(settings, home)
    signed_in().post("/basket/answer/", {"item": "ship-room-concepts", "number": "1", "take": "recommended"})
    queued = SyncRequest.objects.get(kind="answer")
    assert queued.payload == {"item": "ship-room-concepts", "number": 1, "question": "One deck or two?",
                              "answer": "One deck, as in your cutaway picture."}
    assert records.answers(home) == {}
    settings.SCORE_MODE = settings.LOCAL
    BasketAnswer.objects.all().delete()
    done = applying.apply({"kind": "answer", "user": "joey", "payload": queued.payload}, None)
    assert done.state == "done" and records.answers(home)["ship-room-concepts"]["1"]["by"] == "joey"
    stranger = applying.apply({"kind": "answer", "user": "mallory", "payload": queued.payload}, None)
    assert stranger.state == "refused"


def test_hosted_a_checkout_is_queued_with_the_items_he_saw(home, settings):
    hosted(settings, home)
    item = records.item(home, "alpha-pieces")
    owner, key = signed_in(), "a" * 32
    owner.post("/basket/choose/", {"item": "alpha-pieces", "version": item["version"], "choice": "buy"})
    owner.post("/basket/checkout/", {"key": key, "confirm": "yes"})
    queued = SyncRequest.objects.get(kind="checkout")
    assert queued.payload == {"key": key, "items": [{"id": "alpha-pieces", "version": item["version"]}]}
    assert "waits for the store's machine" in basket.last_checkout()


def test_the_viewer_outlines_what_the_item_changes_on_each_side(home, world):
    copy = world.source.web_copies / "alpha"
    copy.mkdir(parents=True, exist_ok=True)
    (copy / "alpha.json").write_text(json.dumps({"made_at": "2026-10-19T08:00:00Z", "objects": []}))
    after = signed_in().get("/view/alpha?item=alpha-pieces&embed=1").content.decode()
    given = json.loads(after.split('id="view3d-data" type="application/json">')[1].split("</script>")[0])
    assert given["base"] == "/basket-file/alpha/web3d/"
    assert sorted(mark["kind"] for mark in given["marks"]) == ["added", "added", "lamp", "refinished"]
    assert 'class="view3d embed"' in after
    before = signed_in("other").get("/view/alpha?item=alpha-pieces&side=before").content.decode()
    given = json.loads(before.split('id="view3d-data" type="application/json">')[1].split("</script>")[0])
    assert given["base"] == "/web/alpha/" and sorted(mark["kind"] for mark in given["marks"]) == [
        "lamp", "refinished", "removed"]


def test_the_old_changes_page_goes_to_the_basket(home):
    answer = signed_in().get("/changes/")
    assert answer.status_code in (301, 302) and answer["Location"] == "/basket/"
