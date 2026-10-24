"""Checks for the Scaleway backend's container path (registry, object_store and the runtime key), with every `scw`
call stubbed: nothing is made or read on the provider.

Run: .venv/bin/python tools/cloud/backends/scaleway_test.py   (make tests runs it)
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import scaleway  # noqa: E402

OURS = "project-ours"
OTHER = "project-other"


class FakeScw:
    """Answers `scw` calls from a table of (first three arguments) -> answer, recording every call."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def __call__(self, *arguments):
        self.calls.append(arguments)
        if arguments[:3] == ("secret", "version", "create"):
            data = next(argument for argument in arguments if argument.startswith("data=@"))
            self.stored = pathlib.Path(data[len("data=@"):]).read_text()
        return self.answers.get(arguments[:3])

    def made(self, *head):
        return [call for call in self.calls if call[:len(head)] == head]


def with_fake(answers, check):
    """Run `check(fake)` with the backend's scw, account, secret and bucket calls stubbed."""
    kept = scaleway.scw, scaleway.account, scaleway.secret, scaleway.make_bucket
    fake = FakeScw(answers)
    scaleway.scw, scaleway.account = fake, lambda: OURS
    scaleway.secret = lambda name: json.dumps({"access_key": "AK", "secret_key": "SK"})
    scaleway.make_bucket = lambda store: fake.calls.append(("bucket", store["bucket"]))
    try:
        check(fake)
    finally:
        scaleway.scw, scaleway.account, scaleway.secret, scaleway.make_bucket = kept


def key_secret(project):
    return {("secret", "secret", "list"): [{"name": scaleway.RUNTIME_KEY_SECRET, "project_id": project}]}


def test_an_existing_private_namespace_of_ours_is_used():
    answers = {**key_secret(OURS), ("registry", "namespace", "list"): [
        {"name": scaleway.REGISTRY_NAMESPACE, "project_id": OURS, "is_public": False, "endpoint": "rg/ours"}]}

    def check(fake):
        assert scaleway.registry() == {"endpoint": "rg/ours", "username": "nologin", "password": "SK"}
        assert not fake.made("registry", "namespace", "create")
    with_fake(answers, check)


def test_a_namespace_of_another_project_is_never_taken():
    answers = {**key_secret(OURS),
               ("registry", "namespace", "list"): [
                   {"name": scaleway.REGISTRY_NAMESPACE, "project_id": OTHER, "is_public": False, "endpoint": "rg/x"}],
               ("registry", "namespace", "create"): {"name": scaleway.REGISTRY_NAMESPACE, "project_id": OURS,
                                                     "is_public": False, "endpoint": "rg/new"}}

    def check(fake):
        assert scaleway.registry()["endpoint"] == "rg/new"
        made = fake.made("registry", "namespace", "create")
        assert len(made) == 1 and f"project-id={OURS}" in made[0] and "is-public=false" in made[0]
    with_fake(answers, check)


def test_a_public_namespace_is_refused():
    answers = {**key_secret(OURS), ("registry", "namespace", "list"): [
        {"name": scaleway.REGISTRY_NAMESPACE, "project_id": OURS, "is_public": True, "endpoint": "rg/ours"}]}

    def check(fake):
        try:
            scaleway.registry()
        except SystemExit as refusal:
            assert "public" in str(refusal)
        else:
            raise AssertionError("a public namespace was taken")
    with_fake(answers, check)


def test_the_object_store_names_its_bucket_and_makes_it_once():
    def check(fake):
        store = scaleway.object_store()
        assert store == {"endpoint": "https://s3.fr-par.scw.cloud", "region": "fr-par", "bucket": scaleway.BUCKET,
                         "access_key": "AK", "secret_key": "SK"}
        assert ("bucket", scaleway.BUCKET) in fake.calls
    with_fake(key_secret(OURS), check)


