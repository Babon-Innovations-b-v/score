"""The free-only restore of a lost store (#13): the runner's own drive, made unable to spend, so that only today's keys
and today's gates decide what stands again.

    guard_free_only()                                    # this process and its children: SCORE_FREE_ONLY, no Blender
    runner = FreeRunner(stages, world, store, notes, library=library_outputs(root), checkouts=None, fetch=None)
    found = runner.drive(places, jobs=2)                 # {node: what it did}, as any drive

The old WSL disk went on 2026-10-19 with the store, the spend ledgers and the runner's keys; the bucket and the
library (score_lib, every entry's provenance naming the node, its output and the runner's key it was made under)
survived. The prop route and the method were hardened a lot since most outputs were made, so most must be made again,
and nothing old may look current:

- A paid node is never made: `cleared` raises Blocked, so a paid make (`spending`) and a paid gatherer (`gather_one`)
  are refused at the runner's own choke point, and `gatherable` leaves out the gatherers that carry euros, so their
  checks answer unknown from missing evidence (a gap, never a pass). No record is written for a refused node.
- An old paid output stands again only when its node's key today equals the key the library says it was made under,
  its bytes rebuild to that exact output hash, and today's gates pass on it (re-attached here, judged and accepted by
  the runner's own run_held). Without `fetch` (the default) such a match is only counted ("would re-attach").
- A Blender call or a paid point reached in a node (ledger.FreeOnly) blocks that node as unknown and writes no
  judgement, so no unknown caused by the guard is kept under today's evidence state; reached in a gatherer declared
  free, its evidence stays missing and the node is blocked as unknown.
- The library rows are never made: their handover pushes score_lib and writes to the bucket (LIBRARY_REFUSED).
- A re-attached output's record says nothing made it today (reattached_record).
- Nothing is written by hand: no record, judgement, evidence, accept, reject, waiver, clearance or spend yes comes from
  the bucket or the library's own accept.

Each node's process writes what it found (the key comparison, bytes downloaded) to `notes/<node>.json`, read back by
the command's summary (__main__.py).
"""
import json
import os
import pathlib
import subprocess
import sys
import time

from score import graph
from score.store import locked, tree_hash

REPO = pathlib.Path(__file__).resolve().parents[3]
for _folder in ("tools/props", "tools/props/cloud"):
    if str(REPO / _folder) not in sys.path:
        sys.path.append(str(REPO / _folder))  # appended: its modules must not shadow anyone else's
import ledger  # noqa: E402

PAID_REFUSED = "paid: refused during the restore"
HEAVY_REFUSED = "needs Blender or a paid step: unknown"
# Programs a free-only process never starts (no Blender, no bake on this PC: WSL crashed on 2026-10-19).
HEAVY_PROGRAMS = ("blender",)
LIBRARY_REFUSED = ("library handover: refused during the restore (it pushes score_lib and puts blobs in the bucket): "
                   "unknown")


def heavy_program(arguments, executable=None):
    """The word of a Popen call (its argument list, shell string or path, and its `executable`) naming one of
    HEAVY_PROGRAMS, else None."""
    if isinstance(arguments, (str, bytes)):
        words = os.fsdecode(arguments).split()
    elif isinstance(arguments, os.PathLike):
        words = [os.fspath(arguments)]
    else:
        words = [os.fsdecode(word) if isinstance(word, bytes) else str(word) for word in arguments]
    for word in [*words, *([os.fsdecode(executable)] if executable else [])]:
        if pathlib.PurePath(word).name.lower().startswith(HEAVY_PROGRAMS):
            return word
    return None


class FreeOnlyPopen(subprocess.Popen):
    """subprocess.Popen that refuses a heavy program (ledger.FreeOnly) in a free-only process."""

    def __init__(self, arguments, *rest, **options):
        program = heavy_program(arguments, options.get("executable"))
        if program:
            raise ledger.FreeOnly(f"{program}: refused, this process runs free only ({ledger.FREE_ONLY}=1)")
        super().__init__(arguments, *rest, **options)


def guard_free_only():
    """Make this process and its children free only: SCORE_FREE_ONLY=1 for every paid point (ledger.require_books)
    and no heavy program started from it (FreeOnlyPopen). The Blender tools are guarded here, not in their own files:
    tools/review/renders.py and tools/blender are in rows' keys, so an edit there would make those rows again."""
    os.environ[ledger.FREE_ONLY] = "1"
    subprocess.Popen = FreeOnlyPopen


