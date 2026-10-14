# score/stages/demo_film/

The demo-film row (experimental, 2026-10-14): demo K9's walk-through film of one place, from its final stage once it
passes complete, with its own sound; paid and cleared by the runner like any paid row. `__init__.py`'s docstring has
the make, the output and the gate.

- **Only the places `data/definitions/demo_films.json` names have the row.** Add a place there once it passes complete
  (group by group, the overseer's order); nothing films before. All 18 places come to about EUR 11.
- **The film is the place's own**: the neighbours output where the place shows others, else its assembly, never a seed;
  one camera path (the owner's first picked viewpoint, else the scene record's), 1280x720, the look only (no ink).
  People need no handling: the characters layer lays nobody today.
- **The gate measures**: film_checks' video checks (size, sound, black, frozen, length) and the clearance on every
  frame. Whether the film reads well is the creator's call.
- Run: add the place to the record, then `python -m score run world1 --place <place> --stage demo-film --detach`.
  Test: `demo_film_test.py` (no Blender, no spend).
