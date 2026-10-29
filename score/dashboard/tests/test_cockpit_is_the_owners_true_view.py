"""The cockpit is the owner's true view: every page shows what the store, the runner and the library say (numbers it
only sums, never makes; unknown as None, never 0; a stale price as no figure), and only the owner, signed in, in his own
process, at the price shown, changes anything (a spend click, a lock, a Keep, an advance, a stop). Driven through the
pages (Django), the API (FastAPI) and pages/, state/screens.py, state/batch_run.py and the sync applier they call, on
the fixture environment (tests/fixture.py), a tiny library folder, written logs and pools, stand-in models: no call
is made, nothing is spent, no real store or home is read.

Each test's docstring names the code break that turns it red; each was applied once and seen red (2026-10-26).
Wording checks guard owner rules and say which (numbers not prose #42, node ids only in the details fold, no stop shown,
a guess never a price, the theme's tokens, and the package's own rule that no file names or imports a
provider: the list of names is built from the repository's own cloud backends and API kinds, so this file names none)."""
import ast
import base64
import contextlib
import datetime
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import time
import types
import urllib.error
from html import unescape
from html.parser import HTMLParser

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.utils import timezone
from django.utils.html import escape
from fastapi.testclient import TestClient
from PIL import Image

from score.dashboard.pages import actions, library_actions, run_monitor, seen
from score.dashboard.pages.models import (BasketAnswer, BasketChoice, Checkout, Launch, Plan, RefineItem,
                                          SyncRequest)
from score.dashboard.proposals import make, records
from score.dashboard.state import batch_run, local, machine, plain, screens, versions
from score.dashboard.state.exported import ExportedSource
from score.dashboard.state.models import CostLine, Spend, WorldState
from score.dashboard.sync import applying, building, client, listen, one_store
from score.dashboard.tests import fixture
from score.dashboard.tests.fixture import (MADE, NODE, ORIGIN, SPEND, TOKEN, FakeBackend, hosted_client, opener_of,
                                          outside_details)

pytestmark = pytest.mark.django_db(transaction=True)
REPO = pathlib.Path(__file__).resolve().parents[3]
WORD_BUDGET = 40  # a screen's words outside data, hover text and scripts (owner, 2026-10-20: text down about 98%)


# --- clients ----------------------------------------------------------------------------------------------------------

def signed_in(name="joey"):
    """A pages client signed in as `name` (joey is SCORE_OWNER)."""
    user, _ = get_user_model().objects.get_or_create(username=name)
    page = Client()
    page.force_login(user)
    return page


def api(name="joey"):
    """A FastAPI client carrying a signed-in session and its CSRF cookie and header (the page's own fetch)."""
    from score.dashboard.site.asgi import app
    pages = signed_in(name)
    pages.get("/login/")  # sets the csrftoken cookie
    web = TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000))
    for cookie in pages.cookies.values():
        web.cookies.set(cookie.key, cookie.value)
    token = pages.cookies["csrftoken"].value if "csrftoken" in pages.cookies else ""
    web.headers.update({"X-CSRFToken": token, "Origin": ORIGIN})
    return web


def remote_of(web, name=None):
    named = {"machine_name": name} if name else {}
    return client.Remote("http://hosted", TOKEN, opener_of(web), **named)


class Prose(HTMLParser):
    """The words a page shows that are not data: its text outside script, style, title (hover text) and any element
    marked data-v (a number, a name, a state)."""
    SKIP = {"script", "style", "title"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.hidden, self.words = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.hidden.append(tag in self.SKIP or any(name == "data-v" for name, _ in attrs)
                               or bool(self.hidden and self.hidden[-1]))

    def handle_startendtag(self, tag, attrs):
        """A self-closed element (an SVG circle) opens nothing."""

    def handle_endtag(self, tag):
        if tag not in self.VOID and self.hidden:
            self.hidden.pop()

    def handle_data(self, data):
        if not (self.hidden and self.hidden[-1]):
            self.words += re.findall(r"[A-Za-z][A-Za-z'-]*", data)


def prose(html):
    parser = Prose()
    parser.feed(html)
    return parser.words


def view_data(html):
    return json.loads(re.search(r'<script id="view3d-data" type="application/json">(.*?)</script>', html,
                                re.S).group(1))


def a_png(colour=(40, 90, 160), size=(96, 60)):
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, "PNG")
    return buffer.getvalue()


# --- the fixture environment's gaps, their price and prepare's record -------------------------------------------------

MEASURED = {"likely_euros": 2.0, "high_euros": 3.0, "likely_minutes": 10.0, "high_minutes": 20.0, "runs": 4,
            "cards": 1}
FORECAST = {**MEASURED, "basis": "per unit × forecast", "units": 2, "unit_source": "the place's missing rows"}
GUESSED = {"likely_euros": None, "high_euros": None, "guess_euros": 1.0, "guess_from": "score/stages/__init__.py:243",
           "likely_minutes": None, "high_minutes": None, "runs": 0, "basis": "not measured yet", "units": None}
SETTLE = {**MEASURED, "basis": "measured runs"}  # a paid step off the prop route, measured
PLAN_WORK = "data/plans/alpha.json with its leads"


def a_gaps_finding(world, settings, tmp_path):
    """The gaps check's findings for alpha over its accepted assembly: two lamps the close-up fills (a basket item
    carries it, measured), a gate on a step nothing buys now, and the plan no stage makes yet; the basket made with
    that one item (2026-10-19)."""
    folder = world.root / "props/work/checks/gaps/alpha"
    folder.mkdir(parents=True, exist_ok=True)
    missing = {"rule": "missing", "kind": "generate", "sentence": "a lamp: nothing made for it yet (made by the route)",
               "picture": None, "row": "lamp", "gates": [], "source": "inventory", "node": "closeup@alpha",
               "work": None, "placed": "spot"}
    (folder / "findings.json").write_text(json.dumps({"place": "alpha", "outputs": {
        "assembly@alpha": world.outputs["assembly@alpha"]}, "findings": [
        dict(missing, id="missing:lamp_1", prim="/alpha/Gaps/lamp_1", low=[0, 0, 0], high=[1, 1, 1]),
        dict(missing, id="missing:lamp_2", prim="/alpha/Gaps/lamp_2", low=[2, 0, 0], high=[3, 1, 1]),
        {"id": "gate:complete/painted:crate_1", "rule": "gate", "prim": "/alpha/Objects/crate_1", "kind": None,
         "sentence": "crate_1: still the rough paint", "picture": None, "row": "crate", "gates": ["complete/painted"],
         "source": "judgement:complete@alpha", "node": "complete@alpha", "work": None, "placed": None,
         "low": [4, 0, 0], "high": [5, 1, 1]},
        {"id": "place:plan", "rule": "place", "prim": "/alpha", "kind": None,
         "sentence": "this place's plan is not accepted", "picture": None, "row": None, "gates": [], "source": "route",
         "node": None, "work": PLAN_WORK, "placed": None, "low": None, "high": None}]}))
    settings.SCORE_HOME = tmp_path / "home"
    root = settings.SCORE_HOME / "proposals"
    root.mkdir(parents=True)
    items = make.grouped([{"node": "closeup@alpha", "why": "code changed", "again": True, "price": MEASURED}],
                         {"closeup": "pieces"}, [], {})
    records.put_index(root, {"made_at": "2026-10-19T08:00:00Z", "items": items})
    return items


def a_gaps_price(world, **more):
    """The runner's price of alpha's gaps (score price --gaps), made now on this checkout's code: the close-up per unit
    times its forecast, the sound only guessed, complete free (`more` over it)."""
    from score import graph
    folder = world.root / "props/work/checks/gaps-price"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "world1.json").write_text(json.dumps({
        "world": "world1", "made_at": graph.now(), "priced_on": {**local.priced_here(), "uncommitted": False},
        "nodes": {"closeup@alpha": FORECAST, "sound@alpha": GUESSED},
        "chains": {"alpha": {"closeup@alpha": ["closeup@alpha", "complete@alpha", "sound@alpha"],
                             "complete@alpha": ["complete@alpha", "sound@alpha"]}},
        "gaps": {"alpha": {}}, "free": ["complete@alpha"], "totals": {},
        "unfillable": [{"work": PLAN_WORK, "gaps": 1}], "outside": [], "not_current": [], "not_checked": [], **more}))


def take(place, status, lost=True):
    return {"place": place, "take": f"{place}_{status}", "status": status,
            "inputs": ["view v1's picture is not in the work folder"] if lost else []}


def a_design(approved):
    """Prepare's design record: alpha's and beta's, the `approved` ones approved, the others in design."""
    def one(place):
        if place in approved:
            return {"concept": "picked", "plan": "approved", "output": "o" * 64, "hint": "K01"}
        return {"concept": "missing", "plan": "remake", "output": None, "hint": None}
    return {"places": {place: one(place) for place in ("alpha", "beta")}, "approved": list(approved)}


def a_remake(world, priced_on=None, approved=("alpha", "beta"), inventory=None):
    """Prepare's record as the real one is shaped: alpha's three takes, two bought waiting on a lost input and one a
    predicted gap, priced EUR 10 to 12 with the likeness calibration unpriced; the designs of `approved` approved."""
    folder = world.root / "props/work/checks/prepare"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "remake.json").write_text(json.dumps({
        "made_at": "2026-10-20T11:19:22+00:00",
        "priced_on": priced_on or {**local.priced_here(), "uncommitted": False},
        "takes": [take("alpha", "bought"), take("alpha", "bought"), take("alpha", "predicted gap")],
        "layers": {"closeup": {"takes": 2, "price": {"likely_euros": 10.0, "high_euros": 12.0}},
                   "likeness-calibration": {"takes": 2, "price": {"likely_euros": None, "high_euros": None}}},
        "totals": {"likely_euros": 10.0, "high_euros": 12.0, "unpriced": ["likeness-calibration"]},
        "eta": {"likely_minutes": None, "high_minutes": None, "at_least_minutes": 30.0, "path": [],
                "unknown": [{"node": "closeup"}, {"node": "pixal"}]}, "design": a_design(approved),
        **({"inventory": inventory} if inventory else {})}))


def a_month(monkeypatch, **more):
    """The month's spend as the store's machine read it: the cloud bill known, the model bill only partly counted (no
    figure), the environment's one stop line at EUR 250."""
    lines = [CostLine(source="cloud", label="Cloud compute", euros=12.5),
             CostLine(source="models", label="Model calls", euros=0.0, partial=True)]
    monkeypatch.setattr(actions, "spend", lambda: Spend(ceiling=250.0, month="2026-10", lines=lines, **more))


MONTH = Spend(spent=120.0, reserved=30.0, ceiling=900.0, world="world1", month="2026-10", days=[
    {"day": "2026-10-19", "cloud": 4.5, "models": 0.0}, {"day": "2026-10-20", "cloud": 1.25, "models": 0.4}], lines=[
    CostLine(source="cloud", label="Cloud compute", euros=2118.87, origin="the cloud bill"),
    CostLine(source="models", label="Model calls", euros=None, partial=True, origin="no rows yet")])


@pytest.fixture
def month_read():
    """The routes read the month through their FastAPI dependency: MONTH in its place."""
    from score.dashboard.site.asgi import inner
    inner.dependency_overrides[actions.spend] = lambda: MONTH
    yield MONTH
    inner.dependency_overrides.clear()


@pytest.fixture
def cockpit(world, read, settings, tmp_path):
    """The fixture environment with alpha's gaps priced (the close-up on the prop route, settle off it and measured,
    the sound guessed), prepare's record, and the basket made."""
    items = a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world, nodes={"closeup@alpha": {**MEASURED, "basis": "per unit × forecast"},
                                "settle@alpha": SETTLE, "sound@alpha": {
                                    "likely_euros": None, "high_euros": None, "guess_euros": 1.0,
                                    "basis": "not measured yet", "likely_minutes": None, "high_minutes": None}},
                  eta={"likely_minutes": None, "high_minutes": None, "at_least_minutes": 20.0,
                       "unknown": [{"node": "sound@alpha"}]})
    a_remake(world)
    world.source.refresh()
    world.items = items
    return world


# === who may see and act ==============================================================================================

PAGES = ["/", "/place/alpha/", "/place/beta/", "/place/alpha/step/closeup/", "/place/beta/step/assembly/",
         "/world/step/terrain/", "/basket/", "/buy/", "/stats/", "/runs/", "/requests/", "/picks/alpha", "/view/alpha"]
POSTS = ["/place/alpha/step/closeup/request/", "/place/alpha/step/closeup/decide/", "/place/alpha/step/closeup/queue/",
         "/basket/change/", "/refresh/", "/freshness/"]


def test_every_page_answers_the_owner_and_sends_a_stranger_to_sign_in(world):
    """Break: pages/views.py `place_page` raises for beta."""
    owner = signed_in()
    for page in PAGES:
        assert owner.get(page).status_code == 200, page
        answer = Client().get(page)
        assert answer.status_code == 302 and answer["Location"].startswith("/login/"), page


def test_every_post_needs_its_csrf_token_and_back_stays_on_this_site(world):
    """Break: site/settings.py drops CsrfViewMiddleware."""
    user = get_user_model().objects.create_user("joey", password="a long enough password")
    guarded = Client(enforce_csrf_checks=True)
    guarded.force_login(user)
    for page in POSTS:
        assert guarded.post(page, {"words": "x"}).status_code == 403, page
    owner = signed_in()
    for back in ("https://evil.example/", "//evil.example/", "javascript:alert(1)"):
        answer = owner.post("/refresh/", {"back": back})
        assert answer.status_code == 302 and answer["Location"] == "/", back
    assert owner.post("/refresh/", {"back": "/place/alpha/"})["Location"] == "/place/alpha/"


def test_node_ids_stay_inside_the_details_fold(world, read):
    """Owner rule (a wording check): node ids only inside details.ids, on the screens and the 3D viewer's page. Break:
    templates/pages/step.html prints `{{ detail.node }}` beside each read."""
    copy = world.root / "web" / "alpha"
    copy.mkdir(parents=True)
    (copy / "alpha.json").write_text(json.dumps({
        "place": "alpha", "from_output": world.outputs["assembly@alpha"], "made_at": "2026-10-18T12:00:00Z",
        "objects": [{"name": "Lamp", "layer": "light", "low": [0, 0, 0], "high": [1, 1, 1]}], "bytes": 10,
        "light_bytes": 5, "triangles": 12}))
    owner = signed_in()
    for page in [*PAGES[:6], "/view/alpha"]:
        found = NODE.search(outside_details(owner.get(page).content.decode()))
        assert found is None, (page, found and found.group(0))


def test_the_owner_decides_a_waiting_output_and_anyone_else_is_refused(world):
    """A worse output needs his reason; a guest sees no action and is refused. Break: pages/actions.py `decide` sends
    `worse_reason or 'none'` (a reason he never gave)."""
    owner = signed_in()
    waiting = world.outputs["closeup@alpha waiting"]
    owner.post("/place/alpha/step/closeup/decide/", {"decision": "accept", "output": waiting})
    assert world.store.accepted("closeup@alpha") != waiting  # worse, no reason: not taken
    owner.post("/place/alpha/step/closeup/decide/", {"decision": "accept", "output": waiting,
                                                     "worse_reason": "one fault is fine here"})
    assert world.store.accepted("closeup@alpha") == waiting
    assert world.store.current_accept("closeup@alpha")["by"] == "joey"
    guest = signed_in("guest")
    assert "Accept this output" not in guest.get("/place/alpha/step/closeup/").content.decode()
    assert guest.post("/place/alpha/step/closeup/decide/").status_code == 403


def test_a_change_request_lands_in_the_inbox_and_queue_this_or_next_adds_the_right_step(world, settings):
    """Break: pages/views.py `step_queue` queues the step itself for "next"."""
    from score.dashboard.pages.models import BasketItem, ChangeRequest
    owner = signed_in()
    assert owner.post("/place/alpha/step/closeup/request/", {"words": "the lamp is too red", "output": "x"}
                      ).status_code == 302
    change = ChangeRequest.objects.get()
    assert change.node == "closeup@alpha" and change.words == "the lamp is too red"
    assert (settings.SCORE_HOME / "inbox" / f"{change.pk}.json").is_file()
    owner.post("/place/alpha/step/plan/queue/", {"which": "this"})
    owner.post("/place/alpha/step/scene-record/queue/", {"which": "next"})
    queued = {(item.place, item.stage) for item in BasketItem.objects.all()}
    assert queued == {("alpha", "plan"), ("alpha", "assembly")}  # the stage table: scene-record, then assembly


# === nothing advances unseen ==========================================================================================

PAID = "demo-film@alpha"  # reads assembly@alpha and complete@alpha, both accepted in the fixture environment


def ready_plan(buys):
    body = {"groups": [{"places": ["alpha"], "stages": ["demo-film"], "missing": [], "buys": buys, "refusal": None,
                        "to_run": {}, "blocked": {}}], "buys": buys, "jobs": 8, "rebuys": 0.0, "nodes": [],
            "money": {"high": 13.67, "likely": 13.31, "spent": 100.0, "reserved": 10.0, "ceiling": 250.0,
                      "room": 140.0, "note": ""}, "time": {"likely_minutes": 10, "high_minutes": 20}}
    return Plan.objects.create(basket_hash="h", made_by="joey", state="ready", body=body, finished=timezone.now())


def test_a_paid_launch_waits_until_the_owner_advanced_what_it_reads(world):
    """Only the owner advances; a launch reading assembly and complete is refused until both are. Break: pages/seen.py
    `unseen_reads` holds nothing back (`if False:`)."""
    assert signed_in("guest").post("/place/alpha/step/assembly/advance/", {"output": "x"}).status_code == 403
    plan = ready_plan([{"node": PAID, "euros": 5.0, "why": "never ran", "again": False}])
    assert set(actions.unseen(plan)) == {(PAID, "assembly@alpha"), (PAID, "complete@alpha")}
    refused = actions.launch_refusals(get_user_model()(username="joey"), plan, True, "")
    assert any(why.startswith("not seen by owner") for why in refused)
    owner = signed_in()
    for stage in ("assembly", "complete"):
        assert owner.post(f"/place/alpha/step/{stage}/advance/", {"output": world.outputs[f"{stage}@alpha"]}
                          ).status_code == 302
    assert seen.advanced("assembly@alpha", world.outputs["assembly@alpha"]) and actions.unseen(plan) == []


class PaidFilm(FakeBackend):
    """The fake backend buying the film as well as the close-up."""

    def plan(self, group):
        planned = FakeBackend.plan(self, group)
        planned.buys += [{"node": f"demo-film@{place}", "euros": 5.0, "why": "never ran", "again": False}
                         for place in group.places if "demo-film" in group.stages]
        return planned


def test_a_hosted_advance_is_queued_and_the_stores_machine_applies_only_the_owners(world, settings):
    """Hosted, the click queues; on the store's machine a launch is refused until his advances are applied, and someone
    else's advance is refused. Break: sync/applying.py `apply_advance` skips its `from_owner` check."""
    settings.SCORE_LEDGER_FILES = [world.ledger]
    launch = {"kind": "launch", "user": "joey", "payload": {"items": [{"place": "alpha", "stage": "demo-film"}]}}
    refused = applying.apply(launch, world.source, PaidFilm())
    assert refused.state == "refused" and "not seen by owner" in refused.detail, refused.detail
    other = applying.apply({"kind": "advance", "user": "mallory", "payload": {
        "node": "assembly@alpha", "output": world.outputs["assembly@alpha"]}}, world.source)
    assert other.state == "refused" and not seen.advanced("assembly@alpha", world.outputs["assembly@alpha"])
    for node in ("assembly@alpha", "complete@alpha"):
        applied = applying.apply({"kind": "advance", "user": "joey", "payload": {
            "node": node, "output": world.outputs[node]}}, world.source)
        assert applied.state == "done", applied.detail
    assert applying.apply(launch, world.source, PaidFilm()).state == "running"
    settings.SCORE_MODE = "hosted"
    signed_in().post("/place/beta/step/assembly/advance/", {"output": world.outputs["assembly@beta"]})
    assert SyncRequest.objects.get(kind="advance").payload == {"node": "assembly@beta",
                                                               "output": world.outputs["assembly@beta"]}


# === numbers, not prose ===============================================================================================

SCREENS = ["/", "/places/", "/environments/world1/", "/place/alpha/", "/buy/", "/stats/", "/library/"]


def test_every_screen_shows_numbers_not_prose_and_sets_no_stop(world, settings, tmp_path, monkeypatch):
    """Owner rules (wording checks, #42, 2026-10-20): at most WORD_BUDGET words outside data, no traceback, no stop or
    month figure set from the cockpit. Break: templates/pages/stats.html gains a paragraph of 54 plain words."""
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    world.source.refresh()
    a_month(monkeypatch, paid_refused="the month's books are lost")
    owner = signed_in()
    for page in SCREENS:
        html = owner.get(page).content.decode()
        words = prose(html)
        assert len(words) <= WORD_BUDGET, (page, len(words), words)
        assert "Traceback" not in html and "/api/money/stop" not in html and "/api/money/month" not in html, page


# === the runner's prices, summed and never made =======================================================================

def test_the_runners_prices_are_summed_each_basis_apart_and_a_guess_is_never_measured():
    """By hand: three measured nodes of EUR 2-3 each in their own basis; guesses 1.0 + 1.5 apart; the film with neither
    unknown; 3 of 6 nodes measured. Break: state/gaps.py `money_of` counts the guessed nodes as measured."""
    from score.dashboard.pages import cockpit
    from score.dashboard.state import gaps
    from score.dashboard.state.models import GapsPrice
    price = GapsPrice(made_at="2026-10-19T20:00:00+00:00", nodes={
        "pixal@alpha": {**MEASURED, "basis": "measured runs"},
        "bake@alpha": {**MEASURED, "basis": "per unit × counted"},
        "lists@alpha": {**FORECAST},
        "sound@alpha": GUESSED, "sound@beta": {**GUESSED, "guess_euros": 1.5},
        "film@alpha": {**GUESSED, "guess_euros": None, "guess_from": None}})
    sums = gaps.summed(price.nodes)
    assert [(entry["basis"], entry["likely"], entry["high"], entry["nodes"]) for entry in sums["bases"]] == [
        ("measured runs", 2.0, 3.0, 1), ("per unit × counted", 2.0, 3.0, 1), ("per unit × forecast", 2.0, 3.0, 1)]
    assert sums["guessed"]["euros"] == 2.5 and sums["guessed"]["nodes"] == 2 and sums["unknown"] == ["film@alpha"]
    assert cockpit.measured_prices(price) == (3, 6)


def test_a_lost_input_read_by_two_places_and_the_world_is_one_gap(world):
    """One lost seed read by alpha, beta and the environment, plus one lost take at the world: 2 lost inputs, not 4.
    Break: state/local.py `gaps_total` drops `lost_once`."""
    lost = {"id": "place:lost:earth-seed:usd-r3", "rule": "place", "prim": None, "kind": None,
            "sentence": "lost input usd-r3", "picture": None, "row": None, "gates": [], "source": "inputs",
            "node": None, "work": "earth seed lost", "placed": None, "low": None, "high": None}
    taken = dict(lost, id="place:lost:pixal:pliers-pf", sentence="lost input pliers-pf", work="take lost")
    for place, outputs, found in (("alpha", {"assembly@alpha": world.outputs["assembly@alpha"]}, [lost]),
                                  ("beta", {"assembly@beta": world.outputs["assembly@beta"]}, [lost]),
                                  ("world", {}, [lost, taken])):
        folder = world.root / "props/work/checks/gaps" / place
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "findings.json").write_text(json.dumps({"place": place, "outputs": outputs, "findings": found}))
    total = world.source.gaps_total()
    assert total.counts == {"lost": 2} and total.unfillable == ["earth seed lost", "take lost"], total


def test_a_standalone_checks_findings_stand_only_while_what_they_judged_is_accepted(world, settings, tmp_path):
    """Gaps are not repeated among the check findings; a library finding over beta's accepted assembly stands, over
    another output it is not read. Break: state/local.py `check_findings` reads findings.json whole instead of
    `current_findings`."""
    a_gaps_finding(world, settings, tmp_path)
    assert [finding.check for finding in world.source.check_findings("alpha")] == []
    assert [gap.id for gap in world.source.gaps("alpha")][:1] == ["missing:lamp_1"]
    folder = world.root / "props/work/checks/library/beta"
    (folder / "marks").mkdir(parents=True, exist_ok=True)
    (folder / "marks/beta-0.png").write_bytes(fixture.picture((200, 60, 40)))

    def judged(output):
        (folder / "findings.json").write_text(json.dumps({"place": "beta", "outputs": {"assembly@beta": output},
            "findings": [{"rule": "finish not from the library", "prim": "/beta/Objects/crate_1",
                          "sentence": "3 models (crate) finish not from the library", "picture": "marks/beta-0.png"}]}))
    judged(world.outputs["assembly@beta"])
    assert [finding.rule for finding in world.source.check_findings("beta")] == ["finish not from the library"]
    judged("0" * 64)
    assert world.source.check_findings("beta") == []


