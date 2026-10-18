"""Every page renders for the owner from the fixture world, with its pictures and words; a signed-out visitor is sent
to the sign-in page; node ids stay inside the details fold; every POST needs its CSRF token."""
import re

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

pytestmark = pytest.mark.django_db
PAGES = ["/", "/place/alpha/", "/place/beta/", "/place/alpha/step/closeup/", "/place/beta/step/assembly/",
         "/world/step/terrain/", "/basket/", "/runs/", "/requests/", "/picks/alpha"]
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


def test_the_board_shows_pictures_status_and_styles(world):
    html = signed_in().get("/").content.decode()
    assert "the alpha look" in html.lower() and "unassigned" in html.lower()
    assert html.count("/thumbs/") >= 3  # the look's reference and each place's hero
    assert "#334455" in html
    assert "complete" in html and "stopped at" not in outside_details(html).split("Beta")[0]
    assert "spent EUR 100.00" in html or "being read" in html


def test_the_place_page_shows_the_usd_index_and_faults(world):
    html = signed_in().get("/place/beta/").content.decode()
    assert "beta.usda" in html and "light" in html and "assets" in html
    assert "placeholders" in html and "beta: no lamp model" in html
    assert "<video" in html and "/files/" in html


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
