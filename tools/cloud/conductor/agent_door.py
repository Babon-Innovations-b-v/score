"""The agents' door to the conductor: what an agent's ssh may run there, decided here and run marked as an agent's.

sshd runs `/usr/local/bin/score-agent-door` (agent_door.sh) as the forced command of the agents' line in user score's
authorized_keys (cloud-init.yaml: command=...,no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding), and
it runs this file with the checkout's interpreter. The asked command (SSH_ORIGINAL_COMMAND) is split by shlex and run
as an argument list, never through a shell, and only when it is one of these:

    status|plan|price [args]                    python -m score status|plan|price ...
    resume --dry                                python -m score resume --dry
    run <environment> [args] --detach           python -m score run ... --detach --free, with SCORE_FREE_ONLY=1:
                                                a free-only run, every free row for real, paid rows left for the Buy;
                                                `--go <go id>` tags it SCORE_OWNERS_GO, his go recorded by
                                                decide-yes go: a bought batch for review.IN_BATCH (owner, 2026-10-27)
    logs [--lines N]                            python -m score.conductor logs: the newest run logs, fault reports
                                                and the sync, listener, resume and backup journals, secrets left out
    health                                      python -m score.conductor health: the Machine card's health, read
                                                only (writing it is its timer's job)
    disk                                        python -m score.conductor disk: free room and the biggest folders
                                                under $PROPS_HOME (frozen copies, store, cache, logs, ...) and the
                                                whole data disk (outside the home, deleted files still open, kept for
                                                root, what du cannot see), read only
    sweep                                       python -m score.conductor sweep: the data disk's routine sweep, every
                                                step under the warning line (2026-10-30, the owner: "this should be
                                                routine"); a line a step, still under the floor the bigger volume priced
    store-gc [--dry]                            python -m score.conductor store-gc: with no run live, the store's blobs
                                                no file, link or listing names removed (--dry counts only)
    clean-frozen                                python -m score.conductor clean-frozen: remove the frozen copies no
                                                registered run needs and no process works in (2026-10-26: the
                                                data disk full); refused while it cannot tell, never the store or design
    clean-cache                                 python -m score.conductor clean-cache: checkouts' copies made links
                                                to the stored blobs (safe with a run live); with no run live, remove the
                                                store cache's folders made again for free (makes left behind,
                                                checkouts, evidence copies, review pages, scratch); refused with the
                                                reason otherwise; never store/objects, paid drops or work/pixal
    relink-pixal                                python -m score.conductor relink-pixal: work/pixal's files whose bytes
                                                the store holds made hard links to its blobs (safe with a run live:
                                                a file changed in the last 15 min is kept), one summary line
    score-lib status | pull                     python -m score.conductor score-lib: score_lib's checkout after a
                                                fetch, HEAD against origin, ahead and behind, local changes, the newest
                                                push that landed; pull fast-forwards only, refused on local changes or
                                                commits and lists them (2026-10-28: nothing pulled it since boot.sh)
    offload-pixal                               python -m score.conductor offload-pixal: with no run live, work/pixal's
                                                takes committed to score_lib and freed here once read back whole
    checkouts                                  the cockpit's newest checkouts, launches and requests, read only
    stop-batch <reason>                         score.conductor.kill.agent_stop_batch: stop the batch's runs, pools
                                                and parked machines, no latch (owner, 2026-10-25)
    gaps <node>                                 the batch gaps the node's accepted output names (batch-gaps.json):
                                                each gap's name, check and faults, and its batch.log and
                                                finish.log lines saying why a model was not made, read only
    job-log <path>                              a cloud job's log of a run, read only: the path under
                                                $PROPS_HOME/frozen (<copy>.home/work/cloud/<call>/job<n>.log, as a
                                                fault report names it), only a file under a frozen home's work/cloud,
                                                its last JOB_LOG_CHARACTERS (2026-10-27: surfaces-bake@campgrounds'
                                                failed jobs, their logs out of reach)
    run-log [--lines N]                         the newest launch's own run log (the log its handles record, under
                                                $PROPS_HOME/logs or a frozen home's logs), its last N lines (default
                                                RUN_LOG_LINES, at most RUN_LOG_LINES_MAX), secrets left out, read only
    fault <node>                                the fault report <home>/store/faults/<node>.txt of the newest launch's
                                                home (its frozen copy while it lives), secrets left out, read only
                                                (2026-10-27: motion@airlock's fault report out of reach)
    predicted                                   the prepared batch's takes (work/checks/prepare/remake.json) that are
                                                a predicted gap, at risk or an input gap: place, rows, route, size
                                                and the reason, read only
    grant-benchmark <euros> <answer> <question> score.adapters.compute.grant_benchmark: the owner's quoted yes,
                                                asked in a Claude Code session, to one benchmark batch of at most
                                                EUR 20
    benchmark <grant id> <environment> [args] --detach
                                                python -m score run ... --detach tagged
                                                SCORE_BENCHMARK_GRANT=<grant id>; refused while the
                                                owner's free-only latch (SCORE_FREE_ONLY) is set
    batch-money                                 python -m score.dashboard batch-money: what a Buy question names,
                                                read only: the batch's spend so far by the money guard's measure with
                                                its parts, this try's likely, high and stop, the batch total it sets
    buy-yes --batch-total <euros> <high euros> <answer> <question>
                                                python -m score.dashboard buy-yes: the owner's quoted yes, asked in a
                                                Claude Code session, to the basket the Buy screen buys now at that
                                                high within that batch total, every try's spend in it (owner,
                                                2026-10-26: "the stop should be a total of the batch, not per try")
                                                (score/dashboard/checkout/chat_yes.py); prints its id
    buy <yes id>                                python -m score.dashboard buy: his Buy under that yes, once, as his
                                                click (the same checkout, stop line and refusals); again, a retry
                                                of its batch inside the batch's budget, no new ask (owner,
                                                2026-10-26); refused while the free-only latch is set
    decide-yes <decision> <target> [--output H] [--check C] [--sha S] [--reason R] [--worse-reason W] <answer>
               <question>                       python -m score.dashboard decide-yes: the owner's quoted yes, asked in
                                                a Claude Code session, to one accept, reject, waive, lock-concept,
                                                lock-film or go, its target as it stands now (owner, 2026-10-27: "i
                                                hate the rule that i cant make discisions in chat aswell")
                                                (score/dashboard/sync/chat_decisions.py); prints its id
    decide <yes id>                             python -m score.dashboard decide: that decision, once, through the
                                                cockpit's own request code as his click; refused when its target
                                                changed since the question
    store-pull                                  a tar stream on stdout of what a run reads (PULLED: the store's
                                                objects, the design, the work folder, the Google answer cache,
                                                score_lib's file cache), leaving out every file whose path, size
                                                and whole-second mtime the manifest on stdin already names
                                                (`size<TAB>mtime<TAB>path` lines); never keys, ledgers, run records
                                                or frozen copies (owner, 2026-10-27: the door route for this_pc.py)
    store-push [--missing]                      --missing: of the paths on stdin, those the conductor lacks; else
                                                a tar stream on stdin of new files under PUSHED (store/objects,
                                                work), each only added: a file already there is kept, never
                                                replaced; a link, an absolute path, `..` or a path leaving those
                                                folders is refused

Every command runs with each of the store's agent markers set (score/store AGENT_MARKERS), so the owner-only barrier
(the store refusing owner areas in an agent's process) holds over ssh; `buy` lifts them in its own process only for
the one checkout his yes covers, once that yes passed every check and is marked used (score.review.web
as_owner_under), and `decide` likewise for the one decision his yes covers (as_owner_deciding). Anything else is refused with the reason, exit
126. The env file (~/.config/score/dashboard.env) is read as data, NAME=value lines, never run.
"""
import os
import pathlib
import re
import shlex
import shutil
import sys
import tarfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score.store import AGENT_MARKERS  # noqa: E402