def test_a_stale_planless_or_other_codes_price_shows_no_remake_figure(world, settings, tmp_path):
    """A price made on another commit, other per-unit prices, uncommitted code or none at all gives no figure, the why
    as hover text. Break: state/local.py `price_stale` ignores `code_moved`."""
    from score.dashboard.pages import cockpit, views
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    world.source.refresh()
    assert cockpit.remake(views.batch_of(world.source.world_state()))["why"] == "prepare has not run"
    here = local.priced_here()
    for priced_on, said in (({**here, "commit": "0" * 40, "uncommitted": False}, "the code moved"),
                            ({**here, "per_unit_sha256": "0" * 64, "uncommitted": False}, "per-unit prices"),
                            ({**here, "uncommitted": True}, "code not committed"), (None, "before the price")):
        a_gaps_price(world, priced_on=priced_on)
        world.source.refresh()
        remake = cockpit.remake(views.batch_of(world.source.world_state()))
        assert remake["low"] is None and said in remake["why"], (said, remake)
        assert cockpit.measured_prices(world.source.gaps_price()) == (None, None)
    assert said in unescape(signed_in().get("/places/").content.decode())


def test_a_gaps_check_run_again_puts_the_price_out_of_date_at_once(world, settings, tmp_path):
    """Not after the 60 s index: the findings newer than the price make it stale on the next read. Break: state/local.py
    `gaps_price` remembers its read without `gaps_written()` in the key."""
    from score.dashboard.pages import cockpit as numbers
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    world.source.refresh()
    assert numbers.measured_prices(world.source.gaps_price()) == (1, 2)
    findings = world.root / "props/work/checks/gaps/alpha/findings.json"
    price = world.root / "props/work/checks/gaps-price/world1.json"
    findings.write_text(findings.read_text())
    later = price.stat().st_mtime + 2
    os.utime(findings, (later, later))
    assert numbers.measured_prices(world.source.gaps_price()) == (None, None)
    assert "the gaps check ran again at 1 scene since the price was made" in unescape(
        signed_in().get("/places/").content.decode())


def test_a_step_two_places_share_is_in_both_rows_and_in_neither_places_own(world, settings, tmp_path):
    """The ground (guessed EUR 1) in both chains: alpha's money 1 (sound) + 1 (ground), beta's 1; own: alpha's sound
    only. Break: state/gaps.py `own_sum` keeps nodes another place's chain also has (`reach[node] == 1` dropped)."""
    from score.dashboard.state import gaps
    a_gaps_finding(world, settings, tmp_path)
    folder = world.root / "props/work/checks/gaps/beta"
    folder.mkdir(parents=True, exist_ok=True)
    lamp = {"id": "missing:lamp_1", "rule": "missing", "kind": "generate",
            "sentence": "a lamp: nothing made for it yet", "picture": None, "row": "lamp", "gates": [],
            "source": "inventory", "node": "closeup@beta", "work": None, "placed": "spot",
            "prim": "/beta/Gaps/lamp_1", "low": [0, 0, 0], "high": [1, 1, 1]}
    (folder / "findings.json").write_text(json.dumps({"place": "beta", "outputs": {
        "assembly@beta": world.outputs["assembly@beta"]}, "findings": [lamp]}))
    a_gaps_price(world, nodes={"closeup@alpha": FORECAST, "sound@alpha": GUESSED, "terrain": GUESSED,
                                "closeup@beta": FORECAST},
                 chains={"alpha": {"closeup@alpha": ["closeup@alpha", "complete@alpha", "sound@alpha", "terrain"],
                                   "complete@alpha": ["complete@alpha", "sound@alpha", "terrain"]},
                         "beta": {"closeup@beta": ["closeup@beta", "terrain"]}},
                 gaps={"alpha": {}, "beta": {}})
    world.source.refresh()
    details = {place: world.source.gaps(place) for place in ("alpha", "beta")}
    rows = {row["place"]: row for row in gaps.per_place(world.source.gaps_price(), details)}
    assert (rows["alpha"]["money"]["guessed"], rows["beta"]["money"]["guessed"]) == (2.0, 1.0)
    assert (rows["alpha"]["own"]["guessed"], rows["beta"]["own"]["guessed"]) == (1.0, 0)


def test_a_place_never_checked_has_no_price_not_nothing_to_pay():
    """Break: state/gaps.py `place_row` sums the money of a place never checked."""
    from score.dashboard.state import gaps
    price = types.SimpleNamespace(stale=None, not_checked=["gamma"], not_current=[], chains={}, nodes={})
    row = gaps.place_row("gamma", [], price)
    assert row["money"] is None and row["rank"] == len(gaps.KINDS) + 1


def test_the_plan_goes_through_the_export_whole(world, settings, tmp_path):
    """The runner's milestones reach the hosted cockpit unchanged. Break: state/local.py `gaps_price` leaves
    `milestones` out of the GapsPrice."""
    milestones = [{"key": "ground", "title": "The ground", "stages": [{"stage": "terrain", "nodes": 1, "paid": 1}],
                   "nodes": 1, "places": 0, "paid": ["terrain"], "likely_euros": 0, "high_euros": 0, "measured": 0,
                   "set": {"euros": 6.0, "nodes": 1, "from": []}, "unknown": [], "owner": ["the month's books"],
                   "reads": []},
                  {"key": "approval", "title": "Your approval of the final video", "owner": ["you approve it"]}]
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world, milestones=milestones)
    world.source.refresh()
    building.build(world.source, tmp_path / "export", "2026-10-20T09:00:00+00:00", 50, Spend(), world.root)
    assert ExportedSource(tmp_path / "export").world_state().gaps_price.milestones == milestones


def test_every_place_and_lost_item_has_plain_words():
    """Break: state/plain.py `lost_item` splits at the last colon."""
    from score.dashboard.pages import present
    assert plain.place_words("old_station") == "the old station" and present.place_title("old_station") == "Old station"
    assert plain.lost_item("place:lost:earth-seed:usd-r3/flat:x") == "usd-r3/flat:x"
    assert plain.lost_item("place:lost:data:surfaces/launch.json:bake entry far_rocket_1") == (
        "surfaces/launch.json:bake entry far_rocket_1")


def test_keys_outside_the_index_walk_only_their_folder_and_match_the_stores_own_answer(tmp_path):
    """A prefix outside the index's areas: "concepts/cock" holds cock.json and both cockpit folders, a .partial is never
    a key. Break: state/index.py `scoped` keeps only keys one folder below the prefix."""
    from score.dashboard.state.index import scoped
    from score.store import runtime_store
    store = runtime_store.FolderStore(tmp_path)
    for key in ("concepts/cockpit/draws/1.json", "concepts/cockpit2/draws/2.json", "concepts/cock.json",
                "plans/cockpit/a.json", "concepts/cockpit/draws/3.json.partial"):
        (tmp_path / key).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / key).write_text("{}")
    assert sorted(scoped(str(tmp_path), "concepts/cock")) == [
        "concepts/cock.json", "concepts/cockpit/draws/1.json", "concepts/cockpit2/draws/2.json"]
    for prefix in ("concepts/cockpit/", "concepts/", "concepts/cockpit/draws/", "nothing/here/"):
        assert scoped(str(tmp_path), prefix) == store.keys(prefix), prefix


# === the Environment, Place and Stats screens =========================================================================

def test_the_environment_tiles_carry_each_places_worst_gap_and_its_concept_and_the_top_bar_the_buys_figure(
        world, settings, tmp_path, monkeypatch, read):
    """alpha: 4 gaps, worst a route step, its concept; beta: none, its concept lost (never a render). The top bar: the
    cloud bill read, the model bill not ("at least"), no stop; what Buy buys, EUR 2-3, 0.2 h. Break: state/gaps.py
    `place_row` takes the mildest kind as the worst (KINDS reversed)."""
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world, eta={"likely_minutes": 95.0, "high_minutes": 130.0, "unknown": []})
    a_remake(world)
    world.source.refresh()
    a_month(monkeypatch)
    html = signed_in().get("/places/").content.decode()
    tiles = dict(re.findall(r'<a class="ptile" href="/place/(\w+)/"(.*?)</a>', html, re.S))
    assert set(tiles) == {"alpha", "beta"}
    assert "tone-gap-route" in tiles["alpha"] and "<b data-v>4</b>" in tiles["alpha"]
    assert "tone-done" in tiles["beta"] and "<b data-v>0</b>" in tiles["beta"]
    assert '<img src="/thumbs/' in tiles["alpha"] and "<img" not in tiles["beta"] and "concept missing" in tiles["beta"]
    top = html[html.index('<section class="topbar">'):html.index('<section class="ptiles"')]
    assert "<small>&ge;</small> <small>EUR</small> 12.50" in top and "not read: Model calls" in top
    assert "250" not in top and "stop" not in top  # owner rule: no stop shown
    assert "<small>EUR</small> 2&ndash;3<small>, about 0.2 h" in top


def test_the_environment_shows_outside_places_and_opens_each_to_what_sits_inside(world, settings, tmp_path, read):
    """alpha within beta within the yard: one yard tile summing alpha's gaps, then beta, then alpha alone; a shell
    holding no place shows not. Break: pages/cockpit.py `tiles` drops its `parent_of(...) == at` filter."""
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    (world.data / "places/within.json").write_text(json.dumps({
        "shells": {"yard": {"name": "Yard"}, "empty": {"name": "Empty"}},
        "within": {"beta": {"within": "yard"}, "alpha": {"within": "beta"}}}))
    owner = signed_in()

    def tiles(page):
        html = owner.get(page).content.decode()
        return re.findall(r'<a class="ptile" href="([^"]+)"(.*?)</a>', html, re.S), html
    found, _ = tiles("/places/")
    assert [href for href, _ in found] == ["/places/?in=yard"]
    assert "<b data-v>Beta, 1 room</b>" in found[0][1] and "tone-gap-route" in found[0][1]
    found, _ = tiles("/places/?in=yard")
    assert [href for href, _ in found] == ["/places/?in=beta"] and "<b data-v>+1</b>" in found[0][1]
    found, html = tiles("/places/?in=beta")
    assert [href for href, _ in found] == ["/place/alpha/"]
    assert "Outside" not in html  # owner rule (2026-10-20): never an "Outside" card beside its inside places
    head = html[html.index('<section class="phead"'):html.index('<section class="ptiles"')]
    assert '<h1 class="phead-name" data-v>Beta</h1>' in head and "tone-gap-route" in head
    assert owner.get("/places/?in=alpha").status_code == 404 and owner.get("/places/?in=empty").status_code == 404


def test_the_remake_on_every_page_is_what_buy_buys_and_its_time_a_floor_while_a_step_is_untimed(world, settings,
                                                                                                tmp_path):
    """Owner, 2026-10-24: Home said EUR 900-1031 while Buy said 162-314. The remake is batch.now: the basket's close-up,
    EUR 2-3, 10-20 min; with an untimed sound added, no hours, at least the close-up's. Break: pages/cockpit.py `remake`
    gives `at_least_hours` None."""
    from score.dashboard.pages import cockpit, views
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    a_remake(world)
    world.source.refresh()
    state = world.source.world_state()
    remake = cockpit.remake(views.batch_of(state))
    assert (remake["low"], remake["high"], remake["hours"], remake["unknown"]) == (2.0, 3.0, 0.2, 0)
    untimed = {"likely_euros": 1.0, "high_euros": 1.0, "basis": "per unit × forecast", "likely_minutes": None}
    items = [{**item, "nodes": {**item["nodes"], "sound@alpha": untimed}}
             for item in records.items(settings.SCORE_HOME / "proposals")]
    remake = cockpit.remake(screens.batch(state, items))
    assert remake["hours"] is None and (remake["at_least_hours"], remake["untimed"]) == (0.2, 1)


def test_stats_are_numbers_and_a_partial_bill_is_unknown_not_a_figure(world, settings, tmp_path, monkeypatch, read):
    """The cloud line 12.50; the model bill partly counted: AI calls and Total unknown; 1 of 2 steps measured; beta
    complete; the gaps by kind; the days from the bills' growth. No stop, no controls (owner rules). Break:
    pages/cockpit.py `known` reads a partial line's euros as a figure."""
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    world.source.refresh()
    a_month(monkeypatch, bill_days=[{"day": "2026-10-02", "cloud": 2.0, "models": 0.5},
                                    {"day": "2026-10-03", "cloud": 3.5, "models": 0.5}],
            days=[{"day": "2026-10-01", "cloud": 1.0, "models": 0.0}])
    html = signed_in().get("/stats/").content.decode()
    cards = dict(re.findall(r'<div class="num-label">(?:<i [^>]*></i>)?(?:<span data-v>)?([^<]+)(?:</span>)?</div>\s*'
                            r'<div class="num-value[^"]*"[^>]*>(.*?)</div>', html, re.S))
    assert cards["Cloud compute"] == "<small>EUR</small> 12.50"
    assert cards["AI calls"] == "unknown" and cards["Total"] == "unknown"
    assert cards["Steps with a measured price"] == "1<small> of 2</small>"
    assert cards["Places complete"] == "1<small> of 2</small>"
    assert [cards[label] for label in ("not made yet", "failing a check", "steps of the route still to do",
                                       "inputs lost")] == ["2", "1", "1", "0"]
    assert "<title>2026-10-01: EUR 1.00, at least" in html and "<title>2026-10-03: EUR 1.50</title>" in html
    assert "stop" not in html.lower()
    main = html[html.index("<main>"):]
    assert "<form" not in main and "<button" not in main


def test_spend_by_day_takes_the_bills_growth_else_the_ledger_else_a_gap():
    """By hand: the 3rd grew 5.5 - 4.0 = 1.5 whole; the 2nd's growth not known (no day before), its ledger 0.3; the 5th
    misses a line: none; a ledger 0 says nothing. Break: pages/cockpit.py `spend_by_day` takes a missing day before as
    0.0 (its whole reading as the day's growth)."""
    from score.dashboard.pages import cockpit
    bills = [{"day": "2026-10-02", "cloud": 2.0, "models": 0.5}, {"day": "2026-10-03", "cloud": 3.5, "models": 0.5},
             {"day": "2026-10-05", "cloud": 5.0, "models": None}]
    ledger = [{"day": "2026-10-01", "cloud": 1.0, "models": 0.0}, {"day": "2026-10-02", "cloud": 0.3, "models": 0.0},
              {"day": "2026-10-04", "cloud": 0.5, "models": 0.2}, {"day": "2026-10-06", "cloud": 0, "models": 0.0}]
    days = cockpit.spend_by_day(bills, ledger, "2026-10", datetime.date(2026, 10, 6))
    assert [(day["day"][-2:], day["euros"], day["whole"]) for day in days] == [
        ("01", 1.0, False), ("02", 0.3, False), ("03", 1.5, True), ("04", 0.7, False), ("05", None, False),
        ("06", None, False)]
    first = cockpit.spend_by_day([{"day": "2026-10-01", "cloud": 1.0, "models": 1.0}], [], "2026-10",
                                 datetime.date(2026, 10, 1))
    assert first == [{"day": "2026-10-01", "euros": 2.0, "whole": True}]
    chart = cockpit.day_chart(days)
    assert [tick["euros"] for tick in chart["ticks"]] == [0, 1.0, 2.0]
    assert len(chart["bars"]) == 4 and [gap["day"][-2:] for gap in chart["gaps"]] == ["05", "06"]
    assert cockpit.unplaced(10.0, days) == 6.5 and cockpit.unplaced(None, days) is None
    assert [cockpit.scale_top(value) for value in (0, 0.4, 3, 2119.85, 12408)] == [1.0, 1.0, 5, 2500, 20000]


def test_the_place_screen_draws_its_top_level_and_a_branch_loads_its_items_priced_with_his_one_action(
        world, settings, tmp_path, read):
    """Gaps (2 lamps) and Objects load as they open; the lamp's chain EUR 2-3 with a guessed sound "+"; its one action
    the waiting close-up's accept; the crate failing, its chain unknown; no action for a guest. Break: pages/cockpit.py
    `gap_action` drops its accept of a waiting output."""
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    world.source.refresh()
    owner = signed_in()
    html = owner.get("/place/alpha/").content.decode()
    assert re.search(r'<span class="node-label" data-v>Gaps</span><span class="node-count" data-v>2</span>', html)
    assert 'data-title="lamp"' not in html  # only the top level is drawn
    assert 'data-title="place:plan" data-state="route" data-tone="gap-route" data-price="unknown"' in html
    [lamp] = owner.get("/place/alpha/branch/?path=Gaps").json()
    assert (lamp["label"], lamp["count"], lamp["tone"]) == ("lamp", 2, "gap-missing")
    panel = lamp["panel"]
    assert (panel["state"], panel["gap"], panel["price"]) == ("missing", "missing:lamp_1", "EUR 2.00–3.00 +")
    assert (panel["action"], panel["action_label"]) == ("/api/decisions", "Accept")
    assert json.loads(panel["body"]) == {"node": "closeup@alpha", "output": world.outputs["closeup@alpha waiting"],
                                         "decision": "accept"}
    [crate] = owner.get("/place/alpha/branch/?path=Objects").json()
    assert crate["panel"]["state"] == "failing" and crate["panel"]["price"] == "unknown"
    assert "action" not in signed_in("guest").get("/place/alpha/branch/?path=Gaps").json()[0]["panel"]
    assert owner.get("/place/alpha/branch/?path=Nowhere").status_code == 404


PLAYWRIGHT = "playwright@1.62.1"  # viewer_look.py's: its Chromium (1234) is the one installed in ~/.cache/ms-playwright
SHELL = pathlib.Path.home() / ".cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64"


def chromium_runs():
    """Whether the headless Chromium is installed with every library it loads (LD_LIBRARY_PATH counted)."""
    shell = SHELL / "chrome-headless-shell"
    return shell.is_file() and "not found" not in subprocess.run(["ldd", str(shell)], capture_output=True,
                                                                 text=True).stdout


