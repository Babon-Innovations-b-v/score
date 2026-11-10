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
import urllib.error
import math
import os
import pathlib
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "props"))  # tools/props, for the ledger's paths

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
    # Two H100s with 48 cores and 480 GB (the SXM pair has 32): level 1's every tuning body side by side, two threads
    # each, on one card (tools/cloud/level1, 2026-11-02); the second card idles, sold only with the cores.
    "gpu-80gb-x2-48c": ("H100-2-80G",),
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
# The read a self-delete key is checked with before any rent (self_delete_refusal).
SERVERS_URL = "https://api.scaleway.com/instance/v1/zones/{zone}/servers?per_page=1"
QUOTA_PAGE = 100
# What a machine's root disk (block storage, 5k IOPS) and public address cost, in euros a GB-hour and an
# address-hour, each billed by the started hour from the machine's creation (the October 2026 bill: EUR 31.87 for
# 245,140 GB-hours, EUR 15.80 for 3,160 address-hours).
DISK_EUROS_A_GB_HOUR = 0.00013
ADDRESS_EUROS_AN_HOUR = 0.005
# How many times, 10 s apart, a delete waits out a machine that is still shutting down or still being made.
STOPPING_TRIES = 12
# The terminate's refusals that pass once the machine is out of its state (2026-11-05: a delete of a machine the zone
# was still making, "Cannot modify the SBS volumes of an instance in the state SessionState.PROVISION", ended
# surfaces-bake@camp's whole call).
NOT_YET = ("invalid state 'stopping'", "in the state SessionState.PROVISION")
# How many times, 10 s apart, a failed delete reads the machine again to see whether another run deleted it.
GONE_TRIES = 3
# Seconds a refused order's new loose address or disk must stay loose before it is deleted: another order's own
# address is loose for a moment between the CLI making it and its machine taking it.
LOOSE_SETTLE_SECONDS = 15
# A failed read of the API (scw's verbs below) is asked again this many times in all, waiting 5, 10, 20, 40 s between.
READS = {"list", "get", "access-by-path"}
READ_TRIES = 5
READ_WAIT_SECONDS = 5.0


def image_identity():
    """What a job here runs on, for a kept job's content (kept.py): the machine images by name."""
    return json.dumps(IMAGES, sort_keys=True)


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
    """(type, zone) of every machine a run parked with time left (tools/cloud/park.py's records)."""
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


def self_delete_refusal(secret_key, zone):
    """Why a machine in `zone` could not delete itself with the self-delete key `secret_key`, or None when the key
    reads the zone's machines (a free read its policy allows, as self_delete.py's terminate needs). Fault of
    2026-11-02: a key the API answered 401 left an H100 idle 12.8 h after its launcher died with this PC."""
    import urllib.request

    request = urllib.request.Request(SERVERS_URL.format(zone=zone), headers={"X-Auth-Token": secret_key})
    try:
        with urllib.request.urlopen(request, timeout=30) as answer:
            answer.read()
        return None
    except urllib.error.HTTPError as refused:
        return f"Scaleway's instance API answers it {refused.code} {refused.reason}"
    except (urllib.error.URLError, OSError) as failed:
        return f"Scaleway's instance API could not be asked: {failed}"


def self_delete_key_refusal(zone):
    """Why the runner's self-delete key (batch.SELF_DELETE_KEY) would not let a machine in `zone` delete itself, or None
    when the provider takes it (self_delete_refusal, a free read). Here, not in batch.rent, as ledger.rent_started:
    the rough-model and pixal rows declare batch.py, and 52fdadda's check there re-keyed 307 paid rows (EUR 1,131)."""
    import batch

    try:
        secret = json.loads(batch.SELF_DELETE_KEY.read_text()).get("secret_key")
    except (OSError, ValueError, AttributeError) as unread:
        return f"{batch.SELF_DELETE_KEY} unreadable: {unread}"
    if not secret:
        return f"{batch.SELF_DELETE_KEY} holds no secret_key"
    why = self_delete_refusal(secret, zone)
    return f"{batch.SELF_DELETE_KEY}: {why}" if why else None


