"""Each take's predicted outcome before the batch, from a measured failure mode only (#21's batch contract): a group
whose shape every measured row of that shape failed on is a predicted gap, bought all the same and judged by the
real gates (a prediction never drops a row from the Buy, 2026-10-24); each with its shape's measured close-up pass
share beside it; a take this environment's own accepted outputs measured is predicted by that instead (`own_outcome`).
No threshold is a guess at an outcome: the rates are counted
here from the hub's prop-route table (paper/evidence/compare-hub/table.json, 13 objects, 2026-10) against those
objects' sizes as measured (sizes.json beside it, from the hub's inventory of then), every time.

Shapes by size alone (groups.sides, each side over the longest): a rod has its middle side at most ROD of its
longest (a strut, a rib, a pipe), a sheet its shortest side at most SHEET (a mat, a panel), anything else is solid.
On the hub every rod failed the close-up's shape check (the Pro takes), and so did the one sheet; a shape with fewer
than MIN_MEASURED measured rows is `at risk`, never a predicted gap. A row the close-up's failure no longer leaves a
gap is not predicted one: a thin straight row (score/stages/props/thin_straight.py, 2026-10-25) is built in code when
every close-up failed, so it is `at risk`, its code build's likeness on today's SAM 3 cut not measured yet.

A take measured here (`environment_measures`, `own_outcome`; 2026-10-26: 85 rows were `at risk` by the hub's 13
objects while Batch 1 try 4 had drawn and judged most of them): its place's accepted close-up output names its first
row at the object size it is asked at today (tools/props/closeup/stage.py object_size), under today's request (a row
that lies flat measured before FLAT_VIEW_SINCE was drawn at another view, one laid far off before FAR_CROP_SINCE
(one anchored in the sky: SKY_BEYOND_SINCE) from the whole painting: one that passed there is `at risk`, never its
shape's hub rate; a row every take failed before LATER_TAKES_SINCE is asked anew, its next takes from the crop
alone and upright). Its close-up passed: `pass`, unless the accepted Pixal3D output's gaps say no model came back (`at risk`), unless it is a flat sheet the code builds then
(score/stages/props/flat_sheet.py): that build is made here, free, from its stored close-up and held to the likeness
row's free checks that need no paint (`sheet_faults`), so it is a `pass` or a `predicted gap`. Every Pro take failed: a code build the accepted
likeness output judged passes or is a `predicted gap`; one not judged yet is measured free like a sheet's when its
SAM 3 mask is stored (straight-masks@<place>, score/stages/props/masks_row.py: `straight_outcome`, its cut the build's
input), else `at risk`; so is a thin straight row the hub's rate gives a failed close-up; a row no route builds after
is a `predicted gap` (its next step draws new takes, judged by the real gate: bought all the same).
"""
import json
import pathlib
import tempfile

from PIL import Image

import score.stages.props.prop_data as prop_data
from score.stages.complete.prepare import groups
from score.stages.props import thin_straight
import score.stages.props.flat_sheet as flat_sheet

REPO = pathlib.Path(__file__).resolve().parents[4]
TABLE = REPO / "paper/evidence/compare-hub/table.json"
SIZES = TABLE.with_name("sizes.json")  # each table object's size as the hub's inventory gave it when it was measured
ROD = 0.15
SHEET = 0.05
MIN_MEASURED = 3
CLOSEUP_FAILED = "fail: close-up"
# When a close-up of a row that lies flat was first asked from straight above (tools/props/closeup b256f79c, commit
# time in UTC): a flat row's close-up accepted before it was drawn and judged at the three-quarter view.
FLAT_VIEW_SINCE = "2026-10-25T19:52:27+00:00"
# When a gap's later takes (past stage.PRO_TAKES, retry-4 on) were first asked from the crop alone and upright
# (tools/props/closeup/stage.py UPRIGHT, commit time in UTC): a row every take of which failed in a close-up accepted
# before is asked anew when its step is bought again, so its failures are not measured at today's request.
LATER_TAKES_SINCE = "2026-10-26T08:30:50+00:00"
# When a row laid far off (groups.far_made, `far`) was first asked from its crop alone, never the room (tools/props/
# closeup/stage.py pro_wording): its close-up accepted before was drawn from the whole painting.
FAR_CROP_SINCE = "2026-10-26T10:10:22+00:00"
# When a row anchored in the sky was first counted beyond its place (groups.beyond_of), so laid far off and asked from
# its crop alone: its close-up accepted before was drawn from the whole painting (the square's rocket, 2026-10-26).
SKY_BEYOND_SINCE = "2026-10-26T13:10:03+00:00"


