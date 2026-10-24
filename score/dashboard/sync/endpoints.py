"""The hosted dashboard's sync endpoints, signed in by SCORE_SYNC_TOKEN (never a session): the store's machine pushes
its state export and pulls the owner's requests. No inbound connection to the store's machine, ever.

The export travels content-addressed (owner, 2026-10-18: the whole export each pass did not fit the link): the store's
machine asks which files the hosted side lacks, sends only those, one small gzip chunk per request, and then commits
the export as a list of {path: sha256}; the hosted side builds it from hard links to the files it holds.

    POST /api/sync/lacking          {files: {sha256: size}} -> {missing: [sha256]}
    PUT  /api/sync/blobs/{sha}?offset=N&size=S   one gzip chunk of the file, at offset N of its S bytes
    POST /api/sync/commit           {name: <made_at, no colons>, files: {path: sha256}}: swapped in whole, or 409
                                    when its manifest's format is not one this side reads (state/versions.py)
    GET  /api/sync/requests?state=waiting[&kind=a,b][&wait=S]   held open up to S seconds until one is there
    POST /api/sync/requests/{id}/claim   the waiting request taken by its first caller, else 409; 423 for a caller
                                    that is not the store's machine (its X-Score-Machine name, sync/one_store.py)
    POST /api/sync/requests/{id}    {state: picked_up|running|done|refused, detail, log_tail}
    POST /api/sync/requests/{id}/note   {detail}: why a still waiting request waits (a Buy left for the next pass)
    PUT  /api/sync/batch-run        the run monitor's batch-run.json, about every minute while a batch lives
    PUT  /api/sync/request-files/<sha>-<360|1280>.jpg   a picture a request brought back (a concept draw)
    GET  /api/sync/pin              {commit}: the score commit this image was built at (SCORE_COMMIT, None outside an
                                    image), the pin install-sync and the conductor's score-update follow; here, not
                                    only at /healthz, which the hosting proxy answers with a body of its own
"""
import hashlib
import hmac
import json
import os
import pathlib
import re
import shutil
import time
import zlib

from django.conf import settings
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from score.dashboard.pages.models import SyncRequest
from score.dashboard.state import versions
from score.dashboard.sync import one_store

sync = APIRouter()
STATES = ("picked_up", "running", "done", "refused")
KEPT = 2
SHORTEST_TOKEN = 32
CHUNK = 4 * 1024 * 1024  # the most one compressed chunk may carry; the client sends 2 MiB of the file a chunk
SHA = re.compile(r"[0-9a-f]{64}")
PART_DAYS = 1.0
LONGEST_WAIT = 30.0
POLL_SECONDS = 0.5
MACHINE_HEADER = "x-score-machine"  # the store's machine's name on its sync calls (client.Remote)
REQUEST_FILE = re.compile(r"[0-9a-f]{64}-(360|1280)\.jpg")


class Report(BaseModel):
    state: str
    detail: str = ""
    log_tail: str = ""


class Note(BaseModel):
    detail: str


class Lacking(BaseModel):
    files: dict[str, int]


class Commit(BaseModel):
    name: str
    files: dict[str, str]


def token_ok(request: Request):
    """FastAPI dependency: the bearer token equals SCORE_SYNC_TOKEN (32+ characters), compared in constant time."""
    expected = settings.SCORE_SYNC_TOKEN
    given = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if len(expected) < SHORTEST_TOKEN or not hmac.compare_digest(given.encode(), expected.encode()):
        raise HTTPException(401, "a sync needs the sync token")
    return True


def blobs():
    """The folder of the files the hosted side holds, each named by its sha256."""
    folder = settings.SCORE_HOME / "blobs"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def exports():
    folder = settings.SCORE_HOME / "export"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def cap_bytes():
    return int(settings.SCORE_EXPORT_MAX_MB * 1024 * 1024)


def checked_sha(sha):
    if not SHA.fullmatch(sha):
        raise HTTPException(400, f"{sha[:80]}: not a sha256")
    return sha


def checked_path(path):
    """A path inside the export: relative, no "..", no empty part; else 400."""
    pure = pathlib.PurePosixPath(path)
    if not path or pure.is_absolute() or ".." in pure.parts or "" in path.split("/") or "\\" in path:
        raise HTTPException(400, f"{path[:80]}: only relative paths inside the export")
    return pure


def checked_name(name):
    """An export's folder name: its made_at without colons, never `current` or a partial."""
    if not name or "/" in name or name in ("current", ".", "..") or name.endswith(".partial"):
        raise HTTPException(400, f"{name[:80]}: not an export's name")
    return name


def appended(part, body, size):
    """Decompress one gzip chunk onto `part`, never past `size` bytes in all; the part's new length."""
    have = part.stat().st_size if part.exists() else 0
    inflater = zlib.decompressobj(wbits=16 + zlib.MAX_WBITS)
    try:
        data = inflater.decompress(body, size - have + 1)
    except zlib.error as refused:
        raise HTTPException(400, f"not a gzip chunk: {refused}") from refused
    if have + len(data) > size or inflater.unconsumed_tail:
        part.unlink(missing_ok=True)
        raise HTTPException(400, "the chunk runs past the file's size")
    with open(part, "ab") as written:
        written.write(data)
    return have + len(data)


