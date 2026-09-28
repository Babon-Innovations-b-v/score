"""Check the card lock, which is the only thing standing between us and a crashed box.

No test framework: nothing in this repo installs one for Python, and the lock is plain enough
that a script which exits non-zero is honest. It claims a temporary directory rather than the
real tool chain, so running it never disturbs a run in progress.

Run: python3 tools/props/card_test.py
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
_SANDBOX = tempfile.mkdtemp(prefix="card-test-")
# paths.py reads this, and card.py fixes the claim's home when it is imported, so both come
# after. A test that took the real claim could stop somebody else's run.
os.environ["PROPS_HOME"] = _SANDBOX
sys.path.insert(0, str(HERE))

import card  # noqa: E402

card.LOOK_AGAIN_SECONDS = 0.2
# Short, so a lock that fails to notice a free card fails this check rather than hanging it.
card.GIVE_UP_SECONDS = 8

_failures = []


def check(what, held):
    print(("PASS  " if held else "FAIL  ") + what)
    if not held:
        _failures.append(what)


def quietly(line):
    """Swallow what a run would print while it waits."""


def test_it_claims_the_card_and_gives_it_back():
    card.CLAIM.unlink(missing_ok=True)
    card.SECOND_CLAIM.unlink(missing_ok=True)
    with card.claimed("a run", say=quietly):
        claimed = card.CLAIM.exists() and str(os.getpid()) in card.CLAIM.read_text()
    check("claims the card, then gives it back", claimed and not card.CLAIM.exists())


def test_a_claim_whose_process_is_gone_is_taken_over():
    gone = next(pid for pid in range(4000000, 4100000) if not card._process_is_alive(pid))
    card.CLAIM.write_text(f"{gone} a run that died")
    with card.claimed("a later run", say=quietly):
        took_over = str(os.getpid()) in card.CLAIM.read_text()
    check("takes over a claim whose process is gone", took_over)


def test_a_claim_that_is_not_a_claim_names_nobody():
    card.CLAIM.write_text("not a process id at all")
    with card.claimed("a run after rubbish", say=quietly):
        pass
    check("clears a corrupt claim", not card.CLAIM.exists())


def test_a_process_that_has_exited_holds_nothing():
    """The case that matters most: a finished process still answers a signal check.

    Without this the card would be held for ever by a run that is already over, and the person
    waiting would have no way to tell it apart from one that is still working.
    """
    finished = subprocess.Popen([sys.executable, "-c", ""])
    while finished.poll() is None:
        time.sleep(0.05)
    # Deliberately not collected yet, which is exactly the state that fooled the first version.
    card.CLAIM.write_text(f"{finished.pid} a run that has already finished")
    held = card._process_is_alive(finished.pid)
    finished.wait()
    check("a process that has exited but not been collected holds nothing", not held)


def test_it_waits_for_a_live_holder_and_says_who():
    holder = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3)"])
    card.CLAIM.write_text(f"{holder.pid} somebody else's prop")
    said = []
    started = time.time()
    with card.claimed("our run", say=said.append):
        waited = time.time() - started
        ours = str(os.getpid()) in card.CLAIM.read_text()
    holder.wait()
    check("waits for a live holder instead of failing", waited > 2.5 and ours)
    check("says who is on the card", any(str(holder.pid) in line and "somebody else's prop" in line
                                         for line in said))


def test_claiming_twice_in_one_process_is_free():
    with card.claimed("a batch", say=quietly):
        with card.claimed("a step inside the batch", say=quietly):
            inner = card.CLAIM.exists()
        still_held = card.CLAIM.exists()
    check("a nested claim in the same process does not wait", inner and still_held)
    check("the inner block does not give away the batch's claim", not card.CLAIM.exists())


def test_it_gives_the_card_back_when_the_run_throws():
    try:
        with card.claimed("a run that throws", say=quietly):
            raise RuntimeError("the run failed")
    except RuntimeError:
        pass
    check("gives the card back when the run inside it throws", not card.CLAIM.exists())


def _sleeper(seconds):
    return subprocess.Popen([sys.executable, "-c", f"import time; time.sleep({seconds})"])


def test_two_pixal_runs_share_the_card():
    holder = _sleeper(3)
    card.SECOND_CLAIM.unlink(missing_ok=True)
    card.CLAIM.write_text(f"{holder.pid} {card.SHARES}another model")
    started = time.time()
    with card.claimed("a second model", say=quietly, shared=True):
        waited = time.time() - started
        second = card.SECOND_CLAIM.exists() and str(os.getpid()) in card.SECOND_CLAIM.read_text()
    holder.wait()
    card.CLAIM.unlink(missing_ok=True)
    check("a second model run shares the card with the first", waited < 1 and second)
    check("the second slot is given back", not card.SECOND_CLAIM.exists())


def test_a_run_that_shares_waits_for_one_that_must_be_alone():
    holder = _sleeper(3)
    card.CLAIM.write_text(f"{holder.pid} a picture")
    started = time.time()
    with card.claimed("a model", say=quietly, shared=True):
        waited = time.time() - started
    holder.wait()
    check("a model run waits for a picture run", waited > 2.5)


def test_a_run_that_must_be_alone_waits_for_both_models():
    first, second = _sleeper(2), _sleeper(4)
    card.CLAIM.write_text(f"{first.pid} {card.SHARES}a model")
    card.SECOND_CLAIM.write_text(f"{second.pid} {card.SHARES}another model")
    started = time.time()
    with card.claimed("a picture", say=quietly):
        waited = time.time() - started
        alone = not card.SECOND_CLAIM.exists() or card._read_claim(card.SECOND_CLAIM) is None
    first.wait()
    second.wait()
    check("a picture run waits until both model runs are done", waited > 3.5 and alone)


def test_a_third_model_waits():
    first, second = _sleeper(3), _sleeper(3)
    card.CLAIM.write_text(f"{first.pid} {card.SHARES}a model")
    card.SECOND_CLAIM.write_text(f"{second.pid} {card.SHARES}another model")
    started = time.time()
    with card.claimed("a third model", say=quietly, shared=True):
        waited = time.time() - started
    first.wait()
    second.wait()
    check("a third model run waits for a free slot", waited > 2.5)


def main():
    for name, test in sorted(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
    print()
    if _failures:
        print("FAILED: " + "; ".join(_failures))
        return 1
    print("the card lock holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
