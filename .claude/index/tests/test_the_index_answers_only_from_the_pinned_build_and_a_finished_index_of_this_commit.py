"""The code index answers only through the pinned binary and from a finished index of the commit asked about.

ONE TEST (owner 2026-11-01: one test function a file, its checks merged into the answers that matter). It walks one
session's life against scratch state: the binary it may run, the index it may answer from, the published index it may
install, the issues it carries, the server's replies, and what the cache sweep removes.

Driven as its callers drive it: `cbm_pin.verified` with fake binaries whose sha256 this test computes itself,
`cbm_index.ready` and `cbm_index.build` against a scratch git repository and a scratch cache (`CBM_CACHE_DIR`) with
the tool's indexer replaced by a stand-in that writes a `nodes` table, `cbm_fetch.fetch` through a stand-in `gh`
serving one labelled asset, `cbm_issues.answer` through a stand-in `gh` serving two issues into a scratch index in
the tool's own schema, the MCP server's `respond` and its stdio loop with JSON-RPC messages, and `cbm_clean.sweep`
over a scratch cache of known ages. No real binary runs and nothing touches the network, the real cache or the real
checkout. Each expected answer is the rule's (a sha256 is 64 hex characters; upstream v0.12.1 ships four non-Windows
tarballs; an index with no stamp, or stamped for another commit, is not an answer) or the stand-in's (issue numbers,
titles, states), never read from the code under test.

Breaks (each applied once, seen red, reverted):
- in `cbm_pin.verified`, `if not is_pinned_build(binary, build)` made `if not binary.exists()` (any file accepted).
- one `CBM_SHA256_*` line deleted from `pin.env`.
- `install_dir` returns `~/.local/bin`.
- in `cbm_index.ready`, the condition made `if not stamp:` (an index of an older commit is answered from).
- the `row_count` refusal in `cbm_index._assembled` deleted.
- in `server._called`, `"isError": False`.
- the `isinstance(arguments, dict)` refusal in `server.answer` deleted (a string as arguments ended the server).
- in `cbm_issues.answer`, `everything = _held(database, project) < len(cached["issues"])` made `everything = False`.
- in `cbm_issues.gh_unready`, `if done.returncode != 0:` made `if done.returncode == 0:`.
- in `server.answer`, `if cbm_issues.names_issues(tool, given) else ""` made `if True else ""`.
- in `cbm_fetch.rename_project`, `if qualified:` made `if False:`.
- in `cbm_fetch._check_offer`, `if not head or not is_ancestor(shared, commit, head):` made `if not head:`.
- in `cbm_clean._trees`, `if gone or now - _newest(directory, live) > IDLE_DAYS * 86400:` made `if gone:`.
- in `cbm_issues.repository`, the `_origin_repository` fallback dropped.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import cbm_clean  # noqa: E402
import cbm_fetch  # noqa: E402
import cbm_index  # noqa: E402
import cbm_issues  # noqa: E402
import cbm_pin  # noqa: E402
import server  # noqa: E402

_PLATFORMS = ("linux_amd64", "linux_arm64", "darwin_amd64", "darwin_arm64")
_HEX64 = re.compile(r"[0-9a-f]{64}")


def _fake_binary(path: pathlib.Path, version: str) -> str:
    """Write an executable that reports `version`; return its sha256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\necho 'codebase-memory-mcp {version}'\n")
    path.chmod(0o755)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(repo: pathlib.Path, *args: str) -> str:
    """Run git in the scratch repository with a fixed identity."""
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(["git", "-C", str(repo), *args], check=True, env=env,
                          capture_output=True, text=True).stdout.strip()



def _stand_in_indexer(rows: int):
    """Replaces the tool's indexer: a `nodes` table holding `rows` rows for the project."""
    def index_into(binary, root, project, env, rebuild=cbm_index.REBUILD) -> None:
        connection = sqlite3.connect(pathlib.Path(env["CBM_CACHE_DIR"]) / f"{project}.db")
        connection.execute("CREATE TABLE IF NOT EXISTS nodes (project TEXT, label TEXT, name TEXT)")
        connection.executemany("INSERT INTO nodes VALUES (?, 'File', 'a.py')", [(project,)] * rows)
        connection.commit()
        connection.close()
    return index_into


