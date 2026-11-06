"""The agents' door to the conductor: what an agent's ssh may run there, decided here and run marked as an agent's.

sshd runs `/usr/local/bin/score-agent-door` (agent_door.sh) as the forced command of the agents' line in user score's
authorized_keys (cloud-init.yaml: command=...,no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding), and
it runs this file with the checkout's interpreter. The asked command (SSH_ORIGINAL_COMMAND) is split by shlex and run
as an argument list, never through a shell, and only when it is one of these:

    status|plan|price [args]                    python -m score status|plan|price ...
    preflight <environment> [--phase <name>] [args]
                                                python -m score preflight ...: a phase's free check before it is
                                                queued (plan, imports, warm pool, stock), read only (owner,
                                                2026-11-06: "u check if nothing will fail before it")
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
    store-evict [--dry]                         python -m score.conductor store-evict: with no run live, the store's
                                                blobs sent to the store bucket, each one nothing here reads evicted
                                                once the bucket answers with its size and sha256 (#74; --dry counts)
    clean-frozen                                python -m score.conductor clean-frozen: remove the frozen copies no
                                                registered run needs and no process works in (2026-10-26: the
                                                data disk full); refused while it cannot tell, never the store or design
    clean-scratch                               python -m score.conductor clean-scratch: with no run live, every
                                                entry of work/motion-scratch removed (layer_base's copies a killed
                                                make left; 2026-11-04: 3.3 GB, the disk at 7.3 GB free)
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
    pool-log [--lines N]                        the newest changed warm pool collector log (cloud/pools/<run>/
                                                collector.log) of the newest launch's home, its last N lines, secrets
                                                left out, read only (2026-11-05)
    ps                                          the busiest processes by processor share, their command lines cut,
                                                secrets left out, read only (2026-11-06)
    node-log <node>                             a node's own log of the newest launch, its tail, as it runs, secrets
                                                left out, read only (2026-11-06)
    stack <pid>                                 a run's process's every Python thread stack (SIGUSR1, its own dump
                                                file), the process going on; refused for one that does not catch
                                                SIGUSR1, which it would end (2026-11-06)
    lock-phase <environment> <phase> [--place P] python -m score lock-phase: the phase's stages (score/stages/phases)
                                                standing accepted now, at those places, locked, so a later code
                                                change keeps them (Runner.lock_phase; the runner's bookkeeping, no
                                                owner decision; 2026-11-06)
    cluster-check                               whether this box reaches the tenant cluster: the env file's
                                                SCORE_K8S_* settings, kubectl, the kubeconfig and the jobs'
                                                namespace through its context, read only (2026-11-06)
    fault <node>                               the fault report <home>/store/faults/<node>.txt of the newest launch's
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
    buy <yes id> [--phase <phase>]              python -m score.dashboard buy: his Buy under that yes, once, as his
                                                click (the same checkout, stop line and refusals); again, a retry
                                                of its batch inside the batch's budget, no new ask (owner,
                                                2026-10-26); refused while the free-only latch is set; started in
                                                a session of its own, the door answering at once with its log
                                                (2026-11-04: a Buy pricing on 2 cores outlived its caller's ssh);
                                                with --phase only that phase's rows of the basket, the same yes and
                                                batch total (score/stages/phases; owner, 2026-11-06), several as a
                                                comma list; --leave-out <stage>,... stages it neither buys nor
                                                makes; --cluster <kind>,... its run sends those job kinds to the
                                                tenant cluster (SCORE_CLOUD=k8s, SCORE_CLOUD_KINDS), refused unless
                                                cluster-check passes
    buy-log                                     the tail of the newest Buy's log the door started: its checkout
                                                line and its result
    decide-yes <decision> <target> [--output H] [--check C] [--sha S] [--reason R] [--worse-reason W] [--euros E]
               [--purpose P] <answer> <question>
                                                python -m score.dashboard decide-yes: the owner's quoted yes, asked in
                                                a Claude Code session, to one accept, reject, waive, lock-concept,
                                                lock-film, go, spend override (his yes to one run outside the
                                                runner, named) or google-month (his Google figure for this month,
                                                into the books; both owner 2026-11-02), its target as it stands now
                                                (owner, 2026-10-27: "i hate the rule that i cant make discisions in
                                                chat aswell")
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
    carry --no-op <file>=<why> ... [--skip <node>] [--only <prefix>] [--since <commit>] [--write]
                                                python -m score.stages.surfaces.carry on the conductor's store: the
                                                accepted outputs whose key moved only by a file proved a no-op kept
                                                under their new key (--write stores it; else only listed); refused
                                                while a run is live (2026-11-03: 7f68af46's bodies.py edit would have
                                                re-bought about EUR 1,100 of accepted rows, and the door had no route)
    route-log <path>                            the tail of a people route's log, read only: a .log file under
                                                ~/.farm-factory-motion/candidates/ (2026-11-03: officer-made-route's
                                                chain.log, its fault's cause, was unreadable)
    design-file <path>                          one design file, read only: design/props|plans|surfaces/<name>.json,
                                                at most DESIGN_FILE_BYTES (2026-11-03: lab's and workshop's hand-ins
                                                differed from this PC's and nothing could show how)
    store-push --differs | --replace            --differs: of the `size<TAB>sha256<TAB>path` lines on stdin under
                                                work/pixal/, the paths the conductor holds with other bytes; --replace:
                                                those files from the tar stream on stdin put in place, each old one kept
                                                under work/pixal/replaced/<time>/, refused while a run is live (2026-11-03:
                                                takes remade on the PC kept their old close-ups here, the add-only push
                                                never replacing them, and 22 places' palette rows went due)
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
import datetime
import hashlib
import os
import signal
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score.store import AGENT_MARKERS  # noqa: E402

ENV_FILE = pathlib.Path(os.environ.get("SCORE_DOOR_ENV", "/home/score/.config/score/dashboard.env"))
VERBS = ("status, plan, price, preflight <environment> [--phase P], resume --dry, run <environment> ... --detach, logs, health, disk, sweep, store-gc [--dry], store-evict [--dry], clean-frozen, clean-cache, clean-scratch, relink-pixal, score-lib status|pull, offload-pixal, checkouts, gaps <node>, job-log <path>, design-file <path>, route-log <path>, carry --no-op <file>=<why> ..., "
         "run-log [--lines N], pool-log [--lines N], ps, node-log <node>, stack <pid>, cluster-check, lock-phase <environment> <phase> [--place P], fault <node>, predicted, store-pull, store-push [--missing | --differs | --replace], "
         "grant-benchmark, benchmark, batch-money, buy-yes --batch-total, buy <yes id> [--phase <phase>], buy-log, decide-yes, decide <yes id>, "
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
PHASE = re.compile(r"^[a-z][a-z-]*$")
STAGE_LIST = re.compile(r"^[a-z0-9][a-z0-9-]*(,[a-z0-9][a-z0-9-]*)*$")  # a Buy's phases or stages to leave out  # a phase's name (score/stages/phases); the Buy refuses one that is no phase
GRANT_CODE = ("import sys; from score.adapters.compute import grant_benchmark; "
              "print(grant_benchmark(answer=sys.argv[2], question=sys.argv[3], euros=sys.argv[1])['id'])")
REFUSED_EXIT = 126
JOB_LOG = "--job-log"  # this file's own read of a cloud job's log (the job-log verb runs it)
JOB_LOG_CHARACTERS = 40000
RUN_LOG = "--run-log"  # this file's own read of the newest launch's run log (the run-log verb runs it)
FAULT = "--fault"  # this file's own read of a fault report of the newest launch (the fault verb runs it)
POOL_LOG = "--pool-log"  # this file's own read of the newest launch's warm pool collector log (the pool-log verb)
PROCESSES = "--ps"  # this file's own read of the busiest processes (the ps verb runs it)
STACK = "--stack"  # this file's own ask of a run's process for its Python stacks (the stack verb runs it)
CLUSTER_CHECK = "--cluster-check"  # this file's own look at the tenant cluster (the cluster-check verb runs it)
CLUSTER_SETTINGS = ("SCORE_K8S_CONTEXT", "SCORE_K8S_CLUSTER", "SCORE_K8S_PROJECT")  # the box's, never the repo's
CLUSTER_PROVIDER = "scaleway/tenant"
CLUSTER_SECONDS = 60
NODE_LOG = "--node-log"  # this file's own read of a node's own log of the newest launch (the node-log verb runs it)
PS_LINES = 40
DESIGN_FILE = "--design-file"  # this file's own read of one design file (the design-file verb runs it)
ROUTE_LOG = "--route-log"  # this file's own read of a people route's log (the route-log verb runs it)
CARRY = "--carry"  # this file's own carry, refused while a run is live (the carry verb runs it)
BUY = "--buy"  # this file's own start of a Buy in a session of its own (the buy verb runs it)
BUY_LOG = "--buy-log"  # this file's own read of the newest Buy's log (the buy-log verb runs it)
BUY_LOGS = "logs/buys"  # under PROPS_HOME: one log a Buy the door started
CARRY_FLAGS = ("--no-op", "--skip", "--only", "--since")  # carry's options that take a value
CANDIDATES = pathlib.Path.home() / ".farm-factory-motion" / "candidates"  # the people routes' work folders
DESIGN_FILE_PATH = re.compile(r"design/(props|plans|surfaces)/[A-Za-z0-9_-]+\.json")
DESIGN_FILE_BYTES = 4_000_000
RUN_LOG_LINES, RUN_LOG_LINES_MAX = 200, 2000
# The store's copy to and from the owner's PC (tools/cloud/this_pc.py): what a run reads, and the folders it adds to.
STORE_PULL, STORE_MISSING, STORE_PUSH = "--store-pull", "--store-missing", "--store-push"
STORE_OBJECTS = "store/objects/"  # written once by content and key: a pull sends one the PC names by name alone
STORE_DIFFERS, STORE_REPLACE = "--store-differs", "--store-replace"
REPLACEABLE = "work/pixal/"  # the one folder a push replaces in: the PC remakes takes there in place
REPLACED = "work/pixal/replaced"  # where each replaced file is kept, under the push's time
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
    if verb == "preflight":
        if not args or args[0].startswith("-"):
            raise Refused("preflight names an environment first")
        return ["-m", "score", "preflight", *args], {}
    if verb == "lock-phase":
        if len(args) < 2 or not PHASE.match(args[1]) or args[0].startswith("-") or \
                any(flag != "--place" or not NODE.match(place) for flag, place in zip(args[2::2], args[3::2])) or \
                len(args) % 2:
            raise Refused("lock-phase <environment> <phase> [--place <place> ...]: a phase of the table, its stages "
                          "standing accepted now locked")
        return ["-m", "score", "lock-phase", *args], {}
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
    if verb in ("disk", "sweep", "clean-frozen", "clean-cache", "relink-pixal", "offload-pixal", "clean-scratch"):
        if args:
            raise Refused(f"{verb} takes no arguments")
        return ["-m", "score.conductor", verb], {}
    if verb in ("store-gc", "store-evict"):
        if args not in ([], ["--dry"]):
            raise Refused(f"{verb} or {verb} --dry")
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
    if verb == "pool-log":
        if args and (len(args) != 2 or args[0] != "--lines" or not args[1].isdigit() or int(args[1]) < 1):
            raise Refused("pool-log [--lines N], N a whole number of lines")
        lines = min(int(args[1]) if args else RUN_LOG_LINES, RUN_LOG_LINES_MAX)
        return [str(pathlib.Path(__file__).resolve()), POOL_LOG, str(lines)], {}
    if verb == "ps":
        if args:
            raise Refused("ps takes no arguments")
        return [str(pathlib.Path(__file__).resolve()), PROCESSES], {}
    if verb == "carry":
        return [str(pathlib.Path(__file__).resolve()), CARRY, *carry_args(args)], {}
    if verb == "route-log":
        if len(args) != 1 or not args[0].endswith(".log"):
            raise Refused("route-log <a .log path under ~/.farm-factory-motion/candidates>")
        return [str(pathlib.Path(__file__).resolve()), ROUTE_LOG, args[0]], {}
    if verb == "design-file":
        if len(args) != 1 or not DESIGN_FILE_PATH.fullmatch(args[0]):
            raise Refused("design-file design/props|plans|surfaces/<name>.json, one design file")
        return [str(pathlib.Path(__file__).resolve()), DESIGN_FILE, args[0]], {}
    if verb == "stack":
        if len(args) != 1 or not args[0].isdigit():
            raise Refused("stack <pid>, one process of a run")
        return [str(pathlib.Path(__file__).resolve()), STACK, args[0]], {}
    if verb == "cluster-check":
        if args:
            raise Refused("cluster-check takes nothing")
        return [str(pathlib.Path(__file__).resolve()), CLUSTER_CHECK], {}
    if verb == "node-log":
        if len(args) != 1 or not NODE.match(args[0]):
            raise Refused("node-log <node>, one node name such as surfaces-bake@hub")
        return [str(pathlib.Path(__file__).resolve()), NODE_LOG, args[0]], {}
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
        if args not in ([], ["--no-film"]):
            raise Refused("batch-money [--no-film]")
        return ["-m", "score.dashboard", "batch-money", *args], {}
    if verb == "buy-yes":
        film = args[:1] == ["--no-film"]
        rest = args[1:] if film else args
        if len(rest) != 5 or rest[0] != "--batch-total":
            raise Refused("buy-yes [--no-film] --batch-total <euros> <high euros> <the owner's answer> <the question he "
                          "answered>")
        return ["-m", "score.dashboard", "buy-yes", *args], {}
    if verb == "buy":
        if not args or not GRANT_ID.match(args[0]) or not buy_options(args[1:]):
            raise Refused("buy <yes id> [--phase <phase>[,<phase>...]] [--leave-out <stage>[,<stage>...]] "
                          "[--cluster <kind>[,<kind>...]], the id buy-yes printed")
        if latch:
            raise Refused("the owner's free-only latch is set: no Buy")
        return [str(pathlib.Path(__file__).resolve()), BUY, *args], {"SCORE_FREE_ONLY": None}
    if verb == "buy-log":
        if args:
            raise Refused("buy-log takes no arguments: the newest Buy's log")
        return [str(pathlib.Path(__file__).resolve()), BUY_LOG], {}
    if verb == "decide-yes":
        if len(args) < 4 or args[0].startswith("-"):
            raise Refused("decide-yes <decision> <target> [--output H] [--check C] [--sha S] [--reason R] "
                          "[--worse-reason W] [--euros E] [--purpose P] <the owner's answer> "
                          "<the question he answered>")
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
        flags = {(): STORE_PUSH, ("--missing",): STORE_MISSING, ("--differs",): STORE_DIFFERS,
                 ("--replace",): STORE_REPLACE}
        if tuple(args) not in flags:
            raise Refused("store-push [--missing | --differs | --replace]: the paths or the tar stream come on stdin")
        return [str(pathlib.Path(__file__).resolve()), flags[tuple(args)]], {}
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


def catches(pid, number):
    """Whether process `pid` has a handler of its own for signal `number` (its SigCgt mask in /proc): sent to one
    without, SIGUSR1's default ends it (2026-11-06: the stack verb ended checkout 34's score run, exit -10)."""
    try:
        status = pathlib.Path(f"/proc/{pid}/status").read_text()
    except OSError:
        return False
    mask = next((line.split()[1] for line in status.splitlines() if line.startswith("SigCgt:")), "0")
    return bool(int(mask, 16) >> (int(number) - 1) & 1)


def stack(pid, props_home, wait=2.0):
    """Every Python thread's stack of a run's process `pid` (one whose command line names a frozen copy under
    props_home/frozen): a SIGUSR1, which tools/cloud/batch.py's stacks_on_ask turns into <home>/logs/stacks/<pid>.txt,
    then that file read, secrets left out; the process goes on. Refused for any other process, or one that wrote
    none (2026-11-06: bake calls spun for half an hour, nowhere to see where)."""
    from score.conductor.logs import clean
    frozen = str(pathlib.Path(props_home) / "frozen")
    try:
        command = pathlib.Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except OSError:
        raise Refused(f"no process {pid}") from None
    if frozen not in command:
        raise Refused(f"{pid} is no run's process (its command names no frozen copy)")
    if not catches(pid, signal.SIGUSR1):
        raise Refused(f"{pid} does not catch SIGUSR1, which would end it: only a batch runner dumps its stacks")
    folders = [pathlib.Path(props_home) / "logs" / "stacks",
               *sorted(pathlib.Path(frozen).glob("*.home/logs/stacks"))]
    before = {folder: (folder / f"{pid}.txt").stat().st_size if (folder / f"{pid}.txt").is_file() else 0
              for folder in folders}
    os.kill(pid, signal.SIGUSR1)
    time.sleep(wait)
    for folder in folders:
        path = folder / f"{pid}.txt"
        if path.is_file() and path.stat().st_size > before[folder]:
            text = path.read_text(errors="replace")[before[folder]:]
            return "\n".join([f"{path} ({command[:300]}):", *clean(text.splitlines())])
    raise Refused(f"{pid} wrote no stack (started before the stack dump, or not a batch runner)")


def node_log(log, node, props_home, lines=RUN_LOG_LINES):
    """The last `lines` lines of a node's own log (<home>/store/logs/<node>.log) of the launch whose run log is `log`,
    written as it runs, so a node that has not failed is read too (2026-11-06: fifteen Blender calls at 90% of a core
    for ten minutes, and only a fault report could be read); secrets left out; Refused for a bad name or no log."""
    if not NODE.match(node):
        raise Refused(f"{node!r} is not a node name")
    _, owner = launch_home(log, props_home)
    folders = (owner / "store" / "logs", pathlib.Path(props_home) / "store" / "logs")
    read = read_inside([folder / f"{node}.log" for folder in folders], folders)
    if read is None:
        raise Refused(f"no log for {node} at {folders[0]}")
    found, text = read
    return "\n".join([f"{found} (the last {lines} of {len(text)} lines):", *text[-lines:]])


def pool_log(log, props_home, lines):
    """The last `lines` lines of the warm pool collector log (cloud/pools/<run>/collector.log) newest changed in the
    home of the launch whose run log is `log`, else in props_home's, secrets left out (2026-11-05: Batch 1's pool held
    no machine for 10 min, its collector's heartbeats failing, and nothing an agent could read said why); Refused for
    none."""
    _, owner = launch_home(log, props_home)
    folders = [owner / "cloud" / "pools", pathlib.Path(props_home) / "cloud" / "pools"]
    found = sorted((path for folder in folders if folder.is_dir() for path in folder.glob("*/collector.log")),
                   key=lambda path: path.stat().st_mtime)
    read = read_inside(found[-1:], folders) if found else None
    if read is None:
        raise Refused(f"no pool collector log under {folders[0]}")
    path, text = read
    return "\n".join([f"{path} (the last {lines} of {len(text)} lines):", *text[-lines:]])


def own_read(argv, props_home):
    """The text of one of this file's own reads (job-log, run-log, pool-log, fault, design-file), as the door's verb
    asked it."""
    if argv[0] == DESIGN_FILE:
        return design_file(argv[1], props_home)
    if argv[0] == ROUTE_LOG:
        return route_log(argv[1])
    if argv[0] == JOB_LOG:
        return job_log(argv[1], props_home)
    if argv[0] == RUN_LOG:
        return run_log(newest_launch_log(), props_home, int(argv[1]))
    if argv[0] == POOL_LOG:
        return pool_log(newest_launch_log(), props_home, int(argv[1]))
    if argv[0] == PROCESSES:
        return processes()
    if argv[0] == STACK:
        return stack(int(argv[1]), props_home)
    if argv[0] == CLUSTER_CHECK:
        return cluster_check(os.environ)
    if argv[0] == NODE_LOG:
        return node_log(newest_launch_log(), argv[1], props_home)
    return fault(newest_launch_log(), argv[1], props_home)


def processes(lines=PS_LINES):
    """The busiest `lines` processes by processor share (ps: pid, %cpu, %mem, minutes, its command line cut to 200),
    each line a secret names or shows left out (score.conductor.logs.clean), read only (2026-11-06: every place's
    sim-body row ran Newton on the conductor's processor, load 98 on 16 cores, and nothing an agent could read said
    which rows)."""
    from score.conductor.logs import clean
    done = subprocess.run(["ps", "-eo", "pid,pcpu,pmem,etimes,args", "--sort=-pcpu", "--no-headers"],
                          capture_output=True, text=True, check=True)
    rows = [line.strip()[:600] for line in done.stdout.splitlines()[:lines]]
    return "\n".join(["pid %cpu %mem seconds command", *clean(rows)])


def carry_args(args):
    """The carry verb's arguments as asked, checked: at least one --no-op <repository file>=<why>, each option with
    its value, --write at most once; Refused otherwise."""
    rest, no_ops = list(args), 0
    while rest:
        flag = rest.pop(0)
        if flag == "--write":
            continue
        if flag not in CARRY_FLAGS or not rest or not rest[0].strip() or rest[0].startswith("--"):
            raise Refused(f"carry: {flag!r} is not one of --write, {', '.join(CARRY_FLAGS)} with its value")
        value = rest.pop(0)
        if flag == "--no-op":
            name, _, why = value.partition("=")
            if not why.strip() or not name or ".." in pathlib.PurePath(name).parts or name.startswith("/"):
                raise Refused(f"carry --no-op <repository file>=<why>, not {value!r}")
            no_ops += 1
    if not no_ops or list(args).count("--write") > 1:
        raise Refused("carry --no-op <file>=<why> ... [--skip <node>] [--only <prefix>] [--since <commit>] [--write]")
    return list(args)


def carried(args, home):
    """carry's run on this store, once no run is live (replace_refusal: a run may be making the same nodes)."""
    refused = replace_refusal(home)
    if refused:
        raise Refused(f"carry: {refused}")
    from score.stages.surfaces import carry
    return carry.main(args)


