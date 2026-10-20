"""Every page renders for the owner from the fixture world; a signed-out visitor is sent to the sign-in page; node ids
stay inside the details fold; every POST needs its CSRF token; the five screens (#42) show numbers, not prose: at most
WORD_BUDGET words outside data, hover text and scripts, and a number the runner does not give is a grey "unknown"."""
import datetime
import json
import pathlib
import re
from html import unescape
from html.parser import HTMLParser

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

pytestmark = pytest.mark.django_db
PAGES = ["/", "/place/alpha/", "/place/beta/", "/place/alpha/step/closeup/", "/place/beta/step/assembly/",
         "/world/step/terrain/", "/basket/", "/buy/", "/stats/", "/runs/", "/requests/", "/picks/alpha", "/view/alpha"]
POSTS = ["/place/alpha/step/closeup/request/", "/place/alpha/step/closeup/decide/", "/place/alpha/step/closeup/queue/",
         "/basket/change/", "/refresh/", "/freshness/"]
NODE = re.compile(r"\b[a-z][a-z-]+@(alpha|beta)\b")


def signed_in(name="joey"):
    user = get_user_model().objects.create_user(name, password="a long enough password")
    client = Client()
    client.force_login(user)
    return client


def outside_details(html):
    """The page's visible text outside <details class="ids">, its tags and attributes dropped."""
    html = re.sub(r'<details class="ids">.*?</details>', "", html, flags=re.S)
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


def test_every_page_renders_for_the_owner(world):
    client = signed_in()
    for page in PAGES:
        answer = client.get(page)
        assert answer.status_code == 200, (page, answer.status_code)


def test_signed_out_is_sent_to_sign_in():
    for page in PAGES:
        answer = Client().get(page)
        assert answer.status_code == 302 and answer["Location"].startswith("/login/"), page
    assert Client().get("/login/").status_code == 200


def test_the_step_page_shows_its_own_picture_large(world):
    detail = world.source.step_detail("alpha", "assembly")
    html = signed_in().get("/place/alpha/step/assembly/").content.decode()
    assert f'src="{detail.picture.url}"' in html


def test_the_step_page_shows_files_gates_and_the_waiting_output(world):
    html = signed_in().get("/place/alpha/step/closeup/").content.decode()
    assert "closeups/lamp.png" in html and "looks" in html
    assert "Waiting output" in html and "Accept this output" in html and "worse_reason" in html
    assert "Reject" in html and "Queue this step" in html


def test_no_node_id_outside_the_details_fold(world):
    client = signed_in()
    for page in PAGES[:6]:
        found = NODE.search(outside_details(client.get(page).content.decode()))
        assert found is None, (page, found and found.group(0))


def test_a_non_owner_sees_no_owner_actions(world):
    html = signed_in("guest").get("/place/alpha/step/closeup/").content.decode()
    assert "Accept this output" not in html and "Queue this step" not in html
    assert signed_in("guest2").post("/place/alpha/step/closeup/decide/").status_code == 403


def test_csrf_is_enforced_on_every_post(world):
    user = get_user_model().objects.create_user("joey", password="a long enough password")
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    for page in POSTS:
        assert client.post(page, {"words": "x"}).status_code == 403, page


def test_a_change_request_is_recorded_and_written_to_the_inbox(world, settings):
    client = signed_in()
    answer = client.post("/place/alpha/step/closeup/request/", {"words": "the lamp is too red", "output": "x"})
    assert answer.status_code == 302
    from score.dashboard.pages.models import ChangeRequest
    change = ChangeRequest.objects.get()
    assert change.node == "closeup@alpha" and change.words == "the lamp is too red"
    assert (settings.SCORE_HOME / "inbox" / f"{change.pk}.json").is_file()


def test_the_owner_accepts_the_waiting_worse_output_with_a_reason(world):
    client = signed_in()
    waiting = world.outputs["closeup@alpha waiting"]
    client.post("/place/alpha/step/closeup/decide/", {"decision": "accept", "output": waiting})
    assert world.store.accepted("closeup@alpha") != waiting
    client.post("/place/alpha/step/closeup/decide/", {"decision": "accept", "output": waiting,
                                                      "worse_reason": "one fault is fine here"})
    assert world.store.accepted("closeup@alpha") == waiting
    assert world.store.current_accept("closeup@alpha")["by"] == "joey"


def test_queue_this_step_and_the_next(world):
    client = signed_in()
    client.post("/place/alpha/step/plan/queue/", {"which": "this"})
    client.post("/place/alpha/step/scene-record/queue/", {"which": "next"})
    from score.dashboard.pages.models import BasketItem
    queued = {(item.place, item.stage) for item in BasketItem.objects.all()}
    assert ("alpha", "plan") in queued and ("alpha", "assembly") in queued
    html = client.get("/basket/").content.decode()
    assert "Alpha" in html and "Work out the plan" in html


