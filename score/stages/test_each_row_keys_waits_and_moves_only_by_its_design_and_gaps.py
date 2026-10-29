"""Each row of the stage table (score/stages, its top-level modules) keys, waits on and moves only what its design and
its gaps say: its code version moves with its own code alone, the layers a scene has are read off its design, a row's
kind off its own words, every designed person is a look of the people line, a ground follows its words then its
physics, a layer's copy of a read-only seed takes a save, an accepted gap or a batch gap moves only the faults it
names, and the push gate names the paid rows a change would buy again. One section a top-level module below, each
test under its section's heading in the code; the fixtures are each section's own, small, in temporary folders.

--- rows key and wait only on what they read ---

The stage table wires every row to key and wait on exactly what it reads (score/stages/__init__.py): a row's code
version moves with its own code and what it imports, never with another line's module, the runner, the table or the
run machinery (warm pool, provider, ledgers, money guards, cockpit), so an edit there buys nothing again; the rows a
layer or the light waits on are its real reads, and no base or layer row waits on the prop route; a design's dress
rows apply where its people wear them; a place is a scene whose design is done, a parent before its children; the
plan row and the cast read their design and plan, never a kit or a hand-written record; the environment data names no
path into the work folder.

The worked example on environment 1's round-three seeds (the hangar's) went with the old disk (2026-10-19) and only
ever skipped since; the runner's own make-twice-and-rerun-on-change rules are held by score/graph's test.

Breaks (each applied once, seen red, reverted), in score/stages/__init__.py and score/graph/_code.py:
- score/graph/_code.py `FRAMEWORK` without `score/stages/__init__.py`  -> the terrain key test (the table moves
  terrain's key).
- `FRAMEWORK` without `tools/cloud/provider.py`, or without `tools/cloud/secret_store.py`  -> the run machinery test.
- the light layer no longer given the body faces' reads (`FACE_READS`)  -> the light layer test.
- `worn`: `applies` true at every place  -> the two dress row tests.
- `held_scenes`: the batch's places not intersected  -> the scene tree test (the dome counts).
- `places`: the `merged` scenes not taken out  -> the place test.
- `ship_place`: always False  -> the ship place test.
- score/stages/earth_seed/__init__.py: surface_data imported through its package (`from score.stages.surfaces import
  surface_data`)  -> test_the_earth_rows_key_on_the_surface_data_reader_not_the_surface_line.
- score/stages/surfaces/route_views.py: `import place_line` added  ->
  test_the_paint_bake_and_check_code_moves_only_their_own_rows.
- score/stages/assembly/baked.py: `import complete as stage_inputs`  ->
  test_the_completion_gate_s_code_moves_only_complete_and_settle and
  test_the_table_wires_the_gates_and_only_complete_hashes_the_gaps.
- score/stages/shapes_first/__init__.py: the palette's optional Pixal3D read dropped (`optional=row.optional`)  ->
  test_no_base_or_layer_row_must_wait_on_the_prop_route.
- `creator_plan`: the concept declared whether it is kept or not (`if True:`)  ->
  test_the_plan_row_keeps_the_plan_stages_code_version.
- `plan_as_kit`: the plan not handed over as its kit (`{**arguments[position]}`)  ->
  test_the_plan_row_maps_a_place_with_no_kit.
- the surfaces-check row's `"stance rules"` file dropped  -> test_the_check_reads_every_input_check_step_reads.
- `earth_seeded.declared`: the seed-read filter dropped (`return dict(found)`)  ->
  test_the_cast_crowds_from_its_plan_never_a_hand_written_record.
- data/checks/row-kinds.json: its "about" naming `{home}/work/old`  ->
  test_the_environment_data_names_no_path_into_the_work_folder (a wording check guarding the rule above).
- `MOTION_LAYER`: growth's `crops-layer` written `crops`  ->
  test_the_motion_layer_names_only_rows_of_the_table_and_no_old_layer.
- score/graph/_code.py `source_files`: FRAMEWORK not left out (`set()`)  -> every code-version test above, and the push
  gate's test_a_framework_only_edit_lists_nothing.
- `scripts_declared`: the row returned as it was  -> test_every_script_a_row_starts_by_path_is_in_its_key (every
  row that starts a script, surfaces-bake's recipes.py among them); score/graph/_code.py `script_imports`: the files
  beside a script dropped  -> the same test (make_chunky.py's bake.py, pieces.py ...); `STARTED_LEFT` with a row that
  starts nothing  -> the same test; `reads_recipes` always False  ->
  test_a_row_reading_the_recipes_declares_the_vendored_libraries_they_import.

--- a scenes layers are read off its design ---

Which layers a scene has is read off its design alone, and the stage table and the assembly's layers gate give one
answer (design_layers.py): each row shows the layer its kind does, crops are plants on a bed and never a potted
plant, every scene with a design has light and sound, a place with no kept design has no layer at all, and for a
design kept where the plan stage keeps it every layer row the assembly's gate waits on is a row the table holds for
the place, and no other. On designs and row-kind rules written here.

Breaks (each applied once, seen red, reverted), in score/stages/design_layers.py:
- `DOES`: `"loose": "physics"` dropped  -> the kind test (the kettle shows no physics).
- `on_bed`: `or "grows" in ...` dropped  -> the crops test (greens on a planter are no crops).
- `plants_of`: the beds kept among the plants (`if row["id"] not in beds` dropped)  -> the plants test.
- `has_layer`: `if place is None or not path.is_file(): return False` read as returning True  -> the kept test.
- `kinds_of`: `set(EVERY_SCENE)` read as `set()`  -> the kind test (a bare room has no light).
- score/stages/__init__.py: the sound row's `designed("sound")` written `designed("sounds")`  ->
  test_the_table_has_a_row_for_every_layer_the_gate_waits_on.
- data/checks/row-kinds.json: "tree" dropped from the plant nouns  -> test_the_house_rules_call_trees_and_shrubs_plants.

--- a rows kind comes from its own words ---

A scene inventory row's kind comes from its own reading words alone (row_kinds.py): its reading noun first, matched
whole, its name's last word only for a row read with no noun, else the kind its name says holds it; a scene's
emitting, moving and loose rows are picked out by what their kind does; a row's objects are found on a stage by name,
outside the layers' own scopes, and a prim no row's object has is a stranger. On rules written here and on the house
rules (data/checks/row-kinds.json, where the expected kinds are read off the file's own nouns by hand).

Breaks (each applied once, seen red, reverted), in score/stages/row_kinds.py:
- `kind_of`: the noun ignored (`words(row.get("noun")) or` dropped)  -> the noun test ("door panel" read as a door).
- `kind_of`: `wanted in rule["nouns"]` read as any noun inside the words  -> the noun test ("floor plate").
- `held_kind`: `said[-2] in rule["nouns"]` dropped  -> the lamp test ("fence post" read as a lamp).
- `objects_of`: the NOT_OBJECTS prune dropped  -> the objects test (/toy/Effects/door_3 found).
- `of_row`: `(_\\d+)?` read as `.*`  -> the objects test (door_frame_1 found) and the strangers test.
- `does`: only a kind's first deed read (`["does"][:1]`)  ->
  test_a_scenes_rows_are_picked_by_what_their_kind_does_and_a_kind_can_do_more_than_one_thing,
  test_each_row_shows_the_layer_its_kind_does and test_the_table_has_a_row_for_every_layer_the_gate_waits_on.
- data/checks/row-kinds.json: "tv" dropped from the screen nouns  -> test_the_house_rules_read_real_words.

--- every designed person is a look of the line ---

Every person a picked design shows is a look of the shared people line, written from the design alone
(people_rows.py, data/people/rows.json, #26): every people row maps to looks the line holds, one look (one body) for
the people the rows say are and wear the same, written from its largest standing row (its spec and take); a crowd to
one far look read off its words, standing on the plan items its row makes, in a few variants of its body; each person
stood on the plan's people spots, each of a look its own variant; the line's data is exactly what rows.json maps,
each look baked at its person row's size and drawn from the person that maps it; a refresh keeps a hand-made choice
only while its concept stands; a row wears the fabric its words name nearest its measured torso.

Breaks (each applied once, seen red, reverted), in score/stages/people_rows.py:
- `look_of`: the pose and colour words kept in the look's name  -> the grouping test.
- `crowd_ground`: every plan item taken, not only the row's  -> the crowd ground test (the bench is crowd ground).
- `persons`: every person given variant 0  -> the cast test ("each its own variant").
- `placed_spots`: a spot's two plan coordinates swapped  -> the cast test (the spot (1, 1) of a 20 x 10 plan
  stands at (-9, 0, -4)).
- `refreshed_place`: a kept pick taken with no `why`  -> the refresh test.
- `crowd_look`: `needed = 0` (the crowd word alone decides)  -> the crowd look test ("crowd of aliens").
- `mapping_rows`: `if look not in mapped or ...` read as `if look in mapped and ...` (no look mapped)  ->
  test_every_people_row_maps_to_a_look, test_a_person_row_s_look_is_written_from_the_row_alone,
  test_each_line_row_is_drawn_from_the_person_that_maps_it and
  test_the_line_holds_the_mapped_looks_each_baked_at_its_rows_size.
- `mapping_rows`: a sitting row ranked like a standing one  -> test_a_person_row_s_look_is_written_from_the_row_alone
  (drawn from the seated copilot), and the drawn-from and line tests.
- score/stages/complete/prepare/groups.py `stood_beyond`: `and anchors[row_id] not in found` dropped  ->
  test_a_people_row_the_plan_shows_beyond_the_place_is_not_its_own.
- `size_of`: `person_sized` not asked (`if origin:`)  ->
  test_the_line_holds_the_mapped_looks_each_baked_at_its_rows_size (the crowd's extent as one person).
- score/stages/people_refresh.py `drawn_from`: the tallest box read with `min`  -> test_each_line_row_is_drawn_from_the_person_that_maps_it.
- `described`: the spec's description left out (`"name": clothes`)  ->
  test_the_line_holds_the_mapped_looks_each_baked_at_its_rows_size (the line's data no longer as rows.json writes it).
- score/stages/props/closeup_row.py `inventory_rows`: the words the clothes alone (`row.get("clothes", row["name"])`)
  -> test_each_line_rows_close_up_words_say_who_the_look_is.
- score/stages/people_clothes.py `worn`: the nearest fabric read with `max`  ->
  test_a_row_wears_the_fabric_its_words_name_nearest_its_torso.

--- a ground follows its words then its physics ---

A natural ground's recipe follows its row's own words first, else its body's physics against water's phases, and
never a body's name (natural_grounds.py). The expected recipes are worked out by hand from each made-up body's
pressure and its zero-albedo temperature, T = T_star sqrt(R_star / 2d): at 1 AU from a 5772 K star of 695,700 km,
278 K; at 0.2 AU, 622 K (over water's boiling at 101.3 kPa, 373 K); at 5.2 AU, 122 K (under ICE_K); at 1.52 AU,
226 K (no liquid at 0.6 kPa, under the triple point's 273 K, but an air over WIND_KPA).

Breaks (each applied once, seen red, reverted), in score/stages/natural_grounds.py:
- `warmth_k`: `2.0 * child["distance_km"]` read as `child["distance_km"]`  -> the physics test (the hot world, 880 K,
  is still rock, but the wet one at 393 K boils to rock).
- `of_body`: `kelvin <= boils` read as `kelvin <= WATER_TRIPLE_K`  -> the physics test (the wet world reads rock).
- `of_body`: the `kelvin < ICE_K` rule dropped  -> the physics test (the frozen world reads regolith).
- `of_row`: the MADE words not read  -> the words test (the plaza takes its body's sand).
- `pressure_kpa`: the reference table not read  -> the words test (the table's airless body has no pressure).

--- a copy of a read only seed takes a save ---

The copy of a seed a layer is written over takes a save, though the store's seed is read-only and copies keep its
modes (layer_base.py `writable`).

Breaks (each applied once, seen red, reverted), in score/stages/layer_base.py:
- `writable`: its chmod left out (the function body made `return`)  -> a PermissionError on the save.

--- an accepted gap moves only its named faults ---

An accepted gap moves only the faults it names down the line, never loosens a gate (gaps.py): a failing gate passes
only when every finding is a named object's (of the entry's kind when it says one; by its row for a JSON finding),
keeping the findings; any other fault still fails it; a named unknown moves and another stays; complete fails every
gap by name with its numbers, the owner's and the ones a row wrote in its output; a gap is an input of complete and of
the row it names alone, and only complete's code version holds gaps.py, so moving a verdict re-makes nothing paid.

The owner's gap decisions of the old concepts were retired with them (2026-10-21), so each test writes the decision it
judges, in the file's own form, into a gaps folder of its own.

Breaks (each applied once, seen red, reverted), in score/stages/gaps.py:
- `moved`: `if not all(any(covers(...)) ...)` read with `any` over the findings  -> the named-faults cases (another
  fault moves too).
- `covers`: `and entry.get("contains", "") in finding` dropped  -> the order case (a colour fault moves).
- `object_of`: the JSON branch dropped  -> the rows and boxes cases.
- `moved`: the unknown branch dropped  -> the unknown test.
- `files`: the `row is not None and ...` narrowing dropped  -> the inputs test (the paint reads the street's gaps).
- `judge_accepted`: `written(inputs)` left out  -> the written-gap test.
- `entries`: the row and check filter dropped (`return list(found)`)  ->
  test_the_decision_file_is_read_by_row_and_check_and_a_pass_or_unknown_is_left_alone.
- `judge_accepted`: a finding without its gap's name (`f"{fault}"`)  ->
  test_complete_fails_each_accepted_gap_by_name_with_its_numbers (and the batch section's line test).
- score/stages/__init__.py `gap_moved`: `judged.__wrapped__ = check.judge` dropped  ->
  test_the_table_wires_the_gates_and_only_complete_hashes_the_gaps (and the batch section's two table-move tests).

--- a failed paid take is a gap carried down its line ---

A take whose paid step failed inside the batch is a gap carried down its place's line, never a stop and never a
loosened gate (batch_gaps.py, the table's `accepted_gaps` mover): the row whose step failed names the take in its
batch-gaps.json, its gate still fails it and the table moves exactly that fault; the rows after it leave the take out
and carry its gap on; the line runs on to complete, which lists the gap with the batch run that decided it; a fault
no batch gap names still stops the line. The Pixal3D batch and the check's step are faked at their subprocess and
hand-over; the takes are written under the sandbox home.

Fault (#10, 2026-10-21): a failed close-up or Pixal3D job failed the next free gate, and the place's line waited for
the owner, though his yes to the batch had already decided that a failure is a gap.

Breaks (each applied once, seen red, reverted), in score/stages/batch_gaps.py:
- `batch_gaps.read`: `found.setdefault(...)` read as `found[entry["name"]] = ...` with `decided` dropped  -> the
  Pixal3D test (no `decided`).
- `batch_gaps.of`: the inputs' folders left out (only `output`)  -> the views tests and the fixture line (the gap is
  not carried, so complete has nothing to list).
- `batch_gaps.objects`: returns an empty set  -> the Pixal3D test (the table no longer moves the hatch's fault).
- `batch_gaps.write`: writes `{"gaps": []}`  -> every test reading a written gap.
- score/stages/surfaces/route_paint.py: `if found:` read as `if True:` (a gaps file written always)  ->
  test_a_clean_paint_writes_no_gaps_file.
- a fault no batch gap names, and a take lost with none: the gaps section's `moved` break (`all` read as `any`)  ->
  test_a_fault_no_batch_gap_names_still_fails_the_gate and test_a_take_lost_with_no_batch_gap_still_stops_its_line.

--- push gate names the paid rows it moves ---

The push gate (moved.py, `score moved`, .githooks/pre-push-moved) names exactly the paid rows a change would buy
again, each with its price and why, and refuses a push to main only for the rows that push moves and no Moved-rows
trailer names with a reason; drift already on main is a warning, a move no file explains (a params, contract or
model change) is refused like any other, and the hook leaves no process or checkout behind.

A toy git repository stands in for this one (moved.REPO, _code.REPO): a paid render whose make sits in it and imports
a framework file, a paid bake, each reading a data file of its own, and a paid film reading an unpaid drawing of a
third data file. The hook itself is run against a toy repository whose score package only records what it was given.

Faults it guards (2026-10-17): about EUR 65 of re-buys (view maps, turntables, the cockpit library push) came from
code and data changes nobody saw would move a paid row's key before they were pushed (8b402226: blender_cloud.py,
outside every code version but declared by the turntables; 1f90a0fe: new gap files a paid row declares). The first
hook refused every push over drift already on main, refused branch deletions and took any trailer as leave for every
row; its second form let a framework-only push through unchecked and only warned of a move no file explains. The two
tests that worked out the real commits 8b402226 and 1f90a0fe took two minutes (and the first no longer held on
today's table): the toy's declared data files hold the same rule, a file a row declares moves it.

Breaks (each applied once, seen red, reverted), in score/stages/moved.py and .githooks/pre-push-moved:
- `total`: `sum(row.euros ...)` read as `sum(0 * row.euros ...)`  -> the price-and-why test ("about EUR 3.00").
- `main_pushes`: `ref == MAIN and` dropped  -> test_only_pushes_to_main_are_checked.
- `trailer_nodes`: `and why.strip()` dropped  -> test_a_trailer_names_a_row_only_among_its_nodes_and_with_a_reason.
- `split`: the pushed rows' `if base is None or row.node not in known...` dropped  -> the drift tests (drift refused).
- `unexplained`: `not named_in(...)` read as `named_in(...)`  -> test_a_trailer_lets_only_the_rows_it_names_go.
- `edited_into_framework`: `after - before` read as `before - after`  -> the framework-move test.
- .githooks/pre-push-moved: its `trap '... worktree remove ...' EXIT` line made a no-op  -> the changed-tree hook test
  (the checkout is left behind).
- score/__main__.py `moved_check`: `> 0` read as `>= 0`  -> test_nothing_changed_lists_nothing_and_passes.
- score/graph/_code.py `source_files`: FRAMEWORK not left out  -> test_a_framework_only_edit_lists_nothing.
- score/graph/rebuy.py `buys`: `if remade[name]` read as `if not remade[name]`  ->
  test_a_row_moved_through_what_it_reads_is_listed.
- score/graph/__init__.py: `params` left out of a stale row's reasons  -> test_a_move_no_file_explains_is_refused.
- score/__main__.py `pushed_check`: `if base is None` read as `if base is not None`  ->
  test_when_mains_commit_cannot_be_worked_out_every_moved_row_counts_as_the_pushes.
- `snapshot`: `shutil.rmtree(holder)` made `pass`, or its `worktree remove` made `pass`  ->
  test_base_rebuys_is_none_for_a_new_ref_an_unknown_commit_or_a_failing_tree_and_leaves_nothing_behind and
  test_a_hook_that_runs_out_of_time_leaves_no_process_or_checkout_behind.
- `tree_is_at`: the `git status --porcelain` check dropped  ->
  test_pre_push_checks_the_pushed_commit_against_mains_not_a_changed_tree.
- the hook's `= true ] || exit 0` read as `|| true`  -> test_the_hook_is_off_until_the_owner_turns_it_on.
- the hook's `[ "$remote_ref" = refs/heads/main ] &&` dropped  ->
  test_the_hook_passes_deletions_tags_and_other_branches_at_once.
- the hook's `rm -rf "$checkout"` dropped  -> test_the_hook_refuses_and_leaves_nothing_when_no_worktree_can_be_made.
- the hook's `grep -qs -- "--pre-push"` read as `grep -qs -- ""`  ->
  test_the_hook_skips_a_commit_made_before_score_moved.
- the hook's `|| echo 3600` read as `|| echo 900`  -> test_the_hook_gives_the_check_an_hour_unless_told_otherwise.
- the hook's main-checkout python (`$(git rev-parse --git-common-dir)/..`) read as `$repo`  ->
  test_a_worktree_hook_uses_the_main_checkouts_python.
"""

