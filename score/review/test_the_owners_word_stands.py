"""The review's invariant: the owner's word stands and nothing is taken or bought past it. An output that failed or got
worse is never accepted without his written reason, his reject sticks, and his commands run only from his own name or
terminal; every paid call (a concept draw, a Discuss, an environment ask, a plan Correct, a reading, a plan writing)
runs only inside his yes or the standing allowance, at today's measured price, its cost kept; his locks, wordings and
plan edits win over anything written after them, an agent's process writes none of them, and a change above puts what
was drawn under it out of date. What the review works out for him is checked against answers known apart from the
code: the sky over a site (the Moon's phases, the Sun at Greenwich, a house's sun path), a setting's bodies from the
cited table, sites on true distances, and readings and plans against hand-built pictures and boxes.

Every model is a stand-in: no call is made and nothing is spent. Each test's store is a folder of its own.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest -q score/review/test_the_owners_word_stands.py

Each test turns red under the break written for it below (each applied once and seen red, 2026-10-26): the test, then
the file and the exact change. The free fixes' and the sync pass's plans keep tests came in from plan_fixes_test.py
and plans_pass_test.py on 2026-10-27, their breaks applied then. The Square's wording tests read kept plans of their own
(SQUARE_PLANS, 2026-10-28): they had read the real home's, so in a bare PROPS_HOME they failed.
- test_an_output_that_did_not_pass_cannot_be_accepted:
    __init__.py: `if judgement is None or (checks.standing(judgement["verdicts"], waived) != checks.PASS and status
    is None):` made `if judgement is None:`
- test_a_passing_output_is_accepted_by_the_runner_and_a_worse_one_only_by_the_owner_with_a_reason:
    __init__.py: `if worse and not worse_reason:` made `if False:`
- test_the_runner_accepts_within_what_the_owner_allowed_and_no_further:
    __init__.py: `if allowed_judgement is None or regressions(judgement["verdicts"],
    allowed_judgement["verdicts"]):` made `if allowed_judgement is None:`
- test_a_measure_is_worse_only_by_a_step_a_viewer_could_see:
    __init__.py: `return moved > 0 and moved >= tolerance(name, new, old)` made `return moved > 0`
- test_an_answer_that_drops_is_worse_whatever_its_measures_did:
    __init__.py: `if checks.ANSWERS.index(new["answer"]) > checks.ANSWERS.index(old["answer"]):` made `if False:`
- test_an_owners_reject_moves_the_accepted_output_back_and_the_runner_never_takes_it_again:
    __init__.py: `if store.rejected(node, output): return None` made `if False: return None`
- test_the_owners_commands_refuse_without_his_terminal:
    __main__.py: `if not (sys.stdin.isatty() and sys.stdout.isatty()):` made `if False:`
- test_a_waived_gate_lets_its_output_be_accepted_for_that_key_only:
    __init__.py: `waived = store.waivers(node, record["key"]) status` made `waived = {} status`
- test_an_accepted_gaps_objects_leave_the_comparison_and_any_other_object_still_blocks:
    __init__.py: `return [line for line in regressions(judgement["verdicts"], card) if line.split(": ", 1)[0] not in
    excused]` made `return regressions(judgement["verdicts"], card)`
- test_the_page_says_who_accepted_and_offers_no_accept_for_a_failed_output:
    __init__.py: `if current.get("by") == RUNNER else "The owner accepted it"` made `if current.get("by") != RUNNER
    else "The owner accepted it"`
- test_the_signed_in_user_decides_by_his_own_name:
    web.py: `return review.accept(store, node, output, name, reason, worse_reason=worse_reason or None)` made
    `return review.accept(store, node, output, "runner", reason, worse_reason=worse_reason or None)`
- test_a_web_decision_off_his_rules_is_refused:
    web.py: `if not name or name == RUNNER:` made `if not name:`
- test_a_worse_output_needs_his_written_reason_from_the_web_too:
    web.py: `return review.accept(store, node, output, name, reason, worse_reason=worse_reason or None)` made
    `return review.accept(store, node, output, name, reason, worse_reason=worse_reason or "his reason")`
- test_the_signed_in_checkout_writes_the_worlds_stop_line_never_in_an_agents_process:
    web.py: `name = checked_by(by) baseline` made `name = by baseline`
- test_a_draw_runs_only_inside_the_owners_yes:
    concepts.py: `yes = compute.require_cleared("a concept draw", store)` made `yes = {"euros": 0.0, "key":
    "never-cleared"}`
- test_a_first_draw_is_worded_from_the_places_data_and_kept:
    concepts.py: `return f"{wording} The creator's note: {note.strip()}" if note.strip() else wording` made `return
    wording`
- test_a_redraw_sends_the_base_boxed_and_clean_with_each_marks_note:
    concepts.py: `if corrected != own_wording(store, place): worded(` made `if False: worded(`
- test_a_pick_takes_only_a_draw_of_the_place_and_unlocks_again:
    concepts.py: `if sha is not None and sha not in {draw["sha"] for draw in draws(store, place)}:` made `if False:`
- test_a_reading_runs_as_a_process_of_its_own_in_the_picks_store:
    web.py: `env={**os.environ, "SCORE_SPEND_STORE": str(store.cache.parent)}, stdout=out,` made
    `env={**os.environ}, stdout=out,`
- test_every_draw_is_copied_off_this_pc_by_its_sha_and_a_failed_copy_keeps_the_draw_and_says_why:
    concepts.py: `except Exception as failed: # any failure of the copy` made `except ValueError as failed: # any
    failure of the copy`
- test_a_pick_is_handed_to_the_library_by_its_own_concept_command:
    concepts.py: `"--place", place, "--commit"` made `"--place", "", "--commit"`
- test_the_draw_and_redraw_prices_are_the_measured_calls_at_the_standard_tier:
    concepts.py: `share = google_spend.TIER_PRICE["batch"] if "batch" in stage.get("basis", "") else 1.0` made
    `share = 1.0`
- test_the_click_writes_its_yes_at_the_price_shown_then_draws_inside_it:
    web.py: `price = concepts.redraw_euros() if redraw else concepts.draw_euros() if price is None or
    abs(float(euros) - price) > 0.005:` made `price = concepts.redraw_euros() if redraw else concepts.draw_euros()
    if price is None:`
- test_an_agents_process_cannot_pick_or_keep_a_wording_in_the_framework_store:
    concepts.py: `if store.is_framework_store() and running_under_agent():` made `if False:`
- test_a_place_within_another_is_sent_its_picked_picture_first_and_its_wording_as_context:
    concepts.py: `("crop", holder, box))] if box else []` made `("crop", holder, box))] if False else []`
- test_a_reference_comes_from_the_places_data_and_waits_while_it_is_not_here:
    concepts.py: `if not resolved(ref["picture"]).is_file()]` made `if False]`
- test_the_ships_length_and_reference_come_from_the_hangars_data_and_reach_its_rooms:
    concepts.py: `inputs_of(place).get("says", ""), f"Look:` made `"", f"Look:`
- test_no_measure_is_generated_but_the_creators_own_says:
    concepts.py: `words = re.sub(r",? ?(at |about )?\\d+(\\.\\d+)?( ?x ?\\d+(\\.\\d+)?)? ?m\\b", "", words)` made
    `(nothing)`
- test_an_outside_place_is_drawn_from_above_and_an_inside_place_as_a_cutaway:
    concepts.py: `view = INSIDE_VIEW + (ROOF_KEPT if above(place, store) else "") if indoors(store, place) else
    OUTSIDE_VIEW` made `view = OUTSIDE_VIEW`
- test_people_are_drawn_only_where_the_places_data_has_them:
    concepts.py: `return bool(people_rows.persons(place) or people_rows.crowd_row(place) or
    PEOPLE_WORDS.search(look_text(place)))` made `return True`
- test_a_draw_from_an_older_wording_does_not_count_for_draw_all:
    concepts.py: `return any(str(draw.get("wording", "")).startswith(wording)` made `return any(True`
- test_an_edited_wording_is_sent_word_for_word_and_stays_the_places_own_until_back_to_generated:
    concepts.py: `sent = checked_wording(request.get("wording")) or wording_now(store, place)` made `sent =
    wording_now(store, place)`
- test_a_places_wording_names_its_own_doors_and_openings_and_no_others:
    concepts.py: `"no other doors or openings") if leads else ""` made `"") if leads else ""`
- test_a_picked_place_it_opens_into_is_sent_after_the_one_above_and_its_new_pick_puts_the_draw_out_of_date:
    concepts.py: `for other in joined(store, place) if picked(store, other)]` made `for other in [] if picked(store,
    other)]`
- test_a_place_is_sized_against_the_places_beside_it_in_words_only:
    concepts.py: `ratio = round(own[0] / others[-1])` made `ratio = 1`
- test_every_generated_wording_is_short:
    concepts.py: `style(store)) if part)` made `style(store) * 9) if part)`
- test_a_mark_on_the_picture_above_reaches_both_calls_with_that_picture_boxed:
    concepts.py: `(f" of the picked concept of the {mark['on']}" if "on" in mark else "")` made `""`
- test_no_two_ship_rooms_get_the_same_wording_or_references:
    concepts.py: `return f"In the {shell}{side}; for {no_sizes(entry['for'])}."` made `return ""`
- test_a_place_is_drawn_only_once_the_layer_above_is_picked_read_and_planned_and_holds_it:
    concepts.py: `if holder and not plan_made(store, holder):` made `if False:`
- test_a_part_of_a_places_outside_has_no_concept_of_its_own:
    concepts.py: `if place in tree()["parts"]: return f"is part` made `if False: return f"is part`
- test_ship_rooms_share_one_compartment_block_and_are_sent_only_the_crop_of_the_ship:
    concepts.py: `for number, name in enumerate(listed, 1))` made `for number, name in enumerate(listed, 2))`
- test_a_discuss_runs_inside_the_yes_and_keeps_question_answer_and_cost:
    discuss.py: `yes = compute.require_cleared("a concept discussion", store)` made `yes = {"euros": 0.0, "key":
    "never-cleared"}`
- test_a_redraw_after_a_discuss_sends_the_thread_to_the_prompt_rewrite_and_closes_it:
    discuss.py: `if entry["base"] == base and entry["at"] > drawn]` made `if entry["base"] == base]`
- test_the_click_writes_its_yes_at_the_price_shown_then_discusses_inside_it:
    web.py: `price = discuss.price() if price is None or abs(float(euros) - price) > 0.005:` made `price =
    discuss.price() if price is None:`
- test_a_calls_cost_is_read_from_its_token_usage:
    discuss.py: `return round(google_spend.dollars(concepts.PROMPT_MODEL, usage)` made `return round(100 *
    google_spend.dollars(concepts.PROMPT_MODEL, usage)`
- test_environment_1s_concept_is_todays_data_shown_locked:
    environment_concept.py: `if node not in tree["within"] and node not in tree["parts"]` made `if node not in
    tree["within"]`
- test_a_version_kept_before_settings_reads_todays_setting:
    environment_concept.py: `return record if "setting" in concept else {` made `return record if True else {`
- test_a_locked_version_is_what_every_draw_reads:
    concepts.py: `if held is None: return inputs_of(place).get("references", [])` made `if True: return
    inputs_of(place).get("references", [])`
- test_unlocking_puts_every_draw_and_pick_out_of_date_and_stops_new_ones:
    environment_concept.py: `return bool(found) and not found["locked"]` made `return False`
- test_a_concept_out_of_shape_is_refused:
    environment_concept.py: `if len(found) > LONGEST_LINE:` made `if False:`
- test_an_ask_runs_only_inside_the_owners_yes_and_proposes_checked_fields:
    environment_concept.py: `yes = compute.require_cleared("an environment concept ask", store)` made `yes =
    {"euros": 0.0, "key": "never-cleared"}`
- test_the_send_writes_its_yes_at_the_price_shown_then_asks_inside_it:
    web.py: `price = environment_concept.ask_euros() if price is None or abs(float(euros) - price) > 0.005:` made
    `price = environment_concept.ask_euros() if price is None:`
- test_a_new_reference_goes_to_the_bucket_and_its_local_copy_only_while_unlocked:
    environment_concept.py: `if named in index and index[named]["key"] != key:` made `if False:`
- test_an_agents_process_cannot_keep_a_version_or_a_reference:
    environment_concept.py: `if offsite is None and running_under_agent():` made `if False:`
- test_every_real_bodys_value_names_its_source:
    data/physics/bodies.json: `"name": "nasa-sun", "radius_km": "nasa-sun",` made `"name": "nasa-sun",`
- test_environment_one_takes_its_bodies_from_the_table_and_its_gravity_from_their_mass:
    setting.py: `/ (body["radius_km"] * 1000.0) ** 2, 3)` made `/ (body["radius_km"] * 1000.0), 3)`
- test_a_house_on_a_plot_needs_no_bodies_its_sun_is_a_light:
    setting.py: `if shape not in SHAPES:` made `if False:`
- test_a_real_body_set_off_the_table_keeps_his_values_and_an_invented_one_needs_all_of_its_own:
    setting.py: `float(str(value).replace(",", "."))` made `float(str(value))`
- test_a_setting_out_of_shape_is_refused:
    setting.py: `if bodies and sum(1 for body in bodies if not body.get("around")) != 1:` made `if False:`
- test_a_models_values_for_a_real_body_are_dropped_for_the_tables:
    setting.py: `if row.get("reference") else row` made `if False else row`
- test_a_models_answer_never_stacks_two_sites_the_concept_had_apart:
    setting.py: `kept = [earlier[site.get("place")] if count[spot(site)] > 1` made `kept =
    [earlier[site.get("place")] if False`
- test_the_moon_is_full_and_new_when_it_was:
    overhead.py: `lit = (1.0 + float(np.dot(to_light, unit(-toward)))) / 2.0` made `lit = (1.0 -
    float(np.dot(to_light, unit(-toward)))) / 2.0`
- test_the_suns_light_stands_where_it_does_over_greenwich_at_the_equinox_at_its_strength:
    overhead.py: `math.degrees(math.atan2(east, north)) % 360.0` made `math.degrees(math.atan2(north, east)) %
    360.0`
- test_the_suns_disc_is_widest_in_january_and_narrowest_in_july:
    overhead.py: `"across": round(math.degrees(2.0 * math.asin(star["radius_km"] / apart)), 5)` made `"across":
    round(math.degrees(2.0 * math.asin(star["radius_km"] / 1.496e8)), 5)`
- test_earth_hangs_still_about_two_degrees_across_over_a_near_side_moon_site_and_its_phase_turns:
    overhead.py: `if body.get("locked_to"): pole = orbit_pole(body, day)` made `if False: pole = orbit_pole(body,
    day)`
- test_mars_from_earth_and_earth_from_mars_are_points_and_the_sun_is_dimmer_at_mars:
    overhead.py: `lux = star["lux"] * (star["lux_at_km"] / apart) ** 2` made `lux = star["lux"] * (star["lux_at_km"]
    / apart)`
- test_environment_1_overhead_holds_its_bodies_the_suns_light_and_the_stars:
    overhead.py: `if other["body"] == on or other.get("lux") is not None:` made `if other.get("lux") is not None:`
- test_a_houses_sun_is_a_light_on_its_day_path_with_no_bodies:
    overhead.py: `hour = 2.0 * math.pi * since / (light["day_hours"] / 24.0)` made `hour = 0.0`
- test_an_invented_body_turns_by_its_own_day_under_an_invented_star:
    overhead.py: `360.0 * 24.0 / body["day_hours"]` made `360.0 * 24.0 / 24.0`
- test_each_top_scene_stands_where_the_setting_puts_it_shaped_by_its_own_plan:
    environment_plan.py: `return round(max(tops, default=0.0), 2)` made `return 0.0`
- test_a_site_without_a_plan_is_a_gap:
    environment_plan.py: `("plan yet", "size" in site and site["size"] is None))` made `("plan yet", False))`
- test_sites_that_would_overlap_are_moved_clear_along_their_own_bearings:
    environment_plan.py: `sites = cleared(sites, radius, pinned)` made `sites = list(sites)`
- test_a_site_the_creator_placed_himself_stays_and_two_of_his_stay_a_gap:
    environment_plan.py: `if mover["place"] in pinned: still, mover = mover, still` made `if False: still, mover =
    mover, still`
- test_a_new_environment_on_one_plot_places_by_physics_until_plans_land_then_clears:
    environment_plan.py: `"x": round(float(still.get("x") or 0.0) + toward[0] * metres, 2)` made `"x":
    round(float(still.get("x") or 0.0) + toward[0] * metres * 2, 2)`
- test_sites_on_different_grounds_are_never_compared:
    environment_plan.py: `for site in setting["sites"] if site["on"] == key]` made `for site in setting["sites"]]`;
    and `if placed.get(site["place"], {}).get("on") != world["on"]: continue` made `if False: continue`
- test_sites_on_a_plot_are_moved_clear_across_it:
    environment_plan.py: `fixed[axis]) + CLEAR_M)` made `fixed[axis]))`
- test_sites_kilometres_apart_on_the_moon_are_that_far_on_its_map:
    environment_plan.py: `"metres": round(radius * great_angle(one, two) if radius else` made `"metres":
    round(radius * great_angle(one, two) / 2 if radius else`
- test_a_written_plan_keeps_the_fixed_facts_and_works_out_what_each_site_sees_overhead:
    environment_plan.py: `found["terrain"] = {"spots": fixed["terrain"]["spots"] + [spot for spot in spots if
    spot[:2] != [0.0, 0.0]]}` made `found["terrain"] = {"spots": fixed["terrain"]["spots"]}`
- test_a_sites_shape_follows_its_scenes_plan_after_the_writing:
    environment_plan.py: `shape = from_plan(site_plan(store, site["place"])) if store is not None else {}` made
    `shape = {}`
- test_his_edit_is_kept_and_settled_again:
    environment_plan.py: `sites.append({**site, "time": moment(his["time"]), "written_time": None} if
    his.get("time") else site)` made `sites.append(site)`
- test_a_daylight_concept_moves_its_sites_time_to_the_nearest_hour_its_sun_is_up:
    environment_plan.py: `if not (light and light["scene"]["daylight"]) or sun_up(setting, site, written) is not
    False:` made `if True:`
- test_a_plan_made_under_another_concept_is_out_of_date:
    environment_plan.py: `return found.get("method") == METHOD and found.get("environment") ==
    concept_version(store)` made `return found.get("method") == METHOD`
- test_a_house_on_a_plot_stands_on_flat_ground_under_its_sun_light:
    environment_plan.py: `round(-(far * far) / (2 * radius), 4) if radius else 0.0` made `round(-(far * far) / (2 *
    radius), 4) if radius else -1.0`
- test_the_plan_writer_writes_it_under_the_allowance_and_a_refused_answer_is_no_plan:
    environment_plan.py: `plan_writing.cleared(store, [f"environment-{world}"]` made `plan_writing.cleared(store,
    [world]`
- test_no_two_sites_on_one_body_share_a_spot_unless_the_setting_puts_them_there:
    environment_plan.py: `if found["metres"] < SAME_SPOT]` made `if found["metres"] < 0]`
- test_a_room_keeps_the_site_and_time_of_the_top_scene_it_stands_in:
    scene_sky.py: `if site["place"] == top and site.get("time"):` made `if site["place"] == place and
    site.get("time"):`
- test_keep_writes_a_timed_scene_and_takes_it_out_once_its_time_is_gone:
    scene_sky.py: `elif before is not None: path.unlink()` made `elif False: path.unlink()`
- test_a_picked_place_is_read_once_with_its_boxes_and_gaps:
    reading.py: `{**row, "count": len(row["boxes"]), "box": row["boxes"][0]}` made `{**row, "box": row["boxes"][0]}`
- test_a_new_pick_has_no_reading_until_read:
    reading.py: `if sha and found["concept"] == sha and found.get("method")` made `if found.get("method")`
- test_only_what_both_readers_agree_on_is_a_row_and_the_structure_stays:
    reading.py: `else row for row in rows if structural(row) or row["boxes"]]` made `else row for row in rows if
    row["boxes"]]`
- test_a_large_single_object_only_gemini_found_is_a_row_boxed_by_its_region:
    reading.py: `and area(region) >= LARGE * size[0] * size[1]` made `and area(region) >= 0`
- test_duplicates_go_one_box_one_row:
    reading.py: `and head(other) == head(row) and overlapping(other, row, size)), None)` made `and False), None)`
- test_a_row_is_found_by_its_own_words_first_and_an_older_reading_is_read_again_by_sam_only:
    reading.py: `again = {place: asked_again(store, place, folder) for place in places if earlier_rows(store,
    place)}` made `again = {}`
- test_rows_off_the_schema_are_refused:
    reading.py: `wrong += [] if row.get("kind") in KINDS else ["kind"]` made `wrong += []`
- test_a_cut_answer_is_refused_by_its_finish_reason_and_both_asks_answer_under_a_schema:
    reading.py: `raise concepts.Refused(str(unfinished)) from unfinished` made `return ""`
- test_a_rows_answer_off_the_schema_is_kept_with_its_cost_and_read_again:
    reading.py: `refused = {place: answer for place, answer in asked_places.items() if isinstance(answer[0], str)}`
    made `refused = {}`
- test_a_reading_answered_before_parts_were_asked_gets_them_in_one_call_its_rows_kept:
    reading.py: `and (any("part" not in row for row in found["inventory"]["rows"]) or not parts_current(store,
    found))]` made `and (not parts_current(store, found))]`
- test_a_reading_parted_under_an_older_parts_version_is_asked_again_and_the_new_parts_read_over_it:
    reading.py: `again = None if record.get("parts_version", 1) >= PARTS_VERSION else asked_parts_of(store, record,
    current=True)` made `again = None`
- test_a_concepts_light_is_asked_once_of_its_reading_and_refused_off_its_schema:
    reading.py: `wrong += ["scene"] if scene["unseen"] and not COLOUR.fullmatch(str(scene["unseen_colour"])) else
    []` made `wrong += []`
- test_only_a_row_both_readers_put_inside_another_rows_thing_is_a_part_of_it:
    reading_fixes.py: `INSIDE = 0.9` made `INSIDE = 0.5`
- test_a_reading_holding_a_part_is_fixed_once_free_its_children_moved:
    reading_fixes.py: `rows = reading.reanchored([dict(row) for row in rows], {item["row"]: f"on:{item['into']}" for
    item in merged})` made `rows = [dict(row) for row in rows]`
- test_no_plan_before_the_inventory_counts_then_each_item_tied_to_its_row:
    plans.py: `tied[name] = [row_id, *riders.get(row_id, [])]` made `tied[name] = [row_id]`
- test_his_edit_is_kept_as_his_own_and_checked:
    plans.py: `if len(doors) != len(base):` made `if False:`
- test_an_inside_place_waits_for_the_holders_plan_then_gets_its_shape_and_its_row:
    plans.py: `float(plan.get("w") or 6.0)` made `float(plan.get("w") or 5.0)`
- test_his_inside_places_and_rows_redo_what_follows:
    plans.py: `within.update({hold["place"]: holder for hold in edit["plan"]["holds"]})` made `within.update({})`
- test_a_room_adjoining_rooms_a_row_holds_is_held_by_that_row_over_one_it_only_overlaps:
    plans.py: `holds = [{**hold, "row": neighbours_row(hold, holds)} for hold in holds]` made `holds = list(holds)`
- test_a_room_changed_on_the_holders_plan_puts_draws_on_it_out_of_date_and_flags_its_pick:
    plans.py: `return room_at(draw["room"], size) != room_at(room, size)` made `return False`
- test_rewriting_a_parent_keeps_its_locked_childrens_rooms_and_only_his_edit_moves_them_or_hides:
    plans.py: `return {"plan": locked_rooms_kept(store, place, plan), "how": "written"` made `return {"plan": plan,
    "how": "written"`
- test_a_scene_he_added_in_the_app_is_a_place_once_its_design_is_done:
    plans.py: `return shown is not None and shown["how"] != "derived"` made `return shown is not None`
- test_a_parent_scene_with_no_data_of_its_own_is_a_place_once_its_design_is_done:
    plans.py: `if design_done(store, place): kept_for_stage(store, place, record["plan"])` made `if False:
    kept_for_stage(store, place, record["plan"])`
- test_overlapped_rooms_are_one_shared_room_and_a_box_dropped_in_a_room_a_thing_in_it:
    plans.py: `return {**found, **({"name": name} if name else {}), **({"things": things} if things else {})}` made
    `return found`
- test_a_reading_of_the_pick_is_the_inventory_its_rows_on_their_parents_and_its_boxes_the_holders:
    plans.py: `box = (row.get("boxes") or [None])[0] if "boxes" in row else row.get("box")` made `box =
    row.get("box")`
- test_items_are_sized_by_their_reading_and_ordered_by_their_boxes_and_what_has_no_size_or_row_is_a_gap:
    plans.py: `instances = sorted(row_items(rows), key=lambda instance: across(instance[3]))` made `instances =
    row_items(rows)`
- test_the_plan_stage_reads_his_plan_and_drops_it_once_the_pick_goes:
    plans.py: `elif path.is_file(): path.unlink()` made `elif False: path.unlink()`
- test_a_correction_runs_only_inside_his_yes_and_keeps_the_answer_as_his_edit:
    plans.py: `yes = compute.require_cleared("a plan correction", store)` made `yes = {"euros": 0.0, "key":
    "never-cleared"}`
- test_a_correction_with_no_note_sends_his_kept_edits_and_with_none_is_refused_before_any_spend:
    plans.py: `if note or request.get("marks") or request.get("context_marks"): return note` made `if True: return
    note`
- test_a_holder_with_no_outline_of_its_own_gets_one_round_its_inside_places_before_its_items:
    plans.py: `return (round(max(x + size[0] for (x, _), size in zip(spots, sizes)) + GAP, 3),` made `return
    (round(max(x + size[0] for (x, _), size in zip(spots, sizes)), 3),`
- test_a_spot_takes_its_child_scenes_own_plan_size_centred_where_it_sat_and_says_so:
    plans.py: `if size and (abs(size[0] - hold["w"]) > 0.001 or abs(size[1] - hold["d"]) > 0.001):` made `if False:`
- test_the_answer_is_a_plan_of_the_stage_tables_schema_and_each_failed_check_a_named_gap:
    plan_writing.py: `if row_id not in placed and parent in placed:` made `if False:`
- test_a_door_walled_in_or_an_inside_place_overlapping_another_is_a_gap:
    plan_checks.py: `if (mask & other_mask).sum() > OVERLAP * min(mask.sum(), other_mask.sum())]` made `if False]`
- test_a_footprint_answered_as_box_2d_is_measured_from_its_box:
    plan_writing.py: `keys[0]: left + wide / 2 if middle else left` made `keys[0]: left`
- test_an_arrangement_not_the_concepts_and_a_tube_joining_nothing_are_gaps:
    plan_checks.py: `for first, second, axis, said, drawn in relations(seen, laid, turn) if said != drawn]` made
    `for first, second, axis, said, drawn in relations(seen, laid, turn) if False]`
- test_a_row_off_to_the_side_or_facing_the_wrong_way_is_a_gap_and_a_run_of_crates_counts_whole_unless_spread:
    plan_checks.py: `if count > 1 and things and item[3] * item[4] > max(SPREAD * things, things + SPREAD_SLACK):`
    made `if False:`
- test_a_thing_the_creator_planned_is_laid_from_his_plan_where_and_the_way_it_is_drawn:
    plan_writing.py: `middle = [x + wide / 2, y + deep / 2] if facing is None:` made `middle = [x, y] if facing is
    None:`
- test_people_on_their_person_spots_things_seen_far_off_and_rows_beyond_the_place_are_no_gaps:
    plan_checks.py: `gaps, left_out = [], beyond(plan, inventory) | people(inventory)` made `gaps, left_out = [],
    people(inventory)`
- test_with_the_flag_off_a_writing_runs_only_inside_his_yes:
    plan_writing.py: `if AUTOMATIC: return compute.spending(` made `if True: return compute.spending(`
- test_with_the_flag_on_his_click_asks_no_yes_and_a_reading_writes_its_plan:
    web.py: `if not plan_writing.AUTOMATIC: price = plan_writing.price(store)` made `if True: price =
    plan_writing.price(store)`
- test_a_read_place_with_no_plan_is_owed_unless_refused_and_an_older_methods_call_sets_no_price:
    plan_writing.py: `return [place for place in to_write(store, places) if not refused_now(store, place)]` made
    `return to_write(store, places)`
- test_a_scene_added_in_the_app_takes_its_doors_from_its_holders_openings_into_it:
    plan_writing.py: `to = holder if opening.get("to") == place else opening.get("to")` made `to =
    opening.get("to")`
- test_the_free_fixes_stand_people_place_the_missing_turn_and_part_and_leave_the_rest_saying_why:
    plan_fixes.py: `plan["people"] = stood + found` made `plan["people"] = found + stood`
- test_a_box_of_things_drawn_apart_is_split_round_its_spread:
    plan_fixes.py: `for spot in spots: added_item(plan, row["id"], spot, size, shape)` made `for spot in spots[:1]:`
- test_a_correction_is_kept_only_when_it_leaves_fewer_gaps_and_what_is_left_says_why:
    plan_fixes.py: `if len(open_gaps(answer, inventory)) >= len(left): break` made `if False: break`
- test_a_row_at_the_concept_s_foot_marked_beyond_is_placed_where_its_box_projects:
    plan_fixes.py: `plan["beyond"] = [row for row in plan.get("beyond", []) if row in kept]` made `plan["beyond"] =
    plan.get("beyond", [])`
- test_the_narrow_walk_answers_as_the_whole_walk:
    plans_pass.py: `if path.is_file() and not path.name.endswith(".partial")` made `if path.is_file()`
- test_the_keep_runs_inside_one_moment:
    plans_pass.py: `with plans.one_moment():` made `with contextlib.nullcontext():`
- test_a_plan_fixed_before_a_fix_it_needs_is_fixed_again_in_a_process_of_its_own:
    plans_pass.py: `return bool(lacking) and len(missing(plan_fixes.fixed(plan, inventory)[0], inventory)) < lacking`
    made `return False`
- test_a_fixed_plan_with_a_pile_is_parted_again_free_and_then_settled:
    plans_pass.py (settled_again): `if more:` made `if False:`
- test_an_accepted_plan_row_is_never_parted_and_an_unaccepted_one_is_parted_before_the_keep:
    plans_pass.py: `return store.accepted(f"plan@{place}") is None` made `return True`
- test_a_plan_that_places_more_is_left_to_its_own_process_not_parted_first:
    plans_pass.py: `if not parts: return plan, calls` made `if False: return plan, calls`
- test_a_done_place_with_no_kept_plan_gets_one:
    plans_pass.py: `if not (plans.KEPT / f"{place}.json").is_file()` made `if True`
"""
import contextlib
import datetime
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

