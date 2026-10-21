"""The store's machine applies a hosted request locally: a change request into the inbox, the owner's decision
through score.review.web.decide and the owner's advance into this machine's marks (each only when its user is the
local SCORE_OWNER), a launch basket planned and checked with the same guard as a local launch (the owner's advance
marks of this machine included) plus SCORE_SYNC_MAX_EUROS, then launched through the configured backend, and the
owner's buy or not now of a fix on Changes to buy into the checkout's basket here (pages/changes.py), and the
owner's money figures and waivers (OWNER_FIGURES), and his concept review's draws, picks and back to the generated wording (CONCEPT_KINDS), his
environment concept's interview answers, versions and reference pictures (ENVIRONMENT_KINDS) and his plan review's clicks (PLAN_KINDS),
each through the local cockpit's own owner-only function."""
import dataclasses
import json

from django.conf import settings
from django.utils import timezone

from score.dashboard.launch import guard
from score.dashboard.pages import actions, library_actions, seen
from score.dashboard.pages.models import Launch, Plan
from score.dashboard.state.files import HERO_SIDE, THUMB_SIDE, thumbnail

CONCEPT_KINDS = ("concept-draw", "concept-pick", "concept-wording")
# the environment concept's (CONTEXT.md "environment concept"): an interview answer, a new version, a reference picture
ENVIRONMENT_KINDS = ("environment-ask", "environment-save", "environment-reference")
# The plan review's (score/review/plans.py): his plan kept, inside places named, a Correct with notes.
PLAN_KINDS = {"plan-edit": actions.plan_edit, "plan-named": actions.plan_named, "plan-revise": actions.plan_revise,
              "plan-write": actions.plan_write}
DRAWN = ("sha", "name", "at", "by", "euros", "base", "marks", "note")  # a draw's fields its answer carries


@dataclasses.dataclass
class Applied:
    state: str  # done, running, refused
    detail: str = ""
    log_tail: str = ""
    launch_id: int | None = None
    files: dict = dataclasses.field(default_factory=dict)  # {name: path} of pictures sent back with the answer


@dataclasses.dataclass(frozen=True)
class Queued:
    place: str
    stage: str


def apply_change(item):
    payload = item["payload"]
    change = actions.record_change(item["user"], payload.get("place") or None, payload["stage"],
                                   payload.get("output_seen", ""), payload["words"])
    return Applied("done", f"recorded locally as change request {change.pk}")


def from_owner(item):
    return bool(settings.SCORE_OWNER) and item["user"] == settings.SCORE_OWNER


def place_and_stage(node):
    stage, _, place = node.partition("@")
    return (place or None), stage


def apply_decision(item):
    payload = item["payload"]
    if not from_owner(item):
        return Applied("refused", f"{item['user']} is not this store's owner")
    place, stage = place_and_stage(payload["node"])
    said = actions.decide(item["user"], place, stage, payload["output"], payload["decision"],
                          payload.get("reason", ""), payload.get("worse_reason") or "")
    return Applied("done" if said.startswith(("accepted", "rejected")) else "refused", said)


def apply_advance(item):
    """The owner's advance, recorded in this machine's marks, which its launches are checked against."""
    payload = item["payload"]
    if not from_owner(item):
        return Applied("refused", f"{item['user']} is not this store's owner")
    place, stage = place_and_stage(payload["node"])
    said = actions.advance(item["user"], place, stage, payload.get("output", ""))
    return Applied("done" if said.startswith("advanced") else "refused", said)


def launch_refusals(item, plan, items, source):
    """The guard's refusals of a hosted launch, checked on the store's machine (nothing advances unseen: the paid
    steps whose reads the owner has not advanced here are refused), plus the sync cap."""
    payload = item["payload"]
    unseen = seen.unseen_reads(plan.body.get("buys", []), source.reads_of, source.accepted_output) \
        if plan.state == "ready" else []
    found = guard.refusals(plan, from_owner(item), guard.basket_hash(items), actions.running_launch(), True,
                           payload.get("rebuy_reason"), unseen)
    found = [why for why in found if not why.startswith("this dashboard is hosted")]
    cap = settings.SCORE_SYNC_MAX_EUROS
    if cap and plan.state == "ready" and plan.body["money"]["high"] > cap:
        found.append(f"over the hosted launch cap: high EUR {plan.body['money']['high']:.2f}, cap EUR {cap:.2f}")
    return found


