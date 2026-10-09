"""The part splitter page's HTML (split_page.py `page`): a summary of every method over the test set, then per model
its clean close-up and each method's split in flat part colours, from the close-up's camera and turned, with its
scores, seconds and euros. The verdict text is the run folder's verdict.json ({"summary": ..., "methods": {...}}),
written by whoever read the results; the page shows what is there.
"""
import html
import json
import statistics

import split_compare

NAMES = {"partcrafter": "PartCrafter", "segvigen": "SegviGen", "segvigen_guided": "SegviGen guided",
         "geosam2_guided": "GeoSAM2 guided"}
HOW = {"partcrafter": "a new model of parts made from the close-up, laid onto ours (the route today)",
       "segvigen": "our model, no guidance",
       "segvigen_guided": "our model, the close-up's regions as its part-colour map",
       "geosam2_guided": "our model, seeded with the close-up's regions"}
STYLE = """
/* Layout: one column of model sheets; each sheet a row of five plates (close-up, then the four splits). */
:root {
  --bg: #eef0ec; --panel: #fbfcfa; --fg: #1a1f1c; --muted: #5a645e; --line: #d5dad4; --accent: #2c6a5c;
  --good: #23704a; --bad: #a63d2b;
  --display: "Barlow Semi Condensed", "Arial Narrow", sans-serif;
  --body: "Source Sans 3", "Segoe UI", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #111513; --panel: #181d1a; --fg: #e3e9e5; --muted: #98a49d; --line: #29312d; --accent: #7cc3b0;
  --good: #6cc492; --bad: #e98a76; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #111513; --panel: #181d1a; --fg: #e3e9e5; --muted: #98a49d; --line: #29312d; --accent: #7cc3b0;
  --good: #6cc492; --bad: #e98a76; color-scheme: dark }
body { background: var(--bg); color: var(--fg); font: 15px/1.5 var(--body); }
main { max-width: 1240px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 64px;
  display: flex; flex-direction: column; gap: 36px; }
h1, h2, h3 { font-family: var(--display); font-weight: 600; text-wrap: balance; margin: 0; letter-spacing: 0.01em; }
h1 { font-size: 2.1rem; line-height: 1.1; }
h2 { font-size: 1.45rem; }
h3 { font-size: 1.05rem; text-transform: uppercase; letter-spacing: 0.06em; }
p { margin: 0; max-width: 68ch; }
.intro { display: flex; flex-direction: column; gap: 12px; }
.muted { color: var(--muted); }
.table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; background: var(--panel); }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { font-family: var(--display); font-weight: 600; font-size: 0.95rem; }
tr:last-child td { border-bottom: 0; }
td.num { font-family: var(--mono); font-size: 0.86rem; white-space: nowrap; }
.verdicts { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
.verdict { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.verdict b { font-family: var(--display); font-size: 1.05rem; color: var(--accent); }
.sheet { display: flex; flex-direction: column; gap: 12px; border-top: 2px solid var(--fg); padding-top: 12px; }
.sheet header { display: flex; flex-wrap: wrap; gap: 4px 14px; align-items: baseline; }
.sheet header .place { font-family: var(--mono); font-size: 0.8rem; color: var(--muted); }
.plates { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
@media (max-width: 1000px) { .plates { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 460px) { .plates { grid-template-columns: minmax(0, 1fr); } }
.plate { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 10px;
  display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.plate .label { font-family: var(--display); font-weight: 600; font-size: 0.98rem; }
.pics { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }
.pics.one { grid-template-columns: 1fr; }
.pics img { width: 100%; height: auto; aspect-ratio: 1; display: block; }
.pics figcaption { font-size: 0.72rem; color: var(--muted); text-align: center; }
figure { margin: 0; }
dl { display: grid; grid-template-columns: auto 1fr; gap: 2px 10px; margin: 0; font-size: 0.84rem; }
dt { color: var(--muted); }
dd { margin: 0; font-family: var(--mono); font-size: 0.8rem; font-variant-numeric: tabular-nums; min-width: 0;
  overflow-wrap: anywhere; }
dd.best { color: var(--good); font-weight: 600; }
.missing { color: var(--bad); font-size: 0.84rem; }
.finishes { font-family: var(--mono); font-size: 0.78rem; color: var(--muted); }
.key { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px 18px; }
.key p { font-size: 0.9rem; }
"""