import ast
import contextlib
import dataclasses
import fnmatch
import functools
import importlib
import inspect
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
# The script's own folder (score/stages) off the path: on it, tools/usd's `import motion` also finds the motion
# stage, and the code versions measured here take in its imports (feet.py, triage.py) as `python -m score` never does.
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:] = [entry for entry in sys.path if pathlib.Path(entry or ".").resolve() != HERE]
sys.path.insert(0, str(REPO))

from pxr import Usd, UsdGeom  # noqa: E402
from score import checks, contracts, graph, review, stages  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.graph import _code  # noqa: E402
from score.stages import (batch_gaps, design_layers, gaps, layer_base, moved, natural_grounds,  # noqa: E402
                          people_refresh, people_rows, row_kinds)
from score.stages.surfaces import route_views  # noqa: E402
from score.store import PROPS_HOME, Store, file_hash  # noqa: E402
import score.stages.props.pixal_row as pixal_row  # noqa: E402


# --- rows key and wait only on what they read ---

@functools.cache
def code_hashed(functions):
    """The runner's code version of these functions and {file: its hash} of each file it hashed, worked out once a
    process: the import walk parses every module behind a row, and the tests below ask it hundreds of times."""
    hashed = {}
    version = graph._code.code_version(list(functions), lambda path: hashed.setdefault(path, file_hash(path)))
    return version, hashed


def code_after_editing(stage, edited):
    """A stage's code version, as the runner works it out, as if the repository file `edited` had changed (its hash
    moved; nothing written)."""
    functions = (stage.make, stage.contract.faults, *(check.judge for check in stage.checks),
                 *([stage.files] if callable(stage.files) else []), *([stage.neighbours] if stage.neighbours else []))
    version, hashed = code_hashed(functions)
    path = REPO / edited
    return [part + "+edit" if path in hashed and part == f"{edited} {hashed[path]}" else part for part in version]


def terrain_code_after_editing(edited):
    """Terrain's code version as if the repository file `edited` had changed."""
    return code_after_editing(stages.TERRAIN, edited)


def test_terrain_s_code_version_moves_with_its_own_code_only():
    """Another line's edits to the runner, the stage table or another stage's module leave terrain's key alone (they
    re-made terrain under the effects line, 2026-10-12); its own module and what it imports move it."""
    before = terrain_code_after_editing("nothing")
    for unrelated in ("score/stages/__init__.py", "score/graph/__init__.py", "score/review/__init__.py",
                      "score/adapters/compute/__init__.py", "score/stages/effects/__init__.py",
                      "score/stages/assembly/__init__.py", "score/stages/surfaces/__init__.py"):
        assert terrain_code_after_editing(unrelated) == before, unrelated
    for own in ("score/stages/terrain/__init__.py", "score/stages/terrain/design.py",
                "score/stages/terrain/outside.py"):
        assert terrain_code_after_editing(own) != before, own


def test_the_earth_rows_key_on_the_surface_data_reader_not_the_surface_line():
    """earth-seed reads a place's surface data through surface_data.py alone: an edit to the surface
    line's rows leaves its key, an edit to the reader moves it (its package's __init__ pulled the whole line in,
    2026-10-21)."""
    table = {stage.name: stage for stage in stages.STAGES}
    for name in ("earth-seed",):
        before = code_after_editing(table[name], "nothing")
        for unrelated in ("score/stages/surfaces/__init__.py", "score/stages/surfaces/place_line.py"):
            assert code_after_editing(table[name], unrelated) == before, (name, unrelated)
        assert code_after_editing(table[name], "score/stages/surfaces/surface_data.py") != before, name


def test_the_paint_bake_and_check_code_moves_only_their_own_rows():
    """Editing the surface line's paint, bake and check code (place_line.py, bake_check.py, feet.py), the resting
    triage, the settle, the pick check or the completion gate leaves the paid rows that do not run them alone: the
    finish route's views, list, split and recheck and terrain (each re-bought on the water
    tank's fix, 2026-10-12, through the surfaces __init__ and complete.py); the paint, bake and check rows move. The
    free effects layer is made over the scene record as the assembly writes it (layer_base.py, 2026-10-21: its
    effects ride the design's objects), so like the motion and light rows it reads the exporter's code."""
    table = {stage.name: stage for stage in stages.STAGES}
    edited = ("score/stages/surfaces/place_line.py", "score/stages/surfaces/bake_check.py",
              "tools/props/library/feet.py", "tools/usd/triage.py", "tools/usd/settle.py", "tools/usd/picks.py",
              "tools/usd/complete.py")
    for name in ("finish-route-views", "finish-route-list", "finish-route-split", "finish-route-recheck",
                 "terrain"):
        before = code_after_editing(table[name], "nothing")
        for path in edited:
            assert code_after_editing(table[name], path) == before, (name, path)
    for name in ("surfaces-paint", "surfaces-bake"):
        assert code_after_editing(table[name], edited[0]) != code_after_editing(table[name], "nothing"), name
    assert code_after_editing(table["surfaces-check"], edited[1]) != code_after_editing(table["surfaces-check"],
                                                                                       "nothing")


def test_run_machinery_moves_no_row_and_a_maker_moves_its_own():
    """Code that only decides where and how a job runs (the warm pool, spreading, the provider and its backend, the
    ledgers, forecasts, money guards, the cockpit) moves no row's code version (a body made again for EUR 0.30 by
    warm-pool edits, owner 2026-10-23); a maker's own code and a runner module that sends its scripts up still do."""
    machinery = ("tools/cloud/pool.py", "tools/cloud/spread.py", "tools/cloud/provider.py",
                 "tools/cloud/backends/scaleway.py", "tools/cloud/ledger.py",
                 "tools/cloud/google_spend.py", "tools/cloud/preflight.py",
                 "tools/cloud/secret_store.py", "score/adapters/compute/guard.py", "score/dashboard/__init__.py")
    moved = {(stage.name, path) for stage in stages.STAGES for path in machinery
             if code_after_editing(stage, path) != code_after_editing(stage, "nothing")}
    assert not moved, sorted(moved)
    bodies = [stage for stage in stages.STAGES if stage.name.startswith("people-body-")]
    assert bodies
    for maker in ("score/stages/people_bodies/bodies.py", "tools/cloud/similar.py"):
        assert all(code_after_editing(stage, maker) != code_after_editing(stage, "nothing") for stage in bodies), maker


def test_the_completion_gate_s_code_moves_only_complete_and_settle():
    """Editing the completion gate (complete.py, its contents checks, reach and snap, the complete stage) moves the
    complete row and no other: the assembly, neighbours and likeness read the inputs record's helpers from
    stage_inputs.py, not complete.py (each re-made by a gate edit before 2026-10-12). The settle row snaps held
    objects with snap.py (score/stages/settling/held.py), so a snap edit moves it too, and only it."""
    edited = ("tools/usd/complete.py", "tools/usd/contents.py", "tools/usd/reach.py", "tools/usd/snap.py",
              "score/stages/complete/__init__.py")
    moved = {stage.name for stage in stages.STAGES for path in edited
             if code_after_editing(stage, path) != code_after_editing(stage, "nothing")}
    assert moved == {"complete", "settle"}, moved


def test_the_light_layer_reads_and_waits_on_every_body_face_row():
    """light-layer@hub, 2026-10-23: read as optional, the face rows were in no place's line and the layer failed its
    sky-elements gate with no face drawn."""
    layer = next(row for row in stages.STAGES if row.name == "light-layer")
    faces = {row.name for row in stages.BODY_FACES}
    assert faces and faces <= set(layer.after) and not faces & set(layer.optional)


def test_no_base_or_layer_row_must_wait_on_the_prop_route():
    """Buy of 2026-10-24: one crashed close-up stopped the square's earth seed, scene record, light and tiles, since
    the scene palette, which the surface library and so the base read, waited on Pixal3D. Through every read that is
    not optional, neither the earth seed nor the scene record reaches the prop route's rows. The light rows do, on
    purpose since 2026-10-29: they light the place as the assembly lays it, its bakes in (light/passes.LAID), so they
    wait on the bake as the assembly does."""
    table = {stage.name: stage for stage in stages.STAGES}
    prop_route = {"closeup", "pixal"}

    def reached(name, seen):
        for before in table[name].after:
            if before not in table[name].optional and before not in seen:
                seen.add(before)
                reached(before, seen)
        return seen
    for start in ("earth-seed", "scene-record"):
        assert not reached(start, set()) & prop_route, (start, reached(start, set()) & prop_route)
    assert "pixal" in table["finish-route-palette"].optional


def test_a_dress_row_is_read_where_a_design_dresses_its_look_so():
    """A dress row is read where a place's design dresses its look so: `-in-<surface>` where a person row's words
    name a fabric near its torso (people_clothes.py), the plain row where the look wears its own paint; no
    hand-kept list of coloured places (captain, 2026-10-13: the concept decides the clothes)."""
    table = {stage.name: stage for stage in stages.STAGES}
    plain = table["people-dress-person_uniform-made"]
    assert plain.applies("tube") and not plain.applies("square")  # the tube's "person in uniform" names no fabric
    worn =[stage for stage in stages.STAGES if stage.name.startswith("people-dress-") and "-in-" in stage.name]
    for stage in worn:
        assert stage.params == {"surface": stage.name.partition("-in-")[2]} and stage.name in table["cast"].after


def test_a_worn_dress_row_applies_only_where_its_look_wears_that_fabric():
    """Today's designs dress no line look in a fabric of its own, so the table above holds no `-in-` row: the row a
    design would add applies where a person row wears its look in that fabric, and the plain row no longer there."""
    from unittest import mock

    from score.stages import people
    worn_row, plain_row = (stages.worn(people.dress_row("person_uniform-made", surface))
                           for surface in ("jacket_blue", None))
    second = stages.worn(people.dress_row("person_uniform-made", None, 1))
    dressed = {"deck": {("person_uniform-made", "jacket_blue", 0)}, "hold": {("person_uniform-made", None, 0)},
               "hall": {("person_uniform-made", None, 0), ("person_uniform-made", None, 1)}}
    with mock.patch.object(stages.characters_layer, "dressed_looks", lambda place: dressed.get(place, set())):
        assert worn_row.applies("deck") and not worn_row.applies("hold") and not worn_row.applies("nowhere")
        assert plain_row.applies("hold") and not plain_row.applies("deck")
        assert second.applies("hall") and not second.applies("hold"), "a person's own variant where they stand"
    assert worn_row.params == {"surface": "jacket_blue"} and second.params == {"variant": 1}


def test_a_parent_scene_s_tree_reads_the_trees_of_its_child_scenes_of_the_batch():
    """scene-tree@<scene> reads its own assembly and, beside, the tree of each child scene its plan lays out that is a
    scene of the batch (one in design is none: the tree's gate names it); a place of every scene but a line no place
    owns; the library reads it, so a scene is complete once its tree stands."""
    table = {stage.name: stage for stage in stages.STAGES}
    row = table["scene-tree"]
    assert row.downward and row.after == {"assembly": ("openusd-stage", 1)}
    assert row.beside == {"scene-tree": ("openusd-stage", 1)} and row.neighbours is stages.held_scenes
    assert not row.applies("people") and row.applies("hangar") and "scene-tree" in table["library"].after
    held, listed = stages.scene_tree.held, stages.places
    try:
        stages.scene_tree.held = lambda place: {"base": ["hangar", "lab", "dome"]}.get(place, [])
        stages.places = lambda world, store=None: ["base", "hangar", "lab"]
        assert stages.held_scenes("base") == ["hangar", "lab"] and stages.held_scenes("lab") == []
    finally:
        stages.scene_tree.held, stages.places = held, listed
    assert stages.parent_first({"cockpit", "hangar", "base", "hub", "wreck", "camp"},
                               {"cockpit": "hangar", "hangar": "base", "hub": "base", "camp": "campgrounds"}) == [
        "base", "hangar", "cockpit", "hub", "camp", "wreck"]


def designed(store, place):
    """`place`'s design done in `store`: a concept locked, its scene inventory read from it and its plan written from
    that reading (plans.design_done)."""
    from score.review import concepts, plan_writing, reading
    sha = place.ljust(64, "0")
    concepts.recorded(store, f"concepts/{place}/picks/2026-10-20T09-00-00.json",
                      {"place": place, "sha": sha, "by": "joey", "at": "2026-10-20T09:00:00+00:00"})
    reading.kept(store, {"place": place, "concept": sha, "at": "2026-10-20T09:10:00+00:00", "method": reading.METHOD,
                         "inventory": {"rows": [{"id": "desk", "name": "desk", "count": 1}]}})
    plan_writing.kept(store, {"place": place, "concept": sha, "reading": "2026-10-20T09:10:00+00:00",
                              "method": plan_writing.METHOD, "at": "2026-10-20T09:30:00+00:00", "by": "test",
                              "euros": 0.0,
                              "plan": {"title": place.upper(), "w": 3.0, "d": 3.0, "items": [], "doors": []}})


