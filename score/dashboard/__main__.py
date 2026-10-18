"""The dashboard's commands.

    .venv/bin/python -m score.dashboard serve             # migrate, read the store, serve on SCORE_BIND (127.0.0.1:8780)
    .venv/bin/python -m score.dashboard owner <name>      # the local owner account (from the owner's own terminal)
    .venv/bin/python -m score.dashboard export --out DIR  # the state export, into DIR
    .venv/bin/python -m score.dashboard sync              # store side: push the export, pull and apply requests
    .venv/bin/python -m score.dashboard check             # Django's checks of the settings
    .venv/bin/python -m score.dashboard web3d <place>     # a place's fresh 3D web copy (web3d/convert.py), free
    .venv/bin/python -m score.dashboard propose <branch> <place>   # a fix branch's proposal for a place, free
    .venv/bin/python -m score.dashboard proposals-finish [--no-before]  # price every proposal, draw its before stills
    .venv/bin/python -m score.dashboard proposal-words <branch> <place> --says "..." [--ask "..." --recommend "..."]
"""
import argparse
import os
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
    propose = commands.add_parser("propose", help="a fix branch's proposal for one place, made for free (proposals/)")
    propose.add_argument("branch")
    propose.add_argument("place")
    propose.add_argument("--media", default=os.environ.get("SCORE_PROPOSAL_MEDIA"),
                         help="a folder of each branch's draft films and sounds, <media>/<branch>/")
    propose.add_argument("--no-stills", action="store_true", help="leave out the Blender stills")
    finishing = commands.add_parser("proposals-finish", help="price every proposal and draw its before stills")
    finishing.add_argument("--no-before", action="store_true", help="price only, no Blender")
    words = commands.add_parser("proposal-words", help="the owner's words of a proposal: what it fixes, a question")
    words.add_argument("branch")
    words.add_argument("place")
    words.add_argument("--says", help="one plain sentence: the fault in the place this fixes, as the owner sees it")
    words.add_argument("--ask", help="a decision only the owner can make, as a question")
    words.add_argument("--recommend", help="the answer you recommend and carry on with")
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


def propose(branch, place, media, with_stills):
    """Make the branch's proposal for the place into the dashboard's home (proposals/propose.py)."""
    from django.conf import settings

    from score.dashboard.proposals import propose as proposing
    try:
        folder = proposing.propose(branch, place, settings.SCORE_HOME, settings.SCORE_PROPS_HOME / "store", media,
                                   with_stills)
    except proposing.Refused as refused:
        sys.exit(f"refused: {refused}")
    print(f"proposal of {branch} at {place}: {folder}")


def proposals_finish(with_before):
    """Price every proposal and draw its before stills where due (proposals/finish.py)."""
    from django.conf import settings

    from score.dashboard.proposals import finish
    root = settings.SCORE_HOME / "proposals"
    changed = finish.finish_all(root, settings.SCORE_PROPS_HOME / "store", with_before)
    names = ", ".join(f"{branch}@{place}" for branch, place in changed) or "none due"
    print(f"finished {len(changed)} proposals: {names}")


def proposal_words(branch, place, says, ask, recommend):
    """Write the owner's words into a made proposal (records.WORDS)."""
    from django.conf import settings

    from score.dashboard.proposals import records
    if bool(ask) != bool(recommend):
        sys.exit("refused: a question needs the answer you recommend (--ask with --recommend)")
    fields = {name: value for name, value in (("sentence", says), ("question", ask), ("recommended", recommend))
              if value}
    if not fields:
        sys.exit("refused: nothing to write (--says, --ask with --recommend)")
    if records.amend(settings.SCORE_HOME / "proposals", branch, place, fields) is None:
        sys.exit(f"refused: no proposal of {branch} at {place}: python -m score.dashboard propose {branch} {place}")
    print(f"proposal of {branch} at {place}: {', '.join(sorted(fields))} written")


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
    elif options.command == "propose":
        propose(options.branch, options.place, options.media, not options.no_stills)
    elif options.command == "proposals-finish":
        proposals_finish(not options.no_before)
    elif options.command == "proposal-words":
        proposal_words(options.branch, options.place, options.says, options.ask, options.recommend)
    else:
        check()


if __name__ == "__main__":
    main()
