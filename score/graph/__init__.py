"""The stage runner, in Infinigen's run_stage shape: a stage table in code, a seed per node, prerequisites, and a finish
record for every output, so a changed input reruns only what it reaches.

    runner = Runner(stages, world, store)
    runner.run(places)        # {node: what it did}: made, judged again, fresh, accepted, or blocked and why
    runner.drive(places)      # every line to its end, evidence gathered; a line that stops leaves a fault report
    runner.lines(places)      # {line: (its state, {node: state})}, running nothing
    runner.status(places)     # {node: its state and why}, running nothing
    runner.why(node)          # the node's records back through every earlier stage it read
    runner.ticket(node)       # the node's key, only when every prerequisite passed and is accepted (paid runs)
    runner.stale(node)        # the earlier nodes whose accepted output moved since the node's accepted output read them

A node is one stage for one place (`stage@place`), or for the whole world (`stage`). Its key hashes the stage's name
and grain, its computed code version (the stage's and its checks' modules and every repository module they import),
its parameters, its seed, its pinned images and models, and the key of every input: a world file's or seed folder's
content hash, or an earlier node's accepted output. A node whose key has a finish record is not made again. Its gates
are judged again, without remaking it, when a check's evidence changes.

Every output is checked against its stage's contract and stamped with it (score.contracts) before it is stored; one
off its contract is not stored. A node reads an earlier output only when its stamp is the schema and version the node
expects, and only when every earlier stage it reads has a finish record for its current key, a judgement on its
current evidence that passed (or whose failed checks the owner waived for that key), and an accept of that very
output. The runner gives that accept by itself (review.accept_automatically) when the output passed, nothing got worse
than the accepted output and the owner never rejected it; otherwise the new output lands beside the accepted one and
waits for the owner. When he rejects an accepted output, its node's accepted output moves back, and every later node
whose accepted output read the rejected one is stale (`stale`, shown in status): its key now names the output
accepted before, so its next run makes (or finds) the output that reads that one.
A paid stage runs cleared by the runner (score.adapters.compute: its inputs pass and the month's ceiling has room for
its estimate, `Stage.euros`), inside that clearance's ticket.

`drive` is the runner with no agent in the loop: it runs each node, every line side by side and each node in a process
of its own, once the nodes it reads stand accepted, gathers a check's missing evidence itself (`Stage.gatherers`, a paid
one cleared like a paid stage; only when nothing else blocks the node, so nothing is spent on an output that fails
anyway), and waits on every cloud step itself. A node that does not end accepted (a gate failed or answered unknown, an
input is missing, it errored or waits for the owner) stops its own line only: the nodes after it are not run, and it
leaves a plain fault report (`faults/<node>.txt` beside the store: the node, the cause, every blocking check's reason,
measures and findings, and the tail of its log, `logs/<node>.log`) for an agent or the owner to be pointed at. A node
that stands removes its old report.
"""
import contextlib
import datetime
import json
import multiprocessing
import multiprocessing.connection
import os
import pathlib
import platform
import shutil
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Callable

from score import checks, contracts, review
from score.adapters import models
from score.graph import _code
from score.store import file_hash, listing_hash, text_hash, tree_hash

GRAINS = ("world", "place")
WORLD_LINE = "world"
LOG_TAIL = 40
# Nodes the drive runs at once: most wait on a rented machine, the rest work on this PC's cores.
JOBS = 8
# Each node runs in a forked process: its output (and its children's) goes to its own log, and the toy stages of the
# tests need no import by name. The drive itself starts no threads, so forking it is safe.
FORK = multiprocessing.get_context("fork")
FORK_WAIT = multiprocessing.connection.wait


class Blocked(Exception):
    """A node cannot run: an input is missing, or an earlier node failed, answered unknown or is not accepted."""


