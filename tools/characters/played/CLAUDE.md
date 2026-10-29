# tools/characters/played/

A clip played on a person's build, the people route's one definition (#70; numpy only, its test runs in the score
venv): `laid`, `chained`, `fk`, `clip_local`, `clip_world` and `floor_lift`, the arithmetic of `../maker/prop_build.py`.

- **Never play a clips rig's own offsets**: people-clips-made's clips are posed on SOMA's zero-identity body, 7 cm
  shorter than the template its bind and surface are; played raw they floated the skin 26 to 57 mm over its ground
  (#70, 2026-10-29). Play them on a build's bones (with none, the rig's own bind's), lifted by `floor_lift`.
- **prop_build.py keeps its own copy until its next paid re-make** (the owner's call): changing its bytes re-makes
  every people-body row on a rented card. The test holds the two equal, bit for bit; when prop_build moves onto this
  module, drop that check.
- Readers: the sim body (`score/stages/sim_body` `person_rig`, `clip_frames`), and through it the film's layer peel.
- This folder is in no row's declared files: its readers' keys follow it by import.
