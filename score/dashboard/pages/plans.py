"""The plan review (CONTEXT.md "plan", "design"; score/review/plans.py): one place's plan page, reached from its card
and its concept page once its scene inventory counts. The plan is made automatically after the pick (owner,
2026-10-21: the pick is the approval); the page is for inspecting and fixing it. The plan drawn top down beside the
picked concept: its outline, doors and where each leads, items as labelled boxes tied to their inventory rows,
keep-clear zones, standing spots, and for a place holding others the inside places it lays out (a list beside it:
rename, remove, add, the row each stands in). He drags and resizes items and inside places, moves doors along their
walls, marks areas on the plan or the concept with a note each; Keep keeps his plan as his own (what follows is made
from it), Correct with notes sends the marks and notes to the prompt model (priced, his click the spend yes).

Each click is the owner's request (SyncRequest kinds in sync/applying.PLAN_KINDS), applied on the store's machine:
locally at once (a correction in a thread: a model call), hosted by its listener. Hosted, his plan kept since the
export shows at once (`review_of`)."""
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from score.dashboard import state
from score.dashboard.pages import actions, concepts, present
from score.dashboard.pages.models import SyncRequest, is_owner
from score.dashboard.state import groups

EDIT, NAMED, REVISE = "plan-edit", "plan-named", "plan-revise"
SLOW = (REVISE,)  # applied in a thread locally: a model call


def review_of(world, place):
    """{plan, how, at} the page shows: the source's PlanReview, and hosted, his newest plan kept since its export
    (what he sent), unless refused; None while the place has no plan."""
    review = world.plan_reviews.get(place)
    if review is None:
        return None
    since = [item for item in concepts.asked(place, EDIT)
             if item.state != "refused" and item.created.isoformat() > (world.made_at or "")]
    if actions.hosted() and since:
        return {"plan": since[-1].payload["plan"], "how": "edited", "at": since[-1].created.isoformat()}
    return {"plan": review.plan, "how": review.how, "at": review.at}


def pending_of(place):
    """His open correction of the place, or None."""
    return next((item for kind in SLOW for item in reversed(concepts.asked(place, kind))
                 if item.state in concepts.OPEN), None)


def refused_of(place):
    """Why his newest plan request of the place was refused, or None."""
    found = sorted([item for kind in (EDIT, REVISE) for item in concepts.asked(place, kind)],
                   key=lambda item: item.created)
    return found[-1].detail if found and found[-1].state == "refused" else None


def picture_of(world, place):
    """The place's picked concept draw's picture (FileRef), None when none is picked."""
    picked = concepts.picked_of(world, place)
    return next((draw.picture for draw in concepts.draws_of(world, place) if draw.picture.sha == picked), None)


def plan_page(request, place):
    """The plan review page of one place (module docstring)."""
    source = state.source()
    world = source.world_state()
    concepts.checked_node(world, source, place)
    names = groups.short_names(world)
    review = review_of(world, place)
    pending = pending_of(place)
    return render(request, "pages/plan.html", {
        "place": place, "name": world.shells.get(place) or names.get(place, present.place_title(place)),
        "review": review, "plan_json": json.dumps(review["plan"]).replace("</", "<\\/") if review else "null",
        "picture": picture_of(world, place), "euros": world.plan_revise_euros,
        "inventory": world.inventories.get(place), "pending": pending and pending.created.isoformat(),
        "refused": refused_of(place), "can": is_owner(request.user) and actions.decisions_on()})


def asked_of(request, place, kind):
    """The owner's plan request of `kind` for `place` from its POST body; (JsonResponse refusal or None, body)."""
    source = state.source()
    world = concepts.light_world(source)
    concepts.checked_node(world, source, place)
    if not is_owner(request.user):
        return JsonResponse({"detail": "only the owner plans"}, status=403), None
    body = concepts.body_of(request)
    if body is None:
        return JsonResponse({"detail": "refused: not a plan request"}, status=422), None
    if kind in SLOW and pending_of(place):
        return JsonResponse({"detail": "refused: a correction of this place is on its way"}, status=409), None
    return None, body


def queued(request, place, kind, payload):
    """The owner's request for the store's machine (local: a correction in a thread, the rest at once);
    JsonResponse {said, request}, or {detail} when refused at once."""
    item = SyncRequest.objects.create(kind=kind, user=request.user.username, payload={"place": place, **payload})
    if not actions.hosted():
        (concepts.in_background if kind in SLOW else concepts.applied_here)(item.pk)
        item.refresh_from_db()
    if item.state == "refused":
        return JsonResponse({"detail": item.detail}, status=409)
    return JsonResponse({"said": item.detail or "asked", "request": item.pk})


@require_POST
def plan_edit(request, place):
    """POST {plan}: his plan as he left it, kept as his own."""
    refusal, body = asked_of(request, place, EDIT)
    return refusal or queued(request, place, EDIT, {"plan": body.get("plan")})


@require_POST
def plan_revise(request, place):
    """POST {marks, context_marks, note, euros}: his Correct with notes, his spend yes at `euros`."""
    refusal, body = asked_of(request, place, REVISE)
    return refusal or queued(request, place, REVISE, {
        "marks": body.get("marks") or [], "context_marks": body.get("context_marks") or [],
        "note": str(body.get("note") or "")[:2000], "euros": body.get("euros")})


@require_POST
def plan_named(request, place):
    """POST {names}: the inside places he names up front on the place's concept page."""
    refusal, body = asked_of(request, place, NAMED)
    return refusal or queued(request, place, NAMED, {"names": [str(name) for name in body.get("names") or []][:40]})


def plan_state(request, place):
    """GET {pending, refused}: the page asks until its correction is answered."""
    source = state.source()
    concepts.checked_node(concepts.light_world(source), source, place)
    return JsonResponse({"pending": pending_of(place) is not None, "refused": refused_of(place)})