def test_a_place_is_a_scene_whose_design_is_done(tmp_path):
    """No kit or plan filed in the data names a place since 2026-10-21: a place is a scene of the design whose concept
    is locked, its inventory read and its plan written; one only drawn is still in design."""
    root = tmp_path
    store = Store.in_folder(root / "store")
    for part in ("kit/old.json", "plans/old.json"):  # an old filed kit and plan: no place
        (root / part).parent.mkdir(parents=True, exist_ok=True)
        (root / part).write_text("{}")
    designed(store, "laid")
    designed(store, "new")
    from score.review import concepts
    concepts.recorded(store, "concepts/drawn/draws/2026-10-20T08-00-00.json",
                      {"place": "drawn", "sha": "d" * 64, "by": "joey", "at": "2026-10-20T08:00:00+00:00"})
    world = graph.Environment("world1", 3, {"data": str(root)})
    assert stages.places(world, store) == ["laid", "new"]
    # a scene merged into another has no stage line, though its design is done
    (root / "places").mkdir()
    (root / "places/within.json").write_text(json.dumps({"merged": {"new": {"into": "laid"}}}))
    assert stages.places(world, store) == ["laid"]
    # nor has a part of another scene's outside: the scene it is part of builds it (the owner, 2026-10-21)
    (root / "places/within.json").write_text(json.dumps({"parts": {"new": {"of": "laid", "as": "far off"}}}))
    assert stages.places(world, store) == ["laid"]


def test_the_plan_row_keeps_the_plan_stages_code_version():
    """The plan row is the scene record's plan step as it stands (its code version kept), reading no kit: its files
    are the step's own."""
    plain = graph.Stage("plan", "place", stages.scene_record.plan.make, stages.scene_record.plan.PLACE_PLAN,
                        stages.scene_record.plan.CHECKS, files=stages.scene_record.plan.files)
    assert code_after_editing(stages.PLAN, "nothing") == code_after_editing(plain, "nothing")
    assert stages.earth_seed.locked_plan("launch") is None
    assert stages.PLAN.files("launch") == stages.scene_record.plan.files("launch")
    assert "kit" not in stages.PLAN.files("launch")


def test_the_plan_row_maps_a_place_with_no_kit(tmp_path):
    """With no kit laid, the plan row's make names the place by its plan and its `mapped` gate judges it."""
    root = tmp_path
    (root / "plans").mkdir()
    (root / "out").mkdir()
    plan = {"title": "NEW ROOM", "w": 3.0, "d": 3.0, "corner": 0.0, "height": "walls 2.5 m", "doors": [],
            "items": [["DESK", 1.0, 1.0, 1.0, 0.6, "S", "item"]], "rows": {"DESK": ["desk"]}, "leads": {},
            "elements": [{"element": "a desk", "rows": ["desk"]}, {"element": "a poster", "drop": "printed"}]}
    (root / "plans/new_room.json").write_text(json.dumps(plan))
    (root / "inventory.json").write_text(json.dumps({"rows": [{"id": "desk"}], "room": {"layout": {}}}))
    inputs = {"plan": str(root / "plans/new_room.json"), "inventory": str(root / "inventory.json"),
              "plans": str(root / "plans")}
    stages.PLAN.make(inputs, root / "out", 0, {})
    assert json.loads((root / "out/plan.json").read_text())["place"] == "new_room"
    verdict = stages.PLAN.checks[0].judge(root / "out", inputs, {})
    assert verdict.answer == checks.PASS, verdict.reason


def inputs_read(function):
    """The constant keys a function reads as inputs["<key>"]."""
    import ast
    tree = ast.parse(inspect.getsource(function))
    return {node.slice.value for node in ast.walk(tree) if isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name) and node.value.id == "inputs" and isinstance(node.slice, ast.Constant)}


def test_the_check_reads_every_input_check_step_reads():
    """surfaces-check hands check_step every key it reads (the crops' twin's stance rules were missing, 2026-10-16:
    KeyError at greenhouse), shortened as the prop environment hands them over (prop_env.short)."""
    bake_check, prop_env = sys.modules["bake_check"], sys.modules["prop_env"]
    read = inputs_read(bake_check.check_step) | inputs_read(bake_check.data_of)
    row = next(row for row in stages.STAGES if row.name == "surfaces-check")
    # only the keys matter here: a declared file may be (path, part), the part the runner reads
    handed = prop_env.short(dict.fromkeys([*row.files("greenhouse"), *row.after], "."))
    assert read <= set(handed), read - set(handed)


def test_a_ship_place_is_read_from_git():
    """On a home with no work folder: the cockpit is a ship place by its place.json mark and the hub is not."""
    assert not (PROPS_HOME / "work/usd-ship/cockpit").exists()
    assert stages.ship_place("cockpit") and not stages.ship_place("hub")


def test_the_cast_crowds_from_its_plan_never_a_hand_written_record():
    """Every place's cast, the ship's and the earth's alike, takes its views from its plan row (an `after`) and
    declares no old scene record (data/scene/<place>.json, the game's shots) and no views file under work/; its kit
    is its own place's, which earth_seeded reads from its earth seed (the design's kit, for its scene record)."""
    row = next(row for row in stages.STAGES if row.name == "cast")
    assert row.after["plan"] == ("place-plan", 2) and row.after["scene-record"] == ("scene-record", 1)
    for place in ("cockpit", "square", "hub"):
        declared = row.files(place)
        paths = [pattern[0] if isinstance(pattern, tuple) else pattern for pattern in declared.values()]
        assert not any(path.startswith("{data}/scene") or "world1-r4" in path for path in paths), (place, declared)
        kit = ["{data}/kit/{place}.json"]  # its own place's: declared, or read from its earth seed once it has one
        assert [path for path in stages.cast.files(place).values() if str(path).startswith("{data}/kit")] == kit
        kept = [] if stages.earth_place(place) else kit
        assert [path for path in paths if path.startswith("{data}/kit")] == kept, declared


def test_the_environment_data_names_no_path_into_the_work_folder():
    """A wording check guarding a rule: the work folder is no store (it went with the old disk, 2026-10-19), so no
    environment data file names a path into it; the last ones went with the old hand-ins (2026-10-21)."""
    found = subprocess.run(["git", "grep", "-l", "-E", r"\{home\}/work/|score-coordinator", "--", "data"], cwd=REPO,
                           capture_output=True, text=True).stdout.split()
    assert not found, f"paths into the work folder (make them a row's output, or a gap): {found}"


def test_the_motion_layer_names_only_rows_of_the_table_and_no_old_layer():
    import fnmatch
    names = [row.name for row in stages.STAGES]
    empty = [pattern for patterns in stages.MOTION_LAYER.values() for pattern in patterns
             if not fnmatch.filter(names, pattern)]
    assert not empty, f"motion layer patterns that name no row of the table: {empty}"
    old = [name for name in names if name.startswith("machines")]
    assert not old, f"rows under the old machines name (the motion layer's models now): {old}"


@functools.cache
def parsed(path):
    return ast.parse(path.read_text(), str(path))


@functools.cache
def named_scripts(path):
    """The repository .py files a source file names by a string path (repository-relative, or beside the file): a
    nested Blender's --python, a cloud or env job's script, a subprocess of a repo script."""
    found = set()
    for node in ast.walk(parsed(path)):
        text = node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else ""
        if text.endswith(".py") and not text.startswith("/") and not any(each.isspace() or each in "{}" for each in text):
            found |= {candidate.resolve() for candidate in (REPO / text, path.parent / text)
                      if candidate.is_file() and _code.in_repo(candidate)}
    return found


@functools.cache
def started_imports(path):
    """What a script run apart imports: its repository imports and the files beside it it imports by bare name (a
    script run apart has its own folder on its path)."""
    beside = {path.parent / (name.split(".")[0] + ".py") for name in _code.imported_names(path.read_text(), path, "")}
    return _code.imports_of(path, pathlib.Path.is_file, pathlib.Path.read_text) | \
        {found.resolve() for found in beside if found.is_file()}


@functools.cache
def repo_declarations(path):
    """The repository paths a source file's "{repo}/..." patterns name (a declared folder holds its files)."""
    return {(REPO / node.value[len("{repo}/"):]).resolve() for node in ast.walk(parsed(path))
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("{repo}/")
            and node.value != "{repo}/"}  # a bare prefix is a path built at run time, no declaration


def files_sources(files):
    """The source files of a row's file map and of every function the stage table wrapped it round (closures), and
    the patterns of any literal map among them."""
    modules, patterns, pending = set(), [], [files]
    while pending:
        found = pending.pop()
        if isinstance(found, dict):
            patterns += list(found.values())
        elif callable(found) and hasattr(found, "__code__"):
            modules.add(pathlib.Path(inspect.getsourcefile(found)).resolve())
            pending += [cell.cell_contents for cell in found.__closure__ or ()]
    return modules, patterns


def unkeyed_scripts(row):
    """(script, the file naming or importing it) of every script the row's code starts by path, followed through
    what those import, that neither its code version nor a "{repo}/" declaration of its code or of the stage table
    (which wraps rows' files) keys. Static: a script built from parts at run time (`HERE / "gates" / "model.py"`)
    is not seen."""
    version = set(_code.source_files(graph.code_functions(row)))
    own, listed = files_sources(row.files)
    table = REPO / "score/stages/__init__.py"
    near = own.union(*(_code.live_imports(path) for path in own - {table})) | {table}
    declared = set().union(*map(repo_declarations, near)) | {
        (REPO / pattern[len("{repo}/"):]).resolve() for pattern in listed
        if isinstance(pattern, str) and pattern.startswith("{repo}/")}
    pending, seen, unkeyed = [(path, False) for path in version], set(version), set()
    while pending:
        path, started = pending.pop()
        if _code.in_framework(path, _code.FRAMEWORK):  # what runs a job, not what a job runs
            continue
        for script, its_start in [(found, True) for found in named_scripts(path)] + \
                [(found, True) for found in (started_imports(path) if started else ())]:
            if script in seen or _code.in_framework(script, _code.FRAMEWORK):
                continue
            seen.add(script)
            pending.append((script, its_start))
            if not any(script == folder or script.is_relative_to(folder) for folder in declared):
                unkeyed.add((script.relative_to(REPO).as_posix(), path.relative_to(REPO).as_posix()))
    return unkeyed


def left(row):
    """True for a row the table leaves without its started scripts declared (stages.STARTED_LEFT)."""
    return any(fnmatch.fnmatch(row.name, pattern) for pattern in stages.STARTED_LEFT)


def test_every_script_a_row_starts_by_path_is_in_its_key():
    """A script a row's make starts by path (a nested Blender's --python, a blender_cloud or env job's script, a
    Newton Python, a subprocess of a repo script) is run apart, so no import keys it: it is a declared file of the
    row (the table's scripts_declared, or its own), with every file it imports, or a change to it never makes the
    row again and an output accepted on old code stays (make_chunky's bake scripts' recipes.py, 2026-10-28). Read
    here on its own, from each row's code: every one not keyed is named with its row; a STARTED_LEFT row, left
    because its re-make would buy again in the cloud, still has one (else it leaves the list)."""
    found = {(row.name, script, by) for row in stages.STAGES for script, by in unkeyed_scripts(row)
             if "{repo}/" + script not in getattr(row.files, "started", dict)()}
    named = [f"{name}: {script} (named by {by})" for name, script, by in sorted(found)
             if not left(next(row for row in stages.STAGES if row.name == name))]
    assert not named, "scripts run apart that no key follows (declare them in the row's files):\n" + "\n".join(named)
    unheld = [row.name for row in stages.STAGES if left(row) and not any(name == row.name for name, _, _ in found)]
    assert not unheld, f"STARTED_LEFT rows with nothing left undeclared: {unheld}"


def test_a_row_reading_the_recipes_declares_the_vendored_libraries_they_import():
    """recipes.py imports the vendored ProcFunc and Infinigen2 in Blender; a row declaring the library's code (the
    dress rows: tools/props/library) declares both, so re-vendoring makes its bakes again."""
    dress = next(row for row in stages.STAGES if row.name.startswith("people-dress-"))
    assert set(stages.VENDORED_RECIPES.values()) <= set(dress.files(None).values())


def test_a_take_the_owner_rejected_is_set_aside_once_and_retaken_without_moving_the_pixal_row(tmp_path):
    """Owner, 2026-10-28 (a failing object remade once, free): the table wires pixal to retake with its code version
    as it was; a take his reject names has its files moved aside once (the other takes and a take its name starts
    kept), is asked at its seed plus the attempt, and stays out of takes_back until its retake is made; a code build's
    take is refused.
    Break: score/stages/__init__.py: '        if not aside.exists():' -> '        if True:'"""
    row = next(row for row in stages.STAGES if row.name == "pixal")
    assert row.retakes and graph.stage_code(row) == graph.stage_code(dataclasses.replace(row,
                                                                                          make=inspect.unwrap(row.make)))
    for name in ("stool_1.glb", "stool_1-final.glb", "stool_1-5000.glb", "stool_1.json", "stool_10.glb", "seat_1.glb"):
        (tmp_path / name).write_text("old")
    (tmp_path / "stool_1.svviews").mkdir()
    (tmp_path / "pipe_1.svviews").mkdir()
    (tmp_path / "pipe_1.svviews" / "code.json").write_text("{}")
    objects = {"stool": {"take": "stool_1"}, "seat": {"take": "seat_1"}, "pipe": {"take": "pipe_1"}}
    retake = {"takes": ["stool_1"], "attempt": 1, "after": "k"}
    assert stages.set_aside(retake, objects, tmp_path) == {"stool_1": 2}
    aside = tmp_path / stages.RETAKEN / "stool_1-r1"
    assert sorted(path.name for path in aside.iterdir()) == [
        "stool_1-5000.glb", "stool_1-final.glb", "stool_1.glb", "stool_1.json", "stool_1.svviews"]
    assert sorted(path.name for path in tmp_path.glob("*.glb")) == ["seat_1.glb", "stool_10.glb"]
    assert stages.retake_pending("stool_1", tmp_path) and not stages.retake_pending("stool_10", tmp_path)
    (tmp_path / "stool_1.glb").write_text("new")
    stages.set_aside(retake, objects, tmp_path)
    assert (tmp_path / "stool_1.glb").read_text() == "new" and (aside / "stool_1.glb").read_text() == "old"
    (aside / stages.RETAKE_MADE).touch()
    assert not stages.retake_pending("stool_1", tmp_path)
    with pytest.raises(ValueError, match="pipe_1"):
        stages.set_aside({**retake, "takes": ["pipe_1"]}, objects, tmp_path)


def test_the_retaking_make_asks_a_retake_at_its_new_seed_and_marks_it_made(tmp_path):
    """The pixal make under a retake (stages.retaking) asks Pixal3D's seed of a named take as set_aside gave it and of
    any other take as its name gives it, its own seed_of put back after; a retake made is marked so; with no retake the
    make runs as it is.
    Break: score/stages/__init__.py: '        pixal_row.seed_of = lambda take: seeds[take] if take in seeds else named(take)' -> '        pass'"""
    pixal = pixal_row.take_files("-")[0].parent
    pixal.mkdir(parents=True, exist_ok=True)
    asked = []

    def make(inputs, out, seed, params):
        asked.append((pixal_row.seed_of("crate_7"), pixal_row.seed_of("seat-s3")))
        for suffix in pixal_row.SUFFIXES:
            pixal.joinpath(f"crate_7{suffix}").write_text("new")
    handin = tmp_path / "handin.json"
    handin.write_text(json.dumps({"objects": {"crate": {"route": "prop", "take": "crate_7"},
                                              "seat": {"route": "prop", "take": "seat-s3"}}}))
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"rows": [{"id": "crate", "size": [0.5, 0.5, 0.5]}]}))
    inputs = {"props": handin, "inventory": inventory, "closeup": tmp_path / "closeup"}
    stages.retaking(make)(inputs, tmp_path, 1, {"retake": {"takes": ["crate_7"], "attempt": 1, "after": "k"}})
    assert asked == [(2, 3)] and pixal_row.seed_of("crate_7") == 1
    assert (pixal / stages.RETAKEN / "crate_7-r1" / stages.RETAKE_MADE).exists()
    stages.retaking(make)(inputs, tmp_path, 1, {})
    assert asked[-1] == (1, 3)


