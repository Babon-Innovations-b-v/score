"""A walk through the creator cockpit as the owner takes it, with no JavaScript: the environment overview (every place
with its holes by kind, the steps that block every paid step, then what to buy first by holes unblocked, the code
work grouped), a place (its holes tree, its groups and each line's source and 3D link), the viewer framing one hole,
and the basket item a hole line links."""
import json
import re
from html import unescape

import pytest

from score.dashboard.tests.pages_test import NODE, ROUGH, a_holes_finding, a_holes_price, outside_details, signed_in

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
    assert "route steps not done" in alpha and "This place has no rough model" in alpha
    assert "2.00" in alpha and "3.00" in alpha and "1.00" in alpha  # likely, high and the guess, apart
    beta = re.search(r'<a href="/place/beta/">.*?</tr>', places, re.S).group(0)
    assert "not checked" in beta or "no holes found" in beta
    first = unescape(section(html, "what to buy first"))
    blockers = re.findall(r"<li><b>(.*?)</b>", first)
    assert blockers[:2] == ["Set a stop.", "The month's books are not known."], blockers
    assert "score spend --read-back" in first and REFUSED in first  # the refusal in its details fold
    assert '<pre class="command">.venv/bin/python -m score spend --owners-month EUR</pre>' in first  # as it names it
    buys = re.findall(r'<ol class="buy-list".*?</ol>', first, re.S)[0]
    # the sound is in the chains of the lamps and of the crate, the close-up in the lamps' only: a count, not a price
    sound, closeup = buys.index("The sound step of the alpha"), buys.index("The close-ups step of the alpha")
    assert sound < closeup
    assert ("The sound step of the alpha: unblocks 3 holes in 1 place · EUR 1.00 guessed, not a price · in no basket "
            "item yet") in buys
    assert ("The close-ups step of the alpha: unblocks 2 holes in 1 place · likely EUR 2.00, high EUR 3.00 "
            "(per unit × forecast) · <a href=\"/basket/item/alpha-pieces/\">its basket item</a>") in buys
    total = section(html, "what every place still needs")
    assert "A rough-model stage</b>: unblocks 1 hole at 1 place" in total and ROUGH + " (1 hole)" in total
    assert "To complete: likely EUR 2, high EUR 3 measured by per unit × forecast, plus EUR 1 guessed" in total
    assert NODE.search(outside_details(html)) is None


def test_a_place_shows_its_holes_tree_its_groups_and_each_lines_source(cockpit):
    html = signed_in().get("/place/alpha/").content.decode()
    tree = re.search(r'<ul class="tree">.*?</ul>\s*</div></details>', html, re.S).group(0)
    assert re.search(r"/alpha</span>\s*<span class=\"soft small\">holes below: 4</span>", tree)
    assert re.search(r'<a href="#hole-missing:lamp_1">lamp</a>\s*<span class="soft small">holes below: 2</span>'
                     r'\s*<span class="badge missing">2</span>', tree)
    assert 'class="badge gate">1<' in tree and 'class="badge route">1<' in tree
    assert "The holes layer only" in html
    for title in ("Steps of the route not done (1)", "Not made yet (2)", "Made, but failing a check (1)"):
        assert f"<h3>{title}</h3>" in html, title
    assert "If left, the place cannot be complete while a row of its scene inventory has no object." in html
    for label in ("inventory row lamp", "gate complete/painted", "route step rough-model"):
        assert f'<span class="source small">{label}</span>' in html, label
    lamp = re.search(r'<li id="hole-missing:lamp_1" data-anchor="hole-missing:lamp_1">(.*?)</li>', html, re.S).group(1)
    assert 'href="/view/alpha?holes=1&amp;hole=missing%3Alamp_1"' in lamp
    assert "Needs the close-ups step of the alpha; its chain is 3 steps, 2 of them paid." in lamp
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
    assert "No 3D web copy of this place yet: only its holes are drawn" in answer.content.decode()
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
