"""A tiny environment for the dashboard's tests, written with the framework's own store calls: two places (alpha, beta)
designed in its store (concept picked, scene inventory read, plan written) over a temp data root; nodes of plan, scene-record, closeup (paid), assembly, complete and demo-film,
each with a stored output, a finish record, a judgement and the runner's automatic accept (beta's close-up fails);
one fault report, one log, a waiting worse close-up at alpha, a two-row ledger, and FakeBackend, a compute backend
that records its calls and starts nothing."""
import dataclasses
import datetime
import io
import json
import pathlib
import re

from score import graph, review, stages
from score.dashboard.launch.backend import GroupPlan, LaunchHandle, LaunchState
from score.dashboard.launch.localrun import RESULT, RESULT_STATES
from score.dashboard.state.local import LocalSource
from score.dashboard.state.models import Spend
from score.store import Store, file_hash

PLACES = ("alpha", "beta")
ROW_NAMES = ("terrain", "plan", "scene-record", "closeup", "assembly", "complete", "demo-film")
USDA = """#usda 1.0
(
    defaultPrim = "{place}"
    subLayers = [
        @./layers/edit.usda@,
        @./layers/light.usda@,
        @./layers/base.usda@
    ]
)
"""
PALETTE = ["#334455", "#ddccaa"]


def picture(colour=(40, 90, 160)):
    """A small PNG's bytes."""
    from PIL import Image
    buffer = io.BytesIO()
    Image.new("RGB", (64, 48), colour).save(buffer, "PNG")
    return buffer.getvalue()


def rows():
    """The real rows of ROW_NAMES, for every place (their own `applies` read the real world's data)."""
    by_name = {row.name: row for row in stages.STAGES}
    return tuple(dataclasses.replace(by_name[name], applies=None) for name in ROW_NAMES)


def stamp(minutes_ago):
    at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes_ago)
    return at.isoformat(timespec="microseconds")


def files_of(stage, place, tweak):
    """{relative path: bytes} of a node's output."""
    if stage == "closeup":
        return {"closeups/lamp.png": picture((200, 120 + tweak, 40)), "closeups.json": b"{}"}
    if stage == "assembly":
        return {f"{place}.usda": USDA.format(place=place).encode(), "layers/edit.usda": b"#usda 1.0\n",
                "layers/light.usda": b"#usda 1.0\n", "layers/base.usda": b"#usda 1.0\n",
                "assets/lamp_1.usdc": b"usdc"}
    if stage == "demo-film":
        return {"concept.png": picture((90, 140, 90)), "film.mp4": b"\x00\x00\x00\x18ftypmp42", "views.json": b"[]"}
    if stage == "terrain":
        return {"grounds/moon.png": picture((120, 120, 120))}
    return {f"{stage}.json": json.dumps({"stage": stage, "place": place}).encode()}


def stored(store, folder, files):
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(data)
    return store.put_tree(folder)


def made(store, work, stage, place, answer="pass", faults=0, tweak=0, minutes_ago=60):
    """One node made, judged and (when it passed and is no worse) accepted by the runner; its output."""
    node = stage if place is None else f"{stage}@{place}"
    output = stored(store, work / f"{node}-{tweak}", files_of(stage, place, tweak))
    key = f"key-{node}-{tweak}".replace("@", "-")
    finished = stamp(minutes_ago)
    store.write_record(node, key, {"node": node, "key": key, "output": output, "stage": stage, "place": place,
                                   "finished": finished, "started": finished, "minutes": 2.5 + tweak, "euros": 0,
                                   "commit": "abc123", "machine": "test", "after": {}, "files": {}})
    store.write_judgement(node, key, "e1", {
        "node": node, "key": key, "output": output, "evidence": "e1", "at": finished, "answer": answer,
        "verdicts": {"looks": {"check": "looks", "answer": answer, "reason": f"{faults} faults",
                               "measures": {"faults": faults}, "better": {"faults": "lower"}, "findings": []}}})
    review.accept_automatically(store, node, output)
    return output


@dataclasses.dataclass
class Built:
    root: pathlib.Path
    data: pathlib.Path
    store: Store
    source: LocalSource
    ledger: pathlib.Path
    outputs: dict


