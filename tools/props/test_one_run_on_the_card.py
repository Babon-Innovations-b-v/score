"""One run on the graphics card at a time (card.claimed): a run waits for a live holder and says who it is, a claim
whose process is gone (or never was a claim) holds nothing, the card is given back however the block ends, a nested
claim in one process is free; and, only while card.SHARING is on, two Pixal3D runs share it and nothing else does.

Two runs on one card crash the box, so these are the lock's whole reason. Every case runs on the claim files in the
sandbox home (PROPS_HOME), never the real one; holders are short sleeping processes, so a wait is measured in seconds.

Breaks that turn each test red (each applied once and seen red, 2026-10-26):
- test_it_claims_the_card_and_gives_it_back: claimed's `finally: _drop_stale_claim(...)` made `finally: pass`.
- test_it_gives_the_card_back_when_the_run_throws: the same `try/finally` made `yield` then `if True:`.
- test_a_claim_whose_process_is_gone_is_taken_over: _process_is_alive's `except ProcessLookupError: return False`
  made `return True`.
- test_a_claim_that_is_not_a_claim_names_nobody: _read_claim's `except ValueError: return None` made
  `pid = os.getppid()` (the corrupt claim then names a live process and is never cleared).
- test_a_process_that_has_exited_holds_nothing: _has_finished_but_not_been_collected returns False always.
- test_it_waits_for_a_live_holder_and_says_who: _take_claim's `os.O_CREAT | os.O_EXCL | os.O_WRONLY` without O_EXCL.
- test_claiming_twice_in_one_process_is_free: claimed's own-claim check `if any(_ours(...` made `if False and any(`
  together with _try_alone's `not _ours(_read_claim(CLAIM)) and ` dropped (either one alone still holds: the inner
  block finds its own claim and gives back only a claim written with its own words).
- test_with_sharing_off_a_second_model_run_waits: card.SHARING = True.
- test_with_sharing_on_a_second_model_run_shares_the_card: _may_share returns False always.
- test_with_sharing_on_a_model_run_waits_for_one_that_must_be_alone: _may_share made `holder is not None`.
- test_with_sharing_on_a_run_that_must_be_alone_waits_for_both_models: _wait_for_the_card's `(shared or
  _read_claim(SECOND_CLAIM) is None)` made `(True)`.
- test_with_sharing_on_a_third_model_waits: _take_claim without O_EXCL (as above).
"""
import os
import pathlib
import subprocess
import sys
import time

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import card  # noqa: E402

HOLD = 2.0  # how long a holder keeps the card, in seconds
WAITED = 1.5  # a run that waited for a holder took at least this long


@pytest.fixture(autouse=True)
def quick_lock(monkeypatch):
    """No claim at the start; looks again often, and gives up soon so a lock that never sees a free card fails."""
    monkeypatch.setattr(card, "LOOK_AGAIN_SECONDS", 0.1)
    monkeypatch.setattr(card, "GIVE_UP_SECONDS", 8)
    for claim in (card.CLAIM, card.SECOND_CLAIM):
        claim.unlink(missing_ok=True)
    yield
    for claim in (card.CLAIM, card.SECOND_CLAIM):
        claim.unlink(missing_ok=True)


@pytest.fixture
def sharing(monkeypatch):
    monkeypatch.setattr(card, "SHARING", True)


def quietly(line):
    """Swallow what a run would print while it waits."""


def holder(seconds=HOLD):
    """A live process that holds nothing itself, for a claim to name."""
    return subprocess.Popen([sys.executable, "-c", f"import time; time.sleep({seconds})"])


def timed(doing, shared=False, say=quietly):
    """Seconds a claim waited, and whether it then held the main claim (`CLAIM`) or the second one."""
    started = time.time()
    with card.claimed(doing, say=say, shared=shared):
        waited = time.time() - started
        main = str(os.getpid()) in (card.CLAIM.read_text() if card.CLAIM.exists() else "")
        second = str(os.getpid()) in (card.SECOND_CLAIM.read_text() if card.SECOND_CLAIM.exists() else "")
    return waited, main, second


