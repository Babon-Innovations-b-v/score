"""The prop route as rows of the stage table: every object goes the prop route first (close-up, Pixal3D, then the
surface line's split, library paint and the bake that makes it solid), and only one whose measured checks fail is
built in code and checked again (the owner's decision, 2026-10-12, flipping the parts check's order).

    props-inputs  free   the objects as close-up rows; gate: boxed or drawn (the close-up stage's box gate)
    closeup       paid   Nano Banana Pro close-ups (pro.py, google_spend); gate: the shape check's measured half
    pixal         paid   Pixal3D takes by the cloud batch, into WORK/pixal; gate: takes made and in the surface data
    (surfaces-*)         the surface line, whose first row waits on pixal (score/stages/__init__.py wires it)
    likeness      free   every object held to its close-up and the model checks; DINOv2 evidence gathered (paid)

Each row applies only to a place with prop data (data/props/<place>.json, prop_data.py); no world 1 place has one
yet, so the table's existing nodes keep their keys. `compare.py` runs a place in both orders, each in a store of its
own, and writes the table and the review page.
"""
from score import contracts, graph
import score.stages.props.calibration_row as calibration_row
import score.stages.props.closeup_row as closeup_row
import score.stages.props.likeness_row as likeness_row
import score.stages.props.pixal_row as pixal_row
import score.stages.props.prop_data as prop_data
from score.stages.surfaces.surface_gates import guarded


def contract(schema, faults):
    return contracts.Contract(schema, 1, faults)


INPUTS = graph.Stage("props-inputs", "place", closeup_row.make_inputs,
                     contract("props-inputs", closeup_row.inputs_faults),
                     (guarded("boxed or drawn", closeup_row.judge_inputs),), files=prop_data.inputs_files,
                     applies=prop_data.applies, selects=True)
CLOSEUP = graph.Stage("closeup", "place", closeup_row.make_closeups, contract("props-closeups",
                                                                             closeup_row.closeups_faults),
                      (guarded("close-up", closeup_row.judge_closeups),),
                      files=prop_data.closeup_row_files, after={"props-inputs": ("props-inputs", 1)}, paid=True,
                      euros=closeup_row.EUROS,
                      applies=prop_data.applies, selects=True)
PIXAL = graph.Stage("pixal", "place", pixal_row.make_pixal, contract("props-pixal", pixal_row.pixal_faults),
                    (guarded("takes", pixal_row.judge_takes),), files=prop_data.pixal_files,
                    after={"closeup": ("props-closeups", 1)}, paid=True, euros=pixal_row.EUROS,
                    applies=prop_data.applies, selects=True)
CALIBRATION = graph.Stage("likeness-calibration", "place", calibration_row.make_calibration,
                          contract("likeness-calibration", calibration_row.calibration_faults),
                          (guarded("calibrated", calibration_row.judge_calibration),),
                          files=prop_data.calibration_files, paid=True, euros=calibration_row.EUROS,
                          applies=prop_data.calibration_applies)
LIKENESS = graph.Stage("likeness", "place", likeness_row.make_likeness,
                       contract("props-likeness", likeness_row.likeness_faults), likeness_row.CHECKS,
                       files=likeness_row.files, gatherers=likeness_row.GATHERERS,
                       after={"likeness-calibration": ("likeness-calibration", 1),
                              "closeup": ("props-closeups", 1), "surfaces-bake": ("surfaces-bake", 1),
                              "surfaces-parts": ("surfaces-parts", 1), "surfaces-check": ("surfaces-check", 1),
                              # the rows whose batch gaps it carries to complete (score/stages/batch_gaps.py)
                              "pixal": ("props-pixal", 1), "finish-route-split": ("finish-route-split", 1),
                              "finish-route-recheck": ("finish-route-recheck", 1)},
                       applies=prop_data.applies, selects=True)
# What the surface line's first row reads of the prop route (score/stages/__init__.py adds it to its `after`).
FEEDS = {"pixal": ("props-pixal", 1)}
