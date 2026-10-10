"""Make a whole batch of models on rented cloud graphics cards, then delete the machines.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/batch.py <list.txt> --who "<session>"
        --inventory data/inventory/<scene>.json [data/inventory/<scene>.json ...]
        [--minutes 60] [--per-card N] [--max-cards 20] [--classes gpu-24gb,gpu-80gb]
        [--no-finish] [--dry-run]

The list has one model a line, `<name> <picture> [pixal.py options]`, e.g.
`crate ~/pics/crate.png --faces 12000 --feet`; `#` starts a comment. The pictures must be ones the
owner approved. A batch builds scenes' rows (the scene workflow of 2026-10-04, #121; several scenes
in one batch since modules batch one, 2026-10-07): it is refused without each scene's inventory
approved by the owner (inventory.py) and its place's style text (place.json), and every model's
name is one of their `generate` or `mechanic` rows, by the row's id or its prop kind, alone or after
a prefix (`habitat-locker`) or before a take (`locker-b`).

A character the owner asked for is the one other thing a batch builds: `batch.py --characters
data/characters/makes/<name>.json [...] --who "<session>"` takes no list; each spec must carry
"approved" (who asked, and when) and its "picture", and its model is named after the spec's "name"
(the character maker's animal route, job characters-full, 2026-10-09).

The cut-out and the raw Pixal3D step run in the cloud (#55): no model runs on this PC (owner,
2026-10-03; local_models.py). The pictures go up as they are, each machine cuts its own out with
the same BiRefNet-lite as the lab, and as many cards are rented as it takes to finish in about --minutes, across the
zones and capability classes that hold Pixal3D (capacity.py), best stocked and fastest first, spread over the zones. A
machine that does not answer within START_MINUTES is deleted and another rented from the next offer. Each machine
takes new work only
when it has room, so a slow or late machine never holds up the rest, and one that fails hands its
unfinished jobs back. Every model comes back into WORK/pixal/ as if made here, with the camera
folder its finish paints from (<name>.svviews), and is finished here with `pixal.py --finish-only`
(Blender and the processor, no model) while the machines are still working. This is the way to make
every model, one or a hundred. Under SCORE_CLOUD=k8s the takes go to the Kubernetes cluster as Jobs of the pixal
image instead (run_on_cluster, tools/cloud/k8s/cluster_jobs.py), finished here the same way; the machines stay the
default.

Before anything is rented, the prices are read from the cloud backend (provider.py) and printed, and a batch that would
pass four hours, €60, or the month's ceiling (ledger.MONTH_EUROS) is refused (ledger.py). Every machine is deleted whatever
happens: when its work is done, on an error, on Ctrl-C, by a watchdog process at the time limit if
this one is gone, and by the next run's sweep.
"""
import argparse
import collections
import concurrent.futures
import contextlib
import fcntl
import json
import math
import os
import pathlib
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "scene"))

import capacity  # noqa: E402
import provider  # noqa: E402
import inventory as inventories  # noqa: E402
import ledger  # noqa: E402
import pixal  # noqa: E402
import place  # noqa: E402
from provider import cloud  # noqa: E402
from paths import HOME, REPO, VENV_PYTHON, WORK  # noqa: E402

# Pixal3D runs at once on one card, measured on an L4 (2026-09-29): 3 at once made about 19 models an
# hour at a 10.6 GB peak; 6 made about 20 at 17 to 20 GB and one run died, so the card is already full at 3.
PER_CARD = 3
# Seconds a stopped machine may answer "out of stock" before its offer is given up for the next one.
OUT_OF_STOCK_SECONDS = 60
MAX_CARDS = 20
TARGET_MINUTES = 60
DISK_GB = 60
CLOUD = HOME / "cloud"
KEY = CLOUD / "ssh_key"
# The key a machine deletes itself with: the account's machines, addresses and disks only, never
# creating anything (made 2026-09-29 at the owner's word). It lives here and on the machines, never in the repo.
SELF_DELETE_KEY = CLOUD / "self_delete_key.json"
# A machine that has not heard from this PC for this long deletes itself.
QUIET_MINUTES = 15
BATCHES = WORK / "cloud"
LAB = REPO / "vendor" / "image-to-3dlab"
# Renting, starting and installing took 2.3 min on the first batch (2026-09-29); the margin covers a
# slow download. A card's minutes per model come from the ledger once a batch has run.
SETUP_MINUTES = 5.0
MODEL_MINUTES = 5.0
# How often each machine is looked at, its results brought back and its queue topped up.
POLL_SECONDS = 15
# A machine that has not answered over ssh this long after its order is given back and the next offer tried (24 GB
# cards answered in about 2 min, 2026-09-29; on 2026-10-08 machines in one zone never started at all).
START_MINUTES = 5
# How often a claim or a fleet short of machines asks every class and zone again when none was in stock (owner,
# 2026-10-09: keep retrying every few minutes, never settle for one card).
STOCK_RETRY_MINUTES = 3
# Set when the runner is stopped by a signal: claims still asking in other threads stop, and a machine one of them
# rents after the main thread's last delete is deleted at once (a builder outlived its runner's SIGTERM, 2026-10-09).
STOPPING = threading.Event()
# How long after an order the runner asks the machine to start, to learn whether the zone has a card.
START_CHECK_SECONDS = 5
# A booted machine that still refuses the key this long never will (measured 2026-09-29: up and
# answering in about 2 min).
REFUSED_MINUTES = 3
WATCHDOG_GRACE_MINUTES = 5
# The processor's share: two finishes at once (Blender), within FINISH_SLOTS.
FINISHERS = 2
# How many finishes may run at once on this PC, across every batch: Blender at 100,000 triangles
# takes several GB each; kept at 2 while the PC is unstable (four blue screens, 2026-09-29 and 30).
FINISH_SLOTS = 2


def say(line):
    print(f"[cloud] {time.strftime('%H:%M:%S')} {line}", file=sys.stderr, flush=True)


