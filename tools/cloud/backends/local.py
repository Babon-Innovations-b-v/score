"""This PC as the one machine the runners use (SCORE_CLOUD=local; the owner, 2026-10-27: "couldnt u just finish the
rest of env1 on this gpu aswell", then "yes"): its card, never rented, never billed.

The machine is one Docker container on this PC (MACHINE), made from IMAGE (Ubuntu 24.04 with NVIDIA's CUDA base, as
the rented card machines run, plus sshd): the runners reach it as root over ssh and rsync with the runner's key, at
the same absolute paths, exactly as a rented machine, so no runner changes. Its set-up (Blender, a kind's venv) stays
in the container from one job to the next, each kind's own (park.own_set_up: its own /root/venv, its marks never
removed there), so a kind sets up once. The card comes in
through WSL's /dev/dxg and /usr/lib/wsl (on plain Linux through `--gpus all`); the container's memory is held under
this PC's own so a job that runs out of memory fails alone and never takes WSL down.

One claim at a time over the whole PC (a file lock, `take`), but for the SHARED kinds: a claim that finds it busy gets
None and its runner waits and asks again (batch.claim_rounds polls park.adopt). A SHARED kind's jobs (Blender: every
input and output at its own absolute path, nothing of one claim's in another's way) share the machine across claims:
such a claim holds the lock shared and takes every free one of RUNS_AT_ONCE's turns (a lock file each, one Blender
job a turn), each turn let go as its slot runs out of work (spread.tend), so the container runs RUNS_AT_ONCE's Blender
jobs at once (as many as its memory holds at a take's measured peak) over all the places' bake rows, never one row at
a time (env1, 2026-10-28: 26 bake rows waited on the claim of one place). An exclusive claim waiting (its want under
WANTING) keeps new shared claims out until it has its turn, so a stream of bakes never starves it; the container's
set-up and each claim's own (`setting_up`) run one at a time. Each of the jobs' card calls (the Cycles bake, a render)
waits its turn on the card (card_turn.py, put into the container's Blender startup folder at every claim), so the
card never works for more than card_turn.CARD_SLOTS (two) jobs at once. Its offers are
always `parked`, so batch.rent never orders anything: the machine is only ever taken through park.adopt
(park.here), which asks no clearance, since it costs nothing (price 0; the ledger's rows carry the measured minutes
at EUR 0). A job that needs more card or memory than this PC has is refused at its claim with the reason, never run
to an out-of-memory; it stays a cloud job. The need is the job's own measure when its run gives one (a characters
run of clip steps only: characters.card_need), else its kind's (TOO_BIG). `delete` restarts the container, which ends whatever a job left running on
the card (a detached worker), and keeps its files: only when no other claim holds it, so the last shared claim to
leave restarts it and none restarts it under another claim's jobs.

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
import time
import uuid

import provider
from paths import HOME

NAME = "local"
MACHINE = "score-this-pc"  # the container's name, and the machine type the offers name
ZONE = "this-pc"
IMAGE = "score-this-pc:1"
# Memory the container never gets: 8 GB WSL keeps free, 8 GB for the run's processor steps beside the container
# (score run --jobs; owner, 2026-10-27: a WSL out of memory is the worst outcome, the sum stays under RAM less 8 GB).
HOST_RESERVE_GB = 16
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
BLENDER_PEAK_GB = 8.5
BLENDER_MARGIN_GB = 2
HELD = {}  # {machine id: the open lock file} for the claims this process holds
TURNS = {}  # {machine id: [its open turn files]} for the shared claims this process holds
# Kinds whose claims share the machine (the docstring): each of their jobs' files is at its own absolute path.
SHARED = frozenset({"blender"})
# An exclusive claim's want holds this long after its last ask (it asks every park.PARKED_POLL_SECONDS).
WANT_SECONDS = 120
SSHD_SECONDS = 60
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
    past CARD_GB, or its system memory GB (`need`'s "memory_gb") past the container's (memory_cap)."""
    need = need or {}
    card = need.get("card_gb", TOO_BIG.get(kind))
    if card is not None and card > CARD_GB:
        return (f"a {kind} job needs about {card} GB of card and this PC has {CARD_GB} GB: it stays a cloud job "
                f"(SCORE_CLOUD=local runs it nowhere)")
    memory = need.get("memory_gb")
    if memory is not None and memory > int(memory_cap()[:-1]):
        return (f"a {kind} job needs about {memory} GB of memory and this PC's machine has {memory_cap()}: it stays "
                f"a cloud job (SCORE_CLOUD=local runs it nowhere)")
    return None


