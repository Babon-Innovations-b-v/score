"""The basket: every item a run on main would buy (proposals/make.py), grouped by place, each opening to its details,
free and fast to read, made before anything is bought: the place in 3D with the parts it changes marked and a
before and after switch, the list of what changes read from the two OpenUSD stages, what each paid step would be made
from, the price on the runner's measured numbers (guesses said apart) and the questions with their recommended answers.
Read from the basket's records (proposals/records.py) here or in the export; nothing here is worked out from the store.

A buy or a not now is the owner's only (BasketChoice), kept as he saw the item (its version). So is an answer to a
question (BasketAnswer): he takes the recommended answer or gives his own, kept where agents read it (the basket's
answers.json on the store's machine: at once locally, hosted through a SyncRequest of kind "answer"). His one
checkout of what he bought (checkout/flow.py: each item's plan, the stop line, one batch) starts here: local at once,
hosted queued as a SyncRequest of kind "checkout" with the items he saw, run by the store's machine when they still
stand as he saw them."""
import json
import re
import uuid
from collections import Counter

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from score.dashboard import state
from score.dashboard.pages import actions
from score.dashboard.pages.models import BasketAnswer, BasketChoice, SyncRequest, is_owner
from score.dashboard.proposals import records
from score.dashboard.state import groups

CHOICES = {"buy": "Bought", "later": "Not now"}
NUMBERED = re.compile(r"[_-]?\d+$")
# A buy's reason in the runner's words, and in the owner's.
REASONS = {"code changed": "the code that makes it changed", "never ran": "it was never made",
           "library changed": "the library changed", "places changed": "the places changed",
           "maker changed": "its maker changed", "files changed": "its data changed"}
OBJECT_WORDS = (("added", "added"), ("removed", "taken out"), ("moved", "moved"), ("reshaped", "reshaped"),
                ("refinished", "refinished"))
KEYED_WORDS = (("added", "added"), ("removed", "taken out"), ("changed", "changed"))
MOST_NAMED = 8
SEVERAL = "several places"


def basket_root():
    """Where this process reads the basket: the dashboard's home locally, the current export when hosted."""
    if actions.hosted():
        return settings.SCORE_HOME / "export" / "current" / "proposals"
    return settings.SCORE_HOME / "proposals"


def file_url(folder, name):
    return f"/basket-file/{folder or records.ENVIRONMENT}/{name}"


# --- words ----------------------------------------------------------------------------------------------------------

def clean(word):
    """A name's word for a person: without the number a repeat gets, the underscores or the dashes."""
    return NUMBERED.sub("", word).replace("_", " ").replace("-", " ").strip() or word


def pretty(name):
    """A changed thing's name in words: its own name without the path (a shown place's part as "camp's outside")."""
    parts = (name or "").strip("/").split("/")
    if parts[0] == "Places" and len(parts) > 2:
        return f"{clean(parts[1])}'s {clean(parts[2])}"
    return clean(parts[-1])


def named(entries):
    """"3 x crate, lamp post" of changed things: each name once with its count, the most common first."""
    counts = Counter(pretty(entry["name"]) for entry in entries)
    shown = [f"{count} x {name}" if count > 1 else name for name, count in counts.most_common(MOST_NAMED)]
    rest = len(counts) - MOST_NAMED
    return ", ".join(shown) + (f" and {rest} more" if rest > 0 else "")


def layer_words(layers):
    return " and ".join(layer.replace("-", " ") for layer in layers)


def place_words(place):
    return place.replace("_", " ") if place else "the environment"


def item_name(item):
    return item.get("title") or layer_words(item["layers"]).capitalize() or item["id"]


def reason_words(why):
    """A buy's reason in plain words: "reads a@p" is what it is made from being made again."""
    if why.startswith("reads "):
        read = sorted({groups.label(name.split("@")[0]) for name in why[len("reads "):].split(";")[0].split(", ")})
        return f"what it is made from is made again ({', '.join(read)})"
    return "; ".join(REASONS.get(part.strip(), part.strip()) for part in why.split(";")[0].split(","))


def sentence(item, said):
    """The item in one sentence: a department's own words, else what it makes again and the runner's main reason."""
    if said.get("sentence"):
        return said["sentence"]
    if not item["nodes"]:
        return "A run on main does not buy this yet."
    reasons = Counter(reason_words(why) for why in item["why"].values())
    return f"{layer_words(item['layers']).capitalize()} made again: {reasons.most_common(1)[0][0]}."


def hours(minutes):
    if not minutes:
        return None
    return f"{minutes:.0f} min" if minutes < 90 else f"{minutes / 60:.1f} h"


