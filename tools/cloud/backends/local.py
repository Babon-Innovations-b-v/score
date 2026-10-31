"""This PC as the one machine the runners use (SCORE_CLOUD=local; the owner, 2026-10-27: "couldnt u just finish the
rest of env1 on this gpu aswell", then "yes"): its card, never rented, never billed.

The machine is a Docker container on this PC per kind (container: MACHINE for the FIRST kinds, Blender and the
library bakes, whose set-up it holds; MACHINE-<kind> for every other; PRD #73), each made from IMAGE (Ubuntu 24.04
with NVIDIA's CUDA base, as the rented card machines run, plus sshd) with no commit of another, so the image's id in
every kept job's content stays: the runners reach it as root over ssh and rsync with the runner's key, at the same
absolute paths, exactly as a rented machine, so no runner changes. A kind's set-up stays in its container from one
job to the next (park.own_set_up: its own /root/venv, its marks never removed there), so a kind sets up once; a kind
moved out of MACHINE sets up once in its own. The card comes in through WSL's /dev/dxg and /usr/lib/wsl (on plain
Linux through `--gpus all`); each container's memory and cores are held under this PC's own (memory_cap, cpu_arguments)
so a job that runs out of memory fails alone and never takes WSL down.

Claims of different kinds run side by side, each in its container, while their shares of this PC's one card queue
(card_queue.py: card GB from CARD_NEED or the run's measured need, memory GiB from memory_need; an unmeasured need
holds the whole) fit together; a claim holds the PC's LOCK shared and its container's lock (container_lock), one claim
a container at a time but for the SHARED kinds. A claim that finds either busy, or the queue without room for it, gets
None and its runner waits and asks again (batch.claim_rounds polls park.adopt); a claim the queue refused waits in
it, first come first served, so a stream of claims never starves an earlier one, and a card user outside the
containers (sim body tuning, a proof container) never passes the card beside them. A SHARED kind's jobs (Blender:
every input and output at its own absolute path, nothing of one claim's in another's way) share its container across
claims: such a claim holds its container's lock shared and takes free ones of RUNS_AT_ONCE's turns (a lock file each,
one Blender job a turn) as many as the queue's free memory holds (free_memory_turns), each turn let go as its slot
runs out of work (spread.tend, its share's memory with it), so the container runs up to RUNS_AT_ONCE's Blender jobs at
once over all the places' bake rows, never one row at a time (env1, 2026-10-28: 26 bake rows waited on the claim of
one place). An exclusive claim waiting for a lock (its want beside the lock) keeps new shared claims of it out until
it has its turn; set-ups (`setting_up`) run one at a time over the PC. Each of the jobs' card calls (the Cycles bake,
a render) waits its turn on the card (card_turn.py, put into the claim's container's Blender startup folder at every
claim), so the card never works for more than card_turn.CARD_SLOTS (two) Blender jobs at once. Its offers are
always `parked`, so batch.rent never orders anything: the machine is only ever taken through park.adopt
(park.here), which asks no clearance, since it costs nothing (price 0; the ledger's rows carry the measured minutes
at EUR 0). A job that needs more card or memory than this PC has is refused at its claim with the reason, never run
to an out-of-memory; it stays a cloud job. The need is the job's own measure when its run gives one (a characters
run whose steps are all measured: characters.card_need), else its kind's (TOO_BIG). A job predicted past its
container's memory runs alone (the PC's LOCK exclusive). `delete` restarts the claim's container, which ends whatever
a job left running on the card (a detached worker), and keeps its files: only when no other claim holds it, so the
last shared claim to leave restarts it and none restarts it under another claim's jobs.

The interface is provider.py's; what has no meaning here (accounts, addresses, disks, the registry and the object
store) says so or gives nothing.
"""
import contextlib
import fcntl
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import uuid

import math

import card_queue
import provider
from paths import HOME

