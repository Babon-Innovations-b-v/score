"""The store's machine's listener (`python -m score.dashboard listen`): the owner's quick requests answered within a
second of his click, not at the next sync pass. It holds one call open to the hosted side (GET /api/sync/requests
with `wait`, signed in by the sync token, the store's machine calling out as ever), and claims, applies and answers
each request of LISTENED the moment one is there (client.answered: the pictures a draw brought back first, then its
report). The sync pass answers the same kinds when the listener is not running; a claim keeps each request to one.

It runs as the owner's own long-lived systemd user service (deploy/score-listen.service.example, installed beside the
timer by `install-sync`), its token read by name from his secret manager like the timer's, so every request is
applied in his process and never an agent's (the store and score.review.web refuse there).
"""
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor

from score.dashboard.sync import applying, client

LISTENED = (*applying.CONCEPT_KINDS, *applying.ENVIRONMENT_KINDS, *applying.PLAN_KINDS)
WAIT_SECONDS = 25  # how long one call is held open; under the hosted side's LONGEST_WAIT and client.TIMEOUT
RETRY_SECONDS = 5.0  # after the hosted side could not be reached
SHORTEST_ROUND = 2.0  # an empty answer sooner than this waits this long before the next call


def round_once(remote, source):
    """One held call: every waiting request of LISTENED answered, side by side (a Draw all's draws are one direct
    call each, made at once); [(id, state)]."""
    items = remote.waiting(LISTENED, WAIT_SECONDS)
    with ThreadPoolExecutor(max_workers=max(1, len(items))) as pool:
        answers = list(pool.map(lambda item: (item["id"], client.answered(remote, item, source)), items))
    return [(request_id, applied.state) for request_id, applied in answers if applied is not None]


def listen(remote, source, rounds=None, log=print, pause=time.sleep):
    """Answer the owner's quick requests until stopped (`rounds` held calls when given); an unreachable hosted side
    is said in one line and asked again after RETRY_SECONDS."""
    count = 0
    while rounds is None or count < rounds:
        count += 1
        started = time.monotonic()
        try:
            answered = round_once(remote, source)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as unreachable:
            log(f"the hosted side did not answer ({unreachable}); asking again in {RETRY_SECONDS:.0f} s")
            pause(RETRY_SECONDS)
            continue
        for request_id, state in answered:
            log(f"request {request_id}: {state}")
        if not answered and time.monotonic() - started < SHORTEST_ROUND:
            pause(SHORTEST_ROUND)  # a hosted side that does not hold the call open is not asked in a tight loop