def data_root(root):
    """The looks and the gaps of the fixture environment (its places are its designs': no kit or plan is filed in the
    data since 2026-10-21)."""
    data = root / "data"
    (data / "definitions").mkdir(parents=True, exist_ok=True)
    (data / "places").mkdir(parents=True, exist_ok=True)
    (data / "definitions/place.json").write_text(json.dumps({
        "shared": {"is": "rules"},
        "alpha_look": {"name": "the alpha look", "scenes": ["alpha"], "style": {"text": "plain"}, "palette": PALETTE,
                       "pictures": {"do": [{"picture": "WORK/references/ref.png", "said": "this one"}]}}}))
    (data / "checks/gaps").mkdir(parents=True, exist_ok=True)
    (data / "checks/gaps/beta.json").write_text(json.dumps({"gaps": [
        {"name": "beta: no lamp model", "row": "assembly", "check": "placeholders", "reason": "next month"}]}))
    return data


def a_concept(store, data, folder, node):
    """A concept picture of `node`: its concept review draw, its bytes in the store's blobs."""
    from score.review import concepts
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{node}.png"
    path.write_bytes(picture((123, 45, 67)))  # a colour no output of the fixture has
    sha = file_hash(path)
    store.put_blob(path, sha)
    concepts.recorded(store, f"concepts/{node}/draws/2026-10-20T07-00-00.json",
                      {"place": node, "sha": sha, "name": path.name, "by": "joey",
                       "at": "2026-10-20T07:00:00+00:00"})
    return sha


def a_lost_concept(store, node):
    """A concept draw of `node` whose picture is lost (drawn on no room: an outside place then): its record only, no
    bytes in the blobs."""
    from score.review import concepts
    concepts.recorded(store, f"concepts/{node}/draws/2026-10-20T07-00-00.json",
                      {"place": node, "sha": "b" * 64, "name": f"{node}.png", "by": "joey", "room": None,
                       "at": "2026-10-20T07:00:00+00:00"})


def an_inventory_read(store, data, node, sha, at=None, size=None):
    """`node`'s concept `sha` picked (a pick record, no draw needed) and its scene inventory read from it by today's
    method (score/review/reading.py), its lamp row `size` in metres when given, and, given the data root `data`, kept
    in the design beside it, so its numbers count (CONTEXT.md "scene inventory")."""
    from score.review import concepts, reading
    if concepts.picked(store, node) != sha:
        concepts.recorded(store, f"concepts/{node}/picks/2026-10-20T09-00-00.json",
                          {"place": node, "sha": sha, "by": "joey", "at": "2026-10-20T09:00:00+00:00"})
    reading.kept(store, {"place": node, "concept": sha, "at": at or concepts.now(), "method": reading.METHOD,
                         "gaps": [], "skipped": [], "merged": [], "euros": {"total": 0.0}, "seconds": {},
                         "size": [96, 60],
                         "inventory": {"scene": node, "concept_pick": {"sha256": sha},
                                       "rows": [{"id": "r1", "name": "lamp", "noun": "lamp", "kind": "generate",
                                                 "terrain": False, "count": 2, "anchor": "floor", "where": "middle",
                                                 "boxes": [[10, 10, 20, 30], [40, 10, 50, 30]],
                                                 "box": [10, 10, 50, 30], **({"size": size} if size else {})}]}})
    if data is not None:  # kept in the design too, where the cockpit counts it
        kept_inventory(data.parent / "props", node, sha)


def kept_inventory(props, node, sha):
    """`node`'s scene inventory kept in the design where the cockpit reads it, read from its concept `sha`."""
    folder = props / "design" / "inventory"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{node}.json").write_text(json.dumps({
        "scene": node, "concept_pick": {"sha256": sha}, "rows": [{"id": "r1", "name": "lamp", "count": 2}]}))


def concept_of(store, node):
    """The sha of `node`'s picked concept, else of its newest draw, else None."""
    from score.review import concepts
    return concepts.picked(store, node) or next((draw["sha"] for draw in reversed(concepts.draws(store, node))), None)


