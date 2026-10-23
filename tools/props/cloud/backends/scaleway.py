"""The Scaleway backend of the cloud layer (`../provider.py` says what a backend gives), through the logged-in `scw`
command. Scaleway is the backend the framework runs on today.

Every call names the project and the zone itself. The CLI's default profile may point at another project, and it is
never changed from here, so leaving either out could rent a machine on the wrong account. The "account" of the
provider interface is a Scaleway project here.
"""
import base64
import datetime
import functools
import json
import math
import os
import pathlib
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))  # tools/props, for the ledger's paths

from paths import HOME  # noqa: E402
from provider import Offer, cards  # noqa: E402

NAME = "scaleway"
# The Scaleway project the machines are rented in, looked up by name, so no account id sits in the repo:
# SCORE_SCALEWAY_PROJECT, else the one the owner set aside for the first world's machines.
PROJECT_NAME = os.environ.get("SCORE_SCALEWAY_PROJECT", "farm-factory")
# Ubuntu 24.04 with the NVIDIA driver and CUDA runtime (Scaleway's own GPU image), and plain Ubuntu 24.04 for the
# processor machines.
IMAGES = {"gpu": "ubuntu_noble_gpu_os_13_nvidia", "cpu": "ubuntu_noble"}
# Each capability class as the Scaleway machine types that give it, tried in this order (2026-10-08). The P100
# (RENDER-S) gives none: this GPU image's driver does not see its card.
CLASSES = {
    "gpu-24gb": ("L4-1-24G",),
    "gpu-48gb": ("L40S-1-48G",),
    "gpu-80gb": ("H100-1-80G",),
    "gpu-24gb-x2": ("L4-2-24G",),
    "gpu-80gb-x2": ("H100-SXM-2-80G", "H100-2-80G"),
    # The big processor machines a render or bake takes from a run's warm pool (owner, 2026-10-23: "cant u just get a
    # faster cpu"): Cycles on a processor scales about with its cores and so does the price, so more cores render a
    # job sooner at about the same euros. POP2-HC (2 GB a core) is the cheapest a core: EUR 0.027 a core-hour in
    # nl-ams-2 against 0.037 for POP2 (2026-10-23). The same POP2 family and image as the 32-core types; the 48- and
    # 64-core ones not yet seen running here.
    "cpu-64c-128gb": ("POP2-HC-64C-128G",),
    "cpu-64c-256gb": ("POP2-64C-256G",),
    "cpu-48c-96gb": ("POP2-HC-48C-96G",),
    "cpu-48c-192gb": ("POP2-48C-192G",),
    "cpu-32c-128gb": ("POP2-32C-128G",),
    "cpu-32c-64gb": ("POP2-HC-32C-64G",),
    "cpu-32c-256gb": ("POP2-HM-32C-256G",),
    "cpu-16c-64gb": ("POP2-16C-64G",),
    "cpu-16c-128gb": ("POP2-HM-16C-128G",),
    "cpu-4c-32gb": ("POP2-HM-4C-32G",),
}
# How many machines of a class the project may hold at once, where Scaleway granted a quota (2026-10-08: H100-1-80G 20,
# L4-1-24G 50, L40S-1-48G 10, across fr-par-1, fr-par-2 and pl-waw-2). Stock is still the real limit; a class not
# listed has the provider's default quota, and a rent past any quota is refused and the next offer taken.
QUOTAS = {"gpu-80gb": 20, "gpu-24gb": 50, "gpu-48gb": 10}
# Minutes in each unit Scaleway's price list prices a machine by: the cards by the minute, the
# processor machines (POP2) by the hour (2026-10-05).
PER_UNIT_MINUTES = {"minute": 1, "hour": 60}
# Scaleway's words for a type's stock, best first.
STOCK_ORDER = {"available": 0, "parked": 1, "scarce": 1, "shortage": 2}
# Addresses whose machines drop SSH (reset or closed connections on every run that got one, 2026-10-10 to 13): a new
# machine given one gets a fresh address, and the bad one is kept in the project under QUARANTINED (about EUR 3.60 a
# month each, captain 2026-10-13), which leftover_addresses and so every sweep leave alone.
BAD_ADDRESSES = {"151.115.78.211": "ssh-drops-2026-10-13"}
QUARANTINED = "farm-factory-quarantined"
# Where park.py keeps its records of parked machines (batch.CLOUD / "parked"); read here, not imported (park imports
# batch, which imports this backend through provider).
PARKED = HOME / "cloud" / "parked"
# Every machine the runner rents carries this tag, so a sweep can find what a crashed run left.
TAG = "farm-factory-batch"
# The zones that rent graphics cards (2026-09-29).
ZONES = ("pl-waw-2", "fr-par-2", "fr-par-1")
# The other zones that rent processor machines (2026-10-23: every big POP2 type short in fr-par-1, fr-par-2, fr-par-3
# and nl-ams-1, in stock in nl-ams-2, nl-ams-3, pl-waw-1, pl-waw-3 and it-mil-1): a processor class is offered in
# every zone of `rent_zones()`, a card class in ZONES only.
PROCESSOR_ZONES = ("nl-ams-2", "nl-ams-3", "pl-waw-1", "pl-waw-3", "it-mil-1", "fr-par-3", "nl-ams-1")
# A machine type's quota in a zone is named this and the type (POP2-HC-48C-96G: cp_servers_type_POP2_HC_48C_96G).
QUOTA_PREFIX = "cp_servers_type_"
QUOTA_URL = "https://api.scaleway.com/iam/v1alpha1/quota"
QUOTA_PAGE = 100
# What a machine's root disk (block storage, 5k IOPS) and public address cost, in euros a GB-hour and an
# address-hour, each billed by the started hour from the machine's creation (the October 2026 bill: EUR 31.87 for
# 245,140 GB-hours, EUR 15.80 for 3,160 address-hours).
DISK_EUROS_A_GB_HOUR = 0.00013
ADDRESS_EUROS_AN_HOUR = 0.005
# How many times, 10 s apart, a delete waits out a machine that is still shutting down.
STOPPING_TRIES = 12
# How many times, 10 s apart, a failed delete reads the machine again to see whether another run deleted it.
GONE_TRIES = 3
# Seconds a refused order's new loose address or disk must stay loose before it is deleted: another order's own
# address is loose for a moment between the CLI making it and its machine taking it.
LOOSE_SETTLE_SECONDS = 15
# A failed read of the API (scw's verbs below) is asked again this many times in all, waiting 5, 10, 20, 40 s between.
READS = {"list", "get", "access-by-path"}
READ_TRIES = 5
READ_WAIT_SECONDS = 5.0


