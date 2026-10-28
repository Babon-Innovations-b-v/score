"""The Scaleway backend touches only its own project's resources, and every euro a machine causes is counted.

Every `scw` call is stubbed (and the `subprocess.run` the backend calls `scw` through): nothing is made, read or deleted
on the provider, and the ledger is a file in the sandbox home.

The invariants, each with the break that turns its test red (each applied once and seen red):

- A registry namespace, the runtime key's secret, a bill line, a leftover address and a machine a refused order made
  are taken only when their own record names our project (and the runner's tag, for a machine).
  Break: drop `and space.get("project_id") == project` in `registry_namespace` -> another project's namespace is used.
  Break: drop `if line.get("project_id") != project: continue` in `consumption` -> the bill reads EUR 100.5.
  Break: drop `server.get("project") == project and` in `delete_left_by_refusal` -> srv-other is deleted.
  Break: drop `and QUARANTINED not in ...` in `leftover_addresses` -> the quarantined address is a leftover.
- A machine whose state cannot be read is a refusal its waiter waits out and deletes, never a crash. Break: in
  `start_if_stopped`, the `except subprocess.CalledProcessError` return -> `raise`.
- A public registry namespace is refused. Break: drop the `is_public` refusal in `registry_namespace`.
- A missing runtime key is made scoped to the project alone and kept only in Secret Manager, never on a command line.
  Break: pass `f"data={value}"` instead of `data=@{path}` in `make_runtime_key` -> the secret is on the command line.
- Offers: a processor class in every rent zone with quota, a card class in the card zones only, each zone's type list
  read once; a short type our own run parked is offered as `parked`; a type with no quota is never offered.
  Break: `here = list(classes)` in `offers` -> the card class is offered in the processor zone.
  Break: drop the `parked` rewrite in `offers` -> fr-par-2 stays `shortage`.
- Quotas are read by type and zone; a key that may not read them (403) means "no quota known", not "none allowed".
  Break: `.replace("_", "-")` dropped in `zone_quotas` -> the types do not match. Break: re-raise on 403.
- A machine's disk and address are billed by the started hour from its creation (the October 2026 bill held EUR 71 of
  disks and EUR 37 of addresses the ledger never counted), written as one ledger line when it is deleted.
  Break: `math.floor` for `math.ceil` in `disk_and_address_euros` -> 61 minutes cost one hour.
  Break: drop `record_disk_and_address(...)` in `delete` -> no ledger line.
- An address Scaleway hands us from BAD_ADDRESSES (every machine on it dropped SSH, 2026-10-10 to 13) is swapped for a
  fresh one and kept quarantined; when that cannot be done safely the machine is deleted and the next offer taken.
  Break: drop the project check in `quarantine_bad_address` -> another project's address is detached and tagged.
- A refused order's own machine (HTTP 500 that made it anyway, 2026-10-22) and its own loose address and disk are
  deleted, and the loose ones' euros are the order's ledger line; another order's racing address is left alone.
  Break: drop `left &= loose(project, zone)` in `delete_loose_left_by_refusal` -> ip-racing is deleted too.
  Break: drop the `delete_left_by_refusal(...)` call in `create` -> srv-made stays.
- Deleting something another sweep already deleted is done, not an error (surfaces-bake@wreck, 2026-10-13); any other
  refusal raises. Break: `return False` -> `raise` in `delete`'s `gone_after_failure` branch; or `is_gone` always False.
- This PC's backend (local.py) costs nothing and orders nothing: every class it serves is offered `parked` at EUR 0,
  a class beyond its one 16 GB card is refused at once, a kind too big for the card is refused at its claim, one claim
  holds it at a time, and a delete from another process leaves a claim still held alone.
  Break: `return not found.group(2) and int(found.group(1)) <= 24` -> `return True` in `serves` -> gpu-80gb is offered.
  Break: drop `| fcntl.LOCK_NB` handling (return the machine without the lock) in `take` -> a second claim gets it.
  Break: in `delete`, drop the `except BlockingIOError: ... return False` -> another claim's container is restarted.
- A job is refused by its measured need, not its kind: a characters run of clip steps (4 GB of card, 17 GB of memory
  with the encoder on the processor) takes this PC, a whole characters machine (17 GB of card) or a need past the
  container's memory does not. Break: `card = TOO_BIG.get(kind)` in `refusal` -> the clip run is refused; or drop the
  memory check -> the 40 GB job is taken.
- The container's memory leaves this PC HOST_RESERVE_GB for WSL and the run's own steps beside it: a 43 GB PC gives
  the container 27 GB, and a small PC still 8. Break: `total - HOST_RESERVE_GB` -> `total - 8` -> 35g.
- The container never swaps past its memory, made new or found already made. Break: drop `"--memory-swap",
  memory_cap()` in `memory_arguments` -> the run's swap is unset; or drop the `docker("update", ...)` -> the old
  container keeps its swap.
- This PC's claim runs as many Blender jobs side by side as its container's memory holds at a take's measured peak
  (27 GiB: three; a small PC: one), all on its one card, and every claim puts card_turn.py into the container's Blender
  startup folder. Break: drop `"blender": blender_at_once(...)` from `RUNS_AT_ONCE` -> one slot; or drop
  `card_in_turns()` in `take` -> nothing is copied.
- card_turn.py gives the card to CARD_SLOTS (two) card calls at a time (the Cycles bake, a render) across Blender
  processes, and leaves every other operator call free to run beside it. Break: in `turned`, call `call(...)` without
  `with card_turn(lock_path):` -> five bakes are on the card at once; or `range(CARD_SLOTS)` -> `range(1)` in
  `card_turn` -> one at a time.
"""
import json
import pathlib
import subprocess
import sys
import threading
import time
import types
import urllib.error

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import scaleway  # noqa: E402