@functools.lru_cache(maxsize=None)
def zone_quotas():
    """{(machine type, zone): machines} the project's organisation may hold, read once a process (a free read). A
    type and zone it lists no quota for holds none (POP2-HC-64C-128G and POP2-64C-256G, 2026-10-23, until the owner's
    request for more is granted), so it is never ordered."""
    organization = scw("account", "project", "get", f"project-id={account()}")["organization_id"]
    found = {}
    try:
        pages = quota_pages(organization, scw("config", "get", "secret-key"))
    except urllib.error.HTTPError as refused:
        if refused.code != 403:
            raise
        # a key with no right to read quotas (the conductor's, 2026-10-24): order by stock alone, the provider refusing
        # a type over its quota as it refuses one out of stock
        print("scaleway: quotas not readable with this key (403): every type in stock is offered", file=sys.stderr)
        return None
    for quota in pages:
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
                if machine_type not in listed or (quotas is not None and not quotas.get((machine_type, zone))):
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


# The env1 cap's whole bill (the plan of 2026-11-09, B2): SCORE's usage on every project of the organisation. The
# projects SCORE owns count whole; babon's shared project counts but for babon's own services (its products below),
# and its machine, disk and address lines are split by the pool tag of what the watcher saw running there
# (tools/cloud/cap_watch): only what is proven babon's is taken off, so a line that cannot be split counts whole.
SCORE_PROJECTS = ("farm-factory", "score-conductor")
SHARED_PROJECT = "babon-platform"
# babon's own services in the shared project, by the bill's category (and Network's load balancers by product).
SHARED_OWN_CATEGORIES = ("Managed Databases", "Serverless", "BareMetal", "Observability", "Security and Identity",
                         "Containers")
SHARED_OWN_PRODUCTS = ("Loadbalancer", "Block Snapshot")
# Kapsule's tag on a node's machine naming its pool; pools named so are SCORE's (its card pools, the conductor's node,
# and every gate pool: the plan counts all gate lines as env1's, babon's own gate pushes too).
POOL_TAG = "pool-name="
SCORE_POOLS = ("score", "gate")
# Every zone a machine, disk or address of the organisation may stand in (the cap's read, every project).
ALL_ZONES = ("fr-par-1", "fr-par-2", "fr-par-3", "nl-ams-1", "nl-ams-2", "nl-ams-3", "pl-waw-1", "pl-waw-2",
             "pl-waw-3", "it-mil-1")
KAPSULE_REGIONS = ("fr-par", "nl-ams", "pl-waw")


class Unread(RuntimeError):
    """The whole bill or the live machines could not be read as they must be: the cap's watch fails closed on it."""


def euros_of(value):
    return (value or {}).get("units", 0) + (value or {}).get("nanos", 0) / 1e9


def consumption_all():
    """Scaleway's month-to-date bill of the whole organisation, no project filter: a line per project, product and
    zone, {project, project_id, category, product, sku, euros}. Unread when it answers nothing (an empty bill is a
    read that failed, never EUR 0)."""
    lines = [{"project": line.get("project_name") or line.get("project_id"), "project_id": line.get("project_id"),
              "category": line.get("category_name"), "product": line.get("product_name"), "sku": line.get("sku"),
              "euros": euros_of(line.get("value"))}
             for line in scw("billing", "consumption", "list") or []]
    if not lines:
        raise Unread("Scaleway's bill answered no line")
    return lines


def counted(line):
    """True for a bill line SCORE's usage is on: a SCORE project's every line, the shared project's but babon's own
    services; no other project's."""
    if line["project"] in SCORE_PROJECTS:
        return True
    if line["project"] != SHARED_PROJECT:
        return False
    return (line["category"] not in SHARED_OWN_CATEGORIES
            and not any(str(line["product"] or "").startswith(own) for own in SHARED_OWN_PRODUCTS))


def line_key(line):
    return f"{line['project']}|{line['sku']}"