def test_back_after_a_post_stays_on_this_site(world):
    client = signed_in()
    for back in ("https://evil.example/", "//evil.example/", "javascript:alert(1)"):
        answer = client.post("/refresh/", {"back": back})
        assert answer.status_code == 302 and answer["Location"] == "/", back
    assert client.post("/refresh/", {"back": "/place/alpha/"})["Location"] == "/place/alpha/"


def test_the_step_page_shows_its_output_beside_what_it_read(world):
    html = signed_in().get("/place/alpha/step/demo-film/").content.decode()
    assert "Output beside what it was made from" in html
    assert "reads: OpenUSD stage" in html and "reads: completion" in html and "this step's output" in html
    assert 'data-fps="24"' in html  # the film's frame scrubber


def test_the_3d_viewer_without_a_copy_says_so(world):
    html = signed_in().get("/view/alpha").content.decode()
    assert "No 3D web copy of this place yet" in html and "view3d.js" not in html
    assert signed_in("other").get("/view/nowhere").status_code == 404


def test_the_3d_viewer_loads_a_places_copy_with_its_layer_makers(world):
    import json
    folder = world.root / "web" / "alpha"
    folder.mkdir(parents=True)
    (folder / "alpha.json").write_text(json.dumps({
        "place": "alpha", "from_output": world.outputs["assembly@alpha"], "made_at": "2026-10-18T12:00:00Z",
        "objects": [{"name": "Lamp", "layer": "light", "low": [0, 0, 0], "high": [1, 1, 1]}], "bytes": 10,
        "light_bytes": 5, "triangles": 12}))
    client = signed_in()
    html = client.get("/view/alpha").content.decode()
    assert "/static/pages/view3d.js" in html and "importmap" in html
    given = json.loads(re.search(r'<script id="view3d-data" type="application/json">(.*?)</script>', html,
                                 re.S).group(1))
    assert given["place"] == "alpha" and given["layers"]["light"] == {"label": "light sweep",
                                                                      "url": "/place/alpha/step/light/"}
    assert "edit" in given["order"] and "edit" not in given["layers"]  # the owner's own edits: no step made them
    assert NODE.search(outside_details(html)) is None
    assert 'src="/view/alpha?gaps=1&amp;embed=1"' in client.get("/place/alpha/").content.decode()


def a_check_finding(world, judged):
    """The library check's findings.json for beta over the output `judged` of its assembly, with one marked picture."""
    import json
    from score.dashboard.tests import fixture
    folder = world.root / "props/work/checks/library/beta"
    (folder / "marks").mkdir(parents=True, exist_ok=True)
    (folder / "marks/beta-0.png").write_bytes(fixture.picture((200, 60, 40)))
    (folder / "findings.json").write_text(json.dumps({"place": "beta", "outputs": {"assembly@beta": judged},
        "findings": [{"rule": "finish not from the library", "prim": "/beta/Objects/crate_1",
                      "sentence": "3 models (crate) finish not from the library: a picture's own texture",
                      "picture": "marks/beta-0.png"}]}))


MEASURED = {"likely_euros": 2.0, "high_euros": 3.0, "likely_minutes": 10.0, "high_minutes": 20.0, "runs": 4,
            "cards": 1}
PLAN_WORK = "data/plans/alpha.json with its leads"


def a_gaps_finding(world, settings, tmp_path):
    """The gaps check's findings.json for alpha over its accepted assembly: two objects of a row the close-up step
    fills (a basket item carries it, measured), a gate on a step nothing buys now, and the plan no stage
    makes yet (its scene record names no leads); the basket made with that one item."""
    import json
    from score.dashboard.proposals import make, records
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


FORECAST = {**MEASURED, "basis": "per unit × forecast", "units": 2, "unit_source": "the place's missing rows"}
GUESSED = {"likely_euros": None, "high_euros": None, "guess_euros": 1.0, "guess_from": "score/stages/__init__.py:243",
           "likely_minutes": None, "high_minutes": None, "runs": 0, "basis": "not measured yet", "units": None}


def a_gaps_price(world, **more):
    """The runner's price of alpha's gaps (score price --gaps), made now on this checkout's code, after the
    findings: the close-up priced per unit times its forecast units, the sound it needs to complete only guessed,
    complete free (`more` over it)."""
    import json
    from score import graph
    from score.dashboard.state import local
    folder = world.root / "props/work/checks/gaps-price"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "world1.json").write_text(json.dumps({
        "world": "world1", "made_at": graph.now(), "priced_on": {**local.priced_here(), "uncommitted": False},
        "nodes": {"closeup@alpha": FORECAST, "sound@alpha": GUESSED},
        "chains": {"alpha": {"closeup@alpha": ["closeup@alpha", "complete@alpha", "sound@alpha"],
                             "complete@alpha": ["complete@alpha", "sound@alpha"]}},
        "gaps": {"alpha": {}}, "free": ["complete@alpha"], "totals": {},
        "unfillable": [{"work": PLAN_WORK, "gaps": 1}], "outside": [], "not_current": [], "not_checked": [], **more}))


