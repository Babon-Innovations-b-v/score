"""Every call to Google's Gemini API goes through here: priced, written down, and refused past the day's cap.

    response = google_spend.generate(model, body, key, timeout, caller="gemini_judge", cache=True)

Each call's cost is counted from the response's usageMetadata (input, output and thinking tokens, and image tokens)
at Google's published paid-tier prices (PRICES) and appended as one line to google-ledger.jsonl beside the cloud
ledger. A call is refused (SpendCapReached, never retried) when today's total, the Europe/Amsterdam day, plus the
call's estimate would pass the day's cap: SCORE_GOOGLE_DAY_EUROS, else the number in google-day-euros.txt beside the
ledger, else DAY_EUROS (the owner's EUR 100, 2026-10-11). With cache=True the same request (same pictures, text,
allowed answers, model and settings) is asked once: its response is kept in google-cache/ and read back after.
"""
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
import pathlib
import sys
import threading
import urllib.request
import zoneinfo

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from paths import HOME  # noqa: E402

CLOUD = HOME / "cloud"
LEDGER = CLOUD / "google-ledger.jsonl"
CAP_FILE = CLOUD / "google-day-euros.txt"
CACHE = CLOUD / "google-cache"
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DAY_EUROS = 100.0
DAY_ZONE = zoneinfo.ZoneInfo("Europe/Amsterdam")
# Dollars counted as euros one to one: a dollar is worth less than a euro, so the day's total is overstated, never
# under, and the cap bites early rather than late.
EUROS_PER_DOLLAR = 1.0
# USD per 1M tokens, paid tier, ai.google.dev/gemini-api/docs/pricing (read 2026-10-11). Thinking is billed as
# output; "long" applies to prompts over 200k tokens. "estimate" is the dollars a call is assumed to cost before it
# is made, for the cap check: above a typical call of each.
PRICES = {
    "gemini-3.1-pro-preview": {"input": 2.0, "output": 12.0, "input_long": 4.0, "output_long": 18.0,
                               "estimate": 0.10},
    "gemini-3-pro-image": {"input": 2.0, "output": 12.0, "image": 120.0, "estimate": 0.25},
}
LONG_PROMPT = 200_000


class SpendCapReached(RuntimeError):
    """A Google call refused: it would take today's Google spend past the day's cap."""


def day_cap():
    """The day's cap in euros: SCORE_GOOGLE_DAY_EUROS, else google-day-euros.txt, else DAY_EUROS."""
    if os.environ.get("SCORE_GOOGLE_DAY_EUROS"):
        return float(os.environ["SCORE_GOOGLE_DAY_EUROS"])
    return float(CAP_FILE.read_text().strip()) if CAP_FILE.exists() else DAY_EUROS


def today():
    """Today's date in Amsterdam, YYYY-MM-DD."""
    return datetime.datetime.now(DAY_ZONE).date().isoformat()


def dollars(model, usage):
    """What one response cost, from its usageMetadata, at PRICES."""
    price = PRICES[model]
    prompt = usage.get("promptTokenCount", 0)
    images = sum(detail.get("tokenCount", 0) for detail in usage.get("candidatesTokensDetails", [])
                 if detail.get("modality") == "IMAGE")
    text_out = usage.get("candidatesTokenCount", 0) - images + usage.get("thoughtsTokenCount", 0)
    long = prompt > LONG_PROMPT and "input_long" in price
    return (prompt * price["input_long" if long else "input"] + text_out * price["output_long" if long else "output"]
            + images * price.get("image", 0)) / 1e6


@contextlib.contextmanager
def ledger_lock():
    """One check-or-write at a time across every process."""
    CLOUD.mkdir(parents=True, exist_ok=True)
    with (CLOUD / "google-ledger.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def day_total(day):
    """Euros spent on `day` by the ledger's calls."""
    if not LEDGER.exists():
        return 0.0
    return sum(entry["euros"] for entry in map(json.loads, LEDGER.read_text().splitlines()) if entry["day"] == day)


def refuse_past_cap(model, caller):
    """Raise SpendCapReached when today's total plus this call's estimate would pass the cap."""
    if model not in PRICES:
        raise SpendCapReached(f"{caller}: no price for {model} in google_spend.PRICES, so it cannot be guarded")
    spent, cap = day_total(today()), day_cap()
    if spent + PRICES[model]["estimate"] * EUROS_PER_DOLLAR > cap:
        raise SpendCapReached(f"{caller}: Google spend today is EUR {spent:.2f} of the EUR {cap:.0f} day cap "
                              f"(SCORE_GOOGLE_DAY_EUROS or {CAP_FILE}); {model} refused until tomorrow")


def record(model, caller, response):
    """Append one call's line to the ledger; its euros."""
    usage = response.get("usageMetadata", {})
    cost = dollars(model, usage)
    entry = {"time": datetime.datetime.now(DAY_ZONE).isoformat(timespec="seconds"), "day": today(), "model": model,
             "caller": caller, "input": usage.get("promptTokenCount", 0),
             "output": usage.get("candidatesTokenCount", 0), "thinking": usage.get("thoughtsTokenCount", 0),
             "dollars": round(cost, 6), "euros": round(cost * EUROS_PER_DOLLAR, 6)}
    with ledger_lock(), LEDGER.open("a") as ledger:
        ledger.write(json.dumps(entry) + "\n")
    return entry["euros"]


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
    """One guarded generateContent call: with cache=True a response asked before is read back; otherwise refused
    past the day's cap (SpendCapReached), made, recorded and, with cache=True, kept."""
    kept = cache_path(model, body)
    if cache and kept.exists():
        return json.loads(kept.read_text())
    # shortcut: no reservation for calls in flight, so parallel callers can pass the cap by their in-flight calls
    # (about EUR 0.10 each); add reservations if the overshoot ever matters.
    with ledger_lock():
        refuse_past_cap(model, caller)
    response = post(model, body, key, timeout)
    record(model, caller, response)
    if cache:
        keep(kept, response)
    return response
