"""The cockpit's home and each environment's concept page (CONTEXT.md "environment concept", the owner 2026-10-21).

`/` is the home: the environments (environment 1 only today), each opening its concept page, and the hub of what
spans them (the month's spend, Stats, Library, Buy). `/environments/<world>/` is the environment concept: its style
line, setting (what everything stands on and in: its bodies, lights, backdrops, plots and each top place's site;
shown as a picture and a card a thing, `setting_picture`), reference pictures and places with what each may hold, and
the set interview (environment_concept.QUESTIONS, one at a time, `?q=<topic>`), each Send one priced model call his
click says yes to; its Places button opens the places (the Places screen, `/places/`). Locked it is for looking at; Unlock asks a second time in the page, since
it puts every place's concept made from it out of date.

Every click is the owner's request (a SyncRequest of ENVIRONMENT_KINDS, sync/applying.py) applied on the store's
machine: locally here at once (an ask, a picture in a thread), hosted by its listener. Hosted, his versions and
pictures since the export show at once (`shown`)."""
import json
import re

from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from score.dashboard import state
from score.dashboard.pages import actions, cockpit, concepts, setting_picture
from score.dashboard.pages.models import SyncRequest, is_owner
from score.dashboard.state.files import file_ref

ASK, SAVE, REFERENCE = "environment-ask", "environment-save", "environment-reference"
QUESTIONS = (  # score/review/environment_concept.QUESTIONS (environment_test holds them equal): hosted imports none
    ("style", "Style", "What style holds the whole environment, in one short line?"),
    ("setting", "Physics", "What does everything stand on: a plot of ground, a world, or several bodies that move one "
                           "another? Name real bodies or give an invented one's values, what lights it and what is "
                           "too far to move, and say where each first place stands."),
    ("references", "Reference pictures", "Which pictures guide the look, and what is each one for?"),
    ("places", "Scenes", "Which places come first?"),
    ("insides", "Child scenes", "What places may each of them hold inside?"),
)
LONGEST_PICTURE_TEXT = 17 * 1024 * 1024  # base64 of environment_concept.LARGEST_PICTURE
# an export made before the environment concept was read into it: nothing to show, nothing to edit, until the next
EMPTY_SETTING = {"bodies": [], "lights": [], "backdrops": [], "plots": [], "sites": []}
NOT_READ = {"concept": {"style": "", "setting": EMPTY_SETTING, "references": [], "places": []}, "locked": True,
            "prefilled": True, "versions": 0}
# The edit form's fields a thing of the setting, each (field, label, tip); score/review/setting.py is their rule. A
# body's other values (its node, periapsis and pole) ride along unseen in its row's data-keep.
BODY_COLUMNS = (
    ("name", "Body", "moves under the physics: a star, world or moon"),
    ("reference", "Real", "a real body of the reference table (data/physics/bodies.json): its values are the table's, "
                          "each cited; empty for an invented one"),
    ("radius_km", "Radius km", "its mean radius"), ("mass_kg", "Mass kg", "its mass: its gravity follows"),
    ("around", "Orbits", "the body it orbits; empty for the one the others orbit"),
    ("distance_km", "Distance km", "its orbit's semi-major axis"), ("period_days", "Period days", "one orbit"),
    ("eccentricity", "Eccentricity", "how far its orbit is from a circle"),
    ("inclination_deg", "Inclination °", "its orbit's tilt to the ecliptic"),
    ("day_hours", "Day h", "one turn"), ("tilt_deg", "Tilt °", "its axis' tilt to its orbit"),
    ("locked_to", "Faces", "the body it keeps one side to (no day of its own)"),
    ("kelvin", "Light K", "for one that shines: its light's colour"),
    ("lux", "Lux", "for one that shines: its light's strength at the distance below"),
    ("lux_at_km", "Lux at km", "the distance that strength is measured at"))
LIGHT_COLUMNS = (
    ("name", "Light", "a far source of light with no body: one house's sun"), ("kelvin", "K", "its colour"),
    ("lux", "Lux", "its strength on ground facing it"), ("latitude", "Latitude °", "of the ground its path is over"),
    ("tilt_deg", "Tilt °", "how far it swings over a year"), ("day_hours", "Day h", "one day"),
    ("year_days", "Year days", "one year"), ("equinox", "Equinox", "a spring equinox at local noon (UTC)"))
BACKDROP_COLUMNS = (
    ("name", "Backdrop", "too far to move: the stars, a distant skyline"),
    ("shape", "Shape", "dome (round everything) or skyline (round the horizon)"), ("lux", "Lux", "the light it gives"),
    ("kelvin", "K", "its light's colour, when it has one"))
