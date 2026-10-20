# score/stages/people_bodies/

The people's body rows (#5, experimental): `bodies.py` (`people-look-parts-<look>`, paid: the look's parts, its own
priced row, never bought inside the body; `people-body-<look>`, paid: the maker's build, settle and checks, and every
body gate), `clips.py` (the body judged clip by clip; `people-clips`' make) and `far.py` (a far-only
look's gates). The people package (`../people/`) builds the table's rows from them; its overlay holds the gates'
rules.

- **Keep this package's `__init__.py` empty of imports.** A body row's code version takes in its package's
  `__init__`; in the people package that pulled in the whole surface stage, so every surface edit re-keyed (and
  re-bought) every body (2026-10-13). Import nothing here from `score.stages.people`.
- Tests: `../people/people_test.py`.
- **One batch a body, no buy on a known failure (#21).** A full look's tucks are measured at the bind pose right after
  its build (`pokes.py --bind`, free, here): over 5 mm there every clip fails, so its settle is not bought and the row
  fails, a hole. Its record (`checks/bind_tucks.json`) carries the hash of its inputs (`prop_person.bind_inputs`);
  while that hash stands the row is Blocked before any machine is rented, so a body batch whose every look failed
  at the bind spends nothing. A new body is a new batch once the take, its parts or the maker changed.
