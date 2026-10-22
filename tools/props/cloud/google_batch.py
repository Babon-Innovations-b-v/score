"""Gemini asks sent through Google's Batch API at half price, on google_spend's ledger and cache.

    answers = google_batch.generate(model, {key: body}, api_key, caller="finish-route-list")
    # {key: the response, or an Unanswered saying why there is none}

Google's batch page (ai.google.dev/gemini-api/docs/batch-mode, read 2026-10-20): POST
`models/<model>:batchGenerateContent` with the requests inline (`batch.input_config.requests.requests`, each a
`request` and `metadata.key`, under 20 MB in all) makes a job `batches/<id>`; GET `<name>` until `done`, its state
`*_SUCCEEDED`, `*_FAILED`, `*_CANCELLED` or `*_EXPIRED` (pending or running over 48 hours), the answers in
`response.inlinedResponses`, each a `response` or an `error`.

A batch is one shot (CONTEXT.md "batch", #21). A request asked before is read back from google_spend's cache, free.
The rest go into one job (more only past INLINE_MOST bytes), each with a started line on the Google ledger before the
job is sent. The job's name is kept beside the cache (`pending_path`) before it is waited on, so a run cut off
mid-wait picks up the same job and never sends it again. Each answer is priced at the batch tier
(google_spend.TIER_PRICE), its finished line written and it kept in the cache. A request the job answers with an
error, or every request of a job that fails, is cancelled or expires, gets a failed line and is Unanswered for its
caller: never asked again here; new spend on it is a new batch.

At the send, a refusal that did no work (HTTP 429, 500, 503, 504) is sent again after a wait that doubles, at most
REFUSED_SENDS times; any
other HTTP status is a set-up fault and reaches the caller as it is, its requests failed on the ledger. A send cut
off (a timeout, a lost connection) leaves every request in it Unanswered: the job may have been made, so it is not
sent again. A poll that fails costs nothing and is tried again, up to POLL_FAULTS_MOST in a row; past them the error
reaches the caller, and the next run waits on the same job. A poll answered 404 means the job is gone: it is not
polled again, its requests are failed lines and Unanswered as a failed job's are, and its kept name is dropped (audit,
2026-10-22: a dead job was polled POLL_FAULTS_MOST times a run, every run).
"""
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import google_spend  # noqa: E402

API = "https://generativelanguage.googleapis.com/v1beta"
INLINE_MOST = 19_000_000  # bytes of requests a job: Google's inline limit is 20 MB
REFUSED, REFUSED_SENDS, REFUSED_WAIT = (429, 500, 503, 504), 3, 30
GONE = "GONE (the job answered HTTP 404)"
SEND_TIMEOUT, POLL_TIMEOUT = 300, 60
POLL_SECONDS = 60
POLL_FAULTS_MOST = 30
DONE_WELL = "SUCCEEDED"
TIER = "batch"


class Unanswered(Exception):
    """A request the batch gave no answer to: the job failed, was cancelled or expired, the send was cut off, or the
    job answered it with an error."""


def send(model, request, api_key):
    """The raw batchGenerateContent POST; the job (an operation) it made."""
    sent = urllib.request.Request(f"{API}/models/{model}:batchGenerateContent", data=json.dumps(request).encode(),
                                  method="POST", headers={"x-goog-api-key": api_key, "Content-Type": "application/json"})
    with urllib.request.urlopen(sent, timeout=SEND_TIMEOUT) as response:
        return json.loads(response.read())


def status(name, api_key):
    """The raw GET of a job by its name; the operation."""
    asked = urllib.request.Request(f"{API}/{name}", headers={"x-goog-api-key": api_key})
    with urllib.request.urlopen(asked, timeout=POLL_TIMEOUT) as response:
        return json.loads(response.read())


def chunks(bodies):
    """The requests ({key: body}) in jobs of at most INLINE_MOST bytes each, in key order."""
    found, size = [{}], 0
    for key in sorted(bodies):
        weight = len(json.dumps(bodies[key]))
        if found[-1] and size + weight > INLINE_MOST:
            found.append({})
            size = 0
        found[-1][key] = bodies[key]
        size += weight
    return [chunk for chunk in found if chunk]


def job_request(chunk, caller):
    """The batchGenerateContent body of one job's requests."""
    return {"batch": {"display_name": caller, "input_config": {"requests": {"requests": [
        {"request": body, "metadata": {"key": key}} for key, body in chunk.items()]}}}}


def pending_path(model, chunk):
    """Where a sent job's name and its requests' ledger calls are kept until it is settled."""
    digest = hashlib.sha256(json.dumps([model, chunk], sort_keys=True).encode()).hexdigest()
    return google_spend.CACHE / f"batch-{digest}.json"