NAME = "local"
MACHINE = "score-this-pc"  # the container's name, and the machine type the offers name
ZONE = "this-pc"
IMAGE = "score-this-pc:1"
# Memory the container never gets: 8 GB WSL keeps free, 8 GB for the run's processor steps beside the container
# (score run --jobs; owner, 2026-10-27: a WSL out of memory is the worst outcome, the sum stays under RAM less 8 GB).
HOST_RESERVE_GB = 16
# A job predicted past the container's memory (memory_cap) runs alone, its claim exclusive (alone): the container is
# raised to this PC's memory less HOST_FLOOR_GB (WSL's own) and less what its RAM drives hold (alone_cap), and only
# while that room is free now (alone_room); the run's steps beside it stay with the runner's reserve (score/graph
# memory_room, which counts the container's raised room). 2026-10-30: base's light passes, predicted 29.8 GB, were
# refused by the 27 GiB cap on a 43 GiB PC.
HOST_FLOOR_GB = 8
CARD_GB = 16  # the RTX 5080 (the desktop holds part of it while Windows runs)
CARD_CLASS = f"gpu-{CARD_GB}gb"
# The kinds that need more card than CARD_GB, in GB (tools/cloud/capacity.py KINDS' notes): cloud-only unless a run
# gives its own smaller measured need (characters: 17 is Kimodo with its text encoder on the card, the whole machine).
TOO_BIG = {"judge": 30, "pictures-20b": 58, "characters": 17, "meshparts": 24, "moss-sound": 15.6}
# Classes this PC answers for: a single card of at most 24 GB (the jobs that ask one fit on 16 GB unless TOO_BIG says
# otherwise) and every processor class (24 cores here; a job takes longer, never fails for it).
SERVES = (provider.GPU, provider.CPU)
CLASSES = {}  # nothing is ever ordered (offers are `parked`); the classes served are SERVES'
QUOTAS = {CARD_CLASS: 1}  # one machine; capacity.caps needs one entry
LOCK = HOME / "cloud" / "this-pc.lock"
CARD_TURN = pathlib.Path(__file__).resolve().parent / "card_turn.py"
# Blender jobs at once (RUNS_AT_ONCE): a take's paint and bake peak, measured (env1, 2026-10-28; one take,
# garage_vehicle_lift, once held 27), and what the container holds beside the peaks (sshd, rsync, idle Blenders).
# The p90 of the last 50 paint and bake takes (memory/container-peaks.json, 2026-10-29: 6.62 GB, the highest 9.2),
# so four run in the 27 GiB container where three left about 2.9 of 24 cores busy; a tail take past the cap fails
# alone in the container, never WSL.
BLENDER_PEAK_GB = 6.7
BLENDER_MARGIN_GB = 2
GB_IN_GIB = 1e9 / 2**30  # the peaks are decimal GB, the card queue's memory GiB (as Docker's "g")
HELD = {}  # {machine id: the open lock file} for the claims this process holds
# The card GB a claim holds in this PC's card queue (card_queue.py, shared with every card user outside the container),
# measured less the desktop's 2.4: Blender's two card calls beside its resting jobs (card_turn.py: 12.1 of 16.3 GB),
# a Pixal3D take (13.2 of 16 GB, 2026-10-28). A run's own measured need (run.need's card_gb) comes first; a kind in
# neither holds the whole card. DINOv2's likeness (similar_worker.py): 2026-10-31, 56 pairs of an env1 likeness in a
# container of this image, the card's total read every 100 ms: 729 MiB over a steady 2324 before and after.
# The library bakes (library_bake.py): the card queue's own measure of a claim alone on the card, 1.4 GB (2026-10-31,
# card_queue.py measured; a Cycles bake is mostly processor work).
CARD_NEED = {"blender": 9.7, "pixal": 10.8, "similar": 0.8, "library": 1.4}
# The memory GB a kind's claim holds when its run gives none (run.need's memory_gb comes first); a kind in neither
# holds the whole memory. DINOv2's likeness: 2026-10-31, the same 56 pairs, the worker's resident peak 1.26 GB.
MEMORY_NEED = {"similar": 1.3}
CARDS = {}  # {machine id: its open share of the card queue} for the claims this process holds
# Cores the container never gets (--cpus): WSL, the desktop and the run's own steps beside it keep them, so this PC
# answers while the container is busy (2026-10-31: the PC lagged under load). No kind's cores are measured yet: each
# claim's are, from the container's cgroup (card_queue.py measured), to set a kind's own from.
HOST_CORES = 4
# A claim whose run gives its measured memory (run.need's memory_gb: characters' steps, MOSS) runs in the container
# held to that times MEMORY_MARGIN, so a job past its measure ends alone; any other keeps memory_cap.
MEMORY_MARGIN = 1.5
TURNS = {}  # {machine id: [its open turn files]} for the shared claims this process holds
# Kinds whose claims share the machine (the docstring): each of their jobs' files is at its own absolute path.
SHARED = frozenset({"blender"})
# The kinds that stay in MACHINE, the first container, which holds their set-up (Blender 5.0 and its system packages,
# card_turn.py); every other kind has a container of its own (container), made from the same IMAGE (PRD #73).
FIRST = frozenset({"blender", "library"})
# Containers of their own for the other kinds only when the run says so (SCORE_THIS_PC_OWN_CONTAINERS=1, set at a
# restart: each such kind then sets up once in its own); without it every kind stays in MACHINE, one claim at a time
# but Blender's, as before.
OWN = os.environ.get("SCORE_THIS_PC_OWN_CONTAINERS") == "1"
# An exclusive claim's want holds this long after its last ask (it asks every park.PARKED_POLL_SECONDS).
WANT_SECONDS = 120
SSHD_SECONDS = 60
# Where a container's cgroup is (score/graph CGROUPS: systemd's driver, then cgroupfs).
CGROUPS = ("/sys/fs/cgroup/system.slice/docker-{id}.scope", "/sys/fs/cgroup/docker/{id}")
DOCKERFILE = """\
FROM nvidia/cuda:12.8.1-base-ubuntu24.04@sha256:133c78a0575303be34164d0b90137a042172bdf60696af01a3c424ab402d86e2
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends openssh-server python3 python3-venv rsync curl \\
      ca-certificates xz-utils git procps build-essential \\
 && mkdir -p /run/sshd /root/.ssh && chmod 700 /root/.ssh \\
 && echo /usr/lib/wsl/lib > /etc/ld.so.conf.d/wsl.conf && ln -s /usr/lib/wsl/lib/nvidia-smi /usr/local/bin/nvidia-smi
CMD ["sh", "-c", "printf '%s\\\\n' \\"$AUTHORIZED_KEY\\" > /root/.ssh/authorized_keys && ldconfig && exec /usr/sbin/sshd -D -e"]
"""


