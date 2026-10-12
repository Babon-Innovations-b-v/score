# score/stages/surfaces/

The surface stage (R4, the paper's core contribution: shape and surface apart, every part one surface of the shared
library), step 1 of PRD #6, as rows of world 1's stage table (`__init__.py`, `ROWS`). Bible: `architecture/components`
and `architecture/experimental`; method: the paper's Methods, "Shape and surface apart".

- **One line per place, run by the runner**: `python -m score run world1 --place <place> --detach` (score's overlay:
  never walk the rows by hand). Every row is place grain (`surfaces-inputs@greenhouse` ... `surfaces-check@greenhouse`);
  no place waits on another.
- **The method sits behind one interface**: its rows end in the contract `surfaces-parts` v1 (`parts.json`: per model
  its parts, each with the library surface the method named (`judge`), its words, a proposed new surface or null;
  `finish` null when nothing is measured; `<take>/parts.npy` one part per welded face; `<take>/colours.npy` each
  face's seen colour, NaN when none is measured). Another method replaces the method's rows and writes it; the
  framework's rows (`place_line.py`: paint, bake, check) do not change.
- **The method is the finish-map method** (owner, 2026-10-12: "finish map seed 1 looks great"; it replaced g-texture,
  whose record is branch `surface-first` and main before this change): `finish_parts.py` (inputs, parts),
  `turntable_row.py` (the raw model's texture unlit from the close-up's camera and the sides and back, with the face
  under each pixel; `inside/turntable.py`, `turntable_views.py`), `finish_rows.py` (Gemini 3.1 Pro's finish list of
  the close-up; Nano Banana Pro's finish map of the close-up, drawn up to three times, the last more strictly, then
  of each turntable view against it; `finish_ask.py`, `finish_maps.py`), `segvigen_row.py` (SegviGen guided by the
  close-up's map). Each paid row has a module of its own, so a free change never pays again; every Google ask is
  cached by its input's hash. The six-model re-test rows are `../finishmap/trial.py`.
- **A library change re-keys only the rows that read the library** (lists, names, parts, paint, bake, check:
  `surface_data.line_files`); inputs, turntable, maps and SegviGen declare none (`shape_files`), the inputs'
  output names no folder of its run, and the turntable renders on the processor with a fixed seed
  (`inside/turntable.py` `cycles_fixed`). On 2026-10-12 the making folder in `job.json` and card renders that
  differed run to run made one library change re-render every place and re-draw every view map (about EUR 50).
  Before pushing a change that moves a paid row's key, list what it re-buys (`_code.source_files` and the
  row's files).
- **A map that does not settle blocks its model, never passes**: measured (`finish_maps.check`: overlap, share near
  a label colour, every finish used), filled from labelled neighbours only when its sole fault is a labelled share
  between `FILL_LEAST` and `NEAR_LEAST`; a one-finish model is not drawn (its map is the close-up's object mask:
  asked to paint one colour, the picture model tinted the photo); a model with no settled close-up map is named in `surfaces-maps`' fail and
  stops its place's line (once the owner waives it, later rows leave it out). A part whose voted faces mix two
  finishes fails `surfaces-parts` the same way.
- **Each finish's surface is checked against the close-up's colour** (`finish_parts.checked_finishes`,
  `COLOUR_DELTA_E` 32 CIE76, set on round 4's six models): the colour only chooses among library surfaces (the
  nearest of the listed one's family); a finish none fits gets a tinted proposal in the registry and fails the paint
  row's gate "colour against the close-up" by name.
- **A finish is named again when its words or colour contradict its surface** (`surfaces-names`, paid, cached): its
  words name a material its surface's family is not (`finish_parts.contradicts`: black rubber as bare_steel), or its
  surface lies over `COLOUR_DELTA_E` from its close-up colour; Gemini is asked once with the close-up, the finish map
  and every surface the take's library places allow. New library surfaces are made the library's own way (a variant
  in `data/library/materials.json` on a palette token, the place taking it in `place.json`), never a picture's colour.
- **The bake takes today's library and the method's paint only**: every painted surface's spec from the library, an
  old job's `regions` boxes dropped.
- **The check is its own module** (`bake_check.py`, so its edits move the check row alone; wired in
  `score/stages/__init__.py` until the 2026-10-12 fan-out ends, since this folder's `__init__.py` is in the
  turntable's and SegviGen's code version). A near-black triangle is a blotch only when its colour lies over
  `BLOTCH_DELTA_E` from every surface within its reach: on a border it may bake its neighbour (the seed tray's paper
  label on black plastic passes), a black smudge along the border still fails. It also fails a model whose surfaces
  bake to one grey look its close-up does not have (`one_look_faults`: every two within 12, each near neutral, the
  close-up's over 24 apart; the greenhouse's water tank and crop crate, 2026-10-12: the check of bake against
  library alone passed them at dE 0), two opaque surfaces whose lightness order the bake reverses (`order_faults`:
  seen over 10 L* lighter, baked over 3 darker; the light moves L* but keeps the order), and a part baked over 32
  from its close-up colour (kept at 32: the close-up's light lifts right surfaces 15 to 30 L*, so a tighter number
  fails right blacks; compare a model's surfaces with each other instead).
- **The paint levels a take's feet before its bake** (`place_line.levelled_feet`, `tools/props/library/feet.py`):
  a take a row lays loose on the floor or held (`stands_on_feet`, from the inventory and the resting rules, declared
  in the table) has its short legs stretched onto the level plane through its lowest foot, in its own frame; a foot
  over a tenth of its size up is a missing leg and fails the gate "feet in one plane" by name. Never level by
  tipping the model: its own up is the reference (the water tank's top lay level within 0.25 degrees).
- **Painting is 3D parts plus the shared library, only.** A picture's colours never reach a model: a map's label
  colours only name finishes, each part is painted from its finish's library surface.
- **The finish registry is a store item** (`registry.py`; `registry/surfaces/` in the store): append-only, the new
  library surfaces a method proposed, each standing as first proposed for the owner to accept into the library or
  not; until then the part keeps the nearest library surface the method named (`stands_in`). The paint writes it
  outside its key.
- **Per-place data is world data** (`surface_data.py`, `data/surfaces/<place>.json`): the takes a place paints, the
  library name, the bake (the route's make_chunky job, model per take, entries the job lacks), and `elsewhere`: the
  models it lays that another place claims. Everything is repainted, the owner's picks included (a pick chooses the
  model, never its old paint: owner, 2026-10-12); each take is painted by one place only, and a place reads a claimed
  model from the claiming place's bake (`elsewhere.json` in its bake output; the bake gate fails a claim the other
  place does not bake). A place with no file blocks at `surfaces-inputs`; one with no `bake` blocks at
  `surfaces-bake` before anything is cleared. A place with nothing to paint (code-built pieces only: gdoor, hdoor,
  tube) has a file with no takes and a `nothing` line; its line has no surface rows (`Stage.applies`).
- **Gates never crash or pass on what is missing** (`surface_gates.guarded`: unknown with the missing file named).
- Steps needing trimesh run in the prop environment through their module's command line (`prop_env.py`), each make
  defined in its step's own module so that module is its code version. Tests: `surfaces_test.py` (the framework
  side) and `finish_test.py` (the method's steps), both on the framework's Python.
