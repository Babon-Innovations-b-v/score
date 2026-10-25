"""The agents' door to the conductor: what an agent's ssh may run there, decided here and run marked as an agent's.

sshd runs `/usr/local/bin/score-agent-door` (agent_door.sh) as the forced command of the agents' line in user score's
authorized_keys (cloud-init.yaml: command=...,no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding), and
it runs this file with the checkout's interpreter. The asked command (SSH_ORIGINAL_COMMAND) is split by shlex and run
as an argument list, never through a shell, and only when it is one of these:

    status|plan|price [args]                    python -m score status|plan|price ...
    resume --dry                                python -m score resume --dry
    run <environment> [args] --detach           python -m score run ... --detach --free, with SCORE_FREE_ONLY=1:
                                                a free-only run, every free row for real, paid rows left for the Buy
    logs [--lines N]                            python -m score.conductor logs: the newest run logs, fault reports
                                                and the sync, listener, resume and backup journals, secrets left out
    health                                      python -m score.conductor health: the Machine card's health, read
                                                only (writing it is its timer's job)
    checkouts                                   the cockpit's newest checkouts, launches and requests, read only
    gaps <node>                                 the batch gaps the node's accepted output names (batch-gaps.json):
                                                each gap's name, check and faults, read only
    grant-benchmark <euros> <answer> <question> score.adapters.compute.grant_benchmark: the owner's quoted yes,
                                                asked in a Claude Code session, to one benchmark batch of at most
                                                EUR 20
    benchmark <grant id> <environment> [args] --detach
                                                python -m score run ... --detach tagged
                                                SCORE_BENCHMARK_GRANT=<grant id>; refused while the
                                                owner's free-only latch (SCORE_FREE_ONLY) is set
    buy-yes <stop euros> <high euros> <answer> <question>
                                                python -m score.dashboard buy-yes: the owner's quoted yes, asked in a
                                                Claude Code session, to the basket the Buy screen buys now at that high
                                                and stop (score/dashboard/checkout/chat_yes.py); prints its id
    buy <yes id>                                python -m score.dashboard buy: his Buy under that yes, once, as his
                                                click (the same checkout, stop line and refusals); refused while the
                                                free-only latch is set

Every command runs with each of the store's agent markers set (score/store AGENT_MARKERS), so the owner-only barrier
(the store refusing owner areas in an agent's process) holds over ssh; `buy` lifts them in its own process only for
the one checkout his yes covers, once that yes passed every check and is marked used (score.review.web
as_owner_under). Anything else is refused with the reason, exit
126. The env file (~/.config/score/dashboard.env) is read as data, NAME=value lines, never run.
"""
import os
import pathlib
import re
import shlex
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score.store import AGENT_MARKERS  # noqa: E402

ENV_FILE = pathlib.Path(os.environ.get("SCORE_DOOR_ENV", "/home/score/.config/score/dashboard.env"))
VERBS = ("status, plan, price, resume --dry, run <environment> ... --detach, logs, health, checkouts, gaps <node>, "
         "grant-benchmark, benchmark, buy-yes, buy <yes id>")
# The cockpit's newest checkouts, launches and requests with their answers, read only (2026-10-24: a Buy the conductor
# applied launched nothing and nothing outside said why).
CHECKOUTS_CODE = (
    "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'score.dashboard.site.settings'); django.setup(); "
    "from django.apps import apps; "
    "[print(model.__name__, row.pk, getattr(row, 'kind', ''), row.state, str(getattr(row, 'detail', '') or "
    "getattr(row, 'result', ''))[:400]) for model in apps.get_models() if model.__name__ in ('Checkout', 'Launch', "
    "'SyncRequest') for row in model.objects.order_by('-pk')[:5]]")
# One node's batch gaps, read only (2026-10-24: the cockpit listed 147 close-up gaps and the door could not say why).
GAPS_CODE = (
    "import sys; from score.store import Store; store = Store.default(); node = sys.argv[1]; "
    "output = store.accepted(node); "
    "gaps = (store.read_file(output, 'batch-gaps.json') or {}).get('gaps', []) if output else []; "
    "print(f'{node}: accepted output {output}, {len(gaps)} batch gaps'); "
    "[print(gap['name'], '|', gap['check'], '|', ' ; '.join(gap['faults'])) for gap in gaps]")
NODE = re.compile(r"^[a-z0-9][a-z0-9_.-]*(@[a-z0-9_.-]+)?$")
GRANT_ID = re.compile(r"^[A-Za-z0-9._:-]+$")
GRANT_CODE = ("import sys; from score.adapters.compute import grant_benchmark; "
              "print(grant_benchmark(answer=sys.argv[2], question=sys.argv[3], euros=sys.argv[1])['id'])")
REFUSED_EXIT = 126


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
        return ["-m", "score", "run", *args, "--free"], {}
    if verb == "logs":
        return ["-m", "score.conductor", "logs", *args], {}
    if verb == "health":
        if args:
            raise Refused("health takes no arguments: writing it is its timer's job")
        return ["-m", "score.conductor", "health"], {}
    if verb == "checkouts":
        if args:
            raise Refused("checkouts takes no arguments")
        return ["-c", CHECKOUTS_CODE], {}
    if verb == "gaps":
        if len(args) != 1 or not NODE.match(args[0]):
            raise Refused("gaps <node>, one node name such as closeup@hub")
        return ["-c", GAPS_CODE, args[0]], {}
    if verb == "grant-benchmark":
        if len(args) != 3:
            raise Refused("grant-benchmark <euros> <the owner's answer> <the question he answered>")
        return ["-c", GRANT_CODE, *args], {}
    if verb == "benchmark":
        return benchmark(args, latch)
    if verb == "buy-yes":
        if len(args) != 4:
            raise Refused("buy-yes <stop euros> <high euros> <the owner's answer> <the question he answered>")
        return ["-m", "score.dashboard", "buy-yes", *args], {}
    if verb == "buy":
        if len(args) != 1 or not GRANT_ID.match(args[0]):
            raise Refused("buy <yes id>, the id buy-yes printed")
        if latch:
            raise Refused("the owner's free-only latch is set: no Buy")
        return ["-m", "score.dashboard", "buy", args[0]], {"SCORE_FREE_ONLY": None}
    raise Refused(f"{verb} is not a door command; name one of: {VERBS}")


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
    command lifts it (a benchmark), and no grant unless the command names one."""
    env = {**os.environ, **values}
    env.pop("SCORE_BENCHMARK_GRANT", None)
    env["SCORE_FREE_ONLY"] = "1"
    for name, value in extra.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    for marker in AGENT_MARKERS:
        env[marker] = "1"
    return env


def main():
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