OURS = "project-ours"
OTHER = "project-other"
BAD = next(iter(scaleway.BAD_ADDRESSES))


class FakeScw:
    """Answers `scw` calls from a table of (first three arguments) -> answer, recording every call."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []
        self.stored = None

    def __call__(self, *arguments):
        self.calls.append(arguments)
        if arguments[:3] == ("secret", "version", "create"):
            data = next(argument for argument in arguments if argument.startswith("data="))
            self.stored = pathlib.Path(data[len("data=@"):]).read_text()
        return self.answers.get(arguments[:3])

    def made(self, *head):
        return [call for call in self.calls if call[:len(head)] == head]


@pytest.fixture
def ledger_file(monkeypatch, tmp_path):
    """The cloud ledger as a fresh file; its lines read back."""
    import ledger
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.jsonl")
    return lambda: [json.loads(line) for line in ledger.LEDGER.read_text().splitlines()] if ledger.LEDGER.exists() \
        else []


@pytest.fixture
def fake(monkeypatch):
    """A FakeScw with the account and runtime secret stubbed; set `fake.answers` before calling the backend."""
    stub = FakeScw({})
    monkeypatch.setattr(scaleway, "scw", stub)
    monkeypatch.setattr(scaleway, "account", lambda: OURS)
    monkeypatch.setattr(scaleway, "secret", lambda name: json.dumps({"access_key": "AK", "secret_key": "SK"}))
    return stub


def ours_key():
    return {("secret", "secret", "list"): [{"name": scaleway.RUNTIME_KEY_SECRET, "project_id": OURS}]}


def namespace(project, public=False, endpoint="rg/x"):
    return {"name": scaleway.REGISTRY_NAMESPACE, "project_id": project, "is_public": public, "endpoint": endpoint}


# --- only our own project's resources -------------------------------------------------------------------------------

def test_the_registry_is_our_own_private_namespace(fake):
    fake.answers = {**ours_key(), ("registry", "namespace", "list"): [namespace(OURS, endpoint="rg/ours")]}
    assert scaleway.registry() == {"endpoint": "rg/ours", "username": "nologin", "password": "SK"}
    assert not fake.made("registry", "namespace", "create")

    fake.answers = {**ours_key(), ("registry", "namespace", "list"): [namespace(OTHER)],
                    ("registry", "namespace", "create"): namespace(OURS, endpoint="rg/new")}
    assert scaleway.registry()["endpoint"] == "rg/new"
    made = fake.made("registry", "namespace", "create")
    assert len(made) == 1 and f"project-id={OURS}" in made[0] and "is-public=false" in made[0]

    fake.answers = {**ours_key(), ("registry", "namespace", "list"): [namespace(OURS, public=True)]}
    with pytest.raises(SystemExit, match="public"):
        scaleway.registry()


def test_a_missing_runtime_key_is_scoped_to_the_project_and_kept_only_in_the_secret(fake):
    fake.answers = {("secret", "secret", "list"): [{"name": scaleway.RUNTIME_KEY_SECRET, "project_id": OTHER}],
                    ("iam", "application", "list"): [], ("iam", "application", "create"): {"id": "app"},
                    ("iam", "policy", "list"): [],
                    ("iam", "api-key", "create"): {"access_key": "AK2", "secret_key": "SK2"},
                    ("secret", "secret", "create"): {"id": "held"}}
    scaleway.runtime_key(OURS)
    policy = fake.made("iam", "policy", "create")[0]
    assert f"rules.0.project-ids.0={OURS}" in policy and "application-id=app" in policy
    assert {argument.split("=", 1)[1] for argument in policy if ".permission-set-names." in argument} == {
        "ObjectStorageFullAccess", "ContainerRegistryFullAccess"}
    assert f"default-project-id={OURS}" in fake.made("iam", "api-key", "create")[0]
    assert f"project-id={OURS}" in fake.made("secret", "secret", "create")[0]
    assert json.loads(fake.stored) == {"access_key": "AK2", "secret_key": "SK2"}
    assert not any("SK2" in argument for call in fake.calls for argument in call)


def test_the_bill_keeps_only_the_projects_own_lines(fake):
    fake.answers = {("billing", "consumption", "list"): [
        {"project_id": OURS, "product_name": "L4", "sku": "s", "unit": "minute", "billed_quantity": "10",
         "value": {"units": 1, "nanos": 500000000}},
        {"project_id": OTHER, "product_name": "L4", "sku": "x", "value": {"units": 99}}]}
    assert scaleway.month_spend(OURS) == 1.5


def test_a_quarantined_or_foreign_address_is_never_a_leftover(monkeypatch):
    addresses = [{"id": "ip-q", "address": BAD, "project": OURS, "server": None, "tags": [scaleway.QUARANTINED]},
                 {"id": "ip-l", "address": "151.115.1.1", "project": OURS, "server": None, "tags": []},
                 {"id": "ip-x", "address": "151.115.2.2", "project": OTHER, "server": None, "tags": []},
                 {"id": "ip-on", "address": "151.115.3.3", "project": OURS, "server": {"id": "s"}, "tags": []}]
    monkeypatch.setattr(scaleway, "scw", lambda *arguments: addresses)
    assert scaleway.leftover_addresses(OURS, ("pl-waw-2",)) == [("ip-l", "pl-waw-2", "151.115.1.1")]


# --- offers and quotas ----------------------------------------------------------------------------------------------

def offered(monkeypatch, tmp_path, classes, zones, processor_zones, listed, quotas, parked=()):
    """scaleway.offers on stubbed zones, type lists (`listed` in every zone), quotas and parked records; (the offers,
    the zones whose type list was read)."""
    read = []
    monkeypatch.setattr(scaleway, "scw", lambda *arguments: read.append(arguments[-1]) or listed)
    monkeypatch.setattr(scaleway, "price", lambda machine_type, zone: (0.02, 60))
    folder = tmp_path / "parked"
    folder.mkdir(exist_ok=True)
    for index, record in enumerate(parked):
        (folder / f"{index}.json").write_text(record if isinstance(record, str) else json.dumps(record))
    monkeypatch.setattr(scaleway, "PARKED", folder)
    monkeypatch.setattr(scaleway, "ZONES", zones)
    monkeypatch.setattr(scaleway, "PROCESSOR_ZONES", processor_zones)
    monkeypatch.setattr(scaleway, "zone_quotas", lambda: quotas)
    return scaleway.offers(classes), read


def test_a_processor_class_is_offered_wherever_it_has_quota_and_a_card_class_only_in_card_zones(monkeypatch, tmp_path):
    """Owner, 2026-10-23 ("cant u just get a faster cpu"): the big POP2 types were short in the card zones and in stock
    elsewhere; a type with no quota (POP2-HC-64C-128G) is never ordered."""
    listed = [{"name": "POP2-HC-64C-128G", "availability": "available"},
              {"name": "POP2-HC-48C-96G", "availability": "available"},
              {"name": "L4-1-24G", "availability": "available"}]
    quotas = {("POP2-HC-48C-96G", "fr-par-1"): 1, ("POP2-HC-48C-96G", "nl-ams-2"): 1, ("L4-1-24G", "fr-par-1"): 50,
              ("L4-1-24G", "nl-ams-2"): 50}
    found, read = offered(monkeypatch, tmp_path, ["cpu-64c-128gb", "cpu-48c-96gb", "gpu-24gb"], ("fr-par-1",),
                          ("nl-ams-2", "fr-par-1"), listed, quotas)
    assert sorted((offer.machine_class, offer.zone) for offer in found) == [
        ("cpu-48c-96gb", "fr-par-1"), ("cpu-48c-96gb", "nl-ams-2"), ("gpu-24gb", "fr-par-1")]
    assert read == ["zone=fr-par-1", "zone=nl-ams-2"]
    _, read = offered(monkeypatch, tmp_path, ["gpu-24gb"], ("fr-par-1",), ("nl-ams-2",), listed, quotas)
    assert read == ["zone=fr-par-1"]  # a card-only ask reads no processor zone


def test_a_type_short_where_our_run_parked_one_is_offered_as_parked(monkeypatch, tmp_path):
    """2026-10-12: every POP2-32C-128G was short because our runs held them parked, and blender_cloud refused for no
    stock instead of taking one. An expired record and one half-written do not count."""
    import time
    parked = [{"type": "POP2-32C-128G", "zone": "fr-par-2", "until": time.time() + 600},
              {"type": "POP2-32C-128G", "zone": "pl-waw-2", "until": time.time() - 60}, "{\"type\": "]
    quotas = {("POP2-32C-128G", "fr-par-2"): 2, ("POP2-32C-128G", "pl-waw-2"): 2}
    found, _ = offered(monkeypatch, tmp_path, ["cpu-32c-128gb"], ("fr-par-2", "pl-waw-2"), (),
                       [{"name": "POP2-32C-128G", "availability": "shortage"}], quotas, parked)
    assert {offer.zone: offer.stock_word for offer in found} == {"fr-par-2": "parked", "pl-waw-2": "shortage"}
    assert {offer.zone: offer.stock for offer in found} == {"fr-par-2": 1, "pl-waw-2": 2}


@pytest.fixture
def quota_world(fake, monkeypatch):
    fake.answers = {("account", "project", "get"): {"organization_id": "org"}, ("config", "get", "secret-key"): "key"}
    scaleway.zone_quotas.cache_clear()
    yield monkeypatch
    scaleway.zone_quotas.cache_clear()


def test_quotas_are_read_by_type_and_zone(quota_world):
    pages = [{"name": "cp_servers_type_POP2_HC_48C_96G", "limits": [{"zone": "nl-ams-2", "limit": 1},
                                                                    {"zone": "pl-waw-1", "limit": 0}]},
             {"name": "cp_servers_type_L4_1_24G", "limits": [{"zone": "fr-par-1", "unlimited": True}]},
             {"name": "adt_beta", "limits": [{"zone": "fr-par-1", "limit": 1}]}]
    quota_world.setattr(scaleway, "quota_pages",
                        lambda organization, key: pages if (organization, key) == ("org", "key") else [])
    assert scaleway.zone_quotas() == {("POP2-HC-48C-96G", "nl-ams-2"): 1, ("POP2-HC-48C-96G", "pl-waw-1"): 0,
                                      ("L4-1-24G", "fr-par-1"): float("inf")}


def test_a_key_that_may_not_read_quotas_leaves_them_unknown(quota_world):
    """The conductor's key reads no quota (HTTP 403, 2026-10-24): the Buy stopped at its pool."""
    def refused(organization, key):
        raise urllib.error.HTTPError("https://api.scaleway.com", 403, "Forbidden", {}, None)
    quota_world.setattr(scaleway, "quota_pages", refused)
    assert scaleway.zone_quotas() is None