def esc(text):
    return html.escape(str(text))


def places_of():
    """Each take's places and model names, from data/parts/models.json."""
    found = {}
    for place, models in json.loads((split_compare.labels.REPO / "data/parts/models.json").read_text()).items():
        for model, take in models.items():
            found.setdefault(take, []).append(f"{place}/{model}")
    return found


def owned_share(entry):
    total = len(entry["owned"]) + len(entry["missed"])
    return len(entry["owned"]) / total if total else 1.0


def summary_rows(found):
    """Per method: mean share of finishes owned, mean needless cuts, mean region agreement (whole, pure), mean
    parts, median seconds, mean euros, and on how many models it scored best on owned finishes."""
    rows = []
    for method in NAMES:
        entries = [entry["methods"][method] for entry in found.values() if method in entry["methods"]]
        if not entries:
            continue
        costs = [entry["costs"][method] for entry in found.values() if method in entry.get("costs", {})]
        best = sum(1 for entry in found.values() if method in entry["methods"] and owned_share(entry["methods"][method])
                   >= max(owned_share(other) for other in entry["methods"].values()))
        rows.append({"method": method, "models": len(entries),
                     "owned": statistics.mean(owned_share(entry) for entry in entries),
                     "needless": statistics.mean(entry["needless"] for entry in entries),
                     "whole": statistics.mean(entry["whole"] for entry in entries),
                     "pure": statistics.mean(entry["pure"] for entry in entries),
                     "parts": statistics.median(entry["parts"] for entry in entries),
                     "seconds": statistics.median(cost["seconds"] for cost in costs) if costs else None,
                     "euros": statistics.mean(cost["euros"] for cost in costs) if costs else None,
                     "best": best})
    return rows


def shown(value, spec):
    """A number in `spec`, or nothing when there is none."""
    return "" if value is None else format(value, spec)


def summary_table(rows):
    head = ("<tr><th>Method</th><th>Models</th><th>Finishes with own parts</th><th>Needless cuts</th>"
            "<th>Regions kept whole</th><th>Parts pure in finish</th><th>Parts (median)</th><th>Seconds (median)</th>"
            "<th>€ per object</th><th>Best on finishes</th></tr>")
    body = "".join(
        f"<tr><td><b>{esc(NAMES[row['method']])}</b><br><span class=\"muted\">{esc(HOW[row['method']])}</span></td>"
        f"<td class=\"num\">{row['models']}</td><td class=\"num\">{row['owned']:.0%}</td>"
        f"<td class=\"num\">{row['needless']:.1%}</td><td class=\"num\">{row['whole']:.0%}</td>"
        f"<td class=\"num\">{row['pure']:.0%}</td><td class=\"num\">{row['parts']:g}</td>"
        f"<td class=\"num\">{shown(row['seconds'], '.0f')}</td><td class=\"num\">{shown(row['euros'], '.3f')}</td>"
        f"<td class=\"num\">{row['best']}</td></tr>" for row in rows)
    return f"<div class=\"table-wrap\"><table>{head}{body}</table></div>"


def stat_rows(entry, cost, best, finish_names):
    """A method's plate figures, the best of the model's methods marked."""
    total = len(entry["owned"]) + len(entry["missed"])
    missed = ", ".join(finish_names[number] for number in entry["missed"])
    lines = [("parts", str(entry["parts"]), False),
             ("finishes owned", f"{len(entry['owned'])} of {total}", best["owned"]),
             ("needless cuts", f"{entry['needless']:.1%} ({entry['cut_surfaces']} surfaces)", best["needless"]),
             ("regions whole", f"{entry['whole']:.0%}", False),
             ("parts pure", f"{entry['pure']:.0%}", best["pure"])]
    if cost:
        lines.append(("time, cost", f"{cost['seconds']:.0f} s, €{cost['euros']:.3f}", False))
    rows = "".join(f"<dt>{esc(name)}</dt><dd{' class=\"best\"' if mark else ''}>{esc(value)}</dd>"
                   for name, value, mark in lines)
    note = f"<p class=\"missing\">no own part: {esc(missed)}</p>" if missed else ""
    return f"<dl>{rows}</dl>{note}"


