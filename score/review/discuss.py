"""Discuss (CONTEXT.md "discussion", owner 2026-10-21): the creator's question about the concept draw his review page
shows, asked before he draws again. One Gemini 3.1 Pro call (the model Redraw with notes corrects its prompt with) is
sent everything that redraw would send (the draw boxed with his marks and clean, each locked concept it was drawn on
that he marked, the prompt it was drawn from, his marks' notes), the discussion so far and his question; it answers in
plain text. Each Discuss is his click and its own spend yes, at the measured Gemini answer (concepts.MEASURED_ASK);
what the call really cost is read from its token usage and kept on the record, and every discussion's cost sums into
the cockpit's running total (`spent`). A discussion stays open until the next draw of the place: Redraw with notes then
sends its open thread with the notes to the prompt model (concepts.redrawn), and from then on it is closed, kept for
the record.

    concepts/<place>/discussions/<time>.json  {place, base, question, answer, marks, context_marks, at, by, euros (the
                                               call's measured cost), yes, yes_euros, seconds}

Written only in the owner's process (concepts.recorded). Run as its own process inside his yes, like a draw:

    SCORE_SPEND_TICKET="override <key>" python -m score.review.discuss <place> <request.json> <by>

`request.json` is {base (the sha of the draw shown), question, marks, context_marks}."""
import json
import pathlib
import sys
import time
import urllib.error

from score.review import concepts
from score.store import stamp_key

CALLER = "concept-discuss"  # its own caller on the Google ledger, so its calls can be measured apart
LONGEST_QUESTION = 2000


def price(per_unit=concepts.DATA / "costs/per-unit.json"):
    """The euros of one Discuss: the measured Gemini 3.1 Pro answer on pictures at the standard tier; None while it is
    not measured."""
    return concepts.draw_euros(per_unit, (concepts.MEASURED_ASK,))


def yes_key(place, at):
    return f"discuss-{place}-{stamp_key(at)}"


def discussions(store, place):
    """Every discussion entry of `place`, oldest first."""
    return [store.read(key) for key in sorted(store.objects.keys(f"{concepts.AREA}/{place}/discussions/"))]


def open_thread(store, place, base):
    """The entries about draw `base` asked since the place's newest draw: the thread its next redraw sends."""
    drawn = max((record["at"] for record in concepts.draws(store, place)), default="")
    return [entry for entry in discussions(store, place) if entry["base"] == base and entry["at"] > drawn]


def thread_words(thread):
    """The discussion as the prompt model reads it, "" with none."""
    return "".join(f"\nCreator: {entry['question']}\nYou: {entry['answer']}" for entry in thread)


def redraw_words(thread):
    """What a Redraw with notes adds to its prompt question for an open thread, "" with none."""
    return (f"\n\nBefore this redraw the creator discussed the painting with you; work what the discussion settled into "
            f"the prompt too:{thread_words(thread)}") if thread else ""


def question_of(parts, thread, question):
    """What Gemini is asked for one Discuss: the pictures and prompt Redraw with notes would send, his notes, the
    discussion so far and his question, answered in plain text."""
    notes = concepts.notes_words(parts["marks"], parts["context"], "")
    return (f"{concepts.pictures_words(parts['context'])} The painting was drawn from the prompt below. The creator is "
            "reviewing it before asking for a redraw and asks you about it. Answer in plain text, briefly and "
            "concretely, as the concept artist who will correct the prompt: what you see, what you would change and "
            "how the prompt could say it. Do not write the whole prompt."
            + (f"\n\nThe creator's notes: {notes}" if notes else "")
            + (f"\n\nThe discussion so far:{thread_words(thread)}" if thread else "")
            + f"\n\nThe creator's question: {question}\n\nThe prompt:\n{parts['prompt']}")


def call_euros(response):
    """What one answered call cost, from its token usage, as google_spend writes it on its ledger."""
    _, google_spend, _ = concepts.tools()
    usage = response.get("usageMetadata", {})
    tier = usage.get("serviceTier") or response.get("serviceTier")
    return round(google_spend.dollars(concepts.PROMPT_MODEL, usage)
                 * google_spend.TIER_PRICE.get(str(tier).lower(), 1.0) * google_spend.EUROS_PER_DOLLAR, 6)


def asked(question, pictures):
    """One Gemini 3.1 Pro call (google_spend, on its ledger, never cached: each click is its own); (the text it
    answered, its euros), or concepts.Refused."""
    pro, google_spend, secret_store = concepts.tools()
    body = {"contents": [{"role": "user", "parts": [{"text": question}]
                          + [pro.part(picture, concepts.LONGEST_SENT) for picture in pictures]}],
            "generationConfig": {"temperature": 0.4}}
    try:
        response = google_spend.generate(concepts.PROMPT_MODEL, body, secret_store.secret(pro.KEY_SECRET),
                                         concepts.TIMEOUT, caller=CALLER)
    except urllib.error.HTTPError as error:
        raise concepts.Refused(f"the prompt model refused ({error.code})") from error
    candidate = (response.get("candidates") or [{}])[0]
    text = "".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", [])
                   if not part.get("thought")).strip()
    return text, call_euros(response)


def discuss(store, place, request, by, asker=asked):
    """One Discuss inside the owner's yes (SCORE_SPEND_TICKET names it; compute.require_cleared refuses otherwise):
    `asker(question, pictures)` answers (text, euros); the entry kept and returned. concepts.Refused for no shown draw,
    no question, or no answer."""
    from score.adapters import compute
    yes = compute.require_cleared("a concept discussion", store)
    question = str(request.get("question") or "").strip()
    if not question or len(question) > LONGEST_QUESTION:
        raise concepts.Refused(f"a question is 1 to {LONGEST_QUESTION} characters")
    if not request.get("base"):
        raise concepts.Refused("there is no draw to discuss yet")
    parts = concepts.redraw_parts(store, place, request)
    began = time.time()
    answer, euros = asker(question_of(parts, open_thread(store, place, request["base"]), question), parts["pictures"])
    if not answer:
        raise concepts.Refused("the prompt model answered nothing")
    entry = {"place": place, "base": request["base"], "question": question, "answer": answer,
             "marks": parts["marks"], "context_marks": parts["context"], "at": concepts.now(), "by": by,
             "euros": euros, "yes": yes["key"], "yes_euros": yes["euros"], "seconds": round(time.time() - began, 1)}
    concepts.recorded(store, f"{concepts.AREA}/{place}/discussions/{stamp_key(entry['at'])}.json", entry)
    return entry


def spent(store, places):
    """The euros every discussion of `places` cost, measured, in sum (the cockpit's running total)."""
    return round(sum(entry["euros"] for place in places for entry in discussions(store, place)), 4)


def main(argv):
    """`<place> <request.json> <by>`: one Discuss in the store its yes is in (SCORE_SPEND_STORE, else the
    framework's); its entry as one JSON line, or the refusal on stderr with exit 1."""
    import os
    from score.adapters.compute import STORE, Refused as NotCleared
    from score.store import Store
    place, request, by = argv
    store = Store.in_folder(os.environ[STORE]) if os.environ.get(STORE) else Store.default()
    try:
        entry = discuss(store, place, json.loads(pathlib.Path(request).read_text()), by)
    except (concepts.Refused, NotCleared) as refused:
        print(f"refused: {refused}", file=sys.stderr)
        return 1
    print(json.dumps(entry))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
