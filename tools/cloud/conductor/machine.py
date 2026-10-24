"""The conductor: one always-on Scaleway CPU machine of our own that holds the store, the design, the ledgers, the
dashboard home and the runner, with sync, the listener, resume, prepare and every free step (the owner's PC keeps a
browser). This module is the machine as code, driving the scw CLI as tools/cloud/k8s/clusters/scaleway.py does:

    python3 tools/cloud/conductor/machine.py up [--dry]     # make or update everything (costs money; the owner's)
    python3 tools/cloud/conductor/machine.py status         # the server, its size, its IP, volumes, last health
    python3 tools/cloud/conductor/machine.py grow|shrink    # the size function: batch size, or idle size
    python3 tools/cloud/conductor/machine.py stop           # power off: the owner's hard stop, from his PC
    python3 tools/cloud/conductor/machine.py move [--dry]   # the store's one-time move from this PC (the owner's)
    python3 tools/cloud/conductor/machine.py down [--with-data]   # delete all but the data volume and backup bucket
    python3 tools/cloud/conductor/machine.py price          # per month, from Scaleway's product catalog
    python3 tools/cloud/conductor/machine.py dry            # free: cloud-init schema, the units, `up --dry`

What `up` makes, in the project named SCORE_CONDUCTOR_PROJECT (default score-conductor, looked up by name, never
written down), zone fr-par-2 (SCORE_CONDUCTOR_ZONE): a security group (inbound tcp/22 only, outbound open), a 20 GB
SBS root volume, a 100 GB SBS 5K data volume (mounted at /home/score/.farm-factory-props, so PROPS_HOME keeps its
default), one flexible IPv4, a POP2-HM-2C-16G server named and tagged score-conductor (never farm-factory-batch, so
the runner's leftover sweeps cannot touch it), protected from deletion, with cloud-init.yaml as its user-data; the
backup bucket (SCORE_CONDUCTOR_BUCKET, default score-conductor-backup, nl-ams, versioning on, non-current versions
kept 30 days: lifecycle.json); and the Serverless Function score-conductor-size (size_function/). Then, over ssh with
the owner's key, it pipes the conductor's one credential (a scoped Scaleway IAM API key: read by name from the secret
score-conductor-key in the conductor's own project, which prepare.sh fills and only the owner's credential may read,
else typed by the owner; never in user-data, the repository or a file on this PC) into
/home/score/.config/scw/config.yaml at mode 600, and the conductor's env file (~/.config/score/dashboard.env: no
secret, the sync URL and owner from the owner's own env file) beside it, and runs boot.sh's user part.

`up` and `move` are the owner's: they refuse in an agent's process (the store's agent markers, score/store
AGENT_MARKERS) unless the owner's yes to the switch is recorded and open for that step
(score/store/backup/conductor_yes.py: asked in a Claude Code session with its question tool, his answer and the
question quoted). Under that yes they use a one-off ssh key without a passphrase that lives only in memory
(ONCE_KEY, /dev/shm), made by `up` and put in the server's cloud-init, since an agent cannot type a passphrase; the
move ends by taking that key off the server and deleting it. What this gives up while the key lives (from up to the
move's end): any process on this PC, an agent's included, can read it and open a full shell on the conductor past the
agents' door. After the move nobody holds a full shell (the agents' key, when given, reaches only the door); a later
one needs `down` (the data volume kept) and `up` again.

Every scw call names its zone or region, and every create or list names the project; a resource is used or deleted
only after its own record's project_id is checked. The owner's CLI profile may point at another project: it is
never changed and never relied on.

The conductor's key may: Instances in the batch project, read Secret Manager, Object Storage for the job bucket and
the backup bucket, read billing consumption, invoke the size function, and read the organisation's projects (so a
name finds its id). The size function's own key (the secret score-conductor-size-key, JSON {access_key,
secret_key}) may change Instances in the conductor's project and read the backup bucket. Both are made by prepare.sh, with the
secrets the conductor reads.

Unchecked until the first `up`, which needs the owner's yes: that Scaleway allows POP2-HM-2C-16G <-> POP2-HM-16C-128G
on a powered-off block-only server and how long the round trip takes (refused: a fixed POP2-HM-8C-64G with
--oversubscribe instead); the SBS data volume's device path (/dev/disk/by-id/scsi-0SCW_sbs_volume-<id>); the
lifecycle JSON's shape for `scw object bucket-lifecycle create`.
"""
import argparse
import base64
import getpass
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
CLOUD = REPO / "tools" / "cloud"
sys.path.insert(0, str(HERE / "size_function"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(CLOUD.parent / "props"))  # tools/props: the ledger reads paths
sys.path.insert(0, str(CLOUD))

import ledger  # noqa: E402
import s3  # noqa: E402
from score.store import AGENT_MARKERS, PROPS_HOME, Store  # noqa: E402
from score.store.backup import conductor_yes  # noqa: E402

PROJECT_NAME = os.environ.get("SCORE_CONDUCTOR_PROJECT", "score-conductor")
# The batch project (the runner's machines), and the project whose Secret Manager holds the secrets, by name.
BATCH_PROJECT_NAME = os.environ.get("SCORE_SCALEWAY_PROJECT", "farm-factory")
SECRETS_PROJECT_NAME = os.environ.get("SCORE_SECRETS_PROJECT", BATCH_PROJECT_NAME)
SECRETS_REGION = "fr-par"
ZONE = os.environ.get("SCORE_CONDUCTOR_ZONE", "fr-par-2")
REGION = ZONE.rsplit("-", 1)[0]
NAME = TAG = "score-conductor"
BATCH_TAG = "farm-factory-batch"  # the runner's machines' tag, which its leftover sweeps delete by: never ours
IDLE_TYPE, BATCH_TYPE = "POP2-HM-2C-16G", "POP2-HM-16C-128G"
CHEAPER_BATCH_TYPE, FIXED_TYPE = "POP2-16C-64G", "POP2-HM-8C-64G"
IMAGE = "ubuntu_noble"
ROOT_GB, DATA_GB, IOPS = 20, 100, 5000
DATA_NAME = "score-conductor-data"
DATA_DEVICE = "/dev/disk/by-id/scsi-0SCW_sbs_volume-{}"
BUCKET = os.environ.get("SCORE_CONDUCTOR_BUCKET", "score-conductor-backup")
BUCKET_REGION = "nl-ams"
# The store's restic repository (score/store/backup) under restic/ in the backup bucket; the health record beside it.
BACKUP_REPO = f"s3:https://s3.{BUCKET_REGION}.scw.cloud/{BUCKET}/restic"
FUNCTION = "score-conductor-size"
FUNCTION_RUNTIME = "python312"
SIZE_TOKEN_SECRET, SIZE_KEY_SECRET = "score-conductor-size-token", "score-conductor-size-key"
# The conductor's own key, JSON {access_key, secret_key}, in the conductor's own project (prepare.sh): not the secrets
# project, whose secrets the conductor's key reads, so only the owner's credential reads it.
CONDUCTOR_KEY_SECRET = "score-conductor-key"
# The one-off ssh key an agent's process uses under the owner's yes: in memory only, gone at reboot or the move's end.
ONCE_KEY = pathlib.Path("/dev/shm/score-conductor-once")
# Where the move sets this PC's home aside, read-only, once the store is on the conductor.
PC_FINAL_HOME = PROPS_HOME.with_name(f"{PROPS_HOME.name}.pc-final")
SCORE_UID = 1100
SCORE_HOME = "/home/score"
# The conductor's sizes as score/conductor reads them (score.conductor.machine): piped by `up` to RECORD_PATH, merged
# into $PROPS_HOME/machine.json by the move (score/store/backup migrate --onto-conductor), which makes it a conductor.
SIZES = {"zone": ZONE, "idle_type": IDLE_TYPE, "batch_type": BATCH_TYPE, "idle_cores": 2, "batch_cores": 16,
         "project": PROJECT_NAME}
RECORD_PATH = f"{SCORE_HOME}/.config/score/conductor.json"
SIZE_URL_NAME = "SCORE_CONDUCTOR_SIZE_URL"  # score/conductor SIZE_URL
HOURS_A_MONTH = 730
ADDRESS_EUROS_AN_HOUR = 0.005  # a flexible IPv4: the backend's figure (backends/scaleway.py), not in the catalog
# The owner's env file values the conductor's env file carries over (none is a secret; the token is read by name).
CARRIED = ("SCORE_OWNER", "SCORE_SYNC_URL", "SCORE_SYNC_MAX_EUROS", "SCORE_EXPORT_MAX_MB", "SCORE_GOOGLE_BILLING_TABLE")
SECRET_ARGUMENT = ".value="
# The deploy templates' slots (score/dashboard/deploy) as boot.sh fills them for user score; keep the two the same.
UNIT_SLOTS = {"<path to the score repository>": "%h/projects/score",
              "<path to the env file kept outside the repo>": "%h/.config/score/dashboard.env",
              "<the sync token's name in your secret manager>": "score-cockpit-sync-token"}
ACTIVE_STATES = ("running", "starting")
# This PC's units that act as the store's machine (score/dashboard install-sync, score-resume): the move switches
# them off before the PC's backup, so only the conductor acts as the store afterwards (sync/one_store.py).
PC_UNITS = ("score-sync.timer", "score-listen.service", "score-resume.service")
NAMESPACE_WAIT_SECONDS = 300


class Scw:
    """The scw CLI, one JSON answer a call. Dry: each call is printed and recorded, none is made, and every answer is
    empty, so `up --dry` shows the whole make from nothing. A secret argument's value is never printed."""

    def __init__(self, dry=False, say=print):
        self.dry, self.say, self.calls = dry, say, []

    @staticmethod
    def shown(arguments):
        return " ".join(shlex.quote(argument.split(SECRET_ARGUMENT)[0] + SECRET_ARGUMENT + "<secret>"
                                    if SECRET_ARGUMENT in argument else argument) for argument in arguments)

    def __call__(self, *arguments):
        text = self.shown(arguments)
        self.calls.append(text)
        if self.dry:
            self.say(f"scw {text}")
            return None
        done = subprocess.run(["scw", *arguments, "-o", "json"], capture_output=True, text=True)
        if done.returncode != 0:
            raise SystemExit(f"scw {text} failed: {(done.stderr or done.stdout).strip()}")
        if not done.stdout.strip():
            return None
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError:  # `scw function deploy` prints its progress as text, even with -o json
            return done.stdout


def agent_refusal(environ=os.environ):
    """Why this process may not make or delete the machine, or None: an agent's process never does."""
    found = [name for name in AGENT_MARKERS if environ.get(name)]
    if found:
        return (f"refused in an agent's process ({', '.join(found)} set): up, down and the owner's credential are "
                "his own, run from his terminal")
    return None


def step_refusal(step, environ=os.environ, open_yes=conductor_yes.open_yes):
    """(why this process may not run `step` (up or move), or None; the owner's yes it runs under, or None). His own
    process needs no yes; an agent's runs only under his recorded yes open for that step."""
    refused = agent_refusal(environ)
    if refused is None:
        return None, None
    found = open_yes(step)
    if found is None:
        return f"{refused}, or under his recorded yes to the switch (conductor_yes record): none open for {step}", None
    return None, found


def project_id(scw, name):
    """The id of the one project named `name` (a placeholder in a dry run)."""
    found = [item for item in scw("account", "project", "list", f"name={name}") or []
             if item["name"] == name]
    if scw.dry:
        return f"<id of project {name}>"
    if len(found) != 1:
        raise SystemExit(f"expected one Scaleway project named {name}, found {len(found)}")
    return found[0]["id"]


def ours(items, project, name=None):
    """The listed records that belong to `project` (and carry `name`), checked by each record's own fields."""
    return [item for item in items or [] if item.get("project_id", item.get("project")) == project
            and (name is None or item.get("name") == name)]


def one(items, what):
    if len(items) > 1:
        raise SystemExit(f"{len(items)} {what} in the project; resolve that by hand")
    return items[0] if items else None


def placeholder(scw, what, made):
    """A created resource's id, or a placeholder naming it in a dry run."""
    return f"<id of the new {what}>" if scw.dry else made["id"]


def security_group(scw, project):
    """The conductor's security group: inbound dropped but tcp/22, outbound open. Made when missing."""
    found = one(ours(scw("instance", "security-group", "list", f"name={NAME}", f"project-id={project}", f"zone={ZONE}"),
                     project, NAME), "security groups named score-conductor")
    if found:
        return found["id"]
    made = scw("instance", "security-group", "create", f"name={NAME}", f"project-id={project}", f"zone={ZONE}",
               "description=SCORE conductor: ssh only", "inbound-default-policy=drop",
               "outbound-default-policy=accept", "stateful=true", f"tags.0={TAG}")
    group = placeholder(scw, "security group", made and made["security_group"])
    scw("instance", "security-group", "create-rule", f"security-group-id={group}", "protocol=TCP",
        "direction=inbound", "action=accept", "ip-range=0.0.0.0/0", "dest-port-from=22", "dest-port-to=22",
        f"zone={ZONE}")
    return group


def address(scw, project):
    """The conductor's flexible IPv4 record ({id, address}). Made when missing."""
    found = one(ours(scw("instance", "ip", "list", f"project-id={project}", f"tags.0={TAG}", f"zone={ZONE}"), project),
                "flexible IPs tagged score-conductor")
    if found:
        return found
    if not scw.dry:  # the order's ledger line first: the address is billed by the hour from the order on
        ledger.order_started("conductor-ip", NAME, {"zone": ZONE})
    made = scw("instance", "ip", "create", "type=routed_ipv4", f"project-id={project}", f"tags.0={TAG}",
               f"zone={ZONE}")
    return {"id": placeholder(scw, "flexible IPv4", made and made["ip"]),
            "address": "<its address>" if scw.dry else made["ip"]["address"]}


def data_volume(scw, project):
    """The data volume's id: 100 GB SBS at 5K IOPS, kept by `down` unless --with-data. Made when missing."""
    found = one(ours(scw("block", "volume", "list", f"name={DATA_NAME}", f"project-id={project}", f"zone={ZONE}"),
                     project, DATA_NAME), "volumes named score-conductor-data")
    if found:
        return found["id"]
    if not scw.dry:
        ledger.order_started("conductor-volume", DATA_NAME, {"zone": ZONE, "size_gb": DATA_GB})
    made = scw("block", "volume", "create", f"name={DATA_NAME}", f"perf-iops={IOPS}", f"from-empty.size={DATA_GB}GB",
               f"project-id={project}", f"tags.0={TAG}", f"zone={ZONE}")
    return placeholder(scw, "data volume", made)


def server(scw, project):
    """The conductor's server record, or None. A server named score-conductor without the tag is refused."""
    found = one(ours(scw("instance", "server", "list", f"name={NAME}", f"project-id={project}", f"zone={ZONE}"),
                     project, NAME), "servers named score-conductor")
    if found and (TAG not in found.get("tags", []) or BATCH_TAG in found.get("tags", [])):
        raise SystemExit("the server named score-conductor is not tagged as the conductor; resolve that by hand")
    return found


def make_server(scw, project, group, ip, volume, user_data):
    """Create the server at the idle size with its root and data volumes, IP, group and cloud-init; protect it."""
    if not scw.dry:
        ledger.order_started("conductor-server", NAME, {"type": IDLE_TYPE, "zone": ZONE})
    made = scw("instance", "server", "create", f"image={IMAGE}", f"type={IDLE_TYPE}", f"name={NAME}",
               f"root-volume=sbs:{ROOT_GB}GB:{IOPS}", f"additional-volumes.0={volume}", f"ip={ip}",
               f"security-group-id={group}", f"tags.0={TAG}", f"cloud-init=@{user_data}", f"project-id={project}",
               f"zone={ZONE}", "--wait")
    server_id = placeholder(scw, "server", made)
    scw("instance", "server", "update", f"server-id={server_id}", "protected=true", f"zone={ZONE}")
    return server_id


def authorized_keys(owner_key, agent_key):
    """cloud-init's ssh_authorized_keys lines: the owner's key, and the agents' key held to the door."""
    lines = [f"      - {json.dumps(owner_key.strip())}"]
    if agent_key:
        door = ('command="/usr/local/bin/score-agent-door",no-pty,no-port-forwarding,no-agent-forwarding,'
                'no-X11-forwarding ')
        lines.append(f"      - {json.dumps(door + agent_key.strip())}")
    return "\n".join(lines)


def render_cloud_init(owner_key, agent_key, volume, commit):
    """cloud-init.yaml with its slots filled: the keys, the data volume's device and the commit to clone."""
    text = (HERE / "cloud-init.yaml").read_text()
    for slot, value in (("@AUTHORIZED_KEYS@", authorized_keys(owner_key, agent_key)),
                        ("@DATA_DEVICE@", DATA_DEVICE.format(volume)), ("@COMMIT@", commit)):
        text = text.replace(slot, value)
    return text


def pushed_commit(dry):
    """This checkout's HEAD, which must be on origin/main (the machine clones the public repository at it); a dry
    run takes HEAD as it is."""
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()
    held = subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", head, "origin/main"])
    if held.returncode != 0 and not dry:
        raise SystemExit(f"HEAD {head[:12]} is not on origin/main: the machine clones the public repository; "
                         "push first")
    return head


def bucket(scw, project):
    """The backup bucket in nl-ams, versioned, its non-current versions kept 30 days. Made when missing."""
    listed = scw("object", "bucket", "list", f"project-id={project}", f"region={BUCKET_REGION}") or []
    if not any(BUCKET in (item.get("name"), item.get("Name")) for item in listed):  # scw lists it as Name
        scw("object", "bucket", "create", f"name={BUCKET}", "enable-versioning=true", "acl=private",
            f"project-id={project}", f"region={BUCKET_REGION}")
    scw("object", "bucket-lifecycle", "create", BUCKET, f"lifecycle-configuration={HERE / 'lifecycle.json'}",
        f"project-id={project}", f"region={BUCKET_REGION}")


def secret_value(scw, name, project_name=SECRETS_PROJECT_NAME):
    """A secret's latest value from the project named `project_name` (the secrets project), by name; a placeholder in
    a dry run."""
    project = project_id(scw, project_name)
    version = scw("secret", "version", "access-by-path", f"secret-name={name}", f"project-id={project}",
                  "revision=latest", f"region={SECRETS_REGION}")
    if scw.dry:
        return f"<secret {name}>"
    return base64.b64decode(version["data"]).decode().strip()


def namespace(scw, project):
    """The function namespace's id (named score-conductor), made when missing and waited on until ready."""
    found = one(ours(scw("function", "namespace", "list", f"name={NAME}", f"project-id={project}",
                         f"region={REGION}"), project, NAME), "function namespaces named score-conductor")
    if found:
        return found["id"]
    made = scw("function", "namespace", "create", f"name={NAME}", f"project-id={project}", f"region={REGION}",
               "description=SCORE conductor: its size function")
    if scw.dry:
        return "<id of the new namespace>"
    deadline = time.monotonic() + NAMESPACE_WAIT_SECONDS
    while scw("function", "namespace", "get", f"namespace-id={made['id']}", f"region={REGION}")["status"] != "ready":
        if time.monotonic() > deadline:
            raise SystemExit("the function namespace is not ready after 5 minutes")
        time.sleep(5)
    return made["id"]


def function_settings(server_id, key, token):
    """The size function's settings: runtime, scale, timeout, its environment and its secret environment."""
    plain = {"SCORE_SERVER_ID": server_id, "SCORE_ZONE": ZONE, "SCORE_IDLE_TYPE": IDLE_TYPE,
             "SCORE_BATCH_TYPE": BATCH_TYPE, "SCORE_HEALTH_BUCKET": BUCKET, "SCORE_HEALTH_REGION": BUCKET_REGION}
    secrets = {"SCW_ACCESS_KEY": key["access_key"], "SCW_SECRET_KEY": key["secret_key"], "SCORE_SIZE_TOKEN": token}
    settings = [f"runtime={FUNCTION_RUNTIME}", "handler=handler.handle", "privacy=public", "min-scale=0",
                "max-scale=1", "memory-limit=128", "timeout=900s", "http-option=redirected",
                *(f"environment-variables.{name}={value}" for name, value in plain.items())]
    for index, (name, value) in enumerate(secrets.items()):
        settings += [f"secret-environment-variables.{index}.key={name}",
                     f"secret-environment-variables.{index}.value={value}"]
    return settings


def size_key(scw):
    """The size function's own Scaleway key ({access_key, secret_key}), from the secret score-conductor-size-key."""
    raw = secret_value(scw, SIZE_KEY_SECRET)
    return {"access_key": "<access key>", "secret_key": raw} if scw.dry else json.loads(raw)


def function_zip(folder):
    """size_function/ zipped for upload (handler.py and s3.py, nothing else)."""
    path = pathlib.Path(folder) / "size_function.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ("handler.py", "s3.py"):
            archive.write(HERE / "size_function" / name, name)
    return path


def size_function(scw, project, server_id, folder):
    """Make or update the function score-conductor-size and deploy size_function/ to it."""
    space = namespace(scw, project)
    settings = function_settings(server_id, size_key(scw), secret_value(scw, SIZE_TOKEN_SECRET))
    found = one([item for item in scw("function", "function", "list", f"namespace-id={space}", f"name={FUNCTION}",
                                      f"project-id={project}", f"region={REGION}") or []
                 if item.get("name") == FUNCTION], "functions named score-conductor-size")
    if found:
        scw("function", "function", "update", f"function-id={found['id']}", *settings, f"region={REGION}")
    else:
        scw("function", "function", "create", f"name={FUNCTION}", f"namespace-id={space}", *settings,
            f"region={REGION}")
    scw("function", "deploy", f"namespace-id={space}", f"name={FUNCTION}", f"runtime={FUNCTION_RUNTIME}",
        f"zip-file={function_zip(folder)}", f"region={REGION}")


def once_key():
    """ONCE_KEY, made (no passphrase, in memory) when missing: the owner's key for an agent's process under his yes."""
    if not ONCE_KEY.exists():
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "score-conductor-once", "-f",
                        str(ONCE_KEY)], check=True)
    return ONCE_KEY


