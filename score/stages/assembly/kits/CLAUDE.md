# score/stages/assembly/kits/

Kit pieces laid by their connectors (#93, under #55): a score_lib kit entry's `piece.json` (`PIECE_SCHEMA`) carries
each connector's frame (`at`, `out` its +z, `up` its +y), its mating `size`, interface `kind` and allowed `twists`,
and the piece's `fit` (metres, degrees; 0.1 mm and 0.1 degree when not given). `lay` joins pieces at their connectors,
`joint_faults` fails a joint outside the tighter piece's fit, a loop's closing joint included.

- **Method from marso-skills (Apache-2.0)**: `marso-blender-kit`'s kit contract and `marso-blender-compose`'s
  `snap_component.py`, reimplemented on plain matrices; nothing copied. Never take from Marso's four proprietary
  scene skills (#85).
- **Pure numpy, no stage imports it yet.** The assembly stage lays kits once score_lib holds the pipe pieces #55
  waits on; wiring it in moves the assembly's key, so check `score moved` first.
- **Never loosen a fit to pass a joint.** A joint off its fit is a piece or a laying fault: fix the piece's frames.
- `test_two_pieces_join_only_within_their_fit.py`: one test, hand-laid answers, both ways round each limit.