@pytest.mark.skipif(not chromium_runs(), reason="no headless Chromium that runs on this machine")
def test_a_click_on_a_scene_item_opens_its_panel_frames_it_and_posts_its_action(world, settings, tmp_path, read):
    """In a browser: a branch loaded once, the panel filled, the 3D view told to frame its gap, its Accept the owner's
    JSON request with the CSRF token, the panel a history step of its own. Break: static/pages/dash.js never posts the
    `{gap}` message to the viewer frame (`if (false)`)."""
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    world.source.refresh()
    owner = signed_in()
    branch = "/place/alpha/branch/?path=Gaps"
    job = tmp_path / "click.json"
    job.write_text(json.dumps({
        "page": "/place/alpha/", "html": owner.get("/place/alpha/").content.decode(), "branch": "Gaps",
        "item": "lamp", "branches": {branch: owner.get(branch).json()},
        "dash": str(REPO / "score/dashboard/pages/static/pages/dash.js")}))
    done = subprocess.run(["npx", "-y", "-p", PLAYWRIGHT, "node", str(pathlib.Path(__file__).with_name(
        "screens_click.mjs")), str(job)], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr[-3000:]
    found = json.loads(done.stdout.strip().splitlines()[-1])
    assert found["before"] == 0 and found["fetched"] == [branch]
    assert (found["open"], found["title"], found["state"], found["price"], found["button"]) == (
        True, "lamp", "missing", "EUR 2.00–3.00 +", "Accept")
    assert json.loads(found["framed"]) == {"gap": "missing:lamp_1"}
    assert found["back"] == {"open": False, "hash": ""} and found["forward"] == {"open": True, "title": "lamp"}
    assert found["reloaded"] == {"open": True, "title": "lamp", "steps": 3}
    assert found["posted"] == [{"url": "/api/decisions", "csrf": "token", "body": {
        "node": "closeup@alpha", "output": world.outputs["closeup@alpha waiting"], "decision": "accept"}}]


# === the 3D viewer ====================================================================================================

def test_the_viewer_frames_its_gaps_with_or_without_a_web_copy_and_names_each_layers_step(world, settings, tmp_path,
                                                                                        read):
    """No marks unless asked; asked, the three boxed gaps (the plan has no box); framing one names its row's line; the
    light layer links to its step; no copy: gaps alone, no viewer script. Break: pages/present.py `gap_marks` keeps
    findings with no box."""
    a_gaps_finding(world, settings, tmp_path)
    owner = signed_in()
    assert "view3d.js" not in owner.get("/view/alpha").content.decode()  # no copy yet
    framed = owner.get("/view/alpha?gaps=1&gap=missing:lamp_2").content.decode()
    given = view_data(framed)
    assert given["gap"] == "missing:lamp_2" and given["gaps_only"] is True
    lamp = next(mark for mark in given["marks"] if mark["id"] == "missing:lamp_2")
    assert lamp["sentence"].startswith("A lamp should be in the alpha")
    assert lamp["url"] == "/place/alpha/#gap-missing:lamp_1"
    (world.root / "web/alpha").mkdir(parents=True)
    (world.root / "web/alpha/alpha.json").write_text(json.dumps({
        "place": "alpha", "from_output": world.outputs["assembly@alpha"], "made_at": "2026-10-18T12:00:00Z",
        "objects": [{"name": "Lamp", "layer": "light", "low": [0, 0, 0], "high": [1, 1, 1]}], "bytes": 10,
        "light_bytes": 5, "triangles": 12}))
    assert view_data(owner.get("/view/alpha").content.decode())["marks"] == []
    given = view_data(owner.get("/view/alpha?gaps=1").content.decode())
    assert [{name: mark[name] for name in ("id", "low", "high", "kind")} for mark in given["marks"]] == [
        {"id": "missing:lamp_1", "low": [0, 0, 0], "high": [1, 1, 1], "kind": "missing"},
        {"id": "missing:lamp_2", "low": [2, 0, 0], "high": [3, 1, 1], "kind": "missing"},
        {"id": "gate:complete/painted:crate_1", "low": [4, 0, 0], "high": [5, 1, 1], "kind": "gate"}]
    assert given["gaps_only"] is False
    assert given["layers"]["light"] == {"label": "light sweep", "url": "/place/alpha/step/light/"}
    assert "edit" in given["order"] and "edit" not in given["layers"]  # the owner's own edits: no step made them
    assert signed_in("other").get("/view/nowhere").status_code == 404


def test_the_step_page_shows_its_own_picture_and_what_it_read(world):
    """Break: templates/pages/step.html drops the "reads:" caption."""
    detail = world.source.step_detail("alpha", "assembly")
    owner = signed_in()
    assert f'src="{detail.picture.url}"' in owner.get("/place/alpha/step/assembly/").content.decode()
    html = owner.get("/place/alpha/step/demo-film/").content.decode()
    assert "reads: OpenUSD stage" in html and "reads: completion" in html  # the stage table's reads of demo-film


# === screens' data (state/screens.py) =================================================================================

def test_the_environment_screen_sums_the_remake_its_eta_floor_and_each_places_tile(cockpit):
    """prepare's route EUR 10 (2 blocked, 1 predicted gap) plus settle off it (EUR 2-3), the sound unpriced: 12-15, 2
    unpriced; the month: 2118.87 cloud, models not read, against the stop 120 + 30. Break: state/screens.py
    `remake_money` leaves `rest` out of the whole."""
    found = screens.environment(cockpit.source, MONTH)
    remake = found["remake"]
    assert (remake["route"]["likely"], remake["route"]["blocked"], remake["route"]["predicted_gaps"]) == (10.0, 2, 1)
    assert remake["rest"] == {"likely": 2.0, "high": 3.0, "priced": 1, "unpriced": 1}
    assert (remake["likely"], remake["high"], remake["unpriced"]) == (12.0, 15.0, 2)
    assert remake["eta"] == {"likely_minutes": None, "high_minutes": None, "at_least_minutes": 30.0, "untimed": 3}
    assert found["money"] == {"month": "2026-10", "cloud": 2118.87, "models": None, "total": 2118.87,
                              "whole": False, "stop": 900.0, "against_stop": 150.0, "in_flight": 30.0,
                              "refused": False}
    alpha = next(place for place in found["places"] if place["place"] == "alpha")
    assert alpha["gaps"] == 4 and alpha["worst"] == "route" and alpha["takes"]["takes"] == 3
    assert [bool(place["picture"]) for place in found["places"]] == [True, False]
    assert found["gaps"] == {"missing": 2, "gate": 1, "route": 1}
    world = cockpit.source.world_state()
    assert screens.picture_of(world, "alpha") == (f"/thumbs/{world.concepts['alpha'].sha}.jpg", "concept")
    assert screens.picture_of(world, "beta") == (None, None)  # lost: never a render instead


def test_before_any_design_is_approved_the_remake_is_an_estimate_that_buys_nothing(cockpit):
    """Owner, 2026-10-21: prepare's figure over the read inventories (1 of 2), its floor and unpriced layers, on the
    remake tile and Buy; never buyable; stale on uncommitted code. Break: state/screens.py `estimate` keeps its figure
    while stale (`current = True`)."""
    a_remake(cockpit, approved=(), inventory={"read": ["alpha"], "waiting": ["beta"]})
    cockpit.source.refresh()
    assert screens.remake_money(cockpit.source.world_state())["estimate"] == {
        "likely": 10.0, "high": 12.0, "unpriced": ["likeness-calibration"], "places": 1, "waiting": 1,
        "eta": {"likely_minutes": None, "high_minutes": None, "at_least_minutes": 30.0, "untimed": 2}, "stale": None}
    owner = signed_in()
    for page, start, end in (("/buy/", ">After design<", '<ul class="buy-layers buy-design">'),
                             ("/places/", ">remake<", "Review and buy")):
        html = owner.get(page).content.decode()
        tile = html[html.index(start):html.index(end)]
        assert "<small>EUR</small> 10&ndash;12<small>, " in tile
        assert "1 <small>of</small> 2 <small>scenes</small>" in tile
    assert 'data-url="/buy/yes/"' not in owner.get("/buy/").content.decode()
    a_remake(cockpit, approved=(), inventory={"read": ["alpha"], "waiting": ["beta"]},
             priced_on={"commit": "6cdf4d40", "uncommitted": True, "per_unit_sha256": "x"})
    cockpit.source.refresh()
    stale = screens.remake_money(cockpit.source.world_state())["estimate"]
    assert stale["likely"] is None and stale["stale"] == "it was made on code not committed"


def test_a_remake_priced_on_code_not_committed_shows_unknown_and_buy_disabled(cockpit):
    """Never 0.00 stale. Break: state/screens.py `remake_money` drops prepare's `stale`."""
    a_remake(cockpit, priced_on={"commit": "6cdf4d40", "uncommitted": True, "per_unit_sha256": "x"})
    cockpit.source.refresh()
    assert screens.remake_money(cockpit.source.world_state())["stale"] == ["it was made on code not committed"]
    html = signed_in().get("/buy/").content.decode()
    after = html[html.index(">Buy now<"):html.index('<ul class="buy-layers buy-design">')]
    assert after.count(">unknown</span>") == 1 and "&ndash;" not in after
    assert 'data-url="/buy/yes/"' not in html and 'disabled title="it was made on code not committed' in after


def test_the_place_screen_lists_its_gaps_and_prices_each_chain_once(cockpit):
    """The close-up's chain: its EUR 2-3 plus the guessed sound (1 unpriced); complete's: free plus the sound. Break:
    state/screens.py `chain_price` prices every node of the record, not the chain's."""
    found = screens.place(cockpit.source, "alpha", None)
    assert [item["kind"] for item in found["items"]] == ["missing", "missing", "gate", "route"]
    assert found["items"][0]["prim"] == "/alpha/Gaps/lamp_1" and found["items"][0]["node"] == "closeup@alpha"
    assert found["prices"]["closeup@alpha"] == {"likely": 2.0, "high": 3.0, "priced": 1, "unpriced": 1}
    assert found["prices"]["complete@alpha"] == {"likely": 0, "high": 0, "priced": 0, "unpriced": 1}
    assert found["gaps"] == {"missing": 2, "gate": 1, "route": 1} and not found["price_stale"]


def test_buy_totals_the_chosen_items_and_a_choice_on_another_version_is_none(cockpit, month_read):
    """Stop = high 3 + 10% = 3.3; no choice, no stop. Break: state/screens.py `buy` sets the stop at the high, without
    BUFFER."""
    item = cockpit.items[0]
    assert screens.buy(cockpit.items, {}, MONTH)["stop"] is None
    found = screens.buy(cockpit.items, {item["id"]: "buy"}, MONTH)
    assert found["chosen"] == 1 and (found["total"]["likely"], found["total"]["high"], found["stop"]) == (2.0, 3.0, 3.3)
    assert found["eta"] == {"likely_minutes": 10.0, "high_minutes": 20.0, "untimed": 0}
    stored = records.items(cockpit.root / "home" / "proposals")[0]
    BasketChoice.objects.create(item=stored["id"], version="0" * 16, choice="buy", by="joey")
    shown = api().get("/api/screens/buy").json()
    assert shown["chosen"] == 0 and shown["items"][0]["choice"] is None


def test_the_batch_is_what_buy_buys_and_what_waits_is_counted_with_no_euros(cockpit):
    """The basket buys closeup@alpha now at its own price (2-3, not prepare's share); settle and the sound wait, counted
    by why with no euros; a lost input buys nothing. Break: state/screens.py `now_items` keeps items waiting on a
    missing input."""
    found = screens.batch(cockpit.source.world_state(), cockpit.items)
    models, motion, sound = found["layers"]
    assert (models["make"], models["waiting"], models["models"]) == (2, 0, 2)
    assert (models["likely"], models["high"]) == (2.0, 3.0)
    assert (motion["waiting"], motion["why"], motion["likely"]) == (1, {"an earlier step first": 1}, 0.0)
    assert (sound["waiting"], sound["likely"], sound["guessed"]) == (1, 0.0, 0.0)
    assert (found["total"]["likely"], found["total"]["high"]) == (found["now"]["likely"], found["now"]["high"]) == (
        2.0, 3.0)
    assert (found["now"]["steps"], found["now"]["places"], found["now"]["stop"]) == (1, ["alpha"], 3.3)
    assert found["waiting"] == {"steps": 2, "why": ["an earlier step first"]}
    blocked = [{**item, "missing": ["a lost input"]} for item in cockpit.items]
    waits = screens.batch(cockpit.source.world_state(), blocked)
    assert waits["now"]["steps"] == 0 and waits["now"]["stop"] is None
    assert waits["layers"][0]["why"]["lost concept views"] == 2


def test_the_buy_line_is_priced_as_its_checkout_records_it_and_refused_on_a_basket_older_than_the_price(cockpit):
    """With two guessed steps (1.5 each) and an unpriced rough model: likely 2, high 3 + 3 = 6, stop 6.6; no ETA, 3
    untimed kinds; refused while the basket is older than the price or of unknown age. Break: state/screens.py
    `buy_refusals` never says the basket is older than the price."""
    from score.dashboard.checkout import pricing
    guessed = {"likely_euros": None, "high_euros": None, "guess_euros": 1.5, "basis": "not measured yet",
               "likely_minutes": None, "high_minutes": None}
    unpriced = {"likely_euros": None, "high_euros": None, "basis": "not measured yet"}
    items = [{**item, "nodes": {**item["nodes"], "sound@alpha": guessed, "light-passes@alpha": guessed,
                                 "rough-model@alpha": unpriced}} for item in cockpit.items]
    world = cockpit.source.world_state()
    found = screens.batch(world, items, "2099-01-01T00:00:00Z")
    now = found["now"]
    totals = pricing.totals(pricing.basket_prices(screens.now_items(items, screens.approved_places(world))))
    assert (now["likely"], now["high"], now["guessed"], now["guesses"]) == (2.0, 6.0, 3.0, 2)
    assert now["high"] == pricing.cleared_high(totals) and now["stop"] == 6.6
    assert now["no_price"] == {"models": 1}
    assert now["eta"]["likely_minutes"] is None and now["eta"]["untimed_kinds"] == {"rough model": 1,
                                                                                    "light renders": 1, "sound": 1}
    assert now["eta"]["at_least_minutes"] == 10.0 and now["eta"]["at_least_high_minutes"] == 20.0
    assert found["refused"] == []
    older = screens.batch(world, items, "2026-10-19T08:00:00Z")["refused"]
    assert len(older) == 1 and older[0].startswith("the basket (2026-10-19 08:00) is older than the price (")
    assert screens.batch(world, items)["refused"] == ["the basket's time is not known"]


def test_no_step_is_bought_at_a_place_whose_design_is_not_approved(cockpit):
    """Owner, 2026-10-20, "design decides inventory". Break: state/screens.py `now_items` drops `approved and
    for_approved(...)`."""
    a_remake(cockpit, approved=())
    cockpit.source.refresh()
    world = cockpit.source.world_state()
    found = screens.batch(world, cockpit.items)
    assert found["now"]["steps"] == 0 and found["now"]["stop"] is None and found["layers"] == []
    money = screens.remake_money(world)
    assert (money["likely"], money["approved"], money["in_design"]) == (None, 0, 2)
    assert screens.now_items(cockpit.items, ["beta"]) == []
    design = screens.design(cockpit.source, world)
    assert design["approved"] == [] and [row["design"]["plan"] for row in design["places"]] == ["remake", "remake"]
    a_remake(cockpit, approved=("alpha",))
    cockpit.source.refresh()
    money = screens.remake_money(cockpit.source.world_state())
    assert (money["likely"], money["high"], money["in_design"]) == (12.0, 15.0, 1)
    assert money["eta"]["at_least_minutes"] is None  # the runner times the whole remake only


def test_buy_buys_the_people_line_with_the_places_whose_cast_reads_it():
    """Buy of 2026-10-24 refused "the run would also buy closeup@people". Break: state/screens.py `for_approved` ignores
    an item's `for`."""
    from score.dashboard.checkout import flow
    from score.dashboard.launch.backend import GroupPlan
    price = {"likely_euros": 1.0, "high_euros": 2.0, "runs": 1}

    def item(ident, places, nodes, held):
        return {"id": ident, "places": places, "nodes": {node: price for node in nodes}, "missing": [], "for": held}
    items = [item("alpha-settle", ["alpha"], ["settle@alpha"], ["alpha"]),
             item("beta-settle", ["beta"], ["settle@beta"], ["beta"]),
             item("people-base", ["people"], ["closeup@people", "people-dress-pilot-made"], ["alpha", "beta"]),
             item("environment-body-face", [], ["body-face-moon"], [])]
    bought = screens.now_items(items, ["alpha"])
    assert [found["id"] for found in bought] == ["alpha-settle", "people-base", "environment-body-face"]
    assert [found["id"] for found in screens.now_items(items, ["gamma"])] == ["environment-body-face"]
    plan = GroupPlan(missing=[], refusal=None, to_run={}, blocked={},
                     buys=[{"node": node, "why": "", "again": False}
                           for node in ("settle@alpha", "closeup@people", "people-dress-pilot-made", "body-face-moon")])
    assert flow.plan_refusals(types.SimpleNamespace(items=bought), [(None, plan)]) == []


def test_the_buy_counts_every_plant_of_the_design(cockpit):
    """Owner, 2026-10-24: every growing row is a plant, its count its objects; the planter its bed. By hand: greens on 4
    planters (1 crop row) and 3 palms: 2 rows, 4 objects, 4 beds; the desk no plant. Break: state/screens.py
    `plants_total` leaves `beds` out."""
    kept = cockpit.source.props_home / "design" / "inventory"
    kept.mkdir(parents=True, exist_ok=True)
    (kept / "alpha.json").write_text(json.dumps({"rows": [
        {"id": "planter", "noun": "planter", "count": 4}, {"id": "greens", "noun": "plants", "anchor": "on:planter"},
        {"id": "palm", "noun": "tree", "count": 3}, {"id": "desk", "noun": "desk"}]}))
    cockpit.source.refresh()
    world = cockpit.source.world_state()
    assert world.plants == {"alpha": {"rows": 2, "objects": 4, "crops": 1, "beds": 4}}
    assert screens.batch(world, cockpit.items)["plants"] == {"rows": 2, "objects": 4, "crops": 1, "beds": 4,
                                                            "places": ["alpha"]}
    world.plants = {}
    assert screens.batch(world, cockpit.items)["plants"] is None


def test_the_stats_count_measured_prices_gaps_and_places_complete(cockpit):
    """settle and the close-up measured, the sound not: 2 of 3. Break: state/screens.py `stats` counts every basis as
    measured."""
    found = screens.stats(cockpit.source, MONTH)
    assert found["prices"]["measured"] == 2 and found["prices"]["steps"] == 3
    assert found["days"][-1] == {"day": "2026-10-20", "cloud": 1.25, "models": 0.4}
    assert found["places"]["total"] == 2 and found["gaps"]["missing"] == 2


def test_every_screen_route_answers_json_and_the_remake_travels_in_the_export(cockpit, month_read):
    """Break: api/routes.py `place_screen` drops its unknown-place 404."""
    web = api()
    for path in ("environment", "place/alpha", "buy", "stats", "library"):
        assert web.get(f"/api/screens/{path}").status_code == 200, path
    assert web.get("/api/screens/place/nowhere").status_code == 404
    world = cockpit.source.world_state(MONTH)
    assert WorldState.model_validate_json(world.model_dump_json()).remake.counts["blocked"] == 2


def test_a_place_shows_no_numbers_until_its_inventory_is_read_from_its_locked_concept(drafting):
    """Owner, 2026-10-20 ("inventory can't exist" before the lock): drawing, no ring, its card opens its concept; once
    designed, numbers; findings older than the lock: check; another lock or an unlock: nothing counts. Break:
    state/screens.py `inventory_current` drops its sha equality."""
    from score.review import concepts
    world = drafting

    def alpha():
        world.source.refresh()
        return next(place for place in screens.environment(world.source, MONTH)["places"] if place["place"] == "alpha")
    assert (alpha()["design"], alpha()["progress"], alpha()["gaps"]) == ("draw", None, None)
    html = signed_in().get("/places/").content.decode()
    assert "data-v>0/3</b>" in html and 'class="ring' not in html
    assert 'href="/place/alpha/"' not in html and 'class="ptile" href="/concept/alpha/"' in html
    assert signed_in("joey2").get("/place/alpha/").status_code == 404
    fixture.designed(world.store, "alpha", fixture.concept_of(world.store, "alpha"), world.root / "props")
    shown = alpha()
    assert shown["design"] is None and shown["progress"]["needed"] > 0 and shown["gaps"] is not None
    findings = world.root / "props/work/checks/gaps/alpha/findings.json"
    findings.parent.mkdir(parents=True)
    findings.write_text("{}")
    os.utime(findings, (1760000000, 1760000000))  # checked before the lock
    assert alpha()["design"] == "check"
    findings.unlink()
    concepts.recorded(world.store, "concepts/alpha/picks/2026-10-20T10-00-00.json",
                      {"place": "alpha", "sha": "o" * 64, "by": "joey", "at": "2026-10-20T10:00:00+00:00"})
    shown = alpha()
    assert (shown["design"], shown["progress"], shown["gaps"]) == ("read", None, None)
    assert screens.place(world.source, "alpha", None)["items"] == []
    concepts.recorded(world.store, "concepts/alpha/picks/2026-10-20T11-00-00.json",
                      {"place": "alpha", "sha": None, "by": "joey", "at": "2026-10-20T11:00:00+00:00"})
    assert (alpha()["design"], alpha()["progress"]) == ("draw", None)


def test_a_withdrawn_library_place_is_no_3d_for_its_place_screen():
    """Owner, 2026-10-21. Break: state/screens.py `web3d_link` drops its withdrawn check."""
    no_copy = types.SimpleNamespace(web3d=lambda place: False)
    entry = types.SimpleNamespace(kind="place", entry_id="alpha", state="withdrawn",
                                  web3d=types.SimpleNamespace(sha="ab12"))
    shelf_of = types.SimpleNamespace(entries=lambda: [entry])
    assert screens.web3d_link(no_copy, "alpha", shelf_of) == (None, None)
    entry.state = "draft"
    assert screens.web3d_link(no_copy, "alpha", shelf_of) == ("/library-files/files/ab12", "library")


# === the Buy screen ===================================================================================================

def test_the_buy_screen_is_design_first_and_buys_only_approved_places_once_the_basket_is_current(
        world, settings, tmp_path, monkeypatch):
    """No design approved: no price, nothing to buy; alpha's approved: Buy disabled while the basket is older than the
    price, then the close-up EUR 2-3, stop 3.30, two steps waiting; a layer a line; the plants counted; a guest has no
    Buy and is refused; the Benchmarks item is not in the basket. Break: pages/basket.py `buy_yes` skips its owner
    check."""
    a_month(monkeypatch)
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world, nodes={"settle@alpha": SETTLE, "sound@alpha": {
        "likely_euros": None, "high_euros": None, "guess_euros": 1.0, "basis": "not measured yet"}},
        eta={"likely_minutes": None, "high_minutes": None, "at_least_minutes": 20.0, "unknown": [{"node": "sound"}]})
    a_remake(world, approved=())
    world.source.refresh()
    owner = signed_in()
    html = owner.get("/buy/").content.decode()
    top = html[html.index('<div class="topbar">'):html.index('<ul class="buy-layers buy-design">')]
    assert "0 <small>of</small> 2 <small>approved</small>" in top and "EUR" not in top
    assert 'data-url="/buy/yes/"' not in html
    a_remake(world, approved=("alpha",))
    world.source.refresh()
    top = owner.get("/buy/").content.decode().split('<ul class="buy-layers buy-design">')[0]
    assert re.search(r'<button type="button" class="primary big" disabled title="the basket \(2026-10-19 08:00\) is '
                     r'older than the price', top)
    from score import graph
    root = settings.SCORE_HOME / "proposals"
    records.put_index(root, {**records.index(root), "made_at": graph.now()})
    html = owner.get("/buy/").content.decode()
    buy_now = html.split('<ul class="buy-layers buy-design">')[0].split(">Buy now<")[1]
    assert '"batch": "now"' in html and "<small>EUR</small> 2.00&ndash;3.00" in buy_now
    assert "<small>stop EUR</small> 3.30" in buy_now and "+ 2 <small>steps wait</small>" in buy_now
    layers = re.findall(r'<span class="node-label" data-v>(\w+)</span><span class="buy-n" data-v>(\d+)</span>', html)
    assert layers == [("Models", "2"), ("Motion", "1"), ("Sound", "1")]
    assert not re.search(r"calibration|lost concept|<details", html)  # no step's own name
    assert owner.post("/buy/yes/", "{}", content_type="application/json").status_code == 422
    refused = owner.post("/buy/yes/", {"key": "a" * 32, "batch": "benchmarks"}, content_type="application/json")
    assert refused.status_code == 409 and refused.json()["detail"].startswith("refused")
    assert signed_in("guest").post("/buy/yes/", {"key": "a" * 32}, content_type="application/json").status_code == 403
    assert 'data-url="/buy/yes/"' not in signed_in("guest2").get("/buy/").content.decode()


def test_the_buy_screen_shows_the_books_buttons_only_while_needed_and_only_to_the_owner(world, monkeypatch):
    """Owner rule (2026-10-20): no Basket link; the model calls' figure button while that bill is not read; the
    read-back while paid work is refused. Break: pages/views.py gives `figure` True whatever the model bill."""
    a_month(monkeypatch)
    owner = signed_in()
    html = owner.get("/buy/").content.decode()
    assert 'href="/basket/"' not in html.split('<main')[-1] and "/api/money/read-back" not in html
    assert ">Model calls figure</button>" in html
    lines = [CostLine(source="cloud", label="Cloud compute", euros=12.5),
             CostLine(source="models", label="Model calls", euros=1030.0)]
    monkeypatch.setattr(actions, "spend", lambda: Spend(ceiling=250.0, month="2026-10", lines=lines))
    assert "/api/money/books-figure" not in owner.get("/buy/").content.decode()
    a_month(monkeypatch, paid_refused="the month's books are lost")
    html = owner.get("/buy/").content.decode()
    assert 'data-post="/api/money/read-back"' in html and 'data-post="/api/money/books-figure"' in html
    guest = signed_in("guest").get("/buy/").content.decode()
    assert "/api/money/read-back" not in guest and "/api/money/books-figure" not in guest


# === the basket =======================================================================================================

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
BASKET_GUESS = {"likely_euros": None, "high_euros": None, "guess_euros": 2.7, "likely_minutes": None,
                "high_minutes": None, "runs": 0, "cards": None}


def a_basket_place(root, place, found, picture=False):
    partial = root / f".{place}-partial"
    (partial / "inputs").mkdir(parents=True)
    if picture:
        (partial / "inputs" / "1.jpg").write_bytes(b"jpeg")
    records.put_place(root, partial, place, found)


@pytest.fixture
def basket(world, settings, tmp_path):
    """A made basket: alpha's pieces (measured, what changes, a picture it is made from), the environment's people
    body (never measured), and the ship's declared item with a question."""
    settings.SCORE_HOME = tmp_path / "home"
    root = settings.SCORE_HOME / "proposals"
    root.mkdir(parents=True)
    records.put_declared(root, "ship-room-concepts", SHIP)
    buys = [{"node": "closeup@alpha", "why": "code changed", "again": True, "price": MEASURED},
            {"node": "people-body-bram-work", "why": "never ran", "again": False, "price": BASKET_GUESS},
            {"node": "concept-views", "why": "files changed", "again": True, "price": MEASURED}]
    records.put_index(root, {"made_at": "2026-10-19T08:00:00Z",
                             "items": make.grouped(buys, {"closeup": "pieces"}, [], records.declared(root))})
    a_basket_place(root, "alpha", {"place": "alpha", "copy": {"triangles": 10}, "changes": CHANGES,
                                   "made": ["assembly"], "inputs": {"closeup@alpha": {
                                       "reads": [{"node": "plan@alpha", "how": records.MADE}],
                                       "files": [{"from": "plan@alpha", "how": records.MADE, "name": "props.png",
                                                  "kind": "picture", "file": "inputs/1.jpg"}]}}}, picture=True)
    a_basket_place(root, None, {"place": None, "inputs": {
        "people-body-bram-work": {"reads": [], "files": [
            {"from": "data", "how": None, "name": "brief: bram.txt", "kind": "text",
             "text": "Bram, the mechanic, in work clothes."}]},
        "concept-views": {"reads": [], "files": []}}})
    return root


def test_a_basket_item_says_what_changes_and_a_guess_is_never_a_price(basket):
    """Counted from CHANGES: 2 added, 1 taken out, 1 refinished; the measured price 2.00 to 3.00; the guess said as no
    price (owner rule, a wording check, 2018-10-18). Break: templates/pages/basket_item.html words the guess as "cost
    about EUR 2.70"."""
    page = signed_in().get("/basket/").content.decode()
    assert "2 objects added · 1 object taken out · 1 object refinished" in page and "at most 3.00" in page
    environment = signed_in("visitor").get("/basket/item/environment-people-body/").content.decode()
    assert "EUR 2.70, which is not a price" in environment and "Only the owner buys" in environment
    assert signed_in("other").get("/basket/item/nothing-here/").status_code == 404


def test_only_the_owner_buys_as_he_saw_it_and_his_answer_is_kept_where_agents_read_it(basket):
    """A choice on another version is not kept. Break: pages/basket.py `choose` skips its version check."""
    item = records.item(basket, "alpha-pieces")
    form = {"item": "alpha-pieces", "version": item["version"], "choice": "buy"}
    assert signed_in("visitor").post("/basket/choose/", form).status_code == 403 and not BasketChoice.objects.exists()
    owner = signed_in()
    owner.post("/basket/choose/", {**form, "version": "0" * 16})
    assert not BasketChoice.objects.exists()
    owner.post("/basket/choose/", form)
    assert BasketChoice.objects.get(item="alpha-pieces").choice == "buy"
    owner.post("/basket/answer/", {"item": "ship-room-concepts", "number": "1", "take": "recommended"})
    assert records.answers(basket)["ship-room-concepts"]["1"]["answer"] == "One deck, as in your cutaway picture."
    owner.post("/basket/answer/", {"item": "ship-room-concepts", "number": "1", "take": "own",
                                   "answer": "Two decks where they fit."})
    assert records.answers(basket)["ship-room-concepts"]["1"]["answer"] == "Two decks where they fit."
    assert signed_in("visitor").post("/basket/answer/", {"item": "ship-room-concepts", "number": "1",
                                                         "take": "recommended"}).status_code == 403


