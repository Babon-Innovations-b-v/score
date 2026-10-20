"""The dashboard's pages: visual first (a picture per piece, labelled plans, few words); node ids only in a small
details fold. Every page reads the source of this mode (state.source()); actions go through the owner's checks."""
import datetime
import json
import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from score.dashboard import state
from score.dashboard.launch import guard
from score.dashboard.pages import actions, cockpit, library, present, seen
from score.dashboard.pages import basket as basket_items
from score.dashboard.pages.models import BasketItem, ChangeRequest, Launch, Plan, RefineItem, SyncRequest, is_owner
from score.dashboard.proposals import records
from score.dashboard.state import costs, groups, gaps, screens
from score.dashboard.state import money as month_money


def everywhere(request):
    """What every page shows: the mode, when the store (or export) was read, and what this user may do."""
    source = state.source()
    return {"mode": settings.SCORE_MODE, "hosted": settings.SCORE_MODE == settings.HOSTED,
            "read_at": source.read_at() if request.user.is_authenticated else None,
            "export_age": source.age_words() if hasattr(source, "age_words") else None,
            "owner": is_owner(request.user), "decisions_on": actions.decisions_on(),
            "decisions_off_why": actions.decisions_off_why(), "proxy_mode": settings.SCORE_PROXY_MODE,
            "basket_count": basket_count() if request.user.is_authenticated else 0}


def basket_count():
    """What waits in the basket: steps queued by hand and library entries to refine (the Buy screen's one batch asks
    no choice an item)."""
    return BasketItem.objects.count() + RefineItem.objects.count()


def money_bar(spent, reserved, likely, high, ceiling):
    """The four parts of the one money bar as shares of the stop (percent), or None without a stop or a reading."""
    if not ceiling or spent is None or reserved is None:
        return None
    parts = [("spent", spent), ("reserved", reserved), ("likely", likely or 0.0),
             ("high", max(0.0, (high or 0.0) - (likely or 0.0)))]
    return [{"name": name, "euros": round(value, 2), "share": min(100.0, 100.0 * value / ceiling)}
            for name, value in parts]


def overview_of(source):
    """{world, names, rows, view} every screen of the environment reads: the WorldState with the month's spend, the
    places' titles, each place's row of gaps (gaps.per_place) and the month's MoneyView."""
    world = source.world_state(actions.spend())
    names = present.place_names(present.look_groups(world, set()))
    rows = gaps.per_place(world.gaps_price, every_place_gaps(source))
    return {"world": world, "names": names, "rows": rows, "view": month_money.view(world.spend)}


def every_place_gaps(source):
    """{place: [gap]} of every place of the environment, the gaps check's findings."""
    if hasattr(source, "gaps"):
        return {place: source.gaps(place) for place in source.places()}
    return {place: source.place_detail(place).gaps for place in source.places()}


def environment(request):
    """Screen 1: the month's spend against the stop, the remake's price and time, a tile per outside place or shell;
    `?in=<place or shell>` the places inside it, one level down (shapes first); `?kind=<gap kind>` (the Stats
    screen's links) only the tiles holding gaps of that kind, each counting those."""
    found = overview_of(state.source())
    world, at = found["world"], request.GET.get("in") or None
    kind = request.GET.get("kind") if request.GET.get("kind") in cockpit.KIND_WORDS else None
    trail = cockpit.trail(world, found["names"], at) if at else []
    if trail is None:
        raise Http404(f"nothing sits within {at}")
    tiles = cockpit.tiles(world, found["names"], cockpit.of_kind(found["rows"], kind) if kind else found["rows"], at)
    if kind:
        tiles = [{**tile, "href": tile["href"] + (f"&kind={kind}" if tile["href"].startswith("/?") else "")}
                 for tile in tiles if tile["gaps"]]
        trail = [{**step, "href": f"{step['href']}&kind={kind}"} for step in trail]
    return render(request, "pages/environment.html", {
        "money": cockpit.month_money(found["view"]), "remake": cockpit.remake(world), "trail": trail,
        "kind": kind and {"kind": kind, "label": cockpit.KIND_WORDS[kind][0], "tone": cockpit.KIND_TONES[kind]},
        "tiles": tiles})