# The list and the plan.

def read_list(path):
    """The batch's models: name, picture and pixal.py's options for each, checked up front."""
    parser = pixal.options_parser()
    models = []
    for number, line in enumerate(pathlib.Path(path).read_text().splitlines(), 1):
        words = shlex.split(line, comments=True)
        if not words:
            continue
        if len(words) < 2:
            raise SystemExit(f"{path}:{number}: needs a name and a picture")
        name, picture, *flags = words
        options = parser.parse_args([os.path.expanduser(picture), name, "--who", "batch", *flags])
        if not pathlib.Path(options.picture).is_file():
            raise SystemExit(f"{path}:{number}: no picture at {options.picture}")
        models.append(options)
    names = [options.name for options in models]
    if len(set(names)) != len(names):
        raise SystemExit(f"{path}: a name appears twice")
    return models


def from_the_inventory(models, paths):
    """The approved inventories a batch builds from; refused without one, without a place's style
    text, or with a model on none of their rows."""
    kinds = set()
    for path in paths:
        approved = inventories.approved_inventory(path)
        place.style_text(approved["place"])
        kinds |= row_kinds(approved)
    strays = [options.name for options in models if not on_a_row(options.name, kinds)]
    if strays:
        raise SystemExit(f"on no row of {', '.join(map(str, paths))}: {', '.join(strays)}; a batch builds only "
                         "the scenes' rows")
    return kinds


def from_the_characters(paths):
    """The models of character specs (data/characters/makes/<name>.json), one each, named after the spec; refused
    for a spec the owner did not approve or whose picture is missing."""
    parser = pixal.options_parser()
    models = []
    for path in paths:
        spec = json.loads(pathlib.Path(path).read_text())
        if not spec.get("approved"):
            raise SystemExit(f"{path}: not approved; a batch builds only characters the owner asked for")
        picture = os.path.expanduser(spec.get("picture") or "")
        if not pathlib.Path(picture).is_file():
            raise SystemExit(f"{path}: no picture at '{picture}'")
        models.append(parser.parse_args([picture, spec["name"], "--who", "batch", *spec.get("pixal", [])]))
    names = [options.name for options in models]
    if len(set(names)) != len(names):
        raise SystemExit("two character specs share a name")
    return models


def row_kinds(inventory):
    """The names a model may be built under: every generated or mechanic row's id and prop kind."""
    kinds = set()
    for row in inventory["rows"]:
        if row["kind"] in ("generate", "mechanic"):
            kinds.add(row["id"])
            kinds.add(row.get("prop") or row["thing"].split(":", 1)[1])
    return kinds


def on_a_row(name, kinds):
    """Whether a model's name is a row's, alone, after a prefix or before a take's mark."""
    return any(name == kind or name.endswith(f"-{kind}") or name.startswith(f"{kind}-") for kind in kinds)


def taken(models):
    """The names that already have a raw model here, which a batch would overwrite."""
    return [options.name for options in models if (pixal.OUT / f"{options.name}.glb").exists()]


def card_minutes_per_model():
    """A card's minutes per model in the last batch started that measured one, or the first guess.
    By start, not by line: a batch stopped part way is written when it stops, after later ones."""
    for entry in sorted(ledger.entries(), key=lambda entry: entry.get("started", ""), reverse=True):
        if entry.get("models_done"):
            return entry.get("card_minutes", entry.get("generate_minutes")) / entry["models_done"]
    return MODEL_MINUTES


def cards_needed(count, per_card, minutes, per_model):
    """Cards to make `count` models in about `minutes`: after the setup, and after the last
    model's own run, which a card spends `per_model * per_card` minutes on."""
    working = minutes - SETUP_MINUTES - per_model * per_card
    if working <= 0:
        raise SystemExit(f"{minutes} min is too short: setup and one run take about "
                         f"{SETUP_MINUTES + per_model * per_card:.0f}")
    return max(1, math.ceil(count * per_model / working))


def expected_minutes(count, cards, per_card, per_model):
    """How long a batch keeps its machines, on `cards` cards."""
    return SETUP_MINUTES + count * per_model / cards + per_model * per_card


def offers(classes):
    """Where machines of `classes` can be rented right now (the cloud backend's provider.Offer list), each said with
    its stock and price."""
    found = cloud.offers(classes)
    for offer in found:
        say(f"{offer.machine_class} ({offer.type}) in {offer.zone}: {offer.stock_word}, €{offer.price * 60:.2f} an hour "
            f"({cloud.NAME}'s price list)")
    return found


# Leftovers.

def process_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def tag_value(tags, key):
    """The value of a `key=value` tag, or None."""
    for tag in tags:
        if tag.startswith(key + "="):
            return tag.split("=", 1)[1]
    return None


def is_leftover(tags, now):
    """Whether a machine was left by a run that is over: past its deadline, or its process gone."""
    deadline = tag_value(tags, "deadline")
    if deadline is None or float(deadline) < now:
        return True
    pid = tag_value(tags, "pid")
    return tag_value(tags, "host") == socket.gethostname() and not (pid and process_alive(int(pid)))


def sweep(account):
    """Delete every machine a finished or crashed run left in the account; the count deleted."""
    deleted, running = 0, 0
    for server_id, zone, name, tags in cloud.ours(account):
        if is_leftover(tags, time.time()):
            say(f"deleting {name} in {zone}, left by an earlier run")
            deleted += cloud.delete(server_id, zone)
        else:
            say(f"{name} in {zone} belongs to a batch still running; left alone")
            running += 1
    if not running:
        sweep_what_machines_left(account)
    return deleted


def sweep_what_machines_left(account):
    """Delete the addresses and disks a machine that deleted itself left behind. Only while no batch
    is running, so a machine being set up never loses its own."""
    for address_id, zone, address in cloud.leftover_addresses(account):
        say(f"deleting address {address} ({address_id}) in {zone}, account {account}, left by a machine")
        cloud.delete_address(address_id, zone)
    for disk_id, zone, name in cloud.leftover_disks(account):
        say(f"deleting disk {name} ({disk_id}) in {zone}, account {account}, left by a machine")
        cloud.delete_disk(disk_id, zone)


