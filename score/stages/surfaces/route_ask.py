"""The finish route's paid asks: Gemini 3.1 Pro through Google's Batch API at half price (tools/props/cloud/
google_batch.py, on google_spend's ledger and cache; the key `gemini-api-key` by name through secret_store). One row
run sends all its takes' asks as one batch, asked once: an ask asked before is read back free, one the batch gives no
answer to is its take's hole, never asked again (a new batch is new spend). Refused outside a cleared run.
"""
import finish_ask  # puts google_spend's folder on the path
import google_batch  # noqa: E402

# What a take's ask with no usable answer raises or holds: no answer from the batch, a reply that does not parse.
UNANSWERED = (*finish_ask.UNANSWERED, google_batch.Unanswered)


def asked(bodies, caller):
    """{take: the answer's text, or the google_batch.Unanswered saying why there is none} of one batch of
    generateContent bodies ({take: body})."""
    from score.adapters import compute
    compute.require_cleared(f"a Gemini batch ({caller})")
    answers = google_batch.generate(finish_ask.LIST_MODEL, bodies, finish_ask.secret_key(), caller)
    return {take: answer if isinstance(answer, Exception) else finish_ask.reply_text(answer)
            for take, answer in answers.items()}