def test_a_missing_key_is_made_scoped_to_the_project_and_kept_only_in_the_secret():
    answers = {("secret", "secret", "list"): [{"name": scaleway.RUNTIME_KEY_SECRET, "project_id": OTHER}],
               ("iam", "application", "list"): [],
               ("iam", "application", "create"): {"id": "app"},
               ("iam", "policy", "list"): [],
               ("iam", "api-key", "create"): {"access_key": "AK2", "secret_key": "SK2"},
               ("secret", "secret", "create"): {"id": "held"}}

    def check(fake):
        scaleway.runtime_key(OURS)
        policy = fake.made("iam", "policy", "create")[0]
        assert f"rules.0.project-ids.0={OURS}" in policy and "application-id=app" in policy
        assert {argument.split("=", 1)[1] for argument in policy if ".permission-set-names." in argument} == set(
            scaleway.RUNTIME_PERMISSIONS)
        assert f"default-project-id={OURS}" in fake.made("iam", "api-key", "create")[0]
        assert f"project-id={OURS}" in fake.made("secret", "secret", "create")[0]
        assert json.loads(fake.stored) == {"access_key": "AK2", "secret_key": "SK2"}
        assert not any("SK2" in argument for call in fake.calls for argument in call)
    with_fake(answers, check)


def test_a_machines_disk_and_address_are_billed_by_the_started_hour():
    """Fault (2026-10-12): the bill held EUR 71 of disks and EUR 37 of addresses the ledger never counted; Scaleway
    bills each by the started hour from the machine's creation."""
    server = {"creation_date": "2026-10-12T10:00:00Z", "public_ips": [{"id": "ip"}]}
    created = 1791799200.0  # 2026-10-12T10:00:00Z
    one_hour = 60 * scaleway.DISK_EUROS_A_GB_HOUR + scaleway.ADDRESS_EUROS_AN_HOUR
    assert abs(scaleway.disk_and_address_euros(server, 60, created + 61 * 60) - 2 * one_hour) < 1e-9
    assert abs(scaleway.disk_and_address_euros(server, 60, created + 2 * 60) - one_hour) < 1e-9


def test_a_deleted_machine_writes_its_disk_and_address_to_the_ledger():
    import ledger

    server = {"id": "s1", "name": "blender-1", "commercial_type": "L4-1-24G", "creation_date": "2026-10-12T10:00:00Z",
              "public_ips": [{"id": "ip"}]}
    written = []
    kept = scaleway.server_record, scaleway.disk_gb, scaleway.terminate, ledger.record
    scaleway.server_record, scaleway.disk_gb = (lambda *_: server), (lambda *_: 60.0)
    scaleway.terminate, ledger.record = (lambda *_: True), written.append
    try:
        assert scaleway.delete("s1", "fr-par-2")
        scaleway.server_record = lambda *_: None  # gone already: nothing deleted, nothing written
        assert not scaleway.delete("s1", "fr-par-2")
    finally:
        scaleway.server_record, scaleway.disk_gb, scaleway.terminate, ledger.record = kept
    assert len(written) == 1 and written[0]["kind"] == "disk-and-address" and written[0]["euros"] > 0


def test_the_bill_keeps_only_the_projects_own_lines():
    answers = {("billing", "consumption", "list"): [
        {"project_id": OURS, "product_name": "L4", "sku": "/instance/server/l4_1_24g/fr-par-2", "unit": "minute",
         "billed_quantity": "10", "value": {"units": 1, "nanos": 500000000}},
        {"project_id": OTHER, "product_name": "L4", "sku": "x", "value": {"units": 99}}]}

    def check(fake):
        assert scaleway.month_spend(OURS) == 1.5
    with_fake(answers, check)