def file_sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as read:
        for block in iter(lambda: read.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finished(part, sha):
    """Move a complete part to its blob when its sha256 is `sha`; a mismatch deletes the part (400)."""
    if file_sha(part) != sha:
        part.unlink()
        raise HTTPException(400, f"{sha}: the file sent does not hash to its name")
    os.replace(part, blobs() / sha)


def readable(manifest_sha):
    """The manifest; refused (409) when its format is not one this side reads (one with no format is the first, 1)."""
    try:
        manifest = json.loads((blobs() / manifest_sha).read_text())
    except ValueError as refused:
        raise HTTPException(400, f"the manifest is not JSON: {refused}") from refused
    found = manifest.get("format", 1) if isinstance(manifest, dict) else None
    if found not in versions.READABLE:
        raise HTTPException(409, f"export format {found} cannot be read here (this side reads "
                                 f"{', '.join(map(str, versions.READABLE))}): the last export stays current until "
                                 f"the store's machine and the hosted side run matching code")
    return manifest


def linked(name, files):
    """export/<name>.partial built from hard links to the held blobs; its path."""
    partial = exports() / f"{name}.partial"
    shutil.rmtree(partial, ignore_errors=True)
    for path, sha in files.items():
        target = partial.joinpath(*checked_path(path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(blobs() / sha, target)
    return partial


def swapped(partial, name):
    """Rename the partial into place and point export/current at it in one step; the KEPT newest kept."""
    folder = exports()
    final = folder / name
    shutil.rmtree(final, ignore_errors=True)
    partial.rename(final)
    link = folder / "current.partial-link"
    link.unlink(missing_ok=True)
    link.symlink_to(name)
    os.replace(link, folder / "current")
    kept = sorted(path for path in folder.iterdir() if path.is_dir() and not path.is_symlink()
                  and not path.name.endswith(".partial"))
    for old in kept[:-KEPT]:
        shutil.rmtree(old)


def swept(now=None):
    """Delete the blobs no kept export links to, and parts older than PART_DAYS; how many went."""
    now = now or time.time()
    gone = 0
    for path in blobs().iterdir():
        unused = not path.name.endswith(".part") and path.stat().st_nlink == 1
        stale = path.name.endswith(".part") and now - path.stat().st_mtime > PART_DAYS * 86400
        if unused or stale:
            path.unlink()
            gone += 1
    return gone


def request_out(item):
    return {"id": item.pk, "kind": item.kind, "payload": item.payload, "user": item.user,
            "created": item.created.isoformat(), "state": item.state, "detail": item.detail}


@sync.get("/pin")
def pin(allowed=Depends(token_ok)):
    """The score commit this cockpit runs (token only)."""
    return {"commit": settings.SCORE_COMMIT}


@sync.post("/lacking")
def lacking(body: Lacking, allowed=Depends(token_ok)):
    for sha, size in body.files.items():
        checked_sha(sha)
        if size < 0:
            raise HTTPException(400, f"{sha}: a size is never negative")
    if sum(body.files.values()) > cap_bytes():
        raise HTTPException(413, "the export is over the cap")
    return {"missing": [sha for sha in body.files if not (blobs() / sha).is_file()]}


@sync.put("/blobs/{sha}")
async def blob(sha: str, offset: int, size: int, request: Request, allowed=Depends(token_ok)):
    checked_sha(sha)
    if size < 0 or size > cap_bytes():
        raise HTTPException(413, "the file is over the cap")
    if (blobs() / sha).is_file():
        return {"have": size, "done": True}
    part = blobs() / f"{sha}.part"
    have = part.stat().st_size if part.exists() else 0
    if offset != have:
        return JSONResponse({"have": have}, status_code=409)
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > CHUNK:
            raise HTTPException(413, "a chunk is at most 4 MiB")
    have = appended(part, bytes(body), size) if body else have
    if have == size:
        part.touch()  # an empty file has sent no chunk, so its part may not exist yet
        finished(part, sha)
        return {"have": have, "done": True}
    return {"have": have, "done": False}


@sync.post("/commit")
def commit(body: Commit, allowed=Depends(token_ok)):
    name = checked_name(body.name)
    for path, sha in body.files.items():
        checked_path(path)
        checked_sha(sha)
    if "manifest.json" not in body.files:
        raise HTTPException(400, "the export has no manifest.json")
    absent = sorted({sha for sha in body.files.values() if not (blobs() / sha).is_file()})
    if absent:
        raise HTTPException(409, f"{len(absent)} files are not here yet: {', '.join(absent[:3])}")
    manifest = readable(body.files["manifest.json"])
    swapped(linked(name, body.files), name)
    one_store.exported_by(manifest.get("machine"), manifest.get("made_at"))
    gone = swept()
    from score.dashboard import state
    state.source().refresh()
    return {"current": name, "swept": gone}


def listed(state, kinds, skipped=()):
    """The requests in `state` (of `kinds` when given, less the ids `skipped`), oldest first."""
    found = SyncRequest.objects.filter(state=state).exclude(pk__in=skipped)
    return [request_out(item) for item in (found.filter(kind__in=kinds) if kinds else found).order_by("created")]


@sync.get("/requests")
def requests(state: str = "waiting", kind: str = "", skip: str = "", wait: float = 0.0, allowed=Depends(token_ok)):
    """The requests in `state`, of the comma-separated `kind`s when given, less the comma-separated ids `skip` (a
    Buy the listener left for the pass); with `wait` (seconds, at most LONGEST_WAIT) the answer waits until one is
    there or the time is up: the store's machine's listener (sync/listen.py) holds one such call open, so an owner's
    click reaches it within a POLL_SECONDS."""
    kinds = [name for name in kind.split(",") if name]
    skipped = [int(name) for name in skip.split(",") if name.isdigit()]
    deadline = time.monotonic() + min(max(wait, 0.0), LONGEST_WAIT)
    while True:
        found = listed(state, kinds, skipped)
        if found or time.monotonic() >= deadline:
            return found
        time.sleep(POLL_SECONDS)


@sync.post("/requests/{request_id}/claim")
def claim(request_id: int, request: Request, allowed=Depends(token_ok)):
    """Take a waiting request for the one caller that asks first (the listener or the sync pass); 409 when it was
    taken already, 423 when the caller is not the store's machine (sync/one_store.py: nothing is applied there)."""
    refused = one_store.claim_refusal(request.headers.get(MACHINE_HEADER, "").strip())
    if refused:
        raise HTTPException(423, refused)
    if not SyncRequest.objects.filter(pk=request_id, state="waiting").update(state="picked_up"):
        raise HTTPException(409, "taken already")
    return request_out(SyncRequest.objects.get(pk=request_id))


@sync.post("/requests/{request_id}/note")
def note(request_id: int, body: Note, allowed=Depends(token_ok)):
    """Words on a request still waiting (why the store's machine leaves it for its next pass); its state untouched,
    so a claim still takes it once. 409 once it is no longer waiting."""
    if not SyncRequest.objects.filter(pk=request_id, state="waiting").update(detail=body.detail[:4000]):
        raise HTTPException(409, "no longer waiting")
    return request_out(SyncRequest.objects.get(pk=request_id))


@sync.put("/batch-run")
async def batch_run(request: Request, allowed=Depends(token_ok)):
    """The run monitor's record of the batch now (state/batch_run.py), sent by the listener about every minute while a
    batch lives, kept beside the export (ExportedSource.batch_run reads the newer); only the store's machine's."""
    refused = one_store.claim_refusal(request.headers.get(MACHINE_HEADER, "").strip())
    if refused:
        raise HTTPException(423, refused)
    body = await request.body()
    if len(body) > CHUNK:
        raise HTTPException(413, "a batch record is at most 4 MiB")
    try:
        run = json.loads(body)
    except ValueError as unread:
        raise HTTPException(400, f"not JSON: {unread}") from unread
    if not isinstance(run, dict) or not isinstance(run.get("read_at"), str):
        raise HTTPException(400, "a batch record is an object with its read_at")
    folder = settings.SCORE_HOME / "request-files"
    folder.mkdir(parents=True, exist_ok=True)
    partial = folder / "batch-run.json.partial"
    partial.write_bytes(body)
    os.replace(partial, folder / "batch-run.json")
    return {"kept": run["read_at"]}


@sync.put("/request-files/{name}")
async def request_file(name: str, request: Request, allowed=Depends(token_ok)):
    """One picture a request brought back (`<sha>-360.jpg` or `<sha>-1280.jpg`, the sha the source picture's), kept
    in SCORE_HOME/request-files and served beside the export's (state/exported.py) until the next export holds it."""
    if not REQUEST_FILE.fullmatch(name):
        raise HTTPException(400, f"{name[:80]}: not a request's picture")
    body = await request.body()
    if len(body) > CHUNK:
        raise HTTPException(413, "a request's picture is at most 4 MiB")
    folder = settings.SCORE_HOME / "request-files"
    folder.mkdir(parents=True, exist_ok=True)
    partial = folder / f"{name}.partial"
    partial.write_bytes(body)
    os.replace(partial, folder / name)
    return {"kept": name}


@sync.post("/requests/{request_id}")
def report(request_id: int, body: Report, allowed=Depends(token_ok)):
    if body.state not in STATES:
        raise HTTPException(422, f"a state is one of {', '.join(STATES)}")
    item = SyncRequest.objects.filter(pk=request_id).first()
    if item is None:
        raise HTTPException(404, "no such request")
    item.state, item.detail, item.log_tail = body.state, body.detail[:4000], body.log_tail[-8000:]
    item.save()
    return request_out(item)
