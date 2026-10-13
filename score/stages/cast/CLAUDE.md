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
  copied from them (`KEEP`, body sizes, `BODIES`, `SHIPPABLE`) are checked in `cast_test.py`.
- **`made` and `drapes` fail until the people route lands.** A look is made when its take under `PROP_PEOPLE` has its
  built body in `out/` and a `checks.txt` with no FAIL. Until then the characters layer is not written from a cast:
  never pass today's SOMA-mesh bodies in the rejected drapes off as done.
- **The characters layer** (`layer.py`, row `characters-layer@<place>`) lays each person of the accepted cast in
  their own look's accepted dressed body (`people-dress-<look>`); a person whose cast names no look, or whose look has
  no accepted body, is left out and the row answers unknown. Never lay a stand-in body. `layer_test.py` holds it.
- `cast_test.py` runs the make and gates on the hub's record and seed and breaks `standing`, `clear` and `counted`.