def test_hosted_an_answer_and_a_checkout_are_queued_for_the_stores_machine(basket, settings):
    """The answer is kept only once the store's machine applies the owner's; the checkout carries the items he saw.
    Break: sync/applying.py `apply_answer` skips its `from_owner` check."""
    from score.dashboard.pages import basket as page
    settings.SCORE_MODE = settings.HOSTED
    (basket.parent / "export" / "current").mkdir(parents=True)
    (basket.parent / "export" / "current" / "proposals").symlink_to(basket)
    owner = signed_in()
    owner.post("/basket/answer/", {"item": "ship-room-concepts", "number": "1", "take": "recommended"})
    queued = SyncRequest.objects.get(kind="answer")
    assert records.answers(basket) == {}
    item = records.item(basket, "alpha-pieces")
    owner.post("/basket/choose/", {"item": "alpha-pieces", "version": item["version"], "choice": "buy"})
    owner.post("/basket/checkout/", {"key": "a" * 32, "confirm": "yes"})
    assert SyncRequest.objects.get(kind="checkout").payload == {
        "key": "a" * 32, "items": [{"id": "alpha-pieces", "version": item["version"]}]}
    assert "waits for the store's machine" in page.last_checkout()
    settings.SCORE_MODE = settings.LOCAL
    BasketAnswer.objects.all().delete()
    assert applying.apply({"kind": "answer", "user": "mallory", "payload": queued.payload}, None).state == "refused"
    assert records.answers(basket) == {}
    done = applying.apply({"kind": "answer", "user": "joey", "payload": queued.payload}, None)
    assert done.state == "done" and records.answers(basket)["ship-room-concepts"]["1"]["by"] == "joey"


def test_the_viewer_outlines_what_a_basket_item_changes_on_each_side(basket, world):
    """After: the 2 added, the lamp and the floor; before: the removed lamp, the lamp, the floor. Break:
    pages/basket.py's marks put `removed` on the after side."""
    copy = world.source.web_copies / "alpha"
    copy.mkdir(parents=True, exist_ok=True)
    (copy / "alpha.json").write_text(json.dumps({"made_at": "2026-10-19T08:00:00Z", "objects": []}))
    after = view_data(signed_in().get("/view/alpha?item=alpha-pieces&embed=1").content.decode())
    assert after["base"] == "/basket-file/alpha/web3d/"
    assert sorted(mark["kind"] for mark in after["marks"]) == ["added", "added", "lamp", "refinished"]
    before = view_data(signed_in("other").get("/view/alpha?item=alpha-pieces&side=before").content.decode())
    assert before["base"] == "/web/alpha/" and sorted(mark["kind"] for mark in before["marks"]) == [
        "lamp", "refinished", "removed"]


# === the run monitor ==================================================================================================

RUN = "joey-1-1792840013"
TOTALS = {"likely_euros": 186.14, "high_euros": 327.24, "guessed_euros": 33.16, "likely_minutes": 121.5,
          "high_minutes": 305.3, "unmeasured": ["closeup@beta"]}
PLAN = {"groups": [{"places": ["alpha", "beta"], "to_run": {"terrain": "to run", "plan@alpha": "to run"},
                    "blocked": {"assembly@alpha": "waits", "assembly@beta": "waits"},
                    "buys": [{"node": "closeup@alpha"}, {"node": "closeup@beta"}]}]}


def heartbeat(at, done, running, queued, paid, euros):
    """One heartbeat line of a run's detached log, as the runner writes it."""
    return (f"heartbeat {at}: rows done {done}, running {running}, queued {queued}; this run's rows: paid runs open "
            f"{paid}, EUR {euros} in the ledger since the run started")


LOG = "\n".join([
    "paid rows this run would buy: 2, about EUR 8.33; re-buys of accepted outputs: 0, about EUR 0.00",
    "[cloud] 13:07:00 pool of 2 gpu-24gb, 1 cpu-16c-64gb opened for run {run} until 17:07; jobs start on the first "
    "warm card",
    heartbeat("2026-10-24T11:09:00+00:00", 0, 2, 4, 1, "0.00"),
    "terrain: made: pass, accepted automatically",
    "plan@alpha: fresh",
    heartbeat("2026-10-24T11:11:00+00:00", 2, 2, 2, 1, "1.20"),
    "closeup@beta: blocked: no card of gpu-24gb was had before the deadline: the takes are gaps; fault report "
    "/x/faults/closeup@beta.txt",
    "assembly@beta: not run: its line stopped at closeup@beta",
    heartbeat("2026-10-24T11:13:00+00:00", 4, 1, 1, 1, "3.21"), ""])


def a_pool(props):
    """The run's warm pool: two cards and a processor machine asked, one card warm and busy, the rest not in stock."""
    folder = props / "cloud" / "pools" / RUN
    (folder / "cards").mkdir(parents=True, exist_ok=True)
    (folder / "plan.json").write_text(json.dumps({"sizes": {"gpu-24gb": 2, "cpu-16c-64gb": 1},
                                                  "deadline": time.time() + 3600}))
    (folder / "cards" / "m-1.json").write_text(json.dumps({"id": "m-1", "class": "gpu-24gb", "for": "gpu-24gb",
                                                           "holder": 4242}))
    (folder / "collector.log").write_text("[cloud] 13:07:13 rented a card\n"
                                          "pool: 2 card(s) short, none in stock; asking again in 3 min\n")


def a_batch(world, log=LOG, state="launched", pool=True, key="a"):
    """A checkout launched one run whose log is `log`; closeup@alpha's own log written since (it runs now)."""
    props, store = world.source.props_home, world.source.store_root
    (props / "logs").mkdir(parents=True, exist_ok=True)
    path = props / "logs" / f"score-run-{key}.log"
    path.write_text(log.format(run=RUN))
    plan = Plan.objects.create(basket_hash=f"checkout-{key}", made_by="joey", state="ready", body=PLAN)
    launch = Launch.objects.create(plan=plan, by="joey", state="running", handles=[
        {"command": ["score", "run"], "pid": None, "log": str(path), "refused": None}])
    record = Checkout.objects.create(key=key * 32, by="joey", state=state, totals=TOTALS, launch=launch,
                                     items=[{"nodes": {"closeup@alpha": {}, "closeup@beta": {}}}],
                                     stop_line={"euros": 516.44, "spent": 120.0, "reserved": 0.0, "batch_from": 90.0,
                                                "at": "2026-10-24T11:08:38+00:00"})
    (store / "logs").mkdir(parents=True, exist_ok=True)
    row_log = store / "logs" / "closeup@alpha.log"
    row_log.write_text("drawing\n")
    later = time.time() + 5
    os.utime(row_log, (later, later))
    if pool:
        a_pool(props)
    return record


def newest():
    from score.dashboard.checkout import watched
    return watched.newest()


def test_the_batch_is_read_from_its_log_its_rows_and_its_pool(world):
    """From LOG by hand: 6 rows planned; terrain and plan@alpha done, closeup@beta failed, assembly@beta not run,
    closeup@alpha running (its log newer), assembly@alpha queued; EUR 3.21 the last heartbeat; one card warm and busy of
    two, one short. Break: state/batch_run.py `pool_of` counts no card busy."""
    a_batch(world)
    run = world.source.batch_run()
    assert run["state"] == "running" and run["checkout"] == Checkout.objects.get().pk
    assert run["rows"] == {"total": 6, "done": 2, "failed": 1, "not_run": 1, "running": 1, "queued": 1}
    assert run["money"]["runs"] == 3.21 and run["money"]["line"] == 516.44
    # spent is the money guard's: the environment's 100 since its first line less the 90 the batch began at
    assert (run["money"]["spent"], run["money"]["other"]) == (10.0, 6.79)
    assert run["eta"]["likely_minutes"] == 121.5 and run["eta"]["untimed"] == 1
    scenes = {scene["place"]: scene for scene in run["scenes"]}
    assert scenes[""]["state"] == "done" and scenes["alpha"]["running"] == ["close-ups"]
    assert scenes["beta"]["failed"] == 1 and scenes["beta"]["not_run"] == 1 and scenes["beta"]["state"] == "failed"
    assert run["pool"]["cards"] == {"size": 2, "warm": 1, "busy": 1, "idle": 0, "short": 1}
    assert run["pool"]["processors"] == {"size": 1, "warm": 0, "busy": 0, "idle": 0, "short": 1}
    [problem] = run["problems"]
    assert problem["place"] == "beta" and problem["words"].startswith(
        "The close-ups step stopped: no card of 24 GB graphics card was had")
    assert "gpu-" not in problem["words"] and "1 later step" in problem["words"]


def test_a_relaunch_goes_on_where_the_checkout_was(world):
    """A second run plans only what is not accepted: every planned row still counted, those accepted since done, a stale
    accept not. Break: state/batch_run.py `row_states` counts a row done whatever its accept's time."""
    record = a_batch(world)
    first = record.launch.plan
    first.body = {**PLAN, "checkout": record.pk}
    first.save()
    rest = {"groups": [{"places": ["alpha", "beta"], "to_run": {}, "blocked": {"assembly@alpha": "waits"},
                        "buys": [{"node": "closeup@alpha"}, {"node": "closeup@beta"}]}], "checkout": record.pk}
    again = Plan.objects.create(basket_hash="checkout-1", made_by="joey", state="ready", body=rest)
    Launch.objects.filter(pk=record.launch.pk).update(plan=again)
    after = (record.at + datetime.timedelta(minutes=5)).isoformat()
    accepts = {"terrain": after, "plan@alpha": after, "assembly@beta": after,
               "assembly@alpha": (record.at - datetime.timedelta(days=1)).isoformat()}
    found = batch_run.gathered(newest(), world.source.props_home, world.source.store_root, accepted_at=accepts.get)
    assert found["rows"] == {"total": 6, "done": 3, "failed": 1, "not_run": 0, "running": 1, "queued": 1}
    assert {scene["place"]: (scene["done"], scene["total"]) for scene in found["scenes"]} == {
        "": (1, 1), "alpha": (1, 3), "beta": (1, 2)}


def test_a_relaunch_adds_the_first_runs_money_and_clock_and_parked_machines_show(world):
    """Fault of 2026-10-24: spend began again at 0 and 13 parked machines billed unseen. 1.18 + 3.21 = 4.39; 2 parked of
    this run plus the old run's: 3. Break: state/batch_run.py `parked_of` counts none."""
    record = a_batch(world)
    first_log = world.source.props_home / "logs" / "score-run-0.log"
    first_log.write_text("[cloud] 12:00:00 pool of 2 gpu-24gb opened for run old-run until 16:00\n"
                         "heartbeat 2026-10-24T10:30:00+00:00: rows done 1, running 0, queued 5; this run's rows: "
                         "paid runs open 0, EUR 1.18 in the ledger since the run started\n")
    plan = Plan.objects.create(basket_hash="checkout-1", made_by="joey", state="ready",
                               body={**PLAN, "checkout": record.pk})
    earlier = Launch.objects.create(plan=plan, by="joey", state="stopped", handles=[
        {"command": ["score", "run"], "pid": None, "log": str(first_log), "refused": None}])
    began = record.launch.at - datetime.timedelta(minutes=45)
    Launch.objects.filter(pk=earlier.pk).update(at=began)
    parked = world.source.props_home / "cloud" / "parked"
    parked.mkdir(parents=True)
    for number, pool in enumerate(["old-run", RUN, RUN, "someone-else"]):
        (parked / f"m-{number}.json").write_text(json.dumps({"id": f"m-{number}", "pool": pool}))
    (world.source.props_home / "cloud" / "pools" / RUN / "closed").write_text("")
    found = batch_run.gathered(newest(), world.source.props_home, world.source.store_root)
    assert found["money"]["runs"] == 4.39
    assert found["started"] == began.isoformat(timespec="seconds") and found["eta"]["elapsed"] >= 45
    assert not found["pool"]["open"] and found["pool"]["renting"] == 3
    html = signed_in().get("/buy/run/").content.decode()
    assert "3 still renting" in html and len(prose(html)) <= 60


def test_the_state_follows_the_result_line_the_checkout_and_the_pool():
    """A drive that ended with lines stopped is finished; a refusal, an error or a traceback is stopped; no warm card
    while stock is short is waiting. Break: state/batch_run.py `overall` never says waiting (its pool check `if
    False:`)."""
    def said(log):
        return batch_run.overall({"state": "launched", "launch": {}}, batch_run.read_log(log.splitlines(), set()),
                                 False, None)
    assert said("exit: stopped, 3 of 4 lines done, 1 stopped\ndetached: failed exit=1 minutes=80.0") == (
        "finished", "some scenes' lines stopped")
    assert said("refused: these inputs are missing, so the rows ...\n  /x/a.json\nexit: exited, exit 1\n"
                "detached: failed exit=1 minutes=0.3") == (
        "stopped", "refused: these inputs are missing, so the rows ...")
    assert said("exit: error: KeyError: 'x'\ndetached: failed exit=1 minutes=2.0") == (
        "stopped", "error: KeyError: 'x'")
    assert said("Traceback\ndetached: failed exit=1 minutes=0.1")[0] == "stopped"
    pool = {"open": True, "cards": {"warm": 0, "short": 2}}
    nothing = batch_run.read_log([], set())
    assert batch_run.overall({"state": "launched", "launch": {}}, nothing, True, pool)[0] == "waiting"
    pool["cards"]["warm"] = 1
    assert batch_run.overall({"state": "launched", "launch": {}}, nothing, True, pool)[0] == "running"
    assert batch_run.overall({"state": "launched", "launch": {}}, nothing, False, None) == (
        "stopped", "the run ended without its result line")


def test_a_run_finished_stopped_or_starting_says_so_on_the_monitor(world):
    """Break: state/batch_run.py `overall` drops its launching -> starting line."""
    record = a_batch(world, log=LOG + "detached: ok exit=0 minutes=15.6 log=x outputs=y\n")
    run = world.source.batch_run()
    assert run["state"] == "finished" and run["ended"] and run["scenes"][1]["running"] == []
    record.launch.handles[0]["log"] = str(world.source.props_home / "logs" / "gone.log")
    record.launch.save()
    (world.source.props_home / "logs" / "gone.log").write_text(
        LOG.format(run=RUN) + "detached: stopped by signal 15 exit=143 minutes=0.0 log=x outputs=y\n")
    run = world.source.batch_run()
    assert run["state"] == "stopped" and run["problems"][0]["kind"] == "run"
    Checkout.objects.update(state="launching", launch=None)
    assert world.source.batch_run()["state"] == "starting"


def test_the_money_is_this_batchs_high_with_its_guesses_and_its_room_the_line_less_what_came_before(world):
    """327.24 + 33.16 = 360.40; the line 516.44 less 120 before it = 396.44 = 360.40 x 1.1; no line yet: the high plus
    10% and nothing spent. Break: state/batch_run.py `own_stop` leaves the spend before out of the room."""
    record = a_batch(world)
    money = world.source.batch_run()["money"]
    assert money["high"] == 360.40 and money["stop"] == 396.44 == round(360.40 * 1.1, 2)
    assert not run_monitor.money_bar({**money, "try_spent": 340.0})["over"]
    assert batch_run.own_stop({"euros": 396.44}) is None  # a line without what it was written over
    record.state, record.stop_line = "launching", {}
    record.save()
    (world.source.props_home / "logs" / "score-run-a.log").write_text("paid rows this run would buy: 2\n")
    money = world.source.batch_run()["money"]
    assert money["runs"] == 0.0 and money["stop"] == round(money["high"] * batch_run.BUFFER, 2)


def test_a_finished_rows_batch_gaps_are_problems(world):
    """Break: state/batch_run.py `gap_problems` asks no row for its batch gaps."""
    a_batch(world)
    found = batch_run.gathered(newest(), world.source.props_home, world.source.store_root,
                               lambda node: [{"name": "hatch: no model"}] if node == "plan@alpha" else [])
    assert [problem for problem in found["problems"] if problem["kind"] == "gaps"] == [
        {"at": "2026-10-24T11:09:00+00:00", "place": "alpha", "node": "plan@alpha", "kind": "gaps",
         "words": "Plan left 1 thing out as gaps.", "tip": "hatch: no model"}]


def test_scenes_show_parent_scenes_before_their_child_scenes():
    """Break: pages/run_monitor.py `ordered` sorts by the scene's own name only."""
    within = {"cockpit": "ship", "galley": "ship", "ship": "hangar", "flat": "block"}
    names = {"hangar": "Hangar", "ship": "Ship", "cockpit": "Cockpit", "galley": "Galley", "flat": "Flat"}
    assert run_monitor.ordered(["galley", "flat", "hangar", "cockpit", "ship", ""], within, names) == [
        ("", 0), ("flat", 0), ("hangar", 0), ("ship", 1), ("cockpit", 2), ("galley", 2)]


def test_the_monitor_shows_the_owner_his_stops_while_the_batch_lives_and_home_and_buy_lead_to_it(world):
    """Stop only for the owner, only while it lives; no batch: says so; Home links to it while it lives; Buy shows the
    live batch instead of a second Buy. Break: templates/pages/run_monitor.html shows the stops `{% if live %}` (not
    only to the owner)."""
    owner = signed_in()
    assert "No batch yet" in owner.get("/buy/run/").content.decode()
    assert 'href="/buy/run/"' not in owner.get("/").content.decode() and ">Batch</a>" not in owner.get(
        "/buy/").content.decode()
    a_batch(world)
    html = owner.get("/buy/run/").content.decode()
    assert 'data-url="/api/machine/stop"' in html and 'data-url="/api/machine/stop-batch"' in html
    assert "396.44" in html and "waiting for stock" in html and 'href="/place/alpha/"' not in html
    assert len(prose(html)) <= 60, prose(html)
    assert "/api/machine/stop" not in signed_in("sam").get("/buy/run/").content.decode()
    assert 'href="/buy/run/"' in owner.get("/").content.decode()
    buy = owner.get("/buy/").content.decode()
    assert re.search(r"Batch \d+ is (starting|running|waiting for machines): \d+ of \d+ steps, EUR [\d.]+ spent", buy)
    assert 'data-url="/buy/yes/"' not in buy and ">Batch</a>" in buy


def test_an_ended_try_is_history_under_the_batch_now(world):
    """Owner, 2026-10-26: "the cockpit is still just a bunch of red". Break: pages/run_monitor.py `ended` always
    None."""
    a_batch(world, log=LOG + "detached: stopped by signal 15 exit=143 minutes=0.0 log=x outputs=y\n", pool=False)
    Launch.objects.update(state="failed")
    html = signed_in().get("/buy/run/").content.decode()
    assert "Next try not started" in html and "Try 1 ended" in html
    assert re.search(r'<details class="rm-history"><summary[^>]*>Problems when try 1 ended <span data-v>\d+', html)
    assert "data-rm-reload=" not in html and "/api/machine/stop-batch" not in html


def test_the_export_carries_the_batch_and_the_hosted_page_says_how_fresh(world, tmp_path, monkeypatch):
    """Break: sync/building.py `batch_run_file` writes nothing."""
    a_batch(world)
    building.build(world.source, tmp_path / "one", MADE, 50, SPEND, world.root)
    exported = ExportedSource(tmp_path / "one")
    run = exported.batch_run()
    assert run["read_at"] == MADE and run["money"]["runs"] == 3.21 and run["rows"]["done"] == 2
    from score.dashboard import state
    monkeypatch.setattr(state, "source", lambda: exported)
    with override_settings(SCORE_MODE="hosted"):
        html = signed_in().get("/buy/run/").content.decode()
        assert "min ago" in html and "Buy sent" not in html
        SyncRequest.objects.create(kind="checkout", user="joey", payload={})
        SyncRequest.objects.filter(kind="checkout").update(
            created=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1))
        assert "Buy sent" in signed_in("sam").get("/buy/run/").content.decode()


def test_a_fault_is_said_as_a_short_plain_cause_and_rows_sharing_one_are_one_problem(tmp_path):
    """Break: state/batch_run.py `failure_problem` never says in how many places."""
    cloud = ("error: CalledProcessError: Command '['/home/score/tools/cloud/blender_cloud.py', '--scene', 'x']' "
             "returned non-zero exit status 1.")
    assert plain.step_cause(cloud, "  | no card could be rented") == "no cloud machine could be rented"
    assert plain.step_cause(cloud, "") == "its run on a cloud machine failed"
    assert plain.step_cause("error: RuntimeError: light@a: an input changed while it ran; nothing is stored") == \
        "an input file changed while it ran"
    assert plain.step_cause("made: fail") == "it was made but failed its check"
    assert plain.step_cause("error: ValueError: need at least one array to concatenate") == \
        "need at least one array to concatenate"
    said = plain.step_cause("error: KeyError: " + "word " * 40 + "/home/score/deep/file.json")
    assert len(said) <= 103 and "/home" not in said
    report = tmp_path / "faults.txt"
    report.write_text("  | no card could be rented\n")
    fault = (f"error: CalledProcessError: Command '['/x/blender_cloud.py']' returned non-zero exit status 1; "
             f"fault report {report}")
    rows = {f"light@{place}": ("failed", fault, "2026-10-24T11:09:00+00:00") for place in ("a", "b", "c")}
    rows["film@a"] = ("not_run", "not run: its line stopped at light@a", None)
    [problem] = batch_run.failures(rows)
    assert problem["places"] == ["a", "b", "c"] and problem["place"] == ""
    assert problem["words"].endswith(
        "stopped in 3 places: no cloud machine could be rented. 1 later step waits on them.")
    assert len(problem["raw"]) == 3 and "blender_cloud.py" in problem["raw"][0]


def test_the_next_buy_says_what_it_makes_again_first_and_keeps():
    """Of a, b, c, d planned: a, b made, c failed, d never ran; the next buys c, d, e. Break: state/batch_run.py
    `next_buy` counts a failed step as never run too (`unrun = planned - made`); `retries` ends the batch on a design
    edit since (owner, 2026-10-26: the fixes made to finish a batch are part of it)."""
    run = {"checkout": 3, "batch": 1, "at": "2026-10-25T09:10:00+00:00", "state": "finished",
           "nodes": {"planned": ["a", "b", "c", "d"], "made": ["a", "b"], "failed": ["c"]}}
    assert batch_run.next_buy(run, ["c", "d", "e"]) == (
        "Retry Batch 1: makes again the 1 step that failed and the 1 that never ran; makes 1 step for the "
        "first time; keeps the 2 already made.")
    assert batch_run.next_buy({**run, "design_at": "2026-10-25T10:00:00Z"}, ["c"]).startswith("Retry Batch 1:")
    made = {"planned": ["a", "b"], "made": ["a", "b"], "failed": []}
    assert batch_run.next_buy({**run, "nodes": made}, ["a"]).startswith("Batch 2, after Batch 1: makes again the 1")
    assert batch_run.next_buy({**run, "state": "running"}, ["c"]) is None
    assert batch_run.next_buy({"checkout": 1, "state": "finished"}, ["c"]) is None


def test_a_buy_while_the_batch_is_unfinished_is_its_next_try_whatever_the_design_edits(world):
    """Owner, 2026-10-25: "its the same batch, ur just retrying a failed part of it; it will become a mess if we split
    after fail"; 2026-10-26: Batch 1's fifth Buy, after a day of design fixes, was called Batch 2. A design edit ends no
    batch; a relaunch whose run never began (stopped while waiting for size) is no try; a batch ends once every row
    it planned was made. Break: checkout/watched.py `batch_ended` ends a batch when `design_at` is past its last try;
    `started` counts a launch stopped before its first heartbeat."""
    first = a_batch(world)
    retry = a_batch(world, key="b")
    retry.at = first.at + datetime.timedelta(hours=1)
    retry.save()
    found = world.source.batch_run()
    assert (found["batch"], found["tries"], found["checkout"]) == (1, 2, retry.pk)
    unstarted = a_batch(world, key="c", log="score run: waiting for size: 16 jobs, 2 cores; registered as w1; x\n"
                        "score run: stopped by signal 15 while waiting for size\ndetached: stopped by signal 15\n")
    unstarted.at, unstarted.design_at = retry.at + datetime.timedelta(hours=1), \
        (retry.at + datetime.timedelta(minutes=5)).isoformat()
    unstarted.save()
    assert (world.source.batch_run()["batch"], world.source.batch_run()["tries"]) == (1, 3)  # the newest is shown
    relaunch = a_batch(world, key="d")
    relaunch.at = unstarted.at + datetime.timedelta(minutes=20)
    relaunch.save()
    Launch.objects.filter(pk=unstarted.launch_id).update(state="stopped")  # as polling left it
    assert (world.source.batch_run()["batch"], world.source.batch_run()["tries"]) == (1, 3)
    from score.dashboard.checkout import watched
    every = list(Checkout.objects.order_by("at"))
    made = lambda node: (relaunch.at - datetime.timedelta(minutes=1)).isoformat()  # noqa: E731
    after = Checkout(at=relaunch.at + datetime.timedelta(hours=1))
    assert watched.batch_ended(every, after, made) and not watched.batch_ended(every, after, lambda node: None)