PLOT_COLUMNS = (("name", "Plot", "flat ground with no body under it"), ("gravity", "Gravity m/s²", "its pull"))
SITE_COLUMNS = (
    ("place", "Site", "the top scene standing there"), ("on", "On", "the body or plot it stands on"),
    ("latitude", "Lat °", "on a body: degrees north"), ("longitude", "Lon °", "on a body: degrees east"),
    ("x", "x m", "on a plot: metres east"), ("y", "y m", "on a plot: metres south"),
    ("height_m", "Height m", "over the ground's mean level"))
FORM = (("bodies", "a body", BODY_COLUMNS), ("lights", "a light", LIGHT_COLUMNS),
        ("backdrops", "a backdrop", BACKDROP_COLUMNS), ("plots", "a plot", PLOT_COLUMNS),
        ("sites", "a site", SITE_COLUMNS))


def cell(value):
    """A value as a field shows it: a number in full (no rounding, so an unchanged Save keeps it), else its text."""
    if value is None:
        return ""
    return repr(float(value)) if isinstance(value, (int, float)) and not isinstance(value, bool) else str(value)


def setting_form(setting):
    """[{kind, adds, rows}] of the setting's edit form, a group a kind of thing: each row its fields [(field, label,
    tip, value)] in order and its whole row as JSON (data-keep), then an empty row that adds one."""
    def row_of(row, columns):
        return {"fields": [(field, label, tip, cell(row.get(field))) for field, label, tip in columns],
                "keep": json.dumps(row) if row else "{}"}
    return [{"kind": kind, "adds": adds, "rows": [row_of(row, columns) for row in setting.get(kind, [])],
             "new": row_of({}, columns)} for kind, adds, columns in FORM]


def scene_times(world_state):
    """{place: its scene time} from the environment's plan, where it has one."""
    plan = (world_state.environment_plan or {}).get("plan") or {}
    return {site["place"]: site["time"] for found in plan.get("maps", []) for site in found.get("sites", [])
            if site.get("time")}


def title_of(world):
    """'Environment 1' of `world1`."""
    number = re.search(r"\d+$", world)
    return f"Environment {number.group()}" if number else world


def checked_world(source, world):
    """The WorldState of `world` when it is this cockpit's environment; else 404."""
    found = source.world_state()
    if world != found.world:
        raise Http404(f"no environment {world}")
    return found


def requests_of(world, kinds):
    """The owner's requests of `kinds` for `world`, oldest first; an answered picture's bytes dropped from its
    request once (the store's machine keeps the picture)."""
    found = list(SyncRequest.objects.filter(kind__in=kinds, payload__world=world).order_by("created"))
    for item in found:
        if item.kind == REFERENCE and item.state not in concepts.OPEN and item.payload.get("data"):
            item.payload = {**item.payload, "data": ""}
            item.save(update_fields=["payload"])
    return found


def pending(world):
    """True while one of his environment concept requests is on its way."""
    return any(item.state in concepts.OPEN for item in requests_of(world, (ASK, SAVE, REFERENCE)))


def answer_of(item):
    try:
        return json.loads(item.detail or "{}")
    except ValueError:
        return {}


def shown(world_state):
    """{concept, locked, ...} as his page shows it: the source's, and hosted, his versions and pictures since its
    export unless refused."""
    found = dict(world_state.environment_concept or {})
    if not actions.hosted() or not found:
        return found
    for item in requests_of(world_state.world, (SAVE, REFERENCE)):
        if item.state == "refused" or item.created.isoformat() <= (world_state.made_at or ""):
            continue
        if item.kind == SAVE:
            found = {**found, "concept": item.payload["concept"], "locked": item.payload["locked"], "prefilled": False}
        elif item.state == "done" and answer_of(item).get("picture"):
            added = {"picture": answer_of(item)["picture"], "shows": item.payload.get("shows") or "",
                     "place": item.payload.get("place") or None}
            found = {**found, "concept": {**found["concept"], "references": [*found["concept"]["references"], added]}}
    return found


def pictures(world_state):
    """{picture path: FileRef} of the references: the source's, and hosted, those answered since its export."""
    found = dict(world_state.environment_pictures)
    for item in requests_of(world_state.world, (REFERENCE,)):
        answer = answer_of(item)
        if item.state == "done" and answer.get("sha") and answer["picture"] not in found:
            found[answer["picture"]] = file_ref(answer["sha"], answer["name"], 0)
    return found