def keys(owner_key_path, agent_key_path, dry, once=False):
    """(owner's public key, agents' public key or None). The owner's private key must have a passphrase, so an
    agent on his PC cannot use it to reach the conductor without the door (checked, except in a dry run and for
    ONCE_KEY under his yes, `once`)."""
    private = pathlib.Path(owner_key_path).expanduser()
    public = pathlib.Path(f"{private}.pub")
    if not public.is_file():
        raise SystemExit(f"no public key at {public}: name the owner's key with --owner-key")
    if not dry and not once:
        bare = subprocess.run(["ssh-keygen", "-y", "-P", "", "-f", str(private)], capture_output=True)
        if bare.returncode == 0:
            raise SystemExit(f"{private} has no passphrase: an agent on this PC could use it to reach the conductor "
                             "past the door; use a key with a passphrase")
    agent = pathlib.Path(agent_key_path).expanduser() if agent_key_path else None
    if agent and not agent.is_file():
        raise SystemExit(f"no agents' public key at {agent}")
    return public.read_text(), agent.read_text() if agent else None


def env_text(owner_env):
    """The conductor's env file: the carried values of the owner's env file, and the conductor's own."""
    values = {}
    for line in pathlib.Path(owner_env).expanduser().read_text().splitlines():
        name, equals, value = line.partition("=")
        if equals and name.strip() in CARRIED:
            values[name.strip()] = value.strip()
    if not values.get("SCORE_SYNC_URL") or not values.get("SCORE_OWNER"):
        raise SystemExit(f"{owner_env} sets no SCORE_SYNC_URL or SCORE_OWNER")
    values.update({"SCORE_SECRET_READER": "/usr/local/bin/score-secret-reader",
                   "SCORE_SECRETS_PROJECT": SECRETS_PROJECT_NAME, "SCORE_SCALEWAY_PROJECT": BATCH_PROJECT_NAME,
                   "SCORE_CONDUCTOR_BUCKET": BUCKET, "SCORE_CONDUCTOR_BUCKET_REGION": BUCKET_REGION,
                   "SCORE_BACKUP_REPO": BACKUP_REPO, "SCORE_CONDUCTOR_PROJECT": PROJECT_NAME,
                   "SCORE_CONDUCTOR_RECORD": RECORD_PATH,
                   "CLOUDSDK_CONFIG": f"/run/user/{SCORE_UID}/score/gcloud",
                   "PATH": f"{SCORE_HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin"})
    return "".join(f"{name}={value}\n" for name, value in values.items())