def bill_all(last_whole=None):
    """The whole bill as the cap reads it: {whole (every line of every project), lines ({project|sku: euros} of the
    counted lines), projects ({name: id})}. Unread when it is empty or its whole is below `last_whole`, the whole the
    last kept read had: a bill only grows within its month, so a lower one is a read gone wrong (or a new month) and
    never a smaller spend."""
    lines = consumption_all()
    whole = sum(line["euros"] for line in lines)
    if last_whole is not None and whole < last_whole - 0.005:
        raise Unread(f"Scaleway's bill reads EUR {whole:.2f}, below the EUR {last_whole:.2f} last kept")
    found = {}
    for line in lines:
        if counted(line):
            found[line_key(line)] = found.get(line_key(line), 0.0) + line["euros"]
    return {"whole": round(whole, 4), "lines": {key: round(euros, 4) for key, euros in found.items()},
            "projects": {line["project"]: line["project_id"] for line in lines}}


def created_at(item):
    """When a machine or disk was made (seconds); 0 for one whose record says not (an address): counted from the
    cap's start then, never less."""
    stamp = item.get("creation_date") or item.get("created_at")
    return datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp() if stamp else 0.0


def euros_since(per_minute, unit_minutes, created, start, now):
    """What a thing priced `per_minute` (billed by `unit_minutes`) has cost from the later of its creation and `start`
    to `now`, each started billing unit counted whole (a processor machine's started hour)."""
    minutes = max(0.0, now - max(created, start)) / 60
    return math.ceil(minutes / unit_minutes) * unit_minutes * per_minute if minutes else 0.0


def owner_of(server, names):
    """'score' or 'babon' for a machine: a SCORE project's, or the shared project's in a pool SCORE_POOLS names, is
    SCORE's; any other machine of the shared project is babon's; None for any other project's."""
    project = names.get(server.get("project"))
    if project in SCORE_PROJECTS:
        return "score"
    if project != SHARED_PROJECT:
        return None
    pool = next((tag[len(POOL_TAG):] for tag in server.get("tags") or [] if tag.startswith(POOL_TAG)), "")
    return "score" if pool.startswith(SCORE_POOLS) else "babon"


def node_ids():
    """The machine id of every node of every Kubernetes cluster the organisation holds (Kapsule's provider id
    scaleway://instance/<zone>/<id>). Unread when a region cannot be read."""
    found = set()
    for region in KAPSULE_REGIONS:
        try:
            nodes = [node for cluster in scw("k8s", "cluster", "list", f"region={region}") or []
                     for node in scw("k8s", "node", "list", f"cluster-id={cluster['id']}", f"region={region}") or []]
        except subprocess.CalledProcessError as error:
            raise Unread(f"the clusters' nodes in {region} could not be read: {(error.stderr or '').strip()[-200:]}")
        found |= {node["provider_id"].rsplit("/", 1)[-1] for node in nodes if node.get("provider_id")}
    return found


