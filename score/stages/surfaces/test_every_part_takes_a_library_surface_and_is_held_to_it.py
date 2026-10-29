"""Every part of a place takes a library surface by the finish route and is held to it: the route's rows from the
scene palette and the scene's surface library through views, list, split, parts, bake, paint, recheck and check
(Google and the cloud calls faked, no spend), the method's shared steps on a take's faces (finish_parts.py,
finish_ask.py), the bake check against the bake's specs, the paint's levelling, the bake job written from git
(bake_job.py), the bodies' faces (body_faces.py), the finish registry, the per-place data, and the keys the paint and
bake rows take from the library (library_reads.py, carry.py). A gate that cannot read what it needs answers unknown.

Each test makes its own small world in a temporary folder or under $PROPS_HOME; no designed place's hand-in is read
(prepare's), so DESIGN points at a folder that is not there.

Breaks (each applied once, seen red, reverted), in score/stages/surfaces/ unless named; old -> new  -> the
tests it turned red:
- registry.py: `if standing is None:` -> `if True:`  -> a_proposed_library_surface_stands_as_first_proposed
- registry.py: `return re.sub(r"[^a-z0-9]+", "_", name.lower())` -> `return re.sub(r"[^a-z0-9]+", "_", name)`  ->
  names_alike_but_for_case_stand_as_one_entry
- place_line.py: `record["proposed"] = standing["spec"]` -> `record["proposed"] = row["proposed"]`  ->
  the_paint_takes_the_method_s_surface_and_records_its_proposal
- surface_data.py: `return not path(place).exists() or bool(takes(place))` -> `return not path(place).exists() or not
  takes(place)`  -> each_take_is_painted_by_one_place_and_every_claim_is_baked_by_its_place
- __init__.py: `("finish-route-palette", scene_library.ROW, "surfaces-parts"), paid=True` -> `(scene_library.ROW,
  "surfaces-parts"), paid=True`  -> every_place_s_surface_line_is_rows_of_world_one
- __init__.py: `route_data.shape_files, selects=True),` -> `route_data.library_files, selects=True),`  ->
  a_method_change_moves_only_the_rows_that_read_the_library
- __init__.py: `after=(), applies=data.paints, **more):` -> `after=(), applies=lambda place: True, **more):`  ->
  a_place_without_data_blocks_before_anything_is_spent_and_one_with_nothing_to_paint_has_no_rows
- surface_gates.py: `except (FileNotFoundError, KeyError, json.JSONDecodeError) as missing:` -> `except (KeyError,
  json.JSONDecodeError) as missing:`  -> a_gate_that_cannot_read_its_evidence_answers_unknown
- bake_check.py: `(colour[:, 0] < BLOTCH_L) & (far > BLOTCH_DELTA_E)` -> `(colour[:, 0] < BLOTCH_L)`  ->
  a_clean_label_border_passes_and_a_black_smudge_along_it_fails, a_surfaces_own_drawn_seams_are_not_blotches
- bake_check.py: `if finish.get("measured_lab") is not None and not finish.get("cover"):` -> `if
  finish.get("measured_lab") is not None:`  -> a_finish_judged_by_its_own_colour_is_not_compared_with_its_close_up
- bake_check.py: `name = route_settings.settings_name(finish["surface"], settings) if settings else finish["surface"]`
  -> `name = finish["surface"]`  -> a_surface_with_the_list_s_settings_is_compared_with_its_close_up
- bake_check.py: `if seen > ORDER_L and baked < -ORDER_BAKED:` -> `if False:`  ->
  the_water_tank_s_reversed_greys_fail_and_its_cream_paint_passes
- bake_check.py: `if apart >= 1: return []` -> `if apart >= 0: return []`  ->
  one_look_fails_only_what_a_viewer_cannot_tell_apart_at_the_place_s_view_distance
- place_line.py: `band = wide if not tall else min(FOOT_BAND, FOOT_BAND_METRES / tall) * height` -> `band = wide`  ->
  a_tall_take_s_feet_are_found_in_the_resting_check_s_band
- place_line.py: `if record["feet"] == 2:` -> `if False:`  -> a_take_on_two_feet_has_its_short_one_levelled
- place_line.py: `if band < wide: # then` -> `if False: # then`  ->
  a_tall_take_s_leg_ending_over_the_narrow_band_is_still_levelled
- place_line.py: `if found_row["id"] == row and stands(found_row` -> `if stands(found_row`  ->
  a_take_another_place_lays_standing_is_levelled_by_its_rows
- place_line.py: `for take, report in found.items() if report.get("feet", {}).get("refused")]` -> `for take, report in
  found.items() if False]`  -> a_take_s_short_legs_are_levelled_before_its_bake_and_a_missing_leg_fails_by_name
- place_line.py: `if row.get("group") == "kit: floor" or row.get("route") == "ground":` -> `if row.get("route") ==
  "ground":`  -> a_designed_place_s_paint_reads_its_hand_in_rows_for_feet_never_the_old_inventory
- place_line.py: `if unknown: raise` -> `if False: raise`  -> the_kit_route_s_bake_answers_the_empty_library_by_name
- inside/paint_take.py: `return os.waitstatus_to_exitcode(status), usage.ru_maxrss / 1e6` -> `return status,
  usage.ru_maxrss / 1e6`  -> a_killed_paint_on_the_machine_says_its_signal_and_peak
- place_line.py: `*inventories, *models, *(REPO` -> `*inventories, *(REPO`  ->
  a_take_s_paint_job_sends_what_it_reads_and_brings_its_folder_back
- bake_check.py: `nearest = min(nearest, float(np.linalg.norm(baked - (worn + share * toward))))` -> `nearest =
  min(nearest, float(np.linalg.norm(baked - worn)))`  ->
  a_bake_is_held_against_its_surface_dirtied_as_far_as_its_place_s_dirt
- bake_check.py: `worn = clean + share_worn * (bare - clean) if bare is not None else clean` -> `worn = clean`  ->
  a_bake_is_held_against_its_surface_worn_as_far_as_its_place_s_wear,
  wear_passes_only_toward_the_surface_s_bare_colour_and_only_as_far_as_its_place_s_wear
- bake_check.py: `order = np.argsort(colour, axis=0)` -> `order = np.repeat(np.argsort(colour[:, 0])[:, None],
  colour.shape[1], axis=1)`  -> a_part_s_baked_colour_is_its_area_s_median_on_each_channel
- bake_check.py: `owners[chosen] = np.where(found >= 0, chosen[np.maximum(found, 0)], chosen)` -> `owners[chosen] =
  chosen`  -> a_triangle_under_a_texel_is_named_by_where_the_bake_wrote_its_texel
- bake_check.py: `surface = ray_surfaces(geometry, laid, codes, entry["size"], sampled)` -> `surface =
  np.full(len(middles), -1)`  -> a_baked_triangle_beside_a_thin_post_is_named_by_the_bake_s_ray_not_the_nearest_part
- bake_check.py: `found.append(round(float(chosen[:, 1].min() - low[1]), 3))` -> `found.append(0.0)`  ->
  a_standing_model_with_a_foot_off_the_floor_fails_and_lying_wreckage_is_left_out
- place_line.py: `if gaps.max() > most:` -> `if False:`  ->
  a_base_that_slopes_as_one_piece_is_brought_down_level_and_a_far_gap_is_refused
- place_line.py: `if len(under) < 3 or rise <= tolerance or` -> `if True or`  ->
  a_base_sloping_as_one_plane_through_its_middle_is_brought_down_level
- place_line.py: `if normal[1] > -1e-6: # no face` -> `if True: # no face`  ->
  a_tall_cabinet_s_base_step_is_levelled_against_its_footprint
- place_line.py: `if data.get("foot_traffic", True):` -> `if True:`  ->
  only_a_place_nobody_walks_bakes_with_no_kick_wear
- place_line.py: `CLASSES = "gpu-24gb"` -> `CLASSES = "gpu-24gb,gpu-48gb"`  ->
  bake_and_paint_rent_one_machine_class_each
- library_reads.py: `for name in entry["variants"]] if bakes else []` -> `for name in entry["variants"]]`  ->
  a_surface_added_anywhere_moves_no_paint_key_and_every_bake_key
- library_reads.py: `"details": {kind: details.get(kind) for kind in kind_names}}` -> `"details": {}}`  ->
  a_kinds_details_move_the_paint_key_and_place_json_keys_neither
- library_reads.py: `"library": (wide["library"], library_part(kinds(record), bakes)),` -> `"library": wide["library"],`
  -> the_paint_and_bake_rows_and_their_twins_key_the_library_by_part
- library_reads.py: `if why:` -> `if False:`  -> a_bake_model_with_no_written_entry_is_declared_missing_by_name
- carry.py: `if record.get("uncommitted", True) or not record.get("commit"):` -> `if not record.get("commit"):`  ->
  a_record_from_an_uncommitted_tree_or_a_changed_code_without_proof_never_carries
- carry.py: `if not str(proof.get("no-ops", {}).get(name, "")).strip()]` -> `if False]`  ->
  a_proof_carries_only_when_it_names_every_changed_file_for_these_code_versions
- carry.py: `str(folder), commit],` -> `str(folder), "HEAD"],`  -> a_proof_speaks_from_the_code_rows_had_at_its_commit
- finish_parts.py: `found[reached] = face_label[source[reached]]` -> `found[reached] = 0`  ->
  unvoted_faces_take_the_nearest_voted_label_along_the_surface
- finish_parts.py: `host = np.flatnonzero(hosts & (face_label == finish))` -> `host = np.flatnonzero(hosts)`  ->
  a_loose_bit_joins_the_nearest_larger_island_of_its_own_finish
- finish_parts.py: `part_of[lost] = island[lost[0]]` -> `part_of[lost] = island[lost]`  ->
  a_finish_of_crumbs_only_keeps_them_as_one_part_however_small
- finish_parts.py: `return kept_finishes(face_label, labels.without_crumbs(mesh, smoothed))` -> `return
  labels.without_crumbs(mesh, smoothed)`  -> cleaning_never_removes_a_finish_whole
- finish_parts.py: `stray = small & ~np.isclose(area, piece_area[piece[face_of]]) & np.isin(finish, finish[~small])` ->
  `stray = small & ~np.isclose(area, piece_area[piece[face_of]])`  ->
  a_stray_island_takes_the_finish_round_it_and_patchy_paint_is_named
- finish_parts.py: `own = np.where(np.isin(face_label, details), part_of.max() + 1 + island, part_of)` -> `own =
  part_of`  -> islands_of_a_detail_finish_sharing_a_part_are_no_stray
- finish_parts.py: `areas[seen & (face_label == label)].sum()` -> `areas[seen].sum()`  ->
  agreement_counts_against_the_maps
- finish_parts.py: `own = finish.get("colour") and finish["surface"] == finish.get("listed_surface", finish["surface"])`
  -> `own = finish.get("colour")`  -> a_finish_out_of_order_is_found_and_a_see_through_finish_is_known
- finish_ask.py: `if error.code not in REFUSED: raise` -> `if False: raise`  ->
  an_ask_is_made_once_a_timeout_reaches_the_row_and_only_a_refusal_is_asked_again
- finish_parts.py: `if nearest_apart <= COLOUR_DELTA_E:` -> `if False:`  ->
  a_finish_takes_the_nearest_surface_of_its_family_by_colour_or_is_flagged
- finish_parts.py: `if not reordered(lighter, darker, every, lightness, wide) and wide:` -> `if not reordered(lighter,
  darker, every, lightness, wide) and False:`  ->
  a_finish_keeps_the_close_ups_lightness_order_and_glass_keeps_its_own_colour
- finish_parts.py: `if fit and (wide or fit[0] < close_up_apart(finish, every)):` -> `if fit and wide:`  ->
  a_finish_a_little_out_of_order_keeps_it_by_a_nearer_surface_of_either
- finish_parts.py: `if apart > COLOUR_DELTA_E and coloured_cover(finish, every):` -> `if False:`  ->
  a_coloured_see_through_finish_keeps_its_surface_against_its_highlights
- finish_ask.py: `entry = dict(entry, surface=names[codes.index(entry["surface"])])` -> `entry = dict(entry)`  ->
  a_finish_list_reply_is_parsed_to_library_names
- route_views.py: `if record["seen_share"] < SEEN_LEAST * reachable:` -> `if record["seen_share"] < SEEN_LEAST:`  ->
  the_views_cover_every_side_and_find_both_colours
- route_views.py: `while candidates and len(angles) < MOST_VIEWS and not seen.all():` -> `while False:`  ->
  the_coverage_check_adds_a_view_for_faces_the_base_views_miss
- route_views.py: `if record.get("model") is None: return [f"{take}: no raw take` -> `if False: return [f"{take}: no raw
  take`  -> a_model_with_no_file_or_no_take_fails_by_name
- route_list.py: `return (level, cause) if level in levels and cause else (None, None)` -> `return (level, cause) if
  level in levels else (None, None)`  ->
  one_batch_lists_every_take_library_first_and_the_split_gives_every_face_one_finish
- route_split.py: `if found["unassigned"] > 0:` -> `if False:`  ->
  an_unassigned_face_is_a_gap_and_views_that_disagree_are_settled_by_the_squarer_view
- route_split.py: `own = np.where((votes.sum(1) > 0) & ~tied, votes.argmax(1), -1)` -> `own = np.where(votes.sum(1) >
  0, votes.argmax(1), -1)`; and, apart, `votes[seen, label[seen]] += square * (` -> `votes[seen, label[seen]] += 1.0 * (`
  -> an_unassigned_face_is_a_gap_and_views_that_disagree_are_settled_by_the_squarer_view
- route_split.py `split_take`: the old colour check put back, a fault when a labelled region's sRGB lies over
  150 from its finish's token colour (`fault = split_fault(found) or next(...)`)  ->
  the_split_decides_by_the_labels_alone
- route_views.py `laid_close_up`: `if fit < cast.CLOSE_UP_FIT:` -> `if True:` (no close-up ever laid)  ->
  a_finish_only_the_close_up_shows_gets_its_region_its_faces_and_a_part (2026-10-29)
- route_views.py: `centres = merged_centres(every, fine_centres(every, seed))` -> `centres = kmeans2(every,
  REGIONS, seed=seed, minit="++")[0]`  -> a_small_colour_far_from_the_rest_keeps_a_region_of_its_own
- route_views.py: `every_faces[CLOSE_UP], every_colours[CLOSE_UP] = laid` -> `pass`  ->
  a_finish_only_the_close_up_shows_gets_its_region_its_faces_and_a_part
- route_split.py: `return close_up_only(votes, per_map)` -> `return votes`  ->
  a_finish_only_the_close_up_shows_gets_its_region_its_faces_and_a_part
- route_list.py: `failing.append(f"{take}: no finish list" + (f" ({asked['unanswered'][take]})"` ->
  `failing.append(f"{take}: no finish list" + ("" if True else f" ({asked['unanswered'][take]})"`  ->
  a_take_with_no_usable_answer_is_a_gap_named_by_the_list
- route_parts.py: `np.save(folders["out"] / "parts.npy", part_of.astype(np.int32))` -> `np.save(folders["out"] /
  "parts.npy", part_of[:1].astype(np.int32))`  ->
  the_parts_row_writes_the_methods_interface_each_finish_checked_against_its_colour
- route_parts.py: `and not lamps.on_stem({"size": built.get("size")})` -> `and True`  ->
  a_light_built_in_code_takes_the_glowing_surface_nearest_its_colour; so does `zip(checked, lit if any(lit) else
  [True] * len(checked))` -> `zip(checked, [True] * len(checked))` (the light bar's metal end caps glowing)
- route_bake.py: `surface=route_settings.settings_name(record["surface"], record["settings"])` ->
  `surface=record["surface"]`  ->
  the_bake_paints_and_bakes_each_take_in_one_card_job_with_the_lists_settings_and_the_paint_takes_it_over
- route_check.py: `library.by_library = lambda name: {**palette_library.specs(palette), **baked}` -> `library.by_library
  = lambda name: {**palette_library.specs(palette)}`  -> the_check_holds_each_surface_against_the_spec_the_bake_baked
- route_recheck.py: `**({"colour": tokens[settings["token"]]} if settings.get("token") in tokens else {}),` deleted  ->
  the_recheck_words_a_finish_in_the_token_it_is_drawn_and_baked_in
- route_recheck.py: `wrong = failed(finishes, answers)` -> `wrong = []`  ->
  the_recheck_sorts_one_answer_into_pass_or_a_gap_its_suggestion_unapplied
- route_recheck.py: `if faults: found[take] = {"colour_faults"` -> `if False: found[take] = {"colour_faults"`  ->
  the_recheck_makes_an_unanswered_take_a_gap_and_never_asks_a_take_off_its_colour
- scene_palette.py: `tokens.setdefault(entry["token"], entry["colour"].lower())` -> `tokens[entry["token"]] =
  entry["colour"].lower()`  -> the_palette_is_read_from_the_locked_concept_by_one_ask
- scene_palette.py: `if parsed["wear"] not in levels or parsed["dirt_token"] not in tokens:` -> `if False:`  ->
  a_palette_off_the_library_or_unanswered_or_too_narrow_fails_by_name
- scene_palette.py: `left_out="Leave out colours only the people in it wear. " if own else "",` -> `left_out="Leave out
  colours only the people in it wear. ",`  -> a_line_no_scene_owns_is_asked_over_every_concept
- scene_palette.py: `close_ups=CLOSE_UPS.format(count=len(close_ups)) if close_ups else "",` -> `close_ups="",`  ->
  the_palette_sees_every_take_s_close_up_after_the_concepts
- scene_library.py: `for colour in surface.get("colours") or [] if colour["setting"] in needs})` -> `for colour in
  surface.get("colours") or []})`  -> the_scene_s_surfaces_are_made_fresh_from_its_palette_and_kinds_by_one_ask
- scene_library.py: `for kind in kinds if not found.get("kinds", {}).get(kind)]` -> `for kind in kinds if False]`  ->
  a_scene_library_missing_a_kind_or_unanswered_fails_by_name
- scene_library.py: `parts.add("stair")` -> `pass`  ->
  the_shell_a_locked_plan_lays_is_a_kind_the_scene_library_must_cover
- scene_library.py: `for name, defaults in method["recipes"].items() if name not in PICTURED}` -> `for name, defaults in
  method["recipes"].items()}`  -> a_scene_library_offers_and_keeps_no_recipe_that_paints_a_picture
- scene_library.py: `if recipe and row.get("noun"):` -> `if False:`  ->
  a_scene_s_ground_rows_take_their_natural_ground_by_rule
- tools/props/library/library.py: `if missing: raise LibraryEmpty` -> `if False: raise LibraryEmpty`  ->
  the_empty_library_is_a_named_missing_input
- palette_library.py: `"stair": ("stairs", "stair", "steps", "ramp", "floor")}` -> `"stair": ("stairs", "stair",
  "steps", "ramp")}`  -> the_scene_s_shell_surfaces_are_its_library_s_for_the_shell_kinds
- route_ask.py: `compute.require_cleared(f"a Gemini batch ({caller})")` deleted  ->
  paid_asks_refuse_outside_a_cleared_run
- route_ask.py: `if not all(google_spend.cache_path(finish_ask.LIST_MODEL, body).exists() for body in bodies.values()):`
  -> `if True:`  -> paid_asks_refuse_outside_a_cleared_run
- route_ask.py: `google_spend.cache_path(finish_ask.LIST_MODEL, body).unlink(missing_ok=True)` -> `pass`  ->
  an_answer_that_does_not_parse_is_a_gap_dropped_from_the_cache
- __init__.py: `route_data.shape_files, selects=True),` -> `route_data.shape_files),`  ->
  the_object_filter_keys_only_a_selecting_row
- __init__.py: `after=reads("finish-route-palette", scene_library.ROW, "surfaces-bake", "surfaces-paint",` ->
  `after=reads(scene_library.ROW, "surfaces-bake", "surfaces-paint",`  -> the_route_is_the_default_line
- bake_job.py: `if inline is None: raise NoEntry` -> `if inline is None: return {"name": model} raise NoEntry`  ->
  an_entry_the_data_writes_out_is_taken_as_written_and_a_model_with_none_stops_the_bake
- bake_job.py: `return TURNS[min(TURNS, key=misfit)]` -> `return TURNS[0]`  ->
  a_design_entry_written_without_a_turn_is_turned_by_its_take_s_measured_footprint
- bake_job.py: `size = inline["size"] if built else boxed(...)` -> `size = inline["size"]` (no correction), `off(drawn,
  said) <= limit or` dropped from boxed (a box within the row's spread corrects), or `or off(own, drawn) > limit`
  dropped (the box alone corrects), or `wide > tall or` dropped (a stove top's height grown from above)  -> a_pixal3d_take_keeps_its_own_width_for_height_
  only_where_its_box_and_take_both_disagree_with_its_row
- route_bake.py: `if kept or not tumble.tumbled(laid):` -> `if True:`, or tumble.py: `return f"its design lays it
  lying ({said})"` -> `return None`  -> a_rolled_take_is_stood_square_and_a_lying_one_keeps_its_pose
- bake_check.py: `and record["square"]["loose"] > tumble.LOOSE]` -> `and False]`  ->
  the_check_fails_a_tumbled_bake_by_name_with_its_angle_and_leaves_a_lying_one_out
- route_bake.py: `opening = min(span, float(recess["wide"]) + room * (1.0 if room_side else 2.0))` -> `opening =
  min(span, float(recess["wide"]))`  -> a_swinging_door_at_full_open_touches_nothing_in_its_recess
- route_bake.py: `depth = min(float(recess["depth"]), 2 * half - RECESS_BACK)` -> `depth = 2 * half + RECESS_OUT` (a
  tunnel), or `low[across], high[across] = middle - opening / 2, middle + opening / 2` -> the door's own `along`
  unkept  -> a_moving_door_s_holder_bakes_with_a_recess_behind_it_and_the_recess_has_a_back
- bake_job.py: `if built or slender(size):` -> `if slender(size):` (laid_size)  ->
  a_code_build_bakes_at_its_own_section_its_longest_side_the_row_s; -> `if False:`  -> that one and
  a_slender_design_entry_keeps_its_take_s_own_proportions_its_longest_side_the_row_s
- surface_data.py: `"bake scripts": "{repo}/tools/props/library/inside", "library": "{data}/library"}` -> `"bake
  scripts": "{repo}/tools/props/library/inside", "library": "{data}/library", "details": "{data}/library/details.json"}`
  -> every_place_s_bake_is_written_from_git_or_blocks_on_a_named_entry
- body_faces.py: `for body in settings.checked(concept(store)["setting"])["bodies"] if body.get("kelvin") is None]` ->
  `for body in settings.checked(concept(store)["setting"])["bodies"]]`  ->
  every_body_that_does_not_shine_has_a_paid_row_of_its_own
- body_faces.py: `"recipe": {"type": "STRING", "enum": [recipe]},` -> `"recipe": {"type": "STRING", "enum":
  list(method["recipes"])},`  -> the_face_is_made_from_one_ask_in_the_methods_recipes
- body_faces.py: `failing += [f"recipe {variant['recipe']} is no natural ground"] * (variant["recipe"] not in
  natural_grounds.RECIPES)` deleted  -> a_face_off_its_palette_or_the_method_fails_and_no_answer_is_named
- body_faces.py: `if recipe is None: raise ValueError` -> `if False: raise ValueError`  ->
  a_body_whose_physics_the_setting_lacks_gets_no_face
- claude_asks.py: `"finish-route-list", ` deleted from ROWS  -> the_four_asks_go_to_claude_and_the_faces_stay
- claude_asks.py: `module.ask = gemini` -> `pass`  -> the_four_asks_go_to_claude_and_the_faces_stay
- claude_asks.py: `again[take] = repaired(bodies[take], answer, off, levels)` -> `pass`  ->
  a_palette_answer_off_its_own_palette_is_asked_once_more_told_why
- place_line.py: `return turn.T` -> `return None` in `recovered_turn`  ->
  the_paint_reads_the_finish_s_turn_off_the_final_model_whatever_code_stood_it
"""
import inspect
import io
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import urllib.error

import numpy as np
import pytest
import trimesh
from PIL import Image
from trimesh.visual.material import PBRMaterial

REPO = pathlib.Path(__file__).resolve().parents[3]

from score import checks, graph, stages  # noqa: E402
from score.review import setting as settings  # noqa: E402
from score.stages import shapes_first, surfaces  # noqa: E402
from score.stages.surfaces import (bake_check, body_faces, carry, claude_asks, finish_ask, finish_parts, library_reads,  # noqa: E402
                                   palette_library, place_line, registry, route_ask, route_bake, route_cast,
                                   route_check, route_data, route_list, route_paint, route_parts, route_recheck,
                                   route_settings, route_split, route_views, scene_library, scene_palette,
                                   surface_data, surface_gates)
from score.store import PROPS_HOME, Store, text_hash  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402

import bake_job  # noqa: E402  (place_line puts its folder and tools/props/library on the path)
import library  # noqa: E402
import place_route  # noqa: E402
import route  # noqa: E402

# No designed place's hand-in (the home's design/, which the sandbox links) is read here: prepare's test holds those.
prop_data.DESIGN = surface_data.DESIGN = pathlib.Path(tempfile.mkdtemp()) / "no design"
surfaces.data.DESIGN = surface_data.DESIGN  # the table's own import of it (bare `surface_data`)
ROWS = {row.name: row for row in stages.STAGES}


# --- surfaces ---

def a_store():
    return Store.in_folder(tempfile.mkdtemp())


def test_a_proposed_library_surface_stands_as_first_proposed():
    store = a_store()
    first = registry.Registry(store).propose_surface("Aluminium tape, silver", {"stands_in": "galvanized_dull"},
                                                     {"take": "a"})
    second = registry.Registry(store).propose_surface("Aluminium tape, silver", {"stands_in": "bare_steel"},
                                                      {"take": "b"})
    assert first["spec"] == second["spec"] == {"stands_in": "galvanized_dull"}
    assert len(store.registry("surfaces")) == 1


def test_names_alike_but_for_case_stand_as_one_entry():
    store = a_store()
    first = registry.Registry(store).propose_surface("Polished Chrome", {"stands_in": "pipe_steel"}, {"take": "a"})
    second = registry.Registry(store).propose_surface("polished chrome", {"stands_in": "bare_steel"}, {"take": "b"})
    assert second == first and len(store.registry("surfaces")) == 1
    other = registry.Registry(store).propose_surface("Polished brass", {"stands_in": "brass"}, {"take": "c"})
    assert other["name"] == "Polished brass" and len(store.registry("surfaces")) == 2


def test_the_paint_takes_the_method_s_surface_and_records_its_proposal():
    store = a_store()
    rows = [{"part": 0, "judge": "dark_panel", "proposed": None},
            {"part": 1, "judge": "galvanized_dull", "proposed": {"name": "aluminium tape", "description": "shiny",
                                                                  "why": "thinner than steel"}}]
    found = surfaces.place_line.method_surfaces("power_unit-r3", "old_station", rows, registry.Registry(store))
    assert [record["surface"] for record in found] == ["dark_panel", "galvanized_dull"]
    assert found[1]["proposed"]["stands_in"] == "galvanized_dull" and found[1]["proposed"]["status"] == "proposed"
    assert [entry["name"] for entry in store.registry("surfaces")] == ["aluminium tape"]