def shape_of(size):
    """rod, sheet or solid by a size's sides; None for a size that is not three positive numbers."""
    found = groups.sides(size)
    if found is None:
        return None
    shortest, middle = found
    if middle <= ROD:
        return "rod"
    return "sheet" if shortest <= SHEET else "solid"


def measured(table_rows, sizes):
    """{shape: {"failed", "of", "objects"}} of the table's objects with a size (`sizes`, {object: size}): how many of
    each shape failed at the close-up (the route's first paid step)."""
    found = {}
    for row in table_rows:
        shape = shape_of(sizes.get(row["object"]))
        if shape is None:
            continue
        counted = found.setdefault(shape, {"failed": 0, "of": 0, "objects": []})
        counted["of"] += 1
        counted["objects"].append(row["object"])
        counted["failed"] += row["prop route"].startswith(CLOSEUP_FAILED)
    return found


def hub_rates():
    """measured() of the hub's table against its objects' sizes as measured (SIZES, beside the table)."""
    rows = json.loads(TABLE.read_text())["rows"]
    return measured(rows, json.loads(SIZES.read_text())["sizes"])


def predicted(size, rates, row=None, take=None, measures=None):
    """{outcome, shape, pass_share, mode, measured} of a take of this size (its first inventory row `row`, by its
    name and noun): `predicted gap` when every one of at least MIN_MEASURED measured rows of its shape failed the
    close-up and no route builds it after (code_built; one that is built is its build's measured outcome where its
    mask is stored, `straight_outcome` of the take and its place's `measures`, else `at risk`), `at risk` when its
    shape has fewer measured rows and some failed, else `pass` (pass_share its shape's measured close-up pass share,
    None unmeasured)."""
    shape = shape_of(size)
    counted = rates.get(shape)
    if counted is None:
        return {"outcome": "pass", "shape": shape, "pass_share": None, "mode": None,
                "measured": f"no measured row of shape {shape}"}
    said = f"{counted['failed']} of {counted['of']} hub {shape}s failed the close-up ({TABLE.name})"
    share = round(1 - counted["failed"] / counted["of"], 3)
    if counted["failed"] == counted["of"] and counted["of"] >= MIN_MEASURED:
        if code_built(row, size):
            built = straight_outcome(take, row, measures) if take else None
            if built is not None:
                return {"shape": shape, **built, "measured": f"{said}; {BUILD_MEASURED}"}
            return {"outcome": "at risk", "shape": shape, "pass_share": None, "measured": said,
                    "mode": "close-up fails; built in code after (thin_straight), its likeness not measured yet"}
        return {"outcome": "predicted gap", "shape": shape, "pass_share": share,
                "mode": f"close-up: every Pro take of a {shape} failed the shape check", "measured": said}
    outcome = "at risk" if counted["failed"] and counted["of"] < MIN_MEASURED else "pass"
    return {"outcome": outcome, "shape": shape, "pass_share": share, "mode": None, "measured": said}


def code_built(row, size):
    """Whether a row whose close-up fails is built in code instead (thin_straight.thin_straight on its size)."""
    return row is not None and thin_straight.thin_straight({**row, "size": size})


def environment_measures(store, places):
    """{place: {at, closeups, unmade, built, masks}} from each place's accepted outputs: the close-up row's objects
    (closeups.json, by a take's first row) and when it was accepted, the takes Pixal3D made no model of (its batch
    gaps), {row: passed} of the code builds the likeness row judged (likeness.json `made` code; passed when no
    batch gap of it is carried), and the thin straight rows' masks (straight-masks@<place>'s output, or None)."""
    found = {}
    for place in places:
        standing = store.current_accept(f"closeup@{place}")
        masks = store.accepted(f"straight-masks@{place}")
        if standing is None and masks is None:
            continue
        found[place] = {"store": store, "masks": masks}
        if standing is not None:
            found[place].update(
                at=standing["at"],
                closeups=(store.read_file(standing["output"], "closeups.json") or {}).get("objects", {}),
                unmade=gap_objects(store, store.accepted(f"pixal@{place}"), "pixal"),
                built=code_builds(store, store.accepted(f"likeness@{place}")), closeup_output=standing["output"])
    return found