# --- every euro counted ---------------------------------------------------------------------------------------------

def test_disk_and_address_are_billed_by_the_started_hour_and_written_on_delete(monkeypatch, ledger_file):
    server = {"id": "s1", "name": "blender-1", "commercial_type": "L4-1-24G", "creation_date": "2026-10-12T10:00:00Z",
              "public_ips": [{"id": "ip"}]}
    created = 1791799200.0  # 2026-10-12T10:00:00Z
    one_hour = 60 * 0.00013 + 0.005  # 60 GB at EUR 0.00013 a GB-hour, one address at EUR 0.005 an hour
    assert scaleway.disk_and_address_euros(server, 60, created + 61 * 60) == pytest.approx(2 * one_hour)
    assert scaleway.disk_and_address_euros(server, 60, created + 2 * 60) == pytest.approx(one_hour)

    monkeypatch.setattr(scaleway, "server_record", lambda *_: server)
    monkeypatch.setattr(scaleway, "disk_gb", lambda *_: 60.0)
    monkeypatch.setattr(scaleway, "terminate", lambda *_: True)
    assert scaleway.delete("s1", "fr-par-2")
    monkeypatch.setattr(scaleway, "server_record", lambda *_: None)  # already gone: nothing deleted, nothing written
    assert not scaleway.delete("s1", "fr-par-2")
    lines = ledger_file()
    assert [line["kind"] for line in lines] == ["disk-and-address"] and lines[0]["euros"] >= one_hour


