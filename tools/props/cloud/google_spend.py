"""Every call to Google's Gemini API goes through here: priced and written down, and asked once when cached.

    response = google_spend.generate(model, body, key, timeout, caller="gemini_judge", cache=True)

Each call writes a "started" line to google-ledger.jsonl (beside the cloud ledger) before it is sent, so a call
killed or lost mid-way still shows, then a "finished" line with its cost, counted from the response's usageMetadata
(input, output and thinking tokens, and image tokens) at Google's published prices (PRICES, times TIER_PRICE for its
service tier), or a "failed" line with the error. month_euros reads it back for the runner's month check: a started
call with no finished line counts at its model's estimate (Google may bill a call the caller timed out on; the Oct 11
day billed EUR 549 against EUR 30 on this ledger, which then wrote only after a call came back). No cap: the owner
wants none (2026-10-11).
With cache=True the same request (same pictures, text, allowed answers, model and settings) is asked once: its
response is kept in google-cache/ and read back by every later caller, any place line or rerun.
"""
import datetime
import hashlib
import json
import os
import pathlib
import sys
import threading
import uuid
import urllib.request
import zoneinfo

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from paths import HOME  # noqa: E402

CLOUD = HOME / "cloud"
LEDGER = CLOUD / "google-ledger.jsonl"
CACHE = CLOUD / "google-cache"
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DAY_ZONE = zoneinfo.ZoneInfo("Europe/Amsterdam")
# Dollars counted as euros one to one: a dollar is worth less than a euro, so the ledger's euros are overstated,
# never under.
EUROS_PER_DOLLAR = 1.0
# USD per 1M tokens, paid tier, ai.google.dev/gemini-api/docs/pricing (read 2026-10-11). Thinking is billed as
# output; "long" applies to prompts over 200k tokens. A model missing here is recorded with its tokens and no price.
PRICES = {
    "gemini-3.1-pro-preview": {"input": 2.0, "output": 12.0, "input_long": 4.0, "output_long": 18.0},
    "gemini-3-pro-image": {"input": 2.0, "output": 12.0, "image": 120.0},
}
LONG_PROMPT = 200_000
# The same page's other tiers, as a share of standard: priority is 1.8 times every price, batch and flex half.
TIER_PRICE = {"priority": 1.8, "batch": 0.5, "flex": 0.5}
# USD a call that never finished is counted at: a 2K picture is 1120 image tokens ($0.134) plus its prompt and
# thinking; a 3.1 Pro text ask measured EUR 0.01 to 0.03 on the ledger (2026-10-12). Another model: the larger.
ESTIMATES = {"gemini-3-pro-image": 0.15, "gemini-3.1-pro-preview": 0.05}


def today():
    """Today's date in Amsterdam, YYYY-MM-DD."""
    return datetime.datetime.now(DAY_ZONE).date().isoformat()


def dollars(model, usage):
    """What one response cost, from its usageMetadata, at PRICES; None for a model with no price."""
    if model not in PRICES:
        return None
    price = PRICES[model]
    prompt = usage.get("promptTokenCount", 0)
    images = sum(detail.get("tokenCount", 0) for detail in usage.get("candidatesTokensDetails", [])
                 if detail.get("modality") == "IMAGE")
    text_out = usage.get("candidatesTokenCount", 0) - images + usage.get("thoughtsTokenCount", 0)
    long = prompt > LONG_PROMPT and "input_long" in price
    return (prompt * price["input_long" if long else "input"] + text_out * price["output_long" if long else "output"]
            + images * price.get("image", 0)) / 1e6


def write(entry):
    """Append one line to the ledger, stamped with the time and day."""
    entry = {"time": datetime.datetime.now(DAY_ZONE).isoformat(timespec="seconds"), "day": today(), **entry}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as ledger:  # one short line, appended whole: no lock needed
        ledger.write(json.dumps(entry) + "\n")


def estimate(model):
    """The euros a call of this model that never finished is counted at."""
    return ESTIMATES.get(model, max(ESTIMATES.values())) * EUROS_PER_DOLLAR


def started(model, caller):
    """Write the line of a call about to be sent; its id."""
    call = uuid.uuid4().hex
    write({"call": call, "state": "started", "model": model, "caller": caller, "estimate": estimate(model)})
    return call


def record(model, caller, response, call=None):
    """Append one finished call's line to the ledger; its euros."""
    usage = response.get("usageMetadata", {})
    tier = usage.get("serviceTier") or response.get("serviceTier")
    cost = dollars(model, usage)
    cost = None if cost is None else cost * TIER_PRICE.get(str(tier).lower(), 1.0)
    entry = {"call": call, "state": "finished", "model": model, "caller": caller, "tier": tier,
             "input": usage.get("promptTokenCount", 0),
             "output": usage.get("candidatesTokenCount", 0), "thinking": usage.get("thoughtsTokenCount", 0),
             "dollars": None if cost is None else round(cost, 6),
             "euros": None if cost is None else round(cost * EUROS_PER_DOLLAR, 6)}
    write(entry)
    return entry["euros"]


def month_euros(month):
    """What Google calls cost in `month` (YYYY-MM, by the line's own time): finished calls at their price, a call
    started with no finished line (failed, killed, still going) and an unpriced one at its model's estimate."""
    if not LEDGER.exists():
        return 0.0
    lines = [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]
    lines = [line for line in lines if line["time"].startswith(month)]
    finished = {line.get("call") for line in lines if line.get("state", "finished") == "finished"}
    total = sum(estimate(line["model"]) if line["euros"] is None else line["euros"]
                for line in lines if line.get("state", "finished") == "finished")
    return total + sum(line["estimate"] for line in lines
                       if line.get("state") == "started" and line["call"] not in finished)


def cache_path(model, body):
    """Where the response to this exact request is kept."""
    digest = hashlib.sha256(json.dumps([model, body], sort_keys=True).encode()).hexdigest()
    return CACHE / f"{digest}.json"


def keep(path, response):
    """Write a response to the cache whole (a reader never sees half a file)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    part = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}")
    part.write_text(json.dumps(response))
    part.replace(path)


def post(model, body, key, timeout):
    """The raw generateContent call; its parsed response. HTTP and network errors reach the caller unchanged."""
    request = urllib.request.Request(URL.format(model=model), data=json.dumps(body).encode(), method="POST",
                                     headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def generate(model, body, key, timeout, caller, cache=False):
    """One generateContent call: with cache=True a response asked before is read back; otherwise made, recorded
    and, with cache=True, kept."""
    kept = cache_path(model, body)
    if cache and kept.exists():
        return json.loads(kept.read_text())
    call = started(model, caller)
    try:
        response = post(model, body, key, timeout)
    except BaseException as error:  # counted at its estimate either way (month_euros); the line says why
        write({"call": call, "state": "failed", "model": model, "caller": caller, "error": repr(error)[:300]})
        raise
    record(model, caller, response, call)
    if cache:
        keep(kept, response)
    return response
