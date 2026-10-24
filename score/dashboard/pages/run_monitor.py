"""The run monitor (`/buy/run/`, `run_monitor.html`): the newest Buy's batch on one screen, summary before detail. Its
state with when it started, how long it has run and the ETA left (the checkout's runner times; "at least" while a
bought step was never timed), the owner's Stop everything while it lives; the money spent against its likely and high
price and its stop on one bar; a row a scene, parent scenes before their child scenes, each with its rows done of its
total, what it does now and a state chip, a finished one linking to its result; the warm pool's cards and processor
machines; the problems, newest first. Read from state/batch_run.py: live locally, from the export hosted (the page
says how fresh, and reads itself again while the batch lives). Hosted, a Buy the store's machine has not answered yet
shows as sent, waiting for its next pass. The Buy's yes opens this page; Home links to it while a batch lives."""
import datetime

from django.shortcuts import render

from score.dashboard import state
from score.dashboard.pages import actions, present
from score.dashboard.pages.models import SyncRequest, is_owner
from score.dashboard.state import batch_run, costs, groups

# A batch state's words, chip tone and hover text.
STATES = {"starting": ("Starting", "idle", "the runner plans the batch it bought"),
          "running": ("Running", "new", "the batch runs"),
          "waiting": ("Waiting for machines", "review", "the batch runs, but no graphics card is warm yet"),
          "stopped": ("Stopped", "bad", "the batch stopped before every scene was done"),
          "finished": ("Finished", "done", "every row ran")}
SCENE_STATES = {"done": ("done", "done"), "failed": ("failed", "bad"), "working": ("working", "new"),
                "waiting": ("waiting", "idle"), "left": ("not done", "idle")}
RELOAD_SECONDS = {False: 20, True: 60}  # while a batch lives: local reads live, hosted follows the sync passes
ENVIRONMENT = "Whole environment"


def chain(place, within):
    """The scenes and parent shells holding `place`, outermost first, then the place itself."""
    found, seen = [place], {place}
    while within.get(found[0]) and within[found[0]] not in seen:
        found.insert(0, within[found[0]])
        seen.add(found[0])
    return found


def ordered(places, within, names):
    """[(place, depth)] parent scenes before their child scenes, by name inside a parent; depth counts the
    scenes of `places` holding it. The environment's own rows ("") first."""
    shown = set(places)
    keyed = sorted(places, key=lambda place: [names.get(each, each).lower() for each in chain(place, within)]
                   if place else [])
    return [(place, sum(1 for each in chain(place, within)[:-1] if each in shown)) for place in keyed]


def scene_name(place, names):
    """A scene's short name, else its key in words; the environment's own rows as the whole environment."""
    return (names.get(place) or present.place_title(place)) if place else ENVIRONMENT


def result_link(source, place):
    """A finished scene's result: its 3D web copy, else its scene page; None for the environment's rows."""
    if not place:
        return None
    return f"/view/{place}" if source.web3d(place) else f"/place/{place}/"


def percent(part, whole):
    return round(100 * part / whole, 1) if whole else 0


def scene_rows(source, run, world):
    """The scenes of the batch as rows: name, depth, done of total, the bar's done and failed shares, what it does
    now, its chip and its result link once done."""
    names = groups.short_names(world)
    by_place = {scene["place"]: scene for scene in run["scenes"]}
    rows = []
    for place, depth in ordered(list(by_place), world.within, names):
        scene = by_place[place]
        words, tone = SCENE_STATES[scene["state"]]
        rows.append({"place": place, "name": scene_name(place, names), "depth": depth,
                     "done": scene["done"], "total": scene["total"], "failed": scene["failed"],
                     "not_run": scene["not_run"], "bar_done": percent(scene["done"], scene["total"]),
                     "bar_failed": percent(scene["failed"] + scene["not_run"], scene["total"]),
                     "now": ", ".join(scene["running"]), "state": words, "tone": tone,
                     "href": result_link(source, place) if scene["state"] == "done" else None})
    return rows


def money_bar(money):
    """The money as one bar to the stop: the spent share, the likely and high marks, in percent of the scale (the
    stop, else the high); None without a scale."""
    scale = max(value for value in (money["stop"], money["high"], money["spent"], 0) if value is not None)
    if not scale:
        return None
    spent = money["spent"] or 0
    return {"spent": percent(spent, scale), "likely": percent(money["likely"] or 0, scale),
            "high": percent(money["high"] or 0, scale), "over": money["high"] is not None and spent > money["high"]}


def moment(text):
    return datetime.datetime.fromisoformat(text) if text else None


