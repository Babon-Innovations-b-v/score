"""The carry-over of the paint and bake rows' accepted outputs (and their crops and people twins) to their narrower
keys (library_reads.py, 2026-10-13), remaking nothing.

    .venv/bin/python -m score.stages.surfaces.carry [--write]     # what carries and why not; --write stores it now

The runner carries by itself too: before it makes one of these rows it asks `carried`, and `rebuy` counts a row that
carries as no buy. An accepted output carries when its record was made from a committed tree, its code is the row's
code under the wide key today, every other key part (contract, inputs, earlier outputs, parameters, seed, models,
every other world file) is the new key's, and the library and place.json parts the row reads, worked out on those
files as they were at the record's commit (rebuilt from git), are today's. A row whose own code changed since carries
only with a proof stored as evidence on the output that the change leaves its result as it is (`proof_fault`: every
changed file named with why, the free rows before it made again to their accepted outputs); no proof, no carry. It is
then stored once more under the new key: the same output, its record and judgements copied, the record saying "same
inputs, narrower key" with both keys, the commit and code that made it and the proof it rests on. The accepted output
does not move (an accept names the output, not the key): a runner rule, never an accept by hand. Anything else is
made as usual.
"""
import argparse
import dataclasses
import json
import os
import pathlib
import subprocess
import sys

from score import graph, review
from score.graph import Blocked, _code
from score.store import PROPS_HOME, file_hash, listing_hash, text_hash

REASON = "same inputs, narrower key"
NARROWED = ("library", "places")
SAME = ("contract", "expects", "params", "seed", "models", "after", "beside")
TRACKED = {"library": "data/library", "places": "data/definitions/place.json"}
COMMITS = PROPS_HOME / "work/carry-commits"  # the tracked files as each record's commit had them, written once
WIDE_CODES = {}


def at_commit(commit, path):
    """The repository's file or folder `path` as it was at `commit`, under COMMITS/<commit>/ (written once, each
    file landing whole, so runner processes side by side read it safely)."""
    target = COMMITS / commit / path
    names = subprocess.run(["git", "-C", str(_code.REPO), "ls-tree", "-r", "--name-only", commit, path],
                           capture_output=True, text=True, check=True).stdout.split()
    for name in names:
        out = COMMITS / commit / name
        if out.exists():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        partial = out.with_name(f"{out.name}.{os.getpid()}.partial")
        partial.write_bytes(subprocess.run(["git", "-C", str(_code.REPO), "show", f"{commit}:{name}"],
                                           capture_output=True, check=True).stdout)
        os.replace(partial, out)
    return target


def wide_code(row):
    """The row's code version under its wide key (its files before library_reads), once a process."""
    if row.name not in WIDE_CODES:
        wide = dataclasses.replace(row, files=row.files.wide)
        WIDE_CODES[row.name] = listing_hash(_code.code_version(graph.code_functions(wide), file_hash))
    return WIDE_CODES[row.name]


def narrowed_then(row, place, record):
    """{name: hash} of the row's library and place.json parts as the record's commit had those files."""
    files = row.files(place)
    then = {name: at_commit(record["commit"], path) for name, path in TRACKED.items()}  # the library reads place.json
    return {name: text_hash(files[name][1](then[name])) for name in NARROWED}


def proof_check(code):
    """The evidence check a "same result" proof is stored under for one code version (one proof a code version)."""
    return f"same-result-{code}"


def changed_files(row, commit):
    """The row's source files (under its wide key) that differ between `commit` and this tree."""
    wide = dataclasses.replace(row, files=row.files.wide)
    files = [str(path.relative_to(_code.REPO)) for path in _code.source_files(graph.code_functions(wide))]
    found = subprocess.run(["git", "-C", str(_code.REPO), "diff", "--name-only", commit, "--", *files],
                           capture_output=True, text=True, check=True).stdout.split()
    return sorted(found)


