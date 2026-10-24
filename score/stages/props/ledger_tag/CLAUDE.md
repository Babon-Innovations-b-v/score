# score/stages/props/ledger_tag/

`sitecustomize.py` only: a process started with this folder on PYTHONPATH and `SCORE_LEDGER_TAG` set tags every cloud
and Google ledger line it and its children write (compare.py's runs: `compare-<place>-<order>`). Never put this folder
on the path of environment 1's runner, and never edit `tools/cloud/ledger.py` or `google_spend.py` for tagging: they
are in other stages' code versions, and an edit re-keys (re-buys) them.