ENV_FILE = pathlib.Path(os.environ.get("SCORE_DOOR_ENV", "/home/score/.config/score/dashboard.env"))
VERBS = ("status, plan, price, resume --dry, run <environment> ... --detach, logs, health, disk, sweep, store-gc [--dry], clean-frozen, clean-cache, relink-pixal, score-lib status|pull, offload-pixal, checkouts, gaps <node>, job-log <path>, "
         "run-log [--lines N], fault <node>, predicted, store-pull, store-push [--missing], "
         "grant-benchmark, benchmark, batch-money, buy-yes --batch-total, buy <yes id>, decide-yes, decide <yes id>, "
         "stop-batch <reason>")
# The cockpit's newest checkouts, launches and requests with their answers, read only (2026-10-24: a Buy the conductor
# applied launched nothing and nothing outside said why).
# Stop this batch from an agent (owner, 2026-10-25: "this is also something u should just do urself"): its runs,
# pools and parked machines, no latch.
STOP_CODE = ("import json, sys; from score.conductor import kill; "
             "print('stopped the batch: ' + json.dumps(kill.agent_stop_batch(sys.argv[1])))")
CHECKOUTS_CODE = (
    "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'score.dashboard.site.settings'); django.setup(); "
    "from django.apps import apps; "
    "[print(model.__name__, row.pk, getattr(row, 'kind', ''), row.state, str(getattr(row, 'detail', '') or "
    "getattr(row, 'result', ''))[:400]) for model in apps.get_models() if model.__name__ in ('Checkout', 'Launch', "
    "'SyncRequest') for row in model.objects.order_by('-pk')[:5]]")
