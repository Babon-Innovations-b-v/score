"""The guard on the test rule (docs/bible.md workflow/module-standard; owner, 2026-10-26: "only 1 but one actual good
meaning full test file per module ... i feel like that rule kinda drifted by now"): it lists every way the repository's
test files break the rule, so the rule cannot drift again. `make tests` runs it and fails on any fault.

    python3 tools/test_rule/check.py                 # every module in the repository
    python3 tools/test_rule/check.py <test file> ... # only the modules those files belong to

A test file is a file named `test_*.py` or `*_test.py`, tracked or new (not ignored), outside `vendor/`. Its faults:

- **named for its module, not its invariant**: every test file is `test_<invariant>.py`.
- **no break**: its module docstring has no line naming the break that turns it red ("break" and "red" in one statement,
  at most 200 characters apart, as "Breaks (each applied once, seen red, reverted), in ...:").
- **more than one test function in a file** (owner, 2026-11-01): a test file holds ONE `test_*` function (a method of
  a `Test*` class counts); parametrized cases of one check are one function. A script-style file's checks count the
  same (2026-11-07): each entry of its top-level `CHECKS` and each top-level `def check_*`, a name counted once. A
  docstring line starting `second test:` with a reason excuses it, but only up to the count the file has on
  origin/main (one for a file not there): a note never grows a file. `FUNCTION_DEBT` holds the files over it that day
  with their count: one may not grow, one that shrank must lower its entry, one down to one test (or gone) must lose it.
- **tests that run only under `__main__`**: a test file with an `if __name__ == ...` block and no `test_*` function
  holds checks pytest never finds. `MAIN_ONLY` lists the files that did so on 2026-11-07; it only shrinks.
- **a SyntaxWarning** (an invalid escape sequence, say) is a fault of the file that raises it.
- **more than one test file in a module**: a module is the directory its test file sits in, a `tests/` folder counting
  as its parent's (`.claude/hooks/tests` is `.claude/hooks`). In a flat folder of independent tools (`FLAT_TOOL_FOLDERS`)
  a top-level test file belongs to the tool script its docstring names first (as `tools/<folder>/<tool>.py`, else as
  `<tool>.py`, else as the bare name), and one that names none is a fault of its own.

`ALLOWLIST` holds the modules other agents' sweeps are still reworking, dated, each pattern with the test files and
test functions it covered on 2026-11-07; like `FUNCTION_DEBT` it only shrinks (a pattern covering more is a fault, one
covering less must lower its entry, one covering none must go), and nothing else goes in it.

    python3 tools/test_rule/check.py --ran <test file> <its output file>

is the run's own fault (`make tests` asks it for each file whose output says skipped): a file that printed a line
starting `skipped`, or whose pytest summary is skips only, did not run, unless `MAY_SKIP` names it with the reason.
The output is one summary line, then one line a fault.
"""
import ast
import fnmatch
import functools
import pathlib
import re
import subprocess
import sys
import warnings

REPO = pathlib.Path(__file__).resolve().parents[2]

# Folders of independent command-line tools: each top-level tool script is a module of its own.
FLAT_TOOL_FOLDERS = ("tools/cloud", "tools/props", "tools/review", "tools/usd")

# Modules still being swept by other agents on 2026-10-26: skipped until their sweep empties the entry. Each pattern
# holds (test files, test functions) it covered when recounted on 2026-11-07; only ever shrinks.
ALLOWLIST_DATE = "2026-10-26"
ALLOWLIST_COUNT_DATE = "2026-11-07"
ALLOWLIST = {
    "tools/usd/*": (21, 144),
    "score/stages/complete/*": (10, 97),
    "score/stages/props/*": (4, 55),
    "score/stages/settling/*": (1, 17),
    "score/stages/physics/*": (1, 12),
    "*prepare*": (1, 32),
}

