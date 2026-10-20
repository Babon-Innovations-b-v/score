"""A walk through the creator cockpit as the owner takes it, with no JavaScript: the environment overview (every place
with its holes by kind, the steps that block every paid step, then what to buy first by how many holes have each
paid step in their chain, the code work grouped, a lost input read by two places and the environment), a place (its holes tree, its groups and each line's source and 3D link), the viewer framing one hole,
and the basket item a hole line links."""
import json
import re
from html import unescape

import pytest

from score.dashboard.tests.pages_test import (FORECAST, NODE, PLAN_WORK, a_holes_finding, a_holes_price, outside_details,
                                              signed_in)

pytestmark = pytest.mark.django_db
REFUSED = ("the month's books are lost (books.json): paid work is refused until the owner gives his month's figure "
           "(score spend --owners-month EUR) or the month ends")


@pytest.fixture
def cockpit(world, settings, tmp_path, monkeypatch):
    """The fixture environment with alpha's holes priced, and a spend read with no stop and the books not known."""
    from score.dashboard.pages import actions
    from score.dashboard.state.models import Spend
    a_holes_finding(world, settings, tmp_path)
    a_holes_price(world)
    world.source.refresh()
    monkeypatch.setattr(actions, "spend", lambda: Spend(spent=0.0, reserved=0.0, as_of="2026-10-19T08:00:00+00:00",
                                                        paid_refused=REFUSED))
    return world


def section(html, label):
    return re.search(rf'<section[^>]*aria-label="{label}".*?</section>', html, re.S).group(0)


