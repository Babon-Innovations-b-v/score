"""Check job inputs through the object store without renting anything: the same files give the same key from any
run, a changed file a new one, an input goes up once however often it is staged, the machine's fetch reads it in byte
ranges from a signed link, checks it, keeps it and unpacks it where it lay, a corrupt object is refused, an input
changed after its key was taken is never stored under it, and the Blender runner sends directly whatever the store
path did not bring.

Run: .venv/bin/python tools/props/cloud/inputs_test.py   (make tests runs it)
"""
import http.server
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading

HERE = pathlib.Path(__file__).resolve().parent
os.environ["PROPS_WORK"] = tempfile.mkdtemp(prefix="inputs-test-work-")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools/cloud/runtime"))
import blender_cloud  # noqa: E402
import input_fetch  # noqa: E402
import inputs  # noqa: E402
import store as stores  # noqa: E402


def an_input(root, extra=b""):
    """A small parts folder: two files, one in a subfolder."""
    folder = root / "parts"
    (folder / "deep").mkdir(parents=True, exist_ok=True)
    (folder / "a.glb").write_bytes(b"glb" * 1000 + extra)
    (folder / "deep" / "b.json").write_text('{"b": 1}')
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
    """A ranged server over `root` on a free port, in a thread; its base link."""
    Ranged.root, Ranged.asked = root, []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Ranged)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"


def the_key_follows_the_content():
    with tempfile.TemporaryDirectory() as temporary:
        root = pathlib.Path(temporary)
        first = inputs.content_key(an_input(root / "one"))
        again = inputs.content_key(an_input(root / "two"))
        changed = inputs.content_key(an_input(root / "three", extra=b"!"))
        problems = []
        if first != again:
            problems.append("the same files in another place give another key")
        if first == changed:
            problems.append("a changed file keeps the old key")
        if not first.startswith("inputs/") or not first.endswith(".tar"):
            problems.append(f"the key is {first}")
        return problems


def an_input_goes_up_once():
    with tempfile.TemporaryDirectory() as temporary:
        root = pathlib.Path(temporary)
        store = stores.FolderStore(root / "store")
        folder = an_input(root)
        first, second = inputs.staged(store, folder), inputs.staged(store, folder)
        problems = []
        if not first["uploaded"] or second["uploaded"]:
            problems.append(f"uploaded {first['uploaded']} then {second['uploaded']}, not once")
        if first["key"] != second["key"] or not store.exists(first["key"]):
            problems.append("the staged key is not in the store")
        if first["bytes"] != 3000 + len('{"b": 1}'):
            problems.append(f"the input counts {first['bytes']} bytes")
        if list((inputs.FOLDER).glob("*.partial")):
            problems.append("a partial tar was left behind")
        return problems


def fetched(items, cache):
    """input_fetch.py run as the machine runs it; its JSON lines."""
    done = subprocess.run([sys.executable, str(HERE / "input_fetch.py")], capture_output=True, text=True,
                          input=json.dumps({"cache": str(cache), "items": items}))
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip().splitlines()[-1])
    return [json.loads(line) for line in done.stdout.splitlines()]


def the_machine_pulls_ranges_and_unpacks():
    with tempfile.TemporaryDirectory() as temporary:
        root = pathlib.Path(temporary)
        store = stores.FolderStore(root / "store")
        item = inputs.staged(store, an_input(root / "here"))
        base = served(store.root)
        machine = root / "machine"
        request = {"path": str(machine / "parts"), "key": item["key"], "url": f"{base}/{item['key']}"}
        input_fetch.RANGE_SIZE = 1000
        tar = machine / "cache" / item["key"].split("/")[1]
        tar.parent.mkdir(parents=True)
        problems = []
        size = input_fetch.download(request["url"], tar)
        if len(Ranged.asked) < 3:
            problems.append(f"the object came in {len(Ranged.asked)} requests, not in ranges")
        if size != store.size(item["key"]) or tar.read_bytes() != store.read_bytes(item["key"]):
            problems.append("the downloaded tar differs from the stored one")
        tar.unlink()
        first = fetched([request], machine / "cache")
        second = fetched([request], machine / "cache")
        if not first[0]["fetched"] or second[0]["fetched"]:
            problems.append("the machine's cache did not keep the tar for its next job")
        if (machine / "parts/deep/b.json").read_text() != '{"b": 1}' or \
                (machine / "parts/a.glb").read_bytes() != (root / "here/parts/a.glb").read_bytes():
            problems.append("the input was not unpacked where it lay")
        return problems