_ISSUE_PAGE = {"data": {"repository": {"issues": {"pageInfo": {"hasNextPage": False}, "nodes": [
    {"number": 10, "url": "https://github.com/o/r/issues/10", "title": "The effort", "state": "OPEN",
     "createdAt": "2026-10-01T00:00:00Z", "updatedAt": "2026-10-02T00:00:00Z", "closedAt": None,
     "body": "- [ ] first open task\n- [x] done task", "labels": {"nodes": [{"name": "PRD"}]},
     "assignees": {"nodes": [{"login": "someone"}]}, "parent": None,
     "comments": {"totalCount": 0, "nodes": []}, "latest": {"nodes": []}},
    {"number": 11, "url": "https://github.com/o/r/issues/11", "title": "A piece of it", "state": "CLOSED",
     "createdAt": "2026-10-01T00:00:00Z", "updatedAt": "2026-10-03T00:00:00Z",
     "closedAt": "2099-01-01T00:00:00Z", "body": "", "labels": {"nodes": []}, "assignees": {"nodes": []},
     "parent": {"number": 10}, "comments": {"totalCount": 0, "nodes": []}, "latest": {"nodes": []}},
]}}}}


def _issue_rows(database: pathlib.Path) -> dict:
    """Issue number to (title, properties, parent number) as the index holds them."""
    connection = sqlite3.connect(database)
    try:
        rows = {json.loads(props)["number"]: (name, json.loads(props), None) for name, props in connection.execute(
            "SELECT name, properties FROM nodes WHERE label = 'Issue'")}
        for child, parent in connection.execute(
                "SELECT c.qualified_name, p.qualified_name FROM edges e JOIN nodes c ON c.id = e.source_id "
                "JOIN nodes p ON p.id = e.target_id WHERE e.type = 'CHILD_OF'"):
            number = int(child.split(":")[1])
            rows[number] = (*rows[number][:2], int(parent.split(":")[1]))
        return rows
    finally:
        connection.close()


def _published(tmp_path: pathlib.Path, project: str, head: str) -> pathlib.Path:
    """An index in the tool's schema built as `project` for `head`, the file a publisher uploads."""
    database = tmp_path / "published.db"
    database.unlink(missing_ok=True)
    connection = sqlite3.connect(database)
    connection.executescript("""
        CREATE TABLE projects (name TEXT PRIMARY KEY, indexed_at TEXT, root_path TEXT);
        CREATE TABLE nodes (id INTEGER PRIMARY KEY, project TEXT, label TEXT, name TEXT, qualified_name TEXT);
        CREATE INDEX idx_nodes_qn ON nodes(project, qualified_name);
        CREATE TABLE store_meta (k TEXT PRIMARY KEY, v TEXT);
    """)
    connection.execute("INSERT INTO projects VALUES (?, '', '/elsewhere/repo')", (project,))
    connection.execute("INSERT INTO nodes VALUES (1, ?, 'Function', 'f', ?)", (project, f"{project}.a.f"))
    connection.execute("INSERT INTO store_meta VALUES (?, '1')", (f"fp:{project}",))
    connection.commit()
    connection.close()
    cbm_index.write_stamp(database, project, head)
    return database


def _repo(root: pathlib.Path) -> pathlib.Path:
    """A one-commit git repository at `root`."""
    root.mkdir(parents=True)
    _git(root, "init", "-q")
    (root / "a.py").write_text("x = 1\n")
    _git(root, "add", "a.py")
    _git(root, "commit", "-q", "-m", "one")
    return root.resolve()


def _commit(repo: pathlib.Path, name: str) -> str:
    """Add one file as a new commit; return the commit."""
    (repo / name).write_text("y = 2\n")
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", name)
    return _git(repo, "rev-parse", "HEAD")


