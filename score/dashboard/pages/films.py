"""The FILM pages: the creator's film scripts (score/dashboard/films), each edited on a timeline and played for free on
the places' 3D web copies and existing films, its render items priced against the stop. Saving writes only the
cockpit's home; the basket takes only rows that exist; nothing here starts a paid run. The Film step (after the
scenes, before Buy) opens on the environment's own film (`films.default`); his Lock is his approval of a script, the
copy the environment-film row reads (`film-lock`, applied on the store's machine, hosted through the sync)."""
import datetime
import json

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from score.dashboard import state
from score.dashboard.checkout import WORLD
from score.dashboard.films import default, media, render as compiler, script
from score.dashboard.pages import actions
from score.dashboard.pages.models import Checkout, SyncRequest, is_owner
from score.dashboard.pages.views import money_bar

# The OpenUSD layers bottom up, as a layer split stacks them: the ground under everything, then the stage's sublayers
# weakest first (state/local.py LAYER_FILES, strongest first, reversed).
STACK_ORDER = ("ground", "base", "settle", "motion-models", "crops", "effects", "motion", "light", "sound", "characters",
               "edit")


# Film names the FILM pages' own addresses take.
RESERVED = ("new", "pictures", "all")
LOCK = "film-lock"  # the SyncRequest kind of his Lock and Unlock (sync/applying.py)
ENDED = ("refused", "failed")  # a checkout in these bought nothing


def environment_default(source, film):
    """The environment's default script (films/default.py), filled in from its setting and scenes; None when its
    setting places no scene holding others."""
    if hasattr(source, "hierarchy"):
        found = source.hierarchy()
        concept, plan = source.environment_concept()["environment_concept"], source.environment_plan()["environment_plan"]
    else:
        world = source.world_state()
        concept, plan = world.environment_concept, world.environment_plan
        found = {"within": world.within, "shells": world.shells, "parts": world.parts, "removed": world.removed}
    within = {place: holder for place, holder in found["within"].items()
              if place not in found["parts"] and place not in found["removed"]}
    from score.dashboard.pages.environment import title_of
    starters = [script.read(settings.SCORE_REPO, settings.SCORE_HOME, name)[0]
                for name in script.names(settings.SCORE_REPO, settings.SCORE_HOME)]
    facts = default.facts_of(WORLD, title_of(WORLD), (concept or {}).get("concept", {}).get("setting", {}),
                             (plan or {}).get("plan"), within, found["shells"], default.drawn_surfaces(starters))
    return facts and default.built(film, facts)


def script_or_404(film):
    """(the film's script, where it was read from: saved, starter or default); 404 when the film has none."""
    if not script.NAME.match(film):
        raise Http404(film)
    found, origin = script.read(settings.SCORE_REPO, settings.SCORE_HOME, film)
    if found is None and film == script.default_name(settings.SCORE_REPO, settings.SCORE_HOME, WORLD):
        found, origin = environment_default(state.source(), film), "default"
    if found is None:
        raise Http404(f"no film script {film}")
    return found, origin


def lock_time(film):
    """When the film was locked (its locked copy's time), or None."""
    path = script.locked_path(settings.SCORE_HOME, film)
    return datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc) if path.is_file() else None


def bought_since(film):
    """Why the film's lock stands for good, in words, or "": a batch bought since it was locked holds a film row
    (hosted: any checkout sent since)."""
    since = lock_time(film)
    if since is None:
        return ""
    if actions.hosted():
        sent = SyncRequest.objects.filter(kind="checkout", created__gte=since).exclude(state="refused").exists()
        return "a batch was bought on this lock" if sent else ""
    bought = [record for record in Checkout.objects.filter(at__gte=since).exclude(state__in=ENDED)
              if any(script.films_node(node) for item in record.items for node in item.get("nodes", {}))]
    return f"checkout {bought[0].pk} bought its film rows on this lock" if bought else ""


def film_locked(user, payload):
    """His Lock ({film, script}: the script as his editor shows it, also saved as his) or Unlock ({film}, refused once
    a batch was bought on the lock) of a film script, on the store's machine; words."""
    film = str(payload.get("film", ""))
    if not script.NAME.match(film):
        return "refused: no such film"
    if "script" not in payload:
        stands = bought_since(film)
        if stands:
            return f"refused: {stands}; it stays locked"
        script.unlock(settings.SCORE_HOME, film)
        return f"unlocked {film}"
    given = payload["script"]
    source = state.source()
    found = script.faults(given, set(source.places()) | set(shells_of(source))) if given.get("film") == film else [
        f"the script is not film {film}'s"]
    if found:
        return "refused: " + "; ".join(found)
    script.save(settings.SCORE_HOME, given)
    script.lock(settings.SCORE_HOME, given)
    return f"locked {film}"


