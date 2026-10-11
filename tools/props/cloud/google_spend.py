"""Every call to Google's Gemini API goes through here: priced and written down, and asked once when cached.

    response = google_spend.generate(model, body, key, timeout, caller="gemini_judge", cache=True)

Each call's cost is counted from the response's usageMetadata (input, output and thinking tokens, and image tokens)
at Google's published paid-tier prices (PRICES) and appended as one line to google-ledger.jsonl beside the cloud
ledger, so where the Google spend goes can be read back. No cap: the owner wants none (2026-10-11).
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


def record(model, caller, response):
    """Append one call's line to the ledger; its euros."""
    usage = response.get("usageMetadata", {})
    cost = dollars(model, usage)
    entry = {"time": datetime.datetime.now(DAY_ZONE).isoformat(timespec="seconds"), "day": today(), "model": model,
             "caller": caller, "input": usage.get("promptTokenCount", 0),
             "output": usage.get("candidatesTokenCount", 0), "thinking": usage.get("thoughtsTokenCount", 0),
             "dollars": None if cost is None else round(cost, 6),
             "euros": None if cost is None else round(cost * EUROS_PER_DOLLAR, 6)}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as ledger:  # one short line, appended whole: no lock needed
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
    """One generateContent call: with cache=True a response asked before is read back; otherwise made, recorded
    and, with cache=True, kept."""
    kept = cache_path(model, body)
    if cache and kept.exists():
        return json.loads(kept.read_text())
    response = post(model, body, key, timeout)
    record(model, caller, response)
    if cache:
        keep(kept, response)
    return response
