"""Run environment 1's rest on this PC's card (SCORE_CLOUD=local, backends/local.py; owner, 2026-10-27: "couldnt u just
finish the rest of env1 on this gpu aswell", then "yes"): the store pulled from the conductor, a free-only run here
whose machine work runs on this PC's card at EUR 0, the new outputs pushed back so the conductor's sync shows them in
the cockpit.

    python3 tools/cloud/this_pc.py env1        # pull, run world1, push: the one command
    python3 tools/cloud/this_pc.py pull | push | run [<score run arguments>]
    python3 tools/cloud/this_pc.py decide-yes ... | decide <yes id>   # the owner's decisions in chat, below
    python3 tools/cloud/this_pc.py env1 --go <go id>   # a run the owner gave his go: a bought batch, below

Pull and push go through the agents' door (tools/cloud/conductor/agent_door.py, the agents' key
~/.ssh/score_conductor_agents; owner, 2026-10-27: the door route, not his own key on the conductor, agents never get a
shell): its `store-pull` and `store-push` verbs, a tar stream each way over ssh.

- **Pull** copies what a run reads (the door's PULLED: the store's objects, the design, the work folder, the Google
  answer cache, score_lib's file cache) into HOME, a home of its own (default ~/.score-this-pc): never the PC's old
  home, and never the conductor's keys, ledgers, run registry or frozen copies. It sends the door a manifest of what
  HOME holds, so only new and changed files come down. The prop environment is the PC's (`env` linked), and the
  runner's ssh key here is one of its own, let into this PC's container only.
- **Run** is `score run <environment> --free` under SCORE_CLOUD=local, SCORE_FREE_ONLY=1 and SCORE_INPUTS_DIRECT=1:
  every free row and every paid row whose machine work this PC's card does runs for real; a row that would buy
  anything (a Google ask its cache does not answer, a rented card a kind too big for this card needs) fails, saying
  what, and is left for the Buy.
- **Push** adds the store's new objects and the work folder's new files (regular files; links stay here) to the
  conductor's: `store-push --missing` names what the conductor lacks, `store-push` adds those, never replacing a file
  that is there: the store is written once by content and key, so the conductor's own outputs stand and a node made
  on both sides keeps the conductor's record. Files land under the conductor's tmp/ first, so its store never lists
  half a file.
- **The owner's decisions in chat** (owner, 2026-10-27: "i hate the rule that i cant make discisions in chat
  aswell"): `decide-yes ...` and `decide <yes id>` are the door's verbs of the same name (score/dashboard/sync/
  chat_decisions.py) against HOME's store, so a decision on this run's outputs is his recorded yes applied through the
  cockpit's own request code, and goes back to the conductor's store with the next push like any new output.
- **His go** (owner, 2026-10-27, his "sure" to: "let a free run you started accept passing results on its own, like a
  bought batch, so the run doesn't stop for clicks"): `decide-yes go world1 <answer> <question>` records it in HOME's
  store, and `env1 --go <go id>` (or `run ... --go <go id>`) tags the run SCORE_OWNERS_GO, so the runner takes it as a
  bought batch for review.IN_BATCH (score.review.web.owners_go checks the go is his); without a go nothing changes.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tarfile

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "cloud" / "conductor"))

from agent_door import PULLED, PUSHED, env_file_values, manifest, walked  # noqa: E402

HOME = pathlib.Path(os.environ.get("SCORE_THIS_PC_HOME", pathlib.Path.home() / ".score-this-pc"))
DASHBOARD_ENV = pathlib.Path.home() / ".config" / "score" / "dashboard.env"  # this PC's cockpit's, its SCORE_OWNER
OWNERS_GO = "SCORE_OWNERS_GO"  # score.review.web.OWNERS_GO: the run's go, the owner's recorded in a session
PC_ENV = pathlib.Path.home() / ".farm-factory-props" / "env"  # the prop environment bootstrap.sh builds here
CONDUCTOR = ("score-conductor", "fr-par-2")  # its server's name and zone (tools/cloud/conductor/machine.py)
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


def door_command(host, key, verb):
    """The ssh that asks the conductor's agents' door for `verb` (the door decides; no shell)."""
    return ["ssh", "-i", str(pathlib.Path(key).expanduser()), "-o", "IdentitiesOnly=yes", "-o",
            "StrictHostKeyChecking=accept-new", f"score@{host}", verb]


def pull(home, command):
    """Copies PULLED down through the door's store-pull (`command`) into `home`, only what `home` lacks or holds
    changed; (files, bytes)."""
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    process.stdin.write(manifest(home, PULLED).encode())
    process.stdin.close()
    files, size = 0, 0
    with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
        for member in archive:
            archive.extract(member, home, filter="tar")
            files, size = files + 1, size + member.size
    if process.wait():
        raise SystemExit(f"store-pull failed (exit {process.returncode}) after {files} files")
    return files, size


def push(home, missing_command, push_command):
    """Adds `home`'s regular files under PUSHED that the conductor lacks (the door's store-push --missing, then
    store-push); (files, bytes)."""
    names = [path.relative_to(home).as_posix() for path in walked(home, PUSHED) if not path.is_symlink()]
    asked = subprocess.run(missing_command, input="".join(f"{name}\n" for name in names), capture_output=True,
                           text=True, check=True).stdout.split()
    process = subprocess.Popen(push_command, stdin=subprocess.PIPE)
    with tarfile.open(fileobj=process.stdin, mode="w|", dereference=True) as archive:
        for name in asked:
            archive.add(home / name, arcname=name, recursive=False)
    process.stdin.close()
    if process.wait():
        raise SystemExit(f"store-push failed (exit {process.returncode})")
    return len(asked), sum((home / name).stat().st_size for name in asked)


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


def run_environment(home, go=None):
    """The environment a run here gets: PROPS_HOME the pulled home, this PC's card, free only, inputs direct, and the
    owner's go when one is named (no go taken from this shell)."""
    found = {**os.environ, **ENVIRONMENT, "PROPS_HOME": str(home)}
    found.pop(OWNERS_GO, None)
    return {**found, **({OWNERS_GO: go} if go else {})}