def docker(*arguments, check=True, **keywords):
    """One docker call; its output as text."""
    return subprocess.run(["docker", *arguments], check=check, capture_output=True, text=True, **keywords)


def image_identity():
    """What a job here runs on, for a kept job's content (kept.py): the container image's id ('' before it is
    built)."""
    return f"{IMAGE} {docker('image', 'inspect', '-f', '{{.Id}}', IMAGE, check=False).stdout.strip()}"


def serves(machine_class):
    """Whether this PC runs a job that asks `machine_class`: one card of at most 24 GB, or a processor machine."""
    found = provider.GPU.match(machine_class)
    if found:
        return not found.group(2) and int(found.group(1)) <= 24
    return bool(provider.CPU.match(machine_class))


def account():
    return ZONE


def offers(classes):
    """This PC for every class of `classes` it serves, at EUR 0 and always `parked` (taken only through park.adopt);
    SystemExit naming the classes when it serves none of them, so a cloud-only job never waits on this PC."""
    served = [name for name in classes if serves(name)]
    if not served:
        raise SystemExit(f"this PC's card is {CARD_GB} GB and it has no second card: {', '.join(classes)} is "
                         f"cloud-only (SCORE_CLOUD=local)")
    return [provider.Offer(0.0, 0, MACHINE, ZONE, 0.0, name, order, "parked") for order, name in enumerate(served)]


