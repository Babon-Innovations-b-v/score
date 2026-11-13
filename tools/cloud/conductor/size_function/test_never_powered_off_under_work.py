"""The size function powers the conductor off only when nothing is known to work on it, only for its own server at
one of its two sizes, and never leaves it off or unprotected; its S3 reads are signed as AWS's own example says.

One test drives a table of requests through the function's entry point `handler.handle`, against a fake Instances
API and a fake object store that holds the health record: no cloud. Each invariant with the break that turns it red
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
- The health record is read signed with the function's own key for its region, by s3's SigV4 signer, which the fake
  store trusts only because it reproduces AWS's published 'GET Object' example. Break: sort the header names in
  reverse.
"""
import datetime
import json
import pathlib
import sys
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import handler  # noqa: E402
import s3  # noqa: E402

IDLE, BATCH = "POP2-HM-2C-16G", "POP2-HM-16C-128G"
CONFIG = {"SCORE_SERVER_ID": "srv-1", "SCORE_ZONE": "fr-par-2", "SCORE_IDLE_TYPE": IDLE, "SCORE_BATCH_TYPE": BATCH,
          "SCORE_HEALTH_BUCKET": "b", "SCORE_HEALTH_REGION": "nl-ams", "SCW_ACCESS_KEY": "AK", "SCW_SECRET_KEY": "SK",
          "SCORE_SIZE_TOKEN": "tok"}
UNPROTECT, OFF, ON, PROTECT = {"protected": False}, {"action": "poweroff"}, {"action": "poweron"}, {"protected": True}
TO_BATCH, TO_IDLE = {"commercial_type": BATCH}, {"commercial_type": IDLE}
FULL_GROW = [UNPROTECT, OFF, TO_BATCH, ON, PROTECT]
AWS_EXAMPLE_SIGNATURE = "Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"


class FakeApi:
    """The Instances API for one server, protected as `machine.py up` leaves it: poweroff stops it after two reads
    and is refused while it is protected (as Scaleway's 400 'server is protected'); a type change on a server that is
    not stopped is refused, as Scaleway refuses it. `refuse` names a write Scaleway refuses outright."""

    def __init__(self, kind=IDLE, state="running", name="score-conductor", tags=("score-conductor",),
                 protected=True, refuse=None):
        self.server = {"id": "srv-1", "name": name, "tags": list(tags), "commercial_type": kind, "state": state,
                       "protected": protected}
        self.calls, self.stopping, self.refuse = [], None, refuse

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        if method == "GET":
            if self.stopping is not None:
                self.stopping -= 1
                if self.stopping <= 0:
                    self.server["state"], self.stopping = "stopped", None
            return {"server": dict(self.server)}
        if self.refuse is not None and self.refuse in body.values():
            raise OSError(f"Scaleway refused {body}")
        if "protected" in body:
            self.server["protected"] = body["protected"]
        elif "commercial_type" in body:
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


class FakeStore:
    """The health bucket as `urlopen`: it serves health/conductor.json (404 when there is none) only to a read signed
    with the function's key for its region, checked by recomputing s3's signature, which it trusts only because s3
    reproduces AWS's published S3 SigV4 'GET Object' example (us-east-1, 2013-05-24, Range bytes=0-9)."""

    def __init__(self, record):
        aws = s3.signed_headers(
            "GET", "https://examplebucket.s3.amazonaws.com/test.txt", "us-east-1", "AKIAIOSFODNN7EXAMPLE",
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", s3.digest(b""),
            datetime.datetime(2013, 5, 24, tzinfo=datetime.timezone.utc), {"Range": "bytes=0-9"})["authorization"]
        assert aws.endswith(AWS_EXAMPLE_SIGNATURE), aws
        assert "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date" in aws, aws
        self.record, self.reads = record, 0

    def __call__(self, request, timeout):
        url = s3.object_url(CONFIG["SCORE_HEALTH_BUCKET"], handler.HEALTH_KEY, CONFIG["SCORE_HEALTH_REGION"])
        assert request.full_url == url
        signed_at = datetime.datetime.strptime(request.get_header("X-amz-date"), "%Y%m%dT%H%M%SZ").replace(
            tzinfo=datetime.timezone.utc)
        assert request.get_header("Authorization") == s3.signed_headers(
            "GET", url, CONFIG["SCORE_HEALTH_REGION"], CONFIG["SCW_ACCESS_KEY"], CONFIG["SCW_SECRET_KEY"],
            s3.digest(b""), signed_at)["authorization"]
        self.reads += 1
        if self.record is None:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        body = json.dumps(self.record).encode()

        class Answer:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return body
        return Answer()


