"""Changes to buy: every proposal record shows as its fix with before and after pictures, a plain sentence, the free
and the paid part with the runner's price, the owner's question with its recommended answer and a show-in-3D; only
the owner's buy or not now is taken, hosted it is queued for the store's machine and applied there into the
checkout's basket; the export carries the proposals; a sync pass prices what is not priced."""
import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from score.dashboard.pages import changes
from score.dashboard.pages.models import BasketBranch, ProposalChoice, SyncRequest
from score.dashboard.proposals import exporting, finish, records
from score.dashboard.sync import applying
from score.dashboard.tests import fixture

pytestmark = pytest.mark.django_db
COMMIT = "c0ffee" * 6 + "c0ff"


def signed_in(name="joey"):
    client = Client()
    client.force_login(get_user_model().objects.create_user(name, password="a long enough password"))
    return client


def made(root, branch="fix-ship-hull", place="alpha", **fields):
    """A made proposal as propose.py leaves it: its stills, its 3D copy, its taken nodes."""
    partial = root / f".{branch}-{place}-partial"
    (partial / "stills").mkdir(parents=True)
    (partial / "stills" / "from-door.jpg").write_bytes(b"jpeg")
    (partial / "web3d").mkdir()
    (partial / "web3d" / f"{place}.json").write_text("{}")
    (partial / "web3d" / f"{place}.glb").write_bytes(b"whole")
    record = {"branch": branch, "place": place, "commit": COMMIT, "made_at": "2026-10-18T12:00:00Z",
              "change": "The hull is one piece (#10); the hangar fits it (#10).", "made": ["assembly", "plan"],
              "needs_paid_batch": ["surfaces-bake"], "has_3d": True, "hero": "stills/from-door.jpg", "moved_paid": [],
              "stills": [{"name": "from-door", "file": "stills/from-door.jpg"}],
              "layers": [{"node": f"assembly@{place}", "stage": "assembly", "how": records.MADE},
                         {"node": f"surfaces-bake@{place}", "stage": "surfaces-bake", "how": records.PAID}],
              **fields}
    return records.put(root, partial, record)


@pytest.fixture
def home(world, settings, tmp_path):
    settings.SCORE_HOME = tmp_path / "home"
    (settings.SCORE_HOME / "proposals").mkdir(parents=True)
    return settings.SCORE_HOME / "proposals"


def test_every_proposal_shows_its_pictures_words_price_question_and_3d(home):
    made(home, sentence="The ship was too small for its hangar.", question="Keep the old hangar doors?",
         recommended="No: the new ones fit the 46 m ship.")
    finish.finish(home, "fix-ship-hull", "alpha", home / "store", with_pictures=False, chosen=fixture.FakeBackend())
    page = signed_in().get("/changes/").content.decode()
    assert "The ship was too small for its hangar." in page
    assert "/proposal/fix-ship-hull/alpha/stills/from-door.jpg" in page
    assert "Keep the old hangar doors?" in page and "the new ones fit the 46 m ship" in page
    assert "/view/alpha?proposal=fix-ship-hull" in page
    assert "EUR 10.00" in page and "EUR 15.00" in page
    assert 'value="buy"' in page and 'value="later"' in page


def test_a_proposal_without_words_says_its_first_change_without_issue_numbers(home):
    made(home)
    page = signed_in().get("/changes/").content.decode()
    assert "The hull is one piece." in page and "(#10)" not in page.split("<details")[0]
    assert "Price not worked out yet" in page


def test_only_the_owner_buys(home):
    made(home)
    answer = signed_in("visitor").post("/changes/choose/", {"branch": "fix-ship-hull", "commit": COMMIT,
                                                             "choice": "buy"})
    assert answer.status_code == 403 and not ProposalChoice.objects.exists()
    assert "Only the owner buys" in signed_in("visitor2").get("/changes/").content.decode()


def test_hosted_a_buy_is_kept_and_queued_for_the_stores_machine(home, settings):
    settings.SCORE_MODE = settings.HOSTED
    settings.SCORE_HOME = home.parent
    (home.parent / "export" / "current").mkdir(parents=True)
    (home.parent / "export" / "current" / "proposals").symlink_to(home)
    made(home)
    signed_in().post("/changes/choose/", {"branch": "fix-ship-hull", "commit": COMMIT, "choice": "buy"})
    assert ProposalChoice.objects.get(branch="fix-ship-hull").choice == "buy"
    queued = SyncRequest.objects.get(kind="proposal")
    assert queued.payload == {"branch": "fix-ship-hull", "commit": COMMIT, "choice": "buy"}
    assert "waiting for the store" in signed_in("other").get("/changes/").content.decode()


