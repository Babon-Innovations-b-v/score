"""The concept review (CONTEXT.md "concept review", owner 2026-10-20): one place's design page, opened from its card
on the Environment screen; three parts, all open as one cockpit of panels with one action rail, each panel enlarging
to fill the screen (the owner, 2026-10-21): the
concept (the picture shown, areas marked on it each with a note, a free note, Draw (or Redraw) priced per click, the
place's draws, and Pick (lock it for the design) or Unlock), the inventory (the reading's boxes on the picked concept,
its rows and what it skipped) and the plan (pages/plans.py).

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
from score.dashboard.pages import actions, cockpit, present
from score.dashboard.pages.models import SyncRequest, is_owner
from score.dashboard.state import groups, screens
from score.dashboard.state.files import file_ref
from score.dashboard.state.models import ConceptDraw, ConceptWording, WorldState

DRAW, PICK, WORDING = "concept-draw", "concept-pick", "concept-wording"
OPEN = ("waiting", "picked_up", "running")


def light_world(source):
    """The WorldState the clicks and the page's asking read: hosted the export's (read once a swap), local only the
    concept review's part and the shells (the whole state is the pages' to read)."""
    if not hasattr(source, "concept_review"):
        return source.world_state()
    found = source.hierarchy()
    return WorldState(made_at="", source=source.name, world="", engines=[], shells=found["shells"],
                      within=found["within"], **source.concept_review())


def checked_node(world, source, place):
    """`place` when it is a place or shell of the environment, or an inside place his kept plans name; else 404."""
    if place not in source.places() and place not in world.shells and place not in world.within:
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
    return [*world.concept_draws.get(place, []), *since_export(world, place)]


def since_export(world, place):
    """Hosted, the place's draws answered since its export (the source holds none of them yet); local, none. A draw
    from before the export that it does not hold (its place removed, say) is not one."""
    if not actions.hosted():
        return []
    held = {draw.picture.sha for draw in world.concept_draws.get(place, [])}
    return [draw for draw in answered_draws(place) if draw.picture.sha not in held and (draw.at or "") > world.made_at]


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


def wording_of(world, place):
    """The place's ConceptWording: the source's, and hosted, his own wording as his requests since its export left
    it (a first draw sent with his edited wording, or back to the generated one), unless refused."""
    found = world.concept_wordings.get(place) or ConceptWording()
    if not actions.hosted():
        return found
    since = [item for item in sorted([*asked(place, DRAW), *asked(place, WORDING)], key=lambda item: item.created)
             if item.state != "refused" and item.created.isoformat() > (world.made_at or "")
             and (item.kind == WORDING or (item.payload.get("wording") and not item.payload.get("base"))
                  or (item.payload.get("base") and item.state == "done" and corrected_in(item)))]
    if not since:
        return found
    sent = corrected_in(since[-1]) if since[-1].payload.get("base") else since[-1].payload.get("wording") or None
    return found.model_copy(update={"own": None if sent == found.generated else sent})


def corrected_in(item):
    """The corrected prompt an answered Redraw with notes carries (its detail), None without one."""
    try:
        return json.loads(item.detail or "{}").get("corrected")
    except ValueError:
        return None


def pending_of(place):
    """The owner's open draw request for the place, or None."""
    return next((item for item in reversed(asked(place, DRAW)) if item.state in OPEN), None)


def refused_of(place):
    """Why the place's newest draw request was refused, when it was; else None."""
    found = asked(place, DRAW)
    return (found[-1].detail or "refused") if found and found[-1].state == "refused" else None


def review_href(world, place):
    """The concept review page of a card's place, None once its concept is locked (unless the plan above has since
    changed its room: drawn again)."""
    return None if picked_of(world, place) and place not in world.plan_changed else f"/concept/{place}/"


def inventory_of(world, place, picked):
    """The place's scene inventory as its concept page shows it once picked (CONTEXT.md "scene inventory"): None
    before a pick; {state: made, rows [{name, count}]} when read from the picked draw; else {state: to read, older:
    whether the one there is from an older concept, which counts for nothing}."""
    if not picked:
        return None
    if screens.inventory_current(world, place, picked):
        return {"state": "made", "rows": world.inventories[place]["rows"]}
    return {"state": "to read", "older": place in world.inventories}