def buy_options(rest):
    """Whether the options after a Buy's yes id are each --phase, --leave-out or --cluster once with a comma list of
    names."""
    seen = set()
    while rest:
        if len(rest) < 2 or rest[0] not in ("--phase", "--leave-out", "--cluster") or rest[0] in seen or \
                not STAGE_LIST.match(rest[1]):
            return False
        seen.add(rest[0])
        rest = rest[2:]
    return True


def cluster_check(environment, kubectl=None):
    """What this box reaches of the tenant cluster (k8s/clusters/tenant.py, SCORE_K8S_PROVIDER=scaleway/tenant): its
    settings in `environment` (the env file's), kubectl, the kubeconfig and the jobs' namespace read through its
    context, read only; a line saying so, else Refused naming every gap (2026-11-06: the Buy's cluster fallback,
    the conductor held none of them)."""
    found = shutil.which("kubectl", path=environment.get("PATH")) if kubectl is None else kubectl
    config = pathlib.Path(environment.get("SCORE_K8S_KUBECONFIG") or pathlib.Path.home() / ".kube" / "config")
    gaps = [f"{name} is not set in the env file" for name in CLUSTER_SETTINGS if not environment.get(name)]
    if environment.get("SCORE_K8S_PROVIDER") != CLUSTER_PROVIDER:
        gaps.append(f"SCORE_K8S_PROVIDER is not {CLUSTER_PROVIDER}")
    gaps += [] if found else ["no kubectl on this box"]
    gaps += [] if config.is_file() else [f"no kubeconfig at {config}"]
    if gaps:
        raise Refused("the tenant cluster is out of reach: " + "; ".join(gaps))
    namespace = environment.get("SCORE_K8S_NAMESPACE", "score-jobs")
    try:
        done = subprocess.run([found, "--kubeconfig", str(config), "--context", environment["SCORE_K8S_CONTEXT"],
                               "get", "namespace", namespace, "-o", "name"], capture_output=True, text=True,
                              timeout=CLUSTER_SECONDS)
    except subprocess.TimeoutExpired:
        raise Refused(f"the tenant cluster did not answer within {CLUSTER_SECONDS} s") from None
    if done.returncode != 0:
        lines = (done.stderr or done.stdout).strip().splitlines()
        raise Refused(f"the tenant cluster refused: {lines[-1] if lines else f'exit {done.returncode}'}")
    return f"the tenant cluster answers: {done.stdout.strip()} through {config}"


