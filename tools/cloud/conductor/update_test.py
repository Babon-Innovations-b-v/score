"""score-update against a local origin and a local cockpit's /api/sync/pin: it follows the pin, refuses one off main,
falls back to origin/main forward only while the cockpit reports none, moves nothing while the pin cannot be read or a
uv.lock change would re-sync the .venv a live run uses, waits while score starts from the checkout, and syncs .venv
only when uv.lock moved."""
import contextlib
import http.server
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import update  # noqa: E402

GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.org", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True,
                          env={**os.environ, **GIT_ENV}).stdout.strip()


def commit(repo, name, text):
    (pathlib.Path(repo) / name).write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", name)
    return git(repo, "rev-parse", "HEAD")


TOKEN = "t" * 40


def token():
    return TOKEN


@contextlib.contextmanager
def cockpit(answer):
    """A local cockpit, its base URL: /api/sync/pin with the token answers `answer` (a dict), anything else the
    hosting proxy's own /healthz body or 401, as babon's Caddy and the token check do."""
    class Health(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            signed_in = self.headers.get("Authorization") == f"Bearer {TOKEN}"
            if self.path == "/healthz":
                body, status = json.dumps({"ok": True, "checks": [{"name": "cockpit", "ok": True}]}).encode(), 200
            elif self.path == "/api/sync/pin" and signed_in:
                body, status = json.dumps(answer).encode(), 200
            else:
                body, status = b'{"detail": "a sync needs the sync token"}', 401
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Health)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()


def setup(folder):
    """(origin, checkout, [commits on main], uv shim, its log, empty proc folder)."""
    folder = pathlib.Path(folder)
    origin = folder / "origin"
    origin.mkdir()
    git(origin, "init", "-q", "-b", "main")
    commits = [commit(origin, "uv.lock", "one"), commit(origin, "a.txt", "two"), commit(origin, "uv.lock", "three")]
    checkout = folder / "checkout"
    subprocess.run(["git", "clone", "-q", str(origin), str(checkout)], check=True, env={**os.environ, **GIT_ENV})
    git(checkout, "checkout", "-q", "--detach", commits[0])
    log = folder / "uv.log"
    uv = folder / "uv"
    uv.write_text(f"#!/bin/sh\necho \"${{UV_PROJECT_ENVIRONMENT:-}} $*\" >> {log}\n")
    uv.chmod(0o755)
    proc = folder / "proc"
    proc.mkdir()
    return origin, checkout, commits, uv, log, proc


def moved(checkout, url, uv, proc):
    """update.update with the test's uv shim, proc folder, token and a home beside them."""
    return update.update(checkout, url, uv=str(uv), proc=proc, token=token, home=proc.parent / "home")


def test_follows_the_pin_and_syncs_only_when_the_lock_moved():
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        with cockpit({"ok": True, "commit": commits[1]}) as url:
            line = moved(checkout, url, uv, proc)
        assert git(checkout, "rev-parse", "HEAD") == commits[1], line
        assert "the cockpit's pin" in line and not log.exists()
        with cockpit({"ok": True, "commit": commits[2]}) as url:
            line = moved(checkout, url, uv, proc)
        assert git(checkout, "rev-parse", "HEAD") == commits[2] and ".venv synced" in line
        assert log.read_text().split() == ["sync", "-q", "--frozen", "--group", "dashboard"]


def test_a_lock_move_syncs_the_prop_environment_once_the_move_made_it():
    """After the move (machine.json), the rows' prop environment ($PROPS_HOME/env) follows uv.lock with .venv."""
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        home = proc.parent / "home"
        home.mkdir()
        (home / "machine.json").write_text("{}")
        with cockpit({"ok": True, "commit": commits[2]}) as url:
            line = moved(checkout, url, uv, proc)
        assert "the prop environment synced" in line, line
        assert log.read_text().splitlines()[-1].split() == [str(home / "env"), "sync", "-q", "--frozen", "--no-dev",
                                                            "--project", str(checkout)]


def test_a_missing_prop_environment_is_built_with_the_checkout_unmoved():
    """The prop environment is left out of every backup: a conductor without one gets it at the next update."""
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        home = proc.parent / "home"
        home.mkdir()
        with cockpit({"ok": True, "commit": commits[0]}) as url:
            assert "prop environment" not in moved(checkout, url, uv, proc)  # before the move: the home stays empty
            (home / "machine.json").write_text("{}")
            line = moved(checkout, url, uv, proc)
            assert line.startswith("update: at ") and "the prop environment synced" in line, line
            (home / "env" / "bin").mkdir(parents=True)
            (home / "env" / "bin" / "python").write_text("")
            assert "prop environment" not in moved(checkout, url, uv, proc)
        assert len(log.read_text().splitlines()) == 1


