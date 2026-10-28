# score/stages/sim_body/inside/muscles/

The static optimisation, frame by frame (`Physics`): `needed` (inverse dynamics), `contacts` (`contact.pushes` on the
person's colliders), `stops` and `shared` (one bounded least squares, `solvers.least`, sharing the needed forces
between the ground's pushes, the joints' stops and the muscles' activations; the pelvis' six rows `BALANCE` times a
joint's). What they cannot give is the pelvis' residual and each joint's reserve: measured, never applied (the
parent overlay).

- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built.