def gap_objects(store, output, row):
    """The objects the output's batch gaps written by `row` name; none without an output."""
    gaps = (store.read_file(output, "batch-gaps.json") or {}).get("gaps", []) if output else []
    return {item for entry in gaps if entry["row"] == row for item in entry["objects"]}


def code_builds(store, output):
    """{row: passed} of the code builds a likeness output judged."""
    if output is None:
        return {}
    found = (store.read_file(output, "likeness.json") or {}).get("objects", {})
    gapped = {item for entry in (store.read_file(output, "batch-gaps.json") or {}).get("gaps", [])
              for item in entry["objects"]}
    return {row: row not in gapped for row, entry in found.items() if entry.get("made") == "code"}


def far_since(row):
    """When a far row was first asked from its crop alone: SKY_BEYOND_SINCE for one anchored in the sky, else
    FAR_CROP_SINCE."""
    return SKY_BEYOND_SINCE if row.get("anchor") == "sky" else FAR_CROP_SINCE


def own_outcome(take, row, measures, rows=None):
    """The take's outcome as this environment measured it (module docstring), or None when it is not measured at
    today's size and request; `row` its first inventory row, `measures` its place's environment_measures, `rows` its
    place's inventory rows by id (a thin straight row whose close-up passed takes the code route with a row of its
    kind whose close-up failed: thin_straight.kin, as the Pixal3D row builds it)."""
    first = take["rows"][0]
    record = (measures or {}).get("closeups", {}).get(first)
    size = (row or {}).get("read_size") or take["size"]
    if record is None or not size or [float(side) for side in record.get("read_size") or record["size"]] != \
            [float(side) for side in size]:
        return None
    with prop_data.tools("props/closeup"):
        import check
    node = f"closeup@{take['place']}"
    outcome = {"shape": shape_of(take["size"]), "pass_share": None, "mode": None}
    asked = None
    if check.lies_flat(size) and measures["at"] < FLAT_VIEW_SINCE:
        asked = "drawn at the three-quarter view, today from above"
    elif (row or {}).get("far") and measures["at"] < far_since(row):
        asked = "drawn from the whole painting, today from its crop alone"
    if asked:
        # its own pass outweighs its shape's hub rate (2026-10-26: the square's 60 m rocket passed, yet was a
        # predicted gap as a hub "rod" once laid far off); its failures at the old request are not measured
        return {**outcome, "outcome": "at risk", "measured": f"its close-up passed ({node})",
                "mode": f"its close-up was {asked}: not measured at today's request"} if record["drawn_by"] else None
    drawn = {name: rows[name] for name in measures.get("closeups", {}) if name in (rows or {})}
    failed = {name for name, entry in measures.get("closeups", {}).items() if not entry["drawn_by"]}
    coded = record["drawn_by"] and first in thin_straight.kin(failed, drawn)
    if record["drawn_by"] and not coded:
        if {first, take["take"]} & measures["unmade"]:
            sheet = sheet_outcome(take, row, measures)
            if sheet is not None:
                return {**outcome, **sheet, "measured": f"its close-up passed ({node}); its flat sheet code build "
                                                         f"measured free against it"}
            return {**outcome, "outcome": "at risk", "mode": f"Pixal3D made no model of it (pixal@{take['place']})",
                    "measured": f"its close-up passed ({node})"}
        return {**outcome, "outcome": "pass", "pass_share": 1.0, "measured": f"its close-up passed ({node})"}
    said = (f"its close-up passed ({node}); a row of its kind failed its own, so it is built in code with it "
            f"(thin_straight.kin)" if coded
            else f"every one of its {len(record['takes'])} Pro takes failed the close-up ({node})")
    if first in measures["built"]:
        passed = measures["built"][first]
        return {**outcome, "outcome": "pass" if passed else "predicted gap", "measured": said,
                "mode": None if passed else f"its code build failed the likeness (likeness@{take['place']})"}
    if code_built(row, take["size"]):
        built = straight_outcome(take, row, measures)
        if built is not None:
            return {**outcome, **built, "measured": f"{said}; {BUILD_MEASURED}"}
        return {**outcome, "outcome": "at risk", "measured": said,
                "mode": "close-up failed; built in code after (thin_straight), its likeness not measured yet"}
    if measures["at"] < LATER_TAKES_SINCE:
        return None
    return {**outcome, "outcome": "predicted gap", "pass_share": 0.0, "measured": said,
            "mode": "close-up: every Pro take of it failed the shape check"}