def proposal_lines(proposed):
    """[line] of an ask's proposed fields, one a row."""
    lines = []
    for field, value in proposed.items():
        if field == "style":
            lines.append(value)
        if field == "setting":
            lines += setting_lines(value)
        for row in value if isinstance(value, list) else []:
            if field == "references":
                lines.append(f"{row['shows']}" + (f" · {row['place']}" if row.get("place") else ""))
            elif field == "places":
                lines.append(row["name"] + (f": {', '.join(row['holds'])}" if row.get("holds") else ""))
    return lines


def setting_lines(setting):
    """[line] of a proposed setting: a body or plot a line with its gravity and what it orbits, a light and a backdrop
    a line, a site a line."""
    return ([f"{row['name']} {row['gravity']} m/s²" + (f" · orbits {row['around']}" if row.get("around") else "")
             + (" · real" if row.get("reference") else "") for row in setting.get("bodies", [])]
            + [f"{row['name']} · a light" for row in setting.get("lights", [])]
            + [f"{row['name']} · a backdrop" for row in setting.get("backdrops", [])]
            + [f"{row['name']} {row['gravity']} m/s² · a plot" for row in setting.get("plots", [])]
            + [f"{row['place']} on {row['on']}" for row in setting.get("sites", [])])


def asks(world):
    """[{id, topic, question, answer, euros, state, lines, why, body}] of his interview's asks, oldest first."""
    words = {topic: question for topic, _, question in QUESTIONS}
    found = []
    for item in requests_of(world, (ASK,)):
        answer = answer_of(item) if item.state == "done" else {}
        found.append({"id": item.pk, "topic": item.payload.get("topic"), "question": words.get(item.payload.get("topic")),
                      "answer": item.payload.get("answer"), "euros": item.payload.get("euros"), "state": item.state,
                      "lines": proposal_lines(answer.get("proposed") or {}),
                      "why": item.detail if item.state == "refused" else None, "body": json.dumps({"ask": item.pk})})
    return found


def topic_now(asked, wanted):
    """The question shown: `wanted` when it is one, else the first with no answer done, else the last."""
    topics = [topic for topic, _, _ in QUESTIONS]
    if wanted in topics:
        return wanted
    done = {item["topic"] for item in asked if item["state"] == "done"}
    return next((topic for topic in topics if topic not in done), topics[-1])


def steps_around(topic):
    """{number, previous, next} of the question shown: its place in QUESTIONS and the topics either side (None at
    an end)."""
    topics = [name for name, _, _ in QUESTIONS]
    at = topics.index(topic)
    return {"number": at + 1, "previous": topics[at - 1] if at else None,
            "next": topics[at + 1] if at + 1 < len(topics) else None}


def home(request):
    """`/`: the environments, each opening its concept page, and the hub of what spans them."""
    from score.dashboard.pages import machine, run_monitor, views
    source = state.source()
    overview = views.overview_of(source)
    world = overview["world"]  # one read of the whole state: each takes seconds on the real store
    concept = shown(world)
    held = concept.get("concept") or {}
    references = pictures(world)
    picture = next((references[ref["picture"]] for ref in held.get("references", []) if ref["picture"] in references),
                   None)
    return render(request, "pages/home.html", {
        "machine": machine.shown(request, source, source.machine()), "batch": run_monitor.live_batch(source),
        "money": cockpit.month_money(overview["view"]), "environments": [{
            "title": title_of(world.world), "href": f"/environments/{world.world}/", "locked": concept.get("locked"),
            "style": held.get("style"), "picture": picture, "places": len(held.get("places", []))}]})


def concept_page(request, world):
    """`/environments/<world>/`: the environment concept (module docstring)."""
    world_state = checked_world(state.source(), world)
    concept = shown(world_state) or NOT_READ
    asked = asks(world)
    topic = topic_now(asked, request.GET.get("q"))
    can = is_owner(request.user) and actions.decisions_on() and concept is not NOT_READ
    waiting = pending(world)
    names = {row["place"]: row["name"] for row in concept["concept"].get("places", []) if row.get("place")}
    setting = {**EMPTY_SETTING, **(concept["concept"].get("setting") or {})}
    return render(request, "pages/environment_concept.html", {
        "world": world, "title": title_of(world), "shown": concept, "concept": concept["concept"],
        "setting": setting_picture.view_of(setting, scene_times(world_state), names),
        "setting_form": setting_form(setting),
        "references": [{**ref, "file": found.get(ref["picture"])} for found in [pictures(world_state)]
                       for ref in concept["concept"]["references"]],
        "asks": [item for item in asked if item["topic"] == topic],
        "topic": topic, "topics": QUESTIONS, **steps_around(topic),
        "question": next(question for name, _, question in QUESTIONS if name == topic),
        "euros": world_state.environment_ask_euros, "pending": waiting, "can": can,
        "editable": can and not concept["locked"] and not waiting,
        "save_body": json.dumps({"locked": False}), "lock_body": json.dumps({"locked": True}),
        "unlock_body": json.dumps({"sure": True, "locked": False}),
        "ask_body": json.dumps({"topic": topic, "euros": world_state.environment_ask_euros})})


