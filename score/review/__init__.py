"""The review page base, the runner's automatic accept and the owner's reject: one page per stage output, built from
its own finish record.

    path = review.page(store, "assembly@hangar")            # the node's newest output; or key=... for another
    review.accept_automatically(store, node, output)         # the runner's: all gates pass, nothing got worse
    review.reject(store, node, output, by, reason)           # the owner's: the accepted output moves back
    review.accept(store, node, output, by, reason, worse_reason=None)   # the owner's own accept, when he wants one
    review.spend(store, node, key, euros, by)                # the owner's override: his yes to a run outside the runner
    review.waive(store, node, key, check, by, reason)        # the owner lets one check pass for one key

A page shows the node's output, where it came from (an unverified seed says so), every gate's answer with its
measures, reason and findings, the record (inputs, code version, commit, seed, machine, time, cost), the judgements
made before, and who accepted it. Pages are written in the store's cache, never in the repository.

The runner accepts an output by itself (the owner's answer of 2026-10-11: from concept and style on everything runs
automatically) when its newest judgement passes once the owner's waivers for its key count, its scorecard is no worse
than the accepted output's, and the owner never rejected it; the accept says it is the runner's. Inside a bought batch
a passing worse output is accepted too, its drop written in the accept's status for him (IN_BATCH). The owner may reject
any accepted output from his terminal: the accepted output moves back to the one accepted before it, and every later
node that read it goes stale (score/graph). His own accept is refused for an output that did not pass, and for a
worse one unless he writes why (`worse_reason`). Rejects, his accepts, waivers and spend yeses come only from `python
-m score.review` in his own terminal; a hook blocks agents from running them or writing those areas of the store
(.claude/hooks/accept_guard.py).
"""
import datetime
import html
import json

from score import checks
from score.store import RUNNER

# The completion gate's check that fails a place's accepted gaps by name (score/stages/gaps.py). An output whose only
# blocking check is this one is complete apart from accepted gaps (CONTEXT.md): a stage's `gapped` reads it, and the
# runner takes it automatically with that status (overseer, 2026-10-17); any other fail is never taken so.
GAPPED = "accepted gaps"
# The owner's rule of 2026-10-27, his "yes": a passing output of a bought batch is accepted though a measure got worse.
IN_BATCH = ("Inside a bought batch, a result that passes every check is accepted automatically, even when a measure is "
            "worse than before; the drop is written down for you to review after the batch, never as a wait. Accepts "
            "stay yours outside batches.")

STYLE = """
:root { --ground: #fbfaf7; --ink: #1d1d1b; --soft: #6b6a66; --line: #dddad2; --pass: #1f7a3a; --fail: #b3261e;
        --unknown: #8a5a00; color-scheme: light; }
@media (prefers-color-scheme: dark) { :root { --ground: #161614; --ink: #ecebe6; --soft: #a3a29c; --line: #34332f;
        --pass: #6fcf8a; --fail: #ff8a80; --unknown: #f0b85a; color-scheme: dark; } }
body { background: var(--ground); color: var(--ink); font: 15px/1.5 system-ui, sans-serif; margin: 0;
       padding: 24px 16px; }
main { max-width: 980px; margin: 0 auto; }
h1 { font-size: 22px; margin: 0 0 4px; } h2 { font-size: 16px; margin: 28px 0 8px; }
.soft { color: var(--soft); } code { font-size: 13px; overflow-wrap: anywhere; }
.pass { color: var(--pass); } .fail { color: var(--fail); } .unknown { color: var(--unknown); }
.banner { border: 1px solid var(--unknown); padding: 8px 12px; margin: 12px 0; }
.scroll { overflow-x: auto; } table { border-collapse: collapse; width: 100%; }
td, th { border-bottom: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top; }
"""
MOST_FINDINGS = 40

