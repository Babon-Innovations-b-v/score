"""The store's machine on the cockpit (state/machine.py, sync/one_store.py, pages/machine.py): the export carries the
machine, its health and its logs' tails (cut, and left out over the cap); a second machine's export is shown but
applies nothing until the owner confirms it (owner only, asked twice; no agent or sync token moves it); Stop
everything and Allow paid work again are the owner's only, asked twice, applied once through score.conductor.kill;
the card and /machine/ render. score.conductor is stood in for here: the real one is the conductor's own."""
import datetime
import hashlib
import json
import os
import shutil
import sys
import types

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from score.dashboard.pages.models import SyncRequest
from score.dashboard.state import machine, versions
from score.dashboard.state.exported import ExportedSource
from score.dashboard.sync import applying, building, client, one_store
from score.dashboard.tests.api_test import api
from score.dashboard.tests.sync_test import MADE, SPEND, TOKEN, hosted_client, opener_of

pytestmark = pytest.mark.django_db(transaction=True)
THEN = datetime.datetime.fromisoformat(MADE) + datetime.timedelta(hours=1)  # an hour after the exports
HEALTH = {"size": "POP2-HM-2C-16G", "state": "idle", "units": {"score-sync.timer": "active"},
          "backup": {"at": "2026-10-18T11:30:00+00:00", "ok": True}, "bill": {"euros": 12.34, "month": "2026-10"},
          "disk": {"used_gb": 40, "total_gb": 100}, "free_only": True}


class Kill:
    """score.conductor.kill stood in: each call kept."""

    def __init__(self):
        self.calls = []

    def stop_all(self, asked_by, words):
        self.calls.append(("stop_all", asked_by, words))
        return {"runs": ["run-1", "run-2"], "parked": ["m-1"], "latched": True}

    def allow_paid(self, asked_by, words):
        self.calls.append(("allow_paid", asked_by, words))
        return {"latched": False}


@pytest.fixture
def conductor(monkeypatch):
    """score.conductor with health, logs and kill stood in; its Kill."""
    kill = Kill()
    parts = {"health": types.SimpleNamespace(read=lambda: dict(HEALTH)),
             "logs": types.SimpleNamespace(tails=lambda limit: {"run.log": [f"line {n} " + "x" * 2000 for n in
                                                                            range(limit)], "faults": ["one fault"]}),
             "kill": kill}
    monkeypatch.setitem(sys.modules, "score.conductor", types.ModuleType("score.conductor"))
    for name, part in parts.items():
        monkeypatch.setitem(sys.modules, f"score.conductor.{name}", part)
    return kill


@pytest.fixture
def no_record(settings):
    """No store's machine recorded and no export swapped in on the hosted side, before and after (the dashboard home
    is the session's: an export left here would be current for the next file's tests)."""
    cleared(settings)
    yield
    cleared(settings)


def cleared(settings):
    one_store.path().unlink(missing_ok=True)
    shutil.rmtree(settings.SCORE_HOME / "export", ignore_errors=True)


def named(world, name):
    (world.source.props_home / machine.MACHINE_FILE).write_text(json.dumps({"name": name, "size": "POP2-HM-2C-16G"}))


def test_the_export_carries_the_machine_its_health_and_its_cut_tails(world, tmp_path, conductor):
    named(world, "conductor")
    manifest = building.build(world.source, tmp_path / "one", MADE, 50, SPEND, world.root)
    found = json.loads((tmp_path / "one/machine.json").read_text())
    assert manifest["machine"] == "conductor" and manifest["written"][:2] == ["state.json", "machine.json"]
    assert found["machine"]["name"] == "conductor" and found["health"]["bill"]["euros"] == 12.34
    assert found["read_at"] == MADE and found["tails"]["faults"] == ["one fault"]
    assert sum(len(line) + 1 for lines in found["tails"].values() for line in lines) <= machine.TAIL_BYTES
    assert found["tails"]["run.log"][-1].startswith(f"line {machine.TAIL_LINES - 1} ")  # the newest kept
    assert ExportedSource(tmp_path / "one").machine() == found
    small = building.build(world.source, tmp_path / "small", MADE, 0.05, SPEND, world.root)
    assert json.loads((tmp_path / "small/machine.json").read_text())["tails"] == {}
    assert {"what": "the store's machine's log tails", "why": "over the export's cap"} in small["left_out"]


def test_off_a_conductor_the_export_says_so_and_names_this_host(world, tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "score.conductor", None)
    building.build(world.source, tmp_path / "one", MADE, 50, SPEND, world.root)
    found = json.loads((tmp_path / "one/machine.json").read_text())
    assert found["health"] == {"missing": machine.NOT_ON_CONDUCTOR} and found["tails"] == {}
    assert found["machine"]["name"]
    card = machine.card(found, MADE)
    assert card["missing"] == machine.NOT_ON_CONDUCTOR and card["state"] is None and card["export_late"]