# One node's batch gaps, read only (2026-10-24: the cockpit listed 147 close-up gaps and the door could not say why),
# and the lines of its output's batch and finish logs that say why a model was not made (2026-10-26: galley's jars
# and oven, "Pixal3D made no model", their reason only in batch.log).
GAPS_CODE = (
    "import sys; from score.store import Store; store = Store.default(); node = sys.argv[1]; "
    "output = store.accepted(node); "
    "gaps = (store.read_file(output, 'batch-gaps.json') or {}).get('gaps', []) if output else []; "
    "print(f'{node}: accepted output {output}, {len(gaps)} batch gaps'); "
    "[print(gap['name'], '|', gap['check'], '|', ' ; '.join(gap['faults'])) for gap in gaps]; "
    "logs = {name: store.objects.read_bytes(f'blobs/{sha}').decode(errors='replace') for name, sha in "
    "(store.listing(output) if output else {}).items() if name in ('batch.log', 'finish.log')}; "
    "[print(f'{name}: {line.strip()}') for name, text in sorted(logs.items()) for line in text.splitlines() "
    "if any(word in line for word in ('gaps (', 'not made', 'failed', 'Error', 'deadline'))]")
# The prepared batch's takes that may not stand, read only (2026-10-26: the retry's predicted failures were read off
# the cockpit by hand), and the backdrop rows no place makes (2026-10-26: the sync pass counted 6 and named none).
PREDICTED_CODE = (
    "import json; from score.store import PROPS_HOME; path = PROPS_HOME / 'work/checks/prepare/remake.json'; "
    "takes = json.loads(path.read_text()).get('takes', []) if path.is_file() else []; "
    "shown = [take for take in takes if take['status'] in ('input gap', 'no maker') "
    "or take['prediction']['outcome'] in ('predicted gap', 'at risk')]; "
    "print(f'{path}: {len(takes)} takes, {len(shown)} predicted gap, at risk, input gap or no maker'); "
    "[print(take['place'], '|', ','.join(take['rows']), '|', take['route'], '|', take.get('size'), '|', "
    "take['status'] if take['status'] in ('input gap', 'no maker') else take['prediction']['outcome'], '|', "
    "' ; '.join(take['inputs']) or take['prediction'].get('mode') or take['prediction'].get('measured')) "
    "for take in shown]")
NODE = re.compile(r"^[a-z0-9][a-z0-9_.-]*(@[a-z0-9_.-]+)?$")
# A grant id is score.store.stamp_key of its UTC time, "+0000" and all (20261026T074845.442617+0000): without the
# plus the door refused every grant the session had written (2026-10-26).
GRANT_ID = re.compile(r"^[A-Za-z0-9._:+-]+$")
GRANT_CODE = ("import sys; from score.adapters.compute import grant_benchmark; "
              "print(grant_benchmark(answer=sys.argv[2], question=sys.argv[3], euros=sys.argv[1])['id'])")