def test_a_rejected_sheet_is_remade_as_its_flat_sheet_build_never_a_new_seed(tmp_path):
    """A sheet's take the owner's reject names (flat_sheet.sheet: a paper pinned to a wall) is remade in code from its
    own close-up (stages.sheet_remakes) before the make runs, so Pixal3D is never asked again for it and the retake is
    marked made; its mark says why.
    Break: score/stages/__init__.py: '        sheet_remakes(seeds, inputs, out)' -> '        pass'"""
    import score.stages.props.flat_sheet as flat_sheet
    import score.stages.props.thin_straight as thin_straight
    from PIL import Image
    pixal = pixal_row.take_files("-")[0].parent
    pixal.mkdir(parents=True, exist_ok=True)
    for suffix in ("-final.glb", "-4000.glb", ".glb"):
        pixal.joinpath(f"note_3{suffix}").write_text("old")
    pixal.joinpath("note_3.svviews").mkdir(exist_ok=True)
    handin = tmp_path / "handin.json"
    handin.write_text(json.dumps({"objects": {"note": {"route": "prop", "take": "note_3"}}}))
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"rows": [{"id": "note", "size": [0.2, 0.01, 0.3]}]}))
    surfaces = tmp_path / "surfaces.json"
    surfaces.write_text(json.dumps({"bake": {"models": {"note_1": "note_3"}, "entries": {"note_1": {"faces": 4000}}}}))
    (tmp_path / "closeup/closeups").mkdir(parents=True)
    picture = Image.new("RGB", (100, 140), (120, 120, 120))
    picture.paste((240, 235, 220), (20, 20, 80, 120))
    picture.save(tmp_path / "closeup/closeups/note.png")
    asked = []

    def make(inputs, out, seed, params):
        asked.append(flat_sheet.built("note_3", pixal))
    inputs = {"props": handin, "inventory": inventory, "closeup": tmp_path / "closeup", "surfaces": surfaces}
    stages.retaking(make)(inputs, tmp_path, 1, {"retake": {"takes": ["note_3"], "attempt": 1, "after": "k"}})
    assert asked == [True]
    assert pixal_row.finished("note_3", 4000)
    assert (pixal / stages.RETAKEN / "note_3-r1" / stages.RETAKE_MADE).exists()
    assert "reject" in json.loads((pixal / "note_3.svviews" / thin_straight.MARK).read_text())["why"]


# --- a scenes layers are read off its design ---

KINDS = {"person": {"nouns": ["astronaut", "crowd"], "does": ["acts"]},
         "kettle": {"nouns": ["kettle"], "does": ["emits", "loose"]},
         "door": {"nouns": ["door"], "does": ["moves"]}, "vehicle": {"nouns": ["rover"], "does": ["moves"]},
         "plant": {"nouns": ["plant", "plants", "planter", "rack"], "does": ["grows"]},
         "loose": {"nouns": ["chair"], "does": ["loose"]}}


def row(row_id, noun, kind="generate", anchor="floor"):
    return {"id": row_id, "noun": noun, "kind": kind, "anchor": anchor}


def test_each_row_shows_the_layer_its_kind_does():
    # a kettle emits and is loose; a rover and a door built as code both move
    assert design_layers.kinds_of({"rows": [row("kettle", "kettle")]}, KINDS) == {"effects", "physics", "light",
                                                                                   "sound"}
    assert design_layers.kinds_of({"rows": [row("rover", "rover")]}, KINDS) == {"motion", "light", "sound"}
    assert design_layers.kinds_of({"rows": [row("door", "door", kind="code")]}, KINDS) == {"motion", "light", "sound"}
    # a crowd acts; a bare room still has its light and sound
    assert design_layers.kinds_of({"rows": [row("crowd", "crowd")]}, KINDS) == {"people", "light", "sound"}
    assert design_layers.kinds_of({"rows": [row("wall", "wall", kind="code")]}, KINDS) == {"light", "sound"}


def test_crops_are_plants_on_a_bed_never_a_potted_plant():
    # plants on a raised planter (a row that grows itself) or on a bed by its noun are crops; a potted plant on the
    # floor or on a desk is not
    beds = [row("planter", "planter"), row("greens", "plants", anchor="on:planter")]
    assert "crops" in design_layers.kinds_of({"rows": beds}, KINDS)
    rack = [row("rack", "rack"), row("greens", "plants", anchor="on:rack")]  # no bed noun: it grows itself
    assert "crops" in design_layers.kinds_of({"rows": rack}, KINDS)
    plot = [row("bed", "bed", kind="code"), row("greens", "plants", anchor="on:bed")]
    assert "crops" in design_layers.kinds_of({"rows": plot}, KINDS)
    potted = [row("desk", "desk"), row("pot", "plant", anchor="on:desk"), row("fern", "plant")]
    assert "crops" not in design_layers.kinds_of({"rows": potted}, KINDS)


def test_plants_are_every_growing_row_and_the_planter_under_crops_is_their_bed():
    design = {"rows": [row("planter", "planter") | {"count": 11},
                       row("greens", "plants", anchor="on:planter") | {"count": 5},
                       row("pot", "plant") | {"count": 2}, row("desk", "desk")]}
    assert design_layers.plants_of(design, KINDS) == {"rows": 2, "objects": 7, "crops": 1, "beds": 11}
    assert design_layers.plants_of({"rows": [row("desk", "desk")]}, KINDS)["rows"] == 0


def test_the_house_rules_call_trees_and_shrubs_plants():
    from score.stages import row_kinds
    rules = row_kinds.table()
    for noun in ("tree", "palm", "shrub", "bush", "moss", "fern", "flower"):
        assert design_layers.plants_of({"rows": [row("green", noun)]}, rules)["rows"] == 1, noun


def test_a_place_has_a_layer_only_by_its_kept_design():
    with tempfile.TemporaryDirectory() as folder:
        kept, design_layers.KEPT = design_layers.KEPT, pathlib.Path(folder)
        try:
            (pathlib.Path(folder) / "shed.json").write_text(json.dumps({"rows": [row("pilot", "astronaut")]}))
            assert design_layers.has_layer("shed", "people") and design_layers.has_layer("shed", "light")
            assert not design_layers.has_layer("shed", "effects")
            # a place with no design has no layer at all, light and sound included
            assert not design_layers.has_layer("barn", "light") and not design_layers.has_layer(None, "sound")
        finally:
            design_layers.KEPT = kept


def test_the_table_has_a_row_for_every_layer_the_gate_waits_on():
    """For a design kept where the plan stage keeps it, every layer stage the assembly's layers gate needs is a row
    the table holds for the place, and no layer row the assembly reads applies beyond them, by the house's rules."""
    import score.stages as stages
    from score.stages import assembly, row_kinds
    design = {"rows": [row("pilot", "astronaut"), row("kettle", "kettle"), row("hatch", "door", kind="code"),
                       row("planter", "planter"), row("greens", "plants", anchor="on:planter")]}
    with tempfile.TemporaryDirectory() as folder:
        kept, design_layers.KEPT = design_layers.KEPT, pathlib.Path(folder)
        try:
            (pathlib.Path(folder) / "shed.json").write_text(json.dumps(design))
            needed = assembly.needed_layers(design, row_kinds.table())
            rows = {stage.name for stage in stages.STAGES if stage.grain == "place"
                    and stage.name in assembly.NEEDS.values() and stage.applies is not None
                    and stage.applies("shed")}
        finally:
            design_layers.KEPT = kept
    assert needed == ["characters-layer", "crops-layer", "effects-layer", "motion", "settle", "light", "sound"]
    assert rows == set(needed), rows


# --- a rows kind comes from its own words ---

RULES = {"door": {"nouns": ["door", "hatch"], "does": ["moves"]},
         "kettle": {"nouns": ["kettle"], "does": ["emits", "loose"]},
         "loose": {"nouns": ["chair", "cylinder"], "does": ["loose"]}}


def test_the_noun_decides_before_the_name():
    # a "door panel" is a panel (its noun), not a door; a row read with no noun falls back on its name's last word
    assert row_kinds.kind_of({"id": "door_panel", "name": "door panel", "noun": "panel"}, RULES) is None
    assert row_kinds.kind_of({"id": "airlock_door", "name": "airlock door", "noun": "door"}, RULES) == "door"
    assert row_kinds.kind_of({"id": "gas_cylinder", "name": "gas cylinder"}, RULES) == "loose"
    assert row_kinds.kind_of({"id": "round_hatch"}, RULES) == "door"
    # a noun of two words is matched whole: a "floor plate" is no plate, though "plate" is a loose noun
    assert row_kinds.kind_of({"id": "floor_plate", "name": "floor plate", "noun": "floor plate"},
                             {"loose": {"nouns": ["plate"], "does": ["loose"]}}) is None


def test_a_lamp_read_as_what_holds_it_is_still_a_lamp():
    # a "floodlight tower" read as a tower is the lamp kind's (held_by); a "light switch" and a "fence post" are none
    rules = {"lamp": {"nouns": ["light", "floodlight"], "does": ["glows"], "held_by": ["tower", "frame", "post"]}}
    assert row_kinds.kind_of({"id": "floodlight_tower", "name": "floodlight tower", "noun": "tower"}, rules) == "lamp"
    assert row_kinds.kind_of({"id": "grow_light_frame", "noun": "frame"}, rules) == "lamp"
    assert row_kinds.kind_of({"id": "light_switch", "name": "light switch", "noun": "switch"}, rules) is None
    assert row_kinds.kind_of({"id": "fence_post", "name": "fence post", "noun": "post"}, rules) is None


def test_a_scenes_rows_are_picked_by_what_their_kind_does_and_a_kind_can_do_more_than_one_thing():
    inventory = {"rows": [{"id": "kettle", "noun": "kettle"}, {"id": "stool", "noun": "chair"},
                          {"id": "front_door", "noun": "door"}, {"id": "wall", "noun": "wall"}]}
    assert [row["id"] for row in row_kinds.rows_that(inventory, "loose", RULES)] == ["kettle", "stool"]
    assert [row["id"] for row in row_kinds.rows_that(inventory, "emits", RULES)] == ["kettle"]
    assert [(row["id"], row["row_kind"]) for row in row_kinds.rows_that(inventory, "moves", RULES)] == [
        ("front_door", "door")]


def test_the_house_rules_read_real_words():
    rules = row_kinds.table()
    expected = {("stove", "stove"): "cooker", ("table lamp", "lamp"): "lamp", ("tracked rover", "rover"): "vehicle",
                ("ceiling light", "light"): "lamp", ("dining chair", "chair"): "loose", ("tv", "tv"): "screen",
                ("laptop", "laptop"): "computer", ("planter bed", "planter"): "plant", ("hatch", "hatch"): "door",
                ("door mat", "mat"): None, ("outer wall", "wall"): None}
    for (name, noun), kind in expected.items():
        assert row_kinds.kind_of({"id": name.replace(" ", "_"), "name": name, "noun": noun}, rules) == kind, name


def test_a_rows_objects_are_found_outside_the_layers_scopes_and_anything_else_is_a_stranger():
    stage = Usd.Stage.CreateInMemory()
    for path in ("/toy", "/toy/Fixtures", "/toy/Fixtures/door_1", "/toy/Fixtures/door_1/door_1", "/toy/Objects",
                 "/toy/Objects/door_2", "/toy/Objects/door_frame_1", "/toy/Effects", "/toy/Effects/door_3"):
        UsdGeom.Xform.Define(stage, path)
    assert row_kinds.objects_of(stage, "toy", "door") == ["/toy/Fixtures/door_1", "/toy/Objects/door_2"]
    assert row_kinds.objects_of(stage, "toy", "window") == []
    assert row_kinds.objects_of(stage, "elsewhere", "door") == []
    inventory = {"rows": [{"id": "door"}, {"id": "kettle"}]}
    assert row_kinds.strangers(["Objects/door_2", "Objects/kettle", "Objects/door_frame_1", "Objects/doormat"],
                               inventory) == ["Objects/door_frame_1", "Objects/doormat"]


# --- every designed person is a look of the line ---

def test_every_people_row_maps_to_a_look():
    found = people_rows.read()
    line = people_rows.line_looks()
    for place, entry in found["places"].items():
        for row, fields in entry["rows"].items():
            if "crowd" in fields:
                assert fields["crowd"] in line, (place, row)
            else:
                assert len(fields["looks"]) == fields["count"], (place, row)  # a look for each person
                assert all(look in line for look in fields["looks"]), (place, row)  # every person can be made
    # one body a look (owner, 2026-10-22): the camp's, the garage's and the airlock's astronauts are one look
    assert people_rows.mapping_rows(found)["astronaut-made"]
    assert {fields["looks"][0] for place in ("camp", "garage", "airlock") for fields in
            found["places"][place]["rows"].values()} == {"astronaut-made"}
    assert all(look.endswith(f"-{people_rows.OUTFIT}") for look in line), "a row asks for the drawn face"


def test_people_rows_are_grouped_into_looks_by_what_they_are_and_wear():
    """One body a look (owner, 2026-10-22): a row's words before where it stands or what it holds, its pose and
    colour words left out (its clip and its dress vary it); a named person or the player is a look of its own."""
    def look(name, crowd=False, row="row"):
        return people_rows.look_of("deck", {"id": row, "name": name, "noun": "person"}, crowd)
    assert look("seated astronaut") == look("astronaut standing") == look("astronauts") == "astronaut-made"
    assert look("person sitting at a table") == look("people on walkway") == look("person holding an umbrella") \
        == look("person") == "person-made"
    assert look("worker in blue jumpsuit") == look("worker in grey jumpsuit") == "worker_jumpsuit-made"
    assert look("person in uniform") == "person_uniform-made" != look("person in spacesuit")
    assert look("crowd of people", crowd=True) == "crowd-made" and look("crowd of aliens", crowd=True) == "alien-made"
    assert look("the player in a work suit", row="hero") == look("Nev at the console", row="hero") == "deck_hero-made"


def test_a_person_row_s_look_is_written_from_the_row_alone():
    """#26: a design's person is made from its row, never a hand-written character file: who by the row's words, the
    build by its metres, face, hair and clothes as the concept draws them; a spec the maker takes."""
    sys.path.insert(0, str(REPO / "tools/characters/maker"))
    import spec as specs
    found = {"places": {"deck": {"concept": "abcdef0123", "rows": {
        "pilot": {"name": "pilot in a red suit", "noun": "person", "count": 2, "size": [0.3, 0.4, 1.7],
                  "where": "standing at the console", "share": 0.2, "looks": ["pilot_suit-made"] * 2},
        "guest": {"name": "seated guest", "noun": "person", "count": 1, "size": [0.7, 0.9, 1.3],
                  "where": "sitting on a sofa", "looks": ["guest-made"]},
        "copilot": {"name": "seated pilot in a suit", "noun": "person", "count": 1, "size": [0.7, 0.9, 1.3],
                    "where": "sitting at the console", "share": 0.5, "looks": ["pilot_suit-made"]},
        "crowd": {"name": "crowd of people", "noun": "crowd", "count": 1, "size": [8.0, 9.0, 1.8],
                  "crowd": "crowd-made"}}}}}
    surfaces = json.loads(people_rows.LINE_FILES["surfaces"].read_text())
    made = people_rows.designed_specs(found, surfaces)
    assert set(made) == {"pilot_suit-made", "guest-made", "crowd-made"}
    pilot = made["pilot_suit-made"]  # drawn from its largest standing person, never the bigger seated one
    assert pilot["name"] == "pilot_suit" and pilot["outfits"] == ["made"] and "abcdef01" in pilot["approved"]
    assert pilot["description"] == "pilot in a red suit, a slim build, as drawn in the deck concept", pilot
    assert people_rows.size_of("pilot_suit-made", found) == ([0.3, 0.4, 1.7], "deck/pilot")
    assert "a broad build" in made["guest-made"]["description"]  # seated: its narrower side, 0.7 m
    assert made["crowd-made"]["description"].startswith("one person of the crowd of people, an average build")
    assert all(not specs.problems_of(spec) for spec in made.values()), [specs.problems_of(s) for s in made.values()]
    assert people_rows.member_size("crowd-made", found) == ([0.55, 0.55, 1.8], "deck/crowd")
    props, inventory, lined = people_rows.with_designed(made, {"objects": {}}, {"rows": []}, surfaces)
    take = lined["bake"]["models"]["pilot_suit-made"]
    assert take == "pilot_suit-made-s1" and props["objects"]["pilot_suit-made"]["take"] == take
    assert lined["takes"][take]["spec"] == "data/people/specs/pilot_suit.json"
    assert lined["takes"][take]["outfit"] == "made" and {row["id"] for row in inventory["rows"]} == set(made)
    assert all(entry["spec"].startswith("data/people/specs/") for entry in surfaces["takes"].values()), \
        "every look on the line is written from a design's row (the hand-made makes were retired, 2026-10-21)"


