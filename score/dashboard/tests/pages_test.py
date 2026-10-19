"""Every page renders for the owner from the fixture world, with its pictures and words; a signed-out visitor is sent
to the sign-in page; node ids stay inside the details fold; every POST needs its CSRF token."""
import re

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

pytestmark = pytest.mark.django_db
PAGES = ["/", "/place/alpha/", "/place/beta/", "/place/alpha/step/closeup/", "/place/beta/step/assembly/",
         "/world/step/terrain/", "/basket/", "/runs/", "/requests/", "/picks/alpha", "/view/alpha"]
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


def test_the_board_shows_each_place_once_with_its_picture_and_one_status(world):
    html = signed_in().get("/").content.decode()
    text = outside_details(html)
    assert "unassigned" not in text.lower() and "Not given a look yet" in text
    assert html.count('class="tile"') == 2 and html.count("/thumbs/") >= 2  # each place's best picture
    assert "complete apart from" not in text and "fault report" not in text
    assert re.search(r'class="status (bad|review|new|done|idle)"', html)
    assert "This month" in text and ("not known yet" in text or "EUR" in text)


def test_the_board_shows_no_basket_bar_while_nothing_waits(world):
    page = signed_in().get("/").content.decode()
    assert 'class="basket-bar"' not in page and "wait for you" not in page


def test_the_place_page_shows_the_usd_index_and_faults(world):
    html = signed_in().get("/place/beta/").content.decode()
    assert "beta.usda" in html and "light" in html and "assets" in html
    assert "placeholders" in html and "beta: no lamp model" in html
    assert "<video" in html and "/files/" in html


def test_a_known_gap_shows_its_picture_and_opens_its_step(world):
    html = signed_in().get("/place/beta/").content.decode()
    problems = html[html.index('class="problems bd-problems"'):html.index("</article>", html.index('class="problems'))]
    gap = next(chunk for chunk in problems.split('class="problem"') if "known gap" in chunk)
    assert gap.startswith(' href="/place/beta/step/assembly/"') and "/thumbs/" in gap


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


def test_the_place_page_says_what_is_not_done_and_scrubs_its_film(world):
    html = signed_in().get("/place/beta/").content.decode()
    assert "Not done for this place" in html and "beta: no lamp model" in html
    assert 'data-fps="24"' in html


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
    assert 'href="/view/alpha"' in client.get("/place/alpha/").content.decode()


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


def test_the_place_page_lists_a_standalone_checks_findings_as_problems(world):
    a_check_finding(world, world.outputs["assembly@beta"])
    html = signed_in().get("/place/beta/").content.decode()
    assert "3 models (crate) finish not from the library" in html and "library check" in html


def test_a_check_finding_on_an_assembly_no_longer_accepted_is_not_listed(world):
    a_check_finding(world, "0" * 64)
    html = signed_in().get("/place/beta/").content.decode()
    assert "finish not from the library" not in html


MEASURED = {"likely_euros": 2.0, "high_euros": 3.0, "likely_minutes": 10.0, "high_minutes": 20.0, "runs": 4,
            "cards": 1}
ROUGH = "a rough-model stage: the prop pipeline on the whole concept, a row in score/stages STAGES"


def a_holes_finding(world, settings, tmp_path):
    """The holes check's findings.json for alpha over its accepted assembly: two objects of a row the close-up step
    fills (a basket item carries it, measured), a gate on a step nothing buys now, and the rough model no stage
    makes yet; the basket made with that one item."""
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
        {"id": "place:rough-model", "rule": "place", "prim": "/alpha", "kind": None,
         "sentence": "this place has no rough model", "picture": None, "row": None, "gates": [], "source": "route",
         "node": None, "work": ROUGH, "placed": None, "low": None, "high": None}]}))
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
        "unfillable": [{"work": ROUGH, "holes": 1}], "outside": [], "not_current": [], "not_checked": [], **more}))