import pytest
from PIL import Image

from score import checks, contracts, graph, review, stages
from score.adapters import compute
from score.review import (concepts, discuss, environment_concept, environment_concept as ec, environment_plan,
                          overhead, plan_checks, plan_drawing, plan_fixes, plan_writing, plans, plans_pass, reading,
                          reading_fixes, scene_sky, setting, web)
from score.store import RUNNER, Store, runtime_store

REPO = pathlib.Path(__file__).resolve().parents[2]
HANDED_OVER = concepts.handed_over  # the real hand-over, for its own test; every other test stands it in


@pytest.fixture
def store(tmp_path, monkeypatch):
    """A store of the test's own, its bucket and kept sky in the test's folder; the books (the ledger's own test's)
    known, no spend ticket or grant, the library hand-over stood in."""
    monkeypatch.setattr(compute, "require_books", lambda what: None)
    monkeypatch.setattr(compute, "books_refusal", lambda: None)
    monkeypatch.delenv("SCORE_SPEND_TICKET", raising=False)
    monkeypatch.delenv(compute.GRANT, raising=False)
    monkeypatch.setattr(concepts, "offsite_store", lambda: runtime_store.FolderStore(tmp_path / "bucket"))
    monkeypatch.setattr(concepts, "handed_over", lambda store, place: "library: stand-in")
    monkeypatch.setattr(scene_sky, "KEPT", tmp_path / "sky")
    return Store.in_folder(tmp_path / "store")


SQUARE_PLANS = {  # the kept plans' parts the wording reads (inside, doors, leads), as the real home's stood 2026-10-28
    "street": {"inside": False, "doors": [["W", 14.4, 1.0, "STREET DOOR (stairwell) 1.0 x 2.06 m", 0.14]],
               "leads": {"W@0.14": {"to": "stairwell", "why": "the stairwell's street door"}}},
    "flat": {"inside": True, "doors": [["W", 2.5, 1.4, "BALCONY DOOR (glass) 1.4 x 2.2 m"],
                                       ["E", 4.4, 1.0, "FRONT DOOR to the stair landing 1.0 x 2.2 m"]],
             "leads": {"W": {"to": "outside", "why": "the glass door onto the flat's balcony, over the square and the "
                                                    "harbour"},
                       "E": {"to": "stairwell", "why": "the front door onto the stairwell's top landing"}}},
    "stairwell": {"inside": True, "doors": [["W", 4.4, 1.0, "FLAT FRONT DOOR (3rd floor) 1.0 x 2.2 m", 9.0],
                                            ["W", 4.4, 1.0, "NEIGHBOUR'S DOOR behind its gate (1st floor) 1.0 x 2.2 m",
                                             3.0],
                                            ["E", 4.4, 1.0, "STREET DOOR (steel gate) 1.0 x 2.2 m", 0.0]],
                  "leads": {"W@9": {"to": "flat"}, "W@3": {"to": "sealed"}, "E": {"to": "street"}}}}


@pytest.fixture
def square_plans(tmp_path, monkeypatch):
    """The Square's places' kept plans in a home of the test's own (SQUARE_PLANS), never the real home's."""
    plans = tmp_path / "home" / "design" / "plans"
    plans.mkdir(parents=True)
    for place, plan in SQUARE_PLANS.items():
        (plans / f"{place}.json").write_text(json.dumps(plan))
    monkeypatch.setattr(concepts, "PROPS_HOME", tmp_path / "home")



# --- accepts, rejects and waivers: nothing failing or worse is taken without his written reason -----------------------

NODE = "tally@hangar"


def make_tally(inputs, out, seed, params):
    (out / "tally.txt").write_text(inputs["tally"].read_text())
    (out / "origin.json").write_text(json.dumps({"seed": True, "from": str(inputs["tally"]),
                                                 "note": "an old output brought in"}))


def judge_tally(output, inputs, evidence):
    faults = int((output / "tally.txt").read_text())
    return checks.Verdict("faults", checks.PASS if faults <= 3 else checks.FAIL, f"{faults} faults, at most 3 pass",
                          {"faults": faults}, {"faults": "lower"}, tuple(f"fault {number}" for number in range(faults)))


TALLY = graph.Stage("tally", "place", make_tally, contracts.Contract("toy-tally", 1, lambda folder: []),
                    (checks.Check("faults", judge_tally),),
                    files={"tally": "{data}/{place}.txt"})


@pytest.fixture
def tally(tmp_path):
    """make(faults) runs the toy tally stage (at most 3 faults pass) on the hangar in one store; its output."""
    tally_store, data = Store.in_folder(tmp_path / "tally-store"), tmp_path / "tally-data"
    data.mkdir()

    def make(faults):
        (data / "hangar.txt").write_text(str(faults))
        graph.Runner([TALLY], graph.Environment("toy", 1, {"data": data}), tally_store).run(["hangar"])
        return review.record_of(tally_store, NODE)["output"]
    make.store, make.data = tally_store, data
    return make


def refusal(call):
    with pytest.raises(review.Refused) as refused:
        call()
    return str(refused.value)


def test_an_output_that_did_not_pass_cannot_be_accepted(tally):
    output = tally(5)
    assert "answered fail" in refusal(lambda: review.accept(tally.store, NODE, output, "owner"))
    assert tally.store.accepted(NODE) is None


def test_a_passing_output_is_accepted_by_the_runner_and_a_worse_one_only_by_the_owner_with_a_reason(tally):
    first = tally(1)
    assert tally.store.accepted(NODE) == first and tally.store.current_accept(NODE)["by"] == RUNNER
    second = tally(2)  # passes, but worse: the runner leaves it
    assert "faults 1 became 2" in refusal(lambda: review.accept(tally.store, NODE, second, "owner"))
    assert tally.store.accepted(NODE) == first
    written = review.accept(tally.store, NODE, second, "owner", worse_reason="the second fault is a false alarm")
    assert written["worse"] == ["faults: faults 1 became 2 (lower is better; worse from 1)"]
    assert tally.store.accepted(NODE) == second


def test_the_runner_accepts_within_what_the_owner_allowed_and_no_further(tally):
    """His worse accept records each measure's from and to; a later passing output no worse than the one he took is
    accepted by the runner with his accept named, one beyond it waits for him."""
    tally(1)
    second = tally(2)
    given = review.accept(tally.store, NODE, second, "owner", worse_reason="two faults are fine here")
    assert given["allowed"] == {"faults": {"faults": {"from": 1, "to": 2}}}
    tally(1)  # better: the runner takes it as ever
    fourth = tally("2\n")  # worse than the third, as bad as the one he took
    assert tally.store.accepted(NODE) == fourth
    assert tally.store.current_accept(NODE)["reason"].startswith(
        f"accepted automatically: within the owner's accept of {given['at'][:10]} ({second[:12]})")
    tally(3)  # beyond what he allowed
    assert tally.store.accepted(NODE) == fourth


def card(answer, **measures):
    sides = {"halo": "higher", "veil": "lower", "faults": "lower", "lowest clap": "higher", "ferry reach": "lower",
             "stray": "lower"}
    return {"heads": {"answer": answer, "measures": measures, "better": {name: sides[name] for name in measures}}}


@pytest.mark.parametrize("new, old, worse", [
    ({"halo": 0.31}, {"halo": 0.32}, False),  # 0.01 darker reads the same (the owner, 2026-10-13: a 2% step)
    ({"veil": 0.059}, {"veil": 0.04}, False),
    ({"halo": 0.30}, {"halo": 0.32}, True),  # 0.02 is worse
    ({"faults": 3}, {"faults": 2}, True),  # one more fault
    ({"lowest clap": 0.3760}, {"lowest clap": 0.3761}, True),  # a score no viewer reads: any move
    ({"ferry reach": 0.024}, {"ferry reach": 0.02}, False),  # 4 mm: unseen
    ({"ferry reach": 0.026}, {"ferry reach": 0.02}, True),  # 6 mm
    ({"stray": 0.0001}, {"stray": 0.0}, False),  # under half a percent of a surface
    ({"stray": 0.006}, {"stray": 0.0}, True),
])
def test_a_measure_is_worse_only_by_a_step_a_viewer_could_see(new, old, worse):
    assert bool(review.regressions(card("pass", **new), card("pass", **old))) == worse


def test_an_answer_that_drops_is_worse_whatever_its_measures_did():
    assert review.regressions(card("fail", halo=0.33), card("pass", halo=0.32)) == ["heads: pass became fail"]


def test_an_owners_reject_moves_the_accepted_output_back_and_the_runner_never_takes_it_again(tally):
    first = tally(1)
    second = tally(0)
    assert tally.store.accepted(NODE) == second  # better: accepted by the runner
    assert "not tally@hangar's accepted output" in refusal(
        lambda: review.reject(tally.store, NODE, first, "owner", "w"))
    assert "needs a reason" in refusal(lambda: review.reject(tally.store, NODE, second, "owner", " "))
    review.reject(tally.store, NODE, second, "owner", "zero faults means the gate saw nothing")
    assert tally.store.accepted(NODE) == first
    assert review.accept_automatically(tally.store, NODE, second) is None
    tally(0)  # the runner runs the same key again: it never takes the rejected output back
    assert tally.store.accepted(NODE) == first
    review.accept(tally.store, NODE, second, "owner", "on a second look it is right")
    assert tally.store.accepted(NODE) == second


def test_the_owners_commands_refuse_without_his_terminal(tally, tmp_path):
    output = tally(1)
    for words in (["reject", NODE, output, "--reason", "x"], ["accept", NODE, output],
                  ["waive", NODE, "k", "faults", "--reason", "x"]):
        found = subprocess.run([sys.executable, "-m", "score.review", *words], cwd=REPO, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, env={**os.environ, "PROPS_HOME": str(tmp_path / "home")})
        assert found.returncode != 0 and "only the owner" in found.stderr, (words, found.stderr)


def test_a_waived_gate_lets_its_output_be_accepted_for_that_key_only(tally):
    """Fault (review of step 0, 2026-10-11): the hook guarded waivers/, but nothing wrote or read a waiver, so the
    owner had no way to let a gate he judged wrong pass."""
    output = tally(5)
    key = review.record_of(tally.store, NODE, output)["key"]
    assert "needs a reason" in refusal(lambda: review.waive(tally.store, NODE, key, "faults", "owner", " "))
    assert "has no check" in refusal(lambda: review.waive(tally.store, NODE, key, "tilt", "owner", "why"))
    review.waive(tally.store, NODE, key, "faults", "owner", "the five are one fault seen five times")
    review.accept(tally.store, NODE, output, "owner")
    assert tally.store.accepted(NODE) == output
    later = tally(6)  # a new key: the waiver does not carry over
    assert "answered fail" in refusal(lambda: review.accept(tally.store, NODE, later, "owner"))


def test_an_accepted_gaps_objects_leave_the_comparison_and_any_other_object_still_blocks(tmp_path, monkeypatch):
    """The got-worse comparison is a gate an accepted gap moves its objects' faults from (overseer 2026-10-16;
    assembly@wreck: resting objects 2 became 3, all three in "wreck: three pieces do not rest"). With a wreck gap
    written here: the gap's objects at new faults pass; another object at a new fault still reads worse."""
    from score.stages import gaps

    def resting(objects, findings):
        return {"resting": {"answer": "pass", "measures": {"objects": objects}, "better": {"objects": "lower"},
                            "findings": findings}}
    old = resting(2, ["/wreck/Objects/leg_strut_1: floats 0.0469: nothing under it",
                      "/wreck/Objects/leg_foot_1: tips 0.2474: its weight falls outside",
                      "/wreck/Objects/crate_1: sunk 0.03: below"])
    named = ["/wreck/Objects/leg_strut_1: tips 0.4439: its weight falls outside",
             "/wreck/Objects/forward_section_1: unstable 0.3228: moves", "/wreck/Objects/crate_1: sunk 0.03: below"]
    monkeypatch.setattr(review, "accepted_card", lambda store, node, output: old)
    monkeypatch.setattr(gaps, "FOLDER", tmp_path / "checks/gaps")  # the owner's decision, written here
    gaps.FOLDER.mkdir(parents=True)
    (gaps.FOLDER / "wreck.json").write_text(json.dumps({"gaps": [{
        "name": "wreck: three pieces do not rest", "row": "assembly", "check": "resting",
        "objects": ["/wreck/Objects/leg_strut_1", "/wreck/Objects/leg_foot_1", "/wreck/Objects/forward_section_1"],
        "reason": "a test's decision", "decided": "owner, 2026-10-16", "faults": []}]}))
    judged = {"output": "new", "verdicts": resting(3, named)}
    assert review.worse_than_accepted(None, "assembly@wreck", judged) == []
    judged = {"output": "new", "verdicts": resting(3, named + ["/wreck/Objects/hull_plate_1: tips 0.3: outside"])}
    assert review.worse_than_accepted(None, "assembly@wreck", judged) == [
        "resting: objects 2 became 3 (lower is better; worse from 1)"]
    grown = [finding.replace("crate_1: sunk 0.03", "crate_1: sunk 0.09") for finding in named]
    judged = {"output": "new", "verdicts": resting(3, grown)}  # an existing fault outside the gaps grows
    assert review.worse_than_accepted(None, "assembly@wreck", judged) != []
    judged = {"output": "new", "verdicts": resting(3, named)}  # no gap reaches this node's gate
    assert review.worse_than_accepted(None, "assembly@hub", judged) != []


def test_the_page_says_who_accepted_and_offers_no_accept_for_a_failed_output(tally):
    """A wording check guarding the owner's rules (score/CLAUDE.md, review/): a seed carries its banner, the page says
    whether the runner or the owner accepted, a worse output is offered to him only with a reason, a failed one not at
    all, and his reject and waiver show."""
    def page():
        return review.page(tally.store, NODE).read_text()
    tally(1)
    assert "Unverified seed." in page() and "The runner accepted this output automatically" in page()
    second = tally(2)
    assert "with the Accept button on the cockpit's page of tally@hangar, saying why it may be worse" in page()
    review.accept(tally.store, NODE, second, "owner", worse_reason="one fault is a false alarm")
    assert "The owner accepted it" in page()
    review.reject(tally.store, NODE, second, "owner", "on a third look it is wrong")
    assert "The owner rejected this output." in page()
    failed = tally(9)
    assert "It cannot be accepted" in page() and "Accept button" not in page()
    review.waive(tally.store, NODE, review.record_of(tally.store, NODE, failed)["key"], "faults", "owner", "seen twice")
    assert "Waived by owner" in page() and "seen twice" in page()


# --- the owner's decision from a signed-in web user -------------------------------------------------------------------

def test_the_signed_in_user_decides_by_his_own_name(tally):
    output = tally(1)
    web.decide(tally.store, NODE, output, "reject", by="joey", reason="looked again later")
    assert tally.store.accepted(NODE) is None
    written = web.decide(tally.store, NODE, output, "accept", by="joey", reason="it reads right after all")
    assert written["by"] == "joey" and tally.store.accepted(NODE) == output


@pytest.mark.parametrize("faults, decision, named, why", [
    (1, "accept", {"by": ""}, "signed-in owner's own name"),
    (1, "accept", {"by": "  "}, "signed-in owner's own name"),
    (1, "accept", {"by": None}, "signed-in owner's own name"),
    (1, "accept", {"by": "runner"}, "signed-in owner's own name"),
    (1, "waive", {"by": "joey"}, "one of accept, reject"),
    (5, "accept", {"by": "joey"}, "answered fail"),
    (1, "reject", {"by": "joey", "reason": " "}, "needs a reason"),
])
def test_a_web_decision_off_his_rules_is_refused(tally, faults, decision, named, why):
    output = tally(faults)
    assert why in refusal(lambda: web.decide(tally.store, NODE, output, decision, **named))


def test_a_worse_output_needs_his_written_reason_from_the_web_too(tally):
    tally(1)
    second = tally(2)
    assert "worse than the accepted one" in refusal(lambda: web.decide(tally.store, NODE, second, "accept", by="joey"))
    written = web.decide(tally.store, NODE, second, "accept", by="joey", worse_reason="two faults are fine")
    assert written["worse_reason"] == "two faults are fine" and tally.store.accepted(NODE) == second


def test_the_signed_in_checkout_writes_the_worlds_stop_line_never_in_an_agents_process(tally, monkeypatch):
    """C22 from the cockpit: his checkout is his money yes; the line is the guard's own, a first line counts from the
    books given; an empty name or the runner's is refused, and an agent's process writes nothing."""
    from score.adapters.compute import guard
    from score.store import AGENT_MARKERS
    for name in AGENT_MARKERS:
        monkeypatch.delenv(name, raising=False)
    books = {"month": "2026-10", "bill": 50.0, "ledger": 40.0, "google": 0.0}
    assert "signed-in owner's own name" in refusal(
        lambda: web.stop(tally.store, "toy", 9.0, "films", by="runner", books=lambda: books))
    line = web.stop(tally.store, "toy", 9.0, "checkout 1: fix-sound", by="joey", books=lambda: books)
    assert line["by"] == "joey" and line["baseline"] == books and guard.current(tally.store, "toy")["euros"] == 9.0
    raised = web.stop(tally.store, "toy", 12.0, "checkout 2", by="joey", books=lambda: {})
    assert raised["before"] == 9.0 and raised["baseline"] == books
    monkeypatch.setenv(AGENT_MARKERS[0], "1")
    with pytest.raises(PermissionError):
        web.stop(tally.store, "toy", 99.0, "an agent's", by="joey", books=lambda: books)
    assert guard.current(tally.store, "toy")["euros"] == 12.0


# --- concept draws and locks: a paid call only inside his yes at today's price ----------------------------------------


def a_picture(colour=(40, 90, 160)):
    buffer = io.BytesIO()
    Image.new("RGB", (64, 40), colour).save(buffer, "PNG")
    return buffer.getvalue()


def stand_in(asked):
    """A model that keeps what it was asked and answers a picture."""
    def answer(wording, pictures):
        asked.append((wording, [picture.size for picture in pictures]))
        return a_picture((len(asked) * 40, 80, 120))
    return answer


def prompt_stand_in(asked, answer="The corrected prompt."):
    """A prompt model that keeps what it was asked and answers `answer`."""
    def corrected(question, pictures):
        asked.append((question, [picture.size for picture in pictures]))
        return answer
    return corrected


def ready_above(monkeypatch, box=(0, 0, 32, 20)):
    """Stand-ins for the layer above's scene inventory reading, its made plan and the box of the row holding a place
    (reading.py's and the plan's own tests own those)."""
    from score.review import reading
    monkeypatch.setattr(reading, "reading_of", lambda store, place: {"stand-in": place})
    monkeypatch.setattr(concepts, "plan_made", lambda store, place: True)
    monkeypatch.setattr(concepts, "holding_row", lambda store, place: "holder")
    monkeypatch.setattr(concepts, "holder_words", lambda store, place: "the black angular spaceship")
    monkeypatch.setattr(concepts, "outlined", lambda store, place: True)
    monkeypatch.setattr(reading, "row_boxes", lambda store, place, row: [list(box)])


def said_yes(store, monkeypatch, place="campgrounds"):
    key = concepts.yes_key(place, review.now())
    review.spend(store, "override", key, 0.15, "joey", purpose="test")
    monkeypatch.setenv("SCORE_SPEND_TICKET", f"override {key}")
    return key


def picked_draw(store, monkeypatch, place, colour):
    """A first draw of `place` made and picked; its sha."""
    said_yes(store, monkeypatch, place)
    sha = concepts.draw(store, place, {}, "joey", caller=lambda wording, pictures: a_picture(colour))["sha"]
    concepts.pick(store, place, sha, "joey")
    return sha


SHIP_ROOMS = ("cockpit", "quarters", "storage", "galley", "shiplock", "engineroom", "walkway")


def test_a_draw_runs_only_inside_the_owners_yes(store, monkeypatch):
    with pytest.raises(compute.Refused):
        concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))
    assert concepts.draws(store, "campgrounds") == []


def test_a_first_draw_is_worded_from_the_places_data_and_kept(store, monkeypatch):
    key = said_yes(store, monkeypatch)
    asked = []
    record = concepts.draw(store, "campgrounds", {"note": "more dust"}, "joey", caller=stand_in(asked))
    assert record["yes"] == key and record["euros"] == 0.15 and record["base"] is None
    assert store.objects.exists(f"blobs/{record['sha']}")
    assert concepts.draws(store, "campgrounds") == [record] and concepts.placed(store) == ["campgrounds"]
    wording, sizes = asked[0]
    assert "campgrounds" in wording and "The creator's note: more dust" in wording
    assert sizes == []  # a top place with no reference: its wording alone


def test_a_redraw_sends_the_base_boxed_and_clean_with_each_marks_note(store, monkeypatch):
    said_yes(store, monkeypatch)
    first = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))
    said_yes(store, monkeypatch)
    asked = []
    marks = [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.3, "note": "a red door"}]
    prompted = []
    second = concepts.draw(store, "campgrounds", {"marks": marks, "note": "warmer", "base": first["sha"]}, "joey",
                           caller=stand_in(asked), reviser=prompt_stand_in(prompted))
    question, seen = prompted[0]  # Gemini: the boxed and clean picture, the prompt it was drawn from, each note
    assert "Box 1 (middle left): a red door." in question and "Overall: warmer" in question
    assert first["wording"] in question and seen == [(64, 40), (64, 40)]
    wording, sizes = asked[0]  # the draw: the corrected prompt, the box's note, the boxed and the clean picture
    assert wording.startswith("The corrected prompt.") and "Box 1 (middle left): a red door." in wording
    assert sizes == [(64, 40), (64, 40)] and "Overall: warmer" in wording
    assert second["base"] == first["sha"] and second["marks"][0]["note"] == "a red door"
    assert [call["model"] for call in second["calls"]] == [concepts.PROMPT_MODEL, "gemini-3-pro-image"]
    assert second["corrected"] == "The corrected prompt." == concepts.own_wording(store, "campgrounds")
    assert concepts.current_draw(store, "campgrounds", concepts.wording_now(store, "campgrounds"))
    with pytest.raises(concepts.Refused, match="outside the picture"):
        concepts.draw(store, "campgrounds", {"marks": [{"x": 0.9, "y": 0, "w": 0.5, "h": 0.1}], "base": first["sha"]},
                      "joey", caller=stand_in([]), reviser=prompt_stand_in([]))
    with pytest.raises(concepts.Refused, match="no draw of"):
        concepts.draw(store, "hub", {"base": first["sha"]}, "joey", caller=stand_in([]), reviser=prompt_stand_in([]))


def test_a_pick_takes_only_a_draw_of_the_place_and_unlocks_again(store, monkeypatch):
    said_yes(store, monkeypatch)
    drawn = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))
    with pytest.raises(concepts.Refused):
        concepts.pick(store, "campgrounds", "0" * 64, "joey")
    concepts.pick(store, "campgrounds", drawn["sha"], "joey")
    assert concepts.picked(store, "campgrounds") == drawn["sha"]
    concepts.pick(store, "campgrounds", None, "joey")
    assert concepts.picked(store, "campgrounds") is None
    started = []
    monkeypatch.setattr(web, "reading_started", lambda store, place, by: started.append((place, by)) or "log")
    assert web.concept_pick(store, "campgrounds", drawn["sha"], "joey")["library"] == "library: stand-in"
    assert started == [("campgrounds", "joey")]  # the pick starts its scene inventory reading, no yes asked
    assert "reading" not in web.concept_pick(store, "campgrounds", None, "joey") and len(started) == 1


def test_a_reading_runs_as_a_process_of_its_own_in_the_picks_store(store):
    started = []
    log = web.reading_started(store, "campgrounds", "joey", start=lambda argv, **named: started.append((argv, named)))
    [(argv, named)] = started
    assert argv[-5:] == ["-m", "score.review.reading", "campgrounds", "--by", "joey"] and named["start_new_session"]
    assert named["env"]["SCORE_SPEND_STORE"] == str(store.cache.parent) and log.endswith(".log")


