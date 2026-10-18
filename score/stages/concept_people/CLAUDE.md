# score/stages/concept_people/

The concept-people stage: how many people each place's concept shows, one paid environment node `concept_people` of its
own runner (`python -m score.stages.concept_people run`), cleared by the runner like any paid stage.

- **Measured, never judged by eye.** SAM 3 finds every figure on every view picture the inventories name; the judge
  (a vision-language model) says of each whether it is a person there, a person outside the place behind glass
  (where the place has no floor: not counted; captain, 2026-10-13, the tube's third figure), a picture of one, a
  reflection, an empty suit or something else, and what a person is doing. A split vote is asked again with more seeds; a tie stays unknown.
- **Its own table, and environment 1's.** It reads the concepts, not a place's stage; it is also an environment node of
  `score.stages.STAGES` (2026-10-12) so the cast stage reads its accepted count like any earlier node. Its key reads
  only the inventories' plan views (`views_text`), not their rows.
- **What reads it.** A place whose concept shows people needs a cast (data/characters/<place>.json); the count and
  each figure's box and doing are the cast's evidence. Never edit a count by hand: change the question or the seeds
  and run the stage again.
