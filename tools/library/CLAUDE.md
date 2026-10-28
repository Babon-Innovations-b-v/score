# tools/library/

The one way a tool reaches the bytes of a made model or a sound an environment's records name: the creator's library,
score_lib (#22). `library_files.py` is the way in (its docstring has the names and the settings).

- **A record names a library reference** (`<kind>/<id>@<version>/<file in the entry>`), or a file kept in git by its
  path from the repository's root (`data/...`). Never a path into another repository or an engine (a Godot resource
  path, the game's checkout): `test_every_record_name_resolves_or_is_a_gap.py` fails on one.
- **What the library does not hold is a gap**, never a crash: `resolve` gives None, the caller leaves the thing out
  and says so once (`say_gap`), and the remake fills it (#19). An old release name (`models/...`, `sound/...`) in a
  record is such a gap. A library that is configured but cannot fetch, or hands back other bytes, is an error.
- **score never imports the library's code.** It runs the library's own command (`score-lib fetch <address> --file
  <file>`) and reads its entry records only for the sha256 it checks every file against.
- **A file a tool makes** (route.py install, the sound tools) goes to `made_folder()`; `score-lib take-in` (the
  library's) takes it in, and the records then name its reference. Nothing here writes to the library.
- **Pixal3D's takes live in the library too** (`pixal_takes.py`, 2026-10-28: work/pixal held the only copy): a take
  is one `take` entry, every file under its work/pixal name (models, record, `.svviews` close-up and camera);
  `taken_in` commits and pushes takes through `score-lib take-in --save`, `read_back` fetches them again and compares
  size and sha256, `take_back` puts a missing take back. It is in `_code.FRAMEWORK`: it never changes a take's bytes.