def test_every_draw_is_copied_off_this_pc_by_its_sha_and_a_failed_copy_keeps_the_draw_and_says_why(
        store, monkeypatch, tmp_path):
    said_yes(store, monkeypatch)
    record = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))
    bucket = runtime_store.FolderStore(tmp_path / "bucket")
    assert record["offsite"] == f"concept-draws/{record['sha']}.png"
    assert bucket.read_bytes(record["offsite"]) == store.objects.read_bytes(f"blobs/{record['sha']}")
    assert json.loads(bucket.read_bytes(f"concept-draws/{record['sha']}.json"))["wording"] == record["wording"]

    class Down:
        def exists(self, key):
            raise ConnectionError("the bucket did not answer")
    said_yes(store, monkeypatch)
    failed = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([1]), offsite=Down())
    assert failed["offsite"] is None and "did not answer" in failed["offsite_refused"]
    assert concepts.draws(store, "campgrounds") == [record, failed]


def test_a_pick_is_handed_to_the_library_by_its_own_concept_command(store, monkeypatch, tmp_path):
    monkeypatch.setattr(concepts, "handed_over", HANDED_OVER)
    from score.stages.library import backend
    monkeypatch.setattr(backend, "settings", lambda: {"SCORE_LIB_ROOT": str(tmp_path / "lib"),
                                                      "SCORE_LIB_COMMAND": "score-lib",
                                                      "SCORE_LIB_BLOBS_DIR": str(tmp_path / "blobs")})
    ran = []

    def run(words, **named):
        ran.append((words, named))
        said = {"place": "campgrounds", "did": "locked", "address": "concept/campgrounds@1",
                "saved": {"committed": "c" * 40, "pushed": True, "why": ""}}
        return subprocess.CompletedProcess(words, 0, json.dumps(said) + "\n", "")
    assert concepts.handed_over(store, "campgrounds", run=run) == "library: locked concept/campgrounds@1"
    words, named = ran[0]
    assert words[:4] == ["score-lib", "--root", str(tmp_path / "lib"), "concept"]
    assert words[words.index("--place") + 1] == "campgrounds" and words[words.index("--world") + 1] == "world1"
    assert words[words.index("--store") + 1] == str(store.objects.root)
    assert named["env"]["SCORE_LIB_BLOBS_DIR"] == str(tmp_path / "blobs") and named["cwd"] == str(tmp_path / "lib")

    refused = lambda words, **named: subprocess.CompletedProcess(words, 1, "", "no SCORE store\n")  # noqa: E731
    assert concepts.handed_over(store, "campgrounds", run=refused) == "not in the library: no SCORE store"
    monkeypatch.setattr(backend, "settings", lambda: {"SCORE_LIB_BACKEND": "none"})
    assert concepts.handed_over(store, "campgrounds", run=run).startswith("not in the library: no library")


def test_the_draw_and_redraw_prices_are_the_measured_calls_at_the_standard_tier(tmp_path):
    per_unit = tmp_path / "per-unit.json"
    measured = {"high_euros": 0.07048, "basis": "batch price of measured calls"}
    per_unit.write_text(json.dumps({"stages": {"closeup": measured}}))
    assert concepts.draw_euros(per_unit) == 0.15  # 0.07048 / 0.5 = 0.14096, up to the cent
    per_unit.write_text(json.dumps({"stages": {
        "closeup": measured, "finish-route-list": {"high_euros": 0.01665, "basis": "batch price of measured calls"}}}))
    assert concepts.redraw_euros(per_unit) == 0.18  # (0.07048 + 0.01665) / 0.5 = 0.17426, up to the cent
    per_unit.write_text(json.dumps({"stages": {}}))
    assert concepts.draw_euros(per_unit) is None


def test_the_click_writes_its_yes_at_the_price_shown_then_draws_inside_it(store, monkeypatch):
    monkeypatch.setattr(concepts, "draw_euros", lambda: 0.15)

    def run(argv, env, **kwargs):  # the draw's own process, here in-process with the stand-in model
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        record = concepts.draw(store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1], caller=stand_in([]))
        return subprocess.CompletedProcess(argv, 0, json.dumps(record) + "\n", "")

    record = web.concept_draw(store, "campgrounds", {"note": ""}, 0.15, "joey", run=run)
    yes = store.spend_yes("override", record["yes"])
    assert yes["by"] == "joey" and yes["euros"] == 0.15 and "campgrounds" in yes["purpose"]
    with pytest.raises(review.Refused, match="not today's measured price"):
        web.concept_draw(store, "campgrounds", {}, 0.10, "joey", run=run)
    with pytest.raises(review.Refused):
        web.concept_draw(store, "campgrounds", {}, 0.15, "runner", run=run)
    monkeypatch.setattr(concepts, "redraw_euros", lambda: 0.19)
    redraw = {"marks": [], "note": "warmer", "base": record["sha"]}
    with pytest.raises(review.Refused, match="not today's measured price"):
        web.concept_draw(store, "campgrounds", redraw, 0.15, "joey", run=run)  # a redraw is two calls: its own price


def test_an_agents_process_cannot_pick_or_keep_a_wording_in_the_framework_store(store, monkeypatch):
    said_yes(store, monkeypatch)
    drawn = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))
    monkeypatch.setattr(store, "is_framework_store", lambda: True)
    monkeypatch.setattr(concepts, "running_under_agent", lambda: True)
    with pytest.raises(PermissionError):
        concepts.pick(store, "campgrounds", drawn["sha"], "joey")
    assert concepts.picked(store, "campgrounds") is None
    with pytest.raises(PermissionError):
        concepts.worded(store, "campgrounds", "my words", "joey")
    assert concepts.own_wording(store, "campgrounds") is None


def test_a_place_within_another_is_sent_its_picked_picture_first_and_its_wording_as_context(store, monkeypatch):
    base = picked_draw(store, monkeypatch, "base", (200, 10, 10))
    ready_above(monkeypatch)
    said_yes(store, monkeypatch, "lab")
    asked = []
    record = concepts.draw(store, "lab", {}, "joey", caller=stand_in(asked))
    wording, sizes = asked[0]
    assert sizes == [(32, 20)] and record["picks"] == {"base": base}  # only the crop of what holds it
    assert wording.startswith("The black angular spaceship (picture 1) is divided into these compartments: 1. hub, ")
    assert "This concept is number 8: lab. " + concepts.INSIDE_ONLY in wording
    assert "1. a crop of the base's picked concept: the black angular spaceship, which holds it" in wording
    assert concepts.current_draw(store, "lab", concepts.wording_now(store, "lab"))
    picked_draw(store, monkeypatch, "base", (10, 200, 10))  # a new pick above: the lab's draw is out of date
    assert not concepts.current_draw(store, "lab", concepts.wording_now(store, "lab"))
    assert concepts.undrawn(store, ["base", "lab"])[0] == ["lab"]
    assert ("In the ship; for flying and navigating the ship, one room: the cockpit at the nose"
            in concepts.generated(store, "cockpit"))


def test_a_reference_comes_from_the_places_data_and_waits_while_it_is_not_here(store, tmp_path, monkeypatch):
    monkeypatch.setattr(concepts, "PROPS_HOME", tmp_path)
    monkeypatch.setattr(concepts, "picked", lambda _store, place: "abc" if place == "hangar" else None)
    monkeypatch.setattr(concepts, "inputs_of", lambda place: {"references": [
        {"picture": "{home}/references/quarters.png", "shows": "its look only"}]} if place == "quarters" else {})
    ready_above(monkeypatch)
    assert "is not on this machine" in concepts.waits(store, "quarters")  # its reference, the owner's quarters picture
    (tmp_path / "references").mkdir()
    Image.new("RGB", (8, 8)).save(tmp_path / "references" / "quarters.png")
    assert concepts.waits(store, "quarters") is None
    sources = [source for _, source in concepts.sent_pictures(store, "quarters")]
    assert sources == [("crop", "hangar", [0, 0, 32, 20]), tmp_path / "references/quarters.png"]
    assert concepts.generated(store, "quarters").endswith("Style: 2099 space base, moon base, mars "
                                                 "base, SpaceX-type rockets, Chinese and American mixed.")


def test_the_ships_length_and_reference_come_from_the_hangars_data_and_reach_its_rooms(store, monkeypatch):
    assert "It holds the ship, a crew shuttle 46 m long" in concepts.generated(store, "hangar")
    assert concepts.sent_pictures(store, "hangar")[-1][1].name == "shuttle-screenshot.png"
    assert "ship" not in concepts.tree()["within"] and "ship" not in concepts.tree()["shells"]  # no layer of its own
    assert concepts.above("cockpit") == "hangar"
    given = {"hangar": {"says": "It holds a barge 80 m long.", "references": []}}
    monkeypatch.setattr(concepts, "inputs_of", lambda place: given.get(place, {}))
    hangar = concepts.generated(store, "hangar")
    assert "It holds a barge 80 m long." in hangar and "46 m" not in hangar
    assert concepts.sent_pictures(store, "hangar") == []  # no crop while the base is not ready, no reference now


def test_no_measure_is_generated_but_the_creators_own_says(store):
    # owner's rule (2026-10-20): a generated wording sizes in relative words; only the creator's own says carry metres
    found = concepts.tree()
    for place in [*found["within"], *found["shells"], "square", "campgrounds"]:
        wording = concepts.generated(store, place)
        for name in filter(None, [place, *concepts.inside_of(place), concepts.above(place)]):
            said = [concepts.inputs_of(name).get("says", ""), *concepts.inputs_of(name).get("holds", {}).values()]
            for words in said:
                wording = wording.replace(words.rstrip("."), "")
        assert not re.search(r"\d+(\.\d+)? ?m\b", wording), (place, wording)


def test_an_outside_place_is_drawn_from_above_and_an_inside_place_as_a_cutaway(store, square_plans):
    assert concepts.OUTSIDE_VIEW in concepts.generated(store, "base")
    assert concepts.OUTSIDE_VIEW in concepts.generated(store, "campgrounds")
    assert concepts.INSIDE_VIEW in concepts.generated(store, "cockpit")
    assert concepts.INSIDE_VIEW in concepts.generated(store, "hangar")
    street = concepts.generated(store, "street")
    assert concepts.EVERY_DRAW in street and concepts.OUTSIDE_VIEW in street


def test_people_are_drawn_only_where_the_places_data_has_them(store, monkeypatch):
    street = concepts.generated(store, "street")  # its design: people
    assert f"{concepts.EVERY_DRAW}, {concepts.WITH_PEOPLE}." in street
    hub = concepts.generated(store, "hub")  # its design shows none and its look names none
    assert f"{concepts.EVERY_DRAW}, {concepts.NO_PEOPLE}." in hub and concepts.WITH_PEOPLE not in hub
    monkeypatch.setattr(concepts, "inputs_of", lambda place: {"people": True} if place == "hub" else {})
    assert concepts.WITH_PEOPLE in concepts.generated(store, "hub")  # the creator's say goes over the design


def test_a_draw_from_an_older_wording_does_not_count_for_draw_all(tmp_path, monkeypatch):
    store = Store.in_folder(tmp_path)
    older = [{"base": None, "wording": "an older wording"}]
    monkeypatch.setattr(concepts, "draws", lambda _store, _place: older)
    assert concepts.undrawn(store, ["old_station"])[0] == ["old_station"]
    older.append({"base": None, "wording": concepts.generated(store, "old_station")})
    assert concepts.undrawn(store, ["old_station"])[0] == []
    concepts.worded(store, "old_station", "One concept painting of the old station at night.", "joey")
    assert concepts.undrawn(store, ["old_station"])[0] == ["old_station"]  # its draw is from the generated wording
    concepts.worded(store, "old_station", None, "joey")
    assert concepts.undrawn(store, ["old_station"])[0] == []


def test_an_edited_wording_is_sent_word_for_word_and_stays_the_places_own_until_back_to_generated(store, monkeypatch):
    generated = concepts.generated(store, "campgrounds")
    asked = []
    said_yes(store, monkeypatch)
    first = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in(asked))
    assert asked[-1][0] == generated and concepts.own_wording(store, "campgrounds") is None
    said_yes(store, monkeypatch)
    edited = "One concept painting of the camp grounds, dusty."
    concepts.draw(store, "campgrounds", {"wording": f"  {edited}\n"}, "joey", caller=stand_in(asked))
    assert asked[-1][0] == edited and concepts.own_wording(store, "campgrounds") == edited
    assert concepts.current_draw(store, "campgrounds", concepts.wording_now(store, "campgrounds"))
    assert not concepts.current_draw(store, "campgrounds", "One concept painting of the camp grounds, clean.")
    said_yes(store, monkeypatch)
    concepts.draw(store, "campgrounds", {"base": first["sha"], "wording": "ignored"}, "joey", caller=stand_in(asked),
                  reviser=prompt_stand_in([], "The camp grounds, dusty, the tents red."))
    corrected = "The camp grounds, dusty, the tents red."  # a redraw's corrected prompt becomes its own wording
    assert "Image 1" in asked[-1][0] and concepts.own_wording(store, "campgrounds") == corrected
    said_yes(store, monkeypatch)
    concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in(asked))  # Draw all's request: no wording
    assert asked[-1][0] == corrected
    with pytest.raises(review.Refused, match="no wording of its own"):
        web.concept_generated(store, "galley", "joey")
    web.concept_generated(store, "campgrounds", "joey")
    assert concepts.wording_now(store, "campgrounds") == generated
    with pytest.raises(concepts.Refused, match="at most"):
        concepts.draw(store, "campgrounds", {"wording": "x" * 9000}, "joey", caller=stand_in(asked))


def test_a_places_wording_names_its_own_doors_and_openings_and_no_others(store, square_plans):
    flat = concepts.generated(store, "flat")
    # owner, 2026-10-21: doors drawn lettered with room names; where a door leads is never written on it
    assert ("Its unlabelled doors: balcony door (glass) onto the outside, over the square and the harbour; front door "
            "to the stair landing into the stairwell; no other doors or openings.") in flat
    assert "no text or signs" in flat
    assert "neighbour's door behind its gate (1st floor) (shut)" in concepts.generated(store, "stairwell")


def test_a_picked_place_it_opens_into_is_sent_after_the_one_above_and_its_new_pick_puts_the_draw_out_of_date(
        store, monkeypatch, square_plans):
    square = picked_draw(store, monkeypatch, "square", (200, 10, 10))
    ready_above(monkeypatch)
    assert concepts.sent_picks(store, "flat") == {"square": square}  # the stairwell is not picked yet: not sent
    said_yes(store, monkeypatch, "stairwell")
    concepts.pick(store, "stairwell", concepts.draw(store, "stairwell", {}, "joey", caller=stand_in([]))["sha"],
                  "joey")
    words = [words for words, _ in concepts.sent_pictures(store, "flat")]
    assert words[0] == "a crop of the square's picked concept: the black angular spaceship, which holds it"
    assert words[1] == "the stairwell, picked: match the door they share"  # no view through its balcony door
    said_yes(store, monkeypatch, "flat")
    asked = []
    record = concepts.draw(store, "flat", {}, "joey", caller=stand_in(asked))
    assert len(asked[0][1]) == 2 and set(record["picks"]) == {"square", "stairwell"}
    assert "2. the stairwell, picked: match the door they share" in asked[0][0]
    assert concepts.current_draw(store, "flat", concepts.wording_now(store, "flat"))
    said_yes(store, monkeypatch, "stairwell")
    concepts.pick(store, "stairwell", concepts.draw(store, "stairwell", {}, "joey", caller=stand_in([1]))["sha"],
                  "joey")
    assert not concepts.current_draw(store, "flat", concepts.wording_now(store, "flat"))


def test_a_place_is_sized_against_the_places_beside_it_in_words_only(store, tmp_path, monkeypatch):
    """Ranked by the floor of each kept plan beside it (the design's, concepts.plan_of), its walls against a person."""
    monkeypatch.setattr(concepts, "PROPS_HOME", tmp_path / "home")
    sizes = {"hangar": (15.0, 14.0, "walls 12 m"), "hub": (5.0, 6.0, ""), "lab": (4.0, 3.0, ""), "tube": (3.0, 2.0, "")}
    (tmp_path / "home/design/plans").mkdir(parents=True)
    for place in concepts.inside_of("base", store):
        wide, deep, height = sizes.get(place, (4.0, 4.0, ""))
        (tmp_path / "home/design/plans" / f"{place}.json").write_text(json.dumps({"w": wide, "d": deep,
                                                                                  "height": height}))
    hangar = concepts.generated(store, "hangar")
    assert "Size: the largest in the base, floor about seven times any other's, walls towering over people." in hangar
    assert concepts.ROOF_KEPT in hangar and concepts.ROOF_KEPT not in concepts.generated(store, "base")
    assert "Size: one of the smaller in the base" in concepts.generated(store, "lab")


def test_every_generated_wording_is_short(store):
    # owner's word budget: a generated wording stays under LONGEST_GENERATED characters
    found = concepts.tree()
    for place in [*found["within"], *found["shells"], "square", "campgrounds", "old_station", "wreck"]:
        assert len(concepts.generated(store, place)) <= concepts.LONGEST_GENERATED, place


def test_a_mark_on_the_picture_above_reaches_both_calls_with_that_picture_boxed(store, monkeypatch):
    picked_draw(store, monkeypatch, "base", (200, 10, 10))
    ready_above(monkeypatch)
    said_yes(store, monkeypatch, "lab")
    first = concepts.draw(store, "lab", {}, "joey", caller=stand_in([]))
    said_yes(store, monkeypatch, "lab")
    asked, prompted = [], []
    above = [{"on": "base", "x": 0.7, "y": 0.0, "w": 0.3, "h": 0.3, "note": "this is the lab: its dome"}]
    record = concepts.draw(store, "lab", {"base": first["sha"], "context_marks": above, "note": ""}, "joey",
                           caller=stand_in(asked), reviser=prompt_stand_in(prompted))
    said = "Box P1 (top right of the picked concept of the base): this is the lab: its dome."
    assert said in prompted[0][0] and said in asked[0][0]
    assert len(prompted[0][1]) == len(asked[0][1]) == 3  # the draw boxed and clean, the base's pick boxed
    assert "image 3 is the picked concept of the base" in asked[0][0]
    assert record["context_marks"][0]["on"] == "base"
    said_yes(store, monkeypatch, "lab")
    with pytest.raises(concepts.Refused, match="no locked concept"):
        concepts.draw(store, "lab", {"base": first["sha"], "context_marks": [{**above[0], "on": "square"}]}, "joey",
                      caller=stand_in([]), reviser=prompt_stand_in([]))


def test_no_two_ship_rooms_get_the_same_wording_or_references(store):
    wordings = {room: concepts.generated(store, room) for room in SHIP_ROOMS}
    assert len(set(wordings.values())) == len(SHIP_ROOMS)
    assert "for food: eat and prepare meals (counter, food stores, a table with fold-down seats)" in wordings["galley"]
    assert "pilot seats" in wordings["cockpit"] and "pilot seats" not in wordings["galley"]  # no copied look
    assert "on the port side" in wordings["quarters"] and "four bunks in two stacks" in wordings["quarters"]
    references = {room: [source.name for _, source in concepts.sent_pictures(store, room)
                         if not isinstance(source, str)]
                  for room in SHIP_ROOMS}
    assert references == {room: [] for room in SHIP_ROOMS}  # the owner, 2026-10-21: no room has a picture of its own


def test_a_place_is_drawn_only_once_the_layer_above_is_picked_read_and_planned_and_holds_it(store, monkeypatch):
    from score.review import reading
    ready, waiting = concepts.undrawn(store, ["base", "hub", "street"])
    assert ready == ["base"]
    assert waiting == {"hub": "waits for base's concept to be locked",
                       "street": "waits for square's concept to be locked"}
    said_yes(store, monkeypatch, "hub")
    with pytest.raises(concepts.Refused, match="hub waits for base's concept to be locked"):
        concepts.draw(store, "hub", {}, "joey", caller=stand_in([]))
    assert concepts.draws(store, "hub") == []
    picked_draw(store, monkeypatch, "base", (200, 10, 10))
    assert concepts.waits(store, "hub") == "waits for base's scene inventory to be read"
    monkeypatch.setattr(reading, "reading_of", lambda store, place: {"stand-in": place})
    assert concepts.waits(store, "hub") == "waits for base's plan to be made"
    monkeypatch.setattr(concepts, "plan_made", lambda store, place: True)
    assert concepts.waits(store, "hub") == "waits for base's plan to lay it out"
    ready_above(monkeypatch)
    assert concepts.waits(store, "hub") is None and "hub" in concepts.undrawn(store, ["hub"])[0]
    said_yes(store, monkeypatch, "hub")
    drawn = concepts.draw(store, "hub", {}, "joey", caller=stand_in([]))
    monkeypatch.setattr(concepts, "plan_made", lambda store, place: False)  # the plan above is made again
    with pytest.raises(concepts.Refused, match="hub waits for base's plan to be made"):
        concepts.pick(store, "hub", drawn["sha"], "joey")
    said_yes(store, monkeypatch, "hub")
    with pytest.raises(concepts.Refused, match="hub waits for base's plan to be made"):
        concepts.draw(store, "hub", {"base": drawn["sha"], "note": "x"}, "joey", caller=stand_in([]),
                      reviser=prompt_stand_in([]))
    assert concepts.step_refusal(store, "hub", "read") == "its concept is not locked"
    assert concepts.step_refusal(store, "base", "read") is None
    monkeypatch.setattr(reading, "reading_of", lambda store, place: None)
    assert concepts.step_refusal(store, "base", "plan") == "its scene inventory is not read"


def test_a_part_of_a_places_outside_has_no_concept_of_its_own(store):
    assert concepts.waits(store, "launch") == "is part of the square's concept, with none of its own"
    assert "launch" not in concepts.undrawn(store, ["square", "launch"])[0]
    assert "launch" not in concepts.undrawn(store, ["square", "launch"])[1]
    assert "part of it: across the water in the distance, the rocket launch" in concepts.generated(store, "square")


def test_ship_rooms_share_one_compartment_block_and_are_sent_only_the_crop_of_the_ship(store, monkeypatch, tmp_path):
    # the hangar's reference is the owner's private picture: a stand-in in this test's home, never the machine's copy
    monkeypatch.setattr(concepts, "PROPS_HOME", tmp_path)
    for ref in concepts.references_of(store, "hangar"):
        concepts.resolved(ref["picture"]).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 8)).save(concepts.resolved(ref["picture"]))
    from score.review import reading
    named = concepts.holder_words
    picked_draw(store, monkeypatch, "base", (200, 10, 10))
    ready_above(monkeypatch, box=(16, 10, 32, 20))
    picked_draw(store, monkeypatch, "hangar", (90, 90, 90))
    with monkeypatch.context() as inventory:  # the holding row's name on the reading above
        inventory.setattr(reading, "reading_of", lambda store, place: {"inventory": {"rows": [
            {"id": "holder", "name": "black angular spaceship"}]}})
        assert named(store, "cockpit") == "the black angular spaceship"
    for room in SHIP_ROOMS:  # the owner, 2026-10-21: no window view, only the crop of what holds it
        sources = [source for _, source in concepts.sent_pictures(store, room)]
        assert sources == [("crop", "hangar", [16, 10, 32, 20])], room
    assert concepts.sent_picture(store, ("crop", "hangar", [16, 10, 32, 20])).size == (16, 10)
    blocks = {room: concepts.generated(store, room).split(" This concept is number ")[0] for room in SHIP_ROOMS}
    assert len(set(blocks.values())) == 1  # every sibling the identical block
    assert blocks["cockpit"].startswith("The black angular spaceship (picture 1) is divided into these compartments: "
                                        "1. cockpit and nav (flying and navigating the ship), 2. ")
    assert "7. walkway (the corridor joining every room" in blocks["cockpit"]
    galley = concepts.generated(store, "galley")
    assert "This concept is number 4: galley. " + concepts.INSIDE_ONLY in galley
    assert "window" not in galley.replace(concepts.INSIDE_ONLY, "")


# --- Discuss: one call inside his yes, its thread sent to the redraw --------------------------------------------------


def answerer(asked, answer="Make the door red and wider.", euros=0.0271):
    """A prompt model that keeps what it was asked and answers `answer` at `euros`."""
    def answered(question, pictures):
        asked.append((question, [picture.size for picture in pictures]))
        return answer, euros
    return answered


def first_draw(store, monkeypatch):
    said_yes(store, monkeypatch)
    return concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))


def test_a_discuss_runs_inside_the_yes_and_keeps_question_answer_and_cost(store, monkeypatch):
    first = first_draw(store, monkeypatch)
    monkeypatch.delenv("SCORE_SPEND_TICKET")
    request = {"base": first["sha"], "question": "is the door too small?",
               "marks": [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.3, "note": "this door"}]}
    with pytest.raises(compute.Refused):
        discuss.discuss(store, "campgrounds", request, "joey", asker=answerer([]))
    key = said_yes(store, monkeypatch)
    asked = []
    entry = discuss.discuss(store, "campgrounds", request, "joey", asker=answerer(asked))
    question, sizes = asked[0]  # the redraw's pictures (boxed, clean), its prompt, the mark's note, the question
    assert "Box 1 (middle left): this door." in question and "is the door too small?" in question
    assert first["wording"] in question and sizes == [(64, 40), (64, 40)]
    assert entry["answer"] == "Make the door red and wider." and entry["euros"] == 0.0271 and entry["yes"] == key
    assert discuss.discussions(store, "campgrounds") == [entry] and discuss.spent(store, ["campgrounds"]) == 0.0271
    said_yes(store, monkeypatch)
    again = []
    discuss.discuss(store, "campgrounds", {"base": first["sha"], "question": "and the roof?"}, "joey",
                    asker=answerer(again, "Keep it."))
    assert "Creator: is the door too small?\nYou: Make the door red and wider." in again[0][0]
    with pytest.raises(concepts.Refused, match="a question"):
        discuss.discuss(store, "campgrounds", {"base": first["sha"], "question": " "}, "joey", asker=answerer([]))


def test_a_redraw_after_a_discuss_sends_the_thread_to_the_prompt_rewrite_and_closes_it(store, monkeypatch):
    first = first_draw(store, monkeypatch)
    said_yes(store, monkeypatch)
    discuss.discuss(store, "campgrounds", {"base": first["sha"], "question": "warmer light?"}, "joey",
                    asker=answerer([], "Yes: late afternoon sun from the left."))
    assert len(discuss.open_thread(store, "campgrounds", first["sha"])) == 1
    said_yes(store, monkeypatch)
    prompted = []
    second = concepts.draw(store, "campgrounds", {"base": first["sha"]}, "joey", caller=stand_in([]),
                           reviser=prompt_stand_in(prompted))
    question = prompted[0][0]
    assert "Creator: warmer light?\nYou: Yes: late afternoon sun from the left." in question
    assert second["discussed"] == [discuss.discussions(store, "campgrounds")[0]["at"]]
    assert discuss.open_thread(store, "campgrounds", first["sha"]) == []  # closed, kept for the record
    assert len(discuss.discussions(store, "campgrounds")) == 1


