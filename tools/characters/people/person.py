"""Who is being built (#112): the look's `person.json`, the choices that differ from one person to
the next. A setting a file leaves out is take C's.

- `scale`: how much the body is scaled from the size SAM 3D Body read; one picture cannot tell a
  big man from a small one.
- `average_body`: built on the body model's average rest shape and skeleton rather than the
  person's own. Take C only: he was drawn, draped and approved that way (#100), before a build
  read a person's own body (#112). Redraped on his own body his drawn mouth doubled and his flag
  lost its star (2026-09-30), so he stays as approved until his face and drapes are redone. That
  redrape was the Warp fork's and was retired with the other Warp drapes (2026-10-10); his kept
  look now wears Newton drapes on the average body.
- `skin`, `hair`, `hair_shine`, `brow`, `iris`, `line`: flat colours picked from the drawing.
- `brow_weight`: the brows' thickness as a share of take C's (thinner on the women).
- `work`, `space`: which design each outfit is, "chinese" (take C's) or "american" (#112's first
  expedition: a light-blue work suit and a white suit with blue stripes and a gold visor).
- `botanist`: a green band round the left upper sleeve and a leaf patch (Nev).
- `glasses`: thin round frames on the head.
- `name`: the letters on the chest name tag (the American outfits).
- `beard`, `freckles`: colours of a painted short beard and moustache, and of freckles.
- `beard_style`, `beard_length`: "full" or "short", and how far down it grows, as a share of
  take C's measure.
- `painted_mouth`: the mouth is one painted line rather than the drawing's (a beard hides the
  drawing's; Nev's drawn one read grim).
- `kit`: this look is a crew kit build (`kit.py`): the `faces`, `hair` styles, `schemes` and
  `plain` outfits its file holds.
- `prologue`, `face`, `hair_style`: this look is one of the prologue's people (`prologue.py`:
  guard, driver, tech_man or tech_woman) on a kit build, with a kit face and hairstyle.
"""
import json

from paths import LOOK

TAKE_C = {"scale": 1.0, "average_body": False, "skin": (226, 172, 138), "hair": (24, 24, 28), "hair_shine": (48, 52, 62),
          "brow": (22, 20, 20), "iris": (62, 40, 30), "line": (46, 30, 26), "brow_weight": 1.0,
          "brow_lift": 0.0,
          "work": "chinese", "space": "chinese", "botanist": False, "glasses": False, "name": None,
          "beard": None, "beard_style": "full", "beard_length": 1.0, "freckles": None,
          "painted_mouth": False, "kit": None, "prologue": None, "face": None, "hair_style": None}


def settings_of_this_person():
    path = LOOK / "person.json"
    settings = dict(TAKE_C)
    if path.exists():
        settings.update(json.loads(path.read_text()))
    for key, value in settings.items():
        if isinstance(value, list):
            settings[key] = tuple(value)
    return settings


WHO = settings_of_this_person()