def scw(*arguments):
    """Run one `scw` command and return its JSON answer, failing loudly with its error output. A read (list, get,
    access) that fails is asked again READ_TRIES times, waiting longer each time: with twenty lines renting at once
    a server list failed once and stopped a paid row (2026-10-11); a write is never repeated, it may have happened."""
    tries = READ_TRIES if set(arguments) & READS else 1
    for attempt in range(tries):
        done = subprocess.run(["scw", *arguments, "-o", "json"], capture_output=True, text=True)
        if done.returncode == 0:
            return json.loads(done.stdout) if done.stdout.strip() else None
        if attempt + 1 < tries:
            time.sleep(READ_WAIT_SECONDS * 2 ** attempt)
    raise subprocess.CalledProcessError(done.returncode, ["scw", *arguments], done.stdout, done.stderr)


def account():
    """The id of the Scaleway project named PROJECT_NAME: the account every call rents in and deletes from."""
    found = [project for project in scw("account", "project", "list", f"name={PROJECT_NAME}")
             if project["name"] == PROJECT_NAME]
    if len(found) != 1:
        raise SystemExit(f"expected one Scaleway project named {PROJECT_NAME}, found {len(found)}")
    return found[0]["id"]


def secret(name):
    """The latest value of the project's secret `name` in Secret Manager; it is
    handed back, never printed or written."""
    version = scw("secret", "version", "access-by-path", f"secret-name={name}",
                  f"project-id={account()}", "revision=latest")
    return base64.b64decode(version["data"]).decode().strip()


@functools.lru_cache(maxsize=None)
def price_list(zone):
    """Scaleway's price list of machines in `zone`, read once a run."""
    return tuple(scw("product-catalog", "product", "list", "product-types.0=instance", f"zone={zone}"))


