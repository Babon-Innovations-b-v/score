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
  with a bald crown (2026-11-25). `hair.py` combs guides on this scalp over the head's hull (ears and all) from one
  explicit parting curve that ends at the crown's whorl (hair runs forward along the parting, spirals out of the
  whorl, roots near either lean in over them), roots it at a real head's density by region (some 190 000 strands,
  vertex 260 a cm2), lays a band of short fine baby hairs under a jittered hairline, grows the strands from blended
  guides in locks that only hang together, with a soft uneven cut, ends turned in, flyaways and the crown's frizz
  (owner, 2026-11-25: a helmet, a hard flat cut line, stringy wiry strands; round 1's judges, 2026-11-26: bald strips
  and an oval beside the parting from above, no baby hairs). It checks them there: roots off the scalp, strands
  before the eyes, the scalp seen bare from above (`top_bare`: the hair rendered from above straight down and from
  four tilts, scalp pixels showing through away from the parting's 3 mm line; round 1's groom showed 6.4% and a
  367 mm2 patch), clumps and strays, gaps in the roots, a hard hairline ("hairline is also still just crazy gap"),
  a strand thicker than a hair, a blunt cut and a ledge in the outline seen from behind ("earmuffs"). The render's
  hair close-ups (`<pose>-hair-*.png`) and `../hair/heads.py`'s head from five sides are where to look.
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
