"""The few Scaleway calls the batch runner makes, through the logged-in `scw` command.

Every call names the project and the zone itself. The CLI's default profile points at another
project, and it is never changed from here, so leaving either out would rent a machine on the
wrong account.
"""
import json
import subprocess

# The project the owner set aside for this game's machines; looked up by name, so no account
# id sits in the repo.
PROJECT_NAME = "farm-factory"
# Ubuntu 24.04 with the NVIDIA driver and CUDA runtime, Scaleway's own GPU image.
IMAGE = "ubuntu_noble_gpu_os_13_nvidia"
# Every machine the runner rents carries this tag, so a sweep can find what a crashed run left.
TAG = "farm-factory-batch"
# The zones that rent graphics cards (2026-09-29).
ZONES = ("pl-waw-2", "fr-par-2", "fr-par-1")


def scw(*arguments):
    """Run one `scw` command and return its JSON answer, failing loudly."""
    done = subprocess.run(["scw", *arguments, "-o", "json"], check=True,
                          capture_output=True, text=True)
    return json.loads(done.stdout) if done.stdout.strip() else None


def project_id():
    """The id of the farm-factory project."""
    found = [project for project in scw("account", "project", "list", f"name={PROJECT_NAME}")
             if project["name"] == PROJECT_NAME]
    if len(found) != 1:
        raise SystemExit(f"expected one Scaleway project named {PROJECT_NAME}, found {len(found)}")
    return found[0]["id"]


def euros_per_minute(machine_type, zone):
    """What one minute of `machine_type` costs in `zone`, from Scaleway's price list."""
    sku = f"/instance/server/{machine_type.lower().replace('-', '_')}/{zone}"
    products = scw("product-catalog", "product", "list", "product-types.0=instance", f"zone={zone}")
    for product in products:
        if product["sku"] == sku:
            if product["unit_of_measure"]["unit"] != "minute":
                raise SystemExit(f"{sku} is priced per {product['unit_of_measure']['unit']}, "
                                 "not per minute; the caps assume minutes")
            price = product["price"]["retail_price"]
            return price["units"] + price["nanos"] / 1e9
    raise SystemExit(f"no price for {machine_type} in {zone}")


def stock(machine_type, zone):
    """Scaleway's word for how many `machine_type` are left in `zone`: available, scarce,
    shortage, or None where it is not sold."""
    for listed in scw("instance", "server-type", "list", f"zone={zone}"):
        if listed["name"] == machine_type:
            return listed.get("availability")
    return None


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


def create(project, machine_type, zone, name, tags, disk_gb):
    """Rent and start one machine: (its id, None), or (None, Scaleway's reason) when refused,
    as when the zone is out of stock or the quota is used up."""
    done = subprocess.run(
        ["scw", "instance", "server", "create", f"project-id={project}", f"zone={zone}",
         f"type={machine_type}", f"image={IMAGE}", f"name={name}", "ip=ipv4",
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
    """Stop and delete one machine with its disk and address; True if it was there to delete."""
    done = subprocess.run(["scw", "instance", "server", "terminate", server_id, f"zone={zone}",
                           "with-ip=true", "with-block=true"], capture_output=True, text=True)
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
    raise RuntimeError(f"deleting {server_id} failed: {done.stderr.strip()}")