def buy_started(yes, home, command=None, phase=None, leave_out=None, cluster=None):
    """`python -m score.dashboard buy <yes> [--phase <phase>]` started in a session of its own, its words in a log
    under home/BUY_LOGS named with the phase, and the door's answer at once: the log's path (2026-11-04: a Buy priced
    on the idle conductor's 2 cores held the ssh past its caller's 15 minutes, the ssh dropped and the Buy was cut
    off, no checkout written). With `cluster` (a comma list of job kinds) its run sends those kinds to the tenant
    cluster (SCORE_CLOUD=k8s, SCORE_CLOUD_KINDS, tools/cloud/k8s), refused unless cluster_check passes."""
    extra = {}
    if cluster:
        cluster_check(os.environ)
        extra = {"SCORE_CLOUD": "k8s", "SCORE_CLOUD_KINDS": cluster}
    folder = pathlib.Path(home) / BUY_LOGS
    folder.mkdir(parents=True, exist_ok=True)
    named = f"{yes}-{phase.replace(',', '+')}" if phase else yes
    log = folder / f"buy-{time.strftime('%Y%m%d-%H%M%S')}-{named}.log"
    asked = [yes, *(["--phase", phase] if phase else []), *(["--leave-out", leave_out] if leave_out else [])]
    with log.open("w") as written:
        subprocess.Popen(command or [sys.executable, "-m", "score.dashboard", "buy", *asked], cwd=REPO,
                         stdin=subprocess.DEVNULL, stdout=written, stderr=subprocess.STDOUT, start_new_session=True,
                         env={**os.environ, **extra})
    asked += ["--cluster", cluster] if cluster else []
    return f"buy {' '.join(asked)}: started in its own session; its checkout and result in {log} (the door's buy-log)"


