# score reads score_lib only through one versioned reader and the score-lib command

**Status:** accepted

The creator's library (score_lib) is a separate repository with its own files: `entries/<kind>/<id>/<version>/
entry.json` and `index/<kind>.json`. Four score modules globbed and parsed those files each in their own way (the
cockpit's library page, the library check, the library sweep and prepare's library first), with no contract on their
shape, so a change of the library's schema would have broken each one silently and differently.

We decided: score reads score_lib's files only through `score/library` (one reader, pure json and pathlib), which
checks every file's `schema` against the version it was written for (`score-lib-entry/1`, `score-lib-index/1`) and
refuses another version (`Unread`) instead of half reading it; and runs the library only through its `score-lib`
command (`score/stages/library/backend.py`, with `tools/library/library_files.py` as the fetch side for its blobs).
score never imports score_lib's code. A new library schema is a change in the reader first.

The trade-off: one more module between the callers and a JSON file, and a refusal where a lenient read would have
limped on. We take that, because one place to version is cheaper than four places to find when the library moves.
The other direction (score_lib reaching into score's tools by `sys.path`) is not settled by this record.