def _stand_in_gh(bin_dir: pathlib.Path, body: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """A `gh` running `body`, first on PATH."""
    bin_dir.mkdir()
    (bin_dir / "gh").write_text(f"#!{sys.executable}\n{body}")
    (bin_dir / "gh").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")


def _release(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """A stand-in gh serving one release asset labelled with a commit; returns a setter for that commit."""
    served, label = tmp_path / "served", tmp_path / "label"
    served.mkdir()
    _stand_in_gh(tmp_path / "ghbin", f"""import json, shutil, sys
arguments = sys.argv[1:]
if arguments[:2] == ["release", "view"]:
    print(json.dumps({{"assets": [{{"name": "i.db.zst", "label": open({str(label)!r}).read()}}]}}))
elif arguments[:2] == ["release", "download"]:
    shutil.copy({str(served / "i.db.zst")!r}, arguments[arguments.index("-D") + 1])
else:
    sys.exit(1)
""", monkeypatch)
    # The asset is served uncompressed; what is under test is what is installed, not the codec.
    monkeypatch.setattr(cbm_fetch, "unzstd", lambda source, into: shutil.copy(source, into))

    def publish(head: str) -> None:
        shutil.copy(_published(tmp_path, "elsewhere-repo", head), served / "i.db.zst")
        label.write_text(head)
    return publish


def _issues_box(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """A checkout naming `o/r`, a stand-in gh logged in or not, and an empty index in the tool's schema."""
    root = tmp_path / "checkout"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude/project.json").write_text(json.dumps({"repo": "o/r"}))
    page = tmp_path / "page.json"
    page.write_text(json.dumps(_ISSUE_PAGE))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    _stand_in_gh(tmp_path / "bin", f"""import sys, os
if sys.argv[1:2] == ["auth"]:
    sys.exit(int(os.environ.get("FAKE_GH_AUTH", "0")))
if any("OPEN, CLOSED" in argument for argument in sys.argv):  # the live sync: nothing changed since
    print('{{"data": {{"repository": {{"issues": {{"pageInfo": {{"hasNextPage": false}}, "nodes": []}}}}}}}}')
else:
    print(open({str(page)!r}).read())
""", monkeypatch)
    database = tmp_path / "issues-cache" / "p.db"
    database.parent.mkdir()
    connection = sqlite3.connect(database)
    connection.executescript("""
        CREATE TABLE nodes (id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL, label TEXT NOT NULL,
            name TEXT NOT NULL, qualified_name TEXT NOT NULL, file_path TEXT DEFAULT '',
            start_line INTEGER DEFAULT 0, end_line INTEGER DEFAULT 0, properties TEXT DEFAULT '{}',
            UNIQUE(project, qualified_name));
        CREATE TABLE edges (id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL, source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL, type TEXT NOT NULL, properties TEXT DEFAULT '{}',
            UNIQUE(source_id, target_id, type));
        CREATE VIRTUAL TABLE nodes_fts USING fts5(name, qualified_name, label, file_path, body, content='');
    """)
    connection.close()
    return root, database


def _swept_cache(tmp_path: pathlib.Path, now: float) -> tuple[pathlib.Path, list, list, pathlib.Path]:
    """A cache of three tree indexes, two binary versions, a legacy root, leftovers and a long log.

    Returns (the cache, what the sweep must remove, what it must keep, the log).
    """
    cache, trees = tmp_path / "codebase-memory-mcp", tmp_path / "codebase-memory-mcp-trees"
    cache.mkdir()
    dead_pid = 2 ** 22 + 7  # above Linux's pid_max default, so never a live process

    def tree(name: str, root: pathlib.Path, when: float) -> pathlib.Path:
        directory = trees / name
        directory.mkdir(parents=True)
        (directory / "meta.json").write_text(json.dumps({"root": str(root)}))
        (cache / f"{name}.db").write_bytes(b"x" * 10)
        for path in (directory / "meta.json", directory, cache / f"{name}.db"):
            os.utime(path, (when, when))
        return directory

    gone = tree("gone-tree", tmp_path / "removed-worktree", now)
    idle = tree("idle-tree", tmp_path, now - 4 * 86400)
    kept = tree("kept-tree", tmp_path, now)
    pinned = cbm_pin.read()["CBM_VERSION"]
    for version in (pinned, "v0.0.1"):
        (tmp_path / "harness/cbm" / version).mkdir(parents=True)
        (tmp_path / "harness/cbm" / version / "codebase-memory-mcp").write_bytes(b"b" * 100)
    legacy = tmp_path / "legacy/cbm/v0.0.2"
    legacy.mkdir(parents=True)
    leftovers = [tmp_path / f".cbm-build.p.{dead_pid}", kept / f".work.{dead_pid}", cache / ".p.build.lock"]
    leftovers[0].mkdir()
    leftovers[1].mkdir()
    leftovers[2].write_text("")
    young = tmp_path / f".cbm-fetch.p.{dead_pid + 1}"
    young.mkdir()
    for path in leftovers:
        os.utime(path, (now - 7200, now - 7200))
    log = cache / "gaps.jsonl"
    log.write_text("".join(f'{{"n": {number}, "padding": "{"x" * 80}"}}\n' for number in range(30)))
    removed = [gone, idle, cache / "gone-tree.db", cache / "idle-tree.db", tmp_path / "harness/cbm/v0.0.1", legacy,
               *leftovers]
    return cache, removed, [kept, cache / "kept-tree.db", tmp_path / "harness/cbm" / pinned, young], log


def test_the_index_answers_only_from_the_pinned_build_and_a_finished_index_of_this_commit(
        tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setenv("CBM_CACHE_DIR", str(tmp_path / "cache"))
    path = os.environ["PATH"]

    # The binary: only the pinned build runs, every shipped platform has its pins, it lives in the cache by version.
    binary = tmp_path / "fake" / "codebase-memory-mcp"
    digest = _fake_binary(binary, "0.12.1")
    assert cbm_pin.verified(binary, cbm_pin.Build("v0.12.1", "a.tar.gz", "0" * 64, digest))
    assert not cbm_pin.verified(binary, cbm_pin.Build("v0.12.1", "a.tar.gz", "0" * 64, "f" * 64))
    assert not cbm_pin.verified(tmp_path / "missing", cbm_pin.Build("v0.12.1", "a", "0" * 64, digest))
    for key in _PLATFORMS:
        build = cbm_pin.build_for(cbm_pin.read(), key)
        assert all(part in build.asset for part in key.split("_")) and build.asset.endswith(".tar.gz"), key
        assert _HEX64.fullmatch(build.tarball_sha256) and _HEX64.fullmatch(build.sha256), key
    assert cbm_pin.binary_path("v9.9.9") == tmp_path / "harness/cbm/v9.9.9/codebase-memory-mcp"

    # The index: a build with no rows is never placed; an unstamped or older commit's index is built before answering.
    repo = _repo(tmp_path / "repo")
    monkeypatch.setattr(cbm_index, "ensure_binary", lambda: pathlib.Path("/no/binary"))
    monkeypatch.setattr(cbm_index, "index_into", _stand_in_indexer(rows=0))
    with pytest.raises(cbm_index.BuildError) as refused:
        cbm_index.build(repo, force=True)
    assert refused.value.fix == cbm_index.REBUILD
    assert not (tmp_path / "cache" / f"{cbm_index.project_for(repo)}.db").exists()
    monkeypatch.setattr(cbm_index, "index_into", _stand_in_indexer(rows=1))
    first = cbm_index.ready(repo)
    assert first.get("rebuilt") and cbm_index.stamp_of(pathlib.Path(first["path"]), first["project"]) == _git(
        repo, "rev-parse", "HEAD")
    assert not cbm_index.ready(repo).get("rebuilt")
    moved_to = _commit(repo, "b.py")
    moved = cbm_index.ready(repo)
    assert moved.get("rebuilt") and cbm_index.stamp_of(pathlib.Path(moved["path"]), moved["project"]) == moved_to

    # A published index: installed as this checkout's own only for an ancestor newer than the index here.
    fetched = _repo(tmp_path / "fetched")
    release = _release(tmp_path, monkeypatch)
    release("0" * 40)
    with pytest.raises(cbm_fetch.FetchError, match="not HEAD or an ancestor"):
        cbm_fetch.fetch(fetched, slug="o/r", tag="t", asset="i.db.zst")
    one = _git(fetched, "rev-parse", "HEAD")
    _commit(fetched, "b.py")
    release(one)
    got = cbm_fetch.fetch(fetched, slug="o/r", tag="t", asset="i.db.zst")
    project = cbm_index.project_name(fetched)
    assert got["head"] == one and got["behind"] == 1 and got["project"] == project
    connection = sqlite3.connect(got["path"])
    assert connection.execute("SELECT project, qualified_name FROM nodes").fetchall() == [(project, f"{project}.a.f")]
    assert connection.execute("SELECT root_path FROM projects").fetchall() == [(str(fetched),)]
    connection.close()
    with pytest.raises(cbm_fetch.FetchError, match="as new as"):
        cbm_fetch.fetch(fetched, slug="o/r", tag="t", asset="i.db.zst")

    # Issues: without a login they say so and name the fix; with one they land with their parent and come back after
    # a rebuild; from a stale cache they say how old; with no repository named, the GitHub origin names it.
    root, database = _issues_box(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_GH_AUTH", "1")
    said = cbm_issues.answer(database, "p", root)
    assert "not loaded" in said and "gh auth login" in said and _issue_rows(database) == {}
    monkeypatch.setenv("FAKE_GH_AUTH", "0")
    cbm_issues.status_of(cbm_issues.cache_beside(database)).unlink(missing_ok=True)
    assert "NOT" not in cbm_issues.answer(database, "p", root)
    rows = _issue_rows(database)
    assert rows[10][0] == "The effort" and rows[10][1]["state"] == "open" and rows[10][1]["is_prd"] is True
    assert rows[10][1]["open_tasks"] == "- [ ] first open task" and rows[11][1]["state"] == "closed"
    assert rows[11][2] == 10
    connection = sqlite3.connect(database)
    connection.execute("DELETE FROM nodes WHERE label = 'Issue'")
    connection.execute("DELETE FROM edges")
    connection.commit()
    connection.close()
    cbm_issues.answer(database, "p", root)
    assert set(_issue_rows(database)) == {10, 11} and _issue_rows(database)[11][2] == 10
    cbm_issues.status_of(cbm_issues.cache_beside(database)).unlink(missing_ok=True)
    monkeypatch.setenv("PATH", "/nonexistent")
    stale = cbm_issues.answer(database, "p", root)
    assert "NOT live" in stale and "minutes ago" in stale and "gh auth login" in stale
    monkeypatch.setenv("PATH", path)
    copy = tmp_path / "copy"
    (copy / ".claude").mkdir(parents=True)
    (copy / ".claude/project.json").write_text(json.dumps({"repo": ""}))
    _git(copy, "init", "-q")
    _git(copy, "remote", "add", "origin", "git@github.com:someone/my-company.git")
    assert cbm_issues.repository(copy) == "someone/my-company"

    # The server: a failed question names its cause and fix; only an issue question waits on GitHub; a malformed
    # call is answered and the stdio loop keeps reading.
    monkeypatch.setattr(cbm_index, "ready", lambda here: {"error": "no network", "fix": cbm_pin.INSTALL})
    reply = server.respond({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                            "params": {"name": "query_graph", "arguments": {"query": "MATCH (n) RETURN n"}}})
    assert reply["result"]["isError"] is True and f"fix: {cbm_pin.INSTALL}" in reply["result"]["content"][0]["text"]
    calls = []
    monkeypatch.setattr(cbm_index, "ready", lambda here: {"path": "/x/p.db", "project": "p", "head": ""})
    monkeypatch.setattr(cbm_index, "ask", lambda tool, given: {"ok": True, "result": "rows: 1"})
    monkeypatch.setattr(cbm_issues, "answer", lambda database, project, root: calls.append(project) or "rows live")
    assert server.answer("query_graph", {"query": "MATCH (i:Issue) RETURN i.number"})["issues"] == "rows live"
    assert "issues" not in server.answer("query_graph", {"query": "MATCH (f:Function) RETURN f.name"})
    assert calls == ["p"]
    lines = ['{"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "query_graph", "arguments": "x"}}',
             "[1, 2]", '{"jsonrpc": "2.0", "id": 6, "method": "ping"}']
    done = subprocess.run([sys.executable, str(pathlib.Path(server.__file__))], input="\n".join(lines) + "\n",
                          capture_output=True, text=True, timeout=30, check=False)
    assert [json.loads(line).get("id") for line in done.stdout.splitlines()] == [5, None, 6] and done.returncode == 0

    # The cache sweep: gone or idle trees, unpinned versions, dead builds' leftovers and a log's head go.
    monkeypatch.setenv("CBM_CACHE_DIR", str(tmp_path / "codebase-memory-mcp"))
    now = time.time()
    cache, removed, kept, log = _swept_cache(tmp_path, now)
    swept = {path for path, _ in cbm_clean.sweep(now, older_roots=(tmp_path / "legacy/cbm",), capped=((log, 10),))}
    assert [json.loads(line)["n"] for line in log.read_text().splitlines()] == list(range(20, 30))
    for path in removed:
        assert str(path) in swept and not path.exists(), path
    for path in kept:
        assert path.exists(), path
