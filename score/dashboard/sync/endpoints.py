"""The hosted dashboard's sync endpoints, signed in by SCORE_SYNC_TOKEN (never a session): the store's machine pushes
its state export and pulls the owner's requests. No inbound connection to the store's machine, ever.

    PUT  /api/sync/export           a tar.gz of one export, at most SCORE_EXPORT_MAX_MB
    GET  /api/sync/requests?state=waiting
    POST /api/sync/requests/{id}    {state: picked_up|running|done|refused, detail, log_tail}
"""
import hmac
import io
import os
import pathlib
import shutil
import tarfile

from django.conf import settings
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from score.dashboard.pages.models import SyncRequest

sync = APIRouter()
STATES = ("picked_up", "running", "done", "refused")
KEPT = 2
SHORTEST_TOKEN = 32


class Report(BaseModel):
    state: str
    detail: str = ""
    log_tail: str = ""


def token_ok(request: Request):
    """FastAPI dependency: the bearer token equals SCORE_SYNC_TOKEN (32+ characters), compared in constant time."""
    expected = settings.SCORE_SYNC_TOKEN
    given = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if len(expected) < SHORTEST_TOKEN or not hmac.compare_digest(given.encode(), expected.encode()):
        raise HTTPException(401, "a sync needs the sync token")
    return True


def safe_members(archive, cap):
    """The archive's members when each is a regular file or folder under a relative path, and their sizes fit
    `cap` bytes; else ValueError."""
    total = 0
    for member in archive.getmembers():
        path = pathlib.PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"{member.name}: only relative paths inside the export")
        if not (member.isfile() or member.isdir()):
            raise ValueError(f"{member.name}: only regular files and folders")
        total += member.size
        if total > cap:
            raise ValueError("the export is over the cap")
    return archive.getmembers()


def unpack(body, exports, cap):
    """Unpack a tar.gz export into exports/<made_at>.partial, then rename it and swap exports/current to it at
    once; keep the KEPT newest. The made_at folder's name."""
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as archive:
        members = safe_members(archive, cap)
        names = {pathlib.PurePosixPath(member.name).parts[0] for member in members}
        if len(names) != 1:
            raise ValueError("the export holds one folder, named by its made_at")
        name = names.pop()
        if name in ("current", "") or name.endswith(".partial"):
            raise ValueError(f"{name}: not an export's name")
        partial = exports / f"{name}.partial"
        shutil.rmtree(partial, ignore_errors=True)
        partial.mkdir(parents=True)
        for member in members:
            inner = pathlib.PurePosixPath(member.name).relative_to(name)
            target = partial.joinpath(*inner.parts) if inner.parts else partial
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, open(target, "wb") as written:
                shutil.copyfileobj(source, written)
    if not (partial / "manifest.json").is_file():
        shutil.rmtree(partial)
        raise ValueError("the export has no manifest.json")
    final = exports / name
    shutil.rmtree(final, ignore_errors=True)
    partial.rename(final)
    link = exports / "current.partial-link"
    link.unlink(missing_ok=True)
    link.symlink_to(name)
    os.replace(link, exports / "current")
    kept = sorted(path for path in exports.iterdir() if path.is_dir() and not path.is_symlink()
                  and not path.name.endswith(".partial"))
    for old in kept[:-KEPT]:
        shutil.rmtree(old)
    return name


def request_out(item):
    return {"id": item.pk, "kind": item.kind, "payload": item.payload, "user": item.user,
            "created": item.created.isoformat(), "state": item.state, "detail": item.detail}


@sync.put("/export")
async def export(request: Request, allowed=Depends(token_ok)):
    cap = int(settings.SCORE_EXPORT_MAX_MB * 1024 * 1024)
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > cap:
            raise HTTPException(413, "the export is over the cap")
    exports = settings.SCORE_HOME / "export"
    exports.mkdir(parents=True, exist_ok=True)
    try:
        name = unpack(bytes(body), exports, cap)
    except (ValueError, tarfile.TarError) as refused:
        raise HTTPException(400, str(refused)) from refused
    from score.dashboard import state
    state.source().refresh()
    return {"current": name}


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