def stored_key(scw):
    """The conductor's own key {access_key, secret_key} from the secret score-conductor-key in its own project, or None
    when prepare.sh has not put one there."""
    project = project_id(scw, PROJECT_NAME)
    listed = scw("secret", "secret", "list", f"name={CONDUCTOR_KEY_SECRET}", f"project-id={project}",
                 f"region={SECRETS_REGION}")
    if not any(item.get("name") == CONDUCTOR_KEY_SECRET for item in listed or []):
        return None
    return json.loads(secret_value(scw, CONDUCTOR_KEY_SECRET, PROJECT_NAME))


def credential_text(organisation, key=None, ask=getpass.getpass):
    """The conductor's scw config.yaml, from its stored key, else the one the owner types (never echoed, never
    written here)."""
    key = key or {"access_key": ask("the conductor's scoped API key, access key: "),
                  "secret_key": ask("its secret key: ")}
    access, secret = key["access_key"].strip(), key["secret_key"].strip()
    if not access or not secret:
        raise SystemExit("no key given")
    return (f"access_key: {access}\nsecret_key: {secret}\ndefault_organization_id: {organisation}\n"
            f"default_region: {REGION}\ndefault_zone: {ZONE}\n")


def ssh(host, key, command, stdin=None):
    """One command as user score on the conductor, with the owner's key; its input piped, never on disk here."""
    done = subprocess.run(["ssh", "-i", str(pathlib.Path(key).expanduser()), "-o", "StrictHostKeyChecking=accept-new",
                           "-o", "IdentitiesOnly=yes", f"score@{host}", command], input=stdin, text=True)
    if done.returncode != 0:
        raise SystemExit(f"ssh score@{host} {command!r} failed (exit {done.returncode})")


