"""The typed JSON API under /api (the pages' live parts and later agents call it), and the file routes the pages
use (/files, /thumbs, /web, /healthz). One sign-in with the pages: api/deps.py."""
from django.conf import settings
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from score.dashboard import state
from score.dashboard.api.deps import owner_only, signed_in
from score.dashboard.launch import guard
from score.dashboard.pages import actions
from score.dashboard.pages.models import BasketItem, ChangeRequest, Launch, Plan
from score.dashboard.state.files import content_type
from score.dashboard.state.models import PlaceDetail, Spend, StepDetail, WorldState

api = APIRouter()
files = APIRouter()
IMMUTABLE = {"Cache-Control": "private, max-age=31536000, immutable"}


class ChangeIn(BaseModel):
    place: str | None = None
    stage: str
    words: str
    output: str = ""


class ChangeOut(BaseModel):
    id: int
    user: str
    place: str
    stage: str
    node: str
    words: str
    created: str
    state: str


class DecisionIn(BaseModel):
    node: str
    output: str
    decision: str
    reason: str = ""
    worse_reason: str | None = None


class Said(BaseModel):
    said: str


class BasketIn(BaseModel):
    place: str | None = None
    stage: str


class BasketOut(BaseModel):
    id: int
    place: str | None
    stage: str
    added_by: str


class PlanOut(BaseModel):
    id: int
    state: str
    basket_hash: str
    started: str
    finished: str | None
    body: dict
    error: str


class LaunchIn(BaseModel):
    plan_id: int
    confirm: bool
    rebuy_reason: str | None = None


class LaunchOut(BaseModel):
    id: int
    plan_id: int
    by: str
    at: str
    state: str
    handles: list
    result: str


def change_out(change):
    return ChangeOut(id=change.pk, user=change.user, place=change.place, stage=change.stage, node=change.node,
                     words=change.words, created=change.created.isoformat(), state=change.state)


def plan_out(plan):
    return PlanOut(id=plan.pk, state=plan.state, basket_hash=plan.basket_hash, started=plan.started.isoformat(),
                   finished=plan.finished.isoformat() if plan.finished else None, body=plan.body, error=plan.error)


def launch_out(record):
    return LaunchOut(id=record.pk, plan_id=record.plan_id, by=record.by, at=record.at.isoformat(), state=record.state,
                     handles=record.handles, result=record.result)


def split_node(node):
    stage, _, place = node.partition("@")
    return (place or None), stage


@api.get("/state", response_model=WorldState)
def world_state(user=Depends(signed_in)):
    return state.source().world_state(actions.spend())


@api.get("/places/{place}", response_model=PlaceDetail)
def place_detail(place: str, user=Depends(signed_in)):
    source = state.source()
    if place not in source.places():
        raise HTTPException(404, f"no place {place}")
    return source.place_detail(place)


def step(place, stage):
    found = state.source().step_detail(place, stage)
    if found is None:
        raise HTTPException(404, f"no step {stage} at {place or 'the world'}")
    return found


@api.get("/places/{place}/steps/{stage}", response_model=StepDetail)
def place_step(place: str, stage: str, user=Depends(signed_in)):
    return step(place, stage)


@api.get("/world/steps/{stage}", response_model=StepDetail)
def world_step(stage: str, user=Depends(signed_in)):
    return step(None, stage)


@api.get("/spend", response_model=Spend)
def spend(user=Depends(signed_in)):
    return actions.spend()


@api.get("/requests", response_model=list[ChangeOut])
def change_list(user=Depends(signed_in)):
    return [change_out(change) for change in ChangeRequest.objects.all()[:200]]


@api.post("/requests", response_model=ChangeOut)
def change_record(body: ChangeIn, user=Depends(signed_in)):
    step(body.place, body.stage)
    if not body.words.strip():
        raise HTTPException(422, "say what should change")
    return change_out(actions.record_change(user.username, body.place, body.stage, body.output, body.words.strip()))


