"""restic, run against the repository SCORE_BACKUP_REPO names, its password read by name at use time.

The password is the secret `score-backup-restic-password`, read through SCORE_SECRET_READER (an executable outside the
repository that prints the secret its one argument names) into the restic process's environment only, never a file.
An `s3:` repository takes its access key from the scw CLI's own configuration (`scw config get access-key`), the one
credential on the store's machine's disk, so nothing else holds it.
"""
import json
import os
import shutil
import subprocess

PASSWORD_SECRET = "score-backup-restic-password"
# restic's exit status when the repository is not there yet (restic 0.17: "repository does not exist").
NO_REPOSITORY = 10
# How long a command waits for another's lock on the repository (the backup timer beside a check, say).
RETRY_LOCK = "30m"
# Variables that would give restic a password some other way than the reader: dropped from its environment.
OTHER_PASSWORDS = ("RESTIC_PASSWORD_FILE", "RESTIC_PASSWORD_COMMAND")


class ResticFailed(RuntimeError):
    """restic, the secret reader or the scw CLI failed; the message says which and why."""


def repository():
    """The repository's location, from SCORE_BACKUP_REPO (an s3: URL on the store's machine, a folder in tests)."""
    location = os.environ.get("SCORE_BACKUP_REPO", "")
    if not location:
        raise ResticFailed("SCORE_BACKUP_REPO is not set: the env file names the backup repository")
    return location


def secret(name):
    """The value of the secret `name`, printed by SCORE_SECRET_READER; never logged."""
    reader = os.environ.get("SCORE_SECRET_READER", "")
    if not reader or not shutil.which(reader):
        raise ResticFailed("SCORE_SECRET_READER names no executable: the env file names the secret reader")
    done = subprocess.run([reader, name], capture_output=True, text=True)
    value = done.stdout.strip()
    if done.returncode or not value:
        raise ResticFailed(f"the secret reader gave no value for {name} (exit {done.returncode})")
    return value


def scw_key():
    """{AWS variable: value} of the scw CLI's access key, for an s3: repository."""
    scw = shutil.which(os.environ.get("SCORE_SCW", "scw"))
    if not scw:
        raise ResticFailed("an s3: backup repository needs the scw CLI, logged in with the machine's key")
    values = {}
    for variable, key in (("AWS_ACCESS_KEY_ID", "access-key"), ("AWS_SECRET_ACCESS_KEY", "secret-key")):
        done = subprocess.run([scw, "config", "get", key], capture_output=True, text=True)
        if done.returncode or not done.stdout.strip():
            raise ResticFailed(f"scw config get {key} gave nothing (exit {done.returncode})")
        values[variable] = done.stdout.strip()
    return values


def environment():
    """The environment restic runs in: this one, with the repository and its password, and the s3 key when needed."""
    location = repository()
    environ = {name: value for name, value in os.environ.items() if name not in OTHER_PASSWORDS}
    environ.update(RESTIC_REPOSITORY=location, RESTIC_PASSWORD=secret(PASSWORD_SECRET))
    if location.startswith("s3:") and not environ.get("AWS_ACCESS_KEY_ID"):
        environ.update(scw_key())
    return environ


def executable():
    """restic's full path."""
    found = shutil.which("restic")
    if not found:
        raise ResticFailed("restic is not installed (bootstrap.sh reports it; the conductor's boot installs it)")
    return found


class Restic:
    """One repository, its environment read once."""

    def __init__(self):
        self.binary = executable()
        self.environ = environment()

    def run(self, *args, cwd=None):
        """Run restic with `args`; its completed process (stdout and stderr captured), whatever its exit status."""
        return subprocess.run([self.binary, "--retry-lock", RETRY_LOCK, *args], cwd=cwd, env=self.environ,
                              capture_output=True, text=True)

    def checked(self, *args, cwd=None):
        """Run restic with `args`; its stdout, or ResticFailed naming the command and the end of its errors."""
        done = self.run(*args, cwd=cwd)
        if done.returncode:
            tail = " | ".join(done.stderr.strip().splitlines()[-4:])
            raise ResticFailed(f"restic {args[0]} failed (exit {done.returncode}): {tail}")
        return done.stdout

    def summary(self, *args, cwd=None):
        """Run a restic command with --json; its closing summary message."""
        lines = self.checked(*args, "--json", cwd=cwd).splitlines()
        messages = [json.loads(line) for line in lines if line.startswith("{")]
        summaries = [message for message in messages if message.get("message_type") == "summary"]
        if not summaries:
            raise ResticFailed(f"restic {args[0]} gave no summary")
        return summaries[-1]

    def ensure(self):
        """The repository, made when it is not there yet (the bucket AREA 1's `up` makes starts empty)."""
        done = self.run("cat", "config")
        if done.returncode == NO_REPOSITORY:
            self.checked("init")
        elif done.returncode:
            said = " | ".join(done.stderr.strip().splitlines()[-2:])
            raise ResticFailed(f"restic cannot open the repository (exit {done.returncode}): {said}")

    def snapshots(self, tag=None):
        """The repository's snapshots, oldest first, those with `tag` only when given."""
        args = ["snapshots", "--json"] + (["--tag", tag] if tag else [])
        return sorted(json.loads(self.checked(*args) or "[]"), key=lambda snapshot: snapshot["time"])

    def newest(self, tag=None):
        """The newest snapshot's id (with `tag` when given); ResticFailed when there is none."""
        found = self.snapshots(tag)
        if not found:
            raise ResticFailed(f"the repository holds no snapshot{f' tagged {tag}' if tag else ''}")
        return found[-1]["id"]
