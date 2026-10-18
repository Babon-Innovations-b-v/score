"""The FILM pages: the creator's film scripts (score/dashboard/films), each edited on a timeline and played for free on
the places' 3D web copies and existing films, its render items priced against the stop. Saving writes only the
cockpit's home; the basket takes only rows that exist; nothing here starts a paid run."""
import json

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from score.dashboard import state
from score.dashboard.films import media, render as compiler, script
from score.dashboard.pages import actions
from score.dashboard.pages.models import is_owner
from score.dashboard.pages.views import money_bar

# The OpenUSD layers bottom up, as a layer split stacks them: the ground under everything, then the stage's sublayers
# weakest first (state/local.py LAYER_FILES, strongest first, reversed).
STACK_ORDER = ("ground", "base", "settle", "machines", "crops", "effects", "motion", "light", "sound", "characters",
               "edit")


# Film names the FILM pages' own addresses take.
RESERVED = ("new", "pictures")


def script_or_404(film):
    """(the film's script, where it was read from); 404 when the film has none."""
    if not script.NAME.match(film):
        raise Http404(film)
    found, origin = script.read(settings.SCORE_REPO, settings.SCORE_HOME, film)
    if found is None:
        raise Http404(f"no film script {film}")
    return found, origin


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
        return redirect("/film/")
    if script.read(settings.SCORE_REPO, settings.SCORE_HOME, film)[0] is not None:
        messages.error(request, f"{film} has a script already")
        return redirect(f"/film/{film}/")
    script.save(settings.SCORE_HOME, script.blank(film, request.POST.get("title", "").strip() or film))
    return redirect(f"/film/{film}/")


def editor_data(request, film_script, origin, source, known):
    """What the editor's script reads (json_script): the script, the words and defaults, every place (`known`)."""
    return {"script": film_script, "origin": origin, "cuts": script.CUTS, "transitions": script.TRANSITIONS,
            "sounds": script.SOUNDS, "steps": script.STEPS, "stack": STACK_ORDER,
            "transition_seconds": script.TRANSITION_SECONDS, "film_shot_from": script.FILM_SHOT_FROM,
            "film_shot_seconds": script.FILM_SHOT_SECONDS, "places": known,
            "pictures": {place: media.step_pictures(source, place) for place in pictured_places(film_script)},
            "can_save": is_owner(request.user),
            "urls": {"save": f"/film/{film_script['film']}/save/", "compile": f"/film/{film_script['film']}/compile/",
                     "pictures": "/film/pictures/"}}


def film_page(request, film):
    film_script, origin = script_or_404(film)
    source = state.source()
    known = media_of(source, source.places())
    return render(request, "pages/film.html", {
        "film": film_script, "origin": origin, "measured": compiler.MEASURED,
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
    return body, script.faults(body, set(state.source().places()))


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
