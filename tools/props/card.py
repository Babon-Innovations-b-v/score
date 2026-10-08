"""One run on the graphics card at a time, or two Pixal3D runs together.

Two runs on one card do not queue, they break. The second one dies with an illegal memory access
inside the text encoder, before any picture work has started, which reads as a broken model rather
than a busy card; on this box it has also taken the whole machine down. So a run claims the card
here before it loads anything onto it.

The one measured exception is Pixal3D: two of its runs share the card safely (2026-09-28, two
bulky models 60 s apart peaked at 12.4 of 16.3 GB, both whole, the pair 30% faster than one after
the other). A run that may share says so (`shared=True`); it takes the main claim when that is
free, or the second one, SECOND_CLAIM, while the main claim's holder may share too. Every other
run holds the card alone: it takes the main claim and then waits for the second to empty. Nothing
else was ever measured beside a Pixal3D run, so nothing else shares. Sharing is switched off for
now (SHARING, below): every run holds the card alone until the owner says the machine is stable.

The claim is a file naming the process that holds it. A process that is gone holds nothing, so a
crash cannot leave a claim that needs a magic word to clear: the next run sees a dead process and
takes the card. That matters, because the crash this was written for was the card itself going
down.

Waiting beats failing. A run that finds the card busy says who is on it and waits, because work
that is worth doing is worth doing a minute later.
"""
import contextlib
import os
import sys
import time

from paths import HOME

CLAIM = HOME / "card.claim"
SECOND_CLAIM = HOME / "card.claim.2"
# Written before what a run is doing when it may share the card.
SHARES = "(shares) "
# Off since 2026-09-30: the PC blue-screened four times (0x3B, 0x154), twice while two runs shared
# the card, with its memory running overclocked. Until the owner says the machine is stable, a run
# that asks to share waits for the whole card like any other. Turning this back on is his call.
SHARING = False

# How often to look again while waiting, and how long to wait before giving up. A prop takes
# well under a minute, a batch of twenty takes twenty, so half an hour is long enough to cover
# any real run and short enough that a wedged process is noticed the same session.
LOOK_AGAIN_SECONDS = 5
GIVE_UP_SECONDS = 1800


def _process_is_alive(pid):
    """Whether a process id still names a process that is running."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Somebody else's process, which is very much alive.
        return True
    return not _has_finished_but_not_been_collected(pid)


def _has_finished_but_not_been_collected(pid):
    """Whether the process has exited and is only waiting for its parent to collect it.

    Such a process answers a signal check exactly as a running one does, so without this a run
    launched by a wrapper that never collects it would hold the card for ever. Found by the
    lock's own test rather than by losing a run to it.
    """
    try:
        with open(f"/proc/{pid}/stat", "rb") as stat:
            # The program's own name sits in brackets and may itself contain spaces or a
            # bracket, so the state is read as the first field after the last closing bracket.
            after_the_name = stat.read().rpartition(b")")[2].split()
    except OSError:
        return False
    return bool(after_the_name) and after_the_name[0] == b"Z"


def _read_claim(path=None):
    """Who holds a claim, as (process id, what they are doing), or None when nobody does."""
    try:
        text = (path or CLAIM).read_text()
    except (FileNotFoundError, OSError):
        return None
    pid_text, _, doing = text.partition(" ")
    try:
        pid = int(pid_text)
    except ValueError:
        # A half-written or corrupt claim names nobody.
        return None
    if not _process_is_alive(pid):
        return None
    return pid, doing.strip() or "an unnamed run"


def _may_share(holder):
    """Whether a claim's holder said it may share the card."""
    return holder is not None and holder[1].startswith(SHARES)


def _drop_stale_claim(text, path=None):
    """Remove a claim whose process is gone, unless somebody rewrote it while we looked."""
    path = path or CLAIM
    try:
        if path.read_text() == text:
            path.unlink()
    except (FileNotFoundError, OSError):
        pass