def proof_fault(runner, row, record):
    """Why the row's code change since its accepted output is not proved a no-op, or None when it is. The proof is
    JSON stored as evidence on the output (Store.put_evidence(proof_check(code now), output, file)): {"made with
    code": the record's code, "code now": the row's code today, "no-ops": {file: why its change leaves the result as
    it is} naming every source file changed since the record's commit, "free rows": {node: output} the free rows
    before it made again under today's code, each that node's accepted output and recorded under its key now}."""
    now = wide_code(row)
    path = runner.store.evidence_file(proof_check(now), record["output"])
    if path is None:
        return "its code changed since, with no proof its result is the same"
    proof = json.loads(pathlib.Path(path).read_text())
    if proof.get("made with code") != record["code"] or proof.get("code now") != now:
        return "its proof is for other code versions"
    unexplained = [name for name in changed_files(row, record["commit"])
                   if not str(proof.get("no-ops", {}).get(name, "")).strip()]
    if unexplained:
        return f"its proof does not say why these changes leave the result as it is: {', '.join(unexplained)}"
    for node, output in proof.get("free rows", {}).items():
        stage_name, _, place = node.partition("@")
        try:
            key = runner.key(runner.stages[stage_name], place or None)["key"]
        except (Blocked, KeyError) as missing:
            return f"its proof's free row {node} cannot be checked: {missing}"
        remade = runner.store.record(node, key)
        if remade is None or remade["output"] != output or runner.store.accepted(node) != output:
            return f"its proof's free row {node} was not made again to the same accepted output"
    return None


def why_not(runner, row, place, record, keyed):
    """Why the accepted record does not carry to the new key, or None when it does."""
    if record.get("uncommitted", True) or not record.get("commit"):
        return "made from a tree with changes not committed"
    if record["code"] != wide_code(row):
        fault = proof_fault(runner, row, record)
        if fault:
            return fault
    moved = [part for part in SAME if record.get(part) != keyed.get(part)]
    moved += [f"file {name}" for name in sorted(set(record["files"]) | set(keyed["files"]))
              if name not in NARROWED and record["files"].get(name) != keyed["files"].get(name)]
    if moved:
        return f"moved: {', '.join(sorted(moved))}"
    then = narrowed_then(row, place, record)
    changed = [name for name in NARROWED if then[name] != keyed["files"][name]]
    return f"the {' and '.join(changed)} it reads changed" if changed else None


def standing(runner, row, place, keyed):
    """(the accepted output's record, why it does not carry or None); (None, why) when nothing is accepted."""
    node = graph.node_name(row, place)
    accepted = runner.store.accepted(node)
    if accepted is None:
        return None, "nothing accepted"
    record = review.record_of(runner.store, node, accepted)
    return record, why_not(runner, row, place, record, keyed)


def carries(runner, row, place, keyed):
    """True when the node's accepted output carries to `keyed` (rebuy: a row that carries is bought by nobody)."""
    return standing(runner, row, place, keyed)[1] is None


def carried(runner, row, place, keyed):
    """The node's accepted output stored under `keyed`, its record and judgements copied with the carry named; its
    new record, or None when it does not carry (the runner then makes it)."""
    record, reason = standing(runner, row, place, keyed)
    if reason:
        return None
    node = graph.node_name(row, place)
    proved = record["code"] != wide_code(row)
    new = {**record, "key": keyed["key"], "code": keyed["code"], "files": keyed["files"],
           "carried": {"reason": REASON + (", its code change proved a no-op" if proved else ""),
                       "from key": record["key"], "to key": keyed["key"],
                       "made by": {"commit": record["commit"], "code": record["code"]},
                       "proof": runner.store.evidence_key(proof_check(wide_code(row)), record["output"])
                       if proved else None}}
    runner.store.write_record(node, keyed["key"], new)
    for judgement in runner.store.judgements(node, record["key"]):
        runner.store.write_judgement(node, keyed["key"], judgement["evidence"],
                                     {**judgement, "key": keyed["key"], "carried": new["carried"]})
    return new


def listed(runner, row, place, write):
    """One node's line: carried, kept, or not carried and why; None when nothing is accepted."""
    node = graph.node_name(row, place)
    if runner.store.accepted(node) is None:
        return None
    try:
        keyed = runner.key(row, place)
    except Blocked as blocked:
        return f"not carried: blocked: {blocked}"
    if runner.store.record(node, keyed["key"]) is not None:
        return "kept: it has a record under its key"
    record, reason = standing(runner, row, place, keyed)
    if reason:
        return f"not carried: {reason}"
    if write:
        carried(runner, row, place, keyed)
    return f"{'carried' if write else 'carries'}: {REASON} ({record['key'][:12]} -> {keyed['key'][:12]})"


def main(argv=None):
    from score import stages
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", action="store_true", help="store what carries now (default: only list it)")
    write = parser.parse_args(argv).write
    runner = stages.runner(world=stages.WORLDS["world1"]())
    places = stages.places(runner.world)
    for row in runner.stages.values():
        if not hasattr(row.files, "wide"):
            continue
        for place in ([None] if row.grain == "world" else places):
            if row.applies and place is not None and not row.applies(place):
                continue
            line = listed(runner, row, place, write)
            if line:
                print(f"{graph.node_name(row, place)}: {line}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