def buy_log(home):
    """The tail of the newest Buy's log (buy_started), at most JOB_LOG_CHARACTERS; Refused when there is none."""
    logs = sorted((pathlib.Path(home) / BUY_LOGS).glob("buy-*.log"))
    if not logs:
        raise Refused(f"no Buy log under {pathlib.Path(home) / BUY_LOGS}")
    text = logs[-1].read_text(errors="replace")
    return f"{logs[-1]}:\n" + text[-JOB_LOG_CHARACTERS:]


def route_log(asked, candidates=None):
    """The tail of a people route's log: a .log file under CANDIDATES (asked whole or under it), no link out, at most
    JOB_LOG_CHARACTERS; Refused for anything else."""
    folder = pathlib.Path(candidates or CANDIDATES)
    named = pathlib.Path(os.path.normpath(folder / asked))
    if named.suffix != ".log" or not named.resolve().is_relative_to(folder.resolve()) or not named.is_file():
        raise Refused(f"route-log reads a .log file under {folder} only, not {asked}")
    text = named.read_text(errors="replace")
    return (f"{named} ({len(text)} characters, the last {JOB_LOG_CHARACTERS}):\n"
            if len(text) > JOB_LOG_CHARACTERS else f"{named}:\n") + text[-JOB_LOG_CHARACTERS:]


