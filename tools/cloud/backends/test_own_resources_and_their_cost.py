"""The Scaleway backend touches only its own project's resources, and every euro a machine causes is counted.

Scaleway is one account of the test's own (`Scaleway`), answering the `subprocess.run` the backend reaches `scw`
through from records of our project and another's: nothing is made, read or deleted on the provider, and the ledger is
a file in the sandbox home.

The invariants, each with the break that turns its test red (each applied once and seen red):

- A registry namespace, the runtime key's secret, a bill line, a leftover address and a machine a refused order made
  are taken only when their own record names our project (and the runner's tag, for a machine).
  Break: drop `and space.get("project_id") == project` in `registry_namespace` -> another project's namespace is used.
  Break: drop `if line.get("project_id") != project: continue` in `consumption` -> the bill reads EUR 187.0.
- The env1 cap's whole bill reads every project: SCORE's whole, the shared one but babon's own services, a machine
  of the shared project SCORE's only in a score or gate pool; an empty bill or a lower one raises.
  Break: `counted` returns True for every line -> the database line counts. Break: drop the `whole < last_whole`
  raise in `bill_all`. Break: `owner_of` returns "score" for any shared machine -> batch-l4 is SCORE's.
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
  A machine the zone is still making is waited out, then deleted (2026-11-05, surfaces-bake@camp). Break: drop the
  PROVISION words from NOT_YET.
- This PC's backend (local.py) costs nothing and orders nothing: every class it serves is offered `parked` at EUR 0,
  a class beyond its one 16 GB card is refused at once, a kind too big for the card is refused at its claim, one claim
  holds it at a time, and a delete from another process leaves a claim still held alone.
  Break: `return not found.group(2) and int(found.group(1)) <= 24` -> `return True` in `serves` -> gpu-80gb is offered.
  Break: drop `| fcntl.LOCK_NB` handling (return the machine without the lock) in `claimed` -> a second claim gets it.
  Break: in `delete`, drop the `except BlockingIOError: ... return False` -> another claim's container is restarted.
  Its object store is the Scaleway backend's (the library's blobs a handover from here puts in, env1 2026-11-04).
  Break: `object_store` raises SystemExit again -> the handover from this PC exits before it runs.
- Blender claims (SHARED) share the machine's RUNS_AT_ONCE turns across places: a claim takes the free turns, lets
  each go as its slot runs out of work, and a second place's claim takes them while the first still runs; an
  exclusive claim is kept out meanwhile and, once it asks, keeps new Blender claims out; the container is restarted
  only by the claim leaving it alone. Break: `fcntl.LOCK_SH if shared` -> `fcntl.LOCK_EX` in `claimed` -> the second
  place waits for the first; or drop the `fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)` check in `delete`'s
  held branch -> the first leaving restarts the container under the second's jobs; or `[] if wanted_elsewhere()`
  dropped in `claimed` -> a waiting exclusive claim is starved; or drop `provider.cloud.let_go_turn` in
  `spread.work_turn` -> a slot out of work keeps its turn.
- A claim's end removes its own files from its container (2026-11-03: 476 GB in the containers' layers, this PC's
  disk 98% full): the claim leaving it alone runs its kind's clean-up and empties the runner's folders there (each
  once, never /root, each folder kept), a shared claim with others beside removes nothing of theirs; before a claim a
  layer past LAYER_LIMIT_GB loses its installer caches, measured once a LAYER_EVERY_SECONDS. Break: in `delete`, drop
  `tidied(name, f"{own}; {swept()}")` -> nothing goes; or in `runner_paths` drop `not folder.is_relative_to("/root")` -> /root/repo is swept; or
  `-mindepth 1` -> `-mindepth 0` in `swept` -> the folders go too; or in `bounded` drop the LAYER_EVERY_SECONDS
  return -> the caches go at every claim; or drop `bounded(name)` in `take` -> none go.
- A job is refused by its measured need, not its kind: a characters run of clip steps (4 GB of card, 17 GB of memory
  with the encoder on the processor) takes this PC, a whole characters machine (17 GB of card) or a need past the
  container's memory does not. Break: `card = TOO_BIG.get(kind)` in `refusal` -> the clip run is refused; or drop the
  memory check -> the 40 GB job is taken.
- A Blender job predicted past the container's memory (round 31: base's light passes, 29.8 GB beside a 27 GiB cap)
  runs alone: its claim waits for every shared claim and keeps new ones out, waits while the room it needs is not
  free (alone_room), then runs one job at a time in the container raised to alone_cap, set back at its delete; a
  need past alone_cap is refused. Break: `shared = kind in SHARED and not alone` -> `kind in SHARED` in `claimed` ->
  it shares three turns; or drop `if alone and memory > alone_room():` ... `return None` in `take` -> it starts
  without the room; or drop the alone `docker("update", ...)` in `take` -> the container stays 27g; or drop the
  `docker("update", *memory_arguments(), ...)` in `delete` -> it stays 35g; or drop `found["turns"] = 1` -> three
  jobs of 30 GB at once.
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
- This PC's card queue (card_queue.py, PRD #73) never lets its holders' shares pass the card's room (one group counted
  once: the run's Blender claims), a env-run claim that waits keeps side jobs off until it has its share, an unmeasured
  need takes the whole card, and `status` leads with the PC's line (shares, waiters, containers' memory). A env-run claim
  that waited YIELD_SECONDS asks side shares back: `run` stops its command's session, gives its share back, waits and
  starts the command again once the card is free. The container's claims hold their share from take to delete and
  wait as for a busy machine while it has no room. A rented machine sizes it to its own card (SCORE_CARD_BUDGET_GB, SCORE_CARD_DESKTOP_GB).
  Break: read `BUDGET_GB` as the constant 13.5 again -> the rented card's 78 GB is capped at this PC's; or
  `> BUDGET_GB` -> `> BUDGET_GB * 2` in `take` -> the side job joins two Blender claims; or drop `ahead or` ->
  the side job starts before the waiting env-run claim; or drop `"film": 1` from `RANK` -> a run frozen before the rename
  (it still writes "film") crashes the queue; or swap "sim-body" and "env-run" in `ORDER` -> the env-run claim starts
  before the waiting sim body share; or `key = entry["group"] or entry["id"]` -> `key = entry["id"]`
  in `in_use` -> the second Blender claim of the same group waits; or drop `{containers()}` in `status` -> no
  containers' memory; or drop the `ask_back(...)` call in `take` -> the env-run claim is never admitted; or drop `stop(child)`
  after the give-way line in `run` -> the first tuning stays alive; or `return child.returncode` -> `continue` in
  `run` -> it never ends; or drop the `if handle and share is None:` block in `local.take` -> the pixal claim starts
  beside the side job; or drop `CARDS[machine_id] = share` in `local.take` -> the claim's share is let go at once; or
  drop `"similar"` from `local.CARD_NEED` -> the likeness claim waits for the whole card beside the side job; or drop
  `"similar"` from `local.MEMORY_NEED` -> it holds the whole memory and a 20 GiB side job waits; or drop `"library"`
  from `local.CARD_NEED` -> the library bake waits for the whole card beside the side job.
- Every watched share (each `run`, each claim of the container) is measured while held: the card's highest reading less
  the desktop, alone or beside another share, with its cores and memory, one line in measures.jsonl when given back.
  Break: drop `record(handle, cores, memory_gb)` in `release` -> nothing measured; or `<= 1` -> `< 1` in `read_card` ->
  never alone; or drop `- DESKTOP_GB` in `record` -> 8.79 GB.
- The container keeps HOST_CORES of this PC's cores (--cpus 20 of 24) at every claim, and a claim whose run gives its
  measured memory is held to it times MEMORY_MARGIN (17 GB: 26g), set back at its delete; one with none keeps 27g.
  Break: drop `*cpu_arguments()` from `running`'s update; or `memory_gb * MEMORY_MARGIN` -> `memory_gb` in `held_to`
  -> 17g; or drop the `elif ... held_to(...)` branch in `take`; or drop `need = own_need(kind, need)` in `take` -> a
  sim-body chain held to blender_cloud's Blender prediction, 3g (sim-body@airlock and @garage killed, 2026-11-13).
- Claims of different kinds run side by side, each in its kind's own container (Blender in score-this-pc, the others
  in score-this-pc-<kind>), while their card and memory shares fit the queue; an unmeasured kind holds the whole
  memory and waits for both; claims the queue refused are served first come first served; a Blender claim takes only
  the turns the free memory holds, and gives a turn's memory back with the turn. Break: `got(whole, alone)` ->
  `got(whole, True)` in `claimed` -> the second kind waits; or `container` -> always MACHINE; or drop `or not OWN` in
  `container` -> without SCORE_THIS_PC_OWN_CONTAINERS the route claim runs beside the bakes in one container; or drop the `most` stop
  in `free_turns` -> the second place takes a turn past the memory; or `(ORDER.index(...), waiter["since"]) < (rank,
  since)` -> `ORDER.index(...) < rank` in `card_queue.take` -> the free turn goes past the Pixal3D claim that asked
  first; or drop the memory sum in `card_queue.take` -> the Pixal3D claim starts beside both; or drop
  `card_queue.resize(...)` in `let_go_turn` -> the second place gets one turn; or drop `if turns else 0` there -> a claim
  that let its last turn go holds memory None and every next claim fails to count the queue's memory.
- A sim-body claim (BESIDE) shares score-this-pc with the Blender bakes, its share of the queue the queue's own measure
  of its kind (5 takes: 3.6 GB of card, 3.12 GB x MEMORY_MARGIN), never the whole card and memory; a second one waits
  while its card does not fit; the run's cap here is as many claims as fit by those shares (claims_at_once), never a
  fixed one. Break: `(kind in SHARED or kind in BESIDE)` -> `kind in SHARED` in `claimed` -> the sim-body claim
  waits on the bakes' lock; or drop `memory_share = measured_memory` in `take` -> it holds the whole memory and
  waits; or `at_once() if at_once else max(...)` -> `max(...)` in `capacity.caps` -> the cap reads 20.
- A claim's memory is its container's highest anon reading while it holds its share, counted for its kind only from
  claims alone in that container. Break: drop the `card_queue.watch_memory(...)` call in `local.take` -> memory
  unmeasured; or drop `and not any(beside(...))` in `card_queue.read_memory` -> 5.0 GB from the two claims together;
  or drop `memory_gb = round(handle.memory_peak / 1e9, 2)` in `record` -> unmeasured.
- A claim the card queue refused says so (`queued`), so park.here holds its run's minutes while it waits there.
  Break: `return any(...)` -> `return False` in `queued`.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import time
import types
import urllib.error

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import card_queue  # noqa: E402
import scaleway  # noqa: E402

OURS = "project-ours"
OTHER = "project-other"
BAD = next(iter(scaleway.BAD_ADDRESSES))


@pytest.fixture(autouse=True)
def self_delete_key(monkeypatch, tmp_path):
    """The runner's self-delete key as a file of the test's own, never this PC's: create's self-delete check reads it
    as it reads the real one, and the provider's answer to it (a network read) takes only this key."""
    import batch
    monkeypatch.setattr(batch, "SELF_DELETE_KEY", tmp_path / "self_delete_key.json")
    batch.SELF_DELETE_KEY.write_text('{"secret_key": "works"}')
    monkeypatch.setattr(scaleway, "self_delete_refusal",
                        lambda secret, zone: None if secret == "works" else "Scaleway's instance API answers it 401")
    return batch.SELF_DELETE_KEY


