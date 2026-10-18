"""The basket and the owner's one checkout: prices from the moved rows and the runner's numbers, every refusal in
words, a key that makes the same checkout twice, branches landed on a temp repo's bare remote in a fixed order (a
conflict lands nothing), the world's stop line written by the owner's name only outside an agent's process, ONE batch
through the fake backend, and the results against their forecast. Nothing launches; no real remote is touched."""
import datetime
import os
import subprocess

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from fastapi.testclient import TestClient

from score.dashboard.checkout import flow, pricing, previews
from score.dashboard.launch.backend import Billed
from score.dashboard.pages.models import BasketBranch, Checkout
from score.dashboard.tests import fixture
from score.dashboard.tests.fixture import FakeBackend
from score.store import AGENT_MARKERS

pytestmark = pytest.mark.django_db(transaction=True)
ORIGIN = "http://127.0.0.1:8780"
BOOKS = {"month": "2026-10", "bill": 0.0, "ledger": 0.0}  # what a first line counts from (the fake spend reads none)
# What each test branch moves: fix-alpha the close-up at alpha by a file, fix-beta the close-up's code (every place it
# is declared at), plus a free row that is never priced.
MOVED = {
    "fix-alpha": {"closeup": {"paid": True, "code": False, "files": {"data/kit/alpha.json": ["alpha"]},
                              "places": ["alpha", "beta"]}},
    "fix-beta": {"closeup": {"paid": True, "code": True, "files": {}, "places": ["beta"]},
                 "plan": {"paid": False, "code": True, "files": {}, "places": ["alpha", "beta"]}},
    "fix-clash": {}, "fix-clash2": {},
}


def git(repo, *arguments):
    done = subprocess.run(["git", "-C", str(repo), *arguments], capture_output=True, text=True, check=True)
    return done.stdout.strip()


def commit_file(repo, name, text, message):
    (repo / name).write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def branch_with(repo, branch, name, text):
    """A fix branch off main with one commit writing `name`."""
    git(repo, "checkout", "-q", "-b", branch, "main")
    commit_file(repo, name, text, f"test: {branch}")
    git(repo, "checkout", "-q", "main")


@pytest.fixture
def repo(tmp_path, settings):
    """A temp repository on main with a bare remote and four fix branches (two that clash); SCORE_REPO points at it."""
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    git(work, "config", "user.email", "test@example.invalid")
    git(work, "config", "user.name", "test")
    commit_file(work, "base.txt", "one\n", "test: base")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "push", "-q", "origin", "main")
    branch_with(work, "fix-alpha", "alpha.txt", "alpha\n")
    branch_with(work, "fix-beta", "beta.txt", "beta\n")
    branch_with(work, "fix-clash", "base.txt", "clash one\n")
    branch_with(work, "fix-clash2", "base.txt", "clash two\n")
    git(work, "fetch", "-q", "origin")
    settings.SCORE_REPO = work
    return work


@pytest.fixture
def shop(world, repo, monkeypatch):
    """The fixture world, the temp repo, pricing and checkout run in this thread, no agent marks, the owner's books."""
    monkeypatch.setattr(pricing, "moved_rows", lambda repo, base, head: MOVED[branch_at(repo, head)])
    monkeypatch.setattr(pricing, "price_soon", lambda record, repo: pricing.work_out(record, repo, FakeBackend()))
    monkeypatch.setattr(flow, "run_soon", lambda record: flow.run(record, FakeBackend()))
    from score.review import web
    monkeypatch.setattr(web, "books_now", lambda: dict(BOOKS))
    for name in AGENT_MARKERS:
        monkeypatch.delenv(name, raising=False)
    FakeBackend.plan_buys, FakeBackend.bill, FakeBackend.ceiling = None, [], 250.0
    return world


def branch_at(repo, commit):
    """The fix branch whose tip is `commit`."""
    return next(branch for branch in MOVED if git(repo, "rev-parse", branch) == commit)


