"""The size function against a fake Instances API, and its S3 signature against AWS's published example: no cloud."""
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import handler  # noqa: E402
import s3  # noqa: E402

CONFIG = {"SCORE_SERVER_ID": "srv-1", "SCORE_ZONE": "fr-par-2", "SCORE_IDLE_TYPE": "POP2-HM-2C-16G",
          "SCORE_BATCH_TYPE": "POP2-HM-16C-128G", "SCORE_HEALTH_BUCKET": "b", "SCORE_HEALTH_REGION": "nl-ams",
          "SCW_ACCESS_KEY": "AK", "SCW_SECRET_KEY": "SK", "SCORE_SIZE_TOKEN": "tok"}


class FakeApi:
    """The Instances API for one server, protected as `machine.py up` leaves it: poweroff stops it after two reads
    and is refused while it is protected (as Scaleway's 400 'server is protected'), patch changes its type or
    protection."""

    def __init__(self, kind="POP2-HM-2C-16G", state="running", name="score-conductor", tags=("score-conductor",)):
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
            assert self.server["state"] == "stopped", "type changed on a running server"
            self.server["commercial_type"] = body["commercial_type"]
        elif body["action"] == "poweroff":
            if self.server["protected"]:
                raise OSError("HTTP Error 400: precondition failed: server is protected")
            self.server["state"], self.stopping = "stopping", 2
        elif body["action"] == "poweron":
            self.server["state"] = "starting"
        return {}


def fresh(**counts):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    return lambda: {"written_at": now, "active_runs": 0, "parked": 0, "frozen": 0, **counts}


def resize(action, api, health=None):
    return handler.resize(action, CONFIG, api, health or fresh(), sleep=lambda seconds: None)


def test_grow_powers_off_changes_type_and_powers_on():
    api = FakeApi()
    answer = resize("grow", api)
    assert answer == {"action": "grow", "from": "POP2-HM-2C-16G", "to": "POP2-HM-16C-128G", "state": "starting",
                      "changed": True}
    actions = [call[2] for call in api.calls if call[0] != "GET"]
    assert actions == [{"protected": False}, {"action": "poweroff"}, {"commercial_type": "POP2-HM-16C-128G"},
                       {"action": "poweron"}, {"protected": True}]
    assert api.server["protected"] is True


def test_already_at_size_changes_nothing():
    api = FakeApi(kind="POP2-HM-16C-128G")
    assert resize("grow", api)["changed"] is False
    assert all(call[0] == "GET" for call in api.calls)


def test_grow_and_shrink_refused_while_busy_stale_or_unknown():
    """Either resize powers the server off, so neither runs while a run, a parked machine or a frozen worktree is
    live on it, or while that is unknown."""
    for action, kind in (("shrink", "POP2-HM-16C-128G"), ("grow", "POP2-HM-2C-16G")):
        for health, words in ((fresh(active_runs=1), "run(s) active"), (fresh(parked=2), "parked"),
                              (fresh(frozen=1), "frozen"), (lambda: None, "no health record"),
                              (lambda: {"written_at": "2026-01-01T00:00:00+00:00"}, "too old")):
            api = FakeApi(kind=kind)
            try:
                resize(action, api, health)
                raise AssertionError(f"{action} went on with {words}")
            except handler.Refused as refused:
                assert words in str(refused), (action, words, str(refused))
            assert all(call[0] == "GET" for call in api.calls)


def test_a_refused_type_change_still_powers_the_conductor_on():
    class Refusing(FakeApi):
        def __call__(self, method, path, body=None):
            if "commercial_type" in (body or {}):
                self.calls.append((method, path, body))
                raise OSError("the type change was refused")
            return super().__call__(method, path, body)
    api = Refusing()
    try:
        resize("grow", api)
        raise AssertionError("a refused type change was taken as done")
    except OSError:
        pass
    assert [call[2] for call in api.calls if call[0] == "POST"] == [{"action": "poweroff"}, {"action": "poweron"}]
    assert api.server["protected"] is True, "a failed type change left the conductor unprotected"


def test_protection_comes_back_when_the_power_off_fails():
    class Stuck(FakeApi):
        def __call__(self, method, path, body=None):
            if body == {"action": "poweroff"}:
                self.calls.append((method, path, body))
                raise OSError("the power off was refused")
            return super().__call__(method, path, body)
    api = Stuck()
    try:
        resize("grow", api)
        raise AssertionError("a refused power off was taken as done")
    except OSError:
        pass
    assert api.server["protected"] is True and api.calls[-1][2] == {"protected": True}


def test_an_unprotected_server_is_left_unprotected():
    api = FakeApi()
    api.server["protected"] = False
    resize("grow", api)
    assert not any("protected" in (call[2] or {}) for call in api.calls)


def test_shrink_of_a_stopped_server_needs_no_record():
    api = FakeApi(kind="POP2-HM-16C-128G", state="stopped")
    assert resize("shrink", api, lambda: None)["to"] == "POP2-HM-2C-16G"


def test_only_the_conductor_at_one_of_its_two_sizes():
    for api in (FakeApi(tags=("farm-factory-batch",)), FakeApi(name="other"), FakeApi(kind="GPU-3070-S")):
        try:
            resize("grow", api)
            raise AssertionError("resized a server that is not the conductor at one of its sizes")
        except handler.Refused:
            pass
        assert all(call[0] == "GET" for call in api.calls)


def test_request_needs_the_token_and_a_known_action():
    def event(token, body):
        return {"httpMethod": "POST", "headers": {"X-Score-Size-Token": token}, "body": json.dumps(body)}
    assert handler.request_action(event("tok", {"action": "shrink"}), "tok") == "shrink"
    for wrong, status in ((event("nope", {"action": "grow"}), 403), (event("tok", {"action": "delete"}), 400),
                          ({"httpMethod": "GET", "headers": {}}, 405)):
        try:
            handler.request_action(wrong, "tok")
            raise AssertionError("took a wrong request")
        except handler.Refused as refused:
            assert refused.status == status


def test_handle_answers_a_refusal_as_json():
    answer = handler.handle({"httpMethod": "POST", "headers": {}, "body": "{}"}, None)
    assert answer["statusCode"] == 500 and "not set up" in json.loads(answer["body"])["refused"]


def test_signature_matches_aws_example():
    """AWS's S3 SigV4 example 'GET Object' (us-east-1, 2013-05-24, Range bytes=0-9)."""
    headers = s3.signed_headers(
        "GET", "https://examplebucket.s3.amazonaws.com/test.txt", "us-east-1", "AKIAIOSFODNN7EXAMPLE",
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", s3.digest(b""),
        datetime.datetime(2013, 5, 24, tzinfo=datetime.timezone.utc), {"Range": "bytes=0-9"})
    assert headers["authorization"].endswith(
        "Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"), headers["authorization"]
    assert "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date" in headers["authorization"]


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"ok {name}")