@pytest.fixture(autouse=True)
def card_queue_folder(monkeypatch, tmp_path):
    """This PC's card queue in the test's own folder, never the PC's real one."""
    monkeypatch.setattr(card_queue, "QUEUE", tmp_path / "card-queue")
    monkeypatch.setattr(card_queue, "WAITING", {})
    monkeypatch.setattr(card_queue, "containers", lambda: "score-this-pc 3GiB / 27GiB")
    monkeypatch.setattr(card_queue, "SAMPLER", SAMPLER)
    monkeypatch.setattr(card_queue, "memory_gb", lambda: 27)  # this PC's 43 GiB less its reserve, whatever runs the test
    import local
    monkeypatch.setattr(local, "OWN", True)  # each kind in its own container (SCORE_THIS_PC_OWN_CONTAINERS=1)
    monkeypatch.setenv("SCORE_CARD_SAMPLER", json.dumps(SAMPLER))  # the `run` under test reads the same card
    return card_queue.QUEUE


# A card read twice: 8000 and 9000 MiB, 6.39 GB less the desktop.
SAMPLER = [sys.executable, "-c", "import time; print(8000); print(9000, flush=True); time.sleep(5)"]



def namespace(project, public=False, endpoint="rg/x"):
    return {"name": scaleway.REGISTRY_NAMESPACE, "project_id": project, "is_public": public, "endpoint": endpoint}


def refused(text):
    return subprocess.CompletedProcess([], 1, "", text)


def made_at(seconds):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(seconds))


def machine(server_id, name, project=OURS, tags=(scaleway.TAG,), addresses=()):
    """A machine record as Scaleway's `server get` answers it: made now, one 60 GB disk, `addresses` on it."""
    return {"id": server_id, "name": name, "project": project, "tags": list(tags), "commercial_type": "POP2-32C-128G",
            "creation_date": made_at(time.time()), "volumes": {"0": {"size": 60e9}},
            "public_ips": [{"id": address["id"], "address": address["address"], "family": "inet"}
                           for address in addresses]}


def loose_address(address_id, address, project=OURS, server=None, tags=()):
    return {"id": address_id, "address": address, "project": project, "server": server and {"id": server},
            "tags": list(tags)}


class Scaleway:
    """One Scaleway account as the backend reaches it through `subprocess.run` (every `scw` command, and the server
    create the backend runs itself): our project's and another's registry namespaces, runtime key secrets, bill lines,
    addresses, disks and machines, answered from these records and changed as Scaleway changes them. Every command is
    kept in `commands`; each of `refusals` ((command head, Scaleway's words, what else happens meanwhile)) answers
    the first command it heads, once; `order` answers a server create; `racing` are addresses another order's machine
    takes once a moment has passed (`settle`)."""

    def __init__(self):
        self.namespaces, self.secrets, self.bill, self.types, self.disks = [], [], [], [], []
        self.addresses, self.servers, self.refusals, self.racing, self.commands = [], [], [], [], []
        self.order, self.stored = None, None

    def __call__(self, command, **options):
        arguments = tuple(command[1:-2] if command[-2:] == ["-o", "json"] else command[1:])
        self.commands.append(arguments)
        for index, (head, words, meanwhile) in enumerate(self.refusals):
            if arguments[:len(head)] == head:
                del self.refusals[index]
                meanwhile()
                return refused(words)
        if arguments[:3] == ("instance", "server", "create"):
            return self.order(dict(argument.split("=", 1) for argument in arguments[3:] if "=" in argument))
        try:
            answer = self.answer(arguments[:3], arguments[3:])
        except LookupError as missing:
            return refused(f"{missing.args[0]} not found")
        return subprocess.CompletedProcess(command, 0, "" if answer is None else json.dumps(answer), "")

    def answer(self, head, rest):
        value = dict(argument.split("=", 1) for argument in rest if "=" in argument)
        target = rest[0] if rest else None
        reads = {("registry", "namespace", "list"): self.namespaces, ("secret", "secret", "list"): self.secrets,
                 ("billing", "consumption", "list"): self.bill, ("instance", "server-type", "list"): self.types,
                 ("instance", "ip", "list"): self.addresses, ("block", "volume", "list"): self.disks,
                 ("instance", "server", "list"): self.servers, ("iam", "application", "list"): [],
                 ("iam", "policy", "list"): [], ("account", "project", "get"): {"organization_id": "org"},
                 ("config", "get", "secret-key"): "key", ("iam", "application", "create"): {"id": "app"},
                 ("iam", "policy", "create"): {}, ("iam", "api-key", "create"): {"access_key": "AK2",
                                                                                 "secret_key": "SK2"}}
        if head in reads:
            return reads[head]
        if head == ("registry", "namespace", "create"):
            self.namespaces.append(namespace(value["project-id"], value["is-public"] == "true", "rg/new"))
            return self.namespaces[-1]
        if head == ("secret", "secret", "create"):
            self.secrets.append({"name": value["name"], "project_id": value["project-id"]})
            return {"id": "held"}
        if head == ("secret", "version", "create"):
            data = value["data"]
            self.stored = pathlib.Path(data[1:]).read_text() if data.startswith("@") else data
            return {}
        if head == ("instance", "ip", "create"):
            self.addresses.append(loose_address(f"ip-fresh-{value['server']}", "151.115.9.9", value["project-id"],
                                                value["server"], [value["tags.0"]]))
            return {}
        if head == ("instance", "ip", "get"):
            return {"ip": self.find(self.addresses, target, "ip")}
        if head == ("instance", "ip", "detach"):
            self.find(self.addresses, target, "ip")["server"] = None
            return {}
        if head == ("instance", "ip", "update"):
            self.find(self.addresses, target, "ip")["tags"] = [value[key] for key in sorted(value) if
                                                               key.startswith("tags.")]
            return {}
        if head == ("instance", "ip", "delete"):
            self.addresses.remove(self.find(self.addresses, target, "ip"))
            return None
        if head == ("block", "volume", "delete"):
            self.disks.remove(self.find(self.disks, target, "volume"))
            return None
        if head == ("instance", "server", "get"):
            return self.find(self.servers, target, "server")
        if head == ("instance", "server", "terminate"):  # with-ip=true: its addresses go with it
            self.servers.remove(self.find(self.servers, target, "server"))
            self.addresses[:] = [address for address in self.addresses
                                 if (address["server"] or {}).get("id") != target]
            return None
        raise AssertionError(f"scw {' '.join(head)} is not one this account answers")

    @staticmethod
    def find(records, item_id, kind):
        found = [record for record in records if record["id"] == item_id]
        if not found:
            raise LookupError(kind)
        return found[0]

    def rent(self, address, owner):
        """Orders answered with a machine of the name asked, given `address` (`owner`'s address record)."""
        def order(value):
            given = loose_address(f"ip-{value['name']}", address, owner, f"srv-{value['name']}")
            self.addresses.append(given)
            self.servers.append(machine(f"srv-{value['name']}", value["name"], addresses=[given]))
            return subprocess.CompletedProcess([], 0, json.dumps(self.servers[-1]), "")
        self.order = order

    def refuse_but_make(self, value):
        """HTTP 500 (2026-10-22) that made the machine anyway, with its own loose address and disk, while another
        order's address is loose for a moment before its machine takes it."""
        self.servers.append(machine("srv-made", value["name"]))
        racing = loose_address("ip-racing", "3.3.3.3")
        self.addresses += [loose_address("ip-new", "2.2.2.2"), racing]
        self.racing.append(racing)
        self.disks.append({"id": "disk-new", "name": value["name"], "project_id": OURS, "references": []})
        return refused('{"error":"cannot create the server: http error 500"}')

    def settle(self):
        for address in self.racing:
            address["server"] = {"id": "srv-racing"}