def api(name="joey"):
    """A FastAPI test client carrying a signed-in Django session and its CSRF cookie."""
    from score.dashboard.site.asgi import app
    user = get_user_model().objects.create_user(name, password="a long enough password")
    pages = Client()
    pages.force_login(user)
    pages.get("/login/")
    client = TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000))
    for cookie in pages.cookies.values():
        client.cookies.set(cookie.key, cookie.value)
    token = pages.cookies["csrftoken"].value if "csrftoken" in pages.cookies else ""
    client.headers.update({"X-CSRFToken": token, "Origin": ORIGIN})
    return client


def add(client, branch):
    """Add a branch as the page shows it."""
    offer = next(item for item in client.get("/api/checkout/offers").json() if item["branch"] == branch)
    return client.post("/api/checkout/basket", json={"branch": branch, "preview_hash": offer["preview_hash"]}).json()


def launches():
    return [call for call in FakeBackend.calls if call[0] == "launch"]


def stop_line(world):
    from score.review import web
    return web.stop_line(world.store, "world1")


# --- prices ------------------------------------------------------------------------------------------------------

def test_a_moved_paid_row_is_bought_where_it_moved_and_a_free_row_never():
    rows = {**MOVED["fix-alpha"], "terrain": {"paid": True, "code": True, "files": {}, "places": ["None"]},
            "plan": {"paid": False, "code": True, "files": {}, "places": ["alpha"]}}
    assert pricing.paid_nodes(rows) == ["closeup@alpha", "terrain"]
    assert pricing.paid_nodes(MOVED["fix-beta"]) == ["closeup@beta"]


def test_totals_count_each_node_once_and_say_what_is_unmeasured_or_unpriced():
    measured = {"likely_euros": 2.0, "high_euros": 3.0, "likely_minutes": 10.0, "high_minutes": 20.0, "cards": 2,
                "runs": 3}
    estimate = {"likely_euros": 5.0, "high_euros": 5.0, "likely_minutes": None, "high_minutes": None, "cards": None,
                "runs": 0}
    items = [{"nodes": {"closeup@alpha": measured, "closeup@beta": measured}},
             {"nodes": {"closeup@beta": measured, "pixal@alpha": estimate, "odd@alpha": {"error": "not a paid row"}}}]
    found = pricing.totals(pricing.basket_prices(items), jobs=1)
    assert (found["likely_euros"], found["high_euros"], found["nodes"]) == (9.0, 11.0, 4)
    assert found["likely_minutes"] == 20.0 and found["high_minutes"] == 40.0 and found["cards"] == 4
    assert found["unmeasured"] == ["pixal@alpha"] and found["unpriced"] == ["odd@alpha"]
    assert pricing.totals(pricing.basket_prices(items), jobs=8)["likely_minutes"] == 10.0  # the longest line


def test_a_preview_hash_moves_with_a_new_commit_or_a_proposal_made_again(repo, settings, tmp_path):
    settings.SCORE_HOME = tmp_path / "home"
    head = git(repo, "rev-parse", "fix-alpha")
    first = previews.preview_hash("fix-alpha", head)
    assert previews.preview_hash("fix-alpha", head) == first
    proposal = previews.proposals_root() / "fix-alpha" / "alpha" / previews.RECORD
    proposal.parent.mkdir(parents=True)
    proposal.write_text('{"commit": "x"}')
    second = previews.preview_hash("fix-alpha", head)
    assert second != first
    proposal.write_text('{"commit": "y"}')
    assert previews.preview_hash("fix-alpha", head) != second
    assert previews.preview_hash("fix-alpha", git(repo, "rev-parse", "main")) != first


def test_an_item_is_priced_on_the_runners_numbers_from_the_moved_rows(shop):
    client = api()
    assert "in the basket" in add(client, "fix-beta")["said"]
    item = client.get("/api/checkout/basket").json()["items"][0]
    assert item["price"]["state"] == "ready" and list(item["price"]["nodes"]) == ["closeup@beta"]
    assert item["price"]["totals"]["high_euros"] == 15.0 and item["price"]["totals"]["likely_minutes"] == 30.0
    assert ("price", "world1", ("closeup@beta",)) in FakeBackend.calls


