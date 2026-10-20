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

from score.dashboard.sync import applying, client

LISTENED = applying.CONCEPT_KINDS
WAIT_SECONDS = 25  # how long one call is held open; under the hosted side's LONGEST_WAIT and client.TIMEOUT
RETRY_SECONDS = 5.0  # after the hosted side could not be reached


def round_once(remote, source):
    """One held call: every waiting request of LISTENED answered; [(id, state)]."""
    done = []
    for item in remote.waiting(LISTENED, WAIT_SECONDS):
        applied = client.answered(remote, item, source)
        if applied is not None:
            done.append((item["id"], applied.state))
    return done


def listen(remote, source, rounds=None, log=print, pause=time.sleep):
    """Answer the owner's quick requests until stopped (`rounds` held calls when given); an unreachable hosted side
    is said in one line and asked again after RETRY_SECONDS."""
    count = 0
    while rounds is None or count < rounds:
        count += 1
        try:
            for request_id, state in round_once(remote, source):
                log(f"request {request_id}: {state}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as unreachable:
            log(f"the hosted side did not answer ({unreachable}); asking again in {RETRY_SECONDS:.0f} s")
            pause(RETRY_SECONDS)