def test_the_stores_machine_puts_a_bought_fix_in_the_basket_at_the_commit_he_saw(home, monkeypatch):
    from score.dashboard.checkout import flow
    monkeypatch.setattr(flow, "offer", lambda branch: {"head": COMMIT, "preview_hash": "f" * 64})
    priced = type("Priced", (), {"state": "ready", "body": {"totals": {"high_euros": 15.0}}, "error": ""})
    monkeypatch.setattr(changes, "priced_now", lambda branch: priced)
    done = applying.apply({"kind": "proposal", "user": "joey",
                           "payload": {"branch": "fix-ship-hull", "commit": COMMIT, "choice": "buy"}}, None)
    assert done.state == "done" and BasketBranch.objects.get(branch="fix-ship-hull").head == COMMIT
    assert "at most EUR 15.00" in done.detail
    moved = applying.apply({"kind": "proposal", "user": "joey",
                            "payload": {"branch": "fix-ship-hull", "commit": "a" * 40, "choice": "buy"}}, None)
    assert moved.state == "refused" and "newer commit" in moved.detail
    later = applying.apply({"kind": "proposal", "user": "joey",
                            "payload": {"branch": "fix-ship-hull", "commit": COMMIT, "choice": "later"}}, None)
    assert later.state == "done" and not BasketBranch.objects.exists()
    stranger = applying.apply({"kind": "proposal", "user": "mallory",
                               "payload": {"branch": "fix-ship-hull", "commit": COMMIT, "choice": "buy"}}, None)
    assert stranger.state == "refused"


def test_pricing_takes_only_the_paid_nodes_once_a_commit_and_keeps_the_words_on_amend(home):
    made(home, sentence="Kept.")
    backend = fixture.FakeBackend()
    fixture.FakeBackend.calls.clear()
    assert finish.finish_all(home, home / "store", False, backend) == [("fix-ship-hull", "alpha")]
    assert finish.finish_all(home, home / "store", False, backend) == []
    assert fixture.FakeBackend.calls == [("price", "world1", ("surfaces-bake@alpha",))]
    record = records.read(home, "fix-ship-hull", "alpha")
    assert record["sentence"] == "Kept." and record["price"]["totals"]["high_euros"] == 15.0
    assert json.loads((home / records.INDEX).read_text())[0]["branch"] == "fix-ship-hull"


def test_a_fix_is_priced_at_every_paid_node_its_branch_makes_again(home):
    made(home, moved_paid=["demo-film@alpha", "sound@beta", "terrain"])
    backend = fixture.FakeBackend()
    fixture.FakeBackend.calls.clear()
    finish.finish_all(home, home / "store", False, backend)
    assert fixture.FakeBackend.calls == [("price", "world1",
                                          ("demo-film@alpha", "sound@beta", "surfaces-bake@alpha", "terrain"))]
    record = records.read(home, "fix-ship-hull", "alpha")
    assert sorted(record["price"]["nodes"]) == ["demo-film@alpha", "surfaces-bake@alpha"]
    assert sorted(record["price"]["branch_nodes"]) == ["sound@beta", "terrain"]
    total = changes.paid_total([record])
    assert total["jobs"] == 4 and total["high"] == 4 * record["price"]["nodes"]["demo-film@alpha"]["high_euros"]
    assert "demo-film" in changes.paid_stages(record)


def test_a_price_made_before_the_moved_rows_were_counted_is_worked_out_again(home):
    made(home, price={"commit": COMMIT, "at": "2026-10-18T12:00:00Z", "nodes": {}, "totals": {}})
    assert finish.price_due(records.read(home, "fix-ship-hull", "alpha"))


def test_the_export_carries_records_and_pictures_before_whole_copies(home):
    made(home)
    (records.folder(home, "fix-ship-hull", "alpha") / "before").mkdir()
    (records.folder(home, "fix-ship-hull", "alpha") / "before" / "from-door.jpg").write_bytes(b"jpeg")
    copied = []

    class Filler:
        def place_copy(self, source, target, what):
            copied.append(target)

    exporting.in_export(home, Filler(), wholes=False)
    exporting.in_export(home, Filler(), wholes=True)
    assert copied[-1] == "proposals/fix-ship-hull/alpha/web3d/alpha.glb"
    assert "proposals/fix-ship-hull/alpha/before/from-door.jpg" in copied[:-1]
    assert copied[0] == "proposals/index.json"