REFUSED_EXIT = 126
JOB_LOG = "--job-log"  # this file's own read of a cloud job's log (the job-log verb runs it)
JOB_LOG_CHARACTERS = 40000
RUN_LOG = "--run-log"  # this file's own read of the newest launch's run log (the run-log verb runs it)
FAULT = "--fault"  # this file's own read of a fault report of the newest launch (the fault verb runs it)
RUN_LOG_LINES, RUN_LOG_LINES_MAX = 200, 2000
# The store's copy to and from the owner's PC (tools/cloud/this_pc.py): what a run reads, and the folders it adds to.
STORE_PULL, STORE_MISSING, STORE_PUSH = "--store-pull", "--store-missing", "--store-push"
PULLED = ("store/objects", "design", "work", "cloud/google-cache", "cache/library")
PUSHED = ("store/objects", "work")


class Refused(Exception):
    """A command the door will not run, with why."""


def words_of(asked):
    """The asked command's words; Refused when there is none or it does not split."""
    if not (asked or "").strip():
        raise Refused(f"no shell here; name one of: {VERBS}")
    try:
        return shlex.split(asked)
    except ValueError as error:
        raise Refused(f"could not read the command ({error})") from None


def env_file_values(path):
    """{name: value} of the env file's NAME=value lines (quotes round a value dropped), or {} when unreadable."""
    try:
        lines = pathlib.Path(path).read_text().splitlines()
    except OSError:
        return {}
    found = {}
    for line in lines:
        name, equals, value = line.partition("=")
        value = value.strip()
        if equals and name.strip() and not name.lstrip().startswith("#"):
            found[name.strip()] = value[1:-1] if len(value) > 1 and value[0] == value[-1] in "'\"" else value
    return found


def latched(values):
    """True while the owner's free-only latch is set in the env file."""
    return values.get("SCORE_FREE_ONLY", "") not in ("", "0")


def detached(args, verb):
    if "--detach" not in args:
        raise Refused(f"{verb} only with --detach: the run goes on in its own session and logs its result line")


