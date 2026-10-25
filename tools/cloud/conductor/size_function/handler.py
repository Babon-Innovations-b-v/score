"""score-conductor-size: the Scaleway Serverless Function that changes the conductor's size, standard library only
(it is deployed as this folder alone, `machine.py up`). It takes one POST {"action": "grow"} or {"action":
"shrink"} with the header X-Score-Size-Token, whose value is the secret score-conductor-size-token, and it:

- allows exactly two commercial types, the idle one (SCORE_IDLE_TYPE) and the batch one (SCORE_BATCH_TYPE), and the
  one server SCORE_SERVER_ID in SCORE_ZONE, all set in its own environment at deploy time (never in the repository);
  a server not named and tagged score-conductor is refused;
- refuses to grow or shrink a running server while the conductor's health record (health/conductor.json in
  SCORE_HEALTH_BUCKET, written every minute by tools/cloud/conductor/health_push.py) says a run is active, a paid
  machine is parked or a frozen worktree is in use, or is older than HEALTH_STALE_SECONDS (an unknown is never an
  idle), and to shrink it while it holds work (`working`: a sync pass, a request, a film preview, a reading): either way the server is powered off, which would cut the run and orphan its rented machines;
- lifts the server's protection (`machine.py up` sets it, and Scaleway refuses to power off a protected server:
  "precondition failed: server is protected", 2026-10-24), powers it off, waits until it is stopped, sets its
  commercial type, powers it on (also when the type change was refused, so the conductor is never left off), protects
  it again (in every path, a failure's too) and returns the new state.

Its own Scaleway key (secret environment variables SCW_ACCESS_KEY, SCW_SECRET_KEY: the secret score-conductor-size-key)
may change Instances in the conductor's project and read that one bucket.
"""
import base64
import datetime
import hmac
import json
import os
import time
import urllib.request

import s3

API = "https://api.scaleway.com/instance/v1/zones"
NAME = "score-conductor"
ACTIONS = ("grow", "shrink")
HEALTH_KEY = "health/conductor.json"
HEALTH_STALE_SECONDS = 600
STOP_WAIT_SECONDS = 600
POLL_SECONDS = 5


class Refused(Exception):
    """A request the function will not carry out, with why; `status` is the HTTP answer."""

    def __init__(self, why, status=409):
        super().__init__(why)
        self.status = status


def settings():
    """The function's own environment: server, zone, the two types, the health bucket, its key and the token."""
    names = ("SCORE_SERVER_ID", "SCORE_ZONE", "SCORE_IDLE_TYPE", "SCORE_BATCH_TYPE", "SCORE_HEALTH_BUCKET",
             "SCORE_HEALTH_REGION", "SCW_ACCESS_KEY", "SCW_SECRET_KEY", "SCORE_SIZE_TOKEN")
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise Refused(f"the function is not set up: {', '.join(missing)} missing", 500)
    return {name: os.environ[name] for name in names}