def piped(path):
    """A remote command writing its stdin to `path` at mode 600, whole (a partial then a rename)."""
    return (f"umask 077 && mkdir -p \"$(dirname {path})\" && cat > {path}.partial && chmod 600 {path}.partial && "
            f"mv -f {path}.partial {path}")


def hand_over(host, key, credential, environment):
    """After cloud-init: the credential, the env file and the sizes record piped over ssh, then boot.sh's user
    part."""
    ssh(host, key, "cloud-init status --wait > /dev/null")
    ssh(host, key, piped("~/.config/scw/config.yaml"), credential)
    ssh(host, key, piped("~/.config/score/dashboard.env"), environment)
    ssh(host, key, piped(RECORD_PATH.replace(SCORE_HOME, "~", 1)), json.dumps(SIZES, indent=1) + "\n")
    ssh(host, key, "bash ~/projects/score/tools/cloud/conductor/boot.sh user")


def up(options, scw, say=print):
    """Make or update the conductor; in a dry run (free, open to agents), print every call and make none. In an
    agent's process only under the owner's open yes (step_refusal), with ONCE_KEY, the step marked done at its end."""
    refused, yes = (None, None) if scw.dry else step_refusal("up")
    if refused:
        raise SystemExit(refused)
    fresh = bool(yes) and not ONCE_KEY.exists()
    owner_key_path = once_key() if yes else options.owner_key
    owner_key, agent_key = keys(owner_key_path, options.agent_key, scw.dry, once=bool(yes))
    environment = env_text(options.env_file) if not scw.dry or pathlib.Path(options.env_file).expanduser().is_file() \
        else None
    commit = pushed_commit(scw.dry)
    project = project_id(scw, PROJECT_NAME)
    group, ip, volume = security_group(scw, project), address(scw, project), data_volume(scw, project)
    found = server(scw, project)
    if found and fresh:
        raise SystemExit(f"the conductor exists, and the one-off key it was made with is gone from {ONCE_KEY} (a "
                         "reboot clears it): `machine.py down` (the data volume is kept) and `up` again, or the owner "
                         "runs up with his own key")
    with tempfile.TemporaryDirectory() as folder:
        user_data = pathlib.Path(folder) / "cloud-init.yaml"
        user_data.write_text(render_cloud_init(owner_key, agent_key, volume, commit))
        server_id = found["id"] if found else make_server(scw, project, group, ip["id"], volume, user_data)
        bucket(scw, project)
        size_function(scw, project, server_id, folder)
    size_url = "https://<the size function's domain>" if scw.dry else function_url(scw, project)
    if environment is not None:
        environment += f"{SIZE_URL_NAME}={size_url}\n"
    if scw.dry:
        say(f"then: ssh score@{ip['address']}: the scoped key (the secret {CONDUCTOR_KEY_SECRET} in {PROJECT_NAME}, "
            f"else typed) to {SCORE_HOME}/.config/scw/config.yaml (mode 600), the env file, boot.sh user")
        return
    key = stored_key(scw)
    if key is None and yes:
        raise SystemExit(f"no secret {CONDUCTOR_KEY_SECRET} in {PROJECT_NAME}: run tools/cloud/conductor/prepare.sh "
                         "first")
    organisation = subprocess.run(["scw", "config", "get", "default-organization-id"], capture_output=True,
                                  text=True, check=True).stdout.strip()
    hand_over(ip["address"], owner_key_path, credential_text(organisation, key), environment)
    if yes:
        conductor_yes.mark_done(yes, "up")
    say(f"up: the conductor runs at {ip['address']} ({IDLE_TYPE}); `machine.py status` shows its health")