def decide(words, latch):
    """(argv after the interpreter, extra environment) for an allowed command; Refused for anything else."""
    verb, args = words[0], words[1:]
    if verb in ("status", "plan", "price"):
        return ["-m", "score", verb, *args], {}
    if verb == "resume":
        if args != ["--dry"]:
            raise Refused("resume only as resume --dry: starting runs again is the boot's job")
        return ["-m", "score", "resume", "--dry"], {}
    if verb == "run":
        if not args or args[0].startswith("-"):
            raise Refused("run names an environment first")
        detached(args, verb)
        return go_tagged(args)
    if verb == "logs":
        return ["-m", "score.conductor", "logs", *args], {}
    if verb == "health":
        if args:
            raise Refused("health takes no arguments: writing it is its timer's job")
        return ["-m", "score.conductor", "health"], {}
    if verb in ("disk", "sweep", "clean-frozen", "clean-cache", "relink-pixal", "offload-pixal"):
        if args:
            raise Refused(f"{verb} takes no arguments")
        return ["-m", "score.conductor", verb], {}
    if verb == "store-gc":
        if args not in ([], ["--dry"]):
            raise Refused("store-gc or store-gc --dry")
        return ["-m", "score.conductor", verb, *args], {}
    if verb == "score-lib":
        if args not in (["status"], ["pull"]):
            raise Refused("score-lib status or score-lib pull")
        return ["-m", "score.conductor", verb, *args], {}
    if verb == "checkouts":
        if args:
            raise Refused("checkouts takes no arguments")
        return ["-c", CHECKOUTS_CODE], {}
    if verb == "gaps":
        if len(args) != 1 or not NODE.match(args[0]):
            raise Refused("gaps <node>, one node name such as closeup@hub")
        return ["-c", GAPS_CODE, args[0]], {}
    if verb == "job-log":
        if len(args) != 1 or not args[0].strip() or ".." in pathlib.PurePath(args[0]).parts:
            raise Refused("job-log <path under $PROPS_HOME/frozen>, such as <copy>.home/work/cloud/<call>/job3.log")
        return [str(pathlib.Path(__file__).resolve()), JOB_LOG, args[0]], {}
    if verb == "run-log":
        if args and (len(args) != 2 or args[0] != "--lines" or not args[1].isdigit() or int(args[1]) < 1):
            raise Refused("run-log [--lines N], N a whole number of lines")
        lines = min(int(args[1]) if args else RUN_LOG_LINES, RUN_LOG_LINES_MAX)
        return [str(pathlib.Path(__file__).resolve()), RUN_LOG, str(lines)], {}
    if verb == "fault":
        if len(args) != 1 or not NODE.match(args[0]):
            raise Refused("fault <node>, one node name such as motion@airlock")
        return [str(pathlib.Path(__file__).resolve()), FAULT, args[0]], {}
    if verb == "predicted":
        if args:
            raise Refused("predicted takes no arguments")
        return ["-c", PREDICTED_CODE], {}
    if verb == "grant-benchmark":
        if len(args) != 3:
            raise Refused("grant-benchmark <euros> <the owner's answer> <the question he answered>")
        return ["-c", GRANT_CODE, *args], {}
    if verb == "benchmark":
        return benchmark(args, latch)
    if verb == "batch-money":
        if args:
            raise Refused("batch-money takes no arguments")
        return ["-m", "score.dashboard", "batch-money"], {}
    if verb == "buy-yes":
        if len(args) != 5 or args[0] != "--batch-total":
            raise Refused("buy-yes --batch-total <euros> <high euros> <the owner's answer> <the question he answered>")
        return ["-m", "score.dashboard", "buy-yes", *args], {}
    if verb == "buy":
        if len(args) != 1 or not GRANT_ID.match(args[0]):
            raise Refused("buy <yes id>, the id buy-yes printed")
        if latch:
            raise Refused("the owner's free-only latch is set: no Buy")
        return ["-m", "score.dashboard", "buy", args[0]], {"SCORE_FREE_ONLY": None}
    if verb == "decide-yes":
        if len(args) < 4 or args[0].startswith("-"):
            raise Refused("decide-yes <decision> <target> [--output H] [--check C] [--sha S] [--reason R] "
                          "[--worse-reason W] <the owner's answer> <the question he answered>")
        return ["-m", "score.dashboard", "decide-yes", *args], {}
    if verb == "decide":
        if len(args) != 1 or not GRANT_ID.match(args[0]):
            raise Refused("decide <yes id>, the id decide-yes printed")
        return ["-m", "score.dashboard", "decide", args[0]], {}
    if verb == "store-pull":
        if args:
            raise Refused("store-pull takes no arguments: the manifest of what you hold comes on stdin")
        return [str(pathlib.Path(__file__).resolve()), STORE_PULL], {}
    if verb == "store-push":
        if args not in ([], ["--missing"]):
            raise Refused("store-push [--missing]: the paths or the tar stream come on stdin")
        return [str(pathlib.Path(__file__).resolve()), STORE_MISSING if args else STORE_PUSH], {}
    if verb == "stop-batch":
        if len(args) != 1 or not args[0].strip():
            raise Refused("stop-batch <reason>, one quoted reason")
        return ["-c", STOP_CODE, args[0]], {}
    raise Refused(f"{verb} is not a door command; name one of: {VERBS}")


def go_tagged(args):
    """A free-only run's argv and environment, `--go <go id>` taken out as SCORE_OWNERS_GO (the runner checks the go
    is his, score.review.web.owners_go)."""
    if "--go" not in args:
        return ["-m", "score", "run", *args, "--free"], {}
    at = args.index("--go")
    if at + 1 >= len(args) or not GRANT_ID.match(args[at + 1]):
        raise Refused("run ... --go <go id>, the id decide-yes go printed")
    return ["-m", "score", "run", *args[:at], *args[at + 2:], "--free"], {"SCORE_OWNERS_GO": args[at + 1]}