# Talking to a machine.

def ssh_key():
    """The runner's own key pair, made once; the public half."""
    if not KEY.exists():
        CLOUD.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "farm-factory-batch",
                        "-f", str(KEY)], check=True)
    return KEY.with_suffix(".pub").read_text().strip()


def ssh_options(folder):
    return ["-i", str(KEY), "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=accept-new",
            "-o", f"UserKnownHostsFile={folder / 'known_hosts'}", "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=30", "-o", "BatchMode=yes"]


def remote(folder, host, command, **keywords):
    """Run a shell command on the machine as root."""
    return subprocess.run(["ssh", *ssh_options(folder), f"root@{host}", command], **keywords)


def copy(folder, sources, destination, *extra):
    """Copy files or folders with rsync over the runner's ssh."""
    ssh = shlex.join(["ssh", *ssh_options(folder)])
    subprocess.run(["rsync", "-a", "--exclude", ".git", *extra, "-e", ssh, *map(str, sources),
                    str(destination)], check=True, capture_output=True)


def wait_for_machine(folder, server_id, zone):
    """The machine's address once it answers over ssh."""
    give_up = time.time() + START_MINUTES * 60
    host, first_refused, out_of_stock = None, None, None
    while time.time() < give_up:
        refused = cloud.start_if_stopped(server_id, zone)
        if refused:
            say(f"{folder.name} is stopped and would not start yet: {refused}")
            if "out of stock" in refused.lower():
                out_of_stock = out_of_stock or time.time()
                if time.time() - out_of_stock > OUT_OF_STOCK_SECONDS:
                    raise TimeoutError(f"out of stock for {OUT_OF_STOCK_SECONDS} s")
        host = host or cloud.address(server_id, zone)
        if host:
            answer = remote(folder, host, "true", capture_output=True, text=True)
            if answer.returncode == 0:
                return host
            if "Permission denied" in answer.stderr:
                first_refused = first_refused or time.time()
                if time.time() - first_refused > REFUSED_MINUTES * 60:
                    raise PermissionError(f"the machine at {host} refuses the runner's ssh key")
        time.sleep(10)
    raise TimeoutError(f"the machine did not answer within {START_MINUTES} min "
                       f"({'at ' + host if host else 'it never got an address'})")


def boot(machine):
    """Wait for a rented machine to answer; its address, kept on the machine with the time it answered."""
    machine["host"] = wait_for_machine(machine["folder"], machine["id"], machine["zone"])
    machine["ready"] = time.time()
    return machine["host"]


def claim(run, account, offers, number, kind=None, disk_gb=DISK_GB, wanted=None):
    """One machine that answers, for a job of `kind`, with a root disk of `disk_gb`; None only when the run no longer
    wants one. A round that finds no stock anywhere is tried again every STOCK_RETRY_MINUTES with the backend's
    offers read afresh, across every class the offers named and every zone, for as long as `still_wanted` (the run's
    deadline, the month's ceiling and the caller's `wanted`) says: a slot never gives up on its first round (six of
    seven spread slots did on 2026-10-09 and one L4 did all the work)."""
    machine = park_taken(run, offers, number, kind, disk_gb) or claim_round(run, account, offers, number, kind, disk_gb)
    while machine is None and still_wanted(run, account, wanted):
        say(f"no machine of {', '.join(sorted({offer.machine_class for offer in offers}))} in stock; asking again in "
            f"{STOCK_RETRY_MINUTES} min")
        STOPPING.wait(STOCK_RETRY_MINUTES * 60)
        if not still_wanted(run, account, wanted):
            break
        offers = fresh_offers(run, offers)
        machine = claim_round(run, account, offers, number, kind, disk_gb)
    return machine


def park_taken(run, offers, number, kind, disk_gb):
    """A machine of `kind` another run parked within its paid hour (park.py), taken for `run`; None when there is
    none."""
    import park

    return park.adopt(run, offers, number, kind, disk_gb)


def still_wanted(run, account, wanted=None):
    """Whether a claim that found no stock should ask again: the run has a deadline still ahead, the month's ceiling
    is not reached, and the caller still has work for the machine (`wanted()`, when given). A claim with no run (a
    check) asks once."""
    if STOPPING.is_set() or run is None or not getattr(run, "deadline", None) or time.time() >= run.deadline:
        return False
    if wanted is not None and not wanted():
        return False
    return account is None or month_spent(account) < ledger.MONTH_EUROS


def fresh_offers(run, offers):
    """The backend's offers for the same capability classes, read again since stock moves, and the run's dropped
    offers forgotten so each is tried once more."""
    classes = sorted({offer.machine_class for offer in offers})
    found = cloud.offers(classes) or list(offers)
    dropped = getattr(run, "dropped", None)
    if dropped is not None:
        with getattr(run, "choosing", None) or contextlib.nullcontext():
            dropped.difference_update({(offer.type, offer.zone) for offer in found})
    return found


def claim_round(run, account, offers, number, kind=None, disk_gb=DISK_GB):
    """One round of a claim: one machine that answers from `offers`, or None. The kind's late classes
    (capacity.late_for) are taken only after capacity.LATE_MINUTES in which no other offer gave a machine, the others
    asked again each minute meanwhile."""
    late = capacity.late_for(kind)
    first = [offer for offer in offers if offer.machine_class not in late]
    began = time.time()
    machine = claim_from(run, account, first, number, kind, disk_gb)
    while machine is None and len(first) < len(offers) and time.time() - began < capacity.LATE_MINUTES * 60:
        say(f"no {', '.join(sorted({offer.machine_class for offer in first}))} machine yet; asking again in a minute "
            f"before taking {', '.join(late)}")
        time.sleep(60)
        machine = claim_from(run, account, first, number, kind, disk_gb)
    if machine is None and len(first) < len(offers):
        machine = claim_from(run, account, [offer for offer in offers if offer.machine_class in late], number, kind,
                             disk_gb)
    return machine