def stats(request):
    """Screen 4, numbers only, no controls, in three groups: the month's money (its lines, total, spend per day and,
    once a batch's stop line is written, the remake's spend so far), progress (places complete, gaps by kind, each
    opening the Environment filtered to it) and prices (paid steps measured, the remake's measured share)."""
    found = overview_of(state.source())
    world, view = found["world"], found["view"]
    complete, of = cockpit.places_complete(found["rows"])
    money = cockpit.month_money(view)
    days = cockpit.spend_by_day(view.bill_days, world.spend.days if world.spend else [], view.month)
    return render(request, "pages/stats.html", {
        "money": money, "so_far": view.world_spent if view.stop is not None else None, "in_flight": view.in_flight,
        "chart": cockpit.day_chart(days), "month_name": datetime.date.fromisoformat(f"{view.month}-01").strftime("%B"),
        "unplaced": cockpit.unplaced(money["total"], days),
        "measured": cockpit.measured_prices(world.gaps_price), "share": cockpit.measured_share(
            screens.batch(world, records.items(basket_items.basket_root()))),
        "kinds": cockpit.gaps_by_kind(world.gaps_total), "complete": complete, "of": of})


def buy(request):
    """Screen 3, design first (CONTEXT.md "design"): each place's concept and its plan, made on
    the place's card and never bought here (screens.design), its Approve once made; then the batch after design
    (screens.batch: the whole remake by layer, how many each makes and its euros), its Buy only once a design is
    approved and only for those places; the last batch's state and stop; the owner's books buttons only while paid
    work is refused or the model calls' month is not read."""
    source = state.source()
    found = overview_of(source)
    world = found["world"]
    items = records.items(basket_items.basket_root())
    names = groups.short_names(world)
    design = screens.design(source, world)
    for row in design["places"]:
        row["name"] = names.get(row["place"], present.place_title(row["place"]))
    return render(request, "pages/buy.html", {
        "design": design, "batch": screens.batch(world, items), "money": found["view"],
        "last": basket_items.last_batch(), "figure": cockpit.month_money(found["view"])["models"] is None,
        "key": uuid.uuid4().hex})


def place_page(request, place):
    """Screen 2: its concept as the header, the place in 3D, its scene tree's top level with each node's gaps (deeper
    branches load as they open, `place_branch`), a side panel per item."""
    source = state.source()
    if place not in source.places():
        raise Http404(f"no place {place}")
    detail = source.place_detail(place)
    world = source.world_state()
    names = present.place_names(present.look_groups(world, set()))
    return render(request, "pages/place.html", {
        "detail": detail, "name": names.get(place, present.place_title(place)), "concept": world.concepts.get(place),
        "tree": scene_branch(request, source, detail, "") if detail.gaps else None,
        "checked": not gaps.not_checked(place, detail.gaps, world.gaps_price)})


def place_branch(request, place):
    """GET ?path=<names below the root>: one branch of the place's scene tree as JSON [row] (c/tree.html's
    children_url)."""
    source = state.source()
    if place not in source.places():
        raise Http404(f"no place {place}")
    rows = scene_branch(request, source, source.place_detail(place), request.GET.get("path", ""))
    if rows is None:
        raise Http404("no such branch")
    return JsonResponse(rows, safe=False)


def scene_branch(request, source, detail, path):
    """[row] of one branch of a place's scene tree (cockpit.branch_rows), each item's panel with its price and, for
    the owner, its action; None when no node stands at `path`."""
    node = cockpit.branch_at(present.prim_tree(detail), path)
    if node is None:
        return None
    price = source.world_state().gaps_price
    owner, steps = is_owner(request.user), {}

    def step_of(gap):
        """The owner's view of the step that fills the gap (its StepDetail, read once a branch), else None."""
        if not owner or not gap.node:
            return None
        if gap.node not in steps:
            stage, _, place = gap.node.partition("@")
            steps[gap.node] = source.step_detail(place or None, stage)
        return steps[gap.node]

    return cockpit.branch_rows(
        node, path, lambda gap, title: cockpit.gap_panel(gap, detail.place, step_of(gap), price),
        lambda at: f"/place/{detail.place}/branch/?{urlencode({'path': at})}")