# "Worse than the accepted output" counts only a move a viewer could see (the owner, 2026-10-13: a measure that moved
# where nothing visible changed must not send him a decision). Each measure's tolerance is the smallest move that
# counts as worse; a check whose answer drops (pass, unknown, fail) is worse whatever its measures did, and a check
# that fails still fails: tolerances never touch pass or fail. Kept here, in a framework file, so changing a step
# moves no node's key (score/graph/_code.FRAMEWORK).
# A whole-number measure counts faults, misses or usable things: one more fault (or one fewer usable) is worse.
COUNT_STEP = 1
# Lightness on 0..1 (a halo's or fill's median, a beam's gain, a haze's wash): about 2% of full scale, 5 of 255
# levels, is the step a viewer notices between two pictures; less reads the same.
LIGHTNESS_STEP = 0.02
# A colour gap in 0..255 levels: the same just-noticeable 2%, 5 levels.
LEVEL_STEP = 5.0
# A brightness ratio (the pad lit by the flame over the lamps): 0.05, under the ~6% change in light that the 2%
# lightness step takes.
RATIO_STEP = 0.05
# A share of the picture (effects shown, ground under the horizon showing nothing): one percent of the picture.
PICTURE_SHARE_STEP = 0.01
# A share of the Earth's lit disc: a twentieth of a disc that is itself a small part of the view.
DISC_SHARE_STEP = 0.05
# A length in metres (a moving part's reach into another, a rider's drift, a loop's seam, a wall's thinnest):
# 5 mm, too small to see from where a viewer stands.
LENGTH_STEP = 0.005
# A share of a model's surface in stray islands of a wrong finish: half a percent, half the smallest island that
# counts as stray (patchy.STRAY_ISLAND), so a move no island could make reads the same.
SURFACE_SHARE_STEP = 0.005
# A score no viewer reads directly (a model's likeness to its reference, a fit's spread): any move counts.
NO_STEP = 0.0
# {measure name, or `*<end>` for a family: its step}; a fractional measure named nowhere here counts any move.
TOLERANCES = {
    "halo": LIGHTNESS_STEP, "fill": LIGHTNESS_STEP, "beam": LIGHTNESS_STEP, "veil": LIGHTNESS_STEP,
    "gap": LEVEL_STEP,
    "least brighter": RATIO_STEP, "least over the lamps": RATIO_STEP,
    "least changed": PICTURE_SHARE_STEP, "least changed share shown": PICTURE_SHARE_STEP,
    "worst after": PICTURE_SHARE_STEP,
    "smooth": DISC_SHARE_STEP, "flat_share": DISC_SHARE_STEP,
    "stray": SURFACE_SHARE_STEP,
    "drift": LENGTH_STEP, "miss": LENGTH_STEP, "seam": LENGTH_STEP, "thinnest": LENGTH_STEP,
    "* reach": LENGTH_STEP, "* height drift": LENGTH_STEP,
    "lowest clap": NO_STEP, "lowest": NO_STEP, "best pure": NO_STEP, "spread": NO_STEP, "least edges kept": NO_STEP,
    "least overlap": NO_STEP, "no verdict share": NO_STEP,
}


class Refused(Exception):
    """The store refuses an accept: the output did not pass, is unknown, or is worse with no reason given."""


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")


def record_of(store, node, output=None):
    """The newest finish record of a node, or of the one that made a given output; None when there is none."""
    found = [record for record in store.records(node) if output in (None, record["output"])]
    return found[-1] if found else None


def newest_judgement(store, record):
    found = store.judgements(record["node"], record["key"])
    return found[-1] if found else None


# --- accepts, rejects, waivers and spend yeses -----------------------------------------------------------------

def fails_only_on_gaps(verdicts, waived):
    """Whether the only check of a scorecard that blocks (a waived one aside) is GAPPED, the accepted gaps check."""
    return [name for name, verdict in verdicts.items()
            if checks.blocks(verdict["answer"]) and name not in waived] == [GAPPED]


def gapped_status(verdicts, waived):
    """"complete apart from accepted gaps (N)" for a scorecard that fails only on its accepted gaps, else None."""
    if not fails_only_on_gaps(verdicts, waived):
        return None
    gapped = verdicts[GAPPED]
    return f"complete apart from accepted gaps ({gapped['measures'].get('gaps', len(gapped.get('findings') or ()))})"