def reading_view(world, place, picked):
    """The place's scene inventory reading of its picked draw as its concept page shows it (score/review/reading.py),
    None without one: its rows numbered, each instance SAM 3 found as a box in shares of the picture (`at`: left, top,
    width, height in percent) and its `group` (objects, structure, terrain), its gaps grouped by row [{number, name,
    words}], what the agreement left out (`skipped`, each with its box and why; `merged`, each with the row it went
    into), what it cost and how long it took."""
    found = world.inventory_readings.get(place)
    if not found or found["concept"] != picked:
        return None
    wide, tall = found["size"]

    def at(box):
        return [round(100 * box[0] / wide, 2), round(100 * box[1] / tall, 2), round(100 * (box[2] - box[0]) / wide, 2),
                round(100 * (box[3] - box[1]) / tall, 2)]
    structural = set(found.get("structural", []))
    rows = [{**row, "number": number, "at": [at(box) for box in row["boxes"]],
             "group": "terrain" if row["terrain"] else "structure" if row["id"] in structural else "objects"}
            for number, row in enumerate(found["inventory"]["rows"], 1)]
    named = {row["id"]: row for row in rows}
    gaps = [{"number": named[row]["number"], "name": named[row]["name"],
             "words": [gap["words"] for gap in found["gaps"] if gap["row"] == row]}
            for row in dict.fromkeys(gap["row"] for gap in found["gaps"]) if row in named]
    skipped = [{**item, "at": item["box"] and at(item["box"])} for item in found.get("skipped", [])]
    merged = [{**item, "into": named[item["into"]]["name"]} for item in found.get("merged", []) if item["into"] in named]
    paid = found.get("cost") or {"euros": found["euros"]["total"], "seconds": sum(found["seconds"].values())}
    return {"rows": rows, "gaps": gaps, "skipped": skipped, "merged": merged, "euros": paid["euros"],
            "minutes": round(paid["seconds"] / 60, 1), "at": found["at"]}


def asked_to_hold(world, place, names):
    """[short name] of the places listed directly inside `place` (within.json), which its draw is asked to hold
    (score/review/concepts.py holding_words, the same for every place)."""
    return [world.shells.get(child) or names.get(child, child) for child, holder in world.within.items()
            if holder == place]


def context_pictures(world, wording, names):
    """[{place, name, picture}] of the picked concepts a draw of the place is drawn on (the layer above's, a joined
    place's: `wording.context`), each beside the draw so the owner can mark it too."""
    found = []
    for item in wording.context:
        picture = next((draw.picture for draw in draws_of(world, item["place"]) if draw.picture.sha == item["sha"]),
                       None)
        if picture:
            found.append({"place": item["place"], "picture": picture,
                          "name": world.shells.get(item["place"]) or names.get(item["place"], item["place"])})
    return found


def plan_part(world, place):
    """The design page's plan part (pages/plans.py): the plan shown, its JSON, its inside places' names by id, the
    picked concept, its prices and his open or refused plan request."""
    from score.dashboard.pages import plans
    review = plans.review_of(world, place)
    pending = plans.pending_of(place)
    names = groups.short_names(world)
    held = {hold["place"]: world.shells.get(hold["place"]) or names.get(hold["place"], present.place_title(hold["place"]))
            for hold in (review["plan"].get("holds") or [] if review else [])}
    return {"review": review, "plan_json": json.dumps(review["plan"]).replace("</", "<\\/") if review else "null",
            "plan_names": json.dumps(held).replace("</", "<\\/"),
            "plan_picture": plans.picture_of(world, place), "plan_euros": world.plan_revise_euros,
            "write_euros": world.plan_write_euros, "automatic": world.plan_automatic,
            "plan_pending": pending and pending.created.isoformat(), "plan_refused": plans.refused_of(place, review and review["at"])}


def concept_page(request, place):
    """The design page of one place (module docstring): its concept, its inventory and its plan, each a part."""
    source = state.source()
    world = source.world_state()
    checked_node(world, source, place)
    draws = draws_of(world, place)
    picked = picked_of(world, place)
    wanted = request.GET.get("draw") or picked
    shown = next((draw for draw in draws if draw.picture.sha == wanted), draws[-1] if draws else None)
    names = groups.short_names(world)
    pending = pending_of(place)
    wording = wording_of(world, place)
    inventory = inventory_of(world, place, picked)
    reading = picked and reading_view(world, place, picked)
    planned = plan_part(world, place)
    return render(request, "pages/concept.html", {
        "place": place, "name": world.shells.get(place) or names.get(place, present.place_title(place)),
        "holds": asked_to_hold(world, place, names), "draws": list(reversed(draws)), "shown": shown, "picked": picked, "replan": place in world.plan_changed, "euros": world.concept_draw_euros, "redraw_euros": world.concept_redraw_euros,
        "pending": pending and pending.created.isoformat(), "refused": refused_of(place),
        "wording": wording, "context": context_pictures(world, wording, names),
        "can": is_owner(request.user) and actions.decisions_on(),
        "approved": place in screens.approved_places(world), "inventory": inventory, "reading": reading,
        "named": world.plan_named.get(place, []), **planned})


def approved(source, place):
    """True once the place's design is approved (prepare's design record): its concept may no longer be unlocked."""
    return place in screens.approved_places(source.world_state())


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
    """POST {marks, note, base, euros, wording}: the owner's Draw click, its spend yes at `euros` (the price his
    button showed), a first draw sent with `wording` when he edited it (the store's machine keeps it as the place's
    own); JSON {said, request}, or {detail} when refused."""
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
        return JsonResponse({"detail": "refused: a draw of this scene is on its way"}, status=409)
    payload = {"marks": body.get("marks") or [], "context_marks": body.get("context_marks") or [],
               "note": str(body.get("note") or "")[:2000],
               "base": body.get("base") or None, "euros": body.get("euros")}
    if body.get("wording") and not payload["base"]:
        payload["wording"] = str(body["wording"])  # whole: the store's machine refuses one too long, never cut
    return JsonResponse({"said": "asked", "request": queued(request, place, DRAW, payload)})