@pytest.fixture
def ledger_file(monkeypatch, tmp_path):
    """The cloud ledger as a fresh file; its lines read back."""
    import ledger
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.jsonl")
    return lambda: [json.loads(line) for line in ledger.LEDGER.read_text().splitlines()] if ledger.LEDGER.exists() \
        else []


@pytest.fixture
def world(monkeypatch, tmp_path, request):
    """One account holding our project's resources beside another's, the backend reaching it only through
    `subprocess.run`; no sleep waits, its quota pages and prices read from here."""
    account = Scaleway()
    account.namespaces = [namespace(OTHER, endpoint="rg/other"), namespace(OURS, endpoint="rg/ours")]
    account.secrets = [{"name": scaleway.RUNTIME_KEY_SECRET, "project_id": OTHER}]
    account.servers = [machine("srv-other", "masks-1", OTHER), machine("srv-untagged", "masks-1", tags=()),
                       machine("srv-near", "masks-10"), machine("srv-wreck", "surfaces-bake-1"),
                       machine("srv-stuck", "surfaces-bake-2"), machine("srv-making", "surfaces-bake-3")]
    account.addresses = [loose_address("ip-old", "1.1.1.1"), loose_address("ip-x", "151.115.2.2", OTHER),
                         loose_address("ip-on", "151.115.3.3", server="srv-near")]
    monkeypatch.setattr(subprocess, "run", account)
    monkeypatch.setattr(scaleway.time, "sleep", lambda seconds: account.settle())
    monkeypatch.setattr(scaleway, "account", lambda: OURS)
    monkeypatch.setattr(scaleway, "secret", lambda name: json.dumps({"access_key": "AK", "secret_key": "SK"}))
    monkeypatch.setattr(scaleway, "price", lambda machine_type, zone: (0.02, 60))
    scaleway.zone_quotas.cache_clear()
    request.addfinalizer(scaleway.zone_quotas.cache_clear)
    return account


# The bill of 2026-11: our project's line and another's (project_id only), and the organisation's whole bill as the
# env1 cap reads it (the plan of 2026-11-09): SCORE's projects whole, the shared one but babon's own services.
SHARED = "babon-platform"
BILL = [
    {"project_id": OURS, "product_name": "L4", "sku": "s", "unit": "minute", "billed_quantity": "10",
     "value": {"units": 1, "nanos": 500000000}},
    {"project_id": OTHER, "product_name": "L4", "sku": "x", "value": {"units": 99}},
    {"project_id": "ff", "project_name": "farm-factory", "category_name": "Compute", "product_name": "L4",
     "sku": "/instance/server/l4_1_24g/fr-par-2", "value": {"units": 10}},
    {"project_id": "sc", "project_name": "score-conductor", "category_name": "Storage", "sku": "/storage/b",
     "product_name": "Block Storage Volume", "value": {"units": 2, "nanos": 500000000}},
    {"project_id": "bp", "project_name": SHARED, "category_name": "Compute", "product_name": "L4",
     "sku": "/instance/server/l4_1_24g/fr-par-2", "value": {"units": 40}},
    {"project_id": "bp", "project_name": SHARED, "category_name": "Managed Databases", "product_name": "DB",
     "sku": "/storage/rdb", "value": {"units": 30}},
    {"project_id": "bp", "project_name": SHARED, "category_name": "Network", "product_name": "Loadbalancer IP",
     "sku": "/network/loadbalancer/ip/par1", "value": {"units": 1}},
    {"project_id": "bw", "project_name": "babon-worker", "category_name": "Security and Identity",
     "product_name": "Secret Manager", "sku": "/paas/secret", "value": {"units": 3}}]

# Whose a machine is, by its project and pool tag: (project id, tags, owner).
OWNERS = [("ff", [], "score"), ("bp", ["pool-name=score-l4-1-z2"], "score"), ("bp", ["pool-name=gate-cpu"], "score"),
          ("bp", ["pool-name=batch-l4"], "babon"), ("bp", [], "babon"), ("xx", ["pool-name=score-x"], None)]

# The registry namespaces the account lists, the endpoint registry() gives (or the refusal) and the namespaces it
# makes: (row, namespaces, endpoint, made).
NAMESPACES = [("ours beside another's", None, "rg/ours", 0),
              ("only another project's: ours is made private", [namespace(OTHER)], "rg/new", 1),
              ("ours public: refused", [namespace(OURS, public=True)], "public", 0)]

# Quotas as Scaleway's IAM pages list them (the CLI has none); a non-type quota is no machine's.
QUOTA_PAGES = [
    {"name": "cp_servers_type_POP2_HC_48C_96G", "limits": [{"zone": "nl-ams-2", "limit": 1},
                                                           {"zone": "fr-par-1", "limit": 1},
                                                           {"zone": "pl-waw-1", "limit": 0}]},
    {"name": "cp_servers_type_L4_1_24G", "limits": [{"zone": "fr-par-1", "unlimited": True},
                                                    {"zone": "nl-ams-2", "limit": 50}]},
    {"name": "cp_servers_type_POP2_32C_128G", "limits": [{"zone": "fr-par-2", "limit": 2},
                                                         {"zone": "pl-waw-2", "limit": 2}]},
    {"name": "adt_beta", "limits": [{"zone": "fr-par-1", "limit": 1}]}]

# Each machine type every zone lists: the big POP2 in stock (owner, 2026-10-23: "cant u just get a faster cpu"), the
# 64-core one with no quota anywhere, POP2-32C-128G short because our own runs parked them (2026-10-12).
TYPES = [{"name": "POP2-HC-64C-128G", "availability": "available"},
         {"name": "POP2-HC-48C-96G", "availability": "available"},
         {"name": "L4-1-24G", "availability": "available"},
         {"name": "POP2-32C-128G", "availability": "shortage"}]