def claim_from(run, account, offers, number, kind, disk_gb=DISK_GB):
    """One machine that answers, with a root disk of `disk_gb`, from the first of `offers` that gives one; None when
    none does. An offer refused,
    out of stock or whose machine does not answer within START_MINUTES is left for the next, the machine deleted
    and its row kept on `run.attempts` for the ledger. The kind's order and the zone with fewest of the run's
    machines decide the next offer (capacity.next_offer), so machines claimed side by side spread over the zones: the
    offer is chosen under the run's `choosing` lock and counted in its `pending` until the machine is on its list, and
    an offer that gave no machine is in the run's `dropped` for every claim after."""
    remaining = list(offers)
    lock, pending = getattr(run, "choosing", None) or contextlib.nullcontext(), getattr(run, "pending", [])
    dropped = getattr(run, "dropped", set())
    while remaining:
        with lock:
            remaining = [offer for offer in remaining if (offer.type, offer.zone) not in dropped]
            offer = capacity.next_offer(remaining, run.machines + pending, kind)
            if offer is None:
                return None
            reserved = {"zone": offer.zone, "class": offer.machine_class}
            pending.append(reserved)
        remaining.remove(offer)
        machine = None
        try:
            machine = rent(run, account, offer, number, disk_gb)
        finally:
            with lock:
                pending.remove(reserved)
                if machine is None:
                    dropped.add((offer.type, offer.zone))
                else:
                    machine["kind"] = kind
                    run.machines.append(machine)
        if machine is None:
            continue
        if STOPPING.is_set():
            delete_machine(machine)
            return None
        try:
            boot(machine)
            if STOPPING.is_set():
                delete_machine(machine)
                return None
            return machine
        except (TimeoutError, PermissionError) as error:
            say(f"{machine['folder'].name}: {machine['type']} in {machine['zone']} did not start ({error}); "
                "trying the next offer")
            delete_machine(machine)
            run.machines.remove(machine)
            run.attempts.append(ledger.machine_row(machine))
    return None


def arm_self_delete(folder, host, deadline, quiet_minutes=QUIET_MINUTES):
    """Start the machine's own watcher, which deletes it if this PC goes quiet (self_delete.py), in place of any
    watcher it had (a parked machine's, park.py)."""
    remote(folder, host, "mkdir -p /root/batch", check=True)
    copy(folder, [SELF_DELETE_KEY, HERE / "self_delete.py"], f"root@{host}:/root/batch/")
    # The pattern's brackets keep pkill from matching the shell that runs it.
    remote(folder, host, "pkill -f '[s]elf_delete[.]py' || true", check=True)
    remote(folder, host, f"chmod 600 /root/batch/{SELF_DELETE_KEY.name}; cd /root/batch; setsid -f "
           f"python3 self_delete.py {deadline:.0f} /root/batch/{SELF_DELETE_KEY.name} {quiet_minutes:.0f} {cloud.NAME} "
           f"> self_delete.log 2>&1 < /dev/null", check=True)


def heartbeat(folder, host):
    """Tell the machine's watcher this PC is still here."""
    remote(folder, host, "touch /root/batch/heartbeat", check=True)


def prepare(folder, host, per_card):
    """Put the lab and the machine's scripts on it, install Pixal3D and start the worker."""
    remote(folder, host, "mkdir -p /root/batch/in /root/batch/queue", check=True)
    copy(folder, [str(LAB) + "/"], f"root@{host}:/root/lab/")
    copy(folder, [HERE / "machine_setup.sh", HERE / "machine_run.py"], f"root@{host}:/root/batch/")
    with (folder / "setup.log").open("w") as log:
        remote(folder, host, "bash /root/batch/machine_setup.sh", check=True, stdout=log,
               stderr=subprocess.STDOUT)
    # setsid -f detaches the run whole; a trailing & would keep the ssh session open until it ends.
    remote(folder, host, f"cd /root/batch; setsid -f /root/venv/bin/python machine_run.py "
           f"{per_card} > run.log 2>&1 < /dev/null", check=True)


def send(folder, host, job):
    """One job onto the machine's queue: its picture first, then the job that points at it."""
    name = job["name"]
    (folder / "queue").mkdir(exist_ok=True)
    (folder / "queue" / f"{name}.json").write_text(json.dumps(job["arguments"]))
    copy(folder, [job["picture"]], f"root@{host}:/root/batch/in/{name}.png")
    copy(folder, [folder / "queue" / f"{name}.json"], f"root@{host}:/root/batch/queue/")


def machine_status(folder, host):
    """The machine's status file, fetched fresh."""
    for attempt in range(3):
        copy(folder, [f"root@{host}:/root/batch/status.json"], folder)
        try:
            return json.loads((folder / "status.json").read_text())
        except ValueError:
            # A garbled read once cost a working card its whole batch (2026-09-29); read again.
            if attempt == 2:
                raise
            time.sleep(2)


def bring_back(folder, host, names):
    """Copy the named finished models, their camera folders and every log into the machine's folder.
    The camera folder is what the finish here paints from; without it the finish would have to cut
    the picture out again, which is a model, and no model runs on this PC."""
    listing = folder / "wanted.txt"
    listing.write_text("".join(f"{name}.glb\n{name}.json\n{name}.svviews\n" for name in names))
    copy(folder, [f"root@{host}:/root/batch/out/"], folder / "out", "-r", "--ignore-missing-args",
         f"--files-from={listing}")
    copy(folder, [f"root@{host}:/root/batch/logs"], folder)


# The fleet.