def accept_automatically(store, node, output, against=None, bought=False):
    """The runner's accept of an output that passed (or fails only on its accepted gaps: complete apart from accepted
    gaps, its status recorded), is no worse than the accepted one and that the owner has not rejected; the accept,
    or None when one of those does not hold. `against`: the accepted output's scorecard judged now by today's gates
    (the runner's rejudged_accepted), compared in place of the one stored when it was judged. `bought`: the run is a
    bought batch (his checkout or his benchmark grant), where a worse output is accepted too (accept_in_batch)."""
    if store.rejected(node, output):
        return None
    try:
        return accept(store, node, output, RUNNER, "accepted automatically: every gate passed and nothing got worse "
                      "than the accepted output", against=against, on_gaps=True)
    except Refused:
        allowed = within_owners_accept(store, node, output)
    return allowed or (accept_in_batch(store, node, output, against) if bought else None)


def accept_in_batch(store, node, output, against=None):
    """The runner's accept, inside a bought batch, of a passing output worse than the accepted one (IN_BATCH): its
    worse measures written in the accept's status for the owner to review after the batch; None when it did not
    pass."""
    try:
        return accept(store, node, output, RUNNER, "accepted automatically inside a bought batch", worse_reason=IN_BATCH,
                      against=against, on_gaps=True, to_review=True)
    except Refused:
        return None


def owners_allowance(store, node):
    """The owner's newest accept of a worse output of the node (one with his `worse_reason`) that no later reject of
    that output undid, or None."""
    rejected = {reject["output"]: reject["at"] for reject in store.rejects(node)}
    allowed = [given for given in store.accepts(node) if given["by"] != RUNNER and given.get("worse_reason")
               and given["at"] > rejected.get(given["output"], "")]
    return allowed[-1] if allowed else None


def within_owners_accept(store, node, output):
    """The runner's accept of a passing output that is worse than the accepted one but no worse than the output the
    owner accepted as worse (owners_allowance; within the tolerances), or None: a move beyond what he accepted still
    waits for him."""
    allowance = owners_allowance(store, node)
    record = record_of(store, node, output)
    judgement = record and newest_judgement(store, record)
    if allowance is None or judgement is None:
        return None
    allowed_judgement = newest_judgement(store, record_of(store, node, allowance["output"]))
    if allowed_judgement is None or regressions(judgement["verdicts"], allowed_judgement["verdicts"]):
        return None
    why = f"within the owner's accept of {allowance['at'][:10]} ({allowance['output'][:12]})"
    try:
        return accept(store, node, output, RUNNER, f"accepted automatically: {why}", worse_reason=why)
    except Refused:
        return None


def reject(store, node, output, by, reason):
    """The owner's reject of a node's accepted output, with his reason: the accepted output moves back to the one
    accepted before it, and every later node that read it goes stale. The reject, as written."""
    if store.accepted(node) != output:
        raise Refused(f"{output[:12]} is not {node}'s accepted output; only the accepted output can be rejected")
    if not reason.strip():
        raise Refused("a reject needs a reason")
    written = {"node": node, "output": output, "by": by, "at": now(), "reason": reason}
    store.write_reject(node, written)
    return written


def accept(store, node, output, by, reason="", worse_reason=None, against=None, on_gaps=False, to_review=False):
    """Move the node's accepted output to `output`: refused unless it passed (`on_gaps`, the runner's: or fails only
    on its accepted gaps, recorded with that status) and no score is worse, or the owner says why it may be worse
    (`to_review`: its worse measures go in the status, for him to review). The accept, as written."""
    record = record_of(store, node, output)
    if record is None:
        raise Refused(f"{node} has no output {output}")
    judgement = newest_judgement(store, record)
    waived = store.waivers(node, record["key"])
    status = gapped_status(judgement["verdicts"], waived) if on_gaps and judgement else None
    if judgement is None or (checks.standing(judgement["verdicts"], waived) != checks.PASS and status is None):
        raise Refused(f"{node}'s output {output[:12]} answered {judgement['answer'] if judgement else 'nothing yet'}; "
                      "only a passing output can be accepted")
    worse = worse_than_accepted(store, node, judgement, against)
    if worse and not worse_reason:
        raise Refused(f"{node}'s output {output[:12]} is worse than the accepted one: {'; '.join(worse)}. "
                      "Accept it only with a written reason (--worse).")
    if to_review and worse:
        status = "; ".join(filter(None, [status, f"to review after the batch, worse: {'; '.join(worse)}"]))
    written = {"node": node, "output": output, "key": record["key"], "by": by, "at": now(), "reason": reason,
               **({"status": status} if status else {}), "worse": worse, "worse_reason": worse_reason,
               "allowed": allowed_moves(judgement["verdicts"], accepted_card(store, node, output)) if worse else {}}
    store.write_accept(node, written)
    return written


