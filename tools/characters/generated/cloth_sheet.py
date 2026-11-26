"""A generated person's cloth sheet: the cloth row over the skinned row (blender_cloth.py's panels: standing front, the
stride from the side and three quarters, the back), cloth.json's numbers on top; and the two films side by side.

    python -m tools.characters.generated.cloth_sheet <cloth renders> <skinned renders> <cloth.json> <sheet.png> <title>
        [<film.mp4>]
"""
import json
import pathlib
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

PANELS = [("standing_front", "standing, front"),
          ("walk_side_left_ahead", "walk side: left ahead"), ("walk_side_passing", "side: passing"),
          ("walk_side_right_ahead", "side: right ahead"),
          ("walk_three_quarter_left_ahead", "3/4: left ahead"), ("walk_three_quarter_passing", "3/4: passing"),
          ("walk_three_quarter_right_ahead", "3/4: right ahead"), ("walk_back_passing", "back: passing")]
HEIGHT = 720
GAP = 8
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FPS = 24


def row(folder):
    pictures = [Image.open(pathlib.Path(folder) / f"{panel}.png").convert("RGB") for panel, _ in PANELS]
    return [picture.resize((round(picture.width * HEIGHT / picture.height), HEIGHT), Image.LANCZOS)
            for picture in pictures]


def summary(record):
    """The run's numbers in one line a clip."""
    lines = []
    for clip, run in record["runs"].items():
        parts = [f"{kind}: riding {found['riding_share']:.0%}, deepest in body {found['deepest_m'] * 1000:.0f} mm, "
                 f"drawn {found['deepest_drawn_m'] * 1000:.0f} mm, stretch {found['largest_stretch']:.2f}, "
                 f"drift {found['drift_most_m'] * 100:.0f} cm, jitter p99 {found['jitter_99_m_per_frame2'] * 1000:.1f} "
                 f"mm/frame2"
                 for kind, found in run["garments"].items()]
        lines.append(f"{clip} ({run['engine'].split(' (')[0]}, {run['seconds']:.0f} s): " + "; ".join(parts))
    return lines


def sheet(cloth, skinned, record, out, title):
    try:
        font = ImageFont.truetype(FONT, 20)
    except OSError:
        font = ImageFont.load_default()
    rows = [("cloth", row(cloth)), ("skinned", row(skinned))]
    width = sum(picture.width for picture in rows[0][1]) + GAP * (len(PANELS) - 1)
    top = 30 * (2 + len(record["runs"]))
    picture = Image.new("RGB", (width, top + 2 * (HEIGHT + 30)), "white")
    draw = ImageDraw.Draw(picture)
    draw.text((6, 6), f"{title}: {record['height_m']} m, garments as cloth (above) and skinned whole (below)",
              fill="black", font=font)
    for number, line in enumerate(summary(record)):
        draw.text((6, 36 + 30 * number), line, fill="black", font=font)
    y = top
    for name, pictures in rows:
        x = 0
        for panel, (_, label) in zip(pictures, PANELS):
            picture.paste(panel, (x, y + 28))
            draw.text((x + 6, y + 2), f"{name}: {label}", fill="black", font=font)
            x += panel.width + GAP
        y += HEIGHT + 30
    out.parent.mkdir(parents=True, exist_ok=True)
    picture.save(out)
    picture.save(out.with_suffix(".jpg"), quality=88)


def film(cloth, skinned, out):
    """The two films side by side (cloth left), H.264 at FPS."""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i",
                    str(pathlib.Path(cloth) / "film/%03d.png"), "-framerate", str(FPS), "-i",
                    str(pathlib.Path(skinned) / "film/%03d.png"), "-filter_complex", "hstack=inputs=2", "-c:v",
                    "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(out)], check=True)


def main():
    cloth, skinned, record, out, title = sys.argv[1:6]
    sheet(cloth, skinned, json.loads(pathlib.Path(record).read_text()), pathlib.Path(out), title)
    if len(sys.argv) > 6:
        film(cloth, skinned, sys.argv[6])
    print("CLOTH SHEET", out, flush=True)


if __name__ == "__main__":
    main()