def test_a_crowd_s_ground_is_the_plan_items_its_row_makes():
    plan = {"w": 20.0, "d": 10.0, "items": [["CROWD 1", 2.0, 1.0, 6.0, 4.0, None, "item"],
                                            ["BENCH 1", 0.0, 0.0, 1.0, 1.0, "N", "item"]],
            "rows": {"CROWD 1": ["crowd"], "BENCH 1": ["bench"]}}
    assert people_rows.crowd_ground(plan, "crowd") == [[-8.0, -4.0, 6.0, 4.0]]  # unframed: the plan's middle at 0
    assert people_rows.crowd_ground(plan, "pilot") == [] and people_rows.crowd_ground(None, "crowd") == []
    inventory = {"concept_pick": {"sha256": "0badcafe"}, "rows": [
        {"id": "crowd", "name": "crowd of people", "noun": "people", "count": 1, "route": "people"}]}
    entry = people_rows.refreshed_place("deck", inventory, plan, None)
    crowd = people_rows.crowd_record("crowd", entry["rows"]["crowd"], entry)
    assert crowd["spread"] == [-8.0, -4.0, 6.0, 4.0] and crowd["grounds"] == [[-8.0, -4.0, 6.0, 4.0]]
    assert crowd["count"] is None and crowd["seed"] == 0x0badcafe and crowd["facing_to"] == entry["middle"]
    # its palettes the variants of its look's body it wears, a few, never more than SAM 3 counted people in it
    assert crowd["palettes"] == list(range(people_rows.CROWD_VARIANTS)) and sum(crowd["palette_shares"]) == 1.0
    counted = {**entry["rows"]["crowd"], "count": 30}
    assert people_rows.crowd_record("crowd", counted, entry)["count"] == 30
    assert people_rows.crowd_record("crowd", {**counted, "count": 3}, entry)["palettes"] == [0, 1, 2]


def test_a_people_row_the_plan_shows_beyond_the_place_is_not_its_own():
    """groups.current routes a people row the plan shows beyond the place to the backdrop, unless it stands on a row
    laid here (2026-10-26: the stairwell's man and woman on its own stairs, listed beyond, were made by nothing)."""
    from score.stages.complete.prepare import groups
    plan = {"w": 20.0, "d": 10.0, "items": [], "rows": {}, "beyond": ["far_crowd", "man", "far_stage", "singer"]}
    rows = [{"id": "far_crowd", "name": "crowd of people", "noun": "crowd", "count": 3, "route": "people",
             "anchor": "ground"},
            {"id": "pilot", "name": "pilot in a red suit", "noun": "pilot", "count": 1, "route": "people",
             "anchor": "floor"},
            {"id": "stairs", "route": "prop", "anchor": "floor"},
            {"id": "man", "name": "man on the stairs", "noun": "man", "count": 1, "route": "people",
             "anchor": "on:stairs"},
            {"id": "far_stage", "route": "prop", "anchor": "ground"},
            {"id": "singer", "name": "singer on the far stage", "noun": "singer", "count": 1, "route": "people",
             "anchor": "on:far_stage"}]
    beyond = groups.stood_beyond(rows, set(plan["beyond"]))
    assert beyond == {"far_crowd", "far_stage", "singer"}, beyond  # the man stands on the place's own stairs
    inventory = {"concept_pick": {"sha256": "0badcafe"}, "rows": [groups.routed(row, set(), beyond) for row in rows]}
    assert set(people_rows.refreshed_place("deck", inventory, plan, None)["rows"]) == {"pilot", "man"}


def test_each_person_stands_on_a_plan_spot_each_its_own_variant_of_the_look():
    """Each person of a row is dealt the plan's people spots in turn (a plan unframed: its middle at 0, so the spot
    (1, 1) of a 20 x 10 m plan stands at (-9, 0, -4)), and each person of one look wears its own variant of the body
    (owner, 2026-10-25: "Each one looks different")."""
    inventory = {"concept_pick": {"sha256": "one"}, "rows": [
        {"id": "pilot", "name": "person in uniform", "noun": "person", "count": 3, "size": [0.5, 0.3, 1.8],
         "route": "people"}]}
    plan = {"w": 20.0, "d": 10.0, "items": [], "rows": {},
            "people": [[1.0, 1.0, 0, "pilot"], [3.0, 2.0, 0, "pilot"], [5.0, 3.0, 0, "pilot"]]}
    entry = people_rows.refreshed_place("deck", inventory, plan, None)
    people = people_rows.cast_record("deck", {"places": {"deck": {**entry, "concept": "one"}}})["people"]
    assert [person["at"] for person in people] == [[-9.0, 0.0, -4.0], [-7.0, 0.0, -3.0], [-5.0, 0.0, -2.0]]
    assert {person["look"] for person in people} == {"person_uniform_made"}
    assert sorted(person["variant"] for person in people) == [0, 1, 2]


def test_the_line_holds_the_mapped_looks_each_baked_at_its_rows_size(tmp_path):
    records = {name: json.loads(path.read_text()) for name, path in people_rows.LINE_FILES.items()}
    # the kept inventories are the home's, never read by a test: each holds the box the line already draws from
    for row in records["inventory"]["rows"]:
        if row.get("view"):
            place, row_id = people_rows.size_of(row["id"])[1].split("/", 1)
            path = tmp_path / f"{place}.json"
            held = json.loads(path.read_text()) if path.exists() else {"rows": []}
            path.write_text(json.dumps({"rows": held["rows"] + [{"id": row_id, "box": row["box"]}]}))
    props, inventory, surfaces = people_refresh.line_rows(people_rows.read(), records["props"], records["inventory"],
                                                       records["surfaces"], tmp_path)
    assert (props, inventory, surfaces) == (records["props"], records["inventory"], records["surfaces"]), \
        "the line's data is not written from rows.json: run python -m score.stages.people_refresh"
    assert set(props["objects"]) == people_rows.every_look()  # every look the designs map, each on the line
    assert set(surfaces["bake"]["entries"]) == set(surfaces["bake"]["models"]) == set(props["objects"])
    assert people_rows.size_of("person_uniform-made")[1] == "tube/person_right"  # the larger of the tube's two rows
    size, origin = people_rows.size_of("crowd-made")
    assert people_rows.person_sized(size) and origin == "square/crowd"  # one member, never the crowd's extent
    walkway = {"name": "people on walkway", "noun": "people", "count": 5, "size": [10.0, 30.0, 1.8], "share": 0.06,
               "looks": ["person-made"] * 5}  # five people standing apart on 10 x 30 m
    found = {"places": {"deck": {"concept": "0badcafe", "rows": {"walkway_crowd": walkway}}}}
    size, origin = people_rows.size_of("person-made", found)
    assert people_rows.person_sized(size) and origin == "deck/walkway_crowd", (size, origin)


def test_each_line_row_is_drawn_from_the_person_that_maps_it():
    """#26: the shared loop draws each look's close-up from the picked design's person row that maps it (its view the
    kept concept, its box SAM 3's, grounded), so no take row and no work folder stands before the line; the line is
    approved by those picks, as the Pixal3D batch takes a design."""
    import tempfile
    records = {name: json.loads(path.read_text()) for name, path in people_rows.LINE_FILES.items()}
    with tempfile.TemporaryDirectory() as held:
        kept = pathlib.Path(held)
        (kept / "tube.json").write_text(json.dumps({"rows": [{"id": "person_right", "box": [1, 2, 3, 4]}]}))
        boxes = [[number, 0, number + 1, 2 + number % 3] for number in range(5)]
        (kept / "garage.json").write_text(json.dumps({"rows": [{"id": "astronaut", "box": boxes[0],
                                                                 "boxes": boxes}]}))
        props, inventory, _ = people_refresh.line_rows(people_rows.read(), records["props"], records["inventory"],
                                                    records["surfaces"], kept)
    rows = {row["id"]: row for row in inventory["rows"]}
    right = rows["person_uniform-made"]
    assert right["view"] == "tube" and right["box"] == [1, 2, 3, 4]
    assert right["grounded"] and right["prop"] == "person_uniform-made"
    assert rows["crowd-made"]["view"] is None, "the square keeps no inventory here"
    assert inventory["plan"]["views"] == [{"id": place, "picture": f"{{home}}/design/concepts/{place}.png"}
                                          for place in ("garage", "tube")]
    assert inventory["approved"]["by"] == "the creator's pick"
    assert inventory["approved"]["places"] == ["garage", "tube"]
    assert "closeup" not in props["objects"]["person_uniform-made"]
    # a look drawn from the tallest of its row's SAM 3 instances: its largest person
    assert rows["astronaut-made"]["view"] == "garage" and rows["astronaut-made"]["box"] == boxes[2]


def test_each_line_rows_close_up_words_say_who_the_look_is():
    """#26: the first people benchmark drew its player, a Chinese man in his thirties by his spec, as someone else:
    the close-up's words were the reading's clothes alone. Every look's words start with its spec's description."""
    from score.stages.props import closeup_row
    inventory = json.loads(people_rows.LINE_FILES["inventory"].read_text())
    rows = {row["id"]: row for row in inventory["rows"]}
    words = {row["id"]: row["words"] for row in closeup_row.inventory_rows(inventory, people_rows.every_look())}
    assert words["person_uniform-made"].startswith("person in uniform, an average build")
    for look, said in words.items():
        assert said == f"{people_rows.description_of(look)}; {rows[look]['clothes']}"


def test_a_refresh_keeps_the_choices_of_the_same_concept():
    inventory = {"concept_pick": {"sha256": "one"}, "rows": [
        {"id": "pilot", "name": "person", "noun": "person", "count": 2, "size": [0.5, 0.3, 1.8], "route": "people"},
        {"id": "crowd", "name": "crowd of people", "noun": "people", "count": 1, "route": "people"},
        {"id": "chair", "name": "chair", "noun": "chair", "count": 1, "route": "prop"}]}
    fresh = people_rows.refreshed_place("deck", inventory, None, None)
    assert fresh["rows"]["pilot"]["looks"] == ["person-made", "person-made"] and "chair" not in fresh["rows"]
    assert fresh["rows"]["crowd"]["crowd"] == "crowd-made", \
        "a crowd takes no look drawn from another scene's row"
    fresh["rows"]["pilot"]["looks"] = ["deck_pilot-made", "person-made"]
    assert people_rows.refreshed_place("deck", inventory, None, fresh)["rows"]["pilot"]["looks"][0] == \
        "person-made", "a pick with no why is no hand-made choice: read again from the design"
    fresh["rows"]["pilot"]["why"] = "the owner's pick: the player"
    assert people_rows.refreshed_place("deck", inventory, None, fresh)["rows"]["pilot"]["looks"][0] == \
        "deck_pilot-made"
    redrawn = {**inventory, "concept_pick": {"sha256": "two"}}
    assert people_rows.refreshed_place("deck", redrawn, None, fresh)["rows"]["pilot"]["looks"][0] == "person-made"


def test_a_crowds_look_is_read_off_its_words():
    """No city square's coats on every crowd: the people line's look sharing the most of the row's words, a crowd
    word only between looks that share no other, a new look when none shares a word."""
    import tempfile
    with tempfile.TemporaryDirectory() as held:
        citizen, astronaut = pathlib.Path(held) / "citizen.json", pathlib.Path(held) / "astronaut.json"
        citizen.write_text(json.dumps({"description": "a man in his thirties, an ordinary citizen in the crowd"}))
        astronaut.write_text(json.dumps({"description": "a man in his thirties, an astronaut of a Moon base"}))
        line = {"citizen-coat": {"object": "a person in a plain mid grey coat", "far_only": True,
                                 "spec": str(citizen)},
                "astronaut-work": {"object": "a person in a dark navy one-piece work suit", "spec": str(astronaut)}}

        def look(name, noun):
            return people_rows.crowd_look("moon", {"id": "crowd", "name": name, "noun": noun}, line)
        assert look("crowd of people", "people") == "citizen-coat"  # "an ordinary citizen in the crowd"
        assert look("crowd of astronauts", "crowd") == "astronaut-work"  # "an astronaut of a Moon base"
        assert look("flock of penguins", "penguin") == "flock_penguin-made"  # its own words' (designed_specs)
        # who the row names decides, never its crowd word alone: a city crowd's look is no one else's crowd
        assert look("crowd of aliens", "crowd") == "alien-made"
        assert look("crowd of martian colonists", "crowd") == "martian_colonist-made"
        assert look("crowd of shoppers in grey coats", "crowd") == "citizen-coat"
        # a look drawn from another scene's crowd row is that row's own, however its words match
        drawn = pathlib.Path(held) / "crowd.json"
        drawn.write_text(json.dumps({"description": "one person of the crowd of people, as drawn in the square "
                                                    "concept"}))
        square = {"square_crowd-drawn": {"object": "one person of the crowd of people", "far_only": True,
                                         "spec": str(people_rows.SPECS / "square_crowd.json")},
                  "people-made": {"object": "one person of the crowd of people", "far_only": True,
                                  "spec": str(drawn)}}
        row = {"id": "crowd", "name": "crowd of people", "noun": "crowd"}
        assert people_rows.crowd_look("moon", row, square) == "crowd-made"
        assert people_rows.crowd_look("moon", row, {**line, **square}) == "citizen-coat"


def a_concept(fabric_lab_colour, box):
    """A 100 x 100 concept, dark, the box's torso painted the given sRGB (0..255)."""
    import numpy as np
    picture = np.full((100, 100, 3), 20, dtype=np.uint8)
    left, top, right, bottom = box
    picture[top:bottom, left:right] = fabric_lab_colour
    return picture


def test_a_row_wears_the_fabric_its_words_name_nearest_its_torso():
    """The concept decides the clothes, per row: of the people fabrics its name names, the nearest its measured torso
    within people_clothes.WITHIN; a row naming none, or one whose torso is far from every named fabric, wears its
    look's own paint; and the cast and the dress rows follow the row (no hand-kept list of places)."""
    import numpy as np
    from score.stages import people_clothes
    labels = people_clothes.labels()
    # the people's fabrics as their surface library gives them (every old surface retired on 2026-10-21: stand-ins)
    blue = np.array([38, 64, 150], dtype=np.uint8)

    def lab(srgb):
        return [float(value) for value in labels.lab(np.array(srgb, dtype=float)[None] / 255)[0]]
    fabrics = {"jacket_blue": lab(blue), "suit_light_blue": lab([150, 180, 220]), "suit_grey": lab([128, 128, 128])}
    assert people_clothes.fabrics() == {}  # the repository's library holds none
    box = [20, 10, 60, 90]
    inventory = {"concept_pick": {"sha256": "one"}, "rows": [
        {"id": "worker", "name": "worker in blue jumpsuit", "where": "near the light", "noun": "worker", "count": 1,
         "size": [0.5, 0.3, 1.8], "route": "people", "boxes": [box]},
        {"id": "pilot", "name": "person", "where": "left", "noun": "person", "count": 1, "size": [0.5, 0.3, 1.8],
         "route": "people", "box": box}]}
    entry = people_rows.refreshed_place("deck", inventory, None, None, a_concept(blue, box), fabrics)
    worker, pilot = entry["rows"]["worker"]["dress"], entry["rows"]["pilot"]["dress"]
    assert worker["surface"] == "jacket_blue" and worker["de"] < 1 and worker["figures"] == 1, worker
    assert "suit_light_blue" in worker["named"] and not any("light" in name and "blue" not in name
                                                            for name in worker["named"]), worker
    assert pilot["surface"] is None and pilot["named"] == [], pilot
    orange = a_concept([230, 90, 20], box)
    far = people_rows.refreshed_place("deck", inventory, None, None, orange, fabrics)["rows"]["worker"]["dress"]
    assert far["surface"] is None and far["de"] > people_clothes.WITHIN, far
    unseen = people_rows.refreshed_place("deck", inventory, None, None, None, fabrics)["rows"]["worker"]["dress"]
    assert unseen["surface"] is None and unseen["torso_lab"] is None, unseen
    found = {"places": {"deck": {**entry, "concept": "one"}}}
    assert people_rows.dressed_looks("deck", found) == {("worker_jumpsuit-made", "jacket_blue", 0),
                                                        ("person-made", None, 0)}
    assert people_rows.every_dressed(found) == {("worker_jumpsuit-made", "jacket_blue", 0)}
    worker_row = {**entry["rows"]["worker"], "looks": ["worker_jumpsuit-made"] * 2}
    twice = {"places": {"deck": {**entry, "concept": "one", "rows": {**entry["rows"], "worker": worker_row}}}}
    assert people_rows.every_dressed(twice) == {("worker_jumpsuit-made", "jacket_blue", 0),
                                                ("worker_jumpsuit-made", "jacket_blue", 1)}, "two people, two variants"
    assert {person["name"]: person["surface"] for person in people_rows.cast_record("deck", found)["people"]} == {
        "worker": "jacket_blue", "pilot": None}