def benchmark(args, latch):
    """A benchmark run tagged with its grant: the one door command that may spend, inside the grant only."""
    if len(args) < 2 or args[1].startswith("-"):
        raise Refused("benchmark <grant id> <environment> [args] --detach")
    if not GRANT_ID.match(args[0]):
        raise Refused(f"{args[0]!r} is not a grant id")
    if latch:
        raise Refused("the owner's free-only latch is set: no paid run, benchmark or not")
    detached(args, "benchmark")
    return ["-m", "score", "run", *args[1:]], {"SCORE_BENCHMARK_GRANT": args[0], "SCORE_FREE_ONLY": None}


def environment(values, extra):
    """The command's environment: this one, the env file's values, every agent marker set, the run free unless the
    command lifts it (a benchmark), and no grant or go unless the command names one."""
    env = {**os.environ, **values}
    env.pop("SCORE_BENCHMARK_GRANT", None)
    env.pop("SCORE_OWNERS_GO", None)
    env["SCORE_FREE_ONLY"] = "1"
    for name, value in extra.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    for marker in AGENT_MARKERS:
        env[marker] = "1"
    return env


def job_log(asked, props_home):
    """The tail of a cloud job's log of a run (`asked` under props_home/frozen, or that path whole): only a file
    under a frozen home's work/cloud (`<copy>.home/work/cloud/...`, a link to the home's own work/cloud), read from
    the home's own work/cloud once the frozen home is gone (clean-frozen removes it, the logs stay), at most
    JOB_LOG_CHARACTERS; Refused for anything else."""
    home = pathlib.Path(props_home)
    frozen = home / "frozen"
    named = pathlib.Path(os.path.normpath(frozen / asked))
    parts = named.relative_to(frozen).parts if named.is_relative_to(frozen) else ()
    if len(parts) < 5 or not parts[0].endswith(".home") or parts[1:3] != ("work", "cloud"):
        raise Refused(f"job-log reads only <copy>.home/work/cloud/... under {frozen}, not {asked}")
    allowed = [(frozen / parts[0] / "work" / "cloud").resolve(), (home / "work" / "cloud").resolve()]
    for candidate in (named, home.joinpath("work", "cloud", *parts[3:])):
        found = candidate.resolve()
        if found.is_file() and any(found.is_relative_to(folder) for folder in allowed):
            text = found.read_text(errors="replace")
            return (f"{found} ({len(text)} characters, the last {JOB_LOG_CHARACTERS}):\n"
                    if len(text) > JOB_LOG_CHARACTERS else f"{found}:\n") + text[-JOB_LOG_CHARACTERS:]
    raise Refused(f"no job log at {named}")


def newest_launch_log():
    """The run log the newest launch that records one names (its last handle's log), from the cockpit's database,
    where `checkouts` reads the launches; Refused for none."""
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "score.dashboard.site.settings")
    django.setup()
    from score.dashboard.pages.models import Launch
    for launch in Launch.objects.order_by("-pk"):
        logs = [handle["log"] for handle in launch.handles if handle.get("log")]
        if logs:
            return logs[-1]
    raise Refused("no launch records a run log")


def launch_home(log, props_home):
    """(the log's path, the home it lies in) for a run log under props_home/logs or a frozen home's logs
    (`<copy>.home/logs/score-run-*.log`); Refused for anything else."""
    home = pathlib.Path(props_home)
    named = pathlib.Path(os.path.normpath(log))
    owner = named.parent.parent
    in_frozen = owner.parent == home / "frozen" and owner.name.endswith(".home")
    if not (named.name.startswith("score-run-") and named.suffix == ".log" and named.parent.name == "logs"
            and (owner == home or in_frozen)):
        raise Refused(f"a launch's run log lies only under {home}/logs or a frozen home's logs, not {log}")
    return named, owner


def read_inside(candidates, folders):
    """The first candidate that is a file inside one of `folders` once links are followed, its lines with secrets
    left out (score.conductor.logs.clean), as (path, lines); None for none."""
    from score.conductor.logs import clean
    allowed = [pathlib.Path(folder).resolve() for folder in folders]
    for candidate in candidates:
        found = pathlib.Path(candidate).resolve()
        if found.is_file() and any(found.is_relative_to(folder) for folder in allowed):
            return found, clean(found.read_text(errors="replace").splitlines())
    return None