def price_words(totals):
    """{likely, high, guessed, guessed_jobs, jobs, measured, hours} of an item's totals; likely and high are the
    measured jobs' only, None when none is measured (a guess is never a price)."""
    jobs, unmeasured = totals.get("nodes", 0), len(totals.get("unmeasured", []))
    measured = jobs - unmeasured
    return {"likely": totals["likely_euros"] if measured else None, "high": totals["high_euros"] if measured else None,
            "guessed": totals.get("guessed_euros", 0.0), "guessed_jobs": unmeasured, "jobs": jobs,
            "measured": measured, "hours": hours(totals.get("high_minutes")), "minutes": totals.get("high_minutes")}


# --- what changes -----------------------------------------------------------------------------------------------------

def change_lines(changes):
    """[{what, names, kind}] of what changes for free, read from a place's details (details.py), in plain words."""
    if not changes:
        return []
    found = []
    for kind, words in OBJECT_WORDS:
        given = changes["objects"][kind]
        if given["count"]:
            found.append({"what": f"{given['count']} object{'s' if given['count'] != 1 else ''} {words}",
                          "names": named(given["listed"]), "kind": kind})
    for kind, words in KEYED_WORDS:
        count = changes["lamps"][kind]["count"]
        if count:
            found.append({"what": f"{count} lamp{'s' if count != 1 else ''} {words}", "names": "", "kind": kind})
    for area, thing in (("sounds", "sound"), ("cameras", "camera")):
        for kind, words in KEYED_WORDS:
            names = changes[area][kind]
            if names:
                found.append({"what": f"{len(names)} {thing}{'s' if len(names) != 1 else ''} {words}",
                              "names": named([{"name": name} for name in names]), "kind": kind})
    return found


def marks(changes, side):
    """[{low, high, kind}] the viewer outlines: on the after, what is added, moved, reshaped or refinished and the
    lamps added or changed; on the before, what is taken out, moved, reshaped or refinished and the lamps taken out
    or changed."""
    if not changes:
        return []
    kinds = ("added", "moved", "reshaped", "refinished") if side == "after" else ("removed", "moved", "reshaped",
                                                                                   "refinished")
    lamps = ("added", "changed") if side == "after" else ("removed", "changed")
    found = [{"low": entry["low"], "high": entry["high"], "kind": kind}
             for kind in kinds for entry in changes["objects"][kind]["listed"] if entry.get("low")]
    return found + [{"low": entry["low"], "high": entry["high"], "kind": "lamp"}
                    for kind in lamps for entry in changes["lamps"][kind]["listed"]]


def has_after(found):
    return bool(found and found.get("copy") and "error" not in found["copy"])


# --- what it is made from ---------------------------------------------------------------------------------------------

def shown_files(folder, files):
    """({pictures}, {texts}) of a details' input files, each picture with its URL."""
    pictures = [{"url": file_url(folder, each["file"]), "name": each["name"],
                 "from": "data" if each["from"] == "data" else groups.label(each["from"].split("@")[0])}
                for each in files if each.get("file")]
    texts = [{"name": each["name"], "text": each["text"]} for each in files if each["kind"] == "text"]
    return pictures, texts


def node_inputs(node, root, known):
    """What one paid step would be made from: {step, place, made, blocked, pictures, texts}."""
    place = node.partition("@")[2] or None
    if place not in known:
        known[place] = records.details(root, place) or {}
    given = known[place].get("inputs", {}).get(node, {})
    pictures, texts = shown_files(place, given.get("files", []))
    return {"step": groups.label(node.split("@")[0]), "place": place_words(place), "node": node,
            "blocked": given.get("blocked"), "pictures": pictures, "texts": texts,
            "made": [groups.label(read["node"].split("@")[0]) for read in given.get("reads", [])
                     if read["how"] == records.MADE]}


def item_inputs(item, root, known):
    """[node_inputs] of the item's paid steps, a declared item's own pictures and files first."""
    found = []
    if item.get("declared"):
        folder = records.declared_folder(item["id"])
        own = (records.details(root, folder) or {}).get("inputs", {}).get("declared", {})
        pictures, texts = shown_files(folder, own.get("files", []))
        if pictures or texts:
            found.append({"step": "its plan", "place": "", "node": "", "blocked": None, "pictures": pictures,
                          "texts": texts, "made": []})
    return found + [node_inputs(node, root, known) for node in item["nodes"]]


# --- questions --------------------------------------------------------------------------------------------------------