# --- a ground follows its words then its physics ---

STAR = {"body": "star", "name": "Star", "kelvin": 5772.0, "radius_km": 695700.0}


AU = 149597870.7


def world(name, kpa, distance_km, around="star"):
    return {"body": name, "name": name.title(), "around": around, "distance_km": distance_km,
            "surface_pressure_kpa": kpa}


def test_the_physics_pick_ocean_rock_ice_sand_and_regolith():
    wet, hot = world("wet", 101.3, AU), world("hot", 101.3, 0.2 * AU)
    frozen, windy = world("frozen", 0.0, 5.2 * AU), world("windy", 0.6, 1.52 * AU)
    airless = world("airless", 0.0, 384400.0, around="wet")  # a moon: its planet's distance from the star
    bodies = [STAR, wet, hot, frozen, windy, airless]
    picked = {body["body"]: natural_grounds.of_body(body, bodies, {})[0] for body in bodies[1:]}
    assert picked == {"wet": "ocean", "hot": "rock", "frozen": "ice", "windy": "sand", "airless": "regolith"}
    assert "278 K" in natural_grounds.of_body(wet, bodies, {})[1]


def test_a_row_s_words_come_first_and_what_is_missing_is_named():
    windy = world("windy", 0.6, 1.52 * AU)
    assert natural_grounds.of_row({"id": "dunes", "name": "red dunes", "noun": "ground"}, None, [], {})[0] == "sand"
    assert natural_grounds.of_row({"id": "g", "name": "martian ground", "noun": "ground"}, windy, [STAR, windy],
                                  {})[0] == "sand"  # the physics, never the word "martian"
    assert natural_grounds.of_row({"id": "g", "noun": "ground"}, None, [], {})[0] is None  # a plot: no physics
    plaza = natural_grounds.of_row({"id": "plaza", "name": "main plaza", "noun": "plaza"}, windy, [STAR, windy], {})
    assert plaza == (None, "the row plaza says plaza: a made ground, no natural one")  # people paved it
    assert natural_grounds.of_row({"id": "sea", "noun": "sea"}, windy, [STAR, windy], {})[0] == "ocean"
    recipe, why = natural_grounds.of_body({"body": "x", "name": "X", "around": "star", "distance_km": AU},
                                          [STAR], {})
    assert recipe is None and "no surface pressure" in why
    table = {"bodies": {"x": {"surface_pressure_kpa": 0.0}}}  # the reference table's value when the setting has none
    assert natural_grounds.of_body({"body": "x", "name": "X", "around": "star", "distance_km": AU}, [STAR],
                                   table)[0] == "regolith"


# --- a copy of a read only seed takes a save ---

def test_a_built_layer_copy_of_a_read_only_seed_is_writable(tmp_path):
    folder = tmp_path / "seed"
    (folder / "layers").mkdir(parents=True)
    (folder / "layers" / "base.usda").write_text("#usda 1.0\n")
    for path in (folder / "layers" / "base.usda", folder / "layers", folder):
        path.chmod(0o555 if path.is_dir() else 0o444)
    layer_base.writable(folder)
    (folder / "layers" / "base.usda").write_text("#usda 1.0\n")
    (folder / "layers" / "new.usda").write_text("#usda 1.0\n")


# --- an accepted gap moves only its named faults ---

ROWS = {row.name: row for row in stages.STAGES}


DECIDED = "owner, 2026-10-14 08:40"


def entry(name, row, check, objects, faults, **more):
    """One accepted gap in the file's form."""
    return {"name": name, "row": row, "check": check, "objects": objects, "reason": "a test's decision",
            "decided": DECIDED, "faults": faults, **more}


@contextlib.contextmanager
def decided(place_gaps):
    """gaps.FOLDER a folder of its own holding {place: [gap]} as the owner's files, for the length of a `with`."""
    held = gaps.FOLDER
    with tempfile.TemporaryDirectory() as folder:
        gaps.FOLDER = pathlib.Path(folder)
        for place, found in place_gaps.items():
            (gaps.FOLDER / f"{place}.json").write_text(json.dumps({"gaps": found}))
        try:
            yield
        finally:
            gaps.FOLDER = held


def recorded(place):
    return {gaps.NAME: str(gaps.FOLDER / f"{place}.json")}


def failed(check, findings):
    return checks.Verdict(check, checks.FAIL, f"{len(findings)} faults", {"faults": len(findings)},
                          {"faults": "lower"}, tuple(findings))


RESTING = entry("fragments: resting in the regolith", "assembly", "resting",
                [f"/wreck/Objects/fragment_{number}" for number in (1, 2)],
                [f"/wreck/Objects/fragment_{number}: sunk 0.05 under its contact points" for number in (1, 2)])


SHIP = entry("ship: no made model", "assembly", "placeholders",
             ["/hangar/Structure/ship", "/hangar/Structure/ship_legs"],
             [f"/hangar/Structure/{name}: plain: drawn by the record's {name} builder (a made piece's stand-in)"
              for name in ("ship", "ship_legs")])


ORDER = entry("fluid shelves: order", "surfaces-check", "baked matches its surfaces", ["fluid_shelves_1"],
              ["fluid_shelves_1: plastic_grey baked over galvanized_steel: the close-up's order reversed"],
              contains="order")


ROWS_GAP = entry("far ferry: no stage makes it", "complete", "rows", ["far_ferry"],
                 [json.dumps({"row": "far_ferry", "why": "no object of this row"})])


BOXES_GAP = entry("wall screen: its box", "complete", "boxes", ["wall_screen"],
                  [json.dumps({"row": "wall_screen", "result": "fail", "why": "judge: no screen in the box"})])


GAME = entry("launch: layout taken from the source game", "complete", "game", ["data/scene/launch.json"],
             ["data/scene/launch.json: 12 entries take their numbers from the game (source), 4 positions placed"])


CASES = {  # gap, another fault of the same gate no gap names
    "plain objects": (RESTING, "/wreck/Objects/fragment_3: floats 0.04: nothing under it"),
    "placeholders": (SHIP, "/hangar/Structure/crate: plain: drawn by the record's box builder (a made piece's "
                           "stand-in)"),
    "of its kind only": (ORDER, "fluid_shelves_1: crane_yellow_paint baked [70.1, 5.0, 60.2] against [74.0, 4.1, "
                                "70.3] (dE 36.4)"),
    "rows by row": (ROWS_GAP, json.dumps({"row": "far_tower", "why": "no object of this row"})),
    "boxes by row": (BOXES_GAP, json.dumps({"row": "bunk", "result": "fail", "why": "judge: x"})),
    "a record by its path": (GAME, "scene-record output x/record/launch.json: 1 entries take their numbers from the "
                                   "game (source), 1 positions placed from it"),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_only_the_named_faults_move_and_any_other_still_stops_the_line(case):
    gap, other = CASES[case]
    named = failed(gap["check"], gap["faults"])
    kept = gaps.moved(named, [gap])
    assert kept.answer == checks.PASS and kept.findings == named.findings, kept
    assert kept.measures["moved"] == len(gap["faults"]) and gap["name"] in kept.reason
    both = failed(gap["check"], [*gap["faults"], other])
    assert gaps.moved(both, [gap]) == both


def test_the_decision_file_is_read_by_row_and_check_and_a_pass_or_unknown_is_left_alone():
    with decided({"wreck": [RESTING, ORDER]}):
        found = gaps.entries(recorded("wreck"), "assembly", "resting")
    assert found == [RESTING]
    unknown = checks.Verdict("resting", checks.UNKNOWN, "no drop run")
    assert gaps.moved(unknown, found) == unknown


def test_a_named_unknown_moves_and_another_unknown_stays():
    """The overseer, 2026-10-15: the likeness no props file answers moves; another unknown stays."""
    found = [entry("launch: no likeness output", "complete", "likeness", [], [], unknown="no accepted likeness@street")]
    assert gaps.moved(checks.Verdict("likeness", checks.UNKNOWN, "no accepted likeness@street"), found).answer \
        == checks.PASS
    other = checks.Verdict("likeness", checks.UNKNOWN, "2 generated rows and no accepted likeness@launch")
    assert gaps.moved(other, found) == other


def test_a_gap_is_an_input_of_complete_and_of_the_row_it_names_alone():
    """The overseer, 2026-10-15: a street's gaps (complete's alone) made the paid paint at three places run again."""
    likeness = entry("launch: no likeness output", "complete", "likeness", [], [], unknown="x")
    with decided({"street": [likeness], "lab": [entry("chairs", "assembly", "placeholders", ["chair_1"], [])]}):
        for row in ("assembly", "surfaces-check", "surfaces-paint"):
            assert gaps.NAME not in ROWS[row].files("street"), row
        assert gaps.NAME in ROWS["complete"].files("street")
        assert gaps.NAME in ROWS["assembly"].files("lab") and gaps.NAME not in ROWS["surfaces-paint"].files("lab")
        assert not gaps.files("nowhere") and not gaps.files("nowhere", "assembly")


def test_complete_fails_each_accepted_gap_by_name_with_its_numbers():
    crane = entry("crane: a foot off the floor", "complete", "resting", ["/campgrounds/Objects/crane_1"],
                  ["/campgrounds/Objects/crane_1: foot 2 3.2 cm off the floor"])
    with decided({"campgrounds": [crane]}):
        found = gaps.judge_accepted(None, recorded("campgrounds"), None)
    assert found.answer == checks.FAIL and "crane: a foot off the floor" in found.reason
    assert found.findings == ("crane: a foot off the floor: /campgrounds/Objects/crane_1: foot 2 3.2 cm off the floor",)
    assert gaps.judge_accepted(None, {}, None).answer == checks.PASS


def test_complete_lists_a_gap_a_row_it_reads_wrote_in_its_output(tmp_path):
    """The neighbours' far city (lost with the old disk, #10): its own gaps.json, listed by complete by name."""
    lost = {"name": "far_city: shown by the plan, not stood", "row": "neighbours", "check": "neighbours",
            "objects": ["/flat/Places/far_city"], "reason": "its seed went with the old disk",
            "decided": "lost input, 2026-10-19 (the old disk)", "faults": []}
    (tmp_path / gaps.WRITTEN).write_text(json.dumps({"gaps": [lost]}))
    found = gaps.judge_accepted(None, {"neighbours": tmp_path}, None)
    assert found.answer == checks.FAIL and "far_city: shown by the plan, not stood" in found.reason, found


def test_the_table_wires_the_gates_and_only_complete_hashes_the_gaps():
    assert graph.GAPPED == "accepted gaps" and graph.GAPPED in [check.name for check in ROWS["complete"].checks]
    for row, gate in (("assembly", "placeholders"), ("assembly", "resting"), ("surfaces-check", "stands level"),
                      ("surfaces-check", "baked matches its surfaces"),
                      ("surfaces-paint", "colour against the close-up"), ("complete", "people"),
                      ("complete", "likeness"), ("complete", "motion"), ("complete", "rows"), ("complete", "game"),
                      ("complete", "boxes")):
        check = next(check for check in ROWS[row].checks if check.name == gate)
        assert hasattr(check.judge, "__wrapped__"), (row, gate)
    hashing = {name for name in ("assembly", "surfaces-check", "surfaces-paint", "complete")
               if _code.REPO / "score/stages/gaps.py" in _code.source_files(graph.code_functions(ROWS[name]))}
    assert hashing == {"complete"}, hashing  # moving a verdict re-makes nothing, the paid paint above all


# --- a failed paid take is a gap carried down its line ---

OBJECTS = {"crate": {"route": "prop", "take": "crate-s1"},
           "hatch": {"route": "prop", "take": "hatch-s1", "rows": ["hatch"]}}


def written(folder, name, found):
    path = folder / name
    path.write_text(json.dumps(found))
    return path


def fake_batch(made):
    """subprocess.run as the Pixal3D batch would answer: only the takes in `made` come back (raw model and camera
    folder; the batch exits 0 and names the rest gaps), and the finish here writes each job's finished models."""
    def run(command, **options):
        pixal = pixal_row.take_files("any")[0].parent
        pixal.mkdir(parents=True, exist_ok=True)
        if command[1].endswith("batch.py"):
            for line in pathlib.Path(command[2]).read_text().splitlines():
                take = line.split()[0]
                if take in made:
                    (pixal / f"{take}.glb").write_text("raw")
                    (pixal / f"{take}.svviews").mkdir(exist_ok=True)
        else:  # every finish one blender_cloud.py call of job files, each bringing its outputs back (484e538e)
            for job in (json.loads(pathlib.Path(path).read_text()) for path in command[2:] if path.endswith(".json")):
                for output in job["outputs"]:
                    pathlib.Path(output).write_text("finished")
        return subprocess.CompletedProcess(command, 0, "", "")
    return run


def pixal_made(made):
    """A Pixal3D row's output from a batch that brought back `made` only, and its inputs."""
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "closeup" / "closeups").mkdir(parents=True)
    for row in OBJECTS:
        (folder / "closeup" / "closeups" / f"{row}.png").write_text("close-up")
    # the close-up row's record of the rows it worked on, which the takes gate narrows to (a8ebe414)
    written(folder / "closeup", "closeups.json", {"objects": {row: {"drawn_by": "drawn"} for row in OBJECTS}})
    entries = {row: {"faces": 1000} for row in OBJECTS}
    inputs = {"closeup": folder / "closeup",
              "props": written(folder, "props.json", {"place": "toy", "objects": OBJECTS}),
              "surfaces": written(folder, "surfaces.json", {
                  "place": "toy", "takes": {entry["take"]: {} for entry in OBJECTS.values()},
                  "bake": {"models": {row: entry["take"] for row, entry in OBJECTS.items()}, "entries": entries}}),
              # each object's reading row: its size says how its close-up was drawn (pixal_row.lies_flat)
              "inventory": written(folder, "inventory.json", {"rows": [{"id": row, "size": [0.6, 0.6, 0.6]}
                                                                       for row in OBJECTS]})}
    out = folder / "pixal"
    out.mkdir()
    running, pixal_row.subprocess.run = pixal_row.subprocess.run, fake_batch(made)
    try:
        pixal_row.make_pixal(inputs, out, 0, {})
    finally:
        pixal_row.subprocess.run = running
    return out, inputs


def test_a_take_the_batch_made_no_model_of_is_a_gap_its_gate_still_fails_and_the_table_moves():
    out, inputs = pixal_made({"crate-s1"})
    found = batch_gaps.read([out])
    assert [entry["name"] for entry in found] == ["hatch: Pixal3D made no model"], found
    assert set(found[0]["objects"]) == {"hatch", "hatch-s1"} and found[0]["row"] == "pixal"
    assert found[0]["decided"] == f"the batch run (pixal, output {out.name})"
    gate = next(check for check in ROWS["pixal"].checks if check.name == "takes")
    raw = gate.judge.__wrapped__(out, inputs, None)
    assert raw.answer == checks.FAIL and all(finding.startswith("hatch: ") for finding in raw.findings), raw
    moved = gate.judge(out, inputs, None)
    assert moved.answer == checks.PASS and moved.findings == raw.findings, moved
    assert "moved to complete as accepted gaps: hatch: Pixal3D made no model (the batch run" in moved.reason


def test_a_fault_no_batch_gap_names_still_fails_the_gate():
    out, inputs = pixal_made({"crate-s1"})
    (pixal_row.take_files("crate-s1")[1]).write_text("changed since it was made")
    gate = next(check for check in ROWS["pixal"].checks if check.name == "takes")
    assert gate.judge(out, inputs, None).answer == checks.FAIL


