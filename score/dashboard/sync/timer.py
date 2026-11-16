"""Install the upkeep pass's systemd user timer from the deploy templates, in one command:

    .venv/bin/python -m score.dashboard install-sync --env-file <the env file, outside the repo> [--no-pull]

The same command installs the units on the owner's PC and on a conductor (user `score`): the templates' slots take
this checkout's path and the env file's, so nothing in them names a machine. --no-pull puts the conductor's update
(tools/cloud/conductor/update.py) in place of the sync unit's pull before each pass, so every pass starts on origin's
main once it is safe to move: the score-update timer alone waits while a pass runs, and a pass outlasts the 5-minute
timer, so the live conductor's checkout never moved (2026-10-24).

It refuses before writing anything when there is no env file. Then it writes both units under ~/.config/systemd/user,
reloads the user manager and enables the timer; it prints what it did. The listener and the cockpit's sync token it
once installed went with the cockpit (owner, 2026-11-16: "cockpit can also go").
"""
import os
import pathlib
import subprocess

DEPLOY = pathlib.Path(__file__).resolve().parents[1] / "deploy"
UNITS = ("score-sync.service", "score-sync.timer")
PULL = "ExecStartPre=/usr/bin/git -C "  # the sync unit's pull before each pass, UPDATE in its place with --no-pull
REPO_SLOT, ENV_SLOT = "<path to the score repository>", "<path to the env file kept outside the repo>"
# The conductor's update before each pass, on the system python (.venv may be what it re-syncs).
UPDATE = f"ExecStartPre=/usr/bin/python3 -I {REPO_SLOT}/tools/cloud/conductor/update.py --repo {REPO_SLOT}\n"


class Refused(Exception):
    """An install that may not go ahead; its words."""


def unit_text(name, repo, env_file, pull=True):
    """A unit's text: its template with the repository and the env file filled in; without `pull`, the sync unit's
    pull before each pass is the conductor's update (UPDATE) instead."""
    text = (DEPLOY / f"{name}.example").read_text()
    if not pull:
        text = "".join(UPDATE if line.startswith(PULL) else line for line in text.splitlines(keepends=True))
    return text.replace(REPO_SLOT, str(repo)).replace(ENV_SLOT, str(env_file))


def unit_folder():
    """~/.config/systemd/user (XDG_CONFIG_HOME's when set)."""
    return pathlib.Path(os.environ.get("XDG_CONFIG_HOME") or pathlib.Path.home() / ".config") / "systemd" / "user"


def user_manager(*args):
    """Run `systemctl --user <args>`; why it failed in words, or None."""
    done = subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True)
    return None if done.returncode == 0 else (done.stderr.strip().splitlines() or [f"exit {done.returncode}"])[-1]


def install(repo, env_file, systemctl=None, pull=True):
    """Write the units, reload the user manager and enable the timer; what it did, in words. Refused (nothing
    written) when there is no env file."""
    if not pathlib.Path(env_file).is_file():
        raise Refused(f"no env file at {env_file}")
    folder = unit_folder()
    folder.mkdir(parents=True, exist_ok=True)
    for name in UNITS:
        (folder / name).write_text(unit_text(name, pathlib.Path(repo).resolve(), pathlib.Path(env_file).resolve(),
                                              pull))
    run = systemctl or user_manager
    for args in (("daemon-reload",), ("enable", "--now", "score-sync.timer")):
        failed = run(*args)
        if failed:
            raise Refused(f"the units are written to {folder}, but systemctl --user {' '.join(args)} failed: {failed}; "
                          f"the user manager needs systemd and `loginctl enable-linger` for this user: install again "
                          f"once it runs")
    return (f"install-sync: {', '.join(UNITS)} written to {folder}"
            f"{'' if pull else ' (no pull before a pass: the conductor update moves the checkout first)'}"
            f"; the timer is enabled (systemctl --user list-timers score-sync.timer); each pass logs to journalctl "
            f"--user -u score-sync.service")