def test_refuses_a_pin_off_main():
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        git(origin, "checkout", "-q", "-b", "side")
        side = commit(origin, "b.txt", "off main")
        git(checkout, "fetch", "-q", "origin", "side")
        with cockpit({"ok": True, "commit": side}) as url:
            line = moved(checkout, url, uv, proc)
        assert "refused" in line and git(checkout, "rev-parse", "HEAD") == commits[0]


def test_without_a_pin_follows_origin_main_forward_only():
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        with cockpit({"ok": True, "mode": "hosted"}) as url:
            line = moved(checkout, url, uv, proc)
        assert git(checkout, "rev-parse", "HEAD") == commits[2] and "origin/main" in line
        assert moved(checkout, None, uv, proc).startswith("update: at ")


def test_a_pin_that_cannot_be_read_moves_nothing():
    """A wrong token (or the proxy's /healthz body) never sends the checkout ahead of the cockpit along origin/main."""
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        with cockpit({"commit": commits[1]}) as url:
            line = update.update(checkout, url, uv=str(uv), proc=proc, token=lambda: "wrong",
                                 home=proc.parent / "home")
        assert line.startswith("update: not now, the cockpit's pin could not be read") and "401" in line
        assert git(checkout, "rev-parse", "HEAD") == commits[0]


def test_a_lock_change_waits_while_a_run_uses_the_venv():
    """A run's frozen copy links this checkout's .venv in: a uv.lock move waits for it, any other move goes on."""
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        copy = proc.parent / "home" / "frozen" / "abc123"
        copy.mkdir(parents=True)
        running = proc / "5151"
        running.mkdir()
        (running / "cmdline").write_bytes(b"/x/.venv/bin/python\0-m\0score\0run\0world1\0")
        (running / "cwd").symlink_to(copy)
        with cockpit({"commit": commits[2]}) as url:
            line = moved(checkout, url, uv, proc)
        assert "not now" in line and "5151" in line and git(checkout, "rev-parse", "HEAD") == commits[0]
        assert not log.exists()
        with cockpit({"commit": commits[1]}) as url:
            assert "->" in moved(checkout, url, uv, proc)  # a.txt only: the .venv stays as it is
        (running / "cwd").unlink()
        (running / "cwd").symlink_to(folder)  # the run ended
        with cockpit({"commit": commits[2]}) as url:
            assert ".venv synced" in moved(checkout, url, uv, proc)


def test_waits_while_score_starts_from_the_checkout():
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        starting = proc / "4242"
        starting.mkdir()
        (starting / "cmdline").write_bytes(b"/x/.venv/bin/python\0-m\0score\0run\0world1\0")
        (starting / "cwd").symlink_to(checkout)
        line = moved(checkout, None, uv, proc)
        assert "not now" in line and "4242" in line and git(checkout, "rev-parse", "HEAD") == commits[0]
        (starting / "cwd").unlink()
        (starting / "cwd").symlink_to(folder)  # a run already in its frozen copy does not hold the checkout
        assert "->" in moved(checkout, None, uv, proc)


def test_a_sync_pass_holds_back_only_a_lock_move():
    """A pass outlasts the 5-minute timer and the next starts right after it (2026-10-25: the checkout sat on an old
    commit all morning): a sync pass from the checkout lets a move go on, and holds back only one changing uv.lock."""
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        syncing = proc / "6161"
        syncing.mkdir()
        (syncing / "cmdline").write_bytes(b"/x/.venv/bin/python\0-m\0score.dashboard\0sync\0")
        (syncing / "cwd").symlink_to(checkout)
        with cockpit({"commit": commits[1]}) as url:
            assert "->" in moved(checkout, url, uv, proc) and git(checkout, "rev-parse", "HEAD") == commits[1]
        with cockpit({"commit": commits[2]}) as url:
            line = moved(checkout, url, uv, proc)
        assert "not now" in line and "6161" in line and git(checkout, "rev-parse", "HEAD") == commits[1]


def test_waits_while_the_checkout_has_changes():
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        (checkout / "uv.lock").write_text("edited")
        assert "tracked changes" in moved(checkout, None, uv, proc)


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"ok {name}")


def test_a_passs_own_update_moves_and_two_calls_take_turns():
    """The sync pass's ExecStartPre runs before its sync process exists, so it moves the checkout; a second call
    (score-update.service meanwhile) waits on the checkout's lock until the first is done."""
    import fcntl
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        assert "->" in moved(checkout, None, uv, proc)  # no sync process yet: nothing holds the checkout
        called = []
        real = update.update
        update.update = lambda repo, url: called.append(repo) or "update: at test"
        try:
            with open(checkout / ".git" / "score-update.lock", "w") as held:
                fcntl.flock(held, fcntl.LOCK_EX)
                second = threading.Thread(target=update.main, args=(["--repo", str(checkout)],))
                second.start()
                second.join(0.5)
                assert second.is_alive() and not called
            second.join(5)
        finally:
            update.update = real
        assert called == [checkout.resolve()]
