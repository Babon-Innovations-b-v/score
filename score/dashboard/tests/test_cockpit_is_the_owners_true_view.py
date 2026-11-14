"""The cockpit is the owner's true view: every page shows what the store, the runner and the library say (numbers it
only sums, never makes; unknown as None, never 0; a stale price as no figure), and only the owner, signed in, in his own
process, at the price shown, changes anything (a spend click, a lock, a Keep, an advance, a stop). Driven through the
pages (Django), the API (FastAPI) and pages/, state/screens.py, state/batch_run.py and the sync applier they call, on
the fixture environment (tests/fixture.py), a tiny library folder, written logs and pools, stand-in models: no call
is made, nothing is spent, no real store or home is read.

The test's docstring names the code breaks that turn it red; each was applied once and seen red (2026-10-26).
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
from score.dashboard.conftest import served
from score.dashboard.previews import films
from score.dashboard.tests import fixture
from score.dashboard.tests.fixture import (MADE, NODE, ORIGIN, SPEND, TOKEN, FakeBackend, hosted_client, opener_of,
                                          outside_details)

pytestmark = pytest.mark.django_db(transaction=True)
REPO = pathlib.Path(__file__).resolve().parents[3]
WORD_BUDGET = 40  # a screen's words outside data, hover text and scripts (owner, 2026-10-20: text down about 98%)


# --- the fixture environment and the library, built once a file and copied -------------------------------------------

@pytest.fixture(scope="module")
def built_once(tmp_path_factory):
    """The fixture environment (tests/fixture.py) built once a file, designed and still in design: each test gets a
    copy of its own (a copy is a fifth of a build), the same files and outputs."""
    return {design: fixture.build(tmp_path_factory.mktemp(f"built-{design}"), design) for design in (True, False)}


def copy_of(built, tmp_path, monkeypatch):
    """`built` copied into this test's tmp_path (its file times kept) and served as conftest's world is."""
    shutil.copytree(built.root, tmp_path, symlinks=True, dirs_exist_ok=True)
    return served(fixture.opened(tmp_path, dict(built.outputs)), monkeypatch)


@pytest.fixture
def world(built_once, tmp_path, monkeypatch):
    """conftest's world (both places designed), copied from this file's one build."""
    return copy_of(built_once[True], tmp_path, monkeypatch)


@pytest.fixture
def drafting(built_once, tmp_path, monkeypatch):
    """conftest's drafting (alpha drawn, beta not, nothing locked), copied from this file's one build."""
    return copy_of(built_once[False], tmp_path, monkeypatch)


@pytest.fixture(autouse=True)
def probed_once(monkeypatch):
    """films.probe asks ffprobe once a file for each film's bytes (the pages ask again on every request while a film
    cannot be read: the fixture's film.mp4 is 16 bytes); its answer for those bytes is ffprobe's own."""
    real = films.probe

    def once(film):
        path = pathlib.Path(film)
        if not path.is_file():
            return real(film)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if sha not in PROBED:
            PROBED[sha] = real(film)
        return PROBED[sha]
    monkeypatch.setattr(films, "probe", once)


PROBED = {}  # film bytes' sha -> films.probe's answer


@pytest.fixture(autouse=True)
def checkout_read_once(monkeypatch):
    """local.priced_here reads this checkout (git's HEAD, the per-unit prices' sha) once a file: no test moves either,
    and every page read them again."""
    real = local.priced_here

    def once():
        if not CHECKOUT:
            CHECKOUT.update(real())
        return dict(CHECKOUT)
    monkeypatch.setattr(local, "priced_here", once)


CHECKOUT = {}  # local.priced_here's answer, read once


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


# === who may see and act ==============================================================================================

PAGES = ["/", "/place/alpha/", "/place/beta/", "/place/alpha/step/closeup/", "/place/beta/step/assembly/",
         "/world/step/terrain/", "/basket/", "/buy/", "/stats/", "/runs/", "/requests/", "/picks/alpha", "/view/alpha"]
POSTS = ["/place/alpha/step/closeup/request/", "/place/alpha/step/closeup/decide/", "/place/alpha/step/closeup/queue/",
         "/basket/change/", "/refresh/", "/freshness/"]
NODE_FREE = [*PAGES[:6], "/view/alpha"]  # node ids only inside details.ids here (the basket and Buy name nodes)
BACKS = [("https://evil.example/", 302, "/"), ("//evil.example/", 302, "/"), ("javascript:alert(1)", 302, "/"),
         ("/place/alpha/", 302, "/place/alpha/")]  # a back link, the answer and where he lands: never off this site


# === nothing advances unseen ==========================================================================================

PAID = "demo-film@alpha"  # reads assembly@alpha and complete@alpha, both accepted in the fixture environment


def ready_plan(buys):
    body = {"groups": [{"places": ["alpha"], "stages": ["demo-film"], "missing": [], "buys": buys, "refusal": None,
                        "to_run": {}, "blocked": {}}], "buys": buys, "jobs": 8, "rebuys": 0.0, "nodes": [],
            "money": {"high": 13.67, "likely": 13.31, "spent": 100.0, "reserved": 10.0, "ceiling": 250.0,
                      "room": 140.0, "note": ""}, "time": {"likely_minutes": 10, "high_minutes": 20}}
    return Plan.objects.create(basket_hash="h", made_by="joey", state="ready", body=body, finished=timezone.now())


class PaidFilm(FakeBackend):
    """The fake backend buying the film as well as the close-up."""

    def plan(self, group):
        planned = FakeBackend.plan(self, group)
        planned.buys += [{"node": f"demo-film@{place}", "euros": 5.0, "why": "never ran", "again": False}
                         for place in group.places if "demo-film" in group.stages]
        return planned


# === numbers, not prose ===============================================================================================

SCREENS = ["/", "/places/", "/environments/world1/", "/place/alpha/", "/buy/", "/stats/", "/library/"]


# === the runner's prices, summed and never made (rows and blocks in the one test) =====================================

PRICED = {  # by hand: three measured nodes of EUR 2-3 each in their own basis, guesses 1.0 + 1.5 apart, the film unknown
    "pixal@alpha": {**MEASURED, "basis": "measured runs"}, "bake@alpha": {**MEASURED, "basis": "per unit × counted"},
    "lists@alpha": {**FORECAST}, "sound@alpha": GUESSED, "sound@beta": {**GUESSED, "guess_euros": 1.5},
    "film@alpha": {**GUESSED, "guess_euros": None, "guess_from": None}}
LOST_ITEMS = ["place:lost:earth-seed:usd-r3/flat:x", "place:lost:data:surfaces/launch.json:bake entry far_rocket_1"]
KEYS = ["concepts/cockpit/draws/1.json", "concepts/cockpit2/draws/2.json", "concepts/cock.json", "plans/cockpit/a.json",
        "concepts/cockpit/draws/3.json.partial"]  # a store's files: a prefix outside the index's areas walks its folder
KEY_PREFIXES = ["concepts/cockpit/", "concepts/", "concepts/cockpit/draws/", "nothing/here/"]
JUDGED = {  # what the pure judges answer on those rows
    "bases": [("measured runs", 2.0, 3.0, 1), ("per unit × counted", 2.0, 3.0, 1), ("per unit × forecast", 2.0, 3.0, 1)],
    "guessed": (2.5, 2), "unknown": ["film@alpha"], "measured of": (3, 6),
    "never checked: money, rank below every kind": (None, True),
    "place words": ("the old station", "Old station"),
    "lost items": ["usd-r3/flat:x", "surfaces/launch.json:bake entry far_rocket_1"],
    "concepts/cock": ["concepts/cock.json", "concepts/cockpit/draws/1.json", "concepts/cockpit2/draws/2.json"],
    "prefixes unlike the store's own answer": [],
    # by hand: the 3rd grew 5.5 - 4.0 = 1.5 whole; the 2nd's growth not known (no day before), its ledger 0.3; the 5th
    # misses a line: none; a ledger 0 says nothing; a month's first day is its whole reading
    "spend by day": [("01", 1.0, False), ("02", 0.3, False), ("03", 1.5, True), ("04", 0.7, False), ("05", None, False),
                     ("06", None, False)],
    "a first day": [{"day": "2026-10-01", "euros": 2.0, "whole": True}],
    "day chart: ticks, bars, gap days": ([0, 1.0, 2.0], 4, ["05", "06"]), "unplaced of 10, of none": (6.5, None),
    "scale tops": [1.0, 1.0, 5, 2500, 20000],
    "3D of a withdrawn library place, then a draft": [(None, None), ("/library-files/files/ab12", "library")]}
SPEND_BILLS = [{"day": "2026-10-02", "cloud": 2.0, "models": 0.5}, {"day": "2026-10-03", "cloud": 3.5, "models": 0.5},
               {"day": "2026-10-05", "cloud": 5.0, "models": None}]
SPEND_LEDGER = [{"day": "2026-10-01", "cloud": 1.0, "models": 0.0}, {"day": "2026-10-02", "cloud": 0.3, "models": 0.0},
                {"day": "2026-10-04", "cloud": 0.5, "models": 0.2}, {"day": "2026-10-06", "cloud": 0, "models": 0.0}]
SCALES = (0, 0.4, 3, 2119.85, 12408)


def library_holding(state):
    """A library holding place alpha in `state`, its web copy ab12 (state/screens.py `web3d_link`)."""
    entry = types.SimpleNamespace(kind="place", entry_id="alpha", state=state, web3d=types.SimpleNamespace(sha="ab12"))
    return types.SimpleNamespace(entries=lambda: [entry])
HERE = object()  # a row's price made on this checkout as it is
STALE = [  # (row, the price's priced_on over this checkout's, findings rewritten after it, why there is no figure)
    ("current", HERE, False, None), ("other commit", {"commit": "0" * 40, "uncommitted": False}, False, "the code moved"),
    ("other per-unit prices", {"per_unit_sha256": "0" * 64, "uncommitted": False}, False, "per-unit prices"),
    ("uncommitted", {"uncommitted": True}, False, "code not committed"), ("none", None, False, "before the price"),
    ("gaps check again", HERE, True, "the gaps check ran again at 1 scene since the price was made"),
    ("current again", HERE, False, None)]
LOST = {"id": "place:lost:earth-seed:usd-r3", "rule": "place", "prim": None, "kind": None,
        "sentence": "lost input usd-r3", "picture": None, "row": None, "gates": [], "source": "inputs",
        "node": None, "work": "earth seed lost", "placed": None, "low": None, "high": None}
TAKEN = dict(LOST, id="place:lost:pixal:pliers-pf", sentence="lost input pliers-pf", work="take lost")
MILESTONES = [{"key": "ground", "title": "The ground", "stages": [{"stage": "terrain", "nodes": 1, "paid": 1}],
               "nodes": 1, "places": 0, "paid": ["terrain"], "likely_euros": 0, "high_euros": 0, "measured": 0,
               "set": {"euros": 6.0, "nodes": 1, "from": []}, "unknown": [], "owner": ["the month's books"],
               "reads": []},
              {"key": "approval", "title": "Your approval of the final video", "owner": ["you approve it"]}]
BETA_LAMP = {"id": "missing:lamp_1", "rule": "missing", "kind": "generate", "sentence": "a lamp: nothing made for it yet",
             "picture": None, "row": "lamp", "gates": [], "source": "inventory", "node": "closeup@beta", "work": None,
             "placed": "spot", "prim": "/beta/Gaps/lamp_1", "low": [0, 0, 0], "high": [1, 1, 1]}


# === a scene item's click, in a browser ===============================================================================

PLAYWRIGHT = "playwright@1.62.1"  # viewer_look.py's: its Chromium (1234) is the one installed in ~/.cache/ms-playwright
SHELL = pathlib.Path.home() / ".cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64"


def chromium_runs():
    """Whether the headless Chromium is installed with every library it loads (LD_LIBRARY_PATH counted)."""
    shell = SHELL / "chrome-headless-shell"
    return shell.is_file() and "not found" not in subprocess.run(["ldd", str(shell)], capture_output=True,
                                                                 text=True).stdout


# === screens' data (state/screens.py) =================================================================================

ABSENT = "(absent)"  # a path not there (picked)
COCKPIT_NODES = {  # alpha's gaps priced: the close-up on the prop route, settle off it and measured, the sound guessed
    "closeup@alpha": {**MEASURED, "basis": "per unit × forecast"}, "settle@alpha": SETTLE,
    "sound@alpha": {"likely_euros": None, "high_euros": None, "guess_euros": 1.0, "basis": "not measured yet",
                    "likely_minutes": None, "high_minutes": None}}
COCKPIT_ETA = {"likely_minutes": None, "high_minutes": None, "at_least_minutes": 20.0, "unknown": [{"node": "sound@alpha"}]}
UNCOMMITTED = {"commit": "6cdf4d40", "uncommitted": True, "per_unit_sha256": "x"}
READ_ALPHA = {"read": ["alpha"], "waiting": ["beta"]}
NOT_COMMITTED = "it was made on code not committed"
OLDER = "older than the price ("
GUESS = {"likely_euros": None, "high_euros": None, "guess_euros": 1.5, "basis": "not measured yet",
         "likely_minutes": None, "high_minutes": None}  # with an unpriced rough model, the buy line's guessed steps
PEOPLE_PRICE = {"likely_euros": 1.0, "high_euros": 2.0, "runs": 1}
PEOPLE = [  # (item, its places, its nodes, the places whose cast reads it): Buy of 2026-10-24 refused closeup@people
    ("alpha-settle", ["alpha"], ["settle@alpha"], ["alpha"]), ("beta-settle", ["beta"], ["settle@beta"], ["beta"]),
    ("people-base", ["people"], ["closeup@people", "people-dress-pilot-made"], ["alpha", "beta"]),
    ("environment-body-face", [], ["body-face-moon"], [])]
PLANTS = [{"id": "planter", "noun": "planter", "count": 4}, {"id": "greens", "noun": "plants", "anchor": "on:planter"},
          {"id": "palm", "noun": "tree", "count": 3}, {"id": "desk", "noun": "desk"}]  # by hand: 2 rows, 4 objects, 4 beds
SCREEN_ROUTES = ("environment", "place/alpha", "buy", "stats", "library", "place/nowhere")
SCREEN_MOMENTS = [  # (moment, prepare's record then, what else is written, {"source:path": what the screens answer})
    ("priced", {}, None, {
        # prepare's route EUR 10 (2 blocked, 1 predicted gap) plus settle off it (EUR 2-3), the sound unpriced
        "environment:remake.route.likely": 10.0, "environment:remake.route.blocked": 2,
        "environment:remake.route.predicted_gaps": 1,
        "environment:remake.rest": {"likely": 2.0, "high": 3.0, "priced": 1, "unpriced": 1},
        "environment:remake.likely": 12.0, "environment:remake.high": 15.0, "environment:remake.unpriced": 2,
        "environment:remake.eta": {"likely_minutes": None, "high_minutes": None, "at_least_minutes": 30.0, "untimed": 3},
        "environment:money": {"month": "2026-10", "cloud": 2118.87, "models": None, "total": 2118.87, "whole": False,
                              "stop": 900.0, "against_stop": 150.0, "in_flight": 30.0, "refused": False},
        "environment:alpha.gaps": 4, "environment:alpha.worst": "route", "environment:alpha.takes.takes": 3,
        "environment:pictured": [True, False], "environment:gaps": {"missing": 2, "gate": 1, "route": 1},
        "pictures:alpha is its concept": True, "pictures:beta": (None, None),  # lost: never a render instead
        # each chain priced once: the close-up's EUR 2-3 plus the guessed sound; complete's free plus the sound
        "place:items.*.kind": ["missing", "missing", "gate", "route"], "place:items.0.prim": "/alpha/Gaps/lamp_1",
        "place:items.0.node": "closeup@alpha",
        "place:prices.closeup@alpha": {"likely": 2.0, "high": 3.0, "priced": 1, "unpriced": 1},
        "place:prices.complete@alpha": {"likely": 0, "high": 0, "priced": 0, "unpriced": 1},
        "place:gaps": {"missing": 2, "gate": 1, "route": 1}, "place:stale": False,
        # the stop is the high 3 + 10%; no choice, no stop
        "buy none:stop": None, "buy chosen:chosen": 1, "buy chosen:total.likely": 2.0, "buy chosen:total.high": 3.0,
        "buy chosen:stop": 3.3, "buy chosen:eta": {"likely_minutes": 10.0, "high_minutes": 20.0, "untimed": 0},
        # the batch buys the close-up now at its own price; settle and the sound wait, counted by why with no euros
        "batch:layers.0.make": 2, "batch:layers.0.waiting": 0, "batch:layers.0.models": 2, "batch:layers.0.likely": 2.0,
        "batch:layers.0.high": 3.0, "batch:layers.1.waiting": 1, "batch:layers.1.why": {"an earlier step first": 1},
        "batch:layers.1.likely": 0.0, "batch:layers.2.waiting": 1, "batch:layers.2.likely": 0.0,
        "batch:layers.2.guessed": 0.0, "batch:layers.3": ABSENT, "batch:total.likely": 2.0, "batch:total.high": 3.0,
        "batch:now.likely": 2.0, "batch:now.high": 3.0, "batch:now.steps": 1, "batch:now.places": ["alpha"],
        "batch:now.stop": 3.3, "batch:waiting": {"steps": 2, "why": ["an earlier step first"]},
        "batch lost input:now.steps": 0, "batch lost input:now.stop": None,  # a lost input buys nothing
        "batch lost input:layers.0.why.lost concept views": 2,
        # two guessed steps (1.5 each), an unpriced rough model: likely 2, high 3 + 3 = 6, stop 6.6, 3 untimed kinds
        "batch guessed:now.likely": 2.0, "batch guessed:now.high": 6.0, "batch guessed:now.guessed": 3.0,
        "batch guessed:now.guesses": 2, "batch guessed:now.stop": 6.6, "batch guessed:now.no_price": {"models": 1},
        "batch guessed:now.eta.likely_minutes": None,
        "batch guessed:now.eta.untimed_kinds": {"rough model": 1, "light renders": 1, "sound": 1},
        "batch guessed:now.eta.at_least_minutes": 10.0, "batch guessed:now.eta.at_least_high_minutes": 20.0,
        "batch guessed:refused": [], "batch guessed:cleared high": 6.0,
        "batch guessed:older": [f"the basket (2026-10-19 08:00) is {OLDER}"],
        "batch guessed:unknown age": ["the basket's time is not known"],
        "stats:prices.measured": 2, "stats:prices.steps": 3,  # settle and the close-up measured, the sound not
        "stats:last day": {"day": "2026-10-20", "cloud": 1.25, "models": 0.4}, "stats:places.total": 2,
        "stats:gaps.missing": 2,
        "routes:codes": [200, 200, 200, 200, 200, 404], "routes:exported blocked": 2,
        "people:alpha": ["alpha-settle", "people-base", "environment-body-face"],
        "people:gamma": ["environment-body-face"], "people:refusals": [], "people:beta of the basket": []}),
    ("on code not committed", {"priced_on": UNCOMMITTED}, None, {  # never 0.00 stale
        "remake money:stale": [NOT_COMMITTED], "buy now:unknowns": 1, "buy now:range": False,
        "buy now:offered": False, "buy now:disabled": True}),
    ("no design approved", {"approved": ()}, None, {  # owner, 2026-10-20: "design decides inventory"
        "batch:now.steps": 0, "batch:now.stop": None, "batch:layers": [], "remake money:likely": None,
        "remake money:approved": 0, "remake money:in_design": 2, "design:approved": [],
        "design:places.*.design.plan": ["remake", "remake"],
        "buy page:approved": "0", "buy page:euros on top": False, "buy page:offered": False}),
    ("alpha's inventory read", {"approved": (), "inventory": READ_ALPHA}, None, {  # an estimate that buys nothing
        "remake money:estimate": {"likely": 10.0, "high": 12.0, "unpriced": ["likeness-calibration"], "places": 1,
                                  "waiting": 1, "eta": {"likely_minutes": None, "high_minutes": None,
                                                        "at_least_minutes": 30.0, "untimed": 2}, "stale": None},
        "tiles:/buy/": [True, True], "tiles:/places/": [True, True], "tiles:offered": False}),
    ("alpha's inventory read, uncommitted", {"approved": (), "inventory": READ_ALPHA, "priced_on": UNCOMMITTED}, None,
     {"remake money:estimate.likely": None, "remake money:estimate.stale": NOT_COMMITTED}),
    ("alpha approved", {"approved": ("alpha",)}, None, {
        "remake money:likely": 12.0, "remake money:high": 15.0, "remake money:in_design": 1,
        "remake money:eta.at_least_minutes": None,  # the runner times the whole remake only
        "buy page:older": True}),  # the basket (2026-10-19 08:00) is older than the price: Buy disabled
    ("alpha approved, the basket current", {"approved": ("alpha",)}, "basket now", {
        # the close-up EUR 2-3, its stop the high + 10%, settle and the sound waiting; a layer a line, no step's name;
        # a post with no key unprocessable, the Benchmarks item not in the basket, a guest refused and offered no Buy
        "buy page:older": False, "buy page:now": (True, True, True, True),
        "buy page:layers": [("Models", "2"), ("Motion", "1"), ("Sound", "1")], "buy page:step names": False,
        "buy page:posts": (422, 409, True, 403, False)}),
    ("a choice on another version", {}, "choice", {"api buy:chosen": 0, "api buy:items.0.choice": None}),
    ("plants", {}, "plants", {  # owner, 2026-10-24: every growing row is a plant, the planter its bed
        "plants:world": {"alpha": {"rows": 2, "objects": 4, "crops": 1, "beds": 4}},
        "plants:batch": {"rows": 2, "objects": 4, "crops": 1, "beds": 4, "places": ["alpha"]}, "plants:none": None})]


# === the books buttons on the Buy screen (owner rule, 2026-10-20) =====================================================

BOOKS = [  # (row, the model calls' bill (None: partly counted), why paid work is refused, who) -> on his Buy screen:
    #        (a Basket link, the model calls' figure button, the read-back, the books figure posted)
    ("model bill not read", None, None, "joey", (False, True, False, True)),
    ("model bill read", 1030.0, None, "joey", (False, False, False, False)),
    ("books lost", None, "the month's books are lost", "joey", (False, True, True, True)),
    ("books lost, a guest", None, "the month's books are lost", "guest", (False, False, False, False))]


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


def a_basket(root):
    """A made basket under `root`: alpha's pieces (measured, what changes, a picture it is made from), the
    environment's people body (never measured), and the ship's declared item with a question."""
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


def a_batch(world, log=LOG, key="a"):
    """A checkout launched one run whose log is `log`; closeup@alpha's own log written since (it runs now)."""
    props, store = world.source.props_home, world.source.store_root
    (props / "logs").mkdir(parents=True, exist_ok=True)
    path = props / "logs" / f"score-run-{key}.log"
    path.write_text(log.format(run=RUN))
    plan = Plan.objects.create(basket_hash=f"checkout-{key}", made_by="joey", state="ready", body=PLAN)
    launch = Launch.objects.create(plan=plan, by="joey", state="running", handles=[
        {"command": ["score", "run"], "pid": None, "log": str(path), "refused": None}])
    record = Checkout.objects.create(key=key * 32, by="joey", state="launched", totals=TOTALS, launch=launch,
                                     items=[{"nodes": {"closeup@alpha": {}, "closeup@beta": {}}}],
                                     stop_line={"euros": 516.44, "spent": 120.0, "reserved": 0.0, "batch_from": 90.0,
                                                "at": "2026-10-24T11:08:38+00:00"})
    (store / "logs").mkdir(parents=True, exist_ok=True)
    row_log = store / "logs" / "closeup@alpha.log"
    row_log.write_text("drawing\n")
    later = time.time() + 5
    os.utime(row_log, (later, later))
    a_pool(props)
    return record


