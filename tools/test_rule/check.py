"""The guard on the test rule (docs/bible.md workflow/module-standard; owner, 2026-10-26: "only 1 but one actual good
meaning full test file per module ... i feel like that rule kinda drifted by now"): it lists every way the repository's
test files break the rule, so the rule cannot drift again. `make tests` runs it and fails on any fault.

    python3 tools/test_rule/check.py                 # every module in the repository
    python3 tools/test_rule/check.py <test file> ... # only the modules those files belong to (make tests TESTS="...")

A test file is a file named `test_*.py` or `*_test.py`, tracked or new (not ignored), outside `vendor/`. Its faults:

- **named for its module, not its invariant**: every test file is `test_<invariant>.py`.
- **no break**: its module docstring has no line naming the break that turns it red ("break" and "red" in one statement,
  at most 200 characters apart, as "Breaks (each applied once, seen red, reverted), in ...:").
- **more than one test function in a file** (owner, 2026-11-01): a test file holds ONE `test_*` function (a method of
  a `Test*` class counts); parametrized cases of one check are one function. A docstring line starting `second test:`
  with a reason excuses it. `FUNCTION_DEBT` holds the files over it that day with their count: one may not grow, one
  that shrank must lower its entry, one down to one test (or gone) must lose it.
- **more than one test file in a module**: a module is the directory its test file sits in, a `tests/` folder counting
  as its parent's (`.claude/hooks/tests` is `.claude/hooks`). In a flat folder of independent tools (`FLAT_TOOL_FOLDERS`)
  a top-level test file belongs to the tool script its docstring names first (as `tools/<folder>/<tool>.py`, else as
  `<tool>.py`, else as the bare name), and one that names none is a fault of its own.

`ALLOWLIST` holds the modules other agents' sweeps are still reworking, dated; each sweep empties its own entries, and
nothing else goes in it. The output is one summary line, then one line a fault.
"""
import ast
import fnmatch
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]

# Folders of independent command-line tools: each top-level tool script is a module of its own.
FLAT_TOOL_FOLDERS = ("tools/cloud", "tools/props", "tools/review", "tools/usd")

# Modules still being swept by other agents on 2026-10-26: skipped until their sweep empties the entry.
ALLOWLIST_DATE = "2026-10-26"
ALLOWLIST = (
    "tools/usd/*",
    "score/stages/complete/*",
    "score/stages/closeup/*",
    "score/stages/props/*",
    "score/stages/settling/*",
    "score/stages/physics/*",
    "*prepare*",
)

