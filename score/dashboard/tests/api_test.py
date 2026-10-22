"""Every API route answers its schema from the fixture environment; owner routes refuse anyone else; the session is the
pages' own; a write needs the CSRF header and an Origin."""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from fastapi.testclient import TestClient

from score.dashboard.state.models import PlaceDetail, Spend, StepDetail, WorldState

pytestmark = pytest.mark.django_db(transaction=True)
ORIGIN = "http://127.0.0.1:8780"


def api(name="joey"):
    """A FastAPI test client carrying a signed-in Django session and its CSRF cookie."""
    from score.dashboard.site.asgi import app
    user = get_user_model().objects.create_user(name, password="a long enough password")
    pages = Client()
    pages.force_login(user)
    pages.get("/login/")  # sets the csrftoken cookie
    client = TestClient(app, base_url="http://127.0.0.1:8780", client=("127.0.0.1", 50000))
    for cookie in pages.cookies.values():
        client.cookies.set(cookie.key, cookie.value)
    token = pages.cookies["csrftoken"].value if "csrftoken" in pages.cookies else ""
    client.headers.update({"X-CSRFToken": token, "Origin": ORIGIN})
    return client


def test_reads_answer_their_schemas(world):
    client = api()
    WorldState.model_validate(client.get("/api/state").json())
    PlaceDetail.model_validate(client.get("/api/places/alpha").json())
    StepDetail.model_validate(client.get("/api/places/alpha/steps/closeup").json())
    StepDetail.model_validate(client.get("/api/world/steps/terrain").json())
    Spend.model_validate(client.get("/api/spend").json())
    assert client.get("/api/places/nowhere").status_code == 404
    assert client.get("/api/places/alpha/steps/nothing").status_code == 404
    assert client.get("/api/launches").json() == []
    assert client.get("/healthz").json() == {"ok": True, "mode": "local", "commit": None}


def test_healthz_reports_the_commit_the_image_was_built_at(settings):
    """The hosted image's SCORE_COMMIT, the pin the conductor's score-update timer follows; open to anyone."""
    from score.dashboard.site.asgi import app
    settings.SCORE_COMMIT = "a" * 40
    answer = TestClient(app, base_url="http://127.0.0.1:8780", client=("127.0.0.1", 50000)).get("/healthz")
    assert answer.status_code == 200 and answer.json()["commit"] == "a" * 40


def test_without_a_session_401():
    from score.dashboard.site.asgi import app
    client = TestClient(app, base_url="http://127.0.0.1:8780", client=("127.0.0.1", 50000))
    for path in ("/api/state", "/api/spend", "/api/requests", "/files/" + "0" * 64, "/api/docs"):
        assert client.get(path).status_code == 401, path


def test_owner_routes_refuse_a_non_owner(world):
    client = api("guest")
    assert client.get("/api/basket/items").status_code == 403
    assert client.post("/api/basket/items", json={"place": "alpha", "stage": "plan"}).status_code == 403
    assert client.post("/api/decisions", json={"node": "closeup@alpha", "output": "x",
                                               "decision": "accept"}).status_code == 403
    assert client.post("/api/launches", json={"plan_id": 1, "confirm": True}).status_code == 403


def test_writes_need_the_csrf_header_and_an_origin(world):
    client = api()
    body = {"place": "alpha", "stage": "closeup", "words": "redder"}
    assert client.post("/api/requests", json=body, headers={"X-CSRFToken": ""}).status_code == 403
    client.headers.pop("Origin")
    assert client.post("/api/requests", json=body).status_code == 403


def test_a_change_request_and_the_basket_round_trip(world):
    client = api()
    made = client.post("/api/requests", json={"place": "alpha", "stage": "closeup", "words": "redder"})
    assert made.status_code == 200 and made.json()["node"] == "closeup@alpha"
    assert [item["words"] for item in client.get("/api/requests").json()] == ["redder"]
    listed = client.post("/api/basket/items", json={"place": "alpha", "stage": "closeup"}).json()
    assert [(item["place"], item["stage"]) for item in listed] == [("alpha", "closeup")]
    assert client.delete(f"/api/basket/items/{listed[0]['id']}").json() == []


def test_a_decision_through_the_api(world):
    client = api()
    waiting = world.outputs["closeup@alpha waiting"]
    refused = client.post("/api/decisions", json={"node": "closeup@alpha", "output": waiting, "decision": "accept"})
    assert refused.status_code == 409 and "worse" in refused.json()["detail"]
    taken = client.post("/api/decisions", json={"node": "closeup@alpha", "output": waiting, "decision": "accept",
                                                "worse_reason": "fine"})
    assert taken.status_code == 200 and world.store.accepted("closeup@alpha") == waiting


def test_files_are_served_only_when_listed(world):
    client = api()
    detail = client.get("/api/places/alpha/steps/closeup").json()
    picture = next(item for item in detail["files"] if item["kind"] == "image")
    assert client.get(picture["url"]).headers["content-type"] == "image/png"
    assert client.get(picture["thumb_url"]).headers["content-type"] == "image/jpeg"
    assert client.get("/files/" + "f" * 64).status_code == 404
    assert client.get("/files/../etc").status_code == 404


def test_an_advance_through_the_api(world):
    from score.dashboard.pages import seen
    output = world.outputs["assembly@alpha"]
    client = api()
    answer = client.post("/api/advances", json={"node": "assembly@alpha", "output": output})
    assert answer.status_code == 200 and answer.json()["said"].startswith("advanced"), answer.text
    assert seen.advanced("assembly@alpha", output)
    assert client.post("/api/advances", json={"node": "nothing@alpha", "output": output}).status_code == 404
    assert client.post("/api/advances", json={"node": "assembly@alpha", "output": ""}).status_code == 409
    assert api("guest").post("/api/advances", json={"node": "assembly@alpha", "output": output}).status_code == 403