def newest():
    from score.dashboard.checkout import watched
    return watched.newest()


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


FINISHED = "detached: ok exit=0 minutes=15.6 log=x outputs=y\n"
STOPPED = "detached: stopped by signal 15 exit=143 minutes=0.0 log=x outputs=y\n"
# What the run monitor judges on its own, row by row (BATCH_JUDGED below holds each answer).
OVERALLS = [  # (the run's log, whether its launch still lives, its pool, what overall says: the state, then its why)
    ("exit: stopped, 3 of 4 lines done, 1 stopped\ndetached: failed exit=1 minutes=80.0", False, None,
     ("finished", "some scenes' lines stopped")),
    ("refused: these inputs are missing, so the rows ...\n  /x/a.json\nexit: exited, exit 1\n"
     "detached: failed exit=1 minutes=0.3", False, None,
     ("stopped", "refused: these inputs are missing, so the rows ...")),
    ("exit: error: KeyError: 'x'\ndetached: failed exit=1 minutes=2.0", False, None,
     ("stopped", "error: KeyError: 'x'")),
    ("Traceback\ndetached: failed exit=1 minutes=0.1", False, None, ("stopped",)),
    ("", True, {"open": True, "cards": {"warm": 0, "short": 2}}, ("waiting",)),  # no warm card while stock is short
    ("", True, {"open": True, "cards": {"warm": 1, "short": 2}}, ("running",)),
    ("", False, None, ("stopped", "the run ended without its result line"))]
CLOUD_FAULT = ("error: CalledProcessError: Command '['/home/score/tools/cloud/blender_cloud.py', '--scene', 'x']' "
               "returned non-zero exit status 1.")
CAUSES = [  # (a step's fault line, its fault report's tail, the plain cause, None where only its shape is pinned)
    (CLOUD_FAULT, "  | no card could be rented", "no cloud machine could be rented"),
    (CLOUD_FAULT, "", "its run on a cloud machine failed"),
    ("error: RuntimeError: light@a: an input changed while it ran; nothing is stored", "",
     "an input file changed while it ran"),
    ("made: fail", "", "it was made but failed its check"),
    ("error: ValueError: need at least one array to concatenate", "", "need at least one array to concatenate"),
    ("error: KeyError: " + "word " * 40 + "/home/score/deep/file.json", "", None)]
NEXT_RUN = {"checkout": 3, "batch": 1, "at": "2026-10-25T09:10:00+00:00", "state": "finished",
            "nodes": {"planned": ["a", "b", "c", "d"], "made": ["a", "b"], "failed": ["c"]}}
NEXT_BUYS = [  # (the batch's run, what the next Buy makes, what it says, whether that is all it says or how it begins)
    (NEXT_RUN, ["c", "d", "e"], "Retry Batch 1: makes again the 1 step that failed and the 1 that never ran; makes 1 "
     "step for the first time; keeps the 2 already made.", True),
    ({**NEXT_RUN, "design_at": "2026-10-25T10:00:00Z"}, ["c"], "Retry Batch 1:", False),  # a design edit ends no batch
    ({**NEXT_RUN, "nodes": {"planned": ["a", "b"], "made": ["a", "b"], "failed": []}}, ["a"],
     "Batch 2, after Batch 1: makes again the 1", False),
    ({**NEXT_RUN, "state": "running"}, ["c"], None, True),
    ({"checkout": 1, "state": "finished"}, ["c"], None, True)]
PREPARED_REMAKE = types.SimpleNamespace(remake=types.SimpleNamespace(
    made_at="2026-10-26T08:00:00+00:00", counts={"predicted_gaps": 12}, stale=None))
BATCH_JUDGED = {
    "overall": [want for *_, want in OVERALLS],
    "causes": [(want, True) for *_, want in CAUSES],
    "next buys": [want for _, _, want, _ in NEXT_BUYS],
    "prepared after the try, before it": [{"at": "2026-10-26T08:00:00+00:00", "gaps": 12, "stale": None}, None],
    "own stop of a line without what it was written over": None,
    "parents before children": [("", 0), ("flat", 0), ("hangar", 0), ("ship", 1), ("cockpit", 2), ("galley", 2)],
    "one fault in 3 places": (["a", "b", "c"], "", True, 3, True)}
WITHIN = {"cockpit": "ship", "galley": "ship", "ship": "hangar", "flat": "block"}
WITHIN_NAMES = {"hangar": "Hangar", "ship": "Ship", "cockpit": "Cockpit", "galley": "Galley", "flat": "Flat"}
AGAIN = (TRY_ONE.splitlines()[0] + "\ncloseup@beta: error: RuntimeError: no card again; fault report /x/f.txt\n"
         "assembly@beta: not run: its line stopped at closeup@beta\ndetached: failed\nexit: stopped, 1 line\n")
BEAT = heartbeat("2026-10-25T09:30:00+00:00", 0, 1, 0, 0, "5.00") + "\ndetached: failed\nexit: stopped, 1 line\n"
TRIES = [  # (the second try's log, None while it launches; whether terrain's accept is read; {probe: what is seen})
    # the try makes closeup@beta and assembly@beta again: they wait, not failed; the first try's light@alpha stays
    (None, True, {"state": "starting", "scene states": {"": "done", "alpha": "failed", "beta": "waiting"},
                  "rows.done": 1, "rows.failed": 1, "rows.not_run": 0, "problem nodes": ["light@alpha"],
                  "retried": 1, "clock.started": "08:59", "clock.batch_started": "24 Oct 23:00"}),
    (AGAIN, True, {"state": "finished", "retried": 0, "problem nodes": ["closeup@beta", "light@alpha"]}),
    # 2.00 + 5.00 = 7.00 the batch's, 5.00 the try's, and the bar fills by the batch's spend
    (BEAT, False, {"money.runs": 7.0, "money.try_spent": 5.0, "bar.spent": 50.0})]
STOPS = ('data-url="/api/machine/stop"', 'data-url="/api/machine/stop-batch"')
LIVE_BATCH = r"Batch \d+ is (starting|running|waiting for machines): \d+ of \d+ steps, EUR [\d.]+ spent"
BATCH_MOMENTS = [  # (moment, {(source, path, test): what is seen}); one batch bought, launched, read and ended,
    # then tried again; a source is the run (batch_run), the run gathered by hand, the export or a page as who sees it
    ("no batch", {("owner /buy/run/", "", "has No batch yet"): True, ("owner /", "", 'has href="/buy/run/"'): False,
                  ("owner /buy/", "", "has >Batch</a>"): False}),
    ("ordered", {("run", "state"): "starting"}),  # launching, no launch yet
    ("launch started", {("run", "money.runs"): 0.0, ("run", "stop is the high plus 10%"): True}),  # no line yet
    # From LOG by hand: 6 rows planned; terrain and plan@alpha done, closeup@beta failed, assembly@beta not run,
    # closeup@alpha running (its log newer), assembly@alpha queued; EUR 3.21 the last heartbeat; spent is the money
    # guard's (the environment's 100 since its first line less the 90 the batch began at); one card warm and busy of
    # two, one short; 327.24 + 33.16 = 360.40 high, the line 516.44 less 120 before it = 396.44 = 360.40 x 1.1.
    ("launched", {
        ("run", "state"): "running", ("run", "checkout is the newest"): True,
        ("run", "rows"): {"total": 6, "done": 2, "failed": 1, "not_run": 1, "running": 1, "queued": 1},
        ("run", "money.runs"): 3.21, ("run", "money.line"): 516.44, ("run", "money.spent"): 10.0,
        ("run", "money.other"): 6.79, ("run", "eta.likely_minutes"): 121.5, ("run", "eta.untimed"): 1,
        ("run", "by place..state"): "done", ("run", "by place.alpha.running"): ["close-ups"],
        ("run", "by place.beta.failed"): 1, ("run", "by place.beta.not_run"): 1,
        ("run", "by place.beta.state"): "failed",
        ("run", "pool.cards"): {"size": 2, "warm": 1, "busy": 1, "idle": 0, "short": 1},
        ("run", "pool.processors"): {"size": 1, "warm": 0, "busy": 0, "idle": 0, "short": 1},
        ("run", "problems.*.place"): ["beta"],
        ("run", "problems.0.words", "starts The close-ups step stopped: no card of 24 GB graphics card was had"): True,
        ("run", "problems.0.words", "has gpu-"): False, ("run", "problems.0.words", "has 1 later step"): True,
        ("run", "money.high"): 360.40, ("run", "money.stop"): 396.44, ("run", "stop is the high plus 10%"): True,
        ("run", "bar over at 340"): False,
        ("gathered", "gap problems"): [{"at": "2026-10-24T11:09:00+00:00", "place": "alpha", "node": "plan@alpha",
                                        "kind": "gaps", "words": "Plan left 1 thing out as gaps.",
                                        "tip": "hatch: no model"}],
        **{("owner /buy/run/", "", f"has {stop}"): True for stop in STOPS},
        ("owner /buy/run/", "", "has 396.44"): True, ("owner /buy/run/", "", "has waiting for stock"): True,
        ("owner /buy/run/", "", 'has href="/place/alpha/"'): False, ("owner /buy/run/", "", "words at most 60"): True,
        ("sam /buy/run/", "", "has /api/machine/stop"): False, ("owner /", "", 'has href="/buy/run/"'): True,
        ("owner /buy/", "", f"re {LIVE_BATCH}"): True, ("owner /buy/", "", 'has data-url="/buy/yes/"'): False,
        ("owner /buy/", "", "has >Batch</a>"): True}),
    ("hosted", {("export", "read_at"): MADE, ("export", "money.runs"): 3.21, ("export", "rows.done"): 2,
                ("owner /buy/run/", "", "has min ago"): True, ("owner /buy/run/", "", "has Buy sent"): False}),
    ("buy sent", {("sam /buy/run/", "", "has Buy sent"): True}),
    # spent is the money guard's measure since the batch's first line; the next Buy's figure the batch total
    ("one budget", {
        ("run", "money.budget"): 740.0, ("run", "left is the budget less spent and in flight"): True,
        ("run", "money.spent"): 20.0,
        ("owner /buy/run/", "", r"re Batch 1: EUR 20.00 spent of EUR 740.00 budget, EUR [\d.]+ left"): True,
        ("run", "next total while it runs"): None, ("run", "next total once stopped"): 740.0,
        ("run", "next total over a smaller budget is spent, in flight and the need"): True}),
    # a second run plans only what is not accepted: every planned row still counted, those accepted since done, a
    # stale accept not
    ("relaunched", {
        ("gathered", "rows"): {"total": 6, "done": 3, "failed": 1, "not_run": 0, "running": 1, "queued": 1},
        ("gathered", "scene counts"): {"": (1, 1), "alpha": (1, 3), "beta": (1, 2)}}),
    # fault of 2026-10-24: spend began again at 0 and 13 parked machines billed unseen; 1.18 + 3.21 = 4.39; 2 parked
    # of this run plus the old run's: 3
    ("first run and parked", {
        ("gathered", "money.runs"): 4.39, ("gathered", "started is the first launch"): True,
        ("gathered", "eta.elapsed", "at least 45"): True, ("gathered", "pool.open"): False,
        ("gathered", "pool.renting"): 3, ("owner /buy/run/", "", "has 3 still renting"): True,
        ("owner /buy/run/", "", "words at most 60"): True}),
    ("finished", {("run", "state"): "finished", ("run", "ended", "set"): True, ("run", "scenes.1.running"): []}),
    ("stopped", {("run", "state"): "stopped", ("run", "problems.0.kind"): "run"}),
    # owner, 2026-10-26: "the cockpit is still just a bunch of red": an ended try is history under the batch now
    ("ended", {("owner /buy/run/", "", "has Next try not started"): True,
               ("owner /buy/run/", "", "has Try 1 ended"): True,
               ("owner /buy/run/", "", r're <details class="rm-history"><summary[^>]*>Problems when try 1 ended '
                                       r'<span data-v>\d+'): True,
               ("owner /buy/run/", "", "has data-rm-reload="): False,
               ("owner /buy/run/", "", "has /api/machine/stop-batch"): False}),
    # owner, 2026-10-25: "its the same batch, ur just retrying a failed part of it"; 2026-10-26: Batch 1's fifth Buy,
    # after a day of design fixes, was called Batch 2. A design edit ends no batch; a relaunch whose run never began
    # (stopped while waiting for size) is no try; a batch ends once every row it planned was made.
    ("retried", {("run", "batch"): 1, ("run", "tries"): 2, ("run", "checkout is the newest"): True}),
    ("stopped waiting for size", {("run", "batch"): 1, ("run", "tries"): 3}),  # the newest is shown
    ("relaunched after it", {("run", "batch"): 1, ("run", "tries"): 3,
                             ("watched", "ended once every row was made"): True,
                             ("watched", "ended while a row was never made"): False})]


# === the store's machine ==============================================================================================

HEALTH = {"size": "POP2-HM-2C-16G", "state": "idle", "units": {"score-sync.timer": "active"},
          "backup": {"at": "2026-10-18T11:30:00+00:00", "ok": True}, "bill": {"euros": 12.34, "month": "2026-10"},
          "disk": {"used_gb": 40, "total_gb": 100}, "free_only": True}
THEN = datetime.datetime.fromisoformat(MADE) + datetime.timedelta(hours=1)
OFF_PIN = {"checkout": "a" * 40, "pin": "b" * 40, "matches": False}
ON_PC = {"machine": {"name": "dupe"}, "health": {"machine": None, "state": None, "runs_active": 1, "backup": None}}
CARDS = [  # (row, machine.json's content, what its card says)
    ("his PC running a run", ON_PC, {"on_pc": True, "state": "running 1 run"}),
    ("his PC idle", {**ON_PC, "health": {**ON_PC["health"], "runs_active": 0}}, {"on_pc": True, "state": "idle"}),
    ("a cloud machine", {"machine": {"name": "conductor", "size": "POP2"}, "health": {"state": "idle"}},
     {"on_pc": False}),
    ("its checkout on the pin", {"health": {"code": {**OFF_PIN, "matches": True}}}, {"code_off": False})]
PINS = [  # (the conductor's machine record, the hosted pin's commit, the Buy's refusal); this checkout is on aaaaaaaa
    ({"name": "conductor"}, "b" * 40,
     "the cloud machine is on aaaaaaaa, the cockpit on bbbbbbbb; it is being updated: buy again in a few minutes"),
    ({"name": "conductor"}, "a" * 40, None), ({"name": "conductor"}, None, None), (None, "b" * 40, None)]
LATCH_STEPS = [  # (what changes, then whether the sync follows the latch, and FREE_ONLY in its environment)
    ("latch written", True, "1"), ("latch taken off", False, None), ("set by whoever started it", False, "1")]
REFUSED = [  # (kind, by, payload, in an agent's shell, on a conductor, words in its refusal): nothing is applied
    ("store-machine", "joey", {"machine": "conductor"}, False, True, ""),  # only his confirm moves the record
    ("stop-everything", "mallory", {}, False, True, ""), ("stop-batch", "mallory", {}, False, True, ""),
    ("stop-everything", "joey", {}, True, True, "agent's shell"),
    ("allow-paid", "joey", {}, True, True, "agent's shell"),
    ("stop-everything", "joey", {}, False, False, machine.NOT_ON_CONDUCTOR)]
ASKS = [  # (who asks, /api/machine/<path>, body, status): no sync token, no one but the owner, never without his second
    # ask, never for a machine no export came from
    ("the sync token alone", "confirm", {"machine": "conductor", "sure": True}, 401),
    ("mallory", "confirm", {"machine": "conductor", "sure": True}, 403),
    ("joey", "confirm", {"machine": "conductor"}, 400),
    ("joey", "confirm", {"machine": "elsewhere", "sure": True}, 409),
    ("joey", "stop", {}, 400), ("joey", "stop-batch", {}, 400),
    ("mallory", "stop", {"sure": True}, 403), ("mallory", "stop-batch", {"sure": True}, 403)]
STOPS = [  # (his ask, its body, the request kind it queues, the one call score.conductor.kill gets for it)
    ("stop", {"sure": True, "words": "now"}, "stop-everything", ("stop_all", "joey", "now")),
    ("stop-batch", {"sure": True}, "stop-batch", ("stop_batch", "joey", "")),
    ("allow-paid", {"sure": True}, "allow-paid", ("allow_paid", "joey", ""))]


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


class Pinned:
    """The hosted side's /pin, answering `commit`."""

    def __init__(self, commit):
        self.commit = commit

    def call(self, method, path):
        assert (method, path) == ("GET", "/pin")
        return {"commit": self.commit}


def stood_in_conductor(monkeypatch):
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


def off_a_conductor(monkeypatch):
    """No score.conductor here, also when an earlier part imported its parts."""
    for name in ("score.conductor", "score.conductor.health", "score.conductor.logs", "score.conductor.kill"):
        monkeypatch.setitem(sys.modules, name, None)


def named_machine(world, name):
    (world.source.props_home / machine.MACHINE_FILE).write_text(json.dumps({"name": name, "size": "POP2-HM-2C-16G"}))


def committed_by(remote, name):
    """An export whose manifest names machine `name`, sent and committed through the sync routes."""
    data = json.dumps({"format": versions.FORMAT, "made_at": MADE, "machine": name}).encode()
    sha = hashlib.sha256(data).hexdigest()
    remote.lacking({sha: len(data)})
    remote.put_chunk(sha, 0, len(data), data)
    return remote.commit(f"export-{name}", {"manifest.json": sha})


# === the concept review ===============================================================================================

PRICE = 0.15
REDRAW_PRICE = 0.19  # a Redraw with notes: the prompt correction and the draw
DISCUSS_PRICE = 0.04


def made_draws(store, place):
    """The place's draws made in the test, oldest first (not the fixture's own, drawn the day before)."""
    from score.review import concepts as drawing
    return [draw for draw in drawing.draws(store, place) if draw["at"] != "2026-10-20T07:00:00+00:00"]


def stood_in(monkeypatch, current):
    """The draw's own process run in-process with a stand-in model, on the world `current()` names (a test may move
    to a fresh copy); [what each draw was asked]."""
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
    monkeypatch.setattr(drawing, "offsite_store",
                        lambda: runtime_store.FolderStore(current().source.store.cache.parent / "bucket"))
    monkeypatch.setattr(drawing, "handed_over", lambda store, place: "library: stand-in")
    monkeypatch.setattr(web, "reading_started", lambda store, place, by: "reading: stand-in")

    def run(argv, env, **kwargs):
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        model = lambda wording, pictures: asked.append(wording) or a_png((30 * len(asked) % 256, 90, 140))  # noqa: E731
        prompt = lambda question, pictures: asked.append(question) or "The corrected prompt."  # noqa: E731
        record = drawing.draw(current().source.store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1],
                              caller=model, reviser=prompt)
        return subprocess.CompletedProcess(argv, 0, json.dumps(record) + "\n", "")
    drawn_here = web.concept_draw
    monkeypatch.setattr(web, "concept_draw", lambda *args, **named: drawn_here(*args, run=run, **named))
    return asked


def answered_in_process(monkeypatch, drafting):
    """The Discuss's own process run in-process on `drafting` with a stand-in prompt model that answers "Paint the door
    red." at a measured EUR 0.0271."""
    from score.review import discuss, web
    monkeypatch.setattr(discuss, "price", lambda *given: DISCUSS_PRICE)

    def run(argv, env, **kwargs):
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        model = lambda question, pictures: ("Paint the door red.", 0.0271)  # noqa: E731
        entry = discuss.discuss(drafting.source.store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1],
                                asker=model)
        return subprocess.CompletedProcess(argv, 0, json.dumps(entry) + "\n", "")
    discussed_here = web.concept_discuss
    monkeypatch.setattr(web, "concept_discuss", lambda *args, **named: discussed_here(*args, run=run, **named))


def drawn(owner, place, **body):
    return owner.post(f"/concept/{place}/draw/", json.dumps(body), content_type="application/json")


# === the plan review and the environment's plan =======================================================================

def plan_data(html):
    return json.loads(html.split('<script id="plan-data" type="application/json">')[1].split("</script>")[0])


def drawing_png():
    buffer = io.BytesIO()
    Image.new("RGB", (600, 600), (255, 255, 255)).save(buffer, "PNG")
    return buffer.getvalue()


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


# === the environment concept ==========================================================================================

ASK_PRICE = 0.05
ENVIRONMENT = "/environments/world1/"
SUN = {"name": "Sun", "kelvin": 5800, "lux": 100000, "latitude": 52.0, "tilt_deg": 23.44, "day_hours": 24,
       "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}
HOUSE = {"bodies": [], "plots": [{"name": "Meadow", "gravity": 9.81}], "lights": [SUN],
         "backdrops": [{"name": "Sky", "lux": 10000}],
         "sites": [{"place": "house", "on": "meadow", "x": 0, "y": "0", "height_m": 0}]}
SUN_MOMENTS = ("2024-03-20T12:00:00Z", "2024-05-02T07:30:00Z", "2024-12-21T15:00:00Z")
HOUSE_CARDS = [("Sun", "light", []), ("Sky", "backdrop", []), ("Meadow", "ground", ["House"])]  # at every moment


def posted(owner, path, body):
    return owner.post(f"{ENVIRONMENT}{path}/", json.dumps(body), content_type="application/json")


def environment_asked(monkeypatch, shaped):
    """The environment concept's ask run in-process on `shaped` with a stand-in model, the bucket a folder; [each
    question asked]."""
    from score.dashboard.pages import concepts
    from score.review import concepts as drawing
    from score.review import environment_concept, web
    from score.store import runtime_store
    asked = []
    monkeypatch.setattr("score.adapters.compute.require_books", lambda what: None)
    monkeypatch.setattr(environment_concept, "ask_euros", lambda *given: ASK_PRICE)
    monkeypatch.setattr(concepts, "in_background", concepts.applied_here)
    monkeypatch.setattr(drawing, "offsite_store",
                        lambda: runtime_store.FolderStore(shaped.source.store.cache.parent / "bucket"))
    monkeypatch.setattr(environment_concept, "running_under_agent", lambda: False)
    monkeypatch.setattr(environment_concept, "PROPS_HOME", shaped.source.store.cache.parent / "home")
    monkeypatch.setattr(drawing, "PROPS_HOME", shaped.source.store.cache.parent / "home")

    def run(argv, env, **kwargs):
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        model = lambda question, pictures: asked.append(question) or '{"style": "Bright frontier"}'  # noqa: E731
        record = environment_concept.ask(shaped.source.store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1],
                                         reviser=model)
        return subprocess.CompletedProcess(argv, 0, json.dumps(record) + "\n", "")
    asked_here = web.environment_ask
    monkeypatch.setattr(web, "environment_ask", lambda *args, **named: asked_here(*args, run=run, **named))
    return asked


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


