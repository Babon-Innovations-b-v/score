"""The store side of hosted mode, one pass (`python -m score.dashboard sync`, the owner's timer every 5 minutes):
build the export and send what the hosted side lacks, pull the waiting requests, mark each picked up, apply it, report
its state; then poll the launches earlier passes started and report how they ended. Every call goes out from the
store's machine; a pass that fails leaves each request in its last reported state and the next pass goes on from there.

The export is sent content-addressed (sync/endpoints.py): only the files the hosted side lacks, in the builder's
priority order, CHUNK bytes of a file per request, so no request nears TIMEOUT on a slow link; files not started within
PASS_SECONDS wait for the next pass and the export committed meanwhile names them "still uploading"."""
import datetime
import gzip
import hashlib
import json
import pathlib
import tempfile
import time
import urllib.error
import urllib.request

from django.conf import settings

from score.dashboard.launch import guard
from score.dashboard.pages.models import Launch
from score.dashboard.sync import applying, building

TIMEOUT = 120
CHUNK = 2 * 1024 * 1024
PASS_SECONDS = 200.0
STILL = "still uploading"


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

    def lacking(self, sizes):
        """The shas of {sha: size} the hosted side does not hold."""
        return self.call("POST", "/lacking", json.dumps({"files": sizes}).encode())["missing"]

    def put_chunk(self, sha, offset, size, data):
        """Send `data` (raw bytes of the file at `offset`) gzipped; {"have", "done"}, or {"have"} when the hosted
        side holds a different length (409), to go on from."""
        try:
            return self.call("PUT", f"/blobs/{sha}?offset={offset}&size={size}", gzip.compress(data, 6),
                             "application/gzip")
        except urllib.error.HTTPError as answer:
            if answer.code != 409:
                raise
            return {**json.loads(answer.read()), "done": False, "conflict": True}

    def commit(self, name, files):
        return self.call("POST", "/commit", json.dumps({"name": name, "files": files}).encode())

    def waiting(self):
        return self.call("GET", "/requests?state=waiting")

    def report(self, request_id, state, detail="", log_tail=""):
        return self.call("POST", f"/requests/{request_id}", json.dumps(
            {"state": state, "detail": detail, "log_tail": log_tail}).encode())


def folder_name(made_at):
    """The export's folder name on the hosted side: its made_at with no colons."""
    return made_at.replace(":", "")


def made_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def sha_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as read:
        for block in iter(lambda: read.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def listing(folder, written):
    """{path: (sha, size)} of the export's files in upload order: the builder's `written`."""
    return {path: (sha_of(folder / path), (folder / path).stat().st_size) for path in written}


def sent_file(remote, path, sha, size):
    """Send one file in CHUNK pieces, going on from what the hosted side already holds; the bytes sent."""
    offset, sent = 0, 0
    with open(path, "rb") as read:
        while True:
            read.seek(offset)
            data = read.read(CHUNK)
            answer = remote.put_chunk(sha, offset, size, data)
            sent += 0 if answer.get("conflict") else len(data)
            if answer["done"]:
                return sent
            if answer["have"] == offset and data:
                raise RuntimeError(f"{path.name}: the hosted side took none of the chunk at {offset}")
            offset = answer["have"]


def uploaded(remote, folder, files, missing, deadline):
    """Send the missing files in order until `deadline` (time.monotonic) passes; (shas now held, bytes sent)."""
    held, sent = set(), 0
    for path, (sha, size) in files.items():
        if sha not in missing or sha in held:
            continue
        if time.monotonic() > deadline:
            break
        sent += sent_file(remote, folder / path, sha, size)
        held.add(sha)
    return held, sent


def with_still_uploading(manifest, files, waiting):
    """The manifest with each file still to come named in left_out and bytes counting what is in."""
    later = [path for path, (sha, _) in files.items() if sha in waiting]
    return {**manifest, "bytes": sum(size for path, (_, size) in files.items() if path not in later),
            "left_out": [*manifest["left_out"], *({"what": path, "why": STILL} for path in later)]}


def committed(remote, folder, manifest, present):
    """Write and send the final manifest, then commit it with the files the hosted side holds; the bytes sent."""
    path = folder / "manifest.json"
    path.write_text(json.dumps(manifest, indent=1))
    own, size = sha_of(path), path.stat().st_size
    sent = sent_file(remote, path, own, size) if remote.lacking({own: size}) else 0
    remote.commit(folder_name(manifest["made_at"]), {**present, "manifest.json": own})
    return sent


def push_export(remote, source, chosen):
    """Build the export in a temporary folder and send what the hosted side lacks, then commit it; what was sent."""
    deadline = time.monotonic() + PASS_SECONDS
    with tempfile.TemporaryDirectory(dir=settings.SCORE_HOME) as made:
        folder = pathlib.Path(made)
        manifest = building.build(source, folder, made_now(), settings.SCORE_EXPORT_MAX_MB, chosen.spend(),
                                  settings.SCORE_REPO)
        files = listing(folder, manifest["written"])
        missing = set(remote.lacking({sha: size for sha, size in files.values()}))
        held, sent = uploaded(remote, folder, files, missing, deadline)
        waiting = missing - held
        manifest = with_still_uploading(manifest, files, waiting)
        sent += committed(remote, folder, manifest, {path: sha for path, (sha, _) in files.items()
                                                       if sha not in waiting})
    return {"made_at": manifest["made_at"], "files": len([path for path, (sha, _) in files.items() if sha in held]),
            "bytes": sent,
            "to_come": len({path for path, (sha, _) in files.items() if sha in waiting}),
            "left_out": manifest["left_out"]}


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
    pushed = push_export(remote, source, chosen)
    applied = apply_waiting(remote, source, chosen)
    ended = report_launches(remote, chosen)
    return (f"pushed the export of {pushed['made_at']}: {pushed['files']} files sent ({pushed['bytes'] / 1e6:.1f} MB), "
            f"{pushed['to_come']} still to come; applied {len(applied)} requests; {len(ended)} launches ended")