class Fleet:
    """What the machines share: the jobs ready to send, the finishing here, and the stop."""

    def __init__(self, models, folder, per_card, deadline, who, finish):
        self.models = {options.name: options for options in models}
        self.account, self.offers, self.attempts = None, [], []
        self.renting = threading.Lock()
        self.folder = folder
        self.per_card = per_card
        self.deadline = deadline
        self.who = who
        self.finish = finish
        self.lock = threading.Lock()
        self.ready = collections.deque()
        self.queueing = True
        self.stop = threading.Event()
        self.machines = []
        self.done, self.failed, self.finish_failed = [], [], []
        self.retried = set()
        self.finishers = concurrent.futures.ThreadPoolExecutor(FINISHERS)

    def next_job(self):
        """A job ready to send, or None."""
        with self.lock:
            return self.ready.popleft() if self.ready else None

    def no_more_work(self):
        with self.lock:
            return not self.queueing and not self.ready

    def give_back(self, jobs):
        """Jobs a machine took but never finished, for the others."""
        with self.lock:
            self.ready.extend(jobs)

    def retry_once(self, job):
        """A failed job goes back for another try, once; True if it went back."""
        with self.lock:
            if job["name"] in self.retried:
                self.failed.append(job["name"])
                return False
            self.retried.add(job["name"])
            self.ready.append(job)
            return True

    def arrived(self, machine_folder, name):
        """A raw model is here: move it where pixal.py looks, and finish it while others work."""
        pixal.OUT.mkdir(parents=True, exist_ok=True)
        for made in (machine_folder / "out").glob(f"{name}.*"):
            if made.is_dir():
                shutil.rmtree(pixal.OUT / made.name, ignore_errors=True)
            made.replace(pixal.OUT / made.name)
        with self.lock:
            self.done.append(name)
        if self.finish:
            self.finishers.submit(self.finish_here, name)

    def finish_here(self, name):
        """Finish one model with pixal.py --finish-only, as a local run would."""
        options = self.models[name]
        flags = [f"--faces={options.faces}", f"--seed={options.seed}"]
        flags += [f"--{flag}" for flag in ("long", "feet", "tube") if getattr(options, flag)]
        with finish_slot(), (self.folder / "finish.log").open("a") as log:
            done = subprocess.run([str(VENV_PYTHON), str(HERE.parent / "pixal.py"), options.picture,
                                   name, "--who", self.who, "--finish-only", *flags],
                                  stdout=log, stderr=subprocess.STDOUT)
        if done.returncode:
            with self.lock:
                self.finish_failed.append(name)


@contextlib.contextmanager
def finish_slot():
    """Hold one of the PC's FINISH_SLOTS for a finish, shared by every batch running on this PC.

    Each batch finishes several models at once in Blender; two batches side by side ran twelve
    finishes at 100,000 triangles and the PC went down twice (2026-09-29 and 30). The slots are
    lock files, so the limit holds across processes and frees itself if one dies.
    """
    CLOUD.mkdir(parents=True, exist_ok=True)
    while True:
        for number in range(FINISH_SLOTS):
            handle = (CLOUD / f"finish-slot-{number}.lock").open("w")
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close()
                continue
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
                handle.close()
            return
        time.sleep(5)


def queue(fleet, models):
    """Make every picture a job for the machines; each machine cuts its pictures out itself."""
    for options in models:
        job = {"name": options.name, "picture": options.picture,
               "arguments": pixal.generator_arguments(f"/root/batch/in/{options.name}.png",
                                                      f"/root/batch/out/{options.name}.glb",
                                                      options.seed)}
        with fleet.lock:
            fleet.ready.append(job)
    with fleet.lock:
        fleet.queueing = False


def rent(fleet, account, offer, number, disk_gb=DISK_GB):
    """Rent one machine from `offer` with its watchdog and a root disk of `disk_gb`; its record, or None when
    refused."""
    machine_type, zone = offer.type, offer.zone
    spent = month_spent(account)
    if spent >= ledger.MONTH_EUROS:
        say(f"€{spent:.2f} spent this month, at the €{ledger.MONTH_EUROS:.0f} ceiling: nothing more is rented")
        return None
    name = f"{fleet.folder.name}-{number}"
    tags = run_tags(os.getpid(), fleet.deadline + WATCHDOG_GRACE_MINUTES * 60)
    server_id, refused = cloud.create(account, offer, name, tags, disk_gb)
    if server_id is None:
        why = refused.splitlines()[-1] if refused else "?"
        say(f"{machine_type} in {zone} refused: {why}")
        fleet.attempts.append(refused_row(offer, why))
        return None
    # A zone out of cards still takes the order and leaves the machine stopped; its start then
    # says so. Give that machine back at once, so the fleet moves on to the next zone instead of
    # filling one empty zone with 20 machines that never run (2026-09-29).
    time.sleep(START_CHECK_SECONDS)
    refused = cloud.start_if_stopped(server_id, zone)
    if refused and "out of stock" in refused.lower():
        cloud.delete(server_id, zone)
        say(f"{machine_type} in {zone} is out of stock; trying the next offer")
        fleet.attempts.append(refused_row(offer, "out of stock"))
        return None
    folder = fleet.folder / name
    folder.mkdir(parents=True, exist_ok=True)  # a claim retried under the same number after a machine that never started
    machine = {"id": server_id, "zone": zone, "type": machine_type, "class": offer.machine_class,
               "cards": provider.cards(offer.machine_class), "price": offer.price,
               "unit_minutes": cloud.price(machine_type, zone)[1], "created": time.time(), "disk_gb": disk_gb,
               "folder": folder, "deleted": None, "ready": None, "generating_began": None, "status": {}}
    machine["watchdog"] = start_watchdog(server_id, zone,
                                         fleet.deadline + WATCHDOG_GRACE_MINUTES * 60, folder)
    say(f"rented {machine_type} in {zone} ({name})")
    return machine


def run_tags(pid, deadline):
    """The tags that say which process on which PC holds a machine, and when it must be gone (is_leftover)."""
    return [f"pid={pid}", f"host={socket.gethostname()}", f"deadline={deadline:.0f}"]


