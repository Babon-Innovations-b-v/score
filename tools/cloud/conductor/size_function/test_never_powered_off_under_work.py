"""The size function powers the conductor off only when nothing is known to work on it, only for its own server at
one of its two sizes, and never leaves it off or unprotected; its S3 reads are signed as AWS's own example says.

Against a fake Instances API and a stubbed health record: no cloud. Each invariant with the break that turns it red
(each applied once and seen red):

- Grow and shrink are refused, before any write, while a run is active, a paid machine parked, a frozen worktree in
  use, or the record is missing or older than 10 min (an unknown is never idle); work under a hold (a sync pass, a
  film preview, or a record that does not say) refuses a shrink only; a stopped server needs no record.
  Break: drop the `parked` entry from `health_refusal`'s fields. Break: `record.get("working", 0)` in `health_refusal`.
  Break: raise HEALTH_STALE_SECONDS to 10**12. Break: drop `if server_state == "stopped": return None`.
- Only the configured server, named and tagged score-conductor, at one of its two types.
  Break: `named = True` in `owned`.
- A resize lifts the protection (Scaleway refuses to power off a protected server, 2026-10-24), powers off, waits for
  stopped, changes the type, powers on also when the change was refused, and protects again in every path; an
  unprotected server stays unprotected; one already at the size is not touched.
  Break: drop the `finally:` around poweron in `change_type`. Break: drop the `finally:` around re-protection in
  `resize`. Break: drop the `wait_stopped` call (the fake refuses a type change on a running server).
- A request needs the token, POST and a known action; a refusal is answered as JSON.
  Break: `return action` before the token check in `request_action`.
- s3's SigV4 signature equals AWS's published 'GET Object' example. Break: sort the header names in reverse.
"""
import datetime
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import handler  # noqa: E402
import s3  # noqa: E402

IDLE, BATCH = "POP2-HM-2C-16G", "POP2-HM-16C-128G"
CONFIG = {"SCORE_SERVER_ID": "srv-1", "SCORE_ZONE": "fr-par-2", "SCORE_IDLE_TYPE": IDLE, "SCORE_BATCH_TYPE": BATCH,
          "SCORE_HEALTH_BUCKET": "b", "SCORE_HEALTH_REGION": "nl-ams", "SCW_ACCESS_KEY": "AK", "SCW_SECRET_KEY": "SK",
          "SCORE_SIZE_TOKEN": "tok"}


class FakeApi:
    """The Instances API for one server, protected as `machine.py up` leaves it: poweroff stops it after two reads
    and is refused while it is protected (as Scaleway's 400 'server is protected'); a type change on a server that is
    not stopped is refused, as Scaleway refuses it."""

    def __init__(self, kind=IDLE, state="running", name="score-conductor", tags=("score-conductor",)):
        self.server = {"id": "srv-1", "name": name, "tags": list(tags), "commercial_type": kind, "state": state,
                       "protected": True}
        self.calls, self.stopping = [], None

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        if method == "GET":
            if self.stopping is not None:
                self.stopping -= 1
                if self.stopping <= 0:
                    self.server["state"], self.stopping = "stopped", None
            return {"server": dict(self.server)}
        if method == "PATCH" and "protected" in body:
            self.server["protected"] = body["protected"]
        elif method == "PATCH":
            if self.server["state"] != "stopped":
                raise OSError("HTTP Error 400: the server must be stopped to change its type")
            self.server["commercial_type"] = body["commercial_type"]
        elif body["action"] == "poweroff":
            if self.server["protected"]:
                raise OSError("HTTP Error 400: precondition failed: server is protected")
            self.server["state"], self.stopping = "stopping", 2
        elif body["action"] == "poweron":
            self.server["state"] = "starting"
        return {}

    def writes(self):
        return [call[2] for call in self.calls if call[0] != "GET"]


def fresh(**counts):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    return lambda: {"written_at": now, "active_runs": 0, "parked": 0, "frozen": 0, "working": 0, **counts}


def resize(action, api, health=None):
    return handler.resize(action, CONFIG, api, health or fresh(), sleep=lambda seconds: None)


def test_grow_lifts_protection_powers_off_changes_type_powers_on_and_protects_again():
    api = FakeApi()
    assert resize("grow", api) == {"action": "grow", "from": IDLE, "to": BATCH, "state": "starting", "changed": True}
    assert api.writes() == [{"protected": False}, {"action": "poweroff"}, {"commercial_type": BATCH},
                            {"action": "poweron"}, {"protected": True}]
    assert api.server["protected"] is True

    unprotected = FakeApi()
    unprotected.server["protected"] = False
    resize("grow", unprotected)
    assert not any("protected" in (body or {}) for body in unprotected.writes())

    at_size = FakeApi(kind=BATCH)
    assert resize("grow", at_size)["changed"] is False and at_size.writes() == []


