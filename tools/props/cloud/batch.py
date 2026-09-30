"""Make a whole batch of models on rented Scaleway graphics cards, then delete the machines.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/batch.py <list.txt> --who "<session>"
        [--minutes 60] [--per-card N] [--max-cards 20] [--types L4-1-24G,L4-2-24G]
        [--no-finish] [--dry-run]

The list has one model a line, `<name> <picture> [pixal.py options]`, e.g.
`crate ~/pics/crate.png --faces 12000 --feet`; `#` starts a comment. The pictures must be ones the
owner approved.

Only the raw Pixal3D step runs in the cloud (#55). The pictures are cut out here, the cut-outs go up
as they are ready, and as many cards are rented as it takes to finish in about --minutes, across the
zones and machine types that have stock, cheapest per card first. Each machine takes new work only
when it has room, so a slow or late machine never holds up the rest, and one that fails hands its
unfinished jobs back. Every model comes back into WORK/pixal/ as if made here and is finished here
with `pixal.py --finish-only` while the machines are still working.

Before anything is rented, the prices are read from Scaleway and printed, and a batch that would
pass four hours, €60, or the month's €700 is refused (ledger.py). Every machine is deleted whatever
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
import signal
import socket
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import ledger  # noqa: E402
import pixal  # noqa: E402
import scaleway  # noqa: E402
from paths import HOME, IMAGE_TO_3DLAB, REPO, VENV_PYTHON, WORK  # noqa: E402

# How many cards each machine type has. Only L4 cards are measured so far; the rest are named so
# a measuring run can ask for them with --types.
CARDS = {"L4-1-24G": 1, "L4-2-24G": 2, "L40S-1-48G": 1, "H100-1-80G": 1, "H100-SXM-2-80G": 2}
TYPES = ("L4-1-24G", "L4-2-24G")
# Pixal3D runs at once on one card, measured on an L4 (2026-09-29): 3 at once made about 19 models an
# hour at a 10.6 GB peak; 6 made about 20 at 17 to 20 GB and one run died, so the card is already full at 3.
PER_CARD = 3
MAX_CARDS = 20
TARGET_MINUTES = 60
STOCK_ORDER = {"available": 0, "scarce": 1, "shortage": 2}
DISK_GB = 60
CLOUD = HOME / "cloud"
KEY = CLOUD / "ssh_key"
# The key a machine deletes itself with: farm-factory machines, addresses and disks only, never
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
BOOT_MINUTES = 10
# How long after an order the runner asks the machine to start, to learn whether the zone has a card.
START_CHECK_SECONDS = 5
# A booted machine that still refuses the key this long never will (measured 2026-09-29: up and
# answering in about 2 min).
REFUSED_MINUTES = 3
WATCHDOG_GRACE_MINUTES = 5
# The processor's share: two cut-out processes, and two finishes at once (Blender), within FINISH_SLOTS.
CUTTERS = 2
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


def taken(models):
    """The names that already have a raw model here, which a batch would overwrite."""
    return [options.name for options in models if (pixal.OUT / f"{options.name}.glb").exists()]


def card_minutes_per_model():
    """A card's minutes per model in the last measured batch, or the first guess."""
    for entry in reversed(ledger.entries()):
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


def offers(types):
    """Where each machine type can be rented: (euros a card a minute, stock rank, type, zone,
    euros a minute), cheapest per card first, then the best stocked."""
    found = []
    for zone in scaleway.ZONES:
        for machine_type in types:
            stock = scaleway.stock(machine_type, zone)
            if stock is None:
                continue
            price = scaleway.euros_per_minute(machine_type, zone)
            found.append((price / CARDS[machine_type], STOCK_ORDER.get(stock, 3), machine_type,
                          zone, price))
            say(f"{machine_type} in {zone}: {stock}, €{price * 60:.2f} an hour (Scaleway's price list)")
    return sorted(found)


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


def sweep(project):
    """Delete every machine a finished or crashed run left in the project; the count deleted."""
    deleted, running = 0, 0
    for server_id, zone, name, tags in scaleway.ours(project):
        if is_leftover(tags, time.time()):
            say(f"deleting {name} in {zone}, left by an earlier run")
            deleted += scaleway.delete(server_id, zone)
        else:
            say(f"{name} in {zone} belongs to a batch still running; left alone")
            running += 1
    if not running:
        sweep_what_machines_left(project)
    return deleted