def test_a_lost_input_two_places_and_the_world_read_is_one_gap_of_the_total(world):
    """The gaps check writes the environment's own lost inputs as the pseudo-place `world`; the total counts it, and
    one lost input read by alpha, beta and the world once."""
    import json
    lost = {"id": "place:lost:earth-seed:usd-r3", "rule": "place", "prim": None, "kind": None,
            "sentence": "lost input usd-r3", "picture": None, "row": None, "gates": [], "source": "inputs",
            "node": None, "work": "earth seed lost", "placed": None, "low": None, "high": None}
    take = dict(lost, id="place:lost:pixal:pliers-pf", sentence="lost input pliers-pf", work="take lost")
    for place, outputs, found in (("alpha", {"assembly@alpha": world.outputs["assembly@alpha"]}, [lost]),
                                  ("beta", {"assembly@beta": world.outputs["assembly@beta"]}, [lost]),
                                  ("world", {}, [lost, take])):
        folder = world.root / "props/work/checks/gaps" / place
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "findings.json").write_text(json.dumps({"place": place, "outputs": outputs, "findings": found}))
    total = world.source.gaps_total()
    assert total.counts == {"lost": 2}, total
    assert total.unfillable == ["earth seed lost", "take lost"], total


BOOKS = "the month's books before any paid step: the month's spend is unknown"


def milestones():
    """A plan the runner wrote: the ground (its set budget, code work and the owner's steps), what alpha holds,
    the environment's film unpriced, the owner's approval."""
    return [
        {"key": "ground", "title": "The ground", "stages": [{"stage": "terrain", "nodes": 1, "paid": 1}], "nodes": 1,
         "places": 0, "paid": ["terrain"], "likely_euros": 0, "high_euros": 0, "measured": 0,
         "set": {"euros": 6.0, "nodes": 1, "from": [{"at": "score/stages/__init__.py:46", "euros": 6.0, "nodes": 1}]},
         "unknown": [{"node": "terrain", "why": "not measured yet: no run of terrain in the cloud ledger"}],
         "after_work": {"likely_euros": 0, "high_euros": 0, "unknown": 0, "nodes": 0},
         "work": [{"work": PIXAL, "gaps": 2}, {"work": OWNERS, "gaps": 1}], "owner": [BOOKS], "reads": []},
        {"key": "made", "title": "What each place holds", "stages": [{"stage": "closeup", "nodes": 1, "paid": 1},
                                                                     {"stage": "sound", "nodes": 1, "paid": 1}],
         "nodes": 2, "places": 1, "paid": ["closeup@alpha", "sound@alpha"], "likely_euros": 2.0, "high_euros": 3.0,
         "measured": 1, "set": {"euros": 1.0, "nodes": 1, "from": [{"at": "score/stages/__init__.py:243", "euros": 1.0,
                                                                     "nodes": 1}]},
         "unknown": [{"node": "sound@alpha", "why": "not measured yet: no run of sound in the cloud ledger"}],
         "after_work": {"likely_euros": 4.0, "high_euros": 6.0, "unknown": 0, "nodes": 2,
                        "counts": ["one Pixal3D model a gap of this work line"]}, "work": [], "owner": [],
         "reads": ["ground"]},
        {"key": "split", "title": "Shells split into inside places", "stages": [], "nodes": 0, "paid": [],
         "likely_euros": 0, "high_euros": 0, "measured": 0, "set": {"euros": 0, "nodes": 0, "from": []},
         "unknown": [], "after_work": {"likely_euros": 0, "high_euros": 0, "unknown": 0, "nodes": 0}, "work": [],
         "owner": [], "reads": [], "missing": ["shell-split"],
         "unpriced": "no row of the stage table does this yet: shell-split"},
        {"key": "environment-film", "title": "The environment's film", "unpriced": "no row of the stage table cuts it",
         "owner": []},
        {"key": "approval", "title": "Your approval of the final video", "owner": ["you approve the final video"]}]


def test_the_plan_goes_through_the_export_whole(world, settings, tmp_path):
    from score.dashboard.state.exported import ExportedSource
    from score.dashboard.state.models import Spend
    from score.dashboard.sync import building
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world, milestones=milestones())
    world.source.refresh()
    building.build(world.source, tmp_path / "export", "2026-10-20T09:00:00+00:00", 50, Spend(), world.root)
    assert ExportedSource(tmp_path / "export").world_state().gaps_price.milestones == milestones()


