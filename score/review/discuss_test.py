"""Discuss (score/review/discuss.py), with stand-ins for the models (no call is made, nothing is spent): a Discuss runs
only inside the owner's yes, sends what a redraw would with the thread so far and keeps the question, answer and the
call's measured cost; a redraw after it sends the open thread to the prompt rewrite and closes it; the click's yes is
written at the price shown."""
import json
import subprocess

import pytest

from score import review
from score.adapters import compute
from score.review import concepts, discuss, web
from score.review.concepts_test import prompt_stand_in, said_yes, stand_in, store  # noqa: F401 (the fixture)


def answerer(asked, answer="Make the door red and wider.", euros=0.0271):
    """A prompt model that keeps what it was asked and answers `answer` at `euros`."""
    def answered(question, pictures):
        asked.append((question, [picture.size for picture in pictures]))
        return answer, euros
    return answered


def first_draw(store, monkeypatch):
    said_yes(store, monkeypatch)
    return concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))


def test_a_discuss_runs_inside_the_yes_and_keeps_question_answer_and_cost(store, monkeypatch):
    first = first_draw(store, monkeypatch)
    monkeypatch.delenv("SCORE_SPEND_TICKET")
    request = {"base": first["sha"], "question": "is the door too small?",
               "marks": [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.3, "note": "this door"}]}
    with pytest.raises(compute.Refused):
        discuss.discuss(store, "campgrounds", request, "joey", asker=answerer([]))
    key = said_yes(store, monkeypatch)
    asked = []
    entry = discuss.discuss(store, "campgrounds", request, "joey", asker=answerer(asked))
    question, sizes = asked[0]  # the redraw's pictures (boxed, clean), its prompt, the mark's note, the question
    assert "Box 1 (middle left): this door." in question and "is the door too small?" in question
    assert first["wording"] in question and sizes == [(64, 40), (64, 40)]
    assert entry["answer"] == "Make the door red and wider." and entry["euros"] == 0.0271 and entry["yes"] == key
    assert discuss.discussions(store, "campgrounds") == [entry] and discuss.spent(store, ["campgrounds"]) == 0.0271
    said_yes(store, monkeypatch)
    again = []
    discuss.discuss(store, "campgrounds", {"base": first["sha"], "question": "and the roof?"}, "joey",
                    asker=answerer(again, "Keep it."))
    assert "Creator: is the door too small?\nYou: Make the door red and wider." in again[0][0]
    with pytest.raises(concepts.Refused, match="a question"):
        discuss.discuss(store, "campgrounds", {"base": first["sha"], "question": " "}, "joey", asker=answerer([]))


def test_a_redraw_after_a_discuss_sends_the_thread_to_the_prompt_rewrite_and_closes_it(store, monkeypatch):
    first = first_draw(store, monkeypatch)
    said_yes(store, monkeypatch)
    discuss.discuss(store, "campgrounds", {"base": first["sha"], "question": "warmer light?"}, "joey",
                    asker=answerer([], "Yes: late afternoon sun from the left."))
    assert len(discuss.open_thread(store, "campgrounds", first["sha"])) == 1
    said_yes(store, monkeypatch)
    prompted = []
    second = concepts.draw(store, "campgrounds", {"base": first["sha"]}, "joey", caller=stand_in([]),
                           reviser=prompt_stand_in(prompted))
    question = prompted[0][0]
    assert "Creator: warmer light?\nYou: Yes: late afternoon sun from the left." in question
    assert second["discussed"] == [discuss.discussions(store, "campgrounds")[0]["at"]]
    assert discuss.open_thread(store, "campgrounds", first["sha"]) == []  # closed, kept for the record
    assert len(discuss.discussions(store, "campgrounds")) == 1


def test_the_click_writes_its_yes_at_the_price_shown_then_discusses_inside_it(store, monkeypatch):
    first = first_draw(store, monkeypatch)
    monkeypatch.setattr(discuss, "price", lambda: 0.04)

    def run(argv, env, **kwargs):  # the Discuss's own process, here in-process with the stand-in model
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        entry = discuss.discuss(store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1], asker=answerer([]))
        return subprocess.CompletedProcess(argv, 0, json.dumps(entry) + "\n", "")

    entry = web.concept_discuss(store, "campgrounds", {"base": first["sha"], "question": "why?"}, 0.04, "joey",
                                run=run)
    yes = store.spend_yes("override", entry["yes"])
    assert yes["by"] == "joey" and yes["euros"] == 0.04 and "Discuss" in yes["purpose"]
    with pytest.raises(review.Refused, match="not today's measured price"):
        web.concept_discuss(store, "campgrounds", {"base": first["sha"], "question": "why?"}, 0.03, "joey", run=run)


def test_a_calls_cost_is_read_from_its_token_usage():
    usage = {"usageMetadata": {"promptTokenCount": 2700, "candidatesTokenCount": 200, "thoughtsTokenCount": 1700}}
    assert 0.02 < discuss.call_euros(usage) < 0.04
