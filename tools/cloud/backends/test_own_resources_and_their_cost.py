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
  A waiter that fits goes past an earlier one of its rank that does not, until that one has waited BACKFILL_SECONDS,
  and one that can never fit beside the shares of an earlier priority keeps nothing out (rounds 38 and 41).
  Break: in `blocks`, drop `or now - waiter["since"] >= BACKFILL_SECONDS` -> the MOSS claim is passed for ever; or
  return True for the same rank -> the Blender claims wait behind MOSS again; or drop `and could_fit(waiter, held)`
  -> the likeness claim waits behind segment for ever.
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
  waits; or `at_once() if at_once else max(...)` -> `max(...)` in `capacity.caps` -> the cap reads 20; or one
  machine id for every claim in `take` -> the sim-body claim is the bakes' own handed back.
- A claim's memory is its container's highest anon reading while it holds its share, counted for its kind only from
  claims alone in that container. Break: drop the `card_queue.watch_memory(...)` call in `local.take` -> memory
  unmeasured; or drop `and not any(beside(...))` in `card_queue.read_memory` -> 5.0 GB from the two claims together;
  or drop `memory_gb = round(handle.memory_peak / 1e9, 2)` in `record` -> unmeasured.
- A claim the card queue refused says so (`queued`), so park.here holds its run's minutes while it waits there.
  Break: `return any(...)` -> `return False` in `queued`.
- A claim that waits holding none is marked so (the runner's drive counts its node apart from --jobs, score/graph
  CLAIM_WAITERS), the mark dropped once it holds one, and the mark of a process that died waiting is swept (2026-11-02:
  76 of 80 marks were of dead processes). Break: `mark_waiting(not handles)` -> `mark_waiting(False)` in `take`; or
  `other.unlink(missing_ok=True)` -> `pass` in `mark_waiting`.