PIXAL = ("Pixal3D take lost: pixal@<place>'s accepted output carries its takes and every reader reads them through an "
         "`after` on it; then each lost take is a pixal gap, priced")
OWNERS = "the owner supplies cockpit.png, his own reference picture (kept off the public repository)"


def test_every_priced_step_and_place_has_plain_words():
    from score.dashboard.pages import present
    from score.dashboard.state import groups, plain
    assert groups.label("crops-layer") == "crops"
    assert groups.label("crops-boxes") == "crop boxes" and groups.label("crops-look") == "crop renders"
    assert groups.label("surface-tiles") == "surface tiles" and groups.label("ship_kit") == "ship kit"
    assert groups.label("people-dress-nev-work") == "dressed body of the nev-work look"
    assert plain.place_words("gdoor") == "the garage door" and present.place_title("hdoor") == "Hangar door"
    assert plain.lost_words("place:lost:earth-seed:gdoor") == "garage door"  # its seed folder, by the kit's title


def test_the_viewer_outlines_the_gaps_when_asked(world, settings, tmp_path):
    import json
    a_gaps_finding(world, settings, tmp_path)
    (world.root / "web/alpha").mkdir(parents=True)
    (world.root / "web/alpha/alpha.json").write_text(json.dumps({
        "place": "alpha", "from_output": world.outputs["assembly@alpha"], "made_at": "2026-10-18T12:00:00Z",
        "objects": [], "bytes": 10, "light_bytes": 5, "triangles": 12}))
    client = signed_in()
    assert 'src="/view/alpha?gaps=1&amp;embed=1"' in client.get("/place/alpha/").content.decode()

    def marks(page):
        html = client.get(page).content.decode()
        return json.loads(re.search(r'<script id="view3d-data" type="application/json">(.*?)</script>', html,
                                    re.S).group(1))["marks"]
    assert marks("/view/alpha") == []
    assert [{name: mark[name] for name in ("id", "low", "high", "kind")} for mark in marks("/view/alpha?gaps=1")] == [
        {"id": "missing:lamp_1", "low": [0, 0, 0], "high": [1, 1, 1], "kind": "missing"},
        {"id": "missing:lamp_2", "low": [2, 0, 0], "high": [3, 1, 1], "kind": "missing"},
        {"id": "gate:complete/painted:crate_1", "low": [4, 0, 0], "high": [5, 1, 1], "kind": "gate"}]


def test_gaps_are_not_repeated_among_the_check_findings(world, settings, tmp_path):
    a_gaps_finding(world, settings, tmp_path)
    assert [finding.check for finding in world.source.check_findings("alpha")] == []
    assert [gap.id for gap in world.source.gaps("alpha")][:1] == ["missing:lamp_1"]


def test_a_standalone_checks_findings_stand_only_while_the_output_they_judged_is_accepted(world):
    a_check_finding(world, world.outputs["assembly@beta"])
    assert [finding.rule for finding in world.source.check_findings("beta")] == ["finish not from the library"]


def test_a_check_finding_on_an_assembly_no_longer_accepted_is_not_read(world):
    a_check_finding(world, "0" * 64)
    assert world.source.check_findings("beta") == []


def test_the_runners_prices_are_summed_each_basis_apart():
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
    assert cockpit.measured_prices(price) == (3, 6)  # a guess is never a measured price


# --- the cockpit's screens (#42): numbers, colours, pictures and buttons, not prose -------------------------------

WORD_BUDGET = 40  # a screen's words outside data, hover text and scripts (owner, 2026-10-20: text down about 98%)
SCREENS = ["/", "/place/alpha/", "/buy/", "/stats/", "/library/"]


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


def test_the_word_count_skips_data_hover_text_and_scripts():
    assert prose('<p>one two <b data-v>Alpha <i>beta</i></b><svg><circle r="1"/><title>a hover</title></svg>'
                 '<span title="many words here">x</span><script>var y</script></p>') == ["one", "two", "x"]


def a_month(monkeypatch, **more):
    """The month's spend as the store's machine read it: the cloud bill known, the model bill only partly counted
    (no figure), the environment's one stop line at EUR 250."""
    from score.dashboard.pages import actions
    from score.dashboard.state.models import CostLine, Spend
    lines = [CostLine(source="cloud", label="Cloud compute", euros=12.5),
             CostLine(source="models", label="Model calls", euros=0.0, partial=True)]
    monkeypatch.setattr(actions, "spend", lambda: Spend(ceiling=250.0, month="2026-10", lines=lines, **more))