def price(machine_type, zone):
    return 0.0, 1


def month_spend(_account):
    return 0.0


def refusal(kind, need=None):
    """Why a job of `kind` cannot run here, or None: its card GB (`need`'s "card_gb", else TOO_BIG's for the kind)
    past CARD_GB, or its system memory GB (`need`'s "memory_gb") past the container's with the job alone (alone_cap)."""
    need = need or {}
    card = need.get("card_gb", TOO_BIG.get(kind))
    if card is not None and card > CARD_GB:
        return (f"a {kind} job needs about {card} GB of card and this PC has {CARD_GB} GB: it stays a cloud job "
                f"(SCORE_CLOUD=local runs it nowhere)")
    memory = need.get("memory_gb")
    if memory is not None and memory > int(alone_cap()[:-1]):
        return (f"a {kind} job needs about {memory:.1f} GB of memory and this PC's machine has {alone_cap()} with "
                f"the job alone: it stays a cloud job (SCORE_CLOUD=local runs it nowhere)")
    return None


def take(kind, public_key, need=None):
    """This PC's machine for one claim, held by this process until `delete`: {id, zone, type, class, cards, price,
    unit_minutes, host, disk_gb, here}; None while another claim holds it, or while the room a job alone needs is
    not free (alone_room). ValueError for a job too big (refusal)."""
    need = {"memory_gb": MEMORY_NEED[kind], **(need or {})} if kind in MEMORY_NEED else need
    refused = refusal(kind, need)
    if refused:
        raise ValueError(refused)
    memory = (need or {}).get("memory_gb", 0) * 2**30
    alone = memory > int(memory_cap()[:-1]) * 2**30
    name = container(kind)
    handles, turns = claimed(kind, alone)
    share = handles and card_queue.take(f"this-pc {kind}", (need or {}).get("card_gb", CARD_NEED.get(kind)), "env-run",
                                        "blender" if turns else None, memory_need(need, turns, alone))
    share = share and card_queue.watch(share)
    if handles and share is None:  # its card or memory is held (another kind's claim, a side job): it waits
        for held in (*turns, *handles):
            held.close()
        handles = []
    mark_waiting(not handles)
    if not handles:
        return None
    try:
        with setting_up():
            host = running(public_key, name)
            if alone and memory > alone_room(name):
                card_queue.release(share)
                for held in handles:
                    held.close()
                want()  # every other claim stays out while it waits for the room
                mark_waiting(True)
                return None
            if alone:
                docker("update", "--memory", alone_cap(), "--memory-swap", alone_cap(), name)
            elif not turns and (need or {}).get("memory_gb"):
                held_to(need["memory_gb"], name)
            card_in_turns(name)
            share.cpu_began = cpu_seconds(name)
    except BaseException:
        card_queue.release(share)
        for held in (*turns, *handles):
            held.close()
        raise
    machine_id = f"{name}:{uuid.uuid4().hex[:12]}"
    HELD[machine_id] = handles
    CARDS[machine_id] = share
    for held in turns or handles[-1:]:  # who holds it: its container's lock, each turn of a shared one
        held.seek(0)
        held.truncate()
        held.write(f"{machine_id} pid {os.getpid()} {kind}\n")
        held.flush()
    found = {"id": machine_id, "zone": ZONE, "type": MACHINE, "class": CARD_CLASS, "cards": 1, "price": 0.0,
             "unit_minutes": 1, "host": host, "disk_gb": shutil.disk_usage(HOME).free // 10**9, "here": True}
    if turns:
        TURNS[machine_id] = turns
        found["turns"] = len(turns)
    elif alone:
        found["turns"] = 1  # one job at a time: the container's whole room is its
    return found


def queued(kind):
    """Whether this process's claim of `kind` waits in the card queue (its waiting entry there, card_queue.take)."""
    return any(job == f"this-pc {kind}" for job, _ in card_queue.WAITING)


def container(kind):
    """The container a claim of `kind` runs in: one of the kind's own under OWN, but MACHINE for the FIRST kinds and
    for every kind without OWN."""
    return MACHINE if kind in FIRST or not OWN else f"{MACHINE}-{kind}"


def container_lock(name):
    """The lock file of container `name`'s claims, beside LOCK."""
    return LOCK.with_name(f"{LOCK.stem}.{name}")


def got(handle, exclusive):
    """Whether this call got `handle`'s flock (exclusive or shared) without waiting."""
    try:
        fcntl.flock(handle, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    return True


def claimed(kind, alone=False):
    """The locks a claim of `kind` holds, and its turns: the PC's LOCK, exclusive for a job `alone` and shared for
    every other claim, so claims of different kinds run side by side (their card and memory then the card queue's);
    and its container's lock (container_lock), exclusive for most kinds and shared for a SHARED kind with every free
    one of its turns (as many of RUNS_AT_ONCE as the queue's memory holds, free_memory_turns). An exclusive lock that
    is busy writes its want, which keeps new shared claims of that lock out until it has its turn. ([], []) while busy
    for it."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    whole = LOCK.open("a+")
    if not got(whole, alone) or not alone and wanted_elsewhere(LOCK):
        whole.close()
        if alone:
            want(LOCK)
        return [], []
    if alone:
        (wanting(LOCK) / str(os.getpid())).unlink(missing_ok=True)
    lock = container_lock(container(kind))
    shared = kind in SHARED and not alone
    own = lock.open("a+")
    if not got(own, not shared) or shared and wanted_elsewhere(lock):
        for held in (own, whole):
            held.close()
        if not shared:
            want(lock)
        return [], []
    if not shared:
        (wanting(lock) / str(os.getpid())).unlink(missing_ok=True)
        return [whole, own], []  # alone: its container's lock too, so a late delete elsewhere leaves it running
    turns = free_turns(RUNS_AT_ONCE.get(kind, 1), free_memory_turns())
    if not turns:
        for held in (own, whole):
            held.close()
        return [], []
    return [whole, own], turns


def memory_need(need, turns, alone):
    """The memory GB a claim holds in the card queue: the whole of it alone, BLENDER_PEAK_GB a turn and
    BLENDER_MARGIN_GB for a shared claim, its run's measured memory_gb, else the whole (unmeasured)."""
    if turns and not alone:
        return (len(turns) * BLENDER_PEAK_GB + BLENDER_MARGIN_GB) * GB_IN_GIB
    return None if alone else (need or {}).get("memory_gb")


def free_memory_turns():
    """How many Blender turns the card queue's free memory holds now (card_queue.memory_free), at least none."""
    return max(0, int((card_queue.memory_free() / GB_IN_GIB - BLENDER_MARGIN_GB) // BLENDER_PEAK_GB))


def waiting_claims():
    """The folder of the claims that wait for the machine and hold none of it, a file named by each such process's
    pid, refreshed at each ask; the runner's drive counts the nodes holding one apart from --jobs
    (score/graph CLAIM_WAITERS), so a Blender row waiting for a turn holds no job slot from other rows."""
    return LOCK.with_name(f"{LOCK.stem}.waiting")


def mark_waiting(waits):
    """This process's mark in waiting_claims: touched while its claim `waits` and it holds no claim (HELD), else
    removed."""
    mark = waiting_claims() / str(os.getpid())
    if waits and not HELD:
        mark.parent.mkdir(parents=True, exist_ok=True)
        mark.touch()
    else:
        mark.unlink(missing_ok=True)


def wanting(lock=None):
    """The folder of the exclusive claims' wants of `lock` (LOCK when None), a file named by each waiting process's
    pid, beside it."""
    lock = lock or LOCK
    return lock.with_name(f"{lock.stem}{lock.suffix}.wanting")


def want(lock=None):
    """This process's want of `lock` exclusive, written (or refreshed) at each ask that found it busy."""
    wanting(lock).mkdir(parents=True, exist_ok=True)
    (wanting(lock) / str(os.getpid())).touch()


def wanted_elsewhere(lock=None, now=None):
    """Whether another live process asked for `lock` exclusive within WANT_SECONDS; the wants of processes gone are
    removed."""
    now = now or time.time()
    found = False
    for path in sorted(wanting(lock).glob("*")) if wanting(lock).exists() else ():
        try:
            fresh = now - path.stat().st_mtime < WANT_SECONDS
            os.kill(int(path.name), 0)
        except (FileNotFoundError, ProcessLookupError, ValueError):
            path.unlink(missing_ok=True)
            continue
        found = found or (fresh and path.name != str(os.getpid()))
    return found


def free_turns(count, most=None):
    """The free ones of `count` turn files beside LOCK, at most `most` (every free one when None), each held exclusive
    (its open file)."""
    turns = []
    for number in range(count):
        if most is not None and len(turns) >= most:
            break
        turn = LOCK.with_name(f"{LOCK.stem}.turn{number}").open("a+")
        try:
            fcntl.flock(turn, fcntl.LOCK_EX | fcntl.LOCK_NB)
            turns.append(turn)
        except BlockingIOError:
            turn.close()
    return turns


def let_go_turn(machine_id):
    """One of a shared claim's turns let go (a slot of its ran out of work), for another claim's job to take."""
    turns = TURNS.get(machine_id) or []
    if turns:
        turns.pop().close()
        card_queue.resize(CARDS[machine_id], memory_need(None, turns, False))


@contextlib.contextmanager
def setting_up():
    """The block run alone among the claims setting this machine up (the container's start, card_turn.py's copy, a
    claim's own set-up: two library_setup.sh on one Blender folder would remove each other's)."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.with_name(f"{LOCK.stem}.setup").open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def running(public_key, name=MACHINE):
    """Container `name`'s address once its sshd answers: the image built and the container started when missing.
    RuntimeError naming the owner's one-time fix when this user may not use Docker."""
    reached = docker("version", "--format", "{{.Server.Version}}", check=False)
    if reached.returncode != 0:
        raise RuntimeError(f"this PC's machine needs Docker, which refused: {reached.stderr.strip()[:200]}. The "
                           "owner, once: sudo usermod -aG docker $USER, then a new terminal")
    if not docker("image", "inspect", IMAGE, check=False).returncode == 0:
        docker("build", "-t", IMAGE, "-", input=DOCKERFILE, timeout=1800)
    state = docker("inspect", "-f", "{{.State.Running}}", name, check=False)
    if state.returncode != 0:
        docker("run", "-d", "--name", name, *card_arguments(), "--shm-size", "8g", *memory_arguments(), *cpu_arguments(),
               "-e", f"AUTHORIZED_KEY={public_key}", IMAGE)
    else:
        docker("update", *memory_arguments(), *cpu_arguments(), name)  # one made before these limits takes them too
        if state.stdout.strip() != "true":
            docker("start", name)
    return answering(name)


def memory_arguments():
    """The container's memory, and its swap held to the same, so a job past it ends alone: with --memory only,
    Docker lets it swap as much again into this PC's swap (env1, 2026-10-28: garage_vehicle_lift's paint at 27 GB
    filled 15 of 16 GB of WSL's swap)."""
    return ["--memory", memory_cap(), "--memory-swap", memory_cap()]


def cpu_arguments():
    """The container's cores: this PC's less HOST_CORES (at least 1)."""
    return ["--cpus", str(max(1, os.cpu_count() - HOST_CORES))]


def held_to(memory_gb, name=MACHINE):
    """Container `name` held to a claim's measured `memory_gb` times MEMORY_MARGIN (never past memory_cap). Docker refuses
    a cap under what the container holds now (a job left from before its restart): the claim then keeps memory_cap,
    as before this limit, and says so."""
    cap = f"{min(math.ceil(memory_gb * MEMORY_MARGIN), int(memory_cap()[:-1]))}g"
    done = docker("update", "--memory", cap, "--memory-swap", cap, name, check=False)
    if getattr(done, "returncode", 0):
        print(f"local: {name} stays at {memory_cap()}: docker refused {cap} ({done.stderr.strip()[:120]})",
              file=sys.stderr, flush=True)


def cpu_seconds(name=MACHINE):
    """The processor seconds container `name`'s processes used since it started (its cgroup's cpu.stat usage_usec);
    None when it cannot be read."""
    identity = docker("inspect", "-f", "{{.Id}}", name, check=False)
    for form in CGROUPS:
        stat = pathlib.Path(form.format(id=getattr(identity, "stdout", "").strip())) / "cpu.stat"
        with contextlib.suppress(OSError, ValueError, StopIteration):
            return int(next(line for line in stat.read_text().splitlines() if line.startswith("usage_usec")).split()[1]) / 1e6
    return None


def card_arguments():
    """How the card reaches the container: WSL's GPU device and driver folder, else NVIDIA's container runtime."""
    if pathlib.Path("/dev/dxg").exists():
        return ["--device", "/dev/dxg", "-v", "/usr/lib/wsl:/usr/lib/wsl:ro"]
    return ["--gpus", "all"]


def memory_cap():
    """The container's memory: this PC's less HOST_RESERVE_GB (at least 8 GB), so the container, the run's own steps
    beside it and WSL never add up past this PC's memory."""
    total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") // 2**30
    return f"{max(8, total - HOST_RESERVE_GB)}g"


def meminfo(name):
    """The bytes of /proc/meminfo's `name` line."""
    line = next(line for line in pathlib.Path("/proc/meminfo").read_text().splitlines() if line.startswith(f"{name}:"))
    return int(line.split()[1]) * 1024


def alone_cap():
    """The container's memory while a job runs in it alone (HOST_FLOOR_GB): this PC's less HOST_FLOOR_GB and less
    what its RAM drives hold (Shmem: /tmp and the other tmpfs), never below memory_cap."""
    room = (meminfo("MemTotal") - meminfo("Shmem")) // 2**30 - HOST_FLOOR_GB
    return f"{max(int(memory_cap()[:-1]), room)}g"


def alone_room(name=MACHINE):
    """The bytes a job alone may grow to now: what the container holds (the anon of its memory.stat, which
    MemAvailable leaves out) and this PC's available memory less HOST_FLOOR_GB, never past alone_cap."""
    stat = docker("exec", name, "cat", "/sys/fs/cgroup/memory.stat").stdout.split()
    held = int(stat[stat.index("anon") + 1])
    return min(held + meminfo("MemAvailable") - HOST_FLOOR_GB * 2**30, int(alone_cap()[:-1]) * 2**30)


def blender_at_once(memory_gb):
    """Blender jobs the container runs at once: its memory (`memory_gb`, decimal GB) less BLENDER_MARGIN_GB, over
    BLENDER_PEAK_GB; at least one."""
    return max(1, int((memory_gb - BLENDER_MARGIN_GB) // BLENDER_PEAK_GB))


# Jobs of a kind this machine runs at once (capacity.runs_at_once reads it, spread.slots runs them in one claim),
# measured here. One Pixal3D take peaked at 13.2 of the 16 GB with the desktop (galley's jars and oven, 2026-10-28), so
# two side by side do not fit. Blender jobs (a bake row's takes: paint, cut-down, unwrap, scene sync and glTF export on
# the processor, the Cycles bake in 1 s bursts on the card) run as many at once as the container's memory holds at a
# take's peak, the card two calls at a time (card_turn.py CARD_SLOTS; env1, 2026-10-28: one take at a time left about 20 of 24
# cores idle and the card under 10% busy 86% of the time).
RUNS_AT_ONCE = {"pixal": 1, "blender": blender_at_once(int(memory_cap()[:-1]) * 2**30 / 1e9)}


def card_in_turns(name=MACHINE):
    """card_turn.py into the container's Blender user startup folder, so every Blender there takes the card at most
    card_turn.CARD_SLOTS calls at a time while RUNS_AT_ONCE's Blender jobs share it."""
    import card_turn

    docker("exec", name, "mkdir", "-p", card_turn.STARTUP)
    # Copied beside and moved in, so a Blender of another claim starting meanwhile never reads half of it.
    docker("cp", str(CARD_TURN), f"{name}:{card_turn.STARTUP}/.{CARD_TURN.name}.new")
    docker("exec", name, "mv", f"{card_turn.STARTUP}/.{CARD_TURN.name}.new", f"{card_turn.STARTUP}/{CARD_TURN.name}")


def answering(name=MACHINE):
    """Container `name`'s address once its sshd listens; RuntimeError after SSHD_SECONDS."""
    give_up = time.time() + SSHD_SECONDS
    while time.time() < give_up:
        host = address(name, ZONE)
        if host and docker("exec", name, "sh", "-c", "pgrep -x sshd", check=False).returncode == 0:
            return host
        time.sleep(1)
    raise RuntimeError(f"{name}'s sshd did not start within {SSHD_SECONDS} s (docker logs {name})")


def address(machine_id, _zone):
    """The address of `machine_id`'s container (the part before its ":") on Docker's bridge, or None while it has
    none."""
    found = docker("inspect", "-f", "{{json .NetworkSettings.Networks}}", machine_id.split(":")[0], check=False)
    if found.returncode != 0:
        return None
    return next((network["IPAddress"] for network in json.loads(found.stdout).values() if network.get("IPAddress")),
                None)


def delete(machine_id, _zone):
    """End a claim: its turns, card share and locks let go, and its container (the part of `machine_id` before ":")
    restarted (whatever its job left running on the card ends; its files stay) when no other claim holds it, so a
    shared claim leaving never restarts it under another's jobs. A claim another process still holds (a watchdog of
    a claim that already ended) is left alone; True when this call ended it."""
    name = machine_id.split(":")[0]
    for turn in TURNS.pop(machine_id, []):
        turn.close()
    if machine_id in CARDS:
        share = CARDS.pop(machine_id)
        used = cpu_seconds(name)
        cores = None if None in (used, share.cpu_began) else round((used - share.cpu_began) / max(
            time.time() - share.began, 1e-3), 2)
        card_queue.release(share, cores)
    handles = HELD.pop(machine_id, None)
    ours = handles is not None
    if not ours:
        if not container_lock(name).exists():
            return False
        handles = [container_lock(name).open("a+")]
    if not got(handles[-1], True):  # held alone: no other claim's jobs run in its container
        for held in handles:
            held.close()
        return ours
    try:
        docker("restart", "-t", "5", name, check=False)
        docker("update", *memory_arguments(), name, check=False)  # back from a job alone's or held_to's room
    finally:
        for held in handles:
            held.close()
    return True


def start_if_stopped(_machine_id, _zone):
    return None


def allow_key(_account, _name, _public_key):
    """Nothing to do: the runner's key goes into the container when it is made (take)."""


def retag(_machine_id, _zone, _tags):
    """Nothing to do: the container carries no tags; its lock says who holds it."""


def create(_account, offer, _name, _tags, _disk_gb):
    return None, f"{offer.type} is this PC: never ordered (its offers are parked; park.adopt takes it)"


def ours(_account):
    """Nothing for a sweep: the container is never deleted by one (its claims end with `delete`)."""
    return []


def leftover_addresses(_account, zones=None):
    return []


def leftover_disks(_account, zones=None):
    return []


def secret(name):
    """A secret from the Scaleway backend's store, read by name (the only store the runners' secrets live in)."""
    import scaleway
    return scaleway.secret(name)


def registry():
    raise SystemExit("SCORE_CLOUD=local has no image registry: its jobs run on the machine path, never the cluster")


def object_store():
    raise SystemExit("SCORE_CLOUD=local has no object store: every input goes straight to the container")
