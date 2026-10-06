"""The library's browser page: every family and variant of data/library/materials.json with its swatches at the three
wear levels, its recipe, token and settings, and the reference it is tuned to. Written outside the repo.

    ~/.farm-factory-props/env/bin/python tools/props/library/browser.py <swatch folder> <out folder>

The swatch folder is a swatch.py run over the library (<variant>-w<wear>.png). Writes <out>/library.html and its
pictures under <out>/img/library/. The page grows with the library: a new variant is a new card on the next run.
"""
import html
import pathlib
import sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import library  # noqa: E402

WEARS = (("0.0", "new"), ("0.4", "worked"), ("0.8", "worn"))
SHOWN_SETTINGS = ("roughness", "metal", "bump", "bump_size", "wear_scale", "pitch", "contrast", "quilt_size")
STYLE = """
:root { --bg: #e3e7e2; --panel: #f3f5f1; --fg: #1b1712; --muted: #5a4e40; --line: #c9cfc8; --accent: #a3302a;
  --display: "Barlow Condensed", "Arial Narrow", sans-serif; --body: "Barlow", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #1b1712; --panel: #29221b;
  --fg: #f3ebda; --muted: #b8aa92; --line: #43392e; --accent: #f2766a; color-scheme: dark } }
:root[data-theme="dark"] { --bg: #1b1712; --panel: #29221b; --fg: #f3ebda; --muted: #b8aa92; --line: #43392e;
  --accent: #f2766a; color-scheme: dark }
body { background: var(--bg); color: var(--fg); font: 15px/1.5 var(--body); margin: 0; }
main { max-width: 1180px; margin: 0 auto; padding: 28px 16px 60px; display: grid; gap: 34px; }
h1, h2 { font-family: var(--display); margin: 0; line-height: 1.1; }
h1 { font-size: clamp(32px, 5vw, 50px); } h2 { font-size: 26px; }
nav { display: flex; flex-wrap: wrap; gap: 8px; }
nav a { font: 600 14px var(--display); letter-spacing: .06em; text-transform: uppercase; color: var(--accent);
  text-decoration: none; border: 1px solid var(--line); padding: 4px 10px; border-radius: 3px; }
section { display: grid; gap: 12px; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 14px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 4px; padding: 12px; display: grid;
  gap: 8px; min-width: 0; }
.card h3 { margin: 0; font: 600 18px var(--display); }
.wear { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
.wear figure { margin: 0; } .wear img { width: 100%; display: block; border-radius: 3px; }
.wear figcaption, .meta { font-size: 12.5px; color: var(--muted); }
.meta code { font: 12px var(--mono); }
.chip { display: inline-block; width: 12px; height: 12px; border-radius: 2px; vertical-align: -1px;
  border: 1px solid var(--line); margin-right: 4px; }
p { margin: 0; max-width: 70ch; }
"""


def hex_of(linear_colour):
    def one(value):
        value = value * 12.92 if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055
        return max(0, min(255, round(value * 255)))
    return "#" + "".join(f"{one(value):02x}" for value in linear_colour)


def picture(source, target, width=300):
    """A swatch as a small JPEG on the page's light ground."""
    image = Image.open(source).convert("RGBA")
    ground = Image.new("RGBA", image.size, (238, 236, 230, 255))
    ground.alpha_composite(image)
    ground = ground.convert("RGB").resize((width, round(image.height * width / image.width)))
    target.parent.mkdir(parents=True, exist_ok=True)
    ground.save(target, quality=85)


def card(name, spec, swatches, out):
    figures = []
    for wear, said in WEARS:
        source = swatches / f"{name}-w{wear}.png"
        if source.exists():
            picture(source, out / "img/library" / f"{name}-w{wear}.jpg")
            figures.append(f'<figure><img loading="lazy" src="img/library/{name}-w{wear}.jpg" '
                           f'alt="{html.escape(name)}, {said}"><figcaption>{said}</figcaption></figure>')
    settings = ", ".join(f"{key} {spec[key]:g}" for key in SHOWN_SETTINGS if isinstance(spec.get(key), (int, float)))
    reference = spec.get("reference")
    tuned = f"<br>tuned to: {html.escape(reference['said'])}" if reference else ""
    title = html.escape(name.replace("_", " "))
    return (f'<div class="card"><h3>{title}</h3><div class="wear">{"".join(figures)}</div>'
            f'<div class="meta"><span class="chip" style="background:{hex_of(spec["colour"])}"></span>'
            f'<code>{html.escape(spec["token"])}</code> · recipe <code>{spec["recipe"]}</code><br>{settings}{tuned}'
            f'</div></div>')


def page(swatches, out):
    data = library.theme_library()
    specs = library.library_specs()
    sections, links = [], []
    for family, entry in data["families"].items():
        links.append(f'<a href="#{family}">{family}</a>')
        cards = "".join(card(name, specs[name], swatches, out) for name in entry["variants"])
        sections.append(f'<section id="{family}"><h2>{family} · {len(entry["variants"])}</h2>'
                        f'<p class="meta">{html.escape(entry["is"])}</p><div class="cards">{cards}</div></section>')
    count = len(specs)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>Material Library</title>"
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600&family='
            f'Barlow+Condensed:wght@600;700&family=JetBrains+Mono&display=swap"><style>{STYLE}</style></head>'
            "<body><main>"
            f"<header style='display:grid;gap:10px'><h1>Material Library</h1><p>{count} variants in "
            f"{len(data['families'])} families for the base theme. Every one is a ProcFunc recipe and its settings, "
            f"coloured only from palette tokens, shown at the three wear levels a room can pick. Rooms take them by "
            f"name; the library only grows.</p><nav>{''.join(links)}</nav></header>{''.join(sections)}</main>"
            "</body></html>")


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    swatches, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    (out / "library.html").write_text(page(swatches, out))
    print(out / "library.html")


if __name__ == "__main__":
    main()