def apply_launch(item, source, chosen=None):
    """Plan the queued basket here, check it, and launch it; Applied running with the launch's id, or refused."""
    payload = item["payload"]
    items = [Queued(entry.get("place") or "", entry["stage"]) for entry in payload.get("items", [])]
    if not items:
        return Applied("refused", "the basket was empty")
    plan = Plan.objects.create(basket_hash=guard.basket_hash(items), made_by=item["user"],
                               body={"jobs": int(payload.get("jobs") or guard.DEFAULT_JOBS)})
    guard.work_out(plan, items, chosen)
    plan.refresh_from_db()
    if plan.state != "ready":
        return Applied("refused", f"the plan could not be worked out: {plan.error}")
    refused = launch_refusals(item, plan, items, source)
    if refused:
        return Applied("refused", "; ".join(refused))
    record = Launch.objects.create(plan=plan, by=item["user"], jobs=plan.body["jobs"],
                                   rebuy_reason=(payload.get("rebuy_reason") or "").strip())
    guard.launch(record, plan, chosen)
    record.refresh_from_db()
    if record.state == "refused":
        return Applied("refused", record.result)
    return Applied("running", f"launched at {timezone.now().isoformat(timespec='seconds')}", launch_id=record.pk)


def apply_library(item):
    """The owner's lock or withdraw of library entries, carried out in the library folder here."""
    if not from_owner(item):
        return Applied("refused", f"{item['user']} is not this store's owner")
    payload = item["payload"]
    said = library_actions.carried_out(payload.get("action", ""), payload.get("addresses", []), item["user"])
    return Applied("refused" if said.startswith("refused") else "done", said)


def apply_checkout(item):
    """The owner's hosted checkout of the items he bought, run here in this pass (checkout/flow.py, every refusal of a
    local checkout, an item changed since he chose it among them)."""
    if not from_owner(item):
        return Applied("refused", f"{item['user']} is not this store's owner")
    from django.contrib.auth import get_user_model

    from score.dashboard.checkout import flow
    owner, _ = get_user_model().objects.get_or_create(username=item["user"])
    seen = [{"id": chosen["id"], "version": chosen["version"]} for chosen in item["payload"].get("items", [])]
    record, said = flow.start(owner, item["payload"]["key"], True, seen, at_once=True)
    return Applied("done" if record is not None and record.state in ("launched", "done") else "refused", said)


def apply_answer(item):
    """The owner's answer to a basket item's question, kept here where agents read it (the basket's answers.json)."""
    if not from_owner(item):
        return Applied("refused", f"{item['user']} is not this store's owner")
    from score.dashboard.pages import basket
    payload = item["payload"]
    said = basket.answered(item["user"], payload.get("item", ""), payload.get("number"), payload.get("question", ""),
                           payload.get("answer", ""))
    return Applied("refused" if said.startswith("refused") else "done", said)


# The owner's money figures and waiver: each applied here only when its user is this machine's owner, through the
# same owner-only function as on the local cockpit (pages/actions.py), whose words start "refused" when it was not.
OWNER_FIGURES = {
    "books-figure": lambda user, payload: actions.set_books_figure(user, payload.get("euros")),
    "read-back": lambda user, payload: actions.read_books_back(user),
    "waiver": lambda user, payload: actions.waive_check(user, *place_and_stage(payload.get("node", "")),
                                                        payload.get("output", ""), payload.get("check", ""),
                                                        payload.get("reason", "")),
}


def apply_owner_figure(item):
    """The owner's books figure, read-back or waiver, applied here by his signed-in name;
    refused for anyone else."""
    if not from_owner(item):
        return Applied("refused", f"{item['user']} is not this store's owner")
    said = OWNER_FIGURES[item["kind"]](item["user"], item["payload"])
    return Applied("refused" if said.startswith(("refused", "decisions are off")) else "done", said)