TRY_ONE = "\n".join([
    heartbeat("2026-10-24T23:05:00+00:00", 0, 2, 3, 1, "2.00"),
    "terrain: made: pass, accepted automatically",
    "light@alpha: error: RuntimeError: boom; fault report /x/faults/light@alpha.txt",
    "closeup@beta: error: RuntimeError: no card; fault report /x/faults/closeup@beta.txt",
    "assembly@beta: not run: its line stopped at closeup@beta",
    "detached: failed", ""])


def two_tries(tmp_path, try_log=None):
    """Batch 1 of two tries: the first failed light@alpha and closeup@beta; the second buys closeup@beta and
    assembly@beta again, launching (no log) or ended with `try_log`."""
    first, second = tmp_path / "try1.log", tmp_path / "try2.log"
    first.write_text(TRY_ONE)
    one = {"at": "2026-10-24T23:00:00+00:00", "logs": [str(first)]}
    two = {"at": "2026-10-25T09:00:00+00:00", "logs": [str(second)]}
    if try_log:
        second.write_text(try_log)
    return {"checkout": 2, "at": "2026-10-25T08:59:00+00:00", "state": "launched" if try_log else "launching",
            "totals": TOTALS, "stop_line": {}, "batch": 1, "tries": 2, "first_at": "2026-10-24T22:59:00+00:00",
            "launch": {"at": two["at"], "state": "done", "result": "failed", "logs": two["logs"]} if try_log else None,
            "runs": [one, two] if try_log else [one], "try_runs": [two] if try_log else [],
            "nodes": ["terrain", "light@alpha", "closeup@beta", "assembly@beta"],
            "try_nodes": ["closeup@beta", "assembly@beta"]}


def test_a_try_shows_what_it_makes_again_as_waiting_and_the_batchs_spend_apart_from_the_trys(tmp_path):
    """Owner, 2026-10-25: "and it still shows all failed etc"; 2026-10-26: is the spend try 4 or the batch? 2.00 + 5.00
    = 7.00 the batch's, 5.00 the try's. Break: state/batch_run.py `gathered` keeps an earlier try's line of a row this
    try makes again."""
    accepted = {"terrain": "2026-10-24T23:04:00+00:00"}.get
    run = batch_run.gathered(two_tries(tmp_path), tmp_path, tmp_path, accepted_at=accepted,
                             now=datetime.datetime(2026, 10, 25, 9, 1, tzinfo=datetime.timezone.utc))
    assert run["state"] == "starting"
    assert {scene["place"]: scene["state"] for scene in run["scenes"]} == {"": "done", "alpha": "failed",
                                                                          "beta": "waiting"}
    assert (run["rows"]["done"], run["rows"]["failed"], run["rows"]["not_run"]) == (1, 1, 0)
    assert [problem["node"] for problem in run["problems"]] == ["light@alpha"] and run["retried"] == 1
    clock = run_monitor.clock(run)
    assert clock["started"] == "08:59" and clock["batch_started"] == "24 Oct 23:00"
    again = TRY_ONE.splitlines()[0] + "\ncloseup@beta: error: RuntimeError: no card again; fault report /x/f.txt\n" \
        "assembly@beta: not run: its line stopped at closeup@beta\ndetached: failed\nexit: stopped, 1 line\n"
    ended = batch_run.gathered(two_tries(tmp_path, again), tmp_path, tmp_path, accepted_at=accepted)
    assert ended["state"] == "finished" and ended["retried"] == 0
    assert {problem["node"] for problem in ended["problems"]} == {"light@alpha", "closeup@beta"}
    beat = heartbeat("2026-10-25T09:30:00+00:00", 0, 1, 0, 0, "5.00") + "\ndetached: failed\nexit: stopped, 1 line\n"
    money = batch_run.gathered(two_tries(tmp_path, beat), tmp_path, tmp_path)["money"]
    assert (money["runs"], money["try_spent"]) == (7.0, 5.0)
    assert run_monitor.money_bar({**money, "high": 8.0, "stop": 10.0})["spent"] == 50.0


def test_the_monitor_shows_the_batchs_spend_of_its_one_budget(world):
    """Owner, 2026-10-26: "i have no idea how far the previours even got filled", then "the stop should be a total of
    the batch, not per try": spent is the money guard's measure since the batch's first line, the next Buy's figure
    the batch total. Break: state/batch_run.py `money_of` gives `left` as the whole budget; checkout/watched.py
    `batch_money` counts spent from 0, not the batch's start; state/batch_run.py `batch_total` drops `need`."""
    record = a_batch(world)
    record.stop_line = {**record.stop_line, "euros": 820.0, "batch_from": 80.0, "batch_budget": 740.0,
                        "batch_used": 410.0}
    record.save()
    money = world.source.batch_run()["money"]
    assert money["budget"] == 740.0 and money["left"] == round(740.0 - money["spent"] - money["in_flight"], 2)
    assert money["spent"] == 20.0 and re.search(r"Batch 1: EUR 20.00 spent of EUR 740.00 budget, EUR [\d.]+ left",
                     signed_in().get("/buy/run/").content.decode())
    from score.dashboard.pages import views  # what the next Buy sets: the batch's total, never a try's stop alone
    run = world.source.batch_run()
    assert views.next_total(run, 33.0) is None and views.next_total({**run, "state": "stopped"}, 33.0) == 740.0
    raised = {**run, "state": "stopped", "money": {**money, "budget": 10.0}}
    assert views.next_total(raised, 33.0) == round(20.0 + money["in_flight"] + 33.0, 2)


def test_what_prepare_predicts_for_the_next_try_shows_once_made_since_the_try():
    """Break: pages/run_monitor.py `prepared` drops its made-after-the-try comparison."""
    remake = types.SimpleNamespace(made_at="2026-10-26T08:00:00+00:00", counts={"predicted_gaps": 12}, stale=None)
    world = types.SimpleNamespace(remake=remake)
    assert run_monitor.prepared(world, {"at": "2026-10-25T16:00:00+00:00"}) == {
        "at": "2026-10-26T08:00:00+00:00", "gaps": 12, "stale": None}
    assert run_monitor.prepared(world, {"at": "2026-10-26T09:00:00+00:00"}) is None


# === the store's machine ==============================================================================================

HEALTH = {"size": "POP2-HM-2C-16G", "state": "idle", "units": {"score-sync.timer": "active"},
          "backup": {"at": "2026-10-18T11:30:00+00:00", "ok": True}, "bill": {"euros": 12.34, "month": "2026-10"},
          "disk": {"used_gb": 40, "total_gb": 100}, "free_only": True}
THEN = datetime.datetime.fromisoformat(MADE) + datetime.timedelta(hours=1)


class Kill:
    """score.conductor.kill stood in: each call kept."""

    def __init__(self):
        self.calls = []

    def stop_all(self, asked_by, words):
        self.calls.append(("stop_all", asked_by, words))
        return {"runs": ["run-1", "run-2"], "parked": ["m-1"], "latched": True}

    def stop_batch(self, asked_by, words):
        self.calls.append(("stop_batch", asked_by, words))
        return {"runs": ["run-1"], "parked": ["m-1"], "free_only": None}

    def allow_paid(self, asked_by, words):
        self.calls.append(("allow_paid", asked_by, words))
        return {"latched": False}


@pytest.fixture
def conductor(monkeypatch):
    """score.conductor with health, logs and kill stood in; its Kill."""
    kill = Kill()
    parts = {"health": types.SimpleNamespace(read=lambda: dict(HEALTH)),
             "logs": types.SimpleNamespace(tails=lambda limit: {"run.log": [f"line {n} " + "x" * 2000 for n in
                                                                            range(limit)], "faults": ["one fault"]}),
             "kill": kill}
    monkeypatch.setitem(sys.modules, "score.conductor", types.ModuleType("score.conductor"))
    for name, part in parts.items():
        monkeypatch.setitem(sys.modules, f"score.conductor.{name}", part)
    return kill


@pytest.fixture
def no_record(settings):
    """No store's machine recorded and no export swapped in on the hosted side, before and after."""
    one_store.path().unlink(missing_ok=True)
    shutil.rmtree(settings.SCORE_HOME / "export", ignore_errors=True)
    yield
    one_store.path().unlink(missing_ok=True)
    shutil.rmtree(settings.SCORE_HOME / "export", ignore_errors=True)


def off_a_conductor(monkeypatch):
    """No score.conductor here, also when an earlier test imported its parts."""
    for name in ("score.conductor", "score.conductor.health", "score.conductor.logs", "score.conductor.kill"):
        monkeypatch.setitem(sys.modules, name, None)


def named_machine(world, name):
    (world.source.props_home / machine.MACHINE_FILE).write_text(json.dumps({"name": name, "size": "POP2-HM-2C-16G"}))


def test_the_export_carries_the_machine_its_health_and_its_tails_cut_to_the_cap(world, tmp_path, conductor):
    """The newest tail lines kept within TAIL_BYTES; none over the export's cap, said; off a conductor said so. Break:
    state/machine.py `cut` drops the newest lines (`pop()`), not the oldest."""
    named_machine(world, "conductor")
    manifest = building.build(world.source, tmp_path / "one", MADE, 50, SPEND, world.root)
    found = json.loads((tmp_path / "one/machine.json").read_text())
    assert manifest["machine"] == "conductor" and manifest["written"][:2] == ["state.json", "machine.json"]
    assert found["health"]["bill"]["euros"] == 12.34 and found["tails"]["faults"] == ["one fault"]
    assert sum(len(line) + 1 for lines in found["tails"].values() for line in lines) <= machine.TAIL_BYTES
    assert found["tails"]["run.log"][-1].startswith(f"line {machine.TAIL_LINES - 1} ")
    assert ExportedSource(tmp_path / "one").machine() == found
    small = building.build(world.source, tmp_path / "small", MADE, 0.05, SPEND, world.root)
    assert json.loads((tmp_path / "small/machine.json").read_text())["tails"] == {}
    assert {"what": "the store's machine's log tails", "why": "over the export's cap"} in small["left_out"]


def test_off_a_conductor_the_export_says_so_and_the_card_shows_no_state(world, tmp_path, monkeypatch):
    """Break: state/machine.py `state_of` reads no state as idle."""
    off_a_conductor(monkeypatch)
    building.build(world.source, tmp_path / "one", MADE, 50, SPEND, world.root)
    found = json.loads((tmp_path / "one/machine.json").read_text())
    assert found["health"] == {"missing": machine.NOT_ON_CONDUCTOR} and found["tails"] == {}
    assert found["machine"]["name"]
    card = machine.card(found, MADE)
    assert card["missing"] == machine.NOT_ON_CONDUCTOR and card["state"] is None and card["export_late"]
    on_pc = {"machine": {"name": "dupe"}, "health": {"machine": None, "state": None, "runs_active": 1, "backup": None}}
    assert machine.card(on_pc)["on_pc"] and machine.card(on_pc)["state"] == "running 1 run"
    assert machine.card({**on_pc, "health": {**on_pc["health"], "runs_active": 0}})["state"] == "idle"
    assert not machine.card({"machine": {"name": "conductor", "size": "POP2"}, "health": {"state": "idle"}})["on_pc"]


def committed_by(remote, name):
    """An export whose manifest names machine `name`, sent and committed through the sync routes."""
    data = json.dumps({"format": versions.FORMAT, "made_at": MADE, "machine": name}).encode()
    sha = hashlib.sha256(data).hexdigest()
    remote.lacking({sha: len(data)})
    remote.put_chunk(sha, 0, len(data), data)
    return remote.commit(f"export-{name}", {"manifest.json": sha})


def test_a_second_machine_is_shown_but_applies_nothing_until_the_owner_confirms_it(world, settings, no_record):
    """No request kind, no sync token, no one but the owner, not without the second ask nor for a machine no export came
    from moves the record. Break: api/routes.py `machine_confirm` skips `asked_twice`."""
    settings.SCORE_SYNC_TOKEN, settings.SCORE_MODE = TOKEN, settings.HOSTED
    web = hosted_client()
    pc, other = remote_of(web, "pc"), remote_of(web, "conductor")
    committed_by(pc, "pc")
    committed_by(other, "conductor")
    assert one_store.record()["name"] == "pc" and one_store.second(THEN) == "conductor"
    item = SyncRequest.objects.create(kind="change", user="joey", payload={"stage": "closeup", "words": "redder"})
    assert other.claim(item.pk) is False and "not the store's machine (pc)" in other.not_the_store
    item.refresh_from_db()
    assert item.state == "waiting"
    assert applying.apply({"kind": "store-machine", "user": "joey", "payload": {"machine": "conductor"}},
                          world.source).state == "refused"
    assert web.post("/api/machine/confirm", json={"machine": "conductor", "sure": True},
                    headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 401
    assert api("mallory").post("/api/machine/confirm", json={"machine": "conductor", "sure": True}).status_code == 403
    owner = api()
    assert owner.post("/api/machine/confirm", json={"machine": "conductor"}).status_code == 400
    assert owner.post("/api/machine/confirm", json={"machine": "elsewhere", "sure": True}).status_code == 409
    assert one_store.record()["name"] == "pc"
    answer = owner.post("/api/machine/confirm", json={"machine": "conductor", "sure": True})
    assert answer.status_code == 200 and one_store.record()["by"] == "joey" and one_store.second(THEN) is None
    assert pc.claim(item.pk) is False and other.claim(item.pk) is True and other.not_the_store is None
    one_store.kept({"name": "pc", "others": {"naive": "2026-10-18T13:00:00", "broken": "not a time"}})
    assert one_store.second(THEN) == "naive"  # a time of no zone or none breaks no page


def test_stop_everything_stop_batch_and_allow_paid_are_the_owners_asked_twice_and_applied_once(world, settings,
                                                                                             conductor, no_record):
    """Hosted nothing is done but queue; the store's machine applies each once through score.conductor.kill. Break:
    sync/client.py `answered` applies a request it could not claim."""
    from score.dashboard.pages import machine as page
    settings.SCORE_SYNC_TOKEN, settings.SCORE_MODE = TOKEN, settings.HOSTED
    owner = api()
    for path in ("stop", "stop-batch"):
        assert owner.post(f"/api/machine/{path}", json={}).status_code == 400  # the second ask not answered
        assert api(f"mallory-{path}").post(f"/api/machine/{path}", json={"sure": True}).status_code == 403
    assert owner.post("/api/machine/stop", json={"sure": True, "words": "now"}).json()["said"].startswith("queued")
    assert owner.post("/api/machine/stop-batch", json={"sure": True}).json()["said"].startswith("queued")
    assert owner.post("/api/machine/allow-paid", json={"sure": True}).json()["said"].startswith("queued")
    assert conductor.calls == []
    settings.SCORE_MODE = settings.LOCAL
    remote = remote_of(hosted_client(), "conductor")
    for kind, call in (("stop-everything", ("stop_all", "joey", "now")), ("stop-batch", ("stop_batch", "joey", "")),
                       ("allow-paid", ("allow_paid", "joey", ""))):
        stop = SyncRequest.objects.get(kind=kind)
        item = {"id": stop.pk, "kind": stop.kind, "user": stop.user, "payload": stop.payload}
        assert client.answered(remote, item, world.source).state == "done" and conductor.calls[-1] == call
        assert client.answered(remote, item, world.source) is None  # claimed once: never applied again
    assert len(conductor.calls) == 3
    assert page.report_counts(SyncRequest.objects.get(kind="stop-batch").detail) == [("parked", 1), ("runs", 1)]
    for kind in ("stop-everything", "stop-batch"):
        assert applying.apply({"kind": kind, "user": "mallory", "payload": {}}, world.source).state == "refused"
    assert len(conductor.calls) == 3


def test_the_kill_switch_refuses_in_an_agents_process_and_off_a_conductor(world, monkeypatch, conductor):
    """Break: pages/actions.py `owner_figure_off_why` drops its `agent_started` refusal."""
    monkeypatch.setattr(actions, "agent_started", lambda: True)
    for kind in ("stop-everything", "allow-paid"):
        applied = applying.apply({"kind": kind, "user": "joey", "payload": {}}, world.source)
        assert applied.state == "refused" and "agent's shell" in applied.detail
    assert conductor.calls == []
    monkeypatch.setattr(actions, "agent_started", lambda: False)
    off_a_conductor(monkeypatch)
    applied = applying.apply({"kind": "stop-everything", "user": "joey", "payload": {}}, world.source)
    assert applied.state == "refused" and machine.NOT_ON_CONDUCTOR in applied.detail


def test_the_card_offers_allow_paid_only_while_latched_and_says_when_the_machine_is_off_the_pin(world, conductor,
                                                                                                 monkeypatch):
    """Break: state/machine.py `card` gives `code_off` False always."""
    named_machine(world, "conductor")
    home = signed_in().get("/").content.decode()
    assert "conductor" in home and "Stop everything" in home and "Allow paid work again" in home  # the latch is set
    page = signed_in().get("/machine/").content.decode()
    assert "one fault" in page and "score-sync.timer" in page
    off = {"checkout": "a" * 40, "pin": "b" * 40, "matches": False}
    monkeypatch.setitem(sys.modules, "score.conductor.health", types.SimpleNamespace(
        read=lambda: {**HEALTH, "free_only": False, "code": off}))
    home = signed_in().get("/").content.decode()
    assert "the cloud machine is on aaaaaaaa, the cockpit on bbbbbbbb; it is being updated" in home
    assert "Allow paid work again" not in home
    assert machine.card({"health": {"code": {**off, "matches": True}}})["code_off"] is False


def test_a_buy_is_refused_on_a_conductor_whose_checkout_is_off_the_pin(monkeypatch):
    """2026-10-25: a retry ran Batch 1's old code unnoticed. Break: sync/client.py `pin_refusal` returns None whatever
    the commits."""
    import score.conductor as real
    monkeypatch.setattr(real, "machine", lambda path=None: {"name": "conductor"})
    monkeypatch.setattr(client, "head", lambda repo: "a" * 40)

    class Pinned:
        def __init__(self, commit):
            self.commit = commit

        def call(self, method, path):
            assert (method, path) == ("GET", "/pin")
            return {"commit": self.commit}
    assert client.pin_refusal(Pinned("b" * 40), "/repo") == (
        "the cloud machine is on aaaaaaaa, the cockpit on bbbbbbbb; it is being updated: buy again in a few minutes")
    assert client.pin_refusal(Pinned("a" * 40), "/repo") is None
    assert client.pin_refusal(Pinned(None), "/repo") is None
    monkeypatch.setattr(real, "machine", lambda path=None: None)
    assert client.pin_refusal(Pinned("b" * 40), "/repo") is None


def test_the_sync_and_the_listener_follow_the_kill_switch_latch(monkeypatch):
    """Set by the latch file, taken off with it; set by whoever started it, never taken off here. Break: sync/client.py
    `free_only_followed` pops FREE_ONLY whenever the latch file is gone."""
    from score import conductor
    monkeypatch.delenv(conductor.FREE_ONLY, raising=False)
    monkeypatch.setitem(client.LATCHED, "set", False)
    conductor.FREE_ONLY_LATCH.parent.mkdir(parents=True, exist_ok=True)
    conductor.FREE_ONLY_LATCH.write_text(f"{conductor.FREE_ONLY}=1\n")
    try:
        assert client.free_only_followed() and os.environ[conductor.FREE_ONLY] == "1"
    finally:
        conductor.FREE_ONLY_LATCH.unlink()
    assert not client.free_only_followed() and conductor.FREE_ONLY not in os.environ
    monkeypatch.setenv(conductor.FREE_ONLY, "1")
    assert not client.free_only_followed() and os.environ[conductor.FREE_ONLY] == "1"


# === the concept review ===============================================================================================

PRICE = 0.15
REDRAW_PRICE = 0.19  # a Redraw with notes: the prompt correction and the draw
DISCUSS_PRICE = 0.04


def made_draws(store, place):
    """The place's draws made in the test, oldest first (not the fixture's own, drawn the day before)."""
    from score.review import concepts as drawing
    return [draw for draw in drawing.draws(store, place) if draw["at"] != "2026-10-20T07:00:00+00:00"]


@pytest.fixture
def stand_in(drafting, monkeypatch):
    """The draw's own process run in-process with a stand-in model; [what each draw was asked]."""
    from score.dashboard.pages import concepts
    from score.review import concepts as drawing
    from score.review import environment_concept, web
    from score.store import runtime_store
    asked = []
    monkeypatch.setattr(environment_concept, "places_now",
                        lambda places: [{"place": place, "name": place.capitalize(), "holds": []} for place in places])
    monkeypatch.setattr("score.adapters.compute.require_books", lambda what: None)
    monkeypatch.setattr(drawing, "draw_euros", lambda *given: PRICE)
    monkeypatch.setattr(drawing, "redraw_euros", lambda *given: REDRAW_PRICE)
    monkeypatch.setattr(concepts, "in_background", concepts.applied_here)
    offsite = drafting.source.store.cache.parent / "bucket"
    monkeypatch.setattr(drawing, "offsite_store", lambda: runtime_store.FolderStore(offsite))
    monkeypatch.setattr(drawing, "handed_over", lambda store, place: "library: stand-in")
    monkeypatch.setattr(web, "reading_started", lambda store, place, by: "reading: stand-in")

    def run(argv, env, **kwargs):
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        model = lambda wording, pictures: asked.append(wording) or a_png((30 * len(asked), 90, 140))  # noqa: E731
        prompt = lambda question, pictures: asked.append(question) or "The corrected prompt."  # noqa: E731
        record = drawing.draw(drafting.source.store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1],
                              caller=model, reviser=prompt)
        return subprocess.CompletedProcess(argv, 0, json.dumps(record) + "\n", "")
    drawn_here = web.concept_draw
    monkeypatch.setattr(web, "concept_draw", lambda *args, **named: drawn_here(*args, run=run, **named))
    return asked


def drawn(owner, place, **body):
    return owner.post(f"/concept/{place}/draw/", json.dumps(body), content_type="application/json")