def status(options, scw, say=print):
    """Print the server, its size and state, its IP, the volumes and the last health record."""
    project = project_id(scw, PROJECT_NAME)
    found = server(scw, project)
    if not found:
        say("status: no conductor server in the project")
        return
    ip = (found.get("public_ip") or {}).get("address")
    say(f"server {found['id']}: {found['commercial_type']}, {found['state']}, {ip}")
    for volume in ours(scw("block", "volume", "list", f"project-id={project}", f"tags.0={TAG}", f"zone={ZONE}"),
                       project):
        say(f"volume {volume['name']}: {volume['size'] // 10 ** 9} GB, {volume['status']}")
    say(f"health: {json.dumps(health_record(scw))}")


def health_record(scw, read=s3.get):
    """The conductor's last health record from the backup bucket, read with the conductor's own key (bucket_key: this
    PC's key is refused there, HTTP 403, 2026-10-24), else the caller's own scw key; or None."""
    def get(name):
        return subprocess.run(["scw", "config", "get", name], capture_output=True, text=True, check=True).stdout.strip()
    key = bucket_key(scw)
    access, secret = ((key["AWS_ACCESS_KEY_ID"], key["AWS_SECRET_ACCESS_KEY"]) if key
                      else (get("access-key"), get("secret-key")))
    raw = read(BUCKET, "health/conductor.json", BUCKET_REGION, access, secret)
    return json.loads(raw) if raw else None


