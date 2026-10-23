"""The environment's plan page (CONTEXT.md "environment plan", owner 2026-10-21; score/review/environment_plan.py):
`/environments/<world>/plan/`, laid out as the design page's cockpit (design.js: panels, enlarge, zoom). A panel a
ground of its setting (a body or a plot), its map in true metres (`static/pages/environment_plan.js`): each top
scene's own plan drawn at its site as its plan page draws it (plan.js `planSheet`; the owner, 2026-10-23: its sites
agree with the scenes, the plan shown being the scene's, `plans.review_of`), the true distances between sites, a north
arrow and a scale bar. The rail: Write and Keep, the gaps, and a row a site: its name (to its plan), its size (its
plan's), its scene time (a field for the owner) and where it stands (the environment concept's setting, shown here,
set there). Its sky is no column: it follows from the setting's bodies at its place and scene time (the owner,
2026-10-21), shown on hover over its time. Keep (SyncRequest `env-plan-edit`) keeps his times as his own; Write
(`env-plan-write`) has the plan writer write it again under the owner's standing allowance for plan writing."""
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from score.dashboard import state
from score.dashboard.pages import actions, concepts, environment, plans
from score.dashboard.pages.models import SyncRequest, is_owner
from score.dashboard.state import groups

EDIT, WRITE = "env-plan-edit", "env-plan-write"
COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def drawn_data(found, names):
    """What environment_plan.js draws of one ground's map: its sites where they stand with their footprints, and the
    distances between them."""
    return {"on": found["on"], "name": found["name"], "distances": found.get("distances", []),
            "sites": [{"place": site["place"], "name": names.get(site["place"], site["name"]), "at": site["at"],
                       "size": site.get("size"), "footprint": site.get("footprint")} for site in found["sites"]]}


def site_plans(world_state, sites):
    """{place: its plan as its plan page shows it} of each site's top scene with one (plans.review_of)."""
    return {site["place"]: review["plan"] for site in sites
            if (review := plans.review_of(world_state, site["place"]))}


def held_names(world_state, plans_of, names):
    """{place: its short name} of every child scene the sites' plans lay out (as the plan page names them)."""
    return {hold["place"]: world_state.shells.get(hold["place"]) or names.get(hold["place"], hold["place"])
            for plan in plans_of.values() for hold in plan.get("holds") or []}


def size_of(site):
    """A site's size in words, its plan's: "109.15 x 109.15 x 15 m", "no plan yet" without one."""
    return " x ".join(f"{value:g}" for value in site["size"]) + " m" if site.get("size") else "no plan yet"


def where_of(site):
    """Where a site stands in a few words: its latitude and longitude on a body, its metres on a plot."""
    if "x" in site:
        return f"{site['x']:.0f} m E, {site['y']:.0f} m S"
    if site.get("latitude") is None:
        return "?"
    return (f"{abs(site['latitude']):.4f}° {'N' if site['latitude'] >= 0 else 'S'}, "
            f"{abs(site['longitude']):.4f}° {'E' if site['longitude'] >= 0 else 'W'}")


def overhead_tip(found):
    """A site's sky at its scene time in one line, worked out from the setting (never set here): each light's height and
    each body above its horizon, where, how big and how much lit; "" before it has a scene time."""
    if not found:
        return ""
    words = [f"{light['name']} {light['altitude']:.0f}° up" for light in found.get("lights", [])]
    for world in found.get("bodies", []):
        if world["altitude"] > 0:
            size = "a point" if world["across"] < 0.05 else f"{world['across']:.1f}°"
            words.append(f"{world['name']} {world['altitude']:.0f}° {COMPASS[round(world['azimuth'] / 45) % 8]}, "
                         f"{size}, {world['lit'] * 100:.0f}% lit")
    return "Overhead, from the physics: " + "; ".join(words)


def plan_page(request, world):
    """`/environments/<world>/plan/` (module docstring)."""
    world_state = environment.checked_world(state.source(), world)
    shown = world_state.environment_plan or {}
    plan = shown.get("plan") or {"maps": [], "gaps": []}
    names = {**groups.short_names(world_state), **world_state.shells}
    maps = sorted(plan["maps"], key=lambda found: -len(found["sites"]))  # the ground with most sites the big panel
    sites = [site for found in maps for site in found["sites"]]
    plans_of = site_plans(world_state, sites)
    drawn = {"maps": [drawn_data(found, names) for found in maps], "plans": plans_of,
             "names": {**held_names(world_state, plans_of, names), **names}}
    rows = [{**found, "rows": [{
        **site, "title": names.get(site["place"], site["name"]), "overhead_tip": overhead_tip(site.get("overhead")),
        "where": where_of(site), "size_words": size_of(site)} for site in found["sites"]]} for found in maps]
    can = is_owner(request.user) and actions.decisions_on()
    return render(request, "pages/environment_plan.html", {
        "world": world, "title": environment.title_of(world), "shown": shown, "plan": plan, "maps": rows,
        "others": max(1, len(maps) - 1), "drawn": json.dumps(drawn).replace("</", "<\\/"),
        "can": can, "pending": pending(world), "edit_body": json.dumps({}), "write_body": json.dumps({})})


def pending(world):
    """True while his Write or Keep of the environment's plan is on its way."""
    return SyncRequest.objects.filter(kind__in=(EDIT, WRITE), payload__world=world,
                                      state__in=concepts.OPEN).exists()


def asked(request, world, kind, payload):
    """His request for the store's machine (a Write in a thread locally); JsonResponse {said}, or {detail}."""
    environment.checked_world(state.source(), world)
    if not is_owner(request.user):
        return JsonResponse({"detail": "only the owner plans"}, status=403)
    if pending(world):
        return JsonResponse({"detail": "refused: one is on its way"}, status=409)
    item = environment.queued(request, world, kind, payload, background=kind == WRITE)
    if item.state == "refused":
        return JsonResponse({"detail": item.detail}, status=409)
    return JsonResponse({"said": item.detail or "asked", "request": item.pk})


@require_POST
def plan_edit(request, world):
    """POST {plan}: his scene times, kept as his own."""
    body = concepts.body_of(request)
    if body is None or not isinstance(body.get("plan"), dict):
        return JsonResponse({"detail": "refused: not a plan"}, status=422)
    return asked(request, world, EDIT, {"plan": body["plan"]})


@require_POST
def plan_write(request, world):
    """POST {}: the plan writer writes the environment's plan again."""
    return asked(request, world, WRITE, {})