@pytest.fixture(scope="module")
def shelf_once(tmp_path_factory):
    """The shelf's folders made once a file: the one test reads a copy of its own."""
    folder = tmp_path_factory.mktemp("shelf")
    shelf_made(folder)
    return folder


@contextlib.contextmanager
def shelf_copy(shelf_once, folder):
    """A tiny library of 15 entries in a git folder with a bare remote, and its blob folder: this file's one shelf
    copied into `folder`, its clone's origin the copy's own bare remote; the library settings point at it while open."""
    shutil.copytree(shelf_once, folder, symlinks=True, dirs_exist_ok=True)
    config = folder / "lib" / ".git" / "config"
    config.write_text(config.read_text().replace(str(shelf_once / "remote.git"), str(folder / "remote.git")))
    root, blobs, command = folder / "lib", folder / "blobs", folder / "score_lib_command.py"
    with override_settings(SCORE_LIB_ROOT=str(root), SCORE_LIB_BLOBS_DIR=str(blobs),
                           SCORE_LIB_COMMAND=f"{sys.executable} {command}"):
        yield root


def shelf_made(tmp_path):
    """The shelf's library folder (`lib`, a git clone of the bare `remote.git`), blob folder and score_lib command,
    written under `tmp_path`."""
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


def item_data(html):
    """The viewer's JSON the item page carries (item3d.js reads it), or None."""
    found = re.search(r'<script id="item-data" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(found.group(1)) if found else None


def item_rules(path, html):
    """The faults of an item page against the 40-word rule and its no file list, ids or blobs (owner rules, wording
    checks: numbers not prose #42, no file list on an item page 2026-10-20)."""
    faults = [] if len(prose(html)) <= WORD_BUDGET else [("words", prose(html))]
    return faults + [gone for gone in ('class="files"', 'class="ids"', "preview.png", "<table", "sha256")
                     if gone in html]


def picked(data, path):
    """The value at a dotted `path` in viewer data ("*" maps over a list, a number indexes), ABSENT when not there."""
    if not path:
        return data
    head, _, rest = path.partition(".")
    if head == "*":
        return [picked(each, rest) for each in data]
    try:
        found = data[int(head)] if head.isdigit() else data[head]
    except (KeyError, IndexError, TypeError):
        return ABSENT
    return picked(found, rest)


def number_of(html, label):
    """The value a number card labelled `label` shows, or None when the page has no such card."""
    found = re.search(rf'<div class="num-label">{re.escape(label)}</div>\s*<div class="num-value" data-v>(.*?)</div>',
                      html, re.S)
    return found and found.group(1)


# The library's branches as the API answers them: (node, the fields read from each child, the children in order).
BRANCHES = [("surface", ("label", "count"), [("Made by code", 1), ("Brushed steel", None)]),
            ("surface/made_by_code", ("href",), [("/library/algorithm/surface_recipes/1/",)]),
            ("light", ("href",), [("/library/light/sky.alpha/1/",)]),
            ("place/alpha", ("href",), [("/library/place/alpha/1/",), ("/library/concept/alpha/1/",),
                                        ("/library/layer/base.alpha/1/",)]),
            ("model/piece", ("label", "count", "tone"), [("Crate", 91, "done"), ("Lamp post", 42, "review")])]
# The shelf's kinds on the library screen, counted by hand: 3 models, 2 surfaces (steel and the recipes' made-by-code
# folder), 3 scenes (the place, its concept, its base layer); no Algorithms, Films, Ground or Layers shelf.
SHELVES = (("Models", 3), ("Surfaces", 2), ("Kits", 1), ("Effects", 1), ("Skies", 1), ("Lamps", 1), ("Sound", 1),
           ("Physics", 0), ("Scenes", 3))
NO_SHELF = ("Algorithms", "Films", "Ground", "Layers")

# The folder judge: (case, its entries as (stem, first rank, how many, place, version, state) rows, what the tree then
# holds as {(fact, node or kind): expected}); a fact is "ids" (a node's children), "labels" (their label and count),
# "count" (a node's count) or "versions" (the versions a kind's members keep).
FOLDERS = [
    ("by name, then place; singles to other",
     [("wall_upper_plain", 0, 30, "alpha", 1, "draft"), ("wall_upper_plain", 0, 20, "beta", 1, "draft"),
      ("wall_lower", 0, 4, "alpha", 1, "draft"), ("lamp", 0, 1, "alpha", 1, "draft"), ("crate", 0, 1, "alpha", 1, "draft")],
     {("ids", "model/wall"): ["model/wall/wall_lower", "model/wall/wall_upper"],
      ("labels", "model/wall/wall_upper"): [("from alpha", 30), ("from beta", 20)], ("count", "model/other"): 2}),
    ("of versions 1, 2 locked and 3 draft, the newest locked",
     [("crate", 0, 1, "alpha", 1, "locked"), ("crate", 0, 1, "alpha", 2, "locked"), ("crate", 0, 1, "alpha", 3, "draft")],
     {("versions", "model"): [2]}),
    ("a withdrawn one in no folder",
     [("crate", 0, 1, "alpha", 1, "draft"), ("crate", 1, 1, "alpha", 1, "withdrawn")], {("count", "model"): 1})]

# The library as each reader finds it, moment by moment on one shelf copy (LIBRARY_MOMENTS): (moment, who, what is
# read, the facts expected). `who` is a user reading a cockpit page or the API (hosted in the "hosted" moment, through
# the export), "export" (an export built by that name now), "bare cache" (the library with no blob folder, at an
# entry) or "library" (lib.library() itself); a fact's key is its probe and argument; "{name.attr}" in what is read, a
# key or a value is filled from the shelf's own entries. Each item page also keeps item_rules.
LIBRARY_SEEN = [
    ("made", "joey", "/library/model/lamp_post.alpha/1/", {  # its light copy, then its whole copy; the close-up beside
        "viewer mode": "copy", "viewer light": "/library-files/files/{lamp.web3d_light.sha}",
        "viewer full": "/library-files/files/{lamp.web3d.sha}", "count <video": 0,
        "count /library-files/pictures/{lamp.closeup.sha}.jpg": 1, "number parts": "3",
        "number score": "42 <small>%</small>"}),
    ("made", "joey", "/library/surface/brushed_steel.alpha/1/", {  # colour and roughness from its material
        "viewer token": "steel", "viewer finish.colour": [0.5, 0.25, 0.125], "viewer finish.roughness": 0.35,
        "viewer palette.sign-gold.0": "#"}),
    ("made", "joey", "/library/layer/light.alpha/1/", {  # a lamp's power 3 x 2 = 6
        "viewer lamps.*.type": ["point", "sun"], "viewer lamps.*.name": ["light_2", "sun_1"],
        "viewer lamps.*.power": [6.0, 1.0]}),
    ("made", "joey", "/library/sound/hum.alpha/1/", {
        "count data-wave=": 2, "number loudness": "-22.0 <small>LUFS</small>", "number length": "4.3 <small>s</small>"}),
    ("made", "joey", "/library/effect/devil.alpha/1/", {  # its settings without its sources in words
        "viewer settings.count": 15000, "viewer settings.from": ABSENT}),
    ("made", "joey", "/library/light/sky.alpha/1/", {"viewer mode": "sky", "viewer sky": "dome"}),
    ("made", "joey", "/library/kit/alpha/1/", {"viewer mode": "kit", "viewer inside": True, "number pieces": "12"}),
    ("made", "joey", "/library/model/wrench/1/", {"count <video": 0, "shown .mp4": []}),  # an old clip never played
    ("made", "joey", "/library/algorithm/surface_recipes/1/", {  # a score means nothing here; its nodes counted
        "numbers say score": False, "count surfaces bake &times; 2": 1}),
    ("made", "joey", "/library/model/crate/1/", {"viewer": None, 'count value="withdraw"': 1}),
    ("made", "guest", "/library/model/crate/1/", {"count data-post": 0}),  # only the owner decides
    ("made", "joey", "/library/model/nothing/1/", {"status": 404}),
    ("made", "joey", "/library/place/alpha/1/", {"count <iframe": 0}),  # no 3D copy made yet
    ("made", "joey", "/api/library/children?node=nowhere", {"status": 404}),
    # The file routes serve only files an entry lists.
    ("made", "joey", "/library-files/thumbs/{walker.picture}.jpg", {"type": "image/jpeg"}),
    ("made", "joey", "/library-files/view/{walker.glb.sha}.json", {"json triangles": 1}),
    ("made", "joey", "/library-files/view/{walker.glb.sha}-light.glb", {"status": 404}),
    ("made", "joey", "/library-files/files/{zero}", {"status": 404}),
    ("made", "joey", "/library-files/files/{unlisted}", {"status": 404}),
    ("made", "guest2", "/library/model/crate/1/3d/", {"status": 404}),
    # The export, light copies only: twice the same; every picture; 5 library files (two takes, two light copies, the
    # print), never a whole copy or an old clip.
    ("made", "export", "one", {"library files": 5, "entries listed": True, "pictures not written": []}),
    ("made", "export", "two", {"written as one": True}),
    ("made", "bare cache", "place/alpha@1", {"picture": None}),
    ("demo kept", "joey", "/library/algorithm/surface_recipes/1/", {"count >The beds<": 1, "number plants": "9"}),
    ("demo missing", "joey", "/library/algorithm/surface_recipes/1/", {
        "count no example of its work is here yet: no example kept": 1}),
    ("copy made", "joey", "/library/layer/base.alpha/1/", {'count <iframe src="/view/alpha?embed=1"': 1}),
    ("cache kept", "bare cache", "place/alpha@1", {"picture": True, "blob": "place/alpha/1/{place.picture_file}"}),
    ("kit marked other", "joey", "/library/kit/alpha/1/", {"viewer": None, "count >3D not here<": 1}),
    ("kit marked own", "joey", "/library/kit/alpha/1/", {"count >3D missing<": 1}),
    ("kit marked own", "export", "three", {"kit missing": ["web3d/light.glb"]}),
    ("hosted", "library", "", {"kind": "ExportedLibrary", "entries": 15}),
    ("hosted", "joey", "/api/library/children?node=model/piece", {"labels": ["Crate", "Lamp post"]}),
    ("hosted", "joey", "/library/model/lamp_post.alpha/1/", {
        "viewer light": "/library-files/files/{lamp.web3d_light.sha}", "viewer full": None}),
    ("hosted", "joey", "/library/character/walker/1/", {"count /3d/": 0})]
LIBRARY_MOMENTS = ("made", "demo kept", "demo missing", "copy made", "cache kept", "kit marked other",
                   "kit marked own", "hosted")

# The owner's library actions on the one shelf, in order, each followed by what the library then holds: (who, how,
# the addresses, its refine option, whether an agent started it (None: as the test runs), the answer, then (the lamp's,
# the hum's and the crate's states, the refine items, what waits on the sync, the remote's last commit subject)).
LOCK_SUBJECT = "lock: 2 entries, the owner's decision on the cockpit (joey)"
LIBRARY_ACTS = [
    ("joey", "refine", ["model/lamp_post.alpha@1", "model/crate@1"], None, None, (200, 2),
     ("draft", "draft", "locked", 2, {}, "entries")),
    ("joey", "refine", ["model/crate@1"], None, None, (200, 0), ("draft", "draft", "locked", 2, {}, "entries")),
    ("joey", "refine", ["model/crate@1"], "repaint", None, (400, "Crate has no refine option 'repaint'"),
     ("draft", "draft", "locked", 2, {}, "entries")),
    ("guest", "refine", ["model/crate@1"], None, None, (403, "only the owner"), ("draft", "draft", "locked", 2, {}, "entries")),
    ("joey", "ask here", ["model/crate@1"], None, None, "refused: Crate is locked; only a draft entry can be locked", ("draft", "draft", "locked", 2, {}, "entries")),
    ("joey", "ask here", ["model/lamp_post.alpha@1"], None, True,
     "refused: this process was started from an agent's shell, and an agent never locks",
     ("draft", "draft", "locked", 2, {}, "entries")),
    ("guest2", "ask", ["model/crate@1"], None, False, (403, "only the owner"), ("draft", "draft", "locked", 2, {}, "entries")),
    ("joey", "ask", ["model/lamp_post.alpha@1", "sound/hum.alpha@1"], None, False, (200, "locked 2 entries"),
     ("locked", "locked", "locked", 2, {}, LOCK_SUBJECT)),
    ("joey", "ask hosted", ["model/crate@1"], None, False,
     "queued: the library's machine will withdraw 1 entry on its next sync",
     ("locked", "locked", "locked", 2, {"model/crate@1": "withdraw"}, LOCK_SUBJECT)),
    ("mallory", "apply", ["model/crate@1"], None, False, "refused",
     ("locked", "locked", "locked", 2, {"model/crate@1": "withdraw"}, LOCK_SUBJECT)),
    ("joey", "apply", ["model/crate@1"], None, False, "done",
     ("locked", "locked", "withdrawn", 2, {"model/crate@1": "withdraw"},
      "withdraw: 1 entry, the owner's decision on the cockpit (joey)"))]


def folder_entries(rows):
    """The LibraryEntry rows a FOLDERS case names: each (stem, first rank, count, place, version, state)."""
    from score.dashboard.state import library as lib
    return [lib.LibraryEntry(address=f"model/{stem}_{rank}.{place}@1", kind="model", entry_id=f"{stem}_{rank}.{place}",
                             version=version, title=stem, state=state, place=place, tags={"model": ["piece"]})
            for stem, first, count, place, version, state in rows for rank in range(first, first + count)]


def folder_fact(made, fact, where):
    """One fact of a folders() answer: a node's children ids, their (label, count) pairs or its count, or the versions
    a kind's members keep."""
    if fact == "versions":
        return [found.version for found in made["members"][where]]
    node = node_of(made["tree"], where)
    if fact == "count":
        return node["count"]
    return [child["id"] if fact == "ids" else (child["label"], child["count"]) for child in node["children"]]
def node_of(tree, node_id):
    for node in tree:
        if node["id"] == node_id:
            return node
        found = node_of(node["children"], node_id)
        if found:
            return found
    return None

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


HOSTED_TEST = "test_cockpit_is_the_owners_true_view"


@pytest.fixture(scope="module", autouse=True)
def hosted_child(request, built_once, shelf_once, tmp_path_factory, django_db_setup, django_db_blocker):
    """HOSTED_TEST's fresh hosted process (HOSTED_CHILD) over a copy of this file's world and shelf, exported as that
    test would (the export reads the empty test database's checkouts), started with the file's first test so it runs
    beside the others (a fresh Django and its migrate are most of its time); None when that test is not run."""
    if not any(item.name == HOSTED_TEST for item in request.session.items):
        yield None
        return
    tmp_path = tmp_path_factory.mktemp("hosted-child")
    shutil.copytree(built_once[True].root, tmp_path, symlinks=True, dirs_exist_ok=True)
    shutil.copytree(shelf_once, tmp_path, symlinks=True, dirs_exist_ok=True)
    config = tmp_path / "lib" / ".git" / "config"
    config.write_text(config.read_text().replace(str(shelf_once / "remote.git"), str(tmp_path / "remote.git")))
    world = fixture.opened(tmp_path, dict(built_once[True].outputs))
    world.source.home.mkdir(parents=True, exist_ok=True)
    home = tmp_path / "hosted"
    with override_settings(SCORE_LIB_ROOT=str(tmp_path / "lib"), SCORE_LIB_BLOBS_DIR=str(tmp_path / "blobs"),
                           SCORE_LIB_COMMAND=f"{sys.executable} {tmp_path / 'score_lib_command.py'}"), \
            django_db_blocker.unblock():
        building.build(world.source, home / "export" / "one", MADE, 50, SPEND, world.root)
    (home / "export" / "current").symlink_to("one")
    env = {**os.environ, "SCORE_DASHBOARD_MODE": "hosted", "SCORE_DASHBOARD_HOME": str(home), "SCORE_LIB_ROOT": "",
           "DJANGO_SETTINGS_MODULE": "score.dashboard.site.settings", "PYTHONPATH": str(REPO)}
    child = subprocess.Popen([sys.executable, "-c", HOSTED_CHILD], env=env, cwd=tmp_path, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
    yield child
    child.kill()
    child.communicate()


# --- what the pages are made of: plain names, the theme's tokens, no provider (rows and one sweep in the one test) ---

NAMES = [  # (kind, library id, library title) -> the plain name, or the whole (name, hover text) pair where pinned
    (("algorithm", "surface_recipes", "Surface functions: ProcFunc material recipes and wear"),
     ("Surface finishes", "Surface functions: ProcFunc material recipes and wear")),
    (("ground", "earth.flat", "Flat ground (earth)"), "Flat ground, earth"),
    (("model", "ac_unit_1", "Ac unit 1"), "Air conditioner 1"),
    (("model", "apron_2p6", "Apron 2p6"), "Apron 2.6 m"),
    (("effect", "drift_0_3.camp", "Drift 0 3"), "Drift, row 1 spot 4"),
    (("layer", "light.camp", "Camp light layer"), "Camp lamps"),
    (("model", "wrench", "Wrench"), ("Wrench", ""))]

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
INKS = [(ink, ground) for ink in ("--color-primary", "--color-text-body", "--color-text-light", "--color-text-faint",
                                  "--color-accent")
        for ground in ("--color-bg", "--color-bg-section", "--color-bg-raised")]
INKS += [("--color-accent-ink", "--color-accent")]
INKS += [("--color-on-status", status) for status in ("--color-idle", "--color-gap-missing", "--color-gap-gate",
                                                     "--color-gap-route", "--color-gap-lost")]
GAP_KINDS = ("missing", "gate", "route", "lost")


def literal_colours(path):
    """Each hard-coded colour in one template or static file, as (line number, the literal)."""
    found = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        declarations = [line] if path.suffix == ".css" else [f":{value}" for value in STYLE.findall(line)]
        literals = [*HEX.findall(line), *FUNCTION.findall(line), *NUMBER_HEX.findall(line),
                    *(colour for value in declarations for colour in CSS_NAMED.findall(value))]
        found += [(number, literal) for literal in literals]
    return found


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


# The viewer look check (tests/viewer_look.py, run by hand): a film picture beside a viewer picture of each colour, its
# measures (all where exact, else those pinned) and whether it passes; then a camera and the viewer link it opens.
FILM_COLOUR = (120, 110, 100)
LOOKS = [  # (viewer colour, measures, passes, exact: every measure pinned)
         (FILM_COLOUR, {"difference": 0.0, "structure": 1.0, "brightness": 1.0, "pink": 0.0, "black": 0.0}, True, True),
         ((0, 0, 0), {"black": 1.0}, False, False),
         ((240, 130, 150), {"pink": 1.0}, False, False)]
CAMERA = {"eye": [1, 2, 3], "aim": [4, 5.5, -6], "fov": 80.0}
VIEWS = [(132, "view=1.000000,2.000000,3.000000,4.000000,5.500000,-6.000000,80.000000&t=132.000"),
         (None, "view=1.000000,2.000000,3.000000,4.000000,5.500000,-6.000000,80.000000")]

# owner rule "No provider here" (dashboard overlay): nothing in this package imports tools.* or score.adapters or
# names a provider (one is named only by its cost line's label); deploy/ holds templates only, every host a placeholder.

PACKAGE = REPO / "score/dashboard"
TEXT = (".py", ".html", ".css", ".js", ".yml", ".example", ".env", ".md", "")


def provider_words():
    """The stems of the cloud backends and cluster modules, and the words of the providers the models adapter's
    paid APIs name (score/adapters/models API); a test file beside them (test_<invariant>.py) names none, nor does the
    `local` backend (this PC, never rented: no provider, and "local" is the cockpit's own mode word), nor
    `card_turn` and `card_queue` (no backends: the Blender startup script that shares the card's turns and this PC's
    one card queue, backends overlay; their stem "card" failed every overlay that says a card)."""
    stems = {path.stem.split("_")[0] for folder in ("tools/cloud/backends", "tools/cloud/k8s/clusters")
             for path in (REPO / folder).glob("*.py") if not path.stem.startswith(("_", "test_"))
             and path.stem not in ("local", "card_turn", "card_queue")}
    models = (REPO / "score/adapters/models/__init__.py").read_text()
    for provider in re.findall(r'"provider":\s*"([^"]+)"', models):
        stems |= {word for word in re.split(r"[^a-z]+", provider.lower()) if word not in ("api",)}
    return {stem for stem in stems if len(stem) > 3}


def cloud_modules():
    return {path.stem for path in (REPO / "tools/cloud").rglob("*.py")}


def imported(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def deploy_value_ok(line):
    """A deploy template's `NAME=value` line holds a placeholder, nothing or a plain non-host word."""
    if line.strip().startswith("#") or "=" not in line or not line.split("=", 1)[0].isupper():
        return True
    value = line.split("=", 1)[1].strip()
    return bool(value == "" or value.startswith("<") or re.fullmatch(r"[\w./:-]+", value) and not re.search(
        r"\.(org|com|net|nl|io)\b", value))

# === the one question: what the owner sees and who may act on it =====================================================

def test_cockpit_is_the_owners_true_view(world, built_once, settings, tmp_path, tmp_path_factory, monkeypatch,
                                         shelf_once, hosted_child):
    """One world (the fixture environment, alpha's gaps checked and priced, the month's books lost) walked through every
    page, then acted on by the owner, a guest, a stranger, a page without its CSRF token and the sync applier. Each
    page answers the owner and sends a stranger to sign in; node ids stay in the details fold; a screen holds at most
    WORD_BUDGET words outside data, no traceback and no stop or month figure; every post needs its CSRF token and a
    back link stays on this site; only the owner decides (a worse output needs his reason), advances and is applied;
    a change request lands in the inbox and "this"/"next" queue the right stage; a paid launch waits until he advanced
    both outputs it reads; hosted, his advance is queued.
    Breaks (each applied once and seen red): pages/views.py `place_page` raises for beta; site/settings.py drops
    CsrfViewMiddleware; templates/pages/step.html prints `{{ detail.node }}` beside each read; pages/actions.py
    `decide` sends `worse_reason or 'none'`; pages/views.py `step_queue` queues the step itself for "next";
    pages/seen.py `unseen_reads` holds nothing back (`if False:`); sync/applying.py `apply_advance` skips its
    `from_owner` check; pages/views.py `step_advance` answers without recording (`said = "advanced"`);
    templates/pages/stats.html gains a paragraph of 54 plain words.
    First, what the pages are made of: each library name in plain words with its title kept as hover text; no package
    file holds a literal colour, names a token never defined, names a provider (the stems of the repository's own cloud
    backends and API kinds), imports tools, the adapters or a cloud module, or (deploy/) holds a real host; the inks
    hold WCAG AA on every ground and the four gap colours stay apart; the token files and the font are served; the
    viewer look check (tests/viewer_look.py) passes a picture against itself, fails black or pink and links its camera.
    Breaks (each applied once and seen red): state/names.py drops its 2p6 -> 2.6 m rule; static/pages/dash.css gains
    `a { color: #ff0000; }`; design/tokens/colours.css sets --color-text-faint to #1a1d22; site/asgi.py mounts
    /static/design at the static folder; tests/viewer_look.py `passes` returns True; `import tools.cloud.ledger` in
    score/dashboard/state/money.py; a comment naming the cloud provider (a stem of tools/cloud/backends) in
    score/dashboard/state/money.py; a real host (`HOST=cockpit.example.com`) in a score/dashboard/deploy template.
    And the runner's prices, summed and never made: each basis summed apart, a guess never measured, a place never
    checked has no price; a lost item and a place in plain words; keys outside the index walk only their folder and
    match the store's own answer; a standalone check's findings stand only while what they judged is accepted; a price
    on other code, other per-unit prices, uncommitted code, none, or under a gaps check run again shows no figure; a
    step two places share is in both rows and neither's own; the milestones go through the export whole; a lost input
    read by two places and the world is one gap.
    Breaks (each applied once and seen red): state/gaps.py `money_of` counts the guessed nodes as measured;
    state/gaps.py `place_row` sums the money of a place never checked; state/plain.py `lost_item` splits at the last
    colon; state/index.py `scoped` keeps only keys one folder below the prefix; state/local.py `check_findings` reads
    findings.json whole instead of `current_findings`; state/local.py `price_stale` ignores `code_moved`;
    state/local.py `gaps_price` remembers its read without `gaps_written()` in the key; state/gaps.py `own_sum` keeps
    nodes another place's chain also has (`reach[node] == 1` dropped); state/local.py `gaps_price` leaves `milestones`
    out of the GapsPrice; state/local.py `gaps_total` drops `lost_once`.
    And the pure judges of the cockpit's numbers: the spend by day takes the bills' growth, else the ledger, else a
    gap, its chart's ticks and its scale; a withdrawn library place is no 3D for its place screen.
    Breaks (each applied once and seen red): pages/cockpit.py `spend_by_day` takes a missing day before as 0.0 (its
    whole reading as the day's growth); state/screens.py `web3d_link` drops its withdrawn check.
    And the 3D viewer, the Environment, Place and Stats screens and the step page over alpha's gaps priced and
    prepare's record (the blocks after the library): the gaps framed with or without a web copy, each layer's step
    named; each place's worst gap and its concept on its tile, the top bar the Buy's figure; the remake on every page
    what Buy buys, its time a floor while a step is untimed; stats numbers, a partial bill unknown, not a figure; the
    place screen's top level and a branch's items priced with his one action; outside places opened to what sits
    inside; the step page's own picture and what it read; in a headless browser (when one runs here), the lamp's click
    loads its branch once, fills the panel, frames its gap in the 3D view and posts its Accept with the CSRF token.
    Breaks (each applied once and seen red): pages/present.py `gap_marks` keeps findings with no box; state/gaps.py
    `place_row` takes the mildest kind as the worst (KINDS reversed); pages/cockpit.py `remake` gives
    `at_least_hours` None; pages/cockpit.py `known` reads a partial line's euros as a figure; pages/cockpit.py
    `gap_action` drops its accept of a waiting output; pages/cockpit.py `tiles` drops its `parent_of(...) == at`
    filter; templates/pages/step.html drops the "reads:" caption; static/pages/dash.js never posts the `{gap}`
    message to the viewer frame (`if (false)`; red only where the browser runs).
    And the library, on a copy of the file's shelf: its kinds counted from its entries, no entry until a branch opens;
    a branch a page at a time; folders by name then place, one newest locked version, no withdrawn entry; each item
    played live from its own files; an algorithm's real example, else why not; the export carries light copies only,
    read whole by a hosted cockpit, and a lost copy is said missing; files served only where an entry lists them; only
    the owner refines, locks and withdraws, never an agent; a hosted library screen imports nothing the hosted image
    lacks, and a library with no blob folder reads its pictures from the store side's cache.
    Breaks (each applied once and seen red): state/library.py `shelf_of` puts every algorithm on its own shelf;
    pages/library.py `children` never adds the "more" branch (`left = 0`); state/library_tree.py `folders` keeps
    withdrawn entries; state/library.py reads a lamp's power as its intensity alone; state/library.py `demo` returns
    None; state/library.py `export_three_d` adds each entry's whole web copy; state/library.py `missing` reads any
    `.lost` mark as lost, whatever sha it names; state/library.py `blob` serves any sha in the blob folder;
    pages/library_actions.py `carried_out` skips `actions.agent_started`; pages/library.py imports score.stages;
    state/library.py `blob` looks only in the blob folder.
    And the screens' data over alpha's gaps priced and prepare's record, moment by moment (SCREEN_MOMENTS): the
    environment's remake is prepare's route plus every paid step off it, with its month against the stop; each gap's
    chain priced once; the Buy's stop its high plus 10%; the batch buys now what Buy buys, at its own price, and counts
    what waits with no euros; guesses and untimed kinds kept apart, refused on a basket older than the price; nothing
    bought at a place whose design is not approved (the people's line goes with the places whose cast reads it); an
    estimate from the read inventories that buys nothing, no figure on code not committed; every plant counted; the
    stats count only measured prices; every screen route answers and an unknown place is 404. The Buy page in those
    moments is design first: no design approved, no price and no Buy; alpha's approved, Buy disabled while the basket
    is older than the price, then the close-up EUR 2-3, stop 3.30, two steps waiting, a layer a line and no step's
    name; a guest has no Buy and is refused, and the Benchmarks item is not in the basket. Its books buttons (BOOKS,
    owner rule 2026-10-20): no Basket link; the model calls' figure button while that bill is not read; the read-back
    while paid work is refused; neither to a guest.
    Breaks (each applied once and seen red): state/screens.py `remake_money` leaves `rest` out of the whole;
    `estimate` keeps its figure while stale (`current = True`); `remake_money` drops prepare's `stale`; `chain_price`
    prices every node of the record, not the chain's; `buy` sets the stop at the high, without BUFFER; `now_items`
    keeps items waiting on a missing input; `buy_refusals` never says the basket is older than the price; `now_items`
    drops `approved and for_approved(...)`; `for_approved` ignores an item's `for`; `plants_total` leaves `beds` out;
    `stats` counts every basis as measured; api/routes.py `place_screen` drops its unknown-place 404; pages/basket.py
    `buy_yes` skips its owner check; pages/views.py gives `figure` True whatever the model bill.
    And the run monitor, over its own judging rows, a batch of two tries and one batch on a fresh copy of the world
    (BATCH_MOMENTS): read from its log, its rows and its pool; a relaunch goes on where the checkout was and adds the
    first run's money and clock, its parked machines shown; the state follows the result line, the checkout and the
    pool; the money is this batch's high with its guesses, its room the line less what came before, and its spend of
    one budget; a row's batch gaps are problems; parent scenes before their child scenes; the stops only for the owner
    while the batch lives; an ended try is history; the export carries the batch and the hosted page says how fresh;
    a fault said as a short plain cause, rows sharing one one problem; the next Buy says what it makes again; a Buy
    while the batch is unfinished is its next try; a try shows what it makes again as waiting; what prepare predicts
    shows once made since the try.
    Breaks (each applied once and seen red): state/batch_run.py `pool_of` counts no card busy; `row_states` counts a
    row done whatever its accept's time; `parked_of` counts none; `overall` never says waiting (its pool check `if
    False:`); `overall` drops its launching -> starting line; `own_stop` leaves the spend before out of the room;
    `gap_problems` asks no row for its batch gaps; pages/run_monitor.py `ordered` sorts by the scene's own name only;
    templates/pages/run_monitor.html shows the stops `{% if live %}` (not only to the owner); pages/run_monitor.py
    `ended` always None; sync/building.py `batch_run_file` writes nothing; state/batch_run.py `failure_problem` never
    says in how many places; `next_buy` counts a failed step as never run too (`unrun = planned - made`); `retries`
    ends the batch on a design edit since; checkout/watched.py `batch_ended` ends a batch when `design_at` is past its
    last try; `started` counts a launch stopped before its first heartbeat; state/batch_run.py `gathered` keeps an
    earlier try's line of a row this try makes again; `money_of` gives `left` as the whole budget;
    checkout/watched.py `batch_money` counts spent from 0, not the batch's start; state/batch_run.py `batch_total`
    drops `need`; pages/run_monitor.py `prepared` drops its made-after-the-try comparison.
    And the store's machine, on a fresh copy of the world (PINS, LATCH_STEPS, CARDS, REFUSED, ASKS, STOPS): a Buy is
    refused while a conductor's checkout is off the pin; the sync follows the kill switch latch it set, never one
    whoever started it set; the export carries the machine, its health and its newest tail lines cut to the cap, and
    off a conductor says so with no state on the card; the card offers Allow paid only while latched and says when the
    machine is off the pin; a second machine is shown but claims nothing until the owner confirms it twice; stop
    everything, stop batch and allow paid are the owner's, asked twice, queued hosted and applied once; refused in an
    agent's shell and off a conductor.
    Breaks (each applied once and seen red): sync/client.py `pin_refusal` returns None whatever the commits;
    sync/client.py `free_only_followed` pops FREE_ONLY whenever the latch file is gone; state/machine.py `cut` drops
    the newest lines (`pop()`), not the oldest; state/machine.py `state_of` reads no state as idle; state/machine.py
    `card` gives `code_off` False always; api/routes.py `machine_confirm` skips `asked_twice`; sync/client.py
    `answered` applies a request it could not claim; pages/actions.py `owner_figure_off_why` drops its `agent_started`
    refusal.
    And the concept review, on a fresh drafting copy (alpha drawn the day before, beta not, nothing locked) and the
    queue emptied: a draw at another price, a Draw all whose total or places moved and anything by anyone else is
    refused; Draw all is one yes for N first draws at N times the price; his click is a spend yes at the price shown; a
    draw with no mark and no note is fresh from the place's wording; a Discuss is answered, refused at another price,
    sent with the next redraw and its cost summed; his marks go to the prompt model, whose prompt becomes the wording;
    his edited wording is kept until back to generated, hosted too; a pick waits on the layer above; Lock refuses a
    draw and Unlock frees it, never for an approved design; a place's page names what it holds directly; the listener
    says an unreachable side and asks again. Then a second fresh copy drawn hosted: draws on their way are not offered
    twice and show until they land, a refused one says why; a draw reaches the listener once and its picture is served.
    Breaks (each applied once and seen red): pages/concepts.py `concept_draw` sends no marks; `concept_draw` takes the
    newest draw as the base when none is posted; `concept_draw` drops the posted `wording`; score/review/web.py
    `concept_draw` drops its price comparison; score/review/concepts.py `pick` skips `step_refusal`; sync/client.py
    `answered` sends no picture back; sync/listen.py `listen` pauses SHORTEST_ROUND after an unreachable side;
    pages/concepts.py `draw_all` prices N draws as one; `concept_draw_all` drops its places comparison; `draw_all`
    offers places with a draw on its way; `asked_to_hold` adds the places two levels down; score/review/concepts.py
    `redrawn` leaves the open discussion out of the prompt rewrite.
    And the environment, on a fresh world copy: environment 1's concept is today's data, locked, each body said from
    the physics (the Moon orbits Earth every 27.3 days, gravity 1.62; Mars a year of 687 days, a day of 24.6 h, 3.7),
    the page's questions the store's; a house setting is its plot from above with its sun's path where overhead.py
    puts it at three moments (SUN_MOMENTS); the environment's plan keeps his scene times, its sky worked out from the
    setting (owner 2026-10-21: no fixed sky), a daylight concept's night time moved to sun up and said, anyone else
    refused; unlock asks to be sure and puts every draw out of date; a new reference goes to the bucket, never the
    repository, its bytes dropped once read; save, send, take and lock reach the store at the price shown and only
    for the owner; a hosted save shows at once and the listener applies it, and an export made before the environment
    concept takes no click.
    Breaks (each applied once and seen red): pages/setting_picture.py `every` words a period in hours;
    pages/setting_picture.py `far_way` drops the light's tilt (season 0); score/review/environment_plan.py keeps a
    daylight site's night time (`if True:`); pages/environment.py `save` unlocks without `sure`; score/review/web.py
    `environment_ask` drops its price comparison; pages/environment.py `requests_of` keeps an answered picture's
    bytes; pages/environment.py `shown` ignores his saves since the export.
    And the basket, on a fresh world copy: an item counts what changes (2 added, 1 taken out, 1 refinished) at its
    measured price, a guess is said as no price (owner rule, a wording check, 2026-10-18); the viewer outlines the
    added, the lamp and the floor after and the removed, the lamp and the floor before; only the owner chooses, and a
    choice on another version is not kept; hosted, his answer is kept only once the store's machine applies the
    owner's and his checkout carries the items he saw; his answers, his own or the recommended one, kept where agents
    read them, a visitor's refused.
    Breaks (each applied once and seen red): templates/pages/basket_item.html words the guess as "cost about EUR
    2.70"; pages/basket.py `choose` skips its version check; sync/applying.py `apply_answer` skips its `from_owner`
    check; pages/basket.py's marks put `removed` on the after side.
    And a place's design on a fresh drafting copy, from its draw to its plan: no numbers and no plan until its
    inventory is read from its locked concept; its reading boxed on the concept page, its euros in the totals; his
    Keep his own, the inside places he names a card and a concept page each, Make plan his yes at the price shown,
    the plan written with its gaps; findings older than the lock a check; a draw on a moved room out of date and a
    merged scene no card, hosted too; another lock or an unlock: nothing counts.
    Breaks (each applied once and seen red): state/screens.py `inventory_current` drops its sha equality;
    pages/concepts.py `reading_view` divides a box's width by the picture's height; pages/plans.py `asked_of` skips
    its owner check; score/review/plans.py keeps a named place's spaces (no `_`); pages/plans.py `plan_write` sends
    EUR 0, not the price he saw; score/review/plans.py `moved_draws` never finds a room moved."""
    from score.dashboard.pages import cockpit, present, views
    from score.dashboard.pages.models import BasketItem, ChangeRequest
    from score.dashboard.state import gaps as gap_rows
    from score.dashboard.state.index import scoped
    from score.dashboard.state.models import GapsPrice
    from score.dashboard.state.names import plain as named
    from score.dashboard.tests import viewer_look
    from score.store import runtime_store

    # What the pages are made of, swept before the world is walked; each fault is named by its file, row or link.
    words, cloud, deploy = provider_words(), cloud_modules(), PACKAGE / "deploy"
    assert words, "the provider list came out empty: the sweep would prove nothing"
    sources = set(SOURCES)
    defined = {name for path in (TOKENS / "colours.css", TOKENS / "scale.css", *SOURCES)
               for name in DEFINED.findall(path.read_text())}
    faults = {f"name {row}": named(*row) for row, want in NAMES
              if (named(*row) if isinstance(want, tuple) else named(*row)[0]) != want}
    for path in sorted(path for path in PACKAGE.rglob("*") if path.is_file() and "__pycache__" not in path.parts):
        text = path.read_text(errors="replace") if path.suffix in TEXT or path.parent == deploy else ""
        found = [*literal_colours(path), *sorted({name for pair in USED.findall(text) for name in pair if name}
                                                 - defined)] if path in sources else []
        found += [word for word in words if path.suffix in TEXT and path.name != pathlib.Path(__file__).name
                  and re.search(rf"\b{re.escape(word)}\b", text.lower())]
        found += [name for name in (imported(path) if path.suffix == ".py" else ())
                  if name.startswith(("tools", "score.adapters")) or name.split(".")[0] in cloud]
        if path.parent == deploy:
            found += [*([] if "TEMPLATE" in text else ["no TEMPLATE"]),
                      *(line for line in text.splitlines() if not deploy_value_ok(line))]
        if found:
            faults[str(path.relative_to(REPO))] = found
    colours = (TOKENS / "colours.css").read_text()
    gaps = [hex_of(f"--color-gap-{kind}", colours) for kind in GAP_KINDS]
    themed = [(pair, ratio) for pair in INKS if (ratio := round(contrast(*(hex_of(name, colours) for name in pair)), 2))
              < 4.5]
    themed += [] if len(set(gaps)) == 4 and hex_of("--color-accent", colours) not in gaps else [("gap colours", gaps)]
    web = hosted_client()
    links = re.findall(r'href="([^"]+)"', (PAGES_ROOT / "templates/pages/tokens.html").read_text())
    themed += [(url, code) for url in [*links, "/static/design/fonts/poppins/poppins-400-latin.woff2",
                                       "/static/pages/tokens.js"] if (code := web.get(url).status_code) != 200]
    look = tmp_path / "look"
    look.mkdir()
    film = look / "film.png"
    Image.new("RGB", (320, 180), FILM_COLOUR).save(film)
    for colour, pinned, passes, exact in LOOKS:
        Image.new("RGB", (320, 180), colour).save(viewer := look / f"{colour}.png")
        measured = viewer_look.measures(film, viewer)
        shown = measured if exact else {key: measured[key] for key in pinned}
        if (shown, viewer_look.passes(measured)) != (pinned, passes):
            themed.append((f"look {colour}", measured))
    themed += [(f"view {frame}", link) for frame, want in VIEWS
               if (link := viewer_look.view_link({**CAMERA, "frame": frame})) != want]
    if themed:
        faults["theme, tokens served, viewer look"] = themed
    price = GapsPrice(made_at="2026-10-19T20:00:00+00:00", nodes=PRICED)
    sums, never = gap_rows.summed(price.nodes), gap_rows.place_row("gamma", [], types.SimpleNamespace(
        stale=None, not_checked=["gamma"], not_current=[], chains={}, nodes={}))
    keys = tmp_path_factory.mktemp("keys")
    for key in KEYS:
        (keys / key).parent.mkdir(parents=True, exist_ok=True)
        (keys / key).write_text("{}")
    days = cockpit.spend_by_day(SPEND_BILLS, SPEND_LEDGER, "2026-10", datetime.date(2026, 10, 6))
    chart = cockpit.day_chart(days)
    judged = {"bases": [(entry["basis"], entry["likely"], entry["high"], entry["nodes"]) for entry in sums["bases"]],
              "guessed": (sums["guessed"]["euros"], sums["guessed"]["nodes"]), "unknown": sums["unknown"],
              "measured of": cockpit.measured_prices(price),
              "never checked: money, rank below every kind": (never["money"], never["rank"] == len(gap_rows.KINDS) + 1),
              "place words": (plain.place_words("old_station"), present.place_title("old_station")),
              "lost items": [plain.lost_item(key) for key in LOST_ITEMS],
              "concepts/cock": sorted(scoped(str(keys), "concepts/cock")),
              "prefixes unlike the store's own answer": [prefix for prefix in KEY_PREFIXES if scoped(str(keys), prefix)
                                                         != runtime_store.FolderStore(keys).keys(prefix)],
              "spend by day": [(day["day"][-2:], day["euros"], day["whole"]) for day in days],
              "a first day": cockpit.spend_by_day([{"day": "2026-10-01", "cloud": 1.0, "models": 1.0}], [], "2026-10",
                                                  datetime.date(2026, 10, 1)),
              "day chart: ticks, bars, gap days": ([tick["euros"] for tick in chart["ticks"]], len(chart["bars"]),
                                                   [gap["day"][-2:] for gap in chart["gaps"]]),
              "unplaced of 10, of none": (cockpit.unplaced(10.0, days), cockpit.unplaced(None, days)),
              "scale tops": [cockpit.scale_top(value) for value in SCALES],
              "3D of a withdrawn library place, then a draft": [screens.web3d_link(types.SimpleNamespace(
                  web3d=lambda place: False), "alpha", library_holding(state)) for state in ("withdrawn", "draft")]}
    if judged != JUDGED:
        faults["the runner's prices and plain words"] = judged
    assert not faults, faults

    # The library, on a copy of this file's shelf, read moment by moment (LIBRARY_SEEN), then acted on (LIBRARY_ACTS).
    from score.dashboard.pages import library as pages_library
    from score.dashboard.state import library as lib
    from score.dashboard.state.library_tree import folders
    shelf_at = tmp_path_factory.mktemp("library")
    with shelf_copy(shelf_once, shelf_at) as shelf:
        blobs, exports, cache = shelf_at / "blobs", shelf_at / "home" / "export", shelf_at / "bare-cache"
        keeper_api, shelves, listed = api(), signed_in().get("/library/").content.decode(), lib.library()
        counted = screens.library_counts(listed)
        models = next(row for row in counted["kinds"] if row["kind"] == "model")
        children = [[tuple(child[field] for field in fields) for child in keeper_api.get(
            "/api/library/children", params={"node": node}).json()] for node, fields, _ in BRANCHES]
        with pytest.MonkeyPatch.context() as paged:
            paged.setattr(pages_library, "PAGE", 1)
            first = keeper_api.get("/api/library/children", params={"node": "model/piece"}).json()
            paging = ([child["label"] for child in first], first[1]["count"],
                      [child["label"] for child in keeper_api.get(first[1]["children_url"]).json()])
        assert ([kind for kind, count in SHELVES if f'<span class="node-label" data-v>{kind}</span><span '
                 f'class="node-count" data-v>{count}</span>' not in shelves],
                [gone for gone in NO_SHELF if f"data-v>{gone}<" in shelves], "Lamp post" in shelves,
                len(prose(shelves)) <= WORD_BUDGET,
                (counted["total"], models["count"], models["locked"], models["pictured"], models["scored"]),
                screens.library_counts(None), children, paging) == (
            [], [], False, True, (15, 3, 1, 3, 2), {"kinds": [], "total": 0}, [want for _, _, want in BRANCHES],
            (["Crate", "more"], 1, ["Lamp post"]))
        for case, rows, want in FOLDERS:
            made = folders(folder_entries(rows))
            assert {key: folder_fact(made, *key) for key in want} == want, case

        named = {"lamp": listed.entry("model/lamp_post.alpha@1"), "walker": listed.entry("character/walker@1"),
                 "place": listed.entry("place/alpha@1"), "zero": "0" * 64,
                 "unlisted": blob(blobs, b"bytes no entry lists")}
        kit = listed.entry("kit/alpha@1").web3d_light.sha
        demos = settings.SCORE_PROPS_HOME / "cache" / "library" / "demos.json"
        mark = listed.cache / "kit/alpha/1/web3d/light.glb.lost"
        writes = {  # each moment's change, as (file, its new text or bytes, or None to remove it)
            "demo kept": [(demos, json.dumps({"surface_recipes": DEMO}))],
            "demo missing": [(demos, json.dumps({"surface_recipes": {"missing": "no example kept"}}))],
            "copy made": [(world.source.web_copies / "alpha" / "alpha.json", json.dumps({"objects": []}))],
            "cache kept": [(cache / "place" / "alpha" / "1" / named["place"].picture_file,
                            (blobs / "blobs" / named["place"].picture[:2] / named["place"].picture).read_bytes())],
            "kit marked other": [(blobs / "blobs" / kit[:2] / kit, None), (mark, "0" * 64)],
            "kit marked own": [(mark, kit)]}
        written = {}

        def read(who, what, want):
            """The facts `want` names, as `who` reads `what` now (LIBRARY_SEEN)."""
            if who == "export":
                made = building.build(world.source, exports / what, MADE, 50, SPEND, world.root)["written"]
                written[what] = made
                if not (exports / "current").exists():
                    (exports / "current").symlink_to(what)
                rows = json.loads((exports / what / lib.EXPORT_ROWS).read_text())
                probes = {"library files": lambda: sum(path.startswith("library/files/") for path in made),
                          "entries listed": lambda: "library/entries.json" in made,
                          "pictures not written": lambda: [each.address for each in lib.library().entries()
                                                           if f"files/{each.picture}-360.jpg" not in made],
                          "written as one": lambda: made == written["one"],
                          "kit missing": lambda: next(row["missing"] for row in rows if row["address"] == "kit/alpha@1")}
                return {key: probes[key]() for key in want}
            if who == "bare cache":
                bare = lib.LocalLibrary(shelf, None, shelf_at / "bare-thumbs", cache)
                sha = bare.entry(what).picture
                probes = {"picture": lambda: (shown := bare.picture_path(sha, 64)) and shown.is_file(),
                          "blob": lambda: str(bare.blob(sha).relative_to(cache))}
                return {key: probes[key]() for key in want}
            if who == "library":
                return {"kind": type(lib.library()).__name__, "entries": len(lib.library().entries())}
            answer = (api if what.startswith(("/api/", "/library-files/")) else signed_in)(who).get(what)
            html = answer.content.decode(errors="replace")
            page = re.fullmatch(r"/library/([^/]+)/([^/]+)/(\d+)/", what)
            if page and answer.status_code == 200:
                assert item_rules(what, html) == [], (what, item_rules(what, html))
            nums = html.split('class="nums"')[-1].split("item-actions")[0].lower()
            probes = {"status": lambda arg: answer.status_code, "type": lambda arg: answer.headers["content-type"],
                      "json": lambda arg: answer.json()[arg],
                      "labels": lambda arg: [node["label"] for node in answer.json()],
                      "viewer": lambda arg: picked(item_data(html), arg), "count": html.count,
                      "number": lambda arg: number_of(html, arg), "numbers": lambda arg: arg.split()[-1] in nums,
                      "shown": lambda arg: [each.name for each in lib.shown_files(lib.library().entry(
                          "{}/{}@{}".format(*page.groups()))) if each.name.endswith(arg)]}
            return {key: probes[key.split(" ")[0]](key.partition(" ")[2]) for key in want}

        def filled(value):
            return value.format(**named) if isinstance(value, str) else value

        with contextlib.ExitStack() as hosting:
            for moment in LIBRARY_MOMENTS:
                for path, content in writes.get(moment, []):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if content is None:
                        path.unlink()
                    else:
                        (path.write_bytes if isinstance(content, bytes) else path.write_text)(content)
                if moment == "hosted":
                    hosting.enter_context(override_settings(SCORE_MODE="hosted", SCORE_HOME=shelf_at / "home",
                                                            SCORE_LIB_ROOT=None))
                for at, who, what, want in LIBRARY_SEEN:
                    if at == moment:
                        want = {filled(key): filled(value) for key, value in want.items()}
                        assert read(who, filled(what), want) == want, (moment, who, what)

        for who, how, addresses, option, agent, said, held in LIBRARY_ACTS:
            with pytest.MonkeyPatch.context() as started:
                if agent is not None:
                    started.setattr(actions, "agent_started", lambda agent=agent: agent)
                if how in ("refine", "ask"):
                    body = {"addresses": addresses, **({"option": option} if option else {}),
                            **({"action": "lock"} if how == "ask" else {})}
                    answer = api(who).post(f"/api/library/{how}", json=body)
                    got = (answer.status_code, answer.json().get({"refine": "added", "ask": "said"}[how],
                                                                 answer.json().get("detail")))
                elif how == "apply":
                    got = applying.apply({"kind": "library", "user": who, "payload": SyncRequest.objects.get(
                        kind="library").payload}, world.source).state
                else:
                    got = library_actions.ask(who, "withdraw" if how == "ask hosted" else "lock", addresses,
                                              hosted=how == "ask hosted")
            remote = subprocess.run(["git", "-C", str(shelf_at / "remote.git"), "log", "-1", "--format=%s"],
                                    capture_output=True, text=True, check=True).stdout.strip()
            assert (got, tuple(lib.library().entry(address).state for address in (
                "model/lamp_post.alpha@1", "sound/hum.alpha@1", "model/crate@1")) + (
                RefineItem.objects.count(), library_actions.waiting(), remote)) == (said, held), (who, how, addresses)

    # A hosted library screen, in its own fresh process over a copy of this world and shelf, imports nothing the
    # hosted image lacks.
    out, err = hosted_child.communicate(timeout=50)
    assert hosted_child.returncode == 0, err[-3000:]
    assert json.loads(out.strip().splitlines()[-1]) == {"codes": [200] * 9, "branch": ["Pieces", "Props"],
                                                        "heavy": []}

    guarded_user, _ = get_user_model().objects.get_or_create(username="joey")
    guarded = Client(enforce_csrf_checks=True)
    guarded.force_login(guarded_user)
    owner, guest = signed_in(), signed_in("guest")
    items = a_gaps_finding(world, settings, tmp_path)

    # The 3D viewer over alpha's gaps: with no web copy (the library's place check above made one; gone here), the gaps
    # alone and no viewer script, framing one naming its row's line; with a copy, no marks unless asked, asked the
    # three boxed gaps (the plan has no box), the light layer linked to its step, the owner's edits no step's.
    copy = world.root / "web" / "alpha"
    (copy / "alpha.json").unlink()
    alone, framed = (owner.get(f"/view/alpha{query}").content.decode() for query in (
        "", "?gaps=1&gap=missing:lamp_2"))
    (copy / "alpha.json").write_text(json.dumps({
        "place": "alpha", "from_output": world.outputs["assembly@alpha"], "made_at": "2026-10-18T12:00:00Z",
        "objects": [{"name": "Lamp", "layer": "light", "low": [0, 0, 0], "high": [1, 1, 1]}], "bytes": 10,
        "light_bytes": 5, "triangles": 12}))
    unasked, asked = (view_data(owner.get(f"/view/alpha{query}").content.decode()) for query in ("", "?gaps=1"))
    framed = view_data(framed)
    marked = next(mark for mark in framed["marks"] if mark["id"] == "missing:lamp_2")
    assert ("view3d.js" in alone, framed["gap"], framed["gaps_only"], marked["sentence"].startswith(
        "A lamp should be in the alpha"), marked["url"], unasked["marks"],
        [{name: mark[name] for name in ("id", "low", "high", "kind")} for mark in asked["marks"]], asked["gaps_only"],
        asked["layers"]["light"], "edit" in asked["order"], "edit" in asked["layers"],
        signed_in("other").get("/view/nowhere").status_code) == (
        False, "missing:lamp_2", True, True, "/place/alpha/#gap-missing:lamp_1", [],
        [{"id": "missing:lamp_1", "low": [0, 0, 0], "high": [1, 1, 1], "kind": "missing"},
         {"id": "missing:lamp_2", "low": [2, 0, 0], "high": [3, 1, 1], "kind": "missing"},
         {"id": "gate:complete/painted:crate_1", "low": [4, 0, 0], "high": [5, 1, 1], "kind": "gate"}], False,
        {"label": "light sweep", "url": "/place/alpha/step/light/"}, True, False, 404)

    # The Environment, Place and Stats screens over alpha's gaps priced on this checkout (the close-up per unit times
    # its forecast, the sound guessed) and prepare's record, the month's model bill partly counted. The tiles: alpha's
    # 4 gaps, worst a route step, its concept; beta none, its concept lost (never a render). The top bar: the cloud
    # bill read, the model bill not ("at least"), no stop; what Buy buys (the remake is batch.now: the close-up, EUR
    # 2-3, 10-20 min), and with an untimed sound added no hours, at least the close-up's. Stats: AI calls and Total
    # unknown, 1 of 2 steps measured, beta complete, the gaps by kind, the days from the bills' growth, no stop and no
    # controls. The place screen: Gaps (2 lamps) and Objects load as they open, the lamp's chain EUR 2-3 with the
    # guessed sound "+", its one action the waiting close-up's accept, the crate failing and its chain unknown, no
    # action for a guest. The step page: its own picture and what it read. Outside places: alpha within beta within
    # the yard is one yard tile summing alpha's gaps, then beta, then alpha alone; a shell holding no place shows not.
    a_gaps_price(world, eta={"likely_minutes": 95.0, "high_minutes": 130.0, "unknown": []})
    a_remake(world)
    world.source.refresh()
    state = world.source.world_state()
    untimed = {"likely_euros": 1.0, "high_euros": 1.0, "basis": "per unit × forecast", "likely_minutes": None}
    remakes = [cockpit.remake(views.batch_of(state)), cockpit.remake(screens.batch(state, [
        {**item, "nodes": {**item["nodes"], "sound@alpha": untimed}} for item in items]))]
    with pytest.MonkeyPatch.context() as month:
        a_month(month, bill_days=[{"day": "2026-10-02", "cloud": 2.0, "models": 0.5},
                                  {"day": "2026-10-03", "cloud": 3.5, "models": 0.5}],
                days=[{"day": "2026-10-01", "cloud": 1.0, "models": 0.0}])
        places, stats = (owner.get(page).content.decode() for page in ("/places/", "/stats/"))
    tiles = dict(re.findall(r'<a class="ptile" href="/place/(\w+)/"(.*?)</a>', places, re.S))
    top = places[places.index('<section class="topbar">'):places.index('<section class="ptiles"')]
    cards = dict(re.findall(r'<div class="num-label">(?:<i [^>]*></i>)?(?:<span data-v>)?([^<]+)(?:</span>)?</div>\s*'
                            r'<div class="num-value[^"]*"[^>]*>(.*?)</div>', stats, re.S))
    stats_main = stats[stats.index("<main>"):]
    [lamp] = owner.get("/place/alpha/branch/?path=Gaps").json()
    [crate] = owner.get("/place/alpha/branch/?path=Objects").json()
    place_html, step = owner.get("/place/alpha/").content.decode(), world.source.step_detail("alpha", "assembly")
    film_step = owner.get("/place/alpha/step/demo-film/").content.decode()
    shown = {
        "tiles": (sorted(tiles), "tone-gap-route" in tiles["alpha"], "<b data-v>4</b>" in tiles["alpha"],
                  "tone-done" in tiles["beta"], "<b data-v>0</b>" in tiles["beta"], '<img src="/thumbs/' in tiles["alpha"],
                  "<img" in tiles["beta"], "concept missing" in tiles["beta"]),
        "top bar: bills, stop, what Buy buys": ("<small>&ge;</small> <small>EUR</small> 12.50" in top,
                                                "not read: Model calls" in top, "250" in top, "stop" in top,
                                                "<small>EUR</small> 2&ndash;3<small>, about 0.2 h" in top),
        "remakes": ((remakes[0]["low"], remakes[0]["high"], remakes[0]["hours"], remakes[0]["unknown"]),
                    (remakes[1]["hours"], remakes[1]["at_least_hours"], remakes[1]["untimed"])),
        "stats cards": [cards[label] for label in (
            "Cloud compute", "AI calls", "Total", "Steps with a measured price", "Places complete", "not made yet",
            "failing a check", "steps of the route still to do", "inputs lost")],
        "stats days, stop, controls": ("<title>2026-10-01: EUR 1.00, at least" in stats,
                                       "<title>2026-10-03: EUR 1.50</title>" in stats, "stop" in stats.lower(),
                                       "<form" in stats_main, "<button" in stats_main),
        "place top level": (bool(re.search(r'<span class="node-label" data-v>Gaps</span><span class="node-count" '
                                           r'data-v>2</span>', place_html)), 'data-title="lamp"' in place_html,
                            'data-title="place:plan" data-state="route" data-tone="gap-route" data-price="unknown"'
                            in place_html),
        "lamp": (lamp["label"], lamp["count"], lamp["tone"], lamp["panel"]["state"], lamp["panel"]["gap"],
                 lamp["panel"]["price"], lamp["panel"]["action"], lamp["panel"]["action_label"],
                 json.loads(lamp["panel"]["body"])),
        "crate": (crate["panel"]["state"], crate["panel"]["price"]),
        "guest's lamp action, a branch nowhere": (
            "action" in guest.get("/place/alpha/branch/?path=Gaps").json()[0]["panel"],
            owner.get("/place/alpha/branch/?path=Nowhere").status_code),
        "step page": (f'src="{step.picture.url}"' in owner.get("/place/alpha/step/assembly/").content.decode(),
                      "reads: OpenUSD stage" in film_step, "reads: completion" in film_step)}  # demo-film's reads
    within = world.data / "places/within.json"
    within.write_text(json.dumps({"shells": {"yard": {"name": "Yard"}, "empty": {"name": "Empty"}},
                                  "within": {"beta": {"within": "yard"}, "alpha": {"within": "beta"}}}))
    outside = {}
    for at in ("", "?in=yard", "?in=beta"):
        html = owner.get(f"/places/{at}").content.decode()
        outside[at] = re.findall(r'<a class="ptile" href="([^"]+)"(.*?)</a>', html, re.S)
    head = html[html.index('<section class="phead"'):html.index('<section class="ptiles"')]
    shown["outside places"] = (
        [href for href, _ in outside[""]], "<b data-v>Beta, 1 room</b>" in outside[""][0][1],
        "tone-gap-route" in outside[""][0][1], [href for href, _ in outside["?in=yard"]],
        "<b data-v>+1</b>" in outside["?in=yard"][0][1], [href for href, _ in outside["?in=beta"]],
        "Outside" in html,  # owner rule (2026-10-20): never an "Outside" card beside its inside places
        '<h1 class="phead-name" data-v>Beta</h1>' in head, "tone-gap-route" in head,
        [owner.get(f"/places/?in={shell}").status_code for shell in ("alpha", "empty")])
    within.unlink()
    world.source.refresh()
    assert shown == {
        "tiles": (["alpha", "beta"], True, True, True, True, True, False, True),
        "top bar: bills, stop, what Buy buys": (True, True, False, False, True),  # owner rule: no stop shown
        "remakes": ((2.0, 3.0, 0.2, 0), (None, 0.2, 1)),
        "stats cards": ["<small>EUR</small> 12.50", "unknown", "unknown", "1<small> of 2</small>",
                        "1<small> of 2</small>", "2", "1", "1", "0"],
        "stats days, stop, controls": (True, True, False, False, False),
        "place top level": (True, False, True),  # only the top level is drawn
        "lamp": ("lamp", 2, "gap-missing", "missing", "missing:lamp_1", "EUR 2.00–3.00 +", "/api/decisions", "Accept",
                 {"node": "closeup@alpha", "output": world.outputs["closeup@alpha waiting"], "decision": "accept"}),
        "crate": ("failing", "unknown"), "guest's lamp action, a branch nowhere": (False, 404),
        "step page": (True, True, True),
        "outside places": (["/places/?in=yard"], True, True, ["/places/?in=beta"], True, ["/place/alpha/"], False,
                           True, True, [404, 404])}

    # The same lamp clicked in a headless browser (when one runs here): the Gaps branch loaded once, the panel filled,
    # the 3D view told to frame its gap, its Accept the owner's JSON request with the CSRF token, the panel a history
    # step of its own.
    if chromium_runs():
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
        assert (found["before"], found["fetched"], found["open"], found["title"], found["state"], found["price"],
                found["button"], json.loads(found["framed"]), found["back"], found["forward"], found["reloaded"],
                found["posted"]) == (
            0, [branch], True, "lamp", "missing", "EUR 2.00–3.00 +", "Accept", {"gap": "missing:lamp_1"},
            {"open": False, "hash": ""}, {"open": True, "title": "lamp"}, {"open": True, "title": "lamp", "steps": 3},
            [{"url": "/api/decisions", "csrf": "token", "body": {
                "node": "closeup@alpha", "output": world.outputs["closeup@alpha waiting"], "decision": "accept"}}])

    # The screens' data (state/screens.py) over alpha's gaps priced and prepare's record, moment by moment
    # (SCREEN_MOMENTS): each moment's record written, then every "source:path" it names read from what the screens,
    # the screen routes and the Buy and Places pages answer on that one world.
    from score import graph
    from score.dashboard.checkout import flow, pricing
    from score.dashboard.launch.backend import GroupPlan
    from score.dashboard.site.asgi import inner
    a_gaps_price(world, nodes=COCKPIT_NODES, eta=COCKPIT_ETA)
    guessed = [{**item, "nodes": {**item["nodes"], "sound@alpha": GUESS, "light-passes@alpha": GUESS,
                                   "rough-model@alpha": {"likely_euros": None, "high_euros": None,
                                                         "basis": "not measured yet"}}} for item in items]
    people = [{"id": ident, "places": places, "nodes": {node: PEOPLE_PRICE for node in nodes}, "missing": [],
               "for": held} for ident, places, nodes, held in PEOPLE]
    inventory = world.source.props_home / "design" / "inventory" / "alpha.json"
    kept_inventory = inventory.read_bytes() if inventory.is_file() else None
    proposals = settings.SCORE_HOME / "proposals"
    basket_made = records.index(proposals)["made_at"]

    def month_api(path):
        """The screen route's answer with the month read as MONTH (its FastAPI dependency)."""
        inner.dependency_overrides[actions.spend] = lambda: MONTH
        try:
            return api().get(f"/api/screens/{path}")
        finally:
            inner.dependency_overrides.pop(actions.spend)

    def environment(state):
        found = screens.environment(world.source, MONTH)
        return {**found, "alpha": next(place for place in found["places"] if place["place"] == "alpha"),
                "pictured": [bool(place["picture"]) for place in found["places"]]}

    def guessed_batch(state):
        found = screens.batch(state, guessed, "2099-01-01T00:00:00Z")
        totals = pricing.totals(pricing.basket_prices(screens.now_items(guessed, screens.approved_places(state))))
        older = screens.batch(state, guessed, "2026-10-19T08:00:00Z")["refused"]
        return {**found, "cleared high": pricing.cleared_high(totals),
                "older": [why.split(OLDER)[0] + OLDER for why in older],
                "unknown age": screens.batch(state, guessed)["refused"]}

    def people_bought(state):
        bought = screens.now_items(people, ["alpha"])
        plan = GroupPlan(missing=[], refusal=None, to_run={}, blocked={}, buys=[
            {"node": node, "why": "", "again": False}
            for node in ("settle@alpha", "closeup@people", "people-dress-pilot-made", "body-face-moon")])
        return {"alpha": [item["id"] for item in bought],
                "gamma": [item["id"] for item in screens.now_items(people, ["gamma"])],
                "refusals": flow.plan_refusals(types.SimpleNamespace(items=bought), [(None, plan)]),
                "beta of the basket": screens.now_items(items, ["beta"])}

    def buy_now(state):
        html = owner.get("/buy/").content.decode()
        after = html[html.index(">Buy now<"):html.index('<ul class="buy-layers buy-design">')]
        return {"unknowns": after.count(">unknown</span>"), "range": "&ndash;" in after,
                "offered": 'data-url="/buy/yes/"' in html, "disabled": f'disabled title="{NOT_COMMITTED}' in after}

    def buy_page(state):
        """The Buy page as the owner reads it, and its Buy yes posted by the owner and by guests."""
        html = owner.get("/buy/").content.decode()
        top = html.split('<ul class="buy-layers buy-design">')[0]
        now = top.split(">Buy now<")[-1]
        refused = owner.post("/buy/yes/", {"key": "a" * 32, "batch": "benchmarks"}, content_type="application/json")
        return {"approved": re.findall(r"(\d+) <small>of</small> 2 <small>approved</small>", top)[0],
                "euros on top": "EUR" in top[top.index('<div class="topbar">'):],
                "offered": 'data-url="/buy/yes/"' in html,
                "older": bool(re.search(r'<button type="button" class="primary big" disabled title="the basket '
                                        r'\(2026-10-19 08:00\) is older than the price', top)),
                "now": ('"batch": "now"' in html, "<small>EUR</small> 2.00&ndash;3.00" in now,
                        "<small>stop EUR</small> 3.30" in now, "+ 2 <small>steps wait</small>" in now),
                "layers": re.findall(r'<span class="node-label" data-v>(\w+)</span><span class="buy-n" data-v>(\d+)'
                                     r'</span>', html),
                "step names": bool(re.search(r"calibration|lost concept|<details", html)),
                "posts": (owner.post("/buy/yes/", "{}", content_type="application/json").status_code,
                          refused.status_code, refused.json()["detail"].startswith("refused"),
                          guest.post("/buy/yes/", {"key": "a" * 32}, content_type="application/json").status_code,
                          'data-url="/buy/yes/"' in signed_in("guest2").get("/buy/").content.decode())}

    def tiles(state):
        found = {"offered": 'data-url="/buy/yes/"' in owner.get("/buy/").content.decode()}
        for page, start, end in (("/buy/", ">After design<", '<ul class="buy-layers buy-design">'),
                                 ("/places/", ">remake<", "Review and buy")):
            html = owner.get(page).content.decode()
            tile = html[html.index(start):html.index(end)]
            found[page] = ["<small>EUR</small> 10&ndash;12<small>, " in tile,
                           "1 <small>of</small> 2 <small>scenes</small>" in tile]
        return found

    def plants(state):
        found = {"world": state.plants, "batch": screens.batch(state, items)["plants"]}
        state.plants = {}
        return {**found, "none": screens.batch(state, items)["plants"]}

    screen_of = {
        "environment": environment, "place": lambda state: {
            **(found := screens.place(world.source, "alpha", None)), "stale": bool(found["price_stale"])},
        "pictures": lambda state: {"alpha is its concept": screens.picture_of(state, "alpha") == (
            f"/thumbs/{state.concepts['alpha'].sha}.jpg", "concept"), "beta": screens.picture_of(state, "beta")},
        "buy none": lambda state: screens.buy(items, {}, MONTH),
        "buy chosen": lambda state: screens.buy(items, {items[0]["id"]: "buy"}, MONTH),
        "batch": lambda state: screens.batch(state, items),
        "batch lost input": lambda state: screens.batch(state, [{**item, "missing": ["a lost input"]}
                                                                for item in items]),
        "batch guessed": guessed_batch, "remake money": screens.remake_money,
        "design": lambda state: screens.design(world.source, state),
        "stats": lambda state: {**(found := screens.stats(world.source, MONTH)), "last day": found["days"][-1]},
        "routes": lambda state: {"codes": [month_api(path).status_code for path in SCREEN_ROUTES],
                                 "exported blocked": WorldState.model_validate_json(world.source.world_state(
                                     MONTH).model_dump_json()).remake.counts["blocked"]},
        "api buy": lambda state: month_api("buy").json(), "people": people_bought, "buy now": buy_now,
        "tiles": tiles, "plants": plants, "buy page": buy_page}
    for moment, record, written, want in SCREEN_MOMENTS:
        a_remake(world, **record)
        if written == "choice":
            BasketChoice.objects.create(item=records.items(settings.SCORE_HOME / "proposals")[0]["id"],
                                        version="0" * 16, choice="buy", by="joey")
        if written == "basket now":
            records.put_index(proposals, {**records.index(proposals), "made_at": graph.now()})
        if written == "plants":
            inventory.parent.mkdir(parents=True, exist_ok=True)
            inventory.write_text(json.dumps({"rows": PLANTS}))
        world.source.refresh()
        state = world.source.world_state()
        answered = {}
        for key in want:
            source = key.split(":")[0]
            if source not in answered:
                answered[source] = screen_of[source](state)
        assert {key: picked(answered[key.split(":")[0]], key.split(":", 1)[1]) for key in want} == want, moment
    (world.root / "props/work/checks/prepare/remake.json").unlink()  # prepare never ran, as the rest below reads it
    if kept_inventory is None:
        inventory.unlink()
    else:
        inventory.write_bytes(kept_inventory)
    BasketChoice.objects.all().delete()
    records.put_index(proposals, {**records.index(proposals), "made_at": basket_made})
    world.source.refresh()

    # A standalone check's findings stand only while what they judged is accepted, and gaps are not repeated among
    # them: a library finding over beta's accepted assembly stands, over another output it is not read.
    library = world.root / "props/work/checks/library/beta"
    (library / "marks").mkdir(parents=True)
    (library / "marks/beta-0.png").write_bytes(fixture.picture((200, 60, 40)))
    stands = []
    for output in (world.outputs["assembly@beta"], "0" * 64):
        (library / "findings.json").write_text(json.dumps({"place": "beta", "outputs": {"assembly@beta": output},
            "findings": [{"rule": "finish not from the library", "prim": "/beta/Objects/crate_1",
                          "sentence": "3 models (crate) finish not from the library", "picture": "marks/beta-0.png"}]}))
        stands.append([finding.rule for finding in world.source.check_findings("beta")])
    assert ([finding.check for finding in world.source.check_findings("alpha")],
            [gap.id for gap in world.source.gaps("alpha")][:1], stands) == (
        [], ["missing:lamp_1"], [["finish not from the library"], []])

    # The price of alpha's gaps gives a figure only while made on this checkout over the current findings: another
    # commit, other per-unit prices, uncommitted code, none at all or the gaps check run again since (on the next read,
    # not after the index's 60 s) give no figure, the why as hover text; prepare never ran, so no remake figure.
    findings = world.root / "props/work/checks/gaps/alpha/findings.json"
    findings_times = (findings.stat().st_atime, findings.stat().st_mtime)
    for row, priced_on, again, why in STALE:
        a_gaps_price(world, **({} if priced_on is HERE else {
            "priced_on": priced_on and {**local.priced_here(), **priced_on}}))
        os.utime(findings, findings_times)
        world.source.refresh()
        before = cockpit.measured_prices(world.source.gaps_price())  # read once, so a remembered read must see a move
        if again:
            findings.write_text(findings.read_text())
            later = (world.root / "props/work/checks/gaps-price/world1.json").stat().st_mtime + 2
            os.utime(findings, (later, later))
        remake = cockpit.remake(views.batch_of(world.source.world_state()))
        said = (remake["why"] == "prepare has not run" if why is None else
                remake["low"] is None and why in remake["why"] and why in unescape(owner.get("/places/").content.decode()))
        figure = (1, 2) if why is None else (None, None)
        assert (said, before, cockpit.measured_prices(world.source.gaps_price())) == (
            True, (1, 2) if again else figure, figure), (row, remake)
    # The books buttons: the model calls' figure while that bill is not read, the read-back while paid work is
    # refused, and only to the owner; never a Basket link.
    for row, models, refused, who, want in BOOKS:
        with pytest.MonkeyPatch.context() as month:
            a_month(month, **({"paid_refused": refused} if refused else {}))
            if models is not None:
                month.setattr(actions, "spend", lambda: Spend(ceiling=250.0, month="2026-10", lines=[
                    CostLine(source="cloud", label="Cloud compute", euros=12.5),
                    CostLine(source="models", label="Model calls", euros=models)]))
            html = signed_in(who).get("/buy/").content.decode()
        # A button shown is a form the page script posts (data-post); a button not shown leaves no trace of its URL.
        as_forms = [f'data-post="/api/money/{url}"' in html for url in ("read-back", "books-figure")]
        as_urls = [f"/api/money/{url}" in html for url in ("read-back", "books-figure")]
        assert ('href="/basket/"' in html.split("<main")[-1], ">Model calls figure</button>" in html,
                *as_forms) == want and as_urls == as_forms, (row, as_forms, as_urls)
    with pytest.MonkeyPatch.context() as month:
        a_month(month, paid_refused="the month's books are lost")
        for page in dict.fromkeys([*PAGES, *SCREENS]):
            answer = owner.get(page)
            html = answer.content.decode(errors="replace")
            assert answer.status_code == 200, page
            assert "Traceback" not in html and "/api/money/stop" not in html and "/api/money/month" not in html, page
            stranger = Client().get(page)
            assert stranger.status_code == 302 and stranger["Location"].startswith("/login/"), page
            found = NODE.search(outside_details(html)) if page in NODE_FREE else None
            assert found is None, (page, found.group(0))
            words = prose(html) if page in SCREENS else []
            assert len(words) <= WORD_BUDGET, (page, len(words), words)

    assert "Accept this output" not in guest.get("/place/alpha/step/closeup/").content.decode()
    for back, status, location in BACKS:
        answer = owner.post("/refresh/", {"back": back})
        assert (answer.status_code, answer["Location"]) == (status, location), back

    # Every post on the one world, each row followed by what the world then holds: (the waiting close-up accepted, by
    # whom, each change request with its inbox file, the queued steps), carried from row to row.
    waiting = world.outputs["closeup@alpha waiting"]

    def held():
        accept = world.store.current_accept("closeup@alpha") or {}
        return (world.store.accepted("closeup@alpha") == waiting, accept.get("by"),
                [(change.node, change.words, (settings.SCORE_HOME / "inbox" / f"{change.pk}.json").is_file())
                 for change in ChangeRequest.objects.all()],
                {(item.place, item.stage) for item in BasketItem.objects.all()})

    untouched = held()
    asked = [("closeup@alpha", "the lamp is too red", True)]
    decide = "/place/alpha/step/closeup/decide/"
    posts = [*((f"no csrf {page}", guarded, page, {"words": "x"}, 403, untouched) for page in POSTS),
             ("guest decides", guest, decide, {"decision": "accept", "output": waiting,
                                               "worse_reason": "one fault is fine here"}, 403, untouched),
             ("worse, no reason", owner, decide, {"decision": "accept", "output": waiting}, 302, untouched),
             ("worse, his reason", owner, decide, {"decision": "accept", "output": waiting,
                                                   "worse_reason": "one fault is fine here"}, 302,
              (True, "joey", [], set())),
             ("change request", owner, "/place/alpha/step/closeup/request/",
              {"words": "the lamp is too red", "output": "x"}, 302, (True, "joey", asked, set())),
             ("queue this", owner, "/place/alpha/step/plan/queue/", {"which": "this"}, 302,
              (True, "joey", asked, {("alpha", "plan")})),
             ("queue next", owner, "/place/alpha/step/scene-record/queue/", {"which": "next"}, 302,  # the stage table:
              (True, "joey", asked, {("alpha", "plan"), ("alpha", "assembly")}))]  # scene-record, then assembly
    for row, actor, page, body, status, after in posts:
        assert (actor.post(page, body).status_code, held()) == (status, after), row

    # Nothing advances unseen: a launch reading assembly and complete is refused until the owner advanced both, by his
    # click here or by his queued request applied on the store's machine; a guest's click and someone else's request
    # advance nothing. Each row: who, how, the node, then the answer, whether it is advanced and what the plan waits on.
    settings.SCORE_LEDGER_FILES = [world.ledger]
    plan = ready_plan([{"node": PAID, "euros": 5.0, "why": "never ran", "again": False}])
    launch = {"kind": "launch", "user": "joey", "payload": {"items": [{"place": "alpha", "stage": "demo-film"}]}}
    clicks, answers = {"guest": guest, "joey": owner}, {302: "done", 403: "refused"}

    def advance(user, how, node):
        if how == "click":
            code = clicks[user].post(f"/place/alpha/step/{node.split('@')[0]}/advance/",
                                     {"output": world.outputs[node]}).status_code
            return answers.get(code, code)
        return applying.apply({"kind": "advance", "user": user, "payload": {
            "node": node, "output": world.outputs[node]}}, world.source).state

    both = {(PAID, "assembly@alpha"), (PAID, "complete@alpha")}
    advances = [("guest", "click", "assembly@alpha", "refused", False, both),
                ("mallory", "request", "assembly@alpha", "refused", False, both),
                ("joey", "click", "assembly@alpha", "done", True, {(PAID, "complete@alpha")}),
                ("joey", "request", "complete@alpha", "done", True, set())]
    for user, how, node, state, advanced, waits in advances:
        refusals = actions.launch_refusals(get_user_model()(username="joey"), plan, True, "")
        assert any(why.startswith("not seen by owner") for why in refusals), (user, how, node, refusals)
        launched = applying.apply(launch, world.source, PaidFilm())
        assert launched.state == "refused" and "not seen by owner" in launched.detail, (user, how, launched.detail)
        assert (advance(user, how, node), bool(seen.advanced(node, world.outputs[node])),
                set(actions.unseen(plan))) == (state, advanced, waits), (user, how, node)
    assert applying.apply(launch, world.source, PaidFilm()).state == "running"


    # The runner's price, split by place and carried whole: a step two places share (the ground, guessed EUR 1) is in
    # both places' rows and in neither's own; the milestones reach the hosted cockpit unchanged; a lost seed read by
    # alpha, beta and the environment plus a take lost at the world are 2 lost inputs, not 4.
    beta = world.root / "props/work/checks/gaps/beta"
    beta.mkdir(parents=True, exist_ok=True)
    (beta / "findings.json").write_text(json.dumps({"place": "beta", "outputs": {
        "assembly@beta": world.outputs["assembly@beta"]}, "findings": [BETA_LAMP]}))
    a_gaps_price(world, nodes={"closeup@alpha": FORECAST, "sound@alpha": GUESSED, "terrain": GUESSED,
                                "closeup@beta": FORECAST},
                 chains={"alpha": {"closeup@alpha": ["closeup@alpha", "complete@alpha", "sound@alpha", "terrain"],
                                   "complete@alpha": ["complete@alpha", "sound@alpha", "terrain"]},
                         "beta": {"closeup@beta": ["closeup@beta", "terrain"]}},
                 gaps={"alpha": {}, "beta": {}}, milestones=MILESTONES)
    world.source.refresh()
    rows = {row["place"]: row for row in gap_rows.per_place(world.source.gaps_price(), {
        place: world.source.gaps(place) for place in ("alpha", "beta")})}
    building.build(world.source, tmp_path / "export", "2026-10-20T09:00:00+00:00", 50, Spend(), world.root)
    exported = ExportedSource(tmp_path / "export").world_state().gaps_price.milestones
    for place, outputs, found in (("alpha", {"assembly@alpha": world.outputs["assembly@alpha"]}, [LOST]),
                                  ("beta", {"assembly@beta": world.outputs["assembly@beta"]}, [LOST]),
                                  ("world", {}, [LOST, TAKEN])):
        folder = world.root / "props/work/checks/gaps" / place
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "findings.json").write_text(json.dumps({"place": place, "outputs": outputs, "findings": found}))
    world.source.refresh()
    total = world.source.gaps_total()
    assert ([(rows[place]["money"]["guessed"], rows[place]["own"]["guessed"]) for place in ("alpha", "beta")],
            exported, total.counts, total.unfillable) == (
        [(2.0, 1.0), (1.0, 0)], MILESTONES, {"lost": 2}, ["earth seed lost", "take lost"])

    settings.SCORE_MODE = "hosted"
    owner.post("/place/beta/step/assembly/advance/", {"output": world.outputs["assembly@beta"]})
    assert SyncRequest.objects.get(kind="advance").payload == {"node": "assembly@beta",
                                                               "output": world.outputs["assembly@beta"]}

    # The run monitor (state/batch_run.py, pages/run_monitor.py, checkout/watched.py). First what it judges on its own,
    # row by row (BATCH_JUDGED), then a batch of two tries gathered by hand (TRIES), then one batch on a fresh copy of
    # the world, bought, launched, read, hosted, relaunched and ended, then tried again (BATCH_MOMENTS).
    from score.dashboard.checkout import watched
    report = tmp_path / "faults.txt"
    report.write_text("  | no card could be rented\n")
    fault = (f"error: CalledProcessError: Command '['/x/blender_cloud.py']' returned non-zero exit status 1; "
             f"fault report {report}")
    fault_rows = {f"light@{place}": ("failed", fault, "2026-10-24T11:09:00+00:00") for place in ("a", "b", "c")}
    [shared] = batch_run.failures({**fault_rows, "film@a": ("not_run", "not run: its line stopped at light@a", None)})
    causes = [(said if want is not None else None, len(said) <= 103 and "/home" not in said)
              for text, tail, want in CAUSES for said in [plain.step_cause(text, tail)]]
    next_buys = [said if whole or said is None else said[:len(want)] for run, nodes, want, whole in NEXT_BUYS
                 for said in [batch_run.next_buy(run, nodes)]]
    judged = {
        "overall": [batch_run.overall({"state": "launched", "launch": {}}, batch_run.read_log(log.splitlines(), set()),
                                      live, pool)[:len(want)] for log, live, pool, want in OVERALLS],
        "causes": causes, "next buys": next_buys,
        "prepared after the try, before it": [run_monitor.prepared(PREPARED_REMAKE, {"at": at}) for at in (
            "2026-10-25T16:00:00+00:00", "2026-10-26T09:00:00+00:00")],
        "own stop of a line without what it was written over": batch_run.own_stop({"euros": 396.44}),
        "parents before children": run_monitor.ordered(["galley", "flat", "hangar", "cockpit", "ship", ""], WITHIN,
                                                       WITHIN_NAMES),
        "one fault in 3 places": (shared["places"], shared["place"], shared["words"].endswith(
            "stopped in 3 places: no cloud machine could be rented. 1 later step waits on them."), len(shared["raw"]),
            "blender_cloud.py" in shared["raw"][0])}
    assert judged == BATCH_JUDGED

    def derived(run):
        """What a probe reads of a gathered run beyond its own fields, by name."""
        money = run.get("money") or {}
        return {
            "scene states": lambda: {scene["place"]: scene["state"] for scene in run["scenes"]},
            "scene counts": lambda: {scene["place"]: (scene["done"], scene["total"]) for scene in run["scenes"]},
            "by place": lambda: {scene["place"]: scene for scene in run["scenes"]},
            "problem nodes": lambda: sorted(problem["node"] for problem in run["problems"]),
            "gap problems": lambda: [problem for problem in run["problems"] if problem["kind"] == "gaps"],
            "clock": lambda: run_monitor.clock(run),
            "bar": lambda: run_monitor.money_bar({**money, "high": 8.0, "stop": 10.0}),
            "bar over at 340": lambda: run_monitor.money_bar({**money, "try_spent": 340.0})["over"],
            "stop is the high plus 10%": lambda: money["stop"] == round(money["high"] * batch_run.BUFFER, 2),
            "left is the budget less spent and in flight": lambda: money["left"] == round(
                money["budget"] - money["spent"] - money["in_flight"], 2),
            "next total while it runs": lambda: views.next_total(run, 33.0),
            "next total once stopped": lambda: views.next_total({**run, "state": "stopped"}, 33.0),
            "next total over a smaller budget is spent, in flight and the need": lambda: views.next_total(
                {**run, "state": "stopped", "money": {**money, "budget": 10.0}}, 33.0) == round(
                money["spent"] + money["in_flight"] + 33.0, 2),
            "checkout is the newest": lambda: run["checkout"] == Checkout.objects.order_by("at").last().pk,
            "started is the first launch": lambda: run["started"] == batched["began"].isoformat(timespec="seconds")}

    def probed(found, path, test=None):
        """The value at `path` of `found` (a derived name first), put through `test` when one is named."""
        head, _, rest = path.partition(".")
        names = derived(found) if isinstance(found, dict) else {}
        value = picked(names[head](), rest) if head in names else picked(found, path)
        if test is None:
            return value
        how, _, arg = test.partition(" ")
        return {"has": lambda: arg in value, "starts": lambda: value.startswith(arg),
                "re": lambda: bool(re.search(arg, value)), "set": lambda: bool(value),
                "at": lambda: value >= float(arg.split()[-1]),
                "words": lambda: len(prose(value)) <= int(arg.split()[-1])}[how]()

    for log, accepted, want in TRIES:
        run = batch_run.gathered(two_tries(tmp_path, log), tmp_path, tmp_path, **(
            {"accepted_at": {"terrain": "2026-10-24T23:04:00+00:00"}.get} if accepted else {}), **(
            {} if log else {"now": datetime.datetime(2026, 10, 25, 9, 1, tzinfo=datetime.timezone.utc)}))
        assert {path: probed(run, path) for path in want} == want, log

    settings.SCORE_MODE = settings.LOCAL
    for model in (Checkout, Launch, Plan, SyncRequest):
        model.objects.all().delete()
    batch_world = copy_of(built_once[True], tmp_path_factory.mktemp("batch"), monkeypatch)
    props, logs = batch_world.source.props_home, batch_world.source.props_home / "logs"
    batched = {}

    def gathered():
        return batch_run.gathered(newest(), props, batch_world.source.store_root,
                                  lambda node: [{"name": "hatch: no model"}] if node == "plan@alpha" else [],
                                  **({"accepted_at": batched["accepts"].get} if "accepts" in batched else {}))

    def exported():
        building.build(batch_world.source, tmp_path / "batch-export", MADE, 50, SPEND, batch_world.root)
        batched["export"] = ExportedSource(tmp_path / "batch-export")
        hosting.enter_context(pytest.MonkeyPatch.context()).setattr(dashboard_state, "source",
                                                                    lambda: batched["export"])
        hosting.enter_context(override_settings(SCORE_MODE="hosted"))

    def buy_sent():
        SyncRequest.objects.create(kind="checkout", user="joey", payload={})
        SyncRequest.objects.filter(kind="checkout").update(
            created=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1))

    def one_budget():
        hosting.close()
        record = Checkout.objects.get()
        record.stop_line = {**record.stop_line, "euros": 820.0, "batch_from": 80.0, "batch_budget": 740.0,
                            "batch_used": 410.0}
        record.save()

    def relaunched():
        record = Checkout.objects.get()
        Plan.objects.filter(pk=record.launch.plan_id).update(body={**PLAN, "checkout": record.pk})
        rest = {"groups": [{"places": ["alpha", "beta"], "to_run": {}, "blocked": {"assembly@alpha": "waits"},
                            "buys": [{"node": "closeup@alpha"}, {"node": "closeup@beta"}]}], "checkout": record.pk}
        again = Plan.objects.create(basket_hash="checkout-1", made_by="joey", state="ready", body=rest)
        Launch.objects.filter(pk=record.launch.pk).update(plan=again)
        after = (record.at + datetime.timedelta(minutes=5)).isoformat()
        batched["accepts"] = {"terrain": after, "plan@alpha": after, "assembly@beta": after,
                              "assembly@alpha": (record.at - datetime.timedelta(days=1)).isoformat()}

    def first_run_and_parked():
        batched.pop("accepts")
        record = Checkout.objects.get()
        (logs / "score-run-0.log").write_text(
            "[cloud] 12:00:00 pool of 2 gpu-24gb opened for run old-run until 16:00\n"
            "heartbeat 2026-10-24T10:30:00+00:00: rows done 1, running 0, queued 5; this run's rows: "
            "paid runs open 0, EUR 1.18 in the ledger since the run started\n")
        plan = Plan.objects.create(basket_hash="checkout-1", made_by="joey", state="ready",
                                   body={**PLAN, "checkout": record.pk})
        earlier = Launch.objects.create(plan=plan, by="joey", state="stopped", handles=[
            {"command": ["score", "run"], "pid": None, "log": str(logs / "score-run-0.log"), "refused": None}])
        batched["began"] = record.launch.at - datetime.timedelta(minutes=45)
        Launch.objects.filter(pk=earlier.pk).update(at=batched["began"])
        (props / "cloud" / "parked").mkdir(parents=True)
        for number, pool in enumerate(["old-run", RUN, RUN, "someone-else"]):
            (props / "cloud" / "parked" / f"m-{number}.json").write_text(json.dumps({"id": f"m-{number}",
                                                                                   "pool": pool}))
        (props / "cloud" / "pools" / RUN / "closed").write_text("")

    def stopped():
        launch = Checkout.objects.get().launch
        launch.handles[0]["log"] = str(logs / "gone.log")
        launch.save()
        (logs / "gone.log").write_text(LOG.format(run=RUN) + STOPPED)

    def retried():
        for model in (Checkout, Launch, Plan):
            model.objects.all().delete()
        first, retry = a_batch(batch_world), a_batch(batch_world, key="b")
        retry.at = first.at + datetime.timedelta(hours=1)
        retry.save()
        batched["last"] = retry

    def waiting_for_size():
        unstarted = a_batch(batch_world, key="c", log="score run: waiting for size: 16 jobs, 2 cores; registered as "
                            "w1; x\nscore run: stopped by signal 15 while waiting for size\n"
                            "detached: stopped by signal 15\n")
        unstarted.at, unstarted.design_at = batched["last"].at + datetime.timedelta(hours=1), \
            (batched["last"].at + datetime.timedelta(minutes=5)).isoformat()
        unstarted.save()
        batched["last"] = unstarted

    def relaunched_after():
        relaunch = a_batch(batch_world, key="d")
        relaunch.at = batched["last"].at + datetime.timedelta(minutes=20)
        relaunch.save()
        Launch.objects.filter(pk=batched["last"].launch_id).update(state="stopped")  # as polling left it
        made = (relaunch.at - datetime.timedelta(minutes=1)).isoformat()
        every, after = list(Checkout.objects.order_by("at")), Checkout(at=relaunch.at + datetime.timedelta(hours=1))
        batched["watched"] = {"ended once every row was made": watched.batch_ended(every, after, lambda node: made),
                              "ended while a row was never made": watched.batch_ended(every, after, lambda node: None)}

    writes = {
        "ordered": lambda: (batched.update(record=a_batch(batch_world)), Checkout.objects.update(
            state="launching", launch=None, stop_line={})),
        "launch started": lambda: (Checkout.objects.update(launch=batched["record"].launch),
                                   (logs / "score-run-a.log").write_text("paid rows this run would buy: 2\n")),
        "launched": lambda: (Checkout.objects.update(state="launched", stop_line=batched["record"].stop_line),
                             (logs / "score-run-a.log").write_text(LOG.format(run=RUN))),
        "hosted": exported, "buy sent": buy_sent, "one budget": one_budget, "relaunched": relaunched,
        "first run and parked": first_run_and_parked,
        "finished": lambda: (logs / "score-run-a.log").write_text(LOG.format(run=RUN) + FINISHED),
        "stopped": stopped, "ended": lambda: Launch.objects.update(state="failed"), "retried": retried,
        "stopped waiting for size": waiting_for_size, "relaunched after it": relaunched_after}
    from score.dashboard import state as dashboard_state
    with contextlib.ExitStack() as hosting:
        for moment, want in BATCH_MOMENTS:
            writes.get(moment, lambda: None)()
            sources = {"run": lambda: (batched["export"] if "export" in batched and settings.SCORE_MODE == "hosted"
                                       else batch_world.source).batch_run(),
                       "gathered": gathered, "export": lambda: batched["export"].batch_run(),
                       "watched": lambda: batched["watched"]}
            answered = {}
            for source, *probe in want:
                if source not in answered:
                    who, _, page = source.partition(" ")
                    answered[source] = sources[source]() if source in sources else signed_in(
                        "joey" if who == "owner" else who).get(page).content.decode()
            assert {(source, *probe): probed(answered[source], *probe) for source, *probe in want} == want, moment

    # the store's machine, on a fresh copy of the world: the Buy's pin and the kill switch latch with score.conductor's
    # own code; then a stood-in conductor exported and carded, a second machine confirmed and the stops applied; then
    # no conductor at all
    settings.SCORE_MODE = settings.LOCAL
    for model in (Checkout, Launch, Plan, SyncRequest):
        model.objects.all().delete()
    machine_world = copy_of(built_once[True], tmp_path_factory.mktemp("machine"), monkeypatch)
    one_store.path().unlink(missing_ok=True)
    shutil.rmtree(settings.SCORE_HOME / "export", ignore_errors=True)
    import score.conductor as real_conductor
    with pytest.MonkeyPatch.context() as pinned:
        pinned.setattr(client, "head", lambda repo: "a" * 40)
        for record, commit, want in PINS:
            pinned.setattr(real_conductor, "machine", lambda path=None, record=record: record)
            assert client.pin_refusal(Pinned(commit), "/repo") == want, (record, commit)
    with pytest.MonkeyPatch.context() as latched:
        latch_file, free_only = real_conductor.FREE_ONLY_LATCH, real_conductor.FREE_ONLY
        latched.delenv(free_only, raising=False)
        latched.setitem(client.LATCHED, "set", False)
        latch_file.parent.mkdir(parents=True, exist_ok=True)
        latch = {"latch written": lambda: latch_file.write_text(f"{free_only}=1\n"),
                 "latch taken off": latch_file.unlink,
                 "set by whoever started it": lambda: latched.setenv(free_only, "1")}
        try:
            for step, followed, environment in LATCH_STEPS:
                latch[step]()
                assert (client.free_only_followed(), os.environ.get(free_only)) == (followed, environment), step
        finally:
            latch_file.unlink(missing_ok=True)
    for row, found, want in CARDS:
        card = machine.card(found)
        assert all(card[field] is said if isinstance(said, bool) else card[field] == said
                   for field, said in want.items()), (row, card)
    kill = stood_in_conductor(monkeypatch)
    named_machine(machine_world, "conductor")
    exports = tmp_path_factory.mktemp("machine-export")
    manifest = building.build(machine_world.source, exports / "one", MADE, 50, SPEND, machine_world.root)
    found = json.loads((exports / "one/machine.json").read_text())
    assert manifest["machine"] == "conductor" and manifest["written"][:2] == ["state.json", "machine.json"]
    assert found["health"]["bill"]["euros"] == 12.34 and found["tails"]["faults"] == ["one fault"]
    assert sum(len(line) + 1 for lines in found["tails"].values() for line in lines) <= machine.TAIL_BYTES
    assert found["tails"]["run.log"][-1].startswith(f"line {machine.TAIL_LINES - 1} ")  # the newest lines kept
    assert ExportedSource(exports / "one").machine() == found
    small = building.build(machine_world.source, exports / "small", MADE, 0.05, SPEND, machine_world.root)
    assert json.loads((exports / "small/machine.json").read_text())["tails"] == {}
    assert {"what": "the store's machine's log tails", "why": "over the export's cap"} in small["left_out"]
    home = signed_in().get("/").content.decode()
    assert "conductor" in home and "Stop everything" in home and "Allow paid work again" in home  # the latch is set
    shown = signed_in().get("/machine/").content.decode()
    assert "one fault" in shown and "score-sync.timer" in shown
    with pytest.MonkeyPatch.context() as off_pin:
        off_pin.setitem(sys.modules, "score.conductor.health", types.SimpleNamespace(
            read=lambda: {**HEALTH, "free_only": False, "code": OFF_PIN}))
        home = signed_in().get("/").content.decode()
    assert "the cloud machine is on aaaaaaaa, the cockpit on bbbbbbbb; it is being updated" in home
    assert "Allow paid work again" not in home
    settings.SCORE_SYNC_TOKEN, settings.SCORE_MODE = TOKEN, settings.HOSTED
    web = hosted_client()
    pc, store_side = remote_of(web, "pc"), remote_of(web, "conductor")
    committed_by(pc, "pc")
    committed_by(store_side, "conductor")
    assert one_store.record()["name"] == "pc" and one_store.second(THEN) == "conductor"
    change = SyncRequest.objects.create(kind="change", user="joey", payload={"stage": "closeup", "words": "redder"})
    assert store_side.claim(change.pk) is False and "not the store's machine (pc)" in store_side.not_the_store
    change.refresh_from_db()
    assert change.state == "waiting"
    settings.SCORE_MODE = settings.LOCAL  # the store's machine applies them
    for kind, by, payload, agent, on_conductor, words in REFUSED:
        with pytest.MonkeyPatch.context() as where:
            where.setattr(actions, "agent_started", lambda agent=agent: agent)
            if not on_conductor:
                off_a_conductor(where)
            applied = applying.apply({"kind": kind, "user": by, "payload": payload}, machine_world.source)
        assert applied.state == "refused" and words in applied.detail, (kind, by, applied.detail)
    assert kill.calls == [] and one_store.record()["name"] == "pc"
    settings.SCORE_MODE = settings.HOSTED
    askers = {"the sync token alone": web, "joey": api(), "mallory": api("mallory")}
    for who, path, body, status in ASKS:
        headers = {"Authorization": f"Bearer {TOKEN}"} if who == "the sync token alone" else {}
        assert askers[who].post(f"/api/machine/{path}", json=body, headers=headers).status_code == status, (who, path)
    assert one_store.record()["name"] == "pc" and list(SyncRequest.objects.values_list("pk", flat=True)) == [change.pk]
    owner = askers["joey"]
    answer = owner.post("/api/machine/confirm", json={"machine": "conductor", "sure": True})
    assert answer.status_code == 200 and one_store.record()["by"] == "joey" and one_store.second(THEN) is None
    assert pc.claim(change.pk) is False and store_side.claim(change.pk) is True and store_side.not_the_store is None
    for path, body, _, _ in STOPS:
        assert owner.post(f"/api/machine/{path}", json=body).json()["said"].startswith("queued"), path
    assert kill.calls == []  # hosted, nothing is done but queue
    settings.SCORE_MODE = settings.LOCAL
    remote = remote_of(hosted_client(), "conductor")
    for _, _, kind, call in STOPS:
        stop = SyncRequest.objects.get(kind=kind)
        item = {"id": stop.pk, "kind": stop.kind, "user": stop.user, "payload": stop.payload}
        assert client.answered(remote, item, machine_world.source).state == "done" and kill.calls[-1] == call, kind
        assert client.answered(remote, item, machine_world.source) is None, kind  # claimed once: never applied again
    assert len(kill.calls) == 3
    from score.dashboard.pages import machine as machine_page
    assert machine_page.report_counts(SyncRequest.objects.get(kind="stop-batch").detail) == [("parked", 1),
                                                                                              ("runs", 1)]
    one_store.kept({"name": "pc", "others": {"naive": "2026-10-18T13:00:00", "broken": "not a time"}})
    assert one_store.second(THEN) == "naive"  # a time of no zone or none breaks no page
    off_a_conductor(monkeypatch)
    building.build(machine_world.source, exports / "off", MADE, 50, SPEND, machine_world.root)
    found = json.loads((exports / "off/machine.json").read_text())
    assert found["health"] == {"missing": machine.NOT_ON_CONDUCTOR} and found["tails"] == {}
    assert found["machine"]["name"]
    card = machine.card(found, MADE)
    assert card["missing"] == machine.NOT_ON_CONDUCTOR and card["state"] is None and card["export_late"]
    one_store.path().unlink(missing_ok=True)
    shutil.rmtree(settings.SCORE_HOME / "export", ignore_errors=True)

    # the concept review, on a fresh drafting copy (alpha drawn the day before, beta not, nothing locked) with the queue
    # emptied: refused, drawn all, drawn, discussed, redrawn by his marks and his wording, held, locked; then a second
    # fresh copy drawn hosted and answered by the listener
    from score.dashboard.pages import concepts as concept_pages
    from score.review import concepts as drawing
    from score.review import web as review_web
    for model in (Checkout, Launch, Plan, SyncRequest):
        model.objects.all().delete()
    drafts = [copy_of(built_once[False], tmp_path_factory.mktemp("drafting"), monkeypatch)]
    asked = stood_in(monkeypatch, lambda: drafts[-1])
    drafting = drafts[-1]
    answered_in_process(monkeypatch, drafting)
    store, owner, mallory = drafting.source.store, signed_in(), signed_in("mallory")

    def sent(poster, page, body):
        return poster.post(page, json.dumps(body), content_type="application/json")

    def offered():
        return concept_pages.draw_all(concept_pages.light_world(drafting.source))

    def beta_newest():
        return owner.get("/concept/beta/state/").json()["newest"]

    places = offered()["places"]
    assert places == ["alpha", "beta"] and "Draw all 2, EUR 0.30" in owner.get("/places/").content.decode()
    refused = [(owner, "/concepts/draw-all/", {"places": places, "euros": 0.15}, 409),  # the total moved
               (owner, "/concepts/draw-all/", {"places": ["alpha"], "euros": 0.30}, 409),  # the places moved
               (mallory, "/concepts/draw-all/", {"places": places, "euros": 0.30}, 403),
               (mallory, "/concept/beta/draw/", {"euros": PRICE}, 403),
               (mallory, "/concept/beta/pick/", {"sha": None}, 403)]
    assert [(page, sent(poster, page, body).status_code) for poster, page, body, _ in refused] == [
        (page, code) for _, page, _, code in refused]
    assert SyncRequest.objects.count() == 0
    drawn(owner, "beta", euros=0.05)
    assert "measured price" in owner.get("/concept/beta/state/").json()["refused"]
    assert made_draws(store, "beta") == []
    with monkeypatch.context() as patched:
        patched.setattr(concept_pages, "approved", lambda source, place: True)
        answer = sent(owner, "/concept/beta/pick/", {"sha": None})
    assert answer.status_code == 409 and "approved" in answer.json()["detail"]  # an approved design stays locked

    assert sent(owner, "/concepts/draw-all/", {"places": places, "euros": 0.30}).status_code == 200
    for place in places:
        found = made_draws(store, place)
        assert len(found) == 1 and found[0]["base"] is None and found[0]["euros"] == PRICE, place
        assert "Draw all, 2 first draws for EUR 0.30" in store.spend_yes("override", found[0]["yes"])["purpose"], place
    assert offered() is None
    waits = drawing.waits
    with monkeypatch.context() as patched:
        patched.setattr(drawing, "waits", lambda held, place: "waits for yard's concept to be locked"
                        if place == "alpha" else waits(held, place))
        assert offered() is None  # alpha waits, beta drawn
    with pytest.raises(review_web.review.Refused, match="changed"):  # on the store's machine, drawn since the click
        review_web.concept_draw(store, "beta", {}, PRICE, by="joey", first=True)
    assert len(made_draws(store, "beta")) == 1

    assert drawn(owner, "beta", euros=PRICE).status_code == 200
    state = owner.get("/concept/beta/state/").json()
    assert state["pending"] is False and state["refused"] is None and state["newest"]
    drawn(owner, "beta", marks=[], note="", base=None, euros=PRICE)
    beta_draws = made_draws(store, "beta")
    first, fresh = beta_draws[-2:]
    assert len(beta_draws) == 3
    yes = store.spend_yes("override", first["yes"])
    assert yes["by"] == "joey" and yes["euros"] == PRICE and "beta" in yes["purpose"]
    assert fresh["base"] is None and fresh["marks"] == [] and fresh["sha"] != first["sha"]
    assert asked[-1] == asked[-2] and "Box" not in asked[-1]
    assert fresh["yes"] != first["yes"] and fresh["euros"] == PRICE
    assert (store.cache.parent / "bucket" / f"concept-draws/{fresh['sha']}.png").is_file()

    base = beta_newest()

    def discussed(question, euros):
        return sent(owner, "/concept/beta/discuss/", {"base": base, "question": question, "euros": euros})

    assert discussed("is the door too small?", DISCUSS_PRICE).status_code == 200
    thread = owner.get(f"/concept/beta/state/?draw={base}").json()["thread"]
    assert thread[0]["answer"] == "Paint the door red." and not thread[0]["closed"]
    discussed("?", 0.03)
    assert "not today" in owner.get("/concept/beta/state/").json()["discuss_refused"]
    drawn(owner, "beta", base=base, euros=REDRAW_PRICE)
    assert "Creator: is the door too small?\nYou: Paint the door red." in asked[-2]
    assert owner.get(f"/concept/beta/state/?draw={base}").json()["thread"][0]["closed"] is True
    assert drafting.source.world_state().discuss_spend == 0.0271

    marks = [{"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "note": "a window"}]
    drawn(owner, "beta", marks=marks, base=beta_newest(), euros=REDRAW_PRICE)
    assert "Box 1 (top left): a window." in asked[-2]  # the prompt model corrects the prompt by it
    assert asked[-1].startswith("The corrected prompt.")
    assert drawing.own_wording(store, "beta") == "The corrected prompt."
    generated = escape(drawing.generated(store, "beta"))
    edited = "One concept painting of beta at dusk, its doors open."
    drawn(owner, "beta", marks=[], note="", base=None, euros=PRICE, wording=edited)
    assert asked[-1] == edited and drawing.own_wording(store, "beta") == edited
    assert f">{edited}</textarea>" in owner.get("/concept/beta/").content.decode()
    assert mallory.post("/concept/beta/generated/").status_code == 403
    assert owner.post("/concept/beta/generated/").json()["said"] == "back to the generated wording"
    assert f">{generated}</textarea>" in owner.get("/concept/beta/").content.decode()

    with monkeypatch.context() as patched:
        patched.setattr(drawing, "step_refusal", lambda held, place, step: "waits for yard's plan to be made")
        page = owner.get("/concept/beta/").content.decode()
        pick = page[page.index('id="concept-pick"'):].split(">", 1)[0]
        assert " disabled" in pick and "waits for yard&#x27;s plan to be made" in pick
        answer = sent(owner, "/concept/beta/pick/", {"sha": made_draws(store, "beta")[-1]["sha"]})
        assert answer.status_code == 409 and "plan to be made" in answer.json()["detail"]
    assert drawing.picked(store, "beta") is None
    assert sent(owner, "/concept/beta/pick/", {"sha": beta_newest()}).json()
    assert 'ptile-review" href="/concept/beta/"' not in owner.get("/places/").content.decode()
    assert drawn(owner, "beta", euros=PRICE).status_code == 409  # locked
    sent(owner, "/concept/beta/pick/", {"sha": None})
    assert 'href="/concept/beta/"' in owner.get("/places/").content.decode()
    assert owner.get("/concept/nowhere/").status_code == 404

    base = beta_newest()
    settings.SCORE_MODE = settings.HOSTED
    discussed("why?", DISCUSS_PRICE)
    assert owner.get("/concept/beta/state/").json()["discussing"] is True
    settings.SCORE_MODE = settings.LOCAL
    with override_settings(SCORE_SYNC_TOKEN=TOKEN):
        item = SyncRequest.objects.filter(kind=concept_pages.DISCUSS).order_by("-pk").first()
        assert listen.round_once(remote_of(hosted_client()), drafting.source) == [(item.pk, "done")]
    assert concept_pages.thread_of(drafting.source.world_state(), "beta", base)[0]["question"] == "why?"
    settings.SCORE_MODE = settings.HOSTED
    drawn(owner, "beta", euros=PRICE, wording="beta, my words")
    assert ">beta, my words</textarea>" in owner.get("/concept/beta/").content.decode()  # before the export
    owner.post("/concept/beta/generated/")
    assert ">beta, my words</textarea>" not in owner.get("/concept/beta/").content.decode()
    settings.SCORE_MODE = settings.LOCAL

    (drafting.data / "places/within.json").write_text(json.dumps({
        "shells": {"yard": {"name": "Yard"}}, "within": {"alpha": {"within": "beta"}, "beta": {"within": "yard"}}}))
    page = owner.get("/concept/yard/").content.decode()
    assert "data-v>Beta</b>" in page and "data-v>Alpha</b>" not in page
    assert "data-v>Alpha</b>" in owner.get("/concept/beta/").content.decode()
    trail = owner.get("/concept/alpha/").content.decode().split('class="trail"')[1].split("</nav>")[0]
    assert trail.index('href="/concept/yard/"') < trail.index('href="/concept/beta/"') < trail.index("Alpha")
    (drafting.data / "places/within.json").write_text(json.dumps({
        "shells": {}, "within": {}, "parts": {"alpha": {"of": "beta", "as": "its far view"}}}))
    html = owner.get("/").content.decode()
    assert 'href="/concept/alpha/"' not in html and 'href="/place/alpha/"' not in html  # a part of another place

    class Down:  # a hosted side that cannot be reached
        def waiting(self, kinds, wait, skip=()):
            raise urllib.error.URLError("refused")

    class Old:  # a hosted side that answers at once, not holding the call
        not_the_store = None

        def waiting(self, kinds, wait, skip=()):
            return []
    for side, rounds, pauses, says in ((Down(), 2, [listen.RETRY_SECONDS] * 2, "did not answer"),
                                       (Old(), 3, [listen.SHORTEST_ROUND] * 3, None)):
        said, paused = [], []
        listen.listen(side, drafting.source, rounds=rounds, log=said.append, pause=paused.append)
        assert paused == pauses and (says is None or len(said) == rounds and says in said[0]), type(side).__name__

    for model in (SyncRequest,):
        model.objects.all().delete()
    shutil.rmtree(settings.SCORE_HOME / "request-files", ignore_errors=True)
    drafts.append(copy_of(built_once[False], tmp_path_factory.mktemp("drafting-hosted"), monkeypatch))
    drafting = drafts[-1]
    store = drafting.source.store
    settings.SCORE_MODE = settings.HOSTED
    sent(owner, "/concepts/draw-all/", {"places": offered()["places"], "euros": 0.30})
    assert offered() is None  # on their way: not offered twice
    settings.SCORE_MODE = settings.LOCAL
    html = owner.get("/places/").content.decode()
    assert "Drawing 2..." in html and html.count('class="draw-busy"') == 2
    SyncRequest.objects.filter(payload__place="beta").update(state="refused", detail="refused: the price moved")
    with override_settings(SCORE_SYNC_TOKEN=TOKEN):
        answered = listen.round_once(remote_of(hosted_client()), drafting.source)
    assert [state for _, state in answered] == ["done"] and len(made_draws(store, "alpha")) == 1
    html = owner.get("/places/").content.decode()
    assert "draw-busy" not in html and 'class="draw-refused" title="refused: the price moved"' in html
    settings.SCORE_MODE = settings.HOSTED
    drawn(owner, "beta", euros=PRICE)
    assert owner.get("/concept/beta/state/").json()["pending"] is True
    settings.SCORE_MODE = settings.LOCAL
    item = SyncRequest.objects.filter(kind=concept_pages.DRAW).order_by("-pk").first()
    with override_settings(SCORE_SYNC_TOKEN=TOKEN):
        web = hosted_client()
        remote = remote_of(web)
        assert web.post(f"/api/sync/requests/{item.pk}/claim",
                        headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200
        SyncRequest.objects.filter(pk=item.pk).update(state="waiting")  # a second caller is refused only once claimed
        assert listen.round_once(remote, drafting.source) == [(item.pk, "done")]
        assert remote.waiting(listen.LISTENED, 0) == [] and not remote.claim(item.pk)  # held once, claimed once
    record = json.loads(SyncRequest.objects.get(pk=item.pk).detail)
    landed = {json.loads(done.detail)["sha"] for done in SyncRequest.objects.filter(kind=concept_pages.DRAW,
                                                                                     state="done")}
    assert record["sha"] in landed and len(landed) == 2
    assert sorted(path.name for path in (settings.SCORE_HOME / "request-files").iterdir()) == sorted(
        f"{sha}-{size}.jpg" for sha in landed for size in (1280, 360))
    shown = concept_pages.answered_draws("beta")
    assert [draw.picture.sha for draw in shown] == [record["sha"]] and shown[0].picture.thumb_url

    # the environment, on a fresh world copy (its concept locked) with the queue emptied, walked once: the locked
    # concept page says each body from the physics and asks the store's questions; the plan page puts the base where
    # the setting does, keeps his scene time and works the sky out of the setting; unlocked only when he is sure; a
    # reference sent to the bucket; saved, asked at the price shown, taken and locked; anyone else refused (ACCESS);
    # then saved hosted, shown at once and applied by the listener. The setting's picture is judged on its own rows.
    from score.dashboard.pages import environment as environment_pages
    from score.dashboard.pages import setting_picture
    from score.review import environment_concept, environment_plan, overhead, reading, setting
    house = setting.checked(HOUSE)
    light = house["lights"][0]
    for when in SUN_MOMENTS:
        found = setting_picture.view_of(house, {"house": when}, {"house": "House"})
        assert len(found["pictures"]) == 1 and 'class="sp-body"' not in found["pictures"][0]["svg"], when  # no body
        assert [(card["name"], card["kind"], card["sites"]) for card in found["cards"]] == HOUSE_CARDS, when
        seen_now = overhead.far_light(light, when)
        since = overhead.day_of(when) - overhead.day_of(light["equinox"])
        assert setting_picture.far_way(light, since) == pytest.approx((seen_now["azimuth"], seen_now["altitude"]),
                                                                      abs=0.01), when

    SyncRequest.objects.all().delete()
    shaped = copy_of(built_once[True], tmp_path_factory.mktemp("environment"), monkeypatch)
    concept_asked = environment_asked(monkeypatch, shaped)
    store, owner = shaped.source.store, signed_in()
    name = shaped.source.world_state().world
    html = owner.get(ENVIRONMENT).content.decode()
    assert ">locked</b>" in html and "Unlock" in html
    assert "data-f=" not in html  # owner 2026-10-21: fields only unlocked
    assert "orbits Earth every 27 days, one face to Earth; gravity 1.6 m/s²" in html  # the reference table's Moon
    assert "orbits Sun every 687 days, a day of 25 h; gravity 3.7 m/s²" in html  # and Mars
    assert [(question_name, question) for question_name, _, question in environment_pages.QUESTIONS] == list(
        environment_concept.QUESTIONS)
    assert [environment_pages.steps_around(question_name)["number"]
            for question_name, _, _ in environment_pages.QUESTIONS] == [1, 2, 3, 4, 5]

    html = owner.get(f"/environments/{name}/plan/").content.decode()
    assert 'data-place="base"' in html and "55.0000° N, 0.0000° E" in html  # where the setting puts it
    plan = {"maps": [{"on": "moon", "sites": [{"place": "base", "time": "2099-06-01T12:00:00Z"}]}]}
    assert owner.post(f"/environments/{name}/plan/keep/", json.dumps({"plan": plan}),
                      content_type="application/json").status_code == 200
    assert environment_plan.current(store, name)["how"] == "edited"
    base = environment_plan.site_of(store, "base", name)
    assert base["time"] == "2099-06-01T12:00:00Z" and base["overhead"]["bodies"]
    shaped.source.refresh()
    html = owner.get(f"/environments/{name}/plan/").content.decode()
    assert ">Sky<" not in html and "Overhead, from the physics: Sun" in html  # no fixed sky
    with monkeypatch.context() as patched:  # a daylight concept's night time moves to sun up and says so
        patched.setattr(reading, "concept_light", lambda held, place: {"rows": {}, "scene": {
            "daylight": True, "unseen": False, "unseen_colour": ""}} if place == "base" else None)
        night = {"maps": [{"on": "moon", "sites": [{"place": "base", "time": "2099-06-16T12:00:00Z"}]}]}
        owner.post(f"/environments/{name}/plan/keep/", json.dumps({"plan": night}), content_type="application/json")
        base = environment_plan.site_of(store, "base", name)
    assert base["written_time"] == "2099-06-16T12:00:00Z" and base["time"] != base["written_time"]

    assert posted(owner, "save", {"locked": False}).status_code == 409  # not sure
    assert not environment_concept.unlocked(store)
    assert posted(owner, "save", {"sure": True, "locked": False}).status_code == 200
    assert environment_concept.unlocked(store)
    assert drawing.waits(store, "alpha") == "waits for the environment concept to be locked"
    answer = posted(owner, "reference", {"name": "dock.png", "data": base64.b64encode(a_png()).decode(),
                                         "shows": "the dock's look", "place": "beta"})
    assert answer.status_code == 200, answer.content
    bucket = runtime_store.FolderStore(store.cache.parent / "bucket")
    assert "dock.png" in json.loads(bucket.read_bytes("references/index.json"))  # the bucket, never the repository
    shaped.source.refresh()
    html = owner.get(ENVIRONMENT).content.decode()
    assert "Send, EUR 0.05" in html and "Question 1 of 5" in html
    assert 'data-picture="{home}/references/dock.png"' in html
    assert SyncRequest.objects.get(kind="environment-reference").payload["data"] == ""  # its bytes dropped once read
    assert drawing.references_of(store, "beta") == []  # unlocked: the draws read nothing new yet

    concept = environment_concept.newest(store, "world1")["concept"]
    assert posted(owner, "save", {"concept": {**concept, "style": "Cold steel"}, "locked": False}).status_code == 200
    assert environment_concept.newest(store, "world1")["concept"]["style"] == "Cold steel"
    posted(owner, "ask", {"topic": "style", "answer": "brighter", "euros": 0.04})
    cheap = SyncRequest.objects.get(kind="environment-ask")
    assert cheap.state == "refused" and "measured price" in cheap.detail and concept_asked == []
    cheap.delete()
    answer = posted(owner, "ask", {"topic": "style", "answer": "brighter", "euros": ASK_PRICE})
    assert answer.status_code == 200 and "brighter" in concept_asked[0] and "Cold steel" in concept_asked[0]
    item = SyncRequest.objects.get(kind="environment-ask")
    assert item.state == "done" and json.loads(item.detail)["proposed"] == {"style": "Bright frontier"}
    assert posted(owner, "take", {"ask": item.pk}).status_code == 200
    assert environment_concept.newest(store, "world1")["concept"]["style"] == "Bright frontier"
    assert posted(owner, "save", {"concept": concept, "locked": True}).status_code == 200
    assert environment_concept.in_force(store)["style"] == concept["style"]
    access = (  # (who, path, body or None for a GET, code), on the locked concept
        ("owner", f"{ENVIRONMENT}ask/", {"topic": "style", "answer": "x", "euros": ASK_PRICE}, 409),  # locked
        ("eve", f"{ENVIRONMENT}ask/", {"topic": "style", "answer": "x", "euros": ASK_PRICE}, 403),
        ("mallory", f"{ENVIRONMENT}save/", {"sure": True, "locked": False}, 403),
        ("joey2", f"/environments/{name}/plan/keep/", {"plan": plan}, 403),
        ("ann", "/environments/world9/", None, 404))
    for who, path, body, code in access:
        asker = owner if who == "owner" else signed_in(who)
        said = asker.get(path) if body is None else asker.post(path, json.dumps(body),
                                                                content_type="application/json")
        assert said.status_code == code, (who, path)
    assert environment_concept.in_force(store)["style"] == concept["style"]

    SyncRequest.objects.all().delete()
    settings.SCORE_MODE = settings.HOSTED
    assert posted(owner, "save", {"sure": True, "locked": False}).status_code == 200
    assert ">unlocked</b>" in owner.get(ENVIRONMENT).content.decode()  # shown at once, before the export
    assert posted(owner, "ask", {"topic": "style", "answer": "x", "euros": ASK_PRICE}).status_code == 409
    settings.SCORE_MODE = settings.LOCAL
    with override_settings(SCORE_SYNC_TOKEN=TOKEN):
        assert listen.round_once(remote_of(hosted_client()), shaped.source) == [(SyncRequest.objects.get().pk, "done")]
    assert environment_concept.unlocked(store)
    SyncRequest.objects.all().delete()
    with monkeypatch.context() as patched:  # an export made before the environment concept takes no click
        patched.setattr(environment_pages, "shown", lambda world_state: {})
        assert posted(owner, "save", {"sure": True, "locked": False}).status_code == 409
    assert SyncRequest.objects.count() == 0

    # the basket, on a fresh world copy with a made basket in a fresh home and the queue emptied: each item says what
    # changes and a guess is never a price; the viewer outlines each side's changes; only the owner chooses, on the
    # version he saw; hosted, his answer and his checkout are queued and the store's machine applies only the owner's;
    # then his answers kept where agents read them, his own words or the recommended one
    from score.dashboard.pages import basket as basket_page
    for model in (BasketAnswer, BasketChoice, Checkout, Launch, Plan, SyncRequest):
        model.objects.all().delete()
    basket_world = copy_of(built_once[True], tmp_path_factory.mktemp("basket"), monkeypatch)
    settings.SCORE_HOME = tmp_path_factory.mktemp("basket-home") / "home"
    basket = a_basket(settings.SCORE_HOME / "proposals")
    owner, visitor = signed_in(), signed_in("visitor")
    page = owner.get("/basket/").content.decode()  # counted from CHANGES; the measured price 2.00 to 3.00
    assert "2 objects added · 1 object taken out · 1 object refinished" in page and "at most 3.00" in page
    guessed = visitor.get("/basket/item/environment-people-body/").content.decode()
    assert "EUR 2.70, which is not a price" in guessed and "Only the owner buys" in guessed
    assert signed_in("other").get("/basket/item/nothing-here/").status_code == 404
    copy = basket_world.source.web_copies / "alpha"
    copy.mkdir(parents=True, exist_ok=True)
    (copy / "alpha.json").write_text(json.dumps({"made_at": "2026-10-19T08:00:00Z", "objects": []}))
    for who, query, base, marks in (  # (who, the viewer's query, its base, the kinds it outlines on that side)
            ("joey", "item=alpha-pieces&embed=1", "/basket-file/alpha/web3d/", ["added", "added", "lamp",
                                                                                "refinished"]),
            ("other", "item=alpha-pieces&side=before", "/web/alpha/", ["lamp", "refinished", "removed"])):
        shown = view_data(signed_in(who).get(f"/view/alpha?{query}").content.decode())
        assert (shown["base"], sorted(mark["kind"] for mark in shown["marks"])) == (base, marks), query
    item = records.item(basket, "alpha-pieces")
    form = {"item": "alpha-pieces", "version": item["version"], "choice": "buy"}
    assert visitor.post("/basket/choose/", form).status_code == 403 and not BasketChoice.objects.exists()
    owner.post("/basket/choose/", {**form, "version": "0" * 16})  # a choice on another version is not kept
    assert not BasketChoice.objects.exists()
    owner.post("/basket/choose/", form)
    assert BasketChoice.objects.get(item="alpha-pieces").choice == "buy"
    settings.SCORE_MODE = settings.HOSTED
    (settings.SCORE_HOME / "export" / "current").mkdir(parents=True)
    (settings.SCORE_HOME / "export" / "current" / "proposals").symlink_to(basket)
    recommended = {"item": "ship-room-concepts", "number": "1", "take": "recommended"}
    owner.post("/basket/answer/", recommended)
    queued = SyncRequest.objects.get(kind="answer")
    assert records.answers(basket) == {}  # kept only once the store's machine applies it
    owner.post("/basket/choose/", form)
    owner.post("/basket/checkout/", {"key": "a" * 32, "confirm": "yes"})
    assert SyncRequest.objects.get(kind="checkout").payload == {
        "key": "a" * 32, "items": [{"id": "alpha-pieces", "version": item["version"]}]}
    assert "waits for the store's machine" in basket_page.last_checkout()
    settings.SCORE_MODE = settings.LOCAL
    BasketAnswer.objects.all().delete()
    assert applying.apply({"kind": "answer", "user": "mallory", "payload": queued.payload}, None).state == "refused"
    assert records.answers(basket) == {}  # only the owner's answer is applied
    done = applying.apply({"kind": "answer", "user": "joey", "payload": queued.payload}, None)
    assert done.state == "done" and records.answers(basket)["ship-room-concepts"]["1"]["by"] == "joey"
    owner.post("/basket/answer/", {**recommended, "take": "own", "answer": "Two decks where they fit."})
    assert records.answers(basket)["ship-room-concepts"]["1"]["answer"] == "Two decks where they fit."
    owner.post("/basket/answer/", recommended)
    assert records.answers(basket)["ship-room-concepts"]["1"]["answer"] == "One deck, as in your cutaway picture."
    assert visitor.post("/basket/answer/", recommended).status_code == 403

    # A place's design, on a fresh drafting copy (alpha drawn, nothing locked), walked once from its draw to its plan
    # (owner, 2026-10-20 and 2026-10-21: "inventory can't exist" before the lock): while drawing no numbers and no plan,
    # its card opening its concept; locked and read, its reading boxed on the concept page and its euros in the totals,
    # its plan next; its plan only once the inventory counts, no Approve, anyone else's Keep refused; the inside places
    # he names laid in it; a draw on a moved room out of date and a merged scene no card, hosted too; his Make plan at
    # the price shown, the plan written with its gaps said plainly; his Keep (an edit replaces the plan Make plan
    # offers to write, so it comes last) gives the places he named a card and a concept page each and is kept as he
    # edited it where the plan stage reads it; designed, numbers, and findings older than the lock a check; then
    # another lock or an unlock: nothing counts.
    from score.dashboard import state as served_state
    from score.review import concepts as drawing
    from score.review import plan_drawing, plan_writing, plans, reading
    design = copy_of(built_once[False], tmp_path_factory.mktemp("design"), monkeypatch)
    store, owner = design.store, signed_in()
    kept_in = tmp_path_factory.mktemp("plans")
    monkeypatch.setattr(plans, "DATA", design.data)
    monkeypatch.setattr(plans, "KEPT", kept_in / "kept")
    monkeypatch.setattr(plans, "KEPT_INVENTORY", kept_in / "kept-inventory")
    monkeypatch.setattr(plans, "KEPT_CONCEPT", kept_in / "kept-concepts")

    def alpha_now():
        design.source.refresh()
        return next(place for place in screens.environment(design.source, MONTH)["places"] if place["place"] == "alpha")

    def kept_plan(poster, plan):
        return poster.post("/plan/alpha/keep/", json.dumps({"plan": plan}), content_type="application/json")
    assert (alpha_now()["design"], alpha_now()["progress"], alpha_now()["gaps"]) == ("draw", None, None)
    html = owner.get("/places/").content.decode()
    assert "data-v>0/3</b>" in html and 'class="ring' not in html
    assert 'href="/place/alpha/"' not in html and 'class="ptile" href="/concept/alpha/"' in html
    assert signed_in("joey2").get("/place/alpha/").status_code == 404
    assert "concept-inventory" not in owner.get("/concept/alpha/").content.decode()  # not locked: no reading
    html = owner.get("/plan/alpha/", follow=True).content.decode()
    assert "after the inventory" in html and "plan-drawing" not in html  # no plan before the inventory counts
    # locked and read: a box of [0, 0, 48, 30] px on its 96 x 60 picture is 50% by 50%
    alpha = fixture.concept_of(store, "alpha")
    drawing.pick(store, "alpha", alpha, "joey")
    drum = {"id": "drum", "name": "fuel drum", "noun": "drum", "kind": "generate", "terrain": False, "count": 2,
            "size_words": "waist", "anchor": "ground", "where": "left", "boxes": [[0, 0, 48, 30]], "box": [0, 0, 48, 30]}
    reading.kept(store, {"place": "alpha", "concept": alpha, "at": "2026-10-21T08:00:00+00:00", "by": "joey",
                         "method": reading.METHOD, "size": [96, 60], "inventory": {"rows": [drum]},
                         "gaps": [{"kind": "size", "row": "drum", "words": "its size in metres not read"}],
                         "skipped": [{"name": "crate", "row": None, "why": reading.ONLY_SAM, "box": [48, 30, 96, 60]}],
                         "merged": [{"name": "blue drum", "row": "blue", "into": "drum"}],
                         "euros": {"rows": 0.03, "boxes": 0.1, "total": 0.13},
                         "seconds": {"rows": 20.0, "boxes": 30.0, "card": 550.0}})
    design.source.refresh()
    page = owner.get("/concept/alpha/").content.decode()
    assert "data-v>fuel drum</span>" in page and "&times;2" in page and "1 rows, 1 gaps, EUR 0.13, 10.0 min" in page
    assert 'style="left:0.0%;top:0.0%;width:50.0%;height:50.0%"' in page
    assert 'class="concept-box skipped"' in page and 'style="left:50.0%;top:50.0%' in page
    assert "skipped 1, merged 1</button>" in page
    assert "inventories EUR</small> 0.13" in signed_in("joey2").get("/places/").content.decode()
    assert screens.design_state(design.source.world_state(), "alpha") == "plan"  # read: its plan is next
    # read again by today's method (its lamp row gives no size): the plan; anyone else's Keep refused; the inside
    # places he names, their spaces made `_`, laid in it
    fixture.an_inventory_read(store, design.data, "alpha", alpha)
    design.source.refresh()
    html = owner.get("/plan/alpha/", follow=True).content.decode()
    assert 'id="plan-drawing"' in html and "Approve" not in html
    assert "data-v>R1 1: no size</span>" in html  # its row gives no size: a gap shown, never hidden
    plan = plan_data(html)
    plan["items"][0][1] = 2.5
    assert kept_plan(signed_in("joey2"), plan).status_code == 403 and plans.current(store, "alpha")["how"] != "edited"
    assert owner.post("/plan/alpha/named/", json.dumps({"names": ["Back Room", "loft"]}),
                      content_type="application/json").status_code == 200
    assert plans.named(store, "alpha") == ["back_room", "loft"]
    holding = plans.current(store, "alpha")["plan"]
    assert [hold["place"] for hold in holding["holds"]] == ["back_room", "loft"]
    # beta drawn on a room inside alpha, the room since moved: out of date, no card picture; then merged: no card
    within = design.data / "places/within.json"
    within_before = within.read_text() if within.exists() else None
    within.write_text(json.dumps({"shells": {}, "within": {"beta": {"within": "alpha"}}}))
    a_draw(design, "beta", {"place": "beta", "x": 90.0, "y": 90.0, "w": 1.0, "d": 1.0})
    assert plans.room_of(store, "beta") is not None
    html, shown = hosted_page(design, tmp_path_factory.mktemp("moved"), monkeypatch, settings, "/places/?in=alpha")
    assert shown.plan_changed == ["beta"] and "beta" not in shown.concepts
    tile = html[html.index('href="/concept/beta/"'):].split('<div class="ptile-box">')[0]
    assert "plan changed" in tile and "<img" not in tile and "Review" not in tile
    within.write_text(json.dumps({"shells": {}, "within": {}, "merged": {"beta": {"into": "alpha"}}}))
    settings.SCORE_MODE = settings.LOCAL
    html, shown = hosted_page(design, tmp_path_factory.mktemp("merged"), monkeypatch, settings, "/places/")
    assert shown.removed == ["beta"] and 'href="/concept/beta/"' not in html and "beta" not in shown.concept_undrawn
    settings.SCORE_MODE = settings.LOCAL
    if within_before is None:
        within.unlink()
    else:
        within.write_text(within_before)
    monkeypatch.setattr(served_state, "source", lambda: design.source)
    # read again, its lamp row across the room (6 x 0.4 m at 100 units a metre) cutting the north spot off its door:
    # Make plan is his yes at the price shown and writes the plan with that gap said plainly
    fixture.an_inventory_read(store, design.data, "alpha", alpha, size=[6.0, 0.4, 0.8])
    design.source.refresh()
    written_plan = {"outline": [[0, 0], [600, 0], [600, 400], [0, 400]],
                    "items": [{"row": "r1", "box_2d": [180, 0, 220, 600], "tall": 0.8}],
                    "people": [[100, 100], [500, 350]],
                    "openings": [{"kind": "door", "at": [300, 400], "wide": 90, "angle": 0, "swing": "left",
                                  "sill": 0.0, "head": 2.1, "to": "outside"}]}
    write_asked = []

    def written(store, place, euros, by):
        write_asked.append(euros)
        finished = {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(written_plan)}]}}
        record, = plan_writing.write(store, [place], by, ask=lambda body: ({"candidates": [finished],
                                                                            "usageMetadata": {}}, 1.0))
        return json.loads(plan_writing.said(record))
    monkeypatch.setattr(review_web, "plan_write", written)
    monkeypatch.setattr(plan_writing, "call_euros", lambda found: 0.04)
    monkeypatch.setattr(plan_drawing, "called", lambda wording, pictures, frame: (drawing_png(), 0.13, 1.0))
    monkeypatch.setattr(plan_writing, "cleared", lambda *found, **named: contextlib.nullcontext())
    monkeypatch.setattr("score.adapters.compute.require_cleared", lambda what, store=None: None)
    price = plan_writing.price(store)
    assert f"EUR {price:.2f}" in owner.get("/plan/alpha/", follow=True).content.decode()
    sent_plan = owner.post("/plan/alpha/write/", json.dumps({"euros": price}), content_type="application/json")
    assert sent_plan.status_code == 200, sent_plan.content
    assert write_asked == [price] and plans.current(store, "alpha")["how"] == "written"
    design.source.refresh()
    html = owner.get("/plan/alpha/", follow=True).content.decode()
    assert 'id="plan-write"' not in html and "the standing spot (north-west) cannot be reached on foot" in html
    # his Keep: the places he named a card and a concept page each, a name he never gave none; his edit kept as edited
    assert kept_plan(owner, plans.current(store, "alpha")["plan"]).status_code == 200
    design.source.refresh()
    assert 'href="/concept/loft/"' in signed_in("joey2").get("/places/?in=alpha").content.decode()
    assert owner.get("/concept/loft/").status_code == 200 and owner.get("/concept/attic/").status_code == 404
    answer = kept_plan(owner, plan)
    assert answer.status_code == 200, answer.content
    assert plans.current(store, "alpha")["how"] == "edited"
    assert json.loads((plans.KEPT / "alpha.json").read_text())["items"][0][1] == 2.5
    # designed: numbers; findings checked before the lock: check
    shown = alpha_now()
    assert shown["design"] is None and shown["progress"]["needed"] > 0 and shown["gaps"] is not None
    findings = design.root / "props/work/checks/gaps/alpha/findings.json"
    findings.parent.mkdir(parents=True)
    findings.write_text("{}")
    os.utime(findings, (1760000000, 1760000000))  # checked before the lock
    assert alpha_now()["design"] == "check"
    findings.unlink()
    # another lock: the reading counts for nothing; an unlock: drawing again
    assert "data-v>lamp</span>" in owner.get("/concept/alpha/").content.decode()
    drawing.recorded(store, "concepts/alpha/picks/2099-01-01T10-00-00.json",
                     {"place": "alpha", "sha": "o" * 64, "by": "joey", "at": "2099-01-01T10:00:00+00:00"})
    shown = alpha_now()
    assert (shown["design"], shown["progress"], shown["gaps"]) == ("read", None, None)
    assert screens.place(design.source, "alpha", None)["items"] == []
    page = signed_in("joey3").get("/concept/alpha/").content.decode()
    assert "data-v>lamp</span>" not in page and "data-v>to read</span>" in page
    drawing.recorded(store, "concepts/alpha/picks/2099-01-01T11-00-00.json",
                     {"place": "alpha", "sha": None, "by": "joey", "at": "2099-01-01T11:00:00+00:00"})
    assert (alpha_now()["design"], alpha_now()["progress"]) == ("draw", None)