def price(machine_type, zone):
    """What `machine_type` costs in `zone`: (euros a minute, the minutes Scaleway bills it by), from its price list.
    The cards are billed by the minute, the processor machines (POP2) and RENDER-S by the started hour."""
    sku = f"/instance/server/{machine_type.lower().replace('-', '_')}/{zone}"
    for product in price_list(zone):
        if product["sku"] == sku:
            unit = product["unit_of_measure"]["unit"]
            if unit not in PER_UNIT_MINUTES:
                raise SystemExit(f"{sku} is priced per {unit}; the caps know minutes and hours")
            listed = product["price"]["retail_price"]
            return (listed["units"] + listed["nanos"] / 1e9) / PER_UNIT_MINUTES[unit], PER_UNIT_MINUTES[unit]
    raise SystemExit(f"no price for {machine_type} in {zone}")


def parked_places(now):
    """(type, zone) of every machine a run parked with time left (tools/props/cloud/park.py's records)."""
    found = set()
    for path in PARKED.glob("*.json"):
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError):  # struck off, or being written, while read: not one to count on
            continue
        if record.get("until", 0) > now:
            found.add((record["type"], record["zone"]))
    return found


def rent_zones():
    """Every zone a machine is rented in: the card zones, then the processor zones."""
    return (*ZONES, *(zone for zone in PROCESSOR_ZONES if zone not in ZONES))


def quota_pages(organization, secret_key):
    """Every quota of the organisation, read page by page from Scaleway's IAM API (the CLI has no quota command)."""
    import urllib.parse
    import urllib.request

    found, page = [], 1
    while True:
        query = urllib.parse.urlencode({"organization_id": organization, "page_size": QUOTA_PAGE, "page": page})
        request = urllib.request.Request(f"{QUOTA_URL}?{query}", headers={"X-Auth-Token": secret_key})
        with urllib.request.urlopen(request, timeout=60) as answer:
            body = json.load(answer)
        found += body.get("quota") or []
        if not body.get("quota") or len(found) >= body.get("total_count", 0):
            return found
        page += 1


@functools.lru_cache(maxsize=None)
def zone_quotas():
    """{(machine type, zone): machines} the project's organisation may hold, read once a process (a free read). A
    type and zone it lists no quota for holds none (POP2-HC-64C-128G and POP2-64C-256G, 2026-10-23, until the owner's
    request for more is granted), so it is never ordered."""
    organization = scw("account", "project", "get", f"project-id={account()}")["organization_id"]
    found = {}
    for quota in quota_pages(organization, scw("config", "get", "secret-key")):
        if quota["name"].startswith(QUOTA_PREFIX):
            machine_type = quota["name"][len(QUOTA_PREFIX):].replace("_", "-")
            for limit in quota.get("limits") or []:
                if "zone" in limit:
                    found[(machine_type, limit["zone"])] = (math.inf if limit.get("unlimited")
                                                            else limit.get("limit") or 0)
    return found


def offers(classes):
    """Every place a machine of one of `classes` can be rented: an Offer for each type and zone that sells it and
    whose quota there is above 0 (zone_quotas), a processor class in every zone of `rent_zones()`. Where Scaleway says
    shortage but one of our runs parked a machine of that type, the offer says `parked`: the claim takes that machine
    first (2026-10-12: every POP2-32C-128G was ours, parked, and blender_cloud refused for no stock)."""
    found = []
    parked = parked_places(time.time())
    quotas = zone_quotas()
    for zone in rent_zones():
        here = [machine_class for machine_class in classes if zone in ZONES or not cards(machine_class)]
        if not here:
            continue
        listed = {server["name"]: server.get("availability") for server in scw("instance", "server-type", "list",
                                                                                 f"zone={zone}")}
        for machine_class in here:
            for order, machine_type in enumerate(CLASSES.get(machine_class, ())):
                if machine_type not in listed or not quotas.get((machine_type, zone)):
                    continue
                euros = price(machine_type, zone)[0]
                stock = listed[machine_type]
                stock = "parked" if stock == "shortage" and (machine_type, zone) in parked else stock
                found.append(Offer(euros / max(1, cards(machine_class)), STOCK_ORDER.get(stock, 3),
                                   machine_type, zone, euros, machine_class, order, stock))
    return found


