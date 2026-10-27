"""Run environment 1's rest on this PC's card (SCORE_CLOUD=local, backends/local.py; owner, 2026-10-27: "couldnt u just
finish the rest of env1 on this gpu aswell", then "yes"): the store pulled from the conductor, a free-only run here
whose machine work runs on this PC's card at EUR 0, the new outputs pushed back so the conductor's sync shows them in
the cockpit.

    python3 tools/cloud/this_pc.py env1        # pull, run world1, push: the one command
    python3 tools/cloud/this_pc.py pull | push | run [<score run arguments>]

The owner's command: pull and push go over his own ssh key to user score on the conductor (its passphrase asked, as
for `machine.py`); an agent reaches the conductor only through its door, which moves no files.

- **Pull** copies what a run reads (PULLED: the store's objects, the design, the work folder, the Google answer cache,
  score_lib's file cache) into HOME, a home of its own (default ~/.score-this-pc): never the PC's old home, and never
  the conductor's keys, ledgers, run registry or frozen copies. The prop environment is the PC's (`env` linked), and the
  runner's ssh key here is one of its own, let into this PC's container only.
- **Run** is `score run <environment> --free` under SCORE_CLOUD=local, SCORE_FREE_ONLY=1 and SCORE_INPUTS_DIRECT=1:
  every free row and every paid row whose machine work this PC's card does runs for real; a row that would buy
  anything (a Google ask its cache does not answer, a rented card a kind too big for this card needs) fails, saying
  what, and is left for the Buy.
- **Push** adds the store's new objects and the work folder's new files to the conductor's, never replacing a file
  that is there: the store is written once by content and key, so the conductor's own outputs stand and a node made
  on both sides keeps the conductor's record. While pushing, files land under the conductor's tmp/ first, so its
  store never lists half a file.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
HOME = pathlib.Path(os.environ.get("SCORE_THIS_PC_HOME", pathlib.Path.home() / ".score-this-pc"))
PC_ENV = pathlib.Path.home() / ".farm-factory-props" / "env"  # the prop environment bootstrap.sh builds here
REMOTE_HOME = "/home/score/.farm-factory-props"  # the conductor's PROPS_HOME (docs/bible.md workflow/bootstrap)
CONDUCTOR = ("score-conductor", "fr-par-2")  # its server's name and zone (tools/cloud/conductor/machine.py)
# What a run reads from the conductor's home: rsync filter rules, in order; everything else stays there.
PULLED = ("/store/", "/store/objects/***", "/design/***", "/work/***", "/cloud/", "/cloud/google-cache/***",
          "/cache/", "/cache/library/***")
# What a run here adds that the conductor needs: the store's outputs and records, and the takes they were made from.
PUSHED = ("store/objects", "work")
ENVIRONMENT = {"SCORE_CLOUD": "local", "SCORE_FREE_ONLY": "1", "SCORE_INPUTS_DIRECT": "1",
               "SCORE_MAX_MACHINES": "all=1"}  # one machine: this PC


def conductor_host():
    """The conductor's public address, read from Scaleway by its name and zone (read only)."""
    name, zone = CONDUCTOR
    found = json.loads(subprocess.run(["scw", "instance", "server", "list", f"zone={zone}", f"name={name}", "-o",
                                       "json"], check=True, capture_output=True, text=True).stdout)
    servers = [server for server in found if server.get("name") == name]
    if len(servers) != 1:
        raise SystemExit(f"{len(servers)} servers named {name} in {zone}: name the conductor with --host")
    return servers[0]["public_ip"]["address"]


def ssh_command(key):
    """The owner's ssh to the conductor, for rsync's -e."""
    return f"ssh -i {pathlib.Path(key).expanduser()} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"


def pull_command(host, key, home):
    """The rsync that copies PULLED from the conductor's home into `home`."""
    rules = [f"--include={rule}" for rule in PULLED]
    return ["rsync", "-a", "--info=stats1", *rules, "--exclude=*", "-e", ssh_command(key),
            f"score@{host}:{REMOTE_HOME}/", f"{home}/"]


def push_commands(host, key, home):
    """The rsyncs that add PUSHED from `home` to the conductor's home, never replacing a file there."""
    temporary = f"{REMOTE_HOME}/tmp/this-pc-push"
    return [["rsync", "-a", "--info=stats1", "--ignore-existing", f"--temp-dir={temporary}",
             f"--rsync-path=mkdir -p {temporary} {REMOTE_HOME}/{folder} && rsync", "-e", ssh_command(key),
             f"{home}/{folder}/", f"score@{host}:{REMOTE_HOME}/{folder}/"] for folder in PUSHED]


def prepared(home):
    """The home made ready for a run: the PC's prop environment linked, the runner's own key for this PC's container,
    and a self-delete key file (a container never deletes itself; batch.py sends the file to every machine)."""
    cloud = home / "cloud"
    cloud.mkdir(parents=True, exist_ok=True)
    if not (home / "env").exists():
        (home / "env").symlink_to(PC_ENV)
    if not (cloud / "ssh_key").exists():
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "score-this-pc", "-f",
                        str(cloud / "ssh_key")], check=True)
    if not (cloud / "self_delete_key.json").exists():
        (cloud / "self_delete_key.json").write_text(json.dumps({"secret_key": "", "for": "this PC: never used"}))
    return home


def run_environment(home):
    """The environment a run here gets: PROPS_HOME the pulled home, this PC's card, free only, inputs direct."""
    return {**os.environ, **ENVIRONMENT, "PROPS_HOME": str(home)}


def run(home, arguments):
    """`score run` here on this PC's card; its exit status."""
    command = [str(REPO / ".venv/bin/python"), "-m", "score", "run", *arguments]
    if "--free" not in command:
        command.append("--free")
    return subprocess.run(command, cwd=REPO, env=run_environment(prepared(home))).returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=("env1", "pull", "run", "push"))
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help="run: score run's arguments (default world1)")
    parser.add_argument("--host", help="the conductor's address (default: read from Scaleway by its name)")
    parser.add_argument("--key", default="~/.ssh/id_ed25519", help="the owner's ssh key to the conductor")
    options = parser.parse_args(argv)
    home = prepared(HOME)
    if options.command == "run":
        return run(home, options.arguments or ["world1"])
    host = options.host or conductor_host()
    if options.command in ("env1", "pull"):
        subprocess.run(pull_command(host, options.key, home), check=True)
    status = run(home, ["world1"]) if options.command == "env1" else 0
    if options.command in ("env1", "push"):
        for command in push_commands(host, options.key, home):
            subprocess.run(command, check=True)
    return status


if __name__ == "__main__":
    sys.exit(main())
