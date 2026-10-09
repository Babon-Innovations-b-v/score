"""Scratch repos and stand-in tools for driving the scripts from outside, never against this machine.

Every script finds the repo from its own path, so each test copies the scripts into a fresh git
repo under tmp_path. `gh`, `claude` and the pinned binaries are replaced by small executables that
log their arguments, and HOME points at a scratch folder.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent
REAL_REPO = SCRIPTS.parents[1]

# A stand-in for gh: answers from FAKE_GH_ANSWERS (keyed by its first two arguments, or
# "graphql query" / "graphql mutation") and appends every call to FAKE_GH_LOG as one JSON line.
FAKE_GH = """#!{python}
import json, os, sys
args = sys.argv[1:]
stdin = sys.stdin.read() if "--input" in args else ""
with open(os.environ["FAKE_GH_LOG"], "a") as log:
    log.write(json.dumps({{"args": args, "stdin": stdin}}) + "\\n")
answers = json.load(open(os.environ["FAKE_GH_ANSWERS"]))
key = " ".join(args[:2])
if key == "api graphql":
    key = "graphql mutation" if "mutation" in " ".join(args) + stdin else "graphql query"
answer = answers.get(key, {{}})
sys.stdout.write(answer.get("stdout", ""))
sys.exit(answer.get("exit", 0))
"""


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def write_tool(folder, name, body):
    """Write an executable stand-in tool and return its path."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(body)
    path.chmod(0o755)
    return path


@pytest.fixture
def scratch_repo(tmp_path):
    """A git repo holding a copy of the scripts, the codebase-memory pin and a project.json."""
    repo = tmp_path / "repo"
    shutil.copytree(SCRIPTS, repo / ".claude" / "scripts", ignore=shutil.ignore_patterns("tests"))
    pin = repo / "vendor" / "codebase-memory-mcp"
    pin.mkdir(parents=True)
    shutil.copy(REAL_REPO / "vendor" / "codebase-memory-mcp" / "release.env", pin)
    (repo / "vendor" / "claude-mem").mkdir()
    (repo / ".claude" / "settings.json").write_text('{"committed": true}\n')
    (repo / ".claude" / "project.json").write_text(json.dumps({"repo": "acme/widget"}) + "\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "remote", "add", "origin", "git@github.com:acme/widget.git")
    return repo


@pytest.fixture
def fake_gh(tmp_path):
    """Put the gh stand-in first on PATH; returns (set answers, read the logged calls)."""
    answers = tmp_path / "gh-answers.json"
    log = tmp_path / "gh-log.jsonl"
    answers.write_text("{}")
    write_tool(tmp_path / "bin", "gh", FAKE_GH.format(python=sys.executable))
    env = dict(os.environ, PATH=f"{tmp_path / 'bin'}:{os.environ['PATH']}",
               FAKE_GH_ANSWERS=str(answers), FAKE_GH_LOG=str(log))

    def answer(by_key):
        answers.write_text(json.dumps(by_key))

    def calls():
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    return env, answer, calls