def consumption(project):
    """Scaleway's own month-to-date bill of the project, a line per product and zone: {"product", "sku", "unit",
    "quantity", "euros"}. Each line is checked to be the project's. It lags by hours."""
    lines = []
    for line in scw("billing", "consumption", "list", f"project-id={project}") or []:
        if line.get("project_id") != project:
            continue
        value = line.get("value") or {}
        lines.append({"product": line.get("product_name"), "sku": line.get("sku"), "unit": line.get("unit"),
                      "quantity": float(line.get("billed_quantity") or 0),
                      "euros": value.get("units", 0) + value.get("nanos", 0) / 1e9})
    return lines


def month_spend(project):
    """What Scaleway has billed the project so far this month, in euros. It lags by hours."""
    return sum(line["euros"] for line in consumption(project))


def server_record(server_id, zone):
    """The machine's record as Scaleway holds it, or None when it is gone."""
    done = subprocess.run(["scw", "instance", "server", "get", server_id, f"zone={zone}", "-o", "json"],
                          capture_output=True, text=True)
    if done.returncode == 0:
        return json.loads(done.stdout)
    if is_gone(done.stderr + done.stdout):
        return None
    raise RuntimeError(f"reading {server_id} failed: {done.stderr.strip()}")


def disk_gb(server, zone):
    """The size of all a machine's disks in GB; a block volume's size is read from the block API, since the
    machine's own record leaves it empty."""
    total = 0
    for volume in (server.get("volumes") or {}).values():
        size = volume.get("size")
        if size is None and volume.get("volume_type") == "sbs_volume":
            size = (scw("block", "volume", "get", volume["id"], f"zone={zone}") or {}).get("size")
        total += size or 0
    return total / 1e9


def disk_and_address_euros(server, gb, now):
    """What a machine's `gb` of disks and its addresses cost from its creation to `now`: Scaleway bills each by the
    started hour, whether the machine ran or not (the October 2026 bill against the audit trail's lifetimes)."""
    created = datetime.datetime.fromisoformat(server["creation_date"].replace("Z", "+00:00")).timestamp()
    hours = math.ceil(max(now - created, 1.0) / 3600)
    addresses = len(server.get("public_ips") or []) or (1 if server.get("public_ip") else 0)
    return hours * (gb * DISK_EUROS_A_GB_HOUR + addresses * ADDRESS_EUROS_AN_HOUR)


def record_disk_and_address(server, gb, now):
    """Write a deleted machine's disks and addresses to the cloud ledger, which counts only its machine time: the
    bill's second and third largest lines after the cards (block storage EUR 71, addresses EUR 37 in October)."""
    import ledger

    euros = disk_and_address_euros(server, gb, now)
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    ledger.record({"started": started, "batch": f"disk-and-address-{server['id']}", "kind": "disk-and-address",
                   "who": "scaleway.delete", "name": server.get("name"), "type": server.get("commercial_type"),
                   "machines": [], "attempts": [], "machine_minutes": 0.0, "euros": euros})


def allow_key(project, name, public_key):
    """Put the runner's public ssh key on the project's key list, once; Scaleway's images let in
    only the keys on that list, and ignore a key sent in the first-boot file."""
    listed = scw("iam", "ssh-key", "list", f"project-id={project}") or []
    if not any(key["public_key"].split()[:2] == public_key.split()[:2] for key in listed):
        scw("iam", "ssh-key", "create", f"name={name}", f"public-key={public_key}",
            f"project-id={project}")


