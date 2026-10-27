"""Invariant of inputs.py and input_fetch.py: a job's big input goes up to the object store once, under a key that is
the sha256 of its bytes (the same files from any place give the same key, a changed file a new one), and arrives on
the machine byte for byte where the job names it; a corrupt object or an input changed after its key was taken is
refused, never stored or unpacked; whatever the store path does not bring is sent directly, so nothing stops a job
(2026-10-10: two review-page machines waited about 2 hours for inputs sent from this PC).

A folder store and a local ranged HTTP server stand in for the bucket and its signed link; no cloud. The break that
turns each red (applied once, seen red, reverted):

- test_the_key_names_the_contents_bytes: in inputs.py `add_fixed`, drop `info.mtime = 0` (the same files written at
  another time give another key).
- test_an_input_goes_up_once_under_its_key: in inputs.py `uploaded`, `if store.exists(key):` -> `if False:` (sent
  again each time it is staged).
- test_the_machine_pulls_it_in_ranges_and_unpacks_it_where_it_lay: in input_fetch.py `cached`, `if tar.exists():` ->
  `if False:` (the machine's cache is not kept for its next job).
- test_a_corrupt_object_is_refused: in input_fetch.py `cached`, `if f"{found}.tar" != name:` -> `if False:`.
- test_an_input_changed_after_its_key_was_taken_is_never_stored_under_it: in inputs.py `uploaded`, `!= key:` ->
  `== None:` (the stale tar is stored).
- test_small_or_switched_off_inputs_go_directly: in inputs.py `stage`, `if not big or os.environ.get(DIRECT):` ->
  `if not big:`.
- test_a_failed_staging_falls_back_to_sending_directly: in inputs.py `stage`, `return []` after the failure's log ->
  `return [{"path": "x"}]`.
- test_the_blender_runner_sends_directly_what_the_store_did_not_bring: in blender_cloud.py `send_inputs`, `not in
  arrived` -> `in arrived`.
- test_an_input_named_through_a_link_is_linked_at_its_named_path: in inputs.py `named_links`, `if at != target:` ->
  `if False:`.
- test_a_folder_link_on_the_way_is_one_link_up_there_so_outputs_land_where_they_come_back_from: in inputs.py
  `named_links`, `for end in range(2, len(parts) + 1):` -> `for end in [len(parts)]:` (only the file's own link, as
  before 2026-10-27); or in `link_named`, drop `rm -rf {shlex.quote(at)}`.
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
import types

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


def test_the_key_names_the_contents_bytes(tmp_path):
    import time
    first = an_input(tmp_path / "one")
    later = an_input(tmp_path / "two")
    for path in later.rglob("*"):
        os.utime(path, (time.time() - 3600, time.time() - 3600))  # the same files, written an hour apart
    assert inputs.content_key(first) == inputs.content_key(later)
    assert inputs.content_key(first) != inputs.content_key(an_input(tmp_path / "three", extra=b"!"))
    store = stores.FolderStore(tmp_path / "store")
    item = inputs.staged(store, first)
    assert item["key"] == f"inputs/{hashlib.sha256(store.read_bytes(item['key'])).hexdigest()}.tar"


def test_an_input_goes_up_once_under_its_key(tmp_path):
    store = stores.FolderStore(tmp_path / "store")
    folder = an_input(tmp_path)
    first, second = inputs.staged(store, folder), inputs.staged(store, folder)
    assert first["uploaded"] and not second["uploaded"] and first["key"] == second["key"]
    assert store.exists(first["key"]) and first["bytes"] == len(GLB) + len(JSON)
    assert not list(inputs.FOLDER.glob("*.partial"))


def test_the_machine_pulls_it_in_ranges_and_unpacks_it_where_it_lay(tmp_path, monkeypatch):
    store = stores.FolderStore(tmp_path / "store")
    item = inputs.staged(store, an_input(tmp_path / "here"))
    base, server = served(store.root)
    try:
        machine = tmp_path / "machine"
        request = {"path": str(machine / "parts"), "key": item["key"], "url": f"{base}/{item['key']}"}
        monkeypatch.setattr(input_fetch, "RANGE_SIZE", 1000)
        tar = machine / "cache" / item["key"].split("/")[1]
        tar.parent.mkdir(parents=True)
        size = input_fetch.download(request["url"], tar)
        assert len(Ranged.asked) >= 3  # in ranges, not one request
        assert size == store.size(item["key"]) and tar.read_bytes() == store.read_bytes(item["key"])
        tar.unlink()
        first, second = fetched([request], machine / "cache"), fetched([request], machine / "cache")
        assert first[0]["fetched"] and not second[0]["fetched"]  # kept in the machine's cache for its next job
        assert (machine / "parts/deep/b.json").read_text() == JSON
        assert (machine / "parts/a.glb").read_bytes() == GLB
    finally:
        server.shutdown()


def test_a_corrupt_object_is_refused(tmp_path):
    store = stores.FolderStore(tmp_path / "store")
    item = inputs.staged(store, an_input(tmp_path / "here"))
    store.path(item["key"]).write_bytes(b"not the tar")
    try:
        fetched([{"path": str(tmp_path / "machine/parts"), "key": item["key"], "url": item["url"]}],
                tmp_path / "machine/cache")
        raise AssertionError("a corrupt object was unpacked")
    except RuntimeError as refused:
        assert "came down as" in str(refused)
    assert not (tmp_path / "machine/parts").exists()


def test_an_input_changed_after_its_key_was_taken_is_never_stored_under_it(tmp_path):
    store = stores.FolderStore(tmp_path / "store")
    folder = an_input(tmp_path)
    key = inputs.content_key(folder)
    (folder / "a.glb").write_bytes(b"changed after the key was taken")
    try:
        inputs.uploaded(store, folder, key)
        raise AssertionError("a tar that no longer matches its key was stored under it")
    except ValueError:
        pass
    assert not store.exists(key)


def test_small_or_switched_off_inputs_go_directly(tmp_path, monkeypatch):
    assert inputs.big_inputs([an_input(tmp_path)]) == []  # 3008 bytes, under 8 MB
    monkeypatch.setattr(inputs, "SMALLEST", 1)
    monkeypatch.setenv(inputs.DIRECT, "1")
    assert inputs.stage(tmp_path, [an_input(tmp_path)]) == []


def test_a_failed_staging_falls_back_to_sending_directly(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(inputs, "SMALLEST", 1)
    monkeypatch.setattr(inputs, "VENV_PYTHON", pathlib.Path("/bin/false"))
    monkeypatch.delenv(inputs.DIRECT, raising=False)
    assert inputs.stage(tmp_path, [an_input(tmp_path)]) == []
    assert "sending directly" in capsys.readouterr().err


def test_the_blender_runner_sends_directly_what_the_store_did_not_bring(monkeypatch):
    sent = []
    monkeypatch.setattr(inputs, "through_store", lambda folder, host, locals_: {str(pathlib.Path("/w/parts").resolve())})
    monkeypatch.setattr(blender_cloud, "send", lambda folder, host, local: sent.append(local))
    monkeypatch.setattr(blender_cloud.batch, "say", lambda line: None)
    blender_cloud.send_inputs(pathlib.Path("/tmp"), "host", ["/w/parts", "/w/job.json"])
    assert sent == ["/w/job.json"]


def test_an_input_named_through_a_link_is_linked_at_its_named_path(tmp_path):
    """Garage's rover, named work/pixal/kit5-rover-3.glb, landed at work/pixal5/: Blender found no file (2026-10-12)."""
    (tmp_path / "pixal5").mkdir()
    (tmp_path / "pixal").mkdir()
    (tmp_path / "pixal5" / "rover.glb").write_bytes(b"model")
    (tmp_path / "pixal" / "rover.glb").symlink_to("../pixal5/rover.glb")
    (tmp_path / "pixal" / "plain.glb").write_bytes(b"model")
    found = inputs.named_links([tmp_path / "pixal" / "rover.glb", tmp_path / "pixal" / "plain.glb"])
    assert found == {str(tmp_path / "pixal" / "rover.glb"): str((tmp_path / "pixal5" / "rover.glb").resolve())}