def designed(store, node, sha, props):
    """`node`'s design done: its concept `sha` picked, its scene inventory read from it and kept in the design under
    `props` (the cockpit's home) and its plan written from that reading, so it is a place of the build (stages.places:
    no place is filed in the data since 2026-10-21)."""
    from score.review import plan_writing
    an_inventory_read(store, None, node, sha, at="2026-10-20T09:10:00+00:00")
    kept_inventory(props, node, sha)
    plan_writing.kept(store, {"place": node, "concept": sha, "reading": plan_writing.reading_at(store, node),
                              "method": plan_writing.METHOD, "by": "test", "at": "2026-10-20T09:30:00+00:00",
                              "euros": 0.0,
                              "plan": {"title": node.upper(), "w": 6.0, "d": 4.0, "height": "", "doors": [],
                                       "items": [], "rows": {}, "people": [], "gaps": []}})


def build(root, design=True):
    """The fixture environment under `root`: its data, its store (not the framework's: owner writes are allowed), its
    source and its ledger; with `design` False alpha only drawn and beta not, neither a place of the build yet."""
    root = pathlib.Path(root)
    data = data_root(root)
    props = root / "props"
    (props / "work/references").mkdir(parents=True, exist_ok=True)
    (props / "work/references/ref.png").write_bytes(picture((10, 10, 10)))
    store = Store.in_folder(root / "store")
    work = root / "work"
    outputs = {"terrain": made(store, work, "terrain", None)}
    for place in PLACES:
        for stage in ROW_NAMES[1:]:
            failing = place == "beta" and stage == "closeup"
            outputs[f"{stage}@{place}"] = made(store, work, stage, place, "fail" if failing else "pass",
                                               faults=3 if failing else 0)
    outputs["closeup@alpha waiting"] = made(store, work, "closeup", "alpha", faults=1, tweak=1, minutes_ago=5)
    (root / "store/faults").mkdir(parents=True, exist_ok=True)
    (root / "store/faults/assembly@beta.txt").write_text(
        "fault: assembly@beta (line beta, world world1)\nwhat the runner did: fresh\n"
        "why its line stopped: assembly@beta answered fail: placeholders: 2 placeholders\n")
    (root / "store/logs").mkdir(parents=True, exist_ok=True)
    (root / "store/logs/closeup@alpha.log").write_text("drew lamp\ndone\n")
    ledger = root / "ledger.jsonl"
    ledger.write_text("\n".join(json.dumps(row) for row in (
        {"ticket": "closeup@alpha key-1", "euros": 10.0, "wall_minutes": 30},
        {"ticket": "closeup@beta key-2", "euros": 12.0, "wall_minutes": 40})) + "\n")
    alpha = a_concept(store, data, root / "concepts", "alpha")
    a_lost_concept(store, "beta")
    if design:
        designed(store, "alpha", alpha, props)
        designed(store, "beta", "b" * 64, props)
    world = graph.Environment("world1", 3, {"data": str(data)})
    source = LocalSource(props, root / "dashboard", root / "web", store_root=root / "store", world=world,
                         rows=rows())
    return Built(root, data, store, source, ledger, outputs)


class FakeBackend:
    """A compute backend that records each call and starts nothing; its answers are set on the class."""

    name = "fake"
    calls = []
    spent, reserved, ceiling = 100.0, 10.0, 250.0
    paid_refused = None  # why the runner refuses paid work while the month's books are unknown
    euros = 13.67
    refusal = None
    missing = []
    ledger = None
    log_folder = None
    price_of = {"likely_euros": 10.0, "high_euros": 15.0, "likely_minutes": 30.0, "high_minutes": 45.0, "cards": 2,
                "runs": 3}
    bill = []  # [launch.backend.Billed]: the fake ledger's lines
    plan_buys = None  # [node]: what the fake plan buys, else its closeup nodes

    def plan(self, group):
        """Its plan of a group: `plan_buys`, else the close-ups the group names (a stage at each of its places, or a
        node named as the checkout's one run names each)."""
        FakeBackend.calls.append(("plan", group))
        named = sorted({stage if "@" in stage else f"{stage}@{place}" for stage in group.stages
                        for place in group.places})
        bought = self.plan_buys if self.plan_buys is not None else [node for node in named
                                                                     if node.startswith("closeup@")]
        buys = [{"node": node, "euros": self.euros, "why": "never ran", "again": False} for node in bought]
        return GroupPlan(missing=list(self.missing), buys=buys, refusal=self.refusal,
                         to_run={node: "to run: never ran" for node in named}, blocked={})

    def spend(self):
        FakeBackend.calls.append(("spend",))
        return Spend(spent=self.spent, reserved=self.reserved, ceiling=self.ceiling, as_of="2026-10-18T12:00:00+00:00",
                     paid_refused=self.paid_refused)

    def launch(self, group, jobs, rebuy_reason):
        FakeBackend.calls.append(("launch", group, jobs, rebuy_reason))
        log = pathlib.Path(FakeBackend.log_folder or "/nonexistent") / f"run-{len(FakeBackend.calls)}.log"
        if FakeBackend.log_folder:
            log.write_text("score run: started\ndetached: ok exit=0 minutes=1 log=x outputs=y\n")
        return LaunchHandle(command=["score", "run", *group.places, *group.stages], pid=None, log=str(log))

    def poll(self, handle):
        if handle.refused is not None:
            return LaunchState("refused", handle.refused)
        path = pathlib.Path(handle.log)
        last = path.read_text().splitlines()[-1] if path.is_file() else ""
        ended = RESULT.match(last)  # the run's result line, read as localrun reads it
        return LaunchState(RESULT_STATES[ended.group(1)] if ended else "running", last, last)

    def price(self, world, nodes):
        FakeBackend.calls.append(("price", world, tuple(nodes)))
        return {node: dict(self.price_of) for node in nodes}

    def ledgered(self, nodes, since):
        return [line for line in self.bill if line.node in nodes and line.started >= since]


