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
than the accepted output's, and the owner never rejected it; the accept says it is the runner's. The owner may reject
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

def accept_automatically(store, node, output):
    """The runner's accept of an output that passed, is no worse than the accepted one and that the owner has not
    rejected; the accept, or None when one of those does not hold."""
    if store.rejected(node, output):
        return None
    try:
        return accept(store, node, output, RUNNER, "accepted automatically: every gate passed and nothing got worse "
                      "than the accepted output")
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


def accept(store, node, output, by, reason="", worse_reason=None):
    """Move the node's accepted output to `output`: refused unless it passed and no score is worse, or the owner
    says why it may be worse. The accept, as written."""
    record = record_of(store, node, output)
    if record is None:
        raise Refused(f"{node} has no output {output}")
    judgement = newest_judgement(store, record)
    if judgement is None or checks.standing(judgement["verdicts"], store.waivers(node, record["key"])) != checks.PASS:
        raise Refused(f"{node}'s output {output[:12]} answered {judgement['answer'] if judgement else 'nothing yet'}; "
                      "only a passing output can be accepted")
    worse = worse_than_accepted(store, node, judgement)
    if worse and not worse_reason:
        raise Refused(f"{node}'s output {output[:12]} is worse than the accepted one: {'; '.join(worse)}. "
                      "Accept it only with a written reason (--worse).")
    written = {"node": node, "output": output, "key": record["key"], "by": by, "at": now(), "reason": reason,
               "worse": worse, "worse_reason": worse_reason}
    store.write_accept(node, written)
    return written


def worse_than_accepted(store, node, judgement):
    """How a judgement's scorecard is worse than the accepted output's, as lines; none when nothing is accepted."""
    accepted = store.accepted(node)
    if accepted is None or accepted == judgement["output"]:
        return []
    accepted_judgement = newest_judgement(store, record_of(store, node, accepted))
    return checks.regressions(judgement["verdicts"], accepted_judgement["verdicts"] if accepted_judgement else {})


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


def spend(store, node, key, euros, by):
    """The owner's override: his yes to one run at its estimate (node `override` for a run outside the runner)."""
    yes = {"node": node, "key": key, "euros": euros, "by": by, "at": now()}
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
    return ("<p>The owner may reject it in his own terminal: <code>.venv/bin/python -m score.review reject "
            f"{escaped(node)} {escaped(output)} --reason &quot;why&quot;</code></p>")


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
        lines.append("<p>The runner did not accept it; the owner may, in his own terminal: <code>.venv/bin/python -m "
                     "score.review accept "
                     f"{escaped(node)} {escaped(output)}</code>{' --worse &quot;why&quot;' if worse else ''}</p>")
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
