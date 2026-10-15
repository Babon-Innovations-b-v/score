"""A place's review from the framework's store, with no cloud rendering: the accepted assembled stage (its neighbours
output where the place shows others, else its assembly) copied out of the store, the completion gate's checks run on
that copy, its web copy for the viewer (viewer/export.py), and one page holding every gate verdict of the place's
line, each painted model's front and back beside its close-up, the library surfaces the place uses that wait for the
owner's review, and the completion gate's results.

    .venv/bin/python tools/review/store_page.py <place> [--world world1] [--audit <text file>] [--no-check]
        [--no-export]

`--audit` lays the place's section of an audit (a heading line in capitals naming the place, up to the next such
line) on the page as what is still open. Out: WORK/review-store/<place>/ (stage/, page.html, one file with every
picture in it, publishable as it is) and the web copy in the viewer's folder; nothing it makes is committed. The page
reads the store and the stage's check results; it writes neither (the checks write beside the copied stage, as
complete.py does). Walk the place with `viewer/serve.py` at VIEWER_URL.
"""
import argparse
import base64
import html
import io
import json
import pathlib
import shutil
import subprocess
import sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/props"))
from paths import WORK  # noqa: E402
from score import review, stages  # noqa: E402
from score.stages.surfaces import surface_data  # noqa: E402
from score.store import Store  # noqa: E402

OUT = WORK / "review-store"
VIEWER_URL = "http://localhost:8770/view/{place}"
TEMPLATE = HERE / "page.html"
LIBRARY = REPO / "data/library/materials.json"
PLACES = REPO / "data/definitions/place.json"
CLOSE_UPS = WORK / "pixal"  # surface_data.PIXAL
PICTURE_SIDE = 520
OWNER_REVIEW = "owner to review"
PYTHON = sys.executable


def escaped(value):
    return html.escape(str(value))


# --- the stage and its tools --------------------------------------------------------------------------------------

def stage_copy(store, place, folder):
    """The place's accepted assembled stage (complete.py assembled_node: its neighbours output, the shown places copied
    in and pointed at, where it shows others, else its assembly), copied out of the store into `folder` (again only
    when the output moved), so the completion gate can write its results beside it; (its .usda, the output's hash)."""
    sys.path.insert(0, str(REPO / "tools/usd"))
    import complete
    node = complete.assembled_node(place)
    output = store.accepted(node)
    if output is None:
        raise SystemExit(f"{node} has no accepted output")
    marker = folder / "output.txt"
    if not (marker.exists() and marker.read_text() == output):
        shutil.rmtree(folder, ignore_errors=True)
        shutil.copytree(store.checkout(output), folder)
        for path in [folder, *folder.rglob("*")]:
            path.chmod(path.stat().st_mode | 0o200)
        marker.write_text(output)
    return folder / f"{place}.usda", output


def run_completion_gate(place, stage):
    """tools/usd/complete.py check, then done, on the copied stage: the results land in <stage folder>/checks and the
    manifest beside the stage. `done` exits non-zero on a place that is not complete, which the page shows."""
    complete = str(REPO / "tools/usd/complete.py")
    subprocess.run([PYTHON, complete, "check", place, "--stage", str(stage)], check=True)
    subprocess.run([PYTHON, complete, "done", place, "--stage", str(stage)])


def export_viewer(place, stage):
    """The place's web copy for the viewer, under the viewer's memory cap (viewer/CLAUDE.md)."""
    subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=16G", PYTHON,
                    str(HERE / "viewer/export.py"), place, "--stage", str(stage)], check=True)


# --- what the page reads ------------------------------------------------------------------------------------------

def line_status(world, place):
    """{node: its runner status} for the place's own nodes, in table order."""
    runner = stages.runner(world=stages.WORLDS[world]())
    return {node: state for node, state in runner.status([place]).items() if node.endswith(f"@{place}")}


def accepted_output(store, node, folder_of):
    """The checkout of a node's accepted output, or None."""
    output = store.accepted(node)
    return folder_of(output) if output else None


