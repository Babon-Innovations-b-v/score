"""The dashboard's commands.

    .venv/bin/python -m score.dashboard serve             # migrate, read the store, serve on SCORE_BIND (127.0.0.1:8780)
    .venv/bin/python -m score.dashboard owner <name>      # the local owner account (from the owner's own terminal)
    .venv/bin/python -m score.dashboard export --out DIR  # the state export, into DIR
    .venv/bin/python -m score.dashboard sync              # store side: push the export, pull and apply requests
    .venv/bin/python -m score.dashboard check             # Django's checks of the settings
    .venv/bin/python -m score.dashboard web3d <place>     # a place's fresh 3D web copy (web3d/convert.py), free
    .venv/bin/python -m score.dashboard basket [--place P ...]  # what a run on main would buy, its free details
    .venv/bin/python -m score.dashboard basket-item <id> [--title T] [--says S] [--node PATTERN ...] [--picture P ...]
        [--file F ...] [--ask Q --recommend A ...]   # a department's basket item, its words and questions
    .venv/bin/python -m score.dashboard basket-answers   # the owner's answers to the basket's questions, as JSON
"""
import argparse
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
    commands.add_parser("check")
    web3d = commands.add_parser("web3d", help="a place's fresh 3D web copy from its accepted OpenUSD stage")
    web3d.add_argument("place")
    web3d.add_argument("--store", help="the store folder (default $PROPS_HOME/store)")
    web3d.add_argument("--out", help="default SCORE_WEB_COPIES, where the viewer reads it")
    basket = commands.add_parser("basket", help="what a run on main would buy, its items' free details (proposals/)")
    basket.add_argument("--place", action="append", default=[], help="make only this place's details again")
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
    return parser.parse_args(argv)


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


def check():
    from django.core.management import call_command
    call_command("check")


def web3d(place, store, out):
    """Make the place's web copy into the folder this dashboard serves it from (SCORE_WEB_COPIES)."""
    from django.conf import settings

    from score.dashboard.web3d import convert
    convert.main([place, "--store", store or str(settings.SCORE_PROPS_HOME / "store"),
                  "--out", out or str(settings.SCORE_WEB_COPIES)])


def basket(places):
    """Make the basket into the dashboard's home (proposals/make.py): one summary line."""
    from django.conf import settings

    from score.dashboard.proposals import make
    made = make.make(settings.SCORE_HOME, settings.SCORE_PROPS_HOME / "store", tuple(places),
                     say=lambda line: print(line, flush=True))
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
    if options.command == "serve":
        serve()
    elif options.command == "owner":
        owner(options.name)
    elif options.command == "export":
        export(options.out)
    elif options.command == "sync":
        sync()
    elif options.command == "web3d":
        web3d(options.place, options.store, options.out)
    elif options.command == "basket":
        basket(options.place)
    elif options.command == "basket-item":
        basket_item(options)
    elif options.command == "basket-answers":
        basket_answers()
    else:
        check()


if __name__ == "__main__":
    main()
