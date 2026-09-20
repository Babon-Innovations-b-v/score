"""Build the page that shows each prop beside the picture it was built from.

Seeing the two together is how the limits become obvious: what the picture showed clearly is what
came through, and what it hid or flattened is what went wrong. It is also how a prop gets chosen,
so several takes of the same prop can sit on one page and be compared.
"""
import argparse
import base64
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from paths import MESHES, PAGES, make_directories  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
# The hull colour from the design system: props are recoloured per kind on import anyway.
DEFAULT_COLOUR = "#f1efe8"
BACKGROUND = "#e8dcc0"


def fact(key, value):
    return f'<div class="fact"><div class="k">{key}</div><div class="v">{value}</div></div>'


def block(report, name):
    picture = pathlib.Path(report["picture"])
    facts = "".join([
        fact("triangles", f"{report['faces_final']:,}"),
        fact("from", f"{report['faces_raw']:,}"),
        fact("file", f"{report['size_kb']:.0f} KB"),
        fact("peak VRAM", f"{report['peak_vram_gb']:.1f} GB"),
        fact("generate", f"{report['generate_seconds']:.0f} s"),
    ])
    encoded = base64.b64encode(picture.read_bytes()).decode()
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
    blocks, data = [], []
    for name in names:
        report_path = MESHES / f"{name}-report.json"
        if not report_path.exists():
            raise SystemExit(f"no mesh made yet for {name}: {report_path} is missing")
        report = json.loads(report_path.read_text())
        blocks.append(block(report, name))
        data.append({
            "name": name,
            "glb": base64.b64encode((MESHES / f"{name}.glb").read_bytes()).decode(),
            "colour": colour,
            "background": BACKGROUND,
            "turn": 0.35,
        })

    total = sum(json.loads((MESHES / f"{name}-report.json").read_text())["faces_final"]
                for name in names)
    page = (HERE / "review.html").read_text()
    for key, value in {
        "TITLE": title,
        "PROPS": "\n".join(blocks),
        "DATA": json.dumps(data),
        "FOOTER": (f"Farm Factory, Looks workstream. {len(names)} "
                   f"prop{'s' if len(names) != 1 else ''}, {total:,} triangles in total. "
                   "Generated from sentences; nothing modelled by hand."),
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
