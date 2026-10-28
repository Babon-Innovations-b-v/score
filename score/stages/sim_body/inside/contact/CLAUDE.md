# score/stages/sim_body/inside/contact/

The body's feet on the scene's ground: `surface` (each collider's points in 26 directions), `lowest_over`, `stances`
(the clip's foot segments standing, low and still: Kovar et al. 2002), `on_ground` and `unslipped` (what the fit
holds), `grounded` (the path moved once so its lowest point stands on the ground at the median frame) and `pushes`
(the points the ground pushes: within `GAP` of the drawn triangle under them or into it, a friction pyramid under
`SLIDE_MOST`, else sliding against the slip).

- #70: SOMA is the truth and is never grounded; ground contact is where SOMA's feet are. `grounded` goes there.
- Its test runs in Newton's own Python (MuJoCo pinned there) by subprocess and prints `skipped` where no env is built.