def questions(item, said, given):
    """[{number, ask, recommended, answer}] of the item's questions, his answer where he gave one to that very
    question."""
    found = []
    for number, asked in enumerate(said.get("questions") or [], 1):
        answer = given.get((item["id"], number))
        found.append({"number": number, "ask": asked["ask"], "recommended": asked["recommended"],
                      "answer": answer.answer if answer is not None and answer.question == asked["ask"] else None})
    return found


def answers_given():
    return {(answer.item, answer.number): answer for answer in BasketAnswer.objects.all()}


def answered(user, ident, number, question, answer):
    """Keep the owner's answer to an item's question, here and, on the store's machine, in the basket's answers.json
    where agents read it; words."""
    if not records.NAME.match(ident or "") or not str(number).isdigit() or not question or not answer.strip():
        return "refused: that is not a question of the basket"
    BasketAnswer.objects.update_or_create(item=ident, number=int(number), defaults={
        "question": question, "answer": answer.strip(), "by": user})
    if actions.hosted():
        SyncRequest.objects.create(kind="answer", user=user, payload={
            "item": ident, "number": int(number), "question": question, "answer": answer.strip()})
        return "Answer kept: the store's machine passes it to the agents on its next sync"
    records.put_answer(basket_root(), ident, number, {"question": question, "answer": answer.strip(), "by": user,
                                                      "at": timezone.now().isoformat(timespec="seconds")})
    return "Answer kept where the agents read it"


# --- the basket page --------------------------------------------------------------------------------------------------

def place_hero(source, place):
    """The place's current picture, or None."""
    if not place or place not in source.places():
        return None
    hero = source.place_card(place).hero
    return (hero.thumb_url or hero.url) if hero else None


def choice_of(item, choices):
    """His answer to the item as he saw it, or None (none yet, or the item changed since)."""
    found = choices.get(item["id"])
    if found is None or found.version != item["version"]:
        return None
    return {"choice": found.choice, "said": CHOICES.get(found.choice, found.choice)}


def summary_words(item, root, known):
    """The tile's one line of what changes for free."""
    lines = [line["what"] for place in item["places"] for line in
             change_lines((known.setdefault(place, records.details(root, place) or {})).get("changes"))]
    if lines:
        return " · ".join(lines[:3])
    reasons = Counter(reason_words(why) for why in item["why"].values())
    if not reasons:
        return "Nothing changes for free: open it to see what it is made from"
    return "Why again: " + "; ".join(reason for reason, _ in reasons.most_common(2))


def tile(item, root, source, known, choices, said, given):
    """One item as the basket lists it."""
    first = next((picture["url"] for step in item_inputs(item, root, known) for picture in step["pictures"]), None)
    open_questions = [asked for asked in questions(item, said, given) if asked["answer"] is None]
    return {"id": item["id"], "name": item_name(item), "sentence": sentence(item, said),
            "summary": summary_words(item, root, known),
            "picture": (place_hero(source, item["place"]) if item["place"] else None) or first,
            "price": price_words(item["totals"]), "choice": choice_of(item, choices), "missing": item["missing"],
            "waiting": not item["nodes"], "questions": len(open_questions)}


def group_of(item):
    """Where the basket lists an item: a department's own item first, under its title; else its one place; else
    with the items across places; else with the environment's own rows."""
    if item.get("declared"):
        return (0, item["title"])
    if item["place"]:
        return (1, item["place"])
    return (2, SEVERAL) if item["places"] else (3, None)


def group_words(key):
    rank, name = key
    return {"place": name if rank == 1 else None, "name": name if rank in (0, 2) else place_words(name)}


def place_groups(root, source):
    """[{place, name, hero, tiles}] of the basket's items: the departments' own items, then by place, then the items
    across places, then the environment's own rows."""
    choices = {choice.item: choice for choice in BasketChoice.objects.all()}
    declared, given, known, by_group = records.declared(root), answers_given(), {}, {}
    for item in records.items(root):
        by_group.setdefault(group_of(item), []).append(item)
    return [{**group_words(key), "hero": place_hero(source, key[1]) if key[0] == 1 else None,
             "tiles": [tile(item, root, source, known, choices, declared.get(item["id"], {}), given)
                       for item in by_group[key]]}
            for key in sorted(by_group, key=lambda key: (key[0], key[1] or ""))]


def chosen_total(found):
    """{count, likely, high, guessed, guessed_jobs, hours} of the items he chose to buy (high None while one has no
    measured job; hours the runner's high minutes of every item end to end, None while one has none)."""
    bought = [each for group in found for each in group["tiles"]
              if each["choice"] and each["choice"]["choice"] == "buy"]

    def summed(key):
        values = [each["price"][key] for each in bought]
        return round(sum(values), 2) if values and None not in values else None
    return {"count": len(bought), "likely": summed("likely"), "high": summed("high"),
            "guessed": round(sum(each["price"]["guessed"] for each in bought), 2),
            "guessed_jobs": sum(each["price"]["guessed_jobs"] for each in bought),
            "hours": hours(summed("minutes"))}


