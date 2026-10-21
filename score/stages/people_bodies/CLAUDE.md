# score/stages/people_bodies/

The people's body rows (#5, experimental): `made_clips.py` (`people-clips-made`, paid: the Kimodo clips with the
fixed seed and the mean rig every body plays, made inside the batch, #26), `bodies.py` (`people-look-parts-<look>`,
paid: the look's parts, its own priced row, never bought inside the body; `people-body-<look>`, paid: the maker's
build, the people route and checks, and every body gate), `clips.py` (the body judged clip by clip;
`people-clips`' make), `far.py` (a far-only look's gates) and `full.py` (which looks get a full body: from the
design alone, a person row of `data/people/rows.json` filling at least FAR_SHARE of its locked concept's frame height,
its `share`; a crowd far always; no hand-written list of looks decides it, the completion gate's far check reads the
same rule). The people package (`../people/`) builds the table's rows from them; its overlay holds the gates'
rules.

- **Keep this package's `__init__.py` empty of imports.** A body row's code version takes in its package's
  `__init__`; in the people package that pulled in the whole surface stage, so every surface edit re-keyed (and
  re-bought) every body (2026-10-13). Import nothing here from `score.stages.people`.
- Tests: `../people/people_test.py`.
- **One batch a body, no buy on a known failure (#21).** The build, route and checks run once. When the paid
  checks find a tuck over the gate in every clip of the route's body (`pokes.json`), the look's record
  (`checks/failed_tucks.json`, `prop_person.tucks_record`) carries the hash of its inputs (`prop_person.tucks_inputs`:
  take, spec, parts, the maker's and people tools' code); while that hash stands the row is Blocked before any
  machine is rented, so the same failure is never bought twice. Not a bind-pose check on the build: the
  route moves cloth over a tuck, so only the measure on the route's body predicts. A new body is a new batch once the
  take, its parts or the code changed.