def test_a_type_short_in_a_zone_where_we_parked_one_is_offered_as_parked():
    """Fault (2026-10-12, people-turntable and others): every POP2-32C-128G was short because our runs held them
    parked, and blender_cloud refused the call for no stock instead of taking one."""
    import tempfile
    import time
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "a.json").write_text(json.dumps({"type": "POP2-32C-128G", "zone": "fr-par-2",
                                               "until": time.time() + 600}))
    (folder / "b.json").write_text(json.dumps({"type": "POP2-32C-128G", "zone": "pl-waw-2", "until": time.time() - 60}))
    (folder / "c.json").write_text("{\"type\": ")  # one being written as it is read
    listed = [{"name": "POP2-32C-128G", "availability": "shortage"}]
    quotas = {("POP2-32C-128G", "fr-par-2"): 2, ("POP2-32C-128G", "pl-waw-2"): 2}
    found = {offer.zone: offer.stock_word
             for offer in offered(["cpu-32c-128gb"], ("fr-par-2", "pl-waw-2"), (), listed, quotas, folder)}
    assert found == {"fr-par-2": "parked", "pl-waw-2": "shortage"}, found


def offered(classes, zones, processor_zones, listed, quotas, parked=None):
    """scaleway.offers on stubbed zones, type lists (`listed` in every zone), quotas and parked folder; the zones it
    read the type lists of, as `offered.read`."""
    import tempfile
    kept = (scaleway.scw, scaleway.price, scaleway.PARKED, scaleway.ZONES, scaleway.PROCESSOR_ZONES,
            scaleway.zone_quotas)
    offered.read = []
    scaleway.scw = lambda *arguments: offered.read.append(arguments[-1]) or listed
    scaleway.price = lambda machine_type, zone: (0.02, 60)
    scaleway.PARKED = parked or pathlib.Path(tempfile.mkdtemp())
    scaleway.ZONES, scaleway.PROCESSOR_ZONES, scaleway.zone_quotas = zones, processor_zones, lambda: quotas
    try:
        return scaleway.offers(classes)
    finally:
        (scaleway.scw, scaleway.price, scaleway.PARKED, scaleway.ZONES, scaleway.PROCESSOR_ZONES,
         scaleway.zone_quotas) = kept


def test_a_processor_class_is_offered_in_every_zone_with_quota_and_a_card_class_in_the_card_zones():
    """The owner, 2026-10-23 ("cant u just get a faster cpu"): the big POP2 types were short in the card zones and in
    stock elsewhere, and a type with no quota (POP2-HC-64C-128G) is never ordered."""
    listed = [{"name": "POP2-HC-64C-128G", "availability": "available"},
              {"name": "POP2-HC-48C-96G", "availability": "available"},
              {"name": "L4-1-24G", "availability": "available"}]
    quotas = {("POP2-HC-48C-96G", "fr-par-1"): 1, ("POP2-HC-48C-96G", "nl-ams-2"): 1, ("L4-1-24G", "fr-par-1"): 50,
              ("L4-1-24G", "nl-ams-2"): 50}
    found = offered(["cpu-64c-128gb", "cpu-48c-96gb", "gpu-24gb"], ("fr-par-1",), ("nl-ams-2", "fr-par-1"), listed,
                    quotas)
    places = sorted((offer.machine_class, offer.zone) for offer in found)
    assert places == [("cpu-48c-96gb", "fr-par-1"), ("cpu-48c-96gb", "nl-ams-2"), ("gpu-24gb", "fr-par-1")], places
    assert offered.read == ["zone=fr-par-1", "zone=nl-ams-2"], offered.read  # each zone read once
    offered(["gpu-24gb"], ("fr-par-1",), ("nl-ams-2",), listed, quotas)
    assert offered.read == ["zone=fr-par-1"], offered.read  # a card-only ask reads no processor zone


