"""A tiny environment for the dashboard's tests, written with the framework's own store calls: two places (alpha, beta)
from kit files in a temp data root; nodes of plan, scene-record, closeup (paid), assembly, complete and demo-film,
each with a stored output, a finish record, a judgement and the runner's automatic accept (beta's close-up fails);
one fault report, one log, a waiting worse close-up at alpha, a two-row ledger, and FakeBackend, a compute backend
that records its calls and starts nothing."""
import dataclasses
import datetime
import io
import json
import pathlib

from score import graph, review, stages
from score.dashboard.launch.backend import GroupPlan, LaunchHandle, LaunchState
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
    """The kit files, the looks, the gaps of the fixture environment."""
    data = root / "data"
    for place in PLACES:
        (data / "kit").mkdir(parents=True, exist_ok=True)
        (data / "kit" / f"{place}.json").write_text("{}")
    (data / "definitions").mkdir(parents=True, exist_ok=True)
    (data / "definitions/place.json").write_text(json.dumps({
        "shared": {"is": "rules"},
        "alpha_look": {"name": "the alpha look", "scenes": ["alpha"], "style": {"text": "plain"}, "palette": PALETTE,
                       "pictures": {"do": [{"picture": "WORK/references/ref.png", "said": "this one"}]}}}))
    (data / "checks/gaps").mkdir(parents=True, exist_ok=True)
    (data / "checks/gaps/beta.json").write_text(json.dumps({"gaps": [
        {"name": "beta: no lamp model", "row": "assembly", "check": "placeholders", "reason": "next month"}]}))
    return data


def a_concept(store, data, folder, node):
    """A concept picture of `node` in the store's blobs, named in data/places/concepts.json."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{node}.png"
    path.write_bytes(picture((123, 45, 67)))  # a colour no output of the fixture has
    sha = file_hash(path)
    store.put_blob(path, sha)
    listed = data / "places" / "concepts.json"
    listed.parent.mkdir(parents=True, exist_ok=True)
    found = json.loads(listed.read_text()) if listed.is_file() else {"concepts": {}}
    found["concepts"][node] = {"sha256": sha, "name": path.name}
    listed.write_text(json.dumps(found))
    return sha


def an_inventory_read(store, data, node, sha):
    """`node`'s concept `sha` picked (its concepts.json picture: a pick record, no draw) and its scene inventory read
    from it, so its numbers count (CONTEXT.md "scene inventory")."""
    from score.review import concepts
    concepts.recorded(store, f"concepts/{node}/picks/2026-10-20T09-00-00.json",
                      {"place": node, "sha": sha, "by": "joey", "at": "2026-10-20T09:00:00+00:00"})
    (data / "inventory").mkdir(parents=True, exist_ok=True)
    (data / "inventory" / f"{node}.json").write_text(json.dumps({
        "scene": node, "concept_pick": {"sha256": sha}, "rows": [{"id": "r1", "name": "lamp", "count": 2}]}))


def build(root):
    """The fixture environment under `root`: its data, its store (not the framework's: owner writes are allowed), its
    source and its ledger."""
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
    a_concept(store, data, root / "concepts", "alpha")  # beta's concept is lost
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
        return LaunchState("done" if last.startswith("detached: ok") else "running", last, last)

    def price(self, world, nodes):
        FakeBackend.calls.append(("price", world, tuple(nodes)))
        return {node: dict(self.price_of) for node in nodes}

    def ledgered(self, nodes, since):
        return [line for line in self.bill if line.node in nodes and line.started >= since]