def test_a_draw_is_the_owners_yes_at_the_price_shown_then_locked_and_unlocked(drafting, stand_in):
    """His click writes a spend yes at exactly 0.15; a redraw sends his marks to the prompt model, whose prompt becomes
    the place's wording; Lock takes the Review button off the card and refuses another draw; Unlock frees it. Break:
    pages/concepts.py `concept_draw` sends no marks."""
    from score.review import concepts as drawing
    owner = signed_in()
    assert drawn(owner, "beta", note="dusty", euros=PRICE).status_code == 200
    state = owner.get("/concept/beta/state/").json()
    assert state["pending"] is False and state["refused"] is None and state["newest"]
    yes = drafting.source.store.spend_yes("override", made_draws(drafting.source.store, "beta")[0]["yes"])
    assert yes["by"] == "joey" and yes["euros"] == PRICE and "beta" in yes["purpose"]
    marks = [{"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "note": "a window"}]
    drawn(owner, "beta", marks=marks, base=state["newest"], euros=REDRAW_PRICE)
    assert "Box 1 (top left): a window." in stand_in[-2]  # the prompt model corrects the prompt by it
    assert stand_in[-1].startswith("The corrected prompt.")
    assert drawing.own_wording(drafting.source.store, "beta") == "The corrected prompt."
    newest_draw = owner.get("/concept/beta/state/").json()["newest"]
    assert owner.post("/concept/beta/pick/", json.dumps({"sha": newest_draw}), content_type="application/json").json()
    assert 'ptile-review" href="/concept/beta/"' not in owner.get("/places/").content.decode()
    assert drawn(owner, "beta", euros=PRICE).status_code == 409  # locked
    owner.post("/concept/beta/pick/", json.dumps({"sha": None}), content_type="application/json")
    assert 'href="/concept/beta/"' in owner.get("/places/").content.decode()
    assert owner.get("/concept/nowhere/").status_code == 404


def test_with_no_mark_and_no_note_a_draw_is_fresh_from_the_places_wording(drafting, stand_in):
    """Break: pages/concepts.py `concept_draw` takes the newest draw as the base when none is posted."""
    owner = signed_in()
    drawn(owner, "beta", euros=PRICE)
    drawn(owner, "beta", marks=[], note="", base=None, euros=PRICE)
    first, fresh = made_draws(drafting.source.store, "beta")
    assert fresh["base"] is None and fresh["marks"] == [] and fresh["sha"] != first["sha"]
    assert stand_in[-1] == stand_in[0] and "Box" not in stand_in[-1]
    assert fresh["yes"] != first["yes"] and fresh["euros"] == PRICE
    assert drafting.source.store.cache.parent.joinpath("bucket", f"concept-draws/{fresh['sha']}.png").is_file()


def test_his_edited_wording_is_sent_and_kept_until_back_to_generated_hosted_too(drafting, stand_in, settings):
    """Break: pages/concepts.py `concept_draw` drops the posted `wording`."""
    from score.review import concepts as drawing
    owner = signed_in()
    generated = escape(drawing.generated(drafting.source.store, "beta"))
    edited = "One concept painting of beta at dusk, its doors open."
    drawn(owner, "beta", marks=[], note="", base=None, euros=PRICE, wording=edited)
    assert stand_in[-1] == edited and drawing.own_wording(drafting.source.store, "beta") == edited
    assert f">{edited}</textarea>" in owner.get("/concept/beta/").content.decode()
    assert signed_in("mallory").post("/concept/beta/generated/").status_code == 403
    assert owner.post("/concept/beta/generated/").json()["said"] == "back to the generated wording"
    assert f">{generated}</textarea>" in owner.get("/concept/beta/").content.decode()
    settings.SCORE_MODE = settings.HOSTED
    try:
        drawn(owner, "beta", euros=PRICE, wording="beta, my words")
        assert ">beta, my words</textarea>" in owner.get("/concept/beta/").content.decode()  # before the export
        owner.post("/concept/beta/generated/")
        assert ">beta, my words</textarea>" not in owner.get("/concept/beta/").content.decode()
    finally:
        settings.SCORE_MODE = settings.LOCAL


def test_a_draw_at_another_price_or_by_anyone_else_is_refused(drafting, stand_in, monkeypatch):
    """Also an approved design's concept cannot be unlocked. Break: score/review/web.py `concept_draw` drops its price
    comparison."""
    from score.dashboard.pages import concepts
    owner = signed_in()
    drawn(owner, "beta", euros=0.05)
    assert "measured price" in owner.get("/concept/beta/state/").json()["refused"]
    assert made_draws(drafting.source.store, "beta") == []
    other = signed_in("mallory")
    assert drawn(other, "beta", euros=PRICE).status_code == 403
    unlock = json.dumps({"sha": None})
    assert other.post("/concept/beta/pick/", unlock, content_type="application/json").status_code == 403
    monkeypatch.setattr(concepts, "approved", lambda source, place: True)
    answer = owner.post("/concept/beta/pick/", json.dumps({"sha": None}), content_type="application/json")
    assert answer.status_code == 409 and "approved" in answer.json()["detail"]


def test_draw_and_lock_wait_while_the_layer_above_is_not_ready_and_the_store_refuses_the_same(drafting, stand_in,
                                                                                              monkeypatch):
    """Break: score/review/concepts.py `pick` skips `step_refusal`."""
    from score.review import concepts as drawing
    owner = signed_in()
    drawn(owner, "beta", euros=PRICE)
    monkeypatch.setattr(drawing, "step_refusal", lambda store, place, step: "waits for yard's plan to be made")
    page = owner.get("/concept/beta/").content.decode()
    pick = page[page.index('id="concept-pick"'):].split(">", 1)[0]
    assert " disabled" in pick and "waits for yard&#x27;s plan to be made" in pick
    sha = made_draws(drafting.source.store, "beta")[-1]["sha"]
    answer = owner.post("/concept/beta/pick/", json.dumps({"sha": sha}), content_type="application/json")
    assert answer.status_code == 409 and "plan to be made" in answer.json()["detail"]
    assert drawing.picked(drafting.source.store, "beta") is None


def test_a_hosted_draw_reaches_the_listener_once_and_its_picture_is_served(drafting, stand_in, settings):
    """One held call, claimed once; the picture sent back before the next export. Break: sync/client.py `answered` sends
    no picture back."""
    from score.dashboard.pages import concepts
    owner = signed_in()
    settings.SCORE_MODE = settings.HOSTED
    try:
        drawn(owner, "beta", euros=PRICE)
        assert owner.get("/concept/beta/state/").json()["pending"] is True
    finally:
        settings.SCORE_MODE = settings.LOCAL
    with override_settings(SCORE_SYNC_TOKEN=TOKEN):
        web = hosted_client()
        remote = remote_of(web)
        assert web.post(f"/api/sync/requests/{SyncRequest.objects.get().pk}/claim",
                        headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200
        SyncRequest.objects.update(state="waiting")  # a second caller is refused only after the first claimed
        assert listen.round_once(remote, drafting.source) == [(SyncRequest.objects.get().pk, "done")]
        assert remote.waiting(listen.LISTENED, 0) == [] and not remote.claim(SyncRequest.objects.get().pk)
    record = json.loads(SyncRequest.objects.get().detail)
    assert sorted(path.name for path in (settings.SCORE_HOME / "request-files").iterdir()) == [
        f"{record['sha']}-1280.jpg", f"{record['sha']}-360.jpg"]
    shown = concepts.answered_draws("beta")
    assert [draw.picture.sha for draw in shown] == [record["sha"]] and shown[0].picture.thumb_url


def test_the_listener_says_an_unreachable_hosted_side_and_asks_again(drafting):
    """Break: sync/listen.py `listen` pauses SHORTEST_ROUND after an unreachable side."""
    class Down:
        def waiting(self, kinds, wait, skip=()):
            raise urllib.error.URLError("refused")
    said, paused = [], []
    listen.listen(Down(), drafting.source, rounds=2, log=said.append, pause=paused.append)
    assert len(said) == 2 and "did not answer" in said[0] and paused == [listen.RETRY_SECONDS] * 2

    class Old:  # a hosted side that answers at once, not holding the call
        not_the_store = None

        def waiting(self, kinds, wait, skip=()):
            return []
    paused.clear()
    listen.listen(Old(), drafting.source, rounds=3, log=said.append, pause=paused.append)
    assert paused == [listen.SHORTEST_ROUND] * 3


def test_draw_all_is_one_yes_for_n_first_draws_at_n_times_the_price(drafting, stand_in, monkeypatch):
    """2 undrawn at 0.15: EUR 0.30; each draw its own yes saying so; then gone. Break: pages/concepts.py `draw_all`
    prices N draws as one."""
    from score.dashboard.pages import concepts
    from score.review import concepts as drawing
    owner = signed_in()
    shown = concepts.draw_all(concepts.light_world(drafting.source))
    assert shown["places"] == ["alpha", "beta"] and "Draw all 2, EUR 0.30" in owner.get("/places/").content.decode()
    assert owner.post("/concepts/draw-all/", json.dumps({"places": shown["places"], "euros": 0.30}),
                      content_type="application/json").status_code == 200
    for place in ("alpha", "beta"):
        found = made_draws(drafting.source.store, place)
        assert len(found) == 1 and found[0]["base"] is None and found[0]["euros"] == PRICE
        yes = drafting.source.store.spend_yes("override", found[0]["yes"])
        assert "Draw all, 2 first draws for EUR 0.30" in yes["purpose"]
    assert concepts.draw_all(concepts.light_world(drafting.source)) is None
    waits = drawing.waits
    monkeypatch.setattr(drawing, "waits", lambda store, place: "waits for yard's concept to be locked"
                        if place == "alpha" else waits(store, place))
    assert concepts.draw_all(concepts.light_world(drafting.source)) is None  # alpha waits, beta drawn


def test_draw_all_is_refused_when_the_total_or_the_places_moved_or_for_anyone_else(drafting, stand_in):
    """And on the store's machine once drawn since the click. Break: pages/concepts.py `concept_draw_all` drops its
    places comparison."""
    from score.dashboard.pages import concepts
    from score.review import web
    owner = signed_in()
    places = concepts.draw_all(concepts.light_world(drafting.source))["places"]
    for body in ({"places": places, "euros": 0.15}, {"places": ["alpha"], "euros": 0.30}):
        assert owner.post("/concepts/draw-all/", json.dumps(body), content_type="application/json").status_code == 409
    assert signed_in("mallory").post("/concepts/draw-all/", json.dumps({"places": places, "euros": 0.30}),
                                     content_type="application/json").status_code == 403
    assert SyncRequest.objects.count() == 0
    drawn(owner, "beta", euros=PRICE)
    with pytest.raises(web.review.Refused, match="changed"):
        web.concept_draw(drafting.source.store, "beta", {}, PRICE, by="joey", first=True)
    assert len(made_draws(drafting.source.store, "beta")) == 1


def test_draws_on_their_way_are_not_offered_twice_and_show_until_they_land(drafting, stand_in, settings):
    """Hosted Draw all answered by the listener side by side; while queued, Draw all is a busy count and each card a
    spinner; a refused one says why. Break: pages/concepts.py `draw_all` offers places with a draw on its way."""
    from score.dashboard.pages import concepts
    owner = signed_in()
    places = concepts.draw_all(concepts.light_world(drafting.source))["places"]
    settings.SCORE_MODE = settings.HOSTED
    try:
        owner.post("/concepts/draw-all/", json.dumps({"places": places, "euros": 0.30}),
                   content_type="application/json")
        assert concepts.draw_all(concepts.light_world(drafting.source)) is None
    finally:
        settings.SCORE_MODE = settings.LOCAL
    html = owner.get("/places/").content.decode()
    assert "Drawing 2..." in html and html.count('class="draw-busy"') == 2
    SyncRequest.objects.filter(payload__place="beta").update(state="refused", detail="refused: the price moved")
    with override_settings(SCORE_SYNC_TOKEN=TOKEN):
        answered = listen.round_once(remote_of(hosted_client()), drafting.source)
    assert [state for _, state in answered] == ["done"]
    assert len(made_draws(drafting.source.store, "alpha")) == 1
    html = owner.get("/places/").content.decode()
    assert "draw-busy" not in html and 'class="draw-refused" title="refused: the price moved"' in html


def test_a_places_page_names_what_it_holds_directly_and_a_part_of_another_place_has_no_card(drafting, stand_in):
    """Break: pages/concepts.py `asked_to_hold` adds the places two levels down."""
    (drafting.data / "places/within.json").write_text(json.dumps({
        "shells": {"yard": {"name": "Yard"}}, "within": {"alpha": {"within": "beta"}, "beta": {"within": "yard"}}}))
    owner = signed_in()
    page = owner.get("/concept/yard/").content.decode()
    assert "data-v>Beta</b>" in page and "data-v>Alpha</b>" not in page
    assert "data-v>Alpha</b>" in owner.get("/concept/beta/").content.decode()
    trail = owner.get("/concept/alpha/").content.decode().split('class="trail"')[1].split("</nav>")[0]
    assert trail.index('href="/concept/yard/"') < trail.index('href="/concept/beta/"') < trail.index("Alpha")
    (drafting.data / "places/within.json").write_text(json.dumps({
        "shells": {}, "within": {}, "parts": {"alpha": {"of": "beta", "as": "its far view"}}}))
    html = owner.get("/").content.decode()
    assert 'href="/concept/alpha/"' not in html and 'href="/place/alpha/"' not in html


def test_a_locked_concepts_page_shows_its_reading_boxed_and_its_euros_reach_the_totals(drafting):
    """A box of [0, 0, 48, 30] px on a 96 x 60 picture is 50% by 50%; another lock: the reading counts for nothing;
    every reading's euros on the Environment and Stats. Break: pages/concepts.py `reading_view` divides a box's width by
    the picture's height."""
    from score.dashboard.state import screens as screen
    from score.review import concepts as drawing
    from score.review import reading
    world = drafting
    assert "concept-inventory" not in signed_in().get("/concept/alpha/").content.decode()  # not locked: none
    alpha = fixture.concept_of(world.store, "alpha")
    drawing.pick(world.store, "alpha", alpha, "joey")
    rows = [{"id": "drum", "name": "fuel drum", "noun": "drum", "kind": "generate", "terrain": False, "count": 2,
             "size_words": "waist", "anchor": "ground", "where": "left", "boxes": [[0, 0, 48, 30]],
             "box": [0, 0, 48, 30]}]
    reading.kept(world.store, {"place": "alpha", "concept": alpha, "at": "2026-10-21T08:00:00+00:00", "by": "joey",
                               "method": reading.METHOD, "size": [96, 60], "inventory": {"rows": rows},
                               "gaps": [{"kind": "size", "row": "drum", "words": "its size in metres not read"}],
                               "skipped": [{"name": "crate", "row": None, "why": reading.ONLY_SAM,
                                            "box": [48, 30, 96, 60]}],
                               "merged": [{"name": "blue drum", "row": "blue", "into": "drum"}],
                               "euros": {"rows": 0.03, "boxes": 0.1, "total": 0.13},
                               "seconds": {"rows": 20.0, "boxes": 30.0, "card": 550.0}})
    world.source.refresh()
    page = signed_in().get("/concept/alpha/").content.decode()
    assert "data-v>fuel drum</span>" in page and "&times;2" in page and "1 rows, 1 gaps, EUR 0.13, 10.0 min" in page
    assert 'style="left:0.0%;top:0.0%;width:50.0%;height:50.0%"' in page
    assert 'class="concept-box skipped"' in page and 'style="left:50.0%;top:50.0%' in page
    assert "skipped 1, merged 1</button>" in page
    assert "inventories EUR</small> 0.13" in signed_in("joey2").get("/places/").content.decode()
    assert screen.design_state(world.source.world_state(), "alpha") == "plan"  # read: its plan is next
    drawing.recorded(world.store, "concepts/alpha/picks/2099-01-01T10-00-00.json",
                     {"place": "alpha", "sha": "o" * 64, "by": "joey", "at": "2099-01-01T10:00:00+00:00"})
    world.source.refresh()
    page = signed_in("joey3").get("/concept/alpha/").content.decode()
    assert "data-v>fuel drum</span>" not in page and "data-v>to read</span>" in page


@pytest.fixture
def answerer(drafting, stand_in, monkeypatch):
    """The Discuss's own process run in-process with a stand-in prompt model; [what each Discuss was asked]."""
    from score.review import discuss, web
    asked = []
    monkeypatch.setattr(discuss, "price", lambda *given: DISCUSS_PRICE)

    def run(argv, env, **kwargs):
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        model = lambda question, pictures: asked.append(question) or ("Paint the door red.", 0.0271)  # noqa: E731
        entry = discuss.discuss(drafting.source.store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1],
                                asker=model)
        return subprocess.CompletedProcess(argv, 0, json.dumps(entry) + "\n", "")
    discussed_here = web.concept_discuss
    monkeypatch.setattr(web, "concept_discuss", lambda *args, **named: discussed_here(*args, run=run, **named))
    return asked


def test_a_discuss_is_answered_kept_and_sent_with_the_next_draw_and_its_cost_summed(drafting, stand_in, answerer,
                                                                                    settings):
    """At another price refused; the measured 0.0271 summed; hosted, the listener answers it. Break:
    score/review/concepts.py `redrawn` leaves the open discussion out of the prompt rewrite."""
    from score.dashboard.pages import concepts
    owner = signed_in()
    drawn(owner, "beta", euros=PRICE)
    base = owner.get("/concept/beta/state/").json()["newest"]
    asked = json.dumps({"base": base, "question": "is the door too small?", "euros": DISCUSS_PRICE})
    assert owner.post("/concept/beta/discuss/", asked, content_type="application/json").status_code == 200
    state = owner.get(f"/concept/beta/state/?draw={base}").json()
    assert state["thread"][0]["answer"] == "Paint the door red." and not state["thread"][0]["closed"]
    owner.post("/concept/beta/discuss/", json.dumps({"base": base, "question": "?", "euros": 0.03}),
               content_type="application/json")
    assert "not today" in owner.get("/concept/beta/state/").json()["discuss_refused"]
    drawn(owner, "beta", base=base, euros=REDRAW_PRICE)
    assert "Creator: is the door too small?\nYou: Paint the door red." in stand_in[-2]
    assert owner.get(f"/concept/beta/state/?draw={base}").json()["thread"][0]["closed"] is True
    assert drafting.source.world_state().discuss_spend == 0.0271
    base = owner.get("/concept/beta/state/").json()["newest"]
    settings.SCORE_MODE = settings.HOSTED
    try:
        owner.post("/concept/beta/discuss/", json.dumps({"base": base, "question": "why?", "euros": DISCUSS_PRICE}),
                   content_type="application/json")
        assert owner.get("/concept/beta/state/").json()["discussing"] is True
    finally:
        settings.SCORE_MODE = settings.LOCAL
    with override_settings(SCORE_SYNC_TOKEN=TOKEN):
        item = SyncRequest.objects.filter(kind=concepts.DISCUSS).order_by("-pk").first()
        assert listen.round_once(remote_of(hosted_client()), drafting.source) == [(item.pk, "done")]
    assert concepts.thread_of(drafting.source.world_state(), "beta", base)[0]["question"] == "why?"


# === the plan review and the environment's plan =======================================================================

@pytest.fixture
def planned(drafting, monkeypatch, tmp_path):
    """alpha's concept locked and its inventory read from it, plans reading the fixture's data."""
    from score.review import plans
    monkeypatch.setattr(plans, "DATA", drafting.data)
    monkeypatch.setattr(plans, "KEPT", tmp_path / "kept")
    monkeypatch.setattr(plans, "KEPT_INVENTORY", tmp_path / "kept-inventory")
    monkeypatch.setattr(plans, "KEPT_CONCEPT", tmp_path / "kept-concepts")
    return drafting


def plan_data(html):
    return json.loads(html.split('<script id="plan-data" type="application/json">')[1].split("</script>")[0])


def test_no_plan_before_the_inventory_counts_then_his_keep_is_his_own_where_the_plan_stage_reads_it(planned):
    """Owner, 2026-10-20 and 2026-10-21: no plan before it counts; no Approve; his Keep kept as edited and written where
    the plan stage reads it; anyone else refused. Break: pages/plans.py `asked_of` skips its owner check."""
    from score.review import plans
    owner = signed_in()
    html = owner.get("/plan/alpha/", follow=True).content.decode()
    assert "after the inventory" in html and "plan-drawing" not in html
    fixture.an_inventory_read(planned.store, planned.data, "alpha", fixture.concept_of(planned.store, "alpha"))
    planned.source.refresh()
    html = owner.get("/plan/alpha/", follow=True).content.decode()
    assert 'id="plan-drawing"' in html and "Approve" not in html
    assert "data-v>R1 1: no size</span>" in html  # its row gives no size: a gap shown, never hidden
    plan = plan_data(html)
    plan["items"][0][1] = 2.5
    refused = signed_in("joey2").post("/plan/alpha/keep/", json.dumps({"plan": plan}), content_type="application/json")
    assert refused.status_code == 403 and plans.current(planned.store, "alpha")["how"] != "edited"
    answer = owner.post("/plan/alpha/keep/", json.dumps({"plan": plan}), content_type="application/json")
    assert answer.status_code == 200, answer.content
    assert plans.current(planned.store, "alpha")["how"] == "edited"
    assert json.loads((plans.KEPT / "alpha.json").read_text())["items"][0][1] == 2.5


def test_an_inside_place_he_names_gets_a_card_and_a_concept_page(planned):
    """Break: score/review/plans.py keeps a named place's spaces (no `_`)."""
    from score.review import plans
    fixture.an_inventory_read(planned.store, planned.data, "alpha", fixture.concept_of(planned.store, "alpha"))
    planned.source.refresh()
    owner = signed_in()
    assert owner.post("/plan/alpha/named/", json.dumps({"names": ["Back Room", "loft"]}),
                      content_type="application/json").status_code == 200
    assert plans.named(planned.store, "alpha") == ["back_room", "loft"]
    plan = plans.current(planned.store, "alpha")["plan"]
    assert [hold["place"] for hold in plan["holds"]] == ["back_room", "loft"]
    kept = owner.post("/plan/alpha/keep/", json.dumps({"plan": plan}), content_type="application/json")
    assert kept.status_code == 200
    planned.source.refresh()
    assert 'href="/concept/loft/"' in signed_in("joey2").get("/places/?in=alpha").content.decode()
    assert owner.get("/concept/loft/").status_code == 200 and owner.get("/concept/attic/").status_code == 404


def drawing_png():
    buffer = io.BytesIO()
    Image.new("RGB", (600, 600), (255, 255, 255)).save(buffer, "PNG")
    return buffer.getvalue()


def test_make_plan_is_his_yes_at_the_price_shown_and_writes_the_plan_with_its_gaps(planned, monkeypatch):
    """A lamp row across the room (6 x 0.4 m at 100 units a metre) cuts the north spot off its door: a gap said plainly.
    Break: pages/plans.py `plan_write` sends EUR 0, not the price he saw."""
    from score.dashboard.pages import concepts
    from score.review import plan_drawing, plan_writing, plans, web
    monkeypatch.setattr(concepts, "in_background", concepts.applied_here)
    fixture.an_inventory_read(planned.store, planned.data, "alpha", fixture.concept_of(planned.store, "alpha"),
                              size=[6.0, 0.4, 0.8])
    planned.source.refresh()
    answer = {"outline": [[0, 0], [600, 0], [600, 400], [0, 400]],
              "items": [{"row": "r1", "box_2d": [180, 0, 220, 600], "tall": 0.8}], "people": [[100, 100], [500, 350]],
              "openings": [{"kind": "door", "at": [300, 400], "wide": 90, "angle": 0, "swing": "left", "sill": 0.0,
                            "head": 2.1, "to": "outside"}]}
    asked = []

    def written(store, place, euros, by):
        asked.append(euros)
        finished = {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(answer)}]}}
        record, = plan_writing.write(store, [place], by, ask=lambda body: ({"candidates": [finished],
                                                                            "usageMetadata": {}}, 1.0))
        return json.loads(plan_writing.said(record))
    monkeypatch.setattr(web, "plan_write", written)
    monkeypatch.setattr(plan_writing, "call_euros", lambda found: 0.04)
    monkeypatch.setattr(plan_drawing, "called", lambda wording, pictures, frame: (drawing_png(), 0.13, 1.0))
    monkeypatch.setattr(plan_writing, "cleared", lambda *found, **named: contextlib.nullcontext())
    monkeypatch.setattr("score.adapters.compute.require_cleared", lambda what, store=None: None)
    owner = signed_in()
    price = plan_writing.price(planned.store)
    assert f"EUR {price:.2f}" in owner.get("/plan/alpha/", follow=True).content.decode()
    sent = owner.post("/plan/alpha/write/", json.dumps({"euros": price}), content_type="application/json")
    assert sent.status_code == 200, sent.content
    assert asked == [price] and plans.current(planned.store, "alpha")["how"] == "written"
    planned.source.refresh()
    html = owner.get("/plan/alpha/", follow=True).content.decode()
    assert 'id="plan-write"' not in html and "the standing spot (north-west) cannot be reached on foot" in html


def a_draw(world, place, room):
    """A first draw of `place` in the store, its blob there, drawn on `room`."""
    from score.review import concepts
    path = world.root / f"{place}-draw.png"
    path.write_bytes(fixture.picture((7, 200, 9)))
    sha = fixture.file_hash(path)
    world.store.put_blob(path, sha)
    concepts.recorded(world.store, f"concepts/{place}/draws/2026-10-21T09-00-00.json",
                      {"place": place, "sha": sha, "name": f"{place}-concept.png", "by": "joey",
                       "at": "2026-10-21T09:00:00+00:00", "room": room})
    return sha


def hosted_page(world, tmp_path, monkeypatch, settings, page):
    """(`page` as the hosted cockpit serves it from an export of the fixture's store, the export's WorldState)."""
    from score.dashboard import state
    world.source.refresh()
    building.build(world.source, tmp_path / "export", MADE, 50, SPEND, world.root)
    source = ExportedSource(tmp_path / "export")
    monkeypatch.setattr(state, "source", lambda: source)
    settings.SCORE_MODE = "hosted"
    return signed_in("joey2").get(page).content.decode(), source.world_state()


def test_a_merged_scene_has_no_card_and_a_draw_on_a_moved_room_is_out_of_date_hosted_too(planned, tmp_path,
                                                                                         monkeypatch, settings):
    """Owner, 2026-10-21 ("nav again showed up here"; "all below would become need for redrawn"). Break:
    score/review/plans.py `moved_draws` never finds a room moved."""
    from score.review import plans
    fixture.an_inventory_read(planned.store, planned.data, "alpha", fixture.concept_of(planned.store, "alpha"))
    (planned.data / "places/within.json").write_text(json.dumps({"shells": {},
                                                                 "within": {"beta": {"within": "alpha"}}}))
    a_draw(planned, "beta", {"place": "beta", "x": 90.0, "y": 90.0, "w": 1.0, "d": 1.0})
    assert plans.room_of(planned.store, "beta") is not None
    html, shown = hosted_page(planned, tmp_path, monkeypatch, settings, "/places/?in=alpha")
    assert shown.plan_changed == ["beta"] and "beta" not in shown.concepts
    tile = html[html.index('href="/concept/beta/"'):].split('<div class="ptile-box">')[0]
    assert "plan changed" in tile and "<img" not in tile and "Review" not in tile
    (planned.data / "places/within.json").write_text(json.dumps({
        "shells": {}, "within": {}, "merged": {"beta": {"into": "alpha"}}}))
    settings.SCORE_MODE = "local"
    html, shown = hosted_page(planned, tmp_path / "again", monkeypatch, settings, "/places/")
    assert shown.removed == ["beta"] and 'href="/concept/beta/"' not in html and "beta" not in shown.concept_undrawn