def test_the_quota_list_is_read_by_type_and_zone():
    pages = [{"name": "cp_servers_type_POP2_HC_48C_96G", "limits": [{"zone": "nl-ams-2", "limit": 1},
                                                                    {"zone": "pl-waw-1", "limit": 0}]},
             {"name": "cp_servers_type_L4_1_24G", "limits": [{"zone": "fr-par-1", "unlimited": True}]},
             {"name": "adt_beta", "limits": [{"zone": "fr-par-1", "limit": 1}]}]
    answers = {("account", "project", "get"): {"organization_id": "org"}, ("config", "get", "secret-key"): "key"}
    kept = scaleway.quota_pages
    scaleway.quota_pages = lambda organization, key: pages if (organization, key) == ("org", "key") else []
    scaleway.zone_quotas.cache_clear()

    def check(fake):
        found = scaleway.zone_quotas()
        assert found == {("POP2-HC-48C-96G", "nl-ams-2"): 1, ("POP2-HC-48C-96G", "pl-waw-1"): 0,
                         ("L4-1-24G", "fr-par-1"): float("inf")}, found
    try:
        with_fake(answers, check)
    finally:
        scaleway.quota_pages = kept
        scaleway.zone_quotas.cache_clear()


def test_a_key_that_may_not_read_quotas_offers_every_type_in_stock():
    """The conductor's key reads no quota (HTTP 403, 2026-10-24): the Buy stopped at its pool; now no quota is known."""
    import urllib.error
    answers = {("account", "project", "get"): {"organization_id": "org"}, ("config", "get", "secret-key"): "key"}
    kept = scaleway.quota_pages

    def refused(organization, key):
        raise urllib.error.HTTPError("https://api.scaleway.com", 403, "Forbidden", {}, None)
    scaleway.quota_pages = refused
    scaleway.zone_quotas.cache_clear()
    try:
        with_fake(answers, lambda fake: scaleway.zone_quotas() is None or (_ for _ in ()).throw(AssertionError("quotas")))
    finally:
        scaleway.quota_pages = kept
        scaleway.zone_quotas.cache_clear()


def created_with(address, failing=(), owner=OURS):
    """create() on a mocked Scaleway whose new machine got `address`; failing: the `ip` commands that fail. (its
    answer, the scw calls, the machines deleted)."""
    import subprocess
    import tempfile
    import types
    import ledger
    calls, deleted = [], []

    def fake_scw(*arguments):
        if arguments[2] != "list":  # the loose addresses and disks read before the order
            calls.append(arguments)
        if arguments[:2] == ("instance", "ip") and arguments[2] in failing:
            raise RuntimeError(f"scw ip {arguments[2]} failed")
        return {"ip": {"id": arguments[3], "project": owner}} if arguments[:3] == ("instance", "ip", "get") else {}

    server = {"id": "srv-1", "public_ips": [{"id": "ip-1", "address": address, "family": "inet"}]}
    kept = scaleway.scw, scaleway.delete, subprocess.run, ledger.LEDGER
    scaleway.scw, scaleway.delete = fake_scw, lambda server_id, zone: deleted.append(server_id) or True
    ledger.LEDGER = pathlib.Path(tempfile.mkdtemp()) / "ledger.jsonl"  # create's started line, never the real ledger
    subprocess.run = lambda *arguments, **options: types.SimpleNamespace(returncode=0, stdout=json.dumps(server),
                                                                          stderr="")
    offer = types.SimpleNamespace(type="POP2-32C-128G", zone="pl-waw-2", machine_class="cpu-32c-128gb", price=0.02)
    try:
        answer = scaleway.create(OURS, offer, "blender-1", [], 60)
    finally:
        scaleway.scw, scaleway.delete, subprocess.run, ledger.LEDGER = kept
    return answer, calls, deleted


def test_a_machine_given_a_bad_address_gets_a_fresh_one_and_the_bad_one_is_quarantined():
    """2026-10-10 to 13: every machine given 151.115.78.211 dropped SSH mid-job."""
    answer, calls, deleted = created_with("151.115.78.211")
    assert answer == ("srv-1", None) and not deleted, (answer, deleted)
    assert [call[2] for call in calls] == ["create", "get", "detach", "update"], calls
    assert "server=srv-1" in calls[0] and f"project-id={OURS}" in calls[0]
    assert f"tags.0={scaleway.QUARANTINED}" in calls[3] and calls[3][3] == "ip-1", calls[3]


