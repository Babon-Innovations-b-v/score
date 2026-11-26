# tools/characters/whole/

One whole person of the people line put together (PRD #223): the SOMA body with its own face (`../face`, #226) as the
skin the clothes are draped on (`../garments --face`, #225), strand hair combed on that head (`hair.py`, the style
read as `../hair`'s, #227), the shoes and belt (`../accessories`, #228) and the jewellery (`jewellery.py`), drawn as
photographs taken in a real place from every side, a face close-up, a wider view of the setting and the photograph
itself (`render.py`). `__init__.py`'s docstring has how the face's body is carried onto the clips rig's bind.

- **Run**: `<motion python> ../face/body_face.py <identity.npz> <body.npz>` (it writes the low body and every joint
  too), `python ../face/face.py <body.npz> <face folder>`, then `python -m tools.characters.garments <outfit.json>
  --face <face.npz> --face-body <body.npz> --out <dressed>` and `python -m tools.characters.whole <outfit.json>
  --dressed <dressed> --face ... --face-body ... --style data/people/hair/<look>.json --frame N --name <pose> --out
  <folder>`.
  Every GPU or Blender step goes through this PC's card queue; outputs live outside the repo.
- **One skin.** The body the clothes are sewn on, the shoes are fitted on and the picture shows is the face's skin
  (the body wears the face's own library skin, `face_skin_light`), never SOMA's mean surface under a separate face.
- **From the library.** Every finish is a score_lib surface the outfit file names (its `jewellery` too); the
  setting is a library light (`SETTING`: a CC0 photographed sky, Poly Haven's, taken in as `light/<id>`). The
  library holds no jewellery model, so each piece is made on the person who wears it (`jewellery.py`); a library
  model, once adopted, replaces the made shape and keeps the checks.
- **The hair is combed on the head it is worn on**, never brought over from another head: Blender's groom grown on
  the made person's hair shell (#227), dropped point by point onto the face's head, lay in flat blocks over the eyes
  with a bald crown (2026-11-25). `hair.py` combs guides on this scalp over the head's hull (ears and all) and grows
  a head's 100 000 strands, a human hair thick, from them in locks with a soft, uneven cut and a few flyaways (owner,
  2026-11-25: a helmet, a hard flat cut line, stringy wiry strands), and checks them there: roots off the scalp,
  strands before the eyes, a bald scalp, clumps and strays, the parting's bare strip seen from above, gaps in the
  roots, a hard hairline (owner, 2026-11-25: "hairline is also still just crazy gap"), a strand thicker than a hair, a
  blunt cut and a ledge in the outline seen from behind ("earmuffs"). The render's hair close-ups
  (`<pose>-hair-*.png`: the parting from above, the hairline from the front and three quarters) are where to look.
- **A fault fails the run** after its pictures (a skin point off its low body, a piece through the skin, an earring
  out of its lobe, the hair's). Limits are never loosened to pass.
- **Made like a photograph, in a real place** (owner, 2026-11-25: the white studio read flat and overexposed; the
  bare concrete wall and floor after it read as a backdrop; 2026-11-26: "photorealism is the goal"): the library sky
  lights her and is what lies behind her, its own ground laid under her (projected from where it was photographed,
  lit by the same sky, so it takes her shadow); exposure and white balance from an incident meter at her
  (`meter.py`: an 18% card reads 18% and neutral), never set by eye; an 85 mm lens with real depth of field, its
  fall-off to the corners and a fine grain. `<pose>-photo.png` and `-photo-portrait.png` are the photograph (three
  quarters, eye height, f/2) to judge her by beside a real photo.
- **Hands at rest.** The clips rig has one joint a hand, so `relaxed_hands` reads each hand's finger joints off the
  skin and lays the hand at rest on them (`../posture`; owner, 2026-11-25: stiff splayed fingers); a hand that still
  stands otherwise fails the run. The hands' flush and thin skin join the face's region tones on the one skin.
- **Look at the pictures**: front, back, both sides and three quarters, standing and mid-walk, and the face close
  up from the front and three quarters (`--views` draws fewer of the whole person's sides). The numbers say the
  pieces sit; only the pictures say whether it reads as a photograph.
- Tests: `test_a_whole_person_wears_its_own_skin_hair_and_jewellery.py` (toy bodies, a toy head, finger, wrist and
  neck, and the posture test's welded toy hand; no SOMA, Newton or Blender).