def test_the_environments_plan_keeps_his_scene_times_and_its_sky_follows_from_the_setting(world, monkeypatch):
    """Owner 2026-10-21 (no fixed sky: a wording check): his time kept as edited, the overhead worked out from the
    setting; a daylight concept's night time moved to sun up and said; anyone else refused. Break:
    score/review/environment_plan.py keeps a daylight site's night time (`if True:`)."""
    from score.review import environment_plan, reading
    name = world.source.world_state().world
    owner = signed_in()
    html = owner.get(f"/environments/{name}/plan/").content.decode()
    assert 'data-place="base"' in html and "55.0000° N, 0.0000° E" in html  # where the setting puts it
    plan = {"maps": [{"on": "moon", "sites": [{"place": "base", "time": "2099-06-01T12:00:00Z"}]}]}
    refused = signed_in("joey2").post(f"/environments/{name}/plan/keep/", json.dumps({"plan": plan}),
                                      content_type="application/json")
    assert refused.status_code == 403
    assert owner.post(f"/environments/{name}/plan/keep/", json.dumps({"plan": plan}),
                      content_type="application/json").status_code == 200
    assert environment_plan.current(world.store, name)["how"] == "edited"
    base = environment_plan.site_of(world.store, "base", name)
    assert base["time"] == "2099-06-01T12:00:00Z" and base["overhead"]["bodies"]
    world.source.refresh()
    page = owner.get(f"/environments/{name}/plan/").content.decode()
    assert ">Sky<" not in page and "Overhead, from the physics: Sun" in page
    monkeypatch.setattr(reading, "concept_light", lambda store, place: {"rows": {}, "scene": {
        "daylight": True, "unseen": False, "unseen_colour": ""}} if place == "base" else None)
    night = {"maps": [{"on": "moon", "sites": [{"place": "base", "time": "2099-06-16T12:00:00Z"}]}]}
    owner.post(f"/environments/{name}/plan/keep/", json.dumps({"plan": night}), content_type="application/json")
    base = environment_plan.site_of(world.store, "base", name)
    assert base["written_time"] == "2099-06-16T12:00:00Z" and base["time"] != base["written_time"]


# === the environment concept ==========================================================================================

ASK_PRICE = 0.05
ENVIRONMENT = "/environments/world1/"
SUN = {"name": "Sun", "kelvin": 5800, "lux": 100000, "latitude": 52.0, "tilt_deg": 23.44, "day_hours": 24,
       "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}
HOUSE = {"bodies": [], "plots": [{"name": "Meadow", "gravity": 9.81}], "lights": [SUN],
         "backdrops": [{"name": "Sky", "lux": 10000}],
         "sites": [{"place": "house", "on": "meadow", "x": 0, "y": "0", "height_m": 0}]}


def posted(owner, path, body):
    return owner.post(f"{ENVIRONMENT}{path}/", json.dumps(body), content_type="application/json")


@pytest.fixture
def asker(world, monkeypatch):
    """The ask's own process run in-process with a stand-in model, the bucket a folder; [each question asked]."""
    from score.dashboard.pages import concepts
    from score.review import concepts as drawing
    from score.review import environment_concept, web
    from score.store import runtime_store
    asked = []
    monkeypatch.setattr("score.adapters.compute.require_books", lambda what: None)
    monkeypatch.setattr(environment_concept, "ask_euros", lambda *given: ASK_PRICE)
    monkeypatch.setattr(concepts, "in_background", concepts.applied_here)
    monkeypatch.setattr(drawing, "offsite_store",
                        lambda: runtime_store.FolderStore(world.source.store.cache.parent / "bucket"))
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


def test_environment_1s_concept_is_todays_data_locked_each_body_said_from_the_physics(world):
    """The Moon orbits Earth every 27.3 days, gravity 1.62; Mars a year of 687 days, a day of 24.6 h, 3.7 (the reference
    table). The page's questions are the store's. Break: pages/setting_picture.py `every` words a period in hours."""
    from score.dashboard.pages import environment
    from score.review import environment_concept
    html = signed_in().get(ENVIRONMENT).content.decode()
    assert ">locked</b>" in html and "Unlock" in html
    assert "data-f=" not in html  # owner 2026-10-21: fields only unlocked
    assert "orbits Earth every 27 days, one face to Earth; gravity 1.6 m/s²" in html
    assert "orbits Sun every 687 days, a day of 25 h; gravity 3.7 m/s²" in html
    assert [(name, question) for name, _, question in environment.QUESTIONS] == list(environment_concept.QUESTIONS)
    assert [environment.steps_around(name)["number"] for name, _, _ in environment.QUESTIONS] == [1, 2, 3, 4, 5]
    assert signed_in("ann").get("/environments/world9/").status_code == 404


def test_a_house_setting_is_its_plot_from_above_with_its_suns_path_where_overhead_puts_it():
    """The page's sum agrees with score/review/overhead.py at three moments. Break: pages/setting_picture.py `far_way`
    drops the light's tilt (season 0)."""
    from score.dashboard.pages import setting_picture
    from score.review import overhead, setting
    house = setting.checked(HOUSE)
    found = setting_picture.view_of(house, {"house": "2024-03-20T12:00:00Z"}, {"house": "House"})
    assert len(found["pictures"]) == 1 and 'class="sp-body"' not in found["pictures"][0]["svg"]  # no body
    assert [(card["name"], card["kind"]) for card in found["cards"]] == [
        ("Sun", "light"), ("Sky", "backdrop"), ("Meadow", "ground")]
    assert found["cards"][2]["sites"] == ["House"]
    light = house["lights"][0]
    for when in ("2024-03-20T12:00:00Z", "2024-05-02T07:30:00Z", "2024-12-21T15:00:00Z"):
        seen_now = overhead.far_light(light, when)
        since = overhead.day_of(when) - overhead.day_of(light["equinox"])
        assert setting_picture.far_way(light, since) == pytest.approx((seen_now["azimuth"], seen_now["altitude"]),
                                                                      abs=0.01)


def test_unlock_asks_to_be_sure_and_puts_every_draw_out_of_date(world, asker):
    """Break: pages/environment.py `save` unlocks without `sure`."""
    from score.review import concepts as drawing
    from score.review import environment_concept
    owner = signed_in()
    assert posted(owner, "save", {"locked": False}).status_code == 409
    assert not environment_concept.unlocked(world.source.store)
    assert posted(owner, "save", {"sure": True, "locked": False}).status_code == 200
    assert environment_concept.unlocked(world.source.store)
    assert drawing.waits(world.source.store, "alpha") == "waits for the environment concept to be locked"
    html = owner.get(ENVIRONMENT).content.decode()
    assert "Send, EUR 0.05" in html and "Question 1 of 5" in html


def test_save_send_take_and_lock_reach_the_store_at_the_price_shown_and_only_for_the_owner(world, asker):
    """Break: score/review/web.py `environment_ask` drops its price comparison."""
    from score.review import environment_concept
    owner = signed_in()
    posted(owner, "save", {"sure": True, "locked": False})
    concept = environment_concept.newest(world.source.store, "world1")["concept"]
    assert posted(owner, "save", {"concept": {**concept, "style": "Cold steel"}, "locked": False}).status_code == 200
    assert environment_concept.newest(world.source.store, "world1")["concept"]["style"] == "Cold steel"
    posted(owner, "ask", {"topic": "style", "answer": "brighter", "euros": 0.04})
    cheap = SyncRequest.objects.get(kind="environment-ask")
    assert cheap.state == "refused" and "measured price" in cheap.detail and asker == []
    cheap.delete()
    answer = posted(owner, "ask", {"topic": "style", "answer": "brighter", "euros": ASK_PRICE})
    assert answer.status_code == 200 and "brighter" in asker[0] and "Cold steel" in asker[0]
    item = SyncRequest.objects.get(kind="environment-ask")
    assert item.state == "done" and json.loads(item.detail)["proposed"] == {"style": "Bright frontier"}
    assert posted(owner, "take", {"ask": item.pk}).status_code == 200
    assert environment_concept.newest(world.source.store, "world1")["concept"]["style"] == "Bright frontier"
    assert posted(owner, "save", {"concept": concept, "locked": True}).status_code == 200
    assert environment_concept.in_force(world.source.store)["style"] == concept["style"]
    assert posted(owner, "ask", {"topic": "style", "answer": "x", "euros": ASK_PRICE}).status_code == 409  # locked
    assert posted(signed_in("mallory"), "save", {"sure": True, "locked": False}).status_code == 403
    assert posted(signed_in("eve"), "ask", {"topic": "style", "answer": "x", "euros": ASK_PRICE}).status_code == 403


def test_a_new_reference_goes_to_the_bucket_never_the_repository_and_its_bytes_are_dropped_once_read(world, asker):
    """Break: pages/environment.py `requests_of` keeps an answered picture's bytes."""
    from score.review import concepts as drawing
    from score.store import runtime_store
    owner = signed_in()
    posted(owner, "save", {"sure": True, "locked": False})
    data = base64.b64encode(a_png()).decode()
    answer = posted(owner, "reference", {"name": "dock.png", "data": data, "shows": "the dock's look", "place": "beta"})
    assert answer.status_code == 200, answer.content
    bucket = runtime_store.FolderStore(world.source.store.cache.parent / "bucket")
    assert "dock.png" in json.loads(bucket.read_bytes("references/index.json"))
    world.source.refresh()
    assert 'data-picture="{home}/references/dock.png"' in owner.get(ENVIRONMENT).content.decode()
    assert SyncRequest.objects.get(kind="environment-reference").payload["data"] == ""
    assert drawing.references_of(world.source.store, "beta") == []  # unlocked: the draws read nothing new yet


def test_a_hosted_save_shows_at_once_and_the_listener_applies_it(world, asker, settings, monkeypatch):
    """And an export made before the environment concept takes no click. Break: pages/environment.py `shown` ignores his
    saves since the export."""
    from score.dashboard.pages import environment
    from score.review import environment_concept
    owner = signed_in()
    settings.SCORE_MODE = settings.HOSTED
    try:
        assert posted(owner, "save", {"sure": True, "locked": False}).status_code == 200
        assert ">unlocked</b>" in owner.get(ENVIRONMENT).content.decode()
        assert posted(owner, "ask", {"topic": "style", "answer": "x", "euros": ASK_PRICE}).status_code == 409
    finally:
        settings.SCORE_MODE = settings.LOCAL
    with override_settings(SCORE_SYNC_TOKEN=TOKEN):
        assert listen.round_once(remote_of(hosted_client()), world.source) == [(SyncRequest.objects.get().pk, "done")]
    assert environment_concept.unlocked(world.source.store)
    SyncRequest.objects.all().delete()
    monkeypatch.setattr(environment, "shown", lambda world_state: {})
    assert posted(owner, "save", {"sure": True, "locked": False}).status_code == 409
    assert SyncRequest.objects.count() == 0


# === the library ======================================================================================================

MATERIAL = b"""#usda 1.0
def Material "steel" {
    custom string score:token = "steel"
    def Shader "surface" {
    color3f inputs:diffuseColor = (0.5, 0.25, 0.125)
    float inputs:metallic = 1
    float inputs:roughness = 0.35
} }"""
SKY = b"""#usda 1.0
def Xform "sky" {
    def DomeLight "Environment" {
        color3f inputs:color = (0.35, 0.48, 0.79)
        float inputs:intensity = 0.22
    }
    def Mesh "Dome" {
    }
}"""
LAMPS = json.dumps({"place": "alpha", "lamps": [
    {"path": "/alpha/Lights/light_2", "spot": [1.0, 3.0, -2.0], "intensity": 3.0, "scale": 2.0},
    {"path": "/alpha/Lights/sun_1", "spot": None, "sun": True, "intensity": 1.0, "scale": 1.0}]}).encode()
DEMO = {"example": "the alpha's two beds", "view": "plan", "bounds": [0, 0, 2, 1],
        "steps": [{"label": "The beds",
                   "shapes": [{"kind": "area", "points": [[0, 0], [1, 0], [1, 1]], "tone": "ground"}]}],
        "numbers": [{"label": "plants", "value": 9, "unit": "", "tip": "plants laid"}]}
SETTINGS = json.dumps({"emitter": "ring", "emitter_size": [4.2, 2.5, 0.6], "count": 15000, "lifetime": 10.0,
                       "loop": 10.0, "speed": [3, 5], "from": "footage: " + "a long source in words " * 20}).encode()
CLIP = b"\x00\x00\x00\x18ftypmp42 a clip's bytes"
# The library's own lock and withdraw, as small as the test needs: the entry's state, and the index rewritten.
FAKE_COMMAND = """
import json, pathlib, sys
root = pathlib.Path.cwd()
action, addresses = sys.argv[1], sys.argv[2:]
for address in addresses:
    kind, rest = address.split("/")
    entry_id, version = rest.split("@")
    path = root / "entries" / kind / entry_id / version / "entry.json"
    record = json.loads(path.read_text())
    wanted = {"lock": "draft", "withdraw": "locked", "index": None}[action]
    if record["state"] != wanted:
        sys.exit(f"{address}: is {record['state']}")
    record["state"] = "locked" if action == "lock" else "withdrawn"
    path.write_text(json.dumps(record))
(root / "index" / "catalogue.json").write_text(json.dumps({"action": action, "addresses": addresses}))
print(f"{action} {len(addresses)}")
"""


def glb():
    """A GLB of one triangle's facts: its JSON chunk, no buffers."""
    facts = json.dumps({"asset": {"version": "2.0"}, "accessors": [{"count": 3}],
                        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}]}).encode()
    facts += b" " * (-len(facts) % 4)
    return struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(facts)) + struct.pack("<II", len(facts), 0x4E4F534A) + facts


def blob(blobs, data):
    """Put bytes into the blob folder; their sha."""
    sha = hashlib.sha256(data).hexdigest()
    path = blobs / "blobs" / sha[:2] / sha
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return sha


def entry(root, blobs, kind, entry_id, state="draft", place="alpha", node="closeup@alpha", files=None, **more):
    """Write one entry.json with a picture; the record."""
    described = {"preview.png": {"role": "picture", "bytes": 1, "sha256": blob(blobs, fixture.picture())}}
    for name, (role, data) in (files or {}).items():
        described[name] = {"role": role, "bytes": len(data), "sha256": blob(blobs, data)}
    record = {"schema": "score-lib-entry/1", "address": f"{kind}/{entry_id}@1", "id": entry_id, "kind": kind,
              "version": 1, "state": state,
              "title": more.pop("title", entry_id.split(".")[0].replace("_", " ").capitalize()), "files": described,
              "picture": {"file": "preview.png"}, "licence": {"spdx": "MIT", "commercial_ok": True},
              "provenance": {"world": "world1", "place": place, "node": node, "commit": "c" * 40},
              "seen_in": [place] if place else [], "tags": {"model": ["piece"]}, "requires": [], **more}
    path = root / "entries" / kind / entry_id / "1" / "entry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record))
    return record


@pytest.fixture
def shelf(tmp_path):
    """A tiny library of 15 entries in a git folder with a bare remote, and its blob folder."""
    root, blobs = tmp_path / "lib", tmp_path / "blobs"
    entry(root, blobs, "model", "lamp_post.alpha",
          files={"web/lamp_post.glb": ("web3d", glb()), "web/lamp_light.glb": ("web3d", glb() + b" " * 4),
                 "closeup.png": ("closeup", fixture.picture((200, 60, 30)))},
          web3d={"file": "web/lamp_post.glb", "light": "web/lamp_light.glb", "objects": 3, "triangles": 1},
          score=42, score_parts=[{"name": "shape", "value": 30, "how": "edges"},
                                 {"name": "likeness", "value": None, "how": "needs a paid judge"}],
          refine_options=["remesh", {"id": "repaint", "label": "paint it again"}])
    entry(root, blobs, "model", "crate", state="locked", place="beta", node="assembly@beta", score=0.91,
          score_parts={"finish": 0.6})
    entry(root, blobs, "model", "wrench", tags={"model": ["prop"]}, files={"clip/clip.mp4": ("clip", CLIP)},
          clip={"file": "clip/clip.mp4", "shelf": "model", "frames": 96, "seconds": 4.0})
    entry(root, blobs, "surface", "brushed_steel.alpha", node=None,
          tags={"family": ["steel"], "recipe": ["bare_metal"]},
          files={"material.usda": ("usd", MATERIAL), "print.png": ("texture", fixture.picture())})
    entry(root, blobs, "sound", "hum.alpha", files={"audio/hum_1.ogg": ("audio", b"OggS one"),
                                                   "audio/hum_2.ogg": ("audio", b"OggS two")}, score=95,
          score_parts=[{"name": "loudness", "measured": -2.0, "unit": "LU off target", "value": 90,
                        "how": "integrated loudness -22.0 LUFS against its shot target -20.0 LUFS"},
                       {"name": "length", "measured": 4.3, "unit": "s", "value": 100, "how": "within"}])
    entry(root, blobs, "effect", "devil.alpha", files={"settings.json": ("record", SETTINGS)})
    entry(root, blobs, "light", "sky.alpha", files={"sky.usda": ("usd", SKY)})
    entry(root, blobs, "layer", "light.alpha", title="Alpha light layer", files={"lamps.json": ("record", LAMPS)})
    entry(root, blobs, "kit", "alpha", files={"web3d/light.glb": ("web3d", glb() + b" " * 8)},
          web3d={"light": "web3d/light.glb", "objects": 12}, tags={"place_kind": ["inside", "moon"]})
    entry(root, blobs, "algorithm", "surface_recipes", title="Surface functions: material recipes and wear",
          provenance={"stage": "surfaces-bake", "nodes": ["surfaces-bake@alpha", "surfaces-bake@beta"]},
          requires=["algorithm/terrain@1"], score=25, files={"presets/world1/data/surface_recipes/alpha.json":
                                                              ("record", b"{}")})
    entry(root, blobs, "ground", "earth.alpha")
    entry(root, blobs, "layer", "base.alpha")
    entry(root, blobs, "character", "walker", place=None, node="people-walker", files={"body.glb": ("gltf", glb())})
    entry(root, blobs, "place", "alpha", node="assembly@alpha", requires=["model/lamp_post.alpha@1"])
    entry(root, blobs, "concept", "alpha", title="alpha concept", node=None, tags={"place": ["alpha"]})
    (root / "index").mkdir()
    (root / "index" / "catalogue.json").write_text("{}")
    command = tmp_path / "score_lib_command.py"
    command.write_text(FAKE_COMMAND)
    git = lambda *arguments, where=root: subprocess.run(["git", "-C", str(where), *arguments], check=True,  # noqa: E731
                                                         capture_output=True)
    subprocess.run(["git", "init", "-q", "--bare", str(tmp_path / "remote.git")], check=True)
    git("init", "-q")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "test")
    git("add", ".")
    git("commit", "-q", "-m", "entries")
    git("remote", "add", "origin", str(tmp_path / "remote.git"))
    git("push", "-q", "-u", "origin", "HEAD")
    with override_settings(SCORE_LIB_ROOT=str(root), SCORE_LIB_BLOBS_DIR=str(blobs),
                           SCORE_LIB_COMMAND=f"{sys.executable} {command}"):
        yield root


