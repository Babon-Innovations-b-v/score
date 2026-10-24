"""Install the sync's systemd user timer from the deploy templates, in one command the owner runs himself:

    .venv/bin/python -m score.dashboard install-sync --env-file <his env file, outside the repo>
        [--host <the repository that hosts the cockpit> --dockerfile <its Dockerfile, in it>] [--secret <name>]
        [--no-pull]

The same command installs the units on the owner's PC and on the conductor (the store's machine in the cloud, user
`score`): the templates' slots take this checkout's path, the env file's and the secret's name, so nothing in them
names a machine. With --host the cockpit's commit is read from the hosting repository's pinned Dockerfile; without
it, from the cockpit's own /api/sync/pin (its `commit`, the SCORE_COMMIT it was built at; signed in by the sync token
the env file's reader reads; never /healthz, which the hosting proxy answers with a body of its own), which is how the
conductor, holding no hosting repository, checks it. --no-pull puts the conductor's update (tools/cloud/conductor/
update.py) in place of the sync unit's pull before each pass, so every pass starts on the commit the cockpit runs: the
score-update timer alone waits while a pass runs, and a pass outlasts the 5-minute timer, so the live conductor's
checkout never moved (2026-10-24).

Every pass of the timer (deploy/score-sync.service.example) reads the sync token from the owner's secret manager by
name, inline, into that one process's environment, never into a file: the env file names the reader
(SCORE_SECRET_READER, an executable outside the repository that prints the value of the secret its one argument
names). The unit runs as the owner, with his HOME, so the reader finds his own credentials where his own shell does
(his CLI's configuration under ~/.config); systemd gives it a short PATH, so the reader names its tools by full path.

It refuses before writing anything: an env file without SCORE_SYNC_URL or an executable SCORE_SECRET_READER, and a
cockpit that cannot read this checkout's export (the commit it runs has another score/dashboard than this checkout's:
release first). Then it writes both units under ~/.config/systemd/user, reloads the user manager, enables the timer
and starts the listener (score-listen.service, sync/listen.py: the owner's quick requests answered as they come); it
prints what it did.
"""
import json
import os
import pathlib
import subprocess
import urllib.request

from score.dashboard.sync.client import git
from score.dashboard.sync.release import Refused, inside, pinned, ran

DEPLOY = pathlib.Path(__file__).resolve().parents[1] / "deploy"
UNITS = ("score-sync.service", "score-sync.timer", "score-listen.service")
STARTED = ("score-sync.timer", "score-listen.service")  # the timer, and the listener (sync/listen.py)
SECRET = "score-cockpit-sync-token"  # the token's name in the owner's secret manager
PULL = "ExecStartPre=/usr/bin/git -C "  # the sync unit's pull before each pass, UPDATE in its place with --no-pull
REPO_SLOT, ENV_SLOT, SECRET_SLOT = ("<path to the score repository>", "<path to the env file kept outside the repo>",
                                    "<the sync token's name in your secret manager>")
# The conductor's update before each pass, on the system python (.venv may be what it re-syncs).
UPDATE = f"ExecStartPre=/usr/bin/python3 -I {REPO_SLOT}/tools/cloud/conductor/update.py --repo {REPO_SLOT}\n"


def unquoted(value):
    """A value without the one pair of quotes round it that systemd's EnvironmentFile strips too."""
    return value[1:-1] if len(value) > 1 and value[0] == value[-1] and value[0] in "'\"" else value


def env_values(path):
    """{name: value} of an env file's NAME=value lines."""
    found = {}
    for line in pathlib.Path(path).read_text().splitlines():
        name, equals, value = line.partition("=")
        if equals and name.strip() and not name.lstrip().startswith("#"):
            found[name.strip()] = unquoted(value.strip())
    return found


def env_refusal(path):
    """Why the env file cannot feed the timer, or None."""
    if not pathlib.Path(path).is_file():
        return f"no env file at {path}"
    values = env_values(path)
    if not values.get("SCORE_SYNC_URL"):
        return f"{path} sets no SCORE_SYNC_URL"
    reader = values.get("SCORE_SECRET_READER", "")
    if not (os.path.isabs(reader) and os.access(reader, os.X_OK)):
        return f"{path} names no SCORE_SECRET_READER that is an executable by its full path"
    return None


def host_pin(host, dockerfile):
    """The commit the hosting repository's origin/main pins in its Dockerfile."""
    ran(host, "fetch", "-q", "origin", "main")
    return pinned(ran(host, "show", f"FETCH_HEAD:{inside(dockerfile)}"))


def secret_value(env_file, secret):
    """The secret `secret`, read by name through the env file's SCORE_SECRET_READER; Refused when it reads none."""
    reader = env_values(env_file)["SCORE_SECRET_READER"]
    done = subprocess.run([reader, secret], capture_output=True, text=True)
    if done.returncode != 0 or not done.stdout.strip():
        raise Refused(f"{reader} read no {secret} (exit {done.returncode})")
    return done.stdout.strip()


