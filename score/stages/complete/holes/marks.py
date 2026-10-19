"""The gate marks of a place: every fault already written about it, as the objects it names, each found on the
place's stage. Nothing is judged here; nothing found is dropped.

    found = marks.judged(store, place)            # the FAIL verdicts' findings of each node's newest judgement
    found += marks.checked(own, place, store)     # every other standalone check's findings.json, while current
    found += marks.gapped(data, place)            # the place's named gaps: decided faults, their reason the work
    holes = marks.holes(stage, place, found)      # one hole an object and filler, with the prims it is on

A finding names its object as gaps.object_of reads it (before its first ": ", or a JSON finding's `row`); a check's
finding names its prim. A name is read as the stage names it (object_name: no "<place>." before it, no take's suffix
or words in brackets after it). The object is found as /<place>/Objects/<object>, else every one of the place's own
prims whose score:row is it (never a shown place's); a fault on the whole node marks the place's root; one found on
nothing is kept with no prim. complete's `rows` findings, and the named gaps on them, are the missing rows'
(rows.py) and its `named gaps` the gaps' own, so all are left to them.
"""
import json
import re

from pxr import Sdf

from score import checks, review, stages
from score.review import GAPPED
from score.stages import gaps
from score.stages.complete.holes import fill, rows

FINDINGS = "findings.json"
SENTENCE = 300
MISSING_ROWS = (fill.COMPLETE, "rows")  # complete's rows gate: its unmade rows are the missing holes (rows.py)
TAKE = re.compile(r"-[a-z]\d+$")  # a take's suffix on an object's name (the paint's "hatch_door_frame-s1")


def place_nodes(place):
    """Every node of the place in the stage table: each place stage that applies to it."""
    return [f"{row.name}@{place}" for row in stages.STAGES
            if row.grain == "place" and (row.applies is None or row.applies(place))]


def said(finding):
    """A finding in words: a JSON finding's `why` (complete's), else the finding as written."""
    if finding.startswith("{"):
        written = json.loads(finding)
        return str(written.get("why") or finding)
    return finding


def judged(store, place):
    """[{stage, gate, object, sentence, source}] of every FAIL verdict of each node's newest judgement; a verdict
    with no findings is a fault of the whole node, on the place."""
    found = []
    for node in place_nodes(place):
        record = review.record_of(store, node)
        judgement = review.newest_judgement(store, record) if record else None
        stage = node.split("@", 1)[0]
        for name, verdict in (judgement or {}).get("verdicts", {}).items():
            if verdict["answer"] != checks.FAIL or (stage == fill.COMPLETE and name in ("rows", GAPPED)):
                continue
            findings = verdict.get("findings") or [f"{place}: {verdict['reason']}"]
            found += [{"stage": stage, "gate": name, "object": gaps.object_of(finding) or place,
                       "sentence": said(finding)[:SENTENCE], "source": f"judgement:{node}", "kind": None}
                      for finding in findings]
    return found


def current(store, written):
    """Whether every output a check judged is still the accepted one."""
    return all(store.accepted(node) == output for node, output in written.get("outputs", {}).items())


def checked(own, place, store):
    """[{stage, gate, object, sentence, source}] of every other standalone check's findings of the place, while
    the outputs it judged stay accepted; `own` this check's out folder, the others' beside it (WORK/checks)."""
    found = []
    for path in sorted(own.parent.glob(f"*/{place}/{FINDINGS}")):
        check = path.parts[-3]
        written = json.loads(path.read_text())
        if path.parent.parent == own or not current(store, written):
            continue
        found += [{"stage": check, "gate": item["rule"], "object": item.get("prim") or item.get("name") or place,
                   "sentence": item["sentence"][:SENTENCE], "source": f"check:{check}", "kind": item.get("kind")}
                  for item in written.get("findings", [])]
    return found


def gapped(data, place):
    """[{stage, gate, object, sentence, source, work}] of each object a named gap of the place names (the place
    itself for a gap that names none): a decided fault, its reason the work."""
    path = data / "checks/gaps" / f"{place}.json"
    if not path.exists():
        return []
    return [{"stage": entry["row"], "gate": entry["check"], "object": item, "kind": None,
             "sentence": f"{entry['name']} (named gap, {entry['decided']})"[:SENTENCE],
             "source": f"gap:{entry['name']}", "work": entry["reason"]}
            for entry in gaps.entries({gaps.NAME: str(path)}) if (entry["row"], entry["check"]) != MISSING_ROWS
            for item in entry.get("objects") or [place]]


def object_name(name, place):
    """The object a finding names, as the stage and the inventory name it: anything from " (" cut off; a name that
    is no path loses a leading "<place>." and a take's suffix ("-s1"). Paths and `<row>_<n>` names are kept."""
    name = name.split(" (", 1)[0]
    if name.startswith("/"):
        return name
    return TAKE.sub("", name.removeprefix(f"{place}."))


def prims_of(stage, place, name, by_row):
    """The prims an object names: its own path, /<place>/Objects/<name>, the place's root, else the prims of its
    row; [] when none is on the stage."""
    if stage is None:
        return []
    for path in (name if name.startswith("/") else None, f"/{place}/Objects/{name}",
                 f"/{place}" if name == place else None):
        if path and Sdf.Path.IsValidPathString(path) and stage.GetPrimAtPath(path):
            return [path]
    return sorted(by_row.get(name, []))


def filler(item, place):
    """(node, work) of a finding: a named gap's reason; a code fix of what the check finds (no stage fills a
    standalone check's finding); a judgement's by fill.gate."""
    if "work" in item:
        return None, item["work"]
    if item["source"].startswith("check:"):
        check = item["stage"]
        return None, f"a code fix for what the {check} check finds (no stage makes it again)"
    return fill.gate(item["stage"], item["gate"], place)


def holes(stage, place, found):
    """One gate hole an object and filler: its gates, sentences, sources and prims."""
    by_row = rows.made_objects(stage, place)
    grouped = {}
    for item in found:
        node, work = filler(item, place)
        name = object_name(item["object"], place)
        key = (name, node, item["source"] if node is None else None)
        hole = grouped.setdefault(key, {"object": name, "node": node, "works": [], "gates": [],
                                        "sentences": [], "source": item["source"], "kind": item["kind"],
                                        "prims": prims_of(stage, place, name, by_row)})
        for field, value in (("gates", f"{item['stage']}/{item['gate']}"), ("sentences", item["sentence"]),
                             ("works", work)):
            if value is not None and value not in hole[field]:
                hole[field].append(value)
    return [dict(hole, gates=sorted(hole["gates"])) for hole in grouped.values()]