def test_a_folder_link_on_the_way_is_one_link_up_there_so_outputs_land_where_they_come_back_from(tmp_path,
                                                                                                    monkeypatch):
    """surfaces-bake@campgrounds (2026-10-27): the frozen run's making folder was named through `<copy>.home/store`, a
    link to the store; the listing was linked file by file into a real folder up there, so the paint wrote its outputs
    into that folder and the runner, bringing back from the resolved path, found none of them in any job."""
    store = tmp_path / "home" / "store"
    making = store / "cache" / "making" / "k-1"
    making.mkdir(parents=True)
    (making / ".bake-crate.json").write_text("{}")
    copy_home = tmp_path / "frozen" / "run.home"
    copy_home.mkdir(parents=True)
    (copy_home / "store").symlink_to(store)
    named = copy_home / "store" / "cache" / "making" / "k-1"
    found = inputs.named_links([named / ".bake-crate.json", named / "labelled" / "crate", named / "made"])
    assert found == {str(copy_home / "store"): str(store.resolve())}, found
    commands = []
    monkeypatch.setitem(sys.modules, "batch", types.SimpleNamespace(
        remote=lambda folder, host, command, check: commands.append(command)))
    inputs.link_named(tmp_path, "host", [named / ".bake-crate.json"])
    # the machine as the old file links left it: a real folder where the link lies here
    (copy_home / "store").unlink()
    (named / "labelled").mkdir(parents=True)
    for _ in range(2):  # and once more with the link right: left alone
        subprocess.run(["sh", "-c", commands[0]], check=True)
    assert (copy_home / "store").is_symlink() and (named / ".bake-crate.json").samefile(making / ".bake-crate.json")
