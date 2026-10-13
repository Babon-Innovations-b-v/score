# score/stages/people_bodies/

The people's body rows (#5, experimental): `bodies.py` (`people-body-<look>`, paid: the maker's build, settle and
checks, and every body gate), `clips.py` (the body judged clip by clip; `people-clips`' make) and `far.py` (a far-only
look's gates). The people package (`../people/`) builds the table's rows from them; its overlay holds the gates'
rules.

- **Keep this package's `__init__.py` empty of imports.** A body row's code version takes in its package's
  `__init__`; in the people package that pulled in the whole surface stage, so every surface edit re-keyed (and
  re-bought) every body (2026-10-13). Import nothing here from `score.stages.people`.
- Tests: `../people/people_test.py`.