@api.post("/decisions", response_model=Said)
def decision(body: DecisionIn, user=Depends(owner_only)):
    if body.decision not in ("accept", "reject"):
        raise HTTPException(422, "a decision is accept or reject")
    place, stage = split_node(body.node)
    said = actions.decide(user.username, place, stage, body.output, body.decision, body.reason,
                          body.worse_reason or "")
    if said.startswith(("refused", "decisions are off")):
        raise HTTPException(409, said)
    return Said(said=said)


@api.get("/basket/items", response_model=list[BasketOut])
def basket_list(user=Depends(owner_only)):
    return [BasketOut(id=item.pk, place=item.place or None, stage=item.stage, added_by=item.added_by)
            for item in BasketItem.objects.all()]


@api.post("/basket/items", response_model=list[BasketOut])
def basket_add(body: BasketIn, user=Depends(owner_only)):
    step(body.place, body.stage)
    actions.queue(user.username, body.place, [body.stage], state.source())
    return basket_list(user)


@api.delete("/basket/items/{item_id}", response_model=list[BasketOut])
def basket_remove(item_id: int, user=Depends(owner_only)):
    BasketItem.objects.filter(pk=item_id).delete()
    return basket_list(user)


@api.post("/basket/plan", response_model=Said)
def basket_plan(user=Depends(owner_only)):
    return Said(said=actions.start_plan(user.username, None))


@api.get("/plans/{plan_id}", response_model=PlanOut)
def plan_read(plan_id: int, user=Depends(owner_only)):
    plan = Plan.objects.filter(pk=plan_id).first()
    if plan is None:
        raise HTTPException(404, "no such plan")
    return plan_out(plan)


@api.post("/launches", response_model=Said)
def launch(body: LaunchIn, user=Depends(owner_only)):
    plan = Plan.objects.filter(pk=body.plan_id).first()
    if plan is None:
        raise HTTPException(404, "no such plan")
    record, said = actions.launch(user.username, plan, body.confirm, body.rebuy_reason or "")
    if record is None and said.startswith("refused"):
        raise HTTPException(409, said)
    return Said(said=said)


@api.get("/launches", response_model=list[LaunchOut])
def launch_list(user=Depends(signed_in)):
    return [launch_out(guard.polled(record)) for record in Launch.objects.all()[:50]]


@api.get("/launches/{launch_id}", response_model=LaunchOut)
def launch_read(launch_id: int, user=Depends(signed_in)):
    record = Launch.objects.filter(pk=launch_id).first()
    if record is None:
        raise HTTPException(404, "no such launch")
    return launch_out(guard.polled(record))


@files.get("/healthz")
def healthz():
    return {"ok": True, "mode": settings.SCORE_MODE}


@files.get("/files/{sha}")
def file(sha: str, user=Depends(signed_in)):
    found = state.source().file(sha)
    if found is None or not found[1].is_file():
        raise HTTPException(404, "no such file")
    name, path = found
    return FileResponse(path, media_type=content_type(name), headers=IMMUTABLE)


@files.get("/thumbs/{sha}.jpg")
def thumb(sha: str, user=Depends(signed_in)):
    path = state.source().thumb_path(sha)
    if path is None:
        raise HTTPException(404, "no such picture")
    return FileResponse(path, media_type="image/jpeg", headers=IMMUTABLE)


@files.get("/web/{place}/{name}")
def web_copy(place: str, name: str, user=Depends(signed_in)):
    """A place's fresh 3D web copy (its preview, its whole copy, its sidecar): local or from the export."""
    if name not in (f"{place}.glb", f"{place}-light.glb", f"{place}.json"):
        raise HTTPException(404, "no such web copy")
    path = state.source().web3d_file(place, name)
    if path is None:
        raise HTTPException(404, "this place has no 3D copy yet: python -m score.dashboard web3d <place>")
    return FileResponse(path, media_type=content_type(name))