def live_rate(start, now, names, nodes=None):
    """Every machine, disk and IPv4 address standing now in every project the bill names (`names`: {project id:
    name}), each SCORE's or babon's (owner_of; a disk or address by the machine it is on, a loose one of a SCORE
    project SCORE's and one of the shared project counted SCORE's: it fails closed): {id: {owner, kind, line (the bill
    line it is billed on), euros (from the later of its creation and `start` to `now`), per_hour}}. An address is
    billed apart from its machine (its own ipv4 line) but lives with it: it is counted from its machine's creation,
    a loose one (its record holds no creation) from `start`; a routed IPv6 is free and not metered (the bill's ipv6
    lines are EUR 0; 2026-11-10, the meter counted 1,027 node addresses, half of them IPv6, each from the cap's start:
    EUR 111 against the bill's EUR 4). Unread when a list cannot be read or a cluster node (node_ids, or `nodes`
    given) is missing from the machines listed: a meter blind to a running machine would let its cost pass unseen."""
    found, servers = {}, {}
    try:
        for zone in ALL_ZONES:
            for server in scw("instance", "server", "list", f"zone={zone}") or []:
                servers[server["id"]] = (server, zone)
    except subprocess.CalledProcessError as error:
        raise Unread(f"the machines could not be read: {(error.stderr or '').strip()[-200:]}")
    missing = (node_ids() if nodes is None else set(nodes)) - set(servers)
    if missing:
        raise Unread(f"{len(missing)} cluster node(s) are not among the machines listed ({sorted(missing)[:3]}): the "
                     "key reads too little to meter what runs")
    owners = {}
    for server_id, (server, zone) in servers.items():
        owner = owner_of(server, names)
        if owner is None:
            continue
        owners[server_id] = owner
        if server.get("state") == "stopped":
            continue  # a machine stopped off its host bills no machine time, only its disks ("stopped in place" bills)
        per_minute, unit = price(server["commercial_type"], zone)
        project = names[server["project"]]
        found[server_id] = {"owner": owner, "kind": "machine", "per_hour": round(per_minute * 60, 4),
                            "line": f"{project}|/instance/server/{server['commercial_type'].lower().replace('-', '_')}"
                                    f"/{zone}",
                            "euros": round(euros_since(per_minute, unit, created_at(server), start, now), 4)}
    for zone in ALL_ZONES:
        try:
            disks = scw("block", "volume", "list", f"zone={zone}") or []
            addresses = scw("instance", "ip", "list", f"zone={zone}") or []
        except subprocess.CalledProcessError as error:
            raise Unread(f"the disks or addresses in {zone} could not be read: {(error.stderr or '').strip()[-200:]}")
        for disk in disks:
            project = names.get(disk.get("project_id"))
            if project is None:
                continue
            held = [ref.get("product_resource_id") for ref in disk.get("references") or []]
            owner = next((owners[server] for server in held if server in owners), "score")
            per_hour = (disk.get("size") or 0) / 1e9 * DISK_EUROS_A_GB_HOUR
            found[disk["id"]] = {"owner": owner, "kind": "disk", "per_hour": round(per_hour, 5),
                                 "line": f"{project}|/storage/block/volume-low-latency-5k/{zone}",
                                 "euros": round(euros_since(per_hour / 60, 60, created_at(disk), start, now), 4)}
        for address in addresses:
            project = names.get(address.get("project"))
            if project is None or "ipv6" in str(address.get("type") or ""):
                continue
            owner = owners.get((address.get("server") or {}).get("id"), "score")
            machine = servers.get((address.get("server") or {}).get("id"))
            born = created_at(machine[0]) if machine else 0.0
            found[address["id"]] = {"owner": owner, "kind": "address", "per_hour": ADDRESS_EUROS_AN_HOUR,
                                    "line": f"{project}|/network/ipam/ipv4/{zone}",
                                    "euros": round(euros_since(ADDRESS_EUROS_AN_HOUR / 60, 60, born, start, now), 4)}
    return found


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
    batch.rent: the pixal rows declare batch.py (Stage.files), and an edit there re-keys them in every place. Before
    both, no machine is ordered with a self-delete key the provider refuses (self_delete_key_refusal; 2026-11-02: every
    terminate got 401 and an H100 sat idle 12.8 h): compute.Refused, naming the key and what the owner fixes."""
    machine_type, zone = offer.type, offer.zone
    refused_key = self_delete_key_refusal(zone)
    if refused_key:
        import batch

        raise batch.compute.Refused(f"a {machine_type} in {zone}: no machine is rented that could not delete itself; "
                                    f"the self-delete key {refused_key}; owner: a working self-delete key there")
    import batch

    batch.compute.cap_check(f"a {machine_type} in {zone}")  # the env1 cap, here and not in batch.rent (its rows' file)
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
    try:
        state = scw("instance", "server", "get", server_id, f"zone={zone}")["state"]
    except subprocess.CalledProcessError as error:
        # Unreadable after scw's own retries (a Warsaw L4, 2026-10-27): a refusal the caller waits out and then
        # deletes as a machine that did not start, never a crashed node with the machine left behind.
        return f"its state could not be read: {(error.stderr or '').strip()[-300:] or error}"
    if state != "stopped":
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
        if not any(words in done.stderr for words in NOT_YET):
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
# The run store's blobs (#74, score/store/offload): a bucket of their own in REGION, Scaleway's default class there
# (Multi-AZ, the owner's choice of 2026-11-02), versioning never turned on; made once by hand, never by the code.
RUN_STORE_BUCKET = os.environ.get("SCORE_RUN_STORE_BUCKET", f"score-{PROJECT_NAME}-store")
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