def test_the_place_page_lists_each_holes_chain_priced_by_the_runner(world, settings, tmp_path):
    from score.dashboard.state import holes
    items = a_holes_finding(world, settings, tmp_path)
    a_holes_price(world)
    world.source.refresh()
    html = signed_in().get("/place/alpha/").content.decode()
    assert "A lamp should be in the alpha but nothing is made for it yet (2 of them)." in html
    lamp = re.search(r"\(2 of them\)\.(.*?)</li>", html, re.S).group(1)
    assert "/basket/item/alpha-pieces/" in lamp and "2 paid steps in its chain" in lamp
    assert "likely EUR 2.00, high EUR 3.00 (1 step)" in lamp and "guessed, not a price: EUR 1.00 (1 step)" in lamp
    rough = re.search(r"<li>This place has no rough model\.(.*?)</li>", html, re.S).group(1)
    assert "No stage can fill this yet: " + ROUGH in rough and "EUR" not in rough
    assert "sound@alpha: not measured yet, guess EUR 1.00 (score/stages/__init__.py:243)" in html  # in details
    assert NODE.search(outside_details(html)) is None
    total = holes.environment(world.source.holes_total(), world.source.holes_price())
    assert total["holes"] == 4 and total["unfillable"] == [{"work": ROUGH, "holes": 1}]
    assert total["sums"]["bases"] == [{"basis": "per unit × forecast", "label": holes.BASES[2][1], "nodes": 1,
                                       "likely": 2.0, "high": 3.0}]
    assert total["sums"]["guessed"] == {"euros": 1.0, "nodes": 1, "sources": [
        {"at": "score/stages/__init__.py:243", "euros": 1.0, "nodes": 1}]}
    assert total["not_in_basket"] == 2  # the basket's file was not read: no items passed
    assert holes.environment(world.source.holes_total(), world.source.holes_price(), items)["not_in_basket"] == 1
    board = signed_in("other").get("/").content.decode()
    assert "4 holes" in board and "likely EUR 2.00, high EUR 3.00 (1 step)" in board and ROUGH + " (1 hole)" in board
    assert "1 of these paid steps is in no basket item yet" in board  # the sound: the basket carries the close-up


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
    assert total.counts == {"place": 2}, total
    assert total.unfillable == ["earth seed lost", "take lost"], total


def test_a_stale_holes_price_shows_no_total(world, settings, tmp_path):
    import os
    import time
    a_holes_finding(world, settings, tmp_path)
    a_holes_price(world)
    later = time.time() + 60
    os.utime(world.root / "props/work/checks/holes/alpha/findings.json", (later, later))  # the check ran again
    world.source.refresh()
    board = signed_in().get("/").content.decode()
    section = re.search(r'<section class="money-card holes-total".*?</section>', board, re.S).group(0)
    assert "No total" in section and "stale" in section and "EUR 2.00" not in section
    html = signed_in("other").get("/place/alpha/").content.decode()
    assert "Its price is stale" in html and "paid steps in its chain" not in html


def test_a_holes_price_made_on_other_code_or_other_per_unit_prices_shows_no_total(world, settings, tmp_path):
    from score.dashboard.state import holes, local
    a_holes_finding(world, settings, tmp_path)
    here = local.priced_here()
    for priced_on, said in (({**here, "commit": "0" * 40, "uncommitted": False}, "the code moved"),
                            ({**here, "per_unit_sha256": "0" * 64, "uncommitted": False}, "per-unit prices"),
                            ({**here, "uncommitted": True}, "code not committed"), (None, "before the price")):
        a_holes_price(world, priced_on=priced_on)
        world.source.refresh()
        total = holes.environment(world.source.holes_total(), world.source.holes_price())
        assert total["sums"] is None and said in total["stale"] and said in total["words"], (said, total)


def test_the_holes_total_names_what_it_could_not_price_and_sums_the_prop_route_after_its_work(world, settings,
                                                                                               tmp_path):
    from score.dashboard.state import holes
    a_holes_finding(world, settings, tmp_path)
    route = {"work": "prop data for beta: data/props/beta.json", "holes": 3, "models": 2, "in_chains": [],
             "nodes": {"pixal@beta": {**FORECAST, "units": 2}, "closeup@beta": GUESSED}}
    a_holes_price(world, after_work={"beta": route}, outside=[{"node": "ship_kit@beta", "holes": 4}],
                  not_checked=["world"])
    world.source.refresh()
    total = holes.environment(world.source.holes_total(), world.source.holes_price())
    assert total["outside"] == [{"node": "ship_kit@beta", "holes": 4}] and total["not_checked"] == ["world"]
    assert total["after_work"]["sums"]["bases"] == [{"basis": "per unit × forecast", "label": holes.BASES[2][1],
                                                     "nodes": 1, "likely": 2.0, "high": 3.0}]
    assert total["after_work"]["sums"]["guessed"]["euros"] == 1.0
    assert "1 node outside the stage table" in total["words"] and "1 place never checked" in total["words"]
    board = signed_in("other").get("/").content.decode()
    section = re.search(r'<section class="money-card holes-total".*?</section>', board, re.S).group(0)
    assert "once each place's prop data is written" in section and "the holes check never ran: world" in section
    assert "1 ship kit step outside the stage table" in section
    assert NODE.search(outside_details(section)) is None  # the ship kit's node only inside the details


