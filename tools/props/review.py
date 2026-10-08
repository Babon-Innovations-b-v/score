"""Build the page that shows each prop beside the picture it was built from.

Seeing the two together is how the limits become obvious: what the picture showed clearly is what
came through, and what it hid or flattened is what went wrong. It is also how a prop gets chosen,
so several takes of the same prop can sit on one page and be compared. A prop is shown as
pixal.py left it (WORK/pixal/<name>-final.glb) beside its picture (PICTURES/<name>.png).
"""
import argparse
import base64
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from paths import PAGES, PICTURES, make_directories  # noqa: E402
from pixal import OUT  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
# The hull colour from the design system: props are recoloured per kind on import anyway.
DEFAULT_COLOUR = "#f1efe8"
BACKGROUND = "#e8dcc0"


def fact(key, value):
    return f'<div class="fact"><div class="k">{key}</div><div class="v">{value}</div></div>'


def model_of(name):
    """The finished model pixal.py made under this name, refused when there is none."""
    path = OUT / f"{name}-final.glb"
    if not path.exists():
        raise SystemExit(f"no model made yet for {name}: {path} is missing")
    return path


def triangles_in(path):
    """How many triangles the model holds, all its meshes together."""
    import trimesh
    return len(trimesh.load(path, force="mesh").faces)


def block(name, triangles, size_kb):
    facts = fact("triangles", f"{triangles:,}") + fact("file", f"{size_kb:.0f} KB")
    encoded = base64.b64encode((PICTURES / f"{name}.png").read_bytes()).decode()
    return f"""
  <div class="prop">
    <h2>{name.replace('-', ' ')}</h2>
    <div class="panes">
      <div class="pane"><span class="tag">the picture</span>
        <img src="data:image/png;base64,{encoded}" alt="reference picture for {name}"></div>
      <div class="pane" id="view-{name}"><span class="tag">the prop, in the look</span></div>
    </div>
    <div class="facts">{facts}</div>
    <div class="hint">drag to turn</div>
  </div>"""


def build(names, title, colour, out_name):
    make_directories()
    blocks, data, total = [], [], 0
    for name in names:
        model = model_of(name)
        triangles = triangles_in(model)
        total += triangles
        blocks.append(block(name, triangles, model.stat().st_size / 1024))
        data.append({
            "name": name,
            "glb": base64.b64encode(model.read_bytes()).decode(),
            "colour": colour,
            "background": BACKGROUND,
            "turn": 0.35,
        })

    page = (HERE / "review.html").read_text()
    for key, value in {
        "TITLE": title,
        "PROPS": "\n".join(blocks),
        "DATA": json.dumps(data),
        "FOOTER": (f"Farm Factory, Looks workstream. {len(names)} "
                   f"prop{'s' if len(names) != 1 else ''}, {total:,} triangles in total. "
                   "Pictures by FLUX.2 klein 4B, models by Pixal3D; nothing modelled by hand."),
    }.items():
        page = page.replace(f"%%{key}%%", value)
    if "%%" in page:
        raise SystemExit("the page still has an unfilled placeholder")

    path = PAGES / f"{out_name}.html"
    path.write_text(page)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="+", help="prop names to show, in the order you want them")
    parser.add_argument("--title", default="Props From Pictures")
    parser.add_argument("--colour", default=DEFAULT_COLOUR)
    parser.add_argument("--out", default="review")
    args = parser.parse_args()
    print(build(args.names, args.title, args.colour, args.out))


if __name__ == "__main__":
    main()