def sheet_outcome(take, row, measures):
    """{outcome, pass_share, mode} of a take whose Pixal3D made no model by its flat sheet code build, measured free
    (sheet_faults); None for a row that is no sheet (flat_sheet.sheet) or whose close-up is not stored."""
    sized = {**(row or {}), "size": take["size"]}
    if row is None or "store" not in measures or not flat_sheet.sheet(sized):
        return None
    faults = sheet_faults(measures["store"], measures["closeup_output"], take["place"], take["rows"][0], sized)
    return None if faults is None else judged_build(faults, "flat sheet code build (flat_sheet.py)")


def judged_build(faults, build):
    """{outcome, pass_share, mode} of a code build by its free faults."""
    if faults:
        return {"outcome": "predicted gap", "pass_share": 0.0,
                "mode": f"its {build} fails the likeness: {'; '.join(faults)}"}
    return {"outcome": "pass", "pass_share": 1.0, "mode": None}


BUILD_MEASURED = "its thin straight code build measured free against its SAM 3 mask (straight-masks)"


def straight_outcome(take, row, measures):
    """{outcome, pass_share, mode} of a thin straight take by its code build (thin_straight.write_take, from its
    concept crop cut by its SAM 3 mask as straight-masks@<place> stored it), held to the likeness row's free checks
    (build_faults); a `predicted gap` when SAM 3 found nothing of it (the Pixal3D row leaves it a gap); None when its
    row was not asked there."""
    output = (measures or {}).get("masks")
    if output is None or row is None:
        return None
    store, name = measures["store"], take["rows"][0]
    if name not in (store.read_file(output, "masks.json") or {}).get("asked", []):
        return None
    sha = store.listing(output).get(f"cuts/{name}.png")
    if sha is None:
        return {"outcome": "predicted gap", "pass_share": 0.0,
                "mode": "SAM 3 found nothing in its box (straight-masks): no code build"}
    sized = {**row, "size": take["size"]}
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        store.place_blob(sha, folder / "cut.png")
        views = thin_straight.write_take(name, sized, Image.open(folder / "cut.png"), "built", folder / "pixal",
                                         folder / "cut.png")
        faults = build_faults(folder / "pixal" / f"{name}-final.glb", views / "input.png", take["place"], name, sized,
                              folder, straight=True)
    return judged_build(faults, "thin straight code build (thin_straight.py)")


def sheet_faults(store, closeup_output, place, name, row):
    """The faults of row `name`'s flat sheet code build (flat_sheet.write_take, from its close-up in the stored
    close-up output) by the likeness row's free checks that need no paint (score/stages/props/likeness_row.py:
    `outline`, at likeness.OUTLINE_LEAST on the close-up as its take's input cut it, and `thin and in proportion`;
    `close-up parts present` needs the finish route's parts, so the likeness row judges it); None when the close-up
    is not stored. CPU only: no renderer, no model, nothing rented."""
    sha = store.listing(closeup_output).get(f"closeups/{name}.png")
    if sha is None:
        return None
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        store.place_blob(sha, folder / "closeup.png")
        views = flat_sheet.write_take(name, row, folder / "closeup.png", "built", folder / "pixal", folder / "cut")
        return build_faults(folder / "pixal" / f"{name}-final.glb", views / "input.png", place, name, row, folder)


def build_faults(model, picture, place, name, row, folder, straight=False):
    """The faults of a code build `model` held to `picture` (its take's input.png) as the likeness row holds a code
    take (likeness_row.object_record): `outline` at likeness.OUTLINE_LEAST on that picture as Pixal3D's cut makes it
    (a thin straight build's, `straight`, turned upright or level: likeness_row.straight_cut), and `thin and in
    proportion`; `close-up parts present` needs the finish route's parts, so the likeness row judges it. CPU only: no
    renderer, no model, nothing rented."""
    import score.stages.props.likeness as likeness
    import score.stages.props.likeness_row as likeness_row
    cut = (likeness_row.straight_cut(picture, folder / "pixal-cut", name, row["size"]) if straight
           else likeness_row.pixal_cut(picture, folder / "pixal-cut", name))
    found = {**likeness.best_way(model, cut, row.get("read_size") or row["size"]),
             **likeness_row.model_checks(model, row["size"], f"{place}_{name}", False)}
    return likeness_row.outline_faults(name, found) + likeness_row.model_faults(name, found)