def design_file(name, props_home):
    """One design file's text (DESIGN_FILE_PATH, no link out of design/), at most DESIGN_FILE_BYTES; Refused else."""
    if not DESIGN_FILE_PATH.fullmatch(name):
        raise Refused(f"design-file reads design/props|plans|surfaces/<name>.json only, not {name!r}")
    path = pathlib.Path(props_home, name)
    if not path.resolve().is_relative_to(pathlib.Path(props_home, "design").resolve()) or not path.is_file():
        raise Refused(f"design-file: no such design file {name}")
    if path.stat().st_size > DESIGN_FILE_BYTES:
        raise Refused(f"design-file: {name} is over {DESIGN_FILE_BYTES} bytes")
    return path.read_text()


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
    """A tar stream into `out` of PULLED under `home`, without what `have` names at the same size and mtime (a link,
    or a store object, named at all: the store is written once by content and key, so the same name is the same bytes;
    2026-11-04: a pull sent 138 GB of objects the PC held, their mtimes other); (files sent, bytes, files the PC
    already held)."""
    home, sent, size, kept = pathlib.Path(home), 0, 0, 0
    with tarfile.open(fileobj=out, mode="w|") as archive:
        for path in walked(home, PULLED):
            name, status = path.relative_to(home).as_posix(), path.lstat()
            if name in have and (path.is_symlink() or name.startswith(STORE_OBJECTS)
                                 or have[name] == (status.st_size, int(status.st_mtime))):
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


