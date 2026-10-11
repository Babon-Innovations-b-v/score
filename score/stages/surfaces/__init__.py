"""The surface stage (R4, the paper's core contribution: shape and surface apart, every part one surface of the shared
library) as rows of world 1's stage table: each place's own line, side by side with every other place's, plus the
world's seed of the finish registry that every line reads.

    from score.stages import surfaces
    surfaces.ROWS          # the rows, in the order a line runs them

A line runs the method, then the framework:
    method (g-texture, round 4's best arm; split_batch.py, split_batch_paid.py, g_texture.py):
        split-inputs, split-turntable, split-unlit, split-regions (SAM 2.1), split-asks, split-judge (Gemini 3.1 Pro),
        split-prompts, split-masks (SAM 3), split-split, surfaces-asks, surfaces-judge, surfaces-parts
    the method's seed of the registry (world grain, the owner's picked models): surfaces-seed-inputs,
        surfaces-seed-turntable, surfaces-seed
    framework (place_line.py): surfaces-paint (the finish registry, registry.py), surfaces-bake, surfaces-check

The method's interface is two contracts: PARTS (per model its parts, each with a measured finish and the judge's
surface for it, parts.json and <take>/parts.npy, <take>/colours.npy) and SEED (the registry's first groups,
seed.json). Another method replaces the method's rows and writes those two; the framework's rows stay.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))  # the stage's modules import each other by name, as in the prop environment

from score import contracts, graph  # noqa: E402
from score.adapters import models  # noqa: E402

import surface_data as data  # noqa: E402
import g_texture  # noqa: E402
import place_line  # noqa: E402
import split_batch  # noqa: E402
import split_batch_paid as paid  # noqa: E402
from surface_gates import guarded  # noqa: E402

PARTS = contracts.Contract("surfaces-parts", 1, g_texture.parts_faults)
SEED = contracts.Contract("surfaces-seed", 1, g_texture.seed_faults)
JUDGE = {"judge": models.api_record("gemini-judge")}  # the judge's model and settings in its rows' keys
REGIONS_FILES = {"segment worker": "{repo}/tools/props/cloud/segment_worker.py",
                 "segment setup": "{repo}/tools/props/cloud/segment_setup.sh"}
MASKS_FILES = {"finish masks worker": "{repo}/tools/props/cloud/finish_masks_worker.py",
               "finish masks setup": "{repo}/tools/props/cloud/finish_masks_setup.sh"}


def contract(schema, faults):
    return contracts.Contract(schema, 1, faults)


def reads(*rows):
    """`after` for rows of this stage, each at its contract's version 1."""
    return {row: (row, 1) for row in rows}


def row(name, make, faults, check, judge, files, after=(), grain="place", **more):
    """One row of the stage: its output's contract is named for the row."""
    return graph.Stage(name, grain, make, contract(name, faults), (guarded(check, judge),), files=files,
                       after=reads(*after), applies=data.paints if grain == "place" else None, **more)


SPLIT = (
    row("split-inputs", split_batch.make_inputs, split_batch.inputs_faults, "inputs", split_batch.judge_inputs,
        data.line_files),
    row("split-turntable", paid.make_turntable, paid.turntable_faults, "turntable", paid.judge_turntable,
        data.turntable_files, ("split-inputs",), paid=True, euros=paid.TURNTABLE_EUROS),
    row("split-unlit", paid.make_unlit, paid.unlit_faults, "unlit", paid.judge_unlit, data.unlit_files,
        ("split-inputs",), paid=True, euros=paid.UNLIT_EUROS),
    row("split-regions", paid.make_regions, paid.regions_faults, "regions", paid.judge_regions, REGIONS_FILES,
        ("split-inputs", "split-unlit"), paid=True, euros=paid.REGIONS_EUROS),
    row("split-asks", split_batch.make_asks, split_batch.asks_faults, "asks", split_batch.judge_asks,
        data.line_files, ("split-inputs", "split-regions")),
    row("split-judge", paid.make_judge, paid.answers_faults, "judge", paid.judge_answered, {}, ("split-asks",),
        paid=True, euros=paid.JUDGE_EUROS, params=JUDGE),
    row("split-prompts", split_batch.make_prompts, split_batch.prompts_faults, "prompts", split_batch.judge_prompts,
        data.line_files, ("split-inputs", "split-regions", "split-turntable", "split-judge")),
    row("split-masks", paid.make_masks, paid.masks_faults, "masks", paid.judge_masks, MASKS_FILES,
        ("split-prompts",), paid=True, euros=paid.MASKS_EUROS),
    row("split-split", split_batch.make_split, split_batch.split_faults, "split", split_batch.judge_split,
        data.line_files, ("split-inputs", "split-regions", "split-turntable", "split-prompts", "split-masks")))
NAMING = (
    row("surfaces-asks", g_texture.make_asks, g_texture.asks_faults, "asks", g_texture.judge_asks, data.line_files,
        ("split-inputs", "split-turntable", "split-split")),
    row("surfaces-judge", paid.make_judge, paid.answers_faults, "judge", paid.judge_answered, {},
        ("surfaces-asks",), paid=True, euros=paid.JUDGE_EUROS, params=JUDGE),
    graph.Stage("surfaces-parts", "place", g_texture.make_parts, PARTS,
                (guarded("parts", g_texture.judge_parts),), files=data.line_files,
                after=reads("split-inputs", "split-turntable", "split-split", "surfaces-judge"), applies=data.paints))
SEEDING = (
    row("surfaces-seed-inputs", split_batch.make_inputs, split_batch.inputs_faults, "inputs",
        split_batch.judge_inputs, data.seed_files, grain="world"),
    row("surfaces-seed-turntable", paid.make_turntable, paid.turntable_faults, "turntable", paid.judge_turntable,
        data.turntable_files, ("surfaces-seed-inputs",), grain="world", paid=True, euros=paid.TURNTABLE_EUROS),
    graph.Stage("surfaces-seed", "world", g_texture.make_seed, SEED, (guarded("seed", g_texture.judge_seed),),
                files=data.seed_files, after=reads("surfaces-seed-inputs", "surfaces-seed-turntable")))
LINE = (
    row("surfaces-paint", place_line.make_paint, place_line.paint_faults, "one surface a part",
        place_line.judge_one_surface, data.line_files, ("surfaces-parts", "surfaces-seed")),
    row("surfaces-bake", place_line.make_bake, place_line.bake_faults, "baked", place_line.judge_baked,
        data.bake_files, ("surfaces-paint",), paid=True, euros=place_line.BAKE_EUROS),
    graph.Stage("surfaces-check", "place", place_line.make_check, contract("surfaces-check", place_line.check_faults),
                (guarded("baked matches its surfaces", place_line.judge_lit),
                 guarded("triangles within budget", place_line.judge_triangles)),
                files=data.line_files, after=reads("surfaces-bake", "surfaces-paint"), applies=data.paints))
ROWS = (*SEEDING, *SPLIT, *NAMING, *LINE)