@dataclass(frozen=True)
class Stage:
    """One row of the stage table.

    make(inputs, out, seed, params) writes the stage's output into the folder `out`; `inputs` maps each input's
    name to a path (a world file or seed folder in place, an earlier stage's accepted output checked out).
    contract: the output's schema, version and units (score.contracts.Contract); every stage has one.
    files: {name: path pattern}, formatted with the world's roots and {place}; or a function of the place giving that
    map, for a stage whose world files differ by place (the surface stage's takes, listed in each place's data).
    after: {earlier stage: (schema, version) this one was written for}, the stages whose accepted output it reads.
    models: pinned image kinds whose record (image digest, model revisions) goes into the key (score.adapters.models).
    paid, euros: a stage that rents, and its run's estimate in euros, cleared against the month's ceiling.
    gatherers: {check name: (gather, euros or None)}, how the runner's drive makes a check's missing evidence:
    gather(output, inputs, folder) writes it and returns its file; a paid one names its estimate in euros. Kept out of
    score.checks on purpose: every stage's code version hashes that module, so a change there reruns every stage.
    applies: for a place stage, applies(place) is False for a place the stage has nothing to do for (its world data
    says so): that place's line has no such node. None: every place.
    beside, neighbours: for a place stage that reads other places' outputs, {earlier stage: (schema, version)} read
    for each place neighbours(place) names (its input `<stage>@<other place>`), versioned and waited on like `after`.
    The table refuses a stage that reads itself through what it reads, after or beside (Runner.reached); two places
    that show each other read a stage that reads nothing back, so they make no cycle.
    """
    name: str
    grain: str
    make: Callable
    contract: contracts.Contract
    checks: tuple = ()
    files: dict | Callable = field(default_factory=dict)
    after: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    paid: bool = False
    euros: float = None
    models: tuple = ()
    gatherers: dict = field(default_factory=dict)
    applies: Callable = None
    beside: dict = field(default_factory=dict)
    neighbours: Callable = None

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


@contextlib.contextmanager
def logged(path):
    """This process's and its children's output (file descriptors 1 and 2) into the log file while the block runs."""
    sys.stdout.flush()
    sys.stderr.flush()
    saved = os.dup(1), os.dup(2)
    with open(path, "w") as log:
        os.dup2(log.fileno(), 1)
        os.dup2(log.fileno(), 2)
        try:
            yield
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            for descriptor, copy in zip((1, 2), saved):
                os.dup2(copy, descriptor)
                os.close(copy)