def instance_api(config):
    """call(method, path, body) against the Instances API of the configured zone, as the function's key."""
    def call(method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(f"{API}/{config['SCORE_ZONE']}{path}", data=data, method=method,
                                         headers={"X-Auth-Token": config["SCW_SECRET_KEY"],
                                                  "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as answer:
            text = answer.read()
        return json.loads(text) if text else {}
    return call


def health_reader(config):
    """read() -> the conductor's last health record, or None when there is none."""
    def read():
        raw = s3.get(config["SCORE_HEALTH_BUCKET"], HEALTH_KEY, config["SCORE_HEALTH_REGION"],
                     config["SCW_ACCESS_KEY"], config["SCW_SECRET_KEY"])
        return json.loads(raw) if raw else None
    return read


def request_action(event, token):
    """The asked action, after the token check; Refused for a wrong method, token or action."""
    if event.get("httpMethod", "POST") != "POST":
        raise Refused("POST only", 405)
    headers = {name.lower(): value for name, value in (event.get("headers") or {}).items()}
    if not hmac.compare_digest(headers.get("x-score-size-token", "").encode(), token.encode()):
        raise Refused("wrong or missing X-Score-Size-Token", 403)
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode()
    try:
        action = json.loads(body).get("action")
    except (ValueError, AttributeError):
        raise Refused("the body is not a JSON object", 400) from None
    if action not in ACTIONS:
        raise Refused(f"action must be one of {', '.join(ACTIONS)}, not {action!r}", 400)
    return action


def health_refusal(record, server_state, now, action="grow"):
    """Why the conductor may not be powered off for `action` now by its health record, or None. Work under a hold
    (a sync pass, a film preview: `working`) refuses only a shrink, and a record that does not say it is unknown."""
    if server_state == "stopped":
        return None
    if not record:
        return "no health record: an unknown is never idle"
    written = datetime.datetime.fromisoformat(record["written_at"])
    if (now - written).total_seconds() > HEALTH_STALE_SECONDS:
        return f"the health record is from {record['written_at']}, too old to trust"
    for field, words in (("active_runs", "run(s) active"), ("parked", "paid machine(s) parked"),
                         ("frozen", "frozen worktree(s) in use")):
        if record.get(field):
            return f"{record[field]} {words}"
    if action == "shrink" and record.get("working", 1):
        return f"{record.get('working', 'unknown')} hold(s) of work (a sync pass, a request, a film preview)"
    return None


def owned(server, config):
    """Refused unless the server is the configured one, named and tagged score-conductor, at one of the two types."""
    named = server.get("name") == NAME and NAME in server.get("tags", [])
    if server.get("id") != config["SCORE_SERVER_ID"] or not named:
        raise Refused("the server is not the conductor this function was deployed for", 403)
    if server.get("commercial_type") not in (config["SCORE_IDLE_TYPE"], config["SCORE_BATCH_TYPE"]):
        raise Refused(f"the server is {server.get('commercial_type')}, neither of the two sizes; change it by hand")


def wait_stopped(api, path, sleep, clock):
    """The server once its state is stopped; Refused when it is not within STOP_WAIT_SECONDS."""
    deadline = clock() + STOP_WAIT_SECONDS
    while True:
        server = api("GET", path)["server"]
        if server["state"] == "stopped":
            return server
        if clock() > deadline:
            raise Refused(f"the server is still {server['state']} after {STOP_WAIT_SECONDS} s", 504)
        sleep(POLL_SECONDS)


def change_type(api, path, state, target, sleep, clock):
    """Power the server off (unless stopped), set its commercial type and power it on, also when the change failed."""
    if state != "stopped":
        api("POST", f"{path}/action", {"action": "poweroff"})
        wait_stopped(api, path, sleep, clock)
    try:
        api("PATCH", path, {"commercial_type": target})
    finally:
        api("POST", f"{path}/action", {"action": "poweron"})


def resize(action, config, api, read_health, sleep=time.sleep, clock=time.monotonic):
    """Carry out grow or shrink: the answer {action, from, to, state, changed}."""
    target = config["SCORE_BATCH_TYPE"] if action == "grow" else config["SCORE_IDLE_TYPE"]
    path = f"/servers/{config['SCORE_SERVER_ID']}"
    server = api("GET", path)["server"]
    owned(server, config)
    was = server["commercial_type"]
    if was == target:
        return {"action": action, "from": was, "to": target, "state": server["state"], "changed": False}
    refused = health_refusal(read_health(), server["state"], datetime.datetime.now(datetime.timezone.utc),
                             action)
    if refused:
        raise Refused(f"{action} refused: {refused}; a resize powers the conductor off")
    protected = server.get("protected")
    if protected:
        api("PATCH", path, {"protected": False})
    try:
        change_type(api, path, server["state"], target, sleep, clock)
    finally:
        if protected:
            api("PATCH", path, {"protected": True})
    state = api("GET", path)["server"]
    return {"action": action, "from": was, "to": state["commercial_type"], "state": state["state"], "changed": True}


def answer(status, body):
    return {"statusCode": status, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}


def handle(event, context):
    """The function's entry point (handler handler.handle)."""
    try:
        config = settings()
        action = request_action(event, config["SCORE_SIZE_TOKEN"])
        return answer(200, resize(action, config, instance_api(config), health_reader(config)))
    except Refused as refused:
        return answer(refused.status, {"refused": str(refused)})