def test_the_views_leave_a_batch_gap_s_take_out_and_carry_its_gap():
    out, inputs = pixal_made({"crate-s1"})
    views = out.parent / "views"
    views.mkdir()
    route_views.make_views({"surfaces": inputs["surfaces"], "pixal": out}, views, 0, {})
    assert list(json.loads((views / "views.json").read_text())) == ["crate-s1"]
    assert [entry["name"] for entry in batch_gaps.read([views])] == ["hatch: Pixal3D made no model"]


def test_the_views_pass_with_their_gaps_carried_when_every_take_is_a_batch_gap():
    """finish-route-views@people, 2026-10-21: every take was left out by carried batch gaps, and the views gate
    failed it as "no take to work on", stopping the line the batch rule says runs on with its gaps."""
    for path in [path for entry in OBJECTS.values() for path in pixal_row.take_files(entry["take"])]:
        if path.is_dir():  # an earlier test's takes, under this sandbox's home
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    out, inputs = pixal_made(set())
    views = out.parent / "views"
    views.mkdir()
    route_views.make_views({"surfaces": inputs["surfaces"], "pixal": out}, views, 0, {})
    assert json.loads((views / "views.json").read_text()) == {}
    verdict = route_views.judge_views(views, {}, None)
    assert verdict.answer == checks.PASS and verdict.measures["left_out"] == 2, verdict
    assert "crate: Pixal3D made no model" in verdict.reason and "hatch: Pixal3D made no model" in verdict.reason
    assert {entry["name"] for entry in batch_gaps.read([views])} == {"crate: Pixal3D made no model",
                                                                     "hatch: Pixal3D made no model"}
    (views / batch_gaps.FILE).write_text(json.dumps({"gaps": []}))  # the same empty views with no gap still fail
    assert route_views.judge_views(views, {}, None).answer == checks.FAIL


# The fixture batch: the prop route's rows by their table names, each a toy make, wrapped by the table's own gap
# mover (stages.accepted_gaps) as the real rows are.
TOY = contracts.Contract("toy", 1, lambda folder: [])


def make_pixal(inputs, out, seed, params):
    """Two takes asked; the batch brought the crate back and not the hatch (its job failed: a gap), unless the brief
    says it lost the crate too and named no gap for it."""
    brief = inputs["brief"].read_text()
    (out / "takes.json").write_text(json.dumps({"crate": "lost" not in brief, "hatch": False}))
    batch_gaps.write(out, [batch_gaps.gap("hatch: Pixal3D made no model", "pixal", "takes", ("hatch", "hatch-s1"),
                                          ["hatch: no hatch-s1.glb"], "the Pixal3D job ran once and failed")])


def judge_takes(output, inputs, evidence):
    takes = json.loads((output / "takes.json").read_text())
    failing = [f"{row}: no {row}-s1.glb" for row, made in sorted(takes.items()) if not made]
    return checks.Verdict("takes", checks.FAIL if failing else checks.PASS, f"{len(failing)} takes not made",
                          {"faults": len(failing)}, {"faults": "lower"}, tuple(failing))


def make_carried(inputs, out, seed, params):
    """A row after the take: works on the made takes, the batch gaps' left out and carried on."""
    batch_gaps.write(out, batch_gaps.of(inputs))
    (out / "made.json").write_text(json.dumps(["crate"]))


def judge_cast(output, inputs, evidence):
    """The views judge only the takes they worked on (the real row's: a left-out take is not in its views.json)."""
    return checks.Verdict("views cast", checks.PASS, f"{len(json.loads((output / 'made.json').read_text()))} cast")


def judge_rows(name):
    """A gate that fails each object of the place's two with no made model by name (as likeness and complete do)."""
    def judge(output, inputs, evidence):
        made = json.loads((output / "made.json").read_text())
        failing = [f"{row}: no model" for row in ("crate", "hatch") if row not in made]
        return checks.Verdict(name, checks.FAIL if failing else checks.PASS, f"{len(failing)} not made",
                              {"faults": len(failing)}, {"faults": "lower"}, tuple(failing))
    return judge


def fixture_line(brief):
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "dock").mkdir()
    (data / "dock" / "brief.txt").write_text(brief)
    rows = (graph.Stage("pixal", "place", make_pixal, TOY, (checks.Check("takes", judge_takes),),
                        files={"brief": "{data}/{place}/brief.txt"}),
            graph.Stage("finish-route-views", "place", make_carried, TOY,
                        (checks.Check("views cast", judge_cast),), after={"pixal": ("toy", 1)}),
            graph.Stage("likeness", "place", make_carried, TOY, (checks.Check("outline", judge_rows("outline")),),
                        after={"finish-route-views": ("toy", 1)}),
            graph.Stage("complete", "place", make_carried, TOY, (checks.Check("rows", judge_rows("rows")),),
                        after={"likeness": ("toy", 1)}))
    world = graph.Environment("toy", 7, {"data": data})
    return graph.Runner(tuple(map(stages.accepted_gaps, rows)), world, Store.in_folder(tempfile.mkdtemp()),
                        model_record=lambda kind: {})


def test_a_failed_pixal_take_leaves_its_place_s_line_running_to_complete_apart_from_its_gaps():
    runner = fixture_line("the batch")
    found = runner.drive(["dock"], say=lambda line: None)
    for node in ("pixal@dock", "likeness@dock"):
        assert found[node] == "made: pass, accepted automatically", found
    assert found["complete@dock"].startswith("made: fail, accepted automatically"), found
    assert runner.status(["dock"])["complete@dock"] == "complete apart from accepted gaps (1), accepted"
    judgement = review.newest_judgement(runner.store, review.record_of(runner.store, "complete@dock"))
    listed = judgement["verdicts"][graph.GAPPED]
    assert "hatch: Pixal3D made no model (the Pixal3D job ran once and failed; the batch run (pixal, output" \
        in listed["reason"] and listed["findings"] == ["hatch: Pixal3D made no model: hatch: no hatch-s1.glb"]


def test_a_take_lost_with_no_batch_gap_still_stops_its_line():
    runner = fixture_line("the batch lost the crate")
    found = runner.drive(["dock"], say=lambda line: None)
    assert found["likeness@dock"] == "not run: its line stopped at pixal@dock", found


def painted(folder):
    """A surfaces-bake output whose take `crate-s1` has a finish off its close-up's colour and `hatch-s1` none, with
    the bake's entries (each take's models) and checks.json as the check's step writes it: `crate` over its budget."""
    baked = folder / "surfaces-bake"
    clean = {"unnamed_parts": 0, "unnamed_share": 0.0, "finishes": [], "feet": {}}
    off = dict(clean, finishes=[{"finish": "lid", "by": "off its colour", "measured_lab": [30.0, 0.0, 0.0],
                                 "surface": "panel", "delta_e": 40.0, "new_surface": {"name": "panel_dark"}}])
    (baked / "labelled" / "crate-s1").mkdir(parents=True)
    (baked / "entries").mkdir()
    written(baked, "painted.json", {"takes": {"crate-s1": off, "hatch-s1": clean}, "left_out": {}})
    written(baked / "entries", "crate-s1.json", {"crate": {}})
    written(baked / "entries", "hatch-s1.json", {"hatch": {}})
    record = {"missing_maps": [], "surfaces": {}, "triangles": 100, "budget": 1000, "stands": False}
    return baked, {"crate": dict(record, triangles=5000), "hatch": record}


def test_a_take_the_paint_or_check_fails_is_a_gap_and_the_table_moves_its_fault_alone():
    from score.stages.surfaces import route_check
    folder = pathlib.Path(tempfile.mkdtemp())
    try:
        baked, records = painted(folder)
        inputs = {"surfaces-bake": baked}
        paint = folder / "paint"
        paint.mkdir()
        ROWS["surfaces-paint"].make(inputs, paint, 0, {})
        found = batch_gaps.read([paint])
        assert [entry["name"] for entry in found] == ["crate-s1: colour against the close-up"], found
        gate = next(check for check in ROWS["surfaces-paint"].checks if check.name == "colour against the close-up")
        assert gate.judge.__wrapped__(paint, inputs, None).answer == checks.FAIL
        moved = gate.judge(paint, inputs, None)
        assert moved.answer == checks.PASS and "moved to complete" in moved.reason, moved
        # the check: its step faked to write checks.json; the model over its budget is a gap of it and its take
        handover = route_check.prop_env.handover
        route_check.prop_env.handover = lambda module, step, given, out: written(out, "checks.json", records)
        check = folder / "check"
        check.mkdir()
        try:
            route_check.make_check({**inputs, "surfaces-paint": paint}, check, 0, {})
        finally:
            route_check.prop_env.handover = handover
        names = {entry["name"]: entry for entry in batch_gaps.read([check])}
        assert set(names) == {"crate-s1: colour against the close-up", "crate: triangles within budget"}, names
        assert set(names["crate: triangles within budget"]["objects"]) == {"crate", "crate-s1"}
        gate = next(check for check in ROWS["surfaces-check"].checks if check.name == "triangles within budget")
        assert gate.judge(check, {**inputs, "surfaces-paint": paint}, None).answer == checks.PASS
        # a fault no gap names still stops: the clean model over its budget too
        written(check, "checks.json", {**records, "hatch": dict(records["hatch"], triangles=5000)})
        assert gate.judge(check, {**inputs, "surfaces-paint": paint}, None).answer == checks.FAIL
    finally:
        shutil.rmtree(folder)


def test_a_clean_paint_writes_no_gaps_file():
    folder = pathlib.Path(tempfile.mkdtemp())
    try:
        baked, _ = painted(folder)
        written(baked, "painted.json", {"takes": {"hatch-s1": {"unnamed_parts": 0, "unnamed_share": 0.0,
                                                               "finishes": [], "feet": {}}}, "left_out": {}})
        paint = folder / "paint"
        paint.mkdir()
        ROWS["surfaces-paint"].make({"surfaces-bake": baked}, paint, 0, {})
        assert not (paint / batch_gaps.FILE).exists()
    finally:
        shutil.rmtree(folder)


# --- push gate names the paid rows it moves ---

def test_a_file_moved_into_framework_and_edited_in_the_same_change_is_named():
    """A module moved into FRAMEWORK and edited in the same change makes the rows that read it again (no narrowing
    carry): it is named, a plain move is not."""
    repo = pathlib.Path(tempfile.mkdtemp(prefix="moved_repo_")).resolve()
    (repo / "score" / "graph").mkdir(parents=True)
    declared = repo / "score" / "graph" / "_code.py"

    def commit(framework, helpers):
        declared.write_text(f"FRAMEWORK = {{REPO / name for name in {framework!r}}}\n")
        for name, text in helpers.items():
            (repo / name).write_text(text)
        for command in (["add", "."], ["-c", "user.name=test", "-c", "user.email=test@test", "commit", "-qm", "step"],
                        ["rev-parse", "HEAD"]):
            done = subprocess.run(["git", "-C", str(repo), *command], check=True, capture_output=True, text=True)
        return done.stdout.strip()

    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    saved = _code.REPO
    _code.REPO = repo
    try:
        first = commit((), {"plain.py": "A = 1\n", "edited.py": "B = 1\n"})
        second = commit(("plain.py", "edited.py"), {"edited.py": "B = 2\n"})
        assert moved.edited_into_framework(first, second) == ["edited.py"]
    finally:
        _code.REPO = saved


TEXT = contracts.Contract("toy-text", 1, lambda folder: [])


RENDER_MAKE = """import toy_frame


def make(inputs, out, seed, params):
    (out / "text.txt").write_text(toy_frame.WORD + inputs["brief"].read_text())
"""


def make_copy(inputs, out, seed, params):
    (out / "text.txt").write_text(inputs["brief"].read_text())


def make_film(inputs, out, seed, params):
    (out / "text.txt").write_text((inputs["draw"] / "text.txt").read_text())


def judge_said(output, inputs, evidence):
    return checks.Verdict("said", checks.PASS, "a text was written")


SAID = (checks.Check("said", judge_said),)


def git(repo, *words):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=toy", "-c", "user.email=toy@example.com",
                           *words], capture_output=True, text=True, check=True).stdout.strip()


def committed(repo, message="toy"):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def command():
    from score import __main__
    return __main__


@contextlib.contextmanager
def toy():
    """A git repository standing in for this one (the render's make, a framework file it imports, three data files)
    for the time of a `with`; the framework's globals and the command's hooks are put back afterwards."""
    main = command()
    kept = (_code.REPO, _code.FRAMEWORK, moved.REPO, list(sys.path), compute.books_refusal,
            main.every_world_moved, moved.base_rebuys)
    repo = pathlib.Path(tempfile.mkdtemp()).resolve()
    git(repo, "init", "-q")
    (repo / "toy_render.py").write_text(RENDER_MAKE)
    (repo / "toy_frame.py").write_text('WORD = "made: "\n')
    (repo / ".gitignore").write_text("__pycache__/\n")  # an import's bytecode is no change to the tree
    (repo / "render.txt").write_text("a hall")
    (repo / "bake.txt").write_text("a hall's light")
    (repo / "draw.txt").write_text("a hall's plan")
    committed(repo)
    _code.REPO = moved.REPO = repo
    _code.FRAMEWORK = _code.FRAMEWORK | {repo / "toy_frame.py"}
    compute.books_refusal = lambda: None  # the month's books are compute_test's; not this one's
    sys.path.insert(0, str(repo))
    _code.search_folders.cache_clear()
    sys.modules.pop("toy_render", None)
    sys.modules.pop("toy_frame", None)
    try:
        yield repo
    finally:
        (_code.REPO, _code.FRAMEWORK, moved.REPO, sys.path[:], compute.books_refusal,
         main.every_world_moved, moved.base_rebuys) = kept
        _code.search_folders.cache_clear()


def a_runner(repo, store, bake_params=None):
    render = graph.Stage("render", "place", importlib.import_module("toy_render").make, TEXT, SAID,
                         files={"brief": "{data}/render.txt"}, paid=True, euros=4.0)
    bake = graph.Stage("bake", "place", make_copy, TEXT, SAID, files={"brief": "{data}/bake.txt"}, paid=True,
                       euros=3.0, params=bake_params or {})
    draw = graph.Stage("draw", "place", make_copy, TEXT, SAID, files={"brief": "{data}/draw.txt"})
    film = graph.Stage("film", "place", make_film, TEXT, SAID, after={"draw": ("toy-text", 1)}, paid=True, euros=2.0)
    return graph.Runner([render, bake, draw, film], graph.Environment("toy", 1, {"data": repo}), store,
                        model_record=lambda kind: {"kind": kind})


def made(repo):
    """Every row made and accepted at the toy repository's commit; their store."""
    store = Store.in_folder(tempfile.mkdtemp())
    runner = a_runner(repo, store)
    for stage in runner.stages.values():
        assert "accepted automatically" in runner.run_node(stage, "hangar"), stage.name
    return store


def rows(repo, store, **table):
    runner = a_runner(repo, store, **table)
    return {"toy": moved.rebuys(runner, list(runner.nodes(["hangar"])))}


def nodes(rows_by_world):
    """{world: [node]}: what base_rebuys gives for a commit."""
    return {world: [row.node for row in found] for world, found in rows_by_world.items()}


def exit_code(call, *args):
    """What `call` printed and its exit code (0 when it returned)."""
    with contextlib.redirect_stdout(io.StringIO()) as printed, contextlib.redirect_stderr(io.StringIO()) as said:
        try:
            call(*args)
        except SystemExit as stop:  # sys.exit("message") prints its message and exits 1
            message = stop.code if isinstance(stop.code, str) else ""
            return printed.getvalue() + said.getvalue() + message, 1 if message else stop.code
    return printed.getvalue() + said.getvalue(), 0


def pushed(repo, message, files):
    """Commit `files` ({name: text}) over the toy repository's tip; (the git push line to main, tip)."""
    base = git(repo, "rev-parse", "HEAD")
    for name, text in files.items():
        (repo / name).write_text(text)
    tip = committed(repo, message)
    return f"refs/heads/main {tip} refs/heads/main {base}", tip


def test_nothing_changed_lists_nothing_and_passes():
    with toy() as repo:
        found = rows(repo, made(repo))
        assert found == {"toy": []} and exit_code(command().moved_check, found)[1] == 0


