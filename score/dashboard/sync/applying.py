"""The store's machine applies a hosted request locally: a change request into the inbox, the owner's decision
through score.review.web.decide (only when its user is the local SCORE_OWNER), a launch basket planned and checked
with the same guard as a local launch plus SCORE_SYNC_MAX_EUROS, then launched through the configured backend."""
import dataclasses

from django.conf import settings
from django.utils import timezone

from score.dashboard.launch import guard
from score.dashboard.pages import actions
from score.dashboard.pages.models import Launch, Plan


@dataclasses.dataclass
class Applied:
    state: str  # done, running, refused
    detail: str = ""
    log_tail: str = ""
    launch_id: int | None = None


@dataclasses.dataclass(frozen=True)
class Queued:
    place: str
    stage: str


def apply_change(item):
    payload = item["payload"]
    change = actions.record_change(item["user"], payload.get("place") or None, payload["stage"],
                                   payload.get("output_seen", ""), payload["words"])
    return Applied("done", f"recorded locally as change request {change.pk}")


def apply_decision(item):
    payload = item["payload"]
    if not settings.SCORE_OWNER or item["user"] != settings.SCORE_OWNER:
        return Applied("refused", f"{item['user']} is not this store's owner")
    place, stage = (payload["node"].split("@", 1)[1], payload["node"].split("@", 1)[0]) if "@" in payload["node"] \
        else (None, payload["node"])
    said = actions.decide(item["user"], place, stage, payload["output"], payload["decision"],
                          payload.get("reason", ""), payload.get("worse_reason") or "")
    return Applied("done" if said.startswith(("accepted", "rejected")) else "refused", said)


def launch_refusals(item, plan, items):
    """The guard's refusals of a hosted launch, checked on the store's machine, plus the sync cap."""
    payload = item["payload"]
    found = guard.refusals(plan, item["user"] == settings.SCORE_OWNER and bool(settings.SCORE_OWNER),
                           guard.basket_hash(items), actions.running_launch(), True, payload.get("rebuy_reason"))
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
    guard.work_out(plan, items, source.stage_records, chosen)
    plan.refresh_from_db()
    if plan.state != "ready":
        return Applied("refused", f"the plan could not be worked out: {plan.error}")
    refused = launch_refusals(item, plan, items)
    if refused:
        return Applied("refused", "; ".join(refused))
    record = Launch.objects.create(plan=plan, by=item["user"], jobs=plan.body["jobs"],
                                   rebuy_reason=(payload.get("rebuy_reason") or "").strip())
    guard.launch(record, plan, chosen)
    record.refresh_from_db()
    if record.state == "refused":
        return Applied("refused", record.result)
    return Applied("running", f"launched at {timezone.now().isoformat(timespec='seconds')}", launch_id=record.pk)


def apply(item, source, chosen=None):
    """Apply one hosted request; Applied."""
    kind = item["kind"]
    if kind == "change":
        return apply_change(item)
    if kind == "decision":
        return apply_decision(item)
    if kind == "launch":
        return apply_launch(item, source, chosen)
    return Applied("refused", f"unknown request kind {kind!r}")