def test_the_overview_lists_every_place_its_holes_by_kind_and_what_to_buy_first(cockpit):
    html = signed_in().get("/").content.decode()
    places = section(html, "every place")
    assert places.count('href="/place/') == 2  # alpha and beta, one row each
    alpha = re.search(r'<tr>\s*<td data-value="[^"]*"><a href="/place/alpha/">.*?</tr>', places, re.S).group(0)
    cells = re.findall(r'<td class="num"[^>]*>([^<]*)</td>', alpha)
    assert cells[:5] == ["4", "2", "1", "1", "0"], cells  # holes; not made, failing, route steps, lost inputs
    assert "route steps not done" in alpha and "This place&#x27;s plan is not accepted" in alpha
    assert "2.00" in alpha and "3.00" in alpha and "1.00" in alpha  # likely, high and the guess, apart
    beta = re.search(r'<a href="/place/beta/">.*?</tr>', places, re.S).group(0)
    assert "not checked" in beta or "no holes found" in beta
    first = unescape(section(html, "what to buy first"))
    blockers = re.findall(r"<li><b>(.*?)</b>", re.search(r'<ol class="blockers">.*?</ol>', first, re.S).group(0))
    assert blockers[:2] == ["Set a stop.", "The month's books are not known."], blockers
    # every hole in a paid chain waits on alpha's plan: the section says so first, then the code work
    assert first.index("No paid step fills a hole yet.") < first.index('<ol class="code-first">') < first.index(
        '<ol class="blockers">')
    assert ("<b>Door kits: a concept view and a plan</b>: at 1 place, where 3 holes with a paid chain wait on it "
            "(EUR 2.00 to 3.00 measured, EUR 1.00 guessed in those chains)") in first
    assert re.search(r'<details class="fold"><summary>Every paid step \(2\), by how many holes have it in their '
                     r'chain</summary>\s*<ol class="buy-list">', first)  # every step folded, none shown open
    assert REFUSED in first  # the refusal in its details fold
    assert "score spend --read-back" not in first  # only the commands the refusal names
    assert '<pre class="command">.venv/bin/python -m score spend --owners-month EUR</pre>' in first  # as it names it
    buys = re.findall(r'<ol class="buy-list".*?</ol>', first, re.S)[0]
    # the sound is in the chains of the lamps and of the crate, the close-up in the lamps' only: a count, not a price
    # each step by its place's title on the board, never its key
    sound, closeup = buys.index("The sound step of The alpha look"), buys.index("The close-ups step of The alpha look")
    assert sound < closeup
    # alpha waits on its plan, a route step: every hole there waits on it first
    assert ('<li id="buy-sound-alpha">The sound step of The alpha look: in the chain of 3 holes at 1 place, all of '
            "them at a place that waits on a lost input or a route step first · EUR 1.00 guessed, not a price · in no "
            "basket item yet") in buys
    assert ("The close-ups step of The alpha look: in the chain of 2 holes at 1 place, all of them at a place that "
            "waits on a lost input or a route step first · likely EUR 2.00, high EUR 3.00 (per unit × forecast) · "
            "<a href=\"/basket/item/alpha-pieces/\">its basket item</a>") in buys
    assert "unblocks" not in first
    work = section(html, "code work no stage does yet")
    assert "Door kits: a concept view and a plan</b>: 1 hole at 1 place" in work and PLAN_WORK + " (1 hole)" in work
    assert html.index('aria-label="what to buy first"') < html.index('aria-label="code work no stage does yet"')
    total = unescape(section(html, "what every place still needs"))
    # the one figure leads; the measured share alone is never said first as if it were the total
    assert "The runner's price today" not in total and "likely EUR 2, high EUR 3 measured by" not in total
    assert total.index("What the runner can price today") < total.index("To fill what the runner can")
    assert ("2 not made yet, 1 made but failing a check, 1 step of the route not done, 0 inputs lost (each once, "
            "however many places read it).") in total  # route steps and lost inputs apart
    # what the runner prices today, its measured share by its basis; the plan's code work brings no paid work
    assert ("<b>What the runner can price today: EUR 3.00 to EUR 4.00</b>, of which EUR 2.00 to 3.00 measured by per "
            'unit × forecast (1 of 2 paid steps) and EUR 1.00 <span class="unknown">guessed, not a price</span> '
            "(1 step).") in total
    assert "Not priced yet" not in total
    assert "In all, to complete" not in total
    tiles = re.findall(r'<a class="tile-foot" href="/place/(\w+)/">(.*?)</a>', html, re.S)
    alpha_tile = dict(tiles)["alpha"]
    assert "4 holes, worst: route steps not done" in alpha_tile and "steps: " in alpha_tile, alpha_tile
    assert re.search(r'<td data-value="1"><span class="status bad">route steps not done', alpha)  # sorts by rank
    assert NODE.search(outside_details(html)) is None


def test_the_first_load_says_set_a_stop_and_only_the_books_not_read_yet(cockpit, monkeypatch):
    """Before the spend read returns: the money card's stop decides "Set a stop", the books are said as not read."""
    from score.dashboard.pages import actions
    from score.dashboard.state.models import Spend
    monkeypatch.setattr(actions, "spend", lambda: Spend(note="the month's spend is being read"))
    first = unescape(section(signed_in().get("/").content.decode(), "what to buy first"))
    blockers = re.findall(r"<li><b>(.*?)</b>", re.search(r'<ol class="blockers">.*?</ol>', first, re.S).group(0))
    assert blockers[:2] == ["Set a stop.", "The month's books are not read yet."], blockers
    assert "not known yet" not in first


