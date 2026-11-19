"""tools/private_names/check.py refuses a pushed line that names a private name or a patent application number, and
passes every other line (score #142). ONE TEST: a small git repository in a temp folder, two commits; a neutral name
stands in for the private ones (its digest given as `names`), so this file names none of them.

Breaks (each applied once, seen red, reverted), in tools/private_names/check.py:
- the digests: line_fault's `in names` -> `in ()` (the stand-in name passes).
- path parts: candidates' inner loop only `parts[start:start + 1]` (a name inside a longer path passes).
- trailing dots: candidates' `joined.rstrip(".")` dropped (a name ending a sentence passes).
- the patent number: line_fault's `if PATENT.search(line):` -> `if False:`.
- only added lines: added_lines' `text.startswith("+")` -> `text.startswith((" ", "+", "-"))` (a removed line refused).
- vendor/ left out: added_lines' LEFT_OUT filter dropped.
"""
import hashlib
import subprocess
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check  # noqa: E402

STAND_IN = "acme-platform"


def git(folder, *words):
    return subprocess.run(["git", "-C", str(folder), "-c", "user.email=t@example.invalid", "-c", "user.name=t", *words],
                          check=True, capture_output=True, text=True).stdout.strip()


def test_a_private_name_or_patent_number_is_refused_and_nothing_else(tmp_path):
    names = frozenset({hashlib.sha256(STAND_IN.encode()).hexdigest()})
    assert check.NAMES and all(len(each) == 64 for each in check.NAMES)
    lines = {
        f'SHARED_PROJECT = "{STAND_IN}"': True,
        f"see {STAND_IN}.": True,
        f"the pool in {STAND_IN}/ops/pool_fallbacks": True,
        f"labels: {{'{STAND_IN.upper()}/role': 'x'}}": True,
        f"under the patent application NL{1234567}": True,
        f"{STAND_IN}-two is another name": False,
        "SHARED_PROJECT = os.environ.get('SCORE_K8S_PROJECT')": False,
        "arXiv:2607.17639; SCORE is public MIT": False,
    }
    assert {line: check.line_fault(line, names) is not None for line in lines} == lines
    git(tmp_path, "init", "-q")
    (tmp_path / "kept.py").write_text(f"OLD = '{STAND_IN}'\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "one")
    base = git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "kept.py").write_text("OLD = 'neutral'\nNEW = 1\n")
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor/third.py").write_text(f"X = '{STAND_IN}'\n")
    (tmp_path / "added.md").write_text(f"plain\nthe {STAND_IN} project\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "two")
    tip = git(tmp_path, "rev-parse", "HEAD")
    assert check.faults(base, tip, cwd=tmp_path, names=names) == [("added.md", 2, check.line_fault(STAND_IN, names))]
    assert check.faults("", base, cwd=tmp_path, names=names) == [("kept.py", 1, check.line_fault(STAND_IN, names))]
