"""The dashboard's pages: visual first (a picture per piece, labelled plans, few words); node ids only in a small
details fold. Every page reads the source of this mode (state.source()); actions go through the owner's checks."""
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from score.dashboard import state
from score.dashboard.launch import guard
from score.dashboard.pages import actions, seen
from score.dashboard.pages.models import BasketItem, ChangeRequest, Launch, Plan, SyncRequest, is_owner
from score.dashboard.state import costs, groups

def everywhere(request):
    """What every page shows: the mode, when the store (or export) was read, and what this user may do."""
    source = state.source()
    return {"mode": settings.SCORE_MODE, "hosted": settings.SCORE_MODE == settings.HOSTED,
            "read_at": source.read_at() if request.user.is_authenticated else None,
            "export_age": source.age_words() if hasattr(source, "age_words") else None,
            "owner": is_owner(request.user), "decisions_on": actions.decisions_on(),
            "decisions_off_why": actions.decisions_off_why(), "proxy_mode": settings.SCORE_PROXY_MODE,
            "basket_count": BasketItem.objects.count() if request.user.is_authenticated else 0}


def money_bar(spent, reserved, likely, high, ceiling):
    """The four parts of the one money bar as shares of the stop (percent), or None without a stop or a reading."""
    if not ceiling or spent is None or reserved is None:
        return None
    parts = [("spent", spent), ("reserved", reserved), ("likely", likely or 0.0),
             ("high", max(0.0, (high or 0.0) - (likely or 0.0)))]
    return [{"name": name, "euros": round(value, 2), "share": min(100.0, 100.0 * value / ceiling)}
            for name, value in parts]


def basket_high():
    plan = Plan.objects.filter(state="ready").first()
    return plan.body["money"] if plan and plan.basket_hash == guard.basket_hash(BasketItem.objects.all()) else None


def with_marks(layers):
    """Set each step card's owner mark (pages/seen.py) in place; the layers."""
    cards = [card for layer in layers for card in layer.steps]
    found = seen.marks([(card.node, card.output) for card in cards])
    for card in cards:
        card.mark = found.get(card.node)
    return layers


def board(request):
    source = state.source()
    world = source.world_state(actions.spend())
    for engine in world.engines:
        for style in engine.styles:
            for card in style.places:
                with_marks(card.layers)
    planned = basket_high() or {}
    bar = money_bar(world.spend.spent, world.spend.reserved, planned.get("likely"), planned.get("high"),
                    world.spend.ceiling)
    queued = {(item.place, item.stage) for item in BasketItem.objects.all()}
    return render(request, "pages/board.html", {"world": world, "bar": bar, "queued_places": {
        place for place, _ in queued}, "planned": planned})


def place_page(request, place):
    source = state.source()
    if place not in source.places():
        raise Http404(f"no place {place}")
    detail = source.place_detail(place)
    with_marks(detail.layers)
    return render(request, "pages/place.html", {"detail": detail, "requests": ChangeRequest.objects.filter(
        place=place)[:10], "snapshot": actions.snapshot_states()})


def step_page(request, stage, place=None):
    source = state.source()
    detail = source.step_detail(place, stage)
    if detail is None:
        raise Http404(f"no step {stage} at {place or 'the world'}")
    snapshot = actions.snapshot_states()
    shown = (detail.accepted or detail.waiting)
    if shown and is_owner(request.user):
        seen.looked(request.user.username, detail.node, shown.output)
    detail.mark = seen.mark(detail.node, shown.output) if shown else None
    films = any(file.kind == "film" for file in [*detail.files, *detail.waiting_files])
    return render(request, "pages/step.html", {
        "film_fps": film_fps(source, place) if films else None,
        "output_picture": next((file for file in detail.files if file.kind == "image"), None),
        "detail": detail, "requests": ChangeRequest.objects.filter(node=detail.node)[:10],
        "sync_requests": SyncRequest.objects.filter(payload__node=detail.node)[:10],
        "queued": BasketItem.objects.filter(place=place or "", stage=stage).exists(),
        "next_steps": detail.readers, "snapshot_state": snapshot.get("nodes", {}).get(detail.node),
        "snapshot_at": snapshot.get("made_at")})