def test_a_place_shows_its_holes_tree_its_groups_and_each_lines_source(cockpit):
    html = signed_in().get("/place/alpha/").content.decode()
    assert 'href="/view/alpha?holes=1"' in html and "Open in 3D: its holes" in html  # no web copy: the holes view
    assert "Open in 3D: not made yet" not in html
    tree = re.search(r'<ul class="tree">.*?</ul>\s*</div></details>', html, re.S).group(0)
    assert re.search(r"/alpha</span>\s*<span class=\"soft small\">holes below: 4</span>", tree)
    assert re.search(r'<a href="#hole-missing:lamp_1">lamp</a>\s*<span class="soft small">holes below: 2</span>'
                     r'\s*<span class="badge missing">2</span>', tree)
    assert 'class="badge gate">1<' in tree and 'class="badge route">1<' in tree
    assert "The holes layer only" in html
    for title in ("Steps of the route not done (1)", "Not made yet (2)", "Made, but failing a check (1)"):
        assert f"<h3>{title}</h3>" in html, title
    assert "If left, the place cannot be complete while a row of its scene inventory has no object." in html
    for label in ("inventory row lamp", "gate complete/painted", "route step plan"):
        assert f'<span class="source small">{label}</span>' in html, label
    lamp = re.search(r'<li id="hole-missing:lamp_1" data-anchor="hole-missing:lamp_1">(.*?)</li>', html, re.S).group(1)
    assert 'href="/view/alpha?holes=1&amp;hole=missing%3Alamp_1"' in lamp
    assert "Needs the close-ups step of The alpha look; its chain is 3 steps, 2 of them paid." in lamp  # its title, as on the board
    assert "Every paid step its holes' chains need, each once: likely EUR 2.00, high EUR 3.00 measured" in html
    assert "The whole environment" not in html
    assert NODE.search(outside_details(html)) is None


def view_data(html):
    return json.loads(re.search(r'<script id="view3d-data" type="application/json">(.*?)</script>', html,
                                re.S).group(1))


def test_the_viewer_frames_one_hole_with_or_without_a_web_copy(cockpit):
    client = signed_in()
    answer = client.get("/view/alpha?holes=1&hole=missing:lamp_2")
    assert answer.status_code == 200
    given = view_data(answer.content.decode())
    assert given["hole"] == "missing:lamp_2" and given["holes_only"] is True
    assert "missing:lamp_2" in [mark["id"] for mark in given["marks"]]
    page = unescape(answer.content.decode())
    assert "No 3D web copy of this place yet: only its holes are drawn" in page
    assert ('Framed: A lamp should be in the alpha but nothing is made for it yet. '
            '<a href="/place/alpha/#hole-missing:lamp_1">') in page  # its line: the row's first lamp
    assert 'class="mark-key framed"' in page and 'class="mark-key gate"' in page  # the crate's gate has a box
    assert "work once a 3D web copy of this place exists" in page
    # a click on a box names its hole: each mark carries its sentence and its line; the corner button is the holes'
    lamp = next(mark for mark in given["marks"] if mark["id"] == "missing:lamp_2")
    assert lamp["sentence"].startswith("A lamp should be in the alpha") and lamp["url"] == (
        "/place/alpha/#hole-missing:lamp_1"), lamp
    assert 'id="hole-picked"' in page and ">Back to all holes</button>" in page and "Look at what changes" not in page
    (cockpit.root / "web/alpha").mkdir(parents=True)
    (cockpit.root / "web/alpha/alpha.json").write_text(json.dumps({
        "place": "alpha", "from_output": cockpit.outputs["assembly@alpha"], "made_at": "2026-10-18T12:00:00Z",
        "objects": [], "bytes": 10, "light_bytes": 5, "triangles": 12}))
    given = view_data(client.get("/view/alpha?holes=1&hole=missing:lamp_2").content.decode())
    assert given["holes_only"] is False and given["hole"] == "missing:lamp_2"


def test_the_basket_item_a_hole_links_opens(cockpit):
    client = signed_in()
    html = client.get("/place/alpha/").content.decode()
    link = re.search(r'href="(/basket/item/[^"]+/)"', html).group(1)
    assert client.get(link).status_code == 200


EARTH = "earth seed lost: a seed row that exports each place's base; terrain and every row after it stay blocked"
PROP_DATA = "prop data for alpha: a props file"


