"""Nothing advances unseen: the owner's mark shows on the place and step pages, the owner advances an output from its
step page or the API, and a paid launch reading an accepted output is refused until that output is advanced, here
and on the store's machine for a hosted launch (the advance request applied there first)."""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from score.dashboard.pages import actions, seen
from score.dashboard.pages.models import Plan, SyncRequest
from score.dashboard.sync import applying
from score.dashboard.tests.fixture import FakeBackend

pytestmark = pytest.mark.django_db
PAID = "demo-film@alpha"  # reads assembly@alpha and complete@alpha, both accepted in the fixture world


def signed_in(name="joey"):
    user = get_user_model().objects.create_user(name, password="a long enough password")
    client = Client()
    client.force_login(user)
    return client


def ready_plan(buys):
    body = {"groups": [{"places": ["alpha"], "stages": ["demo-film"], "missing": [], "buys": buys, "refusal": None,
                        "to_run": {}, "blocked": {}}], "buys": buys, "jobs": 8, "rebuys": 0.0, "nodes": [],
            "money": {"high": 13.67, "likely": 13.31, "spent": 100.0, "reserved": 10.0, "ceiling": 250.0,
                      "room": 140.0, "note": ""}, "time": {"likely_minutes": 10, "high_minutes": 20}}
    return Plan.objects.create(basket_hash="h", made_by="joey", state="ready", body=body, finished=timezone.now())


def test_the_mark_shows_and_the_owner_advances_from_the_step_page(world):
    client = signed_in()
    assert "not seen by owner" in client.get("/place/alpha/").content.decode()
    html = client.get("/place/alpha/step/assembly/").content.decode()
    assert "Seen, not advanced" in html and "I looked: advance this output" in html
    accepted = world.outputs["assembly@alpha"]
    answer = client.post("/place/alpha/step/assembly/advance/", {"output": accepted})
    assert answer.status_code == 302 and seen.advanced("assembly@alpha", accepted)
    html = client.get("/place/alpha/step/assembly/").content.decode()
    assert "Advanced" in html and "I looked: advance this output" not in html


def test_only_the_owner_advances(world):
    answer = signed_in("guest").post("/place/alpha/step/assembly/advance/", {"output": "x"})
    assert answer.status_code == 403 and not SyncRequest.objects.exists()


def test_a_paid_launch_is_refused_until_what_it_reads_is_advanced(world):
    plan = ready_plan([{"node": PAID, "euros": 5.0, "why": "never ran", "again": False}])
    held = actions.unseen(plan)
    assert set(held) == {(PAID, "assembly@alpha"), (PAID, "complete@alpha")}
    refused = actions.launch_refusals(get_user_model()(username="joey"), plan, True, "")
    assert any(why.startswith("not seen by owner") for why in refused)
    client = signed_in()
    for stage in ("assembly", "complete"):
        client.post(f"/place/alpha/step/{stage}/advance/", {"output": world.outputs[f"{stage}@alpha"]})
    assert actions.unseen(plan) == []


class PaidFilm(FakeBackend):
    """The fake backend buying the film as well as the close-up."""

    def plan(self, group):
        planned = FakeBackend.plan(self, group)
        planned.buys += [{"node": f"demo-film@{place}", "euros": 5.0, "why": "never ran", "again": False}
                         for place in group.places if "demo-film" in group.stages]
        return planned


def test_a_hosted_launch_checks_the_advances_applied_on_the_stores_machine(world, settings):
    settings.SCORE_LEDGER_FILES = [world.ledger]
    launch = {"kind": "launch", "user": "joey", "payload": {"items": [{"place": "alpha", "stage": "demo-film"}]}}
    refused = applying.apply(launch, world.source, PaidFilm())
    assert refused.state == "refused" and "not seen by owner" in refused.detail, refused.detail
    from_someone_else = applying.apply({"kind": "advance", "user": "mallory", "payload": {
        "node": "assembly@alpha", "output": world.outputs["assembly@alpha"]}}, world.source)
    assert from_someone_else.state == "refused" and not seen.advanced("assembly@alpha", world.outputs["assembly@alpha"])
    for node in ("assembly@alpha", "complete@alpha"):
        applied = applying.apply({"kind": "advance", "user": "joey", "payload": {
            "node": node, "output": world.outputs[node]}}, world.source)
        assert applied.state == "done", applied.detail
    launched = applying.apply(launch, world.source, PaidFilm())
    assert launched.state == "running", launched.detail


def test_a_hosted_advance_is_recorded_and_queued_for_the_stores_machine(world, settings):
    settings.SCORE_MODE = "hosted"
    signed_in().post("/place/alpha/step/assembly/advance/", {"output": world.outputs["assembly@alpha"]})
    queued = SyncRequest.objects.get(kind="advance")
    assert queued.payload == {"node": "assembly@alpha", "output": world.outputs["assembly@alpha"]}
