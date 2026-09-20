"""One run on the graphics card at a time.

Two runs on one card do not queue, they break. The second one dies with an illegal memory access
inside the text encoder, before any picture work has started, which reads as a broken model rather
than a busy card; on this box it has also taken the whole machine down. So a run claims the card
here before it loads anything onto it.

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


def _read_claim():
    """Who holds the card, as (process id, what they are doing), or None when nobody does."""
    try:
        text = CLAIM.read_text()
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


def _drop_stale_claim(text):
    """Remove a claim whose process is gone, unless somebody rewrote it while we looked."""
    try:
        if CLAIM.read_text() == text:
            CLAIM.unlink()
    except (FileNotFoundError, OSError):
        pass


def _take_claim(doing):
    """Write our own claim, or return False when somebody else got there first."""
    HOME.mkdir(parents=True, exist_ok=True)
    try:
        handle = os.open(CLAIM, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(handle, "w") as claim:
        claim.write(f"{os.getpid()} {doing}")
    return True


def _wait_for_the_card(doing, say):
    """Block until the card is free, then claim it. Raises when the wait runs out."""
    waited = 0
    told_about = None
    holder = None
    while True:
        if _take_claim(doing):
            return
        holder = _read_claim()
        if holder is None:
            # Whoever wrote that claim is gone, or it is not a claim at all. Clear it.
            _drop_a_claim_nobody_holds()
        elif holder[0] == os.getpid():
            # Already ours: a batch claimed the card and is now calling through this again.
            return
        elif told_about != holder[0]:
            say(f"waiting for the graphics card: process {holder[0]} is on {holder[1]}")
            told_about = holder[0]
        if waited >= GIVE_UP_SECONDS:
            held_by = f"process {holder[0]} ({holder[1]})" if holder else "a claim that will not clear"
            raise SystemExit(
                f"the graphics card has been held by {held_by} for {GIVE_UP_SECONDS // 60} "
                f"minutes. Check whether that run is wedged; once it is gone its claim clears "
                f"itself."
            )
        # Slept even when the claim was just cleared, so a claim that refuses to go does not
        # spin the processor while it waits.
        time.sleep(LOOK_AGAIN_SECONDS)
        waited += LOOK_AGAIN_SECONDS


def _drop_a_claim_nobody_holds():
    """Remove the claim file when whoever wrote it is gone, or it is not a claim at all."""
    try:
        _drop_stale_claim(CLAIM.read_text())
    except OSError:
        pass


@contextlib.contextmanager
def claimed(doing, say=lambda line: print(line, file=sys.stderr, flush=True)):
    """Hold the graphics card for the length of this block, waiting for it if somebody else has it.

    Taking it twice in one process is free, so a batch can claim the card once around the whole
    batch and the steps inside it still claim as they normally would.
    """
    held = _read_claim()
    ours_already = held is not None and held[0] == os.getpid()
    if not ours_already:
        _wait_for_the_card(doing, say)
    try:
        yield
    finally:
        if not ours_already:
            _drop_stale_claim(f"{os.getpid()} {doing}")