def create(project, offer, name, tags, disk_gb):
    """Rent and start one machine of `offer`: (its id, None), or (None, Scaleway's reason) when refused,
    as when the zone is out of stock or the quota is used up. The ledger's started line (ledger.rent_started, its run
    read from batch.rent's `<run>-<number>` name, its deadline from the `deadline=` tag) is written before the order is
    sent, and a refused order writes its refused line (ledger.rent_refused). It is written here, not in
    batch.rent: the pixal rows declare batch.py (Stage.files), and an edit there re-keys them in every place."""
    machine_type, zone = offer.type, offer.zone
    image = IMAGES["gpu" if cards(offer.machine_class) else "cpu"]
    import ledger

    deadline = next((float(tag.split("=", 1)[1]) for tag in tags if tag.startswith("deadline=")), None)
    ledger.rent_started(name.rsplit("-", 1)[0], name, {"type": machine_type, "zone": zone,
                                                       "class": offer.machine_class, "price": offer.price}, deadline)
    before = loose(project, zone)
    done = subprocess.run(
        ["scw", "instance", "server", "create", f"project-id={project}", f"zone={zone}",
         f"type={machine_type}", f"image={image}", f"name={name}", "ip=ipv4",
         f"root-volume=sbs:{disk_gb}GB",
         *[f"tags.{index}={tag}" for index, tag in enumerate([TAG, *tags])], "-o", "json"],
        capture_output=True, text=True)
    if done.returncode != 0:
        ledger.rent_refused(name, done.stderr.strip()[:300])
        delete_left_by_refusal(project, zone, name)
        delete_loose_left_by_refusal(project, zone, name, before, disk_gb)
        return None, done.stderr.strip()[:300]
    server = json.loads(done.stdout)
    server_id = server["id"]
    try:
        quarantine_bad_address(project, server, zone)
    except Exception as error:  # noqa: BLE001 - a machine left on a bad address is deleted, the next offer tried
        delete(server_id, zone)  # its disk-and-address row closes the started line
        return None, f"its address could not be swapped off a quarantined one ({error}); deleted"[:300]
    return server_id, None


def delete_left_by_refusal(project, zone, name):
    """Delete the machine a refused order made anyway: an order answered with HTTP 500 had still made it (masks-...-1 in fr-par-1, 2026-10-22: refused at 07:27:31, there since 07:27:04, stopped, never watched). Only
    a machine of the project's own, with the runner's tag and this exact name, in this zone; the names a run's slot
    takes are its own, and a slot whose order was refused holds no machine."""
    servers = scw("instance", "server", "list", f"project-id={project}", f"zone={zone}", f"name={name}") or []
    for server in servers:
        if server.get("name") == name and server.get("project") == project and TAG in (server.get("tags") or []):
            delete(server["id"], zone)


def loose(project, zone):
    """{(kind, id)} of the project's addresses and disks in `zone` attached to nothing."""
    return ({("address", found[0]) for found in leftover_addresses(project, (zone,))}
            | {("disk", found[0]) for found in leftover_disks(project, (zone,))})


def delete_loose_left_by_refusal(project, zone, name, before, gb):
    """Delete the address and disk a refused order made and no machine took (loose now, not `before` the order, and
    still loose LOOSE_SETTLE_SECONDS later), each billed by the started hour until deleted; their euros go to the
    ledger as the order's disk-and-address line, so the run counts them."""
    left = loose(project, zone) - before
    if left:
        time.sleep(LOOSE_SETTLE_SECONDS)
        left &= loose(project, zone)
    for kind, item_id in sorted(left):
        (delete_address if kind == "address" else delete_disk)(item_id, zone)
    if left:
        import ledger
        addresses = sum(kind == "address" for kind, _ in left)
        euros = addresses * ADDRESS_EUROS_AN_HOUR + (gb * DISK_EUROS_A_GB_HOUR if len(left) > addresses else 0.0)
        ledger.record({"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "batch": f"disk-and-address-{name}-refused", "kind": "disk-and-address",
                       "who": "scaleway.create", "name": name, "machines": [], "attempts": [],
                       "machine_minutes": 0.0, "euros": euros})


def quarantine_bad_address(project, server, zone):
    """When the new machine (`server`, as its create answered) got an address in BAD_ADDRESSES: a fresh address
    attached to it first, then the bad one detached and kept in the project, tagged QUARANTINED with its reason, so
    Scaleway never hands it to us again. Each address's own project is checked before it is touched."""
    server_id = server["id"]
    given = {ip["id"]: ip for ip in [*(server.get("public_ips") or []), server.get("public_ip") or {}] if ip.get("id")}
    bad = [ip for ip in given.values() if ip.get("address") in BAD_ADDRESSES]
    if not bad:
        return
    scw("instance", "ip", "create", f"project-id={project}", f"zone={zone}", "type=routed_ipv4",
        f"server={server_id}", f"tags.0={TAG}")
    for ip in bad:
        held = scw("instance", "ip", "get", ip["id"], f"zone={zone}") or {}
        if (held.get("ip") or held).get("project") != project:  # `ip get` answers {"ip": {...}}
            raise RuntimeError(f"address {ip['address']} is not the project's own; left alone")
        scw("instance", "ip", "detach", ip["id"], f"zone={zone}")
        scw("instance", "ip", "update", ip["id"], f"zone={zone}", f"tags.0={QUARANTINED}",
            f"tags.1=reason={BAD_ADDRESSES[ip['address']]}")


