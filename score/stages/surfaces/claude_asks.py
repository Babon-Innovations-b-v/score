"""The finish route's four asks answered by Claude (coordinator for the owner, 2026-10-27, after the side-by-side on the
backlog PRD #36: Claude matched or beat Gemini 3.1 Pro on each, every gate passed): finish-route-palette,
surface-library, finish-route-list and finish-route-recheck make as their own modules do, their one batch of asks sent
to the claude-code adapter (score/adapters/models/claude_code.py: Gemini's request as it was, `claude -p` with
claude-opus-5-5 on the owner's subscription, EUR 0, cached and ledgered) in place of route_ask's Batch API.

Environment 1 runs on the owner's PC (tools/cloud/this_pc.py), where Claude Code is installed. On a machine with none
(the conductor) the adapter raises NotHere, "runs on this PC", before anything is asked: the row stops, never asking
Gemini instead. body-face stays on Gemini.

The stage table (score/stages/__init__.py) wraps the ROWS' makes with `asking_claude`; nothing here imports a step's
module, so each row's code version is its own make's (the wrapper's `__wrapped__`) plus this file and the adapter, and a
change of the pinned model re-keys those four rows alone. The switch is not in scene_palette.py, scene_library.py or
surfaces/__init__.py: body_faces.py (the body-face rows) and ground-join read those.

A palette answer the palette's own reading refuses (its module's palette_of: env1 on the PC, 2026-10-27, Claude named
the shiplock's and the wreck's dirt token without adding it to their palettes) is asked once more, the answer and what
is wrong with it told (`repaired`), at EUR 0: the first answer is cached, so asking the same again gets it again.
"""
import copy
import functools
import sys

from score.adapters.models import claude_code

ROWS = ("finish-route-palette", "surface-library", "finish-route-list", "finish-route-recheck")


def asking_claude(make):
    """The make with its module's `ask` sending its bodies to the claude-code adapter, under the module's CALLER, for
    the make's own call; Gemini's `ask` put back after."""
    module = sys.modules[make.__module__]

    @functools.wraps(make)
    def made(inputs, out, seed, params):
        gemini = module.ask
        module.ask = lambda bodies: answered(bodies, module)
        try:
            return make(inputs, out, seed, params)
        finally:
            module.ask = gemini
    return made


PALETTE = "finish-route-palette"
AGAIN = ("Your answer was:\n{answer}\nIt cannot be used: {why}. Answer the whole question again, in full: every token "
         "your dirt_token or anything else names is one of your palette's tokens (add it, with its colour, when none "
         "is), and wear is one of {levels}.")


def answered(bodies, module):
    """Claude's answers to `bodies` under the module's CALLER; a palette answer its module's palette_of refuses asked
    once more (`repaired`), that answer kept whatever it is."""
    answers = claude_code.asked(bodies, module.CALLER)
    if module.CALLER != PALETTE:
        return answers
    again = {}
    for take, answer in answers.items():
        if isinstance(answer, Exception):
            continue
        levels = bodies[take]["generationConfig"]["responseSchema"]["properties"]["wear"]["enum"]
        try:
            module.palette_of(answer, levels)
        except ValueError as off:
            again[take] = repaired(bodies[take], answer, off, levels)
    return {**answers, **claude_code.asked(again, module.CALLER)} if again else answers


def repaired(body, answer, off, levels):
    """`body` with the refused answer and why after its question, in its one user turn."""
    told = copy.deepcopy(body)
    told["contents"][0]["parts"].append({"text": AGAIN.format(answer=answer, why=off, levels=", ".join(levels))})
    return told
