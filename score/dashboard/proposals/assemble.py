"""A basket item's free after: a place's assembly made from main's code and data over the store's accepted outputs, for
free, into a scratch store of its own, and the inputs each paid node the item buys would be made from. make.py runs it
in a subprocess on the store's machine:

    python -m score.dashboard.proposals.assemble [--place P] --store <real store> --scratch <folder>
        --nodes <nodes.json> --out <result.json> --folder <stage folder>

Every node the assembly reads (and the assembly itself) is taken one of three ways (HOW):

    as now                 it has a record on its current key (a run would make nothing of it) and reads nothing made
                           here, or its key cannot be worked out here: its accepted output
    as now (another place) a node of another place (a claiming place's bake, a shown place's assembly): as it stands,
                           so an item stays one place's work
    made                   a free node a run would make (no record on its current key): made into the scratch store
                           and its gates judged there (shown whatever they answer; nothing is accepted)
    needs the paid batch   a paid node, or one on pinned images, a run would make: its accepted output stands in,
                           named so

The real store is only read. Every write the runner makes (blobs, outputs, records, judgements, the cache, locks)
lands in the scratch folder: Overlay reads through to the real objects and writes into its own root.
"""
import json
import pathlib
import re

from score import graph
from score.graph import node_name
from score.store import Store, runtime_store

