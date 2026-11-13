"""Invariant of inputs.py and input_fetch.py: a job's big input goes up to the object store once, under a key that is
the sha256 of its bytes (the same files from any place give the same key, a changed file a new one), and arrives on
the machine byte for byte where the job names it; a corrupt object or an input changed after its key was taken is
refused, never stored or unpacked; whatever the store path does not bring is sent directly, so nothing stops a job
(2026-10-10: two review-page machines waited about 2 hours for inputs sent from this PC).

A folder store and a local ranged HTTP server stand in for the bucket and its signed link; no cloud. One test,
test_inputs_arrive_intact_and_go_up_once, builds one world (a store home, a frozen run's home linked into it, a parts
folder in its making folder named through that link, a file link beside it, a ranged server over the store), drives
an input through every step (keyed, refused when changed, staged twice, pulled by two machines, refused when corrupt,
routed directly, linked at its named path) and checks each step on that world; the routing to the direct path is a
table of rows. The break that turns it red (each applied once, seen red, reverted):

- in inputs.py `add_fixed`, drop `info.mtime = 0` (the same files written at another time give another key).
- in inputs.py `uploaded`, `if store.exists(key):` -> `if False:` (sent again each time it is staged).
- in input_fetch.py `cached`, `if tar.exists():` -> `if False:` (the machine's cache is not kept for its next job).
- in input_fetch.py `cached`, `if f"{found}.tar" != name:` -> `if False:` (a corrupt object is unpacked).
- in inputs.py `uploaded`, `!= key:` -> `== None:` (the stale tar is stored).
- in inputs.py `stage`, `if not big or os.environ.get(DIRECT):` -> `if not big:` (the switched-off row stages).
- in inputs.py `stage`, `return []` after the failure's log -> `return [{"path": "x"}]` (the failed-staging row).
- in blender_cloud.py `send_inputs`, `not in arrived` -> `in arrived`.
- in inputs.py `named_links`, `if at != target:` -> `if False:` (the file link is not made at its named path).
- in inputs.py `named_links`, `for end in range(2, len(parts) + 1):` -> `for end in [len(parts)]:` (only the file's
  own link, as before 2026-10-27); or in `link_named`, drop `rm -rf {shlex.quote(at)}` (the folder link on the way
  is not one link up there, so outputs land where nothing brings them back).
"""
import hashlib
import http.server
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
import types

import pytest

HERE = pathlib.Path(__file__).resolve().parent
os.environ["PROPS_WORK"] = tempfile.mkdtemp(prefix="inputs-test-work-")  # the key memo's folder (paths.WORK): own
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "runtime"))
import blender_cloud  # noqa: E402
import input_fetch  # noqa: E402
import inputs  # noqa: E402
import store as stores  # noqa: E402

GLB = b"glb" * 1000
JSON = '{"b": 1}'


def an_input(root, extra=b""):
    """A small parts folder: two files, one in a subfolder (3008 bytes, or more with `extra`)."""
    folder = root / "parts"
    (folder / "deep").mkdir(parents=True, exist_ok=True)
    (folder / "a.glb").write_bytes(GLB + extra)
    (folder / "deep" / "b.json").write_text(JSON)
    return folder


class Ranged(http.server.BaseHTTPRequestHandler):
    """Serves the files of `root` with byte ranges, as a signed bucket link does, and counts the ranges asked."""
    root, asked = None, []

    def do_GET(self):
        data = (self.root / self.path.lstrip("/")).read_bytes()
        first, last = (int(part) for part in self.headers["Range"].split("=")[1].split("-"))
        last = min(last, len(data) - 1)
        Ranged.asked.append((first, last))
        self.send_response(206)
        self.send_header("Content-Range", f"bytes {first}-{last}/{len(data)}")
        self.send_header("Content-Length", str(last - first + 1))
        self.end_headers()
        self.wfile.write(data[first:last + 1])

    def log_message(self, *_):
        pass


def served(root):
    """A ranged server over `root` on a free port, in a thread; its base link and the server."""
    Ranged.root, Ranged.asked = root, []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Ranged)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}", server


def fetched(items, cache):
    """input_fetch.py run as the machine runs it; its JSON lines."""
    done = subprocess.run([sys.executable, str(HERE / "input_fetch.py")], capture_output=True, text=True,
                          input=json.dumps({"cache": str(cache), "items": items}))
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip().splitlines()[-1])
    return [json.loads(line) for line in done.stdout.splitlines()]


# How an input that the store path does not take goes directly: (row, SMALLEST, SCORE_INPUTS_DIRECT, says it failed).
# The staging environment is /bin/false in every row, so a row that stages at all says so.
DIRECT_ROWS = [
    ("small input, under SMALLEST", inputs.SMALLEST, None, False),
    ("switched off by SCORE_INPUTS_DIRECT", 1, "1", False),
    ("staging failed", 1, None, True),
]