def provenance_outputs(provenance):
    """Every {node, output, record_key, code, library_commit, accepted_at} named in a library entry's provenance
    block, however deep. `library_commit` is the commit of the library handover that wrote the block (score_lib's
    export), not the commit that made the output, which the library does not hold; `accepted_at` is when the output
    stood accepted then, so its make finished no later."""
    found = []
    if isinstance(provenance, dict):
        if all(isinstance(provenance.get(name), str) for name in ("node", "output", "record_key")):
            found.append({**{name: provenance[name] for name in ("node", "output", "record_key")},
                          "code": provenance.get("code"), "library_commit": provenance.get("commit"),
                          "accepted_at": (provenance.get("accept") or {}).get("at")})
        for value in provenance.values():
            found += provenance_outputs(value)
    elif isinstance(provenance, list):
        for value in provenance:
            found += provenance_outputs(value)
    return found


def library_outputs(root):
    """{node: [{output, record_key, entry, code, library_commit, accepted_at}]} of every output the library at `root`
    (score_lib: entries/**/entry.json) holds with the runner's key it was made under (provenance_outputs)."""
    found = {}
    for path in sorted(pathlib.Path(root, "entries").rglob("entry.json")):
        record = json.loads(path.read_text())
        for held in provenance_outputs(record.get("provenance", {})):
            entry = {**{name: value for name, value in held.items() if name != "node"},
                     "entry": record.get("id") or str(path.relative_to(root))}
            if entry not in found.setdefault(held["node"], []):
                found[held["node"]].append(entry)
    return found


class Notes:
    """What each node's process found, one JSON file a node in `folder`, merged as it is written."""

    def __init__(self, folder):
        self.folder = pathlib.Path(folder)

    def add(self, node, **fields):
        """Merge `fields` into the node's note."""
        path = self.folder / f"{node}.json"
        self.folder.mkdir(parents=True, exist_ok=True)
        with locked(path.with_name(f"{path.name}.lock")):
            held = json.loads(path.read_text()) if path.exists() else {}
            partial = path.with_name(f"{path.name}.{os.getpid()}.partial")
            partial.write_text(json.dumps({**held, **fields}, indent=1))
            partial.replace(path)

    def read(self, node):
        """The node's note, {} when it has none."""
        path = self.folder / f"{node}.json"
        return json.loads(path.read_text()) if path.exists() else {}


