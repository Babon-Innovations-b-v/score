"""The carry-over of the paint and bake rows' accepted outputs (and their crops and people twins) to their narrower
keys (library_reads.py, 2026-10-13), remaking nothing.

    .venv/bin/python -m score.stages.surfaces.carry [--write]     # what carries and why not; --write stores it now

The runner carries by itself too: before it makes one of these rows it asks `carried`, and `rebuy` counts a row that
carries as no buy. An accepted output carries when its record was made from a committed tree, its code is the row's
code under the wide key today, every other key part (contract, inputs, earlier outputs, parameters, seed, models,
every other world file) is the new key's, and the library part the row reads, worked out on the library as it was
at the record's commit (rebuilt from git), is today's. A row whose own code changed since carries
only with a proof stored as evidence on the output that the change leaves its result as it is (`proof_fault`: every
changed file named with why, the free rows before it made again to their accepted outputs); no proof, no carry. It is
then stored once more under the new key: the same output, its record and judgements copied, the record saying "same
inputs, narrower key" with both keys, the commit and code that made it and the proof it rests on. The accepted output
does not move (an accept names the output, not the key): a runner rule, never an accept by hand. Anything else is
made as usual.

A key follows content, never a path's text: an earlier output a key moved by carries when the reading row gives a
content rule for that input (CONTENT_RULES: a framework module beside the row, its RULES {input stage: rule}) and the
old and new outputs hand it the same content under it (`same_content`: closeup's props-inputs rows.json with each
picture path resolved and replaced by the picture's sha256, #75; rough-model's plan, of which it reads the place
alone; a look's parts, body and dress, the people-made they read beside with each look's model as its place in
its bake output, people/same_content.py). By hand: `carry --no-op FILE=WHY ... --only PREFIX [--write]` (a FILE the node's key does not read is
never asked for); the record names the content proof ("same content").
"""
import argparse
import dataclasses
import fnmatch
import importlib
import json
import os
import pathlib
import subprocess
import sys

from score import graph, review
from score.graph import Blocked, _code
from score.store import PROPS_HOME, file_hash, listing_hash, text_hash

REASON ="same inputs, narrower key"
CONTENT_REASON = ("same content: every earlier output its key moved by holds what it read then, by its reader's content "
                  "rule, and every other change since it was made is proved a no-op for it")
# {reading row: the framework module whose RULES are its content rules, {input stage: rule(store, record) -> the
# content that output hands this row}}: an earlier output that moved by path text alone keeps the row (#75).
# A key is an fnmatch pattern of row names (each people row reading people-made beside, #26).
CONTENT_RULES = {"closeup": "score.stages.props.same_content", "rough-model": "score.stages.rough_model.same_content",
                 "rough-align": "score.stages.rough_model.same_content:ALIGN_RULES",
                 "people-look-parts-*": "score.stages.people.same_content", "people-body-*":
                     "score.stages.people.same_content", "people-dress-*": "score.stages.people.same_content"}
# The key parts a content carry needs the same as its accepted record's: all but the earlier outputs (`after`, and
# `beside`: what it reads of other places' nodes).
CONTENT_SAME = ("code", "contract", "expects", "params", "seed", "files", "models")
# The key parts that name earlier outputs, {part: (the reading row, its key there) -> (its stage, its node)}: an
# after read is keyed by stage, in the row's place; a beside read by its node.
EARLIER = {"after": lambda runner, place, name: (name, graph.node_name(runner.stages[name], place)),
           "beside": lambda runner, place, name: (name.partition("@")[0], name)}
AUTO_REASON = "same content: every earlier output its key moved by holds what it reads, by its content rule"
NARROWED = ("library",)
SAME = ("contract", "expects", "params", "seed", "models", "after", "beside")
TRACKED = {"library": "data/library"}
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
    """{name: hash} of the row's library part as the record's commit had it."""
    files = row.files(place)
    then = {name: at_commit(record["commit"], path) for name, path in TRACKED.items()}
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


def content_rules(stage_name):
    """{input stage: its content rule} the reading row gives (CONTENT_RULES); {} for a row that gives none."""
    found = next((rule for pattern, rule in CONTENT_RULES.items() if fnmatch.fnmatchcase(stage_name, pattern)), "")
    module, _, name = found.partition(":")
    return getattr(importlib.import_module(module), name or "RULES") if module else {}


