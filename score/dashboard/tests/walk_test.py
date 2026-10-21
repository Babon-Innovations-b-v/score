"""A walk through the creator cockpit as the owner takes it: the viewer framing one gap, a lost input read by two
places and the environment counted once, a step two places share, and a gaps check run again shown at once."""
import json
import re
from html import unescape

import pytest

from score.dashboard.tests.pages_test import (FORECAST, PLAN_WORK, a_gaps_finding, a_gaps_price, signed_in)

pytestmark = pytest.mark.django_db
REFUSED = ("the month's books are lost (books.json): paid work is refused until the owner gives his month's figure "
           "(score spend --owners-month EUR) or the month ends")


@pytest.fixture
def cockpit(world, settings, tmp_path, monkeypatch):
    """The fixture environment with alpha's gaps priced, and a spend read with no stop and the books not known."""
    from score.dashboard.pages import actions
    from score.dashboard.state.models import Spend
    a_gaps_finding(world, settings, tmp_path)
    a_gaps_price(world)
    world.source.refresh()
    monkeypatch.setattr(actions, "spend", lambda: Spend(spent=0.0, reserved=0.0, as_of="2026-10-19T08:00:00+00:00",
                                                        paid_refused=REFUSED))
    return world


def view_data(html):
    return json.loads(re.search(r'<script id="view3d-data" type="application/json">(.*?)</script>', html,
                                re.S).group(1))


def test_the_viewer_frames_one_gap_with_or_without_a_web_copy(cockpit, read):
    client = signed_in()
    answer = client.get("/view/alpha?gaps=1&gap=missing:lamp_2")
    assert answer.status_code == 200
    given = view_data(answer.content.decode())
    assert given["gap"] == "missing:lamp_2" and given["gaps_only"] is True
    assert "missing:lamp_2" in [mark["id"] for mark in given["marks"]]
    page = unescape(answer.content.decode())
    assert ('Framed: A lamp should be in the alpha but nothing is made for it yet. '
            '<a href="/place/alpha/#gap-missing:lamp_1">') in page  # its line: the row's first lamp
    assert 'class="mark-key framed"' in page and 'class="mark-key gate"' in page  # the crate's gate has a box
    # a click on a box names its gap: each mark carries its sentence and its line
    lamp = next(mark for mark in given["marks"] if mark["id"] == "missing:lamp_2")
    assert lamp["sentence"].startswith("A lamp should be in the alpha") and lamp["url"] == (
        "/place/alpha/#gap-missing:lamp_1"), lamp
    (cockpit.root / "web/alpha").mkdir(parents=True)
    (cockpit.root / "web/alpha/alpha.json").write_text(json.dumps({
        "place": "alpha", "from_output": cockpit.outputs["assembly@alpha"], "made_at": "2026-10-18T12:00:00Z",
        "objects": [], "bytes": 10, "light_bytes": 5, "triangles": 12}))
    given = view_data(client.get("/view/alpha?gaps=1&gap=missing:lamp_2").content.decode())
    assert given["gaps_only"] is False and given["gap"] == "missing:lamp_2"


EARTH = "earth seed lost: a seed row that exports each scene's base; terrain and every row after it stay blocked"


def a_lost_input(world):
    """The earth seed's usd-r3 lost, read by alpha, beta and the environment's own nodes: alpha's findings with it
    added, beta's with only it, the world pseudo-place's."""
    found = json.loads((world.root / "props/work/checks/gaps/alpha/findings.json").read_text())
    lost = {"id": "place:lost:earth-seed:usd-r3", "rule": "place", "prim": None, "kind": None,
            "sentence": "lost input usd-r3", "picture": None, "row": None, "gates": [], "source": "inputs",
            "node": None, "work": EARTH, "placed": None, "low": None, "high": None}
    for place, outputs, gaps in (("alpha", found["outputs"], found["findings"] + [lost]),
                                  ("beta", {"assembly@beta": world.outputs["assembly@beta"]}, [lost]),
                                  ("world", {}, [lost])):
        folder = world.root / "props/work/checks/gaps" / place
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "findings.json").write_text(json.dumps({"place": place, "outputs": outputs, "findings": gaps}))


def test_a_place_never_checked_has_no_price_not_nothing_to_pay():
    from types import SimpleNamespace
    from score.dashboard.state import gaps
    price = SimpleNamespace(stale=None, not_checked=["gamma"], not_current=[], chains={}, nodes={})
    assert gaps.place_row("gamma", [], price)["money"] is None
    assert gaps.place_row("gamma", [], price)["rank"] == len(gaps.KINDS) + 1