@require_POST
def concept_generated(request, place):
    """POST: the owner's "back to generated", the place's own draw wording dropped; JSON {said}, or {detail}."""
    source = state.source()
    world = light_world(source)
    checked_node(world, source, place)
    if not is_owner(request.user):
        return JsonResponse({"detail": "only the owner words a draw"}, status=403)
    item = SyncRequest.objects.get(pk=queued(request, place, WORDING, {"wording": None}))
    if item.state == "refused":
        return JsonResponse({"detail": item.detail}, status=409)
    return JsonResponse({"said": item.detail or "asked"})


def draw_all(world):
    """The Environment's Draw all (owner, 2026-10-20): {places, count, each, euros (count times each), waiting (how
    many with no draw cannot be drawn now)} of every place or shell with no first draw from its current wording
    (the source's `concept_undrawn`) whose first draw can be made now, none answered since the export and none on its
    way; None when there is none or no measured price."""
    places = [node for node in world.concept_undrawn if not since_export(world, node) and not pending_of(node)]
    each = world.concept_draw_euros
    if not places or each is None:
        return None
    euros = round(len(places) * each, 2)
    return {"places": places, "count": len(places), "each": each, "euros": euros,
            "waiting": len(world.concept_unready), "body": json.dumps({"places": places, "euros": euros})}


def drawing():
    """How many of the owner's draws are on their way (the Environment reads itself again until none is)."""
    return SyncRequest.objects.filter(kind=DRAW, state__in=OPEN).count()


def card_state(world, node):
    """{drawing, refused, replan} of a card: drawing while a draw of its place or shell, or of a place within it, is on
    its way; refused, why its own newest draw was refused (None when it was not); replan, its pick drawn on another
    room than the layer above's plan gives it now."""
    on_way = {item.payload.get("place") for item in SyncRequest.objects.filter(kind=DRAW, state__in=OPEN)}
    return {"drawing": node in on_way or bool(cockpit.inside_of(world, node, on_way)), "refused": refused_of(node),
            "replan": node in world.plan_changed}


def newest_pictures(world):
    """{place: its picked draw's picture, else its newest} of the places the concept review drew, hosted with those
    answered since the export, so a card shows a draw as soon as it lands."""
    found = {}
    for place in {*world.concept_draws, *(item.payload.get("place") for item in
                                          SyncRequest.objects.filter(kind=DRAW, state="done"))} - {None}:
        draws, picked = draws_of(world, place), picked_of(world, place)
        if ((not picked and place in world.concept_undrawn) or place in world.plan_changed) \
                and not since_export(world, place):
            continue  # only draws from an older wording or on a room since changed: out of date, never on its card
        if draws:
            found[place] = next((draw.picture for draw in draws if draw.picture.sha == picked), draws[-1].picture)
    return found


@require_POST
def concept_draw_all(request):
    """POST {places, euros}: the owner's Draw all click, his one spend yes for exactly those first draws at that
    total (draw_all as his page showed it); each queued as its own draw at the per-draw price, applied side by side
    on the store's machine, each refused there once the price moved or its place has a draw. JSON {said, requests},
    or {detail} when refused."""
    source = state.source()
    world = light_world(source)
    body = body_of(request)
    if not is_owner(request.user):
        return JsonResponse({"detail": "only the owner draws"}, status=403)
    if body is None:
        return JsonResponse({"detail": "refused: not a draw request"}, status=422)
    shown = draw_all(world)
    if shown is None or sorted(map(str, body.get("places") or [])) != sorted(shown["places"]):
        return JsonResponse({"detail": "refused: the scenes to draw changed; read the page again"}, status=409)
    try:
        euros = float(body.get("euros"))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "refused: no total"}, status=422)
    if abs(euros - shown["euros"]) > 0.005:
        return JsonResponse({"detail": f"refused: the total shown, EUR {euros:.2f}, is not today's "
                                       f"(EUR {shown['euros']:.2f}); read the page again"}, status=409)
    together = {"count": shown["count"], "euros": shown["euros"]}
    asked = [queued(request, place, DRAW, {"marks": [], "note": "", "base": None, "euros": shown["each"],
                                           "all": together}) for place in shown["places"]]
    return JsonResponse({"said": f"asked {len(asked)} draws", "requests": asked})


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
        return JsonResponse({"detail": "refused: that is no draw of this scene"}, status=422)
    if sha is None and approved(source, place):
        return JsonResponse({"detail": "refused: the design is approved; its concept stays locked"}, status=409)
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