def start_if_stopped(server_id, zone):
    """Start the machine if it is stopped; Scaleway's reason when that is refused, else None.

    An order for many machines at once leaves most of them stopped: the start that comes with
    the order fails while a start asked for a moment later works (28 of 32 on 2026-09-29, and a
    probe in fr-par-2 started on the first try by hand). A zone truly out of cards refuses with
    "out of stock", and asking again later may still get one.
    """
    if scw("instance", "server", "get", server_id, f"zone={zone}")["state"] != "stopped":
        return None
    done = subprocess.run(["scw", "instance", "server", "start", server_id, f"zone={zone}"],
                          capture_output=True, text=True)
    return None if done.returncode == 0 else (done.stderr.strip().splitlines() or ["?"])[0]


def retag(server_id, zone, tags):
    """Give one of the runner's machines new tags (the runner's TAG kept first): a parked machine is held by the
    process that will delete it, and a taken one by the run that took it (park.py)."""
    scw("instance", "server", "update", server_id, f"zone={zone}",
        *[f"tags.{index}={tag}" for index, tag in enumerate([TAG, *tags])])


def address(server_id, zone):
    """The machine's public IPv4 address, or None while it has none."""
    server = scw("instance", "server", "get", server_id, f"zone={zone}")
    for ip in server.get("public_ips") or []:
        if ip.get("family") == "inet":
            return ip["address"]
    return (server.get("public_ip") or {}).get("address")


def ours(project):
    """Every machine in the project the runner rented, in every zone: id, zone, name and tags."""
    found = []
    for zone in rent_zones():
        servers = scw("instance", "server", "list", f"project-id={project}", f"zone={zone}",
                      f"tags.0={TAG}")
        # Each machine's own project is checked, not only the filter: a list filter that silently
        # does not apply returns every project's resources, and the organisation holds another
        # company's production next to these (two of its addresses were lost that way, 2026-09-29).
        found += [(server["id"], zone, server["name"], server.get("tags") or [])
                  for server in servers or []
                  if TAG in (server.get("tags") or []) and server.get("project") == project]
    return found


def leftover_addresses(project, zones=None):
    """The project's public addresses attached to no machine, in `zones` (every zone by default): (id, zone, address).

    A machine that deleted itself (self_delete.py) leaves its address behind.
    """
    found = []
    for zone in zones or rent_zones():
        for address in scw("instance", "ip", "list", f"project-id={project}", f"zone={zone}") or []:
            if (address.get("project") == project and not address.get("server")
                    and QUARANTINED not in (address.get("tags") or [])):  # held so it is never given to us again
                found.append((address["id"], zone, address["address"]))
    return found


def leftover_disks(project, zones=None):
    """The project's block disks attached to nothing, in `zones` (every zone by default): (id, zone, name).

    A machine that deleted itself leaves its disk behind.
    """
    found = []
    for zone in zones or rent_zones():
        for disk in scw("block", "volume", "list", f"project-id={project}", f"zone={zone}") or []:
            if disk.get("project_id") == project and not disk.get("references"):
                found.append((disk["id"], zone, disk["name"]))
    return found


def delete_address(address_id, zone):
    deleted_unless_gone("instance", "ip", "delete", address_id, f"zone={zone}")


def delete_disk(disk_id, zone):
    deleted_unless_gone("block", "volume", "delete", disk_id, f"zone={zone}")


def deleted_unless_gone(*arguments):
    """One `scw` delete; one that fails because the item is already gone (another run's sweep took it first) is
    done, any other failure raises."""
    try:
        scw(*arguments)
    except subprocess.CalledProcessError as failed:
        if not is_gone(f"{failed.stderr or ''}{failed.stdout or ''}"):
            raise