def worse_than_accepted(store, node, judgement, against=None):
    """How a judgement's scorecard is worse than the accepted output's (`against` when given: judged now), as lines;
    none when nothing is accepted."""
    card = accepted_card(store, node, judgement["output"])
    card = against if against is not None and card else card
    excused = {name for name, old in card.items()
               if name in judgement["verdicts"] and gap_excused(node, name, judgement["verdicts"][name], old)}
    return [line for line in regressions(judgement["verdicts"], card) if line.split(": ", 1)[0] not in excused]


def accepted_gaps_of(node, check):
    """The accepted gaps of a node's gate, read as the gate's own wrapper reads them (score/stages/gaps.py files and
    entries, only a gate GAP_GATES lets a gap move from): the got-worse comparison is one more gate those gaps move
    their objects' faults from (the paper's rule; overseer 2026-10-16)."""
    from score import stages
    from score.stages import gaps
    row, _, place = node.partition("@")
    if not place or check not in stages.GAP_GATES.get(row, ()):
        return []
    declared = gaps.files(place, row)
    return gaps.entries({name: pattern.format(place=place, data=gaps.FOLDER.parents[1])
                         for name, pattern in declared.items()}, row, check)


def gap_excused(node, check, new, old):
    """True when the check's regression is its accepted gaps' alone: every fault of the new verdict that no accepted gap
    of the check covers (gaps.covers: one of its objects, of its kind) was on the accepted one too, by object and
    kind, and grew by less than the comparison's own tolerance (measure_worse, a fault's size lower is better). A
    gap leaves out only its objects' faults it names; any other object at a new or a grown fault still blocks."""
    from score.stages import gaps
    entries = accepted_gaps_of(node, check)
    if not entries:
        return False

    def outside(verdict):
        found = {}
        for finding in verdict.get("findings") or ():
            if not any(gaps.covers(entry, finding) for entry in entries):
                kind, size = fault_kind(finding), fault_size(finding)
                found[kind] = size if kind not in found else max(found[kind], size, key=lambda value: value or 0)
        return found
    before = outside(old)
    return all(kind in before and not grew(kind[1], size, before[kind]) for kind, size in outside(new).items())


def grew(kind, size, before):
    """Whether a fault's size grew past the comparison's tolerance (measure_worse); one with no number grows only
    from none to one."""
    if size is None or before is None:
        return size is not None and before is None
    return measure_worse(kind, "lower", size, before)


def fault_kind(finding):
    """A finding's object and the first word of its fault ("/wreck/Objects/leg_foot_1: tips 0.36: ..." gives
    (object, "tips")): the same fault however its number moved."""
    from score.stages import gaps
    rest = finding.split(": ", 1)[1] if ": " in finding else ""
    return gaps.object_of(finding), rest.split(" ", 1)[0]


def fault_size(finding):
    """The number after a finding's fault word ("...: tips 0.36: ..." gives 0.36), or None."""
    words = (finding.split(": ", 1)[1] if ": " in finding else "").split(" ")
    try:
        return float(words[1].rstrip(":")) if len(words) > 1 else None
    except ValueError:
        return None


def accepted_card(store, node, output):
    """The accepted output's scorecard; {} when nothing is accepted or `output` is the accepted one."""
    accepted = store.accepted(node)
    if accepted is None or accepted == output:
        return {}
    accepted_judgement = newest_judgement(store, record_of(store, node, accepted))
    return accepted_judgement["verdicts"] if accepted_judgement else {}


def allowed_moves(new_card, old_card):
    """What an accept of a worse output allowed: {check: {measure: {"from": accepted value, "to": new value}}} for
    each measure that moved the wrong way by its tolerance or more."""
    found = {}
    for name, old in old_card.items():
        new = new_card.get(name)
        for measure, side in (old.get("better") or {}).items():
            if new and measure in new["measures"] and measure_worse(measure, side, new["measures"][measure],
                                                                  old["measures"][measure]):
                found.setdefault(name, {})[measure] = {"from": old["measures"][measure],
                                                       "to": new["measures"][measure]}
    return found