def last_checkout():
    """What became of his last checkout, in words, or "": the store's report hosted, the Checkout row local."""
    if actions.hosted():
        queued = SyncRequest.objects.filter(kind="checkout").first()
        if queued is None:
            return ""
        if queued.state in ("waiting", "picked_up"):
            return "Your checkout waits for the store's machine (every few minutes)."
        return f"Your checkout: {queued.state}. {queued.detail}"
    from score.dashboard.pages.models import Checkout
    found = Checkout.objects.order_by("-pk").first()
    return f"Checkout {found.pk}: {found.state}. {found.detail}" if found else ""


BATCH_TONES = {"launching": "review", "waiting": "review", "picked_up": "review", "running": "review",
               "launched": "done", "done": "done", "refused": "bad", "failed": "bad"}


def last_batch():
    """{state, tone, stop, tip} of his last checkout, or None before one: `stop` the batch's own stop (its high plus
    10%, flow.BUFFER) once its stop line is written here, None before that or while hosted (the store's machine
    writes it)."""
    if actions.hosted():
        queued = SyncRequest.objects.filter(kind="checkout").first()
        return queued and {"state": queued.state, "tone": BATCH_TONES.get(queued.state, "idle"), "stop": None,
                           "tip": queued.detail}
    from score.dashboard.checkout import flow
    from score.dashboard.pages.models import Checkout
    found = Checkout.objects.order_by("-pk").first()
    if found is None:
        return None
    high = found.stop_line.get("high")
    return {"state": found.state, "tone": BATCH_TONES.get(found.state, "idle"), "tip": found.detail,
            "stop": round(high * flow.BUFFER, 2) if high is not None else None}


def current_choices(items):
    """{item id: buy or later} of his choices made on the version of each item shown now."""
    versions = {item["id"]: item["version"] for item in items}
    return {choice.item: choice.choice for choice in BasketChoice.objects.all()
            if versions.get(choice.item) == choice.version}


def basket_context():
    """The basket's part of the basket page."""
    root = basket_root()
    found = place_groups(root, state.source())
    return {"places": found, "chosen_items": chosen_total(found), "made_at": records.index(root).get("made_at"),
            "waiting": sum(1 for group in found for each in group["tiles"] if each["choice"] is None),
            "checkout_key": uuid.uuid4().hex, "last_checkout": last_checkout()}


def unanswered():
    """How many items of the basket wait for his answer (the menu's count)."""
    choices = {choice.item: choice for choice in BasketChoice.objects.all()}
    return sum(1 for item in records.items(basket_root()) if choice_of(item, choices) is None)


# --- one item ---------------------------------------------------------------------------------------------------------

def shown_place(item, asked, known, root):
    """The place the item's 3D view shows: the one asked for, else the first with a free after, else the first."""
    for place in item["places"]:
        known.setdefault(place, records.details(root, place) or {})
    if asked in item["places"]:
        return asked
    return next((place for place in item["places"] if has_after(known[place])), item["places"][0] if item["places"]
                else None)


def place_choices(item, shown, known, source):
    """[{place, name, picture, here, changes}] of the item's places, for the picker."""
    return [{"place": place, "name": place_words(place), "picture": place_hero(source, place), "here": place == shown,
             "changes": len(change_lines(known[place].get("changes")))} for place in item["places"]]


def found_item(root, ident):
    try:
        item = records.item(root, records.checked(ident))
    except records.BadName as bad:
        raise Http404(str(bad)) from bad
    if item is None:
        raise Http404(f"no basket item {ident}")
    return item


def item_page(request, ident):
    """One item's details."""
    root, source, known = basket_root(), state.source(), {}
    item = found_item(root, ident)
    said = records.declared(root).get(item["id"], {})
    place = shown_place(item, request.GET.get("place"), known, root)
    here = known.get(place, {}) if place else {}
    choices = {choice.item: choice for choice in BasketChoice.objects.filter(item=item["id"])}
    return render(request, "pages/basket_item.html", {
        "item": item, "name": item_name(item), "sentence": sentence(item, said), "place": place,
        "place_name": place_words(place), "places": place_choices(item, place, known, source),
        "questions": questions(item, said, answers_given()), "has_after": has_after(here),
        "after_error": (here.get("copy") or {}).get("error"), "error": here.get("error"),
        "blocked": here.get("blocked"), "changes": change_lines(here.get("changes")),
        "made": [groups.label(stage) for stage in here.get("made", [])],
        "paid": sorted({groups.label(node.split("@")[0]) for node in item["nodes"]}),
        "inputs": item_inputs(item, root, known), "price": price_words(item["totals"]),
        "choice": choice_of(item, choices), "made_at": here.get("made_at"),
        "view": f"/view/{place}?item={item['id']}&embed=1" if place and place in source.places() else None,
        "reasons": sorted({reason_words(why) for why in item["why"].values()})})