def clock(run):
    """{started, elapsed, left, left_high, at_least, by, by_high, over}: the times in words, the ETA left from the
    runner's minutes (None while not timed), at_least when a bought step was never timed."""
    eta, started = run["eta"], moment(run["started"])
    elapsed = eta["elapsed"] or 0
    likely, high = eta["likely_minutes"], eta["high_minutes"]
    left = None if likely is None else max(0.0, likely - elapsed)
    left_high = None if high is None else max(0.0, high - elapsed)
    return {"started": started.strftime("%H:%M") if started else None,
            "day": started.strftime("%d %b") if started else None,
            "elapsed": costs.hours(elapsed), "left": None if left is None else costs.hours(left),
            "left_high": None if left_high is None else costs.hours(left_high), "at_least": bool(eta["untimed"]),
            "untimed": eta["untimed"],
            "by": (started + datetime.timedelta(minutes=likely)).strftime("%H:%M") if started and likely else None,
            "by_high": (started + datetime.timedelta(minutes=high)).strftime("%H:%M") if started and high else None,
            "over": high is not None and elapsed > high}


def freshness(source, run):
    """(when read, minutes ago or None locally): hosted the export's own time, locally the run's read."""
    made = getattr(source, "export_made_at", lambda: None)()
    when = moment(made) or moment(run["read_at"] if run else None)
    if when is None:
        return None, None
    minutes = int((datetime.datetime.now(datetime.timezone.utc) - when).total_seconds() // 60)
    return when.strftime("%H:%M"), minutes if made else None


def sent(run):
    """Hosted: the owner's newest Buy the store's machine has not made a batch of yet, {state, at, detail}; None
    when none waits (or locally, where a Buy is a checkout at once)."""
    if not actions.hosted():
        return None
    request = SyncRequest.objects.filter(kind="checkout").order_by("-created").first()
    if request is None or (run and moment(run["at"]) >= request.created):
        return None
    return {"state": request.state, "at": request.created.strftime("%H:%M"), "detail": request.detail,
            "tone": "bad" if request.state == "refused" else "review"}


def slots(kind):
    """A square a machine of the pool's size: busy, idle, then the ones still to come."""
    return ["busy"] * kind["busy"] + ["idle"] * kind["idle"] + ["short"] * kind["short"]


def machines(pool):
    """The pool's two kinds of machine as rows: {label, size, warm, busy, idle, short}, the empty kinds left out."""
    if not pool:
        return []
    return [{"label": label, **pool[kind], "slots": slots(pool[kind])} for kind, label in (("cards", "Graphics cards"),
                                                              ("processors", "Processor machines"))
            if pool[kind]["size"] or pool[kind]["warm"]]


def problem_rows(run, world):
    names = groups.short_names(world)
    return [{**problem, "name": scene_name(problem["place"], names) if problem["place"] else "Batch",
             "at": moment(problem["at"]).strftime("%H:%M") if problem["at"] else None, "at_iso": problem["at"]}
            for problem in run["problems"]]


def shown(source, run):
    """The page's context of a batch record."""
    world = source.world_state()
    label, tone, tip = STATES[run["state"]]
    live = run["state"] in batch_run.LIVE
    return {"run": run, "label": label, "tone": tone, "tip": tip, "live": live, "clock": clock(run),
            "bar": money_bar(run["money"]), "scenes": scene_rows(source, run, world),
            "machines": machines(run["pool"]), "problems": problem_rows(run, world),
            "rows_bar": percent(run["rows"]["done"], run["rows"]["total"]),
            "rows_failed_bar": percent(run["rows"]["failed"] + run["rows"]["not_run"], run["rows"]["total"])}


def monitor(request):
    """`/buy/run/`: the newest Buy's batch (module docstring)."""
    source = state.source()
    run = source.batch_run()
    at, minutes = freshness(source, run)
    context = shown(source, run) if run else {"live": False}
    waiting = sent(run)
    return render(request, "pages/run_monitor.html", {
        **context, "sent": waiting, "fresh_at": at, "fresh_minutes": minutes, "owner": is_owner(request.user),
        "reload": RELOAD_SECONDS[actions.hosted()] if context["live"] or waiting else None})


def live_batch(source):
    """Home's link to the monitor while a batch lives: {label, tone, done, total}, else None."""
    run = source.batch_run()
    if not run or run["state"] not in batch_run.LIVE:
        return None
    label, tone, _ = STATES[run["state"]]
    return {"label": label, "tone": tone, "done": run["rows"]["done"], "total": run["rows"]["total"]}