def take(kind, public_key, need=None):
    """This PC's machine for one claim, held by this process until `delete`: {id, zone, type, class, cards, price,
    unit_minutes, host, disk_gb, here}; None while another claim holds it. ValueError for a job too big (refusal)."""
    refused = refusal(kind, need)
    if refused:
        raise ValueError(refused)
    handle, turns = claimed(kind)
    mark_waiting(handle is None)
    if handle is None:
        return None
    try:
        with setting_up():
            host = running(public_key)
            card_in_turns()
    except BaseException:
        for held in (*turns, handle):
            held.close()
        raise
    machine_id = f"{MACHINE}:{uuid.uuid4().hex[:12]}"
    HELD[machine_id] = handle
    for held in turns or [handle]:  # who holds it: the lock file of an exclusive claim, each turn of a shared one
        held.seek(0)
        held.truncate()
        held.write(f"{machine_id} pid {os.getpid()} {kind}\n")
        held.flush()
    found = {"id": machine_id, "zone": ZONE, "type": MACHINE, "class": CARD_CLASS, "cards": 1, "price": 0.0,
             "unit_minutes": 1, "host": host, "disk_gb": shutil.disk_usage(HOME).free // 10**9, "here": True}
    if turns:
        TURNS[machine_id] = turns
        found["turns"] = len(turns)
    return found


def claimed(kind):
    """The lock for a claim of `kind` and its turns: held exclusive for most kinds (the want written while it waits),
    shared for a SHARED kind with every free one of its RUNS_AT_ONCE turns; (None, []) while the machine is busy for
    it (held exclusive, an exclusive claim waiting, or every turn taken)."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    shared = kind in SHARED
    handle = LOCK.open("a+")
    try:
        fcntl.flock(handle, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        if not shared:
            want()
        return None, []
    if not shared:
        (wanting() / str(os.getpid())).unlink(missing_ok=True)
        return handle, []
    turns = [] if wanted_elsewhere() else free_turns(RUNS_AT_ONCE.get(kind, 1))
    if not turns:
        handle.close()
        return None, []
    return handle, turns


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


def wanting():
    """The folder of the exclusive claims' wants, a file named by each waiting process's pid, beside LOCK."""
    return LOCK.with_name(f"{LOCK.stem}.wanting")


def want():
    """This process's want of an exclusive claim, written (or refreshed) at each ask that found the machine busy."""
    wanting().mkdir(parents=True, exist_ok=True)
    (wanting() / str(os.getpid())).touch()


def wanted_elsewhere(now=None):
    """Whether another live process asked for an exclusive claim within WANT_SECONDS; the wants of processes gone
    are removed."""
    now = now or time.time()
    found = False
    for path in sorted(wanting().glob("*")) if wanting().exists() else ():
        try:
            fresh = now - path.stat().st_mtime < WANT_SECONDS
            os.kill(int(path.name), 0)
        except (FileNotFoundError, ProcessLookupError, ValueError):
            path.unlink(missing_ok=True)
            continue
        found = found or (fresh and path.name != str(os.getpid()))
    return found


def free_turns(count):
    """Every free one of `count` turn files beside LOCK, each held exclusive (its open file)."""
    turns = []
    for number in range(count):
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


@contextlib.contextmanager
def setting_up():
    """The block run alone among the claims setting this machine up (the container's start, card_turn.py's copy, a
    claim's own set-up: two library_setup.sh on one Blender folder would remove each other's)."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.with_name(f"{LOCK.stem}.setup").open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def running(public_key):
    """The container's address once its sshd answers: the image built and the container started when missing.
    RuntimeError naming the owner's one-time fix when this user may not use Docker."""
    reached = docker("version", "--format", "{{.Server.Version}}", check=False)
    if reached.returncode != 0:
        raise RuntimeError(f"this PC's machine needs Docker, which refused: {reached.stderr.strip()[:200]}. The "
                           "owner, once: sudo usermod -aG docker $USER, then a new terminal")
    if not docker("image", "inspect", IMAGE, check=False).returncode == 0:
        docker("build", "-t", IMAGE, "-", input=DOCKERFILE, timeout=1800)
    state = docker("inspect", "-f", "{{.State.Running}}", MACHINE, check=False)
    if state.returncode != 0:
        docker("run", "-d", "--name", MACHINE, *card_arguments(), "--shm-size", "8g", *memory_arguments(),
               "-e", f"AUTHORIZED_KEY={public_key}", IMAGE)
    else:
        docker("update", *memory_arguments(), MACHINE)  # a container made before the swap limit takes it too
        if state.stdout.strip() != "true":
            docker("start", MACHINE)
    return answering()


def memory_arguments():
    """The container's memory, and its swap held to the same, so a job past it ends alone: with --memory only,
    Docker lets it swap as much again into this PC's swap (env1, 2026-10-28: garage_vehicle_lift's paint at 27 GB
    filled 15 of 16 GB of WSL's swap)."""
    return ["--memory", memory_cap(), "--memory-swap", memory_cap()]


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


def card_in_turns():
    """card_turn.py into the container's Blender user startup folder, so every Blender there takes the card at most
    card_turn.CARD_SLOTS calls at a time while RUNS_AT_ONCE's Blender jobs share it."""
    import card_turn

    docker("exec", MACHINE, "mkdir", "-p", card_turn.STARTUP)
    # Copied beside and moved in, so a Blender of another claim starting meanwhile never reads half of it.
    docker("cp", str(CARD_TURN), f"{MACHINE}:{card_turn.STARTUP}/.{CARD_TURN.name}.new")
    docker("exec", MACHINE, "mv", f"{card_turn.STARTUP}/.{CARD_TURN.name}.new", f"{card_turn.STARTUP}/{CARD_TURN.name}")


def answering():
    """The container's address once its sshd listens; RuntimeError after SSHD_SECONDS."""
    give_up = time.time() + SSHD_SECONDS
    while time.time() < give_up:
        host = address(MACHINE, ZONE)
        if host and docker("exec", MACHINE, "sh", "-c", "pgrep -x sshd", check=False).returncode == 0:
            return host
        time.sleep(1)
    raise RuntimeError(f"{MACHINE}'s sshd did not start within {SSHD_SECONDS} s (docker logs {MACHINE})")


def address(_machine_id, _zone):
    """The container's address on Docker's bridge, or None while it has none."""
    found = docker("inspect", "-f", "{{json .NetworkSettings.Networks}}", MACHINE, check=False)
    if found.returncode != 0:
        return None
    return next((network["IPAddress"] for network in json.loads(found.stdout).values() if network.get("IPAddress")),
                None)


def delete(machine_id, _zone):
    """End a claim: its turns and lock let go, and the container restarted (whatever its job left running on the card
    ends; its files stay) when no other claim holds it, so a shared claim leaving never restarts it under another's
    jobs. A claim another process still holds (a watchdog of a claim that already ended) is left alone; True when this
    call ended it."""
    for turn in TURNS.pop(machine_id, []):
        turn.close()
    handle = HELD.pop(machine_id, None)
    if handle is not None:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)  # held alone: no other claim's jobs run there
        except BlockingIOError:
            handle.close()
            return True
    else:
        if not LOCK.exists():
            return False
        handle = LOCK.open("a+")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            return False
    try:
        docker("restart", "-t", "5", MACHINE, check=False)
    finally:
        handle.close()
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
