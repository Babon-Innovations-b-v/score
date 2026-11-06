# tools/characters/played/

A clip played on a person's build, the people route's one definition (#70; numpy only, its test runs in the score
venv): `laid`, `chained`, `fk`, `clip_local`, `clip_world` and `floor_lift`, the arithmetic of `../maker/prop_build.py`.

- **Never play a clips rig's own offsets**: people-clips-made's clips are posed on SOMA's zero-identity body, 7 cm
  shorter than the template its bind and surface are; played raw they floated the skin 26 to 57 mm over its ground
  (#70, 2026-10-29). Play them on a build's bones (with none, the rig's own bind's), lifted by `floor_lift`.
- **prop_build.py keeps its own copy until its next paid re-make** (the owner's call): changing its bytes re-makes
  every people-body row on a rented card. The test holds the two equal, bit for bit; when prop_build moves onto this
  module, drop that check.
- **Kimodo's own foot correction, on the build's bones** (`contacted`, #70, 2026-11-06; the owner: "make actual
  contact points in kimodo"): MotionCorrection's `correct_motion` (vendor/kimodo/MotionCorrection, what Kimodo's
  post_process_motion calls) on Kimodo's somaskel30 joints mapped joint by joint (`kimodo_joints`), the rest the
  build's bind (its floor the bind's, not Kimodo's lowest toe plus 2 cm), Kimodo's foot_contacts the clip's. It needs
  that package built where it runs (CMake, its own Eigen and pybind11; never torch: the wrapper is skipped) and
  scipy; the rest of the module stays numpy only.
- Readers: the sim body (`score/stages/sim_body` `person_rig`, `clip_frames`), and through it the film's layer peel.
- This folder is in no row's declared files: its readers' keys follow it by import.
