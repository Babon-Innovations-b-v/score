# score/stages/sim_body/inside/contact/

The body on the scene's ground: `Skin` (the person's drawn surface, SOMA's mesh, each point the blend of the
segments its weights name, each segment riding its bone: the contact surface, a seat's as a floor's), `lowest_over`
and `pushes` (the skin points the ground pushes: within `GAP` of the drawn triangle under them or into it, a friction
pyramid under `SLIDE_MOST`, else sliding against the slip, each acting at the ground under it: the record's `touches`, each body's push and centre
of pressure, `muscles.touches`); `surface` (each collider's points in 26 directions) is
the evaluation's measure only. MyoFullBody's colliders are not the contact (2026-11-01): a seated astronaut's stood 16
to 27 mm inside his skin, which sat 10 mm into his floor, so the floor carried 0 N of his 121 N weight.

- #70: SOMA is the truth: nothing here moves the body. Ground contact is where the fit to SOMA puts the feet; the old
  fit's holds (`stances`, `on_ground`, `unslipped`, `landed`) and `grounded` (the path moved so its lowest point
  stood on the ground) went with it on 2026-10-28.
- Its test runs in Newton's own Python (MuJoCo pinned there) by subprocess and prints `skipped` where no env is built.