def test_the_click_writes_its_yes_at_the_price_shown_then_discusses_inside_it(store, monkeypatch):
    first = first_draw(store, monkeypatch)
    monkeypatch.setattr(discuss, "price", lambda: 0.04)

    def run(argv, env, **kwargs):  # the Discuss's own process, here in-process with the stand-in model
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        entry = discuss.discuss(store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1], asker=answerer([]))
        return subprocess.CompletedProcess(argv, 0, json.dumps(entry) + "\n", "")

    entry = web.concept_discuss(store, "campgrounds", {"base": first["sha"], "question": "why?"}, 0.04, "joey",
                                run=run)
    yes = store.spend_yes("override", entry["yes"])
    assert yes["by"] == "joey" and yes["euros"] == 0.04 and "Discuss" in yes["purpose"]
    with pytest.raises(review.Refused, match="not today's measured price"):
        web.concept_discuss(store, "campgrounds", {"base": first["sha"], "question": "why?"}, 0.03, "joey", run=run)


def test_a_calls_cost_is_read_from_its_token_usage():
    usage = {"usageMetadata": {"promptTokenCount": 2700, "candidatesTokenCount": 200, "thoughtsTokenCount": 1700}}
    assert 0.02 < discuss.call_euros(usage) < 0.04


# --- the environment concept: his locked version is what every draw reads ---------------------------------------------


WORLD = "world1"


def said_yes_to(store, monkeypatch, key="test-yes"):
    review.spend(store, "override", key, 0.05, "joey", purpose="test")
    monkeypatch.setenv("SCORE_SPEND_TICKET", f"override {key}")
    return key


def drawn(store, monkeypatch, place="campgrounds"):
    said_yes_to(store, monkeypatch, concepts.yes_key(place, review.now()))
    return concepts.draw(store, place, {}, "joey", caller=lambda wording, pictures: a_picture(
        (len(concepts.draws(store, place)) * 30, 9, 9)))


def test_environment_1s_concept_is_todays_data_shown_locked(store):
    shown = ec.current(store, WORLD, ["campgrounds", "hangar", "cockpit", "hub", "launch"])
    concept = shown["concept"]
    assert shown["locked"] and shown["prefilled"] and shown["versions"] == 0
    assert concept["style"] == ec.style_now() and concept["style"].startswith("2099 space base")
    assert {(ref["place"], ref["picture"].rsplit("/", 1)[-1]) for ref in concept["references"]} == {
        ("hangar", "shuttle-screenshot.png")}  # the owner, 2026-10-21: the cockpit's and quarters' pictures removed
    assert concept["setting"] == setting.now()  # the reference table's bodies, its sites on them
    assert {body["name"]: body["gravity"] for body in concept["setting"]["bodies"] if body.get("around")} == {
        "Earth": 9.82, "Moon": 1.624, "Mars": 3.728}  # from their mass and radius, never the game's
    places = {row["name"]: row for row in concept["places"]}
    assert places["Base"]["place"] == "base" and "Hangar" in places["Base"]["holds"]
    assert "launch" not in [row.get("place") for row in concept["places"]]  # a part of the square: no place
    assert "Campgrounds" in [row["name"] for row in concept["places"]] or any(
        row["place"] == "campgrounds" for row in concept["places"])
    assert len(places[next(name for name in places if places[name].get("place") == "hangar")]["holds"]) >= 6
    assert ec.in_force(store) is None and ec.version(store) is None and not ec.unlocked(store)


def test_a_version_kept_before_settings_reads_todays_setting(store):
    concepts.recorded(store, f"{ec.AREA}/{WORLD}/versions/20261021T000000.000000+0000.json", {
        "world": WORLD, "concept": {"style": "x", "physics": [{"world": "Moon"}], "references": [], "places": []},
        "locked": True, "by": "joey", "at": "2026-10-21T00:00:00+00:00"})
    found = ec.newest(store, WORLD)["concept"]
    assert "physics" not in found and found["setting"] == setting.now() == ec.setting_of(store, WORLD)


def test_a_locked_version_is_what_every_draw_reads(store):
    concept = ec.prefilled(["campgrounds"])
    concept["style"] = "Cold steel and ice, a frontier mine."
    concept["references"].append({"picture": "{home}/references/mine.png", "shows": "the pit's look",
                                  "place": "campgrounds"})
    ec.saved(store, WORLD, concept, True, "joey")
    assert concepts.style(store) == "Style: Cold steel and ice, a frontier mine."
    assert "Cold steel and ice" in concepts.generated(store, "campgrounds")
    assert concepts.references_of(store, "campgrounds") == [{"picture": "{home}/references/mine.png",
                                                             "shows": "the pit's look"}]
    assert concepts.references_of(store, "street") == []
    assert concepts.waits(store, "campgrounds").startswith("its reference")  # not on this machine


def test_unlocking_puts_every_draw_and_pick_out_of_date_and_stops_new_ones(store, monkeypatch):
    first = drawn(store, monkeypatch)
    assert first["environment"] is None
    concepts.pick(store, "campgrounds", first["sha"], "joey")
    assert concepts.picked(store, "campgrounds") == first["sha"]
    assert concepts.current_draw(store, "campgrounds", concepts.wording_now(store, "campgrounds"))
    ec.saved(store, WORLD, ec.prefilled(["campgrounds"]), False, "joey")  # his Unlock
    assert ec.unlocked(store) and concepts.picked(store, "campgrounds") is None
    assert not concepts.current_draw(store, "campgrounds", concepts.wording_now(store, "campgrounds"))
    assert concepts.waits(store, "campgrounds") == "waits for the environment concept to be locked"
    with pytest.raises(concepts.Refused, match="environment concept"):
        drawn(store, monkeypatch)
    with pytest.raises(concepts.Refused, match="environment concept"):
        concepts.pick(store, "campgrounds", first["sha"], "joey")
    ec.saved(store, WORLD, ec.prefilled(["campgrounds"]), True, "joey")  # locked again: a new version
    with pytest.raises(concepts.Refused, match="another environment concept"):
        concepts.pick(store, "campgrounds", first["sha"], "joey")
    again = drawn(store, monkeypatch)
    assert again["environment"] == ec.version(store)
    concepts.pick(store, "campgrounds", again["sha"], "joey")
    assert concepts.picked(store, "campgrounds") == again["sha"]


def test_a_concept_out_of_shape_is_refused(store):
    with pytest.raises(ec.Refused):
        ec.saved(store, WORLD, {"style": "x" * (ec.LONGEST_LINE + 1)}, True, "joey")
    with pytest.raises(ec.Refused):
        ec.saved(store, WORLD, {"setting": {"bodies": [{"name": "Moon", "radius_km": "heavy"}]}}, True, "joey")
    kept = ec.saved(store, WORLD, {"places": [{"name": " Dock ", "holds": "Bay, Office ,"}]}, False, "joey")
    assert kept["concept"]["places"] == [{"name": "Dock", "holds": ["Bay", "Office"]}]


def test_an_ask_runs_only_inside_the_owners_yes_and_proposes_checked_fields(store, monkeypatch):
    concept = ec.prefilled(["campgrounds"])
    request = {"topic": "setting", "answer": "Only the Sun and Mars, the camp on Mars", "concept": concept}
    asked = []

    def model(question, pictures):
        asked.append((question, pictures))
        return ('```json\n{"setting": {"bodies": [{"body": "sun", "name": "Sun", "reference": "sun"}, {"body": '
                '"mars", "name": "Mars", "reference": "mars", "radius_km": 220}], "sites": [{"place": "campgrounds", '
                '"on": "mars", "latitude": 30, "longitude": 130}]}}\n```')

    with pytest.raises(compute.Refused):
        ec.ask(store, WORLD, request, "joey", reviser=model)
    key = said_yes_to(store, monkeypatch)
    record = ec.ask(store, WORLD, request, "joey", reviser=model)
    mars = record["proposed"]["setting"]["bodies"][1]
    assert record["yes"] == key and mars["radius_km"] == 3389.5 and mars["gravity"] == 3.728  # the table's, not 220
    assert record["proposed"]["setting"]["sites"][0]["on"] == "mars"
    assert "the camp on Mars" in asked[0][0] and ec.question_of("setting") in asked[0][0]
    assert ec.asks(store, WORLD) == [record]
    with pytest.raises(ec.Refused, match="no JSON"):
        ec.ask(store, WORLD, request, "joey", reviser=lambda question, pictures: "I think Mars.")


def test_the_send_writes_its_yes_at_the_price_shown_then_asks_inside_it(store, monkeypatch):
    monkeypatch.setattr(ec, "ask_euros", lambda: 0.05)

    def run(argv, env, **kwargs):  # the ask's own process, here in-process with the stand-in model
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        record = ec.ask(store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1],
                        reviser=lambda question, pictures: '{"style": "Bright and clean"}')
        return subprocess.CompletedProcess(argv, 0, json.dumps(record) + "\n", "")

    request = {"topic": "style", "answer": "brighter", "concept": ec.prefilled([])}
    record = web.environment_ask(store, WORLD, request, 0.05, "joey", run=run)
    yes = store.spend_yes("override", record["yes"])
    assert yes["by"] == "joey" and yes["euros"] == 0.05 and "environment concept" in yes["purpose"]
    assert record["proposed"] == {"style": "Bright and clean"}
    with pytest.raises(review.Refused, match="not today's measured price"):
        web.environment_ask(store, WORLD, request, 0.04, "joey", run=run)
    with pytest.raises(review.Refused):
        web.environment_ask(store, WORLD, request, 0.05, "runner", run=run)


def test_a_new_reference_goes_to_the_bucket_and_its_local_copy_only_while_unlocked(store, tmp_path, monkeypatch):
    monkeypatch.setattr(ec, "PROPS_HOME", tmp_path / "home")
    bucket = runtime_store.FolderStore(tmp_path / "bucket")
    with pytest.raises(ec.Refused, match="locked"):
        ec.referenced(store, WORLD, a_picture(), "dock.png", "the dock's look", "hangar", "joey", offsite=bucket)
    ec.saved(store, WORLD, ec.prefilled([]), False, "joey")
    kept = ec.referenced(store, WORLD, a_picture(), "my dock!.png", "the dock's look", "hangar", "joey",
                         offsite=bucket)
    assert kept["concept"]["references"][-1] == {"picture": "{home}/references/my-dock-.png",
                                                 "shows": "the dock's look", "place": "hangar"}
    index = json.loads(bucket.read_bytes("references/index.json"))
    assert bucket.exists(index["my-dock-.png"]["key"]) and (tmp_path / "home/references/my-dock-.png").is_file()
    with pytest.raises(ec.Refused, match="no picture"):
        ec.referenced(store, WORLD, b"not a picture", "x.png", "", None, "joey", offsite=bucket)
    with pytest.raises(ec.Refused, match="already named"):
        ec.referenced(store, WORLD, a_picture((1, 2, 3)), "my dock!.png", "", None, "joey", offsite=bucket)


def test_an_agents_process_cannot_keep_a_version_or_a_reference(store, monkeypatch):
    monkeypatch.setattr(store, "is_framework_store", lambda: True)
    monkeypatch.setattr(concepts, "running_under_agent", lambda: True)
    monkeypatch.setattr(ec, "running_under_agent", lambda: True)
    with pytest.raises(PermissionError):
        ec.saved(store, WORLD, ec.prefilled([]), False, "joey")
    with pytest.raises(PermissionError):
        ec.kept_reference(a_picture(), "dock.png")


# --- the setting: real bodies from the cited table, invented ones whole -----------------------------------------------