def created_with(monkeypatch, address, failing=(), owner=OURS):
    """create() on a stubbed Scaleway whose new machine got `address`; failing: the `ip` commands that fail. (its
    answer, the scw calls past the loose reads, the machines deleted)."""
    calls, deleted = [], []

    def fake_scw(*arguments):
        if arguments[2] != "list":
            calls.append(arguments)
        if arguments[:2] == ("instance", "ip") and arguments[2] in failing:
            raise RuntimeError(f"scw ip {arguments[2]} failed")
        return {"ip": {"id": arguments[3], "project": owner}} if arguments[:3] == ("instance", "ip", "get") else {}

    server = {"id": "srv-1", "public_ips": [{"id": "ip-1", "address": address, "family": "inet"}]}
    monkeypatch.setattr(scaleway, "scw", fake_scw)
    monkeypatch.setattr(scaleway, "delete", lambda server_id, zone: deleted.append(server_id) or True)
    monkeypatch.setattr(subprocess, "run", lambda *arguments, **options: types.SimpleNamespace(
        returncode=0, stdout=json.dumps(server), stderr=""))
    offer = types.SimpleNamespace(type="POP2-32C-128G", zone="pl-waw-2", machine_class="cpu-32c-128gb", price=0.02)
    return scaleway.create(OURS, offer, "blender-1", [], 60), calls, deleted