def test_each_take_is_painted_by_one_place_and_every_claim_is_baked_by_its_place():
    owner = {}
    records = {path.stem: json.loads(path.read_text()) for path in sorted(surface_data.FOLDER.glob("*.json"))}
    for place, record in records.items():
        assert (REPO / "data/kit" / f"{place}.json").exists() or shapes_first.no_place(place), f"{place}: no such place"
        assert record["takes"] or record.get("nothing"), f"{place}: lists nothing to paint and says not why"
        assert surface_data.paints(place) == bool(record["takes"]), place
        for take, entry in record["takes"].items():
            assert take not in owner, f"{take}: painted by {owner.get(take)} and {place}"
            owner[take] = place
            assert {"place", "kind", "object", "library_places"} <= set(entry), f"{place} {take}"
        bake = record.get("bake")
        if bake:
            assert set(bake["models"].values()) <= set(record["takes"]), f"{place}: bakes a take it does not paint"
    for place, record in records.items():
        for model, claim in record.get("elsewhere", {}).items():
            other = records[claim["place"]]
            assert claim["take"] in other["takes"], f"{place} {model}: {claim['place']} does not paint {claim['take']}"
            assert claim["take"] in other["bake"]["models"].values(), f"{place} {model}: {claim['place']} bakes none"


def test_every_place_s_surface_line_is_rows_of_world_one():
    names = [stage.name for stage in stages.STAGES]
    assert {"finish-route-palette", "surface-library", "finish-route-views", "finish-route-list", "finish-route-split",
            "surfaces-parts", "surfaces-paint", "surfaces-bake", "finish-route-recheck", "surfaces-check"} <= set(names)
    rows = {stage.name: stage for stage in surfaces.ROWS}
    assert all(stage.grain == "place" for stage in surfaces.ROWS)
    # the scene's surfaces made fresh from its palette before anything is listed (owner, 2026-10-21)
    assert set(rows["surface-library"].after) == {"finish-route-palette"}
    for row in ("finish-route-list", "surfaces-parts", "finish-route-recheck", "surfaces-check"):
        assert "surface-library" in rows[row].after, row
    # the method's interface, painted in the bake at the scene palette's wear and dirt (read from its design)
    assert set(rows["surfaces-bake"].after) == {"finish-route-palette", "surface-library", "surfaces-parts"}
    assert set(rows["surfaces-paint"].after) == {"surfaces-bake"}  # the bake's painted takes, the paint's gates
    assert all(stage.euros for stage in surfaces.ROWS if stage.paid)


def test_a_method_change_moves_only_the_rows_that_read_the_library():
    """The surface-library row and the finish route's list, parts, paint, bake, recheck and check read the method's
    library (its recipes); its views and split never do, so a recipe's new default makes the scene's surfaces again
    and re-asks the list, and leaves the renders and their regions where they stood (the split reads the list's
    answers: identical answers keep its key, the graph's own test). The palette row reads its wear levels alone."""
    data, home = pathlib.Path(tempfile.mkdtemp()), pathlib.Path(tempfile.mkdtemp())
    for folder in ("library", "definitions"):
        shutil.copytree(REPO / "data" / folder, data / folder)
    (data / "surfaces").mkdir()
    (data / "surfaces/greenhouse.json").write_text(json.dumps({"place": "greenhouse", "library": "greenhouse", "takes": {
        "crate-t1": {"place": "greenhouse", "kind": "crate", "object": "a crop crate"}},
        "bake": {"models": {"crate_1": "crate-t1"}}}))  # its own surface data (the old greenhouse's were retired)
    world = graph.Environment("world1", 1, {"data": str(data), "home": str(home), "repo": str(REPO), "seeds": str(home)})
    runner = graph.Runner(surfaces.ROWS, world, a_store(), model_record=lambda kind: {"kind": kind})
    for stage in surfaces.ROWS:  # each file a row names, written small in the test's own home
        for name in runner.files_of(stage, "greenhouse"):
            path = runner.file_path(stage, name, "greenhouse")
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name)
    before = {stage.name: runner.file_keys(stage, "greenhouse") for stage in surfaces.ROWS}
    library = json.loads((data / "library" / "materials.json").read_text())
    library["recipes"]["rubber"]["roughness"] = 0.8
    (data / "library" / "materials.json").write_text(json.dumps(library))
    moved = {stage.name for stage in surfaces.ROWS if runner.file_keys(stage, "greenhouse") != before[stage.name]}
    assert moved == {"surface-library", "finish-route-list", "surfaces-parts", "surfaces-paint",
                     "surfaces-bake",
                     "finish-route-recheck", "surfaces-check"}, moved
    library["wear_levels"]["scarred"] = 1.0
    (data / "library" / "materials.json").write_text(json.dumps(library))
    palette = next(stage for stage in surfaces.ROWS if stage.name == "finish-route-palette")
    assert runner.file_keys(palette, "greenhouse") != before["finish-route-palette"]
    shutil.rmtree(data)
    shutil.rmtree(home)


def test_a_place_without_data_blocks_before_anything_is_spent_and_one_with_nothing_to_paint_has_no_rows():
    kept, surfaces.data.FOLDER = surfaces.data.FOLDER, pathlib.Path(tempfile.mkdtemp())
    (surfaces.data.FOLDER / "tube.json").write_text(json.dumps({"place": "tube", "takes": {},
                                                                "nothing": "code-built pieces only"}))
    try:
        blocked_without_data()
    finally:
        shutil.rmtree(surfaces.data.FOLDER)
        surfaces.data.FOLDER = kept


def blocked_without_data():
    """A place with no surface data blocks at its first row and its bake; one with data listing nothing has none."""
    world = graph.Environment("world1", 1, {"data": str(REPO / "data"), "home": tempfile.mkdtemp(), "repo": str(REPO),
                                      "seeds": tempfile.mkdtemp()})
    runner = graph.Runner(surfaces.ROWS, world, a_store(), model_record=lambda kind: {"kind": kind})
    rows = {stage.name: stage for stage in surfaces.ROWS}
    assert "its input surfaces is missing" in runner.node_status(rows["finish-route-views"], "nowhere")
    assert not any(node.endswith("@tube") for node in runner.status(["tube"]))  # code-built pieces only
    try:
        runner.file_keys(rows["surfaces-bake"], "nowhere")
    except graph.Blocked as block:
        assert "nowhere.json" in str(block)
        return
    raise AssertionError("a place with no data did not block at its bake row")


def test_a_gate_that_cannot_read_its_evidence_answers_unknown():
    folder = pathlib.Path(tempfile.mkdtemp())
    def judge_takes(output, inputs, evidence):  # a gate that reads its output's takes.json, as the route's do
        return json.loads((pathlib.Path(output) / "takes.json").read_text())
    check = surface_gates.guarded("views cast", judge_takes)
    found = checks.judge(check, folder, {}, None)
    assert found.answer == checks.UNKNOWN and "takes.json" in found.reason
    shutil.rmtree(folder)


# The seed tray's paper label on black plastic, as baked (greenhouse bake output 439948bc): each of its 65 triangles'
# baked L*a*b*, area (to the largest), the surfaces within its reach (potting_soil, printed_paper, tray_plastic) and
# whether its corners straddle a part border. 19 of them bake the plastic's near black.
SEED_TRAY_PAPER = [
    (79.2, -0.7, 7.6, 0.1987, "011", False),
    (79.2, -0.7, 7.6, 0.8008, "011", False),
    (9.9, 0.7, -0.5, 0.2788, "011", True),
    (79.2, -0.7, 7.6, 0.534, "011", False),
    (9.3, 0.5, -1.4, 0.4221, "011", True),
    (9.9, 0.7, -0.5, 0.1251, "011", True),
    (9.9, 0.7, -0.5, 0.1117, "011", True),
    (9.9, 0.7, -0.5, 0.1437, "011", True),
    (9.9, 0.7, -0.5, 0.4054, "111", True),
    (79.2, -0.7, 7.6, 0.2535, "011", False),
    (9.9, 0.7, -0.5, 0.1022, "011", True),
    (78.8, -0.7, 7.7, 0.8483, "111", False),
    (10.0, 1.2, -0.3, 0.4276, "011", True),
    (77.7, -0.7, 7.7, 0.5298, "011", False),
    (79.2, -0.7, 7.6, 0.3602, "011", False),
    (79.2, -0.7, 7.6, 0.2877, "011", False),
    (78.5, -0.5, 7.2, 0.5201, "011", False),
    (77.0, -0.7, 7.7, 0.2867, "011", False),
    (75.1, -1.1, 7.6, 0.3235, "011", False),
    (79.2, -0.7, 7.6, 0.1694, "011", False),
    (79.2, -0.7, 7.6, 0.676, "011", False),
    (74.5, -0.5, 7.2, 0.0633, "011", False),
    (74.9, -0.5, 7.2, 0.1252, "011", True),
    (20.8, -0.0, 1.4, 0.105, "011", True),
    (72.3, -0.5, 7.3, 0.3978, "011", True),
    (79.2, -0.7, 7.6, 0.226, "011", False),
    (76.7, -0.7, 7.7, 0.608, "011", True),
    (79.2, -0.7, 7.6, 0.7381, "011", True),
    (10.0, 1.2, -0.3, 0.0822, "011", True),
    (74.1, -0.5, 7.2, 0.2326, "011", False),
    (74.1, -0.5, 7.2, 0.1202, "010", False),
    (79.2, -0.7, 7.6, 0.0853, "011", True),
    (79.2, -0.7, 7.6, 0.4938, "011", False),
    (78.1, -0.7, 7.7, 0.3396, "011", False),
    (10.7, 1.7, 1.4, 0.1247, "011", True),
    (75.6, -0.5, 7.2, 0.5145, "011", False),
    (79.2, -0.7, 7.6, 0.896, "011", False),
    (79.2, -0.7, 7.6, 0.1385, "011", False),
    (78.8, -0.7, 7.7, 0.6235, "111", False),
    (9.9, 0.7, -0.5, 0.3203, "111", True),
    (79.2, -0.7, 7.6, 0.1366, "011", False),
    (9.9, 0.7, -0.5, 0.757, "111", True),
    (65.5, -0.5, 6.3, 0.118, "011", False),
    (79.2, -0.7, 7.6, 0.0903, "011", False),
    (9.4, 1.0, -1.2, 0.0811, "011", False),
    (73.0, -0.5, 7.3, 0.4309, "011", True),
    (79.2, -0.7, 7.6, 0.5007, "011", False),
    (10.0, 1.2, -0.3, 0.125, "011", True),
    (9.3, 0.5, -1.4, 0.4311, "011", True),
    (75.6, -0.5, 7.2, 0.3532, "011", False),
    (77.7, -0.7, 7.7, 0.5297, "011", False),
    (78.8, -0.7, 7.7, 0.5839, "011", False),
    (79.2, -0.7, 7.6, 0.1448, "011", True),
    (79.2, -0.7, 7.6, 1.0, "011", False),
    (10.7, 1.7, 1.4, 0.4031, "011", True),
    (10.7, 1.7, 1.4, 0.2377, "011", True),
    (79.2, -0.7, 7.6, 0.098, "011", False),
    (79.2, -0.7, 7.6, 0.6058, "111", True),
    (10.0, 1.2, -0.3, 0.2574, "011", False),
    (74.5, -0.5, 7.2, 0.2059, "011", False),
    (79.2, -0.7, 7.6, 0.1615, "011", False),
    (9.4, 1.0, -1.2, 0.5341, "011", True),
    (77.7, -0.7, 7.7, 0.6325, "011", False),
    (76.3, -0.7, 7.7, 0.4506, "011", False),
    (71.5, -0.5, 7.3, 0.4865, "011", True),
]


SEED_TRAY_SURFACES = [(30.5, 7.6, 15.6), (79.2, -0.7, 7.6), (9.3, 0.5, -1.4)]


def paper_record(rows):
    colour = np.array([row[:3] for row in rows])
    reach = np.array([[flag == "1" for flag in row[4]] for row in rows])
    share = bake_check.blotch_share(colour, np.array([row[3] for row in rows]), np.ones(len(rows), dtype=bool), reach,
                                    [[surface] for surface in SEED_TRAY_SURFACES])
    return {"surfaces": {"printed_paper": {"share": 0.0117, "baked_lab": [77.7, -0.7, 7.7],
                                           "surface_lab": list(SEED_TRAY_SURFACES[1]), "delta_e": 1.5,
                                           "near_black": share}}}


def test_a_clean_label_border_passes_and_a_black_smudge_along_it_fails():
    assert bake_check.surface_faults("seed_tray_1", paper_record(SEED_TRAY_PAPER)) == []
    smudge, area = [], 0.0  # light triangles across the label's border turned black until a tenth of its area
    total = sum(row[3] for row in SEED_TRAY_PAPER)
    for row in SEED_TRAY_PAPER:
        if row[5] and row[0] > bake_check.BLOTCH_L and area < 0.1 * total:
            row, area = (0.0, 0.0, 0.0, *row[3:]), area + row[3]
        smudge.append(row)
    faults = bake_check.surface_faults("seed_tray_1", paper_record(smudge))
    assert len(faults) == 1 and "printed_paper" in faults[0] and "near black" in faults[0], faults
    # the table wraps the make (stages/gaps.py: an accepted gap moves a fault, the wrapper unwraps to the judge); the
    # finish route's check is bake_check's against the bake's specs (route_check.py)
    assert inspect.unwrap({stage.name: stage for stage in stages.STAGES}["surfaces-check"].make) \
        is route_check.make_check


# The flat's quilt_cotton as the library resolves it (linear RGB): red cotton, ink-line seams as its second.
QUILT_COTTON = {"colour": [0.2542, 0.0782, 0.0648], "second": [0.00304, 0.00273, 0.00243]}


def quilt_record(spec):
    """A quilt baked as its recipe draws it (6% of its area the seams' near black, 94% its red; flat bake of
    2026-10-13), its blotch share measured against `spec`'s colours."""
    shades = bake_check.library_shades(spec)
    colour = np.array([shades[0]] * 94 + [bake_check.library_shades(QUILT_COTTON)[1]] * 6)
    share = bake_check.blotch_share(colour, np.ones(100), np.ones(100, dtype=bool), np.ones((100, 1), dtype=bool),
                                    [shades])
    return {"surfaces": {"quilt_cotton": {"share": 1.0, "baked_lab": [round(float(value), 1) for value in shades[0]],
                                          "surface_lab": [round(float(value), 1) for value in shades[0]],
                                          "delta_e": 0.0, "near_black": share}}}


def test_a_surfaces_own_drawn_seams_are_not_blotches():
    assert bake_check.surface_faults("quilt_1", quilt_record(QUILT_COTTON)) == []
    faults = bake_check.surface_faults("quilt_1", quilt_record({"colour": QUILT_COTTON["colour"]}))
    assert len(faults) == 1 and "near black" in faults[0], faults


def test_a_finish_judged_by_its_own_colour_is_not_compared_with_its_close_up():
    """The garage beacon: its red transparent dome measured pale pink on its brighter half (its highlights and what
    lies behind it), so the paint keeps red_plastic by its own colour; the bake check leaves it out of the close-up
    too. The opaque knob of the same surface is still compared."""
    dome = {"finish": "Red transparent plastic", "surface": "red_plastic", "measured_lab": [70.8, 21.2, 11.5],
            "by": "its own colour", "cover": True}
    label = {"finish": "Printed label", "surface": "printed_paper", "measured_lab": [30.0, 5.0, 5.0],
             "by": "its own colour"}  # print off its listed colour: judged by its own colour, still in the close-up
    knob = {"finish": "Red plastic", "surface": "red_plastic", "measured_lab": [40.0, 55.0, 40.0], "by": "the list"}
    with tempfile.TemporaryDirectory() as scratch:
        folder = pathlib.Path(scratch)
        (folder / "labels.json").write_text(json.dumps({"finishes": [dome]}))
        assert bake_check.close_up_colours(folder) == {}
        (folder / "labels.json").write_text(json.dumps({"finishes": [dome, label]}))
        assert bake_check.close_up_colours(folder) == {"printed_paper": [30.0, 5.0, 5.0]}
        (folder / "labels.json").write_text(json.dumps({"finishes": [dome, knob]}))
        assert bake_check.close_up_colours(folder) == {"red_plastic": [40.0, 55.0, 40.0]}
    red = [38.5, 57.0, 47.5]
    assert bake_check.close_up_faults("beacon_1", baked_record({"red_plastic": (1.0, red)}, {})) == []
    faults = bake_check.close_up_faults("beacon_1", baked_record({"red_plastic": (1.0, red)},
                                                                 {"red_plastic": dome["measured_lab"]}))
    assert len(faults) == 1 and "red_plastic" in faults[0], faults


WATER_TANK_CLOSE_UP = {"painted_panel": [80.3, -0.2, 6.0], "bare_steel": [67.3, -0.3, 1.0],
                       "tank_water": [53.2, -3.2, -2.3]}  # the finish-map method's measures, greenhouse, 2026-10-12


def test_a_surface_with_the_list_s_settings_is_compared_with_its_close_up():
    """astronaut-made (2026-10-23): the bake names a part with the list's settings by them (route_settings), so the
    close-up keyed by the variant alone compared nothing; keyed as the part bakes, boots baked L* 65.5 against their
    close-up's 33 fail. A finish the colour check moved to another surface bakes under that surface's own name."""
    settings = {"token": "glass-grey", "roughness": 0.85, "metal": 0.0, "seed": 7}
    boots = {"finish": "boots", "surface": "suit_boots", "listed_surface": "suit_boots", "settings": settings,
             "measured_lab": [33.1, 0.9, 7.6]}
    moved = {"finish": "belt", "surface": "rubber_dark", "listed_surface": "suit_boots", "settings": settings,
             "measured_lab": [20.0, 0.0, 0.0]}
    named = route_settings.settings_name("suit_boots", settings)
    with tempfile.TemporaryDirectory() as scratch:
        folder = pathlib.Path(scratch)
        (folder / "labels.json").write_text(json.dumps({"finishes": [boots, moved]}))
        close_up = bake_check.close_up_colours(folder)
    assert close_up == {named: [33.1, 0.9, 7.6], "rubber_dark": [20.0, 0.0, 0.0]}, close_up
    faults = bake_check.close_up_faults("body", baked_record({named: (1.0, [65.5, 0.0, 0.0])}, close_up))
    assert len(faults) == 1 and named in faults[0] and "33.3" in faults[0], faults


def baked_record(surfaces, close_up, degrees=None):
    """A checks.json record of a model baked exactly on its surfaces ({surface: (share, L*a*b*)})."""
    return {"surfaces": {name: {"share": share, "baked_lab": list(colour), "surface_lab": list(colour),
                                "delta_e": 0.0, "near_black": 0.0} for name, (share, colour) in surfaces.items()},
            "close_up": close_up, "seen_degrees": degrees}


# The water tank's surfaces as the greenhouse's library gave them when it was fixed (2026-10-12), L*a*b*: the
# check's measured case, kept as numbers since every old material was retired (2026-10-21).
TANK_SURFACES = {"bare_steel": [66.3, -1.1, -4.5], "tank_water": [41.5, -3.2, -6.9], "cream_paint": [79.2, -0.7, 7.6]}


def test_the_water_tank_s_reversed_greys_fail_and_its_cream_paint_passes():
    before = baked_record({"painted_panel": (0.7253, [61.6, -1.5, -6.5]), "bare_steel": (0.1536, [66.3, -1.1, -4.5]),
                           "tank_water": (0.1212, [58.7, -1.7, 2.4])}, WATER_TANK_CLOSE_UP)  # its stored check
    before["seen_degrees"] = 23.83  # 1.4 m wide, 3.3 m from the greenhouse's nearest view
    faults = bake_check.surface_faults("water_tank_1", before)
    # its water bakes 8.9 b* off its paint, 1.9 noticeable differences at that size: told apart, not one look
    assert len(faults) == 1 and "painted_panel is 13.0 L* lighter than bare_steel" in faults[0], faults
    grey_body = baked_record({"painted_panel": (0.7253, [61.6, -1.5, -6.5]),
                              "bare_steel": (0.1536, TANK_SURFACES["bare_steel"]),
                              "tank_water": (0.1212, TANK_SURFACES["tank_water"])}, WATER_TANK_CLOSE_UP, 23.83)
    faults = bake_check.surface_faults("water_tank_1", grey_body)  # the water fixed, the body still grey
    assert len(faults) == 1 and "lighter than bare_steel" in faults[0], faults
    after = baked_record({"cream_paint": (0.7253, TANK_SURFACES["cream_paint"]),
                          "bare_steel": (0.1536, TANK_SURFACES["bare_steel"]),
                          "tank_water": (0.1212, TANK_SURFACES["tank_water"])},
                         {"cream_paint": WATER_TANK_CLOSE_UP["painted_panel"],
                          **{name: WATER_TANK_CLOSE_UP[name] for name in ("bare_steel", "tank_water")}}, 23.83)
    assert bake_check.surface_faults("water_tank_1", after) == [], bake_check.surface_faults("water_tank_1", after)
    one = baked_record({"painted_panel": (1.0, [61.6, -1.5, -6.5])}, {"painted_panel": [80.3, -0.2, 6.0]})
    assert bake_check.surface_faults("panel_1", one) == [], "one surface is one look by design"
    dark = baked_record({"painted_panel": (0.9, [61.6, -1.5, -6.5]), "rubber": (0.1, [9.3, 0.5, -1.4])},
                        {"painted_panel": [61.0, 0.0, 0.0], "rubber": [62.0, 0.0, 0.0]})
    faults = bake_check.surface_faults("cabinet_1", dark)
    assert len(faults) == 1 and "rubber" in faults[0] and "over 32" in faults[0], faults


def test_one_look_fails_only_what_a_viewer_cannot_tell_apart_at_the_place_s_view_distance():
    cover = baked_record({"bare_steel": (0.2813, [66.3, -1.1, -4.5]), "hull_white_scorched": (0.7187, [75.6, -1.2, -1.0])},
                         {"hull_white_scorched": [92.7, -0.3, 0.0], "bare_steel": [65.4, 1.6, 5.6]})
    cover["seen_degrees"] = 11.29  # the wreck's access cover, 4.5 m from wreck-home
    assert bake_check.one_look_faults("access_cover", cover) == [], "9.3 L* at 6 degrees is seen"
    fragment = baked_record({"bare_steel": (0.4118, [64.1, -0.8, -3.2]), "galvanized_steel": (0.4758, [68.6, -1.2, -2.2]),
                             "roof_steel_paint": (0.1123, [63.7, -1.0, -2.7])},
                            {"bare_steel": [51.1, 1.9, 7.0], "galvanized_steel": [89.6, -0.2, 3.6],
                             "roof_steel_paint": [49.7, -1.0, 2.8]})
    fragment["seen_degrees"] = 4.71
    faults = bake_check.one_look_faults("fragment", fragment)
    assert len(faults) == 1 and "one grey look" in faults[0], faults
    del fragment["seen_degrees"]
    faults = bake_check.one_look_faults("fragment", fragment)
    assert len(faults) == 1 and "no view distance" in faults[0], "a gate never passes on what it cannot measure"
    assert abs(bake_check.noticed([50, 0, 0], [55.155, 0, 0], 10.0) - 1.0) < 0.01, "ND(50) of L* at 6 degrees"
    desk = [{"model": "models/hub_kit/comms_1.gltf", "at": [2.0, 0.0, 0.0], "yaw": 90.0,
             "children": [{"model": "models/hub_kit/headset_1.gltf", "at": [1.0, 0.5, 0.0]}]}]
    spots = list(bake_check.object_spots(desk, {"headset_1": {"size": [0.2, 0.2, 0.1]}}))
    assert [model for model, _, _ in spots] == ["headset_1"], "a model laid on a desk the kit does not size is found"
    assert [round(value, 6) for value in spots[0][1]] == [2.0, 0.5, -1.0], spots  # turned by the desk's yaw


def tank_mesh(ends, height=1.6):
    """A tank's (vertices, faces), its own frame (+y up), on four corner legs ending `ends` up (the water tank's
    measured)."""
    body = trimesh.creation.box(bounds=((-0.7, 0.3, -0.7), (0.7, height, 0.7)))
    legs = [trimesh.creation.box(bounds=((across - 0.05, end, along - 0.05), (across + 0.05, 0.3, along + 0.05)))
            for (across, along), end in zip(((-0.6, -0.6), (0.6, -0.6), (-0.6, 0.6), (0.6, 0.6)), ends)]
    mesh = trimesh.util.concatenate([body, *legs])
    return np.asarray(mesh.vertices), np.asarray(mesh.faces)


def test_a_tall_take_s_feet_are_found_in_the_resting_check_s_band():
    """The garage's fluid shelves (2026-10-15): a shelf unit 1.0 tall in its own frame, 2.0 m standing, its bottom
    shelf 0.06 up over four legs, one ending 0.02 up (4 cm). In 15% of its height the shelf joins the legs into one
    foot and nothing is levelled; capped at 10 cm through its standing height (0.05 here) the four legs are its feet and
    the short one is brought down."""
    vertices, faces = tank_mesh((0.0, 0.0, 0.0, 0.02), height=1.0)
    vertices[vertices[:, 1] == 0.3, 1] = 0.06  # the body (and the legs' tops) down to a bottom shelf 0.06 up
    _, wide = place_line.levelled_feet(vertices, faces)
    assert wide["feet"] == 1 and not wide["levelled"], wide
    _, capped = place_line.levelled_feet(vertices, faces, tall=2.0)
    assert capped["feet"] == 4 and len(capped["levelled"]) == 1 and not capped["refused"], capped


def test_a_take_on_two_feet_has_its_short_one_levelled():
    """The engine room's fuel tank (2026-10-15): an upright tank on two cradle feet, one 5.9 cm up, tipped onto it
    when dropped; two feet are levelled as three are."""
    body = trimesh.creation.box(bounds=((-0.4, 0.3, -0.4), (0.4, 2.0, 0.4)))
    cradle = [trimesh.creation.box(bounds=((-0.5, end, along - 0.08), (0.5, 0.3, along + 0.08)))
              for along, end in ((-0.3, 0.0), (0.3, 0.059))]
    mesh = trimesh.util.concatenate([body, *cradle])
    points, record = place_line.levelled_feet(np.asarray(mesh.vertices), np.asarray(mesh.faces), tall=2.0)
    assert record["feet"] == 2 and len(record["levelled"]) == 1 and not record["refused"], record
    assert abs(points[:, 1][np.asarray(mesh.vertices)[:, 2] > 0.2].min()) < 1e-9, "the short foot down on the floor"