class FreeRunner(graph.Runner):
    """The runner that spends nothing: paid makes and paid gatherers refused, an old paid output re-attached only on
    today's key (module docstring). `library`: library_outputs; `checkouts`: {output: {key, bytes}} of the bucket's
    checkout tars, or None when not indexed; `fetch`: a reattach.Fetch when the owner said yes to downloads, else None
    (count only)."""

    def __init__(self, stages, world, store, notes, library, checkouts=None, fetch=None, model_record=None):
        super().__init__(stages, world, store, model_record)
        self.notes, self.library, self.checkouts, self.fetch = Notes(notes), library, checkouts, fetch

    def cleared(self, node, euros):
        """Never cleared: a paid make or a paid gatherer is refused before compute is reached."""
        raise graph.Blocked(PAID_REFUSED)

    def gatherable(self, stage, place):
        """The free gatherers only: a check whose gatherer carries euros keeps its evidence missing (unknown)."""
        return [name for name in super().gatherable(stage, place) if not stage.gatherers[name][1]]

    def gather_one(self, stage, place, keyed, name, output):
        """gather_one, a gatherer declared free that still reached Blender or a paid point (ledger.FreeOnly) leaving
        its evidence missing: the node blocked as unknown, its check a gap."""
        try:
            return super().gather_one(stage, place, keyed, name, output)
        except ledger.FreeOnly as refused:
            self.notes.add(graph.node_name(stage, place), free_only=str(refused))
            raise graph.Blocked(f"{HEAVY_REFUSED} ({refused})") from refused

    def run_node(self, stage, place):
        """run_node, a node that reached Blender or a paid point blocked as unknown with nothing written for it."""
        try:
            return super().run_node(stage, place)
        except ledger.FreeOnly as refused:
            self.notes.add(graph.node_name(stage, place), free_only=str(refused))
            return f"blocked: {HEAVY_REFUSED} ({refused})"

    def make(self, stage, place, keyed):
        """A free node made as any; a paid one re-attached on today's key when allowed (paid_make), else refused; the
        library rows never: their make hands over to score_lib, which commits and pushes the library, puts blobs in
        the bucket and runs heavy hooks in processes this guard does not reach."""
        from score.stages import library  # here: the stage table imports the runner's world
        if stage.name in (library.PLACE_ROW, library.WORLD_ROW):
            raise graph.Blocked(LIBRARY_REFUSED)
        if stage.paid:
            return self.paid_make(stage, place, keyed)
        return super().make(stage, place, keyed)

    def paid_make(self, stage, place, keyed):
        """The record of a paid node's old output re-attached under today's key, when the library holds one made
        under that very key, the bucket holds a checkout of it and the owner allowed downloads; else Blocked, saying
        whether the key matches."""
        node = graph.node_name(stage, place)
        held = self.library.get(node, [])
        matching = next((entry for entry in held if entry["record_key"] == keyed["key"]), None)
        tars = (self.checkouts or {}).get(matching["output"], []) if matching else []
        self.notes.add(node, paid=True, key=keyed["key"], library_keys=[entry["record_key"] for entry in held],
                       key_matches=matching is not None, checkouts=tars)
        if matching is None:
            raise graph.Blocked(f"{PAID_REFUSED}; " + (f"the library's {len(held)} output(s) were made under older "
                                                       "keys" if held else "the library holds no output of it"))
        if not tars:
            known = "not in the bucket's checkouts" if self.checkouts is not None else "checkouts not indexed"
            raise graph.Blocked(f"{PAID_REFUSED}; key matches today, output {matching['output'][:12]} {known}")
        if self.fetch is None:
            self.notes.add(node, would_reattach=tars[0]["bytes"])
            raise graph.Blocked(f"{PAID_REFUSED}; key matches today: would re-attach {tars[0]['bytes'] / 1e9:.2f} GB")
        return self.reattached(stage, node, keyed, matching, tars)

    def reattached(self, stage, node, keyed, matching, tars):
        """Download the output's checkouts in turn, smallest first, until one rebuilds to the library's output; store
        it and write its finish record (reattached_record). Blocked when none does, or the budget or the disk stops
        a download; nothing written then."""
        started, clock = graph.now(), time.monotonic()
        for tar in tars:
            output = self.rebuilt(node, matching["output"], tar)
            if output is not None:
                self.notes.add(node, reattached=output)
                return self.write_finish(node, keyed, reattached_record(graph.finish_record(
                    node, keyed, output, stage.name, started, clock), matching, tar))
        raise graph.Blocked(f"{PAID_REFUSED}; no checkout of {matching['output'][:12]} rebuilds to its output hash "
                            f"({len(tars)} tried): nothing stored")

    def rebuilt(self, node, wanted, tar):
        """The output stored from one checkout tar when its bytes rebuild to `wanted`, else None with nothing stored;
        Blocked when the budget or the disk refuses its download."""
        with self.fetch.unpacked(tar["key"], wanted, tar["bytes"]) as folder:
            self.notes.add(node, downloaded=self.notes.read(node).get("downloaded", 0) + tar["bytes"])
            if tree_hash(folder) != wanted:
                return None
            output = self.store.put_tree(folder)
        if output != wanted:
            raise graph.Blocked(f"{PAID_REFUSED}; stored as {output[:12]}, not {wanted[:12]}: no record")
        return output


def reattached_record(made, matching, tar):
    """The finish record of a re-attached old output, from `made` (graph.finish_record, stamped now): nothing in it
    dates or names it as made today. The commit that made it is not known (the library holds its handover's commit
    only), so `commit` is None and `uncommitted` True, which every carry and proof refuses and `graph.made_by` says
    as no commit; `finished` is when the library says it stood accepted (its make ended no later), `started`, the
    machine and the minutes unknown. Today's download, its machine and minutes go under `restored`."""
    return {**made, "commit": None, "uncommitted": True, "machine": None, "started": None,
            "finished": matching.get("accepted_at") or "", "minutes": None,
            "restored": {"entry": matching["entry"], "record_key": matching["record_key"], "bucket_key": tar["key"],
                         "library_commit": matching.get("library_commit"), "at": made["finished"],
                         "machine": made["machine"], "minutes": made["minutes"]}}