# The clients the tests sign in and sync with.
ORIGIN = "http://127.0.0.1:8780"
TOKEN = "t" * 40
MADE = "2026-10-18T12:00:00+00:00"
SPEND = Spend(spent=100.0, reserved=10.0, ceiling=250.0, as_of=MADE)


def api(name="joey"):
    """A FastAPI test client carrying a signed-in Django session and its CSRF cookie."""
    from django.contrib.auth import get_user_model
    from django.test import Client
    from fastapi.testclient import TestClient

    from score.dashboard.site.asgi import app
    user = get_user_model().objects.create_user(name, password="a long enough password")
    pages = Client()
    pages.force_login(user)
    pages.get("/login/")  # sets the csrftoken cookie
    signed_in = TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000))
    for cookie in pages.cookies.values():
        signed_in.cookies.set(cookie.key, cookie.value)
    token = pages.cookies["csrftoken"].value if "csrftoken" in pages.cookies else ""
    signed_in.headers.update({"X-CSRFToken": token, "Origin": ORIGIN})
    return signed_in


def hosted_client():
    """The app as the hosted side runs it, reached from loopback, signed in as no one."""
    from fastapi.testclient import TestClient

    from score.dashboard.site.asgi import app
    return TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 50000))


class Answer:
    """A urlopen answer from a TestClient response."""

    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def opener_of(web):
    """A urlopen stand-in that sends client.Remote's requests to the hosted app in this process, one at a time: the
    test database is SQLite in memory with a shared cache, where a second writer is refused at once ("database table
    is locked") instead of waiting out the busy timeout as the hosted side's file database does, so the listener's
    side-by-side answers (listen.round_once) write to it in turn."""
    import threading
    import urllib.error
    one_at_a_time = threading.Lock()

    def opened(request, timeout):
        path = request.full_url.removeprefix("http://hosted")
        with one_at_a_time:
            answer = web.request(request.get_method(), path, content=request.data,
                                 headers=dict(request.header_items()))
        if answer.status_code >= 400:
            raise urllib.error.HTTPError(request.full_url, answer.status_code, answer.text, {},
                                         io.BytesIO(answer.content))
        return Answer(answer.content)
    return opened


def remote_of(web):
    """The store side's client.Remote speaking to the hosted app `web` with the sync token."""
    from score.dashboard.sync import client
    return client.Remote("http://hosted", TOKEN, opener_of(web))


def exported(world, folder, cap_mb=50):
    """The fixture environment's export built into `folder` at MADE: its manifest."""
    from score.dashboard.sync import building
    return building.build(world.source, folder, MADE, cap_mb, SPEND, world.root)


NODE = re.compile(r"\b[a-z][a-z-]+@(alpha|beta)\b")  # a node id of the fixture's places


def outside_details(html):
    """A page's visible text outside <details class="ids">, its tags and scripts dropped (owner rule: node ids only
    inside that fold)."""
    html = re.sub(r'<details class="ids">.*?</details>', "", html, flags=re.S)
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)