def priced(found, minutes, count, what, account):
    """Say what `count` machines of the dearest of `found` cost for about `minutes` (`what` names the work and the
    machines) and refuse what passes the owner's limits; the minutes the machines may run."""
    dearest = max(offer.per_card for offer in found)
    spent = month_spent(account)
    say(f"{what}: about {minutes:.0f} min, €{ledger.cost(minutes, dearest) * count:.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * count, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return ledger.minutes_allowed(dearest * count, spent)


def month_spent(account):
    """What the month has cost so far: the provider's bill or the ledger's sum, whichever is higher (the bill lags)."""
    return max(cloud.month_spend(account), ledger.month_total(ledger.this_month(), ledger.entries()))


def refused_row(offer, why):
    """The ledger's row for an offer that gave no machine: nothing ran and nothing was billed."""
    return {"type": offer.type, "class": offer.machine_class, "zone": offer.zone,
            "cards": provider.cards(offer.machine_class), "started": False, "why": why, "minutes": 0.0, "euros": 0.0}


def rent_fleet(fleet, cards):
    """Rent machines until `cards` more cards are running or no offer has any left, each from
    capacity.next_offer (best stocked and fastest first, spread over the zones); an offer that gives no machine is
    dropped."""
    with fleet.renting:
        added = 0
        while added < cards and fleet.offers and not fleet.stop.is_set():
            offer = capacity.next_offer(fleet.offers, fleet.machines, "pixal")
            if offer is None:  # every class at its cap (capacity.max_machines, run_cap)
                break
            machine = rent(fleet, fleet.account, offer, len(fleet.machines) + 1)
            if machine is None:
                fleet.offers.remove(offer)
                continue
            added += machine["cards"]
            with fleet.lock:
                fleet.machines.append(machine)
            threading.Thread(target=tend, args=(fleet, machine), daemon=True).start()
        return added


def keep_the_fleet(fleet, found, cards):
    """Wait while the fleet works, and while it runs fewer than `cards` cards with work left, ask the backend again
    every STOCK_RETRY_MINUTES for the machine types of `found` (the affordable ones) in every zone and rent what has
    come into stock; returns when the work is done and every machine is deleted, or at the deadline."""
    types = {offer.type for offer in found}
    asked = time.time()
    while not fleet.stop.is_set() and time.time() < fleet.deadline:
        alive = [machine for machine in list(fleet.machines) if not machine["deleted"]]
        if not alive and fleet.no_more_work():
            return
        short = cards - sum(machine["cards"] for machine in alive)
        if short > 0 and not fleet.no_more_work() and time.time() - asked >= STOCK_RETRY_MINUTES * 60:
            asked = time.time()
            with fleet.renting:
                fleet.offers = [offer for offer in fresh_offers(None, found) if offer.type in types]
            added = rent_fleet(fleet, short)
            say(f"{short} card{'s' if short != 1 else ''} short; {added} more rented as stock came up")
        time.sleep(5)


def replace(fleet, machine):
    """Rent another machine for one that never answered, from any offer but its type in its zone."""
    with fleet.renting:
        fleet.offers = [offer for offer in fleet.offers if (offer.type, offer.zone) != (machine["type"], machine["zone"])]
    if fleet.no_more_work() or fleet.stop.is_set():
        return
    added = rent_fleet(fleet, machine["cards"])
    say(f"{machine['folder'].name} did not start; {added} card{'s' if added != 1 else ''} rented in its place")


def tend(fleet, machine):
    """Run one machine from boot to delete: prepare it, keep its queue topped up, bring its models
    back as they finish, give back what it never finished, and delete it."""
    folder, sent, finished = machine["folder"], {}, set()
    try:
        try:
            host = boot(machine)
        except (TimeoutError, PermissionError) as error:
            say(f"{folder.name}: {machine['type']} in {machine['zone']} did not start ({error})")
            replace(fleet, machine)
            return
        arm_self_delete(folder, host, fleet.deadline + WATCHDOG_GRACE_MINUTES * 60)
        machine["per_card"] = fleet.per_card or capacity.runs_at_once("pixal", machine["class"])
        prepare(folder, host, machine["per_card"])
        machine["generating_began"] = time.time()
        say(f"{folder.name} ready after {(time.time() - machine['created']) / 60:.1f} min, "
            f"{machine['per_card']} runs a card")
        room = machine["cards"] * (machine["per_card"] + 1)
        closed = False
        while not fleet.stop.is_set() and time.time() < fleet.deadline:
            while len(sent) - len(finished) < room:
                job = fleet.next_job()
                if job is None:
                    break
                sent[job["name"]] = job
                send(folder, host, job)
            if not closed and fleet.no_more_work():
                remote(folder, host, "touch /root/batch/closed", check=True)
                closed = True
            heartbeat(folder, host)
            status = machine_status(folder, host)
            machine["status"] = status
            finished |= collect(fleet, folder, host, status, finished, sent)
            if status["finished"]:
                break
            time.sleep(POLL_SECONDS)
    except Exception as error:  # noqa: BLE001 - one machine failing must not stop the fleet
        say(f"{folder.name} failed: {error}")
    finally:
        fleet.give_back([job for name, job in sent.items() if name not in finished])
        delete_machine(machine)


def collect(fleet, folder, host, status, finished, sent):
    """Bring back the models the machine finished since the last look, and send each failed one
    back for one more try (a run can die when the card runs short of memory); the names now over."""
    over = {name for name, job in status["jobs"].items() if job["state"] in ("done", "failed")}
    new = over - finished
    made = sorted(name for name in new if status["jobs"][name]["state"] == "done")
    if made:
        bring_back(folder, host, made)
    for name in made:
        fleet.arrived(folder, name)
    for name in sorted(new - set(made)):
        if fleet.retry_once(sent[name]):
            say(f"{name} failed on {folder.name}; trying it once more")
    return new


def delete_machine(machine):
    """Delete a machine once, or park it for the next run of its kind when its paid hour has time left (park.py),
    and stop its watchdog."""
    import park

    if machine["deleted"]:
        return
    parked = park.park(machine)
    if not parked:
        cloud.delete(machine["id"], machine["zone"])
    machine["deleted"] = time.time()
    with contextlib.suppress(ProcessLookupError):
        os.kill(machine["watchdog"], signal.SIGTERM)
    say(f"{machine['folder'].name} {'parked' if parked else 'deleted'} after "
        f"{(machine['deleted'] - (machine.get('adopted') or machine['created'])) / 60:.1f} min")


def start_watchdog(server_id, zone, deadline, folder):
    """A separate process that deletes the machine at `deadline` if it still exists; its pid."""
    with (folder / "watchdog.log").open("w") as log:
        watchdog = subprocess.Popen([sys.executable, __file__, "--watchdog", server_id, zone,
                                     str(deadline)],
                                    start_new_session=True, stdout=log, stderr=subprocess.STDOUT)
    return watchdog.pid


def watchdog(server_id, zone, deadline):
    """Sleep until the deadline, then delete the machine if the runner has not."""
    time.sleep(max(0.0, deadline - time.time()))
    if cloud.delete(server_id, zone):
        print(f"watchdog deleted {server_id} at the time limit", flush=True)


def stop_on_signals():
    """Turn Ctrl-C, a closed terminal and a kill into an exit, so the machines are deleted."""
    def leave(number, _frame):
        STOPPING.set()
        raise SystemExit(f"stopped by signal {number}")
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, leave)