def _take_claim(doing, path=None):
    """Write our own claim, or return False when somebody else got there first."""
    HOME.mkdir(parents=True, exist_ok=True)
    try:
        handle = os.open(path or CLAIM, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(handle, "w") as claim:
        claim.write(f"{os.getpid()} {doing}")
    return True


def _drop_a_claim_nobody_holds(path=None):
    """Remove the claim file when whoever wrote it is gone, or it is not a claim at all."""
    path = path or CLAIM
    try:
        if _read_claim(path) is None:
            _drop_stale_claim(path.read_text(), path)
    except OSError:
        pass


def _ours(holder):
    return holder is not None and holder[0] == os.getpid()


def _try_alone(doing):
    """One attempt at the card for a run that must be alone on it: the claim it now holds (kept
    while it waits for a sharing run to finish), or None."""
    held = _read_claim(CLAIM)
    if not _ours(held) and not _take_claim(doing, CLAIM):
        return None
    # Claim first, then look at the second slot: a sharing run does the same the other way
    # round, so at least one of two runs arriving together sees the other.
    return CLAIM


def _try_shared(doing):
    """One attempt at the card for a run that may share it: the claim it took, or None."""
    if _take_claim(doing, CLAIM):
        return CLAIM
    if not _may_share(_read_claim(CLAIM)) or not _take_claim(doing, SECOND_CLAIM):
        return None
    if _may_share(_read_claim(CLAIM)) or _read_claim(CLAIM) is None:
        return SECOND_CLAIM
    # A run that must be alone took the main claim meanwhile: give the second back.
    _drop_stale_claim(f"{os.getpid()} {doing}", SECOND_CLAIM)
    return None


def _busy_with(path):
    """Who is on the card in a way that keeps us waiting, clearing claims nobody holds."""
    for claim in (CLAIM, SECOND_CLAIM):
        _drop_a_claim_nobody_holds(claim)
    if path == CLAIM:
        return _read_claim(SECOND_CLAIM)
    return _read_claim(CLAIM)


def _wait_for_the_card(doing, shared, say):
    """Block until the card is ours, and return the claim file we hold. Raises when the wait
    runs out."""
    waited = 0
    told_about = None
    taken = None
    while True:
        taken = taken or (_try_shared(doing) if shared else _try_alone(doing))
        if taken == SECOND_CLAIM or (taken == CLAIM and (shared or _read_claim(SECOND_CLAIM) is None)):
            return taken
        holder = _busy_with(taken)
        if holder is not None and told_about != holder[0]:
            say(f"waiting for the graphics card: process {holder[0]} is on {holder[1]}")
            told_about = holder[0]
        if waited >= GIVE_UP_SECONDS:
            if taken:
                _drop_stale_claim(f"{os.getpid()} {doing}", taken)
            held_by = f"process {holder[0]} ({holder[1]})" if holder else "a claim that will not clear"
            raise SystemExit(
                f"the graphics card has been held by {held_by} for {GIVE_UP_SECONDS // 60} "
                f"minutes. Check whether that run is wedged; once it is gone its claim clears "
                f"itself."
            )
        # Slept even when a claim was just cleared, so a claim that refuses to go does not
        # spin the processor while it waits.
        time.sleep(LOOK_AGAIN_SECONDS)
        waited += LOOK_AGAIN_SECONDS


@contextlib.contextmanager
def claimed(doing, say=lambda line: print(line, file=sys.stderr, flush=True), shared=False):
    """Hold the graphics card for the length of this block, waiting for it if somebody else has it.

    `shared` lets a second run of the same kind onto the card beside this one; only Pixal3D was
    measured safe for that. Taking it twice in one process is free, so a batch can claim the card
    once around the whole batch and the steps inside it still claim as they normally would.
    """
    if any(_ours(_read_claim(claim)) for claim in (CLAIM, SECOND_CLAIM)):
        yield
        return
    shared = shared and SHARING
    doing = SHARES + doing if shared else doing
    taken = _wait_for_the_card(doing, shared, say)
    try:
        yield
    finally:
        _drop_stale_claim(f"{os.getpid()} {doing}", taken)
