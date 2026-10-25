"""The dashboard's commands.

    .venv/bin/python -m score.dashboard serve             # migrate, read the store, serve on SCORE_BIND (127.0.0.1:8780)
    .venv/bin/python -m score.dashboard owner <name>      # the local owner account (from the owner's own terminal)
    .venv/bin/python -m score.dashboard export --out DIR  # the state export, into DIR
    .venv/bin/python -m score.dashboard sync              # store side: push the export, pull and apply requests
    .venv/bin/python -m score.dashboard listen            # store side: answer the owner's quick requests at once
    .venv/bin/python -m score.dashboard check             # Django's checks of the settings
    .venv/bin/python -m score.dashboard web3d <place>     # a place's fresh 3D web copy (web3d/convert.py), free
    .venv/bin/python -m score.dashboard basket [--place P ...] [--plan-only]  # what a run would buy, its free details
    .venv/bin/python -m score.dashboard basket-item <id> [--title T] [--says S] [--node PATTERN ...] [--picture P ...]
        [--file F ...] [--ask Q --recommend A ...]   # a department's basket item, its words and questions
    .venv/bin/python -m score.dashboard basket-answers   # the owner's answers to the basket's questions, as JSON
    .venv/bin/python -m score.dashboard release --host REPO --dockerfile PATH --subject S [--commit SHA] [--trailer T]
        # move the hosted cockpit's pinned SCORE_COMMIT to a pushed commit (sync/release.py)
    .venv/bin/python -m score.dashboard install-sync --env-file F [--host REPO --dockerfile PATH] [--secret NAME]
        [--no-pull]  # the owner's one command: the sync's systemd user units, once the cockpit runs this dashboard
                     # (sync/timer.py); on the conductor without --host (the cockpit's /api/sync/pin) and with --no-pull
    .venv/bin/python -m score.dashboard buy-yes <stop euros> <high euros> <answer> <question>
        # the owner's Buy approved in a session, his answer and the question quoted (checkout/chat_yes.py); its id
    .venv/bin/python -m score.dashboard buy <yes id>   # his Buy under that yes, once, as his click (checkout/chat_yes.py)
"""
import argparse
import json
import os
import pathlib
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "score.dashboard.site.settings")