def test_it_claims_the_card_and_gives_it_back():
    _, main, _ = timed("a run")
    assert main and not card.CLAIM.exists()


def test_it_gives_the_card_back_when_the_run_throws():
    with pytest.raises(RuntimeError):
        with card.claimed("a run that throws", say=quietly):
            raise RuntimeError("the run failed")
    assert not card.CLAIM.exists()


def test_a_claim_whose_process_is_gone_is_taken_over():
    gone = next(pid for pid in range(4000000, 4100000) if not card._process_is_alive(pid))
    card.CLAIM.write_text(f"{gone} a run that died")
    waited, main, _ = timed("a later run")
    assert main and waited < 1


def test_a_claim_that_is_not_a_claim_names_nobody():
    card.CLAIM.write_text("not a process id at all")
    waited, main, _ = timed("a run after rubbish")
    assert main and waited < 1 and not card.CLAIM.exists()


def test_a_process_that_has_exited_holds_nothing():
    """A finished process still answers a signal check until its parent collects it: without the zombie check the
    card would be held for ever by a run that is already over."""
    child = os.fork()  # a child that exits at once and is not collected until the end: a zombie
    if child == 0:
        os._exit(0)
    time.sleep(0.3)
    try:
        card.CLAIM.write_text(f"{child} a run that has already finished")
        assert not card._process_is_alive(child)
        waited, main, _ = timed("the next run")
        assert main and waited < 1
    finally:
        os.waitpid(child, 0)


def test_it_waits_for_a_live_holder_and_says_who():
    running = holder()
    card.CLAIM.write_text(f"{running.pid} somebody else's prop")
    said = []
    waited, main, _ = timed("our run", say=said.append)
    running.wait()
    assert waited > WAITED and main
    assert any(str(running.pid) in line and "somebody else's prop" in line for line in said), said


def test_claiming_twice_in_one_process_is_free():
    with card.claimed("a batch", say=quietly):
        with card.claimed("a step inside the batch", say=quietly):
            inner = card.CLAIM.exists()
        still_held = card.CLAIM.exists()
    assert inner and still_held and not card.CLAIM.exists()


def test_with_sharing_off_a_second_model_run_waits():
    assert card.SHARING is False  # off until the owner says the machine is stable (2026-09-30)
    first = holder()
    card.CLAIM.write_text(f"{first.pid} {card.SHARES}another model")
    waited, _, second = timed("a second model", shared=True)
    first.wait()
    assert waited > WAITED and not second


def test_with_sharing_on_a_second_model_run_shares_the_card(sharing):
    first = holder()
    card.CLAIM.write_text(f"{first.pid} {card.SHARES}another model")
    waited, _, second = timed("a second model", shared=True)
    first.wait()
    assert waited < 1 and second and not card.SECOND_CLAIM.exists()


def test_with_sharing_on_a_model_run_waits_for_one_that_must_be_alone(sharing):
    picture = holder()
    card.CLAIM.write_text(f"{picture.pid} a picture")
    waited, _, _ = timed("a model", shared=True)
    picture.wait()
    assert waited > WAITED


def test_with_sharing_on_a_run_that_must_be_alone_waits_for_both_models(sharing):
    first, second = holder(1.0), holder(HOLD)
    card.CLAIM.write_text(f"{first.pid} {card.SHARES}a model")
    card.SECOND_CLAIM.write_text(f"{second.pid} {card.SHARES}another model")
    waited, main, _ = timed("a picture")
    first.wait()
    second.wait()
    assert waited > WAITED and main


def test_with_sharing_on_a_third_model_waits(sharing):
    first, second = holder(), holder()
    card.CLAIM.write_text(f"{first.pid} {card.SHARES}a model")
    card.SECOND_CLAIM.write_text(f"{second.pid} {card.SHARES}another model")
    waited, _, _ = timed("a third model", shared=True)
    first.wait()
    second.wait()
    assert waited > WAITED
