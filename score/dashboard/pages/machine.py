"""The store's machine on the cockpit: the Machine card on Home (`pages/machine_card.html`) and `/machine/` with its
logs' tails (`pages/machine.html`), both from machine.json (state/machine.py: read live locally, from the export
hosted). The card shows its name, size and state, the last backup's age (red over two hours), the last export's age
(red over 15 minutes: the store's machine is not reaching the cockpit), its own month's bill (the conductor's own
project, never a batch's spend) and, for the owner, Stop everything and Allow paid work again (each asked twice),
and, hosted, a second machine's exports with 'This is the store's machine now' (sync/one_store.py)."""
import json
import re

from django.conf import settings
from django.shortcuts import render

from score.dashboard import state
from score.dashboard.pages import actions
from score.dashboard.pages.models import SyncRequest, is_owner
from score.dashboard.state import machine

KINDS = {"stop-everything": "stop everything", "allow-paid": "paid allowed"}  # each click and its label
REPORT = re.compile(r"^(stopped everything|paid work allowed again): (\{.*\})$", re.S)


def report_counts(said):
    """[(name, count)] of a Stop everything's or Allow paid's report (its JSON after the words): a list counted, a
    number as is; [] for words without one."""
    found = REPORT.match(said or "")
    if not found:
        return []
    try:
        report = json.loads(found.group(2))
    except ValueError:
        return []
    return [(name.replace("_", " "), len(value) if isinstance(value, list) else value)
            for name, value in sorted(report.items()) if isinstance(value, (list, int, float))]


def last_click():
    """The newest Stop everything or Allow paid work again: {kind, state, at, by, said, counts}, or None. Hosted, its
    request with the listener's answer; local, the last stop kept here."""
    if actions.hosted():
        item = SyncRequest.objects.filter(kind__in=list(KINDS)).order_by("-created").first()
        if item is None:
            return None
        found = {"kind": item.kind, "state": item.state, "at": item.created.isoformat(timespec="seconds"),
                 "by": item.user, "said": item.detail}
    else:
        path = settings.SCORE_HOME / actions.LAST_STOP
        if not path.is_file():
            return None
        found = {"kind": "stop-everything", "state": "done", **json.loads(path.read_text())}
    return {**found, "label": KINDS[found["kind"]], "counts": report_counts(found["said"])}


def shown(request, source, found):
    """The Machine card's context from `found` (machine.json's content, read from `source`): `card`
    (state/machine.card), `second` (hosted: the machine a newer export came from that is not the store's), `store`
    (the store's machine as the cockpit records it), `last` (last_click) and `owner`."""
    second, store = None, None
    if actions.hosted():
        from score.dashboard.sync import one_store
        second, store = one_store.second(), one_store.record().get("name")
    return {"card": machine.card(found, source.export_made_at()), "second": second, "store": store,
            "confirm_body": json.dumps({"sure": True, "machine": second}) if second else None,
            "last": last_click(), "owner": is_owner(request.user), "hosted": actions.hosted()}


def machine_page(request):
    """`/machine/`: the card, its health in numbers and the tails of its logs, each a fold."""
    source = state.source()
    found = source.machine() or {}
    tails = sorted((found.get("tails") or {}).items())
    return render(request, "pages/machine.html", {"machine": shown(request, source, found), "tails": [
        {"name": name, "lines": "\n".join(lines), "count": len(lines)} for name, lines in tails]})
