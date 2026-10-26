"""The committed paper build matches its Markdown source, and the check that says so catches every way it drifts.

The PDF and the LaTeX trees are committed so a reader never has to build them, which only works while they are
current (paper/CLAUDE.md: a change to the draft is rebuilt and committed in the same commit). The stamp
(paper/out/stamp.json) records a hash of every input and output; a draft edited without a rebuild, a generated file
edited by hand, a file added or removed, all fail.

The break that turns each test red (applied once each, seen red, reverted):

- test_the_committed_build_matches_its_source: a space added to paper/source/score.md (or any input or committed
  output changed) without `make paper`.
- test_the_check_catches_every_drift: `stale_reasons` returns [] once a stamp exists.

Run: PROPS_HOME=$(mktemp -d) python3 -m pytest paper/build/
"""

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build  # noqa: E402


def test_the_committed_build_matches_its_source():
    reasons = build.stale_reasons()
    assert reasons == [], "the paper is stale; run `make paper` and commit paper/:\n" + "\n".join(reasons)


@pytest.fixture
def paper_copy(tmp_path, monkeypatch):
    """A copy of the paper's tree, with the build module pointed at it: draft, bibliography, figures, outputs, stamp."""
    paper = tmp_path / "paper"
    for part in ("source", "figures", "out", "arxiv"):
        shutil.copytree(build.PAPER / part, paper / part)
    shutil.copytree(build.PAPER / "build", paper / "build", ignore=shutil.ignore_patterns("test_*", "__pycache__"))
    monkeypatch.setattr(build, "__file__", str(paper / "build" / "build.py"))
    for name, path in (("PAPER", paper), ("SOURCE", paper / "source"), ("FIGURES", paper / "figures"),
                       ("OUT", paper / "out"), ("ARXIV", paper / "arxiv"), ("DRAFT", paper / "source/score.md"),
                       ("STAMP", paper / "out/stamp.json"), ("FILTER", paper / "source/markers.lua"),
                       ("BIB", paper / "source/refs.bib"), ("CSL", paper / "source/ieee.csl")):
        monkeypatch.setattr(build, name, path)
    return paper


def test_the_check_catches_every_drift(paper_copy):
    """Each drift is named, by role and path, and only it."""
    assert build.stale_reasons() == []  # the copy is as current as the repository's
    with (paper_copy / "source/score.md").open("a") as draft:
        draft.write("\nA sentence added without a rebuild.\n")
    assert build.stale_reasons() == ["input changed since the last build: paper/source/score.md"]
    (paper_copy / "out/score.tex").write_text((paper_copy / "out/score.tex").read_text() + "% by hand\n")
    (paper_copy / "arxiv/notes.tex").write_text("left over\n")
    pdf = paper_copy / "out/score.pdf"
    pdf.unlink()
    assert build.stale_reasons() == ["input changed since the last build: paper/source/score.md",
                                     "output added since the last build: paper/arxiv/notes.tex",
                                     "output removed since the last build: paper/out/score.pdf",
                                     "output changed since the last build: paper/out/score.tex"]  # by path
    (paper_copy / "out/stamp.json").unlink()
    assert build.stale_reasons() == ["no stamp: the paper has never been built here"]