def test_a_bad_address_is_swapped_and_quarantined_or_the_machine_deleted(monkeypatch, ledger_file):
    answer, calls, deleted = created_with(monkeypatch, BAD)
    assert answer == ("srv-1", None) and not deleted
    assert [call[2] for call in calls] == ["create", "get", "detach", "update"]
    assert "server=srv-1" in calls[0] and f"project-id={OURS}" in calls[0]
    assert f"tags.0={scaleway.QUARANTINED}" in calls[3] and calls[3][3] == "ip-1"

    assert created_with(monkeypatch, "151.115.10.10")[1:] == ([], [])  # a good address is left as it is

    for failing, owner in ((("detach",), OURS), ((), OTHER)):
        answer, calls, deleted = created_with(monkeypatch, BAD, failing, owner)
        assert answer[0] is None and deleted == ["srv-1"]
        assert not any(call[2] == "update" for call in calls)  # nothing tagged past the failed step or the check


def test_a_refused_orders_own_machine_is_deleted_at_once(monkeypatch, ledger_file):
    """2026-10-22: an order refused with HTTP 500 had made its machine (stopped, billed, unwatched)."""
    listed = [{"id": "srv-made", "name": "masks-1", "project": OURS, "tags": [scaleway.TAG]},
              {"id": "srv-other", "name": "masks-1", "project": OTHER, "tags": [scaleway.TAG]},
              {"id": "srv-untagged", "name": "masks-1", "project": OURS, "tags": []},
              {"id": "srv-near", "name": "masks-10", "project": OURS, "tags": [scaleway.TAG]}]
    deleted = []
    monkeypatch.setattr(scaleway, "scw",
                        lambda *arguments: listed if arguments[:3] == ("instance", "server", "list") else [])
    monkeypatch.setattr(scaleway, "delete", lambda server_id, zone: deleted.append((server_id, zone)) or True)
    monkeypatch.setattr(subprocess, "run", lambda *arguments, **options: types.SimpleNamespace(
        returncode=1, stdout="", stderr='{"error":"cannot create the server: http error 500"}'))
    offer = types.SimpleNamespace(type="L4-1-24G", zone="fr-par-1", machine_class="gpu-24gb", price=0.013)
    answer = scaleway.create(OURS, offer, "masks-1", [], 60)
    assert answer[0] is None and "500" in answer[1]
    assert deleted == [("srv-made", "fr-par-1")]
    import ledger
    assert [line["state"] for line in ledger_file() if line["kind"] in (ledger.RENT_STARTED, ledger.RENT_REFUSED)] == [
        "started", "refused"]  # the order's started line, closed by its refusal