def function_url(scw, project):
    """The size function's https address."""
    found = one([item for item in scw("function", "function", "list", f"name={FUNCTION}", f"project-id={project}",
                                      f"region={REGION}") or [] if item.get("name") == FUNCTION],
                "functions named score-conductor-size")
    if not found:
        raise SystemExit("no size function: run `machine.py up` first")
    return f"https://{found['domain_name']}"


def resize(action, scw, say=print):
    """Ask the size function to grow or shrink the conductor; print its answer."""
    url = function_url(scw, project_id(scw, PROJECT_NAME))
    request = urllib.request.Request(url, data=json.dumps({"action": action}).encode(), method="POST",
                                     headers={"Content-Type": "application/json",
                                              "X-Score-Size-Token": secret_value(scw, SIZE_TOKEN_SECRET)})
    try:
        with urllib.request.urlopen(request, timeout=960) as answer:
            say(f"{action}: {answer.read().decode()}")
    except urllib.error.HTTPError as error:
        raise SystemExit(f"{action}: {error.code} {error.read().decode()}") from None


def stop(scw, say=print):
    """Power the conductor off (the owner's hard stop, run from his PC with his own scw)."""
    found = server(scw, project_id(scw, PROJECT_NAME))
    if not found:
        raise SystemExit("no conductor server")
    scw("instance", "server", "stop", f"server-id={found['id']}", f"zone={ZONE}", "--wait")
    say("stop: the conductor is powered off; `machine.py up` or the console powers it on")


# On the conductor: the restore into the empty home, the prop environment built (left out of every backup), then the
# sync's units (score/dashboard install-sync, no pull: score-update moves the checkout). Never before: a sync or listener on the empty home makes dashboard/ and the move
# refuses it. score-health and score-resume wait for the machine.json the restore writes (ConditionPathExists).
LANDED = ("set -a && . ~/.config/score/dashboard.env && set +a && cd ~/projects/score && "
          ".venv/bin/python -m score.store.backup migrate --onto-conductor && "
          "bash tools/cloud/conductor/boot.sh env && "
          ".venv/bin/python -m score.dashboard install-sync --env-file ~/.config/score/dashboard.env --no-pull")


def migrate_environment(scw_path, yes=None):
    """This PC's environment for a migrate step: the backup's password read through the conductor's own reader
    (secret_reader.sh) from the same project the conductor reads (SCORE_SECRETS_PROJECT), with this PC's scw at
    `scw_path`, so the password lives in one place; under the owner's yes, its id (conductor_yes.YES_ID)."""
    environment = {**os.environ, "SCORE_SECRET_READER": str(HERE / "secret_reader.sh"),
                   "SCORE_SECRETS_PROJECT": SECRETS_PROJECT_NAME, "SCORE_SCW": scw_path,
                   "SCORE_BACKUP_REPO": BACKUP_REPO}
    if yes:
        environment[conductor_yes.YES_ID] = yes["id"]
    return environment


def bucket_key(scw):
    """{AWS variable: value} of the conductor's own key for the backup bucket, which lives in its project: S3 reaches a
    bucket through a key's default project, so this PC's own key is refused there (Access Denied, 2026-10-24); {} in a
    dry run or before prepare.sh stored the key."""
    if scw.dry:
        return {}
    key = stored_key(scw)
    return {"AWS_ACCESS_KEY_ID": key["access_key"], "AWS_SECRET_ACCESS_KEY": key["secret_key"]} if key else {}


def move_steps(scw_path, yes=None):
    """The move's two commands: (this PC's migrate --from-pc as an argument list with its environment, the ssh
    command for the conductor)."""
    local = [str(REPO / ".venv" / "bin" / "python"), "-m", "score.store.backup", "migrate", "--from-pc"]
    return (local, migrate_environment(scw_path, yes)), LANDED


def retire_commands():
    """The commands that fill the PC's new empty home: work/ and design/ restored read-only (migrate --pc-test-home,
    what the PC's tests read) and env/ built from uv.lock (bootstrap.sh's build_python); (command, extra env) each."""
    return [([str(REPO / ".venv" / "bin" / "python"), "-m", "score.store.backup", "migrate", "--pc-test-home"], {}),
            (["uv", "sync", "-q", "--frozen", "--no-dev", "--project", str(REPO)],
             {"UV_PROJECT_ENVIRONMENT": str(PROPS_HOME / "env")})]


def retire_pc_home(yes, scw_path, bucket=None, run=subprocess.run):
    """Set this PC's home aside read-only at PC_FINAL_HOME once the store is on the conductor, so no session here
    writes a stale store or syncs it back: an empty home in its place filled by retire_commands, the move marked done
    on the yes in the set-aside store, then that home made read-only."""
    PROPS_HOME.rename(PC_FINAL_HOME)
    PROPS_HOME.mkdir()
    environment = {**migrate_environment(scw_path, yes), **(bucket or {}), conductor_yes.YES_HOME: str(PC_FINAL_HOME)}
    for command, extra in retire_commands():
        done = run(command, env={**environment, **extra})
        if done.returncode != 0:
            raise SystemExit(f"move: the store is on the conductor, but setting this PC's home aside stopped at "
                             f"{' '.join(command[-3:])} (exit {done.returncode}); the old home is at {PC_FINAL_HOME}")
    conductor_yes.mark_done(yes, "move", Store.in_folder(PC_FINAL_HOME / "store"))
    run(["chmod", "-R", "a-w", str(PC_FINAL_HOME)], check=True)


def forget_once_key(host):
    """Take ONCE_KEY's line off the conductor's authorized_keys, then delete the key here."""
    body = shlex.quote(pathlib.Path(f"{ONCE_KEY}.pub").read_text().split()[1])
    listed = "~/.ssh/authorized_keys"
    ssh(host, ONCE_KEY, f"umask 077 && {{ grep -vF -- {body} {listed} > {listed}.partial || [ $? -eq 1 ]; }} && "
                        f"mv -f {listed}.partial {listed}")
    for path in (ONCE_KEY, pathlib.Path(f"{ONCE_KEY}.pub")):
        path.unlink()