# A new machine's address: (row, the address it got, the `ip` command Scaleway refuses, whose the address's record
# says it is, the ip commands sent, whether the machine is kept). A bad one is swapped and quarantined; when that
# cannot be done safely the machine is deleted (its offer refused) and nothing is tagged past the failed step.
ADDRESSES = [("bad: swapped and quarantined", BAD, None, OURS, ["create", "get", "detach", "update"], True),
             ("good: left as it is", "151.115.10.10", None, OURS, [], True),
             ("bad, its detach refused", BAD, "detach", OURS, ["create", "get", "detach"], False),
             ("bad, another project's", BAD, None, OTHER, ["create", "get"], False)]

# A deleted machine's disk (60 GB) and address billed by the started hour: (minutes since its creation, hours billed).
HOURS = [(61, 2), (2, 1)]


def test_only_our_projects_resources_are_taken_and_every_euro_they_cause_is_counted(world, ledger_file, monkeypatch,
                                                                                     tmp_path):
    import ledger
    one_hour = 60 * 0.00013 + 0.005  # 60 GB at EUR 0.00013 a GB-hour, one address at EUR 0.005 an hour

    # the container path: the runtime key (only another project's secret is listed) is made scoped to our project and
    # kept only in Secret Manager; the registry is our own private namespace, made when only another's is listed
    for row, listed, endpoint, making in NAMESPACES:
        world.namespaces = list(listed or world.namespaces)
        before = len(world.commands)
        if endpoint == "public":
            with pytest.raises(SystemExit, match="public"):
                scaleway.registry()
        else:
            assert scaleway.registry() == {"endpoint": endpoint, "username": "nologin", "password": "SK"}, row
        made = [command for command in world.commands[before:] if command[:3] == ("registry", "namespace", "create")]
        assert len(made) == making, row
        assert all(f"project-id={OURS}" in command and "is-public=false" in command for command in made), row
    policies = [command for command in world.commands if command[:3] == ("iam", "policy", "create")]
    assert len(policies) == 1 and f"rules.0.project-ids.0={OURS}" in policies[0] and "application-id=app" in policies[0]
    assert {argument.split("=", 1)[1] for argument in policies[0] if ".permission-set-names." in argument} == {
        "ObjectStorageFullAccess", "ContainerRegistryFullAccess"}
    assert [command for command in world.commands if command[:3] == ("iam", "api-key", "create")
            and f"default-project-id={OURS}" in command]
    assert [command for command in world.commands if command[:3] == ("secret", "secret", "create")
            and f"project-id={OURS}" in command]
    assert json.loads(world.stored) == {"access_key": "AK2", "secret_key": "SK2"}
    assert not any("SK2" in argument for command in world.commands for argument in command)

    # the bill: our project's own lines; the cap's whole bill reads every project and counts SCORE's usage
    world.bill = BILL
    assert scaleway.month_spend(OURS) == 1.5
    read = scaleway.bill_all()
    assert read["whole"] == 187.0 and read["lines"] == {
        "farm-factory|/instance/server/l4_1_24g/fr-par-2": 10.0, "score-conductor|/storage/b": 2.5,
        f"{SHARED}|/instance/server/l4_1_24g/fr-par-2": 40.0}
    assert read["projects"] == {OURS: OURS, OTHER: OTHER, "farm-factory": "ff", "score-conductor": "sc", SHARED: "bp",
                                "babon-worker": "bw"}
    with pytest.raises(scaleway.Unread, match="below"):
        scaleway.bill_all(last_whole=190.0)
    names = {"ff": "farm-factory", "bp": SHARED, "xx": "babon-worker"}
    assert [scaleway.owner_of({"project": project, "tags": tags}, names) for project, tags, _ in OWNERS] == [
        owner for _, _, owner in OWNERS]
    world.bill = []
    with pytest.raises(scaleway.Unread, match="no line"):
        scaleway.bill_all()

    # offers: quotas read by type and zone, a processor class in every rent zone with quota, a card class in the card
    # zones only, each zone's type list read once, a short type our run parked offered as parked (an expired record and
    # a half-written one do not count)
    world.types = TYPES
    monkeypatch.setattr(scaleway, "quota_pages",
                        lambda organization, key: QUOTA_PAGES if (organization, key) == ("org", "key") else [])
    assert scaleway.zone_quotas() == {
        ("POP2-HC-48C-96G", "nl-ams-2"): 1, ("POP2-HC-48C-96G", "fr-par-1"): 1, ("POP2-HC-48C-96G", "pl-waw-1"): 0,
        ("L4-1-24G", "fr-par-1"): float("inf"), ("L4-1-24G", "nl-ams-2"): 50, ("POP2-32C-128G", "fr-par-2"): 2,
        ("POP2-32C-128G", "pl-waw-2"): 2}
    parked = tmp_path / "parked"
    parked.mkdir()
    for index, record in enumerate([{"type": "POP2-32C-128G", "zone": "fr-par-2", "until": time.time() + 600},
                                    {"type": "POP2-32C-128G", "zone": "pl-waw-2", "until": time.time() - 60}]):
        (parked / f"{index}.json").write_text(json.dumps(record))
    (parked / "2.json").write_text("{\"type\": ")
    monkeypatch.setattr(scaleway, "PARKED", parked)
    monkeypatch.setattr(scaleway, "ZONES", ("fr-par-1", "fr-par-2", "pl-waw-2"))
    monkeypatch.setattr(scaleway, "PROCESSOR_ZONES", ("nl-ams-2", "fr-par-1"))
    zones_read = lambda: [command[-1] for command in world.commands  # noqa: E731
                          if command[:3] == ("instance", "server-type", "list")]
    found = scaleway.offers(["cpu-64c-128gb", "cpu-48c-96gb", "gpu-24gb", "cpu-32c-128gb"])
    assert {(offer.machine_class, offer.zone): (offer.stock_word, offer.stock) for offer in found} == {
        ("cpu-48c-96gb", "fr-par-1"): ("available", 0), ("gpu-24gb", "fr-par-1"): ("available", 0),
        ("cpu-32c-128gb", "fr-par-2"): ("parked", 1), ("cpu-32c-128gb", "pl-waw-2"): ("shortage", 2),
        ("cpu-48c-96gb", "nl-ams-2"): ("available", 0)}
    assert zones_read() == ["zone=fr-par-1", "zone=fr-par-2", "zone=pl-waw-2", "zone=nl-ams-2"]
    scaleway.offers(["gpu-24gb"])
    assert zones_read()[4:] == ["zone=fr-par-1", "zone=fr-par-2", "zone=pl-waw-2"]  # a card-only ask: no processor zone

    def refused_quotas(organization, key):  # the conductor's key reads no quota (403, 2026-10-24): none known
        raise urllib.error.HTTPError("https://api.scaleway.com", 403, "Forbidden", {}, None)
    monkeypatch.setattr(scaleway, "quota_pages", refused_quotas)
    scaleway.zone_quotas.cache_clear()
    assert scaleway.zone_quotas() is None

    # renting: a new machine's bad address is swapped for a fresh one and quarantined, or the machine deleted
    terminated = lambda since: [command[3] for command in world.commands[since:]  # noqa: E731
                                if command[:3] == ("instance", "server", "terminate")]
    for number, (row, address, refusing, owner, sent, kept) in enumerate(ADDRESSES, 1):
        name, since = f"blender-{number}", len(world.commands)
        world.rent(address, owner)
        world.refusals = [(("instance", "ip", refusing), f"scw ip {refusing} failed", lambda: None)] if refusing else []
        offer = types.SimpleNamespace(type="POP2-32C-128G", zone="pl-waw-2", machine_class="cpu-32c-128gb", price=0.02)
        answer = scaleway.create(OURS, offer, name, [], 60)
        assert answer[0] == (f"srv-{name}" if kept else None) and (answer[1] is None) == kept, row
        assert terminated(since) == ([] if kept else [f"srv-{name}"]), row
        ip = [command for command in world.commands[since:]
              if command[:2] == ("instance", "ip") and command[2] != "list"]
        assert [command[2] for command in ip] == sent, row
        if kept and sent:
            assert f"server=srv-{name}" in ip[0] and f"project-id={OURS}" in ip[0], row
            assert ip[3][3] == f"ip-{name}" and f"tags.0={scaleway.QUARANTINED}" in ip[3], row

    # a refused order's own machine (HTTP 500 that made it anyway, 2026-10-22: stopped, billed, unwatched) and its own
    # loose address and disk are deleted, their euros its ledger line; another order's racing address is left alone
    since = len(world.commands)
    world.order = world.refuse_but_make
    offer = types.SimpleNamespace(type="L4-1-24G", zone="fr-par-1", machine_class="gpu-24gb", price=0.013)
    answer = scaleway.create(OURS, offer, "masks-1", [], 60)
    assert answer[0] is None and "500" in answer[1]
    assert terminated(since) == ["srv-made"] and "zone=fr-par-1" in next(
        command for command in world.commands[since:] if command[2] == "terminate")
    gone = sorted(command[3] for command in world.commands[since:] if command[2] == "delete")
    assert gone == ["disk-new", "ip-new"]
    lines = ledger_file()
    assert [line["state"] for line in lines if line["kind"] in (ledger.RENT_STARTED, ledger.RENT_REFUSED)
            and line["name"] == "masks-1"] == ["started", "refused"]  # the order's started line, closed by its refusal
    fees = [line for line in lines if line["kind"] == "disk-and-address" and line["who"] == "scaleway.create"]
    assert len(fees) == 1 and fees[0]["name"] == "masks-1"
    assert fees[0]["euros"] == pytest.approx(0.005 + 60 * 0.00013)  # one address-hour, 60 GB for one hour

    # every euro: a machine's disk and address are billed by the started hour from its creation, one ledger line
    # written when it is deleted; a machine already gone deletes nothing and writes nothing
    created = 1791799200.0  # 2026-10-12T10:00:00Z
    server = {"creation_date": made_at(created), "public_ips": [{"id": "ip"}]}
    assert [scaleway.disk_and_address_euros(server, 60, created + minutes * 60) for minutes, _ in HOURS] == [
        pytest.approx(hours * one_hour) for _, hours in HOURS]
    assert scaleway.delete("srv-blender-2", "pl-waw-2") is True
    assert scaleway.delete("srv-blender-2", "pl-waw-2") is False
    written = [line for line in ledger_file() if line["batch"] == "disk-and-address-srv-blender-2"]
    assert len(written) == 1 and written[0]["euros"] == pytest.approx(one_hour)

    # deleting what another sweep already deleted is done (surfaces-bake@wreck, 2026-10-13: two sweeps on one
    # leftover; the second's refused detach killed its job), any other refusal raises; a machine the zone is still
    # making refuses its terminate until it is made: waited out, then deleted (2026-11-05, surfaces-bake@camp)
    constraint = "Failed to detach block volume v-1: volume_id does not respect constraint"
    wreck = world.find(world.servers, "srv-wreck", "server")
    world.refusals = [(("instance", "server", "terminate", "srv-wreck"), constraint,
                       lambda: world.servers.remove(wreck)),
                      (("instance", "server", "terminate", "srv-stuck"), constraint, lambda: None),
                      (("instance", "server", "terminate", "srv-making"), ("precondition failed: , Cannot modify the "
                       "SBS volumes of an instance in the state SessionState.PROVISION"), lambda: None),
                      (("block", "volume", "delete", "v-1"), "permission denied", lambda: None)]
    assert scaleway.delete("srv-wreck", "pl-waw-2") is False
    with pytest.raises(RuntimeError, match="does not respect constraint"):
        scaleway.delete("srv-stuck", "pl-waw-2")
    assert scaleway.terminate("srv-making", "fr-par-2") is True
    assert not [line for line in ledger_file() if line["batch"] in ("disk-and-address-srv-wreck",
                                                                     "disk-and-address-srv-stuck")]
    scaleway.delete_address("ip-1", "pl-waw-2")  # not found: another sweep's
    scaleway.delete_disk("v-2", "pl-waw-2")
    with pytest.raises(subprocess.CalledProcessError):
        scaleway.delete_disk("v-1", "pl-waw-2")

    # a machine whose state cannot be read is a refusal its waiter waits out and deletes, never a crash
    assert "server not found" in scaleway.start_if_stopped("srv-unknown", "pl-waw-2")

    # what is left: only our own loose address is a leftover, never another project's, one on a machine or the
    # quarantined bad address
    assert scaleway.leftover_addresses(OURS, ("pl-waw-2",)) == [("ip-old", "pl-waw-2", "1.1.1.1")]


