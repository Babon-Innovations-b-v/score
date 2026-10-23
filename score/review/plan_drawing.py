"""The top-down drawing a written plan is measured from (CONTEXT.md "plan"; the owner, 2026-10-21, the method of the
ship's outline: measured from drawings, never shaped from words): one Nano Banana Pro call redraws a place's picked
concept as an orthographic architect's plan seen from directly above (the same layout, every part where the concept
puts it, tubes as tubes, domes as circles, no perspective), sent with the place's outline on the layer above's plan
when that lays it out. The plan writer (plan_writing.py) reads positions and shapes off it; part of plan writing,
under the same standing allowance and its spend block. Kept in the store, written once, one per pick and outline:

    plan-drawings/<place>/<time>.json  {place, concept, outline, sha, at, euros, seconds, wording}
    blobs/<sha>                        the drawing (PNG)
"""
import base64
import hashlib
import io
import math
import time
import urllib.error

from score.review import concepts, creator_plans, plans
from score.store import stamp_key

AREA = "plan-drawings"
CALLER = "plan-drawing"
NEAR_BOTTOM = "The painting's near side is at the bottom of your picture and its left at the left."
FROM_SOUTH_EAST = ("The painting is seen from the south-east, a little from above; draw the plan north up, so the "
                   "painting's viewer stands off your picture's bottom-right corner.")
OUTLINE = (" The second picture is the plan of the place holding it, top down and north up, this place the yellow box: "
           "draw this place filling exactly that box's shape and proportions ({wide:g} m west to east, {deep:g} m "
           "north to south: your picture is that shape), north up, its doors where the box's doors are, and every "
           "part at its true size against it.")
# a part the creator planned is drawn at the plan's own size (creator data wins; the owner, 2026-10-21)
PLANNED_SIZE = " ({long:g} m long, {wide:.1f} m wide: draw it at exactly this size)"
# the frames the drawing model draws in (Nano Banana Pro's aspect ratios), wide over deep
FRAMES = ("1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9")
OUTSIDE = ("From straight above every dome and round module is a flat circle, a box-shaped building the rectangle of "
           "its roof, a faceted hall its polygon, every tube or corridor a straight band of even width running between "
           "the two parts it joins.")
INSIDE = ("It is indoors: draw its floor plan from straight above with the ceiling taken off, walls as thick dark "
          "lines, doorways as gaps, every piece of furniture and every thing as its outline from above (a round table "
          "a circle, a bed a rectangle).")
# The owner's method of 2026-10-21, tried on the Base: a square frame and "must NOT copy its viewpoint" are what made
# the model leave the painting's perspective (asked softer, it restyled the painting as it stood).
WORDING = ("Make a new picture: the plan of {name} in the attached painting, as a nadir view looking exactly straight "
           "down from high above, like a map or an architect's {kind}. The painting is an oblique three-quarter view; "
           "your picture must NOT copy its viewpoint or composition: no wall's side may show, no horizon, no sky, only "
           "what is seen from directly overhead. {seen} Its parts: {parts}. Keep every part exactly where it stands "
           "relative to the others and at its size relative to the others: what is left, right, behind or in front of "
           "what, and what joins what. {orientation} Clean technical drawing, plain white background, thin dark "
           "outlines, flat light fills in the parts' own colours, no shadows, no ground texture, no people, no text, "
           "no labels.{outline}")


def parts_of(store, place):
    """The place's parts as its scene inventory names them (a count before a row of more than one), a part a creator
    planned with its own metres (creator_plans), the place itself and its people left out."""
    from score.review import plan_checks
    inventory = plans.inventory_of(store, place) or {}
    left_out = plan_checks.people(inventory)
    planned = creator_plans.planned(plans.derived(store, place).get("holds", []))
    sized = {planned[0]: PLANNED_SIZE.format(long=planned[1]["length"], wide=planned[1]["wide"])} if planned else {}
    said = [(f"{int(row.get('count', 1) or 1)} {row.get('name') or row['id']}" if int(row.get("count", 1) or 1) > 1
             else str(row.get("name") or row["id"])) + sized.get(row["id"], "") for row in inventory.get("rows", [])
            if row["id"] not in left_out and not plans.whole(row, inventory.get("picture"))]
    return ", ".join(said).replace("_", " ")


def wording_of(store, place):
    """What the drawing is asked with: the place's name and parts, how it is seen from above (indoors its floor plan,
    else its roofs), the way the plan is turned against the painting (north up from the fixed south-east view its
    locked draw was drawn to, else the painting's near side at the bottom) and its outline when sent."""
    inside, held = concepts.indoors(store, place), plans.holder_of(store, place)
    return WORDING.format(name=concepts.name_of(place), kind="floor plan" if inside else "roof plan",
                          seen=INSIDE if inside else OUTSIDE, parts=parts_of(store, place),
                          orientation=FROM_SOUTH_EAST if from_south_east(store, place) else NEAR_BOTTOM,
                          outline=OUTLINE.format(wide=held["outline"][2], deep=held["outline"][3]) if held else "")