# The record.

def ledger_entry(fleet, models, started):
    """The ledger's record of one batch: each machine's time, cost and seconds a model, and the card minutes."""
    card_minutes = 0.0
    for machine in fleet.machines:
        ended = machine["deleted"] or time.time()
        if machine["generating_began"]:
            card_minutes += (ended - machine["generating_began"]) / 60 * machine["cards"]
        jobs = machine["status"].get("jobs", {}).values()
        machine["peak_gb"] = machine["status"].get("peak_gb")
        machine["unit_seconds"] = [job["seconds"] for job in jobs if job.get("state") == "done" and job.get("seconds")]
    job_seconds = {name: job.get("seconds") for machine in fleet.machines
                   for name, job in machine["status"].get("jobs", {}).items()}
    return {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
            "batch": fleet.folder.name, "kind": "pixal",
            "per_card": {machine["folder"].name: machine.get("per_card") for machine in fleet.machines},
            **ledger.machines_record(fleet.machines, fleet.attempts, started), "models": len(models),
            "models_done": len(fleet.done), "card_minutes": card_minutes,
            "wall_minutes": (time.time() - started) / 60, "job_seconds": job_seconds}


def report(entry):
    """The batch's speed and cost, the numbers #55 records against the owner's card."""
    done = entry["models_done"]
    say(f"{done} of {entry['models']} models in {entry['wall_minutes']:.0f} min on "
        f"{len(entry['machines'])} machines, {entry['machine_minutes']:.0f} machine minutes, "
        f"€{entry['euros']:.2f}")
    if done and entry["card_minutes"]:
        say(f"{done / (entry['card_minutes'] / 60):.1f} models an hour a card, "
            f"€{entry['euros'] / done:.3f} a model with setup")


# The run.

def affordable(found, minutes, cards, spent):
    """The offers a batch may take: the limits are checked as if every card were the dearest offered, so the
    dearest types are left out, one price at a time, while that alone breaks a limit the cheaper ones keep."""
    cheapest = min(offer.per_card for offer in found)
    while (ledger.refusal(minutes, max(offer.per_card for offer in found) * cards, spent)
           and not ledger.refusal(minutes, cheapest * cards, spent)):
        dearest = max(offer.per_card for offer in found)
        say(f"leaving out {', '.join(sorted({offer.type for offer in found if offer.per_card == dearest}))}: "
            f"{cards} of them would pass the limits")
        found = [offer for offer in found if offer.per_card < dearest]
    return found