def parse(argv):
    parser = argparse.ArgumentParser(prog="score.dashboard", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve")
    commands.add_parser("owner").add_argument("name")
    commands.add_parser("export").add_argument("--out", required=True)
    commands.add_parser("sync")
    commands.add_parser("listen")
    commands.add_parser("check")
    release = commands.add_parser("release", help="move the hosted cockpit's pinned SCORE_COMMIT to a pushed commit")
    install = commands.add_parser("install-sync", help="the sync's systemd user timer (the owner's one command)")
    for command, required in ((release, True), (install, False)):
        command.add_argument("--host", required=required, help=(
            "the repository that hosts the cockpit (without it, the cockpit's /api/sync/pin names its commit)"))
        command.add_argument("--dockerfile", required=required, help="its Dockerfile with ARG SCORE_COMMIT, in it")
    install.add_argument("--no-pull", action="store_true",
                         help="the conductor's update before each pass, not a pull: the checkout follows the pin")
    release.add_argument("--subject", required=True, help="the host's commit subject, {short} the score commit")
    release.add_argument("--commit", help="the score commit to release (default: this checkout's HEAD)")
    release.add_argument("--trailer", action="append", default=[], help="a trailer line of the host's commit")
    install.add_argument("--env-file", required=True, help="the env file outside the repo the timer reads")
    install.add_argument("--secret", help="the sync token's name in the secret manager")
    web3d = commands.add_parser("web3d", help="a place's fresh 3D web copy from its accepted OpenUSD stage")
    web3d.add_argument("place")
    web3d.add_argument("--store", help="the store folder (default $PROPS_HOME/store)")
    web3d.add_argument("--out", help="default SCORE_WEB_COPIES, where the viewer reads it")
    basket = commands.add_parser("basket", help="what a run on main would buy, its items' free details (proposals/)")
    basket.add_argument("--place", action="append", default=[], help="make only this place's details again")
    basket.add_argument("--plan-only", action="store_true", help="the plan and its items only: no place assembled")
    words = commands.add_parser("basket-item", help="a department's basket item: its words, nodes and questions")
    words.add_argument("item")
    words.add_argument("--title", help="the item's name, as the owner reads it")
    words.add_argument("--node", action="append", default=[], help="a pattern of the paid nodes it takes (any place)")
    words.add_argument("--picture", action="append", default=[], help="a picture it is made from (a plan, a drawing)")
    words.add_argument("--file", action="append", default=[], help="a short text it is made from (a brief)")
    commands.add_parser("basket-answers", help="the owner's answers to the basket's questions, as JSON")
    preview = commands.add_parser("film-preview", help="a film script's free preview, end to end (films/preview)")
    preview.add_argument("film")
    preview.add_argument("--export", help="an existing state export to record from (default: build one now)")
    preview.add_argument("--user", help="the owner's name the takes sign in as (default SCORE_OWNER)")
    preview.add_argument("--keep", action="store_true", help="keep each segment's frames")
    words.add_argument("--says", help="one plain sentence: the fault in the place this fixes, as the owner sees it")
    words.add_argument("--ask", action="append", default=[], help="a decision only the owner can make (repeat)")
    words.add_argument("--recommend", action="append", default=[], help="the answer you recommend, one an --ask")
    yes = commands.add_parser("buy-yes", help="the owner's Buy approved in a session, quoted (checkout/chat_yes.py)")
    for name in ("stop", "high", "answer", "question"):
        yes.add_argument(name)
    commands.add_parser("buy", help="his Buy under a yes from buy-yes, once (checkout/chat_yes.py)").add_argument("yes")
    return parser.parse_args(argv)


def buy_yes(options):
    from score.dashboard.checkout import chat_yes
    migrate()
    try:
        yes = chat_yes.record(options.stop, options.high, options.answer, options.question)
    except chat_yes.Refused as refused:
        sys.exit(f"buy-yes: refused: {refused}")
    print(f"buy-yes {yes['id']}: high EUR {yes['high_euros']:.2f}, stop EUR {yes['stop_euros']:.2f}, "
          f"{len(yes['basket']['items'])} items of the basket made at {yes['basket']['made_at']}")


def buy(options):
    from score.dashboard.checkout import chat_yes
    migrate()
    try:
        record, said = chat_yes.buy(options.yes)
    except chat_yes.Refused as refused:
        sys.exit(f"buy {options.yes}: refused: {refused}")
    print(f"buy {options.yes}: {said}")
    if record is None or record.state not in ("launched", "done"):
        sys.exit(1)


def migrate():
    from django.core.management import call_command
    call_command("migrate", interactive=False, verbosity=0)


def serve():
    """Refuse a non-loopback bind without a trusted proxy; migrate; read the store; run uvicorn."""
    from django.conf import settings

    from score.dashboard.auth.owner import bind_refusal
    refused = bind_refusal(settings.SCORE_BIND, settings.SCORE_PROXY_MODE)
    if refused:
        sys.exit(refused)
    migrate()
    from score.dashboard import state
    from score.dashboard.pages import actions
    state.source().refresh()
    why = actions.decisions_off_why()
    if why:
        print(why, flush=True)
    import uvicorn
    host, port = settings.SCORE_BIND.rsplit(":", 1)
    uvicorn.run("score.dashboard.site.asgi:app", host=host, port=int(port), proxy_headers=False, workers=1)


def owner(name):
    from score.dashboard.auth.owner import Refused, owner_command
    migrate()
    try:
        user = owner_command(name)
    except Refused as refused:
        sys.exit(f"refused: {refused}")
    print(f"owner account {user.username} set; set SCORE_OWNER={user.username} for decisions and launches")


def export(out):
    from django.conf import settings

    from score.dashboard import state
    from score.dashboard.launch import guard
    from score.dashboard.sync import building
    manifest = building.build(state.source(), out, building_time(), settings.SCORE_EXPORT_MAX_MB,
                              guard.backend().spend(), settings.SCORE_REPO)
    print(f"export of {manifest['made_at']} in {out}: {manifest['bytes'] / 1e6:.1f} MB, "
          f"{len(manifest['left_out'])} left out")


def building_time():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def sync():
    from django.conf import settings

    from score.dashboard import state
    from score.dashboard.sync.client import Remote, sync_pass
    if not settings.SCORE_SYNC_URL or len(settings.SCORE_SYNC_TOKEN) < 32:
        sys.exit("refused: sync needs SCORE_SYNC_URL and a SCORE_SYNC_TOKEN of 32+ characters")
    migrate()
    print(sync_pass(Remote(settings.SCORE_SYNC_URL, settings.SCORE_SYNC_TOKEN), state.source()))


def listen():
    """Answer the owner's quick requests (a concept draw, a pick) as they come (sync/listen.py), until stopped."""
    from django.conf import settings

    from score.dashboard import state
    from score.dashboard.sync import listen as listening
    from score.dashboard.sync.client import Remote
    if not settings.SCORE_SYNC_URL or len(settings.SCORE_SYNC_TOKEN) < 32:
        sys.exit("refused: listen needs SCORE_SYNC_URL and a SCORE_SYNC_TOKEN of 32+ characters")
    migrate()
    listening.listen(Remote(settings.SCORE_SYNC_URL, settings.SCORE_SYNC_TOKEN), state.source(),
                     log=lambda line: print(line, flush=True))


def release(options):
    """Pin the host's Dockerfile to a pushed score commit and push it (sync/release.py); its words, or why not."""
    from django.conf import settings

    from score.dashboard.sync import release as releasing
    try:
        print(releasing.release(settings.SCORE_REPO, pathlib.Path(options.host), options.dockerfile, options.subject,
                                options.commit, options.trailer))
    except releasing.Refused as refused:
        sys.exit(f"refused: {refused}")


def install_sync(options):
    """Write and enable the sync's systemd user timer (sync/timer.py); its words, or why not."""
    from django.conf import settings

    from score.dashboard.sync import release as releasing
    from score.dashboard.sync import timer
    if bool(options.host) != bool(options.dockerfile):
        sys.exit("refused: --host and --dockerfile go together (without both, /api/sync/pin names the commit)")
    try:
        print(timer.install(settings.SCORE_REPO, options.env_file, options.host and pathlib.Path(options.host),
                            options.dockerfile, options.secret or timer.SECRET, pull=not options.no_pull))
    except releasing.Refused as refused:
        sys.exit(f"refused: {refused}")


def check():
    from django.core.management import call_command
    call_command("check")


def web3d(place, store, out):
    """Make the place's web copy into the folder this dashboard serves it from (SCORE_WEB_COPIES)."""
    from django.conf import settings

    from score.dashboard.web3d import convert
    convert.main([place, "--store", store or str(settings.SCORE_PROPS_HOME / "store"),
                  "--out", out or str(settings.SCORE_WEB_COPIES)])


def basket(places, plan_only=False):
    """Make the basket into the dashboard's home (proposals/make.py): one summary line."""
    from django.conf import settings

    from score.dashboard.proposals import make
    made = make.make(settings.SCORE_HOME, settings.SCORE_PROPS_HOME / "store", tuple(places),
                     say=lambda line: print(line, flush=True), plan_only=plan_only)
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


def film_preview(options):
    from score.dashboard.films.preview import make
    try:
        out, record = make.make(options.film, options.export, options.user, options.keep)
    except make.Refused as refused:
        raise SystemExit(f"film-preview {options.film}: refused: {refused}")
    bed = json.loads(record.read_text())["bed"]
    print(f"film-preview {options.film}: {out} ({record}; sound bed: {bed})")


def main(argv=None):
    import django
    django.setup()
    options = parse(argv)
    if options.command == "serve":
        serve()
    elif options.command == "owner":
        owner(options.name)
    elif options.command == "export":
        export(options.out)
    elif options.command == "sync":
        sync()
    elif options.command == "listen":
        listen()
    elif options.command == "web3d":
        web3d(options.place, options.store, options.out)
    elif options.command == "basket":
        basket(options.place, options.plan_only)
    elif options.command == "basket-item":
        basket_item(options)
    elif options.command == "basket-answers":
        basket_answers()
    elif options.command == "release":
        release(options)
    elif options.command == "film-preview":
        film_preview(options)
    elif options.command == "install-sync":
        install_sync(options)
    elif options.command == "buy-yes":
        buy_yes(options)
    elif options.command == "buy":
        buy(options)
    else:
        check()


if __name__ == "__main__":
    main()
