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
ZONE = "pl-waw-2"
# Ubuntu 24.04 with the NVIDIA driver and CUDA runtime, Scaleway's own GPU image.
IMAGE = "ubuntu_noble_gpu_os_13_nvidia"
# Every machine the runner rents carries this tag, so a sweep can find what a crashed run left.
TAG = "farm-factory-batch"


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


def euros_per_minute(machine_type):
    """What one minute of `machine_type` costs in ZONE, from Scaleway's price list."""
    sku = f"/instance/server/{machine_type.lower().replace('-', '_')}/{ZONE}"
    products = scw("product-catalog", "product", "list", "product-types.0=instance", f"zone={ZONE}")
    for product in products:
        if product["sku"] == sku:
            if product["unit_of_measure"]["unit"] != "minute":
                raise SystemExit(f"{sku} is priced per {product['unit_of_measure']['unit']}, "
                                 "not per minute; the caps assume minutes")
            price = product["price"]["retail_price"]
            return price["units"] + price["nanos"] / 1e9
    raise SystemExit(f"no price for {machine_type} in {ZONE}")


def in_stock(machine_type):
    """Whether Scaleway says `machine_type` can be rented in ZONE right now."""
    for listed in scw("instance", "server-type", "list", f"zone={ZONE}"):
        if listed["name"] == machine_type:
            return listed.get("availability") == "available"
    return False


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


def create(project, machine_type, name, tags, disk_gb):
    """Rent and start one machine; its id."""
    server = scw("instance", "server", "create", f"project-id={project}", f"zone={ZONE}",
                 f"type={machine_type}", f"image={IMAGE}", f"name={name}", "ip=ipv4",
                 f"root-volume=sbs:{disk_gb}GB",
                 *[f"tags.{index}={tag}" for index, tag in enumerate([TAG, *tags])])
    return server["id"]


def address(server_id):
    """The machine's public IPv4 address, or None while it has none."""
    server = scw("instance", "server", "get", server_id, f"zone={ZONE}")
    for ip in server.get("public_ips") or []:
        if ip.get("family") == "inet":
            return ip["address"]
    return (server.get("public_ip") or {}).get("address")


def ours(project):
    """Every machine in the project the runner rented: id, name and tags."""
    servers = scw("instance", "server", "list", f"project-id={project}", f"zone={ZONE}",
                  f"tags.0={TAG}")
    return [(server["id"], server["name"], server.get("tags") or []) for server in servers or []
            if TAG in (server.get("tags") or [])]


def delete(server_id):
    """Stop and delete one machine with its disk and address; True if it was there to delete."""
    done = subprocess.run(["scw", "instance", "server", "terminate", server_id, f"zone={ZONE}",
                           "with-ip=true", "with-block=true"], capture_output=True, text=True)
    if done.returncode == 0:
        return True
    if "not found" in (done.stderr + done.stdout).lower():
        return False
    raise RuntimeError(f"deleting {server_id} failed: {done.stderr.strip()}")