def test_this_pc_orders_nothing_costs_nothing_and_holds_one_claim(monkeypatch, tmp_path):
    import local
    monkeypatch.setattr(local, "LOCK", tmp_path / "this-pc.lock")
    monkeypatch.setattr(local, "running", lambda public_key, name=None: "172.17.0.2")
    restarted, execs = [], []

    def docker(*arguments, **_):
        restarted.extend([arguments] if arguments[0] == "restart" else [])
        execs.extend([arguments[-1]] if arguments[2:4] == ("sh", "-c") else [])
        layer = "90000000000"  # 90 GB, its set-ups' own past the limit too
        return types.SimpleNamespace(returncode=0, stdout=layer if arguments[:2] == ("inspect", "--size") else "",
                                     stderr="")
    monkeypatch.setattr(local, "docker", docker)
    offers = local.offers(["gpu-80gb", "gpu-24gb", "cpu-32c-128gb", "gpu-24gb-x2"])
    assert [offer.machine_class for offer in offers] == ["gpu-24gb", "cpu-32c-128gb"]
    assert {(offer.price, offer.stock_word) for offer in offers} == {(0.0, "parked")}  # batch.rent orders nothing
    with pytest.raises(SystemExit, match="cloud-only"):
        local.offers(["gpu-48gb", "gpu-80gb"])
    with pytest.raises(ValueError, match="30 GB"):
        local.take("judge", "key")
    first = local.take("pixal", "key")
    assert first["here"] and first["price"] == 0.0 and first["host"] == "172.17.0.2"
    assert first["id"].startswith("score-this-pc-pixal:")  # its kind's own container
    assert execs == [local.INSTALLER_CACHES]  # its layer past LAYER_LIMIT_GB: the caches went before the claim
    assert local.take("pixal", "key") is None  # one claim a container
    assert local.take("blender", "key") is None  # unmeasured, the Pixal3D claim holds the whole memory
    assert local.delete("score-this-pc-pixal:another", "this-pc") is False and not restarted  # a watchdog's late delete
    assert local.delete(first["id"], "this-pc") is True and restarted  # its own claim ends: the container restarted
    local.delete(local.take("pixal", "key")["id"], "this-pc")
    assert execs.count(local.INSTALLER_CACHES) == 1  # measured again only after LAYER_EVERY_SECONDS
    import scaleway
    monkeypatch.setattr(scaleway, "object_store", lambda: {"bucket": "the-library-bucket"})
    assert local.object_store() == {"bucket": "the-library-bucket"}  # the library's blobs, where its secrets are


