"""One store's machine (hosted side): the cockpit applies the owner's requests for one machine only, so during the
move off the PC the PC and the conductor can never both act as the store.

    SCORE_HOME/store-machine.json  {name, since, by, before, newest: {name, at}, others: {name: made_at}}

`name` is the store's machine: the first export that names one records it (by "its first export"); after that only
the owner's click 'This is the store's machine now' (owner only, CSRF, asked twice: api/routes.py) moves it, and only
to a machine an export came from (`others`). An export from another machine is still swapped in and shown, and the
card names the last such machine for a day (`second`), but its claims are refused (sync/endpoints.py: 423), so it
applies nothing. The store's machine names itself on every
sync call (client.MACHINE_HEADER). Nothing an agent or a sync token can send moves the record."""
import datetime
import json
import os

from django.conf import settings

RECORD = "store-machine.json"
SECOND_HOURS = 24  # another machine's export older than this no longer shows on the card


def path():
    return settings.SCORE_HOME / RECORD


def record():
    """The record ({} before any export named a machine)."""
    found = path()
    return json.loads(found.read_text()) if found.is_file() else {}


def kept(found):
    """Write the record whole (a .partial file renamed into place)."""
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f"{target.name}.partial")
    partial.write_text(json.dumps(found, indent=1, sort_keys=True))
    os.replace(partial, target)
    return found


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def exported_by(name, made_at):
    """An export from machine `name` was swapped in: kept as the newest, and in `others` {name: made_at} when it is
    not the store's machine; the store's machine when none is yet."""
    if not name:
        return record()
    found = {**record(), "newest": {"name": name, "at": made_at}}
    if not found.get("name"):
        found.update(name=name, since=now(), by="its first export")
    if name != found["name"]:
        found["others"] = {**found.get("others", {}), name: made_at}
    return kept(found)


def claim_refusal(caller):
    """Why a request may not be claimed by the machine `caller` (its sync calls' name), or None."""
    store = record().get("name")
    if store and caller != store:
        return (f"{caller or 'a machine that gave no name'} is not the store's machine ({store}): it applies no "
                f"request until the owner confirms the move on the cockpit")
    return None


def moment(made):
    """An export's made_at as an aware time (a time without a zone read as UTC), or None when it is no time."""
    try:
        found = datetime.datetime.fromisoformat(str(made).replace("Z", "+00:00"))
    except ValueError:
        return None
    return found if found.tzinfo else found.replace(tzinfo=datetime.timezone.utc)


def second(at=None):
    """The other machine (not the store's) whose export came last, within SECOND_HOURS of `at` (now), else None."""
    since = ((at or datetime.datetime.now(datetime.timezone.utc)) - datetime.timedelta(hours=SECOND_HOURS))
    others = {name: moment(made) for name, made in (record().get("others") or {}).items() if made}
    others = {name: made for name, made in others.items() if made and made >= since}
    return max(others, key=others.get) if others else None


def confirmed(name, by):
    """The owner's 'This is the store's machine now' for machine `name`, one an export came from; his words, or why
    not (starting refused). The machine it replaces is kept as `before` and its exports count as another's."""
    found = record()
    if name == found.get("name"):
        return f"{name} is already the store's machine"
    others = dict(found.get("others") or {})
    if not name or name not in others:
        return f"refused: no export came from {name or 'no machine'}"
    was = found.get("name")
    others.pop(name)
    kept({**found, "name": name, "since": now(), "by": by, "before": was, "others": others})
    return f"{name} is the store's machine now (was {was}): only its requests are applied"