SUN = {"name": "Sun", "kelvin": 5800, "lux": 100000, "latitude": 52.0, "tilt_deg": 23.44, "day_hours": 24,
       "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}


HOUSE = {"bodies": [], "plots": [{"name": "Meadow", "gravity": 9.81}], "lights": [SUN],
         "backdrops": [{"name": "Sky", "lux": 10000}],
         "sites": [{"place": "house", "on": "meadow", "x": 0, "y": "0", "height_m": 0}]}


def test_every_real_bodys_value_names_its_source():
    table = setting.reference()
    for key, body in table["bodies"].items():
        values = [field for field in body if field != "cited"]
        assert set(body["cited"]) == set(values), key
        assert all(source in table["sources"] for source in body["cited"].values()), key


def test_environment_one_takes_its_bodies_from_the_table_and_its_gravity_from_their_mass():
    found = setting.now()
    bodies = {body["body"]: body for body in found["bodies"]}
    assert set(bodies) == {"sun", "earth", "moon", "mars"} and found["plots"] == []
    assert {key: bodies[key]["gravity"] for key in ("earth", "moon", "mars")} == pytest.approx(
        {"earth": 9.82, "moon": 1.62, "mars": 3.73}, abs=0.005)  # NASA's fact sheets: surface gravity (mean)
    assert bodies["moon"]["radius_km"] == 1737.4 and bodies["moon"]["locked_to"] == "earth"
    assert bodies["moon"]["distance_km"] == pytest.approx(384400, rel=1e-3)
    assert {site["place"]: site["on"] for site in found["sites"]} == {
        "square": "earth", "wreck": "moon", "old_station": "moon", "base": "moon", "campgrounds": "mars"}
    assert bodies["sun"]["kelvin"] == 5772.0 and bodies["sun"]["lux"] == 128000.0  # the body and the light it gives
    assert "lux" not in bodies["earth"] and found["lights"] == []
    assert found["backdrops"] == [{"backdrop": "stars", "name": "Stars", "shape": "dome", "lux": 0.0001}]


def test_a_house_on_a_plot_needs_no_bodies_its_sun_is_a_light():
    found = setting.checked(HOUSE)
    assert found["bodies"] == [] and found["plots"] == [{"plot": "meadow", "name": "Meadow", "gravity": 9.81}]
    assert found["lights"][0]["light"] == "sun" and found["lights"][0]["day_hours"] == 24.0
    assert found["backdrops"] == [{"backdrop": "sky", "name": "Sky", "shape": "dome", "lux": 10000.0}]
    assert found["sites"] == [{"place": "house", "on": "meadow", "x": 0.0, "y": 0.0, "height_m": 0.0}]
    with pytest.raises(setting.Refused, match="no equinox|equinox is no moment"):
        setting.checked({**HOUSE, "lights": [{**SUN, "equinox": "noon"}]})
    with pytest.raises(setting.Refused, match="shape is one of"):
        setting.checked({**HOUSE, "backdrops": [{"name": "Sky", "lux": 1, "shape": "box"}]})
    with pytest.raises(setting.Refused, match="share a key"):
        setting.checked({**HOUSE, "backdrops": [{"name": "Sun", "lux": 1}]})
    with pytest.raises(setting.Refused, match="shines with"):
        setting.checked({"bodies": [{"name": "Star", "radius_km": 1, "mass_kg": 1, "lux": 5}]})


def test_a_real_body_set_off_the_table_keeps_his_values_and_an_invented_one_needs_all_of_its_own():
    rows = [{"reference": "sun"}, {"reference": "earth", "day_hours": "30", "radius_km": "7000,5"}]
    earth = setting.checked({"bodies": rows})["bodies"][1]
    assert earth["radius_km"] == 7000.5 and earth["day_hours"] == 30.0 and "pole_ra_deg" not in earth  # his own day
    assert earth["mass_kg"] == 5.9722e24 and earth["name"] == "Earth"  # the rest the table's
    with pytest.raises(setting.Refused, match="no distance_km"):
        setting.checked({"bodies": [{"reference": "sun"}, {"name": "Home", "radius_km": 5000, "mass_kg": 5e24,
                                                           "around": "sun"}]})
    with pytest.raises(setting.Refused, match="no real body"):
        setting.checked({"bodies": [{"reference": "vulcan"}]})


def test_a_setting_out_of_shape_is_refused():
    with pytest.raises(setting.Refused, match="no body or plot"):
        setting.checked({**HOUSE, "sites": [{"place": "house", "on": "the moon", "x": 0, "y": 0}]})
    with pytest.raises(setting.Refused, match="orbits nothing"):
        setting.checked({"bodies": [{"reference": "sun"}, {"reference": "mars", "around": ""},
                                    {"name": "Star two", "radius_km": 1, "mass_kg": 1}]})
    with pytest.raises(setting.Refused, match="is no body"):
        setting.checked({"bodies": [{"reference": "sun"}, {"reference": "moon"}]})  # it orbits an Earth not there
    with pytest.raises(setting.Refused, match="latitude of 95"):
        setting.checked({"bodies": [{"reference": "sun"}, {"reference": "mars"}],
                         "sites": [{"place": "camp", "on": "mars", "latitude": 95, "longitude": 0}]})


def test_a_models_values_for_a_real_body_are_dropped_for_the_tables():
    proposed = setting.proposed({"bodies": [{"body": "moon", "name": "Moon", "reference": "moon", "radius_km": 220}]})
    assert proposed["bodies"] == [{"body": "moon", "name": "Moon", "reference": "moon"}]


def test_a_models_answer_never_stacks_two_sites_the_concept_had_apart():
    before = setting.now()
    rounded = [{**site, "latitude": 55.0, "longitude": 0.0} if site["on"] == "moon" else site
               for site in before["sites"]]
    kept = setting.kept_apart({**before, "sites": rounded}, before)
    assert kept["sites"] == before["sites"]  # every Moon site back where it stood
    spots = [setting.spot(site) for site in before["sites"]]
    assert len(set(spots)) == len(spots)  # environment 1's proposal: each site its own spot
    moved = [{**site, "longitude": 0.5} if site["place"] == "base" else site for site in before["sites"]]
    assert setting.kept_apart({**before, "sites": moved}, before)["sites"] == moved  # a site he moves alone moves


# --- overhead: the sky at a site, against skies known apart from the code ---------------------------------------------


ENVIRONMENT_1 = setting.now()


BODIES = ENVIRONMENT_1["bodies"]


LIT_HOUSE = setting.checked({
    "plots": [{"name": "Meadow", "gravity": 9.81}],
    "lights": [{"name": "Sun", "kelvin": 5800, "lux": 100000, "latitude": 52.0, "tilt_deg": 23.44, "day_hours": 24,
                "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}],
    "backdrops": [{"name": "Sky", "shape": "dome", "lux": 10000, "kelvin": 9000}],
    "sites": [{"place": "house", "on": "meadow", "x": 0, "y": 0}]})


def at(found, key):
    return next(body for body in found["bodies"] if body["body"] == key)


def moon_of(when):
    return at(overhead.from_body(BODIES, "earth", 0.0, 0.0, when), "moon")


def test_the_moon_is_full_and_new_when_it_was():
    assert moon_of("2024-01-25T18:00:00Z")["lit"] > 0.97  # full Moon, 25 January 2024, 17:54 UT
    assert moon_of("2024-01-11T12:00:00Z")["lit"] < 0.03  # new Moon, 11 January 2024, 11:57 UT
    assert moon_of("2024-01-25T18:00:00Z")["across"] == pytest.approx(0.52, abs=0.04)


def test_the_suns_light_stands_where_it_does_over_greenwich_at_the_equinox_at_its_strength():
    sun = overhead.from_body(BODIES, "earth", 51.48, 0.0, "2024-03-20T12:07:00Z")["lights"][0]
    assert sun["of"] == "sun" and sun["kelvin"] == 5772.0
    assert sun["altitude"] == pytest.approx(90 - 51.48, abs=0.5) and sun["azimuth"] == pytest.approx(180, abs=1)
    assert sun["lux"] == pytest.approx(128000, rel=0.02)  # March: Earth near its mean distance


def test_the_suns_disc_is_widest_in_january_and_narrowest_in_july():
    sun = [overhead.from_body(BODIES, "earth", 0.0, 0.0, when)["lights"][0]["across"]
           for when in ("2024-01-03T00:00:00Z", "2024-07-05T00:00:00Z")]
    # the Sun's apparent diameter at perihelion and aphelion: 32.53 and 31.46 arc minutes
    assert sun[0] == pytest.approx(32.53 / 60, abs=0.005) and sun[1] == pytest.approx(31.46 / 60, abs=0.005)


def test_earth_hangs_still_about_two_degrees_across_over_a_near_side_moon_site_and_its_phase_turns():
    seen = [at(overhead.from_body(BODIES, "moon", 55.0, 0.0, f"2099-06-{day:02d}T12:00:00Z"), "earth")
            for day in (1, 8, 15)]
    assert all(1.75 < earth["across"] < 2.05 for earth in seen)  # Earth from the Moon: about 1.9 degrees
    assert max(earth["altitude"] for earth in seen) - min(earth["altitude"] for earth in seen) < 1  # locked: it stays
    assert seen[0]["lit"] < 0.1 and seen[2]["lit"] > 0.8  # a fortnight from new Earth to nearly full


def test_mars_from_earth_and_earth_from_mars_are_points_and_the_sun_is_dimmer_at_mars():
    assert at(overhead.from_body(BODIES, "earth", 22.3, 114.2, "2099-06-01T12:00:00Z"), "mars")["across"] < 0.01
    from_mars = overhead.from_body(BODIES, "mars", 30.0, 130.0, "2099-06-01T12:00:00Z")
    assert at(from_mars, "earth")["across"] < 0.01
    assert 45000 < from_mars["lights"][0]["lux"] < 65000  # 1.38 to 1.67 AU: 128000 over its square


def test_environment_1_overhead_holds_its_bodies_the_suns_light_and_the_stars():
    site = next(site for site in ENVIRONMENT_1["sites"] if site["place"] == "base")
    found = overhead.seen(ENVIRONMENT_1, site, "2099-06-01T12:00:00Z")
    assert [light["of"] for light in found["lights"]] == ["sun"]
    assert {body["body"] for body in found["bodies"]} == {"earth", "mars"}  # never the Moon it stands on, nor the Sun
    assert found["backdrops"] == [{"name": "Stars", "shape": "dome", "lux": 0.0001}]


def test_a_houses_sun_is_a_light_on_its_day_path_with_no_bodies():
    site = LIT_HOUSE["sites"][0]
    noon = overhead.seen(LIT_HOUSE, site, "2024-03-20T12:00:00Z")
    assert noon["bodies"] == [] and noon["backdrops"][0]["name"] == "Sky"
    sun = noon["lights"][0]
    assert sun["of"] is None and sun["lux"] == 100000 and sun["kelvin"] == 5800
    assert sun["altitude"] == pytest.approx(90 - 52.0, abs=0.01) and sun["azimuth"] == pytest.approx(180, abs=0.01)
    summer = overhead.seen(LIT_HOUSE, site, "2024-06-20T12:00:00Z")["lights"][0]  # a quarter year on: at its highest
    assert summer["altitude"] == pytest.approx(90 - 52.0 + 23.44, abs=0.3)
    midnight = overhead.seen(LIT_HOUSE, site, "2024-03-21T00:00:00Z")["lights"][0]
    assert midnight["altitude"] == pytest.approx(-38.0, abs=0.5)
    morning = overhead.seen(LIT_HOUSE, site, "2024-03-20T06:00:00Z")["lights"][0]
    assert morning["altitude"] == pytest.approx(0.0, abs=0.15) and morning["azimuth"] == pytest.approx(90, abs=0.2)


def test_an_invented_body_turns_by_its_own_day_under_an_invented_star():
    world = {"body": "home", "name": "Home", "radius_km": 5000.0, "mass_kg": 5e24, "around": "star",
             "distance_km": 1.2e8, "period_days": 300.0, "eccentricity": 0.0, "inclination_deg": 0.0,
             "day_hours": 30.0, "tilt_deg": 0.0}
    bodies = [{"body": "star", "name": "Star", "radius_km": 600000.0, "mass_kg": 2e30, "kelvin": 4000.0,
               "lux": 1e5, "lux_at_km": 1.2e8}, world]
    start = datetime.datetime(2100, 1, 1, tzinfo=datetime.timezone.utc)
    heights = [overhead.from_body(bodies, "home", 0.0, 0.0, (start + datetime.timedelta(hours=hour)).isoformat())
               ["lights"][0]["altitude"] for hour in range(31)]
    assert max(heights) > 80 and min(heights) < -80  # on its equator the star passes over and under once a day
    again = overhead.from_body(bodies, "home", 0.0, 0.0, "2100-01-02T06:00:00Z")["lights"][0]["altitude"]
    assert again == pytest.approx(heights[0], abs=1.5)  # back where it was, less its orbit's turn of 1.5 degrees


# --- the environment plan: sites where the setting puts them, shaped by their own plans -------------------------------


BASE = {"w": 60.0, "d": 50.0, "items": [["CENTRAL HUB", 20.0, 20.0, 18.0, 18.0, "", "item"],
                                        ["LARGE HANGAR", 0.0, 0.0, 16.0, 12.0, "", "item"],
                                        ["RADIO MAST", 50.0, 40.0, 1.0, 1.0, "", "item"],
                                        ["TYRE TRACKS", 0.0, 45.0, 30.0, 2.0, "", "item"]],
        "rows": {"CENTRAL HUB": ["central_hub"], "LARGE HANGAR": ["large_hangar"]},
        "shapes": {"CENTRAL HUB": {"shape": "circle", "tall": 6.0}, "LARGE HANGAR": {"tall": 15.0},
                   "RADIO MAST": {"tall": 12.0}, "TYRE TRACKS": {"tall": 0.0}},
        "holds": [{"place": "hub", "row": "central_hub", "x": 20.0, "y": 20.0, "w": 18.0, "d": 18.0},
                  {"place": "hangar", "row": "large_hangar", "x": 0.0, "y": 0.0, "w": 16.0, "d": 12.0}]}


@pytest.fixture()
def scene_plans(monkeypatch):
    """Each top scene's plan as its plan page shows it (plans.current): the Base's above, the others 20 m squares."""
    shown = {place: {"w": 20.0, "d": 20.0} for place in ("square", "wreck", "old_station", "campgrounds")}
    shown["base"] = BASE
    monkeypatch.setattr(plans, "current", lambda store, place: {"plan": shown[place]} if place in shown else None)
    return shown


def sites_of(plan):
    return {world["on"]: [site["place"] for site in world["sites"]] for world in plan["maps"]}


def site_in(plan, place):
    return next(site for world in plan["maps"] for site in world["sites"] if site["place"] == place)


def kept_setting(store, setting, locked=True):
    concept = environment_concept.prefilled([])
    return environment_concept.saved(store, environment_plan.world_name(), {**concept, "setting": setting}, locked,
                                     "joey")


def bearing_from(plan, still, mover):
    """(east, south) unit bearing of `mover` from `still` on the plan's map."""
    one, two = site_in(plan, still)["at"], site_in(plan, mover)["at"]
    east, south = two[0] - one[0], two[1] - one[1]
    return east / (east ** 2 + south ** 2) ** 0.5, south / (east ** 2 + south ** 2) ** 0.5


NEW = "a-new-environment"  # no world of the repository's: any environment's setting and plans


def answer_of(plan):
    """A written answer: a time for every site, and a latitude, size, outline and block it may not take."""
    return {"time": "2099-06-01T12:00:00Z", "maps": [
        {"on": world["on"], "ground": "grey dust", "sites": [
            {"place": site["place"], "time": "2099-06-01T13:00:00Z", "latitude": 10.0, "longitude": 10.0,
             "size": [120.0, 110.0, 18.0], "footprint": [[0, 0], [120, 0], [120, 110]],
             "blocks": [{"name": "a tower", "points": [[0, 0], [5, 0], [5, 5]], "tall": 30}],
             "terrain": {"spots": [[50, 0, -3.5]]}} for site in world["sites"]]} for world in plan["maps"]]}


def test_each_top_scene_stands_where_the_setting_puts_it_shaped_by_its_own_plan(store, scene_plans):
    plan = environment_plan.derived(store)
    assert sites_of(plan) == {"earth": ["square"], "moon": ["wreck", "old_station", "base"], "mars": ["campgrounds"]}
    moon = next(world for world in plan["maps"] if world["on"] == "moon")
    assert moon["radius_m"] == 1737400.0  # the Moon's true radius, never the game's 220 m ball
    apart = {(found["from"], found["to"]): found["metres"] for found in moon["distances"]}
    assert apart[("old_station", "base")] == pytest.approx(62.5, abs=0.5) and len(apart) == 3
    base = site_in(plan, "base")
    assert base["size"] == [60.0, 50.0, 15.0]  # its plan's wide and deep, its tallest thing
    assert base["footprint"] == [[-30.0, -25.0], [30.0, -25.0], [30.0, 25.0], [-30.0, 25.0]]  # about its middle
    blocks = {block["name"]: block for block in base["blocks"]}
    assert set(blocks) == {"hub", "hangar", "RADIO MAST"}  # its child scenes by place, a standing thing; no tracks
    assert blocks["hangar"]["tall"] == 15.0 and blocks["hub"]["roof"] == "dome"
    assert blocks["hub"]["points"][0] == [-10.0, -5.0]  # at its hold, in site metres
    assert (base["latitude"], base["longitude"]) == (55.0, 0.0) and base["overhead"] is None  # no scene time yet: a gap
    assert min(spot[2] for spot in base["terrain"]["spots"]) > -0.02  # 100 m on the Moon: all but flat
    assert "Base: no scene time" in plan["gaps"] and not any("place on its ground" in gap for gap in plan["gaps"])
    assert {body["body"] for body in plan["setting"]["bodies"]} == {"sun", "earth", "moon", "mars"}


def test_a_site_without_a_plan_is_a_gap(store, scene_plans):
    del scene_plans["wreck"]
    plan = environment_plan.derived(store)
    assert site_in(plan, "wreck")["size"] is None and "Wreck: no plan yet" in plan["gaps"]


def test_sites_that_would_overlap_are_moved_clear_along_their_own_bearings(store, scene_plans):
    before = environment_plan.derived(store)
    scene_plans["base"] = {"w": 110.0, "d": 110.0}  # its true plan: wider than the 57 m to the wreck
    plan = environment_plan.derived(store)
    assert not any("overlap" in gap for gap in plan["gaps"])
    base = site_in(plan, "base")
    assert (base["latitude"], base["longitude"]) == (55.0, 0.0)  # the larger stands where the physics puts it
    for mover in ("wreck", "old_station"):
        assert bearing_from(plan, "base", mover) == pytest.approx(bearing_from(before, "base", mover), abs=1e-3)
        apart = [abs(site_in(plan, mover)["at"][axis] - base["at"][axis]) for axis in (0, 1)]
        assert max(apart) == pytest.approx(55.0 + 10.0 + environment_plan.CLEAR_M, abs=0.05)  # just clear, no more
    moon = next(world for world in plan["maps"] if world["on"] == "moon")
    found = {(found["from"], found["to"]): found["metres"] for found in moon["distances"]}
    assert found[("wreck", "base")] > 75.0  # the page's distances follow


def test_a_site_the_creator_placed_himself_stays_and_two_of_his_stay_a_gap(store, scene_plans):
    scene_plans["base"] = {"w": 110.0, "d": 110.0}
    setting = environment_concept.setting_of(store)
    kept_setting(store, setting)  # his first: the physics' proposal, cleared like any
    assert not any("overlap" in gap for gap in environment_plan.derived(store)["gaps"])
    his = [{**site, "longitude": 0.0005} if site["place"] == "old_station" else site for site in setting["sites"]]
    kept_setting(store, {**setting, "sites": his})  # his own move of the old station, 34 m south of the base
    plan = environment_plan.derived(store)
    old = site_in(plan, "old_station")
    assert (old["latitude"], old["longitude"]) == (54.999165, 0.0005)
    assert site_in(plan, "base")["latitude"] != 55.0 and not any("overlap" in gap for gap in plan["gaps"])
    both = [{**site, "latitude": 55.0, "longitude": 0.0005} if site["place"] == "base" else site for site in his]
    kept_setting(store, {**setting, "sites": both})
    assert "Old station and Base overlap on Moon: move one in the physics" in environment_plan.derived(store)["gaps"]


def test_a_new_environment_on_one_plot_places_by_physics_until_plans_land_then_clears(store, monkeypatch):
    shown = {"house": {"w": 12.0, "d": 9.0}}
    monkeypatch.setattr(plans, "current", lambda store, place: {"plan": shown[place]} if place in shown else None)
    farm = {**HOUSE, "sites": [*HOUSE["sites"], {"place": "shed", "on": "meadow", "x": 8.0, "y": 0.0, "height_m": 0}]}
    environment_concept.saved(store, NEW, {**environment_concept.prefilled([]), "setting": farm}, True, "joey")
    plan = environment_plan.derived(store, NEW)
    assert site_in(plan, "shed")["at"] == [8.0, 0.0] and "Shed: no plan yet" in plan["gaps"]  # the physics' spot
    shown["shed"] = {"w": 4.0, "d": 4.0}  # its plan lands: 8 m from a 12 m house, so it would overlap
    plan = environment_plan.derived(store, NEW)
    assert site_in(plan, "house")["at"] == [0.0, 0.0]
    assert site_in(plan, "shed")["at"] == [6.0 + 2.0 + environment_plan.CLEAR_M, 0.0] and plan["gaps"] == [
        "House: no scene time", "Shed: no scene time"]
    his = {**farm, "sites": [farm["sites"][0], {**farm["sites"][1], "x": 5.0}]}  # he moves the shed himself
    environment_concept.saved(store, NEW, {**environment_concept.prefilled([]), "setting": his}, True, "joey")
    plan = environment_plan.derived(store, NEW)
    assert site_in(plan, "shed")["at"] == [5.0, 0.0]  # his spot wins; the house steps aside along its bearing
    assert site_in(plan, "house")["at"] == [5.0 - 6.0 - 2.0 - environment_plan.CLEAR_M, 0.0]


def test_sites_on_different_grounds_are_never_compared(store, monkeypatch):
    monkeypatch.setattr(plans, "current", lambda store, place: {"plan": {"w": 30.0, "d": 30.0}})
    two = {**HOUSE, "plots": [*HOUSE["plots"], {"name": "Yard", "gravity": 9.81}],
           "sites": [*HOUSE["sites"], {"place": "barn", "on": "yard", "x": 0.0, "y": 0.0, "height_m": 0}]}
    environment_concept.saved(store, NEW, {**environment_concept.prefilled([]), "setting": two}, True, "joey")
    plan = environment_plan.derived(store, NEW)
    assert site_in(plan, "house")["at"] == site_in(plan, "barn")["at"] == [0.0, 0.0]
    assert not any("overlap" in gap or "one spot" in gap for gap in plan["gaps"])


def test_sites_on_a_plot_are_moved_clear_across_it():
    sites = [{"place": "barn", "x": 0.0, "y": 0.0, "footprint": [[-20, -10], [20, -10], [20, 10], [-20, 10]]},
             {"place": "shed", "x": 0.0, "y": 15.0, "footprint": [[-2, -2], [2, -2], [2, 2], [-2, 2]]}]
    barn, shed = environment_plan.cleared(sites, None)
    assert barn == sites[0] and shed["x"] == 0.0 and shed["y"] == 10.0 + 2.0 + environment_plan.CLEAR_M


def test_sites_kilometres_apart_on_the_moon_are_that_far_on_its_map(store, scene_plans):
    setting = environment_concept.setting_of(store)
    moved = [{**site, "latitude": 55.0, "longitude": 0.1} if site["place"] == "old_station" else site
             for site in setting["sites"]]
    kept_setting(store, {**setting, "sites": moved})
    moon = next(world for world in environment_plan.derived(store)["maps"] if world["on"] == "moon")
    apart = {(found["from"], found["to"]): found["metres"] for found in moon["distances"]}
    assert apart[("old_station", "base")] == pytest.approx(1737400 * 0.1 * 0.01745329 * 0.573576, rel=1e-3)  # ~1.7 km
    old = next(site for site in moon["sites"] if site["place"] == "old_station")
    base = next(site for site in moon["sites"] if site["place"] == "base")
    assert old["at"][0] - base["at"][0] == pytest.approx(apart[("old_station", "base")], rel=1e-3)  # due east


def test_a_written_plan_keeps_the_fixed_facts_and_works_out_what_each_site_sees_overhead(store, scene_plans):
    free = environment_plan.derived(store)
    plan = environment_plan.plan_from(answer_of(free), free, store)
    assert plan["gaps"] == [] and plan["time"] == "2099-06-01T12:00:00Z"
    base, square, wreck = site_in(plan, "base"), site_in(plan, "square"), site_in(plan, "wreck")
    assert base["size"] == [60.0, 50.0, 15.0] and base["latitude"] == 55.0  # its plan's shape, the setting's place
    assert square["size"] == [20.0, 20.0, 0.0] and square["blocks"] == []  # a written size or block never stands
    earth = next(body for body in base["overhead"]["bodies"] if body["body"] == "earth")
    assert 1.75 < earth["across"] < 2.05 and earth["altitude"] > 0  # seen from the Moon's near side: about 1.9 degrees
    assert [50.0, 0.0, -3.5] in wreck["terrain"]["spots"]


def test_a_sites_shape_follows_its_scenes_plan_after_the_writing(store, scene_plans):
    free = environment_plan.derived(store)
    environment_plan.edited(store, environment_plan.plan_from(answer_of(free), free, store), "joey")
    scene_plans["square"] = {"w": 29.0, "d": 29.0, "shapes": {"FLOODLIGHT TOWER": {"tall": 18.0}}}
    assert environment_plan.site_of(store, "square")["size"] == [29.0, 29.0, 18.0]  # read again, never kept apart


def test_his_edit_is_kept_and_settled_again(store, scene_plans):
    plan = environment_plan.current(store)["plan"]
    for world in plan["maps"]:
        for site in world["sites"]:
            site.update({"time": "2099-06-01T20:00:00Z", "latitude": 1.0, "size": [1.0, 1.0, 1.0]})
    record = environment_plan.edited(store, plan, "joey")
    shown = environment_plan.current(store)
    assert shown["how"] == "edited" and shown["plan"] == record["plan"] and shown["plan"]["gaps"] == []
    square = environment_plan.site_of(store, "square")
    assert square["on"] == "earth" and square["latitude"] == 22.28  # where it stands is the setting's
    assert square["size"] == [20.0, 20.0, 0.0]  # its size its plan's
    assert square["overhead"]["lights"][0]["altitude"] < 0  # 4 in the morning in Hong Kong
    with pytest.raises(environment_plan.Refused):
        environment_plan.edited(store, {"maps": "none"}, "joey")


def test_a_daylight_concept_moves_its_sites_time_to_the_nearest_hour_its_sun_is_up(store, scene_plans, monkeypatch):
    from score.review import reading
    daylight = {"square": True, "wreck": False}
    monkeypatch.setattr(reading, "concept_light", lambda store, place: {"rows": {}, "scene": {
        "daylight": daylight[place], "unseen": False, "unseen_colour": ""}} if place in daylight else None)
    plan = environment_plan.current(store)["plan"]
    for world in plan["maps"]:
        for site in world["sites"]:
            site["time"] = "2099-06-01T20:00:00Z"  # 4 in the morning in Hong Kong
    environment_plan.edited(store, plan, "joey")
    square = environment_plan.site_of(store, "square")
    assert square["written_time"] == "2099-06-01T20:00:00Z" and square["time"] == "2099-06-01T22:00:00Z"
    assert square["overhead"]["lights"][0]["altitude"] > 0  # the Sun up, the hour before it still under
    assert environment_plan.sun_up(environment_plan.current(store)["plan"]["setting"], square, "2099-06-01T21:00:00Z") \
        is False
    wreck = environment_plan.site_of(store, "wreck")
    assert wreck["time"] == "2099-06-01T20:00:00Z" and "written_time" not in wreck  # no daylight: as written
    daylight["square"] = False  # read again as dark: back to the time written
    assert environment_plan.site_of(store, "square")["time"] == "2099-06-01T20:00:00Z"


def test_a_plan_made_under_another_concept_is_out_of_date(store, scene_plans):
    plan = environment_plan.current(store)["plan"]
    for world in plan["maps"]:
        for site in world["sites"]:
            site["time"] = "2099-06-01T20:00:00Z"
    environment_plan.edited(store, plan, "joey")
    assert environment_plan.current(store)["how"] == "edited"
    kept_setting(store, environment_concept.setting_of(store), locked=False)  # unlocked: a new version
    assert environment_plan.current(store)["how"] == "derived"


def test_a_house_on_a_plot_stands_on_flat_ground_under_its_sun_light(store, monkeypatch):
    monkeypatch.setattr(plans, "current", lambda store, place: {"plan": {"w": 12.0, "d": 9.0}})
    kept_setting(store, HOUSE)
    plan = environment_plan.derived(store)
    assert sites_of(plan) == {"meadow": ["house"]} and plan["maps"][0]["radius_m"] is None
    house = plan["maps"][0]["sites"][0]
    assert house["at"] == [0.0, 0.0] and {spot[2] for spot in house["terrain"]["spots"]} == {0.0}
    house["time"] = "2024-03-20T12:00:00Z"
    edited = environment_plan.edited(store, plan, "joey")["plan"]
    seen = edited["maps"][0]["sites"][0]["overhead"]
    assert seen["bodies"] == [] and seen["lights"][0]["altitude"] == pytest.approx(38.0, abs=0.01)


def test_the_plan_writer_writes_it_under_the_allowance_and_a_refused_answer_is_no_plan(store, monkeypatch, scene_plans):
    from score.adapters import compute
    from score.review import plan_writing
    monkeypatch.setattr(plan_writing, "call_euros", lambda found: 0.07)
    monkeypatch.setattr(compute, "books_refusal", lambda: None)
    monkeypatch.setattr(compute, "require_books", lambda what: None)
    free, asked, clears = environment_plan.derived(store), [], []

    def ask(body):
        asked.append(body)
        return {"candidates": [{"finishReason": "STOP",
                                "content": {"parts": [{"text": json.dumps(answer_of(free))}]}}]}, 2.0

    def clear(store, places, euros, node):
        clears.append((node, places))
        return compute.reading_clearance(store, places, euros, node=node)
    record = environment_plan.write(store, "the allowance", ask=ask, clear=clear)
    assert clears == [(compute.PLAN_WRITING, [f"environment-{environment_plan.world_name()}"])]
    told = asked[0]["contents"][0]["parts"][0]["text"]
    assert record["euros"] == 0.07 and '"radius m": 1737400.0' in told
    assert environment_plan.current(store)["how"] == "written" and record["plan"]["gaps"] == []
    bad = environment_plan.write(store, "the allowance", ask=lambda body: ({"candidates": []}, 1.0), clear=clear)
    assert bad["refused"] and environment_plan.current(store)["how"] == "written"


def test_no_two_sites_on_one_body_share_a_spot_unless_the_setting_puts_them_there(store, scene_plans):
    plan = environment_plan.derived(store)
    for world in plan["maps"]:
        assert all(found["metres"] >= environment_plan.SAME_SPOT for found in world["distances"]), world["on"]
    assert not any("one spot" in gap for gap in plan["gaps"])
    setting = environment_concept.setting_of(store)
    stacked = [{**site, "latitude": 55.0, "longitude": 0.0} if site["place"] == "old_station" else site
               for site in setting["sites"]]
    kept_setting(store, {**setting, "sites": stacked})  # the creator's own setting: kept, and named as a gap
    assert "Old station and Base stand on one spot of Moon" in environment_plan.derived(store)["gaps"]


# --- each scene's kept sky --------------------------------------------------------------------------------------------


NOON = "2024-03-20T12:00:00Z"


def timed(store, when):
    """The house's environment plan with its scene time set to `when` (None: none), kept as his edit."""
    kept_setting(store, HOUSE)
    plan = environment_plan.derived(store)
    plan["maps"][0]["sites"][0]["time"] = when
    return environment_plan.edited(store, plan, "joey")["plan"]


def test_a_room_keeps_the_site_and_time_of_the_top_scene_it_stands_in(store):
    plan = timed(store, NOON)
    found = scene_sky.sky_of(plan, "kitchen", "house")
    assert found["top"] == "house" and found["time"] == NOON
    assert found["site"] == {"on": "meadow", "x": 0.0, "y": 0.0, "height_m": 0.0}
    sun = overhead.seen(found["setting"], found["site"], found["time"])["lights"][0]
    assert sun["altitude"] == pytest.approx(90.0 - 52.0, abs=0.01) and sun["azimuth"] == pytest.approx(180.0, abs=0.01)
    assert scene_sky.sky_of(plan, "barn", "barn") is None  # no site on the plan


def test_keep_writes_a_timed_scene_and_takes_it_out_once_its_time_is_gone(store):
    timed(store, NOON)
    assert scene_sky.keep(store, ["house"]) == (["house"], ["house"])
    kept = json.loads((scene_sky.KEPT / "house.json").read_text())
    assert kept["place"] == kept["top"] == "house" and kept["setting"]["lights"][0]["name"] == "Sun"
    assert scene_sky.keep(store, ["house"]) == (["house"], [])  # unchanged: written once
    timed(store, None)  # a new version of the physics: the timed plan is out of date, the derived one has no time
    assert scene_sky.keep(store, ["house"]) == ([], ["house"])
    assert not (scene_sky.KEPT / "house.json").exists()


# --- the scene inventory reading: only what both readers agree on is a row --------------------------------------------


READ_ROWS = [{"id": "drum", "name": "rusted fuel drum", "noun": "drum", "kind": "generate", "count": 3,
         "size": "waist high", "metres": [0.6, 0.6, 0.9], "anchor": "ground", "where": "left",
         "region": [0, 0, 300, 350]},
        {"id": "drum_right", "name": "blue drum", "noun": "drum", "kind": "generate", "count": 1,
         "size": "waist high", "metres": [0.6, 0.6, 0.9], "anchor": "ground", "where": "right",
         "region": [0, 600, 500, 1000]},
        {"id": "mast", "name": "radio mast", "noun": "mast", "kind": "code", "count": 1, "size": "ten people tall",
         "metres": [0.4, 0.4, 18], "anchor": "ground", "where": "centre", "region": [0, 400, 1000, 600]},
        {"id": "lamp", "name": "lamp", "noun": "lamp", "kind": "code", "count": 1, "size": "a hand",
         "anchor": "on:mast", "where": "top of the mast", "region": [0, 450, 100, 550]}]


def picked_place(store, tmp_path, place="wreck"):
    """A place with one draw, picked: its sha."""
    buffer = io.BytesIO()
    Image.new("RGB", (200, 100), (90, 60, 40)).save(buffer, "PNG")
    sha = hashlib.sha256(buffer.getvalue()).hexdigest()
    (tmp_path / "draw.png").write_bytes(buffer.getvalue())
    store.put_blob(tmp_path / "draw.png", sha)
    store.write_once(f"concepts/{place}/draws/1.json", {"place": place, "sha": sha, "name": "d.png"})
    concepts.pick(store, place, sha, "joey")
    return sha


def stand_in_rows(store, place, folder):
    path = reading.picture_path(store, concepts.picked(store, place), folder)
    return [{"terrain": False, **row} for row in READ_ROWS], 0.03, 12.0, path, (200, 100)


def stand_in_boxes(jobs, folder):
    """SAM 3 finds two drums on the left (one twice), one on the right, one where no drum row stands, the mast, no
    lamp, and a crate no row names."""
    drum = [{"box": [0, 0, 20, 20]}, {"box": [1, 1, 20, 20]}, {"box": [40, 0, 60, 20]}, {"box": [150, 10, 170, 30]},
            {"box": [100, 60, 110, 70]}]
    return ({"wreck.=drum": drum, "wreck.=mast": [{"box": [90, 0, 110, 100]}], "wreck.=lamp": [],
             "wreck.~object": [{"box": [150, 50, 180, 80]}, {"box": [0, 0, 20, 20]}], "wreck.~person": []},
            {"euros": 0.12, "wall_minutes": 10.0, "machines": [{"unit_seconds": [60.0]}]})


def row(row_id, noun, region, boxes, **more):
    """An inventory row as boxed_rows gives it, for the agreement's tests."""
    return {"id": row_id, "name": more.pop("name", noun), "noun": noun, "kind": "generate", "count": 1,
            "terrain": False, "anchor": "floor", "region": region, "boxes": boxes, "box": boxes[0] if boxes else None,
            "size": [1, 1, 1], **more}


def test_a_picked_place_is_read_once_with_its_boxes_and_gaps(store, tmp_path, monkeypatch):
    sha = picked_place(store, tmp_path)
    cleared = []
    monkeypatch.setattr(compute, "READING_GEMINI_EUROS", 0.05)

    def clear(store, places, euros):
        cleared.append((places, euros))
        return compute.reading_clearance(store, places, euros)
    with pytest.raises(concepts.Refused, match="lab: no locked concept"):  # read only after its own pick
        reading.read(store, ["wreck", "lab"], "joey", clear=clear, ask=stand_in_rows, boxes=stand_in_boxes)
    assert cleared == []
    [record] = reading.read(store, ["wreck"], "joey", clear=clear, ask=stand_in_rows, boxes=stand_in_boxes)
    assert cleared == [(["wreck"], 0.05)]
    assert record["concept"] == sha and record["inventory"]["concept_pick"]["sha256"] == sha
    rows = {row["id"]: row for row in record["inventory"]["rows"]}
    assert rows["drum"]["boxes"] == [[0, 0, 20, 20], [40, 0, 60, 20]] and rows["drum"]["box"] == [0, 0, 20, 20]
    assert rows["drum"]["count"] == 2  # read as 3, found twice: the instances found count
    assert rows["drum_right"]["boxes"] == [[150, 10, 170, 30]]  # one noun asked once, each instance to its region
    assert rows["drum"]["size"] == [0.6, 0.6, 0.9] and rows["mast"]["size"] == [0.4, 0.4, 18.0]  # its metres
    assert "lamp" not in rows and record["gaps"] == []  # only Gemini named it: skipped, no gap
    assert [(item["name"], item["why"], item["box"]) for item in record["skipped"]] == [
        ("lamp", reading.ONLY_GEMINI, [90.0, 0.0, 110.0, 10.0]), ("drum", reading.ONLY_SAM, [100, 60, 110, 70]),
        ("object", reading.ONLY_SAM, [150, 50, 180, 80])]
    assert [row["id"] for row in record["answered"]] == ["drum", "drum_right", "mast", "lamp"]  # kept as answered
    assert record["euros"] == {"rows": 0.03, "boxes": 0.12, "total": 0.15}
    assert record["seconds"] == {"rows": 12.0, "boxes": 60.0, "card": 540.0}
    assert reading.reading_of(store, "wreck") == record and reading.spent(store, ["wreck", "lab"]) == 0.15
    assert reading.read(store, ["wreck"], "joey", clear=clear, ask=stand_in_rows, boxes=stand_in_boxes) == []
    assert len(cleared) == 1  # read from this pick already: nothing asked, nothing cleared
    assert reading.row_boxes(store, "wreck", "drum_right") == [[150, 10, 170, 30]]
    assert reading.row_boxes(store, "wreck", "lamp") is None and reading.row_boxes(store, "wreck", "nothing") is None
    assert reading.row_boxes(store, "lab", "drum") is None
    [again] = reading.read(store, ["wreck"], "joey", clear=clear, ask=None, boxes=stand_in_boxes, again=True)
    assert again["euros"]["rows"] == 0.0 and again["answered"] == record["answered"]  # its own rows, SAM 3 only
    assert reading.reading_of(store, "wreck") == again


def test_a_new_pick_has_no_reading_until_read(store, tmp_path):
    picked_place(store, tmp_path)
    reading.read(store, ["wreck"], "joey", ask=stand_in_rows, boxes=stand_in_boxes)
    concepts.pick(store, "wreck", None, "joey")
    assert reading.reading_of(store, "wreck") is None and reading.to_read(store, ["wreck"]) == []


def test_only_what_both_readers_agree_on_is_a_row_and_the_structure_stays():
    rows = [row("wall", "wall", None, []), row("dome", "building", None, [], inside_place=True),
            row("rock", "rock", None, [], terrain=True), row("crate", "crate", [0, 0, 100, 100], []),
            row("chair", "chair", [0, 0, 500, 500], [[0, 0, 10, 10], [20, 0, 30, 10]]),
            row("cup", "cup", None, [], anchor="on:crate")]
    kept, skipped, merged = reading.agreed(rows, [], [{"word": "machine", "box": [50, 50, 60, 60]}], (100, 100))
    assert [(item["id"], item["count"]) for item in kept] == [("wall", 1), ("dome", 1), ("rock", 1), ("chair", 2)]
    assert [(item["name"], item["why"]) for item in skipped] == [
        ("crate", reading.ONLY_GEMINI), ("cup", reading.ONLY_GEMINI), ("machine", reading.ONLY_SAM)]
    assert merged == []
    inside = [row("hangar", "building", None, []), row("ship", "spacecraft", None, [], anchor="on:hangar"),
              row("hatch", "door", None, [], anchor="on:ship"), row("cup", "cup", None, [])]
    assert reading.inside_rows(inside, {"hangar"}) == {"hangar", "ship", "hatch"}  # an inside place's own, kept


def test_a_large_single_object_only_gemini_found_is_a_row_boxed_by_its_region():
    size = (1000, 1000)
    rows = [row("core", "core", [200, 400, 600, 600], []),  # 8% of the picture, counted once: kept
            row("drums", "drum", [0, 0, 500, 500], [], count=3),  # counted three times: one region is no box
            row("pipes", "pipe", [0, 0, 500, 500], [], kind="code"),  # no object of its own
            row("cup", "cup", [0, 0, 100, 100], []),  # 1%: too small to stand on Gemini alone
            row("crate", "crate", [700, 700, 1000, 1000], []),  # its region is the bench's box: another's
            row("bench", "bench", None, [[700, 700, 1000, 1000]])]
    kept, skipped, _ = reading.agreed(rows, [], [], size)
    assert [(item["id"], item["box"], item.get("boxed_by")) for item in kept] == [
        ("core", [400.0, 200.0, 600.0, 600.0], "gemini"), ("bench", [700, 700, 1000, 1000], None)]
    assert [item["row"] for item in skipped] == ["drums", "pipes", "cup", "crate"]


def test_duplicates_go_one_box_one_row():
    size = (100, 100)
    # one instance boxed twice on one row: one box
    [only], _, _ = reading.agreed([row("chair", "chair", None, [[0, 0, 10, 10], [0, 0, 10, 11]])], [], [], size)
    assert only["boxes"] == [[0, 0, 10, 10]] and only["count"] == 1
    # one box held by two rows: the one whose region it fits
    kept, skipped, _ = reading.agreed([row("locker", "locker", [500, 500, 600, 600], [[0, 0, 10, 10]]),
                                       row("chest", "chest", [0, 0, 200, 200], [[0, 0, 10, 10], [40, 40, 50, 50]])],
                                      [], [], size)
    assert {item["id"]: item["boxes"] for item in kept} == {"chest": [[0, 0, 10, 10], [40, 40, 50, 50]]}
    assert [item["name"] for item in skipped] == ["locker"]
    # two rows of one thing: one row, the instances of both counted once, a child on the merged one moved
    kept, _, merged = reading.agreed([row("cabinet", "cabinet", None, [[0, 0, 10, 10]]),
                                      row("storage", "storage cabinets", None, [[0, 0, 10, 11], [60, 0, 70, 10]]),
                                      row("cup", "cup", None, [[62, 0, 64, 2]], anchor="on:storage")], [], [], size)
    assert [(item["id"], item["count"]) for item in kept] == [("cabinet", 2), ("cup", 1)]
    assert merged == [{"name": "storage cabinets", "row": "storage", "into": "cabinet"}]
    assert kept[1]["anchor"] == "on:cabinet"


def test_a_row_is_found_by_its_own_words_first_and_an_older_reading_is_read_again_by_sam_only(store, tmp_path):
    sha = picked_place(store, tmp_path)
    old = [{**dict(READ_ROWS[2]), "view": "v1", "box": None, "boxes": [], "size": [0.4, 0.4, 18.0],
            "size_words": "tall", "thing": "", "name": "glass greenhouse dome", "noun": "building", "id": "greenhouse",
            "terrain": False, "kind": "generate", "anchor": "ground", "where": "left", "region": [0, 0, 1000, 1000]}]
    reading.kept(store, {"place": "wreck", "concept": sha, "at": "2026-01-01T08:00:00+00:00", "by": "joey",
                         "method": 4, "size": [200, 100], "inventory": {"rows": old}, "gaps": [],
                         "euros": {"rows": 0.03, "boxes": 0.1, "total": 0.13}, "seconds": {}})
    asked = []

    def boxes(jobs, folder):
        asked.append([item["nouns"] for item in jobs[0]["rows"]])
        return {"wreck.#greenhouse": [{"box": [10, 10, 90, 90]}], "wreck.=building": []}, {
            "euros": 0.08, "wall_minutes": 5.0, "machines": []}
    never = lambda store, place, folder: pytest.fail("Gemini asked again")  # noqa: E731
    [record] = reading.read(store, ["wreck"], "joey", ask=never, boxes=boxes)
    assert asked[0][:2] == [["glass greenhouse dome"], ["building"]]  # its own words, then its noun
    assert record["inventory"]["rows"][0]["boxes"] == [[10, 10, 90, 90]] and record["from"].startswith(
        "inventory-readings/wreck/")
    assert record["euros"] == {"rows": 0.0, "boxes": 0.08, "total": 0.08} and record["answered"][0]["metres"] == [
        0.4, 0.4, 18.0]
    assert reading.spent(store, ["wreck"]) == 0.21 and reading.cost(store, record)["euros"] == 0.21


def test_rows_off_the_schema_are_refused():
    good = '{"rows": [{"id": "a", "name": "a", "noun": "a", "kind": "code", "count": 1, "size": "s", ' \
           '"anchor": "floor", "where": "w", "terrain": false, "part": "object"}]}'
    assert reading.rows_of(good)[0]["id"] == "a" and reading.rows_of(good)[0]["region"] is None
    for wrong, said in (('"count": 1', '"count": 0'), ('"kind": "code"', '"kind": "mechanic"'),
                        ('"terrain": false', '"terrain": "no"'), ('"part": "object"', '"part": "lamp"')):
        with pytest.raises(concepts.Refused, match=said.split(":")[0].strip('"')):
            reading.rows_of(good.replace(wrong, said))
    assert reading.rows_of(good.replace('"floor"', '"on:b"'))[0]["anchor"] is None  # a gap of its row, not a refusal
    assert reading.anchor_of("a", ["a", "b"]) == "on:a" and reading.region_of([10, 20, 5, 30]) is None
    assert reading.region_of([10, 20, 500, 300]) == [10, 20, 500, 300]
    unread = {"id": "a", "anchor": None, "region": None, "terrain": False, "count": 1, "size": None,
              "boxes": [[0, 0, 1, 1]]}
    assert [gap["kind"] for gap in reading.gaps([unread])] == ["size", "anchor"]
    assert reading.gaps([{"id": "g", "anchor": "ground", "terrain": True, "size": None}]) == []  # the plan sizes it
    assert reading.metres_of([4.8, 1.9, 1.5]) == [4.8, 1.9, 1.5]
    assert [reading.metres_of(wrong) for wrong in ([4.8, 1.9], [4.8, 0, 1.5], "4.8 m", [True, 1, 1])] == [None] * 4
    with pytest.raises(concepts.Refused, match="no JSON"):
        reading.rows_of("rows: none")


def test_a_cut_answer_is_refused_by_its_finish_reason_and_both_asks_answer_under_a_schema():
    cut = {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": '{"rows": [{'}]}}],
           "usageMetadata": {"candidatesTokenCount": 2400, "thoughtsTokenCount": 63136}}
    with pytest.raises(concepts.Refused, match="MAX_TOKENS .*thinking 63136"):
        reading.answer_text(cut)
    finished = {**cut, "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"rows": []}'}]}}]}
    assert reading.answer_text(finished) == '{"rows": []}'
    parts = reading.parts_schema(["drum", "mast"])["properties"]["parts"]
    assert parts["required"] == ["drum", "mast"] and parts["properties"]["mast"]["enum"] == list(reading.PARTS)


def test_a_rows_answer_off_the_schema_is_kept_with_its_cost_and_read_again(store, tmp_path):
    picked_place(store, tmp_path)
    off = lambda store, place, folder: ("row 'earth' has no valid anchor", 0.02, 9.0, None, None)  # noqa: E731
    assert reading.read(store, ["wreck"], "joey", ask=off, boxes=stand_in_boxes) == []
    [refused] = reading.readings(store, "wreck")
    assert "anchor" in refused["refused"] and reading.spent(store, ["wreck"]) == 0.02
    assert reading.reading_of(store, "wreck") is None and reading.to_read(store, ["wreck"]) == ["wreck"]


def test_a_reading_answered_before_parts_were_asked_gets_them_in_one_call_its_rows_kept(store, tmp_path):
    """reading.parted: one call a place whose reading's rows have no part, inside the reading's clearance; the parts
    kept apart and read onto its rows (with_parts), the reading itself, its boxes and plan untouched; an answer
    missing a row or off PARTS is refused and asked again next time."""
    picked_place(store, tmp_path)
    [record] = reading.read(store, ["wreck"], "joey", ask=stand_in_rows, boxes=stand_in_boxes)
    assert reading.unparted(store, ["wreck"]) == ["wreck"]  # the stand-in answered no parts
    ids = [row["id"] for row in record["inventory"]["rows"]]
    with pytest.raises(concepts.Refused, match="'mast'"):
        reading.parts_of('{"parts": {"drum": "object", "drum_right": "object"}}', ids)
    with pytest.raises(concepts.Refused, match="'mast'"):
        reading.parts_of('{"parts": {"drum": "object", "drum_right": "object", "mast": "pole"}}', ids)
    off = lambda store, place, folder: ("no valid part for 'mast'", 0.01, 3.0)  # noqa: E731
    assert reading.parted(store, ["wreck"], "joey", ask=off) == [] and reading.unparted(store, ["wreck"]) == ["wreck"]
    asked = lambda store, place, folder: (reading.parts_of(  # noqa: E731
        '{"parts": {"drum": "object", "drum_right": "object", "mast": "structure"}}', ids), 0.02, 4.0)
    [kept] = reading.parted(store, ["wreck", "lab"], "joey", ask=asked)
    assert kept["reading"] == record["at"] and kept["parts"]["mast"] == "structure"
    now = reading.reading_of(store, "wreck")
    assert [row["part"] for row in now["inventory"]["rows"]] == ["object", "object", "structure"]
    assert now["at"] == record["at"] and reading.unparted(store, ["wreck"]) == []
    assert reading.parted(store, ["wreck"], "joey", ask=None) == []  # parted already: nothing asked
    assert reading.spent(store, ["wreck"]) == round(0.15 + 0.01 + 0.02, 4)


def test_a_reading_parted_under_an_older_parts_version_is_asked_again_and_the_new_parts_read_over_it(
        store, tmp_path, monkeypatch):
    """PARTS_VERSION 2 (Batch 1 try 4): the hull, dome or tube enclosing the room the picture is inside of is its wall,
    no longer a structure modelled whole. A reading answered under an older version is asked its parts again once,
    and the newest record of today's version is read over its rows; one answered under today's is not asked."""
    picked_place(store, tmp_path)

    def parted_rows(store, place, folder):
        rows, *rest = stand_in_rows(store, place, folder)
        return [{**row, "part": "structure" if row["id"] == "mast" else "object"} for row in rows], *rest
    monkeypatch.setattr(reading, "PARTS_VERSION", 1)
    [record] = reading.read(store, ["wreck"], "joey", ask=parted_rows, boxes=stand_in_boxes)
    monkeypatch.setattr(reading, "PARTS_VERSION", 2)
    assert reading.unparted(store, ["wreck"]) == ["wreck"]
    ids = [row["id"] for row in record["inventory"]["rows"]]
    asked = lambda store, place, folder: (reading.parts_of(  # noqa: E731
        '{"parts": {"drum": "object", "drum_right": "object", "mast": "wall"}}', ids), 0.02, 4.0)
    [kept] = reading.parted(store, ["wreck"], "joey", ask=asked)
    assert kept["version"] == 2 and reading.unparted(store, ["wreck"]) == []
    rows = reading.reading_of(store, "wreck")["inventory"]["rows"]
    assert [row["part"] for row in rows] == ["object", "object", "wall"]
    assert reading.parted(store, ["wreck"], "joey", ask=None) == []  # asked under today's version: not again


def test_a_concepts_light_is_asked_once_of_its_reading_and_refused_off_its_schema(store, tmp_path):
    """reading.lit: one call a place whose reading's concept light is not read; every row named with its glow (a
    glowing one with its colour and a brightness over 0), the scene's unseen light with its colour, else refused and
    asked again next time; kept apart from the reading (concept_light), its cost in the running total."""
    picked_place(store, tmp_path)
    [record] = reading.read(store, ["wreck"], "joey", ask=stand_in_rows, boxes=stand_in_boxes)
    ids = [row["id"] for row in record["inventory"]["rows"]]
    dark = {"glows": False, "glowing": "", "colour": "", "brightness": 0}
    lamp = {"id": "mast", "glows": True, "glowing": "its lamp", "colour": "#ffd29a", "brightness": 0.5}
    scene = {"daylight": False, "unseen": True, "unseen_colour": "#8899aa"}
    answer = lambda rows, seen=scene: json.dumps({"rows": rows, "scene": seen})  # noqa: E731
    rows = [{"id": "drum", **dark}, {"id": "drum_right", **dark}, lamp]
    with pytest.raises(concepts.Refused, match="every row"):
        reading.light_of(answer(rows[:2]), ids)
    with pytest.raises(concepts.Refused, match="'mast'"):
        reading.light_of(answer(rows[:2] + [{**lamp, "colour": "warm"}]), ids)
    with pytest.raises(concepts.Refused, match="'scene'"):
        reading.light_of(answer(rows, {**scene, "unseen_colour": ""}), ids)
    assert reading.unlit(store, ["wreck"]) == ["wreck"]
    asked = lambda store, place, folder: (reading.light_of(answer(rows), ids), 0.03, 5.0)  # noqa: E731
    [kept] = reading.lit(store, ["wreck", "lab"], "joey", ask=asked)
    assert kept["reading"] == record["at"] and reading.concept_light(store, "wreck")["rows"]["mast"]["glows"]
    assert reading.unlit(store, ["wreck"]) == [] and reading.lit(store, ["wreck"], "joey", ask=None) == []
    assert reading.spent(store, ["wreck"]) == round(0.15 + 0.03, 4)
    schema = reading.light_schema(ids)["properties"]
    assert schema["rows"]["items"]["properties"]["id"]["enum"] == ids


# --- reading fixes: a part of another row's thing merged into it, free ------------------------------------------------


SIZE = (1000, 1000)


FRIDGE = row("fridge", "fridge", [200, 810, 360, 870], [[810, 200, 870, 360]], part="object")


DOOR = row("door", "door", [210, 820, 340, 870], [[825, 220, 860, 330]], part="object")


HANDLE = row("handle", "handle", [250, 830, 260, 840], [[830, 250, 840, 260]], anchor="on:door", part="object")


def test_only_a_row_both_readers_put_inside_another_rows_thing_is_a_part_of_it():
    rows = [FRIDGE, DOOR,
            row("chair", "chair", [500, 500, 700, 700], [[500, 500, 700, 700]]),  # a person sits in it: 60% inside
            row("person", "person", [480, 500, 680, 700], [[500, 480, 700, 600]]),
            row("desk", "desk", [0, 0, 100, 100], [[0, 0, 100, 100]]),
            row("laptop", "laptop", [0, 0, 90, 90], [[10, 10, 50, 50]], anchor="on:desk")]  # stands on it: its own
    kept, merged = reading_fixes.parts_apart(rows, SIZE)
    assert [item["id"] for item in kept] == ["fridge", "chair", "person", "desk", "laptop"]
    assert merged == [{"name": "door", "row": "door", "into": "fridge"}]


def test_a_reading_holding_a_part_is_fixed_once_free_its_children_moved(store, tmp_path):
    sha = picked_place(store, tmp_path)
    reading.kept(store, {"place": "wreck", "concept": sha, "at": "2026-01-01T08:00:00+00:00", "by": "joey",
                         "method": reading.METHOD, "parts_version": reading.PARTS_VERSION, "size": list(SIZE),
                         "inventory": {"rows": [FRIDGE, DOOR, HANDLE]}, "gaps": [], "skipped": [], "merged": [],
                         "euros": {"rows": 0.03, "boxes": 0.1, "total": 0.13}, "seconds": {}})
    assert reading_fixes.to_fix(store, ["wreck"]) == ["wreck"]
    [record] = reading_fixes.fix(store, ["wreck"], "test")
    assert reading.reading_of(store, "wreck") == record and record["from"].startswith("inventory-readings/wreck/")
    assert [(item["id"], item["anchor"]) for item in record["inventory"]["rows"]] == [
        ("fridge", "floor"), ("handle", "on:fridge")]
    assert record["merged"] == [{"name": "door", "row": "door", "into": "fridge"}]
    assert record["euros"]["total"] == 0.0 and record["parts_version"] == reading.PARTS_VERSION
    assert reading_fixes.to_fix(store, ["wreck"]) == [] and reading_fixes.fix(store, ["wreck"], "test") == []
    assert reading_fixes.said([record]) == "readings fixed: wreck" and reading_fixes.said([]) == "readings: none to fix"


# --- the plan review: his edits win, a locked room moves only by his edit ---------------------------------------------


PICK = "a" * 64


PLAN_ROWS = {"shed": [{"id": "bench", "name": "a bench", "anchor": "floor", "size": [2.0, 0.6, 0.9], "count": 1,
                  "at": [{"x": 0.0, "z": -1.0, "facing": 0}]},
                 {"id": "crate", "name": "a crate", "anchor": "floor", "size": [0.5, 0.5, 0.5], "count": 2, "at": []},
                 {"id": "vice", "name": "a vice", "anchor": "bench", "size": [0.2, 0.2, 0.2], "count": 1},
                 {"id": "lamp", "name": "a wall lamp", "anchor": "wall", "size": [0.3, 0.2, 0.3], "count": 1}],
        "yard": []}


@pytest.fixture
def data(tmp_path, monkeypatch, store):
    """A holder `yard` holding `shed` (data/places/within.json, the one data file a design reads here), the plans
    kept in the test's own folders, and the pick's picture in the store."""
    folder = tmp_path / "data"
    (folder / "places").mkdir(parents=True)
    (folder / "places/within.json").write_text(json.dumps({"within": {"shed": {"within": "yard"}}, "shells": {}}))
    monkeypatch.setattr(plans, "DATA", folder)
    monkeypatch.setattr(plans, "KEPT", tmp_path / "kept")
    monkeypatch.setattr(plans, "KEPT_INVENTORY", tmp_path / "kept-inventory")
    monkeypatch.setattr(plans, "KEPT_CONCEPT", tmp_path / "kept-concepts")
    picture = tmp_path / "pick.png"
    Image.new("RGB", (64, 40), (40, 90, 160)).save(picture)
    store.put_blob(picture, PICK)
    return folder


def read(store, place, rows, at=None, size=None):
    """A reading of the place's pick by today's method: its scene inventory (`rows`), its picture `size` in pixels
    where given (a row's boxes are pixels of it)."""
    from score.review import reading
    reading.kept(store, {"place": place, "concept": PICK, "at": at or concepts.now(), "method": reading.METHOD,
                         **({"size": size} if size else {}),
                         "inventory": {"concept_pick": {"sha256": PICK}, "rows": rows}})


def picked(store, place, rows=None, size=None):
    """The place's draw picked and read: `rows` its reading's rows, else PLAN_ROWS' (none for a place it does not
    name)."""
    store.write_once(f"concepts/{place}/draws/1.json", {"place": place, "sha": PICK, "at": "2026-10-21T00:00"})
    concepts.pick(store, place, PICK, "joey")
    read(store, place, PLAN_ROWS.get(place, []) if rows is None else rows, at="2026-10-21T00:01", size=size)


def written(store, place, plan):
    """The place's plan as plan_writing keeps a writing of its reading."""
    from score.review import plan_writing
    plan_writing.kept(store, {"place": place, "concept": PICK, "reading": plan_writing.reading_at(store, place),
                              "method": plan_writing.METHOD, "by": "test", "at": concepts.now(), "plan": plan})


def test_no_plan_before_the_inventory_counts_then_each_item_tied_to_its_row(store, data):
    assert plans.current(store, "shed") is None  # not picked: no inventory counts
    picked(store, "yard")  # the plan above lays the shed's room
    picked(store, "shed")
    shown = plans.current(store, "shed")
    plan = shown["plan"]
    # no filed plan (retired 2026-10-21): a bare one in its room on the plan above, 6 x 6 m with no plan of its own
    assert shown["how"] == "derived" and (plan["w"], plan["d"]) == (6.0, 6.0) and plan["doors"] == []
    names = {item[0]: item for item in plan["items"]}
    assert plan["rows"]["BENCH 1"] == ["bench", "vice"] and plan["rows"]["CRATE 2"] == ["crate"]
    assert names["BENCH 1"][1:5] == [2.0, 1.7, 2.0, 0.6]  # laid at its spot: its middle 1 m south of the room's
    assert plan["rows"][plan_checks.WALLS_ITEM] == ["lamp"]
    assert plan["people"] == [[3.0, 3.0]]
    assert plan["elements"][0] == {"element": "a bench", "rows": ["bench"]}


def test_his_edit_is_kept_as_his_own_and_checked(store, data):
    picked(store, "yard")
    picked(store, "shed")
    written(store, "shed", {**plans.current(store, "shed")["plan"], "doors": [["S", 2.0, 0.9, "DOOR to the yard"]]})
    plan = plans.current(store, "shed")["plan"]
    plan["items"][0][1] = 0.5
    plan["doors"][0] = ["E", 1.0, 0.9, "moved"]
    plans.edited(store, "shed", plan, "joey")
    shown = plans.current(store, "shed")
    assert shown["how"] == "edited" and shown["plan"]["items"][0][1] == 0.5
    assert shown["plan"]["doors"][0] == ["E", 1.0, 0.9, "DOOR to the yard"]  # moved, its words kept
    with pytest.raises(plans.Refused, match="keeps its doors"):
        plans.edited(store, "shed", {**plan, "doors": []}, "joey")
    with pytest.raises(plans.Refused, match="not a number"):
        plans.edited(store, "shed", {**plan, "items": [["X", "far", 0, 1, 1, None, "item"]]}, "joey")
    concepts.pick(store, "shed", None, "joey")  # unlocked: no plan counts
    assert plans.current(store, "shed") is None


def test_an_inside_place_waits_for_the_holders_plan_then_gets_its_shape_and_its_row(store, data):
    assert plans.holder_of(store, "shed") is None and not plans.made(store, "yard")
    plans.name_inside(store, "yard", ["Tool Hut"], "joey")
    picked(store, "yard")  # the pick is the approval: its inventory read, its plan is made
    holds = plans.current(store, "yard")["plan"]["holds"]
    assert [hold["place"] for hold in holds] == ["shed", "tool_hut"] and holds[0]["w"] == 6.0  # no plan of its own
    assert plans.made(store, "yard")  # its plan shown is its plan made
    _, path = plans.shape_sent(store, "shed")[0]
    assert Image.open(path).size[0] > 100
    assert plans.holder_of(store, "shed") == {"holder": "yard", "row": None, "box": None, "view": None,
                                              "outline": [0.3, 0.3, 6.0, 6.0]}  # the yard's own ground holds it


def test_his_inside_places_and_rows_redo_what_follows(store, data):
    rows = [{"id": "barn", "name": "a barn", "anchor": "floor", "size": [8.0, 6.0, 5.0], "count": 1, "at": [],
             "box": [10, 20, 300, 200], "view": "v1"}]
    picked(store, "yard", rows)
    plan = plans.current(store, "yard")["plan"]
    plan["holds"] = [{**plan["holds"][0], "place": "loft", "row": "barn", "x": 2.0}]
    plans.edited(store, "yard", plan, "joey")
    assert plans.tree(store)["within"].get("loft") == "yard" and "shed" not in plans.tree(store)["within"]
    # the concept review reads the same: the loft's draw waits on the yard, its holder now
    assert concepts.above("loft", store) == "yard" and concepts.inside_of("yard", store) == ["loft"]
    assert concepts.step_refusal(store, "loft", "draw") is None  # the yard read and planned: the loft may be drawn
    assert plans.holder_of(store, "loft") == {"holder": "yard", "row": "barn", "box": [10, 20, 300, 200],
                                              "view": "v1", "outline": [2.0, 0.3, 6.0, 6.0]}
    with pytest.raises(plans.Refused, match="no inventory row"):
        plans.edited(store, "yard", {**plan, "holds": [{**plan["holds"][0], "row": "silo"}]}, "joey")


def test_a_room_adjoining_rooms_a_row_holds_is_held_by_that_row_over_one_it_only_overlaps(store, data):
    """Owner, 2026-10-21: the docking airlock just behind the engine room, its box over the crane, "is still part of
    the ship"; a room its row names (the hub's central_hub) or on its own floor keeps its own."""
    rows = [{"id": row, "name": row, "anchor": "floor", "size": [8.0, 6.0, 5.0], "count": 1, "at": []}
            for row in ("ship", "crane", "loft")]
    picked(store, "yard", rows)
    plan = plans.current(store, "yard")["plan"]
    room = {"x": 2.0, "y": 2.0, "w": 4.0, "d": 3.0}
    plan["holds"] = [{**room, "place": "shed", "row": "ship"}, {**room, "place": "cabin", "row": "ship", "y": -1.0},
                     {**room, "place": "dock", "row": "crane", "x": 3.0, "y": 5.15, "w": 2.0},  # 0.15 m behind it
                     {**room, "place": "loft", "row": "loft", "x": 6.1},  # beside it, its own row by its name
                     {**room, "place": "hut", "row": None, "y": 5.0, "x": 0.0, "w": 1.0}]
    held = {hold["place"]: hold["row"] for hold in plans.edited(store, "yard", plan, "joey")["plan"]["holds"]}
    assert held == {"shed": "ship", "cabin": "ship", "dock": "ship", "loft": "loft", "hut": None}


def test_a_room_changed_on_the_holders_plan_puts_draws_on_it_out_of_date_and_flags_its_pick(store, data, monkeypatch):
    """Owner, 2026-10-21: a merge, move or resize of a room on the plan above means the room is drawn again; a place
    the plan no longer lays out is removed, never an outside place, and has no stage line."""
    monkeypatch.setattr(concepts, "step_refusal", lambda store, place, step: None)
    picked(store, "yard")
    plan = plans.current(store, "yard")["plan"]
    drawn = {"place": "shed", "sha": PICK, "at": concepts.now(), "room": plans.room_of(store, "shed")}
    store.write_once("concepts/shed/draws/1.json", drawn)
    concepts.pick(store, "shed", PICK, "joey")
    store.write_once("concepts/shed/draws/2.json", {"place": "shed", "sha": "c" * 64, "base": PICK,
                                                    "at": concepts.now()})  # a Redraw with notes on it
    store.write_once("concepts/shed/draws/0.json", {"place": "shed", "sha": "d" * 64,
                                                    "at": "2026-10-01T00:00"})  # from before rooms were recorded
    assert drawn["room"]["w"] == 6.0 and not concepts.plan_changed(store, "shed")
    assert plans.moved_draws(store, "shed") == set()
    plans.edited(store, "yard", {**plan, "holds": [{**plan["holds"][0], "w": 8.0}]}, "joey")  # resized
    assert concepts.plan_changed(store, "shed")
    assert plans.moved_draws(store, "shed") == {PICK, "c" * 64, "d" * 64}  # the older one: a plan above made since
    assert plans.removed(store, plans.within_file()[0]) == []
    read(store, "shed", PLAN_ROWS["shed"])
    plans.edited(store, "shed", plans.current(store, "shed")["plan"], "joey")  # its design done: a place of the build
    world = graph.Environment("world1", 3, {"data": str(data)})
    assert stages.places(world, store) == ["yard", "shed"]  # the scene tree's order: the parent scene first
    plans.edited(store, "yard", {**plan, "holds": []}, "joey")  # merged away
    assert plans.removed(store, plans.within_file()[0]) == ["shed"]
    assert stages.places(world, store) == ["yard"]  # the build follows him: no stage line for it


def test_rewriting_a_parent_keeps_its_locked_childrens_rooms_and_only_his_edit_moves_them_or_hides(
        store, data, monkeypatch):
    """Owner, 2026-10-21: "get my concepts back ... i had alr locked them": a plan written again (its inventory read
    again) never moves a locked scene's room nor shows over his own edit; only his edit moves the room."""
    from score.review import plan_writing
    monkeypatch.setattr(concepts, "step_refusal", lambda store, place, step: None)
    picked(store, "yard")
    room = plans.room_of(store, "shed")
    store.write_once("concepts/shed/draws/1.json", {"place": "shed", "sha": PICK, "at": concepts.now(), "room": room})
    concepts.pick(store, "shed", PICK, "joey")
    plan = plans.current(store, "yard")["plan"]
    moved = {**plan, "holds": [{**room, "x": room["x"] + 3.0, "w": 9.0}]}
    plan_writing.kept(store, {"place": "yard", "concept": PICK, "reading": plan_writing.reading_at(store, "yard"),
                              "method": plan_writing.METHOD, "by": "test", "at": concepts.now(), "plan": moved})
    assert plans.current(store, "yard")["how"] == "written" and plans.room_of(store, "shed") == room
    assert not concepts.plan_changed(store, "shed")
    store.write_once("concepts/shed/draws/0.json", {"place": "shed", "sha": "d" * 64, "at": "2026-10-01T00:00"})
    concepts.pick(store, "shed", "d" * 64, "joey")  # locked on a draw from before rooms were recorded
    assert not concepts.plan_changed(store, "shed")  # a writing since moves no locked room
    plans.edited(store, "yard", {**plan, "holds": [{**room, "w": 6.0}]}, "joey")
    assert concepts.plan_changed(store, "shed")  # his edit does
    plan_writing.kept(store, {"place": "yard", "concept": PICK, "reading": plan_writing.reading_at(store, "yard"),
                              "method": plan_writing.METHOD, "by": "test", "at": concepts.now(), "plan": moved})
    shown = plans.current(store, "yard")
    assert shown["how"] == "edited" and shown["plan"]["holds"][0]["w"] == 6.0  # his edit over a newer writing
    assert shown["plan"]["gaps"][-1]["kind"] == "edited"


def test_a_scene_he_added_in_the_app_is_a_place_once_its_design_is_done(store, data, tmp_path):
    """A child scene he added on a plan (no file of it in the data) is a scene in design, no place, until its concept
    is locked, its inventory read and its plan written or edited; then the build lists it and its plan row reads its
    kept plan, with no hand edit (owner, 2026-10-21). Every scene is one: no plan is filed in the data (2026-10-21)."""
    picked(store, "yard")
    plan = plans.current(store, "yard")["plan"]
    plans.edited(store, "yard", {**plan, "holds": [*plan["holds"], {**plan["holds"][0], "place": "hut", "x": 0.0}]},
                 "joey")
    world = graph.Environment("world1", 3, {"data": str(data)})
    assert stages.places(world, store) == ["yard"]  # the shed and the hut in design: their concepts not locked
    picked(store, "hut")
    shown = plans.current(store, "hut")
    assert shown["how"] == "derived" and stages.places(world, store) == ["yard"]  # its plan not written
    assert plans.keep(store, ["hut"]) == ([], []) and not stages.plan_written("hut")
    plans.edited(store, "hut", shown["plan"], "joey")
    assert stages.places(world, store) == ["yard", "hut"]
    assert plans.keep(store, ["hut"]) == (["hut"], []) and (tmp_path / "kept/hut.json").is_file()  # kept at his edit
    assert stages.plan_written("hut") and stages.PLAN.files("hut")["plan"] == "{home}/design/plans/{place}.json"


def test_a_parent_scene_with_no_data_of_its_own_is_a_place_once_its_design_is_done(store, data, tmp_path):
    """A parent scene holding others with no file of its own in the data (the Moon base, a shell) is a place of the
    batch once its design is done, listed before the scenes it holds, and the sync keeps its plan where the plan stage
    and the scene tree read it."""
    (data / "places/within.json").write_text(json.dumps({"within": {"shed": {"within": "yard"},
                                                                    "yard": {"within": "farm"}},
                                                         "shells": {"farm": {"name": "Farm"}}}))
    world = graph.Environment("world1", 3, {"data": str(data)})
    picked(store, "yard")
    plans.edited(store, "yard", plans.current(store, "yard")["plan"], "joey")
    assert stages.places(world, store) == ["yard"]  # the farm in design: no place yet
    picked(store, "farm")
    shown = plans.current(store, "farm")
    assert shown["how"] == "derived" and [hold["place"] for hold in shown["plan"]["holds"]] == ["yard"]
    assert stages.places(world, store) == ["yard"]  # its plan not written
    plans.edited(store, "farm", shown["plan"], "joey")
    assert stages.places(world, store) == ["farm", "yard"]  # the parent scene first
    assert plans.keep(store, ["farm"]) == (["farm"], []) and (tmp_path / "kept/farm.json").is_file()  # at his edit


def test_overlapped_rooms_are_one_shared_room_and_a_box_dropped_in_a_room_a_thing_in_it(store, data):
    """Owner, 2026-10-21: two rooms overlapped on the plan above are one shared room named from both; the add-scene
    box dropped inside a room is a thing kept with that room, no scene of its own, named with its spot in the room's
    draw wording; either changes the room, so its draws are drawn again. A room he left alone stays as it was."""
    plans.name_inside(store, "yard", ["tool hut"], "joey")
    picked(store, "yard")
    plan = plans.current(store, "yard")["plan"]
    shed = plans.room_of(store, "shed")
    plans.edited(store, "yard", plan, "joey")  # kept as laid: no key added to a room he did not touch
    assert plans.room_of(store, "shed") == shed
    store.write_once("concepts/shed/draws/1.json", {"place": "shed", "sha": PICK, "at": concepts.now(), "room": shed})
    merged = {**shed, "w": 8.0, "d": 3.0, "name": "Shed and tool hut",
              "things": [{"name": "workbench", "x": 3.0, "y": 1.0, "w": 2.0, "d": 1.0},
                         {"name": "lathe", "x": 6.5, "y": 0.2, "w": 1.0, "d": 0.6}]}
    plans.edited(store, "yard", {**plan, "holds": [merged]}, "joey")
    assert plans.tree(store)["within"] == {"shed": "yard"}  # the tool hut is no scene any more
    assert plans.room_of(store, "shed")["things"][0] == {"name": "workbench", "x": 3.0, "y": 1.0, "w": 2.0, "d": 1.0}
    assert plans.moved_draws(store, "shed") == {PICK}
    assert concepts.room_name(store, "shed") == "shed and tool hut"
    assert concepts.thing_words(store, "shed") == ("Standing in it: workbench in the middle; lathe in the north-east "
                                                   "corner.")
    assert plans.room_edits(plan, plans.current(store, "yard")["plan"])[0] == \
        "made the scene shed one shared room called Shed and tool hut"
    with pytest.raises(plans.Refused, match="has no name"):
        plans.edited(store, "yard", {**plan, "holds": [{**merged, "things": [{"x": 1, "y": 1, "w": 1, "d": 1}]}]},
                     "joey")


def test_a_reading_of_the_pick_is_the_inventory_its_rows_on_their_parents_and_its_boxes_the_holders(store, data):
    store.write_once("concepts/yard/draws/1.json", {"place": "yard", "sha": PICK, "at": "2026-10-21T00:00"})
    concepts.pick(store, "yard", PICK, "joey")  # picked, not read yet: no inventory, no plan
    assert plans.current(store, "yard") is None and not plans.made(store, "yard")
    rows = [{"id": "barn", "name": "a barn", "kind": "generate", "anchor": "ground", "size": "two storeys",
             "count": 1, "boxes": [[5, 6, 70, 80], [1, 1, 2, 2]]},
            {"id": "bell", "name": "a bell", "kind": "generate", "anchor": "on:barn", "size": "small", "count": 1}]
    read(store, "yard", rows)
    plan = plans.current(store, "yard")["plan"]
    assert plan["rows"]["BARN 1"] == ["barn", "bell"] and plan["items"][0][3:5] == [1.0, 1.0]  # sizes in words: 1 m
    plan["holds"][0]["row"] = "barn"
    plans.edited(store, "yard", plan, "joey")
    assert plans.holder_of(store, "shed")["box"] == [5, 6, 70, 80]  # its surest SAM box
    assert plans.made(store, "yard") and concepts.holding_row(store, "shed") == "barn"  # the concept review's


def test_items_are_sized_by_their_reading_and_ordered_by_their_boxes_and_what_has_no_size_or_row_is_a_gap(store, data):
    rows = [{"id": "barn", "name": "a barn", "anchor": "ground", "size": [3.0, 2.0, 5.0], "size_words": "two storeys",
             "count": 1, "boxes": [[10, 10, 60, 35]]},
            {"id": "cart", "name": "a cart", "anchor": "ground", "size": [1.5, 1.0, 1.2],
             "size_words": "two strides long", "count": 1, "boxes": []},
            {"id": "rock", "name": "a rock", "anchor": "ground", "size": None, "size_words": "waist high",
             "count": 1, "boxes": [[0, 40, 50, 50]]}]
    picked(store, "yard", rows, size=[100, 50])
    plan = plans.current(store, "yard")["plan"]
    items = {item[0]: item for item in plan["items"]}
    assert items["ROCK 1"][1:3] == [0.3, 0.3] and items["BARN 1"][1:5] == [1.6, 0.3, 3.0, 2.0]  # its metres, laid
    # along the walls after the rock, whose box stands left of its: a box orders, it is never projected (owner,
    # 2026-10-21)
    assert items["CART 1"][3:5] == [1.5, 1.0]  # its metres, laid along the walls: no box
    assert items["ROCK 1"][3:5] == [1.0, 1.0]  # a box but no metres: SAM 3 gives where, never size
    assert [gap["words"] for gap in plan["gaps"]] == ["Rock 1: no size"]
    plan["items"] = [[*item[:3], 2.0, 2.0, *item[5:]] if item[0] == "ROCK 1" else item for item in plan["items"]]
    plans.edited(store, "yard", plan, "joey")  # he sized the rock: its gap is gone
    assert plans.current(store, "yard")["plan"]["gaps"] == []


def test_the_plan_stage_reads_his_plan_and_drops_it_once_the_pick_goes(store, data, tmp_path):
    picked(store, "yard")
    picked(store, "shed")
    written(store, "shed", plans.current(store, "shed")["plan"])  # its plan written: its design done
    assert plans.keep(store, ["shed", "yard"]) == (["shed"], ["shed"])  # the yard's plan only derived: none kept
    kept = tmp_path / "kept/shed.json"
    kept_plan = json.loads(kept.read_text())
    assert kept_plan == {**plans.current(store, "shed")["plan"], "concept": {**kept_plan["concept"], "pick": PICK}}
    assert kept_plan["concept"]["picture"] == "{home}/design/concepts/shed.png"  # the picked concept, its input
    assert (tmp_path / "kept-concepts/shed.png").read_bytes() == store.objects.read_bytes(f"blobs/{PICK}")
    assert json.loads((tmp_path / "kept-inventory/shed.json").read_text())["rows"][0]["id"] == "bench"
    plan = plans.current(store, "shed")["plan"]
    plan["people"] = [[3.0, 2.0]]
    plans.edited(store, "shed", plan, "joey")
    assert json.loads(kept.read_text())["people"] == [[3.0, 2.0]]  # his edit, at once
    concepts.pick(store, "shed", None, "joey")
    assert plans.keep(store, ["shed"]) == ([], ["shed"]) and not kept.exists()
    assert not (tmp_path / "kept-inventory/shed.json").exists()
    assert not (tmp_path / "kept-concepts/shed.png").exists()


def test_a_correction_runs_only_inside_his_yes_and_keeps_the_answer_as_his_edit(store, data, monkeypatch):
    picked(store, "yard")
    picked(store, "shed")
    asked = []

    def gemini(question, pictures):
        asked.append((question, len(pictures)))
        return 'Here: {"people": [[1.0, 1.0]]}'

    request = {"marks": [{"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "note": "stand by the bench"}], "note": ""}
    with pytest.raises(compute.Refused):
        plans.revised(store, "shed", request, "joey", reviser=gemini)
    monkeypatch.setattr(plans, "revise_euros", lambda: 0.05)

    def run(argv, env, **named):
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        record = plans.revised(store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1], reviser=gemini)
        return subprocess.CompletedProcess(argv, 0, json.dumps({"how": record["how"]}) + "\n", "")

    assert web.plan_revise(store, "shed", request, 0.05, "joey", run=run) == {"how": "revised"}
    assert asked[0][1] == 2 and "stand by the bench" in asked[0][0]
    assert plans.current(store, "shed")["plan"]["people"] == [[1.0, 1.0]]
    with pytest.raises(review.Refused, match="not today's measured price"):
        web.plan_revise(store, "shed", request, 0.04, "joey", run=run)


def test_a_correction_with_no_note_sends_his_kept_edits_and_with_none_is_refused_before_any_spend(
        store, data, monkeypatch):
    picked(store, "yard")
    picked(store, "shed")
    monkeypatch.setattr(plans, "revise_euros", lambda: 0.05)
    bare = {"marks": [], "context_marks": [], "note": ""}
    with pytest.raises(plans.Refused, match="no note to correct the plan by"):
        web.plan_revise(store, "shed", bare, 0.05, "joey", run=None)  # nothing changed: no yes written
    assert not list((store.cache / plans.AREA / "asked").glob("*.json"))
    plan = plans.current(store, "shed")["plan"]
    plan["items"] = [[item[0], item[1] + 1.0, *item[2:]] for item in plan["items"][:1]] + plan["items"][1:]
    plans.edited(store, "shed", plan, "joey")
    note = plans.note_of(store, "shed", bare)
    assert note.startswith("I changed the plan by hand: item ") and plan["items"][0][0] in note
    assert plans.note_of(store, "shed", {**bare, "note": "wider door"}) == "wider door"


def test_a_holder_with_no_outline_of_its_own_gets_one_round_its_inside_places_before_its_items(store, data):
    from score.review import reading
    # a holder with no outline of its own (the base): the shed, 6 x 6 m with no plan of its own, is inside it
    assert plans.outline_from_inside(store, "yard") == (6.6, 6.6)
    assert reading.outline_of(store, "yard") == (6.6, 6.6)  # the reading sizes its rows against it
    assert reading.outline_of(store, "nowhere") is None
    picked(store, "yard")
    assert plans.current(store, "yard")["plan"]["w"] == 6.6


def test_a_spot_takes_its_child_scenes_own_plan_size_centred_where_it_sat_and_says_so(store, data):
    """Owner, 2026-10-25 ("the framework should be able to solve [it] agnosticly"): a child scene's own plan is drawn
    from its own concept at its own scale, the holder's spot says where it sits; they agree before any paid work."""
    rows = [{"id": "barn", "name": "a barn", "anchor": "floor", "size": [8.0, 6.0, 5.0], "count": 1, "at": []},
            {"id": "cart", "name": "a cart", "anchor": "floor", "size": [1.0, 1.0, 1.0], "count": 1, "at": []}]
    picked(store, "yard", rows)
    plan = plans.current(store, "yard")["plan"]
    plan["w"] = plan["d"] = 30.0
    plan["holds"] = [{"place": "shed", "row": None, "x": 10.0, "y": 10.0, "w": 6.0, "d": 6.0}]
    plan["items"] = [["CART 1", 13.0, 7.5, 1.0, 1.0, None, "item"]]  # clear of the spot, not of the shed's own size
    plans.edited(store, "yard", plan, "joey")
    held = plans.current(store, "yard")["plan"]
    assert held["holds"][0]["w"] == 6.0 and not [gap for gap in held["gaps"] if gap["kind"] == "held"]
    store.write_once("concepts/shed/draws/0.json", {"place": "shed", "sha": "b" * 64, "at": "2026-10-20T00:00",
                                                    "room": held["holds"][0]})  # drawn on the spot as it was
    picked(store, "shed")
    written(store, "shed", {**plans.current(store, "shed")["plan"], "w": 4.0, "d": 10.0})
    fitted = plans.current(store, "yard")["plan"]
    assert {key: fitted["holds"][0][key] for key in "xywd"} == {"x": 11.0, "y": 8.0, "w": 4.0, "d": 10.0}
    assert fitted["items"][0][1:5] == [13.0, 7.0, 1.0, 1.0]  # pushed north off the shed, the shortest way
    assert [gap["item"] for gap in fitted["gaps"] if gap["kind"] == "held"] == ["shed", "CART 1"]
    assert plans.moved_draws(store, "shed") == set()  # its own size is no move of its room


# --- plan writing and its free checks: each failure a named gap -------------------------------------------------------


ANSWER = {
    "outline": [[0, 0], [4, 0], [4, 3], [0, 3]],
    "walls": [{"from": [0, 0], "to": [4, 0], "thick": 0.2, "tall": 2.5}, {"from": [4, 0], "to": [4, 3], "thick": 0.2},
              {"from": [4, 3], "to": [0, 3], "thick": 0.2}, {"from": [0, 3], "to": [0, 0], "thick": 0.2},
              {"from": "nowhere"}],
    "openings": [{"kind": "door", "at": [2.0, 3.0], "wide": 0.9, "angle": 0, "swing": "left", "head": 2.1,
                  "to": "yard"}],
    "levels": [{"name": "floor", "height": 0, "points": [[0, 0], [4, 0], [4, 3], [0, 3]]}],
    "roofs": [{"kind": "pitched", "points": [[0, 0], [4, 0], [4, 3], [0, 3]], "eave": 2.5, "top": 3.4}],
    "terrain": {},
    "structure": ["lamp_nowhere"],
    "items": [{"row": "bench", "x": 2.0, "y": 0.6, "wide": 2.0, "deep": 0.6, "shape": "rect", "facing": "S",
               "tall": 0.9, "base": 0},
              {"row": "crate", "x": 2.2, "y": 0.7, "wide": 0.5, "deep": 0.5, "shape": "circle", "tall": 0.5},
              {"row": "lamp", "x": 0.2, "y": 1.5, "wide": 0.3, "deep": 0.2, "tall": 0.3, "base": 2.0},
              {"row": "ghost", "x": 1, "y": 1, "wide": 1, "deep": 1}],
    "people": [[1.0, 2.0]],
    "section": {"y": 1.5},
}


def response(answer):
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(answer)}]}}],
            "usageMetadata": {}}


