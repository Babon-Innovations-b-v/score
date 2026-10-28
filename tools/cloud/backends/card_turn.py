"""This PC's card at most CARD_SLOTS Blender calls at a time, while several Blender jobs share its machine
(backends/local.py RUNS_AT_ONCE; env1, 2026-10-28: a bake row's takes ran one after another on 1 to 4 of 24 cores, the
card busy in 1 s bursts and idle 86% of the time).

A Blender startup script: local.take copies it into the container's Blender user startup folder (STARTUP), so every
Blender there loads it before its job's own `--python` script, a nested one too (paint_bake.py's make_chunky), and
no stage's code changes. It wraps the operators that work on the card (CARD_OPS: the Cycles bake and the renders) so
each call holds an exclusive flock on one of CARD_SLOTS lock files for as long as it runs and lets it go when the call
returns; the rest of a job (the paint, cut-down, unwrap, glTF export) runs on the processor beside the other jobs. A
job's outputs are its own call's, the same as on a card of its own: the locks only order the calls.
"""
import contextlib
import fcntl
import time

LOCK = "/root/card.lock"
# The operators that put work on the card (bpy.ops.<module>.<name>).
CARD_OPS = frozenset({"object.bake", "render.render", "render.opengl"})
# Card calls at once. A bake call holds the card 4 to 9 s, of which the card works about 1 s: the rest is Cycles' scene
# sync and its pixels back, about 3 cores of the processor (env1, 2026-10-28: one call at a time, the lock held 100% of
# the time with two jobs waiting, the card 17% busy, 5.6 of 24 cores). Each call adds at most 2.6 GB of card beside the
# desktop's and the jobs' resting 6.9 of 16.3 GB, so two fit (12.1 GB); three (14.7) would leave the desktop 1.6 GB.
CARD_SLOTS = 2
WAIT_SECONDS = 0.05  # between looks for a free slot while every one is held
# Where Blender 5.0 (library_setup.sh's version) loads a user's startup scripts from, for root in the container.
STARTUP = "/root/.config/blender/5.0/scripts/startup"


@contextlib.contextmanager
def card_turn(lock_path=LOCK):
    """The card for the block: an exclusive flock on the first free one of CARD_SLOTS files (`lock_path`.<slot>),
    waited for, let go when the block ends."""
    handles = [open(f"{lock_path}.{slot}", "a") for slot in range(CARD_SLOTS)]
    try:
        held = None
        while held is None:
            held = next((handle for handle in handles if took(handle)), None)
            if held is None:
                time.sleep(WAIT_SECONDS)
        try:
            yield
        finally:
            fcntl.flock(held, fcntl.LOCK_UN)
    finally:
        for handle in handles:
            handle.close()


def took(handle):
    """Whether this call got `handle`'s exclusive flock without waiting."""
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    return True


def turned(call, lock_path=LOCK):
    """An operator's __call__ that runs a card operator (CARD_OPS) inside card_turn, every other one as it was."""
    def call_in_turn(operator, *arguments, **keywords):
        if operator.idname_py() not in CARD_OPS:
            return call(operator, *arguments, **keywords)
        with card_turn(lock_path):
            return call(operator, *arguments, **keywords)

    call_in_turn.card_turn = True
    return call_in_turn


def register():
    """Blender's startup hook: bpy.ops' operator calls wrapped (turned), once."""
    import bpy

    operator = bpy.ops._BPyOpsSubModOp
    if not getattr(operator.__call__, "card_turn", False):
        operator.__call__ = turned(operator.__call__)


def unregister():
    """Nothing to undo: the wrap lasts the Blender process."""