def test_the_holes_total_keeps_each_basis_apart_and_a_shared_node_once():
    from score.dashboard.state import holes
    from score.dashboard.state.models import HolesPrice, HolesTotal
    total = HolesTotal(counts={"missing": 2, "gate": 1})
    price = HolesPrice(made_at="2026-10-19T20:00:00+00:00", nodes={
        "pixal@alpha": {**MEASURED, "basis": "measured runs"},
        "bake@alpha": {**MEASURED, "basis": "per unit × counted"},
        "lists@alpha": {**FORECAST},
        "sound@alpha": GUESSED, "sound@beta": {**GUESSED, "guess_euros": 1.5},
        "film@alpha": {**GUESSED, "guess_euros": None, "guess_from": None}},
        chains={"alpha": {"pixal@alpha": ["pixal@alpha", "lists@alpha"], "lists@alpha": ["lists@alpha"]}})
    found = holes.environment(total, price)
    assert [(entry["basis"], entry["likely"], entry["high"], entry["nodes"]) for entry in found["sums"]["bases"]] == [
        ("measured runs", 2.0, 3.0, 1), ("per unit × counted", 2.0, 3.0, 1), ("per unit × forecast", 2.0, 3.0, 1)]
    assert found["sums"]["guessed"]["euros"] == 2.5 and found["sums"]["guessed"]["nodes"] == 2
    assert found["sums"]["unknown"] == ["film@alpha"]
    # two holes whose chains share lists@alpha: each chain counts it, the environment once
    pixal = holes.hole_chain(type("Hole", (), {"node": "pixal@alpha"}), price, "alpha")
    lists = holes.hole_chain(type("Hole", (), {"node": "lists@alpha"}), price, "alpha")
    assert "2 paid steps in its chain" in pixal["words"] and "1 paid step in its chain" in lists["words"]
    assert all("lists@alpha" in [row["node"] for row in chain["rows"]] for chain in (pixal, lists))
    forecast = next(entry for entry in found["sums"]["bases"] if entry["basis"] == "per unit × forecast")
    assert (forecast["nodes"], forecast["likely"]) == (1, 2.0), forecast


def test_the_viewer_outlines_the_holes_when_asked(world, settings, tmp_path):
    import json
    a_holes_finding(world, settings, tmp_path)
    (world.root / "web/alpha").mkdir(parents=True)
    (world.root / "web/alpha/alpha.json").write_text(json.dumps({
        "place": "alpha", "from_output": world.outputs["assembly@alpha"], "made_at": "2026-10-18T12:00:00Z",
        "objects": [], "bytes": 10, "light_bytes": 5, "triangles": 12}))
    client = signed_in()
    assert 'href="/view/alpha?holes=1"' in client.get("/place/alpha/").content.decode()

    def marks(page):
        html = client.get(page).content.decode()
        return json.loads(re.search(r'<script id="view3d-data" type="application/json">(.*?)</script>', html,
                                    re.S).group(1))["marks"]
    assert marks("/view/alpha") == []
    assert marks("/view/alpha?holes=1") == [
        {"low": [0, 0, 0], "high": [1, 1, 1], "kind": "missing"}, {"low": [2, 0, 0], "high": [3, 1, 1], "kind": "missing"},
        {"low": [4, 0, 0], "high": [5, 1, 1], "kind": "gate"}]


def test_holes_are_not_repeated_among_the_check_findings(world, settings, tmp_path):
    a_holes_finding(world, settings, tmp_path)
    assert [finding.check for finding in world.source.check_findings("alpha")] == []
    assert [hole.id for hole in world.source.holes("alpha")][:1] == ["missing:lamp_1"]