def test_a_tall_take_s_leg_ending_over_the_narrow_band_is_still_levelled():
    """The hangar's access stair (2026-10-15): two legs ending 29 and 33 cm up, outside the 10 cm band, were left as
    they were once the band was capped; levelled in the whole band after the narrow one, they come down."""
    vertices, faces = tank_mesh((0.0, 0.0, 0.12, 0.12), height=1.0)
    _, record = place_line.levelled_feet(vertices, faces, tall=2.0)
    assert len(record["levelled"]) == 2 and not record["refused"], record


def test_a_take_another_place_lays_standing_is_levelled_by_its_rows():
    """A hangar laid an old station's parts rack (its `elsewhere`, parts_rack_1 to parts_rack_4) on the floor; the
    old station laid none of its kind, so the rack was never levelled (2026-10-15). Its paint counts the claiming
    place's standing rows: the claimed rack row, never another of its rows. On surface data of the test's own."""
    folder, kept = pathlib.Path(tempfile.mkdtemp()), surfaces.data.FOLDER
    surfaces.data.FOLDER = folder  # the bare surface_data place_line reads (the table's own import)
    (folder / "station.json").write_text(json.dumps({"place": "station", "takes": {"parts_rack-r1": {}}}))
    (folder / "bay.json").write_text(json.dumps({"place": "bay", "takes": {}, "elsewhere": {
        f"parts_rack_{number}": {"take": "parts_rack-r1", "place": "station"} for number in range(1, 5)}}))
    (folder / "inventory.json").write_text(json.dumps({"rows": [
        {"id": "parts_rack", "name": "parts rack", "anchor": "floor"}, {"id": "crane", "anchor": "floor"}]}))
    try:
        inputs = {"surfaces": folder / "station.json", "inventory bay": folder / "inventory.json",
                  "resting rules": REPO / "data/checks/resting.json"}
        rows = place_line.claimed_rows("parts_rack-r1", inputs)
        assert rows and {row["id"] for row in rows} == {"parts_rack"}, rows
        assert place_line.claimed_rows("parts_rack-r1", dict(inputs, **{"inventory bay": None})) == []
    finally:
        surfaces.data.FOLDER = kept
        shutil.rmtree(folder)


def test_a_take_s_short_legs_are_levelled_before_its_bake_and_a_missing_leg_fails_by_name():
    import feet
    vertices, faces = tank_mesh((0.0, 0.022, 0.052, 0.127))
    points, record = place_line.levelled_feet(vertices, faces)
    assert record["feet"] == 4 and len(record["levelled"]) == 3 and not record["refused"], record
    lows = [low for _, low in feet.feet(feet.surface_points(points, faces), 0.15 * 1.6, 0.05)]
    assert len(lows) == 4 and max(lows) - min(lows) < 1e-9, lows
    points, refused = place_line.levelled_feet(*tank_mesh((0.0, 0.0, 0.0, 0.22)))
    assert refused["refused"] == [round(0.22 / max(1.6, 1.4 * 2 ** 0.5), 4)] and not refused["levelled"], refused
    folder = pathlib.Path(tempfile.mkdtemp())
    for found, verdict in ((record, checks.PASS), (refused, checks.FAIL)):
        (folder / "painted.json").write_text(json.dumps({"takes": {"water_tank-r1": {"feet": found}}}))
        judged = place_line.judge_feet(folder, {}, None)
        assert judged.answer == verdict and (verdict == checks.PASS or "water_tank-r1" in judged.findings[0]), judged
    shutil.rmtree(folder)
    paint = {stage.name: stage for stage in stages.STAGES}["surfaces-paint"]
    assert "feet in one plane" in [check.name for check in paint.checks]
    rules = REPO / "data/checks/resting.json"
    tank = {"place": "greenhouse", "kind": "greenhouse_water_tank"}
    glove = {"place": "lab", "kind": "lab_hanging_glove"}  # held on its cabinet, but it hangs: no feet to level
    inventory = folder.parent / f"{folder.name}-inventory.json"
    inventory.write_text(json.dumps({"rows": [
        {"id": "water_tank", "name": "water tank", "anchor": "floor", "thing": "prop:greenhouse_water_tank"},
        {"id": "cabinet", "anchor": "floor"},
        {"id": "glove", "name": "hanging glove", "anchor": "on:cabinet", "thing": "prop:lab_hanging_glove"}]}))
    assert place_line.stands_on_feet(tank, inventory, rules)
    assert not place_line.stands_on_feet(glove, inventory, rules)
    inventory.unlink()


def test_a_designed_place_s_paint_reads_its_hand_in_rows_for_feet_never_the_old_inventory():
    """A designed place's rows are its hand-in's ({home}/design/props/<place>.json, read from its locked concept): the
    paint declares and reads it to tell a take laid loose on the floor from one held, and keys on it, never on the old
    concept's data/inventory file. Its rows name their take (`prop:<take>`) and stand on the floor the reading made a
    row of (`on:<floor row>`)."""
    paint = {stage.name: stage for stage in stages.STAGES}["surfaces-paint"]
    kept, prop_data.DESIGN = prop_data.DESIGN, pathlib.Path(tempfile.mkdtemp())  # the hand-ins apart from surfaces'
    hand_in = prop_data.DESIGN / "greenhouse.json"
    floor = {"id": "floor_plates", "anchor": "ground", "size": [4.0, 5.0, 0.1], "thing": "prop:gh_floor_ab12"}
    rows = [floor,
            {"id": "crate", "name": "crop crate", "anchor": "on:floor_plates", "thing": "prop:gh_crate_ab12"},
            {"id": "jar", "name": "seed jar", "anchor": "on:table", "thing": "prop:gh_jar_ab12"},
            {"id": "table", "name": "work table", "anchor": "floor", "size": [1.5, 0.8, 0.8], "thing": "prop:x"},
            {"id": "wall", "name": "left wall", "anchor": "on:floor_plates", "route": "shell",
             "thing": "prop:gh_wall_ab12"},
            # the cockpit's floor is mounted on its hull, a landing on its stairs: still the floor
            {"id": "hull", "anchor": "ground", "size": [9.0, 9.0, 3.5], "thing": "prop:gh_hull_ab12"},
            {"id": "deck", "anchor": "on:hull", "group": "kit: floor", "size": [9.0, 9.0, 0.1], "route": "shell",
             "thing": "prop:gh_deck_ab12"},
            {"id": "seat", "name": "pilot seat", "anchor": "on:deck", "thing": "prop:gh_seat_ab12"},
            {"id": "lamp", "name": "desk lamp", "anchor": "on:hull", "thing": "prop:gh_lamp_ab12"},
            # a stage on the floor is a floor too; a tin on a box on the floor is held
            {"id": "stage", "anchor": "on:floor_plates", "size": [8.0, 6.0, 1.2], "thing": "prop:x"},
            {"id": "drum", "name": "drum kit", "anchor": "on:stage", "thing": "prop:gh_drum_ab12"},
            {"id": "box", "anchor": "floor", "size": [1.0, 1.0, 1.0], "thing": "prop:x"},
            {"id": "tin", "name": "tin", "anchor": "on:box", "thing": "prop:gh_tin_ab12"}]
    hand_in.write_text(json.dumps({"place": "greenhouse", "rows": rows}))
    kept_surfaces, surfaces.data.FOLDER = surfaces.data.FOLDER, pathlib.Path(tempfile.mkdtemp())  # its surface data
    (surfaces.data.FOLDER / "greenhouse.json").write_text(json.dumps({"place": "greenhouse", "takes": {
        "gh_crate_ab12": {"place": "greenhouse", "kind": "gh_crate"}}}))
    try:
        assert stages.paint_inventory("greenhouse")[0] == "{home}/design/props/greenhouse.json"
        assert paint.files("greenhouse")["inventory greenhouse"][0] == "{home}/design/props/greenhouse.json"
        rules = REPO / "data/checks/resting.json"
        entry = {"place": "greenhouse", "kind": "gh_crate"}  # a designed take's kind lacks its take's suffix
        assert [row["id"] for row in place_line.standing_rows(entry, hand_in, rules, "gh_crate_ab12")] == ["crate"]
        assert not place_line.stands_on_feet(entry, hand_in, rules)  # by kind alone no designed row names it
        assert not place_line.stands_on_feet({"place": "greenhouse", "kind": "gh_jar"}, hand_in, rules, "gh_jar_ab12")
        assert not place_line.stands_on_feet({"place": "greenhouse", "kind": "gh_wall"}, hand_in, rules,
                                             "gh_wall_ab12")
        assert place_line.stands_on_feet({"place": "greenhouse", "kind": "gh_floor"}, hand_in, rules, "gh_floor_ab12")
        for kind, standing in (("gh_seat", True), ("gh_lamp", False), ("gh_drum", True), ("gh_tin", False)):
            assert place_line.stands_on_feet({"place": "greenhouse", "kind": kind}, hand_in, rules,
                                             f"{kind}_ab12") is standing, kind
    finally:
        shutil.rmtree(prop_data.DESIGN)
        shutil.rmtree(surfaces.data.FOLDER)
        prop_data.DESIGN, surfaces.data.FOLDER = kept, kept_surfaces


def test_the_kit_route_s_bake_answers_the_empty_library_by_name():
    """Every old material retired (owner, 2026-10-21): the kit route's bake, which takes the repository's library by
    place, names each painted surface no library holds before anything is rented, never a KeyError."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary) / "take"
        folder.mkdir()
        (folder / "dark_panel.ply").write_text("")
        try:
            place_line.baking_specs("hangar", {}, [folder])
        except RuntimeError as refused:
            assert "surfaces in no library: ['dark_panel']" in str(refused), refused
        else:
            raise AssertionError("a bake was specced from an empty library")


def test_a_killed_paint_on_the_machine_says_its_signal_and_peak():
    sys.path.insert(0, str(REPO / "score/stages/surfaces/inside"))
    import paint_take
    code, peak = paint_take.measured([sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGKILL)"],
                                     dict(os.environ))
    assert code == -9 and peak > 0, (code, peak)


def test_a_take_s_paint_job_sends_what_it_reads_and_brings_its_folder_back():
    with tempfile.TemporaryDirectory() as temporary:
        out, parts = pathlib.Path(temporary) / "out", pathlib.Path(temporary) / "parts"
        out.mkdir()
        own = pathlib.Path(temporary)  # its own surface data and inventory (the old camp grounds' were retired)
        (own / "surfaces.json").write_text(json.dumps({"place": "campgrounds", "library": "campgrounds", "takes": {
            "crane-r1": {"place": "campgrounds", "kind": "crane"}}, "bake": {"models": {"crane": "crane-r1"}}}))
        (own / "inventory.json").write_text(json.dumps({"rows": [{"id": "crane", "anchor": "ground",
                                                                  "thing": "prop:crane"}]}))
        inputs = {"surfaces": own / "surfaces.json", "surfaces-parts": parts,
                  "inventory campgrounds": own / "inventory.json",
                  "resting rules": REPO / "data/checks/resting.json"}
        job = json.loads(place_line.paint_job(inputs, place_line.prop_env.short(inputs), out, "crane-r1",
                                              [{"part": 0}]).read_text())
        assert job["script"] == "score/stages/surfaces/inside/paint_take.py" and job["outputs"] == [
            str(out / "labelled" / "crane-r1")]
        sent = set(job["inputs"])
        assert {str(parts / "crane-r1"), str(parts / "parts.json"), str(REPO / "score"), str(REPO / "tools/props"),
                str(REPO / "data/library")} <= sent, sent
        assert any(path.endswith("work/pixal/crane-r1-final.glb") for path in sent), sent
        listing = json.loads(pathlib.Path(job["args"][0]).read_text())
        assert listing["paint take"] == "crane-r1" and listing["paint repo"] == str(REPO)  # data may lie elsewhere
        assert json.loads(pathlib.Path(listing["paint records"]).read_text()) == [{"part": 0}]


def test_a_bake_is_held_against_its_surface_dirtied_as_far_as_its_place_s_dirt():
    """The wreck: dirt 0.6 in regolith (L* 56.8); its white hull (89.6) bakes to 69.0 and is on its surface; the same
    white at a clean place, or baked darker than its dirt reaches, is not; a wrong surface is not."""
    white, regolith = np.array([89.6, -1.7, 1.6]), np.array([56.8, 0.2, 3.1])
    baked = np.array([69.0, -0.8, -3.2])
    assert bake_check.on_surface(baked, white, regolith, 0.6) < 6
    assert bake_check.on_surface(baked, white, regolith, 0.0) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(np.array([40.0, 0, 0]), white, regolith, 0.6) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(baked, white, None, 0.6) > bake_check.BAKE_DELTA_E


def test_a_bake_is_held_against_its_surface_worn_as_far_as_its_place_s_wear():
    """The engine room, worn 0.8, dirt 0.5: its power core's hazard trim baked a median [73.2, 2.2, 41.3], 20.1 off
    its clean yellow and part worn to bare steel; worn as far as the place's wear it lies on its surface. Unworn, or
    with no bare colour, it does not; a wrong surface (dark_panel) still fails."""
    yellow, bare, soot = np.array([80.5, 3.5, 78.8]), np.array([66.3, -1.1, -4.5]), np.array([13.2, 3.7, 5.9])
    baked = np.array([73.2, 2.2, 41.3])
    assert bake_check.on_surface(baked, yellow, soot, 0.5, bare, 0.8) < 6
    assert bake_check.on_surface(baked, yellow, soot, 0.5, bare, 0.0) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(baked, yellow, soot, 0.5) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(baked, np.array([19.2, -0.7, -3.2]), soot, 0.5, bare, 0.8) > bake_check.BAKE_DELTA_E


def test_wear_passes_only_toward_the_surface_s_bare_colour_and_only_as_far_as_its_place_s_wear():
    """Wear has causes (the paper, Appendix D: the room's wear setting from its use, laid on edges and kicks) and the
    check allows only what those can lay: a yellow worn all the way to bare steel in a place worn 0.4 lies past its
    wear; a yellow darkened toward black (no recipe's bare colour) fails however worn its place; a surface with no
    bare colour has nothing to wear, and in a place with no wear nothing is worn."""
    yellow, bare = np.array([80.5, 3.5, 78.8]), np.array([66.3, -1.1, -4.5])
    worn_through = bare.copy()
    darkened = np.array([50.0, 3.5, 78.8])
    assert bake_check.on_surface(worn_through, yellow, None, 0.0, bare, 0.4) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(darkened, yellow, None, 0.0, bare, 0.8) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(yellow + 0.6 * (bare - yellow), yellow, None, 0.0, None, 0.8) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(yellow + 0.6 * (bare - yellow), yellow, None, 0.0, bare, 0.0) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(yellow + 0.6 * (bare - yellow), yellow, None, 0.0, bare, 0.8) < 1


def test_a_part_s_baked_colour_is_its_area_s_median_on_each_channel():
    """Lab's junction_box_1, bake of 2026-10-14: 56% of its crane_yellow_paint's area baked yellow, 15% between, 29%
    the grey panel at the same L*; a triangle picked by its L* alone was a grey one (dE 37 off the yellow), each
    channel's own median is the yellow the bake wrote."""
    darker, between, grey, lighter = [62.0, 2.0, 38.0], [62.9, 0.5, 17.0], [63.5, -0.7, -4.4], [65.0, 2.0, 38.0]
    colour = np.array([darker] * 28 + [between] * 15 + [grey] * 29 + [lighter] * 28)
    areas = np.ones(len(colour))
    order = np.argsort(colour[:, 0])  # the old pick: the triangle at the area's median L*
    assert colour[order][np.searchsorted(np.cumsum(areas[order]), areas.sum() / 2)].tolist() == grey
    middle = bake_check.area_median(colour, areas)
    assert middle.tolist() == [63.5, 2.0, 38.0], middle
    assert bake_check.area_median(colour, np.array([0.0] * 43 + [1.0] * 29 + [0.0] * 28)).tolist() == grey


def test_a_triangle_under_a_texel_is_named_by_where_the_bake_wrote_its_texel():
    """The flat's bowl stack, bake of 2026-10-13: its glass rims' triangles lie under a texel each, so the texel the
    check samples for one was baked from the centre's point on a neighbour (enamel), and its glass failed at dE 66.6
    while the bake was right. The check names the sampled texel by the ray from that point, as the bake did."""
    enamel = trimesh.creation.box(bounds=[[-1.0, 0.0, -0.05], [0.0, 1.0, 0.05]])
    glass = trimesh.creation.box(bounds=[[0.0, 0.0, -0.05], [1.0, 1.0, 0.05]])
    # one large triangle over the enamel covering texel (0, 0)'s centre in a 2 x 2 texture, one sliver over the glass
    # whose middle falls in that texel but not on its centre
    positions = np.array([[-0.9, 0.1, 0.05], [-0.1, 0.1, 0.05], [-0.5, 0.9, 0.05],
                          [0.4, 0.4, 0.05], [0.6, 0.4, 0.05], [0.5, 0.6, 0.05]])
    uvs = np.array([[0.2, 0.0], [0.5, 0.0], [0.2, 0.45], [0.05, 0.05], [0.12, 0.05], [0.05, 0.12]])
    geometry = {"positions": positions, "uvs": uvs, "triangles": np.array([[0, 1, 2], [3, 4, 5]]),
                "maps": np.array([0, 0])}
    entry = {"base": [1, 0, 0, 0, 1, 0, 0, 0, 1], "size": [2.0, 1.0, 0.1]}
    rows, columns = np.array([0, 0]), np.array([0, 0])
    points, owners = bake_check.sampled_points(geometry, rows, columns, np.array([[2, 2], [2, 2]]))
    assert owners.tolist() == [0, 0], owners
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        enamel.export(folder / "enamel_white.ply")
        glass.export(folder / "glass.ply")
        names, middle_named, _ = bake_check.baked_surfaces(geometry, folder, entry)
        names, texel_named, _ = bake_check.baked_surfaces(geometry, folder, entry, (points, owners))
    assert [names[index] for index in middle_named] == ["enamel_white", "glass"], middle_named
    assert [names[index] for index in texel_named] == ["enamel_white", "enamel_white"], texel_named


def test_a_baked_triangle_beside_a_thin_post_is_named_by_the_bake_s_ray_not_the_nearest_part():
    """far_city's pencil tower, 2026-10-13: the cut-down copy stands 0.6 m proud of the facade; beside a post, the
    post's side lies nearer than the facade the bake's ray meets, so the nearest part named the facade's colour
    post_dark (dE 45). The bake's ray from the triangle inward names the facade; a triangle over the post, the post.
    The check's reach constants are make_chunky's."""
    import ast
    facade = trimesh.creation.box(bounds=[[-5.0, 0.0, -1.0], [5.0, 2.0, 0.0]]).subdivide_to_size(0.1)
    post = trimesh.creation.box(bounds=[[-0.05, 0.0, 0.0], [0.05, 2.0, 1.0]]).subdivide_to_size(0.1)
    beside = [[0.3, 0.9, 0.6], [0.5, 0.9, 0.6], [0.4, 1.1, 0.6]]
    over = [[-0.1, 0.9, 1.6], [0.1, 0.9, 1.6], [0.0, 1.1, 1.6]]
    geometry = {"positions": np.array(beside + over), "triangles": np.array([[0, 1, 2], [3, 4, 5]])}
    entry = {"base": [1, 0, 0, 0, 1, 0, 0, 0, 1], "size": [10.0, 2.0, 2.0]}
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        facade.export(folder / "facade_paint.ply")
        post.export(folder / "post_dark.ply")
        names, surface, reach = bake_check.baked_surfaces(geometry, folder, entry)
        nearest = bake_check.laid_parts(folder, entry)[1].nearest.on_surface([[0.4, 1.0, 0.6]])[0][0]
    assert abs(nearest[0]) <= 0.05 + 1e-9, f"the post lies nearer than the facade behind: {nearest}"
    assert [names[index] for index in surface] == ["facade_paint", "post_dark"], surface
    assert reach[0].all(), "both parts lie within the triangle's reach"
    found = {node.targets[0].id: eval(compile(ast.Expression(node.value), "make_chunky", "eval")) for node in ast.parse(
        (REPO / "tools/props/library/inside/make_chunky.py").read_text()).body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in ("REACH_VOXELS", "REACH_LEAST", "VOXEL_SHARE", "VOXEL_FINEST")}
    assert (found["REACH_VOXELS"], found["REACH_LEAST"], found["VOXEL_SHARE"], found["VOXEL_FINEST"]) == (
        bake_check.BAKE_REACH_VOXELS, bake_check.BAKE_REACH_LEAST, bake_check.BAKE_VOXEL_SHARE,
        bake_check.BAKE_VOXEL_FINEST)


def test_a_standing_model_with_a_foot_off_the_floor_fails_and_lying_wreckage_is_left_out():
    """The hangar's parts rack stood on a middle part, its legs 22 cm up."""
    feet = [(x, z) for x in (-0.5, 0.5) for z in (-0.3, 0.3)]
    level = np.array([[x, 0.0, z] for x, z in feet] + [[0, 1.0, 0]])
    rack = np.array([[x, 0.22 if x > 0 else 0.0, z] for x, z in feet] + [[0, 1.0, 0]])
    assert max(bake_check.stance_lows(level)) == 0.0
    assert abs(max(bake_check.stance_lows(rack)) - 0.22) < 1e-6
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        (folder / "labels.json").write_text(json.dumps({"feet": {"feet": 4}}))
        rows = [{"id": "parts_rack_1", "name": "steel parts rack"}, {"id": "leg_strut", "name": "torn-off landing leg"}]
        assert bake_check.stands("parts_rack_1", folder, rows, ["torn"])
        assert not bake_check.stands("leg_strut", folder, rows, ["torn"])
        (folder / "labels.json").write_text(json.dumps({"feet": {"skipped": "no floor or held row lays its kind"}}))
        assert not bake_check.stands("parts_rack_1", folder, rows, ["torn"])
        (folder / "checks.json").write_text(json.dumps({
            "parts_rack_1": {"stands": True, "stance_lows": [0.0, 0.221, 0.0, 0.24]},
            "leg_strut": {"stands": False, "stance_lows": [0.0, 0.3, 0.2, 0.0]},
            "crate": {"stands": True, "stance_lows": [0.0, 0.01, 0.0, 0.02]}}))
        verdict = bake_check.judge_stance(folder, {}, None)
    assert verdict.answer == "fail" and len(verdict.findings) == 1 and "parts_rack_1: a foot 24.0 cm" in verdict.findings[0]
    assert set(json.loads((REPO / "data/checks/stance.json").read_text())) == {"about", "lies"}


def test_a_base_that_slopes_as_one_piece_is_brought_down_level_and_a_far_gap_is_refused():
    """The hangar's parts rack: two legs ending 8% of its size over a middle part."""
    corners = [(x, z) for x in (-0.4, 0.4) for z in (-0.3, 0.3)]
    rack = np.array([[x, 0.08 if x > 0 else 0.0, z] for x, z in corners] + [[x, 0.5, z] for x, z in corners]
                    + [[0.0, 1.0, 0.0]])
    points, record = place_line.flattened_base(rack, 0.25, 0.01, 0.15)
    assert np.allclose(points[:4, 1], 0.0, atol=1e-9) and record["flattened"] == [0.08, 0.08], record
    assert np.allclose(points[4:, 1], rack[4:, 1]), "a point over the band does not move"
    points, record = place_line.flattened_base(rack + [0, 0, 0], 0.25, 0.01, 0.05)
    assert record["refused"] == [0.08, 0.08] and np.allclose(points, rack)
    level = rack.copy()
    level[:4, 1] = 0.0
    assert place_line.flattened_base(level, 0.25, 0.01, 0.15)[1]["flattened"] == []


def test_a_base_sloping_as_one_plane_through_its_middle_is_brought_down_level():
    """The square's guard hut: a slab base rising 8% of its size from one side to the other, each quadrant's lowest
    point by the middle (flattened_base finds nothing); a level slab and a round bottom are left as they are."""
    slab = trimesh.creation.box(bounds=((-1.0, 0.0, -1.0), (1.0, 2.0, 1.0))).subdivide().subdivide().subdivide()
    slab.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 4, (0, 1, 0)))  # a diamond, as the hut's
    hut = np.asarray(slab.vertices).copy()
    bottom, over = hut[:, 1] < 1e-9, hut[:, 1] > 0.5
    hut[bottom, 1] += 0.08 * (hut[bottom, 0] + 2 ** 0.5) / 2 ** 1.5  # 8 cm up at its far corner, x = 1.41
    quadrants = place_line.flattened_base(hut, 0.5, 0.03, 0.4)[1]
    assert max(quadrants["quadrants"]) < 0.05, quadrants  # the blind spot: each quadrant's lowest lies at x = 0
    points, record = place_line.sloped_base(hut, 0.5, 0.17, 0.03, 0.4)
    assert abs(record["rise"] - 0.08) < 0.01 and not record["refused"], record
    assert np.abs(points[bottom, 1]).max() < 0.01 and np.allclose(points[over], hut[over]), "over the band: as made"
    assert points[:, 1].min() >= hut[:, 1].min() - 1e-12, "nothing comes down past the lowest point"
    assert place_line.sloped_base(hut, 0.5, 0.17, 0.03, 0.05)[1]["refused"] == [record["rise"]]
    level = np.asarray(slab.vertices)
    assert place_line.sloped_base(level, 0.5, 0.17, 0.03, 0.4)[1]["rise"] is None
    ball = np.asarray(trimesh.creation.icosphere(4).vertices)
    points, record = place_line.sloped_base(ball, 0.5, 0.17, 0.03, 0.4)
    assert record["rise"] is None and np.array_equal(points, ball), record