def cockpit_pin(url, token, opener=urllib.request.urlopen):
    """The commit the cockpit at `url` says it runs (its /api/sync/pin `commit`, signed in by `token`); Refused when
    it says none."""
    asked = urllib.request.Request(f"{url.rstrip('/')}/api/sync/pin", headers={"Authorization": f"Bearer {token}"})
    try:
        with opener(asked, timeout=30) as answer:
            found = json.loads(answer.read() or b"{}").get("commit")
    except (OSError, ValueError) as unread:
        raise Refused(f"the cockpit's /api/sync/pin at {url} could not be read: {unread}") from unread
    if not found:
        raise Refused(f"the cockpit at {url} reports no commit: release a commit built with SCORE_COMMIT, then install")
    return found


def dashboard_refusal(repo, pin):
    """Why a cockpit running score `pin` cannot read this checkout's export, or None: its score/dashboard is not
    this checkout's."""
    if git(repo, "cat-file", "-e", f"{pin}^{{commit}}").returncode != 0:
        ran(repo, "fetch", "-q", "origin", "main")
    if git(repo, "cat-file", "-e", f"{pin}^{{commit}}").returncode != 0:
        return f"the cockpit pins score {pin[:8]}, which neither this checkout nor origin's main holds"
    if git(repo, "diff", "--quiet", pin, "HEAD", "--", "score/dashboard").returncode != 0:
        return (f"the cockpit runs score {pin[:8]}, whose dashboard is not this checkout's: release this commit first "
                f"(python -m score.dashboard release), then install the timer")
    return None


def unit_text(name, repo, env_file, secret, pull=True):
    """A unit's text: its template with the repository, the env file and the secret's name filled in; without
    `pull`, the sync unit's pull before each pass is the conductor's update (UPDATE) instead."""
    text = (DEPLOY / f"{name}.example").read_text()
    if not pull:
        text = "".join(UPDATE if line.startswith(PULL) else line for line in text.splitlines(keepends=True))
    return text.replace(REPO_SLOT, str(repo)).replace(ENV_SLOT, str(env_file)).replace(SECRET_SLOT, secret)


def unit_folder():
    """~/.config/systemd/user (XDG_CONFIG_HOME's when set)."""
    return pathlib.Path(os.environ.get("XDG_CONFIG_HOME") or pathlib.Path.home() / ".config") / "systemd" / "user"


def user_manager(*args):
    """Run `systemctl --user <args>`; why it failed in words, or None."""
    done = subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True)
    return None if done.returncode == 0 else (done.stderr.strip().splitlines() or [f"exit {done.returncode}"])[-1]


def install_refusal(repo, env_file, host, dockerfile, opener, secret=SECRET):
    """Why the units may not be installed, or None: env_refusal, else a cockpit on another dashboard (the commit the
    host pins with `host`, else the one the cockpit's /api/sync/pin reports, asked with the sync token `secret`)."""
    refused = env_refusal(env_file)
    if refused:
        return refused
    if host:
        pin = host_pin(host, dockerfile)
    else:
        pin = cockpit_pin(env_values(env_file)["SCORE_SYNC_URL"], secret_value(env_file, secret), opener)
    return dashboard_refusal(repo, pin)


def install(repo, env_file, host=None, dockerfile=None, secret=SECRET, systemctl=None, pull=True,
            opener=urllib.request.urlopen):
    """Write the units, reload the user manager and enable the timer; what it did, in words. Refused (nothing
    written) on install_refusal."""
    refused = install_refusal(repo, env_file, host, dockerfile, opener, secret)
    if refused:
        raise Refused(refused)
    folder = unit_folder()
    folder.mkdir(parents=True, exist_ok=True)
    for name in UNITS:
        (folder / name).write_text(unit_text(name, pathlib.Path(repo).resolve(), pathlib.Path(env_file).resolve(),
                                              secret, pull))
    run = systemctl or user_manager
    for args in (("daemon-reload",), ("enable", "--now", *STARTED), ("restart", STARTED[1])):
        failed = run(*args)
        if failed:
            raise Refused(f"the units are written to {folder}, but systemctl --user {' '.join(args)} failed: {failed}; "
                          f"the user manager needs systemd and `loginctl enable-linger` for this user: install again "
                          f"once it runs")
    return (f"install-sync: {', '.join(UNITS)} written to {folder}"
            f"{'' if pull else ' (no pull before a pass: the conductor update moves the checkout to the pin first)'}"
            f"; the timer is "
            f"enabled and the listener runs (journalctl --user -u score-listen.service); (systemctl --user list-timers "
            f"score-sync.timer); each pass reads the token {secret} by name and logs to journalctl --user -u "
            f"score-sync.service")
