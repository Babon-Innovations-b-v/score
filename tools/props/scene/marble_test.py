"""Checks for marble.py's paid calls, with the World API stubbed: nothing is sent.

Plain python: python3 tools/props/scene/marble_test.py
"""
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import marble  # noqa: E402


def refused_without_a_ticket(paid_call):
    """The Refused message `paid_call` raises with no SCORE_SPEND_TICKET set; fails when it reaches the API."""
    sent = []
    kept, ticket = marble.call, os.environ.pop(marble.compute.TICKET, None)
    marble.call = lambda *arguments: sent.append(arguments)
    try:
        paid_call()
    except marble.compute.Refused as refusal:
        return str(refusal)
    finally:
        marble.call = kept
        if ticket is not None:
            os.environ[marble.compute.TICKET] = ticket
        assert sent == [], "the World API was called outside a cleared run"
    raise AssertionError("a paid World API call ran outside a cleared run")


def test_no_world_or_painting_is_bought_outside_a_cleared_run():
    """Fault (design of 2026-10-11, section 6): generate (1,500 to 3,000 credits) and paint (80) called the World API
    for any caller, outside the runner's gate and the owner's yes."""
    out = pathlib.Path(tempfile.mkdtemp())
    world = refused_without_a_ticket(lambda: marble.generate("lab", out, marble.MODEL, None))
    painting = refused_without_a_ticket(lambda: marble.paint("lab", out, out / "depth.png", 5.0, "words", 7))
    assert "nothing rents outside a cleared run" in world and "nothing rents outside a cleared run" in painting


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("marble_test: ok")