def flagged_surfaces(place):
    """{surface: what was said} of each library surface the place takes that waits for the owner's review."""
    library = json.loads(LIBRARY.read_text())
    variants = {name: entry for family in library["families"].values()
                for name, entry in family.get("variants", {}).items()}
    places = json.loads(PLACES.read_text())
    entry_of = places.get(place) or places.get(host_of(place), {})  # a part takes its host's library surfaces
    taken = {entry["library"] for entry in entry_of.get("materials", {}).values()}
    return {name: variants[name]["said"] for name in sorted(taken)
            if name in variants and OWNER_REVIEW in str(variants[name].get("said", ""))}


def proposals(store, place):
    """The finish registry's proposed library surfaces first named on this place's line."""
    return [entry for entry in store.registry("surfaces") if entry.get("first", {}).get("line") == place]


def audit_section(audit, place):
    """The place's section of an audit text: from the line naming it in capitals to the next capitals heading."""
    lines = audit.read_text().splitlines()
    heading = place.upper()
    start = next((index for index, line in enumerate(lines) if line.strip() == heading), None)
    if start is None:
        return None
    end = next((index for index in range(start + 1, len(lines))
                if lines[index].strip() and lines[index].strip().isupper() and not lines[index].startswith(" ")),
               len(lines))
    return "\n".join(lines[start + 1:end]).rstrip()


# --- the page -----------------------------------------------------------------------------------------------------

def inline_picture(path, caption):
    """A figure with the picture inside the page (JPEG, white behind see-through parts)."""
    picture = Image.open(path).convert("RGBA")
    picture.thumbnail((PICTURE_SIDE, PICTURE_SIDE))
    flat = Image.new("RGB", picture.size, (255, 255, 255))
    flat.paste(picture, mask=picture.split()[3])
    buffer = io.BytesIO()
    flat.save(buffer, "JPEG", quality=84)
    data = base64.b64encode(buffer.getvalue()).decode()
    return (f'<figure><img loading="lazy" src="data:image/jpeg;base64,{data}" alt="{escaped(caption)}">'
            f"<figcaption>{escaped(caption)}</figcaption></figure>")


def answer_pill(answer):
    return f'<span class="pill {"ok" if answer == "pass" else "bad"}">{escaped(answer)}</span>'


def status_pill(found):
    """complete.py's status of the place in its own words (CONTEXT.md): complete, complete apart from named gaps (N)
    or NOT complete; a manifest from before the status says its verdict."""
    status = found.get("status", found["verdict"])
    kind = {"pass": "ok", "gapped": "gapped"}.get(found["verdict"], "bad")
    count = f" ({len(found.get('named_gaps', []))})" if found["verdict"] == "gapped" else ""
    return f'<span class="pill {kind}">{escaped(status + count)}</span>'


def section(anchor, title, body):
    return f'<section id="{anchor}"><h2>{escaped(title)}</h2>{body}</section>'


def line_section(store, statuses):
    """Each node of the place's line: its status, and its accepted output's gates."""
    blocks = []
    for node, state in statuses.items():
        output = store.accepted(node)
        record = review.record_of(store, node, output) if output else None
        judgement = review.newest_judgement(store, record) if record else None
        gates = (review.checks_table(judgement, store.waivers(node, record["key"])) if judgement
                 else '<p class="missing">No accepted output judged.</p>')
        answer = judgement["answer"] if judgement else "none"
        blocks.append(f"<details><summary>{answer_pill(answer)} <b>{escaped(node)}</b> "
                      f'<span class="soft">{escaped(state)}</span></summary>{gates}</details>')
    return section("line", "The line's gates", "".join(blocks))