def run_log(log, props_home, lines):
    """The last `lines` lines of a launch's run log, read where it lies or in props_home/logs once its frozen home
    is gone; Refused for a log outside those or missing."""
    named, owner = launch_home(log, props_home)
    logs = pathlib.Path(props_home) / "logs"
    read = read_inside((named, logs / named.name), (owner / "logs", logs))
    if read is None:
        raise Refused(f"no run log at {named}")
    found, text = read
    return "\n".join([f"{found} (the last {lines} of {len(text)} lines):", *text[-lines:]])


def fault(log, node, props_home):
    """A node's fault report (<home>/store/faults/<node>.txt) of the launch whose run log is `log`: its home's, or
    props_home's once the frozen home is gone; Refused for a bad node name or no report."""
    if not NODE.match(node):
        raise Refused(f"{node!r} is not a node name")
    _, owner = launch_home(log, props_home)
    folders = (owner / "store" / "faults", pathlib.Path(props_home) / "store" / "faults")
    read = read_inside([folder / f"{node}.txt" for folder in folders], folders)
    if read is None:
        raise Refused(f"no fault report for {node} at {folders[0]}")
    found, text = read
    return "\n".join([f"{found}:", *text])


def own_read(argv, props_home):
    """The text of one of this file's own reads (job-log, run-log, fault), as the door's verb asked it."""
    if argv[0] == JOB_LOG:
        return job_log(argv[1], props_home)
    if argv[0] == RUN_LOG:
        return run_log(newest_launch_log(), props_home, int(argv[1]))
    return fault(newest_launch_log(), argv[1], props_home)


def manifest(home, folders):
    """`size<TAB>mtime<TAB>path` lines of every file and link under `folders` of `home` (links not followed)."""
    lines = []
    for path in walked(pathlib.Path(home), folders):
        status = path.lstat()
        lines.append(f"{status.st_size}\t{int(status.st_mtime)}\t{path.relative_to(home).as_posix()}\n")
    return "".join(lines)


def walked(home, folders):
    """Every regular file and link under `folders` of `home`, links never followed."""
    for folder in folders:
        for parent, directories, files in os.walk(home / folder):
            for name in sorted(directories) + sorted(files):
                path = pathlib.Path(parent, name)
                if path.is_symlink() or (name in files and path.is_file()):
                    yield path


def held(text):
    """{path: (size, mtime)} of a manifest's lines."""
    found = {}
    for line in text.splitlines():
        size, mtime, path = line.split("\t", 2)
        found[path] = (int(size), int(mtime))
    return found


def store_pull(home, have, out):
    """A tar stream into `out` of PULLED under `home`, without what `have` names at the same size and mtime (a link
    named at all); (files sent, bytes, files the PC already held)."""
    home, sent, size, kept = pathlib.Path(home), 0, 0, 0
    with tarfile.open(fileobj=out, mode="w|") as archive:
        for path in walked(home, PULLED):
            name, status = path.relative_to(home).as_posix(), path.lstat()
            if name in have and (path.is_symlink() or have[name] == (status.st_size, int(status.st_mtime))):
                kept += 1
                continue
            archive.add(path, arcname=name, recursive=False)
            sent, size = sent + 1, size + (0 if path.is_symlink() else status.st_size)
    return sent, size, kept


def push_target(home, name):
    """Where a pushed path lands under `home`: inside PUSHED only, its folder no link out of it; Refused else."""
    parts = pathlib.PurePosixPath(name).parts
    root = next((folder for folder in PUSHED if parts[:len(folder.split("/"))] == tuple(folder.split("/"))), None)
    if name.startswith("/") or ".." in parts or root is None or len(parts) <= len(root.split("/")):
        raise Refused(f"store-push adds files under {', '.join(PUSHED)} only, not {name!r}")
    target = pathlib.Path(home, *parts)
    if not target.parent.resolve().is_relative_to(pathlib.Path(home, root).resolve()):
        raise Refused(f"store-push: {name!r} leads out of {root} through a link")
    return target


def store_missing(home, asked):
    """Of the paths `asked` (one a line), those the conductor's home lacks, one a line."""
    names = [name for name in asked.splitlines() if name]
    return "".join(f"{name}\n" for name in names if not os.path.lexists(push_target(home, name)))


