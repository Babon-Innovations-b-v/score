"""score-update against a local origin and a local /healthz: it follows the pin, refuses one off main, falls back to
origin/main forward only, waits while score starts from the checkout, and syncs .venv only when uv.lock moved."""
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


@contextlib.contextmanager
def cockpit(answer):
    """A local /healthz answering `answer` (a dict), its base URL."""
    class Health(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps(answer).encode()
            self.send_response(200)
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
    uv.write_text(f"#!/bin/sh\necho \"$*\" >> {log}\n")
    uv.chmod(0o755)
    proc = folder / "proc"
    proc.mkdir()
    return origin, checkout, commits, uv, log, proc


def test_follows_the_pin_and_syncs_only_when_the_lock_moved():
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        with cockpit({"ok": True, "commit": commits[1]}) as url:
            line = update.update(checkout, url, uv=str(uv), proc=proc)
        assert git(checkout, "rev-parse", "HEAD") == commits[1], line
        assert "the cockpit's pin" in line and not log.exists()
        with cockpit({"ok": True, "commit": commits[2]}) as url:
            line = update.update(checkout, url, uv=str(uv), proc=proc)
        assert git(checkout, "rev-parse", "HEAD") == commits[2] and ".venv synced" in line
        assert log.read_text().split() == ["sync", "-q", "--frozen", "--group", "dashboard"]


def test_refuses_a_pin_off_main():
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        git(origin, "checkout", "-q", "-b", "side")
        side = commit(origin, "b.txt", "off main")
        git(checkout, "fetch", "-q", "origin", "side")
        with cockpit({"ok": True, "commit": side}) as url:
            line = update.update(checkout, url, uv=str(uv), proc=proc)
        assert "refused" in line and git(checkout, "rev-parse", "HEAD") == commits[0]


def test_without_a_pin_follows_origin_main_forward_only():
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        with cockpit({"ok": True, "mode": "hosted"}) as url:
            line = update.update(checkout, url, uv=str(uv), proc=proc)
        assert git(checkout, "rev-parse", "HEAD") == commits[2] and "origin/main" in line
        assert update.update(checkout, None, uv=str(uv), proc=proc).startswith("update: at ")


def test_waits_while_score_starts_from_the_checkout():
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        starting = proc / "4242"
        starting.mkdir()
        (starting / "cmdline").write_bytes(b"/x/.venv/bin/python\0-m\0score\0run\0world1\0")
        (starting / "cwd").symlink_to(checkout)
        line = update.update(checkout, None, uv=str(uv), proc=proc)
        assert "not now" in line and "4242" in line and git(checkout, "rev-parse", "HEAD") == commits[0]
        (starting / "cwd").unlink()
        (starting / "cwd").symlink_to(folder)  # a run already in its frozen copy does not hold the checkout
        assert "->" in update.update(checkout, None, uv=str(uv), proc=proc)


def test_waits_while_the_checkout_has_changes():
    with tempfile.TemporaryDirectory() as folder:
        origin, checkout, commits, uv, log, proc = setup(folder)
        (checkout / "uv.lock").write_text("edited")
        assert "tracked changes" in update.update(checkout, None, uv=str(uv), proc=proc)


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"ok {name}")