"""
import contextlib
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
import local  # noqa: E402
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


def ledger_lines():
    """The cloud ledger's lines as written so far (the account's own fresh file)."""
    import ledger
    return [json.loads(line) for line in ledger.LEDGER.read_text().splitlines()] if ledger.LEDGER.exists() else []


def scaleway_account(monkeypatch, tmp_path, request):
    """One account holding our project's resources beside another's, the backend reaching it only through
    `subprocess.run`, the cloud ledger a fresh file; no sleep waits, its quota pages and prices read from here."""
    import ledger
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.jsonl")
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
ONE_HOUR = 60 * 0.00013 + 0.005  # 60 GB at EUR 0.00013 a GB-hour, one address at EUR 0.005 an hour
CONSTRAINT = "Failed to detach block volume v-1: volume_id does not respect constraint"

# The Scaleway account's steps (see ASKS for the queue's): ("account",: the account of our project and another's),
# ("listed", what the account lists, its records), ("registry", namespaces listed or None, the endpoint registry()
# gives or "public" refused, namespaces made), ("runtime key",: made scoped to our project, kept only in Secret
# Manager), ("month spend", euros), ("bill all", the last whole, what it reads or the words it raises), ("owners",
# OWNERS), ("quotas", the IAM pages or "403", what zone_quotas reads), ("parked", our runs' parked records),
# ("cloud offers", classes asked, {(class, zone): (stock word, stock)} or None, the zones' type lists read),
# ("rent", number, *ADDRESSES row), ("refused but made", name: HTTP 500 that made it anyway), ("hours", HOURS),
# ("cloud delete", machine, True / False / the words it raises), ("fee", machine, its disk-and-address euros or None),
# ("refusals", (command head, Scaleway's words, the machine that vanishes meanwhile or None)), ("terminate", machine,
# zone), ("delete address", id), ("delete disk", id, whether it raises), ("start if stopped", machine, words) or
# ("leftovers", the loose addresses left).
CLOUD = [
    ("account",),
    # the container path: the registry is our own private namespace, made when only another's is listed; the runtime
    # key (only another project's secret is listed) is made scoped to our project and kept only in Secret Manager
    *[("registry", listed, endpoint, made) for _, listed, endpoint, made in NAMESPACES],
    ("runtime key",),
    # the bill: our project's own lines; the cap's whole bill reads every project and counts SCORE's usage
    ("listed", "bill", BILL),
    ("month spend", 1.5),
    ("bill all", None, {"whole": 187.0, "lines": {"farm-factory|/instance/server/l4_1_24g/fr-par-2": 10.0,
                                                   "score-conductor|/storage/b": 2.5,
                                                   f"{SHARED}|/instance/server/l4_1_24g/fr-par-2": 40.0},
                        "projects": {OURS: OURS, OTHER: OTHER, "farm-factory": "ff", "score-conductor": "sc",
                                     SHARED: "bp", "babon-worker": "bw"}}),
    ("bill all", 190.0, "below"),
    ("owners", OWNERS),
    ("listed", "bill", []),
    ("bill all", None, "no line"),
    # offers: quotas read by type and zone, a processor class in every rent zone with quota, a card class in the card
    # zones only, each zone's type list read once, a short type our run parked offered as parked (an expired record
    # and a half-written one do not count)
    ("listed", "types", TYPES),
    ("quotas", QUOTA_PAGES, {
        ("POP2-HC-48C-96G", "nl-ams-2"): 1, ("POP2-HC-48C-96G", "fr-par-1"): 1, ("POP2-HC-48C-96G", "pl-waw-1"): 0,
        ("L4-1-24G", "fr-par-1"): float("inf"), ("L4-1-24G", "nl-ams-2"): 50, ("POP2-32C-128G", "fr-par-2"): 2,
        ("POP2-32C-128G", "pl-waw-2"): 2}),
    ("parked", [{"type": "POP2-32C-128G", "zone": "fr-par-2", "until": 600},
                {"type": "POP2-32C-128G", "zone": "pl-waw-2", "until": -60}]),
    ("set", scaleway, "ZONES", ("fr-par-1", "fr-par-2", "pl-waw-2")),
    ("set", scaleway, "PROCESSOR_ZONES", ("nl-ams-2", "fr-par-1")),
    ("cloud offers", ["cpu-64c-128gb", "cpu-48c-96gb", "gpu-24gb", "cpu-32c-128gb"], {
        ("cpu-48c-96gb", "fr-par-1"): ("available", 0), ("gpu-24gb", "fr-par-1"): ("available", 0),
        ("cpu-32c-128gb", "fr-par-2"): ("parked", 1), ("cpu-32c-128gb", "pl-waw-2"): ("shortage", 2),
        ("cpu-48c-96gb", "nl-ams-2"): ("available", 0)},
     ["zone=fr-par-1", "zone=fr-par-2", "zone=pl-waw-2", "zone=nl-ams-2"]),
    ("cloud offers", ["gpu-24gb"], None, ["zone=fr-par-1", "zone=fr-par-2", "zone=pl-waw-2"]),  # no processor zone
    ("quotas", "403", None),  # the conductor's key reads no quota (403, 2026-10-24): none known
    # renting: a new machine's bad address is swapped for a fresh one and quarantined, or the machine deleted
    *[("rent", number, *address) for number, address in enumerate(ADDRESSES, 1)],
    # a refused order's own machine (HTTP 500 that made it anyway, 2026-10-22: stopped, billed, unwatched) and its own
    # loose address and disk are deleted, their euros its ledger line; another order's racing address is left alone
    ("refused but made", "masks-1"),
    # every euro: a machine's disk and address are billed by the started hour from its creation, one ledger line
    # written when it is deleted; a machine already gone deletes nothing and writes nothing
    ("hours", HOURS),
    ("cloud delete", "srv-blender-2", True), ("cloud delete", "srv-blender-2", False),
    ("fee", "srv-blender-2", ONE_HOUR),
    # deleting what another sweep already deleted is done (surfaces-bake@wreck, 2026-10-13: two sweeps on one
    # leftover; the second's refused detach killed its job), any other refusal raises; a machine the zone is still
    # making refuses its terminate until it is made: waited out, then deleted (2026-11-05, surfaces-bake@camp)
    ("refusals", [(("instance", "server", "terminate", "srv-wreck"), CONSTRAINT, "srv-wreck"),
                  (("instance", "server", "terminate", "srv-stuck"), CONSTRAINT, None),
                  (("instance", "server", "terminate", "srv-making"), ("precondition failed: , Cannot modify the SBS "
                   "volumes of an instance in the state SessionState.PROVISION"), None),
                  (("block", "volume", "delete", "v-1"), "permission denied", None)]),
    ("cloud delete", "srv-wreck", False), ("cloud delete", "srv-stuck", "does not respect constraint"),
    ("terminate", "srv-making", "fr-par-2"),
    ("fee", "srv-wreck", None), ("fee", "srv-stuck", None),
    ("delete address", "ip-1"),  # not found: another sweep's
    ("delete disk", "v-2", False), ("delete disk", "v-1", True),
    # a machine whose state cannot be read is a refusal its waiter waits out and deletes, never a crash
    ("start if stopped", "srv-unknown", "server not found"),
    # what is left: only our own loose address is a leftover, never another project's, one on a machine or the
    # quarantined bad address
    ("leftovers", [("ip-old", "pl-waw-2", "1.1.1.1")])]


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


# A Blender job's measured need past the container's 27 GiB (base's light passes, round 31), and the route's claim.
ALONE = {"memory_gb": 29.8e9 / 2**30}
ROUTE = {"card_gb": 1, "memory_gb": 3}


# This PC's card queue and its claims as a run asks them (13.5 GB of card, 27 GiB of memory): (row, steps). A step is
# ("take", share's name or None, job, card GB, priority, group, memory GiB, whether it is admitted: True, False, or
# "in time" while it keeps asking), ("release", name), ("drop", job, priority: a waiter that stopped asking), ("set",
# module, its constant, its value), ("status" or "measured", the pattern that line matches), ("sized", environment,
# BUDGET_GB and DESKTOP_GB as a fresh process reads them), ("run", job, card GB: `card_queue run` of a command that
# notes each start and lives until its input ends, once it holds its share), ("starts", job, its command's starts so
# far, how many of the first are stopped), ("end", job: its input ends, the run exits 0), ("operators", Blender
# operator names called at once through card_turn, the most card calls on the card together) or ("beside", the card
# slots held, an operator that must still run within 5 s).
# This PC's own steps: ("pc size", GiB of memory, memory_cap, Blender jobs at once as local loads), ("offers", the
# classes a run asks, the classes offered or the words of the refusal), ("library store",: local's object store is the
# Scaleway backend's), ("pc",: the PC's world, its container 27g (35g with a job alone, 20 GiB of room free for one at
# first) and every docker call it makes kept), ("runner paths",), ("claim", name, kind, need, None when it waits, the
# words of its refusal, or what the claim holds: turns, slots, id prefix, here, price, host, "not" another claim's
# id), ("delete", name or machine id, what delete answers or None), ("mark", label: the docker calls so far, or with
# "peaks" the Blender kind's takes so far), ("called", a docker call made), ("last update", the last update call),
# ("uncapped since", label: no claim held under 27g), ("memory never" / "memory now", a cap the container's updates
# never / last gave), ("waiters",: a dead process's waiting mark and a live one's), ("waiting", whether this process's
# mark is there), ("waiters swept",), ("queued", kind, whether it is), ("lock free", container), ("card read", claim),
# ("memory peak", claims, bytes all read), ("work out", claim: a slot out of work), ("let go", claim), ("ends with",
# claims: each its clean-up), ("left alone since", label: no restart or exec), ("restarted", container),
# ("restart and sweep since", label, claim: the last to leave restarts and sweeps), ("peaks since", label, takes and
# alone memory takes added), ("sweep",: the runner's folders emptied, each kept), ("anon", anon and file bytes of the
# bakes' container's cgroup), ("card turn copied",), ("started since", label, containers started), ("want",
# "elsewhere" or "gone": a Blender job alone's want as another live process's), ("room", GiB free for a job alone),
# ("measures", job, (card GB, memory GB) of its takes), ("held memory", job, the GiB its held shares hold), ("run
# cap", claims at once) or ("containers", the containers made, each 27g of memory and swap and 20 of 24 cores, its
# installer caches gone once).
ASKS = [
    ("the Scaleway backend takes only our project's resources and counts every euro they cause", CLOUD),
    ("a waiting sim body share goes before the env run's next claims", [
        ("take", "bake", "bake@lab", 9.7, "env-run", "blender", 0, True),
        ("take", None, "sim-body-l1", 6, "sim-body", None, 0, False),  # 9.7 + 6 passes 13.5: it waits
        ("take", None, "similar", 1, "env-run", None, 0, False),  # it would fit, but the sim body waits first
        ("release", "bake"),
        ("take", "tuning", "sim-body-l1", 6, "sim-body", None, 0, True),
        ("take", None, "similar", 1, "env-run", None, 0, True)]),  # beside it, once it has its share
    ("never past the card; a waiting env-run claim keeps side jobs off", [
        ("take", "first", "bake@lab", 9.7, "env-run", "blender", 0, True),
        ("take", "second", "bake@hub", 9.7, "env-run", "blender", 0, True),  # one group: the card's turns are shared
        ("take", None, "sim-body", 6, "other", None, 0, False),  # 9.7 + 6 passes 13.5
        ("release", "first"), ("release", "second"),
        ("take", "side", "sim-body", 6, "other", None, 0, True),
        ("take", None, "pixal", 10.8, "env-run", None, 0, False),  # 6 + 10.8 passes it: the env-run claim waits
        ("take", None, "proof", 1, "other", None, 0, False),  # it would fit, but the env-run claim asked first
        # a run frozen before the rename still writes "film": env-run's rank, so it goes past the Pixal3D claim of its
        # rank that does not fit (blocks), as the proof may not
        ("take", "old", "old-run", 1, "film", None, 0, True),
        ("release", "old"),
        ("status", r"2 waiting"),  # the env-run claim and the proof
        ("release", "side"),
        ("take", "film", "pixal", 10.8, "env-run", None, 0, True),
        ("take", None, "tuning", None, "other", None, 0, False),  # unmeasured: the whole card
        ("release", "film"),
        ("status", r"^card 0\.0 of 13\.5 GB held, memory 0\.0 of 27 GiB, 2 waiting; \d+\.\d GB free; "
                   r"score-this-pc 3GiB / 27GiB")]),
    ("a rented card is sized to its own card, no desktop on it", [
        ("sized", {"SCORE_CARD_BUDGET_GB": "78", "SCORE_CARD_DESKTOP_GB": "0"}, ["78.0", "0.0"])]),
    # round 38, 2026-10-31: sim body's 3 GB and one Blender claim's 9.7 GB held 12.7 of 13.5 GB; a MOSS claim (10 GB)
    # waited first, and two more Blender claims, which join their group's held share and add no card, waited behind it
    # while the card stood nearly idle
    ("a claim that fits goes past an earlier one that does not, but never for long", [
        ("take", "tuning", "sim-body-l1d", 3, "sim-body", None, 0, True),
        ("take", "bakes", "this-pc blender", 9.7, "env-run", "blender", 8, True),
        ("take", None, "this-pc moss-sound", 10, "env-run", None, 20, False),  # 3 + 9.7 + 10: it waits
        # joins the group's card share: it fits, MOSS does not, MOSS has waited under the bound
        ("take", "second", "other blender", 9.7, "env-run", "blender", 8, True),
        ("take", None, "small proof", 1, "env-run", None, 1, False),  # 1 more passes 13.5: it waits too
        ("drop", "small proof", "env-run"),
        ("set", card_queue, "BACKFILL_SECONDS", 0),  # MOSS has waited long enough: nothing passes it now
        ("take", None, "third blender", 9.7, "env-run", "blender", 8, False),
        ("drop", "third blender", "env-run"),
        ("release", "bakes"), ("release", "second"),
        ("take", None, "this-pc moss-sound", 10, "env-run", None, 20, True)]),  # the group gone, MOSS fits
    # round 41, 2026-10-31: sim body held 3 GB; a segment claim asked the whole 13.5 GB, which can never fit beside it,
    # and once it had waited BACKFILL_SECONDS every likeness claim queued behind it with the card idle
    ("a claim that cannot fit beside an earlier priority keeps nothing out", [
        ("take", "tuning", "sim-body-l1d", 3, "sim-body", None, 0, True),
        ("take", None, "this-pc segment", None, "env-run", None, 0, False),  # the whole card: it waits
        ("set", card_queue, "BACKFILL_SECONDS", 0),
        # segment cannot fit until the sim body share goes: it keeps nothing out meanwhile
        ("take", "likeness", "this-pc similar", 0.8, "env-run", None, 1, True),
        ("release", "likeness"), ("release", "tuning"),
        ("take", None, "this-pc segment", None, "env-run", None, 0, True)]),  # alone on the card, it fits
    ("a side job gives the card way to an env-run claim waiting and starts again after", [
        ("run", "tuning", 6),
        ("take", None, "pixal", 10.8, "env-run", None, 0, False),  # 6 + 10.8 passes the card: it waits
        ("set", card_queue, "YIELD_SECONDS", 0),  # it has waited long enough: the side share is asked back
        ("take", "film", "pixal", 10.8, "env-run", None, 0, "in time"),
        ("starts", "tuning", 1, 1),  # the tuning was stopped, not left on the card beside the env-run claim
        ("status", r"waits tuning"),  # its run waits again behind the env-run claim, its share given back
        ("release", "film"),
        ("starts", "tuning", 2, 1),  # started again once the env-run claim let go
        ("end", "tuning"),
        ("take", "after", "pixal", 10.8, "env-run", None, 0, True),  # it ended: its share is free
        ("measured", r"^tuning: 2 takes, card 6\.39 GB \(2 alone\), cores ")]),  # both runs measured
    # card_turn.py, inside each Blender process: the bake and the renders take one of the card's two slots, any other
    # operator runs free beside them
    ("Blender's card calls take the card's slots, never more, and nothing else waits for them", [
        ("operators", ["object.bake", "render.render", "object.bake", "object.bake", "render.opengl"], 2),
        ("beside", 2, "object.select_all")]),
    # this PC orders nothing: what it serves is offered parked at EUR 0, its container sized to the PC's memory
    ("this PC costs nothing and sizes its container to its memory", [
        ("pc size", 43, "27g", 4), ("pc size", 12, "8g", 1),
        ("offers", ["gpu-80gb", "gpu-24gb", "cpu-32c-128gb", "gpu-24gb-x2"], ["gpu-24gb", "cpu-32c-128gb"]),
        ("offers", ["gpu-48gb", "gpu-80gb"], "cloud-only"),  # one card of at most 16 GB, never a second one
        ("library store",)]),  # the library's blobs, where its secrets are
    # one PC's day of claims: refusals by need, a side job's card share, kinds side by side in their own containers,
    # two places' Blender claims sharing the bakes' container's turns, a Blender job past the container alone in the
    # container raised for it, and sim body's measured share beside the bakes; the bakes' container's memory read from
    # its cgroup (2026-10-31: `measured` showed "memory unmeasured" for every claim here): its anon bytes at their
    # highest while a claim holds its share, a reading beside another claim in the same container left out
    ("this PC takes a claim only while its measured need fits beside what is held", [
        ("pc",), ("runner paths",),
        # judged by its measured need alone; Kimodo's encoder on the card is the whole characters machine
        ("claim", None, "judge", None, "30 GB"),
        ("claim", None, "characters", None, "17 GB of card"),
        ("claim", None, "characters", {"card_gb": 4, "memory_gb": 40}, "40.0 GB of memory"),
        ("claim", None, "blender", {"memory_gb": 40}, "with the job alone"),
        ("claim", "clips", "characters", {"card_gb": 4, "memory_gb": 17}, {"here": True}),  # clip steps fit
        ("delete", "clips", None),
        # the clip run: 20 of 24 cores, held to its 17 GB x 1.5, set back at its delete
        ("called", ("update", "--memory", "27g", "--memory-swap", "27g", "--cpus", "20", "score-this-pc-characters")),
        ("called", ("update", "--memory", "26g", "--memory-swap", "26g", "score-this-pc-characters")),
        ("last update", ("update", "--memory", "27g", "--memory-swap", "27g", "score-this-pc-characters")),
        # a side job holds 6 GB of the card: claims hold their measured share beside it, or wait holding none
        ("take", "side", "sim-body", 6, "other", None, 0, True),
        ("claim", "likeness", "similar", None, {}),  # DINOv2's measured 0.8 GB fits beside it
        ("take", "beside", "side memory", 1, "other", None, 20, True),  # it holds its measured 1.3 GB, not all 27
        ("release", "beside"), ("delete", "likeness", None),
        ("claim", "bake", "library", None, {}), ("delete", "bake", None),  # the library bakes' 1.4 GB fits too
        ("waiters",),
        ("claim", None, "pixal", None, None),  # 6 + 10.8 passes the card: it waits, holding no claim
        ("waiting", True), ("waiters swept",),  # marked waiting; the dead one's mark swept
        ("queued", "pixal", True), ("queued", "blender", False),  # in the queue: park.here holds its minutes
        ("lock free", "score-this-pc-pixal"),  # its container's lock was let go
        ("release", "side"),
        ("mark", "pixal"),
        ("claim", "pixal", "pixal", None, {"here": True, "price": 0.0, "host": "172.17.0.2",
                                           "id": "score-this-pc-pixal:", "slots": [0]}),  # unmeasured: all memory
        ("waiting", False),  # it holds a claim
        ("take", None, "sim-body", 6, "other", None, 0, False),  # the claim holds its card share
        ("claim", None, "characters", ROUTE, None),  # and all the memory: no kind beside it
        ("claim", None, "blender", None, None),
        ("claim", None, "pixal", None, None), ("waiting", False),  # one claim a container; it holds one
        ("queued", "pixal", False),
        ("card read", "pixal"),  # the card read while it holds it
        ("mark", "late"),
        ("delete", "score-this-pc-pixal:another", False),  # a watchdog's late delete
        ("left alone since", "late"),  # the claim it names is still held: nothing restarted
        ("delete", "pixal", None),
        ("restarted", "score-this-pc-pixal"),  # its own claim ends: the container restarted
        ("uncapped since", "pixal"),  # no measure: it keeps the container's 27g
        ("drop", "this-pc characters", "env-run"),  # that claim stopped asking
        ("take", "after", "sim-body", 6, "other", None, 0, True), ("release", "after"),
        ("measured", r"this-pc pixal: 1 takes, card 6\.39 GB \(1 alone\)"),  # the claim was measured
        # two places' Blender claims share the bakes' container's turns; it restarts only when the last leaves it
        ("mark", "peaks"),
        ("claim", "first", "blender", None, {"turns": 3, "slots": [0, 0, 0]}),  # one place's bake row: every turn
        ("memory peak", ["first"], 3 * 10**9),  # its container's anon bytes alone
        ("claim", None, "blender", None, None),  # every turn busy
        ("work out", "first"), ("work out", "first"),  # two of its slots ran out of work
        ("claim", "second", "blender", None, {"turns": 2, "slots": [0, 0]}),  # another place's, while the first runs
        ("anon", 5 * 10**9, 0),  # both claims' jobs together
        ("memory peak", ["first", "second"], 5 * 10**9),
        ("claim", None, "pixal", None, None),  # its card share does not fit beside the Blender claims': it waits
        ("let go", "second"),
        # a turn is free: it joins the group's card, past the Pixal3D claim that does not fit (card_queue.blocks),
        # while that one has waited under its bound
        ("claim", "third", "blender", None, {}),
        ("let go", "third"),
        ("set", card_queue, "BACKFILL_SECONDS", 0),
        ("claim", None, "blender", None, None),  # the Pixal3D claim waited its bound: nothing passes it now
        ("ends with", ["first", "second", "third"]),
        ("mark", "leaving"),
        ("delete", "first", True), ("delete", "third", True),  # the others' jobs still run
        ("left alone since", "leaving"),  # nothing of theirs goes either
        ("delete", "second", True),
        ("restart and sweep since", "leaving", "second"),  # the last to leave restarts it, then every job file goes
        # the three shared claims are recorded as takes, and none of their readings (5 GB of two places together)
        # counts as one alone in the container
        ("peaks since", "peaks", (3, 0)),
        ("sweep",),  # the runner's folders emptied, each kept
        ("anon", 3 * 10**9, 9 * 10**9),  # their jobs gone
        ("claim", "pixal", "pixal", None, {}),  # the Blender claims gone, the waiting Pixal3D claim goes
        ("delete", "pixal", None),
        ("set", card_queue, "BACKFILL_SECONDS", card_queue.BACKFILL_SECONDS),
        # claims of different kinds run side by side, each in its own container, while they fit
        ("mark", "kinds"),
        ("claim", "bakes", "blender", None, {"turns": 3, "id": "score-this-pc:", "slots": [0, 0, 0]}),  # 22.1 GiB,
        ("claim", "route", "characters", ROUTE, {"id": "score-this-pc-characters:"}),  # 25.1 GiB: it fits
        ("card turn copied",),  # side by side, all on the one card
        ("started since", "kinds", ["score-this-pc", "score-this-pc-characters"]),
        ("memory peak", ["bakes"], 3 * 10**9),  # alone in its container: the route's claim is in its own
        ("claim", None, "blender", ALONE, None),  # a Blender job past 27g waits for the shared claim to leave
        ("claim", None, "pixal", None, None),  # unmeasured: the whole memory, so it waits for both
        ("drop", "this-pc pixal", "env-run"),
        ("delete", "route", None), ("delete", "bakes", None),
        # the Blender job past the container runs alone, once the room it needs is free
        ("claim", None, "blender", ALONE, None), ("memory never", "35g"),  # 20 GiB free: it waits
        ("want", "elsewhere"),
        ("claim", None, "blender", None, None),  # its want keeps new Blender claims out meanwhile
        ("room", 33),
        ("claim", "alone", "blender", ALONE, {"turns": 1, "slots": [0]}), ("memory now", "35g"),
        ("claim", None, "blender", None, None),
        ("delete", "alone", None), ("memory now", "27g"),  # back to the shared cap once it leaves
        ("want", "gone"),
        ("claim", "small", "blender", {"memory_gb": 6}, {"turns": 3}), ("delete", "small", None),
        # the run did not ask for containers of their own: one, as before
        ("set", local, "OWN", False),
        ("claim", "bakes", "blender", None, {"id": "score-this-pc:"}),
        ("claim", None, "characters", ROUTE, None),
        ("delete", "bakes", None),
        # sim body's claims measured by the queue: its measured share goes beside the bakes
        ("measures", "this-pc sim-body", [(3.6, 3.12), (2.9, 2.4), (3.2, 2.9), (2.6, 2.1), (3.4, 2.7)]),
        ("claim", "bakes", "blender", None, {}),  # 9.7 GB of card, 22.1 GiB
        ("mark", "body"),
        ("claim", "body", "sim-body", {"memory_gb": 1.86}, {"id": "score-this-pc:", "not": "bakes"}),  # 3.6 GB
        ("uncapped since", "body"),  # its memory_gb is blender_cloud's Blender prediction (2 GB): never 3g
        ("held memory", "this-pc sim-body", [4.4]),  # 3.12 GB x 1.5 = 4.4 GiB
        ("claim", None, "sim-body", None, None),  # a second sim body: 16.9 GB of card does not fit, it waits
        ("drop", "this-pc sim-body", "env-run"),
        ("run cap", 2),  # similar's 0.8 and sim-body's 3.6; the bakes' 9.7 not
        ("delete", "body", None), ("delete", "bakes", None),
        # every container's limits as it is made or found made, its installer caches gone once at its first claim
        # (its layer measured again only after LAYER_EVERY_SECONDS)
        ("containers", {"score-this-pc-characters", "score-this-pc-similar", "score-this-pc", "score-this-pc-pixal"}),
        # the Blender kind's memory: its claims' readings alone in the container, the 5 GB of two together left out
        ("measured", r"(?m)^this-pc blender: \d+ takes, .*, memory 3\.0 GB \([1-9]\d* alone\)$")])]


def this_pc(monkeypatch, tmp_path):
    """This PC's world for its claims: its container 27g (35g with a job alone, `room` GiB free for one), the bakes'
    container's cgroup, the runner's folders a claim's clean-up empties, and every docker call it makes kept in
    `calls` (one container, the characters', made before these limits: it takes them by update)."""
    import capacity
    monkeypatch.setattr(local, "LOCK", tmp_path / "this-pc.lock")
    monkeypatch.setattr(local, "RUNS_AT_ONCE", {"pixal": 1, "blender": 3})
    monkeypatch.setattr(local, "memory_cap", lambda: "27g")
    monkeypatch.setattr(local, "alone_cap", lambda: "35g")
    world = types.SimpleNamespace(calls=[], made={"score-this-pc-characters"}, room=[20 * 2**30],
                                  cgroup=tmp_path / "cgroup", home=tmp_path / "pc", temp=tmp_path / "t")
    monkeypatch.setattr(local, "alone_room", lambda name=None: world.room[0])
    monkeypatch.setattr(local, "answering", lambda name=None: "172.17.0.2")
    monkeypatch.setattr(local.os, "cpu_count", lambda: 24)
    monkeypatch.setattr(capacity.provider, "cloud", local)
    monkeypatch.delenv("SCORE_MAX_MACHINES", raising=False)
    world.cgroup.mkdir()  # the bakes' container's cgroup; the other containers have none here
    (world.cgroup / "memory.stat").write_text(f"anon {3 * 10**9}\nfile {9 * 10**9}\n")  # the page cache is no need
    monkeypatch.setattr(local, "cgroup_of", lambda name=local.MACHINE: world.cgroup if name == local.MACHINE else None)
    monkeypatch.setattr(card_queue, "MEMORY_LOOK_SECONDS", 0.01)
    (world.home / ".props").mkdir(parents=True)
    world.temp.mkdir()
    monkeypatch.setattr(local.pathlib.Path, "home", lambda: world.home)
    monkeypatch.setattr(local, "HOME", world.home / ".props")
    monkeypatch.setattr(local, "REPO", pathlib.Path("/root/repo"))
    monkeypatch.setattr(local.tempfile, "tempdir", str(world.temp))

    def docker(*arguments, **_):
        world.calls.append(arguments)
        if arguments[0] == "run":
            world.made.add(arguments[arguments.index("--name") + 1])
        state = arguments[:3] == ("inspect", "-f", "{{.State.Running}}")
        layer = arguments[:2] == ("inspect", "--size")  # 90 GB, its set-ups' own past LAYER_LIMIT_GB
        return types.SimpleNamespace(returncode=1 if state and arguments[3] not in world.made else 0,
                                     stdout="true" if state else "90000000000" if layer else "", stderr="")
    monkeypatch.setattr(local, "docker", docker)
    world.mark = local.waiting_claims() / str(os.getpid())
    return world


def terminated(commands):
    """The machines these account commands terminated, in order."""
    return [command[3] for command in commands if command[:3] == ("instance", "server", "terminate")]


def started(calls):
    """The containers each claim started (each start sets its cores), in order."""
    return [call[call.index("--name") + 1] if call[0] == "run" else call[-1] for call in calls if "--cpus" in call]


def updates(calls):
    """The memory each update of a container gave it, in order."""
    return [call[call.index("--memory") + 1] for call in calls if call[0] == "update"]


@pytest.mark.parametrize("row, steps", ASKS, ids=[row for row, _ in ASKS])
def test_only_our_own_resources_are_taken_and_every_euro_and_share_they_cost_is_counted(
        row, steps, monkeypatch, card_queue_folder, tmp_path, request):
    import importlib
    import capacity
    import card_turn
    import spread
    held, runs, marks, pc, cloud = {}, {}, {}, None, None
    lock = str(tmp_path / "card.lock")
    call = card_turn.turned(Operator.__call__, lock)
    for number, step in enumerate(steps, 1):
        where = f"{row}, step {number}: {step}"
        kind = step[0]
        if kind == "take":
            _, name, job, card_gb, priority, group, memory, admitted = step
            held.pop(name, None)

            def admit():
                held[name] = held.get(name) or card_queue.take(job, card_gb, priority, group, memory=memory)
                return held[name]
            assert (until(admit) if admitted == "in time" else bool(admit()) == admitted), where
        elif kind == "release":
            card_queue.release(held.pop(step[1]))
        elif kind == "drop":
            card_queue.release(card_queue.WAITING.pop(step[1:]))
        elif kind == "set":
            monkeypatch.setattr(step[1], step[2], step[3])
        elif kind in ("status", "measured"):
            line = getattr(card_queue, kind)()
            assert re.search(step[1], line), (where, line)
        elif kind == "run":
            noted = tmp_path / f"{step[1]}.starts"
            command = f"import os, sys; open({str(noted)!r}, 'a').write(f'{{os.getpid()}}\\n'); sys.stdin.read()"
            runs[step[1]] = subprocess.Popen(
                [sys.executable, card_queue.__file__, "run", "--job", step[1], "--card-gb", str(step[2]), "--",
                 sys.executable, "-c", command],
                stdin=subprocess.PIPE, env={**os.environ, "SCORE_CARD_QUEUE": str(card_queue_folder)})
            request.addfinalizer(runs[step[1]].kill)  # a red run leaves no queue runner behind
            assert until(lambda: noted.exists() and f"held {step[1]}" in card_queue.status()), where
        elif kind == "starts":
            noted = tmp_path / f"{step[1]}.starts"
            assert until(lambda: len(noted.read_text().split()) == step[2]), (where, noted.read_text())
            for pid in noted.read_text().split()[:step[3]]:
                with pytest.raises(ProcessLookupError):
                    os.kill(int(pid), 0)
        elif kind == "end":
            runs[step[1]].stdin.close()
            assert runs[step[1]].wait(30) == 0, where
        elif kind == "operators":
            Operator.on_card[0] = Operator.most[0] = 0
            threads = [threading.Thread(target=call, args=(Operator(name),)) for name in step[1]]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            assert Operator.most[0] == step[2] == card_turn.CARD_SLOTS and call.card_turn, (where, Operator.most[0])
        elif kind == "beside":
            with contextlib.ExitStack() as holding:
                for _ in range(step[1]):
                    holding.enter_context(card_turn.card_turn(lock))
                beside = threading.Thread(target=call, args=(Operator(step[2]),))
                beside.start()
                beside.join(5)
                assert not beside.is_alive(), where
        elif kind == "sized":
            sized = subprocess.run([sys.executable, "-c",
                                    "import card_queue; print(card_queue.BUDGET_GB, card_queue.DESKTOP_GB)"],
                                   cwd=card_queue.__file__.rpartition("/")[0], capture_output=True, text=True,
                                   check=True, env={**os.environ, **step[1]})
            assert sized.stdout.split() == step[2], where
        elif kind == "pc size":
            try:
                with monkeypatch.context() as sized:
                    sized.setattr(local.os, "sysconf",
                                  {"SC_PAGE_SIZE": 4096, "SC_PHYS_PAGES": step[1] * 2**30 // 4096}.get)
                    importlib.reload(local)  # RUNS_AT_ONCE is sized as the module loads
                    assert (local.memory_cap(), local.RUNS_AT_ONCE.get("blender", 1)) == step[2:], where
            finally:
                importlib.reload(local)
                monkeypatch.setattr(local, "OWN", True)
        elif kind == "offers":
            if isinstance(step[2], str):
                with pytest.raises(SystemExit, match=step[2]):
                    local.offers(step[1])
            else:
                offered = local.offers(step[1])
                assert [offer.machine_class for offer in offered] == step[2], where
                assert {(offer.price, offer.stock_word) for offer in offered} == {(0.0, "parked")}, where
        elif kind == "library store":
            monkeypatch.setattr(scaleway, "object_store", lambda: {"bucket": "the-library-bucket"})
            assert local.object_store() == {"bucket": "the-library-bucket"}, where
        elif kind == "pc":
            pc = this_pc(monkeypatch, tmp_path)
        elif kind == "account":
            cloud = scaleway_account(monkeypatch, tmp_path, request)
        elif kind == "listed":
            setattr(cloud, step[1], list(step[2]))
        elif kind == "registry":
            cloud.namespaces = list(step[1] or cloud.namespaces)
            before = len(cloud.commands)
            if step[2] == "public":
                with pytest.raises(SystemExit, match="public"):
                    scaleway.registry()
            else:
                assert scaleway.registry() == {"endpoint": step[2], "username": "nologin", "password": "SK"}, where
            made = [command for command in cloud.commands[before:] if command[:3] == ("registry", "namespace", "create")]
            assert len(made) == step[3], where
            assert all(f"project-id={OURS}" in command and "is-public=false" in command for command in made), where
        elif kind == "runtime key":
            policies = [command for command in cloud.commands if command[:3] == ("iam", "policy", "create")]
            assert len(policies) == 1 and f"rules.0.project-ids.0={OURS}" in policies[0] and \
                "application-id=app" in policies[0], (where, policies)
            assert {argument.split("=", 1)[1] for argument in policies[0] if ".permission-set-names." in argument} == {
                "ObjectStorageFullAccess", "ContainerRegistryFullAccess"}, where
            assert [command for command in cloud.commands if command[:3] == ("iam", "api-key", "create")
                    and f"default-project-id={OURS}" in command], where
            assert [command for command in cloud.commands if command[:3] == ("secret", "secret", "create")
                    and f"project-id={OURS}" in command], where
            assert json.loads(cloud.stored) == {"access_key": "AK2", "secret_key": "SK2"}, where
            assert not any("SK2" in argument for command in cloud.commands for argument in command), where
        elif kind == "month spend":
            assert scaleway.month_spend(OURS) == step[1], where
        elif kind == "bill all":
            if isinstance(step[2], str):
                with pytest.raises(scaleway.Unread, match=step[2]):
                    scaleway.bill_all(**({"last_whole": step[1]} if step[1] else {}))
            else:
                read = scaleway.bill_all()
                assert {key: read[key] for key in step[2]} == step[2], (where, read)
        elif kind == "owners":
            names = {"ff": "farm-factory", "bp": SHARED, "xx": "babon-worker"}
            assert [scaleway.owner_of({"project": project, "tags": tags}, names) for project, tags, _ in step[1]] == [
                owner for _, _, owner in step[1]], where
        elif kind == "quotas":
            if step[1] == "403":
                def pages(organization, key):
                    raise urllib.error.HTTPError("https://api.scaleway.com", 403, "Forbidden", {}, None)
            else:
                def pages(organization, key, listed=step[1]):
                    return listed if (organization, key) == ("org", "key") else []
            monkeypatch.setattr(scaleway, "quota_pages", pages)
            scaleway.zone_quotas.cache_clear()
            assert scaleway.zone_quotas() == step[2], where
        elif kind == "parked":
            parked = tmp_path / "parked"
            parked.mkdir()
            for index, record in enumerate(step[1]):
                (parked / f"{index}.json").write_text(json.dumps({**record, "until": time.time() + record["until"]}))
            (parked / f"{len(step[1])}.json").write_text("{\"type\": ")  # half-written
            monkeypatch.setattr(scaleway, "PARKED", parked)
        elif kind == "cloud offers":
            before = len(cloud.commands)
            found = scaleway.offers(step[1])
            assert step[2] is None or {(offer.machine_class, offer.zone): (offer.stock_word, offer.stock)
                                       for offer in found} == step[2], (where, found)
            assert [command[-1] for command in cloud.commands[before:]
                    if command[:3] == ("instance", "server-type", "list")] == step[3], where
        elif kind == "rent":
            _, number, _, address, refusing, owner, sent, kept = step
            name, since = f"blender-{number}", len(cloud.commands)
            cloud.rent(address, owner)
            cloud.refusals = [(("instance", "ip", refusing), f"scw ip {refusing} failed", lambda: None)] \
                if refusing else []
            offer = types.SimpleNamespace(type="POP2-32C-128G", zone="pl-waw-2", machine_class="cpu-32c-128gb",
                                          price=0.02)
            answer = scaleway.create(OURS, offer, name, [], 60)
            assert answer[0] == (f"srv-{name}" if kept else None) and (answer[1] is None) == kept, where
            assert terminated(cloud.commands[since:]) == ([] if kept else [f"srv-{name}"]), where
            ip = [command for command in cloud.commands[since:]
                  if command[:2] == ("instance", "ip") and command[2] != "list"]
            assert [command[2] for command in ip] == sent, where
            if kept and sent:
                assert f"server=srv-{name}" in ip[0] and f"project-id={OURS}" in ip[0], where
                assert ip[3][3] == f"ip-{name}" and f"tags.0={scaleway.QUARANTINED}" in ip[3], where
        elif kind == "refused but made":
            import ledger
            since = len(cloud.commands)
            cloud.order = cloud.refuse_but_make
            offer = types.SimpleNamespace(type="L4-1-24G", zone="fr-par-1", machine_class="gpu-24gb", price=0.013)
            answer = scaleway.create(OURS, offer, step[1], [], 60)
            assert answer[0] is None and "500" in answer[1], where
            assert terminated(cloud.commands[since:]) == ["srv-made"] and "zone=fr-par-1" in next(
                command for command in cloud.commands[since:] if command[2] == "terminate"), where
            assert sorted(command[3] for command in cloud.commands[since:] if command[2] == "delete") == [
                "disk-new", "ip-new"], where
            lines = ledger_lines()
            assert [line["state"] for line in lines if line["kind"] in (ledger.RENT_STARTED, ledger.RENT_REFUSED)
                    and line["name"] == step[1]] == ["started", "refused"], where  # its started line, then refused
            fees = [line for line in lines if line["kind"] == "disk-and-address" and line["who"] == "scaleway.create"]
            assert len(fees) == 1 and fees[0]["name"] == step[1], where
            assert fees[0]["euros"] == pytest.approx(0.005 + 60 * 0.00013), where  # one address-hour, 60 GB an hour
        elif kind == "hours":
            created = 1791799200.0  # 2026-10-12T10:00:00Z
            server = {"creation_date": made_at(created), "public_ips": [{"id": "ip"}]}
            assert [scaleway.disk_and_address_euros(server, 60, created + minutes * 60) for minutes, _ in step[1]] == [
                pytest.approx(hours * ONE_HOUR) for _, hours in step[1]], where
        elif kind == "cloud delete":
            if isinstance(step[2], str):
                with pytest.raises(RuntimeError, match=step[2]):
                    scaleway.delete(step[1], "pl-waw-2")
            else:
                assert scaleway.delete(step[1], "pl-waw-2") is step[2], where
        elif kind == "fee":
            written = [line["euros"] for line in ledger_lines() if line["batch"] == f"disk-and-address-{step[1]}"]
            assert written == ([] if step[2] is None else [pytest.approx(step[2])]), (where, written)
        elif kind == "refusals":
            cloud.refusals = [(head, words, (lambda gone=gone: cloud.servers.remove(
                cloud.find(cloud.servers, gone, "server"))) if gone else (lambda: None))
                for head, words, gone in step[1]]
        elif kind == "terminate":
            assert scaleway.terminate(step[1], step[2]) is True, where
        elif kind == "delete address":
            scaleway.delete_address(step[1], "pl-waw-2")
        elif kind == "delete disk":
            with pytest.raises(subprocess.CalledProcessError) if step[2] else contextlib.nullcontext():
                scaleway.delete_disk(step[1], "pl-waw-2")
        elif kind == "start if stopped":
            assert step[2] in scaleway.start_if_stopped(step[1], "pl-waw-2"), where
        elif kind == "leftovers":
            assert scaleway.leftover_addresses(OURS, ("pl-waw-2",)) == step[1], where
        elif kind == "runner paths":
            assert local.runner_paths() == [pc.home, pc.temp], where
        elif kind == "claim":
            _, name, claim_kind, need, expected = step
            if isinstance(expected, str):
                with pytest.raises(ValueError, match=expected):
                    local.take(claim_kind, "key", need)
                continue
            claim = local.take(claim_kind, "key", need)
            if expected is None:
                assert claim is None, (where, claim)
                continue
            assert claim, where
            held[name] = claim
            for key, value in expected.items():
                if key == "id":
                    assert claim["id"].startswith(value), (where, claim)
                elif key == "slots":
                    assert spread.slots(claim_kind, claim) == value, (where, claim)
                elif key == "not":
                    assert claim["id"] != held[value]["id"], (where, claim, held[value])
                else:
                    assert claim[key] == value, (where, claim)
        elif kind == "delete":
            answer = local.delete(held[step[1]]["id"] if step[1] in held else step[1], local.ZONE)
            assert step[2] is None or answer is step[2], (where, answer)
        elif kind == "mark":
            marks[step[1]] = len(pc.calls)
            marks[f"{step[1]} peaks"] = card_queue.peaks().get("this-pc blender", {"takes": 0, "memory_takes": 0})
        elif kind == "called":
            assert step[1] in pc.calls, (where, pc.calls)
        elif kind == "last update":
            assert [made for made in pc.calls if made[0] == "update"][-1] == step[1], where
        elif kind == "uncapped since":  # a claim held under the container's 27g
            assert not [made for made in pc.calls[marks[step[1]]:]
                        if made[:2] == ("update", "--memory") and made[2] != "27g"], where
        elif kind == "memory never":
            assert step[1] not in updates(pc.calls), where
        elif kind == "memory now":
            assert updates(pc.calls)[-1] == step[1], (where, updates(pc.calls))
        elif kind == "waiters":
            local.waiting_claims().mkdir(parents=True, exist_ok=True)
            pc.gone, pc.alive = local.waiting_claims() / str(2**22 + 7), local.waiting_claims() / str(os.getppid())
            pc.gone.touch()  # a process that died while it waited (no pid is this high: Linux's pid_max at most 2**22)
            pc.alive.touch()
        elif kind == "waiting":
            assert pc.mark.exists() == step[1], where
        elif kind == "waiters swept":
            assert not pc.gone.exists() and pc.alive.exists(), where
        elif kind == "queued":
            assert local.queued(step[1]) == step[2], where
        elif kind == "lock free":
            with local.container_lock(step[1]).open("a+") as probe:
                assert local.got(probe, True), where
        elif kind == "card read":
            assert until(lambda: local.CARDS[held[step[1]]["id"]].card_peak), where
        elif kind == "memory peak":
            assert until(lambda: all(local.CARDS[held[name]["id"]].memory_peak == step[2] for name in step[1])), where
        elif kind == "work out":
            spread.work_turn(held[step[1]], spread.Shares([]), lambda *_: None, 0, threading.Event())
        elif kind == "let go":
            local.let_go_turn(held[step[1]]["id"])
        elif kind == "ends with":
            for name in step[1]:
                local.ends_with(held[name]["id"], f"rm -rf /job/{held[name]['id']}")
        elif kind == "left alone since":
            assert not [made for made in pc.calls[marks[step[1]]:] if made[0] in ("restart", "exec")], where
        elif kind == "restarted":
            assert [made for made in pc.calls if made[0] == "restart"][-1][-1] == step[1], where
        elif kind == "restart and sweep since":
            sent = f"rm -rf /job/{held[step[2]]['id']}; {local.swept()}"
            assert [made for made in pc.calls[marks[step[1]]:] if made[0] in ("restart", "exec")] == [
                ("restart", "-t", "5", local.MACHINE), ("exec", local.MACHINE, "sh", "-c", sent)], where
        elif kind == "peaks since":
            before, after = marks[f"{step[1]} peaks"], card_queue.peaks()["this-pc blender"]
            assert (after["takes"] - before["takes"], after["memory_takes"] - before["memory_takes"]) == step[2], (
                where, before, after)
        elif kind == "sweep":
            for leftover in (pc.home / ".props/store/take.png", pc.home / "work/out/a.glb",
                             pc.temp / "blender_tmp/x"):
                leftover.parent.mkdir(parents=True, exist_ok=True)
                leftover.write_text("x")
            subprocess.run(["sh", "-c", local.swept()], check=True)
            assert pc.home.is_dir() and not any(pc.home.iterdir()) and not any(pc.temp.iterdir()), where
            (pc.home / ".props").mkdir()
        elif kind == "anon":
            (pc.cgroup / "memory.stat").write_text(f"anon {step[1]}\nfile {step[2]}\n")
        elif kind == "card turn copied":
            assert ("cp", str(local.CARD_TURN), f"{local.MACHINE}:{card_turn.STARTUP}/.card_turn.py.new") in pc.calls
            assert ("exec", local.MACHINE, "mv", f"{card_turn.STARTUP}/.card_turn.py.new",
                    f"{card_turn.STARTUP}/card_turn.py") in pc.calls, where
        elif kind == "started since":
            assert started(pc.calls[marks[step[1]]:]) == step[2], where
        elif kind == "want":
            if step[1] == "elsewhere":  # as another live process's
                (local.wanting() / str(os.getpid())).rename(local.wanting() / str(os.getppid()))
            else:
                (local.wanting() / str(os.getppid())).unlink()
        elif kind == "room":
            pc.room[0] = step[1] * 2**30
        elif kind == "measures":
            with (card_queue.QUEUE / "measures.jsonl").open("a") as measures:
                for card_gb, memory_gb in step[2]:
                    measures.write(json.dumps({"job": step[1], "card_gb": card_gb, "alone": True, "cores": 9.7,
                                               "memory_gb": memory_gb, "memory_alone": True}) + "\n")
        elif kind == "held memory":
            assert [round(share["memory_gb"], 1) for share in card_queue.live("held")
                    if share["job"] == step[1]] == step[2], where
        elif kind == "run cap":
            assert capacity.run_cap() == local.claims_at_once() == step[1], where
        else:  # containers: each made or found made with its limits, its installer caches gone once
            assert {(made[made.index("--memory") + 1], made[made.index("--memory-swap") + 1],
                     made[made.index("--cpus") + 1]) for made in pc.calls if "--cpus" in made} == {("27g", "27g", "20")}
            assert pc.made == step[1], where
            assert [made[1] for made in pc.calls if made[-1] == local.INSTALLER_CACHES] == list(
                dict.fromkeys(started(pc.calls))), where


def until(done, seconds=30):
    """Whether `done()` came true within `seconds`, asked every 50 ms (the subprocess under test works meanwhile)."""
    give_up = time.time() + seconds
    while not done() and time.time() < give_up:
        time.sleep(0.05)
    return done()