def shown_places(film_script):
    """The places a script's segments name, in order of first showing."""
    return list(dict.fromkeys((segment.get("shows") or {}).get("place") for segment in film_script["segments"]
                              if (segment.get("shows") or {}).get("place")))


def pictured_places(film_script):
    """The places a step card or a before and after of the script shows."""
    return {segment["shows"]["place"] for segment in film_script["segments"]
            if segment.get("cut") in compiler.PICTURE_CUTS and (segment.get("shows") or {}).get("place")}


def media_of(source, places):
    """{place: what exists for it} of the named places."""
    return {place: media.place_media(source, place) for place in places}


def compiled(film_script, known):
    """(render items, their totals) of a script, from what exists at its places (`known`, {place: media})."""
    found = compiler.items(film_script, known)
    return found, compiler.totals(found)


def stop_bar(totals):
    """The money bar with this script's measured render cost on top of the month's spend, against the stop."""
    spend = actions.spend()
    return money_bar(spend.spent, spend.reserved, totals["euros"], totals["euros"], spend.ceiling), spend


def film_step(request):
    """The Film step opens on the environment's own film."""
    return redirect(f"/film/{script.default_name(settings.SCORE_REPO, settings.SCORE_HOME, WORLD)}/")


def film_list(request):
    source = state.source()
    films = []
    for film in script.names(settings.SCORE_REPO, settings.SCORE_HOME):
        found, origin = script.read(settings.SCORE_REPO, settings.SCORE_HOME, film)
        places = [place for place in shown_places(found) if place in source.places()]
        films.append({"film": film, "title": found.get("title", film), "origin": origin,
                      "seconds": script.total_seconds(found), "target": found.get("target_seconds"),
                      "segments": len(found.get("segments", [])), "places": len(places),
                      "picture": media.hero_picture(source, places[0]) if places else None})
    return render(request, "pages/films.html", {"films": films})


@require_POST
def film_new(request):
    """Start a new film's script (owner only), its title card only."""
    if not is_owner(request.user):
        return HttpResponseForbidden("only the owner writes film scripts")
    film = request.POST.get("film", "").strip().lower()
    if not script.NAME.match(film) or film in RESERVED:
        messages.error(request, "a film's name is lower-case letters, digits and dashes")
        return redirect("/film/all/")
    if script.read(settings.SCORE_REPO, settings.SCORE_HOME, film)[0] is not None:
        messages.error(request, f"{film} has a script already")
        return redirect(f"/film/{film}/")
    script.save(settings.SCORE_HOME, script.blank(film, request.POST.get("title", "").strip() or film))
    return redirect(f"/film/{film}/")


def shells_of(source):
    """{outside shell: its short name} (the Base): a scale zoom may go down to one. Read from within.json on the store's
    machine (its whole world state is slow there), from the export hosted."""
    return source.hierarchy()["shells"] if hasattr(source, "hierarchy") else source.world_state().shells


def preview_of(film):
    """The rendered preview's record with its link ({url, made_at, seconds, script, segments}), or None. The video is
    served by api/routes.py's `film_preview` (ranges, so the player seeks)."""
    video, record = script.preview_files(settings.SCORE_HOME, settings.SCORE_MODE == settings.HOSTED, film)
    if not (video.is_file() and record.is_file()):
        return None
    found = json.loads(record.read_text())
    return {**found, "url": f"/film-preview/{film}.mp4?at={found['made_at']}"}


def editor_data(request, film_script, origin, source, known):
    """What the editor's script reads (json_script): the script, the words and defaults, every place (`known`)."""
    return {"script": film_script, "origin": origin, "cuts": script.CUTS, "groups": script.GROUPS,
            "measured": compiler.MEASURED, "transitions": script.TRANSITIONS,
            "sounds": script.SOUNDS, "steps": script.STEPS, "stack": STACK_ORDER,
            "transition_seconds": script.TRANSITION_SECONDS, "film_shot_from": script.FILM_SHOT_FROM,
            "film_shot_seconds": script.FILM_SHOT_SECONDS, "places": known,
            "shells": shells_of(source), "recorded": script.RECORDED, "legs": script.LAYERS,
            "preview": preview_of(film_script["film"]),
            "pictures": {place: media.step_pictures(source, place) for place in pictured_places(film_script)},
            "can_save": is_owner(request.user),
            "locked": script.locked(settings.SCORE_HOME, film_script["film"]) is not None,
            "urls": {"save": f"/film/{film_script['film']}/save/", "compile": f"/film/{film_script['film']}/compile/",
                     "lock": f"/film/{film_script['film']}/lock/", "pictures": "/film/pictures/"}}


