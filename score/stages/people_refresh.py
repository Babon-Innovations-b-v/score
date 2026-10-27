"""The people rows' refresh from the store (free): rows.json written again from every place's current reading and
plan (score/stages/people_rows.py's docstring has what a refresh keeps), then the people line's data for its mapped
looks (`write_line`: data/props, data/inventory and data/surfaces people.json, data/people/specs). Its own module so
the store's readings, plans and hand-in (review.plans, complete/prepare, and the shell code behind them) key no row
that reads people_rows: no row's make refreshes or writes the line (2026-10-27).

    .venv/bin/python -m score.stages.people_refresh
"""
import json

from score.stages.people_rows import (LINE, LINE_FILES, ROWS, SPECS, described, designed_specs, every_look, read,
                                      refreshed_place, size_of, spec_path, with_designed)


def concept_picture(store, sha):
    """The locked concept (the store's blob `sha`) as an H x W x 3 array, 0..255, or None when the store keeps none."""
    import io

    import numpy as np
    from PIL import Image
    key = f"blobs/{sha}"
    if not store.objects.exists(key):
        return None
    return np.asarray(Image.open(io.BytesIO(store.objects.read_bytes(key))).convert("RGB"))


def refresh(store):
    """rows.json from every place's current reading and plan (a place with none is left out; the places are those
    whose scene inventory the design keeps, plans.KEPT_INVENTORY); written."""
    from score.review import plans
    from score.stages.complete.prepare import groups
    places = sorted(path.stem for path in plans.KEPT_INVENTORY.glob("*.json") if path.stem != LINE)
    inventories, _ = groups.current(store, places)
    old = read() if ROWS.exists() else {"places": {}}
    found = {place: refreshed_place(place, inventory, (plans.current(store, place) or {}).get("plan"),
                                    old["places"].get(place),
                                    concept_picture(store, inventory["concept_pick"]["sha256"]))
             for place, inventory in sorted(inventories.items())}
    record = {"why": old.get("why", ""), "places": found}
    ROWS.write_text(json.dumps(record, indent=1) + "\n")
    return record



# --- the people line's data for the mapped looks -------------------------------------------------------------------

def drawn_from(origin, kept):
    """A line row's concept view and box from the picked design's person row that draws it (`origin` "<place>/<row>",
    origin_of): the view named by its place, its picture the kept concept, its box SAM 3's in the reading
    (handin.GROUNDED): the tallest of its people's instance boxes (`boxes`) when SAM 3 told them apart, else its one
    box, so the shared loop's close-up draws the look from its largest person; {} where the design keeps no inventory
    (`kept`: the kept inventories' folder)."""
    from score.stages.complete.prepare import handin
    place, row_id = origin.split("/", 1)
    path = kept / f"{place}.json"
    read = next((row for row in json.loads(path.read_text())["rows"] if row["id"] == row_id), None) \
        if path.is_file() else None
    if not read or not read.get("box"):
        return {}
    box = max(read.get("boxes") or [read["box"]], key=lambda box: box[3] - box[1])
    return {"view": place, "box": box, "grounded": handin.GROUNDED}


def line_inventory(inventory, rows):
    """The line's inventory of `rows`: a view a place its rows are drawn from (its kept concept), approved by the
    creator's picks that map them (handin.APPROVED_BY, which the Pixal3D batch takes)."""
    from score.stages.complete.prepare import handin
    places = sorted({row["view"] for row in rows if row.get("view")})
    return {**inventory, "approved": {"by": handin.APPROVED_BY, "places": places},
            "plan": {"views": [{"id": place, "picture": "{home}/design/concepts/" + f"{place}.png"}
                               for place in places]}, "rows": rows}


def line_rows(found, props, inventory, surfaces, kept=None):
    """The people line's three records with every designed look (designed_specs, with_designed) narrowed to the
    looks the designs map, each inventory row and bake entry with the look's size (size_of), each row's words its
    spec's description and clothes (described) and each row drawn from its mapping person's view and box
    (drawn_from): (props, inventory, surfaces)."""
    from score.review import plans
    from score.stages.props import compare
    kept = kept or plans.KEPT_INVENTORY
    specs = designed_specs(found, surfaces)
    props, inventory, surfaces = with_designed(specs, props, inventory, surfaces)
    wanted = every_look(found) & set(props["objects"])
    rows = []
    for row in inventory["rows"]:
        if row["id"] in wanted:
            size, origin = size_of(row["id"], found)
            rows.append({**{key: value for key, value in row.items() if key not in ("view", "box", "grounded")},
                         "prop": row["id"], "size": size, "size_from": f"{origin} of data/people/rows.json",
                         "view": None, "box": None, **drawn_from(origin, kept),
                         **described(row["id"], row, specs, surfaces)})
    takes = {props["objects"][look]["take"] for look in wanted}
    models = {look: take for look, take in surfaces["bake"]["models"].items() if look in wanted}
    entries = {look: compare.bake_entry({"id": look, "size": next(row["size"] for row in rows if row["id"] == look)})
               for look in models}
    drawn = {row["id"] for row in rows if row["view"]}  # the loop's close-up draws these: no close-up named
    inventory = line_inventory(inventory, rows)
    # approved by the same picks as its inventory, so its likeness is measured as a designed place's (no calibration)
    return ({**props, "approved": inventory["approved"],
             "objects": {look: {key: value for key, value in entry.items() if not (key == "closeup" and look in drawn)}
                         for look, entry in props["objects"].items() if look in wanted}},
            inventory,
            {**surfaces, "takes": {take: entry for take, entry in surfaces["takes"].items() if take in takes},
             "bake": {**surfaces["bake"], "models": models, "entries": entries}})


def write_specs(specs):
    """Each designed look's spec at its spec_path, and no other file left in SPECS (a look no design maps now)."""
    SPECS.mkdir(parents=True, exist_ok=True)
    written = {spec_path(spec) for spec in specs.values()}
    for path in SPECS.glob("*.json"):
        if path not in written:
            path.unlink()
    for spec in specs.values():
        spec_path(spec).write_text(json.dumps(spec, indent=1) + "\n")


def write_line():
    """The people line's data (LINE_FILES) narrowed and sized for the mapped looks and each designed look's spec,
    written; the designed looks' count."""
    records = {name: json.loads(path.read_text()) for name, path in LINE_FILES.items()}
    found = read()
    specs = designed_specs(found, records["surfaces"])
    write_specs(specs)
    for name, record in zip(LINE_FILES, line_rows(found, records["props"], records["inventory"],
                                                  records["surfaces"])):
        LINE_FILES[name].write_text(json.dumps(record, indent=1) + "\n")
    return len(specs)

def main():
    from score.store import Store
    record = refresh(Store.default())
    designed = write_line()
    print(f"people rows: {len(record['places'])} places, {sum(map(len, (entry['rows'] for entry in record['places'].values())))} "
          f"rows, {designed} looks written from their rows; {ROWS}")


if __name__ == "__main__":
    main()