def sweep_what_machines_left(project):
    """Delete the addresses and disks a machine that deleted itself left behind. Only while no batch
    is running, so a machine being set up never loses its own."""
    for address_id, zone, address in scaleway.leftover_addresses(project):
        say(f"deleting address {address} ({address_id}) in {zone}, project {project}, left by a machine")
        scaleway.delete_address(address_id, zone)
    for disk_id, zone, name in scaleway.leftover_disks(project):
        say(f"deleting disk {name} ({disk_id}) in {zone}, project {project}, left by a machine")
        scaleway.delete_disk(disk_id, zone)


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
    give_up = time.time() + BOOT_MINUTES * 60
    host, first_refused = None, None
    while time.time() < give_up:
        refused = scaleway.start_if_stopped(server_id, zone)
        if refused:
            say(f"{folder.name} is stopped and would not start yet: {refused}")
        host = host or scaleway.address(server_id, zone)
        if host:
            answer = remote(folder, host, "true", capture_output=True, text=True)
            if answer.returncode == 0:
                return host
            if "Permission denied" in answer.stderr:
                first_refused = first_refused or time.time()
                if time.time() - first_refused > REFUSED_MINUTES * 60:
                    raise PermissionError(f"the machine at {host} refuses the runner's ssh key")
        time.sleep(10)
    raise TimeoutError(f"the machine did not answer within {BOOT_MINUTES} min "
                       f"({'at ' + host if host else 'it never got an address'})")