def test_a_tall_cabinet_s_base_step_is_levelled_against_its_footprint():
    """Both ways (the garage's control cabinet, 2026-10-15: 1.5 m tall on a plinth rim whose underside rises across
    its footprint under its floor's level cells, resting 2.1 degrees over; the quadrants and the cells' plane passed it): the
    face it rests on comes down level; a cabinet on a level rim is left as made. And its row, "cables running up from
    its top", stands it on the floor, while a stick mounted on a console and a cairn of stones do not."""

    def cabinet(rise):
        body = trimesh.creation.box(bounds=((-0.3, 0.04, -0.25), (0.3, 1.5, 0.25)))  # its floor 4 cm up, level
        rim = [trimesh.creation.box(bounds=low_high) for low_high in (
            ((-0.3, 0.0, -0.25), (0.3, 0.08, -0.2)), ((-0.3, 0.0, 0.2), (0.3, 0.08, 0.25)),
            ((-0.3, 0.0, -0.25), (-0.25, 0.08, 0.25)), ((0.25, 0.0, -0.25), (0.3, 0.08, 0.25)))]
        body = body.subdivide().subdivide().subdivide().subdivide()  # its floor dense: cells off the rim's plane
        mesh = trimesh.util.concatenate([body, *rim])
        points = np.asarray(mesh.vertices).copy()
        bottom = points[:, 1] < 1e-9
        points[bottom, 1] = rise * (points[bottom, 0] + 0.3) / 0.6  # the rim's underside rises along x
        return points, np.asarray(mesh.faces)

    def resting_lean(points, faces):
        mesh = trimesh.Trimesh(points, faces, process=False)
        middle = (mesh.triangles_center * mesh.area_faces[:, None]).sum(axis=0) / mesh.area
        hull = mesh.convex_hull
        hits, _, struck = hull.ray.intersects_location([[middle[0], 3.0, middle[2]]], [[0.0, -1.0, 0.0]])
        return np.degrees(np.arccos(-hull.face_normals[struck[np.argmin(hits[:, 1])]][1]))

    points, faces = cabinet(0.012)  # 1.2 cm across 0.6 m: under the 1.5 cm a share of its height lets pass
    assert resting_lean(points, faces) > 1.0
    levelled, record = place_line.levelled_feet(points, faces)
    assert record.get("rests") and resting_lean(levelled, faces) < 0.1, record
    points, faces = cabinet(0.0)
    level, record = place_line.levelled_feet(points, faces)
    assert "rests" not in record and np.array_equal(level, points), record
    rules = REPO / "data/checks/resting.json"
    folder = pathlib.Path(tempfile.mkdtemp())
    rows = [{"id": "control_cabinet", "anchor": "floor", "thing": "prop:garage_control_cabinet",
             "name": "a standing steel control cabinet, cables running up from its top"},
            {"id": "control_stick", "anchor": "on:main_console", "thing": "prop:cockpit_control_stick",
             "name": "flight stick set in the console"},
            {"id": "cairn", "anchor": "floor", "thing": "prop:campgrounds_cairn",
             "name": "cairn of flat stones stacked into a narrow tower"},
            {"id": "small_panel", "anchor": "floor", "thing": "prop:wreck_small_panel", "name": "small torn hull panel",
             "leans": "debris lying tilted on purpose"}]
    (folder / "inventory.json").write_text(json.dumps({"rows": rows}))
    assert place_line.stands_on_feet({"kind": "garage_control_cabinet"}, folder / "inventory.json", rules)
    for lying in ("cockpit_control_stick", "campgrounds_cairn"):  # mounted on another object; a pile of stones
        assert not place_line.stands_on_feet({"kind": lying}, folder / "inventory.json", rules), lying
    assert not place_line.stands_on_feet({"kind": "wreck_small_panel"}, folder / "inventory.json", rules)
    shutil.rmtree(folder)


def test_only_a_place_nobody_walks_bakes_with_no_kick_wear():
    """A place whose surface data says nobody walks it (the wreck's did): its bake's specs say kicks 0. Data that
    says nothing hands its specs back as given, the very same object (recipes.WALKED: kicked as before), and its bake
    is the same as before the change (2026-10-13)."""
    specs = {"dark_panel": {"recipe": "painted_metal"}, "bare_steel": {"recipe": "bare_metal"}}
    assert {spec["kicks"] for spec in place_line.unwalked(specs, {"foot_traffic": False}).values()} == {0.0}
    assert place_line.unwalked(specs, {"place": "hub"}) is specs


def test_bake_and_paint_rent_one_machine_class_each():
    """A batch job runs on its one priced class; no stock is a gap, never another class (#21)."""
    assert "," not in place_line.CLASSES and "," not in place_line.PAINT_CLASSES


# --- library_reads ---

ROWS = {row.name: row for row in stages.STAGES}


def a_copy():
    """data/library copied into a folder of its own: the data folder."""
    (PROPS_HOME / "work").mkdir(parents=True, exist_ok=True)
    data = pathlib.Path(tempfile.mkdtemp(prefix="library-reads-", dir=PROPS_HOME / "work"))
    shutil.copytree(REPO / "data/library", data / "library")
    return data


@pytest.fixture
def hub(monkeypatch, tmp_path):
    """The hub's surface data of the test's own: one crate take, baked."""
    (tmp_path / "hub.json").write_text(json.dumps({"place": "hub", "library": "hub", "takes": {
        "crate-t1": {"place": "hub", "kind": "crate", "object": "a crate", "library_places": ["hub"]}},
        "bake": {"models": {"crate_1": "crate-t1"}, "entries": {"crate_1": {"size": [1.0, 1.0, 1.0]}}}}))
    for data in (surfaces.data, surface_data):
        monkeypatch.setattr(data, "FOLDER", tmp_path)


def keys(row, place, data):
    return text_hash(ROWS[row].files(place)["library"][1](data / "library"))


def edit(path, change):
    found = json.loads(path.read_text()) if path.exists() else {}  # details.json: none since the old kinds' retired
    change(found)
    path.write_text(json.dumps(found, indent=1))


def test_a_surface_added_anywhere_moves_no_paint_key_and_every_bake_key(hub):
    """The paint paints the surfaces its records name; the bake's job, written from git (bake_job.py), carries every
    variant of the library as its specs, so a variant added anywhere moves every bake."""
    data = a_copy()
    try:
        before = {row: keys(row, "hub", data) for row in ("surfaces-paint", "surfaces-bake")}
        added = {"recipe": "painted_metal", "token": "hull-trim", "bare": "hull"}
        edit(data / "library/materials.json",
             lambda library: library["families"].setdefault("painted", {"variants": {}})["variants"].update(
                 brand_new_panel=added))
        assert keys("surfaces-paint", "hub", data) == before["surfaces-paint"]
        assert keys("surfaces-bake", "hub", data) != before["surfaces-bake"]
    finally:
        shutil.rmtree(data)


def test_a_kinds_details_move_the_paint_key_and_place_json_keys_neither(hub):
    data = a_copy()
    try:
        kind = "crate"  # the hub's one take's kind
        before = keys("surfaces-paint", "hub", data)
        edit(data / "library/details.json", lambda details: details.setdefault(kind, {}).update(wall=0.123))
        assert keys("surfaces-paint", "hub", data) != before
        for row in ("surfaces-paint", "surfaces-bake"):
            assert "places" not in ROWS[row].files("hub"), row
    finally:
        shutil.rmtree(data)


def test_the_paint_and_bake_rows_and_their_twins_key_the_library_by_part():
    for name, place in (("surfaces-paint", "hub"), ("surfaces-bake", "hub"), ("surfaces-paint", "people")):
        files = ROWS[name].files(place)
        assert isinstance(files["library"], tuple), name
        assert ROWS[name].files.wide(place) if callable(ROWS[name].files.wide) else ROWS[name].files.wide
    assert not isinstance(ROWS["surfaces-parts"].files("hub")["library"], tuple)  # surfaces-names left the line


class StubStore:
    """The store calls the carry rules make here: one proof file, or none."""
    def __init__(self, proof=None):
        self.proof = proof

    def evidence_file(self, check, output):
        return self.proof


class StubRunner:
    def __init__(self, proof=None):
        self.store = StubStore(proof)
        self.stages = ROWS


def a_record(**changes):
    """An accepted record made at the repository's first commit, so the paint's code changed since."""
    first = subprocess.run(["git", "-C", str(REPO), "rev-list", "--max-parents=0", "HEAD"], capture_output=True,
                           text=True, check=True).stdout.split()[0]
    return {"output": "o" * 64, "key": "k" * 64, "commit": first, "uncommitted": False, "code": "old code",
            "files": {}, **changes}


def test_a_bake_model_with_no_written_entry_is_declared_missing_by_name():
    """A bake row's model its data writes no entry for is a file that is never there, naming it; one written out, or
    a design's written without a turn, is none."""
    record = {"bake": {"models": {"bench_1": "bench-t1", "lost_1": "lost-t1"},
                       "entries": {"bench_1": {"size": [2.0, 0.9, 0.5]}}}}
    refused = library_reads.bake_refusals(record, {"surfaces": "{home}/design/surfaces/hub.json"})
    assert list(refused) == ["bake entry lost_1"] and "no entry for lost_1" in refused["bake entry lost_1"], refused


def test_a_record_from_an_uncommitted_tree_or_a_changed_code_without_proof_never_carries():
    row = ROWS["surfaces-paint"]
    assert carry.why_not(StubRunner(), row, "hub", a_record(uncommitted=True), {}) == \
        "made from a tree with changes not committed"
    assert carry.why_not(StubRunner(), row, "hub", a_record(), {}) == \
        "its code changed since, with no proof its result is the same"


def test_a_proof_carries_only_when_it_names_every_changed_file_for_these_code_versions():
    row = ROWS["surfaces-paint"]
    record = a_record()
    changed = carry.changed_files(row, record["commit"])
    assert changed
    (PROPS_HOME / "work").mkdir(parents=True, exist_ok=True)
    folder = pathlib.Path(tempfile.mkdtemp(prefix="carry-proof-", dir=PROPS_HOME / "work"))
    try:
        proof = folder / "proof.json"
        full = {"made with code": "old code", "code now": carry.wide_code(row),
                "no-ops": {name: "its change leaves the parts and surfaces as they were" for name in changed},
                "free rows": {}}
        proof.write_text(json.dumps(full))
        assert carry.proof_fault(StubRunner(proof), row, record) is None
        proof.write_text(json.dumps({**full, "no-ops": {name: "" for name in changed}}))
        assert carry.proof_fault(StubRunner(proof), row, record).startswith("its proof does not say why")
        proof.write_text(json.dumps({**full, "code now": "another code"}))
        assert carry.proof_fault(StubRunner(proof), row, record) == "its proof is for other code versions"
    finally:
        shutil.rmtree(folder)


