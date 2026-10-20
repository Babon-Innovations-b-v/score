"""The concept review (CONTEXT.md "concept review", owner 2026-10-20): one place's concept page, opened from its card
on the Environment screen while its concept is not locked. The picture shown, areas marked on it each with a note, a
free note, Draw (or Redraw) priced per click, the place's draws, and Pick (lock it for the design) or Unlock.

Each click is the owner's request (a SyncRequest of kind concept-draw or concept-pick, sync/applying.py), applied by
the store's machine: locally at once in a thread of this process, hosted by its listener (sync/listen.py) within a
second of the click. The draw's answer comes back on the request (its record as the detail, its picture in
SCORE_HOME/request-files), so the hosted page shows it before the next export holds it; the page asks
`/concept/<place>/state/` until the request is answered, then reads itself again."""
import json
import threading

from django.db import close_old_connections
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from score.dashboard import state
from score.dashboard.pages import actions, present
from score.dashboard.pages.models import SyncRequest, is_owner
from score.dashboard.state import groups
from score.dashboard.state.files import file_ref
from score.dashboard.state.models import ConceptDraw, WorldState

DRAW, PICK = "concept-draw", "concept-pick"
OPEN = ("waiting", "picked_up", "running")


def light_world(source):
    """The WorldState the clicks and the page's asking read: hosted the export's (read once a swap), local only the
    concept review's part and the shells (the whole state is the pages' to read)."""
    if not hasattr(source, "concept_review"):
        return source.world_state()
    return WorldState(made_at="", source=source.name, world="", engines=[], shells=source.hierarchy()["shells"],
                      **source.concept_review())


def checked_node(world, source, place):
    """`place` when it is a place or shell of the environment; else 404."""
    if place not in source.places() and place not in world.shells:
        raise Http404(f"no place {place}")
    return place


def asked(place, kind):
    """The owner's requests of `kind` for `place`, oldest first."""
    return list(SyncRequest.objects.filter(kind=kind, payload__place=place).order_by("created"))


def answered_draws(place):
    """The draws the store's machine answered on this side's requests (newest export may not hold them yet)."""
    found = []
    for item in asked(place, DRAW):
        if item.state != "done":
            continue
        try:
            record = json.loads(item.detail)
        except ValueError:
            continue
        found.append(ConceptDraw(picture=file_ref(record["sha"], record["name"], 0),
                                 **{name: record.get(name) for name in ("at", "by", "euros", "base")},
                                 marks=record.get("marks") or [], note=record.get("note") or ""))
    return found


def draws_of(world, place):
    """The place's draws, oldest first: the source's, and hosted, those answered since its export."""
    found = list(world.concept_draws.get(place, []))
    if actions.hosted():
        held = {draw.picture.sha for draw in found}
        found += [draw for draw in answered_draws(place) if draw.picture.sha not in held]
    return found


def picked_of(world, place):
    """The sha of the place's picked draw, or None: the source's, and hosted, the owner's newest pick request since
    its export unless it was refused."""
    picked = world.concept_picked.get(place)
    if actions.hosted():
        since = [item for item in asked(place, PICK) if item.state != "refused"
                 and item.created.isoformat() > (world.made_at or "")]
        if since:
            picked = since[-1].payload.get("sha") or None
    return picked


def pending_of(place):
    """The owner's open draw request for the place, or None."""
    return next((item for item in reversed(asked(place, DRAW)) if item.state in OPEN), None)


def refused_of(place):
    """Why the place's newest draw request was refused, when it was; else None."""
    found = asked(place, DRAW)
    return (found[-1].detail or "refused") if found and found[-1].state == "refused" else None


def review_href(world, place):
    """The concept review page of a card's place, None once its concept is locked."""
    return None if picked_of(world, place) else f"/concept/{place}/"