def moved_earlier(record, keyed):
    """True when an earlier output the key reads (its after or beside part) is not the record's."""
    return any(record.get(part, {}) != keyed.get(part, {}) for part in EARLIER)


def same_content(runner, stage, place, record, keyed):
    """({input: {"from": its output then, "to": its output now, "rule": the rule}} for every earlier output the key's
    after or beside part moved by (an after input named by its stage, a beside one by its node), None) when each holds
    the same content under the reading row's content rule; (None, why) when one does not, or has no rule, or a
    picture it names resolves to no file."""
    rules = content_rules(stage.name)
    proof = {}
    for part, named in EARLIER.items():
        then, now = record.get(part, {}), keyed.get(part, {})
        for name in sorted(set(then) | set(now)):
            if then.get(name) == now.get(name):
                continue
            before, node = named(runner, place, name)
            rule = rules.get(before)
            if rule is None or name not in then or name not in now:
                return None, f"{name}'s output moved, and {stage.name} gives no content rule for it"
            why = same_output_content(runner, node, rule, then[name], now[name])
            if why:
                return None, f"{name}'s output {why}"
            proof[name] = {"from": then[name], "to": now[name], "rule": f"{rule.__module__}.{rule.__name__}"}
    return proof, None


def same_output_content(runner, node, rule, then, now):
    """Why the node's two outputs hand the reader other content under its rule, or None when the same."""
    contents = []
    for output in (then, now):
        made = review.record_of(runner.store, node, output)
        if made is None:
            return f"{output[:12]} has no record"
        try:
            contents.append(rule(runner.store, made))
        except ValueError as unresolved:
            return f"{output[:12]}: {unresolved}"
    if contents[0] != contents[1]:
        differ = sorted(part for part in set(contents[0]) | set(contents[1])
                        if contents[0].get(part) != contents[1].get(part))
        return f"holds other content ({', '.join(differ)})"
    return None


class Foreseen:
    """A store whose one output is a remake foreseen in a scratch folder ({file: its JSON}), for a content rule."""
    def __init__(self, files):
        self.files = files

    def read_file(self, output, name):
        return self.files.get(name)


def foreseen_same(runner, row, place, moving):
    """True when every node of `moving` (earlier nodes a drive makes again) was foreseen (runner.foreseen: its remake
    in a scratch folder, stages.remade_same) and hands the row the content its accepted output read, by the row's
    content rule: rebuy then keeps the row, as content_carried does when the drive makes them."""
    rules, record = content_rules(row.name), graph_record(runner, row, place)
    if record is None:
        return False
    for node in moving:
        before = node.partition("@")[0]
        then = record.get("beside", {}).get(node) or record.get("after", {}).get(before)  # a beside read by node
        made = review.record_of(runner.store, node, then) if then else None
        if before not in rules or node not in runner.foreseen or made is None:
            return False
        try:
            if rules[before](runner.store, made) != rules[before](Foreseen(runner.foreseen[node]), {"output": None}):
                return False
        except ValueError:
            return False
    return True


def same_earlier(runner, row, place, record, keyed):
    """True when every earlier output the key moved by since `record` hands the row what it read then, by its content
    rule (same_content): the phase lock then holds the row over code and those moves together (Runner.same_earlier)."""
    return same_content(runner, row, place, record, keyed)[0] is not None


def earlier_parts(keyed):
    """The key's parts that name earlier outputs (EARLIER), those it has."""
    return {part: keyed[part] for part in EARLIER if part in keyed}


def graph_record(runner, row, place):
    """The record of the node's accepted output, or None."""
    node = graph.node_name(row, place)
    accepted = runner.store.accepted(node)
    return review.record_of(runner.store, node, accepted) if accepted else None


def content_carries(runner, row, place, keyed):
    """True when the node's accepted output carries to `keyed` by content alone: every key part but the earlier
    outputs is its record's (CONTENT_SAME), and each earlier output that moved holds what the row reads of it, by its
    content rule (same_content)."""
    record = graph_record(runner, row, place)
    if record is None or not moved_earlier(record, keyed):
        return False
    if any(record.get(part) != keyed.get(part) for part in CONTENT_SAME):
        return False
    return same_content(runner, row, place, record, keyed)[0] is not None