def test_this_pc_shares_its_blender_turns_across_places_and_restarts_only_when_left_alone(monkeypatch, tmp_path):
    import os
    import capacity
    import local
    import spread
    monkeypatch.setattr(local, "LOCK", tmp_path / "this-pc.lock")
    monkeypatch.setattr(local, "running", lambda public_key, name=None: "172.17.0.2")
    monkeypatch.setattr(local, "RUNS_AT_ONCE", {"pixal": 1, "blender": 3})
    monkeypatch.setattr(capacity.provider, "cloud", local)
    restarted, execs = [], []

    def docker(*arguments, **_):
        restarted.extend([arguments] if arguments[0] == "restart" else [])
        execs.extend([(len(restarted), arguments[-1])] if arguments[2:4] == ("sh", "-c") else [])
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(local, "docker", docker)
    first = local.take("blender", "key")  # one place's bake row: every free turn
    assert first["turns"] == 3 and spread.slots("blender", first) == [0, 0, 0]
    assert local.take("blender", "key") is None  # every turn busy
    ended = threading.Event()
    spread.work_turn(first, spread.Shares([]), lambda *_: None, 0, ended)  # two of its slots ran out of work
    spread.work_turn(first, spread.Shares([]), lambda *_: None, 0, ended)
    second = local.take("blender", "key")  # another place's bake row, while the first still runs a job
    assert second is not None and second["turns"] == 2 and spread.slots("blender", second) == [0, 0]
    assert local.take("pixal", "key") is None  # its card share does not fit beside the Blender claims': it waits
    local.let_go_turn(second["id"])
    third = local.take("blender", "key")  # a turn is free: it joins the group's card, past the Pixal3D claim that
    assert third is not None  # does not fit (card_queue.blocks), while that one has waited under its bound
    local.let_go_turn(third["id"])
    monkeypatch.setattr(card_queue, "BACKFILL_SECONDS", 0)
    assert local.take("blender", "key") is None  # the Pixal3D claim waited its bound: nothing passes it now
    for claim in (first, second, third):
        local.ends_with(claim["id"], f"rm -rf /job/{claim['id']}")
    execs.clear()
    assert local.delete(first["id"], local.ZONE) is True and not restarted  # the others' jobs still run
    assert not execs  # nothing of theirs goes: an input of one may be another's
    assert local.delete(third["id"], local.ZONE) is True and not restarted
    assert local.delete(second["id"], local.ZONE) is True and restarted  # the last to leave restarts it
    assert execs == [(1, f"rm -rf /job/{second['id']}; {local.swept()}")]  # then every job file

    alone = local.take("pixal", "key")
    assert alone is not None
    local.delete(alone["id"], local.ZONE)

    home = tmp_path / "pc"  # the runner's folders a sweep empties: each once, never the container's own
    monkeypatch.setattr(local.pathlib.Path, "home", lambda: home)
    monkeypatch.setattr(local, "HOME", home / ".props")
    monkeypatch.setattr(local, "REPO", pathlib.Path("/root/repo"))
    monkeypatch.setattr(local.tempfile, "tempdir", str(tmp_path / "t"))
    assert local.runner_paths() == [home, tmp_path / "t"]
    for leftover in (home / ".props/store/take.png", home / "work/out/a.glb", tmp_path / "t/blender_tmp/x"):
        leftover.parent.mkdir(parents=True, exist_ok=True)
        leftover.write_text("x")
    subprocess.run(["sh", "-c", local.swept()], check=True)
    assert home.is_dir() and not any(home.iterdir()) and not any((tmp_path / "t").iterdir())


def test_this_pc_marks_a_claim_that_waits_holding_none_and_drops_the_mark_once_it_holds_one(monkeypatch, tmp_path):
    """The runner's drive counts a node apart from --jobs while it holds such a mark (score/graph CLAIM_WAITERS); the
    mark of a process that died waiting is swept (2026-11-02: 76 of 80 marks were of dead processes).
    Break: tools/cloud/backends/local.py: '    mark_waiting(handle is None)' -> '    mark_waiting(False)'
    Break: tools/cloud/backends/local.py: `            other.unlink(missing_ok=True)` -> `            pass`"""
    import fcntl
    import os
    import local
    monkeypatch.setattr(local, "LOCK", tmp_path / "this-pc.lock")
    monkeypatch.setattr(local, "running", lambda public_key, name=None: "172.17.0.2")
    monkeypatch.setattr(local, "RUNS_AT_ONCE", {"pixal": 1, "blender": 3})
    monkeypatch.setattr(local, "docker", lambda *arguments, **_: None)
    mark = local.waiting_claims() / str(os.getpid())
    local.waiting_claims().mkdir(parents=True)
    gone, alive = local.waiting_claims() / str(2**22 + 7), local.waiting_claims() / str(os.getppid())
    gone.touch()  # a process that died while it waited (no pid is this high: Linux's pid_max at most 2**22)
    alive.touch()
    holder = local.LOCK.open("a+")
    fcntl.flock(holder, fcntl.LOCK_EX)  # another claim holds the machine
    assert local.take("blender", "key") is None and mark.exists()
    assert not gone.exists() and alive.exists()  # the dead one's mark swept, a live one's kept
    holder.close()
    held = local.take("blender", "key")
    assert held is not None and not mark.exists()
    assert local.take("blender", "key") is None and not mark.exists()  # it waits for more, but holds a claim
    local.delete(held["id"], local.ZONE)


def test_this_pc_refuses_a_job_by_its_measured_need_not_its_kind(monkeypatch, tmp_path):
    import local
    monkeypatch.setattr(local, "LOCK", tmp_path / "this-pc.lock")
    monkeypatch.setattr(local, "running", lambda public_key, name=None: "172.17.0.2")
    monkeypatch.setattr(local, "memory_cap", lambda: "35g")
    monkeypatch.setattr(local, "alone_cap", lambda: "35g")
    monkeypatch.setattr(local, "docker", lambda *arguments, **_: None)  # never the PC's own containers
    with pytest.raises(ValueError, match="17 GB of card"):
        local.take("characters", "key")  # the whole machine: Kimodo's encoder on the card
    with pytest.raises(ValueError, match="40.0 GB of memory"):
        local.take("characters", "key", {"card_gb": 4, "memory_gb": 40})
    assert local.take("characters", "key", {"card_gb": 4, "memory_gb": 17})["here"]


def test_this_pc_runs_a_job_past_its_container_alone_in_the_container_raised_for_it(monkeypatch, tmp_path):
    import os
    import capacity
    import local
    import spread
    monkeypatch.setattr(local, "LOCK", tmp_path / "this-pc.lock")
    monkeypatch.setattr(local, "running", lambda public_key, name=None: "172.17.0.2")
    monkeypatch.setattr(local, "RUNS_AT_ONCE", {"pixal": 1, "blender": 3})
    monkeypatch.setattr(local, "memory_cap", lambda: "27g")
    monkeypatch.setattr(local, "alone_cap", lambda: "35g")
    monkeypatch.setattr(capacity.provider, "cloud", local)
    room = [20 * 2**30]
    monkeypatch.setattr(local, "alone_room", lambda name=None: room[0])
    calls = []
    monkeypatch.setattr(local, "docker", lambda *arguments, **_: calls.append(arguments))
    updates = lambda: [call[call.index("--memory") + 1] for call in calls if call[0] == "update"]  # noqa: E731
    base = {"memory_gb": 29.8e9 / 2**30}
    shared = local.take("blender", "key")
    assert shared["turns"] == 3
    assert local.take("blender", "key", base) is None  # it waits for the shared claim to leave
    local.delete(shared["id"], local.ZONE)
    assert local.take("blender", "key", base) is None and "35g" not in updates()  # 20 GiB free: it waits
    (local.wanting() / str(os.getpid())).rename(local.wanting() / str(os.getppid()))  # as another live process's
    assert local.take("blender", "key") is None  # its want keeps new Blender claims out meanwhile
    room[0] = 33 * 2**30
    alone = local.take("blender", "key", base)
    assert alone["turns"] == 1 and spread.slots("blender", alone) == [0] and updates()[-1] == "35g"
    assert local.take("blender", "key") is None
    local.delete(alone["id"], local.ZONE)
    assert updates()[-1] == "27g"  # back to the shared cap once it leaves
    with pytest.raises(ValueError, match="with the job alone"):
        local.take("blender", "key", {"memory_gb": 40})
    (local.wanting() / str(os.getppid())).unlink()  # that want is gone
    small = local.take("blender", "key", {"memory_gb": 6})
    assert small["turns"] == 3
    local.delete(small["id"], local.ZONE)


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
    monkeypatch.setattr(local, "answering", lambda name=None: "172.17.0.2")
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
        monkeypatch.setattr(local, "running", lambda public_key, name=None: "172.17.0.2")
        monkeypatch.setattr(capacity.provider, "cloud", local)
        calls = []
        monkeypatch.setattr(local, "docker", lambda *arguments, **_: calls.append(arguments))
        machine = local.take("blender", "key")
        assert ("cp", str(local.CARD_TURN), f"{local.MACHINE}:{card_turn.STARTUP}/.card_turn.py.new") in calls
        assert ("exec", local.MACHINE, "mv", f"{card_turn.STARTUP}/.card_turn.py.new",
                f"{card_turn.STARTUP}/card_turn.py") in calls
        assert spread.slots("blender", machine) == [0, 0, 0, 0]  # four side by side, all on the one card
        local.delete(machine["id"], local.ZONE)
        alone = local.take("pixal", "key")
        assert spread.slots("pixal", alone) == [0]
        local.delete(alone["id"], local.ZONE)
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


