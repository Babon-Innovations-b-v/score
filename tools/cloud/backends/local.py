"""This PC as the one machine the runners use (SCORE_CLOUD=local; the owner, 2026-10-27: "couldnt u just finish the
rest of env1 on this gpu aswell", then "yes"): its card, never rented, never billed.

The machine is one Docker container on this PC (MACHINE), made from IMAGE (Ubuntu 24.04 with NVIDIA's CUDA base, as
the rented card machines run, plus sshd): the runners reach it as root over ssh and rsync with the runner's key, at
the same absolute paths, exactly as a rented machine, so no runner changes. Its set-up (Blender, a kind's venv) stays
in the container from one job to the next; only the newest set-up mark is kept (park.STALE_MARKS). The card comes in
through WSL's /dev/dxg and /usr/lib/wsl (on plain Linux through `--gpus all`); the container's memory is held under
this PC's own so a job that runs out of memory fails alone and never takes WSL down.

One claim at a time over the whole PC (a file lock, `take`): the card is never shared by two jobs' processes, a claim
that finds it busy gets None and its runner waits and asks again (batch.claim_rounds polls park.adopt). Its offers are
always `parked`, so batch.rent never orders anything: the machine is only ever taken through park.adopt
(park.here), which asks no clearance, since it costs nothing (price 0; the ledger's rows carry the measured minutes
at EUR 0). A job that needs more card or memory than this PC has is refused at its claim with the reason, never run
to an out-of-memory; it stays a cloud job. The need is the job's own measure when its run gives one (a characters
run of clip steps only: characters.card_need), else its kind's (TOO_BIG). `delete` restarts the container, which ends whatever a job left running on
the card (a detached worker), and keeps its files.

The interface is provider.py's; what has no meaning here (accounts, addresses, disks, the registry and the object
store) says so or gives nothing.
"""
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
# Jobs of a kind this card runs at once, measured here: one Pixal3D take peaked at 13.2 of the 16 GB with the desktop
# (galley's jars and oven, 2026-10-28), so two side by side do not fit; capacity.runs_at_once reads it.
RUNS_AT_ONCE = {"pixal": 1}
TOO_BIG = {"judge": 30, "pictures-20b": 58, "characters": 17, "meshparts": 24, "moss-sound": 15.6}
# Classes this PC answers for: a single card of at most 24 GB (the jobs that ask one fit on 16 GB unless TOO_BIG says
# otherwise) and every processor class (24 cores here; a job takes longer, never fails for it).
SERVES = (provider.GPU, provider.CPU)
CLASSES = {}  # nothing is ever ordered (offers are `parked`); the classes served are SERVES'
QUOTAS = {CARD_CLASS: 1}  # one machine; capacity.caps needs one entry
LOCK = HOME / "cloud" / "this-pc.lock"
HELD = {}  # {machine id: the open lock file} for the claims this process holds
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
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK.open("a+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    try:
        host = running(public_key)
    except BaseException:
        handle.close()
        raise
    machine_id = f"{MACHINE}:{uuid.uuid4().hex[:12]}"
    HELD[machine_id] = handle
    handle.seek(0)
    handle.truncate()
    handle.write(f"{machine_id} pid {os.getpid()} {kind}\n")
    handle.flush()
    return {"id": machine_id, "zone": ZONE, "type": MACHINE, "class": CARD_CLASS, "cards": 1, "price": 0.0,
            "unit_minutes": 1, "host": host, "disk_gb": shutil.disk_usage(HOME).free // 10**9, "here": True}


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
    """End a claim: the container restarted (whatever its job left running on the card ends; its files stay) and the
    lock let go. A claim another process still holds (a watchdog of a claim that already ended) is left alone; True
    when this call ended it."""
    handle = HELD.pop(machine_id, None)
    if handle is None:
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
