"""Install the sync's systemd user timer from the deploy templates, in one command the owner runs himself:

    .venv/bin/python -m score.dashboard install-sync --env-file <his env file, outside the repo>
        --host <the repository that hosts the cockpit> --dockerfile <its Dockerfile, in it> [--secret <name>]

Every pass of the timer (deploy/score-sync.service.example) reads the sync token from the owner's secret manager by
name, inline, into that one process's environment, never into a file: the env file names the reader
(SCORE_SECRET_READER, an executable outside the repository that prints the value of the secret its one argument
names). The unit runs as the owner, with his HOME, so the reader finds his own credentials where his own shell does
(his CLI's configuration under ~/.config); systemd gives it a short PATH, so the reader names its tools by full path.

It refuses before writing anything: an env file without SCORE_SYNC_URL or an executable SCORE_SECRET_READER, and a
cockpit that cannot read this checkout's export (the host's pinned SCORE_COMMIT on its origin/main runs another
score/dashboard than this checkout's: release first). Then it writes both units under ~/.config/systemd/user, reloads
the user manager and enables the timer; it prints what it did.
"""
import os
import pathlib
import subprocess

from score.dashboard.sync.client import git
from score.dashboard.sync.release import Refused, pinned, ran

DEPLOY = pathlib.Path(__file__).resolve().parents[1] / "deploy"
UNITS = ("score-sync.service", "score-sync.timer")
SECRET = "score-cockpit-sync-token"  # the token's name in the owner's secret manager
REPO_SLOT, ENV_SLOT, SECRET_SLOT = ("<path to the score repository>", "<path to the env file kept outside the repo>",
                                    "<the sync token's name in your secret manager>")


def env_values(path):
    """{name: value} of an env file's NAME=value lines."""
    found = {}
    for line in pathlib.Path(path).read_text().splitlines():
        name, equals, value = line.partition("=")
        if equals and name.strip() and not name.lstrip().startswith("#"):
            found[name.strip()] = value.strip()
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


def pin_refusal(repo, host, dockerfile):
    """Why the hosted cockpit cannot read this checkout's export yet, or None: the host's main pins a commit whose
    score/dashboard is not this checkout's."""
    ran(host, "fetch", "-q", "origin", "main")
    pin = pinned(ran(host, "show", f"FETCH_HEAD:{dockerfile}"))
    if git(repo, "cat-file", "-e", f"{pin}^{{commit}}").returncode != 0:
        ran(repo, "fetch", "-q", "origin", "main")
    if git(repo, "diff", "--quiet", pin, "HEAD", "--", "score/dashboard").returncode != 0:
        return (f"the cockpit runs score {pin[:8]}, whose dashboard is not this checkout's: release this commit first "
                f"(python -m score.dashboard release), then install the timer")
    return None


def unit_text(name, repo, env_file, secret):
    """A unit's text: its template with the repository, the env file and the secret's name filled in."""
    text = (DEPLOY / f"{name}.example").read_text()
    return text.replace(REPO_SLOT, str(repo)).replace(ENV_SLOT, str(env_file)).replace(SECRET_SLOT, secret)


def unit_folder():
    """~/.config/systemd/user (XDG_CONFIG_HOME's when set)."""
    return pathlib.Path(os.environ.get("XDG_CONFIG_HOME") or pathlib.Path.home() / ".config") / "systemd" / "user"


def install(repo, env_file, host, dockerfile, secret=SECRET, systemctl=None):
    """Write the units, reload the user manager and enable the timer; what it did, in words. Refused (nothing
    written) on env_refusal or pin_refusal."""
    refused = env_refusal(env_file) or pin_refusal(repo, host, dockerfile)
    if refused:
        raise Refused(refused)
    folder = unit_folder()
    folder.mkdir(parents=True, exist_ok=True)
    for name in UNITS:
        (folder / name).write_text(unit_text(name, pathlib.Path(repo).resolve(), pathlib.Path(env_file).resolve(),
                                              secret))
    run = systemctl or (lambda *args: subprocess.run(["systemctl", "--user", *args], check=True))
    run("daemon-reload")
    run("enable", "--now", UNITS[1])
    return (f"install-sync: {', '.join(UNITS)} written to {folder}; the timer is enabled (systemctl --user list-timers "
            f"score-sync.timer); each pass reads the token {secret} by name and logs to journalctl --user -u "
            f"score-sync.service")