def test_a_waiting_sim_body_share_goes_before_the_env_run_s_next_claims(card_queue_folder):
    bake = card_queue.take("bake@lab", 9.7, "env-run", "blender")
    assert bake and card_queue.take("sim-body-l1", 6, "sim-body") is None  # 9.7 + 6 passes 13.5: it waits
    assert card_queue.take("similar", 1, "env-run") is None  # it would fit, but the sim body waits first
    card_queue.release(bake)
    tuning = card_queue.take("sim-body-l1", 6, "sim-body")
    assert tuning and card_queue.take("similar", 1, "env-run")  # beside it, once it has its share


def test_the_card_queue_never_passes_the_card_and_a_waiting_env_run_claim_keeps_side_jobs_off(card_queue_folder):
    first = card_queue.take("bake@lab", 9.7, "env-run", "blender")
    second = card_queue.take("bake@hub", 9.7, "env-run", "blender")  # the same group: the card's turns are shared
    assert first and second
    assert card_queue.take("sim-body", 6, "other") is None  # 9.7 + 6 passes 13.5
    card_queue.release(first)
    card_queue.release(second)
    side = card_queue.take("sim-body", 6, "other")
    assert side and card_queue.take("pixal", 10.8, "env-run") is None  # 6 + 10.8 passes it: the env-run claim waits
    assert card_queue.take("proof", 1, "other") is None  # it would fit, but the env-run claim asked first
    old = card_queue.take("old-run", 1, "film")  # a run frozen before the rename still writes "film": env-run's rank,
    assert old  # so it goes past the Pixal3D claim of its rank that does not fit (blocks), as the proof may not
    card_queue.release(old)
    assert "2 waiting" in card_queue.status()  # the env-run claim and the proof
    card_queue.release(side)
    film = card_queue.take("pixal", 10.8, "env-run")
    assert film and card_queue.take("tuning", None, "other") is None  # unmeasured: the whole card
    card_queue.release(film)
    assert re.match(r"card 0\.0 of 13\.5 GB held, memory 0\.0 of 27 GiB, 2 waiting; \d+\.\d GB free; score-this-pc 3GiB / 27GiB",
                    card_queue.status())
    sized = subprocess.run([sys.executable, "-c", "import card_queue; print(card_queue.BUDGET_GB, card_queue.DESKTOP_GB)"],
                           cwd=card_queue.__file__.rpartition("/")[0], capture_output=True, text=True, check=True,
                           env={**os.environ, "SCORE_CARD_BUDGET_GB": "78", "SCORE_CARD_DESKTOP_GB": "0"})
    assert sized.stdout.split() == ["78.0", "0.0"]  # a rented card's whole size, no desktop on it


def until(done, seconds=30):
    """Whether `done()` came true within `seconds`, asked every 50 ms (the subprocess under test works meanwhile)."""
    give_up = time.time() + seconds
    while not done() and time.time() < give_up:
        time.sleep(0.05)
    return done()


def test_a_claim_that_fits_goes_past_an_earlier_one_that_does_not_but_never_for_long(monkeypatch, card_queue_folder):
    """Round 38, 2026-10-31: sim body's 3 GB and one Blender claim's 9.7 GB held 12.7 of 13.5 GB of the card; a MOSS
    claim (10 GB) waited first, and two more Blender claims, which join their group's held share and add no card, waited
    behind it while the card stood nearly idle. A waiter that fits goes past one of its rank that does not, until that
    one has waited BACKFILL_SECONDS; one that fits keeps its turn.
    Break: in `blocks`, drop `or now - waiter["since"] >= BACKFILL_SECONDS` -> the MOSS claim is passed for ever; or
    return True for the same rank -> the Blender claims wait behind MOSS again."""
    tuning = card_queue.take("sim-body-l1d", 3, "sim-body")
    bakes = card_queue.take("this-pc blender", 9.7, "env-run", "blender", memory=8)
    assert tuning and bakes
    assert card_queue.take("this-pc moss-sound", 10, "env-run", memory=20) is None  # 3 + 9.7 + 10: it waits
    second = card_queue.take("other blender", 9.7, "env-run", "blender", memory=8)
    assert second  # joins the group's card share: it fits, MOSS does not, MOSS has waited under the bound
    assert card_queue.take("small proof", 1, "env-run", memory=1) is None  # 1 more passes 13.5: it waits too
    card_queue.release(card_queue.WAITING.pop(("small proof", "env-run")))
    monkeypatch.setattr(card_queue, "BACKFILL_SECONDS", 0)  # MOSS has waited long enough: nothing passes it now
    assert card_queue.take("third blender", 9.7, "env-run", "blender", memory=8) is None
    card_queue.release(card_queue.WAITING.pop(("third blender", "env-run")))
    for share in (bakes, second):
        card_queue.release(share)
    assert card_queue.take("this-pc moss-sound", 10, "env-run", memory=20)  # the group gone, MOSS fits


def test_a_claim_that_cannot_fit_beside_an_earlier_priority_keeps_nothing_out(monkeypatch, card_queue_folder):
    """Round 41, 2026-10-31: sim body held 3 GB; a segment claim asked the whole 13.5 GB, which can never fit beside
    it, and once it had waited BACKFILL_SECONDS every likeness claim queued behind it with the card idle.
    Break: in `blocks`, drop `and could_fit(waiter, held)` -> the likeness claim waits behind segment for ever."""
    tuning = card_queue.take("sim-body-l1d", 3, "sim-body")
    assert tuning and card_queue.take("this-pc segment", None, "env-run") is None  # the whole card: it waits
    monkeypatch.setattr(card_queue, "BACKFILL_SECONDS", 0)
    likeness = card_queue.take("this-pc similar", 0.8, "env-run", memory=1)
    assert likeness  # segment cannot fit until the sim body share goes: it keeps nothing out meanwhile
    card_queue.release(likeness)
    card_queue.release(tuning)
    assert card_queue.take("this-pc segment", None, "env-run")  # alone on the card, it fits


def test_a_side_job_gives_the_card_way_to_a_film_claim_waiting_and_starts_again_after(monkeypatch, card_queue_folder,
                                                                                         tmp_path, request):
    starts = tmp_path / "starts"
    tuning = (f"import os, sys; open({str(starts)!r}, 'a').write(f'{{os.getpid()}}\\n'); sys.stdin.read()")
    holder = subprocess.Popen([sys.executable, card_queue.__file__, "run", "--job", "tuning", "--card-gb", "6", "--",
                               sys.executable, "-c", tuning],
                              stdin=subprocess.PIPE, env={**os.environ, "SCORE_CARD_QUEUE": str(card_queue_folder)})
    request.addfinalizer(holder.kill)  # a red run leaves no queue runner behind (its command ends with it)
    assert until(lambda: starts.exists() and "held tuning" in card_queue.status())
    assert card_queue.take("pixal", 10.8, "env-run") is None  # 6 + 10.8 passes the card: it waits
    monkeypatch.setattr(card_queue, "YIELD_SECONDS", 0)  # it has waited long enough: the side share is asked back
    film = None

    def admitted():
        nonlocal film
        film = film or card_queue.take("pixal", 10.8, "env-run")
        return film

    assert until(admitted)
    first = int(starts.read_text().split()[0])
    with pytest.raises(ProcessLookupError):
        os.kill(first, 0)  # the tuning was stopped, not left on the card beside the env-run claim
    assert "waits tuning" in card_queue.status()  # its run waits again behind the env-run claim, its share given back
    card_queue.release(film)
    assert until(lambda: len(starts.read_text().split()) == 2)  # started again once the env-run claim let go
    holder.stdin.close()
    assert holder.wait(30) == 0 and card_queue.take("pixal", 10.8, "env-run")  # it ended: its share is free
    assert card_queue.measured().startswith("tuning: 2 takes, card 6.39 GB (2 alone), cores ")  # both runs measured