@pytest.mark.parametrize("action, kind", [("shrink", BATCH), ("grow", IDLE)])
@pytest.mark.parametrize("health, words", [
    (fresh(active_runs=1), "run(s) active"), (fresh(parked=2), "parked"), (fresh(frozen=1), "frozen"),
    (lambda: None, "no health record"), (lambda: {"written_at": "2026-01-01T00:00:00+00:00"}, "too old")])
def test_neither_resize_runs_while_the_conductor_is_busy_or_its_state_unknown(action, kind, health, words):
    api = FakeApi(kind=kind)
    with pytest.raises(handler.Refused, match=words.replace("(", r"\(").replace(")", r"\)")):
        resize(action, api, health)
    assert api.writes() == []


def test_work_under_a_hold_refuses_only_a_shrink_and_a_stopped_server_needs_no_record():
    unsaid = {key: value for key, value in fresh()().items() if key != "working"}
    for health in (fresh(working=1), lambda: unsaid):
        api = FakeApi(kind=BATCH)
        with pytest.raises(handler.Refused, match="hold"):
            resize("shrink", api, health)
        assert api.writes() == []
    assert resize("grow", FakeApi(kind=IDLE), fresh(working=1))["changed"]  # a waiting run asked for it
    assert resize("shrink", FakeApi(kind=BATCH, state="stopped"), lambda: None)["to"] == IDLE


def test_a_refused_type_change_or_power_off_never_leaves_it_off_or_unprotected():
    class Refusing(FakeApi):
        def __call__(self, method, path, body=None):
            if "commercial_type" in (body or {}):
                self.calls.append((method, path, body))
                raise OSError("the type change was refused")
            return super().__call__(method, path, body)
    api = Refusing()
    with pytest.raises(OSError):
        resize("grow", api)
    assert [call[2] for call in api.calls if call[0] == "POST"] == [{"action": "poweroff"}, {"action": "poweron"}]
    assert api.server["protected"] is True

    class Stuck(FakeApi):
        def __call__(self, method, path, body=None):
            if body == {"action": "poweroff"}:
                self.calls.append((method, path, body))
                raise OSError("the power off was refused")
            return super().__call__(method, path, body)
    api = Stuck()
    with pytest.raises(OSError):
        resize("grow", api)
    assert api.server["protected"] is True and api.calls[-1][2] == {"protected": True}


def test_only_the_conductor_at_one_of_its_two_sizes():
    for api in (FakeApi(tags=("farm-factory-batch",)), FakeApi(name="other"), FakeApi(kind="GPU-3070-S")):
        with pytest.raises(handler.Refused):
            resize("grow", api)
        assert api.writes() == []


def test_a_request_needs_post_the_token_and_a_known_action_and_is_answered_as_json(monkeypatch):
    def event(token, body):
        return {"httpMethod": "POST", "headers": {"X-Score-Size-Token": token}, "body": json.dumps(body)}
    assert handler.request_action(event("tok", {"action": "shrink"}), "tok") == "shrink"
    for wrong, status in ((event("nope", {"action": "grow"}), 403), (event("tok", {"action": "delete"}), 400),
                          ({"httpMethod": "GET", "headers": {}}, 405)):
        with pytest.raises(handler.Refused) as refused:
            handler.request_action(wrong, "tok")
        assert refused.value.status == status
    for name in CONFIG:
        monkeypatch.delenv(name, raising=False)
    answer = handler.handle({"httpMethod": "POST", "headers": {}, "body": "{}"}, None)
    assert answer["statusCode"] == 500 and "not set up" in json.loads(answer["body"])["refused"]


def test_the_s3_signature_matches_awss_published_example():
    """AWS's S3 SigV4 example 'GET Object' (us-east-1, 2013-05-24, Range bytes=0-9): the signature is AWS's."""
    headers = s3.signed_headers(
        "GET", "https://examplebucket.s3.amazonaws.com/test.txt", "us-east-1", "AKIAIOSFODNN7EXAMPLE",
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", s3.digest(b""),
        datetime.datetime(2013, 5, 24, tzinfo=datetime.timezone.utc), {"Range": "bytes=0-9"})
    assert headers["authorization"].endswith(
        "Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41")
    assert "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date" in headers["authorization"]