def test_a_machine_given_a_good_address_is_left_as_it_is():
    answer, calls, deleted = created_with("151.115.10.10")
    assert answer == ("srv-1", None) and calls == [] and not deleted


def test_a_failed_detach_or_another_projects_address_deletes_the_machine_for_the_next_offer():
    for failing, owner in ((("detach",), OURS), ((), OTHER)):
        answer, calls, deleted = created_with("151.115.78.211", failing, owner)
        assert answer[0] is None and "deleted" in answer[1] and deleted == ["srv-1"], (answer, deleted)
        assert not any(call[2] == "update" for call in calls), calls  # nothing tagged or touched past the check


def refused_create(listed):
    """create() on a mocked Scaleway whose order fails with HTTP 500 and whose server list in the zone answers
    `listed`; (its answer, the machines deleted)."""
    import subprocess
    import tempfile
    import types
    import ledger
    deleted = []
    kept = scaleway.scw, scaleway.delete, subprocess.run, ledger.LEDGER
    scaleway.scw = lambda *arguments: listed if arguments[:3] == ("instance", "server", "list") else {}
    scaleway.delete = lambda server_id, zone: deleted.append((server_id, zone)) or True
    ledger.LEDGER = pathlib.Path(tempfile.mkdtemp()) / "ledger.jsonl"  # never the real ledger
    subprocess.run = lambda *arguments, **options: types.SimpleNamespace(
        returncode=1, stdout="", stderr='{"error":"cannot create the server: http error 500 Internal Server Error"}')
    offer = types.SimpleNamespace(type="L4-1-24G", zone="fr-par-1", machine_class="gpu-24gb", price=0.013)
    try:
        answer = scaleway.create(OURS, offer, "masks-1", [], 60)
    finally:
        scaleway.scw, scaleway.delete, subprocess.run, ledger.LEDGER = kept
    return answer, deleted


def test_a_machine_a_refused_order_made_anyway_is_deleted_at_once():
    """2026-10-22: an order refused with HTTP 500 had made its machine (stopped, billed, unwatched until a later
    sweep). Only the project's own machine of that name with the runner's tag is deleted."""
    listed = [{"id": "srv-made", "name": "masks-1", "project": OURS, "tags": [scaleway.TAG]},
              {"id": "srv-other", "name": "masks-1", "project": OTHER, "tags": [scaleway.TAG]},
              {"id": "srv-untagged", "name": "masks-1", "project": OURS, "tags": []},
              {"id": "srv-near", "name": "masks-10", "project": OURS, "tags": [scaleway.TAG]}]
    answer, deleted = refused_create(listed)
    assert answer[0] is None and "500" in answer[1], answer
    assert deleted == [("srv-made", "fr-par-1")], deleted
    assert refused_create([])[1] == []


def test_the_address_and_disk_a_refused_order_left_loose_are_deleted_and_counted():
    """Only what the order made: loose after it and not before, and still loose after the settle (another order's
    address is loose for a moment before its machine takes it). Their euros are the order's disk-and-address line."""
    import subprocess
    import tempfile
    import types
    import ledger
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
    kept = scaleway.scw, subprocess.run, ledger.LEDGER, scaleway.time.sleep
    scaleway.scw, scaleway.time.sleep = scw, lambda seconds: None
    ledger.LEDGER = pathlib.Path(tempfile.mkdtemp()) / "ledger.jsonl"
    subprocess.run = lambda *arguments, **options: types.SimpleNamespace(returncode=1, stdout="", stderr="out of stock")
    offer = types.SimpleNamespace(type="L4-1-24G", zone="fr-par-1", machine_class="gpu-24gb", price=0.013)
    try:
        answer = scaleway.create(OURS, offer, "masks-1", [], 60)
        lines = [json.loads(line) for line in ledger.LEDGER.read_text().splitlines()]
    finally:
        scaleway.scw, subprocess.run, ledger.LEDGER, scaleway.time.sleep = kept
    assert answer[0] is None and sorted(deleted) == ["disk-new", "ip-new"], (answer, deleted)
    fees = [line for line in lines if line["kind"] == "disk-and-address"]
    assert len(fees) == 1 and fees[0]["name"] == "masks-1", fees
    assert abs(fees[0]["euros"] - (scaleway.ADDRESS_EUROS_AN_HOUR + 60 * scaleway.DISK_EUROS_A_GB_HOUR)) < 1e-9