def test_a_proof_speaks_from_the_code_rows_had_at_its_commit():
    """codes_at works the rows' code out at a commit: 46d5873 changed place_line.py alone, so the paint's code moved
    from its parent and the maps' did not (a record carries only when made from the code at the proof's commit). The
    two checkouts are worked out side by side: each imports its whole stage table, about 27 s apiece."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(2) as pool:
        before, after = pool.map(carry.codes_at, ("46d5873^", "46d5873"))
    assert before["surfaces-paint"] != after["surfaces-paint"]
    assert before["surfaces-maps"] == after["surfaces-maps"]


# --- finish ---

def test_unvoted_faces_take_the_nearest_voted_label_along_the_surface():
    mesh = trimesh.creation.icosphere(subdivisions=3)
    seen = np.full(len(mesh.faces), -1)
    middles = mesh.triangles_center
    seen[(middles[:, 2] > 0.5) & (middles[:, 0] > 0)] = 0
    seen[(middles[:, 2] > 0.5) & (middles[:, 0] <= 0)] = 1
    walked = finish_parts.walked(mesh, seen)
    assert (walked >= 0).all()
    back = middles[:, 2] < -0.5
    assert (walked[back & (middles[:, 0] > 0.3)] == 0).mean() > 0.9
    assert (walked[back & (middles[:, 0] < -0.3)] == 1).mean() > 0.9


def test_a_loose_bit_joins_the_nearest_larger_island_of_its_own_finish():
    big = trimesh.creation.box(extents=(1, 1, 1))
    loose = trimesh.creation.box(extents=(0.02, 0.02, 0.02))
    loose.apply_translation((0.53, 0, 0))
    far = trimesh.creation.box(extents=(1, 1, 1))
    far.apply_translation((3, 0, 0))
    mesh = trimesh.util.concatenate([big, loose, far])
    label = np.r_[np.zeros(len(big.faces)), np.ones(len(loose.faces)), np.ones(len(far.faces))].astype(int)
    part_of, merged = finish_parts.merged_islands(mesh, label)
    bit = slice(len(big.faces), len(big.faces) + len(loose.faces))
    assert len(np.unique(part_of)) == 2 and (part_of[bit] == part_of[-1]).all() and (merged[bit] == 1).all()


def test_a_finish_of_crumbs_only_keeps_them_as_one_part_however_small():
    host = trimesh.creation.box(extents=(1, 1, 1))
    bands = []
    for number in range(4):  # thin stripes beside the box, each a crumb, together over ISLAND_LEAST
        band = trimesh.creation.box(extents=(0.04, 0.04, 0.04))
        band.apply_translation((0.6, -0.3 + 0.2 * number, 0))
        bands.append(band)
    mesh = trimesh.util.concatenate([host, *bands])
    band_share = sum(band.area for band in bands) / mesh.area
    assert all(band.area / mesh.area < finish_parts.ISLAND_LEAST for band in bands)
    assert band_share >= finish_parts.ISLAND_LEAST
    label = np.r_[np.zeros(len(host.faces)), np.ones(len(mesh.faces) - len(host.faces))].astype(int)
    part_of, merged = finish_parts.merged_islands(mesh, label)
    striped = slice(len(host.faces), None)
    assert len(np.unique(part_of)) == 2 and (merged[striped] == 1).all() and len(np.unique(part_of[striped])) == 1
    one = trimesh.util.concatenate([host, bands[0]])  # one crumb alone keeps its finish as a part of its own
    label = np.r_[np.zeros(len(host.faces)), np.ones(len(bands[0].faces))].astype(int)
    part_of, merged = finish_parts.merged_islands(one, label)
    assert len(np.unique(part_of)) == 2 and (merged[len(host.faces):] == 1).all()


def test_cleaning_never_removes_a_finish_whole():
    mesh = trimesh.creation.icosphere(subdivisions=4)
    middles = mesh.triangles_center
    label = np.zeros(len(mesh.faces), dtype=int)
    dots = np.flatnonzero((middles[:, 1] > 0.9) | (middles[:, 0] > 0.97))[::3]  # scattered single faces of finish 1
    label[dots] = 1
    without = finish_parts.cleaned(mesh, label, 2)
    assert (without[dots] == 1).all() and (without[label == 0] == 0).mean() > 0.99
    kept = finish_parts.kept_finishes(np.array([0, 1, 2, 2]), np.array([0, 0, 0, 2]))
    assert kept.tolist() == [0, 1, 0, 2]  # a finish left with any face stays as the cleaning left it


def test_a_stray_island_takes_the_finish_round_it_and_patchy_paint_is_named():
    """astronaut-made-s1, 2026-10-23: the walk left jagged islands of the dark joints over its fabric (stray 0.054).
    A stray joins the finish it borders; a finish with no island of its own size keeps its islands, a whole piece
    keeps its finish, and a small piece of mixed finishes joins its largest island."""
    import patchy  # on the path finish_parts gives
    sphere = trimesh.creation.icosphere(subdivisions=4)
    loose = trimesh.creation.box(extents=(0.05, 0.05, 0.05))
    loose.apply_translation((3, 0, 0))
    mesh = trimesh.util.concatenate([sphere, loose])
    middles = mesh.triangles_center
    label = np.zeros(len(mesh.faces), dtype=int)
    on_sphere = np.arange(len(mesh.faces)) < len(sphere.faces)
    label[on_sphere & (middles[:, 2] < -0.5)] = 1  # finish 1's large island
    patch = on_sphere & (np.linalg.norm(middles - (0, 0.99, 0.1), axis=1) < 0.08)  # a blotch of finish 1
    label[patch] = 1
    lone = on_sphere & (np.linalg.norm(middles - (0.99, 0, 0.1), axis=1) < 0.08)  # finish 2, nowhere larger
    label[lone] = 2
    label[~on_sphere] = 1  # a whole piece of the shape
    assert 0 < mesh.area_faces[patch].sum() / mesh.area < patchy.STRAY_ISLAND
    body = [{"finish": "white paint", "parts": "the body", "family": "paint"}] * 3
    before = finish_parts.patchiness(mesh, label, label, body)
    found = finish_parts.without_strays(mesh, label)
    assert (found[patch] == 0).all() and (found[lone] == 2).all() and (found[~on_sphere] == 1).all()
    assert (found[~patch] == label[~patch]).all()
    after = finish_parts.patchiness(mesh, found, found, body)
    assert after["stray"] < before["stray"] and after["pass"], (before, after)
    piece = (np.arange(len(mesh.faces)) >= len(sphere.faces)) & (middles[:, 0] > 3.02)  # a small piece, two finishes
    label[piece] = 0
    assert (finish_parts.without_strays(mesh, label)[~on_sphere] == 1).all()
    blotched = np.where(np.linalg.norm(middles - (0, 0, 1), axis=1) < 0.18, 1, 0)
    for spot in ((0, 0, -1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):  # blotches of each finish over 3%
        blotched[on_sphere & (np.linalg.norm(middles - spot, axis=1) < 0.18)] = 1
    blotched[~on_sphere] = 0
    gated = finish_parts.patchiness(mesh, np.where(on_sphere, blotched, 0), np.zeros(len(mesh.faces), dtype=int), body)
    assert not gated["pass"] and route_split.patchy_fault(gated).startswith("patchy paint: stray"), gated


def test_islands_of_a_detail_finish_sharing_a_part_are_no_stray():
    """old_station solar_panel_mast, 2026-10-28: its steel fittings, islands under STRAY_ISLAND each, merged_islands
    gathered into parts of several islands, read stray 0.032. Islands of a detail finish (its family or words: decals,
    stickers, labels, notes, fittings, rubber) are parts of their own as a lone fitting is; the same blotches of a body
    finish still fail."""
    mesh = trimesh.creation.icosphere(subdivisions=4)
    middles = mesh.triangles_center
    label = np.zeros(len(mesh.faces), dtype=int)
    for spot in ((0, 0, 1), (0, 0, -1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):  # six islands, over 3% in all
        label[np.linalg.norm(middles - spot, axis=1) < 0.18] = 1
    part_of = label.copy()  # the six islands one part, as merged_islands leaves a finish with no larger island
    shell = {"finish": "white paint", "parts": "the hull", "family": "paint"}
    fittings = {"finish": "bare steel fittings", "parts": "clamps and collars", "family": "steel"}
    casters = {"finish": "black", "parts": "caster wheels", "family": "rubber"}
    assert finish_parts.detail_finish(fittings) and finish_parts.detail_finish(casters)
    assert not finish_parts.detail_finish(shell)
    for detail in (fittings, casters):
        assert finish_parts.patchiness(mesh, label, part_of, [shell, detail])["pass"]
    blotched = finish_parts.patchiness(mesh, label, part_of, [shell, shell])
    assert not blotched["pass"] and blotched["stray"] > 0.03, blotched


def test_agreement_counts_against_the_maps():
    mesh = trimesh.creation.icosphere(subdivisions=2)
    top = mesh.triangles_center[:, 1] > 0
    face_label = np.zeros(len(mesh.faces), dtype=int)
    front = np.where(top, 1, 0)  # the map says finish 1 on top, the paint says 0 everywhere
    agreement = finish_parts.agreement(mesh, face_label, {"front": front})
    assert 0.4 < agreement["front"] < 0.6, agreement


def test_a_finish_out_of_order_is_found_and_a_see_through_finish_is_known():
    greys = {"anodized_natural": {"colour": [0.2843] * 3}, "dust_coated_paint": {"colour": [0.4075] * 3}}  # L* 60, 70
    lightness = finish_parts.opaque_lightness(greys)
    white = {"surface": "anodized_natural", "measured_lab": [80.6, 1.0, 2.0]}  # the campgrounds' power unit
    dusty = {"surface": "dust_coated_paint", "measured_lab": [69.7, 0, 0]}
    assert finish_parts.out_of_order(white, dusty, greys, lightness)
    assert not finish_parts.out_of_order(dusty, white, greys, lightness)
    assert not finish_parts.out_of_order(white, dict(dusty, measured_lab=None), greys, lightness)
    # a finish route's finish paints in its own colour (its settings' token) while it keeps its listed surface:
    # astronaut-made (2026-10-23): its white shell in suit-white, its variant's own token base-grey
    shell = dict(white, colour=[0.9131] * 3, listed_surface="anodized_natural")
    fabric = dict(dusty, colour=[0.4075] * 3, listed_surface="dust_coated_paint")
    assert not finish_parts.out_of_order(shell, fabric, greys, lightness)
    assert finish_parts.out_of_order(dict(shell, listed_surface="other"), fabric, greys, lightness)  # moved: library's
    every = {"red_plastic": {"family": "plastic"}, "cast_steel": {"family": "steel"}, "glass": {"family": "glass"}}
    listed = [{"finish": "Red transparent plastic", "parts": "lamp dome", "surface": "red_plastic"},
              {"finish": "Polished reflective metal", "parts": "internal reflector", "surface": "cast_steel"},
              {"finish": "Grey painted steel", "parts": "housing", "surface": "cast_steel"}]
    assert [finish_parts.see_through(finish, every) for finish in listed] == [True, False, False]


def test_an_ask_is_made_once_a_timeout_reaches_the_row_and_only_a_refusal_is_asked_again():
    sys.path.insert(0, str(REPO / "tools/cloud"))
    import google_spend
    asked = []

    def answering(*faults):
        def answer(model, body, key, timeout, caller, cache):
            asked.append(body.get("serviceTier"))
            if len(asked) <= len(faults):
                raise faults[len(asked) - 1]
            return "answered"
        return answer

    def refusal(code):
        return urllib.error.HTTPError("url", code, "refused", {}, io.BytesIO())
    saved = google_spend.generate, finish_ask.REFUSED_WAIT
    finish_ask.REFUSED_WAIT = 0
    try:
        google_spend.generate = answering(TimeoutError("The read operation timed out"))
        try:
            finish_ask.generated(finish_ask.LIST_MODEL, {"serviceTier": "flex"}, "key", 1, "test", False)
        except TimeoutError:
            pass
        else:
            raise AssertionError("a timeout reaches the row")
        assert asked == ["flex"], asked
        asked.clear()
        google_spend.generate = answering(refusal(429), refusal(503))
        assert finish_ask.generated(finish_ask.LIST_MODEL, {}, "key", 1, "test", False) == "answered"
        assert len(asked) == 3, asked
        asked.clear()
        google_spend.generate = answering(refusal(500), refusal(504))  # audit, 2026-10-22: these stopped the row
        assert finish_ask.generated(finish_ask.LIST_MODEL, {}, "key", 1, "test", False) == "answered"
        assert len(asked) == 3, asked
        asked.clear()
        google_spend.generate = answering(refusal(400))
        try:
            finish_ask.generated(finish_ask.LIST_MODEL, {}, "key", 1, "test", False)
        except urllib.error.HTTPError:
            pass
        assert len(asked) == 1, asked
        asked.clear()
        rooms = []
        google_spend.generate = answering(refusal(429), refusal(503), refusal(429))
        try:
            finish_ask.generated(finish_ask.LIST_MODEL, {}, "key", 1, "test", False, room=lambda: rooms.append(1))
        except finish_ask.NoAnswer:
            pass
        else:
            raise AssertionError("refused every time is no answer")
        assert len(asked) == finish_ask.REFUSED_ASKS == len(rooms), (asked, rooms)
        asked.clear()
        google_spend.generate = answering(urllib.error.URLError(ConnectionRefusedError(111, "refused")))
        try:
            finish_ask.generated(finish_ask.LIST_MODEL, {}, "key", 1, "test", False)
        except finish_ask.NoAnswer:
            pass
        else:
            raise AssertionError("a lost connection is no answer")
        assert len(asked) == 1, asked
    finally:
        google_spend.generate, finish_ask.REFUSED_WAIT = saved


def test_a_finish_takes_the_nearest_surface_of_its_family_by_colour_or_is_flagged():
    navy, grey, black = [0.03, 0.06, 0.10], [0.35, 0.35, 0.35], [0.01, 0.01, 0.01]
    library = {"vinyl_seat": {"family": "plastic", "colour": navy},
               "grey_plastic": {"family": "plastic", "colour": grey},
               "dark_panel": {"family": "steel", "colour": black}}
    light_grey = finish_parts.library_lab(library["grey_plastic"]) + np.array([3.0, 0, 0])
    found = finish_parts.checked_finishes(
        {"kind": "lab_chair", "object": "desk chair"},
        [{"finish": "grey vinyl", "parts": "seat", "surface": "vinyl_seat", "fits": True},
         {"finish": "grey steel", "parts": "body", "surface": "dark_panel", "fits": True}],
        [light_grey, light_grey], library)
    assert found[0]["surface"] == "grey_plastic" and found[0]["by"] == "nearest of its family by colour"
    assert found[1]["surface"] == "dark_panel" and found[1]["by"] == "off its colour" and not found[1]["fits"]
    assert found[1]["new_surface"]["lab"] == [round(float(value), 1) for value in light_grey]
    # a finish in its own token's colour (the finish route's settings) is held to that colour, not its surface's
    tinted = finish_parts.checked_finishes(
        {"kind": "lab_chair", "object": "desk chair"},
        [{"finish": "grey steel", "parts": "body", "surface": "dark_panel", "fits": True, "colour": grey}],
        [light_grey], library)
    assert tinted[0]["surface"] == "dark_panel" and tinted[0]["by"] == "the list", tinted[0]


def test_a_finish_keeps_the_close_ups_lightness_order_and_glass_keeps_its_own_colour():
    """The water tank: its panel 13 L* lighter than its steel in the close-up, painted_panel under bare_steel in the
    library; cream_paint keeps the order. Glass off the lit colour keeps its surface (owner, #8)."""
    every = {"painted_panel": {"family": "painted", "colour": [0.30, 0.31, 0.33]},
             "cream_paint": {"family": "painted", "colour": [0.55, 0.53, 0.46]},
             "bare_steel": {"family": "steel", "colour": [0.35, 0.36, 0.38]},
             "glass": {"family": "glass", "colour": [0.6, 0.65, 0.7]}}
    panel_lab = [round(float(value), 1) for value in finish_parts.library_lab(every["cream_paint"]) - [4, 0, 0]]
    steel_lab = [round(float(value), 1) for value in finish_parts.library_lab(every["bare_steel"]) - [8, 0, 0]]
    found = finish_parts.in_close_up_order({"object": "water tank"}, [
        {"finish": "off-white paint", "surface": "painted_panel", "measured_lab": panel_lab, "by": "the list"},
        {"finish": "steel legs", "surface": "bare_steel", "measured_lab": steel_lab, "by": "the list"}], every)
    assert found[0]["surface"] == "cream_paint" and found[0]["by"] == "nearest of its family in order", found[0]
    alone = {name: spec for name, spec in every.items() if name != "cream_paint"}
    flagged = finish_parts.in_close_up_order({"object": "water tank"}, [
        {"finish": "off-white paint", "surface": "painted_panel", "measured_lab": panel_lab, "by": "the list"},
        {"finish": "steel legs", "surface": "bare_steel", "measured_lab": steel_lab, "by": "the list"}], alone)
    assert flagged[0]["by"] == "off its colour" and "lighter than bare_steel" in flagged[0]["new_surface"]["why"]
    kept = [{"finish": "steel legs", "surface": "bare_steel", "measured_lab": steel_lab, "by": "the list"}]
    assert finish_parts.in_close_up_order({"object": "x"}, [dict(kept[0])], every) == kept  # nothing to order
    lit = finish_parts.checked_finishes({"kind": "lamp", "object": "lamp"},
                                        [{"finish": "red lit lens", "parts": "lens", "surface": "glass"}],
                                        [np.array([45.0, 60.0, 40.0])], every)
    assert lit[0]["surface"] == "glass" and lit[0]["by"] == "its own colour" and "cover" not in lit[0], lit[0]


def test_a_finish_a_little_out_of_order_keeps_it_by_a_nearer_surface_of_either():
    """The hangar's parts shelving: its grey plastic bins 27.7 L* over its steel in the close-up, plastic_grey 1.5
    under galvanized_steel in the library (the steel baked 3 over its colour, the bins 4.5 under it). The steel, seen
    at L* 42, takes cast_steel, nearer its close-up colour; with none nearer, the order stays as it was."""
    every = {"galvanized_steel": {"family": "steel", "colour": [0.328, 0.361, 0.397]},
             "plastic_grey": {"family": "plastic", "colour": [0.386, 0.332, 0.258]},
             "cast_steel": {"family": "steel", "colour": [0.070, 0.084, 0.102]}}

    def shelving():
        return [{"finish": "Grey steel", "surface": "galvanized_steel", "measured_lab": [41.9, 0.6, -0.6],
                 "by": "the list"},
                {"finish": "Light grey plastic", "surface": "plastic_grey", "measured_lab": [69.6, 0.2, 0.9],
                 "by": "named again (its material)"}]
    found = finish_parts.in_close_up_order({"object": "parts shelving"}, shelving(), every)
    assert found[0]["surface"] == "cast_steel" and found[0]["by"] == "nearest of its family in order", found[0]
    assert found[1]["surface"] == "plastic_grey" and found[1]["by"] == "named again (its material)", found[1]
    bright = [dict(finish) for finish in shelving()]
    bright[0]["measured_lab"] = [66.0, -1.0, -4.0]  # the steel seen as light as galvanized_steel: none nearer
    bright[1]["measured_lab"] = [80.0, 0.0, 0.0]
    assert finish_parts.in_close_up_order({"object": "parts shelving"}, [dict(finish) for finish in bright],
                                          every) == bright


def test_a_coloured_see_through_finish_keeps_its_surface_against_its_highlights():
    """The beacon's red transparent dome measured pale pink on its brighter half: it keeps red_plastic, not the
    nearer plastic_grey; an opaque grey plastic that far off still moves."""
    library = {"red_plastic": {"family": "plastic", "colour": [0.45, 0.02, 0.01]},
               "plastic_grey": {"family": "plastic", "colour": [0.33, 0.31, 0.27]}}
    pale = np.array([70.8, 21.2, 11.5])
    found = finish_parts.checked_finishes(
        {"kind": "beacon", "object": "beacon"},
        [{"finish": "Red transparent plastic", "parts": "lamp dome", "surface": "red_plastic"},
         {"finish": "Red plastic", "parts": "knob", "surface": "red_plastic"}], [pale, pale], library)
    assert found[0]["surface"] == "red_plastic" and found[0]["by"] == "its own colour" and found[0]["cover"], found[0]
    assert found[1]["surface"] == "plastic_grey" and found[1]["by"] == "nearest of its family by colour", found[1]


def test_a_finish_list_reply_is_parsed_to_library_names():
    surfaces = {"mli_gold": {}, "bare_steel": {}}
    reply = json.dumps({"finishes": [{"parts": "foil", "finish": "gold foil", "surface": "M1", "fits": True},
                                     {"parts": "legs", "finish": "steel", "surface": "M2", "fits": True}]})
    assert [entry["surface"] for entry in finish_ask.parsed_list(reply, surfaces)] == ["mli_gold", "bare_steel"]


# --- route ---

RED, BLUE = (200, 30, 30), (150, 120, 220)  # each near its finish's token (sign-red, bay-three): the colour check


TAKE, OTHER = "two_boxes-t1", "other-t1"


def two_boxes(folder):
    """A glb of two boxes side by side, 0.2 apart: the left one textured red, the right one blue by its colour
    factor."""
    left = trimesh.creation.box((1, 1, 1))
    left.apply_translation((-0.6, 0, 0))
    left.visual = trimesh.visual.TextureVisuals(uv=left.vertices[:, :2] + 0.5, material=PBRMaterial(
        baseColorTexture=Image.new("RGB", (4, 4), RED)))
    right = trimesh.creation.box((1, 1, 1))
    right.apply_translation((0.6, 0, 0))
    right.visual = trimesh.visual.TextureVisuals(material=PBRMaterial(baseColorFactor=[*BLUE, 255]))
    path = folder / "two.glb"
    trimesh.Scene([left, right]).export(str(path))
    return path


def place_data(folder):
    path = folder / "place.json"
    entry = {"places": ["cockpit"], "library_places": ["cockpit"], "place": "cockpit", "kind": "two_boxes",
             "object": "two boxes"}
    path.write_text(json.dumps({"place": "cockpit", "takes": {TAKE: entry, OTHER: dict(entry, object="another")}}))
    return path


# The scene palette as its row writes it (scene_palette.py): the tokens the finish list may use, its wear and dirt.
TOKENS = {"sign-red": "#b3241d", "bay-three": "#9a7be0", "hull-trim": "#8c96a0", "steel": "#9ba2a9",
          "glass": "#24313a", "regolith": "#8b8883", "alarm": "#a3302a"}


PALETTE = {"tokens": {token: TOKENS[token] for token in ("sign-red", "bay-three", "hull-trim", "steel", "glass",
                                                "regolith")},
           "wear": {"level": "worked", "dirt": 0.3, "dirt_token": "regolith", "cause": "worked hard"}}


# The scene's surface library as the surface-library row writes it (scene_library.py): the method's recipes, the
# scene's own variants in its own tokens and the variants its kinds are made of.
VARIANTS = {"painted": {"painted_panel": {"recipe": "painted_metal", "token": "hull-trim", "bare": "steel",
                                          "roughness": 0.31},
                        "red_paint": {"recipe": "painted_metal", "token": "sign-red", "bare": "steel"},
                        "blue_paint": {"recipe": "painted_metal", "token": "bay-three", "bare": "steel"}},
            "steel": {"bare_steel": {"recipe": "bare_metal", "token": "steel", "roughness": 0.5}},
            "glass": {"pane": {"recipe": "glass", "token": "glass"}}}


def scene_library_record():
    method = json.loads((REPO / "data/library/materials.json").read_text())
    return {**method, "tokens": TOKENS, "dirt": "regolith", "kinds": {"two_boxes": ["painted_panel"]},
            "families": {family: {"variants": variants} for family, variants in VARIANTS.items()}}


def paletted(folder):
    """The palette row's output folder with PALETTE."""
    found = folder / "palette"
    found.mkdir()
    (found / "palette.json").write_text(json.dumps(PALETTE))
    return found


def libraried(folder):
    """The surface-library row's output folder with the scene library."""
    found = folder / "surface-library"
    found.mkdir()
    (found / "materials.json").write_text(json.dumps(scene_library_record()))
    return found


VIEWS_MADE = {}  # {(takes, the model's bytes): a views output made once}: the make casts 120 views, about 2.5 s


def cast_views(folder, takes=(TAKE,)):
    """The views row's make on the two boxes (each take named the same model), the object filter keeping `takes`;
    the inputs carry the scene palette. Made once a module for the same takes and model (VIEWS_MADE), copied after."""
    views = folder / "views"
    model = two_boxes(folder)
    inputs = {"surfaces": place_data(folder), "finish-route-palette": paletted(folder),
              "surface-library": libraried(folder), **{f"model {take}": model for take in takes}}
    made = VIEWS_MADE.get((takes, model.read_bytes()))
    if made is None:
        views.mkdir()
        route_views.make_views(inputs, views, 7, {"objects": list(takes)})
        made = VIEWS_MADE[takes, model.read_bytes()] = pathlib.Path(tempfile.mkdtemp()) / "views"
        shutil.copytree(views, made)
    else:
        shutil.copytree(made, views)
    return inputs, views


def region_of(views, colour, take=TAKE):
    """The views row's region (0-based) of a colour."""
    regions = json.loads((views / "views.json").read_text())[take]["regions"]
    return next(entry["region"] for entry in regions if entry["srgb"] == list(colour))


def finish_entry(words, surface="M1", token="sign-red", **more):
    return {"parts": words, "finish": words, "surface": surface, "token": token, "roughness": 1.4, "metal": 0.0,
            "fits": True, **more}


def labelled(views, finish_of_colour, take=TAKE):
    """Labels for every region showing in every view: the region of each colour takes finish_of_colour(view, colour)
    (1-based, None to leave it out)."""
    angles = json.loads((views / "views.json").read_text())[take]["views"]
    shown = route_list.regions_shown(views / take, angles)
    found = []
    for view, regions in shown.items():
        for colour in (RED, BLUE):
            finish = finish_of_colour(view, colour)
            if region_of(views, colour, take) in regions and finish is not None:
                found.append({"view": view, "region": region_of(views, colour, take) + 1, "finish": finish})
    return found


def two_finish_answer(views, finish_of_colour=lambda view, colour: 1 if colour == RED else 2):
    finishes = [finish_entry("red paint", wear="worn"),  # a level with no cause is not taken
                dict(finish_entry("blue paint", token="bay-three"), wear="worn", wear_cause="walked path")]
    return {"finishes": finishes, "labels": labelled(views, finish_of_colour)}


def listed(folder, answer, takes=(TAKE,)):
    """The views and list rows made with the list's batch faked to answer `answer(views, take)` (a dict, or an
    exception the batch holds): the rows' inputs and the batches asked."""
    inputs, views = cast_views(folder, takes)
    asked = []
    original = route_list.ask
    route_list.ask = lambda bodies: asked.append(bodies) or {
        take: (answer(views, take) if isinstance(answer(views, take), Exception) else json.dumps(answer(views, take)))
        for take in bodies}
    try:
        out = folder / "list"
        out.mkdir()
        route_list.make_list({**inputs, "finish-route-views": views}, out, 7, {"objects": list(takes)})
    finally:
        route_list.ask = original
    return {**inputs, "finish-route-views": views, "finish-route-list": out}, asked


def split(folder, rows):
    out = folder / "split"
    out.mkdir()
    route_split.make_split(rows, out, 7, {})
    return {**rows, "finish-route-split": out}


def parted(folder, rows):
    out = folder / "parts"
    out.mkdir()
    route_parts.make_parts(rows, out, 7, {"objects": [TAKE]})
    return {**rows, "surfaces-parts": out}


def test_the_views_cover_every_side_and_find_both_colours():
    with tempfile.TemporaryDirectory() as temporary:
        inputs, views = cast_views(pathlib.Path(temporary))
        record = json.loads((views / "views.json").read_text())
        assert list(record) == [TAKE], record  # the filter left other-t1 out
        assert set(route_cast.BASE) <= set(record[TAKE]["views"]), record[TAKE]["views"]
        assert record[TAKE]["close_up"] == route_data.STAND_IN
        assert record[TAKE]["paint_faces"] == record[TAKE]["faces"] == 24, record[TAKE]
        assert record[TAKE]["unseen_faces"] == 0 and record[TAKE]["seen_share"] == 1.0, record[TAKE]
        assert sorted(tuple(entry["srgb"]) for entry in record[TAKE]["regions"]) == sorted([BLUE, RED])
        assert (views / TAKE / "regions-bottom.png").exists() and (views / TAKE / "right.png").exists()
        verdict = route_views.judge_views(views, inputs, {})
        assert verdict.answer == "pass" and verdict.measures["views_most"] == len(record[TAKE]["views"]), verdict
        assert record[TAKE]["reachable_share"] == 1.0, record[TAKE]
    # area inside the model, out of every angle, is no miss (astronaut-made-s1: 49.5% reachable, all of it seen);
    # views seeing under SEEN_LEAST of what any angle sees still are
    inside = {**record[TAKE], "seen_share": 0.495, "reachable_share": 0.495}
    assert not route_views.take_faults(TAKE, inside)
    assert route_views.take_faults(TAKE, {**inside, "seen_share": 0.2})


def test_the_coverage_check_adds_a_view_for_faces_the_base_views_miss():
    """An open tube standing up: the base views miss part of its inside, the check adds views until every face is
    seen, each added view seeing faces no chosen view saw."""
    mesh = trimesh.creation.annulus(0.3, 0.5, 1.0)
    angles, casts = route_views.covering_views(mesh)
    assert list(angles)[:len(route_cast.BASE)] == list(route_cast.BASE) and len(angles) > len(route_cast.BASE), angles
    seen = np.zeros(len(mesh.faces), dtype=bool)
    for view in list(angles)[:len(route_cast.BASE)]:
        seen[casts[view][0][casts[view][0] >= 0]] = True
    for view in list(angles)[len(route_cast.BASE):]:
        found = casts[view][0]
        assert (~seen[found[found >= 0]]).any(), view  # an added view saw something new
        seen[found[found >= 0]] = True
    assert seen.all()


def test_a_model_with_no_file_or_no_take_fails_by_name():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        inputs = {"surfaces": place_data(folder)}
        route_views.make_views(inputs, folder, 7, {"objects": [OTHER]})
        verdict = route_views.judge_views(folder, inputs, {})
        assert verdict.answer == "fail" and verdict.findings[0].startswith(f"{OTHER}: no raw take"), verdict
        folder = folder / "none"
        folder.mkdir()
        route_views.make_views(inputs, folder, 7, {"objects": ["no-such-take"]})
        verdict = route_views.judge_views(folder, inputs, {})
        assert verdict.answer == "fail" and "no take to work on" in verdict.findings[0], verdict


def test_one_batch_lists_every_take_library_first_and_the_split_gives_every_face_one_finish():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        rows, asked = listed(folder, lambda views, take: two_finish_answer(views), takes=(TAKE, OTHER))
        assert len(asked) == 1 and sorted(asked[0]) == [OTHER, TAKE], asked  # one batch, one ask a take
        body = asked[0][TAKE]
        count = len(json.loads((rows["finish-route-views"] / "views.json").read_text())[TAKE]["views"])
        assert "serviceTier" not in body and len(body["contents"][0]["parts"]) == 2 * count + 2  # close-up, views, text
        found = json.loads((rows["finish-route-list"] / f"{TAKE}.json").read_text())
        seed = route_list.take_seed(7, TAKE)
        assert seed != route_list.take_seed(7, OTHER)  # each object's wear and dirt pattern its own
        assert found["finishes"][0]["settings"] == {"token": "sign-red", "roughness": 1.0, "metal": 0.0, "seed": seed}
        assert found["finishes"][1]["settings"]["wear"] == 0.8 and found["finishes"][1]["settings"]["seed"] == seed + 1
        assert found["finishes"][1]["wear_cause"] == "walked path" and found["finishes"][0]["wear_level"] is None
        assert route_list.judge_list(rows["finish-route-list"], rows, {}).answer == "pass"
        # the ask offers the whole library filtered by the scene palette's tokens, and its wear
        question = body["contents"][0]["parts"][-1]["text"]
        offered = body["generationConfig"]["responseSchema"]["properties"]["finishes"]["items"]["properties"]
        palette = route_list.palette_library.read(rows)
        assert offered["token"]["enum"] == [token for token in route_list.palette_library.library_tokens(palette)
                                             if token in PALETTE["tokens"]], offered["token"]
        assert len(offered["surface"]["enum"]) == len(route_list.palette_library.take_surfaces(
            {"kind": "two_boxes"}, palette)) and "Wear is the scene's level (worked)" in question
        assert "token tarp" not in question and "token sign-red" in question
        own = json.loads((rows["finish-route-list"] / "questions.json").read_text())["own_wear"]
        assert len(own) == 2 and "worn (walked path" in own[0], own
        rows = split(folder, rows)
        record = json.loads((rows["finish-route-split"] / "split.json").read_text())[TAKE]
        assert record["fault"] is None and record["unassigned"] == record["disagree"] == 0, record
        finish_of = np.load(rows["finish-route-split"] / TAKE / "finish.npy")
        faces = np.load(rows["finish-route-views"] / TAKE / "faces.npz")["front"]
        colours = np.load(rows["finish-route-views"] / TAKE / "colours.npz")["front"]
        red = np.unique(faces[(faces >= 0) & (colours == RED).all(-1)])
        assert set(finish_of[red]) == {0} and sorted(np.unique(finish_of)) == [0, 1], finish_of
        assert sorted(np.bincount(finish_of)) == [12, 12], finish_of
        assert route_split.judge_split(rows["finish-route-split"], rows, {}).answer == "pass"


def test_an_unassigned_face_is_a_gap_and_views_that_disagree_are_settled_by_the_squarer_view():
    """Owner, 2026-10-28: views disagreeing on 1.2 to 5.8% of eleven takes is a split decision, never a gap. A face
    takes the finish the views that see it most squarely give; a tie takes the finish round it."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        blue_left_out = lambda views, take: two_finish_answer(views, lambda view, colour: 1 if colour == RED else None)
        rows = split(folder, listed(folder, blue_left_out)[0])
        verdict = route_split.judge_split(rows["finish-route-split"], rows, {})
        assert verdict.answer == "fail" and "unassigned" in verdict.findings[0], verdict
        assert not (rows["finish-route-split"] / TAKE).exists()
    mesh = trimesh.creation.icosphere(subdivisions=3)
    apart = {"right": np.zeros(len(mesh.faces), dtype=int), "top": np.ones(len(mesh.faces), dtype=int)}
    votes = route_split.squared_votes(mesh, apart, route_split.cast.BASE, 2)
    found = route_split.shares(mesh, apart, route_split.finish_parts.voted(apart, 2))
    assert found["disagree"] == 1.0 and route_split.split_fault(found) is None, found  # recorded, no gap
    normals = mesh.face_normals
    side, up = np.abs(normals[:, 0]) > 0.9, np.abs(normals[:, 1]) > 0.9
    assert (votes[side].argmax(1) == 0).all() and (votes[up].argmax(1) == 1).all()  # the squarer view wins
    even = np.zeros((len(mesh.faces), 2))
    even[:, 1] = 1.0  # finish 1 round it, so a tie read by argmax alone (finish 0) shows
    patch = np.linalg.norm(mesh.triangles_center - (0, 0, 1), axis=1) < 0.4
    assert mesh.area_faces[patch].sum() / mesh.area > 0.02  # over a stray's size, so only the tie decides it
    even[patch] = 0.5  # tied between the two finishes
    finish_of = route_split.voted_finishes(mesh, even, 2)[1]
    assert (finish_of[patch] == 1).all()  # the finish round it
    even[patch, 0] = 0.6
    assert (route_split.voted_finishes(mesh, even, 2)[1][patch] == 0).all()  # not tied: its own finish


def test_the_split_decides_by_the_labels_alone():
    """The paper: the views are split into colour regions only so the list can label them. The blue box listed in
    red is split, its colour judged after the split against the close-up, never against a texture region here."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        far = lambda views, take: dict(two_finish_answer(views), finishes=[
            finish_entry("red paint"), finish_entry("blue paint", token="sign-red")])  # the blue box in red
        rows = split(folder, listed(folder, far)[0])
        assert json.loads((rows["finish-route-split"] / "split.json").read_text())[TAKE]["fault"] is None
        assert route_split.judge_split(rows["finish-route-split"], rows, {}).answer == "pass"


LIT_RED, LIT_BLUE = (180, 40, 30), (155, 125, 222)  # the close-up's colours, near sign-red and bay-three


SHADED_RED, SHADED_BLUE = (70, 8, 8), (60, 48, 90)  # the raw take's texture: the picture's light baked in


GREEN = (40, 170, 60)  # a label only the close-up shows, on the red box's front


def close_up_of(folder, model, side=256, label=False):
    """A close-up of the two boxes and its camera (Pixal3D's transforms.json, 3 in front, 1.2 rad across): each box
    in its lit colour where the camera sees it, clear elsewhere; with `label` the red box's front GREEN."""
    camera = folder / "transforms.json"
    camera.write_text(json.dumps({"camera_angle_x": 1.2, "frames": [{"transform_matrix": [
        [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 3.0], [0, 0, 0, 1]]}]}))
    loaded = route_cast.loaded(model)
    faces = route_cast.close_up_cast(loaded, route_cast.close_up_camera(camera), (side, side))[0]
    left = loaded.mesh.triangles_center[:, 0] < 0
    picture = np.zeros((side, side, 4), dtype=np.uint8)
    seen = faces >= 0
    picture[seen, :3] = np.where(left[faces[seen]][:, None], LIT_RED, LIT_BLUE)
    if label:
        front = left & (loaded.mesh.face_normals[:, 2] > 0.9)
        picture[seen & front[np.maximum(faces, 0)], :3] = GREEN
    picture[seen, 3] = 255
    Image.fromarray(picture).save(folder / "input.png")
    return {f"close-up {TAKE}": folder / "input.png", f"camera {TAKE}": camera}


def close_up_judged(folder, finishes):
    """bake_check's close-up faults of the two boxes baked each in its finish's colour (its token's, as the bake
    paints it), read against the finishes' close-up colours as the paint reports them (labels.json)."""
    bake_check = route_check.bake_check
    labelled = folder / "labelled"
    labelled.mkdir(exist_ok=True)
    (labelled / "labels.json").write_text(json.dumps({"finishes": finishes}))
    names = {route_settings.settings_name(finish["surface"], route_settings.applied(finish))
             if route_settings.applied(finish) else finish["surface"]: finish for finish in finishes}
    surfaces = {name: {"baked_lab": [float(value) for value in route_parts.finish_parts.library_lab(finish)],
                       "share": 0.5, "family": "painted"} for name, finish in names.items()}
    return bake_check.close_up_faults("two_boxes", {"surfaces": surfaces,
                                                     "close_up": bake_check.close_up_colours(labelled)})


def test_a_finish_is_held_against_its_colour_in_the_close_up_never_the_light_baked_texture():
    """Batch 1 try 4 (2026-10-25): 134 takes were gaps for a surface over dE 32 from a raw texture region, whose colours
    carry the picture's light. The boxes' texture is shaded over the limit from their tokens; the close-up shows
    them near: each keeps its listed surface and the bake check passes it. A wrong surface (the blue box as bare
    steel) is still off its colour, and the bake check still fails it against the close-up."""
    global RED, BLUE
    kept = RED, BLUE
    RED, BLUE = SHADED_RED, SHADED_BLUE
    finish_parts = route_parts.finish_parts
    try:
        with tempfile.TemporaryDirectory() as temporary:
            folder = pathlib.Path(temporary)
            rows = listed(folder, lambda views, take: two_finish_answer(views))[0]
            rows = parted(folder, split(folder, {**rows, **close_up_of(folder, rows[f"model {TAKE}"])}))
            record = json.loads((rows["surfaces-parts"] / "parts.json").read_text())["takes"][TAKE]
            assert record["colour_from"].startswith("close-up"), record["colour_from"]
            assert [finish["by"] for finish in record["finishes"]] == ["the list"] * 2, record["finishes"]
            assert all(finish["delta_e"] <= finish_parts.COLOUR_DELTA_E for finish in record["finishes"])
            finish_of = np.load(rows["finish-route-split"] / TAKE / "finish.npy").astype(int)
            textured = route_parts.seen_colours(rows["finish-route-views"] / TAKE, finish_of, 2)
            assert all(np.linalg.norm(colour - finish_parts.library_lab(finish)) > finish_parts.COLOUR_DELTA_E
                       for colour, finish in zip(textured, record["finishes"])), textured  # what the split failed
            assert close_up_judged(folder, record["finishes"]) == []
        with tempfile.TemporaryDirectory() as temporary:
            folder = pathlib.Path(temporary)
            library = folder / "library"
            library.mkdir()
            palette = route_parts.palette_library.read({"finish-route-palette": paletted(library),
                                                        "surface-library": libraried(library)})
            import part_judge
            steel = part_judge.code(list(route_parts.palette_library.take_surfaces({"kind": "two_boxes"},
                                                                                   palette)).index("bare_steel"))
            wrong = lambda views, take: dict(two_finish_answer(views), finishes=[
                finish_entry("red paint"), finish_entry("blue paint", surface=steel, token="steel")])
            rows = listed(folder, wrong)[0]
            rows = parted(folder, split(folder, {**rows, **close_up_of(folder, rows[f"model {TAKE}"])}))
            finishes = json.loads((rows["surfaces-parts"] / "parts.json").read_text())["takes"][TAKE]["finishes"]
            assert finishes[1]["surface"] == "bare_steel" and finishes[1]["by"] == "off its colour", finishes[1]
            faults = close_up_judged(folder, finishes)
            assert len(faults) == 1 and "bare_steel" in faults[0], faults
    finally:
        RED, BLUE = kept


def test_a_small_colour_far_from_the_rest_keeps_a_region_of_its_own():
    """greenhouse desk (2026-10-29): k-means spent its eight regions on the texture's greys, L* 21 to 62, and its red
    label had none. A grey ramp, a ramp of rust and 40 red pixels: under every seed the red keeps a region of its
    own, the greys and the rust share the rest."""
    greys = np.repeat(np.linspace(50, 210, 20000)[:, None], 3, axis=1)
    rust = np.stack([np.linspace(90, 170, 3000), np.linspace(70, 120, 3000), np.linspace(50, 80, 3000)], axis=1)
    pixels = np.concatenate([greys, rust, np.tile([[200, 30, 30]], (40, 1))]).astype(np.uint8)
    colours = {"front": pixels.reshape(1, -1, 3)}
    faces = {"front": np.zeros((1, len(pixels)), dtype=int)}
    red = route_cast.lab_of(np.array([[200, 30, 30]]))[0]
    for seed in range(7, 12):
        centres, per_pixel = route_views.colour_regions(colours, faces, seed)
        assert len(centres) <= route_views.REGIONS and np.linalg.norm(centres - red, axis=1).min() < 5, (seed, centres)
        assert len(np.unique(per_pixel["front"][0, -40:])) == 1  # one region holds the red, and only the red
        assert not np.isin(per_pixel["front"][0, :-40], per_pixel["front"][0, -40:]).any(), seed