# Test files whose checks ran only under `__main__` on 2026-11-07 (pytest finds none of them); only ever shrinks.
MAIN_ONLY_DATE = "2026-11-07"
MAIN_ONLY = (
    "score/stages/sim_body/inside/batched/test_every_frame_on_the_card_is_mujocos_own_to_its_rounding.py",
    "score/stages/sim_body/inside/bone_groups/test_each_segment_rides_and_groups_bodies_of_its_side_joint_to_joint.py",
    "score/stages/sim_body/inside/calibration/test_the_calibration_lays_each_bone_along_its_segment.py",
    "score/stages/sim_body/inside/contact/test_only_a_point_within_gap_is_pushed.py",
    "score/stages/sim_body/inside/fit/_card/tests/test_the_card_step_and_projection_equal_the_cpu_prototype.py",
    "score/stages/sim_body/inside/fit/test_the_solver_gives_back_the_pose_and_constants_that_made_its_targets.py",
    "score/stages/sim_body/inside/ground/test_a_point_stands_on_the_highest_ground_in_reach.py",
    "score/stages/sim_body/inside/landmarks/test_every_landmark_resolves_on_both_models_where_worked_by_hand.py",
    "score/stages/sim_body/inside/model/test_couplings_keep_a_follower_on_its_leader.py",
    "score/stages/sim_body/inside/muscles/test_a_standing_body_is_carried_by_the_ground.py",
    "score/stages/sim_body/inside/myo/test_the_persons_file_builds_in_newton_as_mujoco_compiles_it.py",
    "score/stages/sim_body/inside/records/test_a_record_keeps_poses_meshes_and_moves_as_worked_by_hand.py",
    "score/stages/sim_body/inside/resting/test_no_muscle_stands_past_its_resting_length.py",
    "score/stages/sim_body/inside/rra/test_rra_moves_mass_and_torso_by_the_mean_residual.py",
    "score/stages/sim_body/inside/sizing/test_a_sized_group_is_somas_length_and_weight.py",
    "score/stages/sim_body/inside/solvers/test_each_solver_meets_a_hand_worked_answer.py",
    "score/stages/sim_body/inside/volumes/test_a_segment_weighs_its_volume_at_its_density.py",
)

# Test files that may print `skipped` (a check not run on this box), each with the reason.
MAY_SKIP = {
    "score/stages/sim_body/inside/*": "needs a GPU: run by hand (make tests) on a GPU box",
    "tools/usd/test_a_hollow_body_keeps_its_hollow.py": "two of its drops need the Newton env, which needs a GPU",
    "score/stages/settling/test_the_settle_layer_lays_and_its_gate_fails_a_broken_drop.py":
        "its two room drops need the Newton env, which needs a GPU",
}

