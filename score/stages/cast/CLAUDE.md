# score/stages/cast/

The cast stage (experimental, design 5 of 2026-10-12): row `cast@<place>` for the places whose concept shows people
(`PLACES`), reading `concept_people`'s accepted count. `__init__.py`'s docstring has the make and the five gates;
`measure.py` the geometry, `spread.py` how a group and a crowd are stood on the place.

- **The record says who, the stage says where they fit.** Named people stand where their record
  (`data/characters/<place>.json`) puts them and the gates judge that; a group's members and a crowd's copies are
  stood on the seed's measured ground, clear of every solid and of each other. Never move a named person by hand to
  pass a gate: put the record right, from the concept (the 10-11 records' tool, `cast_place.py`, is still outside
  the repo).
- **Measured on the geometry, never on a box.** Bodies are cast_check's cylinders tested against the triangles of
  the seed's base layer (FCL); a point instancer's prototypes are left out (they stand only where it copies them).
- **Do not import tools/characters at load.** Its `cast_check` on the path or in `sys.modules` joins the assembly's
  code version through `tools/usd/reach.py` and moves every place's assembly key: `measure.characters()` imports
  `cast` and `cast_check` inside the make and the gates, and the stage declares both files as inputs. Constants
  copied from them (`KEEP`, body sizes) are checked in `cast_test.py`.
- **`made` reads the SOMA-shell route's dress rows.** A look is made when its dress row (`people-dress-<look>`,
  `-in-<place>` where data/people/colours.json colours the place) stands usable; the cast reads them as optional
  inputs (`Stage.optional`), so a look with none stays not made, named, and complete's people check names it too.
  `drapes` is retired (2026-10-13): the SOMA-shell rig replaced the drapes route (owner, 2026-10-12 21:40), and the
  people rows' per-clip, shell and outline gates judge the cloth now.
- **The characters layer** (`layer.py`, row `characters-layer@<place>`) lays each person of the accepted cast in
  their own look's accepted dressed body (`people-dress-<look>`); a person whose cast names no look, or whose look has
  no usable body (its dress rows are optional reads, `Stage.optional`), is left out, named in `characters.json`,
  and the row passes with the gaps as findings, so the place assembles and complete's people check fails each gap
  by name (overseer, 2026-10-13). Never lay a stand-in body. `layer_test.py` holds it.
- `cast_test.py` runs the make and gates on the hub's record and seed and breaks `standing`, `clear` and `counted`.
