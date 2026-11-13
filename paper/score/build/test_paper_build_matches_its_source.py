"""The committed paper build matches its Markdown source, and the check that says so catches every way it drifts.

The PDF and the LaTeX trees are committed so a reader never has to build them, which only works while they are
current (paper/CLAUDE.md: a change to the draft is rebuilt and committed in the same commit). The stamp
(paper/score/out/stamp.json) records a hash of every input and output; a draft edited without a rebuild, a generated file
edited by hand, a file added or removed, all fail.

The break that turns the test red (applied once each, seen red, reverted):

- a space added to paper/score/source/score.md (or any input or committed output changed) without `make paper`:
  every row fails on the repository's own check.
- `stale_reasons` returns [] once a stamp exists: the drift rows fail.

Run: PROPS_HOME=$(mktemp -d) python3 -m pytest paper/score/build/
"""

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build  # noqa: E402

DRAFT_REASON = "input changed since the last build: paper/score/source/score.md"


def copy_paper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A copy of the paper's tree, with the build module pointed at it: draft, bibliography, figures, outputs, stamp."""
    paper = tmp_path / "paper" / "score"
    for part in ("source", "figures", "out", "arxiv"):
        if (build.PAPER / part).exists():  # figures/ is optional, as in the build
            shutil.copytree(build.PAPER / part, paper / part)
    shutil.copytree(build.PAPER / "build", paper / "build", ignore=shutil.ignore_patterns("test_*", "__pycache__"))
    monkeypatch.setattr(build, "__file__", str(paper / "build" / "build.py"))
    for name, path in (("PAPER", paper), ("SOURCE", paper / "source"), ("FIGURES", paper / "figures"),
                       ("OUT", paper / "out"), ("ARXIV", paper / "arxiv"), ("DRAFT", paper / "source/score.md"),
                       ("STAMP", paper / "out/stamp.json"), ("FILTER", paper / "source/markers.lua"),
                       ("BIB", paper / "source/refs.bib"), ("CSL", paper / "source/ieee.csl")):
        monkeypatch.setattr(build, name, path)
    return paper


def drift(paper: Path, action: str, relative: str, text: str = "") -> None:
    """Change one file of the copied paper the way a careless edit would: append to it, write it, or remove it."""
    path = paper / relative
    if action == "append":
        path.write_text(path.read_text() + text)
    elif action == "write":
        path.write_text(text)
    else:
        path.unlink()


@pytest.mark.parametrize("drifts, expected", [
    pytest.param([], [], id="a faithful copy is as current as the repository"),
    pytest.param([("append", "source/score.md", "\nA sentence added without a rebuild.\n")], [DRAFT_REASON],
                 id="draft edited without a rebuild"),
    pytest.param([("append", "source/score.md", "\nA sentence added without a rebuild.\n"),
                  ("append", "out/score.tex", "% by hand\n"),
                  ("write", "arxiv/notes.tex", "left over\n"),
                  ("unlink", "out/score.pdf")],
                 [DRAFT_REASON,
                  "output added since the last build: paper/score/arxiv/notes.tex",
                  "output removed since the last build: paper/score/out/score.pdf",
                  "output changed since the last build: paper/score/out/score.tex"],  # inputs first, then by path
                 id="every drift named by role and path, and only it"),
    pytest.param([("append", "source/score.md", "\nA sentence added without a rebuild.\n"),
                  ("unlink", "out/stamp.json")],
                 ["no stamp: the paper has never been built here"], id="no stamp"),
])
def test_paper_build_matches_its_source(tmp_path, monkeypatch, drifts, expected):
    reasons = build.stale_reasons()
    assert reasons == [], "the paper is stale; run `make paper` and commit paper/:\n" + "\n".join(reasons)
    paper = copy_paper(tmp_path, monkeypatch)
    for change in drifts:
        drift(paper, *change)
    assert build.stale_reasons() == expected