def completion_section(stage):
    """complete.py's manifest on the copied stage, requirement by requirement, with each check's faults."""
    manifest = stage.parent / "manifest.json"
    if not manifest.exists():
        return section("complete", "Completion gate", '<p class="missing">Not run on this stage.</p>')
    found = json.loads(manifest.read_text())
    rows = []
    for requirement in found["requirements"]:
        result = stage.parent / "checks" / f"{requirement['name']}.json"
        faults = json.loads(result.read_text()).get("faults", []) if result.exists() else []
        if requirement["name"] == "named gaps":  # each gap's numbers and who decided it, from the manifest
            faults = [f"{gap['name']} (decided: {gap['decided']}): {fault}" for gap in found.get("named_gaps", [])
                      for fault in gap["faults"]]
        faults = [fault if isinstance(fault, dict) else {"why": fault} for fault in faults]  # contents checks: text
        shown = "".join(f"<li><code>{escaped(fault.get('row') or '')}</code> {escaped(fault.get('why', fault))}</li>"
                        for fault in faults[:12])
        more = f'<li class="soft">and {len(faults) - 12} more</li>' if len(faults) > 12 else ""
        rows.append(f"<tr><td>{escaped(requirement['name'])}</td><td>{answer_pill(requirement['result'])}</td>"
                    f"<td>{escaped(requirement['why'])}<ul>{shown}{more}</ul></td></tr>")
    return section("complete", "Completion gate",
                   f"<p>tools/usd/complete.py on this stage: {status_pill(found)} "
                   f"({escaped(found['at'])})</p>"
                   '<div class="scroll"><table><tr><th>Requirement</th><th>Result</th><th>Why and faults</th></tr>'
                   f"{''.join(rows)}</table></div>")


def models_section(store, place):
    """Each painted take: its close-up, its parts painted front and back, and each part's surface."""
    parts_folder = accepted_output(store, f"surfaces-parts@{place}", store.checkout)
    if parts_folder is None:
        return section("models", "Painted models", '<p class="missing">Not recorded: no accepted parts.</p>')
    takes = json.loads((parts_folder / "parts.json").read_text())["takes"]
    blocks = []
    for take, entry in takes.items():
        shown = (("close-up", CLOSE_UPS / f"{take}.svviews/input.png"),
                 ("front, each part in its surface's colour", parts_folder / take / "front.png"),
                 ("back", parts_folder / take / "back.png"))
        pictures = [inline_picture(path, f"{take}: {label}") for label, path in shown if path.exists()]
        surfaces = {}
        for part in entry["parts"]:
            surfaces[part["judge"]] = surfaces.get(part["judge"], 0) + part["share"]
        listed = ", ".join(f"{name} {share:.0%}" for name, share in sorted(surfaces.items(), key=lambda item: -item[1]))
        blocks.append(f'<div class="model"><h3>{escaped(take)} <small>'
                      f'{escaped(surface_data.takes(place).get(take, {}).get("object", ""))}</small></h3>'
                      f'<p class="soft">{escaped(listed)}</p><div class="cells">{"".join(pictures)}</div></div>')
    return section("models", "Painted models", "".join(blocks))


def surfaces_section(store, place):
    """The flagged library surfaces the place takes, and the registry's proposals first named on its line."""
    flagged = "".join(f"<tr><td><code>{escaped(name)}</code></td><td>{escaped(said)}</td></tr>"
                      for name, said in flagged_surfaces(place).items())
    proposed = "".join(f"<tr><td>{escaped(entry['name'])}</td><td>{escaped(entry['spec'].get('stands_in', ''))}</td>"
                       f"<td>{escaped(entry['first'].get('take', ''))}</td><td>{escaped(entry['spec'].get('why', ''))}"
                       "</td></tr>" for entry in proposals(store, place))
    body = ("<h3>Library surfaces waiting for the owner's review</h3>"
            + (f'<div class="scroll"><table><tr><th>Surface</th><th>Why it was added</th></tr>{flagged}</table></div>'
               if flagged else '<p class="missing">None.</p>')
            + "<h3>New surfaces the method proposed here (not in the library; a stand-in paints the part)</h3>"
            + (f'<div class="scroll"><table><tr><th>Proposed</th><th>Stands in</th><th>Take</th><th>Why</th></tr>'
               f"{proposed}</table></div>" if proposed else '<p class="missing">None.</p>'))
    return section("surfaces", "Surfaces for review", body)


def open_section(audit, place):
    text = audit_section(audit, place) if audit else None
    body = f"<pre>{escaped(text)}</pre>" if text else '<p class="missing">No audit given.</p>'
    return section("open", "Still open for this place", body)