def test_the_viewer_opens_a_fixs_own_3d_copy(home):
    made(home)
    page = signed_in().get("/view/alpha?proposal=fix-ship-hull").content.decode()
    assert "/proposal/fix-ship-hull/alpha/web3d/" in page


def test_a_plain_sentence_drops_issue_numbers_and_keeps_the_first_change():
    assert changes.plain_sentence({"change": "the hull is one piece (#10); and more (#10)."}) == \
        "The hull is one piece."


def test_hosted_checkout_needs_the_tick_and_queues_the_fixes_he_bought(home, settings):
    settings.SCORE_MODE = settings.HOSTED
    settings.SCORE_HOME = home.parent
    (home.parent / "export" / "current").mkdir(parents=True)
    (home.parent / "export" / "current" / "proposals").symlink_to(home)
    made(home)
    owner = signed_in()
    owner.post("/changes/choose/", {"branch": "fix-ship-hull", "commit": COMMIT, "choice": "buy"})
    owner.post("/changes/checkout/", {"key": "a" * 32})
    assert not SyncRequest.objects.filter(kind="checkout").exists()
    owner.post("/changes/checkout/", {"key": "a" * 32, "confirm": "yes"})
    queued = SyncRequest.objects.get(kind="checkout")
    assert queued.payload == {"key": "a" * 32, "fixes": [{"branch": "fix-ship-hull", "commit": COMMIT}]}
    assert signed_in("visitor").post("/changes/checkout/", {"key": "b" * 32, "confirm": "yes"}).status_code == 403


def test_the_stores_machine_checks_out_only_the_basket_he_saw(home, monkeypatch):
    from score.dashboard.checkout import flow
    started = []
    record = type("Done", (), {"state": "launched"})
    monkeypatch.setattr(flow, "start", lambda user, key, confirmed, at_once=False: (
        started.append((user.username, key, confirmed, at_once)) or record, "checkout 1: launched"))
    item = {"kind": "checkout", "user": "joey",
            "payload": {"key": "a" * 32, "fixes": [{"branch": "fix-ship-hull", "commit": COMMIT}]}}
    assert applying.apply(item, None).state == "refused" and not started
    BasketBranch.objects.create(branch="fix-ship-hull", head=COMMIT, preview_hash="f" * 64, added_by="joey")
    assert applying.apply(item, None).state == "done"
    assert started == [("joey", "a" * 32, True, True)]
    assert applying.apply({**item, "user": "mallory"}, None).state == "refused"


def test_a_proposal_made_without_stills_gets_them_from_its_stage_in_the_scratch_store(home, monkeypatch):
    from score.dashboard.proposals import pictures
    made(home, stills=[], assembly="ab" * 32)
    scratch = home.parent / "proposals-work" / "store" / "objects"
    (scratch / "outputs").mkdir(parents=True)
    (scratch / "blobs").mkdir()
    (scratch / "outputs" / f"{'ab' * 32}.json").write_text(json.dumps({"alpha.usda": "cd" * 32}))
    (scratch / "blobs" / ("cd" * 32)).write_text("#usda 1.0")
    drawn = []

    def stills(stage_file, views, out):
        drawn.append(stage_file.read_text())
        out.mkdir(parents=True, exist_ok=True)
        (out / "from-door.jpg").write_bytes(b"jpeg")
        return [{"name": "from-door", "file": "stills/from-door.jpg"}]

    monkeypatch.setattr(pictures, "stills", stills)
    monkeypatch.setattr(pictures, "views", lambda folder, tree, place: [{"name": "from-door"}])
    monkeypatch.setattr(finish, "before_stills", lambda record, store_root, out: [])
    finish.finish(home, "fix-ship-hull", "alpha", home / "store", chosen=fixture.FakeBackend())
    record = records.read(home, "fix-ship-hull", "alpha")
    assert drawn == ["#usda 1.0"] and record["hero"] == "stills/from-door.jpg"
    assert (records.folder(home, "fix-ship-hull", "alpha") / "stills" / "from-door.jpg").is_file()