def apply_concept_draw(item, source):
    """The owner's concept draw (pages/actions.concept_draw); done: the detail the draw as JSON (DRAWN), its picture
    small and large in `files` for the hosted page until the next export holds it."""
    if not from_owner(item):
        return Applied("refused", f"{item['user']} is not this store's owner")
    said, record = actions.concept_draw(item["user"], item["payload"])
    if record is None:
        return Applied("refused", said)
    blob = source.blob_path(record["sha"])
    files = {f"{record['sha']}-{side}.jpg": thumbnail(blob, source.home / "thumbs" / f"{record['sha']}-{side}.jpg",
                                                      side) for side in (THUMB_SIDE, HERO_SIDE)}
    said = {name: record[name] for name in DRAWN}
    with_prompt = json.dumps({**said, "corrected": record.get("corrected")})
    # a Redraw with notes' corrected prompt goes along while the answer stays whole in its 4000 characters
    return Applied("done", with_prompt if len(with_prompt) <= 4000 else json.dumps(said), files=files)


def apply_concept_said(item, action):
    """The owner's Pick or unlock of a place's concept (pages/actions.concept_pick), or his back to the generated
    wording (concept_generated): `action`, answered in words."""
    if not from_owner(item):
        return Applied("refused", f"{item['user']} is not this store's owner")
    said = action(item["user"], item["payload"])
    return Applied("refused" if said.startswith("refused") else "done", said)


def apply_environment_ask(item):
    """His interview answer (pages/actions.environment_ask); done: the detail {topic, proposed, euros} as JSON."""
    if not from_owner(item):
        return Applied("refused", f"{item['user']} is not this store's owner")
    said, record = actions.environment_ask(item["user"], item["payload"])
    if record is None:
        return Applied("refused", said)
    return Applied("done", json.dumps({name: record[name] for name in ("topic", "proposed", "euros")}))


def apply_environment_reference(item, source):
    """His new reference picture (pages/actions.environment_reference); done: the detail {picture, sha} as JSON, its
    picture small and large in `files` for the hosted page until the next export holds it."""
    import hashlib
    from score.review import concepts
    if not from_owner(item):
        return Applied("refused", f"{item['user']} is not this store's owner")
    said, picture = actions.environment_reference(item["user"], item["payload"])
    if picture is None:
        return Applied("refused", said)
    path = concepts.resolved(picture)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    files = {f"{sha}-{side}.jpg": thumbnail(path, source.home / "thumbs" / f"{sha}-{side}.jpg", side)
             for side in (THUMB_SIDE, HERO_SIDE)}
    return Applied("done", json.dumps({"picture": picture, "sha": sha, "name": path.name}), files=files)


def apply(item, source, chosen=None):
    """Apply one hosted request; Applied."""
    kind = item["kind"]
    if kind == "change":
        return apply_change(item)
    if kind == "decision":
        return apply_decision(item)
    if kind == "advance":
        return apply_advance(item)
    if kind == "launch":
        return apply_launch(item, source, chosen)
    if kind == "library":
        return apply_library(item)
    if kind == "checkout":
        return apply_checkout(item)
    if kind == "answer":
        return apply_answer(item)
    if kind == "concept-draw":
        return apply_concept_draw(item, source)
    if kind == "concept-pick":
        return apply_concept_said(item, actions.concept_pick)
    if kind == "concept-wording":
        return apply_concept_said(item, actions.concept_generated)
    if kind == "environment-ask":
        return apply_environment_ask(item)
    if kind == "environment-save":
        return apply_concept_said(item, actions.environment_save)
    if kind == "environment-reference":
        return apply_environment_reference(item, source)
    if kind in PLAN_KINDS:
        return apply_concept_said(item, PLAN_KINDS[kind])
    if kind in OWNER_FIGURES:
        return apply_owner_figure(item)
    return Applied("refused", f"unknown request kind {kind!r}")
