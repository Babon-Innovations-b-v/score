"""The store's machine's listener (`python -m score.dashboard listen`): the owner's quick requests answered within a
second of his click, not at the next sync pass. It holds one call open to the hosted side (GET /api/sync/requests
with `wait`, signed in by the sync token, the store's machine calling out as ever), and claims, applies and answers
each request of LISTENED the moment one is there (client.answered: the pictures a draw brought back first, then its
report): the concept, environment and plan reviews' clicks, the Machine card's Stop everything and Allow paid work
again, and his hosted Buy (a `checkout`, owner 2026-10-24: "can we make that delay less for the following runs"),
through the same checkout as the pass with the same refusals; a Buy whose price needs a fresh pass
(client.buy_waits) is said so on the request at once and left waiting for the pass, never claimed here. On a machine
that is not the store's (sync/one_store.py) every claim is refused, said once in its log. The sync pass answers the
same kinds when the listener is not running; a claim keeps each request to one.

While a batch lives it also sends the run monitor's record (batch-run.json) to the hosted side every PUSH_SECONDS,
apart from the pass's export, and once more when it ends, so the hosted monitor is at most about a minute old.

It runs as the owner's own long-lived systemd user service (deploy/score-listen.service.example, installed beside the
timer by `install-sync`), its token read by name from his secret manager like the timer's, so every request is
applied in his process and never an agent's (the store and score.review.web refuse there). A batch it launches runs
detached in a session of its own (`score run --detach`; on a conductor its own scope too) and the unit stops only its
own process (KillMode=process), so the hourly restart never ends a run.
"""
import threading
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor

from score.dashboard.state import batch_run
from score.dashboard.sync import applying, client

LISTENED = (*applying.CONCEPT_KINDS, *applying.ENVIRONMENT_KINDS, *applying.PLAN_KINDS, *applying.MACHINE_KINDS,
            "checkout")
WAIT_SECONDS = 25  # how long one call is held open; under the hosted side's LONGEST_WAIT and client.TIMEOUT
RETRY_SECONDS = 5.0  # after the hosted side could not be reached
SHORTEST_ROUND = 2.0  # an empty answer sooner than this waits this long before the next call
PUSH_SECONDS = 60.0  # the run monitor's record sent this often while a batch lives


def round_once(remote, source, left=None):
    """One held call: every waiting request of LISTENED answered, side by side (a Draw all's draws are one direct
    call each, made at once); [(id, state)]. `left` the ids of Buys left for the pass, not asked for again."""
    left = set() if left is None else left
    items = [item for item in remote.waiting(LISTENED, WAIT_SECONDS, sorted(left)) if item["id"] not in left]
    with ThreadPoolExecutor(max_workers=max(1, len(items))) as pool:
        answers = list(pool.map(lambda item: (item, client.answered(remote, item, source)), items))
    left.update(item["id"] for item, applied in answers if applied is None and item["kind"] == "checkout")
    return [(item["id"], applied.state) for item, applied in answers if applied is not None]


def batch_pushed(remote, source, was_live):
    """Send the newest Buy's batch (state/batch_run.py) while it lives, and once more as it ends; whether it lives."""
    run = source.batch_run(client.made_now())
    live = bool(run) and run["state"] in batch_run.LIVE
    if live or (was_live and run):
        remote.put_batch_run(run)
    return live


def following(remote, source, log=print, pause=time.sleep):
    """batch_pushed every PUSH_SECONDS until the process ends; a failure said in one line and tried again."""
    live = False
    while True:
        try:
            live = batch_pushed(remote, source, live)
        except Exception as error:  # said in the log; the next minute tries again
            log(f"the batch record was not sent: {type(error).__name__}: {error}")
        pause(PUSH_SECONDS)


def listen(remote, source, rounds=None, log=print, pause=time.sleep):
    """Answer the owner's quick requests until stopped (`rounds` held calls when given, and then no batch record
    sent); an unreachable hosted side is said in one line and asked again after RETRY_SECONDS."""
    if rounds is None:
        threading.Thread(target=following, args=(remote, source, log), daemon=True).start()
    count, said, left = 0, None, set()
    while rounds is None or count < rounds:
        count += 1
        started = time.monotonic()
        try:
            answered = round_once(remote, source, left)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as unreachable:
            log(f"the hosted side did not answer ({unreachable}); asking again in {RETRY_SECONDS:.0f} s")
            pause(RETRY_SECONDS)
            continue
        for request_id, state in answered:
            log(f"request {request_id}: {state}")
        if remote.not_the_store and remote.not_the_store != said:
            said = remote.not_the_store
            log(f"no request applied here: {said}")
        if not answered and time.monotonic() - started < SHORTEST_ROUND:
            pause(SHORTEST_ROUND)  # a hosted side that does not hold the call open is not asked in a tight loop
