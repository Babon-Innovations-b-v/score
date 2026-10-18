# score/stages/library/

The library rows (`__init__.py`'s docstring has the make, `checks.py`'s the gate, `handover.py`'s the report's
shape): `library@<place>` and `library-world` hand every accepted output of a world to the creator's library, so what
is in a world shows up in the library by construction, never by an agent's hand.

- **score never imports the library.** It runs the library's own command (`backend.py`, the template
  `SCORE_LIB_HANDOVER`) and reads only the report it writes, `handover.json`. No provider, host or company name in
  the template, the code or the data: every setting is an environment variable, else a line of
  `$PROPS_HOME/library.env`.
- **Drafts only.** The node never locks, withdraws or deletes an entry; locking is the owner's (the cockpit's library
  actions).
- **The rows are read by nothing**, so a change here re-keys these two rows alone. Never make another row read them,
  and never fold their gate into `complete`: demo-film (paid) reads complete.
- **The report's shape is a contract both ways.** A change is a new version (`handover.VERSION`), never an edit;
  `handover_example.json` holds one full report, and the library repository keeps its own copy of the shape.
- **`traced`** calls the library-finish check's `untraced(stage_file, place, entries, exceptions)` from
  `score/stages/complete/library`; it answers unknown until that module is in. If it lands under another name, wrap it
  in `checks.py`, never edit it here.
- **A library-free world** is an owner's dated decision in `data/checks/library-free.json`; write one only on his
  word.
- `library_test.py` drives the runner over a toy table with a fake library command.
