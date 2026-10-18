"""SCORE's dashboard: one ASGI app, Django pages and a FastAPI /api, over the store's state (score/dashboard/CLAUDE.md).

    .venv/bin/python -m score.dashboard serve            # local: beside the store, 127.0.0.1:8780
    .venv/bin/python -m score.dashboard owner <name>     # local: the one owner account, password from a terminal
    .venv/bin/python -m score.dashboard export --out DIR # the state export a hosted dashboard reads
    .venv/bin/python -m score.dashboard sync             # store side: push the export, pull and apply requests
    .venv/bin/python -m score.dashboard check            # Django's own checks of the settings

No stage imports this package and none of its modules is on sys.path: every import is dotted from score.dashboard.
"""