class Runner:
    def __init__(self, stages, world, store, model_record=None):
        self.stages = {stage.name: stage for stage in stages}
        self.world = world
        self.store = store
        self.model_record = model_record or models.record
        self.code_versions = {}
        unknown = {before for stage in stages for before in (*stage.after, *stage.beside)} - set(self.stages)
        if unknown:
            raise ValueError(f"stages read stages the table lacks: {sorted(unknown)}")
        looping = sorted(name for name in self.stages if name in self.reached(name))
        if looping:
            raise ValueError(f"stages read themselves through what they read, after or beside (a cycle between "
                             f"places): {looping}")

    def reached(self, name):
        """Every stage a stage reads, after or beside, directly or through what those read. A stage graph without a
        loop has no node cycle: after is in one place, and a beside read is another place's node of a stage that
        never reads back to this one (the assembly reads the claiming place's bake beside it; neighbours reads the
        assembly beside it)."""
        found, todo = set(), list((*self.stages[name].after, *self.stages[name].beside))
        while todo:
            before = todo.pop()
            if before not in found:
                found.add(before)
                todo += [*self.stages[before].after, *self.stages[before].beside]
        return found

    # --- keys --------------------------------------------------------------------------------------------------

    def code(self, stage):
        """The stage's computed code version: its make's and its checks' source files and their imports (once a run)."""
        if stage.name not in self.code_versions:
            functions = [stage.make, stage.contract.faults, *(check.judge for check in stage.checks),
                         *([stage.files] if callable(stage.files) else []),
                         *([stage.neighbours] if stage.neighbours else [])]
            self.code_versions[stage.name] = listing_hash(_code.code_version(functions, file_hash))
        return self.code_versions[stage.name]

    def files_of(self, stage, place):
        """{name: path pattern} of the world files the node reads."""
        return stage.files(place) if callable(stage.files) else stage.files

    def file_path(self, stage, name, place):
        pattern = self.files_of(stage, place)[name]
        pattern = pattern[0] if isinstance(pattern, tuple) else pattern
        return pathlib.Path(pattern.format(place=place, **self.world.roots))

    def file_keys(self, stage, place):
        """{name: content hash} of each world file or seed folder the node reads; a missing one blocks. A file
        declared as (pattern, part) is keyed by part(path), the text of the part of it the stage reads (terrain
        reads only its ground's surfaces of the library), so a change elsewhere in the file moves no key."""
        keys = {}
        for name, pattern in self.files_of(stage, place).items():
            path = self.file_path(stage, name, place)
            if not path.exists():
                raise Blocked(f"{node_name(stage, place)}: its input {name} is missing ({path})")
            keys[name] = text_hash(pattern[1](path)) if isinstance(pattern, tuple) else tree_hash(path)
        return keys

    def usable(self, before, place, wanted):
        """The output of an earlier node that passed its gates on its current evidence, that stands accepted, and
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
        waived = self.store.waivers(node, key)
        if checks.blocks(checks.standing(judgement["verdicts"], waived)):
            reasons = "; ".join(f"{name}: {verdict['reason']}" for name, verdict in judgement["verdicts"].items()
                                if checks.blocks(verdict["answer"]) and name not in waived)
            raise Blocked(f"{node} answered {judgement['answer']}: {reasons}")
        accepted = self.store.accepted(node)
        if accepted != record["output"]:
            raise Blocked(f"{node}'s output {record['output'][:12]} is not accepted"
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
                 "expects": {before: list(wanted) for before, wanted in self.reads(stage, place).items()},
                 "params": stage.params,
                 "seed": node_seed(self.world.seed, stage.name, place if stage.grain == "place" else None),
                 "files": self.file_keys(stage, place),
                 "after": {before: self.usable(before, place, wanted)
                           for before, wanted in self.reads(stage, place).items()},
                 "models": {kind: self.model_record(kind) for kind in stage.models}}
        beside = self.besides(stage, place)
        if beside:  # only a stage that reads beside has this part, so no other node's key moves
            parts["beside"] = {node: self.usable(before, other, wanted)
                               for node, (before, other, wanted) in beside.items()}
        return {**parts, "key": text_hash(json.dumps(parts, sort_keys=True))}

    def besides(self, stage, place):
        """{node: (earlier stage, other place, (schema, version))} the node reads of other places (its `beside`, for
        each of its neighbours)."""
        if not stage.beside or place is None:
            return {}
        return {node_name(self.stages[before], other): (before, other, wanted)
                for other in stage.neighbours(place) for before, wanted in stage.beside.items()}

    def reads(self, stage, place):
        """{earlier stage: (schema, version)} the node reads: its `after`, less a place stage that has nothing to do
        for this place (its `applies`), which the node then reads without."""
        return {before: wanted for before, wanted in stage.after.items()
                if place is None or self.stages[before].applies is None or self.stages[before].applies(place)}

    def evidence_state(self, stage, output):
        """The hash of every check's evidence on an output ("none" for a check that needs none)."""
        state = {check.name: (self.store.evidence_hash(check.name, output) or "missing") if check.evidence else "none"
                 for check in stage.checks}
        return text_hash(json.dumps(state, sort_keys=True))

    # --- making and judging ------------------------------------------------------------------------------------

    def input_paths(self, stage, place, keyed):
        """{name: path} the stage's make reads: world files in place, earlier outputs checked out."""
        paths = {name: self.file_path(stage, name, place) for name in self.files_of(stage, place)}
        paths.update({before: self.store.checkout(output) for before, output in keyed["after"].items()})
        paths.update({node: self.store.checkout(output) for node, output in keyed.get("beside", {}).items()})
        return paths

    def spending(self, stage, node):
        """For a paid stage, its clearance's ticket named for the rent points while it makes; else nothing."""
        return self.cleared(node, stage.euros) if stage.paid else contextlib.nullcontext()

    def cleared(self, node, euros):
        """The node's clearance at `euros`, named for the rent points while the block runs; Blocked when refused."""
        from score.adapters import compute  # here: compute imports this module for its tickets
        try:
            return compute.spending(compute.clearance(self, node, euros))
        except compute.Refused as refusal:
            raise Blocked(str(refusal)) from refusal

    def make(self, stage, place, keyed):
        """Make the node's output, store it and write its finish record; the record."""
        node = node_name(stage, place)
        cleared = self.spending(stage, node)
        out = self.store.making(keyed["key"])
        started, clock = now(), time.monotonic()
        with cleared:
            stage.make(self.input_paths(stage, place, keyed), out, keyed["seed"], stage.params)
        if self.file_keys(stage, place) != keyed["files"]:
            raise RuntimeError(f"{node}: an input changed while it ran; nothing is stored")
        contracts.stamp(stage.contract, out)
        output = self.store.put_tree(out)
        shutil.rmtree(out)
        record = {"node": node, "key": keyed["key"], "output": output, "stage": stage.name, "place": keyed["place"],
                  "code": keyed["code"], "contract": keyed["contract"], "expects": keyed["expects"],
                  "params": keyed["params"], "seed": keyed["seed"], "files": keyed["files"], "after": keyed["after"],
                  "models": keyed["models"], **({"beside": keyed["beside"]} if "beside" in keyed else {}),
                  **_code.git_commit(),
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
        """Make the node if its key has no record, judge it if its evidence state has no judgement, accept it when it
        passed and got no worse; what it did."""
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
            done = "fresh"
        else:
            judgement = self.judge(stage, place, record)
            done = f"{'made' if made else 'judged again, output kept'}: {judgement['answer']}"
        accepted = self.store.accepted(node) != record["output"] and review.accept_automatically(
            self.store, node, record["output"])
        return f"{done}, accepted automatically" if accepted else done

    def nodes(self, places):
        """Every (stage, place) in table order: a world stage once, a place stage once per place."""
        for stage in self.stages.values():
            for place in ([None] if stage.grain == "world" else places):
                if place is None or stage.applies is None or stage.applies(place):
                    yield stage, place

    def read_closure(self, only):
        """The named stages and every stage they read, directly or through another."""
        kept, reading = set(), list(only)
        while reading:
            name = reading.pop()
            if name not in kept:
                kept.add(name)
                reading += [*self.stages[name].after, *self.stages[name].beside]
        return kept

    def line_nodes(self, places, whole, only=None):
        """The nodes a drive runs: every one of `nodes` for the whole world, else the places' own and only the world
        nodes they read (directly or through another world node); `only` (stage names) keeps those stages and the
        ones they read."""
        found = list(self.nodes(places))
        if only:
            kept = self.read_closure(only)
            found = [(stage, place) for stage, place in found if stage.name in kept]
        if whole:
            return found
        chosen = [(stage, place) for stage, place in found if stage.grain == "place"]
        names, reading = {node_name(*node) for node in chosen}, list(chosen)
        while reading:  # the world nodes and other places' nodes the places read, and what those read
            for before in self.read_nodes(*reading.pop()):
                if node_name(*before) not in names:
                    names.add(node_name(*before))
                    reading.append(before)
        others = sorted({place for stage, place in self.nodes_named(names)} - {None} - set(places))
        return [node for node in self.nodes([*places, *others]) if node_name(*node) in names]

    def nodes_named(self, names):
        """(stage, place) of each node name."""
        for name in names:
            stage_name, _, place = name.partition("@")
            yield self.stages[stage_name], place or None

    def read_nodes(self, stage, place):
        """(stage, place) of every node this node reads: its own place's or the world's, and other places'."""
        own = [(self.stages[before], place if self.stages[before].grain == "place" else None)
               for before in self.reads(stage, place)]
        return own + [(self.stages[before], other) for before, other, _ in self.besides(stage, place).values()]

    def run(self, places):
        """Run every node in table order; {node: what it did}."""
        return {node_name(stage, place): self.run_node(stage, place) for stage, place in self.nodes(places)}

    # --- driving lines -----------------------------------------------------------------------------------------

    def desk(self, area, node, suffix):
        """A node's file in one of the runner's own areas beside the store (faults, logs)."""
        return self.store.cache.parent / area / f"{node}{suffix}"

    def earlier(self, stage, place):
        """The nodes this node reads."""
        return [node_name(self.stages[before], place) for before in self.reads(stage, place)] + list(
            self.besides(stage, place))

    def gatherable(self, stage, place):
        """The checks whose missing evidence the runner can gather, when they alone keep the node from passing (none
        when another check blocks, or the node has no judgement on its current key)."""
        node = node_name(stage, place)
        keyed = self.key(stage, place)
        record = self.store.record(node, keyed["key"])
        judgement = record and self.store.judgement(node, keyed["key"], self.evidence_state(stage, record["output"]))
        if not judgement:
            return []
        waived = self.store.waivers(node, keyed["key"])
        blocking = {name for name, verdict in judgement["verdicts"].items()
                    if checks.blocks(verdict["answer"]) and name not in waived}
        missing = {name for name in stage.gatherers if self.store.evidence_hash(name, record["output"]) is None}
        return sorted(blocking) if blocking and blocking <= missing else []

    def gather(self, stage, place, wanted):
        """Make each wanted check's evidence on the node's output (a paid one inside its clearance) and store it."""
        node = node_name(stage, place)
        keyed = self.key(stage, place)
        output = self.store.record(node, keyed["key"])["output"]
        for name in wanted:
            gather, euros = stage.gatherers[name]
            folder = self.store.making(f"evidence-{name}-{output}")
            with self.cleared(node, euros) if euros else contextlib.nullcontext():
                found = gather(self.store.checkout(output), self.input_paths(stage, place, keyed), folder)
            self.store.put_evidence(name, output, found)
            shutil.rmtree(folder)

    def drive_node(self, stage, place):
        """Run one node, gathering the evidence it lacks and judging it again; what it did. Its output, a raised
        error's traceback included, goes to its log."""
        log = self.desk("logs", node_name(stage, place), ".log")
        log.parent.mkdir(parents=True, exist_ok=True)
        with logged(log):
            try:
                did = self.run_node(stage, place)
                wanted = [] if did.startswith(("blocked", "broken")) else self.gatherable(stage, place)
                if wanted:
                    self.gather(stage, place, wanted)
                    did = f"{did}; gathered {', '.join(wanted)}: {self.run_node(stage, place)}"
                return did
            except Exception as error:  # noqa: BLE001 - one node's error stops its line, not the run; kept in its log
                traceback.print_exc()
                return f"error: {type(error).__name__}: {error}"

    def standing(self, stage, place):
        """None when the node's current output passed and stands accepted; else why not."""
        try:
            self.usable(stage.name, place, (stage.contract.schema, stage.contract.version))
        except Blocked as block:
            return str(block)
        return None

    def fault_report(self, stage, place, did, cause):
        """Write the node's plain fault report (what it did, why its line stopped, every blocking check's reason,
        measures and findings, its log's tail); its path."""
        node = node_name(stage, place)
        line = place or WORLD_LINE
        lines = [f"fault: {node} (line {line}, world {self.world.name}, {now()})", f"what the runner did: {did}",
                 f"why its line stopped: {cause}", ""]
        lines += self.blocking_checks(stage, place)
        log = self.desk("logs", node, ".log")
        tail = log.read_text(errors="replace").splitlines()[-LOG_TAIL:] if log.exists() else []
        lines += [f"log: {log} (its last {len(tail)} lines)", *(f"  | {text}" for text in tail), "",
                  f"its records: python -m score.stages why {node}",
                  f"to go on once the cause is put right: python -m score run {self.world.name}"
                  + (f" --place {place}" if place else "")]
        path = self.desk("faults", node, ".txt")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n")
        return path

    def blocking_checks(self, stage, place):
        """The node's newest judgement's blocking checks as report lines: answer, reason, measures, findings."""
        node = node_name(stage, place)
        try:
            key = self.key(stage, place)["key"]
        except Blocked:
            return []
        judgements = self.store.judgements(node, key)
        if not judgements:
            return []
        waived = self.store.waivers(node, key)
        lines = [f"checks ({judgements[-1]['answer']}, output {judgements[-1]['output'][:12]}):"]
        for name, verdict in judgements[-1]["verdicts"].items():
            if not checks.blocks(verdict["answer"]) or name in waived:
                continue
            lines += [f"  {name}: {verdict['answer']}: {verdict['reason']}",
                      f"    measures: {json.dumps(verdict['measures'], sort_keys=True)}",
                      *(f"    - {finding}" for finding in verdict["findings"])]
        return lines + [""]

    def start(self, stage, place):
        """Start one node in a process of its own (forked: its output goes to its own log); {its result pipe: (stage,
        place, process)}."""
        receiving, sending = FORK.Pipe(duplex=False)
        sys.stdout.flush()
        sys.stderr.flush()
        process = FORK.Process(target=self.node_process, args=(stage, place, sending), name=node_name(stage, place))
        process.start()
        sending.close()
        return {receiving: (stage, place, process)}

    def node_process(self, stage, place, sending):
        """In the node's own process: drive it and send back what it did."""
        sending.send(self.drive_node(stage, place))
        sending.close()

    def outcome(self, receiving, process):
        """What a node's process did, once it ended; an error when it ended without saying."""
        try:
            did = receiving.recv()
        except EOFError:
            did = None
        receiving.close()
        process.join()
        return did or f"error: its process ended (exit code {process.exitcode}) without saying what it did"

    def conclude(self, stage, place, did):
        """A finished node's fault report when it does not stand, else its old report removed; (what it did, whether
        it stands)."""
        cause = self.standing(stage, place)
        if cause:
            return f"{did}; fault report {self.fault_report(stage, place, did, cause)}", False
        report = self.desk("faults", node_name(stage, place), ".txt")
        if report.exists():
            report.unlink()
        return did, True

    def drive(self, places, say=print, jobs=JOBS, whole=True, only=None):
        """Run every line to its end with no one in the loop, the lines side by side: each node starts in a process of
        its own the moment every node it reads stands accepted, at most `jobs` at once, so a line waiting on a cloud
        step holds up no other line, and nodes of one line that read nothing of each other run side by side. A world
        node is made once and each line that reads it waits on it alone. A node that does not end accepted stops its
        own line and leaves a fault report; {node: what it did}, in table order. `whole` False drives the places'
        lines alone, with only the world nodes they read; `only` (stage names) those stages and the ones they read."""
        chosen = self.line_nodes(places, whole, only)
        waiting = list(chosen)
        done, stopped, stood, running = {}, {}, set(), {}
        while waiting or running:
            for stage, place in list(waiting):
                node, earlier = node_name(stage, place), self.earlier(stage, place)
                waits = [stopped[before] for before in earlier if before in stopped]
                if waits:
                    waiting.remove((stage, place))
                    stopped[node] = waits[0]
                    done[node] = f"not run: its line stopped at {waits[0]}"
                    say(f"{node}: {done[node]}")
                elif stood.issuperset(earlier) and len(running) < jobs:
                    waiting.remove((stage, place))
                    running.update(self.start(stage, place))
            if not running:
                break
            for finished in FORK_WAIT(list(running)):
                stage, place, process = running.pop(finished)
                node = node_name(stage, place)
                done[node], stands = self.conclude(stage, place, self.outcome(finished, process))
                if stands:
                    stood.add(node)
                else:
                    stopped[node] = node
                say(f"{node}: {done[node]}")
        return {node_name(stage, place): done[node_name(stage, place)] for stage, place in chosen
                if node_name(stage, place) in done}

    def lines(self, places, whole=True, only=None):
        """{line: (its state, {node: state})}, running nothing: the world's own nodes are one line, each place's
        another (`whole` False: only the world nodes the places read). A line is done when every node stands
        accepted, else stopped (a fault report waits) or waiting at its first node that does not stand."""
        found = {}
        states = self.status(places)
        for stage, place in self.line_nodes(places, whole, only):
            node, line = node_name(stage, place), place or WORLD_LINE
            summary, nodes = found.get(line, ("done", {}))
            nodes[node] = states[node]
            if summary == "done" and self.standing(stage, place):
                report = self.desk("faults", node, ".txt")
                summary = f"stopped at {node}: fault report {report}" if report.exists() else f"waits at {node}"
            found[line] = (summary, nodes)
        return found

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
        for part in ("files", "after", "beside"):
            if last.get(part, {}) != keyed.get(part, {}):
                reasons += [f"{name} changed" for name in sorted(set(last.get(part, {})) | set(keyed.get(part, {})))
                            if last.get(part, {}).get(name) != keyed.get(part, {}).get(name)]
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
        waived = sorted(self.store.waivers(node, keyed["key"]))
        return (f"{judgement['answer']}{', waived: ' + ', '.join(waived) if waived else ''}, "
                f"{'accepted' if accepted else 'not accepted'}")

    def status(self, places):
        """{node: its state, and the earlier nodes its accepted output went stale on}, running nothing."""
        found = {}
        for stage, place in self.nodes(places):
            node, stale = node_name(stage, place), self.stale(node_name(stage, place))
            found[node] = self.node_status(stage, place) + (
                f", its accepted output is stale: {', '.join(stale)} moved" if stale else "")
        return found

    def stale(self, node):
        """The earlier nodes whose accepted output is no longer the one the node's accepted output read (an owner's
        reject moved it back), or is itself stale; none when the node has no accepted output."""
        accepted = self.store.accepted(node)
        record = review.record_of(self.store, node, accepted) if accepted else None
        if record is None:
            return []
        place = node.partition("@")[2] or None
        earlier = {node_name(self.stages[before], place): output for before, output in record["after"].items()}
        earlier.update(record.get("beside", {}))
        return [before for before, output in earlier.items()
                if self.store.accepted(before) != output or self.stale(before)]

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
        for before in self.read_nodes(self.stages[stage_name], place or None):
            lines += self.why(node_name(*before), depth + 1)
        return lines