LANDING = ("store/objects/blobs/", "store/objects/outputs/")  # land first, in this order: what a record names


def landing_rank(name):
    """A pushed path's place in the landing order: blobs, then output listings, then everything else (records,
    accepts, judgements and work, which name them)."""
    return next((rank for rank, prefix in enumerate(LANDING) if name.startswith(prefix)), len(LANDING))


def store_push(home, stream):
    """Adds each regular file of the tar `stream` under PUSHED, never replacing one already there; (added, bytes,
    kept). The whole stream is written and synced under home/tmp first, and only then linked in place (atomic, refused
    when the path exists), blobs before the listings that name them before the records that name those, each folder
    synced: a stream cut short (a full disk, a dropped ssh) lands nothing, and a crash never leaves a record naming an
    output whose listing is missing or empty (2026-10-31: a settle@airlock record without its listing broke
    batch-money's page; the push had landed files in the folders' disk order, unsynced, through a full disk)."""
    home, parts = pathlib.Path(home), []
    temporary = home / "tmp" / "this-pc-push"
    temporary.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(fileobj=stream, mode="r|") as archive:
            for member in archive:
                if member.isdir():
                    continue
                if not member.isfile():
                    raise Refused(f"store-push takes regular files only, not {member.name!r}")
                target = push_target(home, member.name)
                part = temporary / f"{os.getpid()}-{len(parts)}"
                parts.append((member.name, target, part, member.size))
                with archive.extractfile(member) as source, open(part, "wb") as written:
                    shutil.copyfileobj(source, written)
                    written.flush()
                    os.fsync(written.fileno())
        return landed(sorted(parts, key=lambda row: landing_rank(row[0])))
    finally:
        for _, _, part, _ in parts:
            part.unlink(missing_ok=True)


def landed(parts):
    """Each written part linked at its target in the order given, its folder synced after; (added, bytes, kept)."""
    added, size, kept = 0, 0, 0
    for _, target, part, length in parts:
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(part, target)
            added, size = added + 1, size + length
        except FileExistsError:
            kept += 1
            continue
        folder = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(folder)
        finally:
            os.close(folder)
    return added, size, kept


def store_move(flag, home):
    """One of the store's copies (store-pull, store-push --missing, store-push) over stdin and stdout; its summary."""
    if flag == STORE_MISSING:
        sys.stdout.write(store_missing(home, sys.stdin.read()))
        return "store-push --missing: listed"
    if flag == STORE_PULL:
        sent, size, kept = store_pull(home, held(sys.stdin.read()), sys.stdout.buffer)
        return f"store-pull: sent {sent} files ({size / 1e9:.2f} GB), {kept} already on the PC"
    added, size, kept = store_push(home, sys.stdin.buffer)
    return f"store-push: added {added} files ({size / 1e9:.2f} GB), kept {kept} already there"


def main():
    if sys.argv[1:2] in ([STORE_PULL], [STORE_MISSING], [STORE_PUSH]):
        from score.store import PROPS_HOME
        try:
            print(store_move(sys.argv[1], PROPS_HOME), file=sys.stderr)
        except Refused as refused:
            print(f"score-agent-door: refused: {refused}", file=sys.stderr)
            return REFUSED_EXIT
        return 0
    if sys.argv[1:2] in ([JOB_LOG], [RUN_LOG], [FAULT]):
        from score.store import PROPS_HOME
        try:
            print(own_read(sys.argv[1:], PROPS_HOME))
        except Refused as refused:
            print(f"score-agent-door: refused: {refused}", file=sys.stderr)
            return REFUSED_EXIT
        return 0
    try:
        values = env_file_values(ENV_FILE)
        argv, extra = decide(words_of(os.environ.get("SSH_ORIGINAL_COMMAND")), latched(values))
    except Refused as refused:
        print(f"score-agent-door: refused: {refused}", file=sys.stderr)
        return REFUSED_EXIT
    os.chdir(REPO)
    python = str(REPO / ".venv" / "bin" / "python")
    os.execve(python, [python, *argv], environment(values, extra))


if __name__ == "__main__":
    sys.exit(main())