def test_inputs_arrive_intact_and_go_up_once(tmp_path, monkeypatch, capsys):
    # the world: the store's home, a frozen run's home whose store is a link to it, the input in its making folder
    store_home = tmp_path / "home" / "store"
    making = store_home / "cache" / "making" / "k-1"
    making.mkdir(parents=True)
    (making / ".bake-crate.json").write_text("{}")
    folder = an_input(making)
    copy_home = tmp_path / "frozen" / "run.home"
    copy_home.mkdir(parents=True)
    (copy_home / "store").symlink_to(store_home)
    named = copy_home / "store" / "cache" / "making" / "k-1"
    # garage's rover: a file named work/pixal/rover.glb that lies at work/pixal5/ (2026-10-12), and a plain one
    (tmp_path / "pixal5").mkdir()
    (tmp_path / "pixal").mkdir()
    (tmp_path / "pixal5" / "rover.glb").write_bytes(b"model")
    (tmp_path / "pixal" / "rover.glb").symlink_to("../pixal5/rover.glb")
    (tmp_path / "pixal" / "plain.glb").write_bytes(b"model")
    store = stores.FolderStore(tmp_path / "bucket")

    # the key: the same files written an hour apart elsewhere give it, a changed file does not
    key = inputs.content_key(folder)
    later = an_input(tmp_path / "later")
    for path in later.rglob("*"):
        os.utime(path, (time.time() - 3600, time.time() - 3600))
    changed = an_input(tmp_path / "changed")
    assert inputs.content_key(later) == key and inputs.content_key(changed) == key
    (changed / "a.glb").write_bytes(GLB + b"!")
    assert inputs.content_key(changed) != key
    # a tar that no longer hashes to the key taken before the change is never stored under it
    with pytest.raises(ValueError):
        inputs.uploaded(store, changed, key)
    assert not store.exists(key)

    # staged twice (through the link, as the job names it): up once, under the sha256 of the stored bytes
    first, second = inputs.staged(store, named / "parts"), inputs.staged(store, folder)
    assert first["uploaded"] and not second["uploaded"] and first["key"] == second["key"] == key
    assert key == f"inputs/{hashlib.sha256(store.read_bytes(key)).hexdigest()}.tar"
    assert first["bytes"] == len(GLB) + len(JSON) and not list(inputs.FOLDER.glob("*.partial"))

    # a machine pulls it in ranges, byte for byte, keeps it for its next job and unpacks it where the job names it
    base, server = served(store.root)
    try:
        machine = tmp_path / "machine"
        request = {"path": str(machine / "parts"), "key": key, "url": f"{base}/{key}"}
        monkeypatch.setattr(input_fetch, "RANGE_SIZE", 1000)
        tar = machine / "cache" / key.split("/")[1]
        tar.parent.mkdir(parents=True)
        assert input_fetch.download(request["url"], tar) == store.size(key) and len(Ranged.asked) >= 3
        assert tar.read_bytes() == store.read_bytes(key)
        tar.unlink()
        pulls = fetched([request], machine / "cache"), fetched([request], machine / "cache")
        assert [pull[0]["fetched"] for pull in pulls] == [True, False]
        assert (machine / "parts/deep/b.json").read_text() == JSON and (machine / "parts/a.glb").read_bytes() == GLB
    finally:
        server.shutdown()
    # a second machine, after the object went corrupt in the store, refuses it and unpacks nothing
    store.path(key).write_bytes(b"not the tar")
    with pytest.raises(RuntimeError, match="came down as"):
        fetched([{"path": str(tmp_path / "other/parts"), "key": key, "url": first["url"]}], tmp_path / "other/cache")
    assert not (tmp_path / "other/parts").exists()

    # what the store path does not take goes directly, and a failure says so
    for row, smallest, direct, says in DIRECT_ROWS:
        with monkeypatch.context() as patched:
            patched.setattr(inputs, "SMALLEST", smallest)
            patched.setattr(inputs, "VENV_PYTHON", pathlib.Path("/bin/false"))
            patched.delenv(inputs.DIRECT, raising=False)
            if direct:
                patched.setenv(inputs.DIRECT, direct)
            capsys.readouterr()
            assert inputs.stage(tmp_path, [folder]) == [], row
            assert ("sending directly" in capsys.readouterr().err) == says, row
    # and the Blender runner sends directly every input the store did not bring
    sent = []
    monkeypatch.setattr(inputs, "through_store", lambda log, host, locals_: {str(folder.resolve())})
    monkeypatch.setattr(blender_cloud, "send", lambda log, host, local: sent.append(local))
    monkeypatch.setattr(blender_cloud.batch, "say", lambda line: None)
    blender_cloud.send_inputs(tmp_path, "host", [str(named / "parts"), str(tmp_path / "job.json")])
    assert sent == [str(tmp_path / "job.json")]

    # every link on the way to a named path is one link up there: the frozen home's store folder link (so outputs
    # named through it, not there yet, land where they come back from) and the rover's file link; the plain file none
    job = [named / ".bake-crate.json", named / "labelled" / "crate", named / "made", tmp_path / "pixal" / "rover.glb",
           tmp_path / "pixal" / "plain.glb"]
    assert inputs.named_links(job) == {str(copy_home / "store"): str(store_home.resolve()),
                                       str(tmp_path / "pixal" / "rover.glb"):
                                       str((tmp_path / "pixal5" / "rover.glb").resolve())}
    commands = []
    monkeypatch.setitem(sys.modules, "batch", types.SimpleNamespace(
        remote=lambda log, host, command, check: commands.append(command)))
    inputs.link_named(tmp_path, "host", job)
    # the machine as the old file links left it: a real folder where the folder link lies here, the file link gone
    (copy_home / "store").unlink()
    (named / "labelled").mkdir(parents=True)
    (tmp_path / "pixal" / "rover.glb").unlink()
    for _ in range(2):  # and once more with the links right: left alone
        subprocess.run(["sh", "-c", commands[0]], check=True)
    assert (copy_home / "store").is_symlink() and (named / ".bake-crate.json").samefile(making / ".bake-crate.json")
    assert (tmp_path / "pixal" / "rover.glb").read_bytes() == b"model"
