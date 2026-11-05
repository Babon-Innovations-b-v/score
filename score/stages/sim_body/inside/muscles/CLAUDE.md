# score/stages/sim_body/inside/muscles/

The static optimisation, frame by frame (`Physics`): `needed` (inverse dynamics), `contacts` (`contact.pushes` on the
person's skin, `contact.Skin`), `stops` and `shared` (one bounded least squares, `solvers.least`, sharing the needed forces
between the ground's pushes, the joints' stops and the muscles' activations; the pelvis' six rows `BALANCE` times a
joint's), its `touches` each touching part's push, centre of pressure (weighed by each push along its contact's
normal) and touching ground points, a foot one part (`parts_of`: its calcaneus and toes under its Foot segment's name;
2026-11-05, the heel's and the toes' pushes apart drew an arrow up the shin and one lying in the floor). What they cannot give is the pelvis' residual and each joint's reserve: measured, never applied (the
parent overlay).

- `shared` is `problem` (the frame's least squares, unsolved, from the state laid in `data`), `solved_all` (every
  frame's at once on the card, `batched.least_all`, else `solvers.least` one by one) and `share_of` (the record); `each`
  gives every frame's needed forces with its state laid in `data`, on the card at once when the model is there
  (`batched.Card`), else frame by frame on MuJoCo's C (2026-11-05, #70).
- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built.