def test_a_quarantined_address_is_never_a_leftover_to_delete():
    addresses = [{"id": "ip-q", "address": "151.115.78.211", "project": OURS, "server": None,
                  "tags": [scaleway.QUARANTINED, "reason=ssh"]},
                 {"id": "ip-l", "address": "151.115.1.1", "project": OURS, "server": None, "tags": []},
                 {"id": "ip-x", "address": "151.115.2.2", "project": OTHER, "server": None, "tags": []}]
    kept = scaleway.scw, scaleway.ZONES, scaleway.PROCESSOR_ZONES
    scaleway.scw, scaleway.ZONES, scaleway.PROCESSOR_ZONES = (lambda *arguments: addresses), ("pl-waw-2",), ()
    try:
        found = scaleway.leftover_addresses(OURS)
    finally:
        scaleway.scw, scaleway.ZONES, scaleway.PROCESSOR_ZONES = kept
    assert found == [("ip-l", "pl-waw-2", "151.115.1.1")], found


def deleting(still_there, refusal="Failed to detach block volume v-1: volume_id does not respect constraint"):
    """delete() on a mocked Scaleway whose terminate is refused with `refusal`, the machine read again after it
    `still_there` (True: it still exists). (its answer or the error it raised, the ledger lines written)."""
    import subprocess
    import types
    reads, written = [], []

    def run(command, **options):
        if command[2:4] == ["server", "get"]:
            reads.append(1)
            if len(reads) > 1 and not still_there:
                return types.SimpleNamespace(returncode=1, stdout="", stderr="server not found")
            return types.SimpleNamespace(returncode=0, stdout=json.dumps({"id": "srv-1", "volumes": {}}), stderr="")
        return types.SimpleNamespace(returncode=1, stdout="", stderr=refusal)

    kept = subprocess.run, scaleway.record_disk_and_address, scaleway.time.sleep
    subprocess.run, scaleway.time.sleep = run, lambda seconds: None
    scaleway.record_disk_and_address = lambda server, gb, now: written.append(server["id"])
    try:
        try:
            answer = scaleway.delete("srv-1", "pl-waw-2")
        except RuntimeError as error:
            answer = error
    finally:
        subprocess.run, scaleway.record_disk_and_address, scaleway.time.sleep = kept
    return answer, written


def test_a_leftover_another_sweep_deleted_meanwhile_is_gone_not_an_error():
    """surfaces-bake@wreck, 2026-10-13: two sweeps deleted one leftover; the second's refused detach killed its job."""
    assert deleting(still_there=False) == (False, [])  # gone: the other sweep wrote its ledger line


def test_a_delete_refused_while_the_machine_stays_still_raises():
    answer, written = deleting(still_there=True)
    assert isinstance(answer, RuntimeError) and "does not respect constraint" in str(answer) and not written, answer


def test_deleting_an_address_or_disk_already_gone_is_done_and_another_failure_raises():
    import subprocess

    def refusing(text):
        def scw(*arguments):
            raise subprocess.CalledProcessError(1, ["scw", *arguments], output="", stderr=text)
        return scw
    kept = scaleway.scw
    try:
        scaleway.scw = refusing("ip not found")
        scaleway.delete_address("ip-1", "pl-waw-2")
        scaleway.scw = refusing("volume not found")
        scaleway.delete_disk("v-1", "pl-waw-2")
        scaleway.scw = refusing("permission denied")
        try:
            scaleway.delete_disk("v-1", "pl-waw-2")
            raised = False
        except subprocess.CalledProcessError:
            raised = True
    finally:
        scaleway.scw = kept
    assert raised


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("scaleway_test: ok")