def tolerance(name, new, old):
    """The smallest move of measure `name` that counts as worse: one for whole numbers, else its TOLERANCES step
    (by name, then by family `*<end>`), else nought."""
    if all(isinstance(value, int) and not isinstance(value, bool) for value in (new, old)):
        return COUNT_STEP
    if name in TOLERANCES:
        return TOLERANCES[name]
    return next((step for key, step in TOLERANCES.items() if key.startswith("*") and name.endswith(key[1:])), NO_STEP)


def measure_worse(name, side, new, old):
    """True when a measure moved the wrong way for its side by at least its tolerance (any move when that is nought)."""
    moved = round(new - old if side == "lower" else old - new, 9)  # 0.32 - 0.30 must reach a 0.02 step
    return moved > 0 and moved >= tolerance(name, new, old)


def regressions(new_card, accepted_card):
    """Each way the new scorecard is worse than the accepted one, as a line: a check's answer dropped, a check the
    accepted one had is missing, or a measure moved the wrong way by its tolerance or more."""
    worse = []
    for name, old in accepted_card.items():
        new = new_card.get(name)
        if new is None:
            worse.append(f"{name}: judged on the accepted output, not on this one")
            continue
        if checks.ANSWERS.index(new["answer"]) > checks.ANSWERS.index(old["answer"]):
            worse.append(f"{name}: {old['answer']} became {new['answer']}")
        for measure, side in old.get("better", {}).items():
            if measure not in new["measures"]:
                continue
            before, after = old["measures"][measure], new["measures"][measure]
            if measure_worse(measure, side, after, before):
                worse.append(f"{name}: {measure} {before} became {after} ({side} is better; worse from "
                             f"{tolerance(measure, after, before)})")
    return worse


def waive(store, node, key, check, by, reason):
    """The owner's waiver of one check of a node's output under one key, with his reason; it ends when the key
    changes. The waiver, as written."""
    record = store.record(node, key)
    if record is None:
        raise Refused(f"{node} has no finish record under {key[:12]}")
    if not reason.strip():
        raise Refused("a waiver needs a reason")
    judgement = newest_judgement(store, record)
    if judgement is None or check not in judgement["verdicts"]:
        raise Refused(f"{node} has no check {check} judged under {key[:12]}")
    waiver = {"node": node, "key": key, "check": check, "by": by, "at": now(), "reason": reason}
    store.write_waiver(node, key, check, waiver)
    return waiver


def spend(store, node, key, euros, by, purpose=None):
    """The owner's override: his yes to one run at its estimate (node `override` for a run outside the runner), with
    what it is for when given."""
    yes = {"node": node, "key": key, "euros": euros, "by": by, "at": now(),
           **({"purpose": purpose} if purpose else {})}
    store.write_spend_yes(node, key, yes)
    return yes


# --- the page --------------------------------------------------------------------------------------------------

def escaped(value):
    return html.escape(str(value))


def answer_cell(answer):
    return f'<span class="{escaped(answer)}">{escaped(answer)}</span>'


def waiver_note(waiver):
    return (f"<p class=unknown>Waived by {escaped(waiver['by'])} at {escaped(waiver['at'])}: "
            f"{escaped(waiver['reason'])}</p>") if waiver else ""


def checks_table(judgement, waived):
    """Each gate's answer, reason, measures and findings, and the owner's waiver where he gave one."""
    rows = []
    for name, verdict in judgement["verdicts"].items():
        measures = ", ".join(f"{key} {value}" for key, value in verdict["measures"].items())
        findings = verdict["findings"][:MOST_FINDINGS]
        more = len(verdict["findings"]) - len(findings)
        listed = "".join(f"<li><code>{escaped(item)}</code></li>" for item in findings)
        listed += f"<li class=soft>and {more} more</li>" if more else ""
        rows.append(f"<tr><td>{escaped(name)}</td><td>{answer_cell(verdict['answer'])}</td>"
                    f"<td>{escaped(verdict['reason'])}{waiver_note(waived.get(name))}<ul>{listed}</ul></td>"
                    f"<td>{escaped(measures)}</td></tr>")
    return ('<div class=scroll><table><tr><th>Check</th><th>Answer</th><th>Reason and findings</th><th>Measures</th>'
            f"</tr>{''.join(rows)}</table></div>")


