"""Runs inside Blender: tools/blender/inside/review_models.py with each model framed whole (MARGIN), for the
demo-turntables row.

    blender -b --python score/stages/demo_turntable/turntable_models.py -- <shots.json> <out folder>

review_models.py's own 0.8 cut the long thin tools off (2026-10-14). It is run here with its frame widened rather than
edited, as other rows declare its whole folder and an edit there would move their keys.
"""
import pathlib

MARGIN = 1.05
SCRIPT = pathlib.Path(__file__).resolve().parents[3] / "tools/blender/inside/review_models.py"


def without_main_call(source):
    """review_models.py's code without its last line, the bare main() call, so its MARGIN can be set first."""
    body = source.rstrip()
    if not body.endswith("\nmain()"):
        raise SystemExit(f"{SCRIPT} no longer ends with main(); update {__file__}")
    return body[:-len("main()")]


namespace = {"__name__": "review_models", "__file__": str(SCRIPT)}
exec(compile(without_main_call(SCRIPT.read_text()), str(SCRIPT), "exec"), namespace)
namespace["MARGIN"] = MARGIN
namespace["main"]()