def test_every_screen_shows_numbers_not_prose(world, settings, tmp_path, monkeypatch):
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world, milestones=milestones())
    world.source.refresh()
    a_month(monkeypatch, paid_refused="the month's books are lost")
    client = signed_in()
    for page in SCREENS:
        html = client.get(page).content.decode()
        words = prose(html)
        assert len(words) <= WORD_BUDGET, (page, len(words), words)
        assert "Traceback" not in html and "/api/money/stop" not in html and "/api/money/month" not in html, page


def test_the_environment_is_the_month_the_remake_and_a_tile_per_place(world, settings, tmp_path, monkeypatch):
    from score.dashboard.tests.screens_test import a_remake
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world, milestones=milestones(), eta={"likely_minutes": 95.0, "high_minutes": 130.0, "unknown": []})
    a_remake(world)
    world.source.refresh()
    a_month(monkeypatch)
    client = signed_in()
    html = client.get("/").content.decode()
    tiles = dict(re.findall(r'<a class="ptile" href="/place/(\w+)/"(.*?)</a>', html, re.S))
    assert set(tiles) == {"alpha", "beta"}
    assert "tone-gap-route" in tiles["alpha"] and "<b data-v>4</b>" in tiles["alpha"]  # its worst kind: a route step
    assert "tone-done" in tiles["beta"] and "<b data-v>0</b>" in tiles["beta"]
    assert all(re.search(r"<text [^>]*data-v>\d+/\d+</text>", tile) for tile in tiles.values())  # made / needed
    assert all(re.search(r"<title>made \d+ of \d+</title>", tile) for tile in tiles.values())  # said by hover
    assert 'title="4 gaps"><svg class="gap-icon tone-gap-route"' in tiles["alpha"]
    assert '<img src="/thumbs/' in tiles["alpha"] and "concept missing" not in tiles["alpha"]  # its concept
    assert "<img" not in tiles["beta"] and "concept missing" in tiles["beta"]  # lost: never a render instead
    top = html[html.index('<section class="topbar">'):html.index('<section class="ptiles"')]
    # the cloud bill read, the model bill not: at least the cloud's, the missing line as hover text; no stop shown
    assert "<small>&ge;</small> <small>EUR</small> 12.50" in top and "not read: Model calls" in top
    assert "250" not in top and "stop" not in top
    # prepare's figure (EUR 10 to 12) and the gaps price off the prop route (none measured): prepare times no step
    assert "<small>EUR</small> 10&ndash;12<small>, " in top and "&ge; 0.5 h</span>" in top  # at least its floor
    assert 'href="/buy/">Review and buy</a>' in top


def test_the_environment_shows_the_outside_places_and_opens_each_to_the_places_inside_it(world, settings, tmp_path):
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    (world.data / "places").mkdir(exist_ok=True)
    (world.data / "places/within.json").write_text(json.dumps({
        "shells": {"yard": {"name": "Yard"}, "empty": {"name": "Empty"}},
        "within": {"alpha": {"within": "beta"}, "beta": {"within": "yard"}}}))
    client = signed_in()

    def tiles(page):
        html = client.get(page).content.decode()
        return re.findall(r'<a class="ptile" href="([^"]+)"(.*?)</a>', html, re.S), html
    found, _ = tiles("/")
    assert [href for href, _ in found] == ["/?in=yard"]  # one outside shell; a shell holding no place shows not
    assert "<b data-v>Beta, 1 place</b>" in found[0][1] and "tone-gap-route" in found[0][1]  # alpha's gaps summed
    assert "concept missing" in found[0][1]  # the yard has no concept, and never takes one from inside
    found, html = tiles("/?in=yard")
    assert [href for href, _ in found] == ["/?in=beta"] and '<a href="/" data-v>Environment</a>' in html
    assert "<b data-v>+1</b>" in found[0][1]  # alpha sits in beta, a leaf
    found, html = tiles("/?in=beta")
    assert [href for href, _ in found] == ["/place/beta/", "/place/alpha/"]  # itself first, then what it holds
    assert '<a href="/?in=yard" data-v>Yard</a>' in html and "<b data-v>Beta</b>" in html
    assert client.get("/?in=alpha").status_code == 404 and client.get("/?in=empty").status_code == 404


def test_the_remake_is_prepares_whole_figure_plus_the_rest_and_its_time_only_when_every_step_is_timed(
        world, settings, tmp_path):
    from score.dashboard.pages import cockpit
    from score.dashboard.tests.screens_test import a_remake
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world, milestones=milestones())
    a_remake(world)
    world.source.refresh()
    remake = cockpit.remake(world.source.world_state())
    # prepare's EUR 10 to 12 (the likeness calibration unpriced) and the sound off the prop route, only guessed
    assert (remake["low"], remake["high"], remake["hours"], remake["unknown"]) == (10.0, 12.0, None, 2), remake
    untimed = {"likely_minutes": None, "high_minutes": None, "at_least_minutes": 45.0,
               "unknown": [{"node": "sound@alpha", "paid": True, "why": "no run of sound in the cloud ledger"}]}
    a_gaps_price(world, milestones=milestones(), eta=untimed)
    world.source.refresh()
    remake = cockpit.remake(world.source.world_state())
    assert remake["hours"] is None and remake["at_least_hours"] == 0.8  # the longer floor of the two


