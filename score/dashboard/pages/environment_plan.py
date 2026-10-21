"""The environment's plan page (CONTEXT.md "environment plan", owner 2026-10-21; score/review/environment_plan.py):
`/environments/<world>/plan/`, the plan page pattern for the environment, the first parent. One map a ground of its
setting (a body or a plot), drawn top down (each top place's site with its blocks, the true distances between sites),
and a row a site: its size and scene time (fields for the owner), where it stands (the environment concept's setting,
shown here, set there), the Sun's height and every other body in its sky at that moment (worked out from the setting,
never typed), and its blockout, the structure picture its next draw is drawn on. Keep (SyncRequest `env-plan-edit`)
keeps his times and sizes as his own; Write (`env-plan-write`)
has the plan writer write it again under the owner's standing allowance for plan writing. The places picked before
blockouts existed are named (`without_blockout`)."""
import html
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from score.dashboard import state
from score.dashboard.pages import actions, concepts, environment
from score.dashboard.pages.models import SyncRequest, is_owner
from score.dashboard.state import groups

EDIT, WRITE = "env-plan-edit", "env-plan-write"
MAP_WIDE, MAP_TALL, MAP_EDGE = 640, 400, 24  # the map's drawing in pixels, its margin
COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def site_points(site):
    """Every corner of a site's blocks (else its footprint) on its world's map, metres."""
    shapes = [block["points"] for block in site.get("blocks") or []] or [site.get("footprint") or [[0, 0]]]
    return [[site["at"][0] + x, site["at"][1] + y] for shape in shapes for x, y in shape]


def map_svg(world, names):
    """One world's map as an SVG: each site's blocks at their place, its name, and a line with its metres between
    every two sites."""
    points = [point for site in world["sites"] for point in site_points(site)] or [[0, 0]]
    left, top = min(x for x, _ in points), min(y for _, y in points)
    wide, deep = max(max(x for x, _ in points) - left, 1.0), max(max(y for _, y in points) - top, 1.0)
    scale = min((MAP_WIDE - 2 * MAP_EDGE) / wide, (MAP_TALL - 2 * MAP_EDGE) / deep)

    def at(x, y):
        return MAP_EDGE + (x - left) * scale, MAP_EDGE + (y - top) * scale
    middles = {site["place"]: at(*site["at"]) for site in world["sites"]}
    shapes = []
    for found in world.get("distances", []):
        (x1, y1), (x2, y2) = middles[found["from"]], middles[found["to"]]
        shapes.append(f'<line class="ep-apart" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'
                      f'<text class="ep-metres" x="{(x1 + x2) / 2:.1f}" y="{(y1 + y2) / 2:.1f}">'
                      f'{found["metres"]:.0f} m</text>')
    for site in world["sites"]:
        for block in site.get("blocks") or []:
            corners = " ".join("{:.1f},{:.1f}".format(*at(site["at"][0] + x, site["at"][1] + y))
                               for x, y in block["points"])
            shapes.append(f'<polygon class="ep-block" points="{corners}"><title>{html.escape(block["name"])}'
                          f'</title></polygon>')
        x, y = middles[site["place"]]
        shapes.append(f'<text class="ep-name" x="{x:.1f}" y="{y:.1f}">'
                      f'{html.escape(names.get(site["place"], site["name"]))}</text>')
    return mark_safe(f'<svg class="ep-map" viewBox="0 0 {MAP_WIDE} {MAP_TALL}" role="img" '
                     f'aria-label="{html.escape(world["name"])} map">{"".join(shapes)}</svg>')


def where_of(site):
    """Where a site stands in a few words: its latitude and longitude on a body, its metres on a plot."""
    if "x" in site:
        return f"{site['x']:.0f} m E, {site['y']:.0f} m S"
    if site.get("latitude") is None:
        return "?"
    return (f"{abs(site['latitude']):.4f}° {'N' if site['latitude'] >= 0 else 'S'}, "
            f"{abs(site['longitude']):.4f}° {'E' if site['longitude'] >= 0 else 'W'}")


def sky_line(found):
    """[(name, words, tip)] of the worlds above a site's horizon at its scene time."""
    lines = []
    for world in (found or {}).get("worlds", []):
        if world["altitude"] <= 0:
            continue
        where = f"{world['altitude']:.0f}° {COMPASS[round(world['azimuth'] / 45) % 8]}"
        size = "point" if world["across"] < 0.05 else f"{world['across']:.1f}°"
        lines.append((world["name"], f"{where}, {size}, {world['lit'] * 100:.0f}% lit",
                      f"azimuth {world['azimuth']:.1f}°, altitude {world['altitude']:.1f}°, "
                      f"{world['across']:.4f}° across, lit from east {world['lit_from'][0]:.2f}, "
                      f"north {world['lit_from'][1]:.2f}, up {world['lit_from'][2]:.2f}"))
    return lines


def plan_page(request, world):
    """`/environments/<world>/plan/` (module docstring)."""
    world_state = environment.checked_world(state.source(), world)
    shown = world_state.environment_plan or {}
    plan = shown.get("plan") or {"maps": [], "gaps": []}
    names = {**groups.short_names(world_state), **world_state.shells}
    maps = [{**found, "svg": map_svg(found, names), "rows": [{
        **site, "title": names.get(site["place"], site["name"]), "sky_lines": sky_line(site.get("sky")),
        "where": where_of(site),
        "sun": (site.get("sky") or {}).get("sun"), "blockout": world_state.blockouts.get(site["place"])}
        for site in found["sites"]]} for found in plan["maps"]]
    can = is_owner(request.user) and actions.decisions_on()
    return render(request, "pages/environment_plan.html", {
        "world": world, "title": environment.title_of(world), "shown": shown, "plan": plan, "maps": maps,
        "without": [names.get(place, place) for place in shown.get("without_blockout", [])],
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
    """POST {plan}: his times and sizes, kept as his own."""
    body = concepts.body_of(request)
    if body is None or not isinstance(body.get("plan"), dict):
        return JsonResponse({"detail": "refused: not a plan"}, status=422)
    return asked(request, world, EDIT, {"plan": body["plan"]})


@require_POST
def plan_write(request, world):
    """POST {}: the plan writer writes the environment's plan again."""
    return asked(request, world, WRITE, {})
