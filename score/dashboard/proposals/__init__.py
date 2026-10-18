"""Proposals: what a fix branch would change in one place, made for free on this machine before anything is bought.

    .venv/bin/python -m score.dashboard propose <branch> <place> [--media DIR] [--no-stills]

A proposal is one item of the owner's shopping list: the branch's place assembled from its own code and data over the
store's accepted outputs (a layer it cannot make for free is named "needs the paid batch" and shown as it stands
now), its 3D web copy, a few small stills, the draft films and sounds the branch made, and one sentence of what it
changes. `records.py` is the layout (the dashboard's home and the state export alike), `branch.py` the git side,
`assemble.py` the run inside the branch's scratch checkout, `drawing.py` what the after and the before both draw,
`pictures.py` the stills and media, `compare.py` the after against the before (no change, held), `propose.py` the
command, `exporting.py` the files the state export carries.
"""
