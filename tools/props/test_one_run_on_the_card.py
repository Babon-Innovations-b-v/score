"""One run on the graphics card at a time (card.claimed): a run waits for a live holder and says who it is, a claim
whose process is gone (or never was a claim) holds nothing, the card is given back however the block ends, a nested
claim in one process is free; and, only while card.SHARING is on, two Pixal3D runs share it and nothing else does.

Two runs on one card crash the box, so these are the lock's whole reason. Every case runs on the claim files in the
sandbox home (PROPS_HOME), never the real one; holders are short sleeping processes, so a wait is measured in seconds.
Each row of the one test is a card as a run finds it (who holds which claim, whether sharing is on) and what the run
must then get: whether it waits, which claim it holds, that a step inside it claims again for free, what it says
while it waits, and that it gives its claim back.

Breaks that turn the test red (each applied once and seen red; row ids in brackets, 2026-11-14):
- claimed's `finally: _drop_stale_claim(...)` made `finally: pass` [free].
- the same `try/finally` made `yield` then `if True:` [a run that throws].
- _process_is_alive's `except ProcessLookupError: return False` made `return True` [a dead holder].
- _read_claim's `except ValueError: return None` made `pid = os.getppid()` (the corrupt claim then names a live
  process and is never cleared) [rubbish].
- _has_finished_but_not_been_collected returns False always [an exited holder].
- _take_claim's `os.O_CREAT | os.O_EXCL | os.O_WRONLY` without O_EXCL [a live holder, third model].
- claimed's own-claim check `if any(_ours(...` made `if False and any(` together with _try_alone's
  `not _ours(_read_claim(CLAIM)) and ` dropped (either one alone still holds: the inner step finds its own claim and
  gives back only a claim written with its own words) [every row].
- card.SHARING = True [sharing off].
- _may_share returns False always [second model shares].
- _may_share made `holder is not None` [model waits for a picture].
- _wait_for_the_card's `(shared or _read_claim(SECOND_CLAIM) is None)` made `(True)` [picture waits for both].
"""
import contextlib
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
SHARED_MODEL = f"{card.SHARES}another model"

# Each row: id, sharing on, the claims on the card when the run starts as (claim file, holder kind, what the holder
# is doing, seconds it lives), what the run is doing, whether it may share, whether its body throws, then the
# answer: whether it waits, and which claim it holds ("main" for card.CLAIM, "second" for card.SECOND_CLAIM).
CASES = [
    ("free", False, (), "a run", False, False, False, "main"),
    ("a run that throws", False, (), "a run that throws", False, True, False, "main"),
    ("a dead holder", False, (("main", "gone", "a run that died", 0),), "a later run", False, False, False, "main"),
    ("rubbish", False, (("main", "rubbish", "", 0),), "a run after rubbish", False, False, False, "main"),
    ("an exited holder", False, (("main", "zombie", "a run that has already finished", 0),),
     "the next run", False, False, False, "main"),
    ("a live holder", False, (("main", "live", "somebody else's prop", HOLD),), "our run", False, False, True, "main"),
    ("sharing off", False, (("main", "live", SHARED_MODEL, HOLD),), "a second model", True, False, True, "main"),
    ("second model shares", True, (("main", "live", SHARED_MODEL, HOLD),),
     "a second model", True, False, False, "second"),
    ("model waits for a picture", True, (("main", "live", "a picture", HOLD),), "a model", True, False, True, "main"),
    ("picture waits for both", True,
     (("main", "live", f"{card.SHARES}a model", 1.0), ("second", "live", SHARED_MODEL, HOLD)),
     "a picture", False, False, True, "main"),
    ("third model", True,
     (("main", "live", f"{card.SHARES}a model", HOLD), ("second", "live", SHARED_MODEL, HOLD)),
     "a third model", True, False, True, "main"),
]
CLAIMS = {"main": card.CLAIM, "second": card.SECOND_CLAIM}


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


def holder_pid(kind, seconds, children):
    """A process id for a claim to name: a live sleeper, a gone id, an exited but uncollected child, or None."""
    if kind == "live":
        process = subprocess.Popen([sys.executable, "-c", f"import time; time.sleep({seconds})"])
        children.append(process.wait)
        return process.pid
    if kind == "gone":
        return next(pid for pid in range(4000000, 4100000) if not card._process_is_alive(pid))
    if kind == "zombie":
        child = os.fork()  # a child that exits at once and is not collected until the end: a zombie
        if child == 0:
            os._exit(0)
        children.append(lambda: os.waitpid(child, 0))
        time.sleep(0.3)
        return child
    return None


def holds(claim):
    """Whether this process's id is what the claim file names."""
    return claim.exists() and claim.read_text().split(" ")[0] == str(os.getpid())


@pytest.mark.parametrize(
    "sharing, claims, doing, shared, throws, waits, slot", [case[1:] for case in CASES], ids=[case[0] for case in CASES]
)
def test_one_run_on_the_card(monkeypatch, sharing, claims, doing, shared, throws, waits, slot):
    assert card.SHARING is False  # off until the owner says the machine is stable (2026-09-30)
    monkeypatch.setattr(card, "SHARING", sharing)
    children, said, seen, pids = [], [], {}, {}
    try:
        for slot_name, kind, holder_doing, seconds in claims:
            pid = pids[slot_name] = holder_pid(kind, seconds, children)
            CLAIMS[slot_name].write_text("not a process id at all" if pid is None else f"{pid} {holder_doing}")
            # A claim names somebody only while its process runs; a dead, exited or corrupt one names nobody.
            assert (card._read_claim(CLAIMS[slot_name]) is None) == (kind != "live"), (slot_name, kind)
        started = time.time()
        with pytest.raises(RuntimeError) if throws else contextlib.nullcontext():
            with card.claimed(doing, say=said.append, shared=shared):
                seen["waited"] = time.time() - started
                seen["held"] = [name for name, claim in CLAIMS.items() if holds(claim)]
                with card.claimed("a step inside the run", say=said.append):
                    seen["inner"] = holds(CLAIMS[slot])
                seen["after inner"] = holds(CLAIMS[slot])
                if throws:
                    raise RuntimeError("the run failed")
    finally:
        for collect in children:
            collect()
    assert seen["held"] == [slot], seen
    assert seen["inner"] and seen["after inner"], seen
    assert not CLAIMS[slot].exists(), "the run kept the card"
    if waits:
        # The run first finds the main claim taken, and says whose it is and what they are on.
        main_doing = claims[0][2]
        assert seen["waited"] > WAITED, seen
        assert any(str(pids["main"]) in line and main_doing in line for line in said), said
    else:
        assert seen["waited"] < 1 and said == [], (seen, said)
