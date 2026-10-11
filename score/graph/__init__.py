"""The stage runner, in Infinigen's run_stage shape: a stage table in code, a seed per node, prerequisites, and a finish
record for every output, so a changed input reruns only what it reaches.

    runner = Runner(stages, world, store)
    runner.run(places)        # {node: what it did}: made, judged again, fresh, or blocked and why
    runner.status(places)     # {node: its state and why}, running nothing
    runner.why(node)          # the node's records back through every earlier stage it read
    runner.ticket(node)       # the node's key, only when every prerequisite passed and is accepted (paid runs)

A node is one stage for one place (`stage@place`), or for the whole world (`stage`). Its key hashes the stage's name
and grain, its computed code version (the stage's and its checks' modules and every repository module they import),
its parameters, its seed, its pinned images and models, and the key of every input: a world file's or seed folder's
content hash, or the output an earlier node passed and the owner accepted. A node whose key has a finish record is
not made again. Its gates are judged again, without remaking it, when a check's evidence changes.

Every output is checked against its stage's contract and stamped with it (score.contracts) before it is stored; one
off its contract is not stored. A node reads an earlier output only when its stamp is the schema and version the node
expects, and only when every earlier stage it reads has a finish record for its current key, a judgement on its
current evidence that passed, and the owner's accept of that very output. A rerun's new output lands beside the
accepted one and never replaces it by itself. A paid stage also needs the owner's yes to that run (spend-yes).
"""
import datetime
import json
import pathlib
import platform
import shutil
import time
from dataclasses import dataclass, field
from typing import Callable

from score import checks, contracts
from score.adapters import models
from score.graph import _code
from score.store import file_hash, listing_hash, text_hash, tree_hash

GRAINS = ("world", "place")


class Blocked(Exception):
    """A node cannot run: an input is missing, or an earlier node failed, answered unknown or is not accepted."""


@dataclass(frozen=True)
class Stage:
    """One row of the stage table.

    make(inputs, out, seed, params) writes the stage's output into the folder `out`; `inputs` maps each input's
    name to a path (a world file or seed folder in place, an earlier stage's accepted output checked out).
    contract: the output's schema, version and units (score.contracts.Contract); every stage has one.
    files: {name: path pattern}, formatted with the world's roots and {place}.
    after: {earlier stage: (schema, version) this one was written for}, the stages whose accepted output it reads.
    models: pinned image kinds whose record (image digest, model revisions) goes into the key (score.adapters.models).
    """
    name: str
    grain: str
    make: Callable
    contract: contracts.Contract
    checks: tuple = ()
    files: dict = field(default_factory=dict)
    after: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    paid: bool = False
    models: tuple = ()

    def __post_init__(self):
        if self.grain not in GRAINS:
            raise ValueError(f"stage {self.name}: grain {self.grain!r} is not one of {GRAINS}")
        if not isinstance(self.contract, contracts.Contract):
            raise TypeError(f"stage {self.name}: its output needs a contract (score.contracts), not {self.contract!r}")
        if not isinstance(self.after, dict):
            raise TypeError(f"stage {self.name}: after maps each earlier stage to the (schema, version) it expects")


@dataclass(frozen=True)
class World:
    """A world's name, its seed and the folders its file patterns name ({data}, {seeds}, ...)."""
    name: str
    seed: int
    roots: dict

    @classmethod
    def from_file(cls, path, **roots):
        """A world from its record ({"name", "seed"}), with the roots its stages' files are found under."""
        record = json.loads(pathlib.Path(path).read_text())
        return cls(record["name"], record["seed"], roots)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")


def node_seed(world_seed, stage, place):
    """The seed of one node, from the world's seed, the stage and the place: never a typed number."""
    return int(text_hash(f"{world_seed}/{stage}/{place}")[:8], 16)


def node_name(stage, place):
    return stage.name if stage.grain == "world" else f"{stage.name}@{place}"


