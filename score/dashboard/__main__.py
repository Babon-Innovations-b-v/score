"""The owner's decisions and Buys made in chat, and the store's upkeep pass. The creator cockpit's pages and hosted
side went (owner, 2026-11-16: "cockpit can also go"); these commands are reached from the agents' door
(tools/cloud/conductor/agent_door.py) and tools/cloud/this_pc.py.

    .venv/bin/python -m score.dashboard sync              # the store's upkeep pass (sync/client.py)
    .venv/bin/python -m score.dashboard install-sync --env-file F [--no-pull]   # its systemd user timer (sync/timer.py)
    .venv/bin/python -m score.dashboard basket            # what a run on main would buy (proposals/make.py)
    .venv/bin/python -m score.dashboard basket-item <id> [--title T] [--says S] [--node PATTERN ...] [--picture P ...]
        [--file F ...] [--ask Q --recommend A ...]   # a department's basket item, its words and questions
    .venv/bin/python -m score.dashboard basket-answers   # the owner's answers to the basket's questions, as JSON
    .venv/bin/python -m score.dashboard batch-money   # what a Buy question names, read only: the batch's spend so
        # far by the money guard's measure and its parts, this try's likely, high and stop, the batch total it sets
    .venv/bin/python -m score.dashboard buy-yes --batch-total <euros> <high euros> <answer> <question>
        # the owner's Buy approved in a session: the batch total he approved, this try's high, his answer and the
        # question quoted (checkout/chat_yes.py); its id
    .venv/bin/python -m score.dashboard buy <yes id> [--phase F] [--take-cheap EUR]   # his Buy under that yes, once
        # (checkout/chat_yes.py); with --phase only that phase's rows of the basket (score/stages/phases)
    .venv/bin/python -m score.dashboard decide-yes <decision> <target> ... <answer> <question>   # his decision
        # made in a session, quoted (sync/chat_decisions.py); its id
    .venv/bin/python -m score.dashboard decide <yes id>   # that decision applied once (sync/chat_decisions.py)
"""
import argparse
import json
import os
import pathlib
import sys
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "score.dashboard.site.settings")


