"""The Scaleway backend of the cloud layer (`../provider.py` says what a backend gives), through the logged-in `scw`
command. Scaleway is the backend the framework runs on today.

Every call names the project and the zone itself. The CLI's default profile may point at another project, and it is
never changed from here, so leaving either out could rent a machine on the wrong account. The "account" of the
provider interface is a Scaleway project here.
"""
import base64
import functools
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

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
    "cpu-32c-128gb": ("POP2-32C-128G",),
    "cpu-32c-64gb": ("POP2-HC-32C-64G",),
    "cpu-32c-256gb": ("POP2-HM-32C-256G",),
    "cpu-16c-64gb": ("POP2-16C-64G",),
    "cpu-16c-128gb": ("POP2-HM-16C-128G",),
}
# How many machines of a class the project may hold at once, where Scaleway granted a quota (2026-10-08: H100-1-80G 20,
# L4-1-24G 50, L40S-1-48G 10, across fr-par-1, fr-par-2 and pl-waw-2). Stock is still the real limit; a class not
# listed has the provider's default quota, and a rent past any quota is refused and the next offer taken.
QUOTAS = {"gpu-80gb": 20, "gpu-24gb": 50, "gpu-48gb": 10}
# Minutes in each unit Scaleway's price list prices a machine by: the cards by the minute, the
# processor machines (POP2) by the hour (2026-10-05).
PER_UNIT_MINUTES = {"minute": 1, "hour": 60}
# Scaleway's words for a type's stock, best first.
STOCK_ORDER = {"available": 0, "scarce": 1, "shortage": 2}
# Every machine the runner rents carries this tag, so a sweep can find what a crashed run left.
TAG = "farm-factory-batch"
# The zones that rent graphics cards (2026-09-29).
ZONES = ("pl-waw-2", "fr-par-2", "fr-par-1")
# How many times, 10 s apart, a delete waits out a machine that is still shutting down.
STOPPING_TRIES = 12


def scw(*arguments):
    """Run one `scw` command and return its JSON answer, failing loudly."""
    done = subprocess.run(["scw", *arguments, "-o", "json"], check=True,
                          capture_output=True, text=True)
    return json.loads(done.stdout) if done.stdout.strip() else None


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


def offers(classes):
    """Every place a machine of one of `classes` can be rented: an Offer for each type and zone that sells it."""
    found = []
    for zone in ZONES:
        listed = {server["name"]: server.get("availability") for server in scw("instance", "server-type", "list",
                                                                                 f"zone={zone}")}
        for machine_class in classes:
            for order, machine_type in enumerate(CLASSES.get(machine_class, ())):
                if machine_type not in listed:
                    continue
                euros = price(machine_type, zone)[0]
                found.append(Offer(euros / max(1, cards(machine_class)), STOCK_ORDER.get(listed[machine_type], 3),
                                   machine_type, zone, euros, machine_class, order, listed[machine_type]))
    return found


def month_spend(project):
    """What Scaleway has billed the project so far this month, in euros. It lags by hours."""
    total = 0.0
    for line in scw("billing", "consumption", "list", f"project-id={project}") or []:
        value = line.get("value") or {}
        total += value.get("units", 0) + value.get("nanos", 0) / 1e9
    return total


def allow_key(project, name, public_key):
    """Put the runner's public ssh key on the project's key list, once; Scaleway's images let in
    only the keys on that list, and ignore a key sent in the first-boot file."""
    listed = scw("iam", "ssh-key", "list", f"project-id={project}") or []
    if not any(key["public_key"].split()[:2] == public_key.split()[:2] for key in listed):
        scw("iam", "ssh-key", "create", f"name={name}", f"public-key={public_key}",
            f"project-id={project}")


def create(project, offer, name, tags, disk_gb):
    """Rent and start one machine of `offer`: (its id, None), or (None, Scaleway's reason) when refused,
    as when the zone is out of stock or the quota is used up."""
    machine_type, zone = offer.type, offer.zone
    image = IMAGES["gpu" if cards(offer.machine_class) else "cpu"]
    done = subprocess.run(
        ["scw", "instance", "server", "create", f"project-id={project}", f"zone={zone}",
         f"type={machine_type}", f"image={image}", f"name={name}", "ip=ipv4",
         f"root-volume=sbs:{disk_gb}GB",
         *[f"tags.{index}={tag}" for index, tag in enumerate([TAG, *tags])], "-o", "json"],
        capture_output=True, text=True)
    if done.returncode == 0:
        return json.loads(done.stdout)["id"], None
    return None, done.stderr.strip()[:300]


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
    for zone in ZONES:
        servers = scw("instance", "server", "list", f"project-id={project}", f"zone={zone}",
                      f"tags.0={TAG}")
        # Each machine's own project is checked, not only the filter: a list filter that silently
        # does not apply returns every project's resources, and the organisation holds another
        # company's production next to these (two of its addresses were lost that way, 2026-09-29).
        found += [(server["id"], zone, server["name"], server.get("tags") or [])
                  for server in servers or []
                  if TAG in (server.get("tags") or []) and server.get("project") == project]
    return found


def leftover_addresses(project):
    """The project's public addresses attached to no machine, in every zone: (id, zone, address).

    A machine that deleted itself (self_delete.py) leaves its address behind.
    """
    found = []
    for zone in ZONES:
        for address in scw("instance", "ip", "list", f"project-id={project}", f"zone={zone}") or []:
            if address.get("project") == project and not address.get("server"):
                found.append((address["id"], zone, address["address"]))
    return found


def leftover_disks(project):
    """The project's block disks attached to nothing, in every zone: (id, zone, name).

    A machine that deleted itself leaves its disk behind.
    """
    found = []
    for zone in ZONES:
        for disk in scw("block", "volume", "list", f"project-id={project}", f"zone={zone}") or []:
            if disk.get("project_id") == project and not disk.get("references"):
                found.append((disk["id"], zone, disk["name"]))
    return found


def delete_address(address_id, zone):
    scw("instance", "ip", "delete", address_id, f"zone={zone}")


def delete_disk(disk_id, zone):
    scw("block", "volume", "delete", disk_id, f"zone={zone}")


def delete(server_id, zone):
    """Stop and delete one machine with its disk and address; True if it was there to delete.

    A machine already shutting down refuses both; wait for it to finish, then delete what is left.
    """
    for _ in range(STOPPING_TRIES):
        done = subprocess.run(["scw", "instance", "server", "terminate", server_id, f"zone={zone}",
                               "with-ip=true", "with-block=true"], capture_output=True, text=True)
        if "invalid state 'stopping'" not in done.stderr:
            break
        time.sleep(10)
    if done.returncode == 0:
        return True
    if any(gone in (done.stderr + done.stdout).lower() for gone in ("not found", "cannot find")):
        return False
    if "invalid state 'stopped'" in done.stderr:
        # A machine the zone had no card to start stays stopped, and terminate refuses a stopped
        # one (17 of 20 on 2026-09-29); delete takes it with its disk and address instead.
        done = subprocess.run(["scw", "instance", "server", "delete", server_id, f"zone={zone}",
                               "with-ip=true", "with-volumes=all"], capture_output=True, text=True)
        if done.returncode == 0:
            return True
        if any(gone in (done.stderr + done.stdout).lower() for gone in ("not found", "cannot find")):
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
