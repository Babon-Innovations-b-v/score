"""The conductor's logs for the cockpit's Machine card: the tails the export carries, with no secret in them.

    tails(limit_lines)  # {"run <log>" | "fault <node>" | "journal <unit>": [lines]}

The newest RUN_LOGS detached run logs ($PROPS_HOME/logs/score-run-*.log), the newest FAULTS fault reports (faults/
beside the store), and `journalctl --user` of each unit health.UNITS names, each cut to its last `limit_lines` lines.
A line naming a secret (SECRET_WORDS: the secrets' environment names, their names in the secret manager and the
headers that carry them) or holding the value of a secret variable set in this process is left out whole, never
masked in place: the export leaves the machine.
"""
import os
import pathlib
import subprocess

from score.conductor import health
from score.store import PROPS_HOME, Store

RUN_LOGS, FAULTS = 3, 20
SECRET_ENV = ("SCORE_SYNC_TOKEN", "SCORE_DASHBOARD_SECRET_KEY", "SCORE_STORE_SECRET_KEY", "SCW_SECRET_KEY",
              "GEMINI_API_KEY", "GOOGLE_API_KEY", "WORLDLABS_API_KEY", "HF_TOKEN", "FREESOUND_API_KEY",
              "RESTIC_PASSWORD", "AWS_SECRET_ACCESS_KEY")
SECRET_WORDS = (*SECRET_ENV, "score-cockpit-sync-token", "gemini-api-key", "worldlabs-api-key", "hf-read-token",
                "freesound-api-key", "score-backup-restic-password", "score-conductor-size-token",
                "score-lib-deploy-key", "google-billing-reader", "score-cloud-runtime-key", "x-goog-api-key",
                "x-auth-token", "authorization", "secret_key", "private key")


def secret_values():
    """The values of the secret variables set in this process, long enough to be a secret."""
    return [os.environ[name] for name in SECRET_ENV if len(os.environ.get(name, "")) >= 8]


def clean(lines):
    """The lines that name no secret and hold no secret value."""
    values = secret_values()
    return [line for line in lines
            if not any(word in line.lower() for word in (each.lower() for each in SECRET_WORDS))
            and not any(value in line for value in values)]


def tail(path, limit_lines):
    """A text file's last `limit_lines` clean lines."""
    lines = pathlib.Path(path).read_text(errors="replace").splitlines()
    return clean(lines)[-limit_lines:]


def newest(folder, pattern, count):
    """The `count` newest files in `folder` matching `pattern`, newest first."""
    folder = pathlib.Path(folder)
    found = sorted(folder.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True) if folder.is_dir() \
        else []
    return found[:count]


def journal(unit, limit_lines):
    """A user unit's journal's last `limit_lines` clean lines; why not, when journalctl cannot read it."""
    try:
        done = subprocess.run(["journalctl", "--user", "-u", unit, "-n", str(limit_lines * 2), "--no-pager",
                               "-o", "short-iso"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as error:
        return [f"journal not read: {error}"]
    return clean(done.stdout.splitlines())[-limit_lines:]


def tails(limit_lines=40, logs=None, faults=None, read_journal=journal):
    """{name: [lines]}, the cockpit's shape: `run <log>`, `fault <node>` and `journal <unit>`, each one's clean
    tail."""
    logs = pathlib.Path(logs or PROPS_HOME / "logs")
    faults = pathlib.Path(faults or Store.default().cache.parent / "faults")
    services = [unit for units in health.UNITS.values() for unit in units if unit.endswith(".service")]
    return {**{f"run {path.name}": tail(path, limit_lines) for path in newest(logs, "score-run-*.log", RUN_LOGS)},
            **{f"fault {path.stem}": tail(path, limit_lines) for path in newest(faults, "*.txt", FAULTS)},
            **{f"journal {unit}": read_journal(unit, limit_lines) for unit in services}}