# --- refusals ----------------------------------------------------------------------------------------------------

def test_basket_and_checkout_are_the_owners_and_need_csrf(shop):
    guest = api("guest")
    assert guest.get("/api/checkout/offers").status_code == 200
    assert guest.get("/api/checkout/basket").status_code == 403
    assert guest.post("/api/checkout/basket", json={"branch": "fix-alpha", "preview_hash": "x"}).status_code == 403
    assert guest.post("/api/checkout", json={"key": "k" * 16, "confirmed": True}).status_code == 403
    owner = api()
    owner.headers.pop("X-CSRFToken")
    assert owner.post("/api/checkout", json={"key": "k" * 16, "confirmed": True}).status_code == 403
    assert not Checkout.objects.exists() and not launches()


def test_an_unknown_branch_or_a_preview_he_did_not_see_is_refused(shop):
    client = api()
    assert client.post("/api/checkout/basket", json={"branch": "fix-nothing", "preview_hash": "x"}).status_code == 404
    said = client.post("/api/checkout/basket", json={"branch": "fix-alpha", "preview_hash": "0" * 64}).json()["said"]
    assert "preview changed while you looked" in said and not BasketBranch.objects.exists()


def test_a_preview_changed_since_he_looked_refuses_the_checkout(shop, repo, settings, tmp_path):
    settings.SCORE_HOME = tmp_path / "home"
    client = api()
    add(client, "fix-alpha")
    git(repo, "checkout", "-q", "fix-alpha")
    commit_file(repo, "alpha.txt", "alpha again\n", "test: alpha again")
    git(repo, "checkout", "-q", "main")
    said = client.post("/api/checkout", json={"key": "a" * 16, "confirmed": True}).json()["said"]
    assert "fix-alpha has a new commit since you looked" in said
    git(repo, "branch", "-q", "-f", "fix-alpha", "fix-alpha~1")
    proposal = previews.proposals_root() / "fix-alpha" / "alpha" / previews.RECORD
    proposal.parent.mkdir(parents=True)
    proposal.write_text('{"commit": "a new still"}')
    said = client.post("/api/checkout", json={"key": "b" * 16, "confirmed": True}).json()["said"]
    assert "fix-alpha's preview changed since you looked" in said
    assert not Checkout.objects.exists() and not launches() and stop_line(shop) is None


def test_every_refusal_in_words(shop, settings, monkeypatch):
    client = api()
    said = client.post("/api/checkout", json={"key": "c" * 16, "confirmed": False}).json()["said"]
    assert "the basket is empty" in said and "I buy this basket" in said
    add(client, "fix-alpha")
    settings.SCORE_MONTH_EUROS = None
    assert "stop is not set" in client.post("/api/checkout", json={"key": "c" * 16, "confirmed": True}).json()["said"]
    settings.SCORE_MONTH_EUROS = "250"
    from score.dashboard.pages import actions
    monkeypatch.setattr(actions, "agent_started", lambda: True)
    said = client.post("/api/checkout", json={"key": "c" * 16, "confirmed": True}).json()["said"]
    assert "started from an agent's shell" in said
    assert not Checkout.objects.exists() and not launches()


# --- the checkout ------------------------------------------------------------------------------------------------