def item_data(html):
    """The viewer's JSON the item page carries (item3d.js reads it), or None."""
    found = re.search(r'<script id="item-data" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(found.group(1)) if found else None


def an_item_page(owner, path):
    """An item page that keeps to the 40-word rule and shows no file list, ids or blobs (owner rules, wording checks:
    numbers not prose #42, no file list on an item page 2026-10-20)."""
    html = owner.get(path).content.decode()
    assert len(prose(html)) <= WORD_BUDGET, (path, prose(html))
    for gone in ('class="files"', 'class="ids"', "preview.png", "<table", "sha256"):
        assert gone not in html, (path, gone)
    return html


def number_shown(html, label, value):
    return re.search(rf'<div class="num-label">{re.escape(label)}</div>\s*<div class="num-value" data-v>'
                     rf'{re.escape(value)}', html) is not None


def test_the_library_is_its_kinds_counted_from_its_entries_with_no_entry_until_a_branch_opens(world, shelf):
    """By hand from the shelf: 3 models, 2 surfaces (steel and the recipes' made-by-code folder), 3 scenes (the place,
    its concept, its base layer); no Algorithms, Films, Ground or Layers shelf; at most 40 words; the library counts 15
    entries. Break: state/library.py `shelf_of` puts every algorithm on its own shelf."""
    from score.dashboard.state import library as lib
    html = signed_in().get("/library/").content.decode()
    for kind, count in (("Models", 3), ("Surfaces", 2), ("Kits", 1), ("Effects", 1), ("Skies", 1), ("Lamps", 1),
                        ("Sound", 1), ("Physics", 0), ("Scenes", 3)):
        assert f'<span class="node-label" data-v>{kind}</span><span class="node-count" data-v>{count}</span>' in html
    for gone in ("Algorithms", "Films", "Ground", "Layers"):
        assert f"data-v>{gone}<" not in html
    assert "Lamp post" not in html and len(prose(html)) <= WORD_BUDGET
    found = screens.library_counts(lib.library())
    kinds = {row["kind"]: row for row in found["kinds"]}
    assert found["total"] == 15 and kinds["model"]["count"] == 3 and kinds["model"]["locked"] == 1
    assert kinds["model"]["pictured"] == 3 and kinds["model"]["scored"] == 2
    assert screens.library_counts(None) == {"kinds": [], "total": 0}


def test_a_branch_answers_its_children_a_page_at_a_time_code_in_its_works_folder_a_place_with_its_layers(world, shelf,
                                                                                                         monkeypatch):
    """Break: pages/library.py `children` never adds the "more" branch (`left = 0`)."""
    from score.dashboard.pages import library as pages_library
    web = api()

    def children(node):
        return web.get("/api/library/children", params={"node": node}).json()
    assert [(node["label"], node["count"]) for node in children("surface")] == [("Made by code", 1),
                                                                                ("Brushed steel", None)]
    assert [node["href"] for node in children("surface/made_by_code")] == ["/library/algorithm/surface_recipes/1/"]
    assert [node["href"] for node in children("light")] == ["/library/light/sky.alpha/1/"]
    assert [node["href"] for node in children("place/alpha")] == ["/library/place/alpha/1/",
                                                                  "/library/concept/alpha/1/",
                                                                  "/library/layer/base.alpha/1/"]
    assert [(node["label"], node["count"], node["tone"]) for node in children("model/piece")] == [
        ("Crate", 91, "done"), ("Lamp post", 42, "review")]
    monkeypatch.setattr(pages_library, "PAGE", 1)
    first = children("model/piece")
    assert [node["label"] for node in first] == ["Crate", "more"] and first[1]["count"] == 1
    assert [node["label"] for node in web.get(first[1]["children_url"]).json()] == ["Lamp post"]
    assert web.get("/api/library/children", params={"node": "nowhere"}).status_code == 404


def named_entries(count, stem, place="alpha"):
    from score.dashboard.state import library as lib
    return [lib.LibraryEntry(address=f"model/{stem}_{rank}.{place}@1", kind="model", entry_id=f"{stem}_{rank}.{place}",
                             version=1, title=stem, state="draft", place=place, tags={"model": ["piece"]})
            for rank in range(count)]


def node_of(tree, node_id):
    for node in tree:
        if node["id"] == node_id:
            return node
        found = node_of(node["children"], node_id)
        if found:
            return found
    return None


def test_folders_split_by_name_then_place_hold_one_newest_locked_version_and_no_withdrawn_entry():
    """50 upper walls split by place (30, 20), 4 lower apart, 2 singles to other; of versions 1, 2 locked and 3 draft
    the item is 2; a withdrawn one in no folder. Break: state/library_tree.py `folders` keeps withdrawn entries."""
    from score.dashboard.state.library_tree import folders
    made = folders([*named_entries(30, "wall_upper_plain"), *named_entries(20, "wall_upper_plain", "beta"),
                    *named_entries(4, "wall_lower"), *named_entries(1, "lamp"), *named_entries(1, "crate")])
    assert [child["id"] for child in node_of(made["tree"], "model/wall")["children"]] == [
        "model/wall/wall_lower", "model/wall/wall_upper"]
    upper = node_of(made["tree"], "model/wall/wall_upper")["children"]
    assert [(child["label"], child["count"]) for child in upper] == [("from alpha", 30), ("from beta", 20)]
    assert node_of(made["tree"], "model/other")["count"] == 2
    first = named_entries(1, "crate")[0]
    versions = [first.model_copy(update={"version": 1, "state": "locked"}),
                first.model_copy(update={"version": 2, "state": "locked"}),
                first.model_copy(update={"version": 3, "state": "draft"})]
    assert [found.version for found in folders(versions)["members"]["model"]] == [2]
    entries = named_entries(2, "crate")
    entries[1] = entries[1].model_copy(update={"state": "withdrawn"})
    assert node_of(folders(entries)["tree"], "model")["count"] == 1


def test_an_item_plays_live_in_its_kinds_viewer_from_its_own_files(world, shelf):
    """Each viewer's facts read from the entry's own files: the model's light copy then whole copy; the surface's colour
    and roughness from its material; a lamp's power 3 x 2 = 6; the sound's -22.0 LUFS and 4.3 s; the effect's settings
    without its sources in words; a kit cut open with its 12 pieces; an old preview clip never played; scores only where
    they mean something. Break: state/library.py reads a lamp's power as its intensity alone."""
    from score.dashboard.state import library as lib
    owner = signed_in()
    lamp = an_item_page(owner, "/library/model/lamp_post.alpha/1/")
    found = lib.library().entry("model/lamp_post.alpha@1")
    viewer = item_data(lamp)
    assert viewer["mode"] == "copy" and viewer["light"] == f"/library-files/files/{found.web3d_light.sha}"
    assert viewer["full"] == f"/library-files/files/{found.web3d.sha}" and "<video" not in lamp
    assert f"/library-files/pictures/{found.closeup.sha}.jpg" in lamp  # beside it: the close-up it was made from
    assert number_shown(lamp, "parts", "3") and number_shown(lamp, "score", "42")
    steel = item_data(an_item_page(owner, "/library/surface/brushed_steel.alpha/1/"))
    assert steel["token"] == "steel" and steel["finish"]["colour"] == [0.5, 0.25, 0.125]
    assert steel["finish"]["roughness"] == 0.35 and steel["palette"]["sign-gold"].startswith("#")
    lamps = an_item_page(owner, "/library/layer/light.alpha/1/")
    assert [(each["type"], each["name"], each["power"]) for each in item_data(lamps)["lamps"]] == [
        ("point", "light_2", 6.0), ("sun", "sun_1", 1.0)]
    hum = an_item_page(owner, "/library/sound/hum.alpha/1/")
    assert hum.count("data-wave=") == 2 and number_shown(hum, "loudness", "-22.0 <small>LUFS</small>")
    assert number_shown(hum, "length", "4.3 <small>s</small>")
    devil = item_data(an_item_page(owner, "/library/effect/devil.alpha/1/"))
    assert devil["settings"]["count"] == 15000 and "from" not in devil["settings"]
    sky = item_data(an_item_page(owner, "/library/light/sky.alpha/1/"))
    assert sky["mode"] == "sky" and sky["sky"] == "dome"
    kit = an_item_page(owner, "/library/kit/alpha/1/")
    assert item_data(kit)["mode"] == "kit" and item_data(kit)["inside"] and number_shown(kit, "pieces", "12")
    wrench = an_item_page(owner, "/library/model/wrench/1/")
    assert "<video" not in wrench and not any(each.name.endswith(".mp4")
                                              for each in lib.shown_files(lib.library().entry("model/wrench@1")))
    recipes = an_item_page(owner, "/library/algorithm/surface_recipes/1/")
    assert "score" not in recipes.split('class="nums"')[-1].split("item-actions")[0].lower()  # its score means nothing
    crate = an_item_page(owner, "/library/model/crate/1/")
    assert item_data(crate) is None and 'value="withdraw"' in crate
    assert "data-post" not in an_item_page(signed_in("guest"), "/library/model/crate/1/")  # only the owner decides
    assert owner.get("/library/model/nothing/1/").status_code == 404


def test_an_algorithm_shows_its_work_on_a_real_example_else_why_not(world, shelf):
    """Break: state/library.py `demo` returns None."""
    from django.conf import settings
    owner = signed_in()
    assert "surfaces bake &times; 2" in an_item_page(owner, "/library/algorithm/surface_recipes/1/")
    demos = settings.SCORE_PROPS_HOME / "cache" / "library" / "demos.json"
    demos.parent.mkdir(parents=True, exist_ok=True)
    demos.write_text(json.dumps({"surface_recipes": DEMO}))
    shown = an_item_page(owner, "/library/algorithm/surface_recipes/1/")
    assert ">The beds<" in shown and number_shown(shown, "plants", "9")
    demos.write_text(json.dumps({"surface_recipes": {"missing": "no example kept"}}))
    assert "no example of its work is here yet: no example kept" in an_item_page(
        owner, "/library/algorithm/surface_recipes/1/")


def test_a_place_shows_its_3d_copy_once_made_and_a_lost_copy_is_said_missing(world, shelf, tmp_path):
    """A loss mark of other bytes is not this file; of its own sha it is, and the export carries it. Break:
    state/library.py `missing` reads any `.lost` mark as lost, whatever sha it names."""
    from score.dashboard.state import library as lib
    owner = signed_in()
    assert "<iframe" not in an_item_page(owner, "/library/place/alpha/1/")
    copy = world.source.web_copies / "alpha"
    copy.mkdir(parents=True)
    (copy / "alpha.json").write_text(json.dumps({"objects": []}))
    assert '<iframe src="/view/alpha?embed=1"' in an_item_page(owner, "/library/layer/base.alpha/1/")
    shown = lib.library()
    kit = shown.entry("kit/alpha@1")
    (shelf.parent / "blobs" / "blobs" / kit.web3d_light.sha[:2] / kit.web3d_light.sha).unlink()
    marked = shown.cache / "kit/alpha/1/web3d/light.glb.lost"
    marked.parent.mkdir(parents=True)
    marked.write_text("0" * 64)
    page = an_item_page(owner, "/library/kit/alpha/1/")
    assert item_data(page) is None and ">3D not here<" in page
    marked.write_text(kit.web3d_light.sha)
    assert ">3D missing<" in an_item_page(owner, "/library/kit/alpha/1/")
    building.build(world.source, tmp_path / "home/export/one", MADE, 50, SPEND, world.root)
    rows = json.loads((tmp_path / "home/export/one" / lib.EXPORT_ROWS).read_text())
    assert next(row["missing"] for row in rows if row["address"] == "kit/alpha@1") == ["web3d/light.glb"]


def test_the_file_routes_serve_only_files_an_entry_lists(world, shelf):
    """Break: state/library.py `blob` serves any sha in the blob folder."""
    from score.dashboard.state import library as lib
    web = api()
    found = lib.library().entry("character/walker@1")
    assert web.get(f"/library-files/thumbs/{found.picture}.jpg").headers["content-type"] == "image/jpeg"
    assert web.get(f"/library-files/view/{found.glb.sha}.json").json()["triangles"] == 1
    assert web.get(f"/library-files/view/{found.glb.sha}-light.glb").status_code == 404
    assert web.get(f"/library-files/files/{'0' * 64}").status_code == 404
    unlisted = blob(shelf.parent / "blobs", b"bytes no entry lists")
    assert web.get(f"/library-files/files/{unlisted}").status_code == 404
    assert signed_in("guest2").get("/library/model/crate/1/3d/").status_code == 404


def test_the_owner_refines_locks_and_withdraws_and_no_one_else_nor_an_agent(world, shelf, monkeypatch):
    """Refine items into the basket, once each; a lock committed and pushed with the library's own command; a lock of a
    locked entry refused; an agent never locks; hosted, a withdraw is queued and applied for the owner only. Break:
    pages/library_actions.py `carried_out` skips `actions.agent_started`."""
    from score.dashboard.state import library as lib
    web = api()
    said = web.post("/api/library/refine", json={"addresses": ["model/lamp_post.alpha@1", "model/crate@1"]}).json()
    assert said["added"] == 2
    assert web.post("/api/library/refine", json={"addresses": ["model/crate@1"]}).json()["added"] == 0  # already in
    refused = web.post("/api/library/refine", json={"addresses": ["model/crate@1"], "option": "repaint"})
    assert refused.status_code == 400 and "no refine option" in refused.json()["detail"]
    assert api("guest").post("/api/library/refine", json={"addresses": ["model/crate@1"]}).status_code == 403
    assert RefineItem.objects.count() == 2
    assert library_actions.ask("joey", "lock", ["model/crate@1"], hosted=False).startswith("refused")
    monkeypatch.setattr(actions, "agent_started", lambda: True)
    assert "an agent never locks" in library_actions.ask("joey", "lock", ["model/lamp_post.alpha@1"], hosted=False)
    assert lib.library().entry("model/lamp_post.alpha@1").state == "draft"
    monkeypatch.setattr(actions, "agent_started", lambda: False)
    assert api("guest2").post("/api/library/ask", json={"action": "lock", "addresses": ["model/crate@1"]}
                              ).status_code == 403
    answer = web.post("/api/library/ask", json={"action": "lock",
                                                "addresses": ["model/lamp_post.alpha@1", "sound/hum.alpha@1"]})
    assert "locked 2 entries" in answer.json()["said"]
    assert lib.library().entry("model/lamp_post.alpha@1").state == "locked"
    remote = subprocess.run(["git", "-C", str(shelf.parent / "remote.git"), "log", "-1", "--format=%s"],
                            capture_output=True, text=True).stdout
    assert remote.startswith("lock: 2 entries, the owner's decision on the cockpit")
    assert library_actions.ask("joey", "withdraw", ["model/crate@1"], hosted=True).startswith("queued")
    queued = SyncRequest.objects.get(kind="library")
    assert library_actions.waiting() == {"model/crate@1": "withdraw"}
    assert applying.apply({"kind": "library", "user": "mallory", "payload": queued.payload}, world.source
                          ).state == "refused"
    assert applying.apply({"kind": "library", "user": "joey", "payload": queued.payload}, world.source).state == "done"
    assert lib.library().entry("model/crate@1").state == "withdrawn"


def test_the_export_carries_the_library_to_a_hosted_cockpit_light_copies_only(world, shelf, tmp_path):
    """Twice the same; every picture; 5 library files (two takes, two light copies, the print): never a whole copy or an
    old clip. Break: state/library.py `export_three_d` adds each entry's whole web copy."""
    from score.dashboard.state import library as lib
    first = building.build(world.source, tmp_path / "home/export/one", MADE, 50, SPEND, world.root)
    again = building.build(world.source, tmp_path / "home/export/two", MADE, 50, SPEND, world.root)
    assert first["written"] == again["written"] and "library/entries.json" in first["written"]
    pictures = {each.picture for each in lib.library().entries()}
    assert all(f"files/{sha}-360.jpg" in first["written"] for sha in pictures)
    assert sum(path.startswith("library/files/") for path in first["written"]) == 5
    (tmp_path / "home/export/current").symlink_to("one")
    with override_settings(SCORE_MODE="hosted", SCORE_HOME=tmp_path / "home", SCORE_LIB_ROOT=None):
        hosted = lib.library()
        assert isinstance(hosted, lib.ExportedLibrary) and len(hosted.entries()) == 15
        web = api("joey3")
        assert [node["label"] for node in web.get("/api/library/children", params={"node": "model/piece"}).json()
                ] == ["Crate", "Lamp post"]
        pages = signed_in("joey4")
        lamp = item_data(pages.get("/library/model/lamp_post.alpha/1/").content.decode())
        assert lamp["light"] == f"/library-files/files/{hosted.entry('model/lamp_post.alpha@1').web3d_light.sha}"
        assert lamp["full"] is None  # light only
        assert "/3d/" not in pages.get("/library/character/walker/1/").content.decode()


HOSTED_CHILD = """
import json, sys
import django
django.setup()
from django.core.management import call_command
call_command("migrate", interactive=False, verbosity=0)
from django.contrib.auth import get_user_model
from django.test import Client
from score.dashboard.pages import library
from score.dashboard.state import library as lib
client = Client()
client.force_login(get_user_model().objects.create_user("joey", password="a long enough password"))
codes = [client.get(page, HTTP_HOST="127.0.0.1").status_code for page in (
    "/library/", "/library/model/crate/1/", "/library/model/lamp_post.alpha/1/",
    "/library/surface/brushed_steel.alpha/1/", "/library/sound/hum.alpha/1/", "/library/effect/devil.alpha/1/",
    "/library/light/sky.alpha/1/",
    "/library/algorithm/surface_recipes/1/", "/library/place/alpha/1/")]
branch = [node["label"] for node in library.children(lib.library(), "model")]
import score.dashboard.site.asgi  # what the hosted image serves
heavy = [name for name in sys.modules if name.startswith("score.") and not name.startswith("score.dashboard")]
print(json.dumps({"codes": codes, "branch": branch, "heavy": heavy}))
"""


def test_a_hosted_library_screen_imports_nothing_the_hosted_image_lacks(world, shelf, tmp_path):
    """Break: pages/library.py imports score.stages."""
    home = tmp_path / "hosted"
    building.build(world.source, home / "export" / "one", MADE, 50, SPEND, world.root)
    (home / "export" / "current").symlink_to("one")
    env = {**os.environ, "SCORE_DASHBOARD_MODE": "hosted", "SCORE_DASHBOARD_HOME": str(home), "SCORE_LIB_ROOT": "",
           "DJANGO_SETTINGS_MODULE": "score.dashboard.site.settings", "PYTHONPATH": str(REPO)}
    done = subprocess.run([sys.executable, "-c", HOSTED_CHILD], env=env, cwd=tmp_path, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr[-3000:]
    assert json.loads(done.stdout.strip().splitlines()[-1]) == {"codes": [200] * 9, "branch": ["Pieces", "Props"],
                                                                "heavy": []}


def test_a_library_with_no_blob_folder_reads_its_pictures_from_the_store_sides_cache(shelf, tmp_path):
    """Break: state/library.py `blob` looks only in the blob folder."""
    from score.dashboard.state import library as lib
    blobs, cache = shelf.parent / "blobs", tmp_path / "cache"
    alpha = lib.LocalLibrary(shelf, None, tmp_path / "thumbs", cache).entry("place/alpha@1")
    bare = lib.LocalLibrary(shelf, None, tmp_path / "thumbs", cache)
    assert bare.picture_path(alpha.picture, 64) is None
    kept = cache / "place" / "alpha" / "1" / alpha.picture_file
    kept.parent.mkdir(parents=True)
    kept.write_bytes((blobs / "blobs" / alpha.picture[:2] / alpha.picture).read_bytes())
    assert bare.blob(alpha.picture) == kept and bare.picture_path(alpha.picture, 64).is_file()


def test_names_are_everyday_words_with_the_library_title_kept_as_hover_text():
    """Break: state/names.py drops its 2p6 -> 2.6 m rule."""
    from score.dashboard.state.names import plain as named
    assert named("algorithm", "surface_recipes", "Surface functions: ProcFunc material recipes and wear") == (
        "Surface finishes", "Surface functions: ProcFunc material recipes and wear")
    assert named("ground", "earth.flat", "Flat ground (earth)")[0] == "Flat ground, earth"
    assert named("model", "ac_unit_1", "Ac unit 1")[0] == "Air conditioner 1"
    assert named("model", "apron_2p6", "Apron 2p6")[0] == "Apron 2.6 m"
    assert named("effect", "drift_0_3.camp", "Drift 0 3")[0] == "Drift, row 1 spot 4"
    assert named("layer", "light.camp", "Camp light layer")[0] == "Camp lamps"
    assert named("model", "wrench", "Wrench") == ("Wrench", "")


# === the theme ========================================================================================================

PAGES_ROOT = REPO / "score" / "dashboard" / "pages"
TOKENS = REPO / "design" / "tokens"
SOURCES = [*sorted((PAGES_ROOT / "templates").rglob("*.html")),
           *sorted(path for path in (PAGES_ROOT / "static").rglob("*") if path.suffix in (".css", ".js"))]
HEX = re.compile(r"(?<![\w&/])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
NUMBER_HEX = re.compile(r"\b0x[0-9a-fA-F]{6}\b")
FUNCTION = re.compile(r"\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(\s*[\d.]")
NAMED = ("black|white|red|green|blue|yellow|orange|purple|gray|grey|pink|silver|navy|teal|maroon|olive|lime|aqua|"
         "fuchsia|cyan|magenta|gold|brown")
CSS_NAMED = re.compile(rf":[^;{{}}\"]*(?<![\w-])(?:{NAMED})(?![\w-])")
STYLE = re.compile(r"style=\"([^\"]*)\"")
USED = re.compile(r"var\(\s*(--[\w-]+)|[tT]oken\(\"(--[\w-]+)\"\)")
DEFINED = re.compile(r"(--[\w-]+)\s*:")


def literal_colours(path):
    """Each hard-coded colour in one template or static file, as (line number, the literal)."""
    found = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        declarations = [line] if path.suffix == ".css" else [f":{value}" for value in STYLE.findall(line)]
        literals = [*HEX.findall(line), *FUNCTION.findall(line), *NUMBER_HEX.findall(line),
                    *(colour for value in declarations for colour in CSS_NAMED.findall(value))]
        found += [(number, literal) for literal in literals]
    return found


def test_every_colour_comes_from_the_design_tokens_and_every_token_named_is_defined():
    """Owner rule (a source scan, #25, 2026-10-20): one dark theme on design tokens. Break: static/pages/dash.css gains
    `a { color: #ff0000; }`."""
    found = {str(path.relative_to(REPO)): hits for path in SOURCES if (hits := literal_colours(path))}
    assert not found, f"colours outside design/tokens/colours.css: {found}"
    defined = {name for path in (TOKENS / "colours.css", TOKENS / "scale.css", *SOURCES)
               for name in DEFINED.findall(path.read_text())}
    used = {name for path in SOURCES for pair in USED.findall(path.read_text()) for name in pair if name}
    assert not used - defined, f"tokens named but never defined: {sorted(used - defined)}"


def hex_of(name, text):
    return re.search(rf"{name}:\s*(#[0-9a-fA-F]{{6}})\b", text).group(1)


def contrast(one, other):
    """WCAG 2 contrast ratio of two #rrggbb colours."""
    def luminance(colour):
        channels = [int(colour[at:at + 2], 16) / 255 for at in (1, 3, 5)]
        red, green, blue = [part / 12.92 if part <= 0.04045 else ((part + 0.055) / 1.055) ** 2.4 for part in channels]
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue
    light, dark = sorted((luminance(one), luminance(other)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def test_text_holds_wcag_aa_on_every_surface_and_the_gap_colours_stay_apart():
    """Break: design/tokens/colours.css sets --color-text-faint to #1a1d22."""
    text = (TOKENS / "colours.css").read_text()
    pairs = [(ink, ground) for ink in ("--color-primary", "--color-text-body", "--color-text-light",
                                       "--color-text-faint", "--color-accent")
             for ground in ("--color-bg", "--color-bg-section", "--color-bg-raised")]
    pairs += [("--color-accent-ink", "--color-accent")]
    pairs += [("--color-on-status", status) for status in ("--color-idle", "--color-gap-missing", "--color-gap-gate",
                                                          "--color-gap-route", "--color-gap-lost")]
    low = {pair: round(contrast(hex_of(pair[0], text), hex_of(pair[1], text)), 2) for pair in pairs}
    assert not {pair: ratio for pair, ratio in low.items() if ratio < 4.5}, low
    kinds = [hex_of(f"--color-gap-{kind}", text) for kind in ("missing", "gate", "route", "lost")]
    assert len(set(kinds)) == 4 and hex_of("--color-accent", text) not in kinds


def test_the_tokens_and_the_font_are_served():
    """Break: site/asgi.py mounts /static/design at the static folder."""
    web = hosted_client()
    links = re.findall(r'href="([^"]+)"', (PAGES_ROOT / "templates/pages/tokens.html").read_text())
    for url in [*links, "/static/design/fonts/poppins/poppins-400-latin.woff2", "/static/pages/tokens.js"]:
        assert web.get(url).status_code == 200, url


# === the viewer look check (tests/viewer_look.py, run by hand) ========================================================

def test_the_viewer_look_check_passes_a_picture_against_itself_fails_black_or_pink_and_links_its_camera(tmp_path):
    """Break: tests/viewer_look.py `passes` returns True."""
    from score.dashboard.tests import viewer_look

    def picture(path, colour):
        Image.new("RGB", (320, 180), colour).save(path)
        return path
    film = picture(tmp_path / "film.png", (120, 110, 100))
    same = viewer_look.measures(film, film)
    assert same == {"difference": 0.0, "structure": 1.0, "brightness": 1.0, "pink": 0.0, "black": 0.0}
    assert viewer_look.passes(same)
    black = viewer_look.measures(film, picture(tmp_path / "black.png", (0, 0, 0)))
    assert black["black"] == 1.0 and not viewer_look.passes(black)
    pink = viewer_look.measures(film, picture(tmp_path / "pink.png", (240, 130, 150)))
    assert pink["pink"] == 1.0 and not viewer_look.passes(pink)
    camera = {"eye": [1, 2, 3], "aim": [4, 5.5, -6], "fov": 80.0, "frame": 132}
    assert viewer_look.view_link(camera) == ("view=1.000000,2.000000,3.000000,4.000000,5.500000,-6.000000,80.000000"
                                             "&t=132.000")
    assert viewer_look.view_link({**camera, "frame": None}).endswith(",80.000000")


# --- no provider named or imported (the whole package's invariant, owner rule "No provider here") ---

PACKAGE = REPO / "score/dashboard"
TEXT = (".py", ".html", ".css", ".js", ".yml", ".example", ".env", ".md", "")


def provider_words():
    """The stems of the cloud backends and cluster modules, and the words of the providers the models adapter's
    paid APIs name (score/adapters/models API); a test file beside them (test_<invariant>.py) names none, nor does the
    `local` backend (this PC, never rented: no provider, and "local" is the cockpit's own mode word), nor
    `card_turn` (no backend: the Blender startup script that shares the card's turns, backends overlay; its stem
    "card" failed every overlay that says a card)."""
    stems = {path.stem.split("_")[0] for folder in ("tools/cloud/backends", "tools/cloud/k8s/clusters")
             for path in (REPO / folder).glob("*.py") if not path.stem.startswith(("_", "test_"))
             and path.stem not in ("local", "card_turn")}
    models = (REPO / "score/adapters/models/__init__.py").read_text()
    for provider in re.findall(r'"provider":\s*"([^"]+)"', models):
        stems |= {word for word in re.split(r"[^a-z]+", provider.lower()) if word not in ("api",)}
    return {stem for stem in stems if len(stem) > 3}


def cloud_modules():
    return {path.stem for folder in ("tools/cloud", "tools/cloud") for path in (REPO / folder).rglob("*.py")}


def files():
    return [path for path in PACKAGE.rglob("*") if path.is_file() and "__pycache__" not in path.parts
            and path.suffix in TEXT and path.name != pathlib.Path(__file__).name]


def imported(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


# owner rule: nothing in this package imports tools.* or score.adapters (dashboard overlay, "No provider here")
def test_no_module_imports_tools_the_adapters_or_a_cloud_module():
    """Break: add `import tools.cloud.ledger` to score/dashboard/state/money.py."""
    cloud = cloud_modules()
    for path in PACKAGE.rglob("*.py"):
        for name in imported(path):
            assert not name.startswith(("tools", "score.adapters")), (path, name)
            assert name.split(".")[0] not in cloud, (path, name)


# owner rule: no provider named; one is named only by its cost line's label (dashboard overlay, "Numbers, not prose")
def test_no_file_names_a_provider():
    """Break: a comment naming the cloud provider (a stem of tools/cloud/backends) in score/dashboard/state/money.py."""
    words = provider_words()
    assert words, "the provider list came out empty: the test would prove nothing"
    for path in files():
        text = path.read_text(errors="replace").lower()
        for word in words:
            assert not re.search(rf"\b{re.escape(word)}\b", text), (path, word)


# owner rule: deploy/ holds templates only, every host and name a <placeholder> (dashboard overlay, public repo)
def test_deploy_templates_hold_only_placeholders():
    """Break: a real host (`HOST=cockpit.example.com`) in a score/dashboard/deploy template."""
    for path in (PACKAGE / "deploy").iterdir():
        text = path.read_text()
        assert "TEMPLATE" in text, path
        for line in text.splitlines():
            if line.strip().startswith("#") or "=" not in line or not line.split("=", 1)[0].isupper():
                continue
            value = line.split("=", 1)[1].strip()
            assert value == "" or value.startswith("<") or re.fullmatch(r"[\w./:-]+", value) and not re.search(
                r"\.(org|com|net|nl|io)\b", value), (path, line)
