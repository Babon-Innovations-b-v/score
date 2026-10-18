"""The hosted dashboard's sync endpoints, signed in by SCORE_SYNC_TOKEN (never a session): the store's machine pushes
its state export and pulls the owner's requests. No inbound connection to the store's machine, ever.

The export travels content-addressed (owner, 2026-10-18: the whole export each pass did not fit the link): the store's
machine asks which files the hosted side lacks, sends only those, one small gzip chunk per request, and then commits
the export as a list of {path: sha256}; the hosted side builds it from hard links to the files it holds.

    POST /api/sync/lacking          {files: {sha256: size}} -> {missing: [sha256]}
    PUT  /api/sync/blobs/{sha}?offset=N&size=S   one gzip chunk of the file, at offset N of its S bytes
    POST /api/sync/commit           {name: <made_at, no colons>, files: {path: sha256}}: swapped in whole
    GET  /api/sync/requests?state=waiting
    POST /api/sync/requests/{id}    {state: picked_up|running|done|refused, detail, log_tail}
"""
import hashlib
import hmac
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

sync = APIRouter()
STATES = ("picked_up", "running", "done", "refused")
KEPT = 2
SHORTEST_TOKEN = 32
CHUNK = 4 * 1024 * 1024  # the most one compressed chunk may carry; the client sends 2 MiB of the file a chunk
SHA = re.compile(r"[0-9a-f]{64}")
PART_DAYS = 1.0


class Report(BaseModel):
    state: str
    detail: str = ""
    log_tail: str = ""


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
    swapped(linked(name, body.files), name)
    gone = swept()
    from score.dashboard import state
    state.source().refresh()
    return {"current": name, "swept": gone}


@sync.get("/requests")
def requests(state: str = "waiting", allowed=Depends(token_ok)):
    return [request_out(item) for item in SyncRequest.objects.filter(state=state).order_by("created")]


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
