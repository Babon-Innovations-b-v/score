# score/stages/sim_body/inside/ground/

The scene's ground as the sim body stands on it, pure numpy in the person's own frame (Y up): `standing` (each
point's ground, the highest drawn triangle under it at most `REACH_UP` (the cast's `KNEE`) over it with `HEADROOM`
free over it: under less, a table top or a shelf,
it is a block, not a floor), `heights_over` and `normals` (each triangle's upward normal). The ground is the scene's
drawn triangles themselves: never a heightfield and never MuJoCo's collision (the parent overlay). Its test runs in
the score venv.