def parse(argv):
    parser = argparse.ArgumentParser(prog="score.dashboard", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync")
    install = commands.add_parser("install-sync", help="the upkeep pass's systemd user timer (sync/timer.py)")
    install.add_argument("--env-file", required=True, help="the env file outside the repo the timer reads")
    install.add_argument("--no-pull", action="store_true",
                         help="the conductor's update before each pass, not a pull")
    commands.add_parser("basket", help="what a run on main would buy, grouped into items (proposals/)")
    words = commands.add_parser("basket-item", help="a department's basket item: its words, nodes and questions")
    words.add_argument("item")
    words.add_argument("--title", help="the item's name, as the owner reads it")
    words.add_argument("--node", action="append", default=[], help="a pattern of the paid nodes it takes (any place)")
    words.add_argument("--picture", action="append", default=[], help="a picture it is made from (a plan, a drawing)")
    words.add_argument("--file", action="append", default=[], help="a short text it is made from (a brief)")
    commands.add_parser("basket-answers", help="the owner's answers to the basket's questions, as JSON")
    words.add_argument("--says", help="one plain sentence: the fault in the place this fixes, as the owner sees it")
    words.add_argument("--ask", action="append", default=[], help="a decision only the owner can make (repeat)")
    words.add_argument("--recommend", action="append", default=[], help="the answer you recommend, one an --ask")
    money = commands.add_parser("batch-money", help="the batch's money a Buy question names, read only "
                                                    "(checkout/chat_yes.py)")
    money.add_argument("--no-film", action="store_true", help="this try priced without the demo films' rows")
    yes = commands.add_parser("buy-yes", help="the owner's Buy approved in a session, quoted (checkout/chat_yes.py)")
    yes.add_argument("--batch-total", required=True, help="the batch's whole stop he approved, every try in it")
    yes.add_argument("--no-film", action="store_true", help="his Buy without the demo films: their rows neither "
                                                            "bought nor made")
    for name in ("high", "answer", "question"):
        yes.add_argument(name)
    bought = commands.add_parser("buy", help="his Buy under a yes from buy-yes, once (checkout/chat_yes.py)")
    bought.add_argument("yes")
    bought.add_argument("--phase", help="only that phase's rows of the basket (score/stages/phases); several as a "
                                        "comma list")
    bought.add_argument("--leave-out", help="stages (a comma list) this Buy neither buys nor makes, beside the yes's")
    bought.add_argument("--place", help="only these places' rows (a comma list) and the environment rows they need")
    bought.add_argument("--leave-place", help="every row but these places' (a comma list); a row needing one waits")
    bought.add_argument("--take-cheap", type=float, metavar="EUR",
                        help="take into the basket every row the run would also buy priced under EUR each, in place "
                             "of refusing for it (checkout/flow.cheap_taken)")
    decide_yes = commands.add_parser("decide-yes", help="the owner's decision made in a session, quoted "
                                                        "(sync/chat_decisions.py)")
    decide_yes.add_argument("decision", help="accept, reject, waive, lock-concept, lock-film, go, spend, the "
                                                   "books month (score.review.web.BOOKS_MONTH), stop (an "
                                                   "environment's stop line at --euros) or cap (env1's cap: --euros "
                                                   "--line --start [--month-cap --finish --standing], or --close)")
    decide_yes.add_argument("target", help="the node, place, film, environment, override name or month "
                                                 "(YYYY-MM) it applies to")
    for name in ("output", "check", "sha", "reason", "worse-reason", "euros", "purpose"):
        decide_yes.add_argument(f"--{name}", default="")
    decide_yes.add_argument("--size", default="", help="a film lock's new frame size, WIDTHxHEIGHT")
    decide_yes.add_argument("--under-cap", default="", help="a spend counted under this cap (env1's): env1's spend "
                                                            "for C10, held to its line")
    decide_yes.add_argument("--takes", default="", help="a reject's takes to remake, comma-separated")
    for name in ("line", "start", "month-cap", "finish", "standing"):  # a cap's (chat_decisions.cap_state)
        decide_yes.add_argument(f"--{name}", default="")
    decide_yes.add_argument("--close", action="store_true", help="a cap closed (its film accepted)")
    for name in ("answer", "question"):
        decide_yes.add_argument(name)
    commands.add_parser("decide", help="his decision under a yes from decide-yes, once "
                                       "(sync/chat_decisions.py)").add_argument("yes")
    return parser.parse_args(argv)


def decide_yes(options):
    from score.dashboard.sync import chat_decisions
    migrate()
    try:
        yes = chat_decisions.record(options.decision, options.target, options.answer, options.question,
                                    output=options.output, check=options.check, sha=options.sha,
                                    reason=options.reason, worse_reason=options.worse_reason,
                                    euros=options.euros, purpose=options.purpose, under_cap=options.under_cap,
                                    size=options.size,
                                    takes=sorted(filter(None, options.takes.split(","))), line=options.line,
                                    start=options.start, month_cap=options.month_cap, finish=options.finish,
                                    standing=options.standing, close=options.close or None)
    except chat_decisions.Refused as refused:
        sys.exit(f"decide-yes: refused: {refused}")
    print(f"decide-yes {yes['id']}: {yes['decision']} {json.dumps(yes['target'])}")


def decide(options):
    from score.dashboard.sync import chat_decisions
    migrate()
    try:
        applied = chat_decisions.apply(options.yes)
    except chat_decisions.Refused as refused:
        sys.exit(f"decide {options.yes}: refused: {refused}")
    print(f"decide {options.yes}: {applied.state}: {applied.detail}")
    if applied.state != "done":
        sys.exit(1)


def buy_yes(options):
    from score.dashboard.checkout import chat_yes
    migrate()
    try:
        yes = chat_yes.record(options.batch_total, options.high, options.answer, options.question,
                              leave_out=chat_yes.NO_FILM if options.no_film else ())
    except chat_yes.Refused as refused:
        sys.exit(f"buy-yes: refused: {refused}")
    print(f"buy-yes {yes['id']}: high EUR {yes['high_euros']:.2f}, batch total EUR {yes['batch_total_euros']:.2f}, "
          f"{len(yes['basket']['items'])} items of the basket made at {yes['basket']['made_at']}"
          + (f", without {', '.join(yes['leave_out'])}" if yes["leave_out"] else ""))


def batch_money(no_film=False):
    """Print what a Buy question names (chat_yes.figures), read only, in words, this try without the demo films when
    `no_film`; the figures as JSON last."""
    from score.dashboard.checkout import chat_yes
    from score.dashboard.launch import guard
    found = chat_yes.figures(guard.backend().spend, chat_yes.NO_FILM if no_film else ())
    money, now = found["money"], found["try"]
    print(cap_words(found["cap"]))
    if money is None:
        print(f"Batch {found['batch']}: a new batch, nothing spent of it yet")
    else:
        parts = money["parts"] or {}
        print(f"Batch {found['batch']}, try {found['tries']} the newest: EUR {money['spent']:.2f} spent since its first "
              f"try's line (the money guard's measure, as of {money['as_of']}), EUR {money['in_flight']:.2f} in "
              f"flight; budget EUR {money['budget']:.2f}, EUR {money['left']:.2f} left")
        if found["runs"] is not None:
            print(f"  its runs' own (rows, warm pools, model calls): EUR {found['runs']:.2f}; other spend meanwhile "
                  f"(benchmarks, design calls, the bill over the ledger): EUR {money['spent'] - found['runs']:.2f}")
        if parts:
            print(f"  the environment's books since its first stop line (the batch counts from EUR "
                  f"{money['start']:.2f} of it): cloud EUR {parts['cloud']:.2f} (the higher of bill and ledger; "
                  f"ledger EUR {parts['ledger']:.2f}), model calls EUR {parts['models']:.2f}")
    print(f"This try (the Buy screen's basket now{', without the demo films' if no_film else ''}): likely EUR {now['likely']:.2f}, high EUR {now['high']:.2f}, "
          f"its stop (high plus 10%) EUR {now['stop']:.2f}")
    print(f"Batch {found['batch']} total: at least EUR {found['fits']:.2f} holds this try; a Buy click would set "
          f"EUR {found['click']:.2f}. Ask, then: buy-yes --batch-total <the total he approves> {now['high']:.2f} ...")
    if found["may_stop"]:
        print(f"Under the yes already used (buy <its id>): this try may stop at the batch limit before every step is "
              f"made, EUR {money['left']:.2f} left of the budget against its stop EUR {now['stop']:.2f}")
    print(json.dumps(found))


def cap_words(cap):
    """env1's cap in one line (score.review.web.cap_figure): "env1: EUR X of 300 (bill, all projects)", its stop and
    reading time, or why it is unread."""
    if cap is None:
        return "env1: no cap set"
    if cap.get("counter") is None:
        return f"env1: spend unread ({cap.get('unread')})"
    said = (f"{cap['name']}: EUR {cap['counter']:.2f} of {cap['euros']:g} (bill, all projects), stop line EUR "
            f"{cap['line']:g}, read {(cap.get('at') or '')[:16]}")
    return said + (f"; the last pass could not read: {cap['unread']}" if cap.get("unread") else "") + \
        ("" if cap.get("open") else "; closed")


def buy(options):
    from score import conductor
    from score.conductor import size
    from score.dashboard.checkout import chat_yes
    waits = size.buy_waits()
    if waits:
        grown_first(options, waits)
        return
    migrate()
    try:
        with conductor.holding("buy"):  # the batch size is held while it prices and launches, never shrunk under it
            record, said = chat_yes.buy(options.yes, phase=options.phase, leave_out=options.leave_out,
                                        places=options.place, leave_places=options.leave_place,
                                        take_cheap=options.take_cheap)
    except chat_yes.Refused as refused:
        sys.exit(f"buy {options.yes}{phase_words(options.phase)}: refused: {refused}")
    print(f"buy {options.yes}{phase_words(options.phase)}: {said}")
    if record is None or record.state not in ("launched", "done"):
        sys.exit(1)


def grown_first(options, waits):
    """A Buy on the idle conductor (size.buy_waits): its own command recorded to start again at the boot on the batch
    size (size.ask_grow_for, with its launch settings: the cluster's, the caps) and the grow asked; one line."""
    from score import conductor
    from score.conductor import size
    from score.graph import runs
    from score.store import PROPS_HOME
    asked = [options.yes, *(["--phase", options.phase] if options.phase else []),
             *(["--leave-out", options.leave_out] if options.leave_out else []),
             *(["--place", options.place] if options.place else []),
             *(["--leave-place", options.leave_place] if options.leave_place else []),
             *(["--take-cheap", f"{options.take_cheap:g}"] if options.take_cheap is not None else [])]
    log = PROPS_HOME / "logs" / "buys" / f"buy-{time.strftime('%Y%m%d-%H%M%S')}-{options.yes}-grown.log"
    path = size.ask_grow_for([sys.executable, "-m", "score.dashboard", "buy", *asked], runs.launch_settings(), log,
                             conductor.machine()["batch_cores"])
    print(f"buy {options.yes}{phase_words(options.phase)}: {waits}: asked for the grow (recorded as {path.name}); "
          f"it starts again at the boot on the batch size, its words in {log}")


def phase_words(phase):
    """How a Buy's lines name its phase: " (phase <name>)", nothing without one."""
    return f" (phase {phase})" if phase else ""


def migrate():
    from django.core.management import call_command
    call_command("migrate", interactive=False, verbosity=0)


def sync():
    from score.dashboard import state
    from score.dashboard.sync.client import sync_pass
    from score import conductor
    from score.conductor import size
    from score.graph import stopped
    if size.draining():  # the size timer waits for a gap to shrink an idle machine (2026-11-04: passes left none)
        print("sync: skipped, the idle machine is about to shrink (conductor/draining.json)", flush=True)
        return
    migrate()
    # a stop (the unit's, a shutdown's) exits through the finally blocks, so each step's processes end with the pass
    stopped.stop_on_signals(lambda number: print(f"sync: stopped by signal {number}", flush=True))
    with conductor.holding("sync-pass"):  # the size timer never shrinks the machine under a pass
        print(sync_pass(state.source()))


def install_sync(options):
    """Write and enable the upkeep pass's systemd user timer (sync/timer.py); its words, or why not."""
    from django.conf import settings

    from score.dashboard.sync import timer
    try:
        print(timer.install(settings.SCORE_REPO, options.env_file, pull=not options.no_pull))
    except timer.Refused as refused:
        sys.exit(f"refused: {refused}")


def basket():
    """Make the basket into the dashboard's home (proposals/make.py): one summary line."""
    from django.conf import settings

    from score.dashboard.proposals import make
    made = make.make(settings.SCORE_HOME, settings.SCORE_PROPS_HOME / "store")
    print(f"basket: {len(made['items'])} items, {sum(len(item['nodes']) for item in made['items'])} paid nodes; "
          f"{settings.SCORE_HOME / 'proposals'}")


def declaration(options):
    """A basket item's declared fields from its command line (only those given); SystemExit when a question has no
    recommended answer."""
    if len(options.ask) != len(options.recommend):
        sys.exit("refused: every question needs the answer you recommend (an --ask and a --recommend each)")
    fields = {"title": options.title, "sentence": options.says, "nodes": options.node,
              "pictures": [str(pathlib.Path(path).resolve()) for path in options.picture],
              "files": [str(pathlib.Path(path).resolve()) for path in options.file],
              "questions": [{"ask": ask, "recommended": recommended}
                            for ask, recommended in zip(options.ask, options.recommend)]}
    return {name: value for name, value in fields.items() if value}


def basket_item(options):
    """Keep a department's basket item (records.declared), kept across makes; it shows from the next basket make."""
    from django.conf import settings

    from score.dashboard.proposals import records
    fields = declaration(options)
    if not fields:
        sys.exit("refused: nothing to write (--title, --says, --node, --picture, --file, --ask with --recommend)")
    records.put_declared(settings.SCORE_HOME / "proposals", options.item, fields)
    print(f"basket item {options.item}: {', '.join(sorted(fields))} written; shown from the next basket make")


def basket_answers():
    """Print the owner's answers to the basket's questions (records.answers) as one JSON object."""
    import json

    from django.conf import settings

    from score.dashboard.proposals import records
    print(json.dumps(records.answers(settings.SCORE_HOME / "proposals"), indent=1))


def main(argv=None):
    import django
    django.setup()
    options = parse(argv)
    if options.command == "sync":
        sync()
    elif options.command == "install-sync":
        install_sync(options)
    elif options.command == "basket":
        basket()
    elif options.command == "basket-item":
        basket_item(options)
    elif options.command == "basket-answers":
        basket_answers()
    elif options.command == "batch-money":
        batch_money(options.no_film)
    elif options.command == "buy-yes":
        buy_yes(options)
    elif options.command == "buy":
        buy(options)
    elif options.command == "decide-yes":
        decide_yes(options)
    else:
        decide(options)


if __name__ == "__main__":
    main()