def content_carried(runner, row, place, keyed):
    """The node's accepted output stored under `keyed` when it carries by content (content_carries): its record and
    judgements copied, the record naming both keys, what made it and the content proof. Its new record, or None."""
    if not content_carries(runner, row, place, keyed):
        return None
    record = graph_record(runner, row, place)
    node = graph.node_name(row, place)
    new = {**record, "key": keyed["key"], **earlier_parts(keyed),
           "carried": {"reason": AUTO_REASON, "from key": record["key"], "to key": keyed["key"],
                       "made by": graph.made_by(record),
                       "same content": same_content(runner, row, place, record, keyed)[0]}}
    try:
        runner.store.write_record(node, keyed["key"], new)
    except FileExistsError:  # another run kept it first
        return runner.store.record(node, keyed["key"])
    copy_judgements(runner, node, record, keyed, new["carried"])
    return new


def why_not(runner, row, place, record, keyed):
    """Why the accepted record does not carry to the new key, or None when it does."""
    if record.get("uncommitted", True) or not record.get("commit"):
        return "made from a tree with changes not committed"
    if record["code"] != wide_code(row):
        fault = proof_fault(runner, row, record)
        if fault:
            return fault
    moved = [part for part in SAME if record.get(part) != keyed.get(part)]
    if set(EARLIER) & set(moved) and same_content(runner, row, place, record, keyed)[0] is not None:
        moved = [part for part in moved if part not in EARLIER]
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
    content = same_content(runner, row, place, record, keyed)[0] if moved_earlier(record, keyed) else None
    new = {**record, "key": keyed["key"], "code": keyed["code"], "files": keyed["files"], **earlier_parts(keyed),
           "carried": {"reason": REASON + (", its code change proved a no-op" if proved else "")
                       + (", its moved inputs the same content" if content else ""),
                       "from key": record["key"], "to key": keyed["key"],
                       "made by": {"commit": record["commit"], "code": record["code"]},
                       "proof": runner.store.evidence_key(proof_check(wide_code(row)), record["output"])
                       if proved else None, **({"same content": content} if content else {})}}
    runner.store.write_record(node, keyed["key"], new)
    copy_judgements(runner, node, record, keyed, new["carried"])
    return new


def copy_judgements(runner, node, record, keyed, carried_as):
    """The judgements of the record's key written again under `keyed`, each naming the carry."""
    for judgement in runner.store.judgements(node, record["key"]):
        runner.store.write_judgement(node, keyed["key"], judgement["evidence"],
                                     {**judgement, "key": keyed["key"], "carried": carried_as})


def changes_by_content(runner, stage, place, keyed):
    """((the accepted output's record, the repository files changed since its commit), the content proof, None) when
    its key moved by earlier outputs of the same content (same_content) and otherwise only as changes_since allows
    (its code and declared repository files, or nothing else); (None, None, why) otherwise."""
    node = graph.node_name(stage, place)
    record = review.record_of(runner.store, node, runner.store.accepted(node))
    if record is None or record.get("uncommitted", True) or not record.get("commit") or \
            not moved_earlier(record, keyed):
        return None, None, "other key parts moved"
    content, why = same_content(runner, stage, place, record, keyed)
    if why:
        return None, None, why
    as_then = {**keyed, **earlier_parts(record)}
    found = runner.changes_since(stage, place, as_then)
    if found is not None:
        return found, content, None
    if all(record.get(part) == as_then.get(part) for part in ("code", "files", *SAME)):
        return (record, []), content, None
    return None, None, "other key parts moved"


def kept_by_content(runner, stage, place, keyed, record, check, proof):
    """The node's accepted output stored under `keyed` when the earlier outputs its key moved by hold the same content
    and every other change is proved a no-op (`proof`, stored as evidence `check` on the output): its record and
    judgements copied, the record naming both keys, what made it, the content proof and the no-ops. Its new record."""
    node = graph.node_name(stage, place)
    new = {**record, "key": keyed["key"], "code": keyed["code"], "files": keyed["files"], **earlier_parts(keyed),
           "carried": {"reason": CONTENT_REASON, "from key": record["key"], "to key": keyed["key"],
                       "made by": graph.made_by(record),
                       "proof": runner.store.evidence_key(check, record["output"]),
                       "same content": proof["same content"], "no-ops": proof["no-ops"]}}
    runner.store.write_record(node, keyed["key"], new)
    copy_judgements(runner, node, record, keyed, new["carried"])
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