def best_marks(methods):
    """Per method, whether it is the model's best on owned finishes, needless cuts and purity."""
    top_owned = max(owned_share(entry) for entry in methods.values())
    least_cut = min(entry["needless"] for entry in methods.values())
    top_pure = max(entry["pure"] for entry in methods.values())
    return {method: {"owned": owned_share(entry) == top_owned, "needless": entry["needless"] == least_cut,
                     "pure": entry["pure"] == top_pure} for method, entry in methods.items()}


def model_sheet(take, entry, places, notes):
    marks = best_marks(entry["methods"])
    plates = [f"<div class=\"plate\"><span class=\"label\">Clean close-up</span><figure class=\"pics one\">"
              f"<img src=\"{esc(take)}-closeup.webp\" alt=\"{esc(take)} close-up\" loading=\"lazy\"></figure>"
              f"<p class=\"finishes\">finishes: {esc(', '.join(entry['finishes']))}</p></div>"]
    for method in NAMES:
        if method not in entry["methods"]:
            plates.append(f"<div class=\"plate\"><span class=\"label\">{esc(NAMES[method])}</span>"
                          f"<p class=\"missing\">{esc(notes.get(method, 'no split came back'))}</p></div>")
            continue
        pictures = "".join(f"<figure><img src=\"{esc(take)}-{method}-{view}.webp\" alt=\"{esc(NAMES[method])} "
                           f"{view}\" loading=\"lazy\"><figcaption>{caption}</figcaption></figure>"
                           for view, caption in (("front", "close-up camera"), ("turned", "turned 140°")))
        plates.append(f"<div class=\"plate\"><span class=\"label\">{esc(NAMES[method])}</span>"
                      f"<div class=\"pics\">{pictures}</div>"
                      f"{stat_rows(entry['methods'][method], entry.get('costs', {}).get(method), marks[method], entry['finishes'])}"
                      f"</div>")
    return (f"<section class=\"sheet\" id=\"{esc(take)}\"><header><h2>{esc(take)}</h2>"
            f"<span class=\"place\">{esc(' · '.join(places.get(take, [])))}</span></header>"
            f"<div class=\"plates\">{''.join(plates)}</div></section>")


def page(found, total_euros, run):
    """The whole page."""
    verdict = json.loads((run / "verdict.json").read_text()) if (run / "verdict.json").exists() else {}
    places = places_of()
    rows = summary_rows(found)
    verdicts = "".join(f"<div class=\"verdict\"><b>{esc(NAMES[method])}</b><p>{esc(text)}</p></div>"
                       for method, text in verdict.get("methods", {}).items())
    sheets = "".join(model_sheet(take, entry, places,
                                 json.loads((run / take / "laid.json").read_text()) if (run / take / "laid.json").exists()
                                 else {})
                     for take, entry in found.items())
    return f"""<title>Part Splitter Trial</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@600&family=IBM+Plex+Mono:wght@400;600&family=Source+Sans+3:wght@400;600&display=swap">
<style>{STYLE}</style>
<main>
<section class="intro">
<h1>Part splitter trial: our own Pixal3D models</h1>
<p>{esc(verdict.get('summary', 'Results are in; the verdict is not written yet.'))}</p>
<p class="muted">{len(found)} models. Cloud spend for SegviGen and GeoSAM2: €{total_euros:.2f}, machine set-up included.
Painting stays parts plus the surface library; the splitters' picture colours are never kept.</p>
</section>
<section class="verdicts">{verdicts}</section>
<section class="intro"><h3>Over the test set</h3>{summary_table(rows)}</section>
<section class="key">
<p><b>Finishes owned.</b> The close-up's finishes are its SAM 2.1 regions with the material the repaint judged for
each (regions of one material are one finish; under 1% of the seen area left out). A finish owns parts when at
least 60% of its seen area lies in parts that are at least 70% that finish.</p>
<p><b>Needless cuts.</b> Area on a smooth surface (folds under 15°) lying outside the surface's largest part while
showing the same finish, or no finish the close-up saw, as a share of the model.</p>
<p><b>Regions whole, parts pure.</b> The split drawn from the close-up's camera, pixel by pixel against the close-up:
how much of each region lies in its main part, and how much of each part lies in its main finish.</p>
<p><b>Time and cost.</b> The object's own run on its machine (model loading shared over the takes of a share), at
that machine's rate; PartCrafter from the repaint's own batch records.</p>
</section>
{sheets}
</main>
"""