def film_fps(source, place):
    """The frames a second of a place's films (its stage's own), or None for the world or an unknown place."""
    if not place:
        return None
    if hasattr(source, "film_fps"):
        return source.film_fps(place)
    detail = source.place_detail(place)
    return detail.film_fps if detail else None


def step_url(place, stage):
    return f"/place/{place}/step/{stage}/" if place else f"/world/step/{stage}/"


@require_POST
def step_request(request, stage, place=None):
    """Record what should change about a step's output."""
    words = request.POST.get("words", "").strip()
    if not words:
        messages.error(request, "say what should change")
    else:
        actions.record_change(request.user.username, place, stage, request.POST.get("output", ""), words)
        messages.success(request, "recorded: an agent or the owner turns it into a change")
    return redirect(step_url(place, stage))


@require_POST
def step_decide(request, stage, place=None):
    """The owner's accept or reject of an output."""
    if not is_owner(request.user):
        return HttpResponseForbidden("only the owner accepts or rejects")
    said = actions.decide(request.user.username, place, stage, request.POST.get("output", ""),
                          request.POST.get("decision", ""), request.POST.get("reason", ""),
                          request.POST.get("worse_reason", ""))
    (messages.success if said.startswith(("accepted", "rejected", "queued")) else messages.error)(request, said)
    return redirect(step_url(place, stage))


@require_POST
def step_advance(request, stage, place=None):
    """The owner looked and presses advance: the paid steps reading this output may be launched."""
    if not is_owner(request.user):
        return HttpResponseForbidden("only the owner advances")
    said = actions.advance(request.user.username, place, stage, request.POST.get("output", ""))
    (messages.success if said.startswith("advanced") else messages.error)(request, said)
    return redirect(step_url(place, stage))


@require_POST
def step_queue(request, stage, place=None):
    """Queue this step, or the steps that read it, into the basket (owner only)."""
    if not is_owner(request.user):
        return HttpResponseForbidden("only the owner fills the launch basket")
    source = state.source()
    detail = source.step_detail(place, stage)
    if detail is None:
        raise Http404(stage)
    chosen = detail.readers if request.POST.get("which") == "next" else [stage]
    added = actions.queue(request.user.username, place, chosen, source)
    messages.success(request, f"queued {', '.join(added) or 'nothing new'}")
    return redirect(step_url(place, stage))


def basket(request):
    items = list(BasketItem.objects.all())
    plan = Plan.objects.first()
    current = guard.basket_hash(items)
    body = plan.body if plan and plan.state == "ready" else {}
    money = body.get("money", {})
    return render(request, "pages/basket.html", {
        "items": actions.basket_cards(items), "plan": plan, "plan_current": bool(plan and plan.basket_hash == current),
        "bar": money_bar(money.get("spent"), money.get("reserved"), money.get("likely"), money.get("high"),
                         money.get("ceiling")),
        "likely_time": costs.hours(body.get("time", {}).get("likely_minutes")),
        "high_time": costs.hours(body.get("time", {}).get("high_minutes")),
        "elapsed": int((timezone.now() - plan.started).total_seconds()) if plan and plan.state == "working" else 0})


@require_POST
def basket_change(request):
    """Remove an item, empty the basket, or work out the plan (owner only)."""
    if not is_owner(request.user):
        return HttpResponseForbidden("only the owner changes the launch basket")
    what = request.POST.get("what")
    if what == "remove":
        BasketItem.objects.filter(pk=request.POST.get("item")).delete()
    elif what == "empty":
        BasketItem.objects.all().delete()
    elif what == "plan":
        said = actions.start_plan(request.user.username, request.POST.get("jobs"))
        (messages.success if said.startswith("working") else messages.error)(request, said)
    return redirect("/basket/")