def a_lost_input(world):
    """The earth seed's usd-r3 lost, read by alpha, beta and the environment's own nodes: alpha's findings with it
    added, beta's with only it, the world pseudo-place's."""
    found = json.loads((world.root / "props/work/checks/holes/alpha/findings.json").read_text())
    lost = {"id": "place:lost:earth-seed:usd-r3", "rule": "place", "prim": None, "kind": None,
            "sentence": "lost input usd-r3", "picture": None, "row": None, "gates": [], "source": "inputs",
            "node": None, "work": EARTH, "placed": None, "low": None, "high": None}
    for place, outputs, holes in (("alpha", found["outputs"], found["findings"] + [lost]),
                                  ("beta", {"assembly@beta": world.outputs["assembly@beta"]}, [lost]),
                                  ("world", {}, [lost])):
        folder = world.root / "props/work/checks/holes" / place
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "findings.json").write_text(json.dumps({"place": place, "outputs": outputs, "findings": holes}))


def test_a_lost_input_blocks_the_places_reading_it_and_the_prop_data_is_said_apart(cockpit):
    a_lost_input(cockpit)
    a_holes_price(cockpit, unfillable=[{"work": PLAN_WORK, "holes": 1}, {"work": EARTH, "holes": 1}],
                  after_work={"alpha": {"work": PROP_DATA, "holes": 2, "models": 1, "in_chains": [],
                                        "nodes": {"pixal@alpha": FORECAST}}})
    cockpit.source.refresh()
    html = signed_in().get("/").content.decode()
    first = unescape(section(html, "what to buy first"))
    assert ("<b>The earth seed is lost.</b> Blocks 2 places (1 input). 1 needs code work: Earth seed lost: a seed "
            "row that exports each place's base.") in first
    places = section(html, "every place")
    alpha = re.search(r'<a href="/place/alpha/">.*?</tr>', places, re.S).group(0)
    assert re.findall(r'<td class="num"[^>]*>([^<]*)</td>', alpha)[:5] == ["5", "2", "1", "1", "1"]
    assert "a lost input" in alpha
    beta = re.search(r'<a href="/place/beta/">.*?</tr>', places, re.S).group(0)
    assert '<span class="unknown">no price</span>' in beta and "0.00" not in beta  # its one hole has no stage
    assert re.search(r'<td class="num" data-value="1">1</td>', beta)  # one hole not priced
    work = unescape(section(html, "code work no stage does yet"))
    assert "Earth seed lost: a seed row that exports each place's base</b>: 1 lost input at 2 places" in work
    total = unescape(section(html, "what every place still needs"))
    assert "After the prop data code work, more: EUR 2.00 to EUR 3.00, of which EUR 2.00 to 3.00 measured" in total
    # one figure with the prop route after its code work in it: today's 3 to 4 and the route's 2 to 3
    assert ("<b>Both together, the prop route after its code work in it: EUR 5.00 to EUR 7.00</b>, of which EUR 4.00 "
            "to 6.00 measured by per unit × forecast (2 of 3 paid steps)") in total
    page = signed_in("other").get("/place/beta/").content.decode()
    assert "<h3>Lost inputs (1)</h3>" in page and '<span class="source small">lost input usd-r3</span>' in page
    assert "No stage can fill this yet: Earth seed lost: a seed row that exports each place&#x27;s base" in page
    assert "No price</span>: no hole of this place has a paid step the runner priced" in page
    assert "1 hole no stage can fill yet" in page


def test_a_place_never_checked_has_no_price_not_nothing_to_pay():
    from types import SimpleNamespace
    from score.dashboard.state import holes
    price = SimpleNamespace(stale=None, not_checked=["gamma"], not_current=[], chains={}, nodes={})
    assert holes.place_row("gamma", [], price)["money"] is None
    assert holes.place_row("gamma", [], price)["rank"] == len(holes.KINDS) + 1


def test_a_lost_inputs_item_keeps_its_colons():
    from types import SimpleNamespace
    from score.dashboard.pages import present
    from score.dashboard.state import plain
    hole = SimpleNamespace(id="place:lost:data:surfaces/launch.json:bake entry far_rocket_1", rule="place")
    assert plain.lost_item(hole.id) == "surfaces/launch.json:bake entry far_rocket_1"
    assert present.source_label(hole) == "lost input surfaces/launch.json:bake entry far_rocket_1"