def test_a_refused_orders_own_loose_address_and_disk_are_deleted_and_counted(monkeypatch, ledger_file):
    """Only what the order made: loose after it, not before, and still loose after the settle (another order's address
    is loose for a moment before its machine takes it)."""
    reads, deleted = [], []
    old_ip = {"id": "ip-old", "address": "1.1.1.1", "project": OURS, "server": None, "tags": []}
    new_ip = {"id": "ip-new", "address": "2.2.2.2", "project": OURS, "server": None, "tags": []}
    racing_ip = {"id": "ip-racing", "address": "3.3.3.3", "project": OURS, "server": None, "tags": []}
    new_disk = {"id": "disk-new", "name": "masks-1", "project_id": OURS, "references": []}

    def scw(*arguments):
        if arguments[:3] == ("instance", "ip", "list"):
            reads.append(1)
            return [old_ip] if len(reads) == 1 else ([old_ip, new_ip, racing_ip] if len(reads) == 2
                                                      else [old_ip, new_ip, {**racing_ip, "server": {"id": "x"}}])
        if arguments[:3] == ("block", "volume", "list"):
            return [] if len(reads) == 1 else [new_disk]
        if arguments[2] == "delete":
            deleted.append(arguments[3])
        return []
    monkeypatch.setattr(scaleway, "scw", scw)
    monkeypatch.setattr(scaleway.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(subprocess, "run", lambda *arguments, **options: types.SimpleNamespace(
        returncode=1, stdout="", stderr="out of stock"))
    offer = types.SimpleNamespace(type="L4-1-24G", zone="fr-par-1", machine_class="gpu-24gb", price=0.013)
    answer = scaleway.create(OURS, offer, "masks-1", [], 60)
    assert answer[0] is None and sorted(deleted) == ["disk-new", "ip-new"]
    fees = [line for line in ledger_file() if line["kind"] == "disk-and-address"]
    assert len(fees) == 1 and fees[0]["name"] == "masks-1"
    assert fees[0]["euros"] == pytest.approx(0.005 + 60 * 0.00013)  # one address-hour, 60 GB for one hour


# --- deleting what is already gone ----------------------------------------------------------------------------------

def deleting(monkeypatch, still_there):
    """delete() on a stubbed Scaleway whose terminate is refused (two sweeps on one leftover), the machine read again
    after it `still_there`. (its answer or the error it raised, the ledger lines written)."""
    reads, written = [], []

    def run(command, **options):
        if command[2:4] == ["server", "get"]:
            reads.append(1)
            if len(reads) > 1 and not still_there:
                return types.SimpleNamespace(returncode=1, stdout="", stderr="server not found")
            return types.SimpleNamespace(returncode=0, stdout=json.dumps({"id": "srv-1", "volumes": {}}), stderr="")
        return types.SimpleNamespace(returncode=1, stdout="",
                                     stderr="Failed to detach block volume v-1: volume_id does not respect constraint")
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(scaleway.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(scaleway, "record_disk_and_address", lambda server, gb, now: written.append(server["id"]))
    try:
        return scaleway.delete("srv-1", "pl-waw-2"), written
    except RuntimeError as error:
        return error, written


def test_a_leftover_another_sweep_deleted_is_gone_and_a_machine_that_stays_raises(monkeypatch):
    """surfaces-bake@wreck, 2026-10-13: two sweeps deleted one leftover; the second's refused detach killed its job."""
    assert deleting(monkeypatch, still_there=False) == (False, [])
    answer, written = deleting(monkeypatch, still_there=True)
    assert isinstance(answer, RuntimeError) and "does not respect constraint" in str(answer) and not written


def test_deleting_an_address_or_disk_already_gone_is_done_and_another_failure_raises(monkeypatch):
    def refusing(text):
        def scw(*arguments):
            raise subprocess.CalledProcessError(1, ["scw", *arguments], output="", stderr=text)
        return scw
    monkeypatch.setattr(scaleway, "scw", refusing("ip not found"))
    scaleway.delete_address("ip-1", "pl-waw-2")
    monkeypatch.setattr(scaleway, "scw", refusing("volume not found"))
    scaleway.delete_disk("v-1", "pl-waw-2")
    monkeypatch.setattr(scaleway, "scw", refusing("permission denied"))
    with pytest.raises(subprocess.CalledProcessError):
        scaleway.delete_disk("v-1", "pl-waw-2")


def test_a_machine_whose_state_cannot_be_read_is_refused_not_raised(monkeypatch):
    def unreadable(*arguments):
        raise subprocess.CalledProcessError(1, ["scw"], "", "server not found")
    monkeypatch.setattr(scaleway, "scw", unreadable)
    assert "server not found" in scaleway.start_if_stopped("id", "pl-waw-2")


def test_this_pc_orders_nothing_costs_nothing_and_holds_one_claim(monkeypatch, tmp_path):
    import local
    monkeypatch.setattr(local, "LOCK", tmp_path / "this-pc.lock")
    monkeypatch.setattr(local, "running", lambda public_key: "172.17.0.2")
    restarted = []
    monkeypatch.setattr(local, "docker",
                        lambda *arguments, **_: arguments[0] == "restart" and restarted.append(arguments))
    offers = local.offers(["gpu-80gb", "gpu-24gb", "cpu-32c-128gb", "gpu-24gb-x2"])
    assert [offer.machine_class for offer in offers] == ["gpu-24gb", "cpu-32c-128gb"]
    assert {(offer.price, offer.stock_word) for offer in offers} == {(0.0, "parked")}  # batch.rent orders nothing
    with pytest.raises(SystemExit, match="cloud-only"):
        local.offers(["gpu-48gb", "gpu-80gb"])
    with pytest.raises(ValueError, match="30 GB"):
        local.take("judge", "key")
    first = local.take("blender", "key")
    assert first["here"] and first["price"] == 0.0 and first["host"] == "172.17.0.2"
    assert local.take("blender", "key") is None  # one claim at a time
    assert local.delete("score-this-pc:another", "this-pc") is False and not restarted  # a watchdog's late delete
    assert local.delete(first["id"], "this-pc") is True and restarted  # its own claim ends: the container restarted
    assert local.take("pixal", "key") is not None


def test_this_pc_refuses_a_job_by_its_measured_need_not_its_kind(monkeypatch, tmp_path):
    import local
    monkeypatch.setattr(local, "LOCK", tmp_path / "this-pc.lock")
    monkeypatch.setattr(local, "running", lambda public_key: "172.17.0.2")
    monkeypatch.setattr(local, "memory_cap", lambda: "35g")
    with pytest.raises(ValueError, match="17 GB of card"):
        local.take("characters", "key")  # the whole machine: Kimodo's encoder on the card
    with pytest.raises(ValueError, match="40 GB of memory"):
        local.take("characters", "key", {"card_gb": 4, "memory_gb": 40})
    assert local.take("characters", "key", {"card_gb": 4, "memory_gb": 17})["here"]


def test_this_pc_container_leaves_room_for_wsl_and_the_runs_own_steps(monkeypatch):
    import local
    pages = {"SC_PAGE_SIZE": 4096, "SC_PHYS_PAGES": 43 * 2**30 // 4096}
    monkeypatch.setattr(local.os, "sysconf", pages.get)
    assert local.memory_cap() == "27g"
    pages["SC_PHYS_PAGES"] = 12 * 2**30 // 4096
    assert local.memory_cap() == "8g"



def test_this_pc_container_never_swaps_past_its_memory(monkeypatch):
    import local
    calls = []

    def docker(*arguments, check=True, **options):
        calls.append(arguments)
        made = any(call[0] == "run" for call in calls)
        return types.SimpleNamespace(returncode=0 if arguments[0] != "inspect" or made or found else 1,
                                     stdout="true")
    monkeypatch.setattr(local, "docker", docker)
    monkeypatch.setattr(local, "memory_cap", lambda: "27g")
    monkeypatch.setattr(local, "answering", lambda: "172.17.0.2")
    monkeypatch.setattr(local.shutil, "which", lambda name: "/usr/bin/docker")
    for found in (False, True):
        calls.clear()
        local.running("ssh-ed25519 key")
        limited = [call for call in calls if call[0] in ("run", "update")]
        assert len(limited) == 1 and limited[0][0] == ("update" if found else "run"), calls
        swap = limited[0].index("--memory-swap")
        assert limited[0][swap + 1] == "27g" == limited[0][limited[0].index("--memory") + 1], limited


def test_this_pc_runs_blender_jobs_side_by_side_as_its_memory_holds_with_the_card_in_turns(monkeypatch, tmp_path):
    import importlib
    import capacity
    import card_turn
    import local
    import spread
    assert local.blender_at_once(8) == 1
    pages = {"SC_PAGE_SIZE": 4096, "SC_PHYS_PAGES": 43 * 2**30 // 4096}  # this PC: a 27 GiB container
    monkeypatch.setattr(local.os, "sysconf", pages.get)
    try:
        importlib.reload(local)
        monkeypatch.setattr(local, "LOCK", tmp_path / "this-pc.lock")
        monkeypatch.setattr(local, "running", lambda public_key: "172.17.0.2")
        monkeypatch.setattr(capacity.provider, "cloud", local)
        calls = []
        monkeypatch.setattr(local, "docker", lambda *arguments, **_: calls.append(arguments))
        machine = local.take("blender", "key")
        assert ("cp", str(local.CARD_TURN), f"{local.MACHINE}:{card_turn.STARTUP}/card_turn.py") in calls
        assert spread.slots("blender", machine) == [0, 0, 0]  # three side by side, all on the one card
        assert spread.slots("pixal", machine) == [0]
        local.delete(machine["id"], local.ZONE)
    finally:
        monkeypatch.undo()
        importlib.reload(local)


class Operator:
    """A bpy.ops operator as card_turn sees it: its name, and a call that counts the card calls running at once."""
    on_card, most, guard = [0], [0], threading.Lock()

    def __init__(self, name):
        self.name = name

    def idname_py(self):
        return self.name

    def __call__(self, *_arguments, **_keywords):
        import card_turn
        card = self.name in card_turn.CARD_OPS
        with Operator.guard:
            Operator.on_card[0] += card
            Operator.most[0] = max(Operator.most[0], Operator.on_card[0])
        time.sleep(0.05)
        with Operator.guard:
            Operator.on_card[0] -= card
        return {"FINISHED"}


def test_card_turn_gives_the_card_to_its_slots_of_card_calls_at_a_time(tmp_path):
    import card_turn
    lock = str(tmp_path / "card.lock")
    call = card_turn.turned(Operator.__call__, lock)
    names = ["object.bake", "render.render", "object.bake", "object.bake", "render.opengl"]
    threads = [threading.Thread(target=call, args=(Operator(name),)) for name in names]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert Operator.most[0] == card_turn.CARD_SLOTS == 2 and call.card_turn  # its slots full, never more
    with card_turn.card_turn(lock), card_turn.card_turn(lock):  # bakes fill the card: a selection still runs
        beside = threading.Thread(target=call, args=(Operator("object.select_all"),))
        beside.start()
        beside.join(5)
        assert not beside.is_alive()