def step_page(request, stage, place=None):
    source = state.source()
    detail = source.step_detail(place, stage)
    if detail is None:
        raise Http404(f"no step {stage} at {place or 'the whole environment'}")
    snapshot = actions.snapshot_states()
    shown = (detail.accepted or detail.waiting)
    if shown and is_owner(request.user):
        seen.looked(request.user.username, detail.node, shown.output)
    detail.mark = seen.mark(detail.node, shown.output) if shown else None
    films = any(file.kind == "film" for file in [*detail.files, *detail.waiting_files])
    style = present.look_of_place(source.world_state(), place) if place else None
    return render(request, "pages/step.html", {
        "film_fps": film_fps(source, place) if films else None,
        "output_picture": detail.picture or next((file for file in detail.files if file.kind == "image"), None),
        "output_film": next((file for file in detail.files if file.kind == "film"), None),
        "place_name": (present.place_name(style, detail) if style else present.place_title(place)) if place else None,
        "state_words": present.STATE_WORDS.get(detail.state, detail.state), "mark_words": present.mark_words(detail.mark),
        "failed": [gate for gate in detail.judgement if gate.answer == "fail"],
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
def step_waive(request, stage, place=None):
    """The owner's waiver of one check of the output he saw, with his reason."""
    if not is_owner(request.user):
        return HttpResponseForbidden("only the owner waives a check")
    said = actions.waive_check(request.user.username, place, stage, request.POST.get("output", ""),
                               request.POST.get("check", ""), request.POST.get("reason", ""))
    (messages.success if said.startswith(("waived", "queued")) else messages.error)(request, said)
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
        **basket_items.basket_context(), "items": actions.basket_cards(items),
        "refine": library.refine_cards(RefineItem.objects.all()),
        "plan": plan, "plan_current": bool(plan and plan.basket_hash == current),
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
    elif what == "remove_refine":
        RefineItem.objects.filter(pk=request.POST.get("item")).delete()
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


@xframe_options_sameorigin
def viewer(request, place):
    """The 3D viewer of a place's fresh web copy: orbit and walk, a toggle per OpenUSD layer, a person for scale, a
    measuring tool, and a click names the part, its surface, its layer and the step that made that layer. With a
    basket item (`item`), its free after (`side` before: the place now) with the parts it changes outlined; `embed`
    leaves the panel out (the item's details hold it in a frame); `gaps=1` outlines the place's gaps too (each
    missing object's box and each made object failing a check; the web copy stays the accepted one), and `gap`
    frames that one; with no web copy yet, the gaps alone over a ground grid, said so."""
    source = state.source()
    if place not in source.places():
        raise Http404(place)
    detail = source.place_detail(place)
    after = item_after(place, request.GET.get("item"))
    showing = "after" if after and after["has_copy"] and request.GET.get("side") != "before" else "current"
    base = after["web3d_base"] if showing == "after" else f"/web/{place}/"
    only = only_layer(request.GET.get("only"), detail.usd_index.layers)
    film_view = detail.film_view if request.GET.get("at") == "film" else None
    gap_marks = present.gap_marks(detail) if request.GET.get("gaps") == "1" else []
    gaps_only = bool(gap_marks) and not detail.web3d and showing != "after"
    framed = present.framed_gap(detail, request.GET.get("gap")) if gap_marks else None
    return render(request, "pages/view3d.html", {"detail": detail, "after": after, "showing": showing,
                                                 "only": only, "at_film": bool(film_view),
                                                 "embed": request.GET.get("embed") == "1", "gaps_only": gaps_only,
                                                 "framed": framed,
                                                 "gate_marks": any(mark["kind"] == "gate" for mark in gap_marks),
                                                 "gaps_mode": bool(gap_marks),
                                                 "viewer": {"place": place, "base": base,
                                                            "layers": layer_makers(detail.usd_index.layers),
                                                            "order": [layer.name for layer in detail.usd_index.layers],
                                                            "only": [only, ONLY_WITH] if only else None,
                                                            "at": film_view, "gap": request.GET.get("gap"),
                                                            "gaps_only": gaps_only,
                                                            "marks": basket_items.marks(
                                                                (after or {}).get("changes"),
                                                                "after" if showing == "after" else "before")
                                                            + gap_marks}})


def item_after(place, ident):
    """A basket item's free after of the place as the viewer shows it: {item, name, web3d_base, changes, has_copy},
    or None when the item has no details at this place."""
    if not ident or not records.NAME.match(ident):
        return None
    root = basket_items.basket_root()
    item = records.item(root, ident)
    found = records.details(root, place) if item and place in item["places"] else None
    if not found:
        return None
    return {"item": ident, "name": basket_items.item_name(item), "web3d_base": f"/basket-file/{place}/web3d/",
            "changes": found.get("changes"), "has_copy": basket_items.has_after(found)}


ONLY_WITH = "base"  # the layer kept on beside the one shown alone, for context


def only_layer(asked, layers):
    """The OpenUSD layer the viewer shows alone (with the base), when the link asks for one the place has."""
    return asked if asked and asked in {layer.name for layer in layers if layer.present} else None


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