def concept_page(request, place):
    """The concept review page of one place (module docstring)."""
    source = state.source()
    world = source.world_state()
    checked_node(world, source, place)
    draws = draws_of(world, place)
    picked = picked_of(world, place)
    wanted = request.GET.get("draw") or picked
    shown = next((draw for draw in draws if draw.picture.sha == wanted), draws[-1] if draws else None)
    names = groups.short_names(world)
    pending = pending_of(place)
    return render(request, "pages/concept.html", {
        "place": place, "name": world.shells.get(place) or names.get(place, present.place_title(place)),
        "draws": list(reversed(draws)), "shown": shown, "picked": picked, "euros": world.concept_draw_euros,
        "pending": pending and pending.created.isoformat(), "refused": refused_of(place),
        "can": is_owner(request.user) and actions.decisions_on()})


def body_of(request):
    try:
        found = json.loads(request.body or b"{}")
    except ValueError:
        return None
    return found if isinstance(found, dict) else None


def applied_here(item_id):
    """Apply one of this cockpit's own requests in this process (local mode) and record its answer on it."""
    from score.dashboard.sync import applying
    close_old_connections()
    try:
        item = SyncRequest.objects.get(pk=item_id)
        item.state = "running"
        item.save()
        applied = applying.apply({"id": item.pk, "kind": item.kind, "payload": item.payload, "user": item.user},
                                 state.source())
        item.state, item.detail = applied.state, applied.detail[:4000]
        item.save()
    finally:
        close_old_connections()


def queued(request, place, kind, payload):
    """The owner's request for the store's machine; local mode applies it here (a draw in a thread, it takes the
    model's time); its id."""
    item = SyncRequest.objects.create(kind=kind, user=request.user.username, payload={"place": place, **payload})
    if not actions.hosted():
        (in_background if kind == DRAW else applied_here)(item.pk)
    return item.pk


def in_background(item_id):
    threading.Thread(target=applied_here, args=(item_id,), daemon=True).start()


@require_POST
def concept_draw(request, place):
    """POST {marks, note, base, euros}: the owner's Draw click, its spend yes at `euros` (the price his button
    showed); JSON {said, request}, or {detail} when refused."""
    source = state.source()
    world = light_world(source)
    checked_node(world, source, place)
    body = body_of(request)
    if not is_owner(request.user):
        return JsonResponse({"detail": "only the owner draws"}, status=403)
    if body is None:
        return JsonResponse({"detail": "refused: not a draw request"}, status=422)
    if picked_of(world, place):
        return JsonResponse({"detail": "refused: the concept is locked; unlock it first"}, status=409)
    if pending_of(place):
        return JsonResponse({"detail": "refused: a draw of this place is on its way"}, status=409)
    payload = {"marks": body.get("marks") or [], "note": str(body.get("note") or "")[:2000],
               "base": body.get("base") or None, "euros": body.get("euros")}
    return JsonResponse({"said": "asked", "request": queued(request, place, DRAW, payload)})


@require_POST
def concept_pick(request, place):
    """POST {sha}: the owner's Pick of a draw (sha None: his unlock); JSON {said}, or {detail} when refused."""
    source = state.source()
    world = light_world(source)
    checked_node(world, source, place)
    body = body_of(request)
    if not is_owner(request.user):
        return JsonResponse({"detail": "only the owner picks"}, status=403)
    if body is None:
        return JsonResponse({"detail": "refused: not a pick"}, status=422)
    sha = body.get("sha") or None
    if sha and sha not in {draw.picture.sha for draw in draws_of(world, place)}:
        return JsonResponse({"detail": "refused: that is no draw of this place"}, status=422)
    item = SyncRequest.objects.get(pk=queued(request, place, PICK, {"sha": sha}))
    if item.state == "refused":
        return JsonResponse({"detail": item.detail}, status=409)
    return JsonResponse({"said": item.detail or "asked"})


def concept_state(request, place):
    """GET: {pending (a draw on its way), refused (why the newest draw was refused), newest (the newest draw's sha)}
    for the page to ask until its draw is answered."""
    source = state.source()
    world = light_world(source)
    checked_node(world, source, place)
    draws = draws_of(world, place)
    return JsonResponse({"pending": pending_of(place) is not None, "refused": refused_of(place),
                         "newest": draws[-1].picture.sha if draws else None})