def pc_units_off(present=None, systemctl=None):
    """Disable and stop this PC's units that act as the store's machine (PC_UNITS: the sync's timer, the listener,
    resume), so after the move a reboot never starts a second store here; the ones switched off. score-sync.service
    is left to finish its pass: migrate --from-pc refuses while it runs."""
    run = systemctl or (lambda *args: subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True))
    if present is None:
        listed = run("list-unit-files", "--no-legend", *PC_UNITS)
        present = [line.split()[0] for line in listed.stdout.splitlines() if line.split()]
    found = [unit for unit in PC_UNITS if unit in present]
    if found:
        done = run("disable", "--now", *found)
        if done.returncode != 0:
            raise SystemExit(f"move: systemctl --user disable --now {' '.join(found)} failed: {done.stderr.strip()}")
    return found


def move(options, scw, say=print):
    """The store's one-time move from this PC to the conductor (the owner's, after `up`): this PC's sync timer,
    listener and resume disabled and stopped (pc_units_off: one store only), this PC's home backed up tagged pc-final
    with its manifest, then on the conductor the restore, the manifests compared (any difference stops it),
    machine.json written, the sync and listener installed and the waiting units started. Safe to run again after a
    refusal. Dry: every step printed, nothing run."""
    refused, yes = (None, None) if scw.dry else step_refusal("move")
    if refused:
        raise SystemExit(refused)
    if PC_FINAL_HOME.exists() and not scw.dry:
        raise SystemExit(f"move: this PC's home was already set aside at {PC_FINAL_HOME}: the move ran")
    owner_key = ONCE_KEY if yes else options.owner_key
    found = server(scw, project_id(scw, PROJECT_NAME))
    host = ((found or {}).get("public_ip") or {}).get("address") or "<its address>"
    if not found and not scw.dry:
        raise SystemExit("no conductor server: run `machine.py up` first")
    scw_path = shutil.which("scw")
    if not scw_path and not scw.dry:
        raise SystemExit("move: no scw CLI on this PC's PATH: the backup's password and bucket key are read with it")
    (local, environment), remote = move_steps(scw_path or "scw", yes)
    environment.update(bucket_key(scw))
    if scw.dry:
        say(f"then: systemctl --user disable --now {' '.join(PC_UNITS)} (the ones this PC has)")
        say(f"then: SCORE_BACKUP_REPO={BACKUP_REPO} SCORE_SECRETS_PROJECT={SECRETS_PROJECT_NAME} {' '.join(local)}")
        say(f"then: ssh score@{host} {shlex.quote(remote)}")
        say(f"then, under the owner's yes: {PROPS_HOME} set aside read-only at {PC_FINAL_HOME}, "
            + "; ".join(" ".join(command) for command, _ in retire_commands())
            + f"; the one-off key {ONCE_KEY} taken off the conductor and deleted")
        return
    switched = pc_units_off()
    say(f"move: this PC's {', '.join(switched) or 'store units (none installed)'} disabled and stopped")
    done = subprocess.run(local, env=environment)
    if done.returncode != 0:
        raise SystemExit(f"move: this PC's backup failed (exit {done.returncode}); nothing moved. The store is still "
                         f"on this PC with its units off: run move again once the reason above is gone, or put them "
                         f"back with `systemctl --user enable --now {' '.join(switched)}`")
    ssh(host, owner_key, remote)
    if not yes:
        say(f"move: the store is on the conductor at {host}; the hosted cockpit asks you to confirm it as the store's "
            "machine once its first export arrives. Set this PC's home aside read-only (your step).")
        return
    retire_pc_home(yes, scw_path, bucket_key(scw))
    forget_once_key(host)
    say(f"move: the store is on the conductor at {host}; this PC's home is set aside read-only at {PC_FINAL_HOME} "
        "and the one-off key is gone; the cockpit asks the owner to confirm the machine once its first export arrives")


def confirmed(question, answer=input):
    return answer(f"{question} Type {PROJECT_NAME} to go on: ").strip() == PROJECT_NAME


def down(options, scw, say=print, answer=input):
    """Delete the server with its root volume, the IP, the group and the function namespace; the data volume and the
    backup bucket only with --with-data, confirmed twice."""
    refused = agent_refusal()
    if refused:
        raise SystemExit(refused)
    if not confirmed("This deletes the conductor's server, IP, security group and size function.", answer):
        raise SystemExit("down: not confirmed")
    with_data = options.with_data and confirmed("--with-data deletes the data volume (the store) too.", answer) and \
        confirmed("And the backup bucket. Once more:", answer)
    project = project_id(scw, PROJECT_NAME)
    found = server(scw, project)
    if found:
        scw("instance", "server", "update", f"server-id={found['id']}", "protected=false", f"zone={ZONE}")
        scw("instance", "server", "delete", f"server-id={found['id']}", "with-volumes=root", "with-ip=false",
            "force-shutdown=true", f"zone={ZONE}")
    for ip in ours(scw("instance", "ip", "list", f"project-id={project}", f"tags.0={TAG}", f"zone={ZONE}"), project):
        scw("instance", "ip", "delete", f"ip={ip['id']}", f"zone={ZONE}")
    groups = scw("instance", "security-group", "list", f"name={NAME}", f"project-id={project}", f"zone={ZONE}")
    for group in ours(groups, project, NAME):
        scw("instance", "security-group", "delete", f"security-group-id={group['id']}", f"zone={ZONE}")
    for space in ours(scw("function", "namespace", "list", f"name={NAME}", f"project-id={project}",
                          f"region={REGION}"), project, NAME):
        scw("function", "namespace", "delete", f"namespace-id={space['id']}", f"region={REGION}")
    if with_data:
        for volume in ours(scw("block", "volume", "list", f"name={DATA_NAME}", f"project-id={project}",
                               f"zone={ZONE}"), project, DATA_NAME):
            scw("block", "volume", "delete", f"volume-id={volume['id']}", f"zone={ZONE}")
        scw("object", "bucket", "delete", f"name={BUCKET}", f"project-id={project}", f"region={BUCKET_REGION}")
    say("down: done" + ("" if with_data else f"; kept the data volume {DATA_NAME} and the bucket {BUCKET}"))


def catalog(kind, place):
    """Scaleway's product catalog for one product type in one zone or region (a free read)."""
    sys.path.insert(0, str(CLOUD / "backends"))
    sys.path.insert(0, str(CLOUD))
    import scaleway as backend
    return backend.scw("product-catalog", "product", "list", f"product-types.0={kind}", place)