def test_a_stale_planless_or_other_codes_price_shows_no_remake_figure(world, settings, tmp_path):
    from score.dashboard.pages import cockpit
    from score.dashboard.state import local
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    world.source.refresh()
    assert cockpit.remake(world.source.world_state())["why"] == "prepare has not run"
    here = local.priced_here()
    for priced_on, said in (({**here, "commit": "0" * 40, "uncommitted": False}, "the code moved"),
                            ({**here, "per_unit_sha256": "0" * 64, "uncommitted": False}, "per-unit prices"),
                            ({**here, "uncommitted": True}, "code not committed"), (None, "before the price")):
        a_gaps_price(world, milestones=milestones(), priced_on=priced_on)
        world.source.refresh()
        price = world.source.gaps_price()
        remake = cockpit.remake(world.source.world_state())
        assert remake["low"] is None and said in remake["why"], (said, remake)
        assert cockpit.measured_prices(price) == (None, None)
    assert said in unescape(signed_in().get("/").content.decode())  # the why is the hover text


def test_stats_are_numbers_against_the_one_stop_and_unknown_stays_grey(world, settings, tmp_path, monkeypatch):
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    world.source.refresh()
    a_month(monkeypatch, bill_days=[{"day": "2026-10-02", "cloud": 2.0, "models": 0.5},  # the bills as read
                                    {"day": "2026-10-03", "cloud": 3.5, "models": 0.5}],
            days=[{"day": "2026-10-01", "cloud": 1.0, "models": 0.0}])  # the ledgers' own count
    html = signed_in().get("/stats/").content.decode()
    cards = dict(re.findall(r'<div class="num-label">(?:<i [^>]*></i>)?(?:<span data-v>)?([^<]+)(?:</span>)?</div>\s*'
                            r'<div class="num-value[^"]*"[^>]*>(.*?)</div>', html, re.S))
    assert cards["Cloud compute"] == "<small>EUR</small> 12.50"  # each line by its own label
    assert cards["AI calls"] == "unknown" and cards["Total"] == "unknown"  # a partial count is no figure
    assert "stop" not in html.lower()
    assert cards["Steps with a measured price"] == "1<small> of 2</small>"  # the close-up measured, the sound guessed
    assert cards["Places complete"] == "1<small> of 2</small>"  # beta, checked with no gap
    assert [cards[label] for label in ("not made yet", "failing a check", "steps of the route still to do",
                                       "inputs lost")] == ["2", "1", "1", "0"]
    assert '<a class="num-card num-link" href="/?kind=missing"' in html
    assert "<title>2026-10-01: EUR 1.00, at least" in html and "<title>2026-10-03: EUR 1.50</title>" in html
    main = html[html.index("<main>"):]
    assert "<form" not in main and "<button" not in main  # numbers only, no controls


def test_spend_by_day_takes_the_bills_growth_else_the_ledger_else_a_gap():
    from score.dashboard.pages import cockpit
    bills = [{"day": "2026-10-02", "cloud": 2.0, "models": 0.5}, {"day": "2026-10-03", "cloud": 3.5, "models": 0.5},
             {"day": "2026-10-05", "cloud": 5.0, "models": None}]  # a reading missing a line counts as none
    ledger = [{"day": "2026-10-01", "cloud": 1.0, "models": 0.0}, {"day": "2026-10-02", "cloud": 0.3, "models": 0.0},
              {"day": "2026-10-04", "cloud": 0.5, "models": 0.2},
              {"day": "2026-10-06", "cloud": 0, "models": 0.0}]  # the ledgers' 0 says nothing: they miss the bills
    days = cockpit.spend_by_day(bills, ledger, "2026-10", datetime.date(2026, 10, 6))
    assert [(day["day"][-2:], day["euros"], day["whole"]) for day in days] == [
        ("01", 1.0, False), ("02", 0.3, False), ("03", 1.5, True), ("04", 0.7, False), ("05", None, False),
        ("06", None, False)]  # the 2nd's reading has no reading the day before: its growth is not known
    first = cockpit.spend_by_day([{"day": "2026-10-01", "cloud": 1.0, "models": 1.0}], [], "2026-10",
                                 datetime.date(2026, 10, 1))
    assert first == [{"day": "2026-10-01", "euros": 2.0, "whole": True}]  # the month grows from 0 on the 1st
    chart = cockpit.day_chart(days)
    assert [tick["euros"] for tick in chart["ticks"]] == [0, 1.0, 2.0]  # one scale, a round top
    assert len(chart["bars"]) == 4 and [gap["day"][-2:] for gap in chart["gaps"]] == ["05", "06"]
    assert cockpit.unplaced(10.0, days) == 6.5 and cockpit.unplaced(None, days) is None
    assert [cockpit.scale_top(value) for value in (0, 0.4, 3, 2119.85, 12408)] == [1.0, 1.0, 5, 2500, 20000]


