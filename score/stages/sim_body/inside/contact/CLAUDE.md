# score/stages/sim_body/inside/contact/

The body's feet on the scene's ground: `surface` (each collider's points in 26 directions), `lowest_over` and
`pushes` (the points the ground pushes: within `GAP` of the drawn triangle under them or into it, a friction pyramid
under `SLIDE_MOST`, else sliding against the slip).

- #70: SOMA is the truth: nothing here moves the body. Ground contact is where the fit to SOMA puts the feet; the old
  fit's holds (`stances`, `on_ground`, `unslipped`, `landed`) and `grounded` (the path moved so its lowest point
  stood on the ground) went with it on 2026-10-28.
- Its test runs in Newton's own Python (MuJoCo pinned there) by subprocess and prints `skipped` where no env is built.
