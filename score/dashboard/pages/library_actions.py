"""The owner's library decisions: lock (approve an entry as final) or withdraw, for one entry or a selection.

Hosted, a decision is queued in the request outbox (a SyncRequest of kind "library") and applied on the library's
machine by the owner's own sync pass (sync/applying.py), only when its user is the local SCORE_OWNER. Local, it is
applied at once. Applying is refused in any process an agent started: an agent never locks. It runs the library's
own command (SCORE_LIB_COMMAND, `<command> lock <address>...` and `<command> withdraw <address>`) in SCORE_LIB_ROOT,
then commits and pushes there.
"""
import shlex
import subprocess

from django.conf import settings

from score.dashboard.pages import actions
from score.dashboard.pages.models import SyncRequest
from score.dashboard.state.library import ADDRESS, library

ACTIONS = {"lock": "draft", "withdraw": "locked"}  # what each does, and the state it takes an entry from
PAST = {"lock": "locked", "withdraw": "withdrawn"}
RUN_SECONDS = 600


def counted(count):
    return f"{count} entr{'y' if count == 1 else 'ies'}"


def refusal(action, addresses, shown):
    """Why a decision on these entries cannot be asked, in words, or None."""
    if action not in ACTIONS:
        return f"refused: {action!r} is neither lock nor withdraw"
    if not addresses:
        return "nothing chosen"
    for address in addresses:
        entry = shown.entry(address) if ADDRESS.match(address) else None
        if entry is None:
            return f"refused: {address} is not in the library"
        if entry.state != ACTIONS[action]:
            return f"refused: {entry.title} is {entry.state}; only a {ACTIONS[action]} entry can be {PAST[action]}"
    return None


def waiting():
    """{address: action} of the library decisions queued and not yet applied."""
    found = {}
    for item in SyncRequest.objects.filter(kind="library", state__in=("waiting", "picked_up")).order_by("created"):
        for address in item.payload.get("addresses", []):
            found[address] = item.payload.get("action")
    return found


def ask(user, action, addresses, hosted):
    """The owner's lock or withdraw of these entries; what was done, in words."""
    shown = library()
    if shown is None:
        return "refused: no library here (SCORE_LIB_ROOT is not set)"
    addresses = sorted(set(addresses))
    why = refusal(action, addresses, shown)
    if why:
        return why
    if hosted:
        SyncRequest.objects.create(kind="library", user=user, payload={"action": action, "addresses": addresses})
        return f"queued: the library's machine will {action} {counted(len(addresses))} on its next sync"
    return carried_out(action, addresses, user)


# --- on the library's machine ----------------------------------------------------------------------------------

def run(arguments):
    """Run one command in the library folder; (ok, its last words)."""
    done = subprocess.run(arguments, cwd=settings.SCORE_LIB_ROOT, capture_output=True, text=True,
                          timeout=RUN_SECONDS)
    words = (done.stdout + done.stderr).strip().splitlines()
    return done.returncode == 0, (words[-1] if words else "")


def library_command():
    return shlex.split(settings.SCORE_LIB_COMMAND)


def changed(action, addresses):
    """Run the library's own command for the decision; (ok, words)."""
    command = library_command()
    if action == "lock":
        return run([*command, "lock", *addresses])
    for address in addresses:
        ok, words = run([*command, "withdraw", address])
        if not ok:
            return False, f"{address}: {words}"
    return True, f"withdrawn {len(addresses)}"


def reindexed():
    """Rebuild the library's index after a lock refused midway, so what was locked is listed; (ok, words)."""
    return run([*library_command(), "index"])


def committed(action, addresses, user):
    """Commit the library's records and index when they changed; (ok, words)."""
    ok, status = run(["git", "status", "--porcelain", "--", "entries", "index"])
    if not ok or not status:
        return ok, "nothing to commit" if ok else status
    ok, words = run(["git", "add", "--", "entries", "index"])
    if not ok:
        return ok, words
    title = f"{action}: {counted(len(addresses))}, the owner's decision on the cockpit ({user})"
    return run(["git", "commit", "-q", "-m", title, "-m", "\n".join(addresses)])


def pushed():
    return run(["git", "push", "-q"])


def carried_out(action, addresses, user):
    """Apply a decision in the library folder, commit it and push it; what happened, in words."""
    if not settings.SCORE_LIB_ROOT:
        return "refused: no library here (SCORE_LIB_ROOT is not set)"
    if actions.agent_started():
        return "refused: this process was started from an agent's shell, and an agent never locks"
    why = refusal(action, addresses, library())  # again here: a synced request's addresses come from the hosted side
    if why:
        return why
    ok, words = changed(action, addresses)
    if not ok and action == "lock":
        reindexed()
    saved, saved_words = committed(action, addresses, user)
    if not saved:
        return f"refused: {words}; the commit failed: {saved_words}"
    sent, sent_words = pushed() if saved_words != "nothing to commit" else (True, "")
    said = f"{PAST[action]} {counted(len(addresses))}" if ok else f"refused: {words}"
    return said + ("" if sent else f"; committed, but the push failed: {sent_words}")