def test_the_checkout_lands_writes_the_line_and_launches_one_batch(shop, repo):
    client = api()
    add(client, "fix-beta")
    add(client, "fix-alpha")
    main_before = git(repo, "rev-parse", "origin/main")
    started = client.post("/api/checkout", json={"key": "d" * 16, "confirmed": True}).json()
    record = started["checkout"]
    assert record["state"] == "launched", started
    remote = repo.parent / "remote.git"
    subjects = git(remote, "log", "--format=%s", f"{main_before}..main").splitlines()
    assert subjects == ["test: fix-beta", "test: fix-alpha"]  # landed by name: alpha first, beta on top
    assert git(repo, "rev-parse", "HEAD") == git(remote, "rev-parse", "main") == record["main_after"]
    assert [item["branch"] for item in record["landed"]] == ["fix-alpha", "fix-beta"]
    line = stop_line(shop)
    assert line["euros"] == 100.0 + 10.0 + 30.0 and line["by"] == "joey" and "fix-alpha, fix-beta" in line["reason"]
    assert record["stop_line"]["high"] == 30.0
    (launched,) = launches()
    assert launched[1].places == ("alpha", "beta") and launched[1].stages == ("closeup",)
    assert "the owner's checkout" in launched[3]
    assert record["launch"] is not None


def test_the_same_key_is_the_same_checkout(shop):
    client = api()
    add(client, "fix-alpha")
    first = client.post("/api/checkout", json={"key": "e" * 16, "confirmed": True}).json()
    again = client.post("/api/checkout", json={"key": "e" * 16, "confirmed": True}).json()
    assert again["checkout"]["id"] == first["checkout"]["id"] and "already made with this key" in again["said"]
    assert Checkout.objects.count() == 1 and len(launches()) == 1


def test_a_conflict_lands_nothing_writes_no_line_and_launches_nothing(shop, repo):
    client = api()
    add(client, "fix-clash")
    add(client, "fix-clash2")
    main_before = git(repo.parent / "remote.git", "rev-parse", "main")
    record = client.post("/api/checkout", json={"key": "f" * 16, "confirmed": True}).json()["checkout"]
    found = Checkout.objects.get(pk=record["id"])
    assert found.state == "refused"
    assert "fix-clash2 does not rebase onto main" in found.detail and "base.txt" in found.detail
    assert git(repo.parent / "remote.git", "rev-parse", "main") == main_before
    assert stop_line(shop) is None and not launches()
    assert "checkout-" not in git(repo, "worktree", "list")


def test_branches_that_move_no_paid_row_land_and_buy_nothing(shop, repo):
    client = api()
    add(client, "fix-clash")
    record = client.post("/api/checkout", json={"key": "n" * 16, "confirmed": True}).json()["checkout"]
    found = Checkout.objects.get(pk=record["id"])
    assert found.state == "landed" and "move no paid row" in found.detail
    assert git(repo.parent / "remote.git", "log", "-1", "--format=%s", "main") == "test: fix-clash"
    assert stop_line(shop) is None and not launches() and not [call for call in FakeBackend.calls if call[0] == "plan"]


def test_a_run_that_would_buy_more_than_was_priced_is_refused_before_the_line(shop):
    client = api()
    add(client, "fix-alpha")
    FakeBackend.plan_buys = ["closeup@alpha", "closeup@beta"]
    record = client.post("/api/checkout", json={"key": "g" * 16, "confirmed": True}).json()["checkout"]
    found = Checkout.objects.get(pk=record["id"])
    assert found.state == "refused" and "would also buy closeup@beta" in found.detail
    assert stop_line(shop) is None and not launches()


def test_a_basket_that_cannot_fit_under_the_runners_spend_is_refused_before_start(shop):
    client = api()
    add(client, "fix-alpha")
    FakeBackend.ceiling = 115.0  # the runner still reads an older, lower line: room EUR 5 for a EUR 15 high
    record = client.post("/api/checkout", json={"key": "h" * 16, "confirmed": True}).json()["checkout"]
    found = Checkout.objects.get(pk=record["id"])
    assert found.state == "refused" and "cannot finish under the stop: high EUR 15.00, room EUR 5.00" in found.detail
    assert not launches()