def arm_self_delete(folder, host, deadline):
    """Start the machine's own watcher, which deletes it if this PC goes quiet (self_delete.py)."""
    remote(folder, host, "mkdir -p /root/batch", check=True)
    copy(folder, [SELF_DELETE_KEY, HERE / "self_delete.py"], f"root@{host}:/root/batch/")
    remote(folder, host, f"chmod 600 /root/batch/{SELF_DELETE_KEY.name}; cd /root/batch; setsid -f "
           f"python3 self_delete.py {deadline:.0f} /root/batch/{SELF_DELETE_KEY.name} {QUIET_MINUTES} "
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
    """One job onto the machine's queue: its cut-out first, then the job that points at it."""
    name = job["name"]
    (folder / "queue").mkdir(exist_ok=True)
    (folder / "queue" / f"{name}.json").write_text(json.dumps(job["arguments"]))
    copy(folder, [job["cut"]], f"root@{host}:/root/batch/in/{name}.png")
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
    """Copy the named finished models and every log into the machine's folder."""
    listing = folder / "wanted.txt"
    listing.write_text("".join(f"{name}.glb\n{name}.json\n" for name in names))
    copy(folder, [f"root@{host}:/root/batch/out/"], folder / "out", f"--files-from={listing}")
    copy(folder, [f"root@{host}:/root/batch/logs"], folder)


# The fleet.

class Fleet:
    """What the machines share: the jobs ready to send, the finishing here, and the stop."""

    def __init__(self, models, folder, per_card, deadline, who, finish):
        self.models = {options.name: options for options in models}
        self.folder = folder
        self.per_card = per_card
        self.deadline = deadline
        self.who = who
        self.finish = finish
        self.lock = threading.Lock()
        self.ready = collections.deque()
        self.cutting = True
        self.stop = threading.Event()
        self.machines = []
        self.done, self.failed, self.finish_failed = [], [], []
        self.retried = set()
        self.finishers = concurrent.futures.ThreadPoolExecutor(FINISHERS)

    def next_job(self):
        """A job whose cut-out is ready, or None."""
        with self.lock:
            return self.ready.popleft() if self.ready else None

    def no_more_work(self):
        with self.lock:
            return not self.cutting and not self.ready

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


def cut(fleet, models):
    """Cut every picture out here, handing each to the machines as soon as it is ready."""
    (fleet.folder / "in").mkdir(parents=True, exist_ok=True)
    by_cut = {str(fleet.folder / "in" / f"{options.name}.png"): options for options in models}
    processes = []
    for share in (models[index::CUTTERS] for index in range(CUTTERS)):
        arguments = [value for options in share
                     for value in (options.picture, str(fleet.folder / "in" / f"{options.name}.png"))]
        if arguments:
            processes.append(subprocess.Popen(
                [str(pixal.LAB_PYTHON), str(HERE / "cut_outs.py"), *arguments], cwd=IMAGE_TO_3DLAB,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True))
    readers = [threading.Thread(target=hand_over, args=(fleet, process, by_cut)) for process in processes]
    for reader in readers:
        reader.start()
    for reader in readers:
        reader.join()
    with fleet.lock:
        fleet.cutting = False
    say(f"{sum(1 for path in by_cut if pathlib.Path(path).exists())} of {len(models)} pictures cut out")


def hand_over(fleet, process, by_cut):
    """Make each cut-out a job for the machines the moment its cutting process reports it."""
    for line in process.stdout:
        options = by_cut[line.strip()]
        job = {"name": options.name, "cut": line.strip(),
               "arguments": pixal.generator_arguments(f"/root/batch/in/{options.name}.png",
                                                      f"/root/batch/out/{options.name}.glb",
                                                      options.seed)}
        with fleet.lock:
            fleet.ready.append(job)
    process.wait()


def rent(fleet, project, offer, number):
    """Rent one machine from `offer` with its watchdog; its record, or None when refused."""
    _, _, machine_type, zone, price = offer
    name = f"{fleet.folder.name}-{number}"
    tags = [f"pid={os.getpid()}", f"host={socket.gethostname()}",
            f"deadline={fleet.deadline + WATCHDOG_GRACE_MINUTES * 60:.0f}"]
    server_id, refused = scaleway.create(project, machine_type, zone, name, tags, DISK_GB)
    if server_id is None:
        say(f"{machine_type} in {zone} refused: {refused.splitlines()[-1] if refused else '?'}")
        return None
    # A zone out of cards still takes the order and leaves the machine stopped; its start then
    # says so. Give that machine back at once, so the fleet moves on to the next zone instead of
    # filling one empty zone with 20 machines that never run (2026-09-29).
    time.sleep(START_CHECK_SECONDS)
    refused = scaleway.start_if_stopped(server_id, zone)
    if refused and "out of stock" in refused.lower():
        scaleway.delete(server_id, zone)
        say(f"{machine_type} in {zone} is out of stock; trying the next zone")
        return None
    folder = fleet.folder / name
    folder.mkdir(parents=True)
    machine = {"id": server_id, "zone": zone, "type": machine_type, "cards": CARDS[machine_type],
               "price": price, "created": time.time(), "folder": folder, "deleted": None,
               "generating_began": None, "status": {}}
    machine["watchdog"] = start_watchdog(server_id, zone,
                                         fleet.deadline + WATCHDOG_GRACE_MINUTES * 60, folder)
    say(f"rented {machine_type} in {zone} ({name})")
    return machine


def rent_fleet(fleet, project, found, cards):
    """Rent machines until `cards` cards are running or no offer has any left; the machines."""
    rented, number, remaining = [], 1, list(found)
    while sum(machine["cards"] for machine in rented) < cards and remaining and not fleet.stop.is_set():
        machine = rent(fleet, project, remaining[0], number)
        if machine is None:
            remaining.pop(0)
            continue
        number += 1
        rented.append(machine)
        with fleet.lock:
            fleet.machines.append(machine)
        threading.Thread(target=tend, args=(fleet, machine), daemon=True).start()
    return rented


def tend(fleet, machine):
    """Run one machine from boot to delete: prepare it, keep its queue topped up, bring its models
    back as they finish, give back what it never finished, and delete it."""
    folder, sent, finished = machine["folder"], {}, set()
    try:
        host = wait_for_machine(folder, machine["id"], machine["zone"])
        arm_self_delete(folder, host, fleet.deadline + WATCHDOG_GRACE_MINUTES * 60)
        prepare(folder, host, fleet.per_card)
        machine["generating_began"] = time.time()
        say(f"{folder.name} ready after {(time.time() - machine['created']) / 60:.1f} min")
        room = machine["cards"] * (fleet.per_card + 1)
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
    """Delete a machine once, and stop its watchdog."""
    if machine["deleted"]:
        return
    scaleway.delete(machine["id"], machine["zone"])
    machine["deleted"] = time.time()
    try:
        os.kill(machine["watchdog"], signal.SIGTERM)
    except ProcessLookupError:
        pass
    say(f"{machine['folder'].name} deleted after {(machine['deleted'] - machine['created']) / 60:.1f} min")


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
    if scaleway.delete(server_id, zone):
        print(f"watchdog deleted {server_id} at the time limit", flush=True)


def stop_on_signals():
    """Turn Ctrl-C, a closed terminal and a kill into an exit, so the machines are deleted."""
    def leave(number, _frame):
        raise SystemExit(f"stopped by signal {number}")
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, leave)


# The record.

