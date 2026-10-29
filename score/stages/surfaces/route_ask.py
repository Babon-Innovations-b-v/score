"""The finish route's paid asks: Gemini 3.1 Pro through Google's Batch API at half price (tools/cloud/
google_batch.py, on google_spend's ledger and cache; the key `gemini-api-key` by name through secret_store). One row
run sends all its takes' asks as one batch, asked once: an ask asked before is read back free, one the batch gives no
answer to is its take's gap, never asked again (a new batch is new spend). Every ask here answers JSON under a response
schema; an answer that still does not parse is a gap too, dropped from the cache so the next try asks it fresh rather
than reading the same broken answer back (fault, 2026-10-25: surface-library@camp). A batch with a request the cache
does not answer is refused outside a cleared run; one the cache answers whole costs nothing, so it needs no clearance
and runs in a free-only run too (fault, 2026-10-29: body-face-earth refused although Google's cache held its answer).
"""
import json

import finish_ask  # puts google_spend's folder on the path
import google_batch  # noqa: E402
import google_spend  # noqa: E402

# What a take's ask with no usable answer raises or holds: no answer from the batch, a reply that does not parse.
UNANSWERED = (*finish_ask.UNANSWERED, google_batch.Unanswered)


def asked(bodies, caller):
    """{take: the answer's text, or the google_batch.Unanswered saying why there is none} of one batch of
    generateContent bodies ({take: body})."""
    from score.adapters import compute
    key = None  # google_batch reads the key only for a job it sends, and sends none when the cache answers all
    if not all(google_spend.cache_path(finish_ask.LIST_MODEL, body).exists() for body in bodies.values()):
        compute.require_cleared(f"a Gemini batch ({caller})")
        key = finish_ask.secret_key()
    answers = google_batch.generate(finish_ask.LIST_MODEL, bodies, key, caller)
    return {take: answer if isinstance(answer, Exception) else parsing(answer, bodies[take])
            for take, answer in answers.items()}


def parsing(response, body):
    """The answer's text when it parses as JSON; else google_batch.Unanswered, its cached answer dropped."""
    text = finish_ask.reply_text(response)
    try:
        json.loads(text)
    except ValueError as error:
        google_spend.cache_path(finish_ask.LIST_MODEL, body).unlink(missing_ok=True)
        return google_batch.Unanswered(f"the answer did not parse, a gap the next try asks again: {error!r}")
    return text
