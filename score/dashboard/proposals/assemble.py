"""A proposal's OpenUSD stage: a place's assembly made from a branch's code and data over the store's accepted
outputs, for free, into a scratch store of its own. propose.py loads this file by path inside the branch's scratch
checkout, with that checkout first on the path, so the `score` imported here is the branch's own.

    python -c LAUNCH <tree> <this file> --place P --store <real store> --scratch <folder> --moved <moved.json> --out <result.json>

Every node the assembly reads (and the assembly itself) is taken one of three ways (HOW):

    as now                 its row is not moved by the branch and it reads nothing made here: its accepted output
    made                   a free row the branch moves, or a free node reading one made here: made into the scratch
                           store and its gates judged there (shown whatever they answer; nothing is accepted)
    needs the paid batch   a paid row, or one on pinned images, that the branch moves or that reads one made here:
                           its accepted output stands in, named so

The real store is only read. Every write the runner makes (blobs, outputs, records, judgements, the cache, locks)
lands in the scratch folder: Overlay reads through to the real objects and writes into its own root.
"""
import json
import pathlib

from score import contracts, graph
from score.graph import node_name
from score.store import Store, runtime_store

AS_NOW, MADE, PAID = "as now", "made", "needs the paid batch"
TARGET = "assembly"


class Overlay(runtime_store.FolderStore):
    """A folder store over the real store's objects: a key it holds itself is read from its own root, any other
    from the real one; every write goes into its own root."""

    def __init__(self, root, under):
        super().__init__(root)
        self.under = runtime_store.FolderStore(under)

    def path(self, key):
        own = self.root / key
        return self.under.path(key) if not own.is_file() and self.under.path(key).is_file() else own

    def keys(self, prefix):
        return sorted(set(runtime_store.FolderStore.keys(self.under, prefix)) |
                      set(runtime_store.FolderStore.keys(runtime_store.FolderStore(self.root), prefix)))

    def upload(self, source, key):
        runtime_store.FolderStore(self.root).upload(source, key)

    def write_bytes(self, key, data):
        runtime_store.FolderStore(self.root).write_bytes(key, data)


def overlay_store(real_store, scratch):
    """A Store reading the real store's objects and writing only under `scratch` (its objects, its cache)."""
    scratch = pathlib.Path(scratch)
    return Store(Overlay(scratch / "objects", pathlib.Path(real_store) / "objects"), scratch / "cache")


class ProposalRunner(graph.Runner):
    """The runner taking each node as now, made or stood in (HOW) in place of refusing one not usable."""

    def __init__(self, stages, world, store, moved):
        super().__init__(stages, world, store)
        self.moved = moved
        self.taken = {}
        self.chosen = {}
        self.worked_keys = {}

    def key(self, stage, place):
        """The node's key, worked out once (a Blocked is kept and raised again)."""
        node = node_name(stage, place)
        if node not in self.worked_keys:
            try:
                self.worked_keys[node] = super().key(stage, place)
            except graph.Blocked as block:
                self.worked_keys[node] = block
        found = self.worked_keys[node]
        if isinstance(found, graph.Blocked):
            raise found
        return found

    def usable(self, before, place, wanted, gapped=False):
        """The output this proposal takes for an earlier node (HOW), chosen once."""
        stage = self.stages[before]
        node = node_name(stage, place)
        if node not in self.chosen:
            self.chosen[node] = self.taken_output(stage, place)
        found = self.chosen[node]
        if isinstance(found, graph.Blocked):
            raise found
        return found

    def moved_by_branch(self, stage, place):
        """True when the branch moves this node's row: its code, or a file it declares for this place."""
        row = self.moved.get(stage.name)
        return bool(row) and (row["code"] or any(str(place) in places for places in row["files"].values()))

    def reads_made(self, stage, place):
        """True when a node this one reads was made here."""
        return any(self.taken.get(node_name(*read), {}).get("how") == MADE for read in self.read_nodes(stage, place))

    def taken_output(self, stage, place):
        """The node's output for this proposal, or the Blocked saying why there is none."""
        try:
            keyed, blocked = self.key(stage, place), None
        except graph.Blocked as block:
            keyed, blocked = None, block
        if not (self.moved_by_branch(stage, place) or self.reads_made(stage, place)):
            return self.stood_in(stage, place, AS_NOW)
        if stage.paid or stage.models:
            return self.stood_in(stage, place, PAID)
        return self.made(stage, place, keyed) if keyed else blocked

    def stood_in(self, stage, place, how):
        """The node's accepted output, noted as taken `how`; a Blocked when it has none."""
        node = node_name(stage, place)
        accepted = self.store.accepted(node)
        if accepted is None:
            return graph.Blocked(f"{node} has no accepted output to show ({how})")
        self.note(stage, place, how, accepted, None)
        return accepted

    def made(self, stage, place, keyed):
        """The node made on its key into the scratch store (or found made there) and judged; its output."""
        node = node_name(stage, place)
        record = self.store.record(node, keyed["key"])
        if record is None:
            try:
                record = self.make(stage, place, keyed)
            except contracts.Broken as broken:
                return graph.Blocked(f"{node}: {broken}")
        judgement = self.judge(stage, place, record)
        self.note(stage, place, MADE, record["output"], judgement)
        return record["output"]

    def note(self, stage, place, how, output, judgement):
        node = node_name(stage, place)
        self.taken[node] = {"node": node, "stage": stage.name, "how": how, "output": output, "paid": bool(stage.paid),
                            "answer": judgement["answer"] if judgement else None,
                            "gates": {name: verdict["answer"] for name, verdict in
                                      (judgement["verdicts"] if judgement else {}).items()}}


def linked(store, output, folder):
    """The output's files as links into `folder` to their stored bytes, real or scratch (read only); the folder."""
    for name, sha in store.listing(output).items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(store.objects.path(f"blobs/{sha}"))
    return folder


def assemble(runner, place, folder):
    """The place's assembly for this proposal, linked into `folder`: {assembly output, stage file, every node taken}."""
    output = runner.usable(TARGET, place, None)
    stage_folder = linked(runner.store, output, pathlib.Path(folder))
    return {"assembly": output, "stage": str(stage_folder / f"{place}.usda"),
            "taken": sorted(runner.taken.values(), key=lambda item: item["node"])}


def main(argv):
    import argparse

    from score import stages
    parser = argparse.ArgumentParser(prog="proposal assemble")
    for name in ("--place", "--store", "--scratch", "--moved", "--out", "--folder"):
        parser.add_argument(name, required=True)
    options = parser.parse_args(argv)
    store = overlay_store(options.store, options.scratch)
    Store.default = classmethod(lambda cls: store)  # a stage's own Store.default() reads and writes the same way
    world = stages.world1()
    runner = ProposalRunner(stages.STAGES, world, store, json.loads(pathlib.Path(options.moved).read_text()))
    try:
        result = assemble(runner, options.place, options.folder)
    except graph.Blocked as block:
        result = {"assembly": None, "blocked": str(block),
                  "taken": sorted(runner.taken.values(), key=lambda item: item["node"])}
    pathlib.Path(options.out).write_text(json.dumps(result, indent=1))
