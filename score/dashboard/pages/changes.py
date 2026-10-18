"""The Changes to buy page: every fix a department made a proposal for, one card a fix branch, each place it changes
as a picture before and after, what it fixes in one plain sentence, what was done for free, what needs the paid
batch and its price at the runner's numbers, the owner's question with the recommended answer, a show-in-3D, and
the owner's buy or not now. Read from the proposals' records (proposals/records.py) here or in the export.

A buy or a not now is the owner's only: local, it is applied at once (a buy puts the branch in the checkout's basket
at the commit he saw); hosted, it is kept here and queued for the store's machine (a SyncRequest of kind
"proposal", sync/applying.py), which applies it the same way on its next pass."""
import re

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from score.dashboard import state
from score.dashboard.pages import actions
from score.dashboard.pages.models import ProposalChoice, SyncRequest, is_owner
from score.dashboard.proposals import records
from score.dashboard.state import groups

CHOICES = {"buy": "Bought", "later": "Not now"}
ISSUE = re.compile(r"\s*\(#\d+\)")
FIRST_CLAUSE = re.compile(r"[;]\s")


def proposals_root():
    """Where this process reads proposals: the dashboard's home locally, the current export when hosted."""
    if actions.hosted():
        return settings.SCORE_HOME / "export" / "current" / "proposals"
    return settings.SCORE_HOME / "proposals"


def file_url(record, name):
    return f"/proposal/{record['branch']}/{record['place']}/{name}"


def plain_sentence(record):
    """The department's own sentence, else the branch's first change in its own words, without issue numbers."""
    if record.get("sentence"):
        return record["sentence"]
    first = FIRST_CLAUSE.split(ISSUE.sub("", record.get("change") or ""))[0].strip().rstrip(".")
    return (first[:1].upper() + first[1:] + ".") if first else "No words given for this fix yet."


def pictures_of(record, field):
    """[{name, url}] of a record's stills or before stills Blender drew, and the first failure's words, or ""."""
    drawn = [{"name": still["name"].replace("-", " "), "url": file_url(record, still["file"])}
             for still in record.get(field) or [] if "file" in still]
    failed = next((still["error"] for still in record.get(field) or [] if "error" in still), "")
    return drawn, failed


def place_hero(source, place):
    """The place's current picture from the cockpit's own reading, or None (the before when none was drawn)."""
    if place not in source.places():
        return None
    hero = source.place_detail(place).hero
    return hero.url if hero else None


def pairs(record, source):
    """[{name, before, after}] of the place's views, before and after from the same camera; the place's current
    picture stands in for a before not drawn."""
    after, _ = pictures_of(record, "stills")
    before = {still["name"]: still["url"] for still in pictures_of(record, "before")[0]}
    fallback = place_hero(source, record["place"]) if not before else None
    return [{"name": still["name"], "after": still["url"], "before": before.get(still["name"], fallback),
             "same_camera": still["name"] in before} for still in after]


def labels(stages):
    return [groups.label(stage) for stage in sorted(set(stages))]


def price_words(price):
    """{likely, high, measured, words} of a proposal's price, or {words} when it is not worked out."""
    if not price:
        return {"words": "price not worked out yet"}
    if "error" in price:
        return {"words": "the price could not be worked out", "error": price["error"]}
    sums = price["totals"]
    unmeasured = len(sums.get("unmeasured", []))
    return {"likely": sums["likely_euros"], "high": sums["high_euros"], "nodes": sums["nodes"],
            "measured": unmeasured == 0,
            "words": "measured from earlier runs" if unmeasured == 0 else
                     f"{unmeasured} of {sums['nodes']} jobs never ran before: their price is the stage's estimate"}


def place_part(record, source):
    """One place of a fix: its pictures, its free and paid parts, its 3D link, its own question."""
    after, after_failed = pictures_of(record, "stills")
    return {"place": record["place"], "pairs": pairs(record, source), "failed": after_failed,
            "media": [item for item in record.get("media") or [] if "file" in item],
            "free": labels(record.get("made") or []), "paid": labels(record.get("needs_paid_batch") or []),
            "price": price_words(record.get("price")), "has_3d": record.get("has_3d"),
            "view": f"/view/{record['place']}?proposal={record['branch']}",
            "blocked": record.get("blocked"), "question": record.get("question"),
            "recommended": record.get("recommended"), "made_at": record.get("made_at"),
            "nodes": [item["node"] for item in record.get("layers") or [] if item["how"] == records.PAID]}


def paid_total(found):
    """The fix's likely and high euros, each paid node once over its places; None while any place is unpriced."""
    prices = {}
    for record in found:
        price = record.get("price") or {}
        if "nodes" not in price:
            return None
        prices.update({node: value for node, value in price["nodes"].items() if "error" not in value})
    return {"likely": round(sum(value["likely_euros"] for value in prices.values()), 2),
            "high": round(sum(value["high_euros"] for value in prices.values()), 2), "jobs": len(prices)}