AS_NOW, MADE, PAID = "as now", "made", "needs the paid batch"
ASSEMBLY, NEIGHBOURS = "assembly", "neighbours"
# What an input the item's details show is, by its file's ending: a picture is shown, a short text is quoted.
PICTURES = (".png", ".jpg", ".jpeg", ".webp")
TEXTS = (".txt", ".json")  # a JSON file is quoted only where it holds words (make.WORD_KEYS)
MOST_PICTURES = 8  # an input's pictures shown at most, per paid node
LONGEST_TEXT = 4000  # bytes; a longer text is named, not quoted
BOOKKEEPING = ("contract.json", "inputs.json", "origin.json")  # what the runner writes into every output
# A surface's own maps are no concept, brief, plan or shape: an input picture so named is left out.
MAPS = re.compile(r"(base_?colou?r|albedo|diffuse|normal|rough|metal|occlusion|_ao\b|emissi|height|relief|skin|"
                  r"mask|opacity|_orm\b|displace)", re.I)


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
    """The runner taking each node as now, made or stood in (HOW) in place of refusing one not usable. `real` is the
    store without the scratch overlay: what a run would make is judged against it."""

    def __init__(self, stages, world, store, real, place):
        super().__init__(stages, world, store)
        self.real = real
        self.place = place
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
        """The output this item takes for an earlier node (HOW), chosen once."""
        stage = self.stages[before]
        node = node_name(stage, place)
        if node not in self.chosen:
            self.chosen[node] = self.taken_output(stage, place)
        found = self.chosen[node]
        if isinstance(found, graph.Blocked):
            raise found
        return found

    def made_by_a_run(self, stage, place, keyed):
        """True when a run on main would make this node: the real store has no record on its current key."""
        return self.real.record(node_name(stage, place), keyed["key"]) is None

    def reads_paid(self, stage, place):
        """True when a node this one reads stands in for the paid batch."""
        return any(self.taken.get(node_name(*read), {}).get("how") == PAID for read in self.read_nodes(stage, place))

    def taken_output(self, stage, place):
        """The node's output for this item, or the Blocked saying why there is none."""
        if place not in (None, self.place):
            return self.stood_in(stage, place, AS_NOW, "another place's, shown as it stands")
        try:
            keyed = self.key(stage, place)
        except graph.Blocked as block:
            return self.stood_in(stage, place, AS_NOW, f"its key cannot be worked out here: {str(block)[:300]}")
        if not self.made_by_a_run(stage, place, keyed):
            return self.stood_in(stage, place, AS_NOW)
        if stage.paid or stage.models:
            return self.stood_in(stage, place, PAID)
        return self.made(stage, place, keyed)

    def stood_in(self, stage, place, how, why=None):
        """The node's accepted output, noted as taken `how` (and `why`); a Blocked when it has none."""
        node = node_name(stage, place)
        accepted = self.store.accepted(node)
        if accepted is None:
            return graph.Blocked(f"{node} has no accepted output to show ({how}{': ' + why if why else ''})")
        self.note(stage, place, how, accepted, None, why)
        return accepted

    def made(self, stage, place, keyed):
        """The node made on its key into the scratch store (or found made there) and judged; its output."""
        node = node_name(stage, place)
        record = self.store.record(node, keyed["key"])
        if record is None:
            try:
                record = self.make(stage, place, keyed)
            except Exception as failed:  # said on the proposal: stood in for the batch, or the reason it stops
                return self.unmade(stage, place, f"{type(failed).__name__}: {failed}")
        judgement = self.judge(stage, place, record)
        self.note(stage, place, MADE, record["output"], judgement)
        return record["output"]

    def unmade(self, stage, place, why):
        """A free node whose make failed: when it reads a node standing in for the paid batch, it cannot be made
        before that batch either, so its accepted output stands in, said why; otherwise the Blocked that stops."""
        if self.reads_paid(stage, place):
            return self.stood_in(stage, place, PAID, f"made after the paid batch (made now: {why[:300]})")
        return graph.Blocked(f"{node_name(stage, place)}: {why}")

    def note(self, stage, place, how, output, judgement, why=None):
        node = node_name(stage, place)
        self.taken[node] = {"node": node, "stage": stage.name, "how": how, "output": output, "paid": bool(stage.paid),
                            "why": why,
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


def target(runner, place):
    """The stage whose OpenUSD output the item shows: the place with its neighbours standing when a run would make that
    node again and the place has one, else its assembly."""
    shows = runner.stages.get(NEIGHBOURS)
    if not shows or (shows.applies is not None and not shows.applies(place)):
        return ASSEMBLY
    try:
        keyed = runner.key(shows, place)
    except graph.Blocked:
        return ASSEMBLY
    return NEIGHBOURS if runner.made_by_a_run(shows, place, keyed) else ASSEMBLY


def assemble(runner, place, folder):
    """The place's stage for this item (`target`), linked into `folder`: {its stage row, its output, its stage file,
    every node taken}."""
    shown = target(runner, place)
    output = runner.usable(shown, place, None)
    stage_folder = linked(runner.store, output, pathlib.Path(folder))
    return {"target": shown, "assembly": output, "stage": str(stage_folder / f"{place}.usda"),
            "taken": sorted(runner.taken.values(), key=lambda item: item["node"])}


def kind_of(name, size):
    """"picture", "text" or None (not shown) of an input file by its ending and size; a surface's map is none."""
    lowered = name.lower()
    if lowered.endswith(PICTURES):
        return None if MAPS.search(pathlib.PurePosixPath(lowered).name) else "picture"
    return "text" if lowered.endswith(TEXTS) and size <= LONGEST_TEXT else None


def output_inputs(runner, read, output):
    """[{from, how, name, path, kind}] of the pictures and short texts in one read node's output, the pictures first,
    at most MOST_PICTURES of them."""
    found = []
    for name, sha in sorted(runner.store.listing(output).items()):
        if name in BOOKKEEPING:
            continue
        path = runner.store.objects.path(f"blobs/{sha}")
        kind = kind_of(name, path.stat().st_size if path.is_file() else LONGEST_TEXT + 1)
        if kind:
            found.append({"from": read, "how": runner.taken.get(read, {}).get("how", AS_NOW), "name": name,
                          "path": str(path), "kind": kind})
    pictures = [item for item in found if item["kind"] == "picture"][:MOST_PICTURES]
    return pictures + [item for item in found if item["kind"] == "text"][:2]


def file_inputs(runner, stage, place, keyed):
    """[{from: "data", name, path, kind}] of the pictures and short texts among the environment files and folders the
    node declares (its key's `files`), at most MOST_PICTURES."""
    found = []
    for name in sorted(keyed.get("files") or {}):
        root = pathlib.Path(runner.file_path(stage, name, place))
        paths = sorted(item for item in root.rglob("*") if item.is_file()) if root.is_dir() else [root]
        for each in paths:
            kind = kind_of(each.name, each.stat().st_size) if each.is_file() else None
            if kind:
                found.append({"from": "data", "how": None, "name": f"{name}: {each.name}", "path": str(each),
                              "kind": kind})
    return found[:MOST_PICTURES]


def inputs_of(runner, node):
    """What a paid node would be made from: {reads: [{node, how}], files: [...] (output_inputs and file_inputs)}, or
    {blocked: why} when its key cannot be worked out here."""
    stage_name, _, place = node.partition("@")
    stage = runner.stages[stage_name]
    place = place or None
    try:
        keyed = runner.key(stage, place)
    except graph.Blocked as block:
        return {"blocked": str(block)[:600]}
    reads, files = [], file_inputs(runner, stage, place, keyed)
    for read_stage, read_place in runner.read_nodes(stage, place):
        read = node_name(read_stage, read_place)
        try:
            output = runner.usable(read_stage.name, read_place, None)
        except graph.Blocked:
            continue
        reads.append({"node": read, "how": runner.taken.get(read, {}).get("how", AS_NOW)})
        if read_stage.name not in (ASSEMBLY, NEIGHBOURS):  # the place's stage itself: its details show it in 3D
            files += output_inputs(runner, read, output)
    return {"reads": reads, "files": files}


def main(argv=None):
    import argparse

    from score import stages
    parser = argparse.ArgumentParser(prog="basket assemble")
    parser.add_argument("--place")
    for name in ("--store", "--scratch", "--nodes", "--out", "--folder"):
        parser.add_argument(name, required=True)
    options = parser.parse_args(argv)
    store = overlay_store(options.store, options.scratch)
    real = Store(runtime_store.FolderStore(pathlib.Path(options.store) / "objects"),
                 pathlib.Path(options.scratch) / "real-cache")
    Store.default = classmethod(lambda cls: store)  # a stage's own Store.default() reads and writes the same way
    runner = ProposalRunner(stages.STAGES, stages.world1(), store, real, options.place)
    result = {"assembly": None}
    if options.place:
        try:
            result = assemble(runner, options.place, options.folder)
        except graph.Blocked as block:
            result = {"assembly": None, "blocked": str(block)}
    result["inputs"] = {node: inputs_of(runner, node)
                        for node in json.loads(pathlib.Path(options.nodes).read_text())}
    result["taken"] = sorted(runner.taken.values(), key=lambda item: item["node"])
    pathlib.Path(options.out).write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