def record_table(record):
    """The finish record's fields, one row each."""
    shown = ("key", "output", "stage", "place", "contract", "expects", "code", "commit", "uncommitted", "seed",
             "params", "files", "after", "models", "machine", "started", "finished", "minutes", "euros")
    rows = "".join(f"<tr><th>{escaped(name)}</th><td><code>{escaped(json.dumps(record.get(name)))}</code></td></tr>"
                   for name in shown)
    return f"<div class=scroll><table>{rows}</table></div>"


def origin_banner(store, record):
    """A banner for an output that is an old output brought in, never made by its stage."""
    origin = store.checkout(record["output"]) / "origin.json"
    if not origin.exists():
        return ""
    found = json.loads(origin.read_text())
    return (f"<p class=banner><b>Unverified seed.</b> {escaped(found.get('note', ''))} From "
            f"<code>{escaped(found.get('from', ''))}</code>.</p>")


def reject_line(node, output):
    """How the owner rejects the accepted output."""
    return (f"<p>The owner may reject it with the Reject button on the cockpit's page of {escaped(node)}.</p>")


def accept_section(store, record, judgement):
    """Who accepted this output and how the owner rejects it, or what would be worse and how he accepts it."""
    node, output = record["node"], record["output"]
    current = store.current_accept(node)
    accepted = current and current["output"]
    if accepted == output:
        by = "The runner accepted this output automatically" if current.get("by") == RUNNER else "The owner accepted it"
        return f"<p class=pass>{by} ({escaped(current['at'])}).</p>{reject_line(node, output)}"
    lines = [f"<p>Accepted output: <code>{escaped(accepted or 'none yet')}</code>.</p>"]
    if store.rejected(node, output):
        lines.append("<p class=fail>The owner rejected this output.</p>")
    worse = worse_than_accepted(store, node, judgement) if judgement else []
    lines += [f"<p class=fail>Worse than the accepted output: {escaped(line)}</p>" for line in worse]
    if judgement and checks.standing(judgement["verdicts"], store.waivers(node, record["key"])) == checks.PASS:
        lines.append("<p>The runner did not accept it; the owner may, with the Accept button on the cockpit's page of "
                     f"{escaped(node)}{', saying why it may be worse' if worse else ''}.</p>")
    else:
        lines.append("<p class=soft>It cannot be accepted: its gates did not pass.</p>")
    return "".join(lines)


def page_html(store, record):
    """The whole page of one output, from its record, its judgements and the accepts."""
    judgements = store.judgements(record["node"], record["key"])
    judgement = judgements[-1] if judgements else None
    answer = judgement["answer"] if judgement else "not judged"
    waived = store.waivers(record["node"], record["key"])
    earlier = "".join(f"<li>{escaped(item['at'])}: {answer_cell(item['answer'])}</li>" for item in judgements[:-1])
    return (f"<title>{escaped(record['node'])}</title><style>{STYLE}</style><main>"
            f"<h1>{escaped(record['node'])}: {answer_cell(answer)}</h1>"
            f"<p class=soft>Output <code>{escaped(record['output'])}</code>, made {escaped(record['finished'])}</p>"
            f"{origin_banner(store, record)}"
            f"<h2>Gates</h2>{checks_table(judgement, waived) if judgement else '<p>Not judged yet.</p>'}"
            f"<h2>Accept</h2>{accept_section(store, record, judgement)}"
            f"<h2>Earlier judgements of this output</h2><ul>{earlier or '<li class=soft>none</li>'}</ul>"
            f"<h2>Finish record</h2>{record_table(record)}</main>")


def page(store, node, key=None):
    """Write the review page of a node's output (its newest, or the one made under `key`); the page's path."""
    record = store.record(node, key) if key else record_of(store, node)
    if record is None:
        raise FileNotFoundError(f"{node} has no finish record{' under ' + key if key else ''}")
    path = store.cache / "pages" / record["node"] / f"{record['key']}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page_html(store, record))
    return path