def queued(request, world, kind, payload, background=False):
    """His request for the store's machine; local mode applies it here (`background`: in a thread); the request."""
    item = SyncRequest.objects.create(kind=kind, user=request.user.username, payload={"world": world, **payload})
    if not actions.hosted():
        (concepts.in_background if background else concepts.applied_here)(item.pk)
    return SyncRequest.objects.get(pk=item.pk)


def refused(detail, status=409):
    return JsonResponse({"detail": detail}, status=status)


def answered(item):
    """JSON {said, request} for a request, or {detail} when it was refused."""
    if item.state == "refused":
        return refused(item.detail)
    return JsonResponse({"said": item.detail or "asked", "request": item.pk})


def checked_click(request, world):
    """((the concept as shown, the request's body), None) of an owner's click with nothing of his on its way, or
    (None, the JsonResponse refusing it)."""
    concept = shown(checked_world(state.source(), world))
    body = concepts.body_of(request)
    if not is_owner(request.user):
        return None, refused("only the owner edits the environment concept", 403)
    if body is None:
        return None, refused("refused: not a request", 422)
    if not concept:
        return None, refused("refused: the environment concept is not read here yet")
    if pending(world):
        return None, refused("refused: one of his requests is on its way")
    return (concept, body), None


def unlocked_click(request, world):
    """checked_click, refused too while the concept is locked."""
    found, refusal = checked_click(request, world)
    if found and found[0]["locked"]:
        return None, refused("refused: it is locked; unlock it first")
    return found, refusal


@require_POST
def save(request, world):
    """POST {concept, locked, sure}: his Save (locked false) or Lock (true) of the unlocked concept, or with `sure`
    his Unlock of the locked one (the shown concept kept, unlocked); JSON {said}, or {detail} when refused."""
    found, refusal = checked_click(request, world)
    if refusal:
        return refusal
    concept, body = found
    if concept["locked"]:
        if body.get("locked") or body.get("sure") is not True:
            return refused("refused: it is locked; unlocking asks to be sure")
        return answered(queued(request, world, SAVE, {"concept": concept["concept"], "locked": False}))
    if not isinstance(body.get("concept"), dict):
        return refused("refused: no concept", 422)
    return answered(queued(request, world, SAVE, {"concept": body["concept"], "locked": bool(body.get("locked"))}))


@require_POST
def taken(request, world):
    """POST {ask}: his Take of an answered ask: its proposed fields into the unlocked concept, a new version."""
    found, refusal = unlocked_click(request, world)
    if refusal:
        return refusal
    concept, body = found
    item = SyncRequest.objects.filter(pk=body.get("ask"), kind=ASK, payload__world=world, state="done").first()
    proposed = answer_of(item).get("proposed") if item else None
    if not proposed:
        return refused("refused: no answered ask", 422)
    return answered(queued(request, world, SAVE, {"concept": {**concept["concept"], **proposed}, "locked": False}))


@require_POST
def ask(request, world):
    """POST {topic, answer, euros}: his Send, the spend yes for that one model call at `euros` (the price his button
    showed); JSON {said, request}, or {detail} when refused."""
    found, refusal = unlocked_click(request, world)
    if refusal:
        return refusal
    concept, body = found
    topic, answer = str(body.get("topic") or ""), str(body.get("answer") or "").strip()
    if topic not in {name for name, _, _ in QUESTIONS} or not answer:
        return refused("refused: no question or no answer", 422)
    payload = {"topic": topic, "answer": answer[:2000], "euros": body.get("euros"), "concept": concept["concept"]}
    return answered(queued(request, world, ASK, payload, background=True))


@require_POST
def reference(request, world):
    """POST {name, data (base64), shows, place}: his new reference picture, into the private bucket and the unlocked
    concept; JSON {said}, or {detail} when refused."""
    found, refusal = unlocked_click(request, world)
    if refusal:
        return refusal
    _, body = found
    if not body.get("data") or len(str(body["data"])) > LONGEST_PICTURE_TEXT:
        return refused("refused: no picture, or one too large", 422)
    payload = {name: str(body.get(name) or "") for name in ("name", "data", "shows", "place")}
    return answered(queued(request, world, REFERENCE, payload, background=True))