# Test files holding more than one test function on 2026-11-01 (118 files, 2139 functions over one), each
# with its count that day; only ever shrinks.
FUNCTION_DEBT_DATE = "2026-11-01"
FUNCTION_DEBT = {
    ".claude/hooks/tests/test_hooks_block_only_their_rule_and_fail_open.py": 31,
    ".claude/scripts/tests/test_scripts_touch_only_what_they_own.py": 20,
    "paper/build/test_paper_build_matches_its_source.py": 2,
    "score/adapters/compute/test_paid_work_starts_only_inside_its_clearance.py": 47,
    "score/adapters/engines/test_blender_runs_pinned_and_only_once_cleared.py": 2,
    "score/adapters/models/test_a_node_is_keyed_only_on_pinned_models.py": 7,
    "score/adapters/vendored/test_every_vendored_tool_is_accounted_for.py": 5,
    "score/checks/test_nothing_unproven_passes.py": 10,
    "score/conductor/test_the_conductor_spends_and_stops_only_as_its_owner_says.py": 38,
    "score/contracts/test_nothing_off_contract_passes.py": 7,
    "score/dashboard/auth/test_only_the_proxy_or_the_owner_signs_in.py": 7,
    "score/dashboard/checkout/test_a_batch_buys_only_what_the_owner_approved.py": 37,
    "score/dashboard/films/test_a_film_is_timed_checked_and_priced_from_its_script.py": 27,
    "score/dashboard/previews/test_every_step_card_has_a_picture.py": 19,
    "score/dashboard/proposals/test_a_basket_shows_what_a_run_on_main_would_buy.py": 20,
    "score/dashboard/state/test_the_cockpit_shows_the_store_as_read.py": 21,
    "score/dashboard/sync/test_the_cockpit_gets_the_store_whole_and_the_store_only_the_owners_asks.py": 56,
    "score/dashboard/tests/test_cockpit_is_the_owners_true_view.py": 115,
    "score/dashboard/web3d/test_a_web_copy_is_made_from_the_standing_accept.py": 7,
    "score/graph/test_a_key_is_made_once_from_accepted_inputs.py": 115,
    "score/library/test_read_only_at_known_schema.py": 4,
    "score/review/holders/test_each_plan_item_names_what_holds_it.py": 24,
    "score/review/relation_solver/test_a_crowded_plan_is_parted_inside_its_walls_the_same_way_every_run.py": 2,
    "score/review/test_the_owners_word_stands.py": 144,
    "score/stages/animals/test_animal_rows_follow_the_design.py": 3,
    "score/stages/assembly/test_a_place_stands_from_its_accepted_outputs.py": 54,
    "score/stages/cast/test_people_stand_clear_or_are_named.py": 20,
    "score/stages/crops/test_crops_grow_as_the_concept_grows_them.py": 13,
    "score/stages/demo_film/test_a_film_shows_its_locked_script_within_its_forecast.py": 32,
    "score/stages/earth_seed/test_a_scene_s_base_stands_from_its_design.py": 19,
    "score/stages/effects/test_effects_ride_their_design.py": 6,
    "score/stages/images/test_image_proofs_pass_only_a_proof_that_did_its_jobs.py": 6,
    "score/stages/library/test_everything_handed_to_library.py": 25,
    "score/stages/light/test_light_measured_against_design.py": 41,
    "score/stages/motion/test_a_thing_moves_as_its_design_says.py": 18,
    "score/stages/people/test_looks_dressed_from_the_library_and_judged_by_measure.py": 36,
    "score/stages/people_cloth/test_loose_cloth_rides_its_sim_body_and_is_judged_by_measure.py": 8,
    "score/stages/rough_model/test_a_rough_model_is_bought_once_from_its_concept.py": 11,
    "score/stages/scene_clips/test_a_walk_becomes_constraints_on_its_own_ground.py": 11,
    "score/stages/scene_record/test_a_scene_record_is_written_from_its_design.py": 22,
    "score/stages/shapes_first/test_every_model_goes_through_the_loop.py": 14,
    "score/stages/shell_split/test_a_shell_splits_into_places_that_tile_and_are_reached.py": 14,
    "score/stages/sim_body/inside/evaluation/test_every_evaluation_runs_every_tuning_body_and_the_check_never_chooses.py": 9,
    "score/stages/sim_body/inside/tuning/_adjoint/test_implicit_columns_equal_re_solved_differences.py": 27,
    "score/stages/sim_body/inside/tuning/_paired/test_a_step_counts_only_past_its_noise_floor_on_a_fixed_case_set.py": 6,
    "score/stages/sim_body/inside/tuning/test_one_optimisation_moves_every_unknown_together_within_its_bounds.py": 17,
    "score/stages/sim_body/test_a_body_doing_its_clip_stands_on_its_ground_within_its_residual.py": 9,
    "score/stages/sound/test_a_place_is_heard_as_its_design_says.py": 24,
    "score/stages/surface_tiles/test_shell_tiles.py": 4,
    "score/stages/surfaces/test_every_part_takes_a_library_surface_and_is_held_to_it.py": 116,
    "score/stages/terrain/test_ground_follows_design.py": 10,
    "score/stages/test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps.py": 94,
    "score/stages/video_clips/test_a_row_per_upload_and_gates_refuse_flips.py": 2,
    "score/store/backup/test_a_backup_brings_the_home_back_whole.py": 18,
    "score/store/restore/test_the_restore_spends_nothing_and_accepts_nothing_old_by_hand.py": 21,
    "score/store/test_an_output_is_kept_whole_once_and_never_overwritten.py": 17,
    "tools/blender/inside/test_ink_at_edges_and_each_prim_its_own.py": 5,
    "tools/blender/test_blender_stays_off_the_owners_screen.py": 7,
    "tools/characters/animals/test_rig_follows_the_body.py": 9,
    "tools/characters/clips/test_motion_lands_on_the_rigs_rest.py": 6,
    "tools/characters/maker/test_made_as_asked_and_bound_to_its_limbs.py": 59,
    "tools/characters/people/test_body_pieces_hold_together.py": 16,
    "tools/characters/played/test_a_clip_played_on_a_build_stands_its_feet_where_its_bind_does.py": 4,
    "tools/characters/test_characters_play_as_their_file_and_cast_say.py": 11,
    "tools/cloud/backends/test_own_resources_and_their_cost.py": 33,
    "tools/cloud/conductor/size_function/test_never_powered_off_under_work.py": 7,
    "tools/cloud/conductor/test_owner_gates_and_safe_moves.py": 32,
    "tools/cloud/images/test_built_once_and_every_machine_deleted.py": 6,
    "tools/cloud/k8s/clusters/test_own_cluster_capped_and_ledgered.py": 6,
    "tools/cloud/k8s/test_jobs_take_their_classes_in_order.py": 13,
    "tools/cloud/runtime/test_a_job_runs_once_on_checked_weights.py": 15,
    "tools/cloud/test_batch_pays_once_inside_its_limits_and_leaves_no_machine.py": 38,
    "tools/cloud/test_blender_cloud_runs_a_job_as_written.py": 14,
    "tools/cloud/test_books_unknown_refuse_every_paid_point.py": 16,
    "tools/cloud/test_box_masks_stop_when_no_masks_came_back.py": 3,
    "tools/cloud/test_capacity_rents_the_cheapest_fitting_card_within_the_caps.py": 14,
    "tools/cloud/test_delight_makes_each_unlit_copy_once.py": 3,
    "tools/cloud/test_detached_logs_everything_and_says_one_line.py": 3,
    "tools/cloud/test_gemini_judge_answers_with_a_code_or_no_verdict.py": 5,
    "tools/cloud/test_google_batch_sends_each_request_once.py": 7,
    "tools/cloud/test_google_spend_ledgers_every_call_before_it_is_sent.py": 10,
    "tools/cloud/test_inputs_arrive_intact_and_go_up_once.py": 10,
    "tools/cloud/test_judge_asks_each_question_once_on_a_card_that_holds_it.py": 3,
    "tools/cloud/test_kept_rerun_pays_only_for_missing_jobs.py": 11,
    "tools/cloud/test_library_bake_sends_what_its_job_names.py": 6,
    "tools/cloud/test_meshparts_brings_back_only_the_splits.py": 3,
    "tools/cloud/test_moss_takes_each_briefed_sound_once_and_credits_what_came_back.py": 6,
    "tools/cloud/test_park_holds_a_machine_only_while_it_pays_off.py": 24,
    "tools/cloud/test_pictures_draws_each_listed_picture_once_on_a_card_that_holds_its_model.py": 5,
    "tools/cloud/test_pool_books_every_card_once_and_deletes_every_card.py": 44,
    "tools/cloud/test_preflight_sizes_paid_work_from_measured_numbers.py": 9,
    "tools/cloud/test_prop_batch_pays_each_measured_step_once.py": 6,
    "tools/cloud/test_prop_makers_hand_each_step_its_props_inputs.py": 7,
    "tools/cloud/test_scene_runs_only_an_approved_locked_plan_in_order.py": 7,
    "tools/cloud/test_spread_runs_every_share_once.py": 13,
    "tools/cloud/test_this_pc_pulls_no_keys_and_pushes_without_replacing.py": 10,
    "tools/costs/test_every_euro_is_ledgered_measured_and_adds_up_to_the_bill.py": 34,
    "tools/library/test_every_record_name_resolves_or_is_a_gap.py": 8,
    "tools/props/closeup/test_only_a_clean_closeup_goes_on.py": 25,
    "tools/props/gates/test_model_gate_judges_real_meshes.py": 5,
    "tools/props/library/test_pieces_keep_true_shape_and_library_paint.py": 40,
    "tools/props/scene/test_a_scene_is_made_from_its_concept.py": 25,
    "tools/props/test_crop_as_pixal3d_does.py": 7,
    "tools/props/test_one_run_on_the_card.py": 12,
    "tools/props/test_raw_model_faces_minus_z.py": 3,
    "tools/props/test_refused_on_this_pc.py": 3,
    "tools/props/test_stood_up_and_kept_intact.py": 17,
    "tools/review/test_a_film_is_shown_only_when_its_measures_pass.py": 4,
    "tools/review/test_a_films_shots_keep_clear_and_move_smoothly.py": 17,
    "tools/review/test_a_place_page_reads_its_own_audit_and_status.py": 4,
    "tools/review/test_a_preview_shows_each_shots_ends_and_leaves_the_stage_alone.py": 4,
    "tools/review/test_a_region_is_judged_against_the_games_own_light.py": 4,
    "tools/review/test_the_review_page_shows_what_the_stages_wrote.py": 11,
    "tools/review/test_the_showcase_cuts_every_film_in_order_within_its_cap.py": 8,
    "tools/review/test_the_style_measure_reads_only_the_models_own_pixels.py": 8,
    "tools/review/viewer/test_the_web_copy_is_the_stage_whole_and_the_picks_are_kept.py": 6,
    "tools/sound/loudness/test_no_take_leaves_louder_than_the_rule.py": 5,
    "tools/sound/picker/test_picker_puts_in_only_clean_safe_takes.py": 6,
}

