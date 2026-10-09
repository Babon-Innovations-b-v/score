# tools/assets/

The world's heavy files: the made models and the sounds a world's records name, kept as a release of this repository
(`data/assets/world1.json` is the manifest), never in git. `world.py` is the way in (its docstring has the commands).

- **A record names a file by its manifest name** (`models/<folder>/<file>`, `sound/<...>`) or, for a file kept in git,
  by its path from the repository's root (`data/...`). `world.resolve` gives either on disk. Never a path into another
  repository or an engine (a Godot resource path, the game's checkout): `game_free_test.py` fails on one.
- **Every file has its terms.** A pack stops on a file no licence entry matches: models by the manifest's `licences`,
  sounds by `data/sound/licences.json`. A new file gets its entry in the same change.
- **A release is never changed in place.** A changed or new file means a new tag: pack the local folder
  (`world.py pack <folder> <tag>`), publish it, commit the manifest. The fetched folder is checked against the
  manifest's sha256 once (`.checked`), and tools that make the world's files (route.py install, the sound tools)
  write into the local folder, so its next pack is the next release.
- Keep git small: a binary over a few MB goes in the release, not in `data/`.