def plan(models, options, account):
    """Price the batch and check the limits; the offers, cards and deadline minutes."""
    found = offers(options.classes.split(","))
    if not found:
        raise SystemExit(f"none of those capability classes is sold by the {cloud.NAME} backend")
    per_model = card_minutes_per_model()
    cards = min(options.max_cards,
                cards_needed(len(models), options.per_card or PER_CARD, options.minutes, per_model))
    minutes = expected_minutes(len(models), cards, options.per_card or PER_CARD, per_model)
    spent = month_spent(account)
    found = affordable(found, minutes, cards, spent)
    dearest = max(offer[0] for offer in found)
    say(f"{len(models)} models, {options.per_card or 'as many as fit'} a card, "
        f"{per_model:.2f} card minutes a model: "
        f"{cards} cards for about {minutes:.0f} min, €{ledger.cost(minutes, dearest) * cards:.2f} "
        f"at most; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * cards, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, cards, ledger.minutes_allowed(dearest * cards, spent)


def run(models, options, account, found, cards, allowed_minutes):
    """Rent, cut out and generate, bring back and finish; every machine deleted at the end."""
    started = time.time()
    folder = BATCHES / time.strftime(f"batch-%Y%m%d-%H%M%S-{os.getpid()}")
    folder.mkdir(parents=True)
    fleet = Fleet(models, folder, options.per_card, started + allowed_minutes * 60, options.who,
                  not options.no_finish)
    say(f"every machine deleted by {time.strftime('%H:%M', time.localtime(fleet.deadline))} at the latest")
    try:
        queue(fleet, models)
        fleet.account, fleet.offers = account, list(found)
        say(f"{rent_fleet(fleet, cards)} of {cards} cards rented")
        keep_the_fleet(fleet, found, cards)
    finally:
        fleet.stop.set()
        for machine in fleet.machines:
            delete_machine(machine)
        entry = ledger_entry(fleet, models, started)
        ledger.record(entry)
        report(entry)
        fleet.finishers.shutdown(wait=True)
    say_what_failed(fleet, folder)


def say_what_failed(fleet, folder):
    """Name the models a batch did not make or could not finish, and where their logs are."""
    missing = sorted(set(fleet.models) - set(fleet.done))
    if missing:
        say(f"not made: {', '.join(missing)} (logs under {folder})")
    if fleet.finish_failed:
        say(f"finishing failed: {', '.join(fleet.finish_failed)} (see {folder / 'finish.log'})")


# The Kubernetes path (SCORE_CLOUD=k8s): the takes as Kubernetes Jobs of the pixal image (tools/cloud/images/pixal/:
# its pixal-run wrapper runs the lab's generator from the job's code bundle, the weights from the node cache), through
# tools/cloud/k8s/cluster_jobs.py. A pod has its card to itself, so one job holds as many takes as a 24 GB card runs
# at once (capacity.runs_at_once), started SPACING_SECONDS apart as machine_run.py starts them; the finishing stays
# here, as today.
CLUSTER_MODELS = ["pixal3d", "trellis2-birefnet", "birefnet-general-lite"]
CLUSTER_CODE = ["vendor/image-to-3dlab"]
CLUSTER_SPACING_SECONDS = 30
CLUSTER_TAKE_MINUTES = 30


def cluster_line(group):
    """The shell line of one cluster job: each take of `group` through pixal-run, side by side, its log in the
    output; it fails only when none made its model, so a take that failed is "not made" as on a machine."""
    starts = []
    for turn, options in enumerate(group):
        arguments = pixal.generator_arguments(f"/work/in/{options.name}.png", f"/work/out/{options.name}.glb",
                                              options.seed)
        starts.append(f"(sleep {turn * CLUSTER_SPACING_SECONDS}; pixal-run {shlex.join(arguments)} "
                      f"> /work/out/{options.name}.log 2>&1) &")
    made = " || ".join(f"test -f /work/out/{options.name}.glb" for options in group)
    return f"mkdir -p /work/out && {' '.join(starts)} wait; {made}"


def cluster_job(group, out):
    """One group of takes as a cluster job: its pictures up, the whole output folder back to `out`."""
    return {"command": ["bash", "-c", cluster_line(group)], "code": CLUSTER_CODE, "models": CLUSTER_MODELS,
            "inputs": [{"local": str(pathlib.Path(options.picture).expanduser().resolve()),
                        "path": f"/work/in/{options.name}.png"} for options in group],
            "outputs": [{"path": "/work/out", "local": str(out)}], "minutes": CLUSTER_TAKE_MINUTES * len(group)}


def groups_of(models, size):
    return [models[start:start + size] for start in range(0, len(models), size)]


def run_on_cluster(models, options, parallel=None):
    """The batch on the cluster: the takes in groups, each group's models moved into WORK/pixal and finished here as
    it arrives (Fleet.arrived), as the machines' batch does."""
    sys.path.insert(0, str(REPO / "tools/cloud/k8s"))
    import cluster_jobs

    size = options.per_card or capacity.runs_at_once("pixal", "gpu-24gb")
    folder = BATCHES / time.strftime(f"batch-k8s-%Y%m%d-%H%M%S-{os.getpid()}")
    folder.mkdir(parents=True)
    groups = groups_of(models, size)
    work = [cluster_job(group, folder / f"group{number}" / "out") for number, group in enumerate(groups)]
    fleet = Fleet(models, folder, size, time.time(), options.who, not options.no_finish)
    try:
        cluster_jobs.run("pixal", work, options.who, options.classes.split(","), parallel=parallel)
        for number, group in enumerate(groups):
            for take in group:
                if (folder / f"group{number}" / "out" / f"{take.name}.glb").exists():
                    fleet.arrived(folder / f"group{number}", take.name)
    finally:
        fleet.finishers.shutdown(wait=True)
    say_what_failed(fleet, folder)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("list", nargs="?", help="the models, one a line (not with --characters)")
    parser.add_argument("--who", required=True, help="the session asking")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--inventory", type=pathlib.Path, nargs="+",
                        help="the scenes' approved inventories, data/inventory/<scene>.json")
    source.add_argument("--characters", type=pathlib.Path, nargs="+",
                        help="approved character specs, data/characters/makes/<name>.json, in place of a list")
    parser.add_argument("--minutes", type=float, default=TARGET_MINUTES, help="aim to finish in this long")
    parser.add_argument("--per-card", type=int, help="runs at once on a card (default: as many as its memory "
                        "holds, capacity.runs_at_once)")
    parser.add_argument("--max-cards", type=int, default=MAX_CARDS)
    parser.add_argument("--classes", default=",".join(capacity.classes_for("pixal")),
                        help="capability classes to rent, comma separated (default: every class that holds Pixal3D)")
    parser.add_argument("--no-finish", action="store_true", help="bring back raw models only")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    unknown = set(options.classes.split(",")) - set(cloud.CLASSES)
    if unknown:
        raise SystemExit(f"the {cloud.NAME} backend gives no machine of: {', '.join(sorted(unknown))}")

    if bool(options.characters) == bool(options.list):
        raise SystemExit("give a list with --inventory, or --characters with no list")
    if options.characters:
        models = from_the_characters(options.characters)
    else:
        models = read_list(options.list)
        from_the_inventory(models, options.inventory)
    if taken(models):
        raise SystemExit(f"raw models already here, pick new names: {', '.join(taken(models))}")
    if provider.on_cluster():
        if not options.dry_run:
            run_on_cluster(models, options)
        return
    account = cloud.account()
    sweep(account)
    found, cards, allowed_minutes = plan(models, options, account)
    if options.dry_run:
        return
    cloud.allow_key(account, "farm-factory-batch", ssh_key())
    stop_on_signals()
    run(models, options, account, found, cards, allowed_minutes)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--watchdog"]:
        watchdog(sys.argv[2], sys.argv[3], float(sys.argv[4]))
    else:
        main()