CODES_AT = """import json, sys
sys.path.insert(0, ".")
from score import graph, stages
from score.graph import _code
from score.store import file_hash, listing_hash
print(json.dumps({row.name: listing_hash(_code.code_version(graph.code_functions(row), file_hash))
                  for row in stages.STAGES}))"""


def codes_at(commit):
    """{row: its code version} as the stage table at `commit` works it out, in a checkout of its own (removed)."""
    folder = COMMITS / f"tree-{commit}"
    subprocess.run(["git", "-C", str(_code.REPO), "worktree", "add", "-q", "--detach", str(folder), commit],
                   check=True)
    try:
        done = subprocess.run([sys.executable, "-c", CODES_AT], cwd=folder, capture_output=True, text=True,
                              check=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})  # the tree stays clean
        return json.loads(done.stdout.strip().splitlines()[-1])
    finally:
        subprocess.run(["git", "-C", str(_code.REPO), "worktree", "remove", str(folder)], check=True)


def proved(runner, places, reasons, skip, write, since=None, only=None):
    """Every node in table order whose key moved only by repository files `reasons` names ({file: why its change
    is a no-op}), of `only` (node-name prefixes) when given, never one of `skip` and, given `since` ({row: its code
    at the commit the reasons speak from, codes_at}), only one whose record was made from that code, so the reasons
    speak for every change since: its
    proof stored as evidence on its accepted output (graph.no_op_proof) and the output kept under its new key by the
    runner's rule, so the nodes after it see the same input. Its line."""
    with runner.still():
        for stage, place in runner.nodes(places):
            node = graph.node_name(stage, place)
            if only and not node.startswith(tuple(only)) or runner.store.accepted(node) is None:
                continue
            try:
                keyed = runner.key(stage, place)
            except Blocked as blocked:
                yield f"{node}: blocked: {blocked}"
                continue
            if runner.store.record(node, keyed["key"]) is not None:
                continue
            found, content, why = runner.changes_since(stage, place, keyed), None, "other key parts moved"
            if found is None:
                found, content, why = changes_by_content(runner, stage, place, keyed)
            unproved = None if found is None else [name for name in found[1] if name not in reasons]
            if node in skip or found is None or unproved:
                why = ("its change is not a no-op for it" if node in skip else why
                       if found is None else f"{', '.join(unproved)} changed")
                yield f"{node}: made again ({why})"
                continue
            record, changed = found
            if since is not None and record["code"] != since.get(stage.name):
                yield f"{node}: made again (its record's code is not its code at the proof's commit)"
                continue
            if write:
                proof = {"from key": record["key"], "to key": keyed["key"],
                         "no-ops": {name: reasons[name] for name in changed},
                         **({"same content": content} if content else {})}
                path = COMMITS / f"proof-{keyed['key']}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(proof, indent=1))
                runner.store.put_evidence(f"no-op-{keyed['key']}", record["output"], path)
                path.unlink()
                if content:
                    kept_by_content(runner, stage, place, keyed, record, f"no-op-{keyed['key']}", proof)
                elif runner.kept_by_proof(stage, place, keyed) is None:
                    raise RuntimeError(f"{node}: its proof was stored but the runner did not keep it")
            said = [f"{', '.join(changed)} a no-op"] if changed else []
            said += [f"{before}'s output the same content" for before in content or {}]
            yield f"{node}: {'kept' if write else 'keeps'} ({'; '.join(said)})"


def main(argv=None):
    from score import stages
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", action="store_true", help="store what carries now (default: only list it)")
    parser.add_argument("--no-op", action="append", default=[], metavar="FILE=WHY",
                        help="a repository file whose change is a no-op for every node but --skip ones, and why")
    parser.add_argument("--skip", action="append", default=[], metavar="NODE", help="a node the change does reach")
    parser.add_argument("--only", action="append", metavar="PREFIX", help="only the nodes whose name starts so (the "
                                                                       "reasons speak for these rows alone)")
    parser.add_argument("--since", help="the commit the --no-op reasons speak from: a record not made from the code "
                                        "the row had there is made again")
    options = parser.parse_args(argv)
    write = options.write
    runner = stages.runner(world=stages.WORLDS["world1"]())
    places = stages.places(runner.world, runner.store)
    if options.no_op:
        reasons = dict(entry.split("=", 1) for entry in options.no_op)
        since = codes_at(options.since) if options.since else None
        for line in proved(runner, places, reasons, set(options.skip), write, since, options.only):
            print(line, flush=True)
        return
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