def test_a_file_read_by_one_paid_row_lists_that_row_with_its_price_and_why():
    with toy() as repo:
        store = made(repo)
        (repo / "bake.txt").write_text("a hall's brighter light")
        found = rows(repo, store)
        assert [(row.node, row.euros, row.why) for row in found["toy"]] == [("bake@hangar", 3.0, "brief changed")]
        printed, code = exit_code(command().moved_check, found)
        assert code == moved.MOVED_EXIT and "toy bake@hangar: EUR 3.00, brief changed" in printed
        assert "about EUR 3.00" in printed


def test_a_framework_only_edit_lists_nothing():
    with toy() as repo:
        store = made(repo)
        (repo / "toy_frame.py").write_text('WORD = "made by the framework: "\n')
        assert rows(repo, store) == {"toy": []}


def test_a_row_moved_through_what_it_reads_is_listed():
    with toy() as repo:
        store = made(repo)
        (repo / "draw.txt").write_text("a hall's new plan")
        found = rows(repo, store)
        assert [(row.node, row.euros, row.why) for row in found["toy"]] == [("film@hangar", 2.0, "reads draw@hangar")]


def test_only_pushes_to_main_are_checked():
    tip, base = "a" * 40, "b" * 40
    lines = [f"refs/heads/main {moved.ZERO} refs/heads/main {base}",  # a deletion
             f"refs/tags/v1 {tip} refs/tags/v1 {moved.ZERO}",
             f"refs/heads/side {tip} refs/heads/side {base}"]
    assert moved.main_pushes(lines) == []
    printed, code = exit_code(command().pre_push_check, lines)
    assert code == 0 and "nothing pushed to main" in printed
    assert moved.main_pushes(lines + [f"HEAD {tip} refs/heads/main {base}"]) == [(tip, base)]


def test_a_push_is_refused_only_for_the_rows_it_moves_and_drift_is_a_warning():
    with toy() as repo:
        store = made(repo)
        (repo / "toy_render.py").write_text(RENDER_MAKE + "\n# moved before this push\n")
        committed(repo, "render: already on main")
        base = nodes(rows(repo, store))
        pushed(repo, "data: a brighter hall", {"bake.txt": "a hall's brighter light"})
        found = rows(repo, store)
        assert base == {"toy": ["render@hangar"]} and [row.node for row in found["toy"]] == ["render@hangar",
                                                                                              "bake@hangar"]
        printed, code = exit_code(command().pushed_check, found, base, [])
        assert code == moved.MOVED_EXIT
        assert "warning, not refused" in printed and "toy render@hangar: EUR 4.00, code changed" in printed
        assert "Moved-rows: bake@hangar: <why>" in printed and "render@hangar: <why>" not in printed
        assert "EUR 0" in printed  # the refusal says a cached Google ask is never refused


def test_drift_alone_lets_the_push_go():
    with toy() as repo:
        store = made(repo)
        (repo / "toy_render.py").write_text(RENDER_MAKE + "\n# moved before this push\n")
        committed(repo, "render: already on main")
        base = nodes(rows(repo, store))
        pushed(repo, "notes", {"notes.txt": "nothing a row reads"})
        printed, code = exit_code(command().pushed_check, rows(repo, store), base, [])
        assert code == 0 and "warning, not refused" in printed


def test_a_move_no_file_explains_is_refused():
    """A stage table edit (a row's params here; a contract, a model or an after alike) moves the row with no file of
    its own changed: refused like any other, never a warning."""
    with toy() as repo:
        store = made(repo)
        base = nodes(rows(repo, store))
        found = rows(repo, store, bake_params={"light": 2})
        assert [(row.node, row.why) for row in found["toy"]] == [("bake@hangar", "params changed")]
        printed, code = exit_code(command().pushed_check, found, base, [])
        assert code == moved.MOVED_EXIT and "Moved-rows: bake@hangar: <why>" in printed
        assert "warning, not refused" not in printed


def test_when_mains_commit_cannot_be_worked_out_every_moved_row_counts_as_the_pushes():
    with toy() as repo:
        store = made(repo)
        (repo / "bake.txt").write_text("a hall's brighter light")
        printed, code = exit_code(command().pushed_check, rows(repo, store), None, [])
        assert code == moved.MOVED_EXIT and "Moved-rows: bake@hangar: <why>" in printed
        assert "could not be worked out" in printed


def test_base_rebuys_is_none_for_a_new_ref_an_unknown_commit_or_a_failing_tree_and_leaves_nothing_behind():
    with toy() as repo:
        left = set(repo.parent.glob("moved-*"))
        assert moved.base_rebuys(moved.ZERO) is None
        assert moved.base_rebuys("f" * 40) is None  # no such commit here
        assert moved.base_rebuys(git(repo, "rev-parse", "HEAD")) is None  # the toy has no score package to run
        assert set(repo.parent.glob("moved-*")) == left
        assert len(git(repo, "worktree", "list").splitlines()) == 1


def test_a_trailer_lets_only_the_rows_it_names_go():
    with toy() as repo:
        store = made(repo)
        base = nodes(rows(repo, store))
        line, tip = pushed(repo, "data: a brighter hall and a new plan\n\nMoved-rows: bake@hangar: the owner asked",
                           {"bake.txt": "a hall's brighter light", "draw.txt": "a hall's new plan"})
        found = rows(repo, store)
        pushes = moved.main_pushes([line])
        reasons = moved.pushed_reasons(pushes)
        assert reasons == ["bake@hangar: the owner asked"]
        printed, code = exit_code(command().pushed_check, found, base, reasons)
        assert code == moved.MOVED_EXIT and "Moved-rows: film@hangar: <why>" in printed
        assert moved.pushed_reasons([(tip, moved.ZERO)]) == reasons  # a new remote ref: commits on no remote yet
        assert not moved.named_in("bake@hangar", ["x"]) and not moved.named_in("bake@hang", reasons)
        printed, code = exit_code(command().pushed_check, found, base, reasons + ["film@hangar: a new plan"])
        assert code == 0 and "Moved-rows: bake@hangar: the owner asked" in printed


def test_a_trailer_names_a_row_only_among_its_nodes_and_with_a_reason():
    """"Moved-rows: <node> ...: <reason>": a node with no reason, or one only in another row's reason, is not named."""
    assert moved.named_in("bake@hangar", ["bake@hangar film@hangar: the owner asked"])
    assert moved.named_in("film@hangar", ["bake@hangar, film@hangar: the owner asked"])
    assert not moved.named_in("bake@hangar", ["bake@hangar"])
    assert not moved.named_in("bake@hangar", ["bake@hangar:  "])
    assert not moved.named_in("bake@hangar", ["film@hangar: it reads bake@hangar"])


def test_pre_push_checks_the_pushed_commit_against_mains_not_a_changed_tree():
    with toy() as repo:
        store = made(repo)
        line, tip = pushed(repo, "data: a brighter hall", {"bake.txt": "a hall's brighter light"})
        main = command()
        worked_out, bases = [], []
        main.every_world_moved = lambda: worked_out.append(1) or rows(repo, store)
        moved.base_rebuys = lambda remote: bases.append(remote) or {"toy": []}
        (repo / "draw.txt").write_text("not committed")
        printed, code = exit_code(main.pre_push_check, [line])
        assert code != 0 and "clean checkout" in printed and worked_out == []
        git(repo, "checkout", "--", "draw.txt")
        printed, code = exit_code(main.pre_push_check, [line])
        assert code == moved.MOVED_EXIT and "Moved-rows: bake@hangar: <why>" in printed
        assert worked_out == [1] and bases == [line.split()[3]]


def test_a_framework_only_push_is_still_checked():
    """The stage table is a framework file left out of every code version, yet it sets every row's params, contract,
    models and after: a push of it alone is worked out like any other."""
    with toy() as repo:
        store = made(repo)
        line, _ = pushed(repo, "framework", {"toy_frame.py": 'WORD = "made by the framework: "\n'})
        main = command()
        worked_out = []
        main.every_world_moved = lambda: worked_out.append(1) or rows(repo, store, bake_params={"light": 2})
        moved.base_rebuys = lambda remote: {"toy": []}
        printed, code = exit_code(main.pre_push_check, [line])
        assert worked_out == [1] and code == moved.MOVED_EXIT and "Moved-rows: bake@hangar: <why>" in printed


HOOK = REPO / ".githooks/pre-push-moved"


RECORDER = """import json, os, pathlib, sys
pathlib.Path(os.environ["HOOK_RECORD"]).write_text(json.dumps({"cwd": os.getcwd(), "argv": sys.argv[1:],
    "stdin": sys.stdin.read(), "python": sys.executable}))
sys.exit(int(os.environ.get("HOOK_EXIT", "0")))  # stands in for: score moved --pre-push
"""


STALLED = """import os, pathlib, sys
del sys.modules["score"]  # this toy package: the real score command is loaded in its place
sys.path.insert(0, os.environ["SCORE_REPO"])
from score import __main__ as real
from score.stages import moved
moved.REPO = pathlib.Path.cwd()
sleeper = "import os, pathlib, time; pathlib.Path(%r).write_text(str(os.getpid())); time.sleep(600)"
real.every_world_moved = lambda: moved.snapshot("HEAD", sleeper % os.environ["HOOK_RECORD"])
real.main(["moved", "--pre-push"])  # never --pre-push --again
"""


def hook_repo(command_text=RECORDER):
    """A toy repository whose score package records how the hook ran it (or runs `command_text`), with its own .venv
    python; it sits alone in a folder of its own, where moved.snapshot puts its checkouts."""
    repo = pathlib.Path(tempfile.mkdtemp()).resolve() / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "score").mkdir()
    (repo / "score/__init__.py").write_text("")
    (repo / "score/__main__.py").write_text(command_text)
    (repo / ".gitignore").write_text(".venv/\n__pycache__/\n")
    (repo / ".venv/bin").mkdir(parents=True)
    (repo / ".venv/bin/python").symlink_to(sys.executable)
    committed(repo)
    return repo


def hook(where, push_lines, exit_with=0, temp=None, env=None):
    """Run .githooks/pre-push-moved in `where` (with `env` added to its environment); (its exit code, its output, the
    recorder's record or None)."""
    record = pathlib.Path(tempfile.mkdtemp()) / "record.json"
    ran = subprocess.run(["bash", str(HOOK), "origin", "toy"], cwd=where, input="\n".join(push_lines) + "\n",
                         capture_output=True, text=True,
                         env={**os.environ, "HOOK_RECORD": str(record), "HOOK_EXIT": str(exit_with),
                              **({"TMPDIR": str(temp)} if temp else {}), **(env or {})})
    return ran.returncode, ran.stdout + ran.stderr, json.loads(record.read_text()) if record.exists() else None


def test_the_hook_is_off_until_the_owner_turns_it_on():
    repo = hook_repo()
    tip = git(repo, "rev-parse", "HEAD")
    line = f"refs/heads/main {tip} refs/heads/main {moved.ZERO}"
    assert hook(repo, [line]) == (0, "", None)
    git(repo, "config", "score.movedCheck", "true")
    code, _, record = hook(repo, [line])
    assert code == 0 and record["cwd"] == str(repo) and record["argv"] == ["moved", "--pre-push"]
    assert record["stdin"] == line + "\n"
    assert hook(repo, [line], exit_with=3)[0] == 3


def test_the_hook_passes_deletions_tags_and_other_branches_at_once():
    repo = hook_repo()
    git(repo, "config", "score.movedCheck", "true")
    tip = git(repo, "rev-parse", "HEAD")
    for line in (f"(delete) {moved.ZERO} refs/heads/main {tip}", f"refs/tags/v1 {tip} refs/tags/v1 {moved.ZERO}",
                 f"refs/heads/side {tip} refs/heads/side {moved.ZERO}"):
        assert hook(repo, [line], exit_with=3) == (0, "", None), line


def test_the_hook_checks_a_changed_tree_in_a_worktree_of_the_pushed_commit():
    repo = hook_repo()
    git(repo, "config", "score.movedCheck", "true")
    tip = git(repo, "rev-parse", "HEAD")
    (repo / "loose.txt").write_text("not committed")
    code, _, record = hook(repo, [f"refs/heads/main {tip} refs/heads/main {moved.ZERO}"])
    assert code == 0 and record["cwd"] != str(repo)
    assert not pathlib.Path(record["cwd"]).exists()  # removed afterwards
    assert len(git(repo, "worktree", "list").splitlines()) == 1


def test_the_hook_refuses_and_leaves_nothing_when_no_worktree_can_be_made():
    repo = hook_repo()
    git(repo, "config", "score.movedCheck", "true")
    temp = pathlib.Path(tempfile.mkdtemp())
    code, printed, record = hook(repo, [f"refs/heads/main {'f' * 40} refs/heads/main {moved.ZERO}"], temp=temp)
    assert code != 0 and record is None and "refused" in printed
    assert list(temp.iterdir()) == [] and len(git(repo, "worktree", "list").splitlines()) == 1


def test_the_hook_skips_a_commit_made_before_score_moved():
    repo = hook_repo()
    git(repo, "config", "score.movedCheck", "true")
    (repo / "score/__main__.py").write_text(RECORDER.replace("score moved --pre-push", "an older command"))
    tip = committed(repo, "before score moved")
    code, printed, record = hook(repo, [f"refs/heads/main {tip} refs/heads/main {moved.ZERO}"])
    assert code == 0 and "predates score moved" in printed and record is None


def gone(pid):
    """True once process `pid` has ended (waited for up to 10 s)."""
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.1)
    return False


def test_a_hook_that_runs_out_of_time_leaves_no_process_or_checkout_behind():
    """score.movedTimeout ends the check with SIGTERM while it works out a commit in a checkout of its own: the child
    it started ends and the checkout is removed, its folder and git's record of it alike (review, 2026-10-17: SIGTERM
    killed the Python before its `finally` ran, leaving 10 to 12 moved-* worktrees)."""
    repo = hook_repo(STALLED)
    python = repo / ".venv/bin/python"  # this environment's own python (a bare link to it would leave the venv)
    python.unlink()
    python.write_text(f'#!/usr/bin/env bash\nexec {sys.executable} "$@"\n')
    python.chmod(0o755)
    git(repo, "config", "score.movedCheck", "true")
    git(repo, "config", "score.movedTimeout", "15")
    tip = git(repo, "rev-parse", "HEAD")
    code, printed, sleeper = hook(repo, [f"refs/heads/main {tip} refs/heads/main {moved.ZERO}"],
                                  env={"SCORE_REPO": str(REPO)})  # the sleeper's record is its pid
    assert code != 0 and "ran past 15 s" in printed and isinstance(sleeper, int), printed
    assert gone(sleeper)
    assert sorted(path.name for path in repo.parent.iterdir()) == ["repo"]
    assert len(git(repo, "worktree", "list", "--porcelain").split("worktree ")) == 2


def test_the_hook_gives_the_check_an_hour_unless_told_otherwise():
    """Two commits worked out, every world each, took past 15 minutes under load (review, 2026-10-17): the default
    must not refuse every push to main."""
    repo = hook_repo()
    git(repo, "config", "score.movedCheck", "true")
    shim = pathlib.Path(tempfile.mkdtemp())
    (shim / "timeout").write_text(f'#!/usr/bin/env bash\necho "$1" > "$TIMEOUT_RECORD"\n'
                                  f'exec {shutil.which("timeout")} "$@"\n')
    (shim / "timeout").chmod(0o755)
    limit = shim / "limit.txt"
    tip = git(repo, "rev-parse", "HEAD")
    code, _, _ = hook(repo, [f"refs/heads/main {tip} refs/heads/main {moved.ZERO}"],
                      env={"PATH": f"{shim}:{os.environ['PATH']}", "TIMEOUT_RECORD": str(limit)})
    assert code == 0 and limit.read_text().strip() == "3600"


def test_a_worktree_hook_uses_the_main_checkouts_python():
    repo = hook_repo()
    git(repo, "config", "score.movedCheck", "true")
    tree = pathlib.Path(tempfile.mkdtemp()).resolve() / "tree"
    git(repo, "worktree", "add", "-q", "--detach", str(tree))
    tip = git(tree, "rev-parse", "HEAD")
    code, _, record = hook(tree, [f"refs/heads/main {tip} refs/heads/main {moved.ZERO}"])
    assert code == 0 and record["cwd"] == str(tree) and record["python"] == str(repo / ".venv/bin/python")
    shutil.rmtree(tree)