def is_gone(text):
    """True when Scaleway's answer says the item does not exist."""
    return any(gone in text.lower() for gone in ("not found", "cannot find"))


def delete(server_id, zone):
    """Stop and delete one machine with its disk and address; True if it was there to delete. What its disk and
    address cost is written to the ledger (record_disk_and_address).

    A machine already shutting down refuses both; wait for it to finish, then delete what is left.
    """
    server = server_record(server_id, zone)
    if server is None:
        return False
    try:
        gb = disk_gb(server, zone)
        deleted = terminate(server_id, zone)
    except (RuntimeError, subprocess.CalledProcessError):
        # Two sweeps deleting one leftover at once (surfaces-bake@wreck, 2026-10-13: "Failed to detach block
        # volume ... volume_id does not respect constraint", the machine and its volume gone a moment later): the
        # other one deleted it and wrote its ledger line, so it is gone, not this call's to count.
        if gone_after_failure(server_id, zone):
            return False
        raise
    if deleted:
        record_disk_and_address(server, gb, time.time())
    return deleted


def gone_after_failure(server_id, zone):
    """True when the machine no longer exists, read again up to GONE_TRIES times 10 s apart (a delete under way
    elsewhere takes a moment to finish)."""
    for attempt in range(GONE_TRIES):
        if server_record(server_id, zone) is None:
            return True
        if attempt < GONE_TRIES - 1:
            time.sleep(10)
    return False


def terminate(server_id, zone):
    """Stop and delete one machine with its disk and address; True if it was there to delete."""
    for _ in range(STOPPING_TRIES):
        done = subprocess.run(["scw", "instance", "server", "terminate", server_id, f"zone={zone}",
                               "with-ip=true", "with-block=true"], capture_output=True, text=True)
        if "invalid state 'stopping'" not in done.stderr:
            break
        time.sleep(10)
    if done.returncode == 0:
        return True
    if is_gone(done.stderr + done.stdout):
        return False
    if "invalid state 'stopped'" in done.stderr:
        # A machine the zone had no card to start stays stopped, and terminate refuses a stopped
        # one (17 of 20 on 2026-09-29); delete takes it with its disk and address instead.
        done = subprocess.run(["scw", "instance", "server", "delete", server_id, f"zone={zone}",
                               "with-ip=true", "with-volumes=all"], capture_output=True, text=True)
        if done.returncode == 0:
            return True
        if is_gone(done.stderr + done.stdout):
            return False  # it went while the terminate was refused (another run's sweep, its own self-delete)
    raise RuntimeError(f"deleting {server_id} failed: {done.stderr.strip()}")


# The container path (tools/cloud/): one private image registry and one bucket in the project, region fr-par, and the
# key the runtime reaches both with. Their names carry the project's name, never its id.
REGION = "fr-par"
REGISTRY_NAMESPACE = os.environ.get("SCORE_REGISTRY_NAMESPACE", f"score-{PROJECT_NAME}")
BUCKET = os.environ.get("SCORE_STORE_BUCKET", f"score-{PROJECT_NAME}-cache")
# The secret holding {"access_key", "secret_key"} of an IAM application that may use the project's object storage
# and container registry and nothing else; made by make_runtime_key the first time it is missing.
RUNTIME_KEY_SECRET = "score-cloud-runtime-key"
RUNTIME_APPLICATION = "score-cloud-runtime"
RUNTIME_PERMISSIONS = ("ObjectStorageFullAccess", "ContainerRegistryFullAccess")
# Scaleway's registry takes any user name with the key's secret half as the password.
REGISTRY_USER = "nologin"


def registry():
    """The project's private image registry: its endpoint and the runtime key to log in with."""
    key = runtime_key(account())
    return {"endpoint": registry_namespace(account()), "username": REGISTRY_USER, "password": key["secret_key"]}