def answer_words(choice):
    """What became of his answer: the store's machine's words, hosted read from the request it was queued as."""
    if choice.applied or not actions.hosted():
        return choice.applied
    queued = SyncRequest.objects.filter(kind="proposal", payload__branch=choice.branch).first()
    if queued is None or queued.state in ("waiting", "picked_up"):
        return "waiting for the store's machine to take it (every few minutes)"
    return queued.detail


def fix_card(branch, found, source, choice):
    """One fix branch as the owner reads it: its sentence, its places, its total, his answer so far."""
    newest = max(found, key=lambda record: record.get("made_at") or "")
    places = [place_part(record, source) for record in sorted(found, key=lambda record: record["place"])]
    stale = choice is not None and choice.commit != newest["commit"]
    return {"branch": branch, "commit": newest["commit"], "sentence": plain_sentence(newest),
            "change": newest.get("change"), "places": places, "total": paid_total(found),
            "free_only": all(not place["paid"] for place in places),
            "questions": [place for place in places if place["question"]],
            "choice": None if choice is None or stale else {"said": CHOICES.get(choice.choice, choice.choice),
                                                             "choice": choice.choice, "applied": answer_words(choice)},
            "stale": stale}


def fix_cards(root, source):
    """Every fix with a proposal, newest first."""
    by_branch = {}
    for summary in records.listing(root):
        record = records.read(root, summary["branch"], summary["place"])
        if record:
            by_branch.setdefault(record["branch"], []).append(record)
    choices = {choice.branch: choice for choice in ProposalChoice.objects.all()}
    cards = [fix_card(branch, found, source, choices.get(branch)) for branch, found in by_branch.items()]
    return sorted(cards, key=lambda card: max(place["made_at"] or "" for place in card["places"]), reverse=True)


def bought_total(cards):
    """The sum of the fixes he chose to buy: {likely, high, count}, high None while one is unpriced."""
    bought = [card for card in cards if card["choice"] and card["choice"]["choice"] == "buy"]
    priced = all(card["total"] for card in bought)
    return {"count": len(bought),
            "likely": round(sum(card["total"]["likely"] for card in bought), 2) if priced else None,
            "high": round(sum(card["total"]["high"] for card in bought), 2) if priced else None}


def changes_page(request):
    cards = fix_cards(proposals_root(), state.source())
    return render(request, "pages/changes.html", {
        "cards": cards, "bought": bought_total(cards),
        "waiting": [card for card in cards if card["choice"] is None]})


def chosen(user, branch, commit, choice):
    """Keep the owner's answer and, local, carry it out; what was done, in words."""
    ProposalChoice.objects.update_or_create(branch=branch, defaults={
        "commit": commit, "choice": choice, "by": user, "applied": ""})
    if actions.hosted():
        SyncRequest.objects.create(kind="proposal", user=user, payload={
            "branch": branch, "commit": commit, "choice": choice})
        return f"{CHOICES[choice]}: the store's machine takes it on its next sync"
    return carried_out(branch, commit, choice)


def carried_out(branch, commit, choice):
    """On the store's machine: a buy puts the branch in the checkout's basket at the commit he saw, a not now takes
    it out; refused when the branch moved since. The words are kept on his answer."""
    from score.dashboard.checkout import flow
    from score.dashboard.pages.models import BasketBranch
    now = flow.offer(branch)
    if choice == "buy" and now["head"] != commit:
        said = f"refused: {branch} has a newer commit than the pictures you saw; its proposal is made again first"
    elif choice == "buy":
        BasketBranch.objects.update_or_create(branch=branch, defaults={
            "head": commit, "preview_hash": now["preview_hash"], "added_by": settings.SCORE_OWNER})
        said = f"{branch} is in the checkout's basket"
    else:
        BasketBranch.objects.filter(branch=branch).delete()
        said = f"{branch} is not in the basket"
    ProposalChoice.objects.filter(branch=branch).update(applied=said)
    return said


@require_POST
def proposal_choice(request):
    """The owner's buy or not now of one fix (owner only, CSRF by Django)."""
    if not is_owner(request.user):
        return HttpResponseForbidden("only the owner buys")
    branch, commit, choice = (request.POST.get(name, "") for name in ("branch", "commit", "choice"))
    if choice not in CHOICES or not records.NAME.match(branch) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        messages.error(request, "refused: that is not a fix on this page")
        return redirect("/changes/")
    said = chosen(request.user.username, branch, commit, choice)
    (messages.error if said.startswith("refused") else messages.success)(request, said)
    return redirect(f"/changes/#fix-{branch}")