def evicted_here(home, name):
    """True when `name` is a store blob (store/objects/blobs/<sha>) the conductor evicted into the store bucket (its
    mark, score/store/offload): it is not missing here and is never landed again."""
    from score.store import offload

    parts = pathlib.PurePosixPath(name).parts
    return (len(parts) == 4 and parts[:3] == ("store", "objects", "blobs")
            and offload.mark_of(pathlib.Path(home, "store", "objects"), parts[3]).is_file())


def store_missing(home, asked):
    """Of the paths `asked` (one a line), those the conductor's home lacks and did not evict, one a line."""
    names = [name for name in asked.splitlines() if name]
    return "".join(f"{name}\n" for name in names
                   if not os.path.lexists(push_target(home, name)) and not evicted_here(home, name))


def replaceable_target(home, name):
    """Where a replacing push's path lands: push_target, and only under REPLACEABLE; Refused else."""
    if not name.startswith(REPLACEABLE) or name.startswith(REPLACED + "/"):
        raise Refused(f"store-push --replace replaces files under {REPLACEABLE} only (not its replaced/), not {name!r}")
    return push_target(home, name)


def file_sha(path):
    """The sha256 of a file's bytes, read in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def store_differs(home, asked):
    """Of the `size<TAB>sha256<TAB>path` lines `asked`, the paths the conductor's home holds as a file with other
    bytes (a missing one is store-push --missing's), one a line."""
    found = []
    for line in asked.splitlines():
        if not line:
            continue
        size, sha, name = line.split("\t", 2)
        target = replaceable_target(home, name)
        if target.is_file() and (target.stat().st_size != int(size) or file_sha(target) != sha):
            found.append(f"{name}\n")
    return "".join(found)


def replace_refusal(home):
    """Why work/pixal's files may not be replaced now (a run may read them), or None; a run entry or process that
    cannot be read refuses too."""
    from score.conductor import disk
    from score.graph import runs
    try:
        need = disk.needed(runs.RUNS)
        busy = disk.working(pathlib.Path(home) / "frozen")
    except Exception as unread:  # noqa: BLE001 - Unprovable or unreadable: no replace while it cannot tell
        return f"cannot tell whether a run is live: {unread}"
    if need or busy:
        return f"a run is live ({', '.join(sorted(need)) or ', '.join(sorted(busy))})"
    return None


def store_replace(home, stream, stamp):
    """Puts each regular file of the tar `stream` (under REPLACEABLE only) in place, the file there before kept under
    REPLACED/<stamp>/; one with the same bytes already there is kept as it is. Refused while a run is live
    (replace_refusal). The whole stream is written under home/tmp first; (replaced, bytes, kept)."""
    home = pathlib.Path(home)
    refused = replace_refusal(home)
    if refused:
        raise Refused(f"store-push --replace: {refused}")
    temporary, parts = home / "tmp" / "this-pc-replace", []
    temporary.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(fileobj=stream, mode="r|") as archive:
            for member in archive:
                if member.isdir():
                    continue
                if not member.isfile():
                    raise Refused(f"store-push takes regular files only, not {member.name!r}")
                target = replaceable_target(home, member.name)
                part = temporary / f"{os.getpid()}-{len(parts)}"
                parts.append((member.name, target, part, member.size))
                with archive.extractfile(member) as source, open(part, "wb") as written:
                    shutil.copyfileobj(source, written)
                    written.flush()
                    os.fsync(written.fileno())
        return replaced(home, parts, stamp)
    finally:
        for _, _, part, _ in parts:
            part.unlink(missing_ok=True)


def replaced(home, parts, stamp):
    """Each written part put at its target, the old file first linked under REPLACED/<stamp>/; (replaced, bytes,
    kept)."""
    count, size, kept = 0, 0, 0
    for name, target, part, length in parts:
        if target.is_file() and file_sha(target) == file_sha(part):
            kept += 1
            continue
        if target.exists():
            keep = pathlib.Path(home, REPLACED, stamp, *pathlib.PurePosixPath(name).parts[2:])
            keep.parent.mkdir(parents=True, exist_ok=True)
            os.link(target, keep)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(part, target)
        count, size = count + 1, size + length
    return count, size, kept


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
    batch-money's page; the push had landed files in the folders' disk order, unsynced, through a full disk). A blob
    the conductor evicted into the store bucket (evicted_here) is kept, never landed again."""
    home, parts, evicted = pathlib.Path(home), [], 0
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
                if evicted_here(home, member.name):
                    evicted += 1
                    continue
                part = temporary / f"{os.getpid()}-{len(parts)}"
                parts.append((member.name, target, part, member.size))
                with archive.extractfile(member) as source, open(part, "wb") as written:
                    shutil.copyfileobj(source, written)
                    written.flush()
                    os.fsync(written.fileno())
        added, size, kept = landed(sorted(parts, key=lambda row: landing_rank(row[0])))
        return added, size, kept + evicted
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
    if flag == STORE_DIFFERS:
        sys.stdout.write(store_differs(home, sys.stdin.read()))
        return "store-push --differs: listed"
    if flag == STORE_REPLACE:
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        count, size, kept = store_replace(home, sys.stdin.buffer, stamp)
        return (f"store-push --replace: replaced {count} files ({size / 1e9:.2f} GB), the old ones under "
                f"{REPLACED}/{stamp}; {kept} already the same")
    added, size, kept = store_push(home, sys.stdin.buffer)
    return f"store-push: added {added} files ({size / 1e9:.2f} GB), kept {kept} already there"


def main():
    if sys.argv[1:2] in ([STORE_PULL], [STORE_MISSING], [STORE_PUSH], [STORE_DIFFERS], [STORE_REPLACE]):
        from score.store import PROPS_HOME
        try:
            print(store_move(sys.argv[1], PROPS_HOME), file=sys.stderr)
        except Refused as refused:
            print(f"score-agent-door: refused: {refused}", file=sys.stderr)
            return REFUSED_EXIT
        return 0
    if sys.argv[1:2] in ([BUY], [BUY_LOG]):
        from score.store import PROPS_HOME
        try:
            options = dict(zip(sys.argv[3::2], sys.argv[4::2]))
            print(buy_started(sys.argv[2], PROPS_HOME, phase=options.get("--phase"),
                              leave_out=options.get("--leave-out"), cluster=options.get("--cluster"))
                  if sys.argv[1] == BUY else buy_log(PROPS_HOME))
        except Refused as refused:
            print(f"score-agent-door: refused: {refused}", file=sys.stderr)
            return REFUSED_EXIT
        return 0
    if sys.argv[1:2] == [CARRY]:
        from score.store import PROPS_HOME
        try:
            return carried(carry_args(sys.argv[2:]), PROPS_HOME) or 0
        except Refused as refused:
            print(f"score-agent-door: refused: {refused}", file=sys.stderr)
            return REFUSED_EXIT
    if sys.argv[1:2] in ([JOB_LOG], [RUN_LOG], [POOL_LOG], [PROCESSES], [NODE_LOG], [STACK], [CLUSTER_CHECK], [FAULT], [DESIGN_FILE], [ROUTE_LOG]):
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