def record(**counts):
    """A health record written now, saying nothing works on the conductor unless `counts` says so."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    return {"written_at": now, "active_runs": 0, "parked": 0, "frozen": 0, "working": 0, **counts}


UNSAID = {key: value for key, value in record().items() if key != "working"}
STALE = {"written_at": "2026-01-01T00:00:00+00:00"}


def request(action="grow", token="tok", method="POST"):
    return {"httpMethod": method, "headers": {"X-Score-Size-Token": token}, "body": json.dumps({"action": action})}


def done(action, was, to):
    return {"action": action, "from": was, "to": to, "state": "starting", "changed": True}


BUSY = [(record(active_runs=1), "run(s) active"), (record(parked=2), "parked"), (record(frozen=1), "frozen"),
        (None, "no health record"), (STALE, "too old")]

# id: (request, the server as FakeApi's keywords, the stored health record, the expected answer: (status, the whole
# body or the words its refusal holds) or the error it raises, the writes the Instances API saw in order)
CASES = {
    "grow": (request("grow"), {}, record(), (200, done("grow", IDLE, BATCH)), FULL_GROW),
    "grow-unprotected-stays-unprotected": (request("grow"), {"protected": False}, record(),
                                           (200, done("grow", IDLE, BATCH)), [OFF, TO_BATCH, ON]),
    "grow-at-size-untouched": (request("grow"), {"kind": BATCH}, record(),
                               (200, {"action": "grow", "from": BATCH, "to": BATCH, "state": "running",
                                      "changed": False}), []),
    **{f"{action}-refused-{words.split()[-1]}": (request(action), {"kind": kind}, health, (409, words), [])
       for action, kind in (("shrink", BATCH), ("grow", IDLE)) for health, words in BUSY},
    "shrink-refused-under-a-hold": (request("shrink"), {"kind": BATCH}, record(working=1), (409, "hold"), []),
    "shrink-refused-when-the-record-does-not-say": (request("shrink"), {"kind": BATCH}, UNSAID, (409, "hold"), []),
    "grow-under-a-hold-a-waiting-run-asked": (request("grow"), {}, record(working=1),
                                              (200, done("grow", IDLE, BATCH)), FULL_GROW),
    "shrink-stopped-needs-no-record": (request("shrink"), {"kind": BATCH, "state": "stopped"}, None,
                                       (200, done("shrink", BATCH, IDLE)), [UNPROTECT, TO_IDLE, ON, PROTECT]),
    "type-change-refused-powered-on-and-protected": (request("grow"), {"refuse": BATCH}, record(), OSError,
                                                     FULL_GROW),
    "power-off-refused-protected-again": (request("grow"), {"refuse": "poweroff"}, record(), OSError,
                                          [UNPROTECT, OFF, PROTECT]),
    "not-tagged-the-conductor": (request("grow"), {"tags": ("farm-factory-batch",)}, record(), (403, "not the"), []),
    "not-named-the-conductor": (request("grow"), {"name": "other"}, record(), (403, "not the"), []),
    "neither-of-its-two-sizes": (request("grow"), {"kind": "GPU-3070-S"}, record(), (409, "neither"), []),
    "wrong-token": (request("grow", token="nope"), {}, record(), (403, "X-Score-Size-Token"), []),
    "unknown-action": (request("delete"), {}, record(), (400, "action must be"), []),
    "not-post": ({"httpMethod": "GET", "headers": {}}, {}, record(), (405, "POST only"), []),
    "not-set-up": ({"httpMethod": "POST", "headers": {}, "body": "{}"}, {}, record(), (500, "not set up"), []),
}


@pytest.mark.parametrize("event, server, health, expected, writes", CASES.values(), ids=CASES.keys())
def test_never_powered_off_under_work(monkeypatch, event, server, health, expected, writes):
    for name, value in CONFIG.items():
        monkeypatch.setenv(name, value)
    if expected == (500, "not set up"):
        for name in CONFIG:
            monkeypatch.delenv(name)
    api, store = FakeApi(**server), FakeStore(health)
    monkeypatch.setattr(handler, "instance_api", lambda config: api)
    monkeypatch.setattr(urllib.request, "urlopen", store)
    monkeypatch.setattr(handler, "POLL_SECONDS", 0)

    if expected is OSError:
        with pytest.raises(OSError):
            handler.handle(event, None)
    else:
        status, body = expected
        answer = handler.handle(event, None)
        assert answer["statusCode"] == status and answer["headers"] == {"Content-Type": "application/json"}
        said = json.loads(answer["body"])
        if isinstance(body, dict):
            assert said == body
        else:
            assert set(said) == {"refused"} and body in said["refused"], said
    assert api.writes() == writes
    assert api.server["protected"] is server.get("protected", True)
    assert api.server["state"] in ("running", "starting"), api.server