def from_south_east(store, place):
    """Whether the place's locked draw was drawn to the fixed south-east view: its draw record names the grey
    structure picture locks were drawn on until 2026-10-23 (`blockout`, the ship's rooms), retired since."""
    sha = concepts.picked(store, place)
    return bool(next((draw for draw in concepts.draws(store, place) if draw["sha"] == sha), {}).get("blockout"))


def frame_of(store, place):
    """The drawing's frame: the one of FRAMES nearest the place's box on the layer above's plan (the hangar's 32 x 64 m
    a 9:16), so the drawing can keep its proportions; square when the layer above lays none (the painting's wide frame
    is then not copied as it stands)."""
    held = plans.holder_of(store, place)
    if not held:
        return "1:1"
    wanted = math.log(held["outline"][2] / held["outline"][3])
    return min(FRAMES, key=lambda frame: abs(math.log(int(frame.split(":")[0]) / int(frame.split(":")[1])) - wanted))


def pictures_of(store, place):
    """[PIL] the drawing is sent: the picked concept, then the place's outline on the layer above's plan when it lays
    it out (plans.shape_sent)."""
    from PIL import Image
    found = [concepts.blob_picture(store, concepts.picked(store, place))]
    return found + [Image.open(path) for _, path in plans.shape_sent(store, place)]


def outline_key(pictures):
    """The hash of the outline picture sent (None: none), so a moved outline is drawn again."""
    if len(pictures) < 2:
        return None
    return hashlib.sha256(pictures[1].convert("RGB").tobytes()).hexdigest()


def drawings(store, place):
    return [store.read(key) for key in sorted(store.objects.keys(f"{AREA}/{place}/"))]


def drawing_of(store, place, outline, wording):
    """The newest drawing of `place` from its picked concept, `outline` and `wording`, None with none."""
    sha = concepts.picked(store, place)
    return next((found for found in reversed(drawings(store, place)) if found["concept"] == sha
                 and found.get("outline") == outline and found.get("wording") == wording), None)


def called(wording, pictures, frame="1:1"):
    """One Nano Banana Pro call in `frame` (frame_of; google_spend, on its ledger, never cached); (PNG bytes, euros,
    seconds)."""
    from PIL import Image
    pro, google_spend, secret_store = concepts.tools()
    body = {"contents": [{"role": "user", "parts": [{"text": wording}]
                          + [pro.part(picture, concepts.LONGEST_SENT) for picture in pictures]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"imageSize": "2K",
                                                                                  "aspectRatio": frame}}}
    began = time.time()
    try:
        response = google_spend.generate(pro.MODEL, body, secret_store.secret(pro.KEY_SECRET), concepts.TIMEOUT,
                                         caller=CALLER)
    except urllib.error.HTTPError as error:
        raise concepts.Refused(f"the drawing model refused ({error.code})") from error
    found = pro.pictures_in(response)
    if not found:
        raise concepts.Refused("the drawing model answered with no picture")
    buffer = io.BytesIO()
    Image.open(io.BytesIO(base64.b64decode(found[-1]))).convert("RGB").save(buffer, "PNG")
    euros = round((google_spend.dollars(pro.MODEL, response.get("usageMetadata", {})) or 0.0)
                  * google_spend.EUROS_PER_DOLLAR, 6)
    return buffer.getvalue(), euros, round(time.time() - began, 1)


def drawn(store, place):
    """The top-down drawing of `place` (its record), drawn once per pick and outline inside the plan writing's spend
    block (its record then says `fresh`), else the one kept for the same pick, outline and wording."""
    pictures = pictures_of(store, place)
    outline = outline_key(pictures)
    wording = wording_of(store, place)
    found = drawing_of(store, place, outline, wording)
    if found:
        return found
    png, euros, seconds = called(wording, pictures, frame_of(store, place))
    record = {"place": place, "concept": concepts.picked(store, place), "outline": outline,
              "sha": concepts.kept(store, png), "at": concepts.now(), "euros": euros, "seconds": seconds,
              "wording": wording}
    store.write_once(f"{AREA}/{place}/{stamp_key(record['at'])}.json", record)
    return {**record, "fresh": True}


def spent(store, places):
    """The euros every drawing of `places` cost, in sum."""
    return round(sum(found["euros"] for place in places for found in drawings(store, place)), 4)