# The docstring line that excuses a second test function, with its reason after the colon.
SECOND_TEST = re.compile(r"^\s*second test:\s*\S", re.IGNORECASE | re.MULTILINE)

# "break" and "red" in one statement, which may wrap over the docstring's lines.
BREAK_LINE = re.compile(r"\bbreaks?\b.{0,200}?\bred\b|\bred\b.{0,200}?\bbreaks?\b", re.IGNORECASE)


def is_test_file(path):
    """Whether a repository path names a test file under the rule (vendor/ is third-party, kept as released)."""
    name = path.name
    return (not path.parts or path.parts[0] != "vendor") and name.endswith(".py") and (
        name.startswith("test_") or name.endswith("_test.py"))


def test_files(root):
    """The repository's test files, tracked or new and not ignored, that exist on disk, as paths from the root."""
    listed = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                            check=True, capture_output=True, text=True).stdout
    paths = {pathlib.PurePosixPath(entry) for entry in listed.split("\0") if entry}
    return sorted(path for path in paths if is_test_file(path) and (root / path).is_file())


def allowlisted(path):
    """Whether a test file sits in a module the allowlist still exempts."""
    return any(fnmatch.fnmatch(str(path), pattern) for pattern in ALLOWLIST)


def docstring(root, path):
    """A test file's module docstring ("" when it has none), or None when the file does not parse."""
    try:
        return ast.get_docstring(ast.parse((root / path).read_text(encoding="utf-8"))) or ""
    except SyntaxError:
        return None


