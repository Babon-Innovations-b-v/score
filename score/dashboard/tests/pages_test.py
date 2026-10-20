"""Every page renders for the owner from the fixture world; a signed-out visitor is sent to the sign-in page; node ids
stay inside the details fold; every POST needs its CSRF token; the five screens (#42) show numbers, not prose: at most
WORD_BUDGET words outside data, hover text and scripts, and a number the runner does not give is a grey "unknown"."""
import datetime
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
    assert 'src="/view/alpha?holes=1&amp;embed=1"' in client.get("/place/alpha/").content.decode()


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


def a_holes_finding(world, settings, tmp_path):
    """The holes check's findings.json for alpha over its accepted assembly: two objects of a row the close-up step
    fills (a basket item carries it, measured), a gate on a step nothing buys now, and the plan no stage
    makes yet (its scene record names no leads); the basket made with that one item."""
    import json
    from score.dashboard.proposals import make, records
    folder = world.root / "props/work/checks/holes/alpha"
    folder.mkdir(parents=True, exist_ok=True)
    missing = {"rule": "missing", "kind": "generate", "sentence": "a lamp: nothing made for it yet (made by the route)",
               "picture": None, "row": "lamp", "gates": [], "source": "inventory", "node": "closeup@alpha",
               "work": None, "placed": "spot"}
    (folder / "findings.json").write_text(json.dumps({"place": "alpha", "outputs": {
        "assembly@alpha": world.outputs["assembly@alpha"]}, "findings": [
        dict(missing, id="missing:lamp_1", prim="/alpha/Holes/lamp_1", low=[0, 0, 0], high=[1, 1, 1]),
        dict(missing, id="missing:lamp_2", prim="/alpha/Holes/lamp_2", low=[2, 0, 0], high=[3, 1, 1]),
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


def a_holes_price(world, **more):
    """The runner's price of alpha's holes (score price --holes), made now on this checkout's code, after the
    findings: the close-up priced per unit times its forecast units, the sound it needs to complete only guessed,
    complete free (`more` over it)."""
    import json
    from score import graph
    from score.dashboard.state import local
    folder = world.root / "props/work/checks/holes-price"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "world1.json").write_text(json.dumps({
        "world": "world1", "made_at": graph.now(), "priced_on": {**local.priced_here(), "uncommitted": False},
        "nodes": {"closeup@alpha": FORECAST, "sound@alpha": GUESSED},
        "chains": {"alpha": {"closeup@alpha": ["closeup@alpha", "complete@alpha", "sound@alpha"],
                             "complete@alpha": ["complete@alpha", "sound@alpha"]}},
        "holes": {"alpha": {}}, "free": ["complete@alpha"], "totals": {},
        "unfillable": [{"work": PLAN_WORK, "holes": 1}], "outside": [], "not_current": [], "not_checked": [], **more}))


def test_a_lost_input_two_places_and_the_world_read_is_one_hole_of_the_total(world):
    """The holes check writes the environment's own lost inputs as the pseudo-place `world`; the total counts it, and
    one lost input read by alpha, beta and the world once."""
    import json
    lost = {"id": "place:lost:earth-seed:usd-r3", "rule": "place", "prim": None, "kind": None,
            "sentence": "lost input usd-r3", "picture": None, "row": None, "gates": [], "source": "inputs",
            "node": None, "work": "earth seed lost", "placed": None, "low": None, "high": None}
    take = dict(lost, id="place:lost:pixal:pliers-pf", sentence="lost input pliers-pf", work="take lost")
    for place, outputs, found in (("alpha", {"assembly@alpha": world.outputs["assembly@alpha"]}, [lost]),
                                  ("beta", {"assembly@beta": world.outputs["assembly@beta"]}, [lost]),
                                  ("world", {}, [lost, take])):
        folder = world.root / "props/work/checks/holes" / place
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "findings.json").write_text(json.dumps({"place": place, "outputs": outputs, "findings": found}))
    total = world.source.holes_total()
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
         "work": [{"work": PIXAL, "holes": 2}, {"work": OWNERS, "holes": 1}], "owner": [BOOKS], "reads": []},
        {"key": "made", "title": "What each place holds", "stages": [{"stage": "closeup", "nodes": 1, "paid": 1},
                                                                     {"stage": "sound", "nodes": 1, "paid": 1}],
         "nodes": 2, "places": 1, "paid": ["closeup@alpha", "sound@alpha"], "likely_euros": 2.0, "high_euros": 3.0,
         "measured": 1, "set": {"euros": 1.0, "nodes": 1, "from": [{"at": "score/stages/__init__.py:243", "euros": 1.0,
                                                                     "nodes": 1}]},
         "unknown": [{"node": "sound@alpha", "why": "not measured yet: no run of sound in the cloud ledger"}],
         "after_work": {"likely_euros": 4.0, "high_euros": 6.0, "unknown": 0, "nodes": 2,
                        "counts": ["one Pixal3D model a hole of this work line"]}, "work": [], "owner": [],
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
    a_holes_finding(world, settings, tmp_path)
    a_holes_price(world, milestones=milestones())
    world.source.refresh()
    building.build(world.source, tmp_path / "export", "2026-10-20T09:00:00+00:00", 50, Spend(), world.root)
    assert ExportedSource(tmp_path / "export").world_state().holes_price.milestones == milestones()


PIXAL = ("Pixal3D take lost: pixal@<place>'s accepted output carries its takes and every reader reads them through an "
         "`after` on it; then each lost take is a pixal hole, priced")
OWNERS = "the owner supplies cockpit.png, his own reference picture (kept off the public repository)"


def test_every_priced_step_and_place_has_plain_words():
    from score.dashboard.pages import present
    from score.dashboard.state import groups, plain
    assert groups.label("crops-layer") == "crops"
    assert groups.label("crops-boxes") == "crop boxes" and groups.label("crops-look") == "crop renders"
    assert groups.label("surface-tiles") == "surface tiles" and groups.label("ship_kit") == "ship kit"
    assert groups.label("people-dress-nev-work") == "dressed body of the nev-work look"
    assert plain.place_words("gdoor") == "the garage door" and present.place_title("hdoor") == "Hangar roof door"
    assert plain.lost_words("place:lost:earth-seed:gdoor") == "garage door"  # its seed folder, by the kit's title


def test_the_viewer_outlines_the_holes_when_asked(world, settings, tmp_path):
    import json
    a_holes_finding(world, settings, tmp_path)
    (world.root / "web/alpha").mkdir(parents=True)
    (world.root / "web/alpha/alpha.json").write_text(json.dumps({
        "place": "alpha", "from_output": world.outputs["assembly@alpha"], "made_at": "2026-10-18T12:00:00Z",
        "objects": [], "bytes": 10, "light_bytes": 5, "triangles": 12}))
    client = signed_in()
    assert 'src="/view/alpha?holes=1&amp;embed=1"' in client.get("/place/alpha/").content.decode()

    def marks(page):
        html = client.get(page).content.decode()
        return json.loads(re.search(r'<script id="view3d-data" type="application/json">(.*?)</script>', html,
                                    re.S).group(1))["marks"]
    assert marks("/view/alpha") == []
    assert [{name: mark[name] for name in ("id", "low", "high", "kind")} for mark in marks("/view/alpha?holes=1")] == [
        {"id": "missing:lamp_1", "low": [0, 0, 0], "high": [1, 1, 1], "kind": "missing"},
        {"id": "missing:lamp_2", "low": [2, 0, 0], "high": [3, 1, 1], "kind": "missing"},
        {"id": "gate:complete/painted:crate_1", "low": [4, 0, 0], "high": [5, 1, 1], "kind": "gate"}]


def test_holes_are_not_repeated_among_the_check_findings(world, settings, tmp_path):
    a_holes_finding(world, settings, tmp_path)
    assert [finding.check for finding in world.source.check_findings("alpha")] == []
    assert [hole.id for hole in world.source.holes("alpha")][:1] == ["missing:lamp_1"]


def test_a_standalone_checks_findings_stand_only_while_the_output_they_judged_is_accepted(world):
    a_check_finding(world, world.outputs["assembly@beta"])
    assert [finding.rule for finding in world.source.check_findings("beta")] == ["finish not from the library"]


def test_a_check_finding_on_an_assembly_no_longer_accepted_is_not_read(world):
    a_check_finding(world, "0" * 64)
    assert world.source.check_findings("beta") == []


def test_the_runners_prices_are_summed_each_basis_apart():
    from score.dashboard.pages import cockpit
    from score.dashboard.state import holes
    from score.dashboard.state.models import HolesPrice
    price = HolesPrice(made_at="2026-10-19T20:00:00+00:00", nodes={
        "pixal@alpha": {**MEASURED, "basis": "measured runs"},
        "bake@alpha": {**MEASURED, "basis": "per unit × counted"},
        "lists@alpha": {**FORECAST},
        "sound@alpha": GUESSED, "sound@beta": {**GUESSED, "guess_euros": 1.5},
        "film@alpha": {**GUESSED, "guess_euros": None, "guess_from": None}})
    sums = holes.summed(price.nodes)
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
    a_holes_finding(world, settings, tmp_path)
    a_holes_price(world, milestones=milestones())
    world.source.refresh()
    a_month(monkeypatch, paid_refused="the month's books are lost")
    client = signed_in()
    for page in SCREENS:
        html = client.get(page).content.decode()
        words = prose(html)
        assert len(words) <= WORD_BUDGET, (page, len(words), words)
        assert "Traceback" not in html and "/api/money/stop" not in html and "/api/money/month" not in html, page


def test_the_environment_is_the_month_the_remake_and_a_tile_per_place(world, settings, tmp_path, monkeypatch):
    a_holes_finding(world, settings, tmp_path)
    a_holes_price(world, milestones=milestones(), eta={"likely_minutes": 95.0, "high_minutes": 130.0, "unknown": []})
    world.source.refresh()
    a_month(monkeypatch)
    html = signed_in().get("/").content.decode()
    tiles = dict(re.findall(r'<a class="ptile" href="/place/(\w+)/"(.*?)</a>', html, re.S))
    assert set(tiles) == {"alpha", "beta"}
    assert "tone-hole-route" in tiles["alpha"] and "<b data-v>4</b>" in tiles["alpha"]  # its worst kind: a route step
    assert "tone-done" in tiles["beta"] and "<b data-v>0</b>" in tiles["beta"]
    assert all(re.search(r"<text [^>]*data-v>\d+/\d+</text>", tile) for tile in tiles.values())  # made / needed
    assert all("/thumbs/" in tile for tile in tiles.values())  # each place's best picture
    top = html[html.index('<section class="topbar">'):html.index('<section class="ptiles"')]
    assert '<span class="unknown" title="a bill is not known yet">unknown</span>' in top  # the model bill: no figure
    assert "<small> / 250</small>" in top
    assert "<small>EUR</small> 2&ndash;3<small>, about 1.6 h</small>" in top  # the runner's plan, its ETA
    assert 'href="/buy/">Review and buy</a>' in top


def test_the_remake_is_the_runners_plan_and_its_time_only_when_every_step_is_timed(world, settings, tmp_path):
    from score.dashboard.pages import cockpit
    a_holes_finding(world, settings, tmp_path)
    a_holes_price(world, milestones=milestones())
    world.source.refresh()
    remake = cockpit.remake(world.source.holes_price())
    assert (remake["low"], remake["high"], remake["hours"], remake["unknown"]) == (2.0, 3.0, None, 2), remake
    untimed = {"likely_minutes": None, "high_minutes": None, "at_least_minutes": 30.0,
               "unknown": [{"node": "sound@alpha", "paid": True, "why": "no run of sound in the cloud ledger"}]}
    a_holes_price(world, milestones=milestones(), eta=untimed)
    world.source.refresh()
    assert cockpit.remake(world.source.holes_price())["hours"] is None


def test_a_stale_planless_or_other_codes_price_shows_no_remake_figure(world, settings, tmp_path):
    from score.dashboard.pages import cockpit
    from score.dashboard.state import local
    a_holes_finding(world, settings, tmp_path)
    a_holes_price(world)
    world.source.refresh()
    assert cockpit.remake(world.source.holes_price())["why"] == "no plan in the runner's record"
    here = local.priced_here()
    for priced_on, said in (({**here, "commit": "0" * 40, "uncommitted": False}, "the code moved"),
                            ({**here, "per_unit_sha256": "0" * 64, "uncommitted": False}, "per-unit prices"),
                            ({**here, "uncommitted": True}, "code not committed"), (None, "before the price")):
        a_holes_price(world, milestones=milestones(), priced_on=priced_on)
        world.source.refresh()
        price = world.source.holes_price()
        remake = cockpit.remake(price)
        assert remake["low"] is None and said in remake["why"], (said, remake)
        assert cockpit.measured_prices(price) == (None, None)
    assert said in unescape(signed_in().get("/").content.decode())  # the why is the hover text


def test_stats_are_numbers_against_the_one_stop_and_unknown_stays_grey(world, settings, tmp_path, monkeypatch):
    from score.dashboard.launch.backend import Billed
    from score.dashboard.tests.fixture import FakeBackend
    a_holes_finding(world, settings, tmp_path)
    a_holes_price(world)
    world.source.refresh()
    a_month(monkeypatch)
    monkeypatch.setattr(FakeBackend, "bill", [Billed("closeup@alpha", 2.5, 10.0, "2026-10-03T10:00:00"),
                                              Billed("closeup@alpha", 1.0, 5.0, "2026-10-05T10:00:00"),
                                              Billed("closeup@alpha", 9.0, 5.0, "2026-09-30T10:00:00")])
    html = signed_in().get("/stats/").content.decode()
    cards = dict(re.findall(r'<div class="num-label">(?:<i [^>]*></i>)?([^<]+)</div>\s*<div class="num-value[^"]*"'
                            r"[^>]*>(.*?)</div>", html, re.S))
    assert cards["Cloud compute"] == "<small>EUR</small> 12.50"  # each line by its own label
    assert cards["Model calls"] == "unknown" and cards["Total / stop"] == "unknown"  # a partial count is no figure
    assert cards["Measured prices"] == "1<small> / 2</small>"  # the close-up measured, the sound guessed
    assert cards["Places complete"] == "1<small> / 2</small>"  # beta, checked with no gap
    assert [cards[label] for label in ("lost", "route", "missing", "failing")] == ["0", "1", "2", "1"]
    assert 'title="2026-10-03: EUR 2.50"' in html and 'title="2026-10-05: EUR 1.00"' in html
    assert "2026-09-30" not in html  # last month's run is not this month's spend
    main = html[html.index("<main>"):]
    assert "<form" not in main and "<button" not in main  # numbers only, no controls


def test_the_spend_timeline_is_every_day_of_the_month_so_far():
    from score.dashboard.launch.backend import Billed
    from score.dashboard.pages import cockpit
    days = cockpit.timeline([Billed("a", 2.0, None, "2026-10-02T09:00:00"), Billed("b", 1.0, None, "2026-10-02T20:00"),
                             Billed("c", 1.5, None, "2026-10-04T01:00:00")], "2026-10", datetime.date(2026, 10, 5))
    assert [(day["day"][-2:], day["euros"], day["height"]) for day in days] == [
        ("01", 0.0, 0), ("02", 3.0, 100), ("03", 0.0, 0), ("04", 1.5, 50), ("05", 0.0, 0)]
    assert cockpit.timeline([], "2026-10") == []


def test_the_place_screen_is_its_3d_view_its_scene_tree_and_a_side_panel(world, settings, tmp_path):
    a_holes_finding(world, settings, tmp_path)
    world.source.refresh()
    html = signed_in().get("/place/alpha/").content.decode()
    assert 'src="/view/alpha?holes=1&amp;embed=1"' in html and '<aside class="side-panel" id="panel" hidden>' in html
    assert 'data-opens="panel" data-title="lamp" data-state="2 missing" data-tone="hole-missing"' in html
    assert 'data-title="crate_1" data-state="1 failing" data-tone="hole-gate"' in html
    assert re.search(r'<span class="node-label" data-v>Holes</span><span class="node-count" data-v>2</span>', html)
    assert NODE.search(outside_details(html)) is None


def test_the_buy_screen_has_no_stop_control_and_the_books_buttons_while_paid_work_is_refused(world, monkeypatch):
    a_month(monkeypatch)
    client = signed_in()
    html = client.get("/buy/").content.decode()
    assert "data-step2" in html and 'href="/basket/"' in html and "/api/money/read-back" not in html
    a_month(monkeypatch, paid_refused="the month's books are lost")
    html = client.get("/buy/").content.decode()
    assert 'data-post="/api/money/read-back"' in html and 'data-post="/api/money/books-figure"' in html
    assert "/api/money/read-back" not in signed_in("guest").get("/buy/").content.decode()  # the owner's own buttons