def failed(model, caller, calls, why):
    """A failed line for each request's call; {key: Unanswered(why)}."""
    for call in calls.values():
        google_spend.write({"call": call, "state": "failed", "model": model, "caller": caller, "error": why[:300]})
    return {key: Unanswered(why) for key in calls}


def sent_job(model, request, api_key):
    """The job made by sending `request`: a refusal that did no work is sent again after a wait, at most
    REFUSED_SENDS times in all; any other error reaches the caller."""
    for attempt in range(REFUSED_SENDS):
        try:
            return send(model, request, api_key)
        except urllib.error.HTTPError as error:
            if error.code not in REFUSED or attempt == REFUSED_SENDS - 1:
                raise
            time.sleep(REFUSED_WAIT * 2 ** attempt)


def started_job(model, chunk, api_key, caller):
    """One job sent for `chunk`, its started lines written first and its name kept (pending_path): {name, calls},
    or the requests' Unanswered when the send was cut off. A job sent before is picked up, never sent again."""
    kept = pending_path(model, chunk)
    if kept.exists():
        return json.loads(kept.read_text())
    calls = {key: google_spend.started(model, caller) for key in chunk}
    try:
        job = sent_job(model, job_request(chunk, caller), api_key)
    except urllib.error.HTTPError as error:
        failed(model, caller, calls, f"set-up fault at the send: HTTP {error.code}")
        raise
    except (TimeoutError, urllib.error.URLError, ConnectionError) as error:
        return failed(model, caller, calls, f"the send was cut off, not sent again: {error!r}")
    found = {"name": job["name"], "calls": calls}
    google_spend.keep(kept, found)
    return found


def waited(name, api_key):
    """The job's operation once it is done, polled every POLL_SECONDS; a failing poll is tried again, up to
    POLL_FAULTS_MOST in a row. A job gone (404) is done, in state GONE."""
    faults = 0
    while True:
        try:
            operation = status(name, api_key)
            faults = 0
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return {"name": name, "done": True, "state": GONE}
            faults += 1
            if faults >= POLL_FAULTS_MOST:
                raise
            operation = {}
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            faults += 1
            if faults >= POLL_FAULTS_MOST:
                raise
            operation = {}
        if operation.get("done"):
            return operation
        time.sleep(POLL_SECONDS)


def job_state(operation):
    """The job's state word (the page shows it at `metadata.state` and at `state`)."""
    return str(operation.get("metadata", {}).get("state") or operation.get("state") or "")


def inlined(operation):
    """The job's answers: [{metadata: {key}, response or error}]."""
    output = operation.get("response") or operation.get("dest") or {}
    found = output.get("inlinedResponses", [])
    return found.get("inlinedResponses", []) if isinstance(found, dict) else found


def settled(model, caller, job, operation, chunk):
    """{key: response or Unanswered} of a done job: each answer priced at the batch tier, written and cached."""
    if not job_state(operation).endswith(DONE_WELL):
        return failed(model, caller, job["calls"], f"the batch ended {job_state(operation) or 'with no state'}")
    found = {}
    for entry in inlined(operation):
        key = entry.get("metadata", {}).get("key")
        if key not in job["calls"] or key in found:
            continue
        if "response" not in entry:
            found.update(failed(model, caller, {key: job["calls"][key]},
                                f"the batch answered with an error: {json.dumps(entry.get('error'))}"))
            continue
        # A batch answer's usageMetadata names serviceTier "standard" (finish-route-list, 2026-10-22: priced EUR 0.18,
        # twice its batch price), and google_spend reads that before the top level: the batch tier goes in both.
        usage = {**entry["response"].get("usageMetadata", {}), "serviceTier": TIER}
        response = {**entry["response"], "serviceTier": TIER, "usageMetadata": usage}
        google_spend.record(model, caller, response, job["calls"][key])
        google_spend.keep(google_spend.cache_path(model, chunk[key]), entry["response"])
        found[key] = entry["response"]
    missing = {key: call for key, call in job["calls"].items() if key not in found}
    return {**found, **failed(model, caller, missing, "the batch gave no answer for it")}


def asked_job(model, chunk, api_key, caller):
    """One job's answers ({key: response or Unanswered}): sent (or picked up), waited on and settled."""
    job = started_job(model, chunk, api_key, caller)
    if "name" not in job:
        return job
    found = settled(model, caller, job, waited(job["name"], api_key), chunk)
    pending_path(model, chunk).unlink(missing_ok=True)
    return found


def generate(model, bodies, api_key, caller):
    """Every request of `bodies` ({key: generateContent body}) answered once: from the cache, else through one batch
    (module docstring); {key: response or Unanswered}."""
    found, asked = {}, {}
    for key, body in bodies.items():
        kept = google_spend.cache_path(model, body)
        if kept.exists():
            found[key] = json.loads(kept.read_text())
        else:
            asked[key] = body
    for chunk in chunks(asked):
        found.update(asked_job(model, chunk, api_key, caller))
    return found