def named_tool(root, path, text):
    """The tool script of a flat folder that a top-level test file's docstring names first, or None."""
    folder = path.parent
    tools = {sibling.stem for sibling in (root / folder).glob("*.py")
             if not is_test_file(pathlib.PurePosixPath(sibling.name)) and sibling.name != "__init__.py"}
    for pattern in (re.escape(str(folder)) + r"/(\w+)\.py\b", r"\b(\w+)\.py\b", r"\b(\w+)\b"):
        for found in re.finditer(pattern, text):
            if found.group(1) in tools:
                return found.group(1)
    return None


def module_of(root, path, text):
    """The module a test file belongs to, as a path from the root, or None for a flat-folder test naming no tool."""
    folder = path.parent
    if folder.name == "tests":
        folder = folder.parent
    if str(path.parent) in FLAT_TOOL_FOLDERS:
        tool = named_tool(root, path, text or "")
        return folder / tool if tool else None
    return folder


def test_count(root, path):
    """How many test functions a test file defines (a `Test*` class's methods counted), 0 when it does not parse."""
    try:
        tree = ast.parse((root / path).read_text(encoding="utf-8"))
    except SyntaxError:
        return 0
    count = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            count += 1
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            count += sum(1 for item in node.body
                         if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test"))
    return count


def count_faults(path, count, text, debt):
    """One test file's fault under the one-function rule, against its debt entry if it has one."""
    owed = debt.get(str(path))
    if owed is None:
        if count > 1 and not SECOND_TEST.search(text or ""):
            return [f"{path}: {count} test functions, one a file (merge them into one test of the answer that matters)"]
        return []
    if count > owed:
        return [f"{path}: {count} test functions, its FUNCTION_DEBT entry allows {owed} (a debt file may not grow)"]
    if count <= 1:
        return [f"{path}: {count} test function now, delete its FUNCTION_DEBT entry"]
    if count < owed:
        return [f"{path}: {count} test functions now, lower its FUNCTION_DEBT entry from {owed} to {count}"]
    return []


def file_faults(path, text):
    """One test file's own faults: its name and its docstring's break line."""
    faults = []
    if not path.name.startswith("test_"):
        faults.append(f"{path}: named for its module, not its invariant (rename to test_<invariant>.py)")
    if text is None:
        faults.append(f"{path}: does not parse")
    elif not BREAK_LINE.search(" ".join(text.split())):
        faults.append(f"{path}: its docstring has no line naming the break that turns it red")
    return faults


def faults(root, named=(), debt=None):
    """Every fault of the rule in the repository at `root`, or only in the modules of the `named` test files.

    `debt` is the function-count debt (`FUNCTION_DEBT` when None); a test passes its own.
    """
    root = pathlib.Path(root)
    debt = FUNCTION_DEBT if debt is None else debt
    modules = {}
    found = []
    listed = test_files(root)
    if not named:
        present = {str(path) for path in listed}
        found.extend(f"{test}: on FUNCTION_DEBT but not in the tree, delete its entry"
                     for test in debt if test not in present)
    for path in listed:
        if allowlisted(path):
            continue
        text = docstring(root, path)
        module = module_of(root, path, text)
        if module is None:
            found.append(f"{path}: its docstring names none of {path.parent}'s tool scripts")
            module = path
        modules.setdefault(module, []).append((path, text))
    wanted = {pathlib.PurePosixPath(name) for name in named}
    for module, files in sorted(modules.items()):
        if wanted and not wanted & {path for path, _ in files}:
            continue
        if len(files) > 1:
            found.append(f"{module}: {len(files)} test files, one a module: {', '.join(str(path) for path, _ in files)}")
        for path, text in files:
            found.extend(file_faults(path, text))
            found.extend(count_faults(path, test_count(root, path), text, debt))
    return sorted(set(found))


def main(argv):
    """Print the summary line and each fault; exit 1 when there is any."""
    found = faults(REPO, argv)
    print(f"test rule: {len(found)} fault(s) (allowlist of {ALLOWLIST_DATE}: {len(ALLOWLIST)} entries)")
    for fault in found:
        print(f"  {fault}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