def film_page(request, film):
    film_script, origin = script_or_404(film)
    source = state.source()
    known = media_of(source, source.places())
    return render(request, "pages/film.html", {
        "film": film_script, "origin": origin, "preview": preview_of(film),
        "locked": script.locked(settings.SCORE_HOME, film) is not None,
        "default": film == script.default_name(settings.SCORE_REPO, settings.SCORE_HOME, WORLD),
        "editor": {**editor_data(request, film_script, origin, source, known),
                   "answer": compile_answer(film_script, known)}})


def posted_script(request, film):
    """The script in a POST's JSON body, its name the page's; (script, faults)."""
    try:
        body = json.loads(request.body or b"{}")
    except ValueError:
        return None, ["the body is not JSON"]
    if not isinstance(body, dict) or body.get("film") != film:
        return None, [f"the script is not film {film}'s"]
    source = state.source()
    return body, script.faults(body, set(source.places()) | set(shells_of(source)))


def compile_answer(film_script, known):
    """The JSON the editor shows after a change: the length, the render items and their totals against the stop."""
    items, totals = compiled(film_script, known)
    bar, spend = stop_bar(totals)
    return {"seconds": script.total_seconds(film_script), "items": items, "totals": totals, "bar": bar,
            "ceiling": spend.ceiling, "spent": spend.spent, "reserved": spend.reserved, "note": spend.note}


def shown_media(film_script):
    """What exists at the places a script shows."""
    return media_of(state.source(), shown_places(film_script))


@require_POST
def film_compile(request, film):
    """The render items of the posted script, saved or not (any signed-in user)."""
    film_script, found = posted_script(request, film)
    if found:
        return JsonResponse({"faults": found}, status=400)
    return JsonResponse(compile_answer(film_script, shown_media(film_script)))


@require_POST
def film_save(request, film):
    """Save the posted script to the cockpit's home (owner only)."""
    if not is_owner(request.user):
        return JsonResponse({"faults": ["only the owner saves film scripts"]}, status=403)
    if script.locked(settings.SCORE_HOME, film) is not None:
        return JsonResponse({"faults": ["it is locked: unlock it to change it"]}, status=409)
    film_script, found = posted_script(request, film)
    if found:
        return JsonResponse({"faults": found}, status=400)
    script.save(settings.SCORE_HOME, film_script)
    return JsonResponse({"saved": True, **compile_answer(film_script, shown_media(film_script))})


def film_pictures(request, place):
    """The pictures each framework step made at a place, for a step card the editor just pointed there."""
    source = state.source()
    if place not in source.places():
        raise Http404(place)
    return JsonResponse(media.step_pictures(source, place))


@require_POST
def film_basket(request, film):
    """Queue the place film rows the script needs into the basket (owner only); nothing is launched."""
    if not is_owner(request.user):
        return HttpResponseForbidden("only the owner fills the launch basket")
    film_script, _ = script_or_404(film)
    source = state.source()
    _, totals = compiled(film_script, shown_media(film_script))
    added = [node for node in totals["basket"]
             if actions.queue(request.user.username, node.partition("@")[2], ["demo-film"], source)]
    messages.success(request, f"queued {', '.join(added)}" if added else "nothing new to queue")
    return redirect(f"/film/{film}/")


@require_POST
def film_lock(request, film):
    """POST the script to lock it, or {} to unlock it (owner only): his request for the store's machine, applied here
    at once locally; hosted, this cockpit's own copy follows at once so its Buy and page show it. JSON {said}, or
    {faults} when refused."""
    from score.dashboard.pages.concepts import applied_here
    if not is_owner(request.user):
        return JsonResponse({"faults": ["only the owner locks a film"]}, status=403)
    try:
        body = json.loads(request.body or b"{}")
    except ValueError:
        body = None
    if not isinstance(body, dict):
        return JsonResponse({"faults": ["the body is not JSON"]}, status=400)
    payload = {"film": film, **({"script": body} if body else {})}
    if actions.hosted():
        said = film_locked(request.user.username, payload)
        if not said.startswith("refused"):
            SyncRequest.objects.create(kind=LOCK, user=request.user.username, payload=payload)
    else:
        item = SyncRequest.objects.create(kind=LOCK, user=request.user.username, payload=payload)
        applied_here(item.pk)
        item.refresh_from_db()
        said = item.detail
    if said.startswith("refused"):
        return JsonResponse({"faults": [said]}, status=409)
    return JsonResponse({"said": said, "locked": "script" in payload})