def test_the_place_screen_is_its_3d_view_its_scene_tree_and_a_side_panel(world, settings, tmp_path):
    a_gaps_finding(world, settings, tmp_path)
    world.source.refresh()
    html = signed_in().get("/place/alpha/").content.decode()
    assert 'src="/view/alpha?gaps=1&amp;embed=1"' in html and '<aside class="side-panel" id="panel" hidden>' in html
    assert re.search(r'<span class="node-label" data-v>Gaps</span><span class="node-count" data-v>2</span>', html)
    # only the top level is drawn: each branch loads its rows when it opens
    assert '<details data-children="/place/alpha/branch/?path=Gaps">' in html
    assert '<details data-children="/place/alpha/branch/?path=Objects">' in html
    assert 'data-title="lamp"' not in html and 'data-title="crate_1"' not in html
    # the place's own gap (its plan, a route step) hangs at the top, its panel with no price measured
    assert 'data-title="place:plan" data-state="route" data-tone="gap-route" data-price="unknown"' in html
    assert NODE.search(outside_details(html)) is None


def test_a_scene_branch_loads_its_rows_with_each_items_panel(world, settings, tmp_path):
    import json
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    world.source.refresh()
    client = signed_in()
    [lamp] = client.get("/place/alpha/branch/?path=Gaps").json()
    assert (lamp["label"], lamp["count"], lamp["tone"]) == ("lamp", 2, "gap-missing")
    panel = lamp["panel"]
    assert (panel["title"], panel["state"], panel["gap"], panel["price"]) == (
        "lamp", "missing", "missing:lamp_1", "EUR 2.00–3.00 +")
    # the close-up has a waiting output: the owner's one action is its accept, his signed-in request
    assert (panel["action"], panel["action_label"], panel.get("reason", False)) == ("/api/decisions", "Accept", False)
    assert json.loads(panel["body"]) == {"node": "closeup@alpha", "output": world.outputs["closeup@alpha waiting"],
                                         "decision": "accept"}
    [crate] = client.get("/place/alpha/branch/?path=Objects").json()
    assert crate["panel"]["state"] == "failing" and crate["panel"]["price"] == "unknown"
    assert "action" not in signed_in("guest").get("/place/alpha/branch/?path=Gaps").json()[0]["panel"]
    assert client.get("/place/alpha/branch/?path=Nowhere").status_code == 404


PLAYWRIGHT = "playwright@1.62.1"  # viewer_look.py's: its Chromium (1234) is the one installed in ~/.cache/ms-playwright
SHELL = pathlib.Path.home() / ".cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64"


def chromium_runs():
    """Whether the headless Chromium is installed with every library it loads (LD_LIBRARY_PATH counted)."""
    import subprocess
    shell = SHELL / "chrome-headless-shell"
    return shell.is_file() and "not found" not in subprocess.run(["ldd", str(shell)], capture_output=True,
                                                                 text=True).stdout


