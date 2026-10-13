"""Checks for the Scaleway backend's container path (registry, object_store and the runtime key), with every `scw`
call stubbed: nothing is made or read on the provider.

Run: .venv/bin/python tools/props/cloud/backends/scaleway_test.py   (make tests runs it)
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
    kept = scaleway.scw, scaleway.price, scaleway.PARKED, scaleway.ZONES
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "a.json").write_text(json.dumps({"type": "POP2-32C-128G", "zone": "fr-par-2",
                                               "until": time.time() + 600}))
    (folder / "b.json").write_text(json.dumps({"type": "POP2-32C-128G", "zone": "pl-waw-2", "until": time.time() - 60}))
    (folder / "c.json").write_text("{\"type\": ")  # one being written as it is read
    scaleway.scw = lambda *arguments: [{"name": "POP2-32C-128G", "availability": "shortage"}]
    scaleway.price, scaleway.PARKED = (lambda machine_type, zone: (0.02, 60)), folder
    scaleway.ZONES = ("fr-par-2", "pl-waw-2")
    try:
        found = {offer.zone: offer.stock_word for offer in scaleway.offers(["cpu-32c-128gb"])}
    finally:
        scaleway.scw, scaleway.price, scaleway.PARKED, scaleway.ZONES = kept
    assert found == {"fr-par-2": "parked", "pl-waw-2": "shortage"}, found


def created_with(address, failing=(), owner=OURS):
    """create() on a mocked Scaleway whose new machine got `address`; failing: the `ip` commands that fail. (its
    answer, the scw calls, the machines deleted)."""
    import subprocess
    import types
    calls, deleted = [], []

    def fake_scw(*arguments):
        calls.append(arguments)
        if arguments[:2] == ("instance", "ip") and arguments[2] in failing:
            raise RuntimeError(f"scw ip {arguments[2]} failed")
        return {"ip": {"id": arguments[3], "project": owner}} if arguments[:3] == ("instance", "ip", "get") else {}

    server = {"id": "srv-1", "public_ips": [{"id": "ip-1", "address": address, "family": "inet"}]}
    kept = scaleway.scw, scaleway.delete, subprocess.run
    scaleway.scw, scaleway.delete = fake_scw, lambda server_id, zone: deleted.append(server_id) or True
    subprocess.run = lambda *arguments, **options: types.SimpleNamespace(returncode=0, stdout=json.dumps(server),
                                                                          stderr="")
    offer = types.SimpleNamespace(type="POP2-32C-128G", zone="pl-waw-2", machine_class="cpu-32c-128gb")
    try:
        answer = scaleway.create(OURS, offer, "blender-1", [], 60)
    finally:
        scaleway.scw, scaleway.delete, subprocess.run = kept
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


def test_a_quarantined_address_is_never_a_leftover_to_delete():
    addresses = [{"id": "ip-q", "address": "151.115.78.211", "project": OURS, "server": None,
                  "tags": [scaleway.QUARANTINED, "reason=ssh"]},
                 {"id": "ip-l", "address": "151.115.1.1", "project": OURS, "server": None, "tags": []},
                 {"id": "ip-x", "address": "151.115.2.2", "project": OTHER, "server": None, "tags": []}]
    kept = scaleway.scw, scaleway.ZONES
    scaleway.scw, scaleway.ZONES = (lambda *arguments: addresses), ("pl-waw-2",)
    try:
        found = scaleway.leftover_addresses(OURS)
    finally:
        scaleway.scw, scaleway.ZONES = kept
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
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("scaleway_test: ok")