def registry_namespace(project):
    """The endpoint (<host>/<namespace>) of the project's private registry namespace, made if missing. A namespace is
    taken only when its own record names the project, and a public one is refused."""
    listed = scw("registry", "namespace", "list", f"region={REGION}", f"project-id={project}",
                 f"name={REGISTRY_NAMESPACE}") or []
    found = [space for space in listed
             if space["name"] == REGISTRY_NAMESPACE and space.get("project_id") == project]
    if not found:
        found = [scw("registry", "namespace", "create", f"name={REGISTRY_NAMESPACE}", f"project-id={project}",
                     f"region={REGION}", "is-public=false")]
    if found[0].get("is_public"):
        raise SystemExit(f"the registry namespace {REGISTRY_NAMESPACE} is public; the job images must stay private")
    return found[0]["endpoint"]


def object_store():
    """The project's bucket for the container path, made if missing, with the runtime key to reach it."""
    key = runtime_key(account())
    store = {"endpoint": f"https://s3.{REGION}.scw.cloud", "region": REGION, "bucket": BUCKET,
             "access_key": key["access_key"], "secret_key": key["secret_key"]}
    make_bucket(store)
    return store


def make_bucket(store):
    """Make the store's bucket if it is not there. The runtime key's default project is this project, so a bucket it
    makes lands there; a bucket name held by anyone else is refused (403) and stops here."""
    import boto3
    import botocore.exceptions

    client = boto3.client("s3", endpoint_url=store["endpoint"], region_name=store["region"],
                          aws_access_key_id=store["access_key"], aws_secret_access_key=store["secret_key"])
    try:
        client.head_bucket(Bucket=store["bucket"])
    except botocore.exceptions.ClientError as error:
        if error.response["Error"]["Code"] not in ("404", "NoSuchBucket"):
            raise SystemExit(f"the bucket {store['bucket']} is not ours to use ({error.response['Error']['Code']})")
        try:
            client.create_bucket(Bucket=store["bucket"], ACL="private")
        except client.exceptions.BucketAlreadyOwnedByYou:
            pass  # a retried create whose first try went through (seen on the first make, 2026-10-09)


def runtime_key(project):
    """The runtime key, {"access_key", "secret_key"}, from its secret; made first if the project has none."""
    listed = scw("secret", "secret", "list", f"region={REGION}", f"project-id={project}",
                 f"name={RUNTIME_KEY_SECRET}") or []
    if not any(item["name"] == RUNTIME_KEY_SECRET and item.get("project_id") == project for item in listed):
        make_runtime_key(project)
    return json.loads(secret(RUNTIME_KEY_SECRET))


def runtime_application():
    """The id of the IAM application the runtime key belongs to, made if missing."""
    listed = scw("iam", "application", "list", f"name={RUNTIME_APPLICATION}") or []
    found = [application for application in listed if application["name"] == RUNTIME_APPLICATION]
    if found:
        return found[0]["id"]
    return scw("iam", "application", "create", f"name={RUNTIME_APPLICATION}",
               "description=SCORE container runtime: the project's object storage and registry only")["id"]


def allow_runtime_application(application, project):
    """Give the application the project's object storage and registry, scoped to the project alone, once."""
    listed = scw("iam", "policy", "list", f"application-ids.0={application}") or []
    if any(policy["name"] == RUNTIME_APPLICATION for policy in listed):
        return
    scw("iam", "policy", "create", f"name={RUNTIME_APPLICATION}", f"application-id={application}",
        f"rules.0.project-ids.0={project}",
        *[f"rules.0.permission-set-names.{index}={name}" for index, name in enumerate(RUNTIME_PERMISSIONS)])


def make_runtime_key(project):
    """Make the runtime key (an API key of the runtime application, its default project this one) and keep it only in
    the secret RUNTIME_KEY_SECRET; it is never printed or left on disk."""
    application = runtime_application()
    allow_runtime_application(application, project)
    made = scw("iam", "api-key", "create", f"application-id={application}", f"default-project-id={project}",
               "description=SCORE container runtime")
    value = json.dumps({"access_key": made["access_key"], "secret_key": made["secret_key"]})
    held = scw("secret", "secret", "create", f"name={RUNTIME_KEY_SECRET}", f"project-id={project}",
               f"region={REGION}")
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "value"
        path.touch(mode=0o600)
        path.write_text(value)
        scw("secret", "version", "create", held["id"], f"region={REGION}", f"data=@{path}")