def a_corrupt_object_is_refused():
    with tempfile.TemporaryDirectory() as temporary:
        root = pathlib.Path(temporary)
        store = stores.FolderStore(root / "store")
        item = inputs.staged(store, an_input(root / "here"))
        store.path(item["key"]).write_bytes(b"not the tar")
        try:
            fetched([{"path": str(root / "machine/parts"), "key": item["key"], "url": item["url"]}],
                    root / "machine/cache")
        except RuntimeError as refused:
            return [] if "came down as" in str(refused) else [f"refused for another reason: {refused}"]
        return ["a corrupt object was unpacked"]


def small_or_switched_off_inputs_go_directly():
    with tempfile.TemporaryDirectory() as temporary:
        root = pathlib.Path(temporary)
        problems = []
        if inputs.big_inputs([an_input(root)]):
            problems.append("a small input is staged")
        inputs.SMALLEST = 1
        os.environ[inputs.DIRECT] = "1"
        try:
            if inputs.stage(root, [an_input(root)]):
                problems.append(f"{inputs.DIRECT}=1 still stages")
        finally:
            inputs.SMALLEST = 8 * 1024 * 1024
            del os.environ[inputs.DIRECT]
        return problems


def the_runner_sends_the_rest_directly():
    sent = []
    through, send = inputs.through_store, blender_cloud.send
    inputs.through_store = lambda folder, host, locals_: {str(pathlib.Path("/w/parts").resolve())}
    blender_cloud.send = lambda folder, host, local: sent.append(local)
    try:
        blender_cloud.send_inputs(pathlib.Path("/tmp"), "host", ["/w/parts", "/w/job.json"])
    finally:
        inputs.through_store, blender_cloud.send = through, send
    return [] if sent == ["/w/job.json"] else [f"sent directly: {sent}"]


def a_failed_staging_falls_back():
    with tempfile.TemporaryDirectory() as temporary:
        root = pathlib.Path(temporary)
        inputs.SMALLEST, python = 1, inputs.VENV_PYTHON
        inputs.VENV_PYTHON = pathlib.Path("/bin/false")
        printed = io.StringIO()
        stderr, sys.stderr = sys.stderr, printed
        try:
            found = inputs.stage(root, [an_input(root)])
        finally:
            sys.stderr = stderr
            inputs.SMALLEST, inputs.VENV_PYTHON = 8 * 1024 * 1024, python
        problems = [] if found == [] else [f"a failed staging gave {found}"]
        if "sending directly" not in printed.getvalue():
            problems.append("a failed staging was not said")
        return problems


def a_changed_input_is_not_stored_under_its_old_key():
    with tempfile.TemporaryDirectory() as temporary:
        root = pathlib.Path(temporary)
        store = stores.FolderStore(root / "store")
        folder = an_input(root)
        key = inputs.content_key(folder)
        (folder / "a.glb").write_bytes(b"changed after the key was taken")
        try:
            inputs.uploaded(store, folder, key)
        except ValueError:
            return [] if not store.exists(key) else ["the refused tar is in the store anyway"]
        return ["a tar that no longer matches its key was stored under it"]


CHECKS = (the_key_follows_the_content, an_input_goes_up_once, the_machine_pulls_ranges_and_unpacks,
          a_corrupt_object_is_refused, small_or_switched_off_inputs_go_directly, the_runner_sends_the_rest_directly,
          a_failed_staging_falls_back, a_changed_input_is_not_stored_under_its_old_key)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