def test_a_finish_only_the_close_up_shows_gets_its_region_its_faces_and_a_part():
    """greenhouse desk (2026-10-29): the close-up shows a red DANGER label, a blue decal and teal screens that the raw
    take's texture lacks, so no region of any view had them and no part owned them. The close-up, laid on the model
    through its camera, is one more view of the regions: its green label (on the red box's front, in no texture) has a
    region, the list labels it, and its faces take that finish; the finishes the views do show stay voted."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        views = folder / "views"
        views.mkdir()
        model = two_boxes(folder)
        inputs = {"surfaces": place_data(folder), "finish-route-palette": paletted(folder),
                  "surface-library": libraried(folder), f"model {TAKE}": model,
                  **close_up_of(folder, model, label=True)}
        route_views.make_views(inputs, views, 7, {"objects": [TAKE]})
        record = json.loads((views / "views.json").read_text())[TAKE]
        assert record["close_up_laid"]["laid"] and record["close_up_laid"]["fit"] >= route_cast.CLOSE_UP_FIT, record
        assert list(GREEN) in [entry["srgb"] for entry in record["regions"]], record["regions"]
        finish_of_srgb = {RED: 1, LIT_RED: 1, BLUE: 2, LIT_BLUE: 2, GREEN: 3}
        shown = route_list.regions_shown(views / TAKE, route_list.labelled_views(views / TAKE, record["views"]))
        assert route_views.CLOSE_UP in shown
        labels = [{"view": view, "region": region + 1,
                   "finish": finish_of_srgb[tuple(record["regions"][region]["srgb"])]}
                  for view, regions in shown.items() for region in regions]
        answer = {"finishes": [finish_entry("red paint"), finish_entry("blue paint", token="bay-three"),
                               finish_entry("green label")], "labels": labels}
        asked, original = [], route_list.ask
        route_list.ask = lambda bodies: asked.append(bodies) or {take: json.dumps(answer) for take in bodies}
        try:
            out = folder / "list"
            out.mkdir()
            route_list.make_list({**inputs, "finish-route-views": views}, out, 7, {"objects": [TAKE]})
        finally:
            route_list.ask = original
        body = asked[0][TAKE]
        assert len(body["contents"][0]["parts"]) == 2 * len(record["views"]) + 3  # the laid close-up's regions last
        assert "the view named close-up" in body["contents"][0]["parts"][-1]["text"]
        rows = parted(folder, split(folder, {**inputs, "finish-route-views": views, "finish-route-list": out}))
        finish_of = np.load(rows["finish-route-split"] / TAKE / "finish.npy")
        mesh = route_split.model_of(views / TAKE)
        front = (mesh.triangles_center[:, 0] < 0) & (mesh.face_normals[:, 2] > 0.9)
        assert (finish_of[front] == 2).all() and (finish_of[~front] != 2).all(), finish_of
        found = json.loads((rows["surfaces-parts"] / "parts.json").read_text())["takes"][TAKE]
        assert {row["words"] for row in found["parts"]} == {"red paint", "blue paint", "green label"}, found["parts"]


def test_a_take_with_no_usable_answer_is_a_gap_named_by_the_list():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        lost = route_ask.google_batch.Unanswered("the batch ended JOB_STATE_EXPIRED")
        rows, _ = listed(folder, lambda views, take: lost if take == TAKE else two_finish_answer(views),
                         takes=(TAKE, OTHER))
        assert not (rows["finish-route-list"] / f"{TAKE}.json").exists()
        assert (rows["finish-route-list"] / f"{OTHER}.json").exists()
        verdict = route_list.judge_list(rows["finish-route-list"], rows, {})
        assert verdict.answer == "fail" and list(verdict.findings) == [
            f"{TAKE}: no finish list (no usable answer: Unanswered('the batch ended JOB_STATE_EXPIRED'))"], verdict


def test_the_parts_row_writes_the_methods_interface_each_finish_checked_against_its_colour():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        rows = parted(folder, split(folder, listed(folder, lambda views, take: two_finish_answer(views))[0]))
        found = json.loads((rows["surfaces-parts"] / "parts.json").read_text())
        record = found["takes"][TAKE]
        assert record["method"] == "finish-route" and found["left_out"] == {}, found
        assert {row["words"] for row in record["parts"]} == {"red paint", "blue paint"}, record["parts"]
        assert all(entry["measured_lab"] is not None and entry["by"] for entry in record["finishes"]), record
        assert len(np.load(rows["surfaces-parts"] / TAKE / "parts.npy")) == 24
        assert surfaces.finish_parts.parts_faults(rows["surfaces-parts"]) == []
        assert route_parts.judge_parts(rows["surfaces-parts"], rows, {}).answer == "pass"


def test_a_light_built_in_code_takes_the_glowing_surface_nearest_its_colour():
    with tempfile.TemporaryDirectory() as temporary:
        mark = pathlib.Path(temporary) / "code.json"
        mark.write_text(json.dumps({"route": "code", "size": [1.0, 0.1, 0.1]}))
        assert route_parts.lit_take({"kind": "light", "object": "wall light"}, mark)
        assert not route_parts.lit_take({"kind": "pipe", "object": "wall pipes"}, mark)
        mark.write_text(json.dumps({"route": "code", "size": [0.3, 0.3, 6.0]}))  # a stem lamp's post is a post
        assert not route_parts.lit_take({"kind": "light", "object": "street light"}, mark)
    every = {"warm": {"recipe": "glowing", "colour": [1.0, 0.8, 0.3]}, "cold": {"recipe": "glowing", "colour":
             [0.3, 0.6, 1.0]}, "steel": {"recipe": "bare_metal", "colour": [0.5, 0.5, 0.5]}}
    finish = {"finish": "light bar", "surface": "steel", "fits": True, "by": "the list",
              "measured_lab": [float(value) for value in route_parts.finish_parts.library_lab(every["cold"])]}
    (lit,) = route_parts.lit_finishes([finish], every)
    assert lit["surface"] == "cold" and lit["fits"] and lit["by"] == "its light, built in code", lit
    (unlit,) = route_parts.lit_finishes([finish], {"steel": every["steel"]})
    assert unlit["fits"] is False and "no glowing surface" in unlit["new_surface"]["why"], unlit
    # a light bar listed as its glass tube and its metal end caps (its build carries its crop, so each has its part):
    # the tube glows, the caps keep their own surface (airlock's wall lamp, 2026-10-29: its caps baked glowing)
    tube, caps = dict(finish, family="glass"), dict(finish, finish="metal end caps", family="steel")
    (glows, kept) = route_parts.lit_finishes([tube, caps], every)
    assert glows["surface"] == "cold" and kept == caps, (glows, kept)


def baked(folder, rows):
    """The bake made through the rows, the cloud call faked: each take's job writes back its labelled take, its
    models' entries and a baked model. The bake's inputs, its output and the calls made (with the jobs' files)."""
    data = json.loads(rows["surfaces"].read_text())
    rows["surfaces"].write_text(json.dumps(dict(data, library="cockpit", bake={"models": {"two_boxes": TAKE}})))
    inputs = {"surfaces": rows["surfaces"], "surfaces-parts": rows["surfaces-parts"],
              "finish-route-palette": rows["finish-route-palette"], "surface-library": rows["surface-library"],
              "resting rules": REPO / "data/checks/resting.json"}
    out = folder / "bake"
    out.mkdir()
    calls = []

    def run(command, **_):
        jobs = [json.loads(pathlib.Path(path).read_text()) for path in command if str(path).endswith("-job.json")]
        calls.append({"command": command, "jobs": jobs,
                      "files": {path.name: json.loads(path.read_text()) for path in out.glob(".bake-*.json")}})
        for job in jobs:
            take = json.loads(pathlib.Path(job["args"][0]).read_text())[route_bake.place_line.TAKE]
            labelled = out / "labelled" / take
            labelled.mkdir(parents=True)
            (labelled / "labels.json").write_text(json.dumps({"take": take, "unnamed_parts": []}))
            (out / "entries").mkdir(exist_ok=True)
            (out / "entries" / f"{take}.json").write_text(json.dumps({"two_boxes": {"parts": str(labelled),
                                                                                   "faces": 100}}))
            (out / "made").mkdir(exist_ok=True)
            (out / "made" / "two_boxes.gltf").write_text("{}")
        return subprocess.CompletedProcess(command, 0, "", "")
    original = route_bake.subprocess.run
    route_bake.subprocess.run = run
    try:
        route_bake.make_bake(inputs, out, 7, {})
    finally:
        route_bake.subprocess.run = original
    return inputs, out, calls


def test_the_bake_paints_and_bakes_each_take_in_one_card_job_with_the_lists_settings_and_the_paint_takes_it_over():
    colours = library.token_colours({"tokens": TOKENS})
    finish_parts = route_parts.finish_parts
    kept = finish_parts.COLOUR_DELTA_E
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        finish_parts.COLOUR_DELTA_E = 1000.0  # held wide: every finish keeps its listed surface, so its settings
        try:
            rows = parted(folder, split(folder, listed(folder, lambda views, take: two_finish_answer(views))[0]))
            inputs, out, calls = baked(folder, rows)
        finally:
            finish_parts.COLOUR_DELTA_E = kept
        parts = json.loads((rows["surfaces-parts"] / "parts.json").read_text())["takes"][TAKE]["parts"]
        assert all(row["settings"] for row in parts), parts
        assert len(calls) == 1 and pathlib.Path(calls[0]["command"][1]).name == "blender_cloud.py", calls
        assert calls[0]["command"][-1] == route_bake.place_line.CLASSES  # the bake's cards, one call
        (job,) = calls[0]["jobs"]
        assert job["script"] == route_bake.SCRIPT and str(out / "made") in job["outputs"], job
        records = calls[0]["files"][f".bake-{TAKE}-records.json"]
        head = calls[0]["files"][f".bake-{TAKE}-head.json"]
        assert head["models"] == ["two_boxes"], head
        assert (head["wear"], head["dirt"]) == (0.4, 0.3), head  # the scene palette's, not place.json's
        for record, row in zip(records, parts):
            assert record["surface"] == route_settings.settings_name(row["judge"], row["settings"]), record
            spec = head["specs"][record["surface"]]
            assert spec["library"] == row["judge"] and spec["token"] == row["settings"]["token"], spec
            assert spec["colour"] == colours[row["settings"]["token"]], spec
            assert spec["roughness"] == row["settings"]["roughness"] == 1.0, spec  # the list's 1.4, clipped
            assert spec["seed"] == row["settings"]["seed"] and spec.get("wear") == row["settings"].get("wear"), spec
        # the blue finish's own wear (a cause given) rides its spec; the red one's level without a cause is not taken
        assert sorted(spec.get("wear", 0) for spec in head["specs"].values() if "settings" in spec) == [0, 0.8]
        assert json.loads((out / "specs.json").read_text()) == head["specs"]
        assert json.loads((out / "baked.json").read_text())["two_boxes"]["parts"] == TAKE
        assert not list(out.glob(".bake-*"))  # the jobs' files are gone
        assert route_bake.bake_faults(out) == [] and route_bake.judge_baked(out, inputs, {}).answer == "pass"
        paint = folder / "paint"
        paint.mkdir()
        route_paint.make_paint({"surfaces-bake": out}, paint, 7, {})
        assert (paint / "painted.json").read_text() == (out / "painted.json").read_text()
        assert (paint / "labelled" / TAKE / "labels.json").exists()


def test_the_check_holds_each_surface_against_the_spec_the_bake_baked():
    with tempfile.TemporaryDirectory() as temporary:
        bake = pathlib.Path(temporary)
        (bake / "specs.json").write_text(json.dumps({"painted_panel__sign_red_r100_m000": {"colour": [1, 0, 0]}}))
        seen = {}
        kept = (route_check.bake_check.check_step, library.by_library, library.resolved, library.wear_of,
                route_check.bake_check.check_model)
        route_check.bake_check.check_step = lambda inputs, out: seen.update(
            library=library.by_library("cockpit"), resolved=library.resolved("cockpit"), wear=library.wear_of("cockpit"))
        try:
            route_check.check_step({"bake": bake, "finish-route-palette": paletted(bake),
                                    "surface-library": libraried(bake)}, bake)
        finally:
            (route_check.bake_check.check_step, library.by_library, library.resolved, library.wear_of,
             route_check.bake_check.check_model) = kept
        assert seen["library"]["painted_panel__sign_red_r100_m000"] == {"colour": [1, 0, 0]}
        assert "painted_panel" in seen["library"]  # the library's own surfaces stay
        # the scene's wear, dirt and dirt colour are its scene palette's, nothing of place.json's
        assert seen["wear"] == (0.4, 0.3) and seen["resolved"] == {}, seen["wear"]
        assert seen["library"]["painted_panel"]["dirt_colour"] == library.token_colours({"tokens": TOKENS})["regolith"]
    # a surface with its own wear is measured at it, the others at the place's
    measured = lambda name, entry, labelled, made, materials, dirt=0.0, wear=0.0: {
        "surfaces": {surface: {"wear": wear} for surface in materials}}
    checked = route_check.own_wear_checked(measured)("m", {}, None, None, {"a": {}, "b": {"wear": 0.8}}, 0.2, 0.4)
    assert checked["surfaces"] == {"a": {"wear": 0.4}, "b": {"wear": 0.8}}, checked


def rechecked(folder, answer, wide=True):
    """The recheck made through the rows (the colour check held wide unless `wide` is False), its one batch faked to
    answer `answer` (a dict, or an exception the batch holds): the take's record, its verdict and the batches asked."""
    finish_parts = route_parts.finish_parts
    kept = finish_parts.COLOUR_DELTA_E
    finish_parts.COLOUR_DELTA_E = 1000.0 if wide else 0.5
    asked = []
    original = route_recheck.ask
    route_recheck.ask = lambda bodies: asked.append(bodies) or {
        take: answer if isinstance(answer, Exception) else json.dumps(answer) for take in bodies}
    try:
        rows = parted(folder, split(folder, listed(folder, lambda views, take: two_finish_answer(views))[0]))
        out = folder / "recheck"
        out.mkdir()
        route_recheck.make_recheck(rows, out, 7, {"objects": [TAKE]})
        record = json.loads((out / "recheck.json").read_text())[TAKE]
        return record, route_recheck.judge_recheck(out, rows, {}), asked
    finally:
        route_recheck.ask = original
        finish_parts.COLOUR_DELTA_E = kept


def test_the_recheck_words_a_finish_in_the_token_it_is_drawn_and_baked_in():
    """astronaut-made-s1 (2026-10-22): glass-brown patches on suit_patches (red by default) were worded red."""
    surfaces = {"suit_patches": {"family": "fabric", "colour": [1.0, 0.0, 0.0]}}
    tokens = {"glass-brown": [0.31855, 0.13287, 0.0331]}
    finish = {"finish": "brown fabric", "parts": "patches", "surface": "suit_patches",
              "settings": {"token": "glass-brown", "roughness": 0.9, "metal": 0.0}}
    line = route_recheck.finish_lines([finish], surfaces, tokens)
    assert "roughness 0.90" in line and "drawn red" not in line, line
    assert "drawn red" in route_recheck.finish_lines([dict(finish, settings=None)], surfaces, tokens)


def test_the_recheck_sorts_one_answer_into_pass_or_a_gap_its_suggestion_unapplied():
    with tempfile.TemporaryDirectory() as temporary:
        record, verdict, asked = rechecked(pathlib.Path(temporary),
                                           {"finishes": [{"finish": 1, "matches": True, "why": "red"},
                                                         {"finish": 2, "matches": True, "why": "blue"}]})
        assert len(asked) == 1 and record["passed"] and verdict.answer == "pass", (record, verdict)
    with tempfile.TemporaryDirectory() as temporary:
        record, verdict, asked = rechecked(pathlib.Path(temporary), {"finishes": [
            {"finish": 1, "matches": False, "why": "too dull", "token": "alarm", "roughness": 0.2},
            {"finish": 2, "matches": True, "why": "blue"}]})
        assert len(asked) == 1 and not record["passed"], record
        assert record["suggested"] == {"red paint": {"token": "alarm", "roughness": 0.2}}, record["suggested"]
        assert verdict.answer == "fail" and "too dull" in verdict.findings[0], verdict
        assert (pathlib.Path(temporary) / "recheck" / TAKE / "checked-front.png").exists()


def test_the_recheck_makes_an_unanswered_take_a_gap_and_never_asks_a_take_off_its_colour():
    with tempfile.TemporaryDirectory() as temporary:
        record, verdict, asked = rechecked(pathlib.Path(temporary),
                                           route_ask.google_batch.Unanswered("the batch gave no answer for it"))
        assert len(asked) == 1 and record["asked"] and record["fault"].startswith("no usable answer"), record
        assert verdict.answer == "fail", verdict
    with tempfile.TemporaryDirectory() as temporary:
        record, verdict, asked = rechecked(pathlib.Path(temporary), {"finishes": []}, wide=False)
        assert not asked and not record["asked"] and record["colour_faults"], (record, asked)
        assert verdict.answer == "fail" and "the free colour check, not asked" in verdict.findings[0], verdict


def palette_asked(folder, answer, place="cockpit", concept=True, close_ups=()):
    """The palette row made on a locked concept (or, `concept` False, on a folder of every scene's) and the takes'
    close-ups named, its one ask faked to answer `answer` (a dict, or an exception the batch holds): its output, its
    verdict and the batches asked."""
    concepts = folder / "concepts"
    concepts.mkdir()
    for name in ("cockpit", "hangar"):
        Image.new("RGB", (64, 36), (90, 90, 100)).save(concepts / f"{name}.png")
    surfaces_data = folder / "place.json"
    surfaces_data.write_text(json.dumps({"place": place, "takes": {}}))
    inputs = {"surfaces": surfaces_data, "library": REPO / "data/library/materials.json",
              **({"concept": concepts / "cockpit.png"} if concept else {"concepts": concepts})}
    for take in close_ups:
        Image.new("RGB", (32, 64), (110, 80, 60)).save(folder / f"{take}.png")
        inputs[f"close-up {take}"] = folder / f"{take}.png"
    asked = []
    original = scene_palette.ask
    scene_palette.ask = lambda bodies: asked.append(bodies) or {
        key: answer if isinstance(answer, Exception) else json.dumps(answer) for key in bodies}
    out = folder / "palette"
    out.mkdir()
    try:
        scene_palette.make_palette(inputs, out, 7, {})
    finally:
        scene_palette.ask = original
    return out, scene_palette.judge_palette(out, inputs, {}), asked


def coined(*tokens):
    """A palette answer's tokens, each a name, its colour and what wears it."""
    return [{"token": token, "colour": colour, "what": f"{token} surfaces"} for token, colour in tokens]


def test_the_palette_is_read_from_the_locked_concept_by_one_ask():
    answer = {"palette": coined(("steel", "#9BA2A9"), ("hazard", "#f2c21a"), ("glass", "#24313a"),
                                ("regolith", "#8b8883"), ("steel", "#000000")),
              "wear": "worn", "cause": "scuffed decks", "dirt": 1.7, "dirt_token": "regolith"}
    with tempfile.TemporaryDirectory() as temporary:
        out, verdict, asked = palette_asked(pathlib.Path(temporary), answer)
        assert len(asked) == 1 and list(asked[0]) == ["cockpit"], asked  # one ask a scene, in one batch
        parts = asked[0]["cockpit"]["contents"][0]["parts"]
        assert len(parts) == 2 and "inline_data" in parts[0] and "locked concept" in parts[1]["text"], parts
        assert "people in it wear" in parts[1]["text"] and "grime itself" in parts[1]["text"], parts
        palette = json.loads((out / "palette.json").read_text())
        # its own tokens in the answer's order, a token named twice keeping its first colour; no old token offered
        assert palette["tokens"] == {"steel": "#9ba2a9", "hazard": "#f2c21a", "glass": "#24313a",
                                     "regolith": "#8b8883"}, palette
        assert palette["wear"] == {"level": "worn", "dirt": 1.0, "dirt_token": "regolith", "cause": "scuffed decks"}
        assert verdict.answer == "pass" and palette_library.wear(palette) == (0.8, 1.0), verdict
        assert "sign-red" not in parts[1]["text"] and "hull-trim" not in parts[1]["text"]
        try:  # no surface exists until the surface-library row makes them: the missing input is named
            palette_library.offered(palette)
        except library.LibraryEmpty as empty:
            assert "run surface-library first" in str(empty), empty
        else:
            raise AssertionError("surfaces offered before the scene's surface library was made")
        assert scene_palette.palette_faults(out) == []


def test_a_palette_off_the_library_or_unanswered_or_too_narrow_fails_by_name():
    with tempfile.TemporaryDirectory() as temporary:
        out, verdict, _ = palette_asked(pathlib.Path(temporary), {"palette": coined(("steel", "#9ba2a9")),
                                                             "wear": "shiny", "cause": "", "dirt": 0.2,
                                                             "dirt_token": "steel"})
        assert not (out / "palette.json").exists() and verdict.answer == "fail", verdict
        assert "no usable answer" in verdict.findings[0], verdict
    with tempfile.TemporaryDirectory() as temporary:
        out, verdict, _ = palette_asked(pathlib.Path(temporary), route_ask.google_batch.Unanswered("none for it"))
        assert verdict.answer == "fail" and "none for it" in verdict.findings[0], verdict
    with tempfile.TemporaryDirectory() as temporary:
        out, verdict, _ = palette_asked(pathlib.Path(temporary), {"palette": coined(("steel", "#9ba2a9")),
                                                             "wear": "new", "cause": "", "dirt": 0.0,
                                                             "dirt_token": "steel"})
        assert verdict.answer == "fail" and "a palette of 1 tokens" in verdict.findings[0], verdict
    with tempfile.TemporaryDirectory() as temporary:  # a colour not #rrggbb, or a dirt token not its own
        out, verdict, _ = palette_asked(pathlib.Path(temporary), {"palette": coined(("steel", "grey")), "wear": "new",
                                                             "cause": "", "dirt": 0.0, "dirt_token": "steel"})
        assert verdict.answer == "fail" and "no usable answer" in verdict.findings[0], verdict


def test_a_line_no_scene_owns_is_asked_over_every_concept():
    with tempfile.TemporaryDirectory() as temporary:
        answer = {"palette": coined(*((token, TOKENS[token]) for token in ("steel", "glass", "sign-red", "regolith"))),
                  "wear": "new", "cause": "fresh", "dirt": 0.0, "dirt_token": "regolith"}
        out, verdict, asked = palette_asked(pathlib.Path(temporary), answer, place="people", concept=False)
        parts = asked[0]["people"]["contents"][0]["parts"]
        assert sum("inline_data" in part for part in parts) == 2 and "every scene" in parts[-1]["text"], parts
        # the line's own objects, its people, are what its palette covers (astronaut-made, 2026-10-23)
        assert "skin and hair" in parts[-1]["text"] and "people in it wear" not in parts[-1]["text"], parts
        assert verdict.answer == "pass" and json.loads((out / "palette.json").read_text())["pictures"] == 2
    # only a line no scene owns reads every locked concept; a scene declares its own, locked yet or not, so a scene
    # with none (environment 1's launch) blocks on it by name instead of being asked over every other scene's
    assert scene_palette.files("people")["concepts"] == "{home}/design/concepts"
    for scene in ("cockpit", "no-such-scene"):
        found = scene_palette.files(scene)
        assert found["concept"] == "{home}/design/concepts/" + f"{scene}.png" and "concepts" not in found, found


def test_the_palette_sees_every_take_s_close_up_after_the_concepts():
    """astronaut-made, 2026-10-23: asked over the concepts alone the people's palette had no brown, and the brown
    trousers its close-up shows took moon-dust, 20 L* lighter. The close-ups go with the concepts, every take's whatever
    the object filter keeps, and the row waits on the Pixal3D row that leaves them; with none the ask reads as before."""
    answer = {"palette": coined(*((token, TOKENS[token]) for token in ("steel", "glass", "sign-red", "regolith"))),
              "wear": "new", "cause": "fresh", "dirt": 0.0, "dirt_token": "regolith"}
    with tempfile.TemporaryDirectory() as temporary:
        out, verdict, asked = palette_asked(pathlib.Path(temporary), answer, place="people", concept=False,
                                            close_ups=("worker-t1", "pilot-t1"))
        parts = asked[0]["people"]["contents"][0]["parts"]
        assert sum("inline_data" in part for part in parts) == 4, parts
        assert "The last 2 pictures are close-ups" in parts[-1]["text"] and "first 2 pictures" in parts[-1]["text"]
        assert verdict.answer == "pass" and json.loads((out / "palette.json").read_text())["close_ups"] == 2
    with tempfile.TemporaryDirectory() as temporary:
        out, _, asked = palette_asked(pathlib.Path(temporary), answer)
        text = asked[0]["cockpit"]["contents"][0]["parts"][-1]["text"]
        assert "The picture is the scene's locked concept." in text and "close-up" not in text, text
        assert "close_ups" not in json.loads((out / "palette.json").read_text())
    with tempfile.TemporaryDirectory() as temporary:
        home = pathlib.Path(temporary)
        original = route_data.pixal_folder
        route_data.pixal_folder = lambda: home
        try:
            for take in ("astronaut-made-s1", "pilot-made-s1"):
                (home / f"{take}.svviews").mkdir()
                Image.new("RGB", (8, 8)).save(home / f"{take}.svviews" / "input.png")
            found = scene_palette.palette_files("people")
        finally:
            route_data.pixal_folder = original
        assert sorted(name for name in found if name.startswith("close-up ")) == [
            "close-up astronaut-made-s1", "close-up pilot-made-s1"], found
    palette = next(row for row in shapes_first.finish_route() if row.name == "finish-route-palette")
    assert "pixal" in palette.after and not palette.selects, palette.after


def library_made(folder, answer, kinds=("two_boxes",), grounds=None, plan=None):
    """The surface-library row made on the scene palette and its takes' kinds, its one ask faked to answer `answer`
    (a dict, or an exception the batch holds): its output, its verdict and the batches asked. `grounds` (terrain
    rows) gives it a kept inventory and a kept sky on the Moon; `plan` a locked plan."""
    concept = folder / "cockpit.png"
    Image.new("RGB", (64, 36), (90, 90, 100)).save(concept)
    surfaces_data = folder / "place.json"
    surfaces_data.write_text(json.dumps({"place": "cockpit", "takes": {
        f"{kind}-t1": {"kind": kind, "object": kind.replace("_", " ")} for kind in kinds}}))
    inputs = {"surfaces": surfaces_data, "library": REPO / "data/library/materials.json", "concept": concept,
              "sounds": REPO / "data/sound/surfaces.json", "finish-route-palette": paletted(folder)}
    if grounds:
        from score.review import setting
        (folder / "inventory.json").write_text(json.dumps({"rows": grounds}))
        (folder / "sky.json").write_text(json.dumps({"setting": setting.checked(setting.now()), "site": {"on": "moon"}}))
        inputs.update(inventory=folder / "inventory.json", sky=folder / "sky.json",
                      reference=REPO / "data/physics/bodies.json")
    if plan:
        (folder / "plan.json").write_text(json.dumps(plan))
        inputs["plan"] = folder / "plan.json"
    asked = []
    original = scene_library.ask
    scene_library.ask = lambda bodies: asked.append(bodies) or {
        key: answer if isinstance(answer, Exception) else json.dumps(answer) for key in bodies}
    out = folder / "made-library"
    out.mkdir()
    try:
        scene_library.make_library(inputs, out, 7, {})
    finally:
        scene_library.ask = original
    return out, scene_library.judge_library(out, inputs, {}), asked


def test_the_scene_s_surfaces_are_made_fresh_from_its_palette_and_kinds_by_one_ask():
    answer = {"surfaces": [
        {"name": "Hull Panel", "family": "Paint", "recipe": "painted_metal", "token": "hull-trim", "roughness": 0.4,
         "metal": 0.0, "colours": [{"setting": "bare", "token": "steel"}, {"setting": "second", "token": "glass"}],
         "sound": "steel_plate", "kinds": ["two_boxes"]},
        {"name": "window", "family": "glass", "recipe": "glass", "token": "glass", "roughness": 1.6, "metal": 0.0,
         "sound": "glass", "kinds": []}]}
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        out, verdict, asked = library_made(folder, answer)
        assert len(asked) == 1 and list(asked[0]) == ["cockpit"], asked  # one ask a scene, in one batch
        body = asked[0]["cockpit"]
        text = body["contents"][0]["parts"][-1]["text"]
        assert "two_boxes: two boxes" in text and "painted_metal" in text and "colours: bare" in text, text
        assert "steel_grating" in text  # the sound surfaces it may sound like
        schema = body["generationConfig"]["responseSchema"]["properties"]["surfaces"]["items"]["properties"]
        assert schema["token"]["enum"] == list(PALETTE["tokens"]) and "glass" in schema["recipe"]["enum"], schema
        made = json.loads((out / "materials.json").read_text())
        panel = made["families"]["paint"]["variants"]["hull_panel"]
        # its recipe's colour settings in its own tokens; a setting the recipe does not name is not taken
        assert panel["bare"] == "steel" and "second" not in panel and panel["token"] == "hull-trim", panel
        assert made["families"]["glass"]["variants"]["window"]["roughness"] == 1.0  # held to 0 to 1
        assert made["kinds"] == {"two_boxes": ["hull_panel"]} and made["tokens"] == PALETTE["tokens"], made
        assert made["dirt"] == "regolith" and panel["seed"] != made["families"]["glass"]["variants"]["window"]["seed"]
        assert made["families"]["paint"]["surface"] == panel["surface"] == "steel_plate"  # what the sound layer plays
        assert verdict.answer == "pass" and verdict.measures["surfaces"] == 2, verdict
        # the rows after it read this library through the palette: the take's kind list, its specs in its tokens
        palette = palette_library.read({"finish-route-palette": folder / "palette", "surface-library": out})
        assert set(palette_library.take_surfaces({"kind": "two_boxes"}, palette)) == {"hull_panel", "window"}
        assert palette_library.specs(palette)["hull_panel"]["bare"] == palette_library.library_tokens(palette)["steel"]


def test_a_scene_library_missing_a_kind_or_unanswered_fails_by_name():
    answer = {"surfaces": [{"name": "panel", "family": "paint", "recipe": "painted_metal", "token": "hull-trim",
                            "roughness": 0.4, "metal": 0.0, "kinds": ["two_boxes"]}]}
    with tempfile.TemporaryDirectory() as temporary:
        out, verdict, _ = library_made(pathlib.Path(temporary), answer, kinds=("two_boxes", "crate"))
        assert verdict.answer == "fail", verdict
        assert {"kind crate has no surface", "panel: token None (bare) is not the palette's",
                "panel: sound surface None is not known"} <= set(verdict.findings), verdict.findings
    with tempfile.TemporaryDirectory() as temporary:
        out, verdict, _ = library_made(pathlib.Path(temporary), route_ask.google_batch.Unanswered("none for it"))
        assert not (out / "materials.json").exists() and verdict.answer == "fail", verdict
        assert "none for it" in verdict.findings[0], verdict


def test_the_shell_a_locked_plan_lays_is_a_kind_the_scene_library_must_cover():
    box = [[0.0, 0.0], [6.0, 0.0], [6.0, 4.0], [0.0, 4.0]]
    room = {"w": 6.0, "d": 4.0, "outline": box,
            "walls": [{"from": one, "to": two, "thick": 0.2, "tall": 2.5} for one, two in zip(box, box[1:] + box[:1])],
            "roofs": [{"kind": "flat", "points": box, "eave": 2.5, "top": 2.5}],
            "stairs": [{"kind": "stair", "points": [[4.0, 2.0], [5.0, 2.0], [5.0, 4.0], [4.0, 4.0]]}]}
    panel = {"name": "panel", "family": "paint", "recipe": "painted_metal", "token": "hull-trim", "roughness": 0.4,
             "metal": 0.0, "colours": [{"setting": "bare", "token": "steel"}], "sound": "steel_plate",
             "kinds": ["two_boxes"]}
    with tempfile.TemporaryDirectory() as temporary:
        out, verdict, asked = library_made(pathlib.Path(temporary), {"surfaces": [panel]}, plan=room)
        body = asked[0]["cockpit"]
        enum = body["generationConfig"]["responseSchema"]["properties"]["surfaces"]["items"]["properties"]["kinds"]
        assert {"floor", "wall", "roof", "stairs"} <= set(enum["items"]["enum"]), enum  # no take is the shell
        assert "- wall: the room's walls" in body["contents"][0]["parts"][-1]["text"]
        assert verdict.answer == "fail" and {"kind floor has no surface", "kind wall has no surface",
                                             "kind roof has no surface"} <= set(verdict.findings), verdict.findings
    shell = dict(panel, kinds=["two_boxes", "floor", "wall", "roof", "stairs"])
    with tempfile.TemporaryDirectory() as temporary:
        out, verdict, _ = library_made(pathlib.Path(temporary), {"surfaces": [shell]}, plan=room)
        assert verdict.answer == "pass", verdict
        made = json.loads((out / "materials.json").read_text())
        # the shell's parts find their surface in it (the earth seed, the scene record, the tiles)
        assert {part: palette_library.shell_surface(part, made) for part in ("deck", "wall", "roof", "stair")} == {
            "deck": "panel", "wall": "panel", "roof": "panel", "stair": "panel"}
    # an open place with a raised level: its level is the floor's kind; one with neither lays no shell
    level = {"w": 6.0, "d": 4.0, "levels": [{"name": "stage", "points": box, "height": 0.5}]}
    assert list(scene_library.shell_kinds(level)) == ["floor"]
    assert scene_library.shell_kinds({"w": 6.0, "d": 4.0}) == {}


def test_a_scene_library_offers_and_keeps_no_recipe_that_paints_a_picture():
    """surface-library@people (2026-10-22): suit_patches as `printed`, with no picture, stopped the bake."""
    answer = {"surfaces": [{"name": "patches", "family": "fabric", "recipe": "printed", "token": "hull-trim",
                            "roughness": 0.4, "metal": 0.0, "kinds": ["two_boxes"]}]}
    with tempfile.TemporaryDirectory() as temporary:
        out, verdict, asked = library_made(pathlib.Path(temporary), answer)
        body = asked[0]["cockpit"]
        enum = body["generationConfig"]["responseSchema"]["properties"]["surfaces"]["items"]["properties"]["recipe"]
        assert not set(scene_library.PICTURED) & set(enum["enum"]), enum
        assert "patches: recipe printed paints a picture, and the library has none" in verdict.findings, verdict


def test_a_scene_s_ground_rows_take_their_natural_ground_by_rule():
    """Each terrain row of the kept inventory is a kind the library covers with the recipe its words name, else its
    body's physics (the Moon's: airless, regolith); one covered with another recipe fails by name."""
    rows = [{"id": "crater_1", "noun": "crater", "name": "large crater", "terrain": True},
            {"id": "drift", "noun": "drift", "name": "sand drift", "terrain": True},
            {"id": "hut", "noun": "hut", "name": "hut"}]
    answer = {"surfaces": [
        {"name": "moon_dust", "family": "regolith", "recipe": "regolith", "token": "hull-trim", "roughness": 0.9,
         "metal": 0.0, "colours": [{"setting": "second", "token": "steel"}], "sound": "stone",
         "kinds": ["two_boxes", "crater"]},
        {"name": "drift_paint", "family": "paint", "recipe": "cast_metal", "token": "steel", "roughness": 0.5,
         "metal": 0.0, "sound": "stone", "kinds": ["drift"]}]}
    with tempfile.TemporaryDirectory() as temporary:
        out, verdict, asked = library_made(pathlib.Path(temporary), answer, grounds=rows)
        text = asked[0]["cockpit"]["contents"][0]["parts"][-1]["text"]
        assert "- crater: regolith (Moon:" in text and "- drift: sand (the row drift says sand)" in text, text
        assert "crater: large crater" in text and "hut" not in text  # a ground row is a kind; another row is not
        assert verdict.answer == "fail" and verdict.findings == ("ground drift has no surface of its recipe sand",), \
            verdict.findings


def test_the_empty_library_is_a_named_missing_input():
    """Every old material retired (owner, 2026-10-21): the repository's library is the method alone, and a reader
    of a surface gets the missing input named, never a KeyError."""
    method = library.theme_library()
    assert method["families"] == {} and method["tokens"] == {} and method["pictures"] == {}, method
    assert set(method["recipes"]) and set(method["wear_levels"]) == {"new", "worked", "worn"}
    assert not [setting for defaults in method["recipes"].values() for setting in defaults
                if isinstance(defaults[setting], str)], "a recipe default names an old token"
    assert library.library_specs() == {} and library.variants(method) == {}  # a lookup finds no surface
    for read in (lambda: library.spec(method, "painted_panel", "hull-trim", {}),
                 lambda: route_list.palette_library.specs(PALETTE)):
        try:
            read()
        except library.LibraryEmpty as empty:
            assert library.EMPTY in str(empty), empty
        else:
            raise AssertionError("a surface read from the empty library")


def test_the_scene_s_shell_surfaces_are_its_library_s_for_the_shell_kinds():
    """The shell laid from the locked plan and a prop's paint take one answer (palette_library.SHELL_KINDS): each
    shell part the first variant the scene library gives one of its kinds; none while no library is read."""
    with tempfile.TemporaryDirectory() as folder:
        library = pathlib.Path(folder) / "materials.json"
        library.write_text(json.dumps({"kinds": {"floor": ["deck_plate", "rubber_mat"], "ceiling": ["ceiling_panel"],
                                                 "wall": [], "crate": ["crate_wood"]}}))
        palette = {"tokens": {}, "wear": {}, "library": str(library)}
        assert palette_library.shell_surfaces(palette) == ["ceiling_panel", "deck_plate"]  # no wall surface, no crate
        content = json.loads(library.read_text())
        assert palette_library.shell_surface("stair", content) == "deck_plate"  # no stairs kind: the floor's
        assert palette_library.shell_surface("roof", content) == "ceiling_panel"
        assert palette_library.shell_surface("wall", content) is None
    assert palette_library.shell_surfaces({"tokens": {}, "wear": {}}) == []


def test_paid_asks_refuse_outside_a_cleared_run(monkeypatch):
    """An uncached request is refused outside a cleared run; a batch the cache answers whole runs with no clearance
    and no key (fault, 2026-10-29: body-face-earth refused in a free-only run although the cache held its answer)."""
    from score.adapters import compute
    sent, real = [], route_ask.google_batch.generate
    monkeypatch.delenv(compute.TICKET, raising=False)
    monkeypatch.setattr(route_ask.google_batch, "generate", lambda *asked: sent.append(asked) or {})
    monkeypatch.setattr(route_ask.finish_ask, "secret_key", lambda: "key")
    cached, uncached = {"ask": "cached"}, {"ask": "uncached"}
    answer = {"candidates": [{"content": {"parts": [{"text": "{}"}]}, "finishReason": "STOP"}]}
    route_ask.google_spend.keep(route_ask.google_spend.cache_path(route_ask.finish_ask.LIST_MODEL, cached), answer)
    with pytest.raises(compute.Refused):
        route_ask.asked({TAKE: cached, "other": uncached}, "test")
    assert not sent, "a Gemini batch was sent outside a cleared run"
    monkeypatch.setattr(route_ask.google_batch, "generate",
                        lambda model, asked, key, caller: sent.append(key) or real(model, asked, key, caller))
    assert route_ask.asked({TAKE: cached}, "test") == {TAKE: "{}"}
    assert sent == [None], "a batch the cache answers asked for the key"


def test_an_answer_that_does_not_parse_is_a_gap_dropped_from_the_cache():
    """Fault (2026-10-25, surface-library@camp): a malformed JSON answer was kept in the cache, so every later try read
    the same broken answer back."""
    from score.adapters import compute
    broken = {"candidates": [{"content": {"parts": [{"text": '{"surfaces": [{,}]}'}]}, "finishReason": "STOP"}]}
    good = {"candidates": [{"content": {"parts": [{"text": '{"surfaces": []}'}]}, "finishReason": "STOP"}]}
    bodies = {"broken": {"ask": 1}, "good": {"ask": 2}}
    kept = compute.require_cleared, route_ask.google_batch.generate, route_ask.finish_ask.secret_key
    compute.require_cleared = lambda what, store=None: {"node": "test"}
    route_ask.google_batch.generate = lambda model, asked, key, caller: {"broken": broken, "good": good}
    route_ask.finish_ask.secret_key = lambda: "key"
    try:
        for body, response in zip(bodies.values(), (broken, good)):
            route_ask.google_spend.keep(route_ask.google_spend.cache_path(route_ask.finish_ask.LIST_MODEL, body),
                                        response)
        found = route_ask.asked(bodies, "test")
    finally:
        compute.require_cleared, route_ask.google_batch.generate, route_ask.finish_ask.secret_key = kept
    assert isinstance(found["broken"], route_ask.google_batch.Unanswered) and found["good"] == '{"surfaces": []}'
    assert not route_ask.google_spend.cache_path(route_ask.finish_ask.LIST_MODEL, bodies["broken"]).exists()
    assert route_ask.google_spend.cache_path(route_ask.finish_ask.LIST_MODEL, bodies["good"]).exists()


def test_the_object_filter_keys_only_a_selecting_row():
    from score.stages import world1
    with tempfile.TemporaryDirectory() as temporary:
        runner = graph.Runner(surfaces.ROWS, world1(), Store.in_folder(temporary))
        views = runner.stages["finish-route-views"]
        assert runner.params_of(views) == {}
        runner.objects = frozenset({"b", "a"})
        assert runner.params_of(views) == {"objects": ["a", "b"]}
        assert runner.params_of(runner.stages["surfaces-paint"]) == {}
        assert not any(name.startswith("model ") for name in runner.files_of(views, "old_station"))


def test_the_route_is_the_default_line():
    assert [row.name for row in surfaces.ROWS] == [
        "finish-route-palette", "surface-library", "finish-route-views", "finish-route-list", "finish-route-split",
        "surfaces-parts", "surfaces-bake", "surfaces-paint", "finish-route-recheck", "surfaces-check"]
    assert [row.name for row in surfaces.ROWS if row.paid] == [
        "finish-route-palette", "surface-library", "finish-route-list", "surfaces-bake", "finish-route-recheck"]
    # no row of the route reads data/definitions/place.json: a scene's palette comes from its design
    for row in surfaces.ROWS:
        assert "places" not in (row.files("cockpit") if callable(row.files) else row.files), row.name
    for name in ("finish-route-list", "surfaces-parts", "surfaces-bake", "finish-route-recheck", "surfaces-check"):
        assert "finish-route-palette" in next(row for row in surfaces.ROWS if row.name == name).after, name
    with tempfile.TemporaryDirectory() as temporary:
        runner = graph.Runner(stages.STAGES, stages.world1(), Store.in_folder(temporary))
        line = [graph.node_name(*node) for node in runner.line_nodes(["cockpit"], False)]
        assert all(f"{row.name}@cockpit" in line for row in surfaces.ROWS), line
        gone = ("surfaces-inputs", "surfaces-turntable", "surfaces-lists", "surfaces-maps", "surfaces-names",
                "surfaces-segvigen", "finish-route-fill")
        assert not [name for name in line if name.split("@")[0] in gone], line


# --- bake_job ---

def a_turned_take(folder, turn, size=(2.0, 1.0, 0.6)):
    """A labelled take of one part: a box of `size` (x, y, z) turned by `turn` (rows), as its .ply."""
    box = trimesh.creation.box(extents=size)
    box.vertices = box.vertices @ np.asarray(turn, float).T
    folder.mkdir(parents=True)
    box.export(folder / "paint.ply")
    return folder


def rolled(degrees):
    """A turn about z (rows): a take rolled over sideways."""
    angle = math.radians(degrees)
    return [[math.cos(angle), -math.sin(angle), 0.0], [math.sin(angle), math.cos(angle), 0.0], [0.0, 0.0, 1.0]]


def a_pose_world(folder, row):
    """The bake's pose inputs: a hand-in of one row and the repository's stance and resting rules."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "handin.json").write_text(json.dumps({"rows": [row]}))
    tmp_path = folder
    return {"inventory here": tmp_path / "handin.json", "stance rules": REPO / "data/checks/stance.json",
            "resting rules": REPO / "data/checks/resting.json"}


def test_a_rolled_take_is_stood_square_and_a_lying_one_keeps_its_pose(tmp_path):
    """#36 (2026-10-29: 154 of env1's 406 baked models stood tumbled, camp's bunk bed rolled 44 degrees): a 2 x 1 x
    0.6 m take rolled 40 degrees over, its row 2 m wide, 1 m tall and 0.6 m deep, is stood square before it is laid:
    within a degree of its frame, its box back on its row's proportions. A row whose design lays it lying (wreck's
    crashed rocket section) keeps the turn it was made in, saying why; one standing square already is left as it is.
    Break: score/stages/surfaces/route_bake.py: `if kept or not tumble.tumbled(laid):` -> `if True:`
    Break: score/stages/surfaces/tumble.py: `return f"its design lays it lying ({said})"` -> `return None`"""
    import tumble
    identity = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    entry = {"base": identity, "size": [2.0, 1.0, 0.6]}
    labelled = a_turned_take(tmp_path / "rolled", rolled(40))
    stood = route_bake.stood_square({"bed_1": entry}, labelled, "bed_take",
                                    a_pose_world(tmp_path, {"id": "bed", "name": "bunk bed", "thing": "prop:bed_take"}))
    turn = np.array(stood["bed_1"]["base"]).reshape(3, 3)
    laid = route_bake.labelled_points(labelled) @ turn.T
    assert tumble.measure(laid)[0] < 1.0 and np.allclose(np.ptp(laid, axis=0), (2.0, 1.0, 0.6), atol=0.02), laid
    assert stood["bed_1"]["stood"]["degrees"] > 30.0, stood
    lying = route_bake.stood_square({"rear_1": entry}, labelled, "rear_take", a_pose_world(
        tmp_path / "wreck", {"id": "rear", "name": "crashed rocket rear section", "thing": "prop:rear_take"}))
    assert lying["rear_1"]["base"] == identity and lying["rear_1"]["stood"]["kept"].startswith("its design lays it "
                                                                                                  "lying (crashed)")
    square = a_turned_take(tmp_path / "square", rolled(0))
    assert route_bake.stood_square({"bed_1": entry}, square, "bed_take", a_pose_world(
        tmp_path / "again", {"id": "bed", "thing": "prop:bed_take"}))["bed_1"] == entry


def test_the_check_fails_a_tumbled_bake_by_name_with_its_angle_and_leaves_a_lying_one_out(tmp_path):
    """#36: base's module baked 32 degrees off its frame and passed every gate. `stands square` fails a baked model
    more than tumble.DEGREES off its frame (its frame box over tumble.LOOSE times its own) by name with its angle; a
    row whose design keeps its pose is left out, said why.
    Break: score/stages/surfaces/bake_check.py: `and record["square"]["loose"] > tumble.LOOSE]` -> `and False]`"""
    (tmp_path / "checks.json").write_text(json.dumps({
        "module_1": {"square": {"degrees": 32.06, "loose": 1.742}},
        "bed_1": {"square": {"degrees": 0.4, "loose": 1.002}},
        "rear_1": {"square": {"degrees": 43.4, "loose": 1.215}, "keeps_pose": "its design lays it lying (crashed)"}}))
    found = bake_check.judge_square(tmp_path, {}, None)
    assert found.answer == checks.FAIL and found.measures["failing"] == 1, found
    assert found.findings == ("module_1: stands 32.1 degrees off its frame (its frame box 1.74 times its own)",
                              "rear_1: left out, its design lays it lying (crashed)"), found.findings


def test_one_guard_list_keeps_people_hanging_rows_cable_and_debris_in_their_pose_by_kind_anchor_and_words(tmp_path):
    """#36 (2026-10-29): the bake turned garage's ceiling lamp (`on:ceiling_beam`) 50 degrees and hangar's limp floor
    cables 31, and widened cockpit's seated pilot to his box with its chair. One guard list, read by row kind, anchor
    and words, never by a name: a person (the people route), a hanging row (the resting rules' hanging words, or its
    anchor the ceiling, by word or by its holder's ceiling group), a cable and ground debris (no up), a lying one; a
    stool on the floor is not kept. The bake keeps the lamp's pose and its check leaves the same rows out.
    Break: tumble.py `hangs`: `return f"anchored {anchor}"` -> `return None`
    Break: tumble.py: `NO_UP = ("ground debris", "cable")` -> `NO_UP = ("ground debris",)`
    Break: tumble.py `person`: `return row.get("route") == PEOPLE` -> `return False`
    Break: bake_check.py `keeps_pose_of`: `or (entry.get("stood") or {}).get("kept")` dropped"""
    import tumble
    rules = tumble.rules_of({"stance rules": REPO / "data/checks/stance.json",
                             "resting rules": REPO / "data/checks/resting.json"})
    rows = [{"id": "ceiling_panels", "group": "kit: ceiling"}]
    assert tumble.keeps_pose({"id": "pilot", "route": "people", "anchor": "on:pilot_seat"}, rules) == tumble.PERSON
    assert tumble.keeps_pose({"id": "ceiling_lamp", "name": "ceiling lamp", "anchor": "on:ceiling_beam"},
                             rules).startswith("it hangs (anchored on:ceiling_beam)")
    assert tumble.keeps_pose({"id": "light_1", "name": "light", "anchor": "on:ceiling_panels"}, rules, rows)
    assert tumble.keeps_pose({"id": "glove", "name": "hanging glove", "anchor": "on:cabinet"}, rules)
    assert tumble.keeps_pose({"id": "floor_cables", "name": "thick red cables", "anchor": "floor"},
                             rules) == "no up (cables): it rests as it was made"
    assert tumble.keeps_pose({"id": "rocks", "name": "rubble pile"}, rules)
    assert tumble.keeps_pose({"id": "rear", "name": "crashed rocket rear section"}, rules)
    assert tumble.keeps_pose({"id": "stool", "name": "stool", "anchor": "floor", "route": "prop"}, rules) is None
    identity = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    labelled = a_turned_take(tmp_path / "lamp", rolled(40))
    lamp = {"id": "ceiling_lamp", "name": "ceiling lamp", "anchor": "on:ceiling_beam", "thing": "prop:lamp_take"}
    inputs = a_pose_world(tmp_path / "garage", lamp)
    stood = route_bake.stood_square({"ceiling_lamp_1": {"base": identity, "size": [2.0, 1.0, 0.6]}}, labelled,
                                    "lamp_take", inputs)["ceiling_lamp_1"]
    assert stood["base"] == identity and stood["stood"]["kept"].startswith("it hangs"), stood
    entry = {"parts": "lamp_take", "stood": stood["stood"]}
    assert bake_check.keeps_pose_of("ceiling_lamp_1", entry, [lamp], inputs).startswith("it hangs")
    undone = {"parts": "valves_take", "stood": {"kept": "its turn left it 12.35 degrees off its frame as baked: kept "
                                                        "as made"}}
    assert bake_check.keeps_pose_of("pipe_valves_1", undone, [], inputs).startswith("its turn left it 12.35")


def test_a_take_is_measured_again_as_baked_and_turned_until_square_and_a_turn_that_cannot_square_it_is_undone():
    """#36 (2026-10-29): habitat's stove stood 7.1 degrees on its labelled take and was not turned, then 12.6 degrees
    baked (fitted to its size, remeshed, its feet levelled) and failed `stands square`; hangar's pipe valves were
    turned from 32.8 to 12.4 degrees on their unsteady box and kept that turn. The bake measures each copy as it bakes
    with the check's own measure: a stove copy 12.6 degrees off, never turned, is turned again (its copy then square)
    and baked again; a square one is done; one the bake turned that is still more than tumble.DEGREES off after the
    last measuring takes back the turn it was made in, saying why.
    Break: route_bake.py `squared_again`: `elif turned:` -> `elif False:`
    Break: route_bake.py `squared_again`: `square = not (...) and (not turned or degrees <= tumble.DEGREES)` -> `square
        = not (degrees > tumble.DEGREES and loose > tumble.LOOSE)`
    Break: route_bake.py `squared_again`: `elif measured < route_bake.SQUARE_ROUNDS:` -> `elif False:`"""
    import tumble
    identity = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    box = trimesh.creation.box(extents=(0.8, 0.9, 0.6)).vertices
    tilted = box @ np.array(rolled(12.6)).T
    entries = {"stove_1": {"base": identity, "size": [0.8, 0.9, 0.6]},
               "oven_1": {"base": identity, "size": [0.8, 0.9, 0.6]}}
    found, again = route_bake.squared_again(entries, {"stove_1": tilted, "oven_1": box}, 1)
    assert again == ["stove_1"] and found["oven_1"]["base"] == identity, (found, again)
    turn = np.array(found["stove_1"]["base"]).reshape(3, 3)
    assert tumble.measure(tilted @ turn.T)[0] < 1.0 and found["stove_1"]["stood"]["made"] == identity
    assert found["stove_1"]["stood"]["baked"] == [list(tumble.measure(tilted))]
    done, again = route_bake.squared_again(found, {"stove_1": tilted @ turn.T}, 2)
    assert again == [] and done["stove_1"]["base"] == found["stove_1"]["base"] and "kept" not in done["stove_1"]["stood"]
    turned = {"pipe_valves_1": {"base": [round(value, 6) for value in np.array(rolled(20)).reshape(-1)],
                                "size": [0.8, 0.9, 0.6], "stood": {"made": identity}}}
    # an unsteady box, as the valves': a round blob's oriented box stands over 10 degrees off, its frame box as tight
    still = trimesh.creation.icosphere(subdivisions=3).vertices * np.array([0.5, 0.42, 0.3]) @ np.array(rolled(12.35)).T
    degrees, loose = tumble.measure(still)
    assert degrees > tumble.DEGREES and loose < tumble.LOOSE, (degrees, loose)
    unsquared, again = route_bake.squared_again(turned, {"pipe_valves_1": still}, route_bake.SQUARE_ROUNDS)
    assert again == [] and unsquared["pipe_valves_1"]["base"] == identity, unsquared
    assert unsquared["pipe_valves_1"]["stood"]["kept"] == (f"its turn left it {degrees} degrees off its frame as "
                                                           "baked: kept as made"), unsquared
    loose_only = box @ np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]).T
    assert route_bake.squared_again(turned, {"pipe_valves_1": loose_only}, route_bake.SQUARE_ROUNDS)[0][
        "pipe_valves_1"]["base"] == turned["pipe_valves_1"]["base"]  # square as baked: its turn stays


def test_a_swinging_door_at_full_open_touches_nothing_in_its_recess():
    """#72: a 6 m wide, 0.5 m thick door hinged on its left (the model's -x) swings a quarter turn into its 12 m
    module through its S face (z 6). At 90 degrees it lies along the hinge side, from x -3.5 to -3 and z 0 to 6: its
    recess, widened on that side by its thickness plus 5 cm (x -3.55 to 3), and its swing's 6.05 m deep, holds it with
    5 cm clear of the side wall and of the back.
    Break: score/stages/surfaces/route_bake.py: `opening = min(span, float(recess["wide"]) + room * (1.0 if room_side
        else 2.0))` -> `opening = min(span, float(recess["wide"]))`"""
    swing = {"model": "module_1", "axis": "z", "side": 1.0, "along": 0.0, "wide": 6.0, "room": 0.55,
             "room_side": -1.0, "tall": 8.0, "base": 0.0, "depth": 6.05}
    low, high = (np.array(corner) for corner in route_bake.recess_box([12.0, 12.0, 12.0], swing))
    door_low, door_high = np.array([-3.5, 0.0, 0.0]), np.array([-3.0, 8.0, 6.0])  # at 90 degrees
    clear = np.concatenate([door_low - low, high - door_high])[[0, 2, 3, 5]]  # its sides and its back
    assert (clear[[0, 1]] >= 0.05 - 1e-9).all() and (clear[[2, 3]] >= 0.0).all(), (low, high)


def test_a_door_at_its_face_s_end_clears_the_kept_side_wall_at_full_open_as_it_clears_the_back():
    """#36 (2026-10-29): base's garage door stands at its 12 m module's W end; kept a side wall (RECESS_BACK) inside
    the face, its recess took the 5 cm the door's room had for clearance, and at full open the door lay flush against
    the wall. Its room is its 0.5 m thickness, the clearance and the wall (score/review/holders RECESS_MARGIN,
    RECESS_WALL); the assembly keeps door and room within the face (its hinge edge at -6 + 0.6), so at full open the
    door (x -5.9 to -5.4) clears the wall (the recess from -5.95) by 5 cm, as its 6.05 m deep swing clears the back.
    Break: score/review/holders/__init__.py: `RECESS_WALL = 0.05` -> `RECESS_WALL = 0.0`
    Break: score/stages/surfaces/route_bake.py: `inside = span - 2 * RECESS_BACK` -> `inside = span`"""
    from score.review import holders
    from score.stages.assembly import fitting
    room = 0.5 + holders.RECESS_MARGIN + holders.RECESS_WALL  # as holders.recess_of gives a swing (its own test)
    swing = {"model": "module_1", "axis": "z", "side": 1.0, "along": -7.695, "wide": 6.0, "room": room,
             "room_side": -1.0, "room_way": [-1.0, 0.0], "tall": 8.0, "base": 0.0, "depth": 6.05}
    low, high = route_bake.recess_box([12.0, 12.0, 12.0], swing)
    below, _ = fitting.beside(swing, 0)
    hinge = -6.0 + below  # where the assembly lays the door's hinge edge (fitting.on_holder)
    assert below == pytest.approx(room) and low[0] >= -6.0 + route_bake.RECESS_BACK - 1e-9, (below, low)
    assert hinge - 0.5 - low[0] == pytest.approx(holders.RECESS_MARGIN), (hinge, low)  # clear of the side wall
    assert high[0] - (hinge + 6.0) >= holders.RECESS_MARGIN - 1e-9, (hinge, high)  # and of the latch side


def test_a_moving_door_s_holder_bakes_with_a_recess_behind_it_and_the_recess_has_a_back():
    """#72 (base's garage door swings on its 12 m module's S face): the relation's recess is cut into the holder's
    entry when the job is written. The 6 m door, its middle 7.695 m left of the module's, is kept within the face's
    span less a side wall (RECESS_BACK) at its end (x -5.95 to 0.05: flush with the span's end, base's recess cut its
    module's W side wall away, 2026-10-29), 8 m tall, its swing's 6.05 m deep from 5 cm out of the face (z 6.05 to
    -0.05): a recess with a back, never through the module (z -6). A sliding door's recess is its thickness deep, with
    its width of room along the face; a static door's holder (no recess) bakes as it was.
    Break: score/stages/surfaces/route_bake.py: `depth = min(float(recess["depth"]), 2 * half - RECESS_BACK)` -> `depth
        = 2 * half + RECESS_OUT`
    Break: score/stages/surfaces/route_bake.py: `low[across], high[across] = middle - opening / 2, middle + opening / 2`
        -> `low[across], high[across] = float(recess["along"]) - opening / 2, float(recess["along"]) + opening / 2`
    Break: score/stages/surfaces/route_bake.py: `inside = span - 2 * RECESS_BACK` -> `inside = span` (2026-10-29)"""
    entries = {"module_1": {"size": [12.0, 12.0, 12.0], "cuts": []}, "shed_1": {"size": [4.0, 3.0, 4.0], "cuts": []}}
    swing = {"model": "module_1", "axis": "z", "side": 1.0, "along": -7.695, "wide": 6.0, "room": 0.0, "tall": 8.0,
             "base": 0.0, "depth": 6.05}
    found = route_bake.recessed(entries, {"relations": [{"item": "GARAGE DOOR 1", "row": "garage_door", "recess": swing},
                                                      {"item": "SHUTTER 1", "row": "shutter"}]})
    [cut] = found["module_1"]["cuts"]
    assert cut == {"recess": [[-5.95, 0.0, -0.05], [0.05, 8.0, 6.05]]}, cut
    assert cut["recess"][0][2] > -6.0 + route_bake.RECESS_BACK - 1e-9  # its back: the module stands behind it
    assert cut["recess"][0][0] >= -6.0 + route_bake.RECESS_BACK - 1e-9  # its side: the W wall stands beside it
    assert found["shed_1"]["cuts"] == [] and entries["module_1"]["cuts"] == []
    slide = {**swing, "model": "shed_1", "axis": "x", "side": -1.0, "along": 0.0, "wide": 1.0, "room": 1.0,
             "tall": 2.0, "depth": 0.15}
    [cut] = route_bake.recessed(entries, {"relations": [{"recess": slide}]})["shed_1"]["cuts"]
    assert cut == {"recess": [[-2.05, 0.0, -0.5], [-1.85, 2.0, 1.5]]}, cut


# The people line's bake takes its specs and wear from the repository's library by place; every old material was
# retired (2026-10-21), so these entry checks give it a stand-in library's (no surface: the entries are the subject).
WEAR = (0.4, 0.3)


@pytest.fixture
def stand_in_library(monkeypatch):
    monkeypatch.setattr(bake_job, "specs_of", lambda library_name: {})
    monkeypatch.setattr(library, "wear_of", lambda place_id, *_: WEAR)


def a_folder():
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(prefix="bake-job-", dir=PROPS_HOME / "store-tests"))


def written(folder, name, record):
    path = folder / f"{name}.json"
    path.write_text(json.dumps(record))
    return path


def a_box_take(folder, take, extents):
    """A labelled take of one part: a box of `extents` (x, y, z) written as a .ply, as labels.py writes parts."""
    labelled = folder / "labelled" / take
    labelled.mkdir(parents=True)
    trimesh.creation.box(extents=extents).export(labelled / "hull_white.ply")
    return labelled


def test_an_entry_the_data_writes_out_is_taken_as_written_and_a_model_with_none_stops_the_bake(stand_in_library):
    folder = a_folder()
    try:
        written_out = {"base": [1, 0, 0, 0, 1, 0, 0, 0, 1], "size": [0.5, 0.9, 1.1], "faces": 19000, "foot": 0.0}
        surfaces = written(folder, "surfaces", {"place": "hangar", "library": "hangar", "bake": {
            "models": {"pedestal_1": "pedestal-t1", "lost_1": "lost-t1"}, "entries": {"pedestal_1": written_out}}})
        inputs = {"surfaces": surfaces}
        job, (entry,) = place_line.bake_entries(inputs, {"pedestal-t1": folder / "pedestal-t1"})
        assert {key: entry[key] for key in written_out} == written_out and entry["regions"] == []
        assert (job["wear"], job["dirt"]) == WEAR and job["density"] == route.NEAR
        assert job["faces"] == route.CHUNKY_FACES
        try:
            place_line.bake_entries(inputs, {"pedestal-t1": folder / "p", "lost-t1": folder / "l"})
            raise AssertionError("a model with no entry was baked")
        except bake_job.NoEntry as refused:
            assert "no entry for lost_1" in str(refused), refused
    finally:
        shutil.rmtree(folder)


def test_a_design_entry_written_without_a_turn_is_turned_by_its_take_s_measured_footprint(stand_in_library):
    """A design's take has no hand-set turn: of 0 and 90 degrees, the one whose labelled model's footprint fits its
    row's wide and deep. A take built long along z for a row wide along x is turned a quarter round; one already wide
    along x is not; with no take yet the bake is not refused (it measures once the take is there)."""
    folder = a_folder()
    try:
        labelled = a_box_take(folder, "bench-t1", (0.5, 0.9, 2.0))
        design = {"size": [2.0, 0.9, 0.5], "faces": 19000, "foot": 0.0}
        surfaces = written(folder, "surfaces", {"place": "hub", "library": "hub", "bake": {
            "models": {"bench_1": "bench-t1"}, "entries": {"bench_1": design}}})
        _, (entry,) = place_line.bake_entries({"surfaces": surfaces}, {"bench-t1": labelled})
        assert entry["base"] == bake_job.TURNS[90] and place_route.yaw_of(entry["base"]) == 90.0, entry
        assert bake_job.measured_turn(labelled, [0.5, 0.9, 2.0]) == bake_job.TURNS[0]
        assert bake_job.refusal("bench_1", design) is None
        assert "the data writes none" in bake_job.refusal("lost_1", None)
    finally:
        shutil.rmtree(folder)


def test_a_slender_design_entry_keeps_its_take_s_own_proportions_its_longest_side_the_row_s(stand_in_library):
    """A thin run's row is its thickness on two sides (a sagging string 8 by 0.01 by 0.01) while its take hangs 1 m:
    the bake lays it as one scale, its longest side the row's, never fitted side by side to the box."""
    folder = a_folder()
    try:
        labelled = a_box_take(folder, "string-t1", (0.05, 1.0, 8.0))
        design = {"size": [8.0, 0.01, 0.01], "faces": 19000, "foot": 0.0}
        surfaces = written(folder, "surfaces", {"place": "street", "library": "street", "bake": {
            "models": {"string_1": "string-t1"}, "entries": {"string_1": design}}})
        _, (entry,) = place_line.bake_entries({"surfaces": surfaces}, {"string-t1": labelled})
        assert entry["base"] == bake_job.TURNS[90] and entry["size"] == [8.0, 1.0, 0.05], entry
    finally:
        shutil.rmtree(folder)


def test_a_code_build_bakes_at_its_own_section_its_longest_side_the_row_s(stand_in_library, monkeypatch):
    """A code build (its take's code.json route "code") whose section is its picture's, not its box's: airlock's locker
    lamp built 0.046 m across for a 0.4 by 0.1 by 0.1 row (no slender row: its middle side a quarter of its longest).
    The bake lays it as one scale, its longest side the row's, never fitted side by side to the box (outline 0.813
    built, 0.409 baked so, 2026-10-29); a Pixal3D take of the same row is still fitted to its box."""
    folder = a_folder()
    try:
        monkeypatch.setattr(place_line.prop_env, "PROPS_HOME", folder)
        labelled = a_box_take(folder, "lamp-t1", (0.4, 0.046, 0.046))
        design = {"size": [0.4, 0.1, 0.1], "faces": 5000, "foot": 0.0}
        surfaces = written(folder, "surfaces", {"place": "airlock", "library": "airlock", "bake": {
            "models": {"lamp_1": "lamp-t1"}, "entries": {"lamp_1": design}}})
        _, (entry,) = place_line.bake_entries({"surfaces": surfaces}, {"lamp-t1": labelled})
        assert entry["size"] == [0.4, 0.1, 0.1], entry  # a Pixal3D take: its row's box
        mark = bake_job.code_mark("lamp-t1", folder)
        mark.parent.mkdir(parents=True)
        mark.write_text(json.dumps({"route": "code", "rule": "thin straight (owner, 2026-10-25)"}))
        _, (entry,) = place_line.bake_entries({"surfaces": surfaces}, {"lamp-t1": labelled})
        assert entry["base"] == bake_job.TURNS[0] and entry["size"] == [0.4, 0.046, 0.046], entry
    finally:
        shutil.rmtree(folder)


def test_a_pixal3d_take_keeps_its_own_width_for_height_only_where_its_box_and_take_both_disagree_with_its_row(
        stand_in_library):
    """garage's stool: its row 0.4 by 0.4 by 0.5 m (0.8 wide for its height), its SAM 3 box 67 by 122 px (0.55), its
    take 0.57 (a constructed case: the real take is laid on its side by its paint). Box off the row by more than the
    model gate's spread and the take agreeing with the box within it, so the bake lays it at the take's
    own width for its height, its height (the longer) and depth the row's (owner, 2026-10-29, "Yes, land the rule").
    A box alone or a take alone against the row, or a size whose depth is its longest side, keeps the row."""
    folder = a_folder()
    try:
        def entry_for(take_extents, box):
            labelled = folder / "labelled" / "stool-t1"
            if labelled.exists():
                shutil.rmtree(labelled)
            a_box_take(folder, "stool-t1", take_extents)
            handin = written(folder, "handin", {"rows": [{"id": "stool", "size": [0.4, 0.4, 0.5], "box": box}],
                                                "objects": {"stool": {"route": "prop", "take": "stool-t1"}}})
            surfaces = written(folder, "surfaces", {"place": "garage", "library": "garage", "bake": {
                "models": {"stool_1": "stool-t1"}, "entries": {"stool_1": {"size": [0.4, 0.5, 0.4], "faces": 5000,
                                                                           "foot": 0.0}}}})
            _, (entry,) = place_line.bake_entries({"surfaces": surfaces, "inventory garage": handin},
                                                  {"stool-t1": labelled})
            return entry["size"]
        assert entry_for((0.498, 0.868, 0.502), [927, 603, 994, 725]) == [0.287, 0.5, 0.4]  # both: the take's
        assert entry_for((0.4, 0.5, 0.4), [927, 603, 994, 725]) == [0.4, 0.5, 0.4]  # the box alone
        assert entry_for((0.498, 0.868, 0.502), [0, 0, 80, 100]) == [0.4, 0.5, 0.4]  # the take alone
        assert bake_job.boxed([0.4, 0.5, 0.4], [0, 0, 70, 100], 0.6) == [0.4, 0.5, 0.4]  # the box within the row's
        assert bake_job.boxed([0.4, 0.5, 0.4], [0, 0, 55, 100], 0.7) == [0.4, 0.5, 0.4]  # the take within the row's
        assert bake_job.boxed([1.0, 1.0, 4.0], [0, 0, 100, 10], 3.0) == [1.0, 1.0, 4.0]  # its depth its longest side
        assert bake_job.boxed([4.0, 1.0, 1.0], [0, 0, 100, 50], 2.0) == [4.0, 1.0, 1.0]  # wider than tall: as it is
    finally:
        shutil.rmtree(folder)


def test_the_width_rule_leaves_a_kept_row_as_its_row_says_and_a_person_keeps_its_own_width_for_its_height(
        stand_in_library):
    """#36 (2026-10-29): cockpit's seated pilot (his row 0.5 by 0.3 by 1.8 m) was widened to his SAM 3 box, which
    holds his chair, 1.205 m; his A-pose officer squeezed into 0.5 m, his arms out. The width rule reads the guard list
    (tumble.keeps_pose): a person keeps his take's own width for his row's height whatever his box (a take 0.6 wide
    for its height: 1.08 m at 1.8 m), never squeezed to the row nor stretched to the box; a hanging lamp whose box and
    take both disagree with its row keeps its row's size, as a stool on the floor would not.
    Break: bake_job.py `boxed`: `if person and own:` -> `if False:`
    Break: bake_job.py `boxed`: `if kept or not box` -> `if not box`"""
    folder = a_folder()
    try:
        rules = a_pose_world(folder / "rules", {})

        def entry_for(row, take_extents):
            take = f"{row['id']}-t1"
            a_box_take(folder / row["id"], take, take_extents)
            handin = written(folder, f"handin-{row['id']}", {"rows": [row], "objects": {row["id"]: {"route": "prop",
                                                                                                 "take": take}}})
            surfaces = written(folder, f"surfaces-{row['id']}", {"place": "cockpit", "library": "cockpit", "bake": {
                "models": {f"{row['id']}_1": take}, "entries": {f"{row['id']}_1": {"size": row["kit"], "faces": 5000,
                                                                                     "foot": 0.0}}}})
            inputs = {"surfaces": surfaces, "inventory cockpit": handin, "stance rules": rules["stance rules"],
                      "resting rules": rules["resting rules"]}
            _, (entry,) = place_line.bake_entries(inputs, {take: folder / row["id"] / "labelled" / take})
            return entry["size"]
        pilot = {"id": "pilot", "route": "people", "anchor": "on:pilot_seat", "box": [812, 687, 946, 906],
                 "kit": [0.5, 1.8, 0.3]}
        assert entry_for(pilot, (0.6, 1.0, 0.3)) == [1.08, 1.8, 0.3]  # his take's own width for his height
        assert entry_for(dict(pilot, id="officer", box=[0, 0, 10, 100]), (0.58, 1.0, 0.3)) == [1.044, 1.8, 0.3]
        lamp = {"id": "ceiling_lamp", "name": "ceiling lamp", "anchor": "on:ceiling_beam", "route": "prop",
                "box": [927, 603, 994, 725], "kit": [0.4, 0.5, 0.4]}
        assert entry_for(lamp, (0.498, 0.868, 0.502)) == [0.4, 0.5, 0.4]  # kept: as its row says
        stool = dict(lamp, id="stool", name="stool", anchor="floor")
        assert entry_for(stool, (0.498, 0.868, 0.502)) == [0.287, 0.5, 0.4]  # not kept: the width rule's
    finally:
        shutil.rmtree(folder)


def test_every_place_s_bake_is_written_from_git_or_blocks_on_a_named_entry(stand_in_library):
    """Every place's bake declares no file under the work folder; a model no entry can be written for is declared
    as a file that is never there, naming it (the old kinds' details retired on 2026-10-21, so an old place's laid
    kit models are each named so)."""
    for path in sorted(surface_data.FOLDER.glob("*.json")):
        declared = surface_data.bake_files(path.stem)
        # the work folder ({seeds}, {home}/work); a designed place's surface data, {home}/design, prepare writes again
        assert not any("{home}/work" in pattern or "{seeds}" in pattern for pattern in declared.values()), path.stem
        assert "library bake" in declared, path.stem
        # the old kinds' details and composites retired (2026-10-21): no bake waits on them by name
        assert not {"details", "composites"} & set(declared), path.stem


# --- body_faces ---

METHOD = pathlib.Path(__file__).resolve().parents[3] / "data/library/materials.json"


ANSWER = {"palette": [{"token": "regolith-grey", "colour": "#8a8580"}, {"token": "crater-dark", "colour": "#3b3a38"}],
          "face": {"family": "Regolith", "recipe": "regolith", "token": "regolith-grey", "roughness": 0.95,
                   "metal": 0.0, "colours": [{"setting": "second", "token": "crater-dark"}]}}


GROUND = ["regolith", "Moon: airless, its dust ground by impacts"]


def test_every_body_that_does_not_shine_has_a_paid_row_of_its_own(monkeypatch):
    monkeypatch.setattr(body_faces.environment_concept, "in_force", lambda store: None)
    rows = body_faces.rows(None)
    assert [row.name for row in rows] == ["body-face-earth", "body-face-moon", "body-face-mars"]  # not the Sun
    assert all(row.paid and row.grain == "world" and row.euros == body_faces.FACE_EUROS for row in rows)
    moon = body_faces.body_param("moon")(type("Runner", (), {"store": None}))
    assert moon["radius_km"] == settings.reference()["bodies"]["moon"]["radius_km"]  # the cited table's value
    assert "radius 1,737 km" in body_faces.facts_of(moon)
    runner = type("Runner", (), {"store": None})
    grounds = {key: body_faces.ground_param(key)(runner)[0] for key in ("earth", "moon", "mars")}
    assert grounds == {"earth": "ocean", "moon": "regolith", "mars": "sand"}  # by their physics, no name read


def test_the_face_is_made_from_one_ask_in_the_methods_recipes(tmp_path, monkeypatch):
    asked = []
    monkeypatch.setattr(body_faces.route_ask, "asked", lambda bodies, caller: asked.append((bodies, caller)) or
                        {key: json.dumps(ANSWER) for key in bodies})
    moon = {"body": "moon", "name": "Moon", "radius_km": 1737.4}
    body_faces.make_face({"library": str(METHOD)}, tmp_path, 0, {"body": moon, "style": "worn NASA-punk",
                                                                 "ground": GROUND})
    (bodies, caller), = asked
    assert caller == "body-face" and "worn NASA-punk" in json.dumps(bodies["moon"])
    schema = bodies["moon"]["generationConfig"]["responseSchema"]["properties"]["face"]["properties"]
    assert schema["recipe"]["enum"] == ["regolith"] and "airless" in json.dumps(bodies["moon"])
    face = json.loads((tmp_path / "face.json").read_text())
    assert face["surface"] == "moon_face" and face["family"] == "regolith" and face["hex"] == "#8a8580"
    assert abs(face["colour"][0] - 0.2541) < 1e-3  # #8a = 138: sRGB to linear
    library = json.loads((tmp_path / "materials.json").read_text())
    assert library["families"]["regolith"]["variants"]["moon_face"]["second"] == "crater-dark"
    assert face["recipe"] == "regolith" and face["recipe_by"] == GROUND[1]
    assert body_faces.face_findings("moon", library) == []
    assert body_faces.judge_face(tmp_path, {}, {}).answer == "pass"


def test_a_face_off_its_palette_or_the_method_fails_and_no_answer_is_named(tmp_path, monkeypatch):
    method = json.loads(METHOD.read_text())
    library = body_faces.library_of("mars", json.dumps(ANSWER), method)
    variant = library["families"]["regolith"]["variants"]["mars_face"]
    variant.update(token="rust", recipe="moon_dust", roughness=1.5)
    found = body_faces.face_findings("mars", library)
    assert any("recipe moon_dust" in fault for fault in found) and any("token rust" in fault for fault in found)
    assert any("moon_dust is no natural ground" in fault for fault in found)
    assert any("roughness 1.5" in fault for fault in found)
    monkeypatch.setattr(body_faces.route_ask, "asked",
                        lambda bodies, caller: {key: ValueError("no json") for key in bodies})
    body_faces.make_face({"library": str(METHOD)}, tmp_path, 0, {"body": {"body": "mars", "name": "Mars"}, "style": "",
                                                                 "ground": GROUND})
    assert not (tmp_path / "face.json").exists() and body_faces.judge_face(tmp_path, {}, {}).answer == "fail"


def test_a_body_whose_physics_the_setting_lacks_gets_no_face(tmp_path):
    with pytest.raises(ValueError, match="no natural ground for its face: Vesta: no surface pressure"):
        body_faces.make_face({"library": str(METHOD)}, tmp_path, 0, {
            "body": {"body": "vesta", "name": "Vesta"}, "style": "",
            "ground": [None, "Vesta: no surface pressure in the setting"]})


def test_the_four_asks_go_to_claude_and_the_faces_stay(monkeypatch):
    """The stage table's palette, library, list and recheck rows make through claude_asks, their module's ask sending
    to the claude-code adapter only for the make's own call; body-face still asks route_ask (Gemini)."""
    rows = {row.name: row for row in stages.STAGES}
    switched = {"finish-route-palette": scene_palette, "surface-library": scene_library,
                "finish-route-list": route_list, "finish-route-recheck": route_recheck}
    sent = []
    monkeypatch.setattr(claude_asks.claude_code, "asked", lambda bodies, caller: sent.append(caller) or {})
    for name, module in switched.items():
        own = rows[name].make.__wrapped__
        assert own.__module__ == module.__name__, name
        gemini = module.ask
        def asks_once(inputs, out, seed, params, module=module):  # the make, its one batch of asks alone
            return module.ask({"k": {}})
        asks_once.__module__ = module.__name__
        claude_asks.asking_claude(asks_once)({}, None, 0, {})
        assert module.ask is gemini, name
    assert sent == [scene_palette.CALLER, scene_library.CALLER, route_list.CALLER, route_recheck.CALLER]
    assert not hasattr(rows["body-face-earth"].make, "__wrapped__")
    assert "claude_code" not in inspect.getsource(body_faces) and "route_ask.asked" in inspect.getsource(body_faces)



def test_a_palette_answer_off_its_own_palette_is_asked_once_more_told_why(monkeypatch):
    """A palette answer whose dirt token is not its own (env1's shiplock, 2026-10-27) is asked once more with the
    answer and why after the question, and that answer kept; a good answer, and the other rows, ask once."""
    levels = ["new", "worked", "worn"]
    off = {"palette": coined(("steel", "#9ba2a9"), ("hazard", "#f2c21a"), ("glass", "#24313a"), ("lamp", "#ffffff")),
           "wear": "worn", "cause": "scuffed", "dirt": 0.4, "dirt_token": "soot-grime"}
    fixed = {**off, "palette": [*off["palette"], *coined(("soot-grime", "#3a3633"))]}
    sent, first = [], [off]

    def asked(bodies, caller):
        sent.append(bodies)
        told = any("cannot be used" in part.get("text", "") for body in bodies.values()
                   for part in body["contents"][0]["parts"])
        return {take: json.dumps(fixed if told else first[0]) for take in bodies}
    monkeypatch.setattr(claude_asks.claude_code, "asked", asked)
    bodies = {"cockpit": scene_palette.palette_body([], levels)}
    answers = claude_asks.answered(bodies, scene_palette)
    assert len(sent) == 2 and scene_palette.palette_of(answers["cockpit"], levels)["wear"]["dirt_token"] == "soot-grime"
    again = sent[1]["cockpit"]["contents"][0]["parts"][-1]["text"]
    assert "soot-grime" in again and "cannot be used" in again and "worn" in again, again
    assert bodies["cockpit"]["contents"][0]["parts"][-1]["text"] != again  # the first body kept as it was asked
    sent.clear()
    first[0] = fixed
    assert claude_asks.answered(bodies, scene_palette) and len(sent) == 1, sent  # a good answer: asked once
    sent.clear()
    first[0] = off
    assert claude_asks.answered(bodies, scene_library) and len(sent) == 1, sent  # another row: never asked again



def test_the_paint_reads_the_finish_s_turn_off_the_final_model_whatever_code_stood_it(tmp_path):
    """A take stood by a turn no option of today's glb_file gives (30 degrees round up here; the airlock's four, stood
    before glb_file.squared changed, 48939c57) has that turn read back exactly off its final model's vertices; a final
    that is not its finished file's vertices turned gets none, and the replay decides."""
    import math
    import trimesh
    mesh = trimesh.creation.box([0.6, 0.3, 0.2])
    mesh.vertices[0] += [0.05, 0.02, 0.0]  # not symmetric: one turn only fits it
    angle = math.radians(30)
    turn = np.array([[math.cos(angle), 0.0, math.sin(angle)], [0.0, 1.0, 0.0], [-math.sin(angle), 0.0, math.cos(angle)]])
    mesh.export(tmp_path / "crate_1-5000.glb")
    stood = mesh.copy()
    stood.vertices = mesh.vertices @ turn.T
    stood.export(tmp_path / "crate_1-final.glb")
    with prop_data.tools("props"):
        assert np.allclose(place_line.recovered_turn(tmp_path, "crate_1"), turn, atol=1e-6)
        stood.vertices = stood.vertices + [0.0, 0.0, 0.05]  # moved off its finished file: no exact turn
        stood.export(tmp_path / "crate_1-final.glb")
        assert place_line.recovered_turn(tmp_path, "crate_1") is None