def test_this_pc_claims_hold_their_card_share_and_wait_while_a_side_job_holds_the_card(monkeypatch, tmp_path):
    import local
    monkeypatch.setattr(local, "LOCK", tmp_path / "this-pc.lock")
    monkeypatch.setattr(local, "running", lambda public_key, name=None: "172.17.0.2")
    monkeypatch.setattr(local, "docker", lambda *arguments, **_: None)
    side = card_queue.take("sim-body", 6, "other")
    likeness = local.take("similar", "key")  # DINOv2's measured 0.8 GB fits beside it
    beside = card_queue.take("side memory", 1, "other", memory=20)  # it holds its measured 1.3 GB, not all 27
    assert likeness and beside
    card_queue.release(beside)
    local.delete(likeness["id"], "this-pc")
    bake = local.take("library", "key")  # the library bakes' measured 1.4 GB fits beside it too
    assert bake
    local.delete(bake["id"], "this-pc")
    assert local.take("pixal", "key") is None  # 6 + 10.8 passes the card: it waits, holding no claim
    assert local.queued("pixal") and not local.queued("blender")  # in the queue: park.here holds its minutes
    with local.container_lock("score-this-pc-pixal").open("a+") as probe:
        assert local.got(probe, True)  # its container's lock was let go
    card_queue.release(side)
    machine = local.take("pixal", "key")
    assert machine and card_queue.take("sim-body", 6, "other") is None  # the claim holds its share
    assert not local.queued("pixal")
    assert until(lambda: local.CARDS[machine["id"]].card_peak)  # the card read while it holds it
    local.delete(machine["id"], "this-pc")
    assert card_queue.take("sim-body", 6, "other")
    assert "this-pc pixal: 1 takes, card 6.39 GB (1 alone)" in card_queue.measured()  # the claim was measured


def test_this_pc_claims_memory_is_read_from_its_container_and_counted_only_alone_there(monkeypatch, tmp_path):
    """2026-10-31: `measured` showed "memory unmeasured" for every claim of this PC. A claim's memory is its
    container's anon bytes (cgroup memory.stat) at their highest while it holds its share; a reading taken while
    another claim held the same container (two places' Blender claims in score-this-pc) is not alone and is left out
    of the kind's measure, as a card reading beside another share is."""
    import local
    monkeypatch.setattr(local, "LOCK", tmp_path / "this-pc.lock")
    monkeypatch.setattr(local, "RUNS_AT_ONCE", {"blender": 3})
    monkeypatch.setattr(local, "running", lambda public_key, name=None: "172.17.0.2")
    monkeypatch.setattr(local, "docker", lambda *arguments, **_: None)
    monkeypatch.setattr(card_queue, "MEMORY_LOOK_SECONDS", 0.01)
    cgroup = tmp_path / "cgroup"
    cgroup.mkdir()
    stat = cgroup / "memory.stat"
    monkeypatch.setattr(local, "cgroup_of", lambda name=None: cgroup)
    stat.write_text(f"anon {3 * 10**9}\nfile {9 * 10**9}\n")  # the page cache is not the claim's need
    alone = local.take("blender", "key")
    assert until(lambda: local.CARDS[alone["id"]].memory_peak)
    local.delete(alone["id"], local.ZONE)
    first = local.take("blender", "key")
    local.let_go_turn(first["id"])
    local.let_go_turn(first["id"])
    second = local.take("blender", "key")  # another place's bake row in the same container
    stat.write_text(f"anon {5 * 10**9}\nfile 0\n")  # both claims' jobs together
    assert until(lambda: all(local.CARDS[claim["id"]].memory_peak == 5 * 10**9 for claim in (first, second)))
    local.delete(second["id"], local.ZONE)
    local.delete(first["id"], local.ZONE)
    assert "memory 3.0 GB (1 alone)" in card_queue.measured().split("this-pc blender: 3 takes")[1]


def test_this_pc_container_keeps_cores_for_the_pc_and_a_measured_claim_to_its_memory(monkeypatch, tmp_path):
    import local
    monkeypatch.setattr(local, "LOCK", tmp_path / "this-pc.lock")
    monkeypatch.setattr(local, "answering", lambda name=None: "172.17.0.2")
    monkeypatch.setattr(local, "memory_cap", lambda: "27g")
    monkeypatch.setattr(local.os, "cpu_count", lambda: 24)
    calls = []
    monkeypatch.setattr(local, "docker", lambda *arguments, **_: calls.append(arguments) or types.SimpleNamespace(
        returncode=0, stdout="true", stderr=""))
    machine = local.take("characters", "key", {"card_gb": 4, "memory_gb": 17})
    own = "score-this-pc-characters"
    assert ("update", "--memory", "27g", "--memory-swap", "27g", "--cpus", "20", own) in calls
    assert ("update", "--memory", "26g", "--memory-swap", "26g", own) in calls  # 17 GB measured, x1.5
    local.delete(machine["id"], "this-pc")
    updates = [call for call in calls if call[0] == "update"]
    assert updates[-1] == ("update", "--memory", "27g", "--memory-swap", "27g", own)  # set back
    calls.clear()
    local.delete(local.take("pixal", "key")["id"], "this-pc")
    assert not [call for call in calls if call[:2] == ("update", "--memory") and call[2] != "27g"]  # no measure: 27g
    calls.clear()  # a sim-body chain's memory_gb is blender_cloud's Blender prediction (2 GB), never its measure
    local.delete(local.take("sim-body", "key", {"memory_gb": 1.86})["id"], "this-pc")
    assert not [call for call in calls if call[:2] == ("update", "--memory") and call[2] != "27g"]  # not 3g


def test_this_pc_claims_of_different_kinds_run_side_by_side_each_in_its_own_container_while_they_fit(monkeypatch,
                                                                                                       tmp_path):
    import local
    monkeypatch.setattr(local, "LOCK", tmp_path / "this-pc.lock")
    monkeypatch.setattr(local, "RUNS_AT_ONCE", {"pixal": 1, "blender": 3})
    started = []
    monkeypatch.setattr(local, "running", lambda public_key, name=None: started.append(name) or "172.17.0.2")
    monkeypatch.setattr(local, "docker", lambda *arguments, **_: None)
    bakes = local.take("blender", "key")  # three turns: 3 x 6.7 + 2 = 22.1 GiB, 9.7 GB of card
    route = local.take("characters", "key", {"card_gb": 1, "memory_gb": 3})  # 25.1 GiB and 10.7 GB: it fits
    assert bakes["id"].startswith("score-this-pc:") and route["id"].startswith("score-this-pc-characters:")
    assert started == ["score-this-pc", "score-this-pc-characters"]
    assert local.take("pixal", "key") is None  # unmeasured: the whole memory, so it waits for both
    local.delete(route["id"], local.ZONE)
    local.delete(bakes["id"], local.ZONE)
    alone = local.take("pixal", "key")
    assert alone and local.take("characters", "key", {"card_gb": 1, "memory_gb": 3}) is None  # now it holds it all
    local.delete(alone["id"], local.ZONE)
    card_queue.release(card_queue.WAITING.pop(("this-pc characters", "env-run")))  # that claim stopped asking
    monkeypatch.setattr(local, "OWN", False)  # the run did not ask for containers of their own: one, as before
    bakes = local.take("blender", "key")
    assert bakes["id"].startswith("score-this-pc:") and local.take("characters", "key", {"card_gb": 1,
                                                                                          "memory_gb": 3}) is None
    local.delete(bakes["id"], local.ZONE)
    with (card_queue.QUEUE / "measures.jsonl").open("a") as measures:  # sim-body's claims, measured by the queue
        for card_gb, memory_gb in ((3.6, 3.12), (2.9, 2.4), (3.2, 2.9), (2.6, 2.1), (3.4, 2.7)):
            measures.write(json.dumps({"job": "this-pc sim-body", "card_gb": card_gb, "alone": True, "cores": 9.7,
                                       "memory_gb": memory_gb, "memory_alone": True}) + "\n")
    bakes = local.take("blender", "key")  # 9.7 GB of card, 22.1 GiB
    body = local.take("sim-body", "key", {"memory_gb": 1.86})  # beside them: 3.6 GB, 3.12 GB x 1.5 = 4.4 GiB
    assert body["id"].startswith("score-this-pc:") and body["id"] != bakes["id"]
    assert [round(share["memory_gb"], 1) for share in card_queue.live("held") if share["job"] == "this-pc sim-body"] \
        == [4.4]
    assert local.take("sim-body", "key") is None  # a second sim body: 16.9 GB of card does not fit, it waits
    card_queue.release(card_queue.WAITING.pop(("this-pc sim-body", "env-run")))
    import capacity
    monkeypatch.setattr(capacity.provider, "cloud", local)
    monkeypatch.delenv("SCORE_MAX_MACHINES", raising=False)
    assert capacity.run_cap() == local.claims_at_once() == 2  # similar's 0.8 and sim-body's 3.6; the bakes' 9.7 not
    local.delete(body["id"], local.ZONE)
    local.delete(bakes["id"], local.ZONE)