def test_an_agents_process_writes_no_line_and_launches_nothing(shop):
    client = api()
    add(client, "fix-alpha")
    os.environ[AGENT_MARKERS[0]] = "1"  # the cockpit's own check passed (patched); the guard's writer still refuses
    try:
        record = client.post("/api/checkout", json={"key": "i" * 16, "confirmed": True}).json()["checkout"]
    finally:
        os.environ.pop(AGENT_MARKERS[0])
    found = Checkout.objects.get(pk=record["id"])
    assert found.state == "failed" and "PermissionError" in found.detail
    assert stop_line(shop) is None and not launches()


# --- results -----------------------------------------------------------------------------------------------------

def test_results_show_real_cost_against_forecast_gates_and_new_outputs(shop):
    client = api()
    add(client, "fix-alpha")
    add(client, "fix-beta")
    record = client.post("/api/checkout", json={"key": "j" * 16, "confirmed": True}).json()["checkout"]
    found = Checkout.objects.get(pk=record["id"])
    since = found.at.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    FakeBackend.bill = [Billed("closeup@alpha", 8.5, 25.0, since), Billed("closeup@alpha", 0.5, 0.0, since),
                        Billed("closeup@beta", 99.0, 5.0, "2026-01-01T00:00:00Z")]  # an older run's line
    new = fixture.made(shop.store, shop.root / "work", "closeup", "alpha", tweak=7, minutes_ago=0)
    shop.source.refresh()  # the cockpit reads the store's index again within a minute; the test at once
    shown = client.get(f"/api/checkout/{record['id']}/results").json()
    alpha, beta = shown["items"]
    assert alpha["branch"] == "fix-alpha" and alpha["euros"] == 9.0 and alpha["forecast"]["high_euros"] == 15.0
    (node,) = alpha["nodes"]
    assert node["new"] and node["output"] == new and node["minutes"] == 25.0
    assert node["verdicts"] == [{"check": "looks", "answer": "pass", "reason": "0 faults"}]
    assert beta["euros"] is None and beta["nodes"][0]["output"] is None and beta["nodes"][0]["new"] is False
    fixture.made(shop.store, shop.root / "work", "closeup", "beta", "fail", faults=4, tweak=8, minutes_ago=0)
    shop.source.refresh()
    beta = client.get(f"/api/checkout/{record['id']}/results").json()["items"][1]
    assert beta["new_outputs"] == 1 and beta["failed_gates"] == 1
    assert shown["euros"] == 9.0 and shown["forecast"]["high_euros"] == 30.0
    assert client.get("/api/checkout/999/results").status_code == 404


# --- the shipped backend's price and ledger (subprocess replaced) ------------------------------------------------

def test_the_local_backend_prices_through_score_price_and_reads_the_ledger_by_node(settings, tmp_path):
    import json
    import types
    from score.dashboard.launch import localrun
    said = []

    def run(command, **_):
        said.append(command)
        return types.SimpleNamespace(returncode=0, stderr="", stdout="reading the ledger\n" + json.dumps(
            {"world": "world1", "nodes": {"closeup@alpha": {"likely_euros": 1.0, "high_euros": 2.0}}}))
    found = localrun.LocalBackend(run=run).price("world1", ["closeup@alpha"])
    assert found == {"closeup@alpha": {"likely_euros": 1.0, "high_euros": 2.0}}
    assert said[0][1:] == ["-m", "score", "price", "world1", "--node", "closeup@alpha", "--json"]
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("\n".join(json.dumps(row) for row in (
        {"ticket": "closeup@alpha k1", "euros": 3.0, "wall_minutes": 9, "started": "2026-10-18T12:00:00Z"},
        {"ticket": "closeup@alpha k0", "euros": 7.0, "wall_minutes": 9, "started": "2026-10-17T12:00:00Z"},
        {"ticket": "closeup@beta k2", "euros": 5.0, "wall_minutes": 9, "started": "2026-10-18T12:00:00Z"})) + "\n")
    settings.SCORE_LEDGER_FILES = [ledger]
    (line,) = localrun.LocalBackend(run=run).ledgered(["closeup@alpha"], "2026-10-18T00:00:00Z")
    assert (line.node, line.euros, line.minutes) == ("closeup@alpha", 3.0, 9)