class Runner:
    def __init__(self, stages, world, store, model_record=None):
        self.stages = {stage.name: stage for stage in stages}
        self.world = world
        self.store = store
        self.model_record = model_record or models.record
        self.code_versions = {}
        unknown = {before for stage in stages for before in stage.after} - set(self.stages)
        if unknown:
            raise ValueError(f"stages read stages the table lacks: {sorted(unknown)}")

    # --- keys --------------------------------------------------------------------------------------------------

    def code(self, stage):
        """The stage's computed code version: its make's and its checks' source files and their imports (once a run)."""
        if stage.name not in self.code_versions:
            functions = [stage.make, stage.contract.faults, *(check.judge for check in stage.checks)]
            self.code_versions[stage.name] = listing_hash(_code.code_version(functions, file_hash))
        return self.code_versions[stage.name]

    def file_path(self, stage, name, place):
        return pathlib.Path(stage.files[name].format(place=place, **self.world.roots))

    def file_keys(self, stage, place):
        """{name: content hash} of each world file or seed folder the node reads; a missing one blocks."""
        keys = {}
        for name in stage.files:
            path = self.file_path(stage, name, place)
            if not path.exists():
                raise Blocked(f"{node_name(stage, place)}: its input {name} is missing ({path})")
            keys[name] = tree_hash(path)
        return keys

    def usable(self, before, place, wanted):
        """The output of an earlier node that passed its gates on its current evidence, that the owner accepted, and
        whose stamp is the (schema, version) wanted."""
        stage = self.stages[before]
        node = node_name(stage, place)
        key = self.key(stage, place)["key"]
        record = self.store.record(node, key)
        if record is None:
            raise Blocked(f"{node} has not run on its current inputs")
        judgement = self.store.judgement(node, key, self.evidence_state(stage, record["output"]))
        if judgement is None:
            raise Blocked(f"{node} is not judged on its current evidence")
        if checks.blocks(judgement["answer"]):
            reasons = "; ".join(f"{name}: {verdict['reason']}" for name, verdict in judgement["verdicts"].items()
                                if checks.blocks(verdict["answer"]))
            raise Blocked(f"{node} answered {judgement['answer']}: {reasons}")
        accepted = self.store.accepted(node)
        if accepted != record["output"]:
            raise Blocked(f"{node}'s output {record['output'][:12]} is not accepted by the owner"
                          + (f" (accepted: {accepted[:12]})" if accepted else ""))
        try:
            contracts.expect(wanted, self.store.read_file(record["output"], contracts.STAMP), node)
        except contracts.Mismatch as mismatch:
            raise Blocked(str(mismatch)) from mismatch
        return record["output"]

    def key(self, stage, place):
        """The node's key and everything it hashes; raises Blocked when an input is missing or not usable."""
        parts = {"stage": stage.name, "grain": stage.grain, "place": place if stage.grain == "place" else None,
                 "code": self.code(stage), "contract": stage.contract.stamp_of(),
                 "expects": {before: list(wanted) for before, wanted in stage.after.items()}, "params": stage.params,
                 "seed": node_seed(self.world.seed, stage.name, place if stage.grain == "place" else None),
                 "files": self.file_keys(stage, place),
                 "after": {before: self.usable(before, place, wanted) for before, wanted in stage.after.items()},
                 "models": {kind: self.model_record(kind) for kind in stage.models}}
        return {**parts, "key": text_hash(json.dumps(parts, sort_keys=True))}

    def evidence_state(self, stage, output):
        """The hash of every check's evidence on an output ("none" for a check that needs none)."""
        state = {check.name: (self.store.evidence_hash(check.name, output) or "missing") if check.evidence else "none"
                 for check in stage.checks}
        return text_hash(json.dumps(state, sort_keys=True))

    # --- making and judging ------------------------------------------------------------------------------------

    def input_paths(self, stage, place, keyed):
        """{name: path} the stage's make reads: world files in place, earlier outputs checked out."""
        paths = {name: self.file_path(stage, name, place) for name in stage.files}
        paths.update({before: self.store.checkout(output) for before, output in keyed["after"].items()})
        return paths

    def make(self, stage, place, keyed):
        """Make the node's output, store it and write its finish record; the record."""
        node = node_name(stage, place)
        if stage.paid and self.store.spend_yes(node, keyed["key"]) is None:
            raise Blocked(f"{node} is paid and the owner has not said yes to this run ({keyed['key'][:12]})")
        out = self.store.making(keyed["key"])
        started, clock = now(), time.monotonic()
        stage.make(self.input_paths(stage, place, keyed), out, keyed["seed"], stage.params)
        if self.file_keys(stage, place) != keyed["files"]:
            raise RuntimeError(f"{node}: an input changed while it ran; nothing is stored")
        contracts.stamp(stage.contract, out)
        output = self.store.put_tree(out)
        shutil.rmtree(out)
        record = {"node": node, "key": keyed["key"], "output": output, "stage": stage.name, "place": keyed["place"],
                  "code": keyed["code"], "contract": keyed["contract"], "expects": keyed["expects"],
                  "params": keyed["params"], "seed": keyed["seed"], "files": keyed["files"], "after": keyed["after"],
                  "models": keyed["models"], **_code.git_commit(),
                  "machine": platform.node(), "started": started, "finished": now(),
                  "minutes": round((time.monotonic() - clock) / 60, 3), "euros": 0}
        self.store.write_record(node, keyed["key"], record)
        return record

    def judge(self, stage, place, record):
        """Judge a stored output with the stage's gates on their current evidence and keep the judgement."""
        output = self.store.checkout(record["output"])
        inputs = self.input_paths(stage, place, record)
        verdicts = [checks.judge(check, output, inputs, self.store.evidence_file(check.name, record["output"]))
                    for check in stage.checks]
        judgement = {"node": record["node"], "key": record["key"], "output": record["output"],
                     "evidence": self.evidence_state(stage, record["output"]), "at": now(),
                     "answer": checks.overall(verdicts), "verdicts": checks.scorecard(verdicts)}
        self.store.write_judgement(record["node"], record["key"], judgement["evidence"], judgement)
        return judgement

    def run_node(self, stage, place):
        """Make the node if its key has no record, judge it if its evidence state has no judgement; what it did."""
        try:
            keyed = self.key(stage, place)
        except Blocked as block:
            return f"blocked: {block}"
        node = node_name(stage, place)
        record = self.store.record(node, keyed["key"])
        made = record is None
        if made:
            try:
                record = self.make(stage, place, keyed)
            except Blocked as block:
                return f"blocked: {block}"
            except contracts.Broken as broken:
                return f"broken: {broken}"
        if self.store.judgement(node, keyed["key"], self.evidence_state(stage, record["output"])) is not None:
            return "fresh"
        judgement = self.judge(stage, place, record)
        return f"{'made' if made else 'judged again, output kept'}: {judgement['answer']}"

    def nodes(self, places):
        """Every (stage, place) in table order: a world stage once, a place stage once per place."""
        for stage in self.stages.values():
            for place in ([None] if stage.grain == "world" else places):
                yield stage, place

    def run(self, places):
        """Run every node in table order; {node: what it did}."""
        return {node_name(stage, place): self.run_node(stage, place) for stage, place in self.nodes(places)}

    # --- reading ---------------------------------------------------------------------------------------------

    def stale_reasons(self, stage, place, keyed):
        """Why a node's last record is not its current key: what changed, by part."""
        records = self.store.records(node_name(stage, place))
        if not records:
            return ["never ran"]
        last = records[-1]
        changed = [part for part in ("code", "contract", "expects", "params", "seed", "files", "after", "models")
                   if last.get(part) != keyed[part]]
        reasons = [f"{part} changed" for part in changed if part not in ("files", "after")]
        for part in ("files", "after"):
            if part in changed:
                reasons += [f"{name} changed" for name in sorted(set(last[part]) | set(keyed[part]))
                            if last[part].get(name) != keyed[part].get(name)]
        return reasons

    def node_status(self, stage, place):
        """One node's state, running nothing: blocked, to run (and why), to judge, or its answer and accept."""
        node = node_name(stage, place)
        try:
            keyed = self.key(stage, place)
        except Blocked as block:
            return f"blocked: {block}"
        record = self.store.record(node, keyed["key"])
        if record is None:
            return "to run: " + ", ".join(self.stale_reasons(stage, place, keyed))
        judgement = self.store.judgement(node, keyed["key"], self.evidence_state(stage, record["output"]))
        if judgement is None:
            return "to judge: its evidence changed"
        accepted = self.store.accepted(node) == record["output"]
        return f"{judgement['answer']}, {'accepted' if accepted else 'not accepted'}"

    def status(self, places):
        return {node_name(stage, place): self.node_status(stage, place) for stage, place in self.nodes(places)}

    def ticket(self, node):
        """The node's current key, for a paid run's submit: only when every prerequisite passed and is accepted."""
        stage_name, _, place = node.partition("@")
        keyed = self.key(self.stages[stage_name], place or None)
        return {"node": node, "key": keyed["key"], "after": keyed["after"]}

    def why(self, node, depth=0):
        """A node's newest record and judgement as lines, then each earlier node it read, indented."""
        stage_name, _, place = node.partition("@")
        records = self.store.records(node)
        if not records:
            return ["  " * depth + f"{node}: no finish record"]
        record = records[-1]
        judgements = self.store.judgements(node, record["key"])
        answer = judgements[-1]["answer"] if judgements else "not judged"
        accepted = self.store.accepted(node)
        lines = ["  " * depth + f"{node}: output {record['output'][:12]} {answer}, "
                 f"{'accepted' if accepted == record['output'] else 'not accepted'}; key {record['key'][:12]}, "
                 f"code {record['code'][:12]}, commit {record['commit'][:8]}, seed {record['seed']}, "
                 f"files {', '.join(f'{name} {sha[:12]}' for name, sha in record['files'].items()) or 'none'}"]
        for before in self.stages[stage_name].after:
            lines += self.why(node_name(self.stages[before], place or None), depth + 1)
        return lines
