"""One sheet per person (`python -m tools.characters.generated.sheet <renders> <groom folder> <close-up> <out.jpg>`):
the raw model's row over the regrown hair's row (front, three quarters, side, back, the hairline close), the close-up
photograph and the hair labels beside them, and a line of the run's numbers: the drawn hair's colour against the
photo's (`colours`, also written to <groom folder>/colour.json)."""
import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw

from tools.characters.generated import eyes
from tools.characters.generated import fibre
from tools.characters.generated import labels

VIEWS = ("front", "three_quarter", "side", "back", "hairline")
PANEL = (480, 600)
CAPTION_PX = 28
ROWS = (("raw", "raw TRELLIS.2 model"), ("hair", "hair split off, scalp closed, regrown as strands"))


def panel(path):
    return Image.open(path).convert("RGB").resize(PANEL)


def sheet(renders, groom, closeup, out):
    """The sheet written to `out`."""
    renders, groom = pathlib.Path(renders), pathlib.Path(groom)
    stats = json.loads((groom / "stats.json").read_text())
    found = colours(renders, closeup)
    (groom / "colour.json").write_text(json.dumps(found, indent=1))
    width = PANEL[0] * (len(VIEWS) + 1)
    height = CAPTION_PX + 2 * (PANEL[1] + CAPTION_PX) + PANEL[1] // 2 + CAPTION_PX
    picture = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(picture)
    draw.text((8, 6), line_of(stats) + "; " + colour_line(found), fill=(0, 0, 0))
    top = CAPTION_PX
    for prefix, title in ROWS:
        draw.text((8, top + 6), title + ": " + ", ".join(VIEWS), fill=(0, 0, 0))
        for index, view in enumerate(VIEWS):
            picture.paste(panel(renders / f"{prefix}-{view}.png"), (index * PANEL[0], top + CAPTION_PX))
        top += PANEL[1] + CAPTION_PX
    photo = Image.open(closeup).convert("RGB").resize((PANEL[0], PANEL[0]))
    picture.paste(photo, (len(VIEWS) * PANEL[0], CAPTION_PX * 2))
    draw.text((len(VIEWS) * PANEL[0] + 8, CAPTION_PX + 6), "close-up photograph", fill=(0, 0, 0))
    labels = Image.open(groom / "labels.png").convert("RGB")
    labels = labels.resize((int(labels.width * PANEL[1] / 2 / labels.height), PANEL[1] // 2))
    draw.text((8, top + 6), "hair (and beard) labels on the model's paint, red", fill=(0, 0, 0))
    picture.paste(labels, (0, top + CAPTION_PX))
    picture.save(out, quality=92)


def colours(renders, closeup):
    """The hair's colour (`fibre.measured`) in the photo (`labels.closeup_hair`) and drawn: the front view's head hair
    (`hair-front-mask.png`'s alpha) down to as far under the pupils as the photo's is read (CLOSEUP["chin"]), the
    picture first scaled so the pupils lie as far apart as in the photo (the lightness's spread is read at the photo's
    scale)."""
    photo = np.asarray(Image.open(closeup).convert("RGB").resize((labels.CLOSEUP["size"],) * 2)) / 255.0
    photo_gap = float(np.linalg.norm(np.subtract(*eyes.photo_pupils(photo))))
    pupils = np.asarray(json.loads((pathlib.Path(renders) / "hair-front.json").read_text())["pupils"])
    scale = photo_gap / float(np.linalg.norm(pupils[1] - pupils[0]))
    drawn = Image.open(pathlib.Path(renders) / "hair-front.png").convert("RGB")
    size = (round(drawn.width * scale), round(drawn.height * scale))
    drawn = np.asarray(drawn.resize(size, Image.Resampling.LANCZOS)) / 255.0
    alpha = np.asarray(Image.open(pathlib.Path(renders) / "hair-front-mask.png").convert("RGBA")
                       .resize(size, Image.Resampling.LANCZOS))[..., 3] / 255.0
    hair = alpha > fibre.SWATCH["alpha"]
    hair[int((pupils[:, 1].mean() + labels.CLOSEUP["chin"] * photo_gap / scale) * scale):] = False
    pair = {"photo": labels.closeup_hair(closeup), "drawn": fibre.measured(drawn[hair])}
    return {kind: {"lab": np.round(value["lab"], 1).tolist(), "spread": round(value["spread"], 1)}
            for kind, value in pair.items()}


def colour_line(found):
    """The hair colour's words: photo against drawn, CIELAB and the lightness's spread."""
    return "hair Lab photo {} spread {} / drawn {} spread {}".format(
        found["photo"]["lab"], found["photo"]["spread"], found["drawn"]["lab"], found["drawn"]["spread"])


def line_of(stats):
    """The numbers' line."""
    fibre = stats["fibre"]
    words = [f"{stats['strands']} strands", f"hair {stats['hair_share_of_head']:.1%} of the head's triangles",
             f"hair volume {stats['hair_volume_l']} l", f"melanin {fibre['melanin']} redness {fibre['redness']}"
             f" white {fibre['white_share']}"]
    if "beard_strands" in stats:
        words.append(f"beard {stats['beard_strands']} strands, {stats['beard_share_of_head']:.1%} of the head")
    return "; ".join(words)


if __name__ == "__main__":
    sheet(*sys.argv[1:5])
