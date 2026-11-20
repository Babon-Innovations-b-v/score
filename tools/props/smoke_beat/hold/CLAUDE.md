# tools/props/smoke_beat/hold/

The smoker's hand holding the cigarette (#152): `hold.py` solves, on a people body's character.usdc, the right arm's
joint rotations over its `standing` clip and the cigarette's frame in RightHand's own frame (the index and middle
finger's gap read off the hand's own mesh), written as `pose.json`. Plain CPU, no card.

- The people's skeleton has 27 joints and no fingers (tools/characters/people/body.py merges them into the wrist): the
  pose is the arm, the grip is a place on the hand's mesh. Every angle and share is the builder's own, named so.
- Taken into score_lib with `score-lib take-in` as a `character` entry (the closest kind: a character entry holds
  motion and its records; there is no pose kind); place_build's `hold` lays it on a laid character and sets the prop.
- Test: `test_the_smokers_hand_holds_the_cigarette_between_two_fingers.py`.
