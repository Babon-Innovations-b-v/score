# tools/characters/speech/

The 2099 prologue's leader speaking at the square's lectern (2099 #161): `speech.py` solves, on a people body's
character.usdc, both arms' joint rotations over its `standing` clip (the left forearm resting forward on the lectern,
the right hand raised in front of the chest), written as `pose.json`. Plain CPU, no card.

- The arm geometry is the smoker's hold's (`tools/props/smoke_beat/hold/hold.py`, loaded by its file), never a copy.
  Every angle is the builder's own, named so (`LEFT`, `RIGHT`).
- Taken into score_lib with `score-lib take-in` as a `character` entry (no pose kind), as the smoker's hold is;
  place_build's `hold` lays it on the laid leader.
- Test: `test_the_leader_rests_one_hand_on_the_lectern_and_raises_the_other.py`.