def go_taken(arguments):
    """(arguments without `--go <go id>`, the go id or None)."""
    if "--go" not in arguments:
        return list(arguments), None
    at = arguments.index("--go")
    if at + 1 >= len(arguments):
        raise SystemExit("--go names the go id decide-yes go printed")
    return [*arguments[:at], *arguments[at + 2:]], arguments[at + 1]


def run(home, arguments, go=None):
    """`score run` here on this PC's card, tagged with the owner's go when one is named; its exit status."""
    command = [str(REPO / ".venv/bin/python"), "-m", "score", "run", *arguments]
    if "--free" not in command:
        command.append("--free")
    return subprocess.run(command, cwd=REPO, env=run_environment(prepared(home), go)).returncode


def deciding(home, verb, arguments):
    """`python -m score.dashboard decide-yes|decide ...` against `home`'s store, the owner named as this PC's
    cockpit names him; its exit status."""
    owner = os.environ.get("SCORE_OWNER") or env_file_values(DASHBOARD_ENV).get("SCORE_OWNER", "")
    environment = {**run_environment(home), "SCORE_OWNER": owner}
    return subprocess.run([str(REPO / ".venv/bin/python"), "-m", "score.dashboard", verb, *arguments], cwd=REPO,
                          env=environment).returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=("env1", "pull", "run", "push", "decide-yes", "decide"))
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help="run: score run's arguments (default world1), "
                        "--go <go id> among them; decide-yes and decide: the door's verbs' arguments")
    parser.add_argument("--host", help="the conductor's address (default: read from Scaleway by its name)")
    parser.add_argument("--key", default="~/.ssh/score_conductor_agents", help="the agents' ssh key to the door")
    options = parser.parse_args(argv)
    home = prepared(HOME)
    if options.command in ("decide-yes", "decide"):
        return deciding(home, options.command, options.arguments)
    arguments, go = go_taken(options.arguments)
    if options.command == "run":
        return run(home, arguments or ["world1"], go)
    host = options.host or conductor_host()
    if options.command in ("env1", "pull"):
        files, size = pull(home, door_command(host, options.key, "store-pull"))
        print(f"pulled {files} files ({size / 1e9:.2f} GB) into {home}")
    status = run(home, ["world1"], go) if options.command == "env1" else 0
    if options.command in ("env1", "push"):
        files, size = push(home, door_command(host, options.key, "store-push --missing"),
                           door_command(host, options.key, "store-push"))
        print(f"pushed {files} files ({size / 1e9:.2f} GB)")
    return status


if __name__ == "__main__":
    sys.exit(main())