def a_shared_step(world):
    """beta's gaps check with one lamp the close-up fills, and the runner's price with the ground (`terrain`, the
    environment's one node, only guessed) in the chains of both places, so it is in both rows and once in the total."""
    from score.dashboard.tests.pages_test import GUESSED
    folder = world.root / "props/work/checks/gaps/beta"
    folder.mkdir(parents=True, exist_ok=True)
    lamp = {"id": "missing:lamp_1", "rule": "missing", "kind": "generate", "sentence": "a lamp: nothing made for it yet",
            "picture": None, "row": "lamp", "gates": [], "source": "inventory", "node": "closeup@beta", "work": None,
            "placed": "spot", "prim": "/beta/Gaps/lamp_1", "low": [0, 0, 0], "high": [1, 1, 1]}
    (folder / "findings.json").write_text(json.dumps({"place": "beta", "outputs": {
        "assembly@beta": world.outputs["assembly@beta"]}, "findings": [lamp]}))
    a_gaps_price(world, nodes={"closeup@alpha": FORECAST, "sound@alpha": GUESSED, "terrain": GUESSED,
                                "closeup@beta": FORECAST},
                  chains={"alpha": {"closeup@alpha": ["closeup@alpha", "complete@alpha", "sound@alpha", "terrain"],
                                    "complete@alpha": ["complete@alpha", "sound@alpha", "terrain"]},
                          "beta": {"closeup@beta": ["closeup@beta", "terrain"]}},
                  gaps={"alpha": {}, "beta": {}})




def test_a_lost_input_counts_once_and_marks_every_place_reading_it(cockpit, read):
    a_lost_input(cockpit)
    a_gaps_price(cockpit, unfillable=[{"work": PLAN_WORK, "gaps": 1}, {"work": EARTH, "gaps": 1}])
    cockpit.source.refresh()
    client = signed_in()
    tiles = dict(re.findall(r'<a class="ptile" href="/place/(\w+)/"(.*?)</a>', client.get("/places/").content.decode(), re.S))
    assert "tone-gap-lost" in tiles["alpha"] and "<b data-v>5</b>" in tiles["alpha"]  # the worst kind first
    assert "tone-gap-lost" in tiles["beta"] and "<b data-v>1</b>" in tiles["beta"]
    stats = client.get("/stats/").content.decode()
    lost = re.search(r'<div class="num-label"><i [^>]*></i><span data-v>inputs lost</span></div>\s*'
                     r'<div class="num-value"[^>]*>(\d+)</div>', stats)
    assert lost.group(1) == "1"  # one input, read by alpha, beta and the environment
    only = client.get("/places/?kind=lost").content.decode()  # the Stats link: the places holding that kind, counting it
    assert "<b data-v>inputs lost</b>" in only
    assert dict(re.findall(r'<a class="ptile" href="/place/(\w+)/"(.*?)</a>', only, re.S)).keys() == {"alpha", "beta"}


def test_a_step_two_places_share_is_in_both_rows_and_in_neither_places_own(cockpit):
    from score.dashboard.state import gaps
    a_shared_step(cockpit)
    cockpit.source.refresh()
    details = {place: cockpit.source.gaps(place) for place in ("alpha", "beta")}
    rows = {row["place"]: row for row in gaps.per_place(cockpit.source.gaps_price(), details)}
    assert (rows["alpha"]["money"]["guessed"], rows["beta"]["money"]["guessed"]) == (2.0, 1.0)  # the ground in both
    assert (rows["alpha"]["own"]["guessed"], rows["beta"]["own"]["guessed"]) == (1.0, 0)  # and in neither's own


def test_a_gaps_check_run_again_shows_at_once_not_after_the_index(cockpit):
    import os

    from score.dashboard.pages import cockpit as numbers
    assert numbers.measured_prices(cockpit.source.gaps_price()) == (1, 2)
    findings = cockpit.root / "props/work/checks/gaps/alpha/findings.json"
    price = cockpit.root / "props/work/checks/gaps-price/world1.json"
    findings.write_text(findings.read_text())  # the gaps check ran again; the store's index is not rebuilt
    later = price.stat().st_mtime + 2
    os.utime(findings, (later, later))
    assert numbers.measured_prices(cockpit.source.gaps_price()) == (None, None)
    assert "the gaps check ran again at 1 scene since the price was made" in unescape(
        signed_in().get("/places/").content.decode())  # the remake's hover text


def test_keys_outside_the_index_walk_only_their_folder_and_match_the_whole_walk(tmp_path):
    """A prefix outside the index's areas walks only the folder it names, with the store's own answer."""
    from score.dashboard.state.index import scoped
    from tools.cloud.runtime.store import FolderStore
    store = FolderStore(tmp_path)
    for key in ("concepts/cockpit/draws/1.json", "concepts/cockpit2/draws/2.json", "concepts/cock.json",
                "plans/cockpit/a.json", "concepts/cockpit/draws/3.json.partial"):
        (tmp_path / key).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / key).write_text("{}")
    for prefix in ("concepts/cockpit/", "concepts/cock", "concepts/", "concepts/cockpit/draws/", "nothing/here/"):
        assert scoped(str(tmp_path), prefix) == store.keys(prefix), prefix