def committed_by(remote, name):
    """An export whose manifest names machine `name`, sent and committed through the sync routes."""
    data = json.dumps({"format": versions.FORMAT, "made_at": MADE, "machine": name}).encode()
    sha = hashlib.sha256(data).hexdigest()
    remote.lacking({sha: len(data)})
    remote.put_chunk(sha, 0, len(data), data)
    return remote.commit(f"export-{name}", {"manifest.json": sha})


def remote_of(web, name):
    return client.Remote("http://hosted", TOKEN, opener_of(web), machine_name=name)


def test_a_second_machine_is_shown_but_applies_nothing_until_the_owner_confirms_it(world, settings, no_record):
    settings.SCORE_SYNC_TOKEN, settings.SCORE_MODE = TOKEN, settings.HOSTED
    web = hosted_client()
    pc, conductor = remote_of(web, "pc"), remote_of(web, "conductor")
    committed_by(pc, "pc")
    committed_by(conductor, "conductor")
    assert one_store.record()["name"] == "pc" and one_store.second(THEN) == "conductor"
    item = SyncRequest.objects.create(kind="change", user="joey", payload={"stage": "closeup", "words": "redder"})
    assert conductor.claim(item.pk) is False and "not the store's machine (pc)" in conductor.not_the_store
    item.refresh_from_db()
    assert item.state == "waiting"
    # an agent's request never confirms: no request kind moves the record, nor the sync token alone, nor anyone
    # but the owner, nor the owner without the second ask or for a machine no export came from
    agent = applying.apply({"kind": "store-machine", "user": "joey", "payload": {"machine": "conductor"}},
                           world.source)
    assert agent.state == "refused"
    assert web.post("/api/machine/confirm", json={"machine": "conductor", "sure": True},
                    headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 401
    assert api("mallory").post("/api/machine/confirm", json={"machine": "conductor", "sure": True}).status_code == 403
    owner = api()
    assert owner.post("/api/machine/confirm", json={"machine": "conductor"}).status_code == 400
    assert owner.post("/api/machine/confirm", json={"machine": "elsewhere", "sure": True}).status_code == 409
    assert one_store.record()["name"] == "pc"
    answer = owner.post("/api/machine/confirm", json={"machine": "conductor", "sure": True})
    assert answer.status_code == 200 and "conductor is the store's machine now" in answer.json()["said"]
    assert one_store.record()["by"] == "joey" and one_store.second(THEN) is None
    assert pc.claim(item.pk) is False and conductor.claim(item.pk) is True and conductor.not_the_store is None


def test_stop_everything_and_allow_paid_are_the_owners_asked_twice_and_applied_once(world, settings, conductor,
                                                                                   no_record):
    settings.SCORE_SYNC_TOKEN, settings.SCORE_MODE = TOKEN, settings.HOSTED
    owner = api()
    assert owner.post("/api/machine/stop", json={}).status_code == 400  # the second ask not answered
    assert api("mallory").post("/api/machine/stop", json={"sure": True}).status_code == 403
    assert owner.post("/api/machine/stop", json={"sure": True, "words": "now"}).json()["said"].startswith("queued")
    assert owner.post("/api/machine/allow-paid", json={"sure": True}).json()["said"].startswith("queued")
    assert sorted(SyncRequest.objects.values_list("kind", flat=True)) == ["allow-paid", "stop-everything"]
    assert conductor.calls == []  # hosted, nothing is done: the store's machine applies it
    settings.SCORE_MODE = settings.LOCAL
    remote = remote_of(hosted_client(), "conductor")
    stop = SyncRequest.objects.get(kind="stop-everything")
    item = {"id": stop.pk, "kind": stop.kind, "user": stop.user, "payload": stop.payload}
    applied = client.answered(remote, item, world.source)
    assert applied.state == "done" and conductor.calls == [("stop_all", "joey", "now")]
    assert client.answered(remote, item, world.source) is None  # claimed once: never applied again
    assert conductor.calls == [("stop_all", "joey", "now")]
    stop.refresh_from_db()
    assert stop.state == "done" and '"runs": ["run-1", "run-2"]' in stop.detail
    refused = applying.apply({"kind": "stop-everything", "user": "mallory", "payload": {}}, world.source)
    assert refused.state == "refused" and len(conductor.calls) == 1
    allow = SyncRequest.objects.get(kind="allow-paid")
    applied = client.answered(remote, {"id": allow.pk, "kind": allow.kind, "user": allow.user,
                                       "payload": allow.payload}, world.source)
    assert applied.state == "done" and conductor.calls[-1] == ("allow_paid", "joey", "")


def test_the_kill_switch_refuses_in_an_agents_process_and_off_a_conductor(world, monkeypatch):
    from score.dashboard.pages import actions
    monkeypatch.setitem(sys.modules, "score.conductor", None)
    applied = applying.apply({"kind": "stop-everything", "user": "joey", "payload": {}}, world.source)
    assert applied.state == "refused" and machine.NOT_ON_CONDUCTOR in applied.detail

def test_the_kill_switch_refuses_in_an_agents_process_on_a_conductor(world, monkeypatch, conductor):
    from score.dashboard.pages import actions
    monkeypatch.setattr(actions, "agent_started", lambda: True)
    for kind in ("stop-everything", "allow-paid"):
        applied = applying.apply({"kind": kind, "user": "joey", "payload": {}}, world.source)
        assert applied.state == "refused" and "agent's shell" in applied.detail
    assert conductor.calls == []  # the conductor's kill switch was never reached


def test_a_second_machine_with_a_time_of_no_zone_or_none_breaks_no_page(settings, no_record):
    one_store.kept({"name": "pc", "others": {"naive": "2026-10-18T13:00:00", "broken": "not a time"}})
    assert one_store.second(THEN) == "naive"


def test_the_card_and_the_machine_page_render(world, conductor):
    named(world, "conductor")
    user = get_user_model().objects.create_user("joey", password="a long enough password")
    pages = Client()
    pages.force_login(user)
    home = pages.get("/").content.decode()
    assert "Machine" in home and "conductor" in home and "Stop everything" in home
    assert "Allow paid work again" in home  # the latch is set
    page = pages.get("/machine/").content.decode()
    assert "run.log" in page and "one fault" in page and "score-sync.timer" in page


def test_the_card_says_when_the_cloud_machine_is_off_the_cockpits_pin(world, conductor, monkeypatch):
    named(world, "conductor")
    off = {"checkout": "a" * 40, "pin": "b" * 40, "matches": False}
    monkeypatch.setitem(sys.modules, "score.conductor.health",
                        types.SimpleNamespace(read=lambda: {**HEALTH, "code": off}))
    user = get_user_model().objects.create_user("joey", password="a long enough password")
    pages = Client()
    pages.force_login(user)
    assert "the cloud machine is on aaaaaaaa, the cockpit on bbbbbbbb; it is being updated" in \
        pages.get("/").content.decode()
    assert machine.card({"health": {"code": {**off, "matches": True}}})["code_off"] is False


def test_a_buy_is_refused_on_a_conductor_whose_checkout_is_off_the_pin(monkeypatch, settings):
    """2026-10-25: the checkout never followed the pin and a retry ran Batch 1's old code unnoticed."""
    import score.conductor as real
    monkeypatch.setattr(real, "machine", lambda path=None: {"name": "conductor"})
    monkeypatch.setattr(client, "head", lambda repo: "a" * 40)

    class Pinned:
        def __init__(self, commit):
            self.commit = commit

        def call(self, method, path):
            assert (method, path) == ("GET", "/pin")
            return {"commit": self.commit}
    assert client.pin_refusal(Pinned("b" * 40), "/repo") == (
        "the cloud machine is on aaaaaaaa, the cockpit on bbbbbbbb; it is being updated: buy again in a few minutes")
    assert client.pin_refusal(Pinned("a" * 40), "/repo") is None
    assert client.pin_refusal(Pinned(None), "/repo") is None  # a cockpit reporting no pin
    monkeypatch.setattr(real, "machine", lambda path=None: None)
    assert client.pin_refusal(Pinned("b" * 40), "/repo") is None  # off a conductor


def test_the_sync_and_the_listener_follow_the_kill_switch_latch(monkeypatch):
    from score import conductor
    from score.dashboard.sync import client
    monkeypatch.delenv(conductor.FREE_ONLY, raising=False)
    monkeypatch.setitem(client.LATCHED, "set", False)
    conductor.FREE_ONLY_LATCH.parent.mkdir(parents=True, exist_ok=True)
    conductor.FREE_ONLY_LATCH.write_text(f"{conductor.FREE_ONLY}=1\n")
    try:
        assert client.free_only_followed() and os.environ[conductor.FREE_ONLY] == "1"
    finally:
        conductor.FREE_ONLY_LATCH.unlink()
    assert not client.free_only_followed() and conductor.FREE_ONLY not in os.environ
    monkeypatch.setenv(conductor.FREE_ONLY, "1")  # set by whoever started it (a restore): never taken off here
    assert not client.free_only_followed() and os.environ[conductor.FREE_ONLY] == "1"


def test_on_the_owners_pc_the_card_says_its_runs_and_no_backup_or_bill():
    found = {"machine": {"name": "dupe"}, "health": {"machine": None, "state": None, "runs_active": 1, "backup": None}}
    card = machine.card(found)
    assert card["on_pc"] and card["state"] == "running 1 run"
    assert machine.card({**found, "health": {**found["health"], "runs_active": 0}})["state"] == "idle"
    assert not machine.card({"machine": {"name": "conductor", "size": "POP2"}, "health": {"state": "idle"}})["on_pc"]