def a_shared_step(world):
    """beta's holes check with one lamp the close-up fills, and the runner's price with the ground (`terrain`, the
    environment's one node, only guessed) in the chains of both places, so it is in both rows and once in the total."""
    from score.dashboard.tests.pages_test import GUESSED
    folder = world.root / "props/work/checks/holes/beta"
    folder.mkdir(parents=True, exist_ok=True)
    lamp = {"id": "missing:lamp_1", "rule": "missing", "kind": "generate", "sentence": "a lamp: nothing made for it yet",
            "picture": None, "row": "lamp", "gates": [], "source": "inventory", "node": "closeup@beta", "work": None,
            "placed": "spot", "prim": "/beta/Holes/lamp_1", "low": [0, 0, 0], "high": [1, 1, 1]}
    (folder / "findings.json").write_text(json.dumps({"place": "beta", "outputs": {
        "assembly@beta": world.outputs["assembly@beta"]}, "findings": [lamp]}))
    a_holes_price(world, nodes={"closeup@alpha": FORECAST, "sound@alpha": GUESSED, "terrain": GUESSED,
                                "closeup@beta": FORECAST},
                  chains={"alpha": {"closeup@alpha": ["closeup@alpha", "complete@alpha", "sound@alpha", "terrain"],
                                    "complete@alpha": ["complete@alpha", "sound@alpha", "terrain"]},
                          "beta": {"closeup@beta": ["closeup@beta", "terrain"]}},
                  holes={"alpha": {}, "beta": {}})


def test_a_step_two_places_share_is_in_both_rows_once_in_the_total_and_the_page_says_so(cockpit):
    a_shared_step(cockpit)
    cockpit.source.refresh()
    html = unescape(signed_in().get("/").content.decode())
    total = section(html, "what every place still needs")
    assert "<b>What the runner can price today: EUR 6.00 to EUR 8.00</b>" in total  # 2+2 to 3+3 measured, 1+1 guessed
    places = section(html, "every place")
    rows = re.findall(r'<a href="/place/\w+/">.*?</tr>', places, re.S)
    guessed = [float(re.findall(r'<td class="num" title="guessed, not a price">([^<]*)</td>', row)[0]) for row in rows]
    assert sum(guessed) == 3.0  # the ground's guess in both rows: the column adds up to more than the total's 2
    note = places[:places.index("<table")]
    assert ("A paid step several places share is counted in each of their rows and only once in the total above"
            in note)
    assert ("Shared by two or more places: 1 paid step, likely EUR 0.00, high EUR 0.00 measured, plus EUR 1.00 "
            '<span class="unknown">guessed, not a price</span>.') in note
    own = dict(re.findall(r'<a href="/place/(\w+)/">.*?<td class="num own"[^>]*>([^<]*)</td>', places, re.S))
    assert own == {"alpha": "2.00 to 3.00, 1.00 guessed", "beta": "2.00 to 3.00"}, own  # the ground in neither


def test_a_holes_check_run_again_shows_at_once_not_after_the_index(cockpit):
    import os
    client = signed_in()
    before = unescape(section(client.get("/").content.decode(), "what every place still needs"))
    assert "What the runner can price today: EUR 3.00 to EUR 4.00" in before
    findings = cockpit.root / "props/work/checks/holes/alpha/findings.json"
    price = cockpit.root / "props/work/checks/holes-price/world1.json"
    findings.write_text(findings.read_text())  # the holes check ran again; the store's index is not rebuilt
    later = price.stat().st_mtime + 2
    os.utime(findings, (later, later))
    after = unescape(section(client.get("/").content.decode(), "what every place still needs"))
    assert "What the runner can price today" not in after
    assert "the holes check ran again at 1 place since the price was made" in after