UNITS = 100  # drawing units a metre in the stand-in answer: the rows' metres measure it back


@pytest.fixture
def gemini(monkeypatch):
    asked, drawn = [], []
    monkeypatch.setattr(plan_writing, "call_euros", lambda found: 0.04)
    monkeypatch.setattr(compute, "books_refusal", lambda: None)

    def drawing(wording, pictures, frame):
        drawn.append(wording)
        buffer = io.BytesIO()
        Image.new("RGB", (500, 400), (255, 255, 255)).save(buffer, "PNG")
        return buffer.getvalue(), 0.12, 1.0
    monkeypatch.setattr(plan_drawing, "called", drawing)

    def ask(body):
        asked.append(body)
        return response(plan_writing.metred(ANSWER, (UNITS, UNITS), (0, 0))), 1.0
    ask.drawn = drawn
    return asked, ask


def cleared(cleared_for):
    def clear(store, places, euros, node):
        cleared_for.append((node, places, euros))
        return compute.reading_clearance(store, places, euros, node=node)
    return clear


def test_the_answer_is_a_plan_of_the_stage_tables_schema_and_each_failed_check_a_named_gap(store, data, gemini):
    asked, ask = gemini
    picked(store, "shed")
    assert plans.current(store, "shed")["how"] == "derived"
    clears = []
    price = plan_writing.price(store)
    record, = plan_writing.write(store, ["shed"], "the allowance", clear=cleared(clears), ask=ask)
    assert clears == [(compute.PLAN_WRITING, ["shed"], price)] and record["euros"] == 0.04
    assert record["drawing_euros"] == 0.12 and record["measured"] == {"metres a unit": [0.01, 0.01],
                                                                      "by": "its rows' metres"}
    assert "a bench, 2 a crate" in ask.drawn[0] and len(asked[0]["contents"][0]["parts"]) == 3
    assert plan_writing.spent(store, ["shed"]) == 0.16 and plan_writing.price(store) == 0.16
    plan = plans.current(store, "shed")["plan"]
    assert plans.current(store, "shed")["how"] == "written"
    items = {item[0]: item for item in plan["items"]}
    assert items["BENCH 1"] == ["BENCH 1", 1.0, 0.3, 2.0, 0.6, "S", "item"]
    assert plan["rows"]["BENCH 1"] == ["bench", "vice"]  # the vice rides on it, placed by no item of its own
    assert plan["shapes"]["CRATE 1"]["shape"] == "circle" and plan["shapes"]["LAMP 1"]["base"] == 2.0
    # no filed plan names its doors (retired 2026-10-21): its doorway is the answer's opening, leading to the yard
    assert plan["doors"] == [] and [opening["to"] for opening in plan["openings"]] == ["yard"], plan["openings"]
    assert len(plan["walls"]) == 4 and plan["roofs"][0]["top"] == 3.4 and plan["section"] == {"y": 1.5}
    words = [gap["words"] for gap in plan["gaps"]]
    assert {"item": "ghost", "why": "no such row"} in plan["dropped"] and {"item": "walls", "why": "1 off the schema"} \
        in plan["dropped"]  # kept apart: no gap of his
    # the overlap parted before it is shown; the second crate has no box to place it by, so it is left, saying why
    assert words == [f"crate: 2 in the concept, 1 on the plan: {plan_fixes.WHY['placed']}"]
    assert [fix for fix in plan["fixes"] if "moved" in fix and "out of" in fix]
    assert not [word for word in words if "reached" in word or "outside" in word]
    assert plan_writing.write(store, ["shed"], "the allowance", clear=cleared(clears), ask=ask) == []  # written once
    plan["items"] = [[*item[:2], 0.3, *item[3:]] if item[0] == "CRATE 1" else item for item in plan["items"]]
    plan["items"].append(["CRATE 2", 3.2, 2.0, 0.5, 0.5, None, "item"])
    plan["rows"]["CRATE 2"] = ["crate"]
    plans.edited(store, "shed", plan, "joey")
    words = [gap["words"] for gap in plans.current(store, "shed")["plan"]["gaps"]]
    assert "bench 1 and crate 1 stand in each other (north)" in words
    assert "crate: 2 in the concept, 1 on the plan" not in words  # his second crate counts
    plan["items"] = [[*item[:2], 2.0, *item[3:]] if item[0] == "CRATE 1" else item for item in plan["items"]]
    plan["items"] = [item for item in plan["items"] if item[0] != "CRATE 2"]
    plans.edited(store, "shed", plan, "joey")
    words = [gap["words"] for gap in plans.current(store, "shed")["plan"]["gaps"]]
    assert "bench 1 and crate 1 stand in each other (north)" not in words  # his move, checked again


