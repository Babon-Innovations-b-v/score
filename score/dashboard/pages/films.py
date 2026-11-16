"""A film script's lock, the owner's approval of it (`film-lock`, sync/applying.py), and his Unlock, refused once a
batch was bought on the lock: the copy the environment-film row reads (score/dashboard/films). Reached from his chat
decision (sync/chat_decisions.py lock-film); the FILM pages that edited scripts went with the cockpit (owner,
2026-11-16)."""
import datetime
import json
import pathlib

from django.conf import settings
from django.http import Http404

from score.dashboard import state
from score.dashboard.checkout import WORLD
from score.dashboard.films import default, script
from score.dashboard.pages.models import Checkout

PEOPLE_ROWS = "data/people/rows.json"  # the people each scene's design shows (score/stages/people_rows.py)
LOCK = "film-lock"  # the SyncRequest kind of his Lock and Unlock (sync/applying.py)
ENDED = ("refused", "failed")  # a checkout in these bought nothing


def environment_default(source, film):
    """The environment's default script (films/default.py), filled in from its setting and scenes; None when its
    setting places no scene holding others."""
    facts = environment_facts(source)
    return facts and default.built(film, facts)


def environment_facts(source):
    """The facts the environment's default film is filled in from (films/default.facts_of): its setting, plan,
    scenes, kept plans and scene records as they stand now; None when its setting places no scene holding others."""
    if hasattr(source, "hierarchy"):
        found = source.hierarchy()
        concept, plan = source.environment_concept()["environment_concept"], source.environment_plan()["environment_plan"]
        kept, inside = source.kept_plans(), source.scene_inside()
    else:
        world = source.world_state()
        concept, plan = world.environment_concept, world.environment_plan
        found = {"within": world.within, "shells": world.shells, "parts": world.parts, "removed": world.removed}
        kept = {node: review.plan for node, review in world.plan_reviews.items()}
        inside = world.scene_inside
    within = {place: holder for place, holder in found["within"].items()
              if place not in found["parts"] and place not in found["removed"]}
    starters = [script.read(settings.SCORE_REPO, settings.SCORE_HOME, name)[0]
                for name in script.names(settings.SCORE_REPO, settings.SCORE_HOME)]
    return default.facts_of(WORLD, title_of(WORLD), (concept or {}).get("concept", {}).get("setting", {}),
                            (plan or {}).get("plan"), within, found["shells"], default.drawn_surfaces(starters),
                            people_places(), kept, inside)


def design_faults(source, given):
    """What in a script of the environment no longer says what its design says now (script.design_faults); none for
    another environment's script or while the design places no scene."""
    facts = environment_facts(source) if given.get("world") == WORLD else None
    return script.design_faults(given, default.design_of(facts)) if facts else []


def people_places():
    """{scene: whether one of its people walks} of the scenes whose design shows people (the repository's people
    rows; none where it holds no rows file)."""
    rows = pathlib.Path(settings.SCORE_REPO) / PEOPLE_ROWS
    return default.people_of(json.loads(rows.read_text())) if rows.exists() else {}


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
    """Why the film's lock stands for good, in words, or "": a batch bought since it was locked holds a film row."""
    since = lock_time(film)
    if since is None:
        return ""
    from score.dashboard.pages.basket import batch_state
    bought = [record for record in Checkout.objects.filter(at__gte=since).exclude(state__in=ENDED)
              if batch_state(record)[0] != "refused"  # launched, then its run refused: it bought nothing
              and any(script.films_node(node) for item in record.items for node in item.get("nodes", {}))]
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
    found = found or design_faults(source, given)
    if found:
        return "refused: " + "; ".join(found)
    script.save(settings.SCORE_HOME, given)
    script.lock(settings.SCORE_HOME, given)
    return f"locked {film}"


def title_of(world):
    """'Environment 1' of `world1`."""
    number = world[len(world.rstrip("0123456789")):]  # no regex: a search for \d+$ is quadratic on a long name
    return f"Environment {number}" if number else world


def shells_of(source):
    """{outside shell: its short name} (the Base): a scale zoom may go down to one. Read from within.json on the store's
    machine (its whole world state is slow there), from the export hosted."""
    return source.hierarchy()["shells"] if hasattr(source, "hierarchy") else source.world_state().shells