def confirm(request, plan_id):
    plan = get_object_or_404(Plan, pk=plan_id)
    if request.method == "POST":
        if not is_owner(request.user):
            return HttpResponseForbidden("only the owner launches")
        launched, said = actions.launch(request.user.username, plan, request.POST.get("confirm") == "yes",
                                        request.POST.get("rebuy_reason", ""))
        if launched:
            messages.success(request, said)
            return redirect(f"/runs/{launched.pk}/")
        messages.error(request, said)
    commands = [actions.command_words(group, plan.body.get("jobs", guard.DEFAULT_JOBS))
                for group in guard.run_groups_of(plan.body)] if plan.state == "ready" else []
    money = plan.body.get("money", {})
    return render(request, "pages/confirm.html", {
        "plan": plan, "commands": commands,
        "refusals": actions.launch_refusals(request.user, plan, confirmed=True, rebuy_reason="x"),
        "needs_reason": any(group["refusal"] for group in plan.body.get("groups", [])),
        "bar": money_bar(money.get("spent"), money.get("reserved"), money.get("likely"), money.get("high"),
                         money.get("ceiling")),
        "likely_time": costs.hours(plan.body.get("time", {}).get("likely_minutes")),
        "high_time": costs.hours(plan.body.get("time", {}).get("high_minutes"))})


def runs(request):
    return render(request, "pages/runs.html", {"launches": [guard.polled(item) for item in Launch.objects.all()[:30]],
                                                "queued": SyncRequest.objects.filter(kind="launch")[:30]})


def run_page(request, run_id):
    launched = guard.polled(get_object_or_404(Launch, pk=run_id))
    template = "pages/run_tail.html" if request.GET.get("part") == "tail" else "pages/run.html"
    return render(request, template, {"launch": launched})


def requests_page(request):
    return render(request, "pages/requests.html", {"changes": ChangeRequest.objects.all()[:100],
                                                    "sync_requests": SyncRequest.objects.all()[:100]})


def viewer(request, place):
    """The 3D viewer of a place's fresh web copy: orbit and walk, a toggle per OpenUSD layer, a person for scale, a
    measuring tool, and a click names the part, its surface, its layer and the step that made that layer."""
    source = state.source()
    if place not in source.places():
        raise Http404(place)
    detail = source.place_detail(place)
    return render(request, "pages/view3d.html", {"detail": detail, "viewer": {
        "place": place, "layers": layer_makers(detail.usd_index.layers),
        "order": [layer.name for layer in detail.usd_index.layers]}})


def layer_makers(layers):
    """{layer name: {label, url}} of the step that made each OpenUSD layer, in words and a link (no node ids)."""
    found = {}
    for layer in layers:
        if layer.made_by_step:
            stage, _, at = layer.made_by_step.partition("@")
            found[layer.name] = {"label": groups.label(stage), "url": step_url(at or None, stage)}
    return found


def picks(request, place):
    if request.method == "POST":
        return JsonResponse({"error": "pick viewpoints in the local viewer (tools/review/viewer/serve.py)"},
                            status=403)
    if place not in state.source().places():
        raise Http404(place)
    path = settings.SCORE_REPO / "data/review" / place / "viewpoints.json"
    found = json.loads(path.read_text()) if path.is_file() else []
    return JsonResponse({"place": place, "viewpoints": found.get("viewpoints", found) if isinstance(found, dict)
                         else found})


@require_POST
def refresh(request):
    state.source().refresh()
    messages.success(request, "the store was read again")
    return redirect(back_of(request))


@require_POST
def freshness(request):
    """Start the freshness snapshot (`score status world1 --json`) in the background, one at a time."""
    if not is_owner(request.user):
        return HttpResponseForbidden("only the owner starts the freshness snapshot")
    messages.info(request, actions.start_snapshot())
    return redirect(back_of(request))


def back_of(request):
    """The page to go back to after a POST: the form's `back` when it is a path on this site, else the board."""
    back = request.POST.get("back") or "/"
    allowed = url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()},
                                              require_https=request.is_secure())
    return back if allowed and back.startswith("/") and not back.startswith("//") else "/"


@login_not_required
def login_closed(request):
    """Proxy mode has no password sign-in."""
    return HttpResponseForbidden("sign in through the single sign-on")