@pytest.mark.skipif(not chromium_runs(), reason="no headless Chromium that runs on this machine")
def test_a_click_on_a_scene_item_opens_its_panel_frames_it_and_posts_its_action(world, settings, tmp_path):
    """In a browser: the top level only, a branch loaded once when it opens, an item's panel filled, the 3D view
    told to frame its gap, its Accept the owner's JSON request with the CSRF token."""
    import json
    import subprocess
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    world.source.refresh()
    client = signed_in()
    branch = "/place/alpha/branch/?path=Gaps"
    job = tmp_path / "click.json"
    job.write_text(json.dumps({
        "page": "/place/alpha/", "html": client.get("/place/alpha/").content.decode(), "branch": "Gaps",
        "item": "lamp", "branches": {branch: client.get(branch).json()},
        "dash": str(pathlib.Path(__file__).parents[1] / "pages/static/pages/dash.js")}))
    done = subprocess.run(["npx", "-y", "-p", PLAYWRIGHT, "node", str(pathlib.Path(__file__).with_name(
        "screens_click.mjs")), str(job)], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr[-3000:]
    seen = json.loads(done.stdout.strip().splitlines()[-1])
    assert seen["before"] == 0 and seen["fetched"] == [branch]
    assert (seen["open"], seen["title"], seen["state"], seen["price"], seen["button"]) == (
        True, "lamp", "missing", "EUR 2.00–3.00 +", "Accept")
    assert json.loads(seen["framed"]) == {"gap": "missing:lamp_1"}
    assert seen["posted"] == [{"url": "/api/decisions", "csrf": "token", "body": {
        "node": "closeup@alpha", "output": world.outputs["closeup@alpha waiting"], "decision": "accept"}}]


def test_the_buy_screen_shows_design_first_and_the_batch_after_it_bought_only_for_approved_designs(
        world, settings, tmp_path, monkeypatch):
    """Design first: each place's concept and plan, made on its card, never bought here; the batch after design, each
    layer how many it makes and its euros, no step's own name; its Buy only once a design is approved, and it buys
    only the approved places' steps (the basket's close-up at alpha, its stop its high plus 10%)."""
    from score.dashboard.pages.models import Checkout
    from score.dashboard.tests.screens_test import SETTLE, a_remake
    a_month(monkeypatch)
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world, nodes={"settle@alpha": SETTLE, "sound@alpha": {
        "likely_euros": None, "high_euros": None, "guess_euros": 1.0, "basis": "not measured yet"}},
        eta={"likely_minutes": None, "high_minutes": None, "at_least_minutes": 20.0, "unknown": [{"node": "sound"}]})
    a_remake(world, approved=())
    world.source.refresh()
    client = signed_in()
    html = client.get("/buy/").content.decode()
    top = html[html.index('<div class="topbar">'):html.index('<ul class="buy-layers buy-design">')]
    assert "0 <small>of</small> 2 <small>approved</small>" in top and "<small>EUR</small> 12.00&ndash;15.00" in top
    assert 'data-url="/buy/yes/"' not in html  # no design approved: nothing to buy
    rows = re.findall(r'href="/place/(\w+)/" data-v>.*?</a><span class="buy-n" data-v>(\w+)</span>'
                      r'<span class="buy-n" data-v>([\w ]+)</span>', html)
    assert rows == [("alpha", "missing", "to remake"), ("beta", "missing", "to remake")]
    layers = re.findall(r'<span class="node-label" data-v>(\w+)</span><span class="buy-n" data-v>(\d+)</span>', html)
    assert layers == [("Models", "2"), ("Motion", "1"), ("Sound", "1")]
    assert not re.search(r"predicted to fail|calibration|earlier step|lost concept|<details", html)
    a_remake(world)  # alpha's design approved
    world.source.refresh()
    top = client.get("/buy/").content.decode().split('<ul class="buy-layers buy-design">')[0]
    assert "1 <small>of</small> 2 <small>approved</small>" in top and '"batch": "now"' in top
    assert "it stops at EUR 3.30" in top and re.search(r'<i class="dot" data-slot="said" hidden>', top)
    assert client.post("/buy/yes/", "{}", content_type="application/json").status_code == 422
    refused = client.post("/buy/yes/", {"key": "a" * 32, "batch": "benchmarks"}, content_type="application/json")
    assert refused.status_code == 409 and refused.json()["detail"].startswith("refused")  # no Benchmarks item
    assert signed_in("guest").post("/buy/yes/", {"key": "a" * 32}, content_type="application/json").status_code == 403
    assert 'data-url="/buy/yes/"' not in signed_in("guest2").get("/buy/").content.decode()
    Checkout.objects.create(key="k" * 8, by="joey", state="launched", stop_line={"high": 10.0, "euros": 30.0})
    assert '<small>stop EUR</small> 11.00' in client.get("/buy/").content.decode()


def test_the_buy_screen_has_no_basket_panel_and_the_books_buttons_only_while_needed(world, monkeypatch):
    from score.dashboard.state.models import CostLine, Spend
    from score.dashboard.pages import actions
    a_month(monkeypatch)
    client = signed_in()
    html = client.get("/buy/").content.decode()
    assert 'href="/basket/"' not in html.split('<main')[-1] and "/api/money/read-back" not in html
    assert ">Model calls figure</button>" in html  # the model calls' month is not read: his to enter
    lines = [CostLine(source="cloud", label="Cloud compute", euros=12.5),
             CostLine(source="models", label="Model calls", euros=1030.0)]
    monkeypatch.setattr(actions, "spend", lambda: Spend(ceiling=250.0, month="2026-10", lines=lines))
    assert "/api/money/books-figure" not in client.get("/buy/").content.decode()  # the books are known
    a_month(monkeypatch, paid_refused="the month's books are lost")
    html = client.get("/buy/").content.decode()
    assert 'data-post="/api/money/read-back"' in html and 'data-post="/api/money/books-figure"' in html
    guest = signed_in("guest").get("/buy/").content.decode()
    assert "/api/money/read-back" not in guest and "/api/money/books-figure" not in guest  # the owner's own buttons