def unit_price(products, sku):
    """Euros per unit (an hour, or a GB-hour) of the product `sku`."""
    for product in products:
        if product["sku"] == sku:
            listed = product["price"]["retail_price"]
            return listed["units"] + listed["nanos"] / 1e9
    raise SystemExit(f"no price for {sku}")


def monthly(say=print):
    """Per-month figures at the idle size, and the batch size's extra per hour, from the catalog."""
    instances = catalog("instance", f"zone={ZONE}")
    per_hour = {kind: unit_price(instances, f"/instance/server/{kind.lower().replace('-', '_')}/{ZONE}")
                for kind in (IDLE_TYPE, BATCH_TYPE, CHEAPER_BATCH_TYPE, FIXED_TYPE)}
    block = unit_price(catalog("block_storage", f"zone={ZONE}"), f"/storage/block/volume-low-latency-5k/{ZONE}")
    backup = unit_price(catalog("object_storage", f"region={BUCKET_REGION}"),
                        f"/storage/obj/usage-new-gen-bucket-standard/{BUCKET_REGION}")
    disks = (ROOT_GB + DATA_GB) * block * HOURS_A_MONTH
    idle = per_hour[IDLE_TYPE] * HOURS_A_MONTH
    address_month = ADDRESS_EUROS_AN_HOUR * HOURS_A_MONTH
    say(f"idle {IDLE_TYPE}: EUR {per_hour[IDLE_TYPE]:.3f}/h, EUR {idle:.2f}/month")
    say(f"disks {ROOT_GB}+{DATA_GB} GB SBS 5K: EUR {disks:.2f}/month; flexible IPv4: EUR {address_month:.2f}/month "
        "(the backend's figure)")
    say(f"backups (Multi-AZ, {BUCKET_REGION}): EUR {backup * HOURS_A_MONTH:.4f} per GB-month, "
        f"EUR {10 * backup * HOURS_A_MONTH:.2f}/month at 10 GB")
    say(f"always on: EUR {idle + disks + address_month:.2f}/month before backups")
    for kind in (BATCH_TYPE, CHEAPER_BATCH_TYPE):
        say(f"batch {kind}: EUR {per_hour[kind]:.3f}/h, +EUR {per_hour[kind] - per_hour[IDLE_TYPE]:.3f}/h over idle")
    say(f"fallback, fixed {FIXED_TYPE}: EUR {per_hour[FIXED_TYPE] * HOURS_A_MONTH:.2f}/month")
    say("size function: no catalog price (Serverless Functions' free tier; unconfirmed)")


def unit_files():
    return sorted(path for path in (HERE / "units").iterdir() if path.suffix in (".service", ".timer", ".slice"))


def check_cloud_init(owner_key="ssh-ed25519 AAAA-owner owner", agent_key="ssh-ed25519 AAAA-agent agent"):
    """Why the rendered cloud-init fails `cloud-init schema`, or None."""
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "user-data.yaml"
        path.write_text(render_cloud_init(owner_key, agent_key, "<volume>", "0" * 40))
        done = subprocess.run(["cloud-init", "schema", "--config-file", str(path)], capture_output=True, text=True)
    return None if done.returncode == 0 else (done.stderr or done.stdout).strip()


def rendered_unit(unit):
    """A unit as boot.sh installs it for user score: the deploy templates' slots filled in (boot.sh render_unit)."""
    text = unit.read_text()
    for slot, value in UNIT_SLOTS.items():
        text = text.replace(slot, value)
    return text


def check_units(home):
    """Why a unit fails `systemd-analyze --user verify`, or None; %h is made `home`, whose paths the caller made."""
    with tempfile.TemporaryDirectory() as folder:
        copies = []
        for unit in unit_files():
            copy = pathlib.Path(folder) / unit.name
            copy.write_text(rendered_unit(unit).replace("%h", str(home)))
            copies.append(str(copy))
        done = subprocess.run(["systemd-analyze", "--user", "verify", *copies], capture_output=True, text=True)
    complaint = (done.stderr + done.stdout).strip()
    return complaint if done.returncode != 0 or complaint else None


def fake_home(folder):
    """A home whose paths the units name exist (the checkout's tools, an executable .venv python)."""
    home = pathlib.Path(folder)
    venv = home / "projects" / "score" / ".venv" / "bin"
    venv.mkdir(parents=True)
    (venv / "python").symlink_to(sys.executable)
    (home / "projects" / "score" / "tools").symlink_to(REPO / "tools")
    return home


def dry(options, say=print):
    """The free check: cloud-init's schema, every unit, and `up --dry`."""
    problems = [check_cloud_init()]
    with tempfile.TemporaryDirectory() as folder:
        problems.append(check_units(fake_home(folder)))
    for problem in filter(None, problems):
        say(problem)
    up(options, Scw(dry=True, say=say), say)
    say("dry: " + ("failed" if any(problems) else "cloud-init and units pass; up --dry made no call"))
    return 1 if any(problems) else 0


def parser():
    made = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = made.add_subparsers(dest="command", required=True)
    for name in ("up", "dry"):
        command = commands.add_parser(name)
        command.add_argument("--owner-key", default="~/.ssh/id_ed25519",
                             help="the owner's private ssh key (with a passphrase); its .pub goes into cloud-init")
        command.add_argument("--agent-key", default=None, help="the agents' public key, held to the door")
        command.add_argument("--env-file", default="~/.config/score/dashboard.env",
                             help="the owner's dashboard env file; its non-secret values are carried over")
        if name == "up":
            command.add_argument("--dry", action="store_true", help="print every scw call, make none")
    move = commands.add_parser("move")
    move.add_argument("--owner-key", default="~/.ssh/id_ed25519", help="the owner's private ssh key")
    move.add_argument("--dry", action="store_true", help="print every step, run none")
    for name in ("status", "grow", "shrink", "stop", "price"):
        commands.add_parser(name)
    commands.add_parser("down").add_argument("--with-data", action="store_true")
    return made


def main(argv):
    options = parser().parse_args(argv)
    if options.command == "dry":
        return dry(options)
    if options.command == "price":
        monthly()
        return 0
    scw = Scw(dry=getattr(options, "dry", False))
    if options.command == "up":
        up(options, scw)
    elif options.command == "status":
        status(options, scw)
    elif options.command in ("grow", "shrink"):
        resize(options.command, scw)
    elif options.command == "move":
        move(options, scw)
    elif options.command == "stop":
        stop(scw)
    elif options.command == "down":
        down(options, scw)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
