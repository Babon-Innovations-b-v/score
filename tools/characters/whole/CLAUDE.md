# tools/characters/whole/

One whole person of the people line put together (PRD #223): the SOMA body with its own face (`../face`, #226) as the
skin the clothes are draped on (`../garments --face`, #225), strand hair combed on that head (`hair.py`, the style
read as `../hair`'s, #227), the shoes and belt (`../accessories`, #228) and the jewellery (`jewellery.py`), drawn as
studio photographs from every side, a face close-up and a daylight setting (`render.py`). `__init__.py`'s docstring
has how the face's body is carried onto the clips rig's bind.

- **Run**: `<motion python> ../face/body_face.py <identity.npz> <body.npz>` (it writes the low body and every joint
  too), `python ../face/face.py <body.npz> <face folder>`, then `python -m tools.characters.garments <outfit.json>
  --face <face.npz> --face-body <body.npz> --out <dressed>` and `python -m tools.characters.whole <outfit.json>
  --dressed <dressed> --face ... --face-body ... --style data/people/hair/<look>.json --frame N --name <pose> --out
  <folder>`.
  Every GPU or Blender step goes through this PC's card queue; outputs live outside the repo.
- **One skin.** The body the clothes are sewn on, the shoes are fitted on and the picture shows is the face's skin
  (the body wears the face's own library skin, `face_skin_light`), never SOMA's mean surface under a separate face.
- **From the library.** Every finish is a score_lib surface the outfit file names (its `jewellery` too); the studio's
  backdrop is the library's `paper_white`. The library holds no jewellery model, so each piece is made on the person
  who wears it (`jewellery.py`); a library model, once adopted, replaces the made shape and keeps the checks.
- **The hair is combed on the head it is worn on**, never brought over from another head: Blender's groom grown on
  the made person's hair shell (#227), dropped point by point onto the face's head, lay in flat blocks over the eyes
  with a bald crown (2026-11-25). `hair.py` roots it on this scalp and checks it there: roots off the scalp, strands
  before the eyes, a bald scalp, clumps and strays.
- **A fault fails the run** after its pictures (a skin point off its low body, a piece through the skin, an earring
  out of its lobe, the hair's). Limits are never loosened to pass.
- **Look at the pictures**: front, back, both sides and three quarters, standing and mid-walk. The numbers say the
  pieces sit; only the pictures say whether it reads as a photograph.
- Tests: `test_a_whole_person_wears_its_own_skin_hair_and_jewellery.py` (toy bodies, a toy head, finger, wrist and
  neck; no SOMA, Newton or Blender).