def ledger_entry(fleet, models, started):
    """The ledger's record of one batch: each machine's time and cost, and the card minutes."""
    machines, card_minutes = [], 0.0
    for machine in fleet.machines:
        ended = machine["deleted"] or time.time()
        minutes = (ended - machine["created"]) / 60
        if machine["generating_began"]:
            card_minutes += (ended - machine["generating_began"]) / 60 * machine["cards"]
        machines.append({"type": machine["type"], "zone": machine["zone"], "minutes": minutes,
                         "euros": ledger.cost(minutes, machine["price"]),
                         "peak_gb": machine["status"].get("peak_gb")})
    job_seconds = {name: job.get("seconds") for machine in fleet.machines
                   for name, job in machine["status"].get("jobs", {}).items()}
    return {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
            "batch": fleet.folder.name, "per_card": fleet.per_card, "machines": machines,
            "machine_minutes": sum(machine["minutes"] for machine in machines),
            "euros": sum(machine["euros"] for machine in machines), "models": len(models),
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

def plan(models, options, project):
    """Price the batch and check the limits; the offers, cards and deadline minutes."""
    found = offers(options.types.split(","))
    if not found:
        raise SystemExit("none of those machine types is sold in the zones used")
    per_model = card_minutes_per_model()
    cards = min(options.max_cards,
                cards_needed(len(models), options.per_card, options.minutes, per_model))
    minutes = expected_minutes(len(models), cards, options.per_card, per_model)
    dearest = max(offer[0] for offer in found)
    spent = max(scaleway.month_spend(project), ledger.month_total(ledger.this_month(), ledger.entries()))
    say(f"{len(models)} models, {options.per_card} a card, {per_model:.2f} card minutes a model: "
        f"{cards} cards for about {minutes:.0f} min, €{ledger.cost(minutes, dearest) * cards:.2f} "
        f"at most; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * cards, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, cards, ledger.minutes_allowed(dearest * cards, spent)


def run(models, options, project, found, cards, allowed_minutes):
    """Cut, rent, generate, bring back and finish; every machine deleted at the end."""
    started = time.time()
    folder = BATCHES / time.strftime(f"batch-%Y%m%d-%H%M%S-{os.getpid()}")
    folder.mkdir(parents=True)
    fleet = Fleet(models, folder, options.per_card, started + allowed_minutes * 60, options.who,
                  not options.no_finish)
    say(f"every machine deleted by {time.strftime('%H:%M', time.localtime(fleet.deadline))} at the latest")
    try:
        threading.Thread(target=cut, args=(fleet, models), daemon=True).start()
        rented = rent_fleet(fleet, project, found, cards)
        say(f"{sum(machine['cards'] for machine in rented)} of {cards} cards rented")
        while any(not machine["deleted"] for machine in rented):
            time.sleep(5)
    finally:
        fleet.stop.set()
        for machine in fleet.machines:
            delete_machine(machine)
        entry = ledger_entry(fleet, models, started)
        ledger.record(entry)
        report(entry)
        fleet.finishers.shutdown(wait=True)
    missing = sorted(set(fleet.models) - set(fleet.done))
    if missing:
        say(f"not made: {', '.join(missing)} (logs under {folder})")
    if fleet.finish_failed:
        say(f"finishing failed: {', '.join(fleet.finish_failed)} (see {folder / 'finish.log'})")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("list")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--minutes", type=float, default=TARGET_MINUTES, help="aim to finish in this long")
    parser.add_argument("--per-card", type=int, default=PER_CARD)
    parser.add_argument("--max-cards", type=int, default=MAX_CARDS)
    parser.add_argument("--types", default=",".join(TYPES), help="machine types to rent, comma separated")
    parser.add_argument("--no-finish", action="store_true", help="bring back raw models only")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    unknown = set(options.types.split(",")) - set(CARDS)
    if unknown:
        raise SystemExit(f"unknown machine types: {', '.join(sorted(unknown))}")

    models = read_list(options.list)
    if taken(models):
        raise SystemExit(f"raw models already here, pick new names: {', '.join(taken(models))}")
    project = scaleway.project_id()
    sweep(project)
    found, cards, allowed_minutes = plan(models, options, project)
    if options.dry_run:
        return
    scaleway.allow_key(project, "farm-factory-batch", ssh_key())
    stop_on_signals()
    run(models, options, project, found, cards, allowed_minutes)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--watchdog"]:
        watchdog(sys.argv[2], sys.argv[3], float(sys.argv[4]))
    else:
        main()