def test_a_door_walled_in_or_an_inside_place_overlapping_another_is_a_gap():
    plan = {"w": 6.0, "d": 4.0, "doors": [["S", 3.0, 1.0, "DOOR"]], "people": [[1.0, 1.0]],
            "items": [["WALL OF CRATES 1", 0.0, 2.0, 6.0, 0.6, None, "item"]], "rows": {"WALL OF CRATES 1": ["crate"]},
            "holds": [{"place": "a", "x": 0, "y": 0, "w": 3, "d": 2}, {"place": "b", "x": 2, "y": 0, "w": 3, "d": 2},
                      {"place": "c", "x": 5, "y": 3, "w": 3, "d": 3}]}
    inventory = {"rows": [{"id": "crate", "anchor": "floor", "count": 1}]}
    words = [gap["words"] for gap in plan_checks.checked(plan, inventory)]
    assert any(word.startswith("the standing spot (north-west)") and "reached" in word for word in words) or \
        any(word.startswith("the door on the south wall") and "reached" in word for word in words)
    assert "a and b overlap" in words and "c sticks out of the place" in words
    plan["shapes"] = {"WALL OF CRATES 1": {"shape": "rect", "tall": 0.05}}  # a cable on the floor: walked over
    assert not [word for word in plan_checks.checked(plan, inventory) if "reached" in word]
    plan["shapes"] = {}
    plan["items"][0][3] = 4.0  # a way round the crates: every door and spot reached
    assert not [word for word in plan_checks.checked(plan, inventory) if "reached" in word]


def test_a_footprint_answered_as_box_2d_is_measured_from_its_box():
    answer = {"outline": [[0, 0], [1000, 0], [1000, 1000], [0, 1000]],
              "items": [{"row": "bench", "box_2d": [100, 200, 160, 400]}],
              "places": [{"place": "nook", "box_2d": [500, 500, 700, 800]}]}
    inventory = {"rows": [{"id": "bench", "size": [2.0, 0.6, 0.9]}]}
    found, skeleton, how = plan_writing.measured(answer, {"w": 1.0, "d": 1.0}, inventory, held=False)
    assert how == {"metres a unit": [0.01, 0.01], "by": "its rows' metres"}
    assert (skeleton["w"], skeleton["d"]) == (10, 10)
    assert {key: found["items"][0][key] for key in ("x", "y", "wide", "deep")} == {"x": 3.0, "y": 1.3, "wide": 2.0,
                                                                                    "deep": 0.6}
    assert {key: found["places"][0][key] for key in ("x", "y", "w", "d")} == {"x": 5.0, "y": 5.0, "w": 3.0, "d": 2.0}


def test_an_arrangement_not_the_concepts_and_a_tube_joining_nothing_are_gaps():
    # the concept: a hub in the middle, a dome left of it, a hangar behind it, a tube from the hub to the dome
    inventory = {"picture": [1000, 1000], "rows": [
        {"id": "hub", "count": 1, "boxes": [[400, 400, 600, 600]]},
        {"id": "dome", "count": 1, "boxes": [[100, 420, 250, 580]]},
        {"id": "hangar", "count": 1, "boxes": [[350, 50, 650, 200]]},
        {"id": "tube", "count": 1, "boxes": [[250, 480, 400, 520]]}]}
    rows = {"HUB 1": ["hub"], "DOME 1": ["dome"], "HANGAR 1": ["hangar"], "TUBE 1": ["tube"]}
    laid = [["HUB 1", 20.0, 20.0, 10.0, 10.0, None, "item"], ["DOME 1", 2.0, 21.0, 8.0, 8.0, None, "item"],
            ["HANGAR 1", 15.0, 0.0, 20.0, 10.0, None, "item"], ["TUBE 1", 10.0, 24.0, 10.0, 2.0, None, "item"]]
    plan = {"w": 40.0, "d": 40.0, "doors": [], "people": [[30.0, 35.0]], "items": laid, "rows": rows}
    gaps = [gap for gap in plan_checks.checked(plan, inventory) if gap["kind"] in ("arrangement", "joined")]
    assert gaps == []  # as the concept, seen from the south
    packed = [["HUB 1", 20.0, 20.0, 10.0, 10.0, None, "item"], ["DOME 1", 31.0, 21.0, 8.0, 8.0, None, "item"],
              ["HANGAR 1", 15.0, 0.0, 20.0, 10.0, None, "item"], ["TUBE 1", 2.0, 34.0, 10.0, 2.0, None, "item"]]
    words = [gap["words"] for gap in plan_checks.checked({**plan, "items": packed}, inventory)
             if gap["kind"] in ("arrangement", "joined")]
    assert "dome is left of hub in the concept, right of it on the plan" in words
    assert "hub is joined by a tube in the concept, by none on the plan" in words


def test_a_row_off_to_the_side_or_facing_the_wrong_way_is_a_gap_and_a_run_of_crates_counts_whole_unless_spread():
    # the concept: a pad in the middle, a desk on the left, a rack on the right, all at about one depth
    inventory = {"picture": [1000, 1000], "rows": [
        {"id": "pad", "count": 1, "boxes": [[400, 600, 600, 700]]},
        {"id": "desk", "count": 1, "boxes": [[50, 600, 150, 700]]},
        {"id": "rack", "count": 1, "boxes": [[850, 600, 950, 700]]},
        {"id": "crate", "count": 6, "size": [0.8, 0.8, 0.8], "boxes": [[0, 0, 10, 10]]}]}
    rows = {"PAD 1": ["pad"], "DESK 1": ["desk"], "RACK 1": ["rack"], "CRATE 1": ["crate"]}
    laid = [["PAD 1", 14.0, 10.0, 4.0, 4.0, None, "item"], ["DESK 1", 1.0, 10.0, 2.0, 1.0, "S", "item"],
            ["RACK 1", 28.0, 10.0, 2.0, 1.0, None, "item"], ["CRATE 1", 1.0, 1.0, 4.0, 1.0, None, "item"]]
    plan = {"w": 32.0, "d": 20.0, "doors": [], "people": [[16.0, 18.0]], "items": laid, "rows": rows,
            "shapes": {"CRATE 1": {"count": 6}, "DESK 1": {"seen": ["toward"]}}}
    assert [gap["words"] for gap in plan_checks.checked(plan, inventory)] == []  # a run of 6 crates is all 6
    off = [["PAD 1", 22.0, 10.0, 4.0, 4.0, None, "item"], ["DESK 1", 1.0, 10.0, 2.0, 1.0, "N", "item"], *laid[2:]]
    words = [gap["words"] for gap in plan_checks.checked({**plan, "items": off}, inventory)]
    assert "pad stands in the middle of the concept (50% across), on the right of the plan (81% across)" in words
    assert "desk 1 faces toward in the concept, away on the plan" in words
    spread = [*laid[:3], ["CRATE 1", 1.0, 1.0, 12.0, 8.0, None, "item"]]  # 6 crates boxed round half the place
    words = [gap["words"] for gap in plan_checks.checked({**plan, "items": spread}, inventory)]
    assert "crate 1 boxes 6 things drawn apart as one (12.0 x 8.0 m), not one run" in words