def head():
    """The review page's title link and style, from page.html (the game's design tokens)."""
    template = TEMPLATE.read_text()
    return template[template.index("<link"):template.index("</style>") + len("</style>")]


def host_of(place):
    """The place a part belongs to (contents.json `part_of`: the garage's and the hangar's door leaves), or None."""
    return json.loads((REPO / "data/checks/contents.json").read_text())["places"].get(place, {}).get("part_of")


def place_name(place):
    """The place's name (data/definitions/place.json); a part of another place, which has none of its own (the
    garage's and the hangar's door leaves, contents.json `part_of`), named with its host."""
    places = json.loads(PLACES.read_text())
    if place in places:
        return places[place].get("name", place)
    host = host_of(place)
    if host:
        return f"{place}, part of {places.get(host, {}).get('name', host)}"
    return place


def page_html(store, place, stage, output, statuses, audit):
    name = place_name(place)
    url = VIEWER_URL.format(place=place)
    origin = stage.parent / "origin.json"
    seed = json.loads(origin.read_text()).get("note", "") if origin.exists() else ""
    sections = [line_section(store, statuses), completion_section(stage), models_section(store, place),
                surfaces_section(store, place), open_section(audit, place)]
    extra = "pre { white-space: pre-wrap; font-size: .85rem } details { border-bottom: 1px solid var(--line); " \
            "padding-block: 6px } summary { cursor: pointer } .soft { color: var(--muted) }"
    title = " ".join(word[:1].upper() + word[1:] for word in name.removeprefix("the ").split())
    return (f"<title>{escaped(title)} review</title>{head().replace('</style>', extra + '</style>')}"
            f"<main><header><h1>{escaped(name)}: review</h1>"
            f"<p>Built from the framework store's accepted outputs, no cloud rendering. Walk it in the viewer on this "
            f'machine: <a href="{url}">{url}</a> (start <code>tools/review/viewer/serve.py</code>).</p>'
            f'<p class="soft">Assembly output <code>{escaped(output)}</code>. {escaped(seed)}</p></header>'
            '<nav aria-label="sections"><a href="#line">Gates</a><a href="#complete">Completion</a>'
            '<a href="#models">Models</a><a href="#surfaces">Surfaces</a><a href="#open">Open</a></nav>'
            f"{''.join(sections)}</main>")


def arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("place")
    parser.add_argument("--world", default="world1", choices=sorted(stages.WORLDS))
    parser.add_argument("--audit", type=pathlib.Path)
    parser.add_argument("--no-check", action="store_true", help="reuse the completion gate's results on the copy")
    parser.add_argument("--no-export", action="store_true", help="keep the viewer's web copy as it is")
    return parser.parse_args()


def main():
    options = arguments()
    store = Store.default()
    folder = OUT / options.place
    stage, output = stage_copy(store, options.place, folder / "stage")
    if not options.no_check:
        run_completion_gate(options.place, stage)
    if not options.no_export:
        export_viewer(options.place, stage)
    page = folder / "page.html"
    statuses = line_status(options.world, options.place)
    page.write_text(page_html(store, options.place, stage, output, statuses, options.audit))
    stamp_review(folder, stage)
    if not options.no_check:  # the gate again, now that the page it reviews by stands: its review requirement
        subprocess.run([PYTHON, str(REPO / "tools/usd/complete.py"), "done", options.place, "--stage", str(stage)])
        page.write_text(page_html(store, options.place, stage, output, statuses, options.audit))
    print(f"{page} viewer {VIEWER_URL.format(place=options.place)}")


def stamp_review(folder, stage):
    """The store page's stamp (complete.py's review requirement): the stage it was built from, by fingerprint."""
    sys.path.insert(0, str(REPO / "tools/usd"))
    import complete
    (folder / complete.REVIEW_STAMP).write_text(json.dumps({"fingerprint": complete.fingerprint(stage),
                                                             "at": complete.now(), "page": "page.html"}, indent=1))


if __name__ == "__main__":
    main()
