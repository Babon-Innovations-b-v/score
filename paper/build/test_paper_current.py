"""The committed paper build matches its Markdown source.

The PDF and the LaTeX trees are committed so a reader never has to build them, which only
works while they are current. This fails when the draft, the bibliography, a figure or the
build script changed without a rebuild, or when a generated file was edited by hand.

Run: python3 -m unittest discover -s paper/build    (or: make check)
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build  # noqa: E402


class PaperBuildIsCurrent(unittest.TestCase):
    def test_committed_build_matches_its_source(self):
        reasons = build.stale_reasons()
        self.assertEqual(
            reasons, [], "the paper is stale; run `make paper` and commit paper/:\n" + "\n".join(reasons)
        )


if __name__ == "__main__":
    unittest.main()
