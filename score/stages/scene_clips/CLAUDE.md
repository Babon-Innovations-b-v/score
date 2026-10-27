# score/stages/scene_clips/

The scene-made clips (experimental, PRD #56; CONTEXT.md "scene-made clip"): row `scene-clips@<place>`, paid, for a
place whose design shows people. Each walker of the accepted cast gets a Kimodo clip made from its own route through
the scene, its feet asked on the scene's own ground. `__init__.py`'s docstring has the make, the gates, what Kimodo
cannot hold (with its evidence) and the price; `tools/characters/clips/scene_clips.py` is the machine's program.

- **The route and its ground are the cast's.** The route is the cast's `path`, else a straight leg from the spot the
  way it faces, and it is checked on the very geometry the cast is measured on (`cast/measure.py`: the knee-down ray,
  the body cylinder). Never sample a ground of its own or a flat floor.
- **Only Kimodo's real constraint API.** `constraints_of` writes Kimodo's constraints JSON (`root2d` dense, `left-foot`
  and `right-foot` at stance middles, fewer than 20 a foot); its FK was checked against Kimodo's own
  (`SOMASkeleton77.fk`, `load_constraints_lst`, 2026-10-27: soles on the asked ground to 0.1 mm, toes where their
  ground was read to 0.2 mm). A change to the rest-pose numbers (`HIP_OVER_SOLE`, `FOOT_SIDE`, `HEEL`, `TOE`) is
  measured again with Kimodo's FK, never typed.
- **Output as people-clips-made's** (`rig.npz` `clip_<name>`, `motions/`, `make.json`), plus `scene_clips.json` with
  each clip's placement (its canonical frame under translate `origin`, rotateY `turn`): the sim body, the assembly
  and the film read the clips as they read people-clips-made's.
- **Never edit `tools/characters/maker/` or `people/` for it**: both are declared inputs of the paid people rows. The
  machine's program lives in `tools/characters/clips/`.
- **Nothing reads its output yet**, so no other row's key moves.
- Tests: `test_a_walk_becomes_constraints_on_its_own_ground.py` (a toy place of steps and a wall, written outputs;
  Kimodo itself is not run there).
