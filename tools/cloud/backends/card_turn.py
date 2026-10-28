"""This PC's card one Blender call at a time, while several Blender jobs share its machine (backends/local.py
RUNS_AT_ONCE; env1, 2026-10-28: a bake row's takes ran one after another on 1 to 4 of 24 cores, the card busy in
1 s bursts and idle 86% of the time).

A Blender startup script: local.take copies it into the container's Blender user startup folder (STARTUP), so every
Blender there loads it before its job's own `--python` script, a nested one too (paint_bake.py's make_chunky), and
no stage's code changes. It wraps the operators that work on the card (CARD_OPS: the Cycles bake and the renders) so
each call holds an exclusive flock on LOCK for as long as it runs and lets it go when the call returns; the rest of a
job (the paint, cut-down, unwrap, scene sync, glTF export) runs on the processor beside the other jobs. A job's
outputs are its own call's, the same as on a card of its own: the lock only orders the calls.
"""
import contextlib
import fcntl

LOCK = "/root/card.lock"
# The operators that put work on the card (bpy.ops.<module>.<name>).
CARD_OPS = frozenset({"object.bake", "render.render", "render.opengl"})
# Where Blender 5.0 (library_setup.sh's version) loads a user's startup scripts from, for root in the container.
STARTUP = "/root/.config/blender/5.0/scripts/startup"


@contextlib.contextmanager
def card_turn(lock_path=LOCK):
    """The card for the block alone: an exclusive flock on `lock_path`, waited for, let go when the block ends."""
    with open(lock_path, "a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


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
