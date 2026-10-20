"""The finish route's paint, `surfaces-paint` (free, on this PC: the owner's no paid paint step, 2026-10-20): each
part takes its library surface from the parts row (place_line.method_surfaces, its proposals into the finish
registry first) and each take's labelled folder is written as the rented paint wrote it (place_line.paint_take: the
raw take laid on its finished model, its feet levelled, one .ply a surface), here in the prop environment under
prop_env's memory cap. A take past the cap fails the row by its error; the rented paint (place_line.make_paint)
stays the crops' and people's lines'.

Output and gates as the rented paint's: painted.json (with the takes the parts left out), labelled/<take>/.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import place_line  # noqa: E402
import prop_env  # noqa: E402

RECORDS = "paint records"  # {take: its part records}, worked out before the step (place_line.method_surfaces)


def make_paint(inputs, out, seed, params):
    """Every take of the parts painted here; the parts' proposals go into the finish registry first."""
    from registry import Registry
    from score.store import Store
    short = prop_env.short(inputs)
    data = place_line.data_of(short)
    method = json.loads((short["parts"] / "parts.json").read_text())
    registry = Registry(Store.default())
    records, claimed = out / ".records.json", out / ".claimed.json"
    records.write_text(json.dumps({take: place_line.method_surfaces(take, data["takes"][take]["place"], record["parts"],
                                                                    registry)
                                   for take, record in method["takes"].items()}))
    claimed.write_text(json.dumps({take: place_line.claimed_rows(take, short) for take in method["takes"]}))
    try:
        prop_env.handover(__file__, "paint", {**inputs, RECORDS: records, place_line.CLAIMED: claimed}, out)
    finally:
        records.unlink()
        claimed.unlink()


def paint_step(inputs, out):
    """The prop environment's side: every take painted (place_line.paint_take) from its part records; painted.json."""
    method = json.loads((inputs["parts"] / "parts.json").read_text())
    records = json.loads(inputs[RECORDS].read_text())
    found = {take: place_line.paint_take(inputs, out, take, record, records[take])
             for take, record in method["takes"].items()}
    (out / "painted.json").write_text(json.dumps({"takes": found, "left_out": method["left_out"]}, indent=1))


STEPS = {"paint": paint_step}

if __name__ == "__main__":
    prop_env.main(STEPS)
