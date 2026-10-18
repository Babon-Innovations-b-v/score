"""The store side of hosted mode, one pass (`python -m score.dashboard sync`, the owner's timer every 5 minutes):
build the export and push it, pull the waiting requests, mark each picked up, apply it, report its state; then poll
the launches earlier passes started and report how they ended. Every call goes out from the store's machine; a pass
that fails leaves each request in its last reported state and the next pass goes on from there."""
import datetime
import io
import json
import pathlib
import tarfile
import tempfile
import urllib.request

from django.conf import settings

from score.dashboard.launch import guard
from score.dashboard.pages.models import Launch
from score.dashboard.sync import applying, building

TIMEOUT = 120


class Remote:
    """The hosted dashboard's sync endpoints, called with the token."""

    def __init__(self, url, token, opener=urllib.request.urlopen):
        self.url = url.rstrip("/")
        self.token = token
        self.opener = opener

    def call(self, method, path, body=None, kind="application/json"):
        request = urllib.request.Request(f"{self.url}/api/sync{path}", data=body, method=method, headers={
            "Authorization": f"Bearer {self.token}", "Content-Type": kind})
        with self.opener(request, timeout=TIMEOUT) as answer:
            return json.loads(answer.read() or b"null")

    def put_export(self, archive):
        return self.call("PUT", "/export", archive, "application/gzip")

    def waiting(self):
        return self.call("GET", "/requests?state=waiting")

    def report(self, request_id, state, detail="", log_tail=""):
        return self.call("POST", f"/requests/{request_id}", json.dumps(
            {"state": state, "detail": detail, "log_tail": log_tail}).encode())


def folder_name(made_at):
    """The export's one top folder in its archive: its made_at with no colons."""
    return made_at.replace(":", "")


def archive_of(folder, name):
    """A tar.gz of a folder's files under one top folder `name` (the hosted side's format), in name order."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.add(path, arcname=f"{name}/{path.relative_to(folder).as_posix()}", recursive=False)
    return buffer.getvalue()


def made_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def push_export(remote, source, chosen):
    """Build the export in a temporary folder and push it; its manifest."""
    with tempfile.TemporaryDirectory(dir=settings.SCORE_HOME) as folder:
        manifest = building.build(source, folder, made_now(), settings.SCORE_EXPORT_MAX_MB, chosen.spend(),
                                  settings.SCORE_REPO)
        remote.put_export(archive_of(pathlib.Path(folder), folder_name(manifest["made_at"])))
    return manifest


def tracked_path():
    return settings.SCORE_HOME / "sync" / "launches.json"


def tracked():
    """{hosted request id: local launch id} of launches still being reported."""
    path = tracked_path()
    return json.loads(path.read_text()) if path.is_file() else {}


def keep_tracked(found):
    path = tracked_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(found, indent=1))


def apply_waiting(remote, source, chosen):
    """Pick up, apply and report each waiting request; [(id, state)]."""
    done, following = [], tracked()
    for item in remote.waiting():
        remote.report(item["id"], "picked_up")
        applied = applying.apply(item, source, chosen)
        remote.report(item["id"], applied.state, applied.detail, applied.log_tail)
        if applied.launch_id:
            following[str(item["id"])] = applied.launch_id
        done.append((item["id"], applied.state))
    keep_tracked(following)
    return done


def report_launches(remote, chosen):
    """Report each followed launch that ended; [(id, state)]."""
    following, reported = tracked(), []
    for request_id, launch_id in list(following.items()):
        record = guard.polled(Launch.objects.get(pk=launch_id), chosen)
        if record.state in ("running", "starting"):
            continue
        tail = "\n".join(item.get("log_tail", "") for item in record.handles)[-4000:]
        remote.report(int(request_id), "done" if record.state == "done" else "failed", record.result, tail)
        reported.append((int(request_id), record.state))
        following.pop(request_id)
    keep_tracked(following)
    return reported


def sync_pass(remote, source, chosen=None):
    """One pass; what it did, in words."""
    chosen = chosen or guard.backend()
    manifest = push_export(remote, source, chosen)
    applied = apply_waiting(remote, source, chosen)
    ended = report_launches(remote, chosen)
    return (f"pushed the export of {manifest['made_at']} ({manifest['bytes'] / 1e6:.1f} MB, "
            f"{len(manifest['left_out'])} left out); applied {len(applied)} requests; {len(ended)} launches ended")
