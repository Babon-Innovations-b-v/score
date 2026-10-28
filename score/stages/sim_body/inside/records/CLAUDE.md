# score/stages/sim_body/inside/records/

What the run writes for one person, the contract the stage reads (`../../__init__.py` `measured`, `write_layer`):
`frames` (each frame's record and the drawn arrays: poses, muscle paths), `arrays` (<out>.npz's names), `entry`
(out.json's), `bones_of` (the bone meshes from MuJoCo's own compile, merged within `BONE_CELL`) and
`adjustment_record` (RRA's `adjusted`). A field renamed or dropped here is a contract change: the stage's `CONTRACT`
version moves with it.

- Its test runs in Newton's own Python (MuJoCo pinned there) by subprocess and prints `skipped` where no env is built.