def test_a_thing_the_creator_planned_is_laid_from_his_plan_where_and_the_way_it_is_drawn(monkeypatch):
    from score.review import creator_plans
    ship = {"what": "the ship's floor plan", "places": ["bridge", "hold"], "length": 10.0, "wide": 4.0, "base": 1.0,
            "tall": 3.0, "outline": [[0, 0], [2, 4], [2, 10], [-2, 10], [-2, 4]],
            "rooms": {"bridge": [[-1, 2], [1, 2], [1, 5], [-1, 5]], "hold": [[-2, 5], [2, 5], [2, 10], [-2, 10]]}}
    monkeypatch.setattr(creator_plans, "PLANS", (lambda: ship,))
    holds = [{"place": "bridge", "row": "ship", "x": 0, "y": 0, "w": 1, "d": 1},
             {"place": "hold", "row": "ship", "x": 1, "y": 0, "w": 1, "d": 1}]
    plan = {"items": [["SHIP 1", 18.0, 9.0, 4.0, 2.0, "E", "item"]], "rows": {"SHIP 1": ["ship"]}, "shapes": {},
            "holds": holds}
    laid, gaps = plan_writing.creator_laid(plan)
    assert laid == {"bridge", "hold"} and gaps == []
    assert plan["items"][0] == ["SHIP 1", 15.0, 8.0, 10.0, 4.0, "E", "item"]  # its own 10 x 4 m, nose east, same middle
    assert {hold["place"]: [hold["x"], hold["y"], hold["w"], hold["d"]] for hold in plan["holds"]} == {
        "bridge": [20.0, 9.0, 3.0, 2.0], "hold": [15.0, 8.0, 5.0, 4.0]}
    assert plan["shapes"]["SHIP 1"]["points"][0] == [1.0, 0.5] and plan["shapes"]["SHIP 1"]["base"] == 1.0
    plan["items"][0][5] = None
    assert plan_writing.creator_laid(plan)[1][0]["words"] == "the way ship 1's nose points was not read: laid nose E"


def test_people_on_their_person_spots_things_seen_far_off_and_rows_beyond_the_place_are_no_gaps():
    plan = {"w": 6.0, "d": 4.0, "doors": [], "people": [[4.0, 3.0, None, "diner"]],
            "items": [["CRATE 1", 1.0, 1.0, 1.0, 1.0, None, "item"], ["DINER 1", 1.2, 1.2, 0.5, 0.5, None, "item"],
                      ["DISTANT FLAG 1", 9.0, 1.0, 1.0, 1.0, None, "item"]],
            "rows": {"CRATE 1": ["crate"], "DINER 1": ["diner"], "DISTANT FLAG 1": ["distant_flag"]}}
    inventory = {"rows": [{"id": "crate", "count": 1}, {"id": "diner", "noun": "person", "count": 1},
                          {"id": "distant_flag", "count": 1}, {"id": "stage", "count": 1}]}
    assert [gap["words"] for gap in plan_checks.checked(plan, inventory)] == ["stage: 1 in the concept, 0 on the plan"]
    assert plan_checks.checked({**plan, "beyond": ["stage"]}, inventory) == []


def test_with_the_flag_off_a_writing_runs_only_inside_his_yes(store, data, gemini, monkeypatch):
    _, ask = gemini
    picked(store, "shed")
    monkeypatch.setattr(plan_writing, "AUTOMATIC", False)
    with pytest.raises(compute.Refused):
        plan_writing.write(store, ["shed"], "joey", ask=ask)

    def run(argv, env, **named):
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        record, = plan_writing.write(store, [argv[-3]], argv[-1], ask=ask)
        return subprocess.CompletedProcess(argv, 0, plan_writing.said(record) + "\n", "")

    with pytest.raises(web.review.Refused, match="not today's price"):
        web.plan_write(store, "shed", 0.09, "joey", run=run)
    price = plan_writing.price(store)  # the writing and its top-down drawing
    assert web.plan_write(store, "shed", price, "joey", run=run)["place"] == "shed"
    yes, = [store.read(key) for key in store.objects.keys("spend-yes/") if "plan-write-shed" in key]
    assert yes["euros"] == price and yes["by"] == "joey"
    assert plans.current(store, "shed")["how"] == "written"


def test_with_the_flag_on_his_click_asks_no_yes_and_a_reading_writes_its_plan(store, data, gemini, monkeypatch):
    from score.review import reading
    _, ask = gemini
    picked(store, "shed")
    ran = []

    def run(argv, env, **named):
        ran.append(env)
        return subprocess.CompletedProcess(argv, 0, "", "")

    assert web.plan_write(store, "shed", 0.0, "joey", run=run) == {"place": "shed", "written": "already"}
    assert "SCORE_SPEND_TICKET" not in ran[0] or ran[0]["SCORE_SPEND_TICKET"] == ""
    monkeypatch.setattr(plan_writing, "asked", ask)
    assert reading.planned(store, ["shed"], "the allowance") == 0
    assert plans.current(store, "shed")["how"] == "written"
    monkeypatch.setattr(plan_writing, "AUTOMATIC", False)
    assert reading.planned(store, ["yard"], "the allowance") == 0 and plan_writing.writings(store, "yard") == []


def test_a_read_place_with_no_plan_is_owed_unless_refused_and_an_older_methods_call_sets_no_price(store, data, gemini):
    picked(store, "shed")
    assert plan_writing.owed(store, ["shed", "yard"]) == ["shed"]
    record = {"place": "shed", "concept": plans.pick_of(store, "shed"), "method": plan_writing.METHOD,
              "reading": plan_writing.reading_at(store, "shed"), "at": "2026-10-21T00:00:00+00:00", "euros": 0.2,
              "refused": "no plan"}
    plan_writing.kept(store, record)
    assert plan_writing.to_write(store, ["shed"]) == ["shed"] and plan_writing.owed(store, ["shed"]) == []
    price = plan_writing.price(store)
    plan_writing.kept(store, {**record, "method": 1, "at": "2026-10-21T00:00:01+00:00", "euros": 0.9})
    assert plan_writing.price(store) == price  # an older method's dearer call is no price of today's
    started = []
    assert plan_writing.started(store, ["shed"], start=lambda argv, **named: started.append(argv)).endswith(".log")
    assert started[0][-2:] == ["score.review.plan_writing", "shed"]


def test_a_scene_added_in_the_app_takes_its_doors_from_its_holders_openings_into_it():
    """A place with no doors of its own (plans.base_plan's bare plan) standing in a holder's box gets a door for each
    holder opening in its walls: one into it leads back to the holder, one in a shared outer wall where that opening
    leads; the plan stage reads the door's height off its words. A place with doors of its own keeps them."""
    from score.stages.scene_record.plan import doors_of
    skeleton = {**plans.base_plan("no_such_place"), "w": 3.0, "d": 2.0}
    openings = [{"kind": "door", "at": [11.5, 7.0], "wide": 0.9, "sill": 0.0, "head": 2.1, "to": "airlock"},
                {"kind": "gate", "at": [13.05, 5.6], "wide": 1.2, "sill": 0.0, "head": 2.4, "to": "outside"},
                {"kind": "door", "at": [0.0, 1.0], "wide": 0.9, "sill": 0.0, "head": 2.1, "to": "sealed"}]
    found = plan_writing.held_doors(skeleton, "airlock", "hangar", [10.0, 5.0, 3.0, 2.0], openings)
    assert found["doors"] == [["S", 1.5, 0.9, "door 0.9 x 2.1 m"], ["E", 0.6, 1.2, "gate 1.2 x 2.4 m"]], found
    assert {key: lead["to"] for key, lead in found["leads"].items()} == {"S": "hangar", "E": "outside"}
    made = doors_of(found, {"rows": []})
    assert [(door["side"], door["leads"], door["tall"], door["cut"]) for door in made] == [
        ("south", "hangar", 2.1, True), ("east", "outside", 2.4, True)], made
    own = {**skeleton, "doors": [["N", 1.0, 0.9, "DOOR"]], "leads": {"N": {"to": "sealed", "why": "filed"}}}
    assert plan_writing.held_doors(own, "airlock", "hangar", [10.0, 5.0, 3.0, 2.0], openings) is own


# --- the free fixes of a written plan (plan_fixes.py): free first, a Correct kept only when it leaves fewer gaps -------

ROWS = [  # three rows boxed once on a 1000 px concept, laid so the projection is x = 10 across, y = 10 foot
    {"id": "desk", "count": 1, "size": [1.0, 1.0, 1.0], "boxes": [[150, 400, 250, 500]]},
    {"id": "rack", "count": 1, "size": [1.0, 1.0, 1.0], "boxes": [[750, 400, 850, 500]]},
    {"id": "pad", "count": 1, "size": [1.0, 1.0, 1.0], "boxes": [[450, 800, 550, 900]]},
    {"id": "barrel", "count": 2, "size": [1.0, 1.0, 1.0], "boxes": [[150, 600, 250, 700], [750, 600, 850, 700]]},
    {"id": "worker", "noun": "person", "count": 1, "boxes": [[480, 200, 520, 300]]},
    {"id": "crate", "count": 1, "size": [0.6, 0.6, 0.6]}]


def stand_in_plan():
    items = [["DESK 1", 1.5, 4.5, 1.0, 1.0, "N", "item"], ["RACK 1", 7.5, 4.5, 1.0, 1.0, None, "item"],
             ["PAD 1", 4.5, 8.5, 1.0, 1.0, None, "item"], ["BARREL 1", 7.5, 6.5, 1.0, 1.0, None, "item"],
             ["WORKER 1", 4.8, 2.8, 0.4, 0.4, None, "item"], ["CRATE 1", 1.8, 4.8, 0.6, 0.6, None, "item"]]
    return {"w": 10.0, "d": 10.0, "doors": [], "people": [[9.5, 9.5]], "items": items,
            "rows": {item[0]: [item[0].split(" ")[0].lower()] for item in items},
            "shapes": {"DESK 1": {"shape": "rect", "seen": ["toward"]}}}


def test_the_free_fixes_stand_people_place_the_missing_turn_and_part_and_leave_the_rest_saying_why():
    inventory = {"picture": [1000, 1000], "rows": ROWS}
    plan = stand_in_plan()
    before = [gap["kind"] for gap in plan_checks.checked(plan, inventory)]
    assert {"placed", "people", "overlap", "arrangement"} <= set(before)
    plan, fixes = plan_fixes.fixed(plan, inventory)
    assert plan["people"][0] == [5.0, 3.0, 0.0, "worker"] and plan["people"][1] == [9.5, 9.5]
    assert "WORKER 1" not in {item[0] for item in plan["items"]}  # a person is no furniture
    barrels = sorted((item[1], item[2]) for item in plan["items"] if item[0].startswith("BARREL"))
    assert barrels == [(1.5, 6.5), (7.5, 6.5)]  # the missing one where its box projects
    assert {item[0]: item for item in plan["items"]}["DESK 1"][5] == "S"  # it faces the viewer in the concept
    assert plan_checks.checked(plan, inventory) == [] and len(fixes) == 4


def test_a_missing_thing_crossing_one_of_its_row_is_piled_on_it():
    """2026-10-30: placed_missing laid each missing copy at full size with no neighbour check, so airlock's sandbags
    stood in each other by 5 to 25 cm. A sack laid at plan (3.3, 2.3) and two missing ones projecting to (3.5, 2.3)
    and (6.3, 2.3): the first crosses it and is piled on it (base its 0.2 m tall), the second stands on the floor.
    Break: score/review/plan_fixes.py: `            if base:` -> `            if False:`"""
    sack = {"id": "sack", "count": 3, "size": [0.6, 0.4, 0.2],
            "boxes": [[300, 200, 360, 230], [320, 200, 380, 230], [600, 200, 660, 230]]}
    inventory = {"picture": [1000, 1000], "rows": [*ROWS, sack]}
    plan = stand_in_plan()
    plan["items"].append(["SACK 1", 3.0, 2.1, 0.6, 0.4, None, "item"])
    plan["rows"]["SACK 1"] = ["sack"]
    plan_fixes.placed_missing(plan, inventory, plan_fixes.projector(plan, inventory))
    sacks = {item[0]: [item[1], item[2], plan["shapes"][item[0]].get("base")] for item in plan["items"]
             if item[0].startswith("SACK") and item[0] != "SACK 1"}
    assert sacks == {"SACK 2": [3.2, 2.1, 0.2], "SACK 3": [6.0, 2.1, None]}, sacks


def test_a_box_of_things_drawn_apart_is_split_round_its_spread():
    inventory = {"rows": [{"id": "tree", "count": 4, "size": [1.0, 1.0, 5.0]}]}
    plan = {"w": 12.0, "d": 12.0, "doors": [], "people": [], "items": [["TREE 1", 1.0, 1.0, 10.0, 10.0, None, "item"]],
            "rows": {"TREE 1": ["tree"]}, "shapes": {"TREE 1": {"shape": "circle", "count": 4}}}
    assert plan_checks.run_gaps(plan, inventory)
    fixes = plan_fixes.split_runs(plan, inventory, None)
    assert fixes == ["tree 1: split into its 4 things"] and len(plan["items"]) == 4
    assert all(item[3] == 1.0 and plan["shapes"][item[0]] == {"shape": "circle"} for item in plan["items"])
    assert not plan_checks.run_gaps(plan, inventory)


def test_a_correction_is_kept_only_when_it_leaves_fewer_gaps_and_what_is_left_says_why(monkeypatch):
    inventory = {"picture": [1000, 1000], "rows": [row for row in ROWS if row["id"] != "barrel"] + [
        {"id": "stool", "count": 1, "size": [0.5, 0.5, 0.5]}]}  # no box: no free fix places it
    answers = []

    def correcting(store, place, plan, left, ask):
        answers.append([gap["words"] for gap in left])
        laid = plan["items"] + [["STOOL 1", 3.0, 3.0, 0.5, 0.5, None, "item"]] if len(answers) == 1 else plan["items"]
        return {**plan, "items": laid, "rows": {**plan["rows"], "STOOL 1": ["stool"]}}, {"euros": 0.07}
    monkeypatch.setattr(plan_fixes, "corrected", correcting)
    plan, calls = plan_fixes.settled(None, "shed", stand_in_plan(), inventory, ask=None)
    assert answers == [["stool: 1 in the concept, 0 on the plan"]] and calls == [{"euros": 0.07}]
    assert plan["gaps"] == [] and "the prompt model corrected 1 gaps" in plan["fixes"]
    monkeypatch.setattr(plan_fixes, "corrected", lambda *args: (args[2], {"euros": 0.07}))  # changes nothing
    plan, calls = plan_fixes.settled(None, "shed", stand_in_plan(), inventory, ask=None)
    assert len(calls) == 1 and [gap["words"] for gap in plan["gaps"]] == [
        f"stool: 1 in the concept, 0 on the plan: {plan_fixes.WHY['placed']}"]


def test_a_row_at_the_concept_s_foot_marked_beyond_is_placed_where_its_box_projects():
    """2026-10-26: the airlock's sandbags at its picture's foot were marked beyond and had no plan item, and its rows
    of several things and its rows on the floor plates fitted no projection: now they fit it, and the row is placed."""
    cube = [1.0, 1.0, 1.0]
    rows = [{"id": "plates", "anchor": "ground", "count": 1, "boxes": [[0, 500, 1000, 1000]]},
            {"id": "barrel", "count": 2, "size": cube, "boxes": [[150, 400, 250, 500], [750, 400, 850, 500]]},
            {"id": "pallet", "anchor": "on:plates", "count": 1, "size": cube, "boxes": [[450, 700, 550, 800]]},
            {"id": "desk", "count": 1, "size": cube, "boxes": [[750, 200, 850, 300]]},
            {"id": "sandbags", "anchor": "ground", "count": 1, "size": cube, "boxes": [[450, 900, 550, 1000]]}]
    items = [["BARREL 1", 1.5, 4.5, 1.0, 1.0, None, "item"], ["BARREL 2", 7.5, 4.5, 1.0, 1.0, None, "item"],
             ["PALLET 1", 4.5, 7.5, 1.0, 1.0, None, "item"], ["DESK 1", 7.5, 2.5, 1.0, 1.0, None, "item"]]
    plan = {"w": 10.0, "d": 10.0, "doors": [], "people": [], "items": items, "structure": ["plates"],
            "beyond": ["sandbags"], "rows": {item[0]: [item[0].split(" ")[0].lower()] for item in items}}
    inventory = {"picture": [1000, 1000], "rows": rows}
    assert [gap["row"] for gap in plan_checks.checked(plan, inventory, ["plates"]) if gap["kind"] == "placed"] == [
        "sandbags"]  # the check lists it, its plan's beyond notwithstanding
    plan, fixes = plan_fixes.fixed(plan, inventory)
    assert plan["beyond"] == [] and fixes[0].startswith("sandbags: at the concept's foot")
    sandbags = [item for item in plan["items"] if item[0] == "SANDBAGS 1"]
    assert sandbags and (sandbags[0][1], sandbags[0][2]) == (4.5, 9.5)  # its box's foot projects to y = 10


# --- the sync pass's plans keep (plans_pass.py): the narrow walk, one moment, a re-fix in its own process --------

KEYS = ["outputs/a.json", "outputs/ab/c.json", "outputs/b.json", "plans/x/edits/1.json", "plans/xy/edits/2.json",
        "blobs/abc", "top.json"]


def test_the_narrow_walk_answers_as_the_whole_walk():
    with tempfile.TemporaryDirectory() as folder:
        store = runtime_store.FolderStore(folder)
        for key in KEYS:
            store.write_bytes(key, b"{}")
        store.write_bytes("outputs/half.json.partial", b"")
        whole = runtime_store.FolderStore.keys
        for prefix in ("", "outputs/", "outputs/a", "outputs/ab/", "plans/x", "plans/x/", "plans/x/edits/1", "to",
                       "missing/", "missing/deeper/x"):
            assert plans_pass.narrow_keys(store, prefix) == whole(store, prefix), prefix


def test_the_keep_runs_inside_one_moment():
    seen = {}
    before = (runtime_store.FolderStore.keys, plans.main, plans_pass.restored, plans_pass.to_fix, stages.places,
              plans_pass.parted_first)

    def main(argv):
        seen["argv"], seen["moment"] = argv, plans.HELD.get() is not None
        seen["parted before the keep"] = "parted first" in seen
        seen["narrow"] = runtime_store.FolderStore.keys is plans_pass.narrow_keys
        print("plans for the plan stage: 1 kept")
        return 0
    plans.main = main
    plans_pass.restored = lambda store: seen.setdefault("restored", plans.HELD.get() is not None)
    plans_pass.to_fix = lambda store, places: seen.setdefault("fix asked", places) and []
    plans_pass.parted_first = lambda store, places: (
        seen.setdefault("parted first", (places, plans.HELD.get() is None)) and ["airlock"])
    stages.places = lambda world, store: ["shed"]
    said = io.StringIO()
    try:
        with contextlib.redirect_stdout(said):
            assert plans_pass.main() == 0
    finally:
        (runtime_store.FolderStore.keys, plans.main, plans_pass.restored, plans_pass.to_fix, stages.places,
         plans_pass.parted_first) = before
    assert seen == {"argv": ["keep"], "moment": True, "narrow": True, "restored": True, "fix asked": ["shed"],
                    "parted first": (["shed"], True), "parted before the keep": True}, seen
    assert said.getvalue() == "plans for the plan stage: 1 kept; plans of airlock parted\n", said.getvalue()


def test_a_plan_fixed_before_a_fix_it_needs_is_fixed_again_in_a_process_of_its_own():
    """2026-10-26: the airlock's plan was fixed before rows at the concept's foot were brought in from beyond, so its
    sandbags stayed unplaced; once fixed again, it is settled."""
    cube = [1.0, 1.0, 1.0]
    rows = [{"id": "plates", "anchor": "ground", "count": 1, "boxes": [[0, 500, 1000, 1000]]},
            {"id": "barrel", "count": 2, "size": cube, "boxes": [[150, 400, 250, 500], [750, 400, 850, 500]]},
            {"id": "pallet", "anchor": "on:plates", "count": 1, "size": cube, "boxes": [[450, 700, 550, 800]]},
            {"id": "desk", "count": 1, "size": cube, "boxes": [[750, 200, 850, 300]]},
            {"id": "sandbags", "anchor": "ground", "count": 1, "size": cube, "boxes": [[450, 900, 550, 1000]]}]
    items = [["BARREL 1", 1.5, 4.5, 1.0, 1.0, None, "item"], ["BARREL 2", 7.5, 4.5, 1.0, 1.0, None, "item"],
             ["PALLET 1", 4.5, 7.5, 1.0, 1.0, None, "item"], ["DESK 1", 7.5, 2.5, 1.0, 1.0, None, "item"]]
    plan = {"w": 10.0, "d": 10.0, "doors": [], "people": [], "items": items, "structure": ["plates"], "fixes": [],
            "beyond": ["sandbags"], "rows": {item[0]: [item[0].split(" ")[0].lower()] for item in items}}
    inventory = {"picture": [1000, 1000], "rows": rows}
    assert plans_pass.unsettled(plan, inventory)
    fixed, fixes = plan_fixes.fixed(plan, inventory)
    assert not plans_pass.unsettled({**fixed, "fixes": fixes}, inventory)
    started = []
    with tempfile.TemporaryDirectory() as folder:
        store = Store.in_folder(folder)
        plans_pass.fixing(store, ["airlock"], lambda command, **options: started.append(command))
    assert started and started[0][-3:] == ["score.review.plans_pass", "fix", "airlock"], started


def test_a_fixed_plan_with_a_pile_is_parted_again_free_and_then_settled():
    """2026-10-26: the airlock's sandbags stayed in each other after the nudge; the relation solver parts them on a
    re-fix, free (no Correct asked for overlaps alone), and the parted plan is not fixed again."""
    items = [[f"SANDBAGS {number}", 1.2, 1.3, 0.6, 0.35, None, "item"] for number in range(1, 7)]
    plan = {"w": 3.0, "d": 3.0, "doors": [], "people": [], "items": items, "fixes": ["earlier fix"], "gaps": [],
            "rows": {item[0]: ["sandbags"] for item in items}}
    inventory = {"rows": [{"id": "sandbags", "anchor": "ground", "count": 6, "size": [0.6, 0.35, 0.15]}]}
    assert not plans_pass.placing_more(plan, inventory) and plans_pass.unsettled(plan, inventory)

    def ask(body):
        raise AssertionError("no Correct is asked for overlaps alone")
    fixed, calls = plans_pass.settled_again(None, "airlock", plan, inventory, ask)
    assert calls == [] and fixed["fixes"][0] == "earlier fix" and len(fixed["fixes"]) >= 6
    assert not [gap for gap in fixed["gaps"] if gap["kind"] == "overlap"] and not plans_pass.unsettled(fixed, inventory)


def piled():
    """Six sandbags in one spot on a 3 m floor, fixed once: only the relation solver re-fixes it."""
    items = [[f"SANDBAGS {number}", 1.2, 1.3, 0.6, 0.35, None, "item"] for number in range(1, 7)]
    plan = {"w": 3.0, "d": 3.0, "doors": [], "people": [], "items": items, "fixes": ["earlier fix"], "gaps": [],
            "rows": {item[0]: ["sandbags"] for item in items}}
    return plan, {"rows": [{"id": "sandbags", "anchor": "ground", "count": 6, "size": [0.6, 0.35, 0.15]}]}


def test_an_accepted_plan_row_is_never_parted_and_an_unaccepted_one_is_parted_before_the_keep():
    """Review of 2026-10-26: plan@habitat stands accepted, so a parted writing would re-key it and every row after it;
    the airlock's plan is still to run, so it is parted in the pass, before `plans keep` makes its plan row."""
    plan, inventory = piled()
    kept = []
    before = plan_writing.written_of, plans.inventory_of, plan_writing.kept
    with tempfile.TemporaryDirectory() as folder:
        store = Store.in_folder(folder)
        standing = {"plan@habitat": "the accepted output"}
        store.accepted = standing.get
        plan_writing.written_of = lambda store, place: {"place": place, "at": "then", "plan": plan}
        plans.inventory_of = lambda store, place: inventory
        plan_writing.kept = lambda store, record: kept.append(record) or record
        try:
            assert not plans_pass.parting(store, "habitat") and plans_pass.parting(store, "airlock")
            assert plans_pass.to_fix(store, ["habitat", "airlock"]) == ["airlock"]
            assert plans_pass.refixed(store, "habitat", "test", plans_pass.unasked) is None
            assert plans_pass.parted_first(store, ["habitat", "airlock"]) == ["airlock"]
        finally:
            plan_writing.written_of, plans.inventory_of, plan_writing.kept = before
    assert [record["place"] for record in kept] == ["airlock"] and kept[0]["euros"] == 0.0 and kept[0]["calls"] == []
    assert not plans_pass.unsettled(kept[0]["plan"], inventory)


def test_a_plan_that_places_more_is_left_to_its_own_process_not_parted_first():
    """A re-fix that may ask Corrects (`placing_more`) is never made in the pass: `fixing` makes it under the
    allowance; the accepted row's placing re-fix still runs there, without the solver."""
    plan, inventory = piled()
    plan = {key: value for key, value in plan.items() if key != "fixes"}
    before = plan_writing.written_of, plans.inventory_of
    with tempfile.TemporaryDirectory() as folder:
        store = Store.in_folder(folder)
        store.accepted = {"plan@habitat": "the accepted output"}.get
        plan_writing.written_of = lambda store, place: {"place": place, "at": "then", "plan": plan}
        plans.inventory_of = lambda store, place: inventory
        try:
            assert plans_pass.parted_first(store, ["habitat", "airlock"]) == []
            assert plans_pass.to_fix(store, ["habitat", "airlock"]) == ["habitat", "airlock"]
        finally:
            plan_writing.written_of, plans.inventory_of = before
    asked = []
    fixed, calls = plans_pass.settled_again(None, "habitat", {**plan, "fixes": []}, inventory, asked.append,
                                            parts=False)
    assert fixed["items"] == plan["items"] and calls == [] and asked == []


def test_a_done_place_with_no_kept_plan_gets_one():
    """The wreck, 2026-10-24: an outside place in no tree whose kept plan was taken out is kept again; a place whose
    plan is kept is not asked again."""
    asked = {}
    before = stages.places, plans.keep, plans.KEPT
    with tempfile.TemporaryDirectory() as folder:
        plans.KEPT = pathlib.Path(folder)
        (plans.KEPT / "hangar.json").write_text("{}")
        stages.places = lambda world, store: ["hangar", "wreck"]
        plans.keep = lambda store, places: (asked.setdefault("places", places), places)
        try:
            assert plans_pass.restored("the store") == ["wreck"]
        finally:
            stages.places, plans.keep, plans.KEPT = before
    assert asked == {"places": ["wreck"]}, asked