def seen_items():
    """[{id, version}] of the items he chose to buy, as he saw them."""
    return [{"id": choice.item, "version": choice.version} for choice in BasketChoice.objects.filter(choice="buy")]


def checked_out(user, key, seen):
    """His one checkout of the items he bought: hosted queued for the store's machine, local started here; words."""
    if not seen:
        return "refused: choose Buy on at least one item first"
    if actions.hosted():
        SyncRequest.objects.create(kind="checkout", user=user.username, payload={"key": key, "items": seen})
        return "Checkout sent: the store's machine checks it and starts the batch on its next sync"
    from score.dashboard.checkout import flow
    return flow.start(user, key, True, seen)[1]


@require_POST
def buy_yes(request):
    """The Buy screen's one yes (#42): his checkout of the items he chose, signed in, CSRF by Django; JSON {said},
    or {detail} with 409 when refused. Its stop is the batch's high plus 10%, never asked."""
    if not is_owner(request.user):
        return JsonResponse({"detail": "only the owner checks out"}, status=403)
    try:
        key = str(json.loads(request.body or b"{}").get("key", ""))
    except (ValueError, AttributeError):
        key = ""
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        return JsonResponse({"detail": "refused: no checkout key"}, status=422)
    said = checked_out(request.user, key, seen_items())
    return JsonResponse({"detail": said}, status=409) if said.startswith("refused") else JsonResponse({"said": said})


@require_POST
def checkout(request):
    """The owner's checkout of every item he chose to buy (owner only, CSRF by Django, "I buy these" ticked)."""
    if not is_owner(request.user):
        return HttpResponseForbidden("only the owner checks out")
    key = request.POST.get("key", "")
    if not re.fullmatch(r"[0-9a-f]{32}", key) or request.POST.get("confirm") != "yes":
        messages.error(request, "refused: tick \"I buy these\" first")
        return redirect("/basket/#checkout")
    said = checked_out(request.user, key, seen_items())
    (messages.error if said.startswith("refused") else messages.success)(request, said)
    return redirect("/basket/#checkout")


@require_POST
def choose(request):
    """The owner's buy or not now of one item, as he saw it (owner only, CSRF by Django)."""
    if not is_owner(request.user):
        return HttpResponseForbidden("only the owner buys")
    ident, version, choice = (request.POST.get(name, "") for name in ("item", "version", "choice"))
    item = records.item(basket_root(), ident) if records.NAME.match(ident) else None
    if choice not in CHOICES or item is None:
        messages.error(request, "refused: that is not an item of the basket")
        return redirect("/basket/")
    if item["version"] != version:
        messages.error(request, "refused: the item changed while you looked at it: look again")
    elif choice == "buy" and not item["nodes"]:
        messages.error(request, "refused: a run on main does not buy this yet")
    else:
        BasketChoice.objects.update_or_create(item=ident, defaults={"version": version, "choice": choice,
                                                                    "by": request.user.username})
        messages.success(request, f"{CHOICES[choice]}: {item_name(item)}")
    return redirect(f"/basket/item/{ident}/" if request.POST.get("back") == "item" else f"/basket/#item-{ident}")


@require_POST
def answer(request):
    """The owner's answer to one question of an item: the recommended one, or his own (owner only, CSRF by Django)."""
    if not is_owner(request.user):
        return HttpResponseForbidden("only the owner answers")
    ident, number = request.POST.get("item", ""), request.POST.get("number", "")
    item = records.item(basket_root(), ident) if records.NAME.match(ident) else None
    asked = next((each for each in questions(item, records.declared(basket_root()).get(ident, {}), {})
                  if str(each["number"]) == number), None) if item else None
    if asked is None:
        messages.error(request, "refused: that is not a question of the basket")
        return redirect("/basket/")
    given = asked["recommended"] if request.POST.get("take") == "recommended" else request.POST.get("answer", "")
    said = answered(request.user.username, ident, number, asked["ask"], given)
    (messages.error if said.startswith("refused") else messages.success)(request, said)
    return redirect(f"/basket/item/{ident}/#questions")