# Test files holding more than one test function on 2026-11-01 (118 files, 2139 functions over one), each
# with its count that day, and the script-style files counted from 2026-11-07 (their `CHECKS` and `check_*`
# functions) at their count that day; only ever shrinks.
FUNCTION_DEBT_DATE = "2026-11-01"
FUNCTION_DEBT = {
    ".claude/hooks/tests/test_hooks_block_only_their_rule_and_fail_open.py": 31,
    ".claude/scripts/tests/test_scripts_touch_only_what_they_own.py": 6,
    "paper/score/build/test_paper_build_matches_its_source.py": 2,
    "score/adapters/compute/test_paid_work_starts_only_inside_its_clearance.py": 47,
    "score/adapters/engines/test_blender_runs_pinned_and_only_once_cleared.py": 2,
    "score/adapters/models/test_a_node_is_keyed_only_on_pinned_models.py": 7,
    "score/adapters/vendored/test_every_vendored_tool_is_accounted_for.py": 5,
    "score/checks/test_nothing_unproven_passes.py": 10,
    "score/conductor/test_the_conductor_spends_and_stops_only_as_its_owner_says.py": 29,
    "score/contracts/test_nothing_off_contract_passes.py": 7,
    "score/dashboard/auth/test_only_the_proxy_or_the_owner_signs_in.py": 7,
    "score/dashboard/checkout/test_a_batch_buys_only_what_the_owner_approved.py": 37,
    "score/dashboard/films/test_a_film_is_timed_checked_and_priced_from_its_script.py": 27,
    "score/dashboard/proposals/test_a_basket_shows_what_a_run_on_main_would_buy.py": 20,
    "score/dashboard/state/test_the_cockpit_shows_the_store_as_read.py": 21,
    "score/dashboard/sync/test_the_cockpit_gets_the_store_whole_and_the_store_only_the_owners_asks.py": 29,
    "score/dashboard/tests/test_cockpit_is_the_owners_true_view.py": 90,
    "score/dashboard/web3d/test_a_web_copy_is_made_from_the_standing_accept.py": 7,
    "score/graph/test_a_key_is_made_once_from_accepted_inputs.py": 115,
    "score/library/test_read_only_at_known_schema.py": 4,
    "score/review/holders/test_each_plan_item_names_what_holds_it.py": 24,
    "score/review/relation_solver/test_a_crowded_plan_is_parted_inside_its_walls_the_same_way_every_run.py": 2,
    "score/review/test_the_owners_word_stands.py": 131,
    "score/stages/animals/test_animal_rows_follow_the_design.py": 3,
    "score/stages/assembly/test_a_place_stands_from_its_accepted_outputs.py": 42,
    "score/stages/cast/test_people_stand_clear_or_are_named.py": 20,
    "score/stages/demo_film/test_a_film_shows_its_locked_script_within_its_forecast.py": 32,
    "score/stages/effects/test_effects_ride_their_design.py": 6,
    "score/stages/images/test_image_proofs_pass_only_a_proof_that_did_its_jobs.py": 6,
    "score/stages/library/test_everything_handed_to_library.py": 12,
    "score/stages/light/test_light_measured_against_design.py": 6,
    "score/stages/motion/test_a_thing_moves_as_its_design_says.py": 18,
    "score/stages/people_cloth/test_loose_cloth_rides_its_sim_body_and_is_judged_by_measure.py": 8,
    "score/stages/scene_clips/test_a_walk_becomes_constraints_on_its_own_ground.py": 11,
    "score/stages/scene_record/test_a_scene_record_is_written_from_its_design.py": 22,
    "score/stages/shapes_first/test_every_model_goes_through_the_loop.py": 14,
    "score/stages/sim_body/inside/bone_groups/test_each_segment_rides_and_groups_bodies_of_its_side_joint_to_joint.py": 2,
    "score/stages/sim_body/inside/calibration/test_the_calibration_lays_each_bone_along_its_segment.py": 8,
    "score/stages/sim_body/inside/contact/test_only_a_point_within_gap_is_pushed.py": 5,
    "score/stages/sim_body/inside/evaluation/test_every_evaluation_runs_every_tuning_body_and_the_check_never_chooses.py": 9,
    "score/stages/sim_body/inside/fit/test_the_solver_gives_back_the_pose_and_constants_that_made_its_targets.py": 24,
    "score/stages/sim_body/inside/ground/test_a_point_stands_on_the_highest_ground_in_reach.py": 6,
    "score/stages/sim_body/inside/landmarks/test_every_landmark_resolves_on_both_models_where_worked_by_hand.py": 7,
    "score/stages/sim_body/inside/model/test_couplings_keep_a_follower_on_its_leader.py": 4,
    "score/stages/sim_body/inside/muscles/test_a_standing_body_is_carried_by_the_ground.py": 3,
    "score/stages/sim_body/inside/myo/test_the_persons_file_builds_in_newton_as_mujoco_compiles_it.py": 10,
    "score/stages/sim_body/inside/records/test_a_record_keeps_poses_meshes_and_moves_as_worked_by_hand.py": 6,
    "score/stages/sim_body/inside/rra/test_rra_moves_mass_and_torso_by_the_mean_residual.py": 14,
    "score/stages/sim_body/inside/sizing/test_a_sized_group_is_somas_length_and_weight.py": 6,
    "score/stages/sim_body/inside/solvers/test_each_solver_meets_a_hand_worked_answer.py": 4,
    "score/stages/sim_body/inside/tuning/_adjoint/test_implicit_columns_equal_re_solved_differences.py": 27,
    "score/stages/sim_body/inside/tuning/_paired/test_a_step_counts_only_past_its_noise_floor_on_a_fixed_case_set.py": 6,
    "score/stages/sim_body/inside/tuning/test_one_optimisation_moves_every_unknown_together_within_its_bounds.py": 17,
    "score/stages/sim_body/inside/volumes/test_a_segment_weighs_its_volume_at_its_density.py": 3,
    "score/stages/sim_body/test_a_body_doing_its_clip_stands_on_its_ground_within_its_residual.py": 9,
    "score/stages/sound/test_a_place_is_heard_as_its_design_says.py": 20,
    "score/stages/surface_tiles/test_shell_tiles.py": 4,
    "score/stages/surfaces/test_every_part_takes_a_library_surface_and_is_held_to_it.py": 116,
    "score/stages/terrain/test_ground_follows_design.py": 10,
    "score/stages/test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps.py": 80,
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
    "tools/cloud/conductor/test_owner_gates_and_safe_moves.py": 25,
    "tools/cloud/images/test_built_once_and_every_machine_deleted.py": 6,
    "tools/cloud/k8s/clusters/test_own_cluster_capped_and_ledgered.py": 6,
    "tools/cloud/k8s/test_jobs_take_their_classes_in_order.py": 13,
    "tools/cloud/runtime/test_a_job_runs_once_on_checked_weights.py": 15,
    "tools/cloud/test_batch_pays_once_inside_its_limits_and_leaves_no_machine.py": 36,
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
    "tools/library/test_every_record_name_resolves_or_is_a_gap.py": 8,
    "tools/props/closeup/test_only_a_clean_closeup_goes_on.py": 25,
    "tools/props/gates/test_model_gate_judges_real_meshes.py": 5,
    "tools/props/library/test_pieces_keep_true_shape_and_library_paint.py": 40,
    "tools/props/scene/test_a_scene_is_made_from_its_concept.py": 17,
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

# The pytest summary of a file that ran nothing but skips ("3 skipped in 0.1s").
ONLY_SKIPS = re.compile(r"^\s*\d+ skipped\b", re.MULTILINE)

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


def allowlisted(path, allowlist):
    """Whether a test file sits in a module the allowlist still exempts."""
    return any(fnmatch.fnmatch(str(path), pattern) for pattern in allowlist)


@functools.lru_cache(maxsize=None)
def parse(source):
    """A source's tree (None when it does not parse) and the lines of the SyntaxWarnings parsing it raised."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            tree = None
    raised = tuple(warning.lineno for warning in caught if issubclass(warning.category, SyntaxWarning))
    return tree, raised


def parsed(root, path):
    """A test file's tree and SyntaxWarnings (see `parse`)."""
    return parse((root / path).read_text(encoding="utf-8"))


def docstring(root, path):
    """A test file's module docstring ("" when it has none), or None when the file does not parse."""
    tree, _ = parsed(root, path)
    return None if tree is None else ast.get_docstring(tree) or ""


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


def pytest_tests(tree):
    """The names of the test functions pytest finds in a tree (a `Test*` class's methods as `Class.method`)."""
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            names.update(f"{node.name}.{item.name}" for item in node.body
                         if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test"))
    return names


def script_checks(tree):
    """The names of a script-style file's checks: its top-level `CHECKS` entries and `def check_*` functions."""
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("check_"):
            names.add(node.name)
        elif (isinstance(node, ast.Assign) and isinstance(node.value, (ast.Tuple, ast.List))
              and any(isinstance(target, ast.Name) and target.id == "CHECKS" for target in node.targets)):
            names.update(entry.id if isinstance(entry, ast.Name) else f"CHECKS[{index}]"
                         for index, entry in enumerate(node.value.elts))
    return names


def tree_count(tree):
    """How many test functions a tree defines, pytest's and the script's checks, each name once; 0 for None."""
    return 0 if tree is None else len(pytest_tests(tree) | script_checks(tree))


def test_count(root, path):
    """How many test functions a test file defines (see `tree_count`), 0 when it does not parse."""
    return tree_count(parsed(root, path)[0])


def runs_only_under_main(root, path):
    """Whether a test file has an `if __name__ == ...` block and no test function pytest finds."""
    tree, _ = parsed(root, path)
    if tree is None or pytest_tests(tree):
        return False
    return any(isinstance(node, ast.If) and "__name__" in {name.id for name in ast.walk(node.test)
                                                           if isinstance(name, ast.Name)} for node in tree.body)


def base_count(root, path, base):
    """A test file's test-function count at the git ref `base`, or None when the file (or the ref) is not there."""
    shown = subprocess.run(["git", "-C", str(root), "show", f"{base}:{path}"], capture_output=True, text=True)
    return tree_count(parse(shown.stdout)[0]) if shown.returncode == 0 else None


def count_faults(path, count, text, debt, based):
    """One test file's fault under the one-function rule, against its debt entry if it has one.

    `based` gives the file's count on origin/main, asked only when a `second test:` note must be weighed.
    """
    owed = debt.get(str(path))
    if owed is None:
        if count <= 1:
            return []
        if not SECOND_TEST.search(text or ""):
            return [f"{path}: {count} test functions, one a file (merge them into one test of the answer that matters)"]
        before = based() or 1
        if count > before:
            return [f"{path}: {count} test functions, its `second test:` note covers the {before} it has on origin/main"
                    " (a note never grows a file)"]
        return []
    if count > owed:
        return [f"{path}: {count} test functions, its FUNCTION_DEBT entry allows {owed} (a debt file may not grow)"]
    if count <= 1:
        return [f"{path}: {count} test function now, delete its FUNCTION_DEBT entry"]
    if count < owed:
        return [f"{path}: {count} test functions now, lower its FUNCTION_DEBT entry from {owed} to {count}"]
    return []


def file_faults(path, text, raised=()):
    """One test file's own faults: its name, its docstring's break line and the SyntaxWarnings it raises."""
    faults = [f"{path}: raises a SyntaxWarning on line {line} (python3 -m py_compile shows it)" for line in raised]
    if not path.name.startswith("test_"):
        faults.append(f"{path}: named for its module, not its invariant (rename to test_<invariant>.py)")
    if text is None:
        faults.append(f"{path}: does not parse")
    elif not BREAK_LINE.search(" ".join(text.split())):
        faults.append(f"{path}: its docstring has no line naming the break that turns it red")
    return faults


def allowlist_faults(root, listed, allowlist):
    """The allowlist's own faults: a pattern covering more test files or functions than its entry, less, or none."""
    found = []
    for pattern, owed in sorted(allowlist.items()):
        covered = [path for path in listed if fnmatch.fnmatch(str(path), pattern)]
        count = (len(covered), sum(test_count(root, path) for path in covered))
        if not covered:
            found.append(f"ALLOWLIST {pattern}: covers no test file, delete its entry")
        elif count[0] > owed[0] or count[1] > owed[1]:
            found.append(f"ALLOWLIST {pattern}: covers {count[0]} test files, {count[1]} test functions, its entry"
                         f" allows {owed[0]}, {owed[1]} (an allowlisted module may not grow)")
        elif count != tuple(owed):
            found.append(f"ALLOWLIST {pattern}: covers {count[0]} test files, {count[1]} test functions now, lower its"
                         f" entry from {tuple(owed)} to {count}")
    return found


def stale_faults(listed, debt, main_only):
    """The FUNCTION_DEBT and MAIN_ONLY entries whose file is not in the tree."""
    present = {str(path) for path in listed}
    return [f"{test}: on {name} but not in the tree, delete its entry"
            for name, entries in (("FUNCTION_DEBT", debt), ("MAIN_ONLY", main_only))
            for test in entries if test not in present]


def main_faults(root, path, main_only):
    """A test file's fault under the pytest-finds-it rule, against its MAIN_ONLY entry if it has one."""
    only = runs_only_under_main(root, path)
    if only and str(path) not in main_only:
        return [f"{path}: its tests run only under __main__, pytest finds none (make them one test_ function)"]
    if not only and str(path) in main_only:
        return [f"{path}: pytest finds its test now, delete its MAIN_ONLY entry"]
    return []


def faults(root, named=(), debt=None, allowlist=None, main_only=None, base="origin/main"):
    """Every fault of the rule in the repository at `root`, or only in the modules of the `named` test files.

    `debt`, `allowlist` and `main_only` are `FUNCTION_DEBT`, `ALLOWLIST` and `MAIN_ONLY` when None, and `base` the
    ref a `second test:` note is weighed against; a test passes its own.
    """
    root = pathlib.Path(root)
    debt = FUNCTION_DEBT if debt is None else debt
    allowlist = ALLOWLIST if allowlist is None else allowlist
    main_only = MAIN_ONLY if main_only is None else main_only
    modules = {}
    found = []
    listed = test_files(root)
    if not named:
        found.extend(stale_faults(listed, debt, main_only))
        found.extend(allowlist_faults(root, listed, allowlist))
    for path in listed:
        if allowlisted(path, allowlist):
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
            found.extend(file_faults(path, text, parsed(root, path)[1]))
            found.extend(count_faults(path, test_count(root, path), text, debt,
                                      functools.partial(base_count, root, path, base)))
            found.extend(main_faults(root, path, main_only))
    parse.cache_clear()  # the trees held to the interpreter's exit cost it two seconds to free
    return sorted(set(found))


def ran_faults(path, output, may_skip=None):
    """A test file's run's fault: it printed `skipped` (or pytest skipped all of it) and `may_skip` names it not."""
    may_skip = MAY_SKIP if may_skip is None else may_skip
    skipped = any(line.lstrip().lower().startswith("skipped") for line in output.splitlines())
    if not (skipped or ONLY_SKIPS.search(output)) or any(fnmatch.fnmatch(str(path), key) for key in may_skip):
        return []
    return [f"{path}: printed skipped, so it did not run (run it where it can, or name it in MAY_SKIP with the reason)"]


def main(argv):
    """Print the summary line and each fault; exit 1 when there is any."""
    if argv[:1] == ["--ran"]:
        found = ran_faults(argv[1], pathlib.Path(argv[2]).read_text(encoding="utf-8", errors="replace"))
        for fault in found:
            print(f"  {fault}")
        return 1 if found else 0
    found = faults(REPO, argv)
    print(f"test rule: {len(found)} fault(s) (allowlist of {ALLOWLIST_DATE}: {len(ALLOWLIST)} entries)")
    for fault in found:
        print(f"  {fault}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
