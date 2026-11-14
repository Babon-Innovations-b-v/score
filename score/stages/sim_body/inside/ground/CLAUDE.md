# score/stages/sim_body/inside/ground/

The scene's ground as the sim body stands on it, pure numpy in the person's own frame (Y up): `standing` (each point's
ground, the highest drawn triangle under it at most `REACH_UP` (the cast's `KNEE`) over it (a body's points: over the
body's lowest point, or its middle (the median of its points' heights) where higher, `body_reach`, so a roof over
its head is never its ground, 2026-10-31, and a seat under a seated body with its feet on the floor is, 2026-11-07) with `HEADROOM` free over
it, or as much as the body reaches over it where less (`body_top`: a seated body's lower bunk under the upper
one, 2026-11-13, quarters' person_bed, whose centre of mass had no ground and made RRA's limits NaN): under less, a
table top or a shelf, it is a block, not a floor; or within a knee of the body's lowest point,
`body_floor`, whatever is over it: the deck a foot stands on under a desk, a chair's seat or a railing is its floor,
2026-11-13; never a crossing over the point with another between them, `beneath`: a foot under a desk is under its
top, not in it; nor a crossing of a closed piece the point is outside of, `outside` (`pieces`: triangles joined at
their corners; an even count of its crossings over the point), 2026-11-14: quarters' person_desk's toes on the floor
under its desk's apron read 0.28 m into it), `heights_over` and `normals` (each triangle's upward normal). The ground is the scene's drawn triangles themselves: never a heightfield and never MuJoCo's collision
(the parent overlay). Its test runs in the score venv.
